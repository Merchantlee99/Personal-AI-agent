from __future__ import annotations

import json
from pathlib import Path

STATE_DIR = Path("/app/shared_data/agent_comms/telegram/state")


def state_path(agent_id: str) -> Path:
    return STATE_DIR / f"{agent_id}.json"


def load_offset(agent_id: str) -> int:
    path = state_path(agent_id)
    if not path.exists():
        return 0
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        return int(parsed.get("offset", 0))
    except Exception:
        return 0


def save_offset(agent_id: str, offset: int) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = state_path(agent_id)
    payload = {"offset": int(offset)}
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)
