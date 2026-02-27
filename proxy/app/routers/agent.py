"""에이전트 실시간 채팅 라우터."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.utils.agent_engine import run_agent_turn
from app.utils.agent_registry import AGENT_CONFIG

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AgentChatRequest(BaseModel):
    agent_id: str
    message: str
    history: Optional[List[ChatMessage]] = None
    user_id: Optional[str] = None
    channel: Optional[str] = None


class AgentChatResponse(BaseModel):
    agent_id: str
    agent_name: str
    content: str
    model: str


@router.post("/agent", response_model=AgentChatResponse)
async def agent_chat(req: AgentChatRequest):
    try:
        normalized_history = [
            {"role": msg.role, "content": msg.content}
            for msg in (req.history or [])
        ]
        result = await run_agent_turn(
            req.agent_id,
            req.message,
            history=normalized_history,
            user_id=req.user_id,
            channel=req.channel,
            store_user_message=req.message,
        )
        return AgentChatResponse(
            agent_id=result.agent_id,
            agent_name=result.agent_name,
            content=result.content,
            model=result.model,
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
