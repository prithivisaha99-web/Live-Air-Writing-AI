"""Unit tests for AI Service Module."""
import unittest
from unittest.mock import patch
from app.ai_service import AIService


class TestAIService(unittest.TestCase):

    @patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=True)
    def test_unconfigured_api_key_graceful_handling(self):
        service = AIService(api_key="")
        self.assertFalse(service.is_configured())

        # Test recognize handwriting without key
        res = service.recognize_handwriting("non_existent.png")
        self.assertFalse(res["success"])
        self.assertIn("API key is missing", res["error"])

        # Test clean text without key
        res_clean = service.clean_text("hello wrld")
        self.assertFalse(res_clean["success"])

        # Test summarize text without key
        res_sum = service.summarize_text("some notes")
        self.assertFalse(res_sum["success"])


if __name__ == "__main__":
    unittest.main()
