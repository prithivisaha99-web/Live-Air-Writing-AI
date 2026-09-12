"""Floating Tool Control Dock for Colors, Brush Size, Eraser, Undo/Redo."""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QSlider, QLabel, QColorDialog, QFrame, QComboBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QPainter, QBrush, QPen

from app.drawing_tools import PRESET_COLORS, UndoRedoManager
from app.canvas import CanvasMode


class ColorButton(QPushButton):
    """Circular dimensional color preset button with selection indicator."""

    def __init__(self, color_hex: str, tooltip_name: str, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setToolTip(tooltip_name)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_active(False)

    def set_active(self, active: bool) -> None:
        border = "2px solid #00F0FF" if active else "1px solid rgba(255, 255, 255, 0.2)"
        shadow = "0 0 10px #00F0FF" if active else "none"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color_hex};
                border: {border};
                border-radius: 16px;
            }}
            QPushButton:hover {{
                border: 2px solid #FFFFFF;
            }}
        """)


class BrushPreviewWidget(QWidget):
    """Live visual circle indicator of brush thickness & color."""

    def __init__(self, color: QColor, size: int, parent=None):
        super().__init__(parent)
        self.color = color
        self.brush_size = size
        self.setFixedSize(40, 40)

    def set_properties(self, color: QColor, size: int) -> None:
        self.color = color
        self.brush_size = size
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        
        radius = max(2, min(18, self.brush_size / 2.0))
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.end()


class DrawingToolbar(QFrame):
    """Floating Tool Dock containing brush controls."""

    color_changed = Signal(QColor)
    brush_size_changed = Signal(int)
    eraser_toggled = Signal(bool)
    canvas_mode_changed = Signal(CanvasMode)
    clear_requested = Signal()
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, undo_redo_manager: UndoRedoManager, parent=None):
        super().__init__(parent)
        self.undo_redo = undo_redo_manager
        self.color_buttons: list[ColorButton] = []
        self.current_color = QColor("#00F0FF")
        self.is_eraser = False

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        self.setObjectName("glass-card")
        self.setStyleSheet("""
            QFrame#glass-card {
                background-color: rgba(15, 23, 42, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                padding: 6px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(18)

        # 1. Colors Section
        colors_box = QHBoxLayout()
        colors_box.setSpacing(8)

        for item in PRESET_COLORS:
            btn = ColorButton(item["hex"], item["name"])
            btn.clicked.connect(lambda _, c=item["hex"], b=btn: self._select_color(QColor(c), b))
            self.color_buttons.append(btn)
            colors_box.addWidget(btn)

        # Set first color active by default
        self.color_buttons[0].set_active(True)

        # Custom Color Picker Button
        self.btn_custom_color = QPushButton("🎨")
        self.btn_custom_color.setToolTip("Custom Color Picker")
        self.btn_custom_color.setFixedSize(32, 32)
        self.btn_custom_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_custom_color.clicked.connect(self._open_color_picker)
        colors_box.addWidget(self.btn_custom_color)

        # 2. Brush Size Section
        brush_box = QHBoxLayout()
        brush_box.setSpacing(10)

        lbl_brush = QLabel("Size:")
        lbl_brush.setStyleSheet("font-weight: 600; color: #94A3B8;")

        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(2, 40)
        self.slider_size.setValue(8)
        self.slider_size.setFixedWidth(110)
        self.slider_size.valueChanged.connect(self._on_size_changed)

        self.lbl_size_num = QLabel("8px")
        self.lbl_size_num.setFixedWidth(32)
        self.lbl_size_num.setStyleSheet("font-weight: 600; color: #00F0FF;")

        self.brush_preview = BrushPreviewWidget(self.current_color, 8)

        brush_box.addWidget(lbl_brush)
        brush_box.addWidget(self.slider_size)
        brush_box.addWidget(self.lbl_size_num)
        brush_box.addWidget(self.brush_preview)

        # 3. Mode Toggles (Eraser, Canvas View)
        mode_box = QHBoxLayout()
        mode_box.setSpacing(10)

        self.btn_eraser = QPushButton("🧹 Eraser")
        self.btn_eraser.setCheckable(True)
        self.btn_eraser.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eraser.toggled.connect(self._on_eraser_toggled)

        self.combo_canvas_mode = QComboBox()
        self.combo_canvas_mode.addItems([mode.value for mode in CanvasMode])
        self.combo_canvas_mode.currentTextChanged.connect(self._on_canvas_mode_changed)

        mode_box.addWidget(self.btn_eraser)
        mode_box.addWidget(self.combo_canvas_mode)

        # 4. Action Buttons (Undo, Redo, Clear)
        actions_box = QHBoxLayout()
        actions_box.setSpacing(8)

        self.btn_undo = QPushButton("↩️ Undo")
        self.btn_undo.setToolTip("Undo last stroke")
        self.btn_undo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.undo_requested.emit)

        self.btn_redo = QPushButton("↪️ Redo")
        self.btn_redo.setToolTip("Redo un-done stroke")
        self.btn_redo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(self.redo_requested.emit)

        self.btn_clear = QPushButton("🗑️ Clear")
        self.btn_clear.setToolTip("Clear all strokes")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setStyleSheet("QPushButton:hover { border: 1px solid #EF4444; color: #EF4444; }")
        self.btn_clear.clicked.connect(self.clear_requested.emit)

        actions_box.addWidget(self.btn_undo)
        actions_box.addWidget(self.btn_redo)
        actions_box.addWidget(self.btn_clear)

        # Separators
        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.VLine); sep1.setStyleSheet("color: rgba(255,255,255,0.1);")
        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.VLine); sep2.setStyleSheet("color: rgba(255,255,255,0.1);")
        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.VLine); sep3.setStyleSheet("color: rgba(255,255,255,0.1);")

        # Assembly
        layout.addLayout(colors_box)
        layout.addWidget(sep1)
        layout.addLayout(brush_box)
        layout.addWidget(sep2)
        layout.addLayout(mode_box)
        layout.addWidget(sep3)
        layout.addLayout(actions_box)

    def _connect_signals(self) -> None:
        self.undo_redo.can_undo_changed.connect(self.btn_undo.setEnabled)
        self.undo_redo.can_redo_changed.connect(self.btn_redo.setEnabled)

    def _select_color(self, color: QColor, target_btn: ColorButton | None = None) -> None:
        self.current_color = color
        for btn in self.color_buttons:
            btn.set_active(btn == target_btn)
        
        if self.is_eraser:
            self.btn_eraser.setChecked(False)

        self.brush_preview.set_properties(color, self.slider_size.value())
        self.color_changed.emit(color)

    def _open_color_picker(self) -> None:
        chosen = QColorDialog.getColor(self.current_color, self, "Select Custom Brush Color")
        if chosen.isValid():
            self._select_color(chosen, None)

    def _on_size_changed(self, val: int) -> None:
        self.lbl_size_num.setText(f"{val}px")
        self.brush_preview.set_properties(self.current_color, val)
        self.brush_size_changed.emit(val)

    def _on_eraser_toggled(self, checked: bool) -> None:
        self.is_eraser = checked
        if checked:
            self.btn_eraser.setStyleSheet("QPushButton { border: 2px solid #A855F7; color: #A855F7; }")
        else:
            self.btn_eraser.setStyleSheet("")
        self.eraser_toggled.emit(checked)

    def _on_canvas_mode_changed(self, text: str) -> None:
        for mode in CanvasMode:
            if mode.value == text:
                self.canvas_mode_changed.emit(mode)
                break
