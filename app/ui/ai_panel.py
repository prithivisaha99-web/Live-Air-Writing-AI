"""AI Assist Dock Panel with Async OpenAI Processing Workers."""
import os
import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QApplication, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QClipboard

from app.ai_service import AIService
from app.canvas import AirWritingCanvas

logger = logging.getLogger(__name__)


class AIWorkerThread(QThread):
    """Background worker for OpenAI API requests to keep UI responsive."""

    result_ready = Signal(dict)

    def __init__(self, ai_service: AIService, task_type: str, payload: str, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.task_type = task_type
        self.payload = payload

    def run(self) -> None:
        if self.task_type == "recognize":
            res = self.ai_service.recognize_handwriting(self.payload)
        elif self.task_type == "clean":
            res = self.ai_service.clean_text(self.payload)
        elif self.task_type == "summarize":
            res = self.ai_service.summarize_text(self.payload)
        else:
            res = {"success": False, "error": "Unknown AI Task"}
            
        self.result_ready.emit(res)


class AIAssistPanel(QFrame):
    """Dimensional Card Widget for AI-Powered Handwriting Operations."""

    def __init__(self, ai_service: AIService, canvas: AirWritingCanvas, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.canvas = canvas
        self.worker: AIWorkerThread | None = None

        self._init_ui()
        self.update_api_status()

    def _init_ui(self) -> None:
        self.setObjectName("glass-card")
        self.setStyleSheet("""
            QFrame#glass-card {
                background-color: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 20px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header Title & Status Badge
        header_layout = QHBoxLayout()
        lbl_title = QLabel("🤖 AI ASSIST")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #00F0FF;")

        self.lbl_api_status = QLabel("Checking Key...")
        self.lbl_api_status.setProperty("class", "header-badge")

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_api_status)

        # Progress Bar (Hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate spinner
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                height: 4px;
                background-color: rgba(255,255,255,0.05);
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F0FF, stop:1 #A855F7);
            }
        """)
        self.progress_bar.setVisible(False)

        # AI Action Buttons
        btn_grid = QVBoxLayout()
        btn_grid.setSpacing(10)

        self.btn_recognize = QPushButton("👁️ Recognize Writing")
        self.btn_recognize.setToolTip("Use OpenAI Vision to transcribe air writing canvas")
        self.btn_recognize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_recognize.clicked.connect(self._on_recognize_clicked)

        self.btn_clean = QPushButton("✍️ Clean Fix Text")
        self.btn_clean.setToolTip("Correct spelling, typos, and formatting")
        self.btn_clean.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clean.clicked.connect(self._on_clean_clicked)

        self.btn_summarize = QPushButton("📝 Summarize Notes")
        self.btn_summarize.setToolTip("Summarize recognized text into key points")
        self.btn_summarize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_summarize.clicked.connect(self._on_summarize_clicked)

        self.btn_copy = QPushButton("📋 Copy Text")
        self.btn_copy.setToolTip("Copy result to system clipboard")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self._on_copy_clicked)

        btn_grid.addWidget(self.btn_recognize)
        btn_grid.addWidget(self.btn_clean)
        btn_grid.addWidget(self.btn_summarize)
        btn_grid.addWidget(self.btn_copy)

        # Output Result Text Edit
        self.txt_output = QTextEdit()
        self.txt_output.setPlaceholderText("Transcribed or processed AI text will appear here...")
        self.txt_output.setMinimumHeight(140)

        # Assembly
        layout.addLayout(header_layout)
        layout.addWidget(self.progress_bar)
        layout.addLayout(btn_grid)
        layout.addWidget(self.txt_output)

    def update_api_status(self) -> None:
        if self.ai_service.is_configured():
            self.lbl_api_status.setText("API Ready")
            self.lbl_api_status.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.15);
                border: 1px solid #10B981;
                color: #10B981;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            """)
        else:
            self.lbl_api_status.setText("API Key Missing")
            self.lbl_api_status.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.15);
                border: 1px solid #EF4444;
                color: #EF4444;
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            """)

    def _set_loading(self, loading: bool, active_task: str | None = None) -> None:
        self.progress_bar.setVisible(loading)
        self.btn_recognize.setEnabled(not loading)
        self.btn_clean.setEnabled(not loading)
        self.btn_summarize.setEnabled(not loading)

        if loading:
            if active_task == "recognize":
                self.btn_recognize.setText("Processing...")
            elif active_task == "clean":
                self.btn_clean.setText("Processing...")
            elif active_task == "summarize":
                self.btn_summarize.setText("Processing...")
        else:
            self.btn_recognize.setText("👁️ Recognize Writing")
            self.btn_clean.setText("✍️ Clean Fix Text")
            self.btn_summarize.setText("📝 Summarize Notes")

    def _on_recognize_clicked(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        if not self.ai_service.is_configured():
            self.txt_output.setText("❌ OpenAI API Key is missing.\n\nPlease configure your API key in Settings or in the local .env file.")
            return

        # Check if canvas has any drawn stroke points
        if len(self.canvas.undo_redo.history) == 0 and self.canvas.active_stroke is None:
            self.txt_output.setText("⚠️ Canvas is empty. Create some air writing first before recognizing.")
            return

        # Export current canvas image to temporary path
        temp_img_path = self.canvas.export_image(transparent=False)
        if not temp_img_path or not os.path.exists(temp_img_path):
            self.txt_output.setText("⚠️ Failed to capture canvas image for recognition.")
            return

        self._set_loading(True, active_task="recognize")
        self.txt_output.setText("Analyzing air handwriting with OpenAI Vision...")

        self.worker = AIWorkerThread(self.ai_service, "recognize", temp_img_path, self)
        self.worker.result_ready.connect(self._handle_recognize_result)
        self.worker.start()

    def _handle_recognize_result(self, res: dict) -> None:
        self._set_loading(False)
        if res.get("success"):
            text = res.get("text", "")
            self.txt_output.setText(text if text else "No text could be recognized.")
        else:
            self.txt_output.setText(f"❌ {res.get('error', 'Error during recognition')}")

    def _on_clean_clicked(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        if not self.ai_service.is_configured():
            self.txt_output.setText("❌ OpenAI API Key is missing.\n\nPlease configure your API key in Settings or in the local .env file.")
            return

        current_text = self.txt_output.toPlainText()
        if not current_text.strip() or current_text.startswith("❌") or current_text.startswith("⚠️"):
            self.txt_output.setText("⚠️ Please recognize writing first before cleaning text.")
            return

        self._set_loading(True, active_task="clean")
        self.worker = AIWorkerThread(self.ai_service, "clean", current_text, self)
        self.worker.result_ready.connect(self._handle_clean_result)
        self.worker.start()

    def _handle_clean_result(self, res: dict) -> None:
        self._set_loading(False)
        if res.get("success"):
            self.txt_output.setText(res.get("text", ""))
        else:
            self.txt_output.setText(f"❌ {res.get('error', 'Error cleaning text')}")

    def _on_summarize_clicked(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        if not self.ai_service.is_configured():
            self.txt_output.setText("❌ OpenAI API Key is missing.\n\nPlease configure your API key in Settings or in the local .env file.")
            return

        current_text = self.txt_output.toPlainText()
        if not current_text.strip() or current_text.startswith("❌") or current_text.startswith("⚠️"):
            self.txt_output.setText("⚠️ Please recognize writing first before summarizing.")
            return

        self._set_loading(True, active_task="summarize")
        self.worker = AIWorkerThread(self.ai_service, "summarize", current_text, self)
        self.worker.result_ready.connect(self._handle_summarize_result)
        self.worker.start()

    def _handle_summarize_result(self, res: dict) -> None:
        self._set_loading(False)
        if res.get("success"):
            self.txt_output.setText(res.get("summary", ""))
        else:
            self.txt_output.setText(f"❌ {res.get('error', 'Error summarizing text')}")

    def _on_copy_clicked(self) -> None:
        text = self.txt_output.toPlainText()
        if not text.strip() or text.startswith("❌") or text.startswith("⚠️"):
            self.btn_copy.setText("⚠️ No Text to Copy")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copy Text"))
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.btn_copy.setText("✅ Copied!")
        QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copy Text"))
