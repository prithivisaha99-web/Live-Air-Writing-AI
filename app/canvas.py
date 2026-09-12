"""Virtual Canvas & Vector Rendering Widget using PySide6 QPainter with Unified Display Geometry & Crosshair Debug."""
import enum
import os
from datetime import datetime
import logging
import numpy as np

from PySide6.QtWidgets import QWidget, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QRectF, Signal, Slot
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QImage, QPixmap, QBrush, QFont
)

from app.drawing_tools import VectorStroke, UndoRedoManager

logger = logging.getLogger(__name__)


class CanvasMode(enum.Enum):
    CAMERA_OVERLAY = "Camera Workspace"
    DARK = "Dark Canvas"
    LIGHT = "Light Canvas"


class AirWritingCanvas(QWidget):
    """High-performance virtual drawing canvas for rendering air strokes with unified coordinate mapping and live crosshair debug."""

    stroke_added = Signal()

    def __init__(self, undo_redo_manager: UndoRedoManager, parent=None):
        super().__init__(parent)
        self.undo_redo = undo_redo_manager
        self.undo_redo.history_changed.connect(self.update)
        
        self.mode = CanvasMode.CAMERA_OVERLAY
        self.camera_pixmap: QPixmap | None = None
        self.active_stroke: VectorStroke | None = None

        # Default Tool Settings
        self.current_color = QColor("#00F0FF")  # Neon Cyan
        self.current_brush_width = 8
        self.is_eraser_active = False
        self.eraser_width = 30

        # On-Screen Diagnostic HUD Data
        self.show_diagnostic = True
        self.diag_info = {
            "hand_count": 0,
            "raw_index": None,
            "smooth_index": None,
            "gesture": "NO HAND",
            "is_drawing": False,
            "raw_count": 0,
            "interp_count": 0,
            "stroke_points": 0,
            "fps": 0.0,
            "index_state": "NONE",
            "middle_state": "NONE",
            "ring_state": "NONE",
            "pinky_state": "NONE"
        }

        self.setMinimumSize(640, 480)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def set_canvas_mode(self, mode: CanvasMode) -> None:
        self.mode = mode
        self.update()

    def set_diagnostic_info(self, info: dict) -> None:
        """Update live diagnostic overlay metrics."""
        finger_states = info.get("finger_states", {})
        self.diag_info = {
            "hand_count": info.get("hand_count", 0),
            "raw_index": info.get("raw_index"),
            "smooth_index": info.get("smooth_index"),
            "gesture": info.get("gesture").value if hasattr(info.get("gesture"), "value") else str(info.get("gesture", "NO HAND")),
            "is_drawing": bool(info.get("is_drawing", False)),
            "raw_count": info.get("raw_count", 0),
            "interp_count": info.get("interp_count", 0),
            "stroke_points": info.get("stroke_points", 0),
            "fps": info.get("vision_fps", info.get("fps", 0.0)),
            "index_state": finger_states.get("Index", "NONE"),
            "middle_state": finger_states.get("Middle", "NONE"),
            "ring_state": finger_states.get("Ring", "NONE"),
            "pinky_state": finger_states.get("Pinky", "NONE")
        }
        self.update()

    def set_camera_frame(self, cv_bgr_frame: np.ndarray) -> None:
        """Convert BGR OpenCV frame to QPixmap for rendering as background."""
        h, w, ch = cv_bgr_frame.shape
        bytes_per_line = ch * w
        rgb_frame = np.ascontiguousarray(cv_bgr_frame[:, :, ::-1])
        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.camera_pixmap = QPixmap.fromImage(qimg)
        self.update()

    def start_active_stroke(self, start_norm_pt: tuple[float, float]) -> None:
        width = self.eraser_width if self.is_eraser_active else self.current_brush_width
        self.active_stroke = VectorStroke(
            points=[start_norm_pt],
            color=QColor(0, 0, 0, 0) if self.is_eraser_active else QColor(self.current_color),
            width=width,
            is_eraser=self.is_eraser_active
        )
        self.update()

    def update_active_stroke(self, norm_pt: tuple[float, float]) -> None:
        if self.active_stroke:
            self.active_stroke.points.append(norm_pt)
            self.update()

    def commit_active_stroke(self) -> None:
        if self.active_stroke and len(self.active_stroke.points) > 1:
            self.undo_redo.add_stroke(self.active_stroke)
            self.stroke_added.emit()
        self.active_stroke = None
        self.update()

    def cancel_active_stroke(self) -> None:
        self.active_stroke = None
        self.update()

    def get_display_geometry(self) -> tuple[float, float, float, float]:
        """
        Calculates the single unified display rectangle for the camera background and vector strokes.
        Returns: (offset_x, offset_y, display_width, display_height)
        """
        canvas_w = float(self.width())
        canvas_h = float(self.height())

        if self.mode == CanvasMode.CAMERA_OVERLAY and self.camera_pixmap and not self.camera_pixmap.isNull():
            cam_w = float(self.camera_pixmap.width())
            cam_h = float(self.camera_pixmap.height())
            if cam_w > 0 and cam_h > 0:
                scale = min(canvas_w / cam_w, canvas_h / cam_h)
                display_w = cam_w * scale
                display_h = cam_h * scale
                offset_x = (canvas_w - display_w) / 2.0
                offset_y = (canvas_h - display_h) / 2.0
                return (offset_x, offset_y, display_w, display_h)

        return (0.0, 0.0, canvas_w, canvas_h)

    def norm_to_widget(self, nx: float, ny: float) -> tuple[float, float]:
        """Convert normalized camera coordinate (0.0 to 1.0) to exact widget pixel coordinate."""
        offset_x, offset_y, display_w, display_h = self.get_display_geometry()
        px = offset_x + nx * display_w
        py = offset_y + ny * display_h
        return (px, py)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        rect = self.rect()
        offset_x, offset_y, display_w, display_h = self.get_display_geometry()

        # 1. Render Background Layer
        if self.mode == CanvasMode.CAMERA_OVERLAY:
            painter.fillRect(rect, QColor("#0F172A"))
            if self.camera_pixmap and not self.camera_pixmap.isNull():
                target_rect = QRectF(offset_x, offset_y, display_w, display_h)
                source_rect = QRectF(0, 0, self.camera_pixmap.width(), self.camera_pixmap.height())
                painter.drawPixmap(target_rect, self.camera_pixmap, source_rect)
        elif self.mode == CanvasMode.DARK:
            painter.fillRect(rect, QColor("#0B0F17"))
            self._draw_grid(painter, rect, QColor(255, 255, 255, 12))
        elif self.mode == CanvasMode.LIGHT:
            painter.fillRect(rect, QColor("#FFFFFF"))
            self._draw_grid(painter, rect, QColor(0, 0, 0, 15))

        # 2. Render Committed History Vector Strokes
        for stroke in self.undo_redo.history:
            self._draw_vector_stroke(painter, stroke, offset_x, offset_y, display_w, display_h)

        # 3. Render Active Live Vector Stroke
        if self.active_stroke:
            self._draw_vector_stroke(painter, self.active_stroke, offset_x, offset_y, display_w, display_h)

        # 4. TEMPORARY DEBUG CROSSHAIR at mapped fingertip position
        smooth_idx = self.diag_info.get("smooth_index")
        if smooth_idx and self.diag_info.get("hand_count", 0) > 0:
            cx, cy = self.norm_to_widget(smooth_idx[0], smooth_idx[1])
            self._draw_debug_crosshair(painter, cx, cy)

        # 5. Render On-Screen Diagnostic Overlay HUD
        if self.show_diagnostic:
            self._draw_diagnostic_hud(painter)

        painter.end()

    def _draw_grid(self, painter: QPainter, rect: QRectF, color: QColor) -> None:
        """Render subtle background grid."""
        grid_size = 40
        pen = QPen(color, 1, Qt.PenStyle.DotLine)
        painter.setPen(pen)

        width = int(rect.width())
        height = int(rect.height())

        for x in range(0, width, grid_size):
            painter.drawLine(x, 0, x, height)
        for y in range(0, height, grid_size):
            painter.drawLine(0, y, width, y)

    def _draw_vector_stroke(
        self,
        painter: QPainter,
        stroke: VectorStroke,
        offset_x: float,
        offset_y: float,
        display_w: float,
        display_h: float
    ) -> None:
        if len(stroke.points) < 1:
            return

        pixel_points = [(offset_x + nx * display_w, offset_y + ny * display_h) for nx, ny in stroke.points]

        if len(pixel_points) == 1:
            pt = pixel_points[0]
            pen = QPen(stroke.color, stroke.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPoint(int(pt[0]), int(pt[1]))
            return

        path = QPainterPath()
        if len(pixel_points) == 2:
            path.moveTo(pixel_points[0][0], pixel_points[0][1])
            path.lineTo(pixel_points[1][0], pixel_points[1][1])
        else:
            path.moveTo(pixel_points[0][0], pixel_points[0][1])
            first_mid_x = (pixel_points[0][0] + pixel_points[1][0]) / 2.0
            first_mid_y = (pixel_points[0][1] + pixel_points[1][1]) / 2.0
            path.lineTo(first_mid_x, first_mid_y)

            for i in range(1, len(pixel_points) - 1):
                p0 = pixel_points[i]
                p1 = pixel_points[i + 1]
                mid_x = (p0[0] + p1[0]) / 2.0
                mid_y = (p0[1] + p1[1]) / 2.0
                path.quadTo(p0[0], p0[1], mid_x, mid_y)

            path.lineTo(pixel_points[-1][0], pixel_points[-1][1])

        if stroke.is_eraser:
            eraser_color = QColor("#0B0F17") if self.mode in (CanvasMode.CAMERA_OVERLAY, CanvasMode.DARK) else QColor("#FFFFFF")
            pen = QPen(eraser_color, stroke.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(path)
        else:
            # Glow effect for Dark / Overlay mode
            if self.mode in (CanvasMode.CAMERA_OVERLAY, CanvasMode.DARK):
                glow_color = QColor(stroke.color)
                glow_color.setAlpha(60)
                glow_pen = QPen(glow_color, stroke.width + 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(glow_pen)
                painter.drawPath(path)

            # Core stroke
            core_pen = QPen(stroke.color, stroke.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(core_pen)
            painter.drawPath(path)

    def _draw_debug_crosshair(self, painter: QPainter, cx: float, cy: float) -> None:
        """Render high-visibility neon crosshair at the exact mapped drawing coordinate."""
        # Outer cyan ring
        painter.setPen(QPen(QColor("#00F0FF"), 2, Qt.PenStyle.SolidLine))
        painter.drawEllipse(QRectF(cx - 12, cy - 12, 24, 24))
        
        # Red crosshair lines
        painter.setPen(QPen(QColor("#FF0055"), 2, Qt.PenStyle.SolidLine))
        painter.drawLine(int(cx - 18), int(cy), int(cx + 18), int(cy))
        painter.drawLine(int(cx), int(cy - 18), int(cx), int(cy + 18))
        
        # Center red dot
        painter.setBrush(QBrush(QColor("#FF0055")))
        painter.drawEllipse(QRectF(cx - 4, cy - 4, 8, 8))

    def _draw_diagnostic_hud(self, painter: QPainter) -> None:
        """Render live diagnostic stats block on top-left of canvas."""
        hud_w, hud_h = 240, 240
        padding = 12
        x, y = 16, 16

        # Translucent glass box background
        hud_rect = QRectF(x, y, hud_w, hud_h)
        painter.fillRect(hud_rect, QColor(15, 23, 42, 220))
        
        pen = QPen(QColor(0, 240, 255, 180), 1)
        painter.setPen(pen)
        painter.drawRoundedRect(hud_rect, 8, 8)

        # Monospace font for aligned metrics display
        font = QFont("Consolas", 9, QFont.Weight.Bold)
        font.setStyleHint(QFont.StyleHint.Monospace)
        painter.setFont(font)

        gesture = self.diag_info["gesture"]
        is_drawing = self.diag_info["is_drawing"]
        fps = self.diag_info["fps"]

        raw_cnt = self.diag_info.get("raw_count", 0)
        interp_cnt = self.diag_info.get("interp_count", 0)
        stroke_pts = self.diag_info.get("stroke_points", 0)

        idx_st = self.diag_info.get("index_state", "NONE")
        mid_st = self.diag_info.get("middle_state", "NONE")
        rng_st = self.diag_info.get("ring_state", "NONE")
        pnk_st = self.diag_info.get("pinky_state", "NONE")

        lines = [
            ("Index:", f"{idx_st}", QColor("#10B981") if idx_st == "EXTENDED" else QColor("#EF4444")),
            ("Middle:", f"{mid_st}", QColor("#10B981") if mid_st == "EXTENDED" else QColor("#EF4444")),
            ("Ring:", f"{rng_st}", QColor("#10B981") if rng_st == "EXTENDED" else QColor("#EF4444")),
            ("Pinky:", f"{pnk_st}", QColor("#10B981") if pnk_st == "EXTENDED" else QColor("#EF4444")),
            ("Gesture:", f"{gesture}", QColor("#F59E0B") if gesture == "DRAW" else (QColor("#EC4899") if gesture == "ERASER" else QColor("#38BDF8"))),
            ("Drawing Active:", f"{is_drawing}", QColor("#10B981") if is_drawing else QColor("#EF4444")),
            ("Raw/Frame:", f"{raw_cnt}", QColor("#38BDF8")),
            ("Interp/Frame:", f"{interp_cnt}", QColor("#38BDF8")),
            ("Active Stroke Pts:", f"{stroke_pts}", QColor("#00F0FF")),
            ("FPS:", f"{fps:.1f}", QColor("#A855F7"))
        ]

        line_y = y + padding + 12
        for label, val, val_color in lines:
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(int(x + padding), int(line_y), label)
            
            painter.setPen(val_color)
            painter.drawText(int(x + padding + 115), int(line_y), val)
            line_y += 20

    def export_image(self, file_path: str = "", transparent: bool = False) -> str | None:
        """Export high-resolution PNG image of the canvas."""
        export_size = self.size()
        image = QImage(export_size, QImage.Format.Format_ARGB32)
        
        if transparent:
            image.fill(Qt.GlobalColor.transparent)
        else:
            bg_color = QColor("#0B0F17") if self.mode in (CanvasMode.DARK, CanvasMode.CAMERA_OVERLAY) else QColor("#FFFFFF")
            image.fill(bg_color)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        if not transparent:
            grid_color = QColor(255, 255, 255, 15) if self.mode in (CanvasMode.DARK, CanvasMode.CAMERA_OVERLAY) else QColor(0, 0, 0, 15)
            self._draw_grid(painter, QRectF(0, 0, export_size.width(), export_size.height()), grid_color)

        offset_x, offset_y, display_w, display_h = self.get_display_geometry()
        for stroke in self.undo_redo.history:
            self._draw_vector_stroke(painter, stroke, offset_x, offset_y, display_w, display_h)
            
        painter.end()

        if not file_path:
            out_dir = os.path.join(os.getcwd(), "saved_drawings")
            os.makedirs(out_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(out_dir, f"air_writing_{timestamp}.png")

        success = image.save(file_path, "PNG")
        if success:
            logger.info(f"Canvas saved successfully to: {file_path}")
            return file_path
        else:
            logger.error(f"Failed to save canvas image to: {file_path}")
            return None
