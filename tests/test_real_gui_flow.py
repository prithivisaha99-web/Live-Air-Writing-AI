"""Integration test for PySide6 AIAssistPanel real GUI context flow."""
import os
import sys
import unittest
from PySide6.QtWidgets import QApplication

from app.settings import SettingsManager
from app.ai_service import AIService
from app.canvas import AirWritingCanvas, UndoRedoManager
from app.ui.ai_panel import AIAssistPanel

# Ensure QApplication instance exists
app = QApplication.instance() or QApplication(sys.argv)


class TestRealGUIFlow(unittest.TestCase):
    """Verifies AIAssistPanel UI state updates and context creation."""

    def setUp(self):
        self.settings = SettingsManager()
        self.ai_service = AIService()
        self.undo_redo = UndoRedoManager()
        self.canvas = AirWritingCanvas(self.undo_redo)
        self.panel = AIAssistPanel(self.ai_service, self.canvas)

    def test_api_status_is_ready(self):
        """Verify that API status badge displays 'API Ready' when key is loaded."""
        self.panel.update_api_status()
        self.assertEqual(self.panel.lbl_api_status.text(), "API Ready")

    def test_recognize_result_populates_context_card(self):
        """Simulate a successful recognition result and verify context card labels."""
        res = {
            "success": True,
            "text": "Machine",
            "description": "Handwritten word Machine in white on dark canvas"
        }
        self.panel._handle_recognize_result(res)

        self.assertEqual(self.panel.current_writing, "Machine")
        self.assertEqual(self.panel.current_description, "Handwritten word Machine in white on dark canvas")
        self.assertEqual(self.panel.lbl_context_writing.text(), "Writing: Machine")
        self.assertEqual(self.panel.lbl_context_desc.text(), "Description: Handwritten word Machine in white on dark canvas")

    def test_chat_result_appends_to_chat_history(self):
        """Simulate chat response and verify history tracking."""
        self.panel.current_writing = "Machine"
        self.panel.current_description = "Handwritten word Machine in white on dark canvas"

        res1 = {
            "success": True,
            "answer": "A machine is a physical system using power to apply forces and control movement to perform an intended action."
        }
        self.panel._handle_chat_result(res1)
        self.assertIn("A machine is a physical system", self.panel.txt_chat_display.toPlainText())

    def test_send_button_and_enter_key_signals(self):
        """Verify btn_send click and txt_chat_input returnPressed trigger chat send handler."""
        self.panel.ai_service.chat_writing = lambda *args, **kwargs: {"success": True, "answer": "Mocked AI Answer"}
        self.panel.txt_chat_input.setText("Test signal question")
        self.panel.current_writing = "Machine"
        self.panel.current_description = "Handwritten word Machine"

        # Click send button
        self.panel.btn_send.click()
        if self.panel.worker:
            self.panel.worker.wait(1000)
        self.assertIn("You:", self.panel.txt_chat_display.toHtml())

        # Reset worker state and simulate Enter key signal
        self.panel.worker = None
        self.panel.txt_chat_input.setText("Test enter key question")
        self.panel.txt_chat_input.returnPressed.emit()
        if self.panel.worker:
            self.panel.worker.wait(1000)
        self.assertIn("Test enter key question", self.panel.txt_chat_display.toHtml())

    def test_empty_question_shows_warning(self):
        """Verify empty question input displays a helpful warning message."""
        self.panel.txt_chat_input.clear()
        self.panel._on_send_chat_clicked()
        self.assertIn("Please type a question", self.panel.txt_chat_display.toPlainText())

    def test_missing_writing_context_shows_warning(self):
        """Verify question sent without writing context alerts user to recognize writing first."""
        self.panel.current_writing = ""
        self.panel.current_description = ""
        self.panel.txt_chat_input.setText("What is this?")
        self.panel._on_send_chat_clicked()
        self.assertIn("Recognize Writing", self.panel.txt_chat_display.toHtml())

    def test_api_key_never_exposed_in_ui(self):
        """Verify API key value is never rendered in any UI label or chat text."""
        ui_text = self.panel.txt_chat_display.toPlainText() + self.panel.lbl_api_status.text()
        self.assertNotIn("PASTE_YOUR", ui_text)
        if self.ai_service.api_key:
            self.assertNotIn(self.ai_service.api_key, ui_text)

    def tearDown(self):
        self.panel.close()


if __name__ == "__main__":
    unittest.main()
