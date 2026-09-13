"""FastAPI Backend Application for Live Air Writing AI."""
import base64
import logging
import os
from typing import Optional
from fastapi import FastAPI, Request, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from web.backend.ai_service import WebAIService

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Live Air Writing AI Backend",
    description="Production-ready FastAPI backend for browser air writing and Gemini AI assist operations.",
    version="1.0.0"
)

# CORS Configuration for Web Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits local dev & static web hosting
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_service = WebAIService()


# Pydantic Schemas
class TextRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to process")


class ImageJsonRequest(BaseModel):
    image: str = Field(..., description="Base64 PNG image data URL or raw base64 string")


class AIResponse(BaseModel):
    result: str


class HealthResponse(BaseModel):
    status: str
    service: str
    has_api_key: bool


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint to verify backend status and API key availability."""
    has_key = bool(ai_service.api_key or os.getenv("GEMINI_API_KEY"))
    return HealthResponse(status="ok", service="Live Air Writing AI API", has_api_key=has_key)


@app.post("/api/recognize", response_model=AIResponse)
async def recognize_handwriting(
    request: Request,
    file: Optional[UploadFile] = File(None)
):
    """Recognize handwritten text from uploaded canvas PNG image (supports multipart file or base64 JSON)."""
    image_bytes = None
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            image_str = body.get("image", "")
            if not image_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No image field provided in JSON payload."
                )
            if "," in image_str:
                image_str = image_str.split(",", 1)[1]
            image_bytes = base64.b64decode(image_str)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base64 image encoding: {e}"
            )
    elif file:
        image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No canvas image file or base64 image data provided."
        )

    try:
        result = ai_service.recognize_handwriting(image_bytes)
        return AIResponse(result=result)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except RuntimeError as re:
        err_str = str(re).lower()
        if "quota" in err_str or "rate limit" in err_str:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(re))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/clean", response_model=AIResponse)
def clean_text(req: TextRequest):
    """Clean and fix formatting, grammar, and line breaks of transcribed text."""
    try:
        result = ai_service.clean_text(req.text)
        return AIResponse(result=result)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except RuntimeError as re:
        err_str = str(re).lower()
        if "quota" in err_str or "rate limit" in err_str:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(re))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/summarize", response_model=AIResponse)
def summarize_text(req: TextRequest):
    """Summarize transcribed text into clear notes."""
    try:
        result = ai_service.summarize_text(req.text)
        return AIResponse(result=result)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except RuntimeError as re:
        err_str = str(re).lower()
        if "quota" in err_str or "rate limit" in err_str:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(re))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/analyze-scene", response_model=AIResponse)
async def analyze_scene(
    request: Request,
    file: Optional[UploadFile] = File(None)
):
    """Analyze scene/objects in uploaded camera image frame (supports multipart file or base64 JSON)."""
    image_bytes = None
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            image_str = body.get("image", "")
            if not image_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No image field provided in JSON payload."
                )
            if "," in image_str:
                image_str = image_str.split(",", 1)[1]
            image_bytes = base64.b64decode(image_str)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base64 image encoding: {e}"
            )
    elif file:
        image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No camera image frame or base64 image data provided."
        )

    try:
        result = ai_service.analyze_scene(image_bytes)
        return AIResponse(result=result)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except RuntimeError as re:
        err_str = str(re).lower()
        if "quota" in err_str or "rate limit" in err_str:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(re))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


class ChatHistoryItem(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class ChatWritingRequest(BaseModel):
    writing: Optional[str] = ""
    description: Optional[str] = ""
    question: str = Field(..., min_length=1, description="Question asked by the user")
    history: Optional[list[ChatHistoryItem]] = []


class ChatWritingResponse(BaseModel):
    answer: str


@app.post("/api/chat-writing", response_model=ChatWritingResponse)
def chat_writing(req: ChatWritingRequest):
    """Answer questions about the active air writing context using Gemini."""
    if not req.question or not req.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is required and cannot be empty."
        )

    try:
        history_list = [h.model_dump() for h in req.history] if req.history else []
        answer = ai_service.chat_writing(
            writing=req.writing or "",
            description=req.description or "",
            question=req.question,
            history=history_list
        )
        return ChatWritingResponse(answer=answer)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except RuntimeError as re:
        err_str = str(re).lower()
        if "quota" in err_str or "rate limit" in err_str:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(re))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ----------------------------------------------------
# Static Files & Frontend Mount (Mounted after API routes)
# ----------------------------------------------------
FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend"
)

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    logger.warning(f"Frontend directory not found at: {FRONTEND_DIR}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("web.backend.main:app", host="0.0.0.0", port=port, reload=True)
