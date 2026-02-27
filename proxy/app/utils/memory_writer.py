"""
에이스 응답에서 <memory_update> 태그를 파싱하고
실제 MEMORY.md 파일에 내용을 추가하는 유틸리티.
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

VAULT_DIR = Path("/app/vault")
MEMORY_FILE = VAULT_DIR / "MEMORY.md"


def _quarantine_dir() -> Path:
    raw = os.getenv("MEMORY_QUARANTINE_DIR", "/app/shared_data/agent_comms/quarantine").strip()
    if raw.startswith("/app/shared/agent_comms"):
        raw = raw.replace("/app/shared/agent_comms", "/app/shared_data/agent_comms", 1)
    return Path(raw)


QUARANTINE_DIR = _quarantine_dir()

MEMORY_TAG_PATTERN = re.compile(
    r"<memory_update>\s*(.*?)\s*</memory_update>",
    re.DOTALL,
)


def extract_memory_updates(response_text: str) -> tuple[str, list[str]]:
    """
    응답 텍스트에서 <memory_update> 태그를 추출.

    Returns:
        (clean_text, updates): 태그 제거된 텍스트, 업데이트 내용 리스트
    """
    updates = MEMORY_TAG_PATTERN.findall(response_text)
    clean_text = MEMORY_TAG_PATTERN.sub("", response_text).strip()
    # 연속 줄바꿈 정리
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)
    return clean_text, updates


def apply_memory_updates(updates: list[str]) -> bool:
    """
    MEMORY.md 파일에 업데이트 내용을 추가.

    섹션 매칭 로직:
    - 업데이트에 "## 섹션명"이 있으면 해당 섹션을 찾아서 끝에 추가
    - 매칭되는 섹션이 없으면 "## 교훈 아카이브" 섹션 끝에 추가
    - MEMORY.md 자체가 없으면 새로 생성

    Returns:
        True if successful
    """
    if not updates:
        return False

    try:
        # 현재 MEMORY.md 읽기
        if MEMORY_FILE.exists():
            content = MEMORY_FILE.read_text(encoding="utf-8")
        else:
            content = "# 🐙 에이스 메모리 (Living Document)\n\n"

        for update in updates:
            update = update.strip()
            if not update:
                continue

            # 업데이트에서 섹션 헤더 추출
            section_match = re.match(r"^##\s+(.+)$", update, re.MULTILINE)

            if section_match:
                section_name = section_match.group(1).strip()
                # 해당 섹션의 내용만 추출 (헤더 제외)
                update_body = update[section_match.end():].strip()

                # MEMORY.md에서 해당 섹션 찾기
                section_pattern = re.compile(
                    rf"(## {re.escape(section_name)}.*?)(?=\n## |\Z)",
                    re.DOTALL,
                )
                match = section_pattern.search(content)

                if match:
                    # 섹션 끝에 추가
                    insert_pos = match.end()
                    content = (
                        content[:insert_pos].rstrip()
                        + "\n"
                        + update_body
                        + "\n\n"
                        + content[insert_pos:].lstrip()
                    )
                else:
                    # 섹션이 없으면 파일 끝에 섹션째로 추가
                    content = content.rstrip() + "\n\n" + update + "\n"
            else:
                # 섹션 헤더가 없으면 교훈 아카이브에 추가
                archive_pattern = re.compile(
                    r"(## 교훈 아카이브.*?)(?=\n## |\Z)",
                    re.DOTALL,
                )
                match = archive_pattern.search(content)
                if match:
                    insert_pos = match.end()
                    content = (
                        content[:insert_pos].rstrip()
                        + "\n"
                        + update
                        + "\n\n"
                        + content[insert_pos:].lstrip()
                    )
                else:
                    content = content.rstrip() + "\n\n" + update + "\n"

        # 파일 쓰기
        MEMORY_FILE.write_text(content, encoding="utf-8")
        logger.info("MEMORY.md updated with %d entries", len(updates))
        return True

    except Exception:
        logger.exception("Failed to update MEMORY.md")
        return False


def quarantine_memory_updates(
    updates: list[str],
    *,
    reason: str,
    source_message: str,
    agent_id: str = "ace",
) -> str | None:
    """Store memory updates in quarantine for manual approval."""
    if not updates:
        return None

    try:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        filename = f"memory_update_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.json"
        path = QUARANTINE_DIR / filename
        payload = {
            "id": uuid.uuid4().hex,
            "agent_id": agent_id,
            "status": "pending_approval",
            "reason": reason,
            "created_at": now.isoformat(),
            "source_message": source_message,
            "updates": updates,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Memory update quarantined: %s", path)
        return str(path)
    except Exception:
        logger.exception("Failed to quarantine memory updates")
        return None
