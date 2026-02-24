import asyncio
import os
from typing import Literal, Optional

import anthropic
import google.generativeai as genai
from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

router = APIRouter()

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


def _require_api_key(name: str) -> str:
    key = os.getenv(name, "").strip()
    if not key:
        raise ValueError(f"Missing required environment variable: {name}")
    return key


def _normalize_openai_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
            else:
                text = getattr(item, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part).strip()
    return ""


async def _call_openai(req: LLMRequest) -> tuple[str, str]:
    model_name = req.model or DEFAULT_MODELS["openai"]
    api_key = _require_api_key("OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=api_key)

    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.append({"role": "user", "content": req.prompt})

    response = await client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
    )
    message = response.choices[0].message
    content = _normalize_openai_content(message.content)
    if not content:
        raise ValueError("OpenAI response did not contain text content")

    return model_name, content


async def _call_gemini(req: LLMRequest) -> tuple[str, str]:
    model_name = req.model or DEFAULT_MODELS["gemini"]
    api_key = _require_api_key("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    generation_config = {
        "temperature": req.temperature,
        "max_output_tokens": req.max_tokens,
    }
    model = genai.GenerativeModel(model_name=model_name, system_instruction=req.system)
    response = await asyncio.to_thread(
        model.generate_content,
        req.prompt,
        generation_config=generation_config,
    )

    content = (getattr(response, "text", None) or "").strip()
    if not content and getattr(response, "candidates", None):
        parts = []
        for candidate in response.candidates:
            candidate_content = getattr(candidate, "content", None)
            candidate_parts = getattr(candidate_content, "parts", []) or []
            for part in candidate_parts:
                text = getattr(part, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        content = "\n".join(parts).strip()

    if not content:
        raise ValueError("Gemini response did not contain text content")

    return model_name, content


async def _call_anthropic(req: LLMRequest) -> tuple[str, str]:
    model_name = req.model or DEFAULT_MODELS["anthropic"]
    api_key = _require_api_key("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    kwargs = {
        "model": model_name,
        "messages": [{"role": "user", "content": req.prompt}],
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
    }
    if req.system:
        kwargs["system"] = req.system

    response = await asyncio.to_thread(client.messages.create, **kwargs)
    parts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    content = "\n".join(parts).strip()
    if not content:
        raise ValueError("Anthropic response did not contain text content")

    return model_name, content


@router.post("/llm", response_model=LLMResponse)
async def llm_proxy(req: LLMRequest):
    try:
        if req.provider == "openai":
            model_name, content = await _call_openai(req)
        elif req.provider == "gemini":
            model_name, content = await _call_gemini(req)
        elif req.provider == "anthropic":
            model_name, content = await _call_anthropic(req)
        else:
            raise ValueError("Unsupported provider")

        return LLMResponse(provider=req.provider, model=model_name, content=content)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
