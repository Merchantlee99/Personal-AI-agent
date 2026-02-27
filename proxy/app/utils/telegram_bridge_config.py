from __future__ import annotations

import os

from app.utils.agent_registry import AGENT_CONFIG, normalize_agent_id

TOKEN_ENV_BY_AGENT = {
    "ace": "TELEGRAM_BOT_TOKEN_ACE",
    "owl": "TELEGRAM_BOT_TOKEN_OWL",
    "dolphin": "TELEGRAM_BOT_TOKEN_DOLPHIN",
}
ALLOW_CHAT_IDS_ENV_BY_AGENT = {
    "ace": "TELEGRAM_ALLOWED_CHAT_IDS_ACE",
    "owl": "TELEGRAM_ALLOWED_CHAT_IDS_OWL",
    "dolphin": "TELEGRAM_ALLOWED_CHAT_IDS_DOLPHIN",
}
ALLOWED_COMMANDS_ENV_BY_AGENT = {
    "ace": "TELEGRAM_ALLOWED_COMMANDS_ACE",
    "owl": "TELEGRAM_ALLOWED_COMMANDS_OWL",
    "dolphin": "TELEGRAM_ALLOWED_COMMANDS_DOLPHIN",
}
SHARED_USER_ID_ENV_BY_AGENT = {
    "ace": "TELEGRAM_SHARED_USER_ID_ACE",
    "owl": "TELEGRAM_SHARED_USER_ID_OWL",
    "dolphin": "TELEGRAM_SHARED_USER_ID_DOLPHIN",
}
DEFAULT_COMMANDS_BY_AGENT = {
    "ace": {"read", "summary", "chat"},
    "owl": {"read", "summary", "chat"},
    "dolphin": {"read", "summary", "trend", "chat"},
}
SUPPORTED_COMMANDS = {"read", "summary", "trend", "chat"}


def as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def bot_token(agent_id: str) -> str:
    env_name = TOKEN_ENV_BY_AGENT.get(agent_id, "")
    return os.getenv(env_name, "").strip() if env_name else ""


def allowed_chat_ids(agent_id: str) -> set[str]:
    env_name = ALLOW_CHAT_IDS_ENV_BY_AGENT.get(agent_id, "")
    values = split_csv(os.getenv(env_name, ""))
    return set(values)


def allowed_commands(agent_id: str) -> set[str]:
    env_name = ALLOWED_COMMANDS_ENV_BY_AGENT.get(agent_id, "")
    values = {cmd.lower() for cmd in split_csv(os.getenv(env_name, ""))}
    if not values:
        values = set(DEFAULT_COMMANDS_BY_AGENT.get(agent_id, {"read", "summary", "chat"}))
    if "summary" in values:
        values.add("chat")
    return {cmd for cmd in values if cmd in SUPPORTED_COMMANDS}


def enabled_agent_ids() -> list[str]:
    if not as_bool(os.getenv("TELEGRAM_BRIDGE_ENABLED", "false")):
        return []

    raw = os.getenv("TELEGRAM_ENABLED_AGENTS", "ace")
    normalized: list[str] = []
    for item in split_csv(raw):
        agent_id = normalize_agent_id(item)
        if agent_id in AGENT_CONFIG and agent_id not in normalized:
            normalized.append(agent_id)
    return [agent_id for agent_id in normalized if bot_token(agent_id)]


def poll_interval_seconds() -> float:
    raw = os.getenv("TELEGRAM_POLL_INTERVAL_SEC", "6").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 6.0
    return min(max(value, 2.0), 60.0)


def poll_limit() -> int:
    raw = os.getenv("TELEGRAM_MAX_UPDATES_PER_POLL", "20").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 20
    return min(max(value, 1), 100)


def conversation_user_id(agent_id: str, chat_id: str) -> str:
    env_name = SHARED_USER_ID_ENV_BY_AGENT.get(agent_id, "")
    configured = os.getenv(env_name, "").strip() if env_name else ""
    if configured:
        return configured
    if agent_id == "ace":
        return "owner"
    return f"telegram:{chat_id}"
