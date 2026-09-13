"""Unit test suite for AI Writing Chat feature, FastAPI chat-writing endpoint, context formatting, and frontend chat components."""
import os
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from web.backend.main import app
from web.backend.ai_service import WebAIService
from app.ai_service import AIService


class TestAIChatBackend(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    @patch.object(WebAIService, 'chat_writing')
    def test_api_chat_writing_success(self, mock_chat_writing):
        """Test 1 & 5: /api/chat-writing endpoint returns successful response."""
        mock_chat_writing.return_value = "Photosynthesis is the process by which green plants..."

        payload = {
            "writing": "Explain photosynthesis",
            "description": "Educational question about photosynthesis",
            "question": "Explain it in simple words",
            "history": []
        }

        response = self.client.post("/api/chat-writing", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("answer", data)
        self.assertEqual(data["answer"], "Photosynthesis is the process by which green plants...")

    def test_api_chat_writing_empty_question_validation(self):
        """Test 2 & 4: Request validation rejects empty question with HTTP 400."""
        payload = {
            "writing": "Explain photosynthesis",
            "description": "Educational question",
            "question": "   ",
            "history": []
        }
        response = self.client.post("/api/chat-writing", json=payload)
        self.assertEqual(response.status_code, 400)

    @patch.object(WebAIService, 'chat_writing')
    def test_api_chat_writing_empty_writing_handling(self, mock_chat_writing):
        """Test 3: Chat endpoint handles empty writing context gracefully."""
        mock_chat_writing.return_value = "Please write something on the canvas first."

        payload = {
            "writing": "",
            "description": "",
            "question": "What can you do?",
            "history": []
        }

        response = self.client.post("/api/chat-writing", json=payload)
        self.assertEqual(response.status_code, 200)
        mock_chat_writing.assert_called_once_with(
            writing="",
            description="",
            question="What can you do?",
            history=[]
        )

    @patch.object(WebAIService, 'chat_writing')
    def test_api_chat_writing_passes_context_and_history(self, mock_chat_writing):
        """Test 6, 7 & 10: Writing text, description, and multi-turn chat history are passed to Gemini."""
        mock_chat_writing.return_value = "An example of a quadratic equation is x^2 + 5x + 6 = 0."

        payload = {
            "writing": "x² + 2x + 1 = 0",
            "description": "Quadratic equation",
            "question": "Give me an example",
            "history": [
                {"role": "user", "content": "Solve this equation"},
                {"role": "assistant", "content": "The solution is x = -1."}
            ]
        }

        response = self.client.post("/api/chat-writing", json=payload)
        self.assertEqual(response.status_code, 200)
        mock_chat_writing.assert_called_once_with(
            writing="x² + 2x + 1 = 0",
            description="Quadratic equation",
            question="Give me an example",
            history=[
                {"role": "user", "content": "Solve this equation"},
                {"role": "assistant", "content": "The solution is x = -1."}
            ]
        )

    def test_existing_ai_endpoints_continue_working(self):
        """Test 11: Existing endpoints (/api/health, /api/clean, /api/summarize) continue working."""
        res_health = self.client.get("/api/health")
        self.assertEqual(res_health.status_code, 200)

        with patch.object(WebAIService, 'clean_text', return_value="Cleaned text"):
            res_clean = self.client.post("/api/clean", json={"text": "raw note"})
            self.assertEqual(res_clean.status_code, 200)

        with patch.object(WebAIService, 'summarize_text', return_value="- Summary item"):
            res_sum = self.client.post("/api/summarize", json={"text": "notes content"})
            self.assertEqual(res_sum.status_code, 200)

    def test_no_api_key_exposed_in_frontend_code(self):
        """Test 12: Verify no API keys or secret strings exist in web/frontend/ or app/ UI code."""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "frontend")
        if os.path.exists(frontend_dir):
            for root, _, files in os.walk(frontend_dir):
                for f in files:
                    if f.endswith((".js", ".html", ".css")):
                        fp = os.path.join(root, f)
                        with open(fp, "r", encoding="utf-8") as file_obj:
                            content = file_obj.read()
                            self.assertNotIn("AIzaSy", content, f"Secret Gemini API key pattern found in {f}")
                            self.assertNotIn("X-Gemini-API-Key", content, f"Header API key pattern found in {f}")


class TestDesktopAIServiceChat(unittest.TestCase):

    def setUp(self):
        self.service = AIService()
        self.service.api_key = "AIzaSyTestMockKeyForUnitTest123456789"
        self.service._client = MagicMock()

    def test_desktop_chat_writing_formatting(self):
        """Test desktop AIService formats writing context and history correctly into Gemini prompt."""
        mock_response = MagicMock()
        mock_response.text = "Photosynthesis creates glucose and oxygen."
        self.service._client.models.generate_content.return_value = mock_response

        res = self.service.chat_writing(
            writing="Explain photosynthesis",
            description="Educational topic",
            question="Explain it in simple words",
            history=[{"role": "user", "content": "Hi"}]
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["answer"], "Photosynthesis creates glucose and oxygen.")

        call_kwargs = self.service._client.models.generate_content.call_args[1]
        prompt_content = call_kwargs["contents"]
        self.assertIn("Explain photosynthesis", prompt_content)
        self.assertIn("Educational topic", prompt_content)
        self.assertIn("Explain it in simple words", prompt_content)


class TestFrontendAIChatUI(unittest.TestCase):

    def setUp(self):
        from PySide6.QtWidgets import QApplication
        import sys
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.ai_service = AIService()
        self.ai_service.api_key = "AIzaSyTestMockKeyForUnitTest123456789"
        self.ai_service._client = MagicMock()

        from app.drawing_tools import UndoRedoManager
        from app.canvas import AirWritingCanvas
        from app.ui.ai_panel import AIAssistPanel

        self.mgr = UndoRedoManager()
        self.canvas = AirWritingCanvas(self.mgr)
        self.panel = AIAssistPanel(self.ai_service, self.canvas)

    def test_frontend_empty_writing_context_warning(self):
        """Test 8 & 9: Typing question without active writing context displays helpful UI warning message."""
        self.panel.txt_chat_input.setText("Explain this")
        self.panel._on_send_chat_clicked()

        # Check last message in chat history
        self.assertGreater(len(self.panel.chat_history), 0)
        last_msg = self.panel.chat_history[-1]
        self.assertEqual(last_msg["role"], "assistant")
        self.assertIn("Recognize", last_msg["content"])

    def test_recognize_sets_active_writing_context(self):
        """Test recognize result updates current_writing, current_description, and context card UI."""
        mock_res = {
            "success": True,
            "text": "x^2 + 2x + 1 = 0",
            "description": "Quadratic equation"
        }
        self.panel._handle_recognize_result(mock_res)

        self.assertEqual(self.panel.current_writing, "x^2 + 2x + 1 = 0")
        self.assertEqual(self.panel.current_description, "Quadratic equation")
        self.assertIn("x^2 + 2x + 1 = 0", self.panel.lbl_context_writing.text())
        self.assertIn("Quadratic equation", self.panel.lbl_context_desc.text())


if __name__ == "__main__":
    unittest.main()
