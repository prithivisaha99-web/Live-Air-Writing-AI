"""Modular Gemini API Service for Handwriting Vision Recognition & Text Processing."""
import os
import base64
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Load environment variables from .env file if available
load_dotenv()


class AIService:
    """Manages optional Gemini Vision and Text operations with full offline safety."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash"):
        key_candidate = api_key.strip() if (api_key and isinstance(api_key, str)) else None
        self.api_key = key_candidate or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = model or "gemini-2.5-flash"
        self._client = None
        self._init_client()

    def set_api_key(self, api_key: str | None) -> None:
        key_candidate = api_key.strip() if (api_key and isinstance(api_key, str)) else None
        self.api_key = key_candidate or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self._client = None
        self._init_client()

    def is_configured(self) -> bool:
        if not self.api_key or not isinstance(self.api_key, str):
            return False
        clean_key = self.api_key.strip()
        if not clean_key:
            return False
        if clean_key.startswith("your_gemini") or clean_key.startswith("your_openai") or clean_key == "sk-...":
            return False
        return True

    def _init_client(self) -> None:
        if self.is_configured():
            try:
                self._client = genai.Client(api_key=self.api_key.strip())
                logger.info("Gemini client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self._client = None
        else:
            self._client = None

    def recognize_handwriting(self, image_path: str) -> dict[str, str | bool]:
        """
        Recognize air-written text on a canvas image using Gemini Vision.
        """
        if not self.is_configured() or not self._client:
            return {
                "success": False,
                "error": "Gemini API key is missing or invalid. Please configure your API key in Settings or GEMINI_API_KEY env var.",
                "text": ""
            }

        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image file not found at: {image_path}",
                "text": ""
            }

        try:
            with open(image_path, "rb") as f:
                img_bytes = f.read()

            prompt = (
                "You are an expert handwriting recognition assistant. "
                "Analyze the provided image of handwritten text/drawing created via air writing. "
                "Transcribe all text accurately. If there are drawings or equations, describe them clearly. "
                "Return ONLY the transcribed text without conversational commentary."
            )

            image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")

            response = self._client.models.generate_content(
                model=self.model,
                contents=[prompt, image_part]
            )

            transcribed_text = response.text.strip() if (response and response.text) else ""
            return {
                "success": True,
                "error": "",
                "text": transcribed_text
            }
        except Exception as e:
            logger.error(f"Gemini Vision request failed: {e}")
            err_type = type(e).__name__
            err_str = str(e)
            if "401" in err_str or "API_KEY_INVALID" in err_str or "Unauthenticated" in err_str:
                err_msg = "Invalid Gemini API Key. Please verify your API key in Settings or GEMINI_API_KEY environment variable."
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota" in err_str:
                err_msg = "Gemini API rate limit or quota exceeded."
            elif "Connect" in err_str or "Network" in err_str:
                err_msg = "Network Connection Error. Unable to reach Gemini servers."
            else:
                err_msg = f"Gemini AI Recognition Error ({err_type}): {err_str}"

            return {
                "success": False,
                "error": err_msg,
                "text": ""
            }

    def clean_text(self, text: str) -> dict[str, str | bool]:
        """Clean up typos, formatting, and spelling in transcribed text using Gemini."""
        if not self.is_configured() or not self._client:
            return {"success": False, "error": "Gemini API key is missing or invalid. Please configure your API key in Settings or GEMINI_API_KEY env var.", "text": text}

        if not text.strip():
            return {"success": False, "error": "No text provided to clean.", "text": ""}

        try:
            prompt = f"Correct grammar, spelling, typos, and formatting of the following transcribed handwritten notes while strictly preserving the original meaning and technical terms. Return ONLY the cleaned text:\n\n{text}"
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            cleaned = response.text.strip() if (response and response.text) else ""
            return {"success": True, "error": "", "text": cleaned}
        except Exception as e:
            logger.error(f"Gemini clean text failed: {e}")
            err_str = str(e)
            if "401" in err_str or "API_KEY_INVALID" in err_str:
                err_msg = "Invalid Gemini API Key."
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                err_msg = "Gemini API rate limit exceeded."
            else:
                err_msg = f"Gemini AI Error: {err_str}"
            return {"success": False, "error": err_msg, "text": text}

    def summarize_text(self, text: str) -> dict[str, str | bool]:
        """Summarize transcribed handwriting into concise key points using Gemini."""
        if not self.is_configured() or not self._client:
            return {"success": False, "error": "Gemini API key is missing or invalid. Please configure your API key in Settings or GEMINI_API_KEY env var.", "summary": ""}

        if not text.strip():
            return {"success": False, "error": "No text provided to summarize.", "summary": ""}

        try:
            prompt = f"Summarize the provided handwritten notes into concise, clear bullet points. Preserve essential points and remove repetition. Return ONLY the summary:\n\n{text}"
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            summary = response.text.strip() if (response and response.text) else ""
            return {"success": True, "error": "", "summary": summary}
        except Exception as e:
            logger.error(f"Gemini summarize failed: {e}")
            err_str = str(e)
            if "401" in err_str or "API_KEY_INVALID" in err_str:
                err_msg = "Invalid Gemini API Key."
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                err_msg = "Gemini API rate limit exceeded."
            else:
                err_msg = f"Gemini AI Error: {err_str}"
            return {"success": False, "error": err_msg, "summary": ""}
