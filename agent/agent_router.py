"""
에이전트 라우터: 입력 데이터의 유형에 따라 적절한 에이전트로 분배.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

try:
    from agent.llm_client import call_llm
except ImportError:
    from llm_client import call_llm

PERSONAS_DIR = Path("/app/agent/personas")
VAULT_DIR = Path("/app/shared_data/obsidian_vault")
COMMS_DIR = Path("/app/shared_data/agent_comms")
VERIFIED_DIR = Path("/app/shared_data/verified_inbox")
LOGS_DIR = Path("/app/shared_data/logs")

# 에이전트 설정
AGENTS = {
    "ace": {
        "provider": "anthropic",
        "model": "claude-opus-4-6",
        "persona_file": "ace.md",
    },
    "owl": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "persona_file": "owl.md",
    },
    "dolphin": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "persona_file": "dolphin.md",
    },
}


def load_persona(agent_id: str) -> str:
    """에이전트 페르소나 시스템 프롬프트를 로드"""
    persona_path = PERSONAS_DIR / AGENTS[agent_id]["persona_file"]
    if persona_path.exists():
        return persona_path.read_text(encoding="utf-8")
    return f"You are the {agent_id} agent."


def load_memory() -> str:
    """에이스용 MEMORY.md 로드"""
    memory_path = VAULT_DIR / "MEMORY.md"
    if memory_path.exists():
        return memory_path.read_text(encoding="utf-8")
    return ""


async def route_to_agent(
    agent_id: str,
    prompt: str,
    include_memory: bool = False,
) -> str:
    """지정된 에이전트로 프롬프트를 라우팅"""
    agent = AGENTS.get(agent_id)
    if not agent:
        raise ValueError(f"Unknown agent: {agent_id}")

    system = load_persona(agent_id)

    # 에이스는 항상 MEMORY.md를 컨텍스트에 포함
    if agent_id == "ace" or include_memory:
        memory = load_memory()
        if memory:
            system += f"\n\n<current_memory>\n{memory}\n</current_memory>"

    result = await call_llm(
        prompt=prompt,
        provider=agent["provider"],
        model=agent["model"],
        system=system,
    )
    return result


async def agent_communicate(
    from_agent: str,
    to_agent: str,
    message_type: str,
    content: str,
) -> None:
    """에이전트 간 메시지 전달"""
    COMMS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    msg = {
        "from": from_agent,
        "to": to_agent,
        "type": message_type,
        "timestamp": timestamp,
        "content": content,
    }
    filename = f"{to_agent}_{timestamp}_{message_type}.json"
    (COMMS_DIR / filename).write_text(
        json.dumps(msg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def log_event(event_type: str, details: str) -> None:
    """시스템 로그 기록"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{event_type}] {details}\n"
    log_file = LOGS_DIR / f"system_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)
