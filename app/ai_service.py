"""Modular Gemini API Service for Handwriting Vision Recognition & Text Processing."""
import os
import base64
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Load environment variables from .env files if available
backend_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "backend", ".env")
root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(backend_env)
load_dotenv(root_env)
load_dotenv()


def _is_valid_key_string(key: str | None) -> bool:
    if not key or not isinstance(key, str):
        return False
    k = key.strip().lower()
    if not k:
        return False
    if (k.startswith("paste_your") or k.startswith("your_") or k.startswith("sk-placeholder") or 
        "placeholder" in k or k == "sk-..."):
        return False
    return True


class AIService:
    """Manages optional Gemini Vision and Text operations with full offline safety."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-3.6-flash"):
        self.model = model or "gemini-3.6-flash"
        self._resolve_and_init(api_key)

    def set_api_key(self, api_key: str | None) -> None:
        self._resolve_and_init(api_key)

    def _resolve_and_init(self, api_key_candidate: str | None = None) -> None:
        env_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        env_key_valid = _is_valid_key_string(env_key)

        config_key = api_key_candidate.strip() if (api_key_candidate and isinstance(api_key_candidate, str)) else None
        config_key_valid = _is_valid_key_string(config_key)

        if config_key_valid:
            self.api_key = config_key
            source = "config"
        elif env_key_valid:
            self.api_key = env_key.strip()
            source = "environment"
        else:
            self.api_key = None
            source = "none"

        logger.info(f"[AIConfig] dotenv_path={backend_env}")
        logger.info(f"[AIConfig] dotenv_exists={os.path.exists(backend_env)}")
        logger.info(f"[AIConfig] environment_key_present={env_key_valid}")
        logger.info(f"[AIConfig] config_key_present={config_key_valid}")
        logger.info(f"[AIConfig] resolved_key_source={source}")
        logger.info(f"[AIConfig] ai_service_configured={_is_valid_key_string(self.api_key)}")
        logger.info(f"[AIConfig] model={self.model}")

        self._client = None
        self._init_client()

    def is_configured(self) -> bool:
        return _is_valid_key_string(self.api_key)

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
                "Analyze the provided image of handwritten text/drawing created via air writing.\n"
                "Return a JSON object with two fields:\n"
                '1. "text": Transcribe all text, numbers, or math equations accurately.\n'
                '2. "description": Provide a concise factual description of what the writing content represents '
                '(e.g., "Educational question asking for an explanation of photosynthesis", "Quadratic equation", "Shopping list", etc.).\n'
                "Output ONLY valid JSON without markdown code blocks."
            )

            image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")

            response = self._client.models.generate_content(
                model=self.model,
                contents=[prompt, image_part]
            )

            raw_text = response.text.strip() if (response and response.text) else ""
            clean_raw = raw_text
            if clean_raw.startswith("```json"):
                clean_raw = clean_raw.split("```json", 1)[1].rsplit("```", 1)[0].strip()
            elif clean_raw.startswith("```"):
                clean_raw = clean_raw.split("```", 1)[1].rsplit("```", 1)[0].strip()

            import json
            try:
                data = json.loads(clean_raw)
                transcribed_text = data.get("text", raw_text)
                desc = data.get("description", "Handwritten content")
            except Exception:
                transcribed_text = raw_text
                desc = f"Handwritten content: '{raw_text[:30]}...'" if raw_text else "Handwritten note"

            return {
                "success": True,
                "error": "",
                "text": transcribed_text,
                "description": desc
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
                "text": "",
                "description": ""
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

    def analyze_scene(self, image_path: str) -> dict[str, str | bool]:
        """Analyze scene/objects in a captured camera frame using Gemini Vision."""
        if not self.is_configured() or not self._client:
            return {
                "success": False,
                "error": "Gemini API key is missing or invalid. Please configure your API key in Settings or GEMINI_API_KEY env var.",
                "analysis": ""
            }

        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image file not found at: {image_path}",
                "analysis": ""
            }

        try:
            with open(image_path, "rb") as f:
                img_bytes = f.read()

            prompt = (
                "Analyze this camera image and identify all key objects, animals, structures, "
                "or general scene elements visible. Provide a clear, concise breakdown of what is present in the scene."
            )

            image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")
            response = self._client.models.generate_content(
                model=self.model,
                contents=[prompt, image_part]
            )

            text = response.text.strip() if (response and response.text) else ""
            return {
                "success": True,
                "error": "",
                "analysis": text
            }
        except Exception as e:
            logger.error(f"Gemini analyze_scene failed: {e}")
            return {
                "success": False,
                "error": f"Gemini AI Error: {e}",
                "analysis": ""
            }

    def chat_writing(self, writing: str, description: str, question: str, history: list[dict] | None = None) -> dict[str, str | bool]:
        """Ask a question about the active writing context with multi-turn chat history using Gemini."""
        if not self.is_configured() or not self._client:
            return {
                "success": False,
                "error": "Gemini API key is missing or invalid. Please configure your API key in Settings or GEMINI_API_KEY env var.",
                "answer": ""
            }

        if not question or not question.strip():
            return {
                "success": False,
                "error": "Question cannot be empty.",
                "answer": ""
            }

        try:
            prompt_parts = []
            prompt_parts.append(
                "You are Live Air Writing AI, an intelligent assistant. Answer the user's question clearly and accurately."
            )
            if writing or description:
                prompt_parts.append("\n=== CURRENT WRITING CONTEXT ===")
                if writing:
                    prompt_parts.append(f"Recognized Writing: {writing}")
                if description:
                    prompt_parts.append(f"Description: {description}")
                prompt_parts.append("===============================\n")
            else:
                prompt_parts.append("\nNote: No active handwriting content provided on canvas.\n")

            if history:
                prompt_parts.append("=== CONVERSATION HISTORY ===")
                for item in history:
                    role = "User" if item.get("role") == "user" else "Assistant"
                    prompt_parts.append(f"{role}: {item.get('content', '')}")
                prompt_parts.append("============================\n")

            prompt_parts.append(f"User Question: {question.strip()}")
            full_prompt = "\n".join(prompt_parts)

            response = self._client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )

            answer = response.text.strip() if (response and response.text) else ""
            return {
                "success": True,
                "error": "",
                "answer": answer
            }
        except Exception as e:
            logger.error(f"Gemini Chat Writing request failed: {e}")
            err_str = str(e)
            if "401" in err_str or "API_KEY_INVALID" in err_str:
                err_msg = "Invalid Gemini API Key."
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                err_msg = "Gemini API rate limit exceeded."
            else:
                err_msg = f"Gemini AI Error: {err_str}"
            return {
                "success": False,
                "error": err_msg,
                "answer": ""
            }
