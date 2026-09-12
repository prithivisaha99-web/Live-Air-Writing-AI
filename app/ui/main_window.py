"""Main Application Window with strict state management and normalized air writing pipeline."""
import os
import logging
import numpy as np

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFileDialog, QMessageBox, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont

from app.settings import SettingsManager
from app.drawing_tools import UndoRedoManager
from app.canvas import AirWritingCanvas, CanvasMode
from app.ai_service import AIService
from app.vision_worker import VisionWorkerThread
from app.gesture_detection import GestureType, GestureMode

from app.ui.styles import DARK_FUTURISTIC_STYLE
from app.ui.startup_screen import StartupScreen
from app.ui.toolbar import DrawingToolbar
from app.ui.ai_panel import AIAssistPanel
from app.ui.settings_panel import SettingsDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main Workspace Window for Live Air Writing AI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Live Air Writing AI")
        self.resize(1380, 880)
        self.setMinimumSize(1024, 700)
        self.setStyleSheet(DARK_FUTURISTIC_STYLE)

        # Settings & Core Managers
        self.settings = SettingsManager()
        self.undo_redo = UndoRedoManager()
        
        loaded_key = self.settings.get("gemini_api_key") or self.settings.get("openai_api_key", "")
        loaded_model = self.settings.get("gemini_model", "gemini-2.5-flash")
        self.ai_service = AIService(
            api_key=loaded_key,
            model=loaded_model
        )

        # Vision Asynchronous Worker Thread
        res = self.settings.get("camera_resolution", [640, 480])
        mode_str = self.settings.get("gesture_mode", GestureMode.POINTING.value)
        gesture_mode = GestureMode.PINCH if "Pinch" in mode_str else GestureMode.POINTING

        self.vision_worker = VisionWorkerThread(
            camera_index=self.settings.get("camera_index", 0),
            width=res[0],
            height=res[1],
            flip_h=self.settings.get("camera_flip_h", True),
            draw_skeleton=self.settings.get("draw_skeleton", True),
            gesture_mode=gesture_mode,
            smoothing_factor=float(self.settings.get("smoothing_factor", 0.6)),
            parent=self
        )

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        self.stacked_widget = QStackedWidget(self)
        self.setCentralWidget(self.stacked_widget)

        # Page 1: Startup Screen
        self.startup_screen = StartupScreen()
        self.stacked_widget.addWidget(self.startup_screen)

        # Page 2: Main Workspace Widget
        self.workspace_widget = QWidget()
        self._build_workspace_ui(self.workspace_widget)
        self.stacked_widget.addWidget(self.workspace_widget)

        # Start on Startup Screen
        self.stacked_widget.setCurrentWidget(self.startup_screen)

    def _build_workspace_ui(self, container: QWidget) -> None:
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # 1. Top Navigation & Status Bar (Dimensional Elevated Card)
        header_frame = QFrame()
        header_frame.setObjectName("glass-card")
        header_frame.setStyleSheet("""
            QFrame#glass-card {
                background-color: rgba(15, 23, 42, 0.9);
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 16px;
                padding: 6px 14px;
            }
        """)

        # 3D shadow effect on header
        shadow_header = QGraphicsDropShadowEffect(self)
        shadow_header.setBlurRadius(20)
        shadow_header.setColor(QColor(0, 240, 255, 30))
        shadow_header.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow_header)

        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 6, 12, 6)

        # Title / Brand
        lbl_brand = QLabel("LIVE AIR WRITING AI")
        lbl_brand.setStyleSheet("font-size: 18px; font-weight: 900; color: #00F0FF; letter-spacing: 1.5px;")

        # Status Indicators
        status_box = QHBoxLayout()
        status_box.setSpacing(16)

        self.lbl_cam_status = QLabel("Camera: Ready")
        self.lbl_cam_status.setStyleSheet("color: #10B981; font-weight: 600; font-size: 12px;")

        self.lbl_hand_count = QLabel("Hands: 0")
        self.lbl_hand_count.setStyleSheet("color: #64748B; font-weight: 700; font-size: 12px;")

        self.lbl_fingertip_pos = QLabel("Index: (0, 0)")
        self.lbl_fingertip_pos.setStyleSheet("color: #94A3B8; font-size: 12px;")

        self.lbl_fps = QLabel("FPS: 0.0")
        self.lbl_fps.setStyleSheet("color: #38BDF8; font-weight: 700; font-size: 12px;")

        self.lbl_gesture_status = QLabel("GESTURE: NO HAND")
        self.lbl_gesture_status.setProperty("class", "header-badge")

        status_box.addWidget(self.lbl_cam_status)
        status_box.addWidget(self.lbl_hand_count)
        status_box.addWidget(self.lbl_fingertip_pos)
        status_box.addWidget(self.lbl_fps)
        status_box.addWidget(self.lbl_gesture_status)

        # Top Right Action Buttons
        actions_box = QHBoxLayout()
        actions_box.setSpacing(10)

        btn_export = QPushButton("💾 Export PNG")
        btn_export.setToolTip("Export air drawing as high-res PNG")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self._on_export_clicked)

        btn_settings = QPushButton("⚙️ Settings")
        btn_settings.setToolTip("Configure camera and gesture sensitivity")
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.clicked.connect(self._open_settings_dialog)

        btn_home = QPushButton("🏠 Startup")
        btn_home.setToolTip("Return to main startup screen")
        btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_home.clicked.connect(self._show_startup)

        actions_box.addWidget(btn_export)
        actions_box.addWidget(btn_settings)
        actions_box.addWidget(btn_home)

        header_layout.addWidget(lbl_brand)
        header_layout.addSpacing(20)
        header_layout.addLayout(status_box)
        header_layout.addStretch()
        header_layout.addLayout(actions_box)

        # 2. Central Balanced Workspace Area
        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)

        # Left / Central Camera & Air Writing Workspace
        canvas_container = QVBoxLayout()
        canvas_container.setSpacing(12)

        self.canvas = AirWritingCanvas(self.undo_redo, self)
        
        # 3D shadow on canvas frame
        shadow_canvas = QGraphicsDropShadowEffect(self)
        shadow_canvas.setBlurRadius(25)
        shadow_canvas.setColor(QColor(0, 0, 0, 100))
        shadow_canvas.setOffset(0, 8)
        self.canvas.setGraphicsEffect(shadow_canvas)

        # Bottom Floating Drawing Toolbar
        self.toolbar = DrawingToolbar(self.undo_redo, self)

        canvas_container.addWidget(self.canvas, stretch=1)
        canvas_container.addWidget(self.toolbar, alignment=Qt.AlignmentFlag.AlignCenter)

        # Right Side AI Assist Panel
        self.ai_panel = AIAssistPanel(self.ai_service, self.canvas, self)
        self.ai_panel.setFixedWidth(310)

        content_layout.addLayout(canvas_container, stretch=1)
        content_layout.addWidget(self.ai_panel)

        main_layout.addWidget(header_frame)
        main_layout.addLayout(content_layout, stretch=1)

    def _connect_signals(self) -> None:
        # Startup screen navigation
        self.startup_screen.start_requested.connect(self._show_workspace)
        self.startup_screen.settings_requested.connect(self._open_settings_dialog)
        self.startup_screen.exit_requested.connect(self.close)

        # Vision Worker Background Signals
        self.vision_worker.frame_processed.connect(self._on_frame_processed)
        self.vision_worker.status_changed.connect(self._on_camera_status_changed)
        self.vision_worker.error_occurred.connect(self._on_camera_error)

        # Toolbar Controls
        self.toolbar.color_changed.connect(self._on_color_changed)
        self.toolbar.brush_size_changed.connect(self._on_brush_size_changed)
        self.toolbar.eraser_toggled.connect(self._on_eraser_toggled)
        self.toolbar.canvas_mode_changed.connect(self.canvas.set_canvas_mode)
        self.toolbar.clear_requested.connect(self.undo_redo.clear)
        self.toolbar.undo_requested.connect(self.undo_redo.undo)
        self.toolbar.redo_requested.connect(self.undo_redo.redo)

    @Slot()
    def _show_workspace(self) -> None:
        self.stacked_widget.setCurrentWidget(self.workspace_widget)
        if not self.vision_worker.isRunning():
            self.vision_worker.start()

    @Slot()
    def _show_startup(self) -> None:
        if self.vision_worker.isRunning():
            self.vision_worker.stop()
        self.stacked_widget.setCurrentWidget(self.startup_screen)

    @Slot(dict)
    def _on_frame_processed(self, data: dict) -> None:
        """
        Runs on Qt GUI Main Thread - receives pre-processed background worker data.
        Performs strict state management for active vector strokes.
        """
        frame = data.get("frame")
        hand_data = data.get("hand_data")
        hand_count = data.get("hand_count", 0)
        gesture = data.get("gesture")
        is_drawing = data.get("is_drawing", False)
        new_points = data.get("new_points", [])
        finished_stroke = data.get("finished_stroke")
        vision_fps = data.get("vision_fps", 0.0)

        # 1. Update Canvas Background & Diagnostic HUD
        if frame is not None:
            self.canvas.set_camera_frame(frame)
        self.canvas.set_diagnostic_info(data)

        # 2. Sync Eraser Gesture state BEFORE stroke processing
        if gesture == GestureType.ERASER:
            self.canvas.is_eraser_active = True
        elif not self.toolbar.is_eraser:
            self.canvas.is_eraser_active = False

        # 3. STRICT STATE RULE 1: Handle finished stroke from air engine
        if finished_stroke is not None:
            if self.canvas.active_stroke is not None:
                self.canvas.commit_active_stroke()

        # 4. STRICT STATE RULE 2: Process live stroke points
        if is_drawing and new_points:
            for pt in new_points:
                if self.canvas.active_stroke is None:
                    self.canvas.start_active_stroke(pt)
                else:
                    self.canvas.update_active_stroke(pt)
        elif not is_drawing:
            # IMMEDIATELY TERMINATE STROKE if hand disappears or gesture changes
            if self.canvas.active_stroke is not None:
                self.canvas.commit_active_stroke()

        # 4. Update Top Header Status Readouts
        self.lbl_fps.setText(f"FPS: {vision_fps:.1f}")
        self.lbl_hand_count.setText(f"Hands: {hand_count}")
        if hand_count > 0:
            self.lbl_hand_count.setStyleSheet("color: #10B981; font-weight: 700; font-size: 12px;")
        else:
            self.lbl_hand_count.setStyleSheet("color: #64748B; font-weight: 700; font-size: 12px;")

        if hand_data and "index_tip" in hand_data:
            ix, iy = hand_data["index_tip"]
            self.lbl_fingertip_pos.setText(f"Index: ({ix}, {iy})")
        else:
            self.lbl_fingertip_pos.setText("Index: (0, 0)")

        gesture_val = gesture.value if hasattr(gesture, "value") else str(gesture)
        self.lbl_gesture_status.setText(f"GESTURE: {gesture_val}")

    @Slot(str)
    def _on_camera_status_changed(self, status: str) -> None:
        self.lbl_cam_status.setText(f"Camera: {status}")

    @Slot(str)
    def _on_camera_error(self, err_msg: str) -> None:
        QMessageBox.warning(self, "Camera Error", err_msg)

    @Slot(QColor)
    def _on_color_changed(self, color: QColor) -> None:
        self.canvas.current_color = color

    @Slot(int)
    def _on_brush_size_changed(self, size: int) -> None:
        self.canvas.current_brush_width = size

    @Slot(bool)
    def _on_eraser_toggled(self, active: bool) -> None:
        self.canvas.is_eraser_active = active

    def _on_export_clicked(self) -> None:
        out_dir = os.path.join(os.getcwd(), "saved_drawings")
        os.makedirs(out_dir, exist_ok=True)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Air Writing Canvas",
            os.path.join(out_dir, "air_writing.png"),
            "PNG Image (*.png)"
        )
        if file_path:
            saved_path = self.canvas.export_image(file_path=file_path)
            if saved_path:
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Canvas exported successfully to:\n{saved_path}"
                )

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        dialog.settings_saved.connect(self._apply_settings_changes)
        dialog.exec()

    def _apply_settings_changes(self) -> None:
        # Update AI Service
        key_val = self.settings.get("gemini_api_key") or self.settings.get("openai_api_key", "")
        model_val = self.settings.get("gemini_model", "gemini-2.5-flash")
        self.ai_service.set_api_key(key_val)
        self.ai_service.model = model_val
        self.ai_panel.update_api_status()

        # Update Vision Worker settings
        self.vision_worker.set_draw_skeleton(self.settings.get("draw_skeleton", True))

        mode_str = self.settings.get("gesture_mode", GestureMode.POINTING.value)
        gesture_mode = GestureMode.PINCH if "Pinch" in mode_str else GestureMode.POINTING
        self.vision_worker.set_gesture_mode(gesture_mode)

        self.vision_worker.set_smoothing(float(self.settings.get("smoothing_factor", 0.6)))

        res = self.settings.get("camera_resolution", [640, 480])
        self.vision_worker.set_camera_index(self.settings.get("camera_index", 0))
        self.vision_worker.set_resolution(res[0], res[1])
        self.vision_worker.set_flip(self.settings.get("camera_flip_h", True))

    def closeEvent(self, event) -> None:
        if self.vision_worker.isRunning():
            self.vision_worker.stop()
        event.accept()
