"""Unit tests for FastAPI web backend endpoints and Gemini AI service mocking."""
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from web.backend.main import app


class TestWebBackendEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_check_endpoint(self):
        """Test GET /api/health returns 200 OK with correct status payload."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "Live Air Writing AI API")

    def test_root_serves_frontend_index_html(self):
        """Test GET / serves web/frontend/index.html with 200 OK."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("<title>Live Air Writing AI - Web</title>", response.text)

    def test_static_assets_serving(self):
        """Test static assets (CSS & JS modules) are served with 200 OK."""
        css_res = self.client.get("/css/style.css")
        self.assertEqual(css_res.status_code, 200)

        landing_css_res = self.client.get("/css/landing.css")
        self.assertEqual(landing_css_res.status_code, 200)

        js_app_res = self.client.get("/js/app.js")
        self.assertEqual(js_app_res.status_code, 200)

        landing_js_res = self.client.get("/js/landing.js")
        self.assertEqual(landing_js_res.status_code, 200)

        js_canvas_res = self.client.get("/js/air_canvas.js")
        self.assertEqual(js_canvas_res.status_code, 200)

    @patch("web.backend.main.ai_service.recognize_handwriting")
    def test_recognize_handwriting_file_upload(self, mock_recognize):
        """Test POST /api/recognize with multipart image file upload."""
        mock_recognize.return_value = "Hello Gemini Air Writing"
        fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        response = self.client.post(
            "/api/recognize",
            files={"file": ("canvas.png", fake_png, "image/png")}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"result": "Hello Gemini Air Writing"})
        mock_recognize.assert_called_once()

    @patch("web.backend.main.ai_service.recognize_handwriting")
    def test_recognize_handwriting_base64_json(self, mock_recognize):
        """Test POST /api/recognize with base64 data URL in JSON payload."""
        mock_recognize.return_value = "Base64 Transcribed Math"
        fake_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        response = self.client.post(
            "/api/recognize",
            json={"image": fake_b64}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"result": "Base64 Transcribed Math"})
        mock_recognize.assert_called_once()

    def test_recognize_handwriting_missing_image(self):
        """Test POST /api/recognize returns 400 Bad Request when no image is supplied."""
        response = self.client.post("/api/recognize")
        self.assertEqual(response.status_code, 400)
        self.assertIn("No canvas image file or base64 image data provided", response.json()["detail"])

    @patch("web.backend.main.ai_service.clean_text")
    def test_clean_text_success(self, mock_clean):
        """Test POST /api/clean with valid text payload."""
        mock_clean.return_value = "Hello world. This is clean text."

        response = self.client.post(
            "/api/clean",
            json={"text": "hello wrld. this is clean text."}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"result": "Hello world. This is clean text."})
        mock_clean.assert_called_once_with("hello wrld. this is clean text.")

    def test_clean_text_validation_error(self):
        """Test POST /api/clean returns 422 Unprocessable Entity for invalid/empty request body."""
        response = self.client.post("/api/clean", json={"text": ""})
        self.assertEqual(response.status_code, 422)

    @patch("web.backend.main.ai_service.summarize_text")
    def test_summarize_text_success(self, mock_summarize):
        """Test POST /api/summarize with valid text payload."""
        mock_summarize.return_value = "• Key Point 1\n• Key Point 2"

        response = self.client.post(
            "/api/summarize",
            json={"text": "Long detailed notes here..."}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"result": "• Key Point 1\n• Key Point 2"})
        mock_summarize.assert_called_once_with("Long detailed notes here...")

    @patch("web.backend.main.ai_service.clean_text")
    def test_error_handling_missing_api_key(self, mock_clean):
        """Test endpoint handles missing API key ValueError as 400 Bad Request."""
        mock_clean.side_effect = ValueError("GEMINI_API_KEY environment variable is missing.")

        response = self.client.post("/api/clean", json={"text": "sample text"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("GEMINI_API_KEY environment variable is missing", response.json()["detail"])

    @patch("web.backend.main.ai_service.clean_text")
    def test_error_handling_quota_exceeded(self, mock_clean):
        """Test endpoint handles quota/rate limit error as 429 Too Many Requests."""
        mock_clean.side_effect = RuntimeError("Gemini API rate limit or quota exceeded. Please try again later.")

        response = self.client.post("/api/clean", json={"text": "sample text"})
        self.assertEqual(response.status_code, 429)
        self.assertIn("quota exceeded", response.json()["detail"])

    @patch("web.backend.main.ai_service.summarize_text")
    def test_error_handling_internal_server_error(self, mock_summarize):
        """Test endpoint handles unhandled server runtime error as 500 Internal Server Error."""
        mock_summarize.side_effect = RuntimeError("Connection timeout to Gemini endpoint.")

        response = self.client.post("/api/summarize", json={"text": "sample text"})
        self.assertEqual(response.status_code, 500)
        self.assertIn("Connection timeout", response.json()["detail"])

    @patch("web.backend.main.ai_service.analyze_scene")
    def test_analyze_scene_file_upload(self, mock_analyze):
        """Test POST /api/analyze-scene with multipart image file upload."""
        mock_analyze.return_value = "• Object 1: Golden Retriever Dog\n• Object 2: Wooden Table"
        fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        response = self.client.post(
            "/api/analyze-scene",
            files={"file": ("frame.png", fake_png, "image/png")}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"result": "• Object 1: Golden Retriever Dog\n• Object 2: Wooden Table"})
        mock_analyze.assert_called_once()

    @patch("web.backend.main.ai_service.analyze_scene")
    def test_analyze_scene_base64_json(self, mock_analyze):
        """Test POST /api/analyze-scene with base64 data URL in JSON payload."""
        mock_analyze.return_value = "• Identified structure: Eiffel Tower"
        fake_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        response = self.client.post(
            "/api/analyze-scene",
            json={"image": fake_b64}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"result": "• Identified structure: Eiffel Tower"})
        mock_analyze.assert_called_once()

    def test_analyze_scene_missing_image(self):
        """Test POST /api/analyze-scene returns 400 Bad Request when no image is supplied."""
        response = self.client.post("/api/analyze-scene")
        self.assertEqual(response.status_code, 400)
        self.assertIn("No camera image frame or base64 image data provided", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
