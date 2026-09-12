"""Web AI Service wrapper for Google Gemini API using google-genai SDK."""
import os
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.6-flash"


class WebAIService:
    """Service handling server-side Gemini API inference for the web application."""

    def __init__(self, api_key: str | None = None, model_name: str = DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name

    def _get_client(self) -> genai.Client:
        key = self.api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is missing. "
                "Please configure GEMINI_API_KEY in your environment or web/backend/.env file."
            )
        return genai.Client(api_key=key)

    def recognize_handwriting(self, image_bytes: bytes) -> str:
        """Recognize handwritten text from air-writing canvas PNG image bytes using Gemini multimodal vision."""
        if not image_bytes:
            raise ValueError("No image data provided for handwriting recognition.")

        client = self._get_client()
        prompt = (
            "Transcribe all handwritten text, numbers, symbols, or math equations present in this "
            "air-writing canvas image. Output ONLY the raw transcribed text with no conversational filler, "
            "commentary, or code block wrapping."
        )

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    prompt
                ]
            )
            text = (response.text or "").strip()
            if not text:
                return "⚠️ No handwriting text recognized in the canvas image."
            return text
        except Exception as e:
            logger.error(f"[Gemini API Error] recognize_handwriting failed: {e}")
            err_str = str(e).lower()
            if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                raise RuntimeError("Gemini API rate limit or quota exceeded. Please try again later.")
            elif "api_key" in err_str or "unauthorized" in err_str or "401" in err_str or "invalid" in err_str:
                raise ValueError("Invalid or unauthorized Gemini API key.")
            else:
                raise RuntimeError(f"Gemini API request failed: {e}")

    def clean_text(self, text: str) -> str:
        """Clean, format, and correct spelling/grammar of transcribed text."""
        cleaned_input = (text or "").strip()
        if not cleaned_input:
            raise ValueError("Text input is required for cleaning.")

        client = self._get_client()
        prompt = (
            f"Clean and fix formatting, spelling, grammar, and line breaks for the following "
            f"transcribed text while preserving its exact original meaning:\n\n{cleaned_input}"
        )

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            result = (response.text or "").strip()
            return result if result else cleaned_input
        except Exception as e:
            logger.error(f"[Gemini API Error] clean_text failed: {e}")
            err_str = str(e).lower()
            if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                raise RuntimeError("Gemini API rate limit or quota exceeded. Please try again later.")
            elif "api_key" in err_str or "unauthorized" in err_str or "401" in err_str or "invalid" in err_str:
                raise ValueError("Invalid or unauthorized Gemini API key.")
            else:
                raise RuntimeError(f"Gemini API request failed: {e}")

    def summarize_text(self, text: str) -> str:
        """Summarize transcribed text into clear bullet points or notes."""
        cleaned_input = (text or "").strip()
        if not cleaned_input:
            raise ValueError("Text input is required for summarization.")

        client = self._get_client()
        prompt = f"Provide a concise, structured summary of the following notes/text:\n\n{cleaned_input}"

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            result = (response.text or "").strip()
            return result if result else cleaned_input
        except Exception as e:
            logger.error(f"[Gemini API Error] summarize_text failed: {e}")
            err_str = str(e).lower()
            if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                raise RuntimeError("Gemini API rate limit or quota exceeded. Please try again later.")
            elif "api_key" in err_str or "unauthorized" in err_str or "401" in err_str or "invalid" in err_str:
                raise ValueError("Invalid or unauthorized Gemini API key.")
            else:
                raise RuntimeError(f"Gemini API request failed: {e}")

    def analyze_scene(self, image_bytes: bytes) -> str:
        """Analyze scene/objects in a captured camera image frame (e.g. Dog, Cat, Tower/building, general scene/object)."""
        if not image_bytes:
            raise ValueError("No image data provided for scene analysis.")

        client = self._get_client()
        prompt = (
            "Analyze this camera image and identify all key objects, animals (e.g., dog, cat), structures "
            "(e.g., towers, buildings), or general scene elements visible. Provide a clear, concise bulleted breakdown "
            "and summary of what is present in the scene."
        )

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    prompt
                ]
            )
            text = (response.text or "").strip()
            if not text:
                return "⚠️ No objects or scene details identified in the image."
            return text
        except Exception as e:
            logger.error(f"[Gemini API Error] analyze_scene failed: {e}")
            err_str = str(e).lower()
            if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                raise RuntimeError("Gemini API rate limit or quota exceeded. Please try again later.")
            elif "api_key" in err_str or "unauthorized" in err_str or "401" in err_str or "invalid" in err_str:
                raise ValueError("Invalid or unauthorized Gemini API key.")
            else:
                raise RuntimeError(f"Gemini API request failed: {e}")
