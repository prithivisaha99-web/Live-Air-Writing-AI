"""End-to-End integration tests for web application full pipeline (Frontend API Contract -> FastAPI Backend -> Gemini AI Service)."""
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from web.backend.main import app


class TestWebIntegrationPipeline(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    @patch("web.backend.main.ai_service.recognize_handwriting")
    @patch("web.backend.main.ai_service.clean_text")
    @patch("web.backend.main.ai_service.summarize_text")
    def test_full_ai_assist_pipeline_flow(self, mock_summarize, mock_clean, mock_recognize):
        """Test end-to-end workflow: Recognize Canvas PNG -> Clean Text -> Summarize Notes."""

        # 1. Step 1: Recognize handwriting from canvas image
        mock_recognize.return_value = "air writing math formula e = mc^2"
        fake_png_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        recognize_res = self.client.post("/api/recognize", json={"image": fake_png_b64})
        self.assertEqual(recognize_res.status_code, 200)
        raw_text = recognize_res.json()["result"]
        self.assertEqual(raw_text, "air writing math formula e = mc^2")

        # 2. Step 2: Clean and format the transcribed text
        mock_clean.return_value = "Air writing math formula: E = mc²."
        clean_res = self.client.post("/api/clean", json={"text": raw_text})
        self.assertEqual(clean_res.status_code, 200)
        cleaned_text = clean_res.json()["result"]
        self.assertEqual(cleaned_text, "Air writing math formula: E = mc².")

        # 3. Step 3: Summarize the cleaned text into notes
        mock_summarize.return_value = "• Math Formula: Mass-energy equivalence equation (E = mc²)"
        summarize_res = self.client.post("/api/summarize", json={"text": cleaned_text})
        self.assertEqual(summarize_res.status_code, 200)
        summary = summarize_res.json()["result"]
        self.assertEqual(summary, "• Math Formula: Mass-energy equivalence equation (E = mc²)")

        # Verify mocks were invoked in sequence
        mock_recognize.assert_called_once()
        mock_clean.assert_called_once_with("air writing math formula e = mc^2")
        mock_summarize.assert_called_once_with("Air writing math formula: E = mc².")

    @patch("web.backend.main.ai_service.recognize_handwriting")
    def test_pipeline_server_key_only(self, mock_recognize):
        """Test client requests proceed using server environment key, ignoring any extra headers."""
        mock_recognize.return_value = "Server Key Handwriting Text"
        fake_png_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        res = self.client.post(
            "/api/recognize",
            json={"image": fake_png_b64}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["result"], "Server Key Handwriting Text")
        mock_recognize.assert_called_once_with(unittest.mock.ANY)

    def test_cors_headers_present(self):
        """Test CORS headers are returned for cross-origin browser requests."""
        response = self.client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        self.assertEqual(response.status_code, 200)
    @patch("web.backend.main.ai_service.chat_writing")
    def test_chat_writing_pipeline_flow(self, mock_chat):
        """Test POST /api/chat-writing endpoint contract with writing context and history."""
        mock_chat.return_value = "A machine is a mechanical system."
        payload = {
            "writing": "Machine",
            "description": "Handwritten word Machine",
            "question": "What is this?",
            "history": [{"role": "user", "content": "Hi"}]
        }
        res = self.client.post("/api/chat-writing", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["answer"], "A machine is a mechanical system.")
        mock_chat.assert_called_once_with(
            writing="Machine",
            description="Handwritten word Machine",
            question="What is this?",
            history=[{"role": "user", "content": "Hi"}]
        )

    def test_chat_writing_empty_question_returns_400(self):
        """Test POST /api/chat-writing with empty question returns 400 Bad Request."""
        payload = {"writing": "Machine", "description": "", "question": "   ", "history": []}
        res = self.client.post("/api/chat-writing", json=payload)
        self.assertEqual(res.status_code, 400)

    @patch("web.backend.main.ai_service.chat_writing")
    def test_chat_writing_key_not_exposed(self, mock_chat):
        """Test API key value is never returned in chat-writing response headers or body."""
        mock_chat.return_value = "Sample AI response"
        payload = {"writing": "Machine", "description": "Word", "question": "Explain"}
        res = self.client.post("/api/chat-writing", json=payload)
        self.assertEqual(res.status_code, 200)
        body = res.text
        self.assertNotIn("PASTE_YOUR", body)
        self.assertNotIn("GEMINI_API_KEY", body)


if __name__ == "__main__":
    unittest.main()
