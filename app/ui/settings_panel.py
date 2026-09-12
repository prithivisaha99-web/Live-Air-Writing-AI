"""Settings Configuration Dialog for Camera, Hand Tracking, Gesture, and AI."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox, QSlider,
    QLineEdit, QPushButton, QGroupBox, QFormLayout, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from app.settings import SettingsManager
from app.camera import list_available_cameras
from app.gesture_detection import GestureMode


class SettingsDialog(QDialog):
    """Professional Glassmorphic Settings Dialog."""

    settings_saved = Signal()

    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Live Air Writing AI - Settings")
        self.setMinimumWidth(520)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #0B0F17;
                color: #F8FAFC;
            }
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: 700;
                color: #00F0FF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
            }
        """)

        self._init_ui()
        self._load_current_values()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Header Title
        lbl_header = QLabel("⚙️ Application Preferences")
        lbl_header.setStyleSheet("font-size: 20px; font-weight: 800; color: #00F0FF;")
        layout.addWidget(lbl_header)

        # Group 1: Camera Setup
        grp_camera = QGroupBox("Camera Configuration")
        form_camera = QFormLayout(grp_camera)
        form_camera.setSpacing(12)

        self.combo_camera = QComboBox()
        available_cams = list_available_cameras()
        for cam in available_cams:
            self.combo_camera.addItem(cam["name"], cam["index"])

        self.combo_res = QComboBox()
        self.combo_res.addItem("1280 x 720 (HD)", [1280, 720])
        self.combo_res.addItem("1920 x 1080 (Full HD)", [1920, 1080])
        self.combo_res.addItem("640 x 480 (SD)", [640, 480])

        self.chk_flip = QCheckBox("Mirror Camera Feed Horizontally")

        form_camera.addRow("Select Webcam:", self.combo_camera)
        form_camera.addRow("Resolution:", self.combo_res)
        form_camera.addRow("", self.chk_flip)

        # Group 2: Hand Tracking & Gesture Engine
        grp_hand = QGroupBox("Hand Tracking & Gesture Controls")
        form_hand = QFormLayout(grp_hand)
        form_hand.setSpacing(12)

        self.chk_skeleton = QCheckBox("Render Futuristic Hand Skeleton Overlay")

        self.combo_gesture_mode = QComboBox()
        for mode in GestureMode:
            self.combo_gesture_mode.addItem(mode.value, mode)

        self.slider_smoothing = QSlider(Qt.Orientation.Horizontal)
        self.slider_smoothing.setRange(1, 9) # 0.1 to 0.9
        self.lbl_smoothing_val = QLabel("0.4")

        slider_box = QHBoxLayout()
        slider_box.addWidget(self.slider_smoothing)
        slider_box.addWidget(self.lbl_smoothing_val)
        self.slider_smoothing.valueChanged.connect(lambda v: self.lbl_smoothing_val.setText(f"{v / 10.0:.1f}"))

        form_hand.addRow("", self.chk_skeleton)
        form_hand.addRow("Gesture Trigger Mode:", self.combo_gesture_mode)
        form_hand.addRow("Line Smoothing Level:", slider_box)

        # Group 3: Gemini AI Features
        grp_ai = QGroupBox("Google Gemini AI Integration (Free Tier Available)")
        form_ai = QFormLayout(grp_ai)
        form_ai.setSpacing(12)

        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText("AIzaSy...")

        self.combo_ai_model = QComboBox()
        self.combo_ai_model.addItem("gemini-2.5-flash (Recommended & Free Tier)", "gemini-2.5-flash")
        self.combo_ai_model.addItem("gemini-2.0-flash (Fast)", "gemini-2.0-flash")

        form_ai.addRow("Gemini API Key:", self.txt_api_key)
        form_ai.addRow("Vision & Text Model:", self.combo_ai_model)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        btn_reset = QPushButton("Reset Defaults")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self._on_reset)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save & Apply")
        btn_save.setProperty("class", "btn-primary")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._on_save)

        btn_box.addWidget(btn_reset)
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)

        layout.addWidget(grp_camera)
        layout.addWidget(grp_hand)
        layout.addWidget(grp_ai)
        layout.addSpacing(10)
        layout.addLayout(btn_box)

    def _load_current_values(self) -> None:
        # Camera
        cam_idx = self.settings.get("camera_index", 0)
        index = self.combo_camera.findData(cam_idx)
        if index >= 0:
            self.combo_camera.setCurrentIndex(index)

        res = self.settings.get("camera_resolution", [1280, 720])
        for i in range(self.combo_res.count()):
            if self.combo_res.itemData(i) == res:
                self.combo_res.setCurrentIndex(i)
                break

        self.chk_flip.setChecked(self.settings.get("camera_flip_h", True))

        # Hand tracking
        self.chk_skeleton.setChecked(self.settings.get("draw_skeleton", True))
        
        mode_val = self.settings.get("gesture_mode", GestureMode.POINTING.value)
        for i in range(self.combo_gesture_mode.count()):
            if self.combo_gesture_mode.itemText(i) == mode_val:
                self.combo_gesture_mode.setCurrentIndex(i)
                break

        alpha = float(self.settings.get("smoothing_factor", 0.4))
        int_val = max(1, min(9, int(alpha * 10)))
        self.slider_smoothing.setValue(int_val)
        self.lbl_smoothing_val.setText(f"{alpha:.1f}")

        # AI
        loaded_key = self.settings.get("gemini_api_key") or self.settings.get("openai_api_key", "")
        self.txt_api_key.setText(loaded_key if isinstance(loaded_key, str) else "")
        model_name = self.settings.get("gemini_model", "gemini-2.5-flash")
        for i in range(self.combo_ai_model.count()):
            if self.combo_ai_model.itemData(i) == model_name:
                self.combo_ai_model.setCurrentIndex(i)
                break

    def _on_save(self) -> None:
        self.settings.set("camera_index", self.combo_camera.currentData())
        self.settings.set("camera_resolution", self.combo_res.currentData())
        self.settings.set("camera_flip_h", self.chk_flip.isChecked())
        self.settings.set("draw_skeleton", self.chk_skeleton.isChecked())
        self.settings.set("gesture_mode", self.combo_gesture_mode.currentText())
        self.settings.set("smoothing_factor", self.slider_smoothing.value() / 10.0)
        
        key_val = self.txt_api_key.text().strip()
        self.settings.set("gemini_api_key", key_val)
        self.settings.set("gemini_model", self.combo_ai_model.currentData())

        self.settings_saved.emit()
        self.accept()

    def _on_reset(self) -> None:
        ret = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all preferences to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret == QMessageBox.StandardButton.Yes:
            self.settings.reset_defaults()
            self._load_current_values()
