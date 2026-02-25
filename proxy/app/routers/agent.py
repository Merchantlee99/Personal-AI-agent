"""
에이전트 실시간 채팅 라우터.
프론트엔드 → Next.js → 이 엔드포인트 → LLM API
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import google.generativeai as genai
import httpx
from anthropic import AsyncAnthropic
from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.utils.memory_writer import apply_memory_updates, extract_memory_updates

router = APIRouter()

PERSONAS_DIR = Path("/app/personas")
VAULT_DIR = Path("/app/vault")
KST = timezone(timedelta(hours=9))
DEFAULT_LOCAL_WEBHOOK = "http://n8n:5678/webhook/hermes-trend"
N8N_WEBHOOK_URL_INTERNAL = os.getenv("N8N_WEBHOOK_URL_INTERNAL", "").strip()
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "").strip()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
AGENT_ALIASES = {
    "ace": "ace",
    "에이스": "ace",
    "morpheus": "ace",
    "모르피어스": "ace",
    "owl": "owl",
    "clio": "owl",
    "클리오": "owl",
    "dolphin": "dolphin",
    "hermes": "dolphin",
    "헤르메스": "dolphin",
}


def _resolve_n8n_webhook_url() -> str:
    return N8N_WEBHOOK_URL_INTERNAL or N8N_WEBHOOK_URL or DEFAULT_LOCAL_WEBHOOK

OBSIDIAN_FORMAT_GUIDE = """
반드시 아래 형식의 옵시디언 마크다운으로만 답변해.
- YAML frontmatter 필수
- 파일명은 kebab-case 제안
- 본문은 한국어
- 과한 장식/강조(**) 금지

템플릿:
---
tags: [topic]
source: user_request
created: YYYY-MM-DD
status: processed
related: [[관련노트]]
---
# 제목
## 핵심 요약 (3줄)
## 상세 내용
## 핵심 질문 (NotebookLM용)
- Q1:
- Q2:
## 인사이트
## 관련 노트 연결
"""

# 에이전트 설정
AGENT_CONFIG = {
    "ace": {
        "name": "Morpheus",
        "provider": "anthropic",
        "model": "claude-opus-4-6",
        "persona_file": "ace.md",
        "include_memory": True,
        "memory_file": "MEMORY.md",
    },
    "owl": {
        "name": "Clio",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "persona_file": "owl.md",
        "include_memory": True,
        "memory_file": "MEMORY_CLIO.md",
    },
    "dolphin": {
        "name": "Hermes",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "persona_file": "dolphin.md",
        "include_memory": True,
        "memory_file": "MEMORY_HERMES.md",
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


def _normalize_agent_id(agent_id: str) -> str:
    raw = (agent_id or "").strip()
    lowered = raw.lower()
    return AGENT_ALIASES.get(lowered) or AGENT_ALIASES.get(raw) or raw


def _load_persona(agent_id: str) -> str:
    config = AGENT_CONFIG.get(agent_id)
    if not config:
        return ""
    persona_path = PERSONAS_DIR / config["persona_file"]
    if persona_path.exists():
        return persona_path.read_text(encoding="utf-8")
    return f"You are the {agent_id} agent."


def _load_memory(agent_id: str) -> str:
    config = AGENT_CONFIG.get(agent_id) or {}
    memory_file = config.get("memory_file", "")
    if not memory_file:
        return ""
    memory_path = VAULT_DIR / memory_file
    if memory_path.exists():
        return memory_path.read_text(encoding="utf-8")
    return ""


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


async def _fetch_n8n_search(query: str) -> tuple[str, str]:
    webhook_url = _resolve_n8n_webhook_url()

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            webhook_url,
            json={
                "message": query,
                "source": "nanoclaw",
                "agentId": "dolphin",
                "tavily_api_key": TAVILY_API_KEY,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if isinstance(data, list):
        data = data[0] if data else {}

    final_text = str(data.get("final_text", "")).strip()
    filename = str(data.get("filename", "")).strip()
    return final_text, filename


@router.post("/agent", response_model=AgentChatResponse)
async def agent_chat(req: AgentChatRequest):
    normalized_agent_id = _normalize_agent_id(req.agent_id)
    config = AGENT_CONFIG.get(normalized_agent_id)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent: {req.agent_id}. Available: {list(AGENT_CONFIG.keys())}",
        )

    # 시스템 프롬프트 구성
    system = _load_persona(normalized_agent_id)
    if config.get("include_memory"):
        memory = _load_memory(normalized_agent_id)
        if memory:
            system += f"\n\n<current_memory>\n{memory}\n</current_memory>"

    if normalized_agent_id == "owl":
        system += (
            "\n\n<obsidian_output_contract>\n"
            + OBSIDIAN_FORMAT_GUIDE.replace("YYYY-MM-DD", _today_kst())
            + "\n</obsidian_output_contract>"
        )

    user_message = req.message
    if normalized_agent_id == "dolphin":
        try:
            final_text, filename = await _fetch_n8n_search(req.message)
            if final_text:
                trimmed = final_text[:12000]
                user_message = (
                    f"[요청]\n{req.message}\n\n"
                    f"[n8n 웹검색 결과 | file={filename or '-'}]\n{trimmed}\n\n"
                    f"[작성 지시]\n"
                    f"- HOT / INSIGHT / MONITOR로 분류\n"
                    f"- 각 항목에 근거 1줄, 출처 표기\n"
                    f"- 불확실 정보는 '⚠️ 확인 필요' 표기\n"
                    f"- 마지막에 추천 액션 3개 제시"
                )
            else:
                user_message = (
                    f"{req.message}\n\n"
                    f"[안내] n8n 검색 결과가 비어 있음. 비어 있음을 명시하고 보수적으로 답변할 것."
                )
        except Exception as exc:
            user_message = (
                f"{req.message}\n\n"
                f"[안내] n8n 검색 호출 실패: {str(exc)}\n"
                f"- 실패 사실을 먼저 명시\n"
                f"- 확인 불가 항목은 '⚠️ 확인 필요'로 표기"
            )

    # 대화 히스토리 구성
    messages = []
    if req.history:
        for msg in req.history:
            if msg.role in {"user", "assistant"}:
                messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

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
        if normalized_agent_id == "ace":
            clean_content, updates = extract_memory_updates(content)
            if updates:
                memory_updated = apply_memory_updates(updates)
                content = clean_content  # 사용자에게는 태그 제거된 응답만 전달
                if not content and memory_updated:
                    content = "요청한 내용을 MEMORY.md에 기록했어."

        return AgentChatResponse(
            agent_id=normalized_agent_id,
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
