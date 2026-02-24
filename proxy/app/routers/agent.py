"""
에이전트 실시간 채팅 라우터.
프론트엔드 → Next.js → 이 엔드포인트 → LLM API
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import List, Optional

import google.generativeai as genai
from anthropic import AsyncAnthropic
from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.utils.memory_writer import apply_memory_updates, extract_memory_updates

router = APIRouter()

PERSONAS_DIR = Path("/app/personas")
VAULT_DIR = Path("/app/vault")

# 에이전트 설정
AGENT_CONFIG = {
    "ace": {
        "name": "Morpheus",
        "provider": "anthropic",
        "model": "claude-opus-4-6",
        "persona_file": "ace.md",
        "include_memory": True,
    },
    "owl": {
        "name": "Clio",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "persona_file": "owl.md",
        "include_memory": False,
    },
    "dolphin": {
        "name": "Hermes",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "persona_file": "dolphin.md",
        "include_memory": False,
    },
}


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AgentChatRequest(BaseModel):
    agent_id: str
    message: str
    history: Optional[List[ChatMessage]] = None


class AgentChatResponse(BaseModel):
    agent_id: str
    agent_name: str
    content: str
    model: str


def _load_persona(agent_id: str) -> str:
    config = AGENT_CONFIG.get(agent_id)
    if not config:
        return ""
    persona_path = PERSONAS_DIR / config["persona_file"]
    if persona_path.exists():
        return persona_path.read_text(encoding="utf-8")
    return f"You are the {agent_id} agent."


def _load_memory() -> str:
    memory_path = VAULT_DIR / "MEMORY.md"
    if memory_path.exists():
        return memory_path.read_text(encoding="utf-8")
    return ""


@router.post("/agent", response_model=AgentChatResponse)
async def agent_chat(req: AgentChatRequest):
    config = AGENT_CONFIG.get(req.agent_id)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent: {req.agent_id}. Available: {list(AGENT_CONFIG.keys())}",
        )

    # 시스템 프롬프트 구성
    system = _load_persona(req.agent_id)
    if config.get("include_memory"):
        memory = _load_memory()
        if memory:
            system += f"\n\n<current_memory>\n{memory}\n</current_memory>"

    # 대화 히스토리 구성
    messages = []
    if req.history:
        for msg in req.history:
            if msg.role in {"user", "assistant"}:
                messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    provider = config["provider"]
    model = config["model"]

    try:
        if provider == "anthropic":
            content = await _call_anthropic(system, messages, model)
        elif provider == "openai":
            content = await _call_openai(system, messages, model)
        elif provider == "gemini":
            content = await _call_gemini(system, messages, model)
        else:
            raise HTTPException(status_code=500, detail=f"Unknown provider: {provider}")

        # 에이스 응답에서 memory_update 태그 처리
        memory_updated = False
        if req.agent_id == "ace":
            clean_content, updates = extract_memory_updates(content)
            if updates:
                memory_updated = apply_memory_updates(updates)
                content = clean_content  # 사용자에게는 태그 제거된 응답만 전달
                if not content and memory_updated:
                    content = "요청한 내용을 MEMORY.md에 기록했어."

        return AgentChatResponse(
            agent_id=req.agent_id,
            agent_name=config["name"],
            content=content,
            model=model,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent call failed: {str(exc)}") from exc


async def _call_anthropic(system: str, messages: list, model: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    client = AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=messages,
    )
    parts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    content = "\n".join(parts).strip()
    if not content:
        raise HTTPException(status_code=502, detail="Anthropic response did not contain text")
    return content


async def _call_openai(system: str, messages: list, model: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    client = AsyncOpenAI(api_key=api_key)
    all_messages = [{"role": "system", "content": system}] + messages
    response = await client.chat.completions.create(
        model=model, messages=all_messages, max_tokens=4096
    )
    content = response.choices[0].message.content
    if isinstance(content, list):
        merged = []
        for item in content:
            text = getattr(item, "text", None)
            if isinstance(text, str):
                merged.append(text)
        return "\n".join(merged).strip()
    return (content or "").strip()


async def _call_gemini(system: str, messages: list, model: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
    genai.configure(api_key=api_key)
    gen_model = genai.GenerativeModel(model_name=model, system_instruction=system)
    # 마지막 user 메시지만 전달 (Gemini 멀티턴은 별도 처리 필요)
    user_msg = messages[-1]["content"] if messages else ""
    response = await asyncio.to_thread(gen_model.generate_content, user_msg)
    return (response.text or "").strip()


@router.get("/agents")
async def list_agents():
    """프론트엔드가 사용 가능한 에이전트 목록을 가져올 때"""
    return {
        agent_id: {
            "name": config["name"],
            "model": config["model"],
        }
        for agent_id, config in AGENT_CONFIG.items()
    }
