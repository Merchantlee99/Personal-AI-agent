import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.utils.provider_clients import call_provider

router = APIRouter()
logger = logging.getLogger(__name__)

DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "gemini": "gemini-2.5-pro",
    "anthropic": "claude-sonnet-4-5-20250929",
}


class LLMRequest(BaseModel):
    provider: Literal["anthropic", "openai", "gemini"]
    prompt: str = Field(..., min_length=1)
    model: Optional[str] = None
    system: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7


class LLMResponse(BaseModel):
    provider: str
    model: str
    content: str


@router.post("/llm", response_model=LLMResponse)
async def llm_proxy(req: LLMRequest):
    try:
        model_name = req.model or DEFAULT_MODELS[req.provider]
        system = req.system or ""
        messages = [{"role": "user", "content": req.prompt}]
        content = await call_provider(
            req.provider,
            system,
            messages,
            model_name,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
        return LLMResponse(provider=req.provider, model=model_name, content=content)
    except HTTPException:
        raise
    except Exception:
        logger.exception("LLM provider call failed")
        raise HTTPException(status_code=502, detail="LLM provider call failed")
