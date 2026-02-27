from __future__ import annotations

import json
from pathlib import Path
from typing import Final

CATALOG_PATH: Final[Path] = Path(__file__).resolve().parent / "personas" / "agent_catalog.json"

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

DEFAULT_AGENTS: Final[dict[str, dict[str, object]]] = {
    "ace": {
        "name": "Morpheus",
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


def _load_catalog() -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    if not CATALOG_PATH.exists():
        return dict(DEFAULT_AGENT_ALIASES), dict(DEFAULT_AGENTS)
    try:
        payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        aliases = payload.get("aliases")
        agents = payload.get("agents")
        if not isinstance(aliases, dict) or not isinstance(agents, dict):
            return dict(DEFAULT_AGENT_ALIASES), dict(DEFAULT_AGENTS)
        return dict(aliases), dict(agents)
    except Exception:
        return dict(DEFAULT_AGENT_ALIASES), dict(DEFAULT_AGENTS)


AGENT_ALIASES_DATA, AGENTS_DATA = _load_catalog()
AGENT_ALIASES: Final[dict[str, str]] = AGENT_ALIASES_DATA
AGENTS: Final[dict[str, dict[str, object]]] = AGENTS_DATA
VALID_AGENT_IDS: Final[set[str]] = set(AGENTS.keys())


def normalize_agent_id(raw: str) -> str:
    value = (raw or "").strip()
    lowered = value.lower()
    return AGENT_ALIASES.get(lowered) or AGENT_ALIASES.get(value) or value


def canonical_agent_id(raw: str, fallback: str) -> str:
    normalized = normalize_agent_id(raw)
    return normalized if normalized in VALID_AGENT_IDS else fallback
