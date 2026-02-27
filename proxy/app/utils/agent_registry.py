from __future__ import annotations

import json
from pathlib import Path
from typing import Final

CATALOG_PATH: Final[Path] = Path("/app/personas/agent_catalog.json")

DEFAULT_AGENT_ALIASES: Final[dict[str, str]] = {
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

DEFAULT_AGENT_CONFIG: Final[dict[str, dict[str, object]]] = {
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


def _load_catalog() -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    if not CATALOG_PATH.exists():
        return dict(DEFAULT_AGENT_ALIASES), dict(DEFAULT_AGENT_CONFIG)
    try:
        payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        aliases = payload.get("aliases")
        agents = payload.get("agents")
        if not isinstance(aliases, dict) or not isinstance(agents, dict):
            return dict(DEFAULT_AGENT_ALIASES), dict(DEFAULT_AGENT_CONFIG)
        return dict(aliases), dict(agents)
    except Exception:
        return dict(DEFAULT_AGENT_ALIASES), dict(DEFAULT_AGENT_CONFIG)


AGENT_ALIASES_DATA, AGENT_CONFIG_DATA = _load_catalog()
AGENT_ALIASES: Final[dict[str, str]] = AGENT_ALIASES_DATA
AGENT_CONFIG: Final[dict[str, dict[str, object]]] = AGENT_CONFIG_DATA


def normalize_agent_id(agent_id: str) -> str:
    raw = (agent_id or "").strip()
    lowered = raw.lower()
    return AGENT_ALIASES.get(lowered) or AGENT_ALIASES.get(raw) or raw
