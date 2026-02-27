from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

DB_PATH_DEFAULT = "/app/shared_data/agent_comms/history/agent_history.sqlite3"
DEFAULT_TARGET_AGENTS = {"ace"}
DEFAULT_MAX_CONTEXT_MESSAGES = 20
DEFAULT_MAX_STORED_MESSAGES = 300
DEFAULT_MAX_MESSAGE_CHARS = 4000

_DB_LOCK = Lock()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _db_path() -> Path:
    raw = os.getenv("AGENT_HISTORY_DB_PATH", DB_PATH_DEFAULT).strip() or DB_PATH_DEFAULT
    if raw.startswith("/app/shared/agent_comms"):
        raw = raw.replace("/app/shared/agent_comms", "/app/shared_data/agent_comms", 1)
    return Path(raw)


def _connect() -> sqlite3.Connection:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema() -> None:
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_messages (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_key TEXT NOT NULL,
                  agent_id TEXT NOT NULL,
                  role TEXT NOT NULL,
                  content TEXT NOT NULL,
                  channel TEXT NOT NULL,
                  created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_agent_messages_user_agent_id
                ON agent_messages (user_key, agent_id, id)
                """
            )
            conn.commit()
        finally:
            conn.close()


def _max_context_messages() -> int:
    raw = os.getenv("AGENT_HISTORY_MAX_CONTEXT_MESSAGES", str(DEFAULT_MAX_CONTEXT_MESSAGES)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        parsed = DEFAULT_MAX_CONTEXT_MESSAGES
    return min(max(parsed, 2), 60)


def _max_stored_messages() -> int:
    raw = os.getenv("AGENT_HISTORY_MAX_STORED_MESSAGES", str(DEFAULT_MAX_STORED_MESSAGES)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        parsed = DEFAULT_MAX_STORED_MESSAGES
    return min(max(parsed, 50), 5000)


def _max_message_chars() -> int:
    raw = os.getenv("AGENT_HISTORY_MAX_MESSAGE_CHARS", str(DEFAULT_MAX_MESSAGE_CHARS)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        parsed = DEFAULT_MAX_MESSAGE_CHARS
    return min(max(parsed, 200), 50000)


def _trim_message(content: str) -> str:
    limit = _max_message_chars()
    normalized = (content or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip()


def _normalize_user_key(raw: str | None) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    safe = value.replace("\n", " ").replace("\r", " ")
    return safe[:120]


def _default_user_key(agent_id: str) -> str:
    env_name = f"AGENT_SHARED_HISTORY_DEFAULT_USER_{agent_id.upper()}"
    value = _normalize_user_key(os.getenv(env_name, ""))
    if value:
        return value
    if agent_id == "ace":
        return "owner"
    return ""


def resolve_user_key(agent_id: str, user_id: str | None) -> str:
    provided = _normalize_user_key(user_id)
    return provided or _default_user_key(agent_id)


def shared_history_enabled_for_agent(agent_id: str) -> bool:
    if not _as_bool(os.getenv("AGENT_SHARED_HISTORY_ENABLED", "true"), default=True):
        return False
    targets = {item.lower() for item in _split_csv(os.getenv("AGENT_SHARED_HISTORY_TARGETS", "ace"))}
    if not targets:
        targets = set(DEFAULT_TARGET_AGENTS)
    return agent_id.lower() in targets


def get_recent_messages(user_key: str, agent_id: str) -> list[dict[str, str]]:
    normalized_user_key = _normalize_user_key(user_key)
    if not normalized_user_key:
        return []

    _ensure_schema()
    limit = _max_context_messages()
    with _DB_LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT role, content
                FROM agent_messages
                WHERE user_key = ? AND agent_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (normalized_user_key, agent_id, limit),
            ).fetchall()
        finally:
            conn.close()

    ordered = list(reversed(rows))
    result: list[dict[str, str]] = []
    for row in ordered:
        role = str(row["role"]).strip()
        content = str(row["content"]).strip()
        if role in {"user", "assistant"} and content:
            result.append({"role": role, "content": content})
    return result


def append_turn(
    *,
    user_key: str,
    agent_id: str,
    user_content: str,
    assistant_content: str,
    channel: str,
) -> None:
    normalized_user_key = _normalize_user_key(user_key)
    if not normalized_user_key:
        return

    user_text = _trim_message(user_content)
    assistant_text = _trim_message(assistant_content)
    if not user_text or not assistant_text:
        return

    _ensure_schema()
    now = datetime.now(timezone.utc).isoformat()
    max_stored = _max_stored_messages()

    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO agent_messages (user_key, agent_id, role, content, channel, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (normalized_user_key, agent_id, "user", user_text, channel, now),
            )
            conn.execute(
                """
                INSERT INTO agent_messages (user_key, agent_id, role, content, channel, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (normalized_user_key, agent_id, "assistant", assistant_text, channel, now),
            )
            conn.execute(
                """
                DELETE FROM agent_messages
                WHERE id IN (
                    SELECT id
                    FROM agent_messages
                    WHERE user_key = ? AND agent_id = ?
                    ORDER BY id DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (normalized_user_key, agent_id, max_stored),
            )
            conn.commit()
        finally:
            conn.close()
