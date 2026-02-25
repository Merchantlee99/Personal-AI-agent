"""
에이전트 실시간 채팅 라우터.
프론트엔드 → Next.js → 이 엔드포인트 → LLM API
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.utils.agent_context import (
    append_calendar_context_if_needed,
    fetch_n8n_search,
    looks_like_search_query,
)
from app.utils.agent_registry import AGENT_CONFIG, normalize_agent_id
from app.utils.memory_writer import apply_memory_updates, extract_memory_updates
from app.utils.provider_clients import call_provider

router = APIRouter()
logger = logging.getLogger(__name__)

PERSONAS_DIR = Path("/app/personas")
VAULT_DIR = Path("/app/vault")
KST = timezone(timedelta(hours=9))

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
    persona_file = str(config.get("persona_file", ""))
    persona_path = PERSONAS_DIR / persona_file
    if persona_path.exists():
        return persona_path.read_text(encoding="utf-8")
    return f"You are the {agent_id} agent."


def _load_memory(agent_id: str) -> str:
    config = AGENT_CONFIG.get(agent_id) or {}
    memory_file = str(config.get("memory_file", "")).strip()
    if not memory_file:
        return ""
    memory_path = VAULT_DIR / memory_file
    if memory_path.exists():
        return memory_path.read_text(encoding="utf-8")
    return ""


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _build_search_fallback_message(original_message: str) -> str:
    return (
        f"{original_message}\n\n"
        "[안내] n8n 검색 호출 실패: 외부 검색 응답 오류\n"
        "- 실패 사실을 먼저 명시\n"
        "- 확인 불가 항목은 '⚠️ 확인 필요'로 표기"
    )


@router.post("/agent", response_model=AgentChatResponse)
async def agent_chat(req: AgentChatRequest):
    normalized_agent_id = normalize_agent_id(req.agent_id)
    config = AGENT_CONFIG.get(normalized_agent_id)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent: {req.agent_id}. Available: {list(AGENT_CONFIG.keys())}",
        )

    system = _load_persona(normalized_agent_id)
    if bool(config.get("include_memory")):
        memory = _load_memory(normalized_agent_id)
        if memory:
            system += f"\n\n<current_memory>\n{memory}\n</current_memory>"

    if normalized_agent_id == "owl":
        system += (
            "\n\n<obsidian_output_contract>\n"
            + OBSIDIAN_FORMAT_GUIDE.replace("YYYY-MM-DD", _today_kst())
            + "\n</obsidian_output_contract>"
        )

    user_message = await append_calendar_context_if_needed(normalized_agent_id, req.message)
    if normalized_agent_id == "dolphin" and looks_like_search_query(req.message):
        tavily_api_key = os.getenv("TAVILY_API_KEY", "").strip()
        try:
            final_text, filename = await fetch_n8n_search(req.message, tavily_api_key)
            if final_text:
                trimmed = final_text[:12000]
                user_message = (
                    f"[요청]\n{req.message}\n\n"
                    f"[n8n 웹검색 결과 | file={filename or '-'}]\n{trimmed}\n\n"
                    "[작성 지시]\n"
                    "- HOT / INSIGHT / MONITOR로 분류\n"
                    "- 각 항목에 근거 1줄, 출처 표기\n"
                    "- 불확실 정보는 '⚠️ 확인 필요' 표기\n"
                    "- 마지막에 추천 액션 3개 제시"
                )
            else:
                user_message = (
                    f"{req.message}\n\n"
                    "[안내] n8n 검색 결과가 비어 있음. 비어 있음을 명시하고 보수적으로 답변할 것."
                )
        except Exception:
            user_message = _build_search_fallback_message(req.message)

    messages: list[dict[str, str]] = []
    if req.history:
        for msg in req.history:
            if msg.role in {"user", "assistant"}:
                messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    provider = str(config.get("provider", ""))
    model = str(config.get("model", ""))

    try:
        content = await call_provider(provider, system, messages, model)

        # 에이스 응답에서 memory_update 태그 처리
        if normalized_agent_id == "ace":
            clean_content, updates = extract_memory_updates(content)
            if updates:
                memory_updated = apply_memory_updates(updates)
                content = clean_content
                if not content and memory_updated:
                    content = "요청한 내용을 MEMORY.md에 기록했어."

        return AgentChatResponse(
            agent_id=normalized_agent_id,
            agent_name=str(config.get("name", normalized_agent_id)),
            content=content,
            model=model,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Agent call failed")
        raise HTTPException(status_code=502, detail="Agent call failed")


@router.get("/agents")
async def list_agents():
    """프론트엔드가 사용 가능한 에이전트 목록을 가져올 때"""
    return {
        agent_id: {
            "name": str(config.get("name", agent_id)),
            "model": str(config.get("model", "")),
        }
        for agent_id, config in AGENT_CONFIG.items()
    }
