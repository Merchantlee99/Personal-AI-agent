from __future__ import annotations

from typing import Final

AGENT_ALIASES: Final[dict[str, str]] = {
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

AGENT_CONFIG: Final[dict[str, dict[str, object]]] = {
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


def normalize_agent_id(agent_id: str) -> str:
    raw = (agent_id or "").strip()
    lowered = raw.lower()
    return AGENT_ALIASES.get(lowered) or AGENT_ALIASES.get(raw) or raw
