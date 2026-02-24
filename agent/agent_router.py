"""
에이전트 라우터: 입력 데이터의 유형에 따라 적절한 에이전트로 분배.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from agent.llm_client import call_llm, web_search
except ImportError:
    from llm_client import call_llm, web_search

PERSONAS_DIR = Path("/app/agent/personas")
VAULT_DIR = Path("/app/shared_data/obsidian_vault")
COMMS_DIR = Path("/app/shared_data/agent_comms")
VERIFIED_DIR = Path("/app/shared_data/verified_inbox")
LOGS_DIR = Path("/app/shared_data/logs")
KST = timezone(timedelta(hours=9))
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

OBSIDIAN_FORMAT_GUIDE = """
반드시 아래 형식의 옵시디언 마크다운으로만 답변해.
- YAML frontmatter 포함
- 파일명 제안은 kebab-case
- 본문은 한국어, 과한 장식/강조(**) 금지

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
AGENTS = {
    "ace": {
        "provider": "anthropic",
        "model": "claude-opus-4-6",
        "persona_file": "ace.md",
        "memory_file": "MEMORY.md",
        "include_memory": True,
    },
    "owl": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "persona_file": "owl.md",
        "memory_file": "MEMORY_CLIO.md",
        "include_memory": True,
    },
    "dolphin": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "persona_file": "dolphin.md",
        "memory_file": "MEMORY_HERMES.md",
        "include_memory": True,
    },
}


def load_persona(agent_id: str) -> str:
    """에이전트 페르소나 시스템 프롬프트를 로드"""
    persona_path = PERSONAS_DIR / AGENTS[agent_id]["persona_file"]
    if persona_path.exists():
        return persona_path.read_text(encoding="utf-8")
    return f"You are the {agent_id} agent."


def load_memory(agent_id: str) -> str:
    """에이전트별 메모리 파일 로드"""
    memory_file = AGENTS.get(agent_id, {}).get("memory_file")
    if not memory_file:
        return ""
    memory_path = VAULT_DIR / memory_file
    if memory_path.exists():
        return memory_path.read_text(encoding="utf-8")
    return ""


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def normalize_agent_id(agent_id: str) -> str:
    raw = (agent_id or "").strip()
    lowered = raw.lower()
    return AGENT_ALIASES.get(lowered) or AGENT_ALIASES.get(raw) or raw


async def _prepare_prompt(agent_id: str, prompt: str) -> str:
    if agent_id == "owl":
        return f"{prompt.strip()}\n\n[Clio 출력 규칙]\n{OBSIDIAN_FORMAT_GUIDE.replace('YYYY-MM-DD', _today_kst())}"

    if agent_id == "dolphin":
        try:
            search_result = await web_search(prompt)
            final_text = str(search_result.get("final_text", "")).strip()
            filename = str(search_result.get("filename", "")).strip()
            if final_text:
                log_event("DOLPHIN_SEARCH_OK", f"filename={filename or '-'}")
                return (
                    f"[사용자 요청]\n{prompt.strip()}\n\n"
                    f"[n8n 웹검색 결과]\n{final_text}\n\n"
                    f"[작성 지시]\n"
                    f"- 결과를 HOT/INSIGHT/MONITOR로 분류\n"
                    f"- 각 항목에 근거 요약 1줄과 출처 표시\n"
                    f"- 마지막에 PM 실행 액션 3개 제시\n"
                    f"- 검증 불충분 항목은 '⚠️ 확인 필요'로 표기"
                )
            log_event("DOLPHIN_SEARCH_EMPTY", "search returned empty final_text")
        except Exception as exc:
            log_event("DOLPHIN_SEARCH_FAIL", str(exc))
        return (
            f"{prompt.strip()}\n\n"
            f"[작성 지시]\n"
            f"- n8n 검색 결과 수신 실패 상태를 명시\n"
            f"- 가능한 범위에서 HOT/INSIGHT/MONITOR로 정리\n"
            f"- 불확실 정보는 '⚠️ 확인 필요'로 표기"
        )

    return prompt


async def route_to_agent(
    agent_id: str,
    prompt: str,
    include_memory: bool = False,
) -> str:
    """지정된 에이전트로 프롬프트를 라우팅"""
    agent_id = normalize_agent_id(agent_id)
    agent = AGENTS.get(agent_id)
    if not agent:
        raise ValueError(f"Unknown agent: {agent_id}")

    system = load_persona(agent_id)

    should_include_memory = bool(agent.get("include_memory")) or include_memory
    if should_include_memory:
        memory = load_memory(agent_id)
        if memory:
            system += f"\n\n<current_memory>\n{memory}\n</current_memory>"

    enriched_prompt = await _prepare_prompt(agent_id, prompt)

    result = await call_llm(
        prompt=enriched_prompt,
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
    from_agent = normalize_agent_id(from_agent)
    to_agent = normalize_agent_id(to_agent)
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
