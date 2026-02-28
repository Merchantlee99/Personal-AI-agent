from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Literal

from anthropic import AsyncAnthropic
from fastapi import HTTPException
import google.generativeai as genai
from openai import AsyncOpenAI

Provider = Literal["anthropic", "openai", "gemini"]


@dataclass(frozen=True)
class ProviderCallResult:
    content: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


def _api_key(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise HTTPException(status_code=500, detail=f"{name} not configured")
    return value


def _safe_int(value: object) -> int:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except Exception:
        return 0
    return parsed if parsed > 0 else 0


def _normalize_openai_content(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            else:
                text = getattr(item, "text", None)
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()
    return ""


async def call_provider(
    provider: Provider,
    system: str,
    messages: list[dict[str, str]],
    model: str,
    *,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> ProviderCallResult:
    if provider == "anthropic":
        client = AsyncAnthropic(api_key=_api_key("ANTHROPIC_API_KEY"))
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            temperature=temperature,
        )
        parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        content = "\n".join(parts).strip()
        if not content:
            raise HTTPException(status_code=502, detail="Anthropic response did not contain text")
        usage = getattr(response, "usage", None)
        input_tokens = _safe_int(getattr(usage, "input_tokens", 0))
        output_tokens = _safe_int(getattr(usage, "output_tokens", 0))
        return ProviderCallResult(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )
    if provider == "openai":
        client = AsyncOpenAI(api_key=_api_key("OPENAI_API_KEY"))
        all_messages = [{"role": "system", "content": system}] + messages
        response = await client.chat.completions.create(
            model=model,
            messages=all_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = _normalize_openai_content(response.choices[0].message.content)
        if not content:
            raise HTTPException(status_code=502, detail="OpenAI response did not contain text")
        usage = getattr(response, "usage", None)
        input_tokens = _safe_int(getattr(usage, "prompt_tokens", 0))
        output_tokens = _safe_int(getattr(usage, "completion_tokens", 0))
        total_tokens = _safe_int(getattr(usage, "total_tokens", input_tokens + output_tokens))
        if total_tokens == 0:
            total_tokens = input_tokens + output_tokens
        return ProviderCallResult(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
    if provider == "gemini":
        genai.configure(api_key=_api_key("GEMINI_API_KEY"))
        gen_model = genai.GenerativeModel(model_name=model, system_instruction=system)
        user_msg = messages[-1]["content"] if messages else ""
        response = await asyncio.to_thread(
            gen_model.generate_content,
            user_msg,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        content = (getattr(response, "text", None) or "").strip()
        if not content and getattr(response, "candidates", None):
            parts: list[str] = []
            for candidate in response.candidates:
                candidate_content = getattr(candidate, "content", None)
                for part in getattr(candidate_content, "parts", []) or []:
                    text = getattr(part, "text", None)
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            content = "\n".join(parts).strip()
        if not content:
            raise HTTPException(status_code=502, detail="Gemini response did not contain text")
        usage = getattr(response, "usage_metadata", None)
        input_tokens = _safe_int(getattr(usage, "prompt_token_count", 0))
        output_tokens = _safe_int(getattr(usage, "candidates_token_count", 0))
        total_tokens = _safe_int(getattr(usage, "total_token_count", input_tokens + output_tokens))
        if total_tokens == 0:
            total_tokens = input_tokens + output_tokens
        return ProviderCallResult(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
    raise HTTPException(status_code=500, detail=f"Unknown provider: {provider}")
