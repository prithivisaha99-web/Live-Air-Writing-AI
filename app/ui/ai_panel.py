"""AI Assist Dock Panel with Async Gemini Processing Workers and AI Writing Chat."""
import os
import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QLineEdit, QApplication, QProgressBar, QGridLayout
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QClipboard

from app.ai_service import AIService
from app.canvas import AirWritingCanvas

logger = logging.getLogger(__name__)


class AIWorkerThread(QThread):
    """Background worker for Gemini API requests to keep UI responsive."""

    result_ready = Signal(dict)

    def __init__(self, ai_service: AIService, task_type: str, payload: dict | str, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.task_type = task_type
        self.payload = payload

    def run(self) -> None:
        if self.task_type == "recognize":
            res = self.ai_service.recognize_handwriting(self.payload)
        elif self.task_type == "analyze_scene":
            res = self.ai_service.analyze_scene(self.payload)
        elif self.task_type == "clean":
            res = self.ai_service.clean_text(self.payload)
        elif self.task_type == "summarize":
            res = self.ai_service.summarize_text(self.payload)
        elif self.task_type == "chat":
            if isinstance(self.payload, dict):
                w = self.payload.get("writing", "")
                d = self.payload.get("description", "")
                q = self.payload.get("question", "")
                h = self.payload.get("history", [])
                res = self.ai_service.chat_writing(w, d, q, h)
            else:
                res = {"success": False, "error": "Invalid chat payload"}
        else:
            res = {"success": False, "error": "Unknown AI Task"}
            
        self.result_ready.emit(res)


class AIAssistPanel(QFrame):
    """Dimensional Card Widget for AI Writing Chat & Handwriting Operations."""

    def __init__(self, ai_service: AIService, canvas: AirWritingCanvas, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.canvas = canvas
        self.worker: AIWorkerThread | None = None

        self.current_writing: str = ""
        self.current_description: str = ""
        self.chat_history: list[dict] = []

        self._init_ui()
        self.update_api_status()
        self.canvas.undo_redo.history_changed.connect(self._on_canvas_history_changed)
        logger.info("[AIChatUI] panel_created")

    def _init_ui(self) -> None:
        self.setObjectName("glass-card")
        self.setStyleSheet("""
            QFrame#glass-card {
                background-color: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 20px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header Title & Status Badge
        header_layout = QHBoxLayout()
        lbl_title = QLabel("🤖 AI ASSIST")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #00F0FF;")

        self.lbl_api_status = QLabel("Checking Key...")
        self.lbl_api_status.setProperty("class", "header-badge")

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_api_status)

        # Progress Bar (Hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
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

        # 1. Action Buttons Grid (5 Buttons in compact 2-row layout)
        btn_grid = QGridLayout()
        btn_grid.setSpacing(4)

        self.btn_recognize = QPushButton("👁️ Recognize Writing")
        self.btn_recognize.setToolTip("Recognize air writing and set writing context")
        self.btn_recognize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_recognize.clicked.connect(self._on_recognize_clicked)

        self.btn_analyze_scene = QPushButton("🔍 Analyze Scene")
        self.btn_analyze_scene.setToolTip("Analyze camera scene and objects")
        self.btn_analyze_scene.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze_scene.clicked.connect(self._on_analyze_scene_clicked)

        self.btn_clean = QPushButton("✍️ Clean Fix Text")
        self.btn_clean.setToolTip("Fix grammar and spelling")
        self.btn_clean.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clean.clicked.connect(self._on_clean_clicked)

        self.btn_summarize = QPushButton("📝 Summarize Notes")
        self.btn_summarize.setToolTip("Summarize notes into bullet points")
        self.btn_summarize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_summarize.clicked.connect(self._on_summarize_clicked)

        self.btn_copy = QPushButton("📋 Copy Text")
        self.btn_copy.setToolTip("Copy recognized text to clipboard")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self._on_copy_clicked)

        all_btns = (self.btn_recognize, self.btn_analyze_scene, self.btn_clean, self.btn_summarize, self.btn_copy)
        for btn in all_btns:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(30, 41, 59, 0.8);
                    border: 1px solid rgba(0, 240, 255, 0.25);
                    border-radius: 8px;
                    color: #FFFFFF;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 5px 4px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 240, 255, 0.2);
                    border: 1px solid #00F0FF;
                }
                QPushButton:disabled {
                    background-color: rgba(30, 41, 59, 0.3);
                    color: #64748B;
                }
            """)

        btn_grid.addWidget(self.btn_recognize, 0, 0)
        btn_grid.addWidget(self.btn_analyze_scene, 0, 1)
        btn_grid.addWidget(self.btn_clean, 1, 0)
        btn_grid.addWidget(self.btn_summarize, 1, 1)
        btn_grid.addWidget(self.btn_copy, 2, 0, 1, 2)

        # 2. Active Writing Analysis Card
        context_card = QFrame()
        context_card.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 41, 59, 0.7);
                border: 1px solid rgba(0, 240, 255, 0.25);
                border-radius: 12px;
                padding: 6px;
            }
        """)
        ctx_layout = QVBoxLayout(context_card)
        ctx_layout.setContentsMargins(8, 6, 8, 6)
        ctx_layout.setSpacing(4)

        lbl_ctx_title = QLabel("WRITING CONTEXT")
        lbl_ctx_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #38BDF8; letter-spacing: 0.5px;")

        self.lbl_context_writing = QLabel("Writing: (No text recognized yet)")
        self.lbl_context_writing.setWordWrap(True)
        self.lbl_context_writing.setStyleSheet("font-size: 11px; font-weight: 700; color: #FFFFFF;")

        self.lbl_context_desc = QLabel("Description: Air-write and click 'Recognize Writing' to set context")
        self.lbl_context_desc.setWordWrap(True)
        self.lbl_context_desc.setStyleSheet("font-size: 10px; color: #94A3B8;")

        ctx_layout.addWidget(lbl_ctx_title)
        ctx_layout.addWidget(self.lbl_context_writing)
        ctx_layout.addWidget(self.lbl_context_desc)
        logger.info("[AIChatUI] context_card_created")

        # 3. Chat Messages Conversation Display
        self.txt_chat_display = QTextEdit()
        self.txt_chat_display.setReadOnly(True)
        self.txt_chat_display.setMinimumHeight(140)
        self.txt_chat_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 8px;
                color: #E2E8F0;
                font-size: 11px;
            }
        """)

        # Add initial greeting message
        self._append_chat_message(
            "assistant",
            "👋 Welcome! Air-write on your canvas and click <b>Recognize Writing</b> to start chatting about your writing!"
        )
        logger.info("[AIChatUI] chat_area_created")

        # 4. Chat Message Input Area (Input + Send Button)
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        self.txt_chat_input = QLineEdit()
        self.txt_chat_input.setPlaceholderText("Ask something about your writing...")
        self.txt_chat_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(30, 41, 59, 0.8);
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 10px;
                padding: 6px 10px;
                color: #FFFFFF;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #00F0FF;
            }
        """)
        self.txt_chat_input.returnPressed.connect(self._on_send_chat_clicked)
        logger.info("[AIChatDebug] input_created")
        logger.info("[AIChatDebug] enter_key_connected")

        self.btn_send = QPushButton("💬 Send")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #00F0FF;
                color: #0F172A;
                font-weight: 700;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #38BDF8;
            }
            QPushButton:disabled {
                background-color: #475569;
                color: #94A3B8;
            }
        """)
        self.btn_send.clicked.connect(self._on_send_chat_clicked)
        logger.info("[AIChatDebug] send_button_created")
        logger.info("[AIChatDebug] send_button_connected")

        input_layout.addWidget(self.txt_chat_input, stretch=1)
        input_layout.addWidget(self.btn_send)

        # 5. Gesture Shortcuts Panel Section
        shortcut_frame = QFrame()
        shortcut_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.5);
                border: 1px solid rgba(0, 240, 255, 0.15);
                border-radius: 10px;
                padding: 4px;
            }
        """)
        shortcut_layout = QVBoxLayout(shortcut_frame)
        shortcut_layout.setContentsMargins(8, 4, 8, 4)
        shortcut_layout.setSpacing(2)

        lbl_sc_title = QLabel("✌️ GESTURE SHORTCUTS")
        lbl_sc_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #00F0FF;")

        lbl_sc_items = QLabel("✌️ Undo  |  🤟 Redo  |  👍 Confirm")
        lbl_sc_items.setStyleSheet("font-size: 9px; color: #94A3B8;")

        self.lbl_shortcut_status = QLabel("Shortcut: Ready")
        self.lbl_shortcut_status.setStyleSheet("font-size: 9px; color: #38BDF8; font-weight: 600;")

        shortcut_layout.addWidget(lbl_sc_title)
        shortcut_layout.addWidget(lbl_sc_items)
        shortcut_layout.addWidget(self.lbl_shortcut_status)

        # Assembly
        layout.addLayout(header_layout)
        layout.addWidget(self.progress_bar)
        layout.addLayout(btn_grid)
        layout.addWidget(context_card)
        layout.addWidget(self.txt_chat_display, stretch=1)
        layout.addLayout(input_layout)
        layout.addWidget(shortcut_frame)

    def _on_canvas_history_changed(self) -> None:
        """Reset writing context if canvas is completely cleared."""
        if len(self.canvas.undo_redo.history) == 0 and self.canvas.active_stroke is None:
            logger.info("[AIChatDebug] canvas_cleared -> resetting writing context")
            self.current_writing = ""
            self.current_description = ""
            self.lbl_context_writing.setText("Writing: (Canvas cleared)")
            self.lbl_context_desc.setText("Description: Air-write and click 'Recognize Writing' to set context")

    def _append_chat_message(self, role: str, content: str) -> None:
        """Appends formatted message to chat display."""
        if role in ("user", "assistant"):
            self.chat_history.append({"role": role, "content": content})

        if role == "user":
            html = f'<div style="margin-bottom: 8px; text-align: right;"><span style="background-color: rgba(0,240,255,0.15); color: #00F0FF; padding: 4px 8px; border-radius: 8px; border: 1px solid rgba(0,240,255,0.3);"><b>You:</b> {content}</span></div>'
        else:
            html = f'<div style="margin-bottom: 8px; text-align: left;"><span style="background-color: rgba(168,85,247,0.15); color: #E2E8F0; padding: 4px 8px; border-radius: 8px; border: 1px solid rgba(168,85,247,0.3);"><b style="color: #A855F7;">🤖 AI:</b> {content}</span></div>'

        self.txt_chat_display.append(html)
        sb = self.txt_chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def show_shortcut_status(self, msg: str) -> None:
        if hasattr(self, "lbl_shortcut_status"):
            self.lbl_shortcut_status.setText(f"Status: {msg}")
            self.lbl_shortcut_status.setStyleSheet("font-size: 9px; color: #00F0FF; font-weight: 700;")
            QTimer.singleShot(2000, lambda: self.lbl_shortcut_status.setText("Shortcut: Ready"))
            QTimer.singleShot(2000, lambda: self.lbl_shortcut_status.setStyleSheet("font-size: 9px; color: #38BDF8; font-weight: 600;"))

    def update_api_status(self) -> None:
        is_cfg = self.ai_service.is_configured()
        logger.info(f"[AIConfig] ai_service_configured={is_cfg}")
        if is_cfg:
            self.lbl_api_status.setText("API Ready")
            logger.info("[AIConfig] ui_api_status=READY")
            self.lbl_api_status.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.15);
                border: 1px solid #10B981;
                color: #10B981;
                border-radius: 10px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 600;
            """)
        else:
            self.lbl_api_status.setText("API Key Missing")
            logger.info("[AIConfig] ui_api_status=MISSING")
            self.lbl_api_status.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.15);
                border: 1px solid #EF4444;
                color: #EF4444;
                border-radius: 10px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 600;
            """)

    def _set_loading(self, loading: bool, active_task: str | None = None) -> None:
        self.progress_bar.setVisible(loading)
        self.btn_recognize.setEnabled(not loading)
        self.btn_analyze_scene.setEnabled(not loading)
        self.btn_clean.setEnabled(not loading)
        self.btn_summarize.setEnabled(not loading)
        self.btn_send.setEnabled(not loading)
        self.txt_chat_input.setEnabled(not loading)

        if loading:
            if active_task == "recognize":
                self.btn_recognize.setText("Analyzing...")
            elif active_task == "analyze_scene":
                self.btn_analyze_scene.setText("Analyzing...")
            elif active_task == "clean":
                self.btn_clean.setText("Cleaning...")
            elif active_task == "summarize":
                self.btn_summarize.setText("Summarizing...")
            elif active_task == "chat":
                self.btn_send.setText("Thinking...")
        else:
            self.btn_recognize.setText("👁️ Recognize Writing")
            self.btn_analyze_scene.setText("🔍 Analyze Scene")
            self.btn_clean.setText("✍️ Clean Fix Text")
            self.btn_summarize.setText("📝 Summarize Notes")
            self.btn_send.setText("💬 Send")

    def _on_recognize_clicked(self) -> None:
        logger.info("[AIChatDebug] recognize_clicked")
        if self.worker and self.worker.isRunning():
            return

        if not self.ai_service.is_configured():
            self._append_chat_message("assistant", "❌ Gemini API Key is missing. Please configure your API key in Settings or local .env file.")
            return

        if len(self.canvas.undo_redo.history) == 0 and self.canvas.active_stroke is None:
            logger.info("[AIChatDebug] canvas_capture=empty_canvas")
            self._append_chat_message("assistant", "⚠️ Canvas is empty. Create some air writing first before recognizing.")
            return

        temp_img_path = self.canvas.export_image(transparent=False)
        if not temp_img_path or not os.path.exists(temp_img_path):
            logger.info("[AIChatDebug] canvas_capture=failure")
            self._append_chat_message("assistant", "⚠️ Failed to capture canvas image for recognition.")
            return

        logger.info(f"[AIChatDebug] canvas_capture=success path={temp_img_path}")
        self._set_loading(True, active_task="recognize")
        self._append_chat_message("assistant", "⏳ Analyzing handwriting and context with Gemini Vision...")

        self.worker = AIWorkerThread(self.ai_service, "recognize", temp_img_path, self)
        self.worker.result_ready.connect(self._handle_recognize_result)
        self.worker.start()

    def _handle_recognize_result(self, res: dict) -> None:
        self._set_loading(False)
        if res.get("success"):
            text = res.get("text", "")
            desc = res.get("description", "Handwritten content")
            self.current_writing = text
            self.current_description = desc

            logger.info(f"[AIChatDebug] recognition_result={text}")
            logger.info(f"[AIChatDebug] description_result={desc}")
            logger.info("[AIChatDebug] context_updated")
            logger.info("[AIChatDebug] chat_ready")

            self.lbl_context_writing.setText(f"Writing: {text}")
            self.lbl_context_desc.setText(f"Description: {desc}")

            msg = f"Detected: <b>\"{text}\"</b><br><i style='color:#94A3B8;'>Description: {desc}</i><br><br>Ask me any question about your writing below!"
            self._append_chat_message("assistant", msg)
        else:
            err = res.get("error", "Error during recognition")
            logger.info(f"[AIChatDebug] recognition_error={err}")
            self._append_chat_message("assistant", f"❌ {err}")

    def _on_analyze_scene_clicked(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        if not self.ai_service.is_configured():
            self._append_chat_message("assistant", "❌ Gemini API Key is missing.")
            return

        temp_img_path = self.canvas.export_image(transparent=False)
        if not temp_img_path or not os.path.exists(temp_img_path):
            self._append_chat_message("assistant", "⚠️ Failed to capture frame for scene analysis.")
            return

        self._set_loading(True, active_task="analyze_scene")
        self._append_chat_message("assistant", "🔍 Analyzing scene and objects with Gemini...")

        self.worker = AIWorkerThread(self.ai_service, "analyze_scene", temp_img_path, self)
        self.worker.result_ready.connect(self._handle_analyze_scene_result)
        self.worker.start()

    def _handle_analyze_scene_result(self, res: dict) -> None:
        self._set_loading(False)
        if res.get("success"):
            analysis = res.get("analysis", "")
            self._append_chat_message("assistant", f"🔍 <b>Scene Analysis:</b><br>{analysis}")
        else:
            self._append_chat_message("assistant", f"❌ {res.get('error', 'Error analyzing scene')}")

    def _on_clean_clicked(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        if not self.ai_service.is_configured():
            self._append_chat_message("assistant", "❌ Gemini API Key is missing.")
            return

        target_text = self.current_writing
        if not target_text.strip():
            self._append_chat_message("assistant", "⚠️ Please recognize writing first before cleaning text.")
            return

        self._set_loading(True, active_task="clean")
        self.worker = AIWorkerThread(self.ai_service, "clean", target_text, self)
        self.worker.result_ready.connect(self._handle_clean_result)
        self.worker.start()

    def _handle_clean_result(self, res: dict) -> None:
        self._set_loading(False)
        if res.get("success"):
            cleaned = res.get("text", "")
            self.current_writing = cleaned
            self.lbl_context_writing.setText(f"Writing: {cleaned}")
            self._append_chat_message("assistant", f"✨ <b>Cleaned Text:</b><br>{cleaned}")
        else:
            self._append_chat_message("assistant", f"❌ {res.get('error', 'Error cleaning text')}")

    def _on_summarize_clicked(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        if not self.ai_service.is_configured():
            self._append_chat_message("assistant", "❌ Gemini API Key is missing.")
            return

        target_text = self.current_writing
        if not target_text.strip():
            self._append_chat_message("assistant", "⚠️ Please recognize writing first before summarizing.")
            return

        self._set_loading(True, active_task="summarize")
        self.worker = AIWorkerThread(self.ai_service, "summarize", target_text, self)
        self.worker.result_ready.connect(self._handle_summarize_result)
        self.worker.start()

    def _handle_summarize_result(self, res: dict) -> None:
        self._set_loading(False)
        if res.get("success"):
            summary = res.get("summary", "")
            self._append_chat_message("assistant", f"📝 <b>Summary:</b><br>{summary}")
        else:
            self._append_chat_message("assistant", f"❌ {res.get('error', 'Error summarizing text')}")

    def _on_copy_clicked(self) -> None:
        text = self.current_writing
        if not text.strip():
            self.btn_copy.setText("⚠️ No Text")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copy Text"))
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.btn_copy.setText("✅ Copied!")
        QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copy Text"))

    def _on_send_chat_clicked(self) -> None:
        logger.info("[AIChatDebug] send_clicked")
        if self.worker and self.worker.isRunning():
            logger.info("[AIChatDebug] worker_running -> ignoring duplicate send click")
            return

        question = self.txt_chat_input.text().strip()
        q_present = bool(question)
        logger.info(f"[AIChatDebug] question_present={q_present}")

        if not q_present:
            self._append_chat_message("assistant", "⚠️ Please type a question before clicking Send.")
            logger.info("[AIChatDebug] chat_message_added")
            return

        has_context = bool(self.current_writing or self.current_description)
        logger.info(f"[AIChatDebug] writing_context_present={has_context}")

        api_cfg = self.ai_service.is_configured()
        logger.info(f"[AIChatDebug] api_configured={api_cfg}")

        if not has_context:
            self._append_chat_message("user", question)
            logger.info("[AIChatDebug] chat_message_added")
            self._append_chat_message(
                "assistant",
                "⚠️ Write something on the canvas and click <b>Recognize Writing</b> first so I can answer questions about it."
            )
            logger.info("[AIChatDebug] chat_message_added")
            self.txt_chat_input.clear()
            return

        self._append_chat_message("user", question)
        logger.info("[AIChatDebug] chat_message_added")
        self.txt_chat_input.clear()

        if not api_cfg:
            self._append_chat_message("assistant", "❌ Gemini API Key is missing. Please configure your API key in Settings or local .env file.")
            logger.info("[AIChatDebug] chat_message_added")
            return

        self._set_loading(True, active_task="chat")
        logger.info("[AIChatDebug] chat_request_started")

        payload = {
            "writing": self.current_writing,
            "description": self.current_description,
            "question": question,
            "history": list(self.chat_history[:-1])
        }

        self.worker = AIWorkerThread(self.ai_service, "chat", payload, self)
        self.worker.result_ready.connect(self._handle_chat_result)
        self.worker.start()

    def _handle_chat_result(self, res: dict) -> None:
        self._set_loading(False)
        logger.info(f"[AIChatDebug] chat_response_received success={res.get('success')}")
        if res.get("success"):
            answer = res.get("answer", "")
            logger.info(f"[AIChatDebug] chat_response_length={len(answer)}")
            self._append_chat_message("assistant", answer)
            logger.info("[AIChatDebug] chat_message_added")
        else:
            err = res.get("error", "Error generating chat response.")
            logger.info(f"[AIChatDebug] chat_response_length=0")
            self._append_chat_message("assistant", f"❌ {err}")
            logger.info("[AIChatDebug] chat_message_added")
