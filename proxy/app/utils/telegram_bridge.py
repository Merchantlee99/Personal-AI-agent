from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any

from app.utils.agent_engine import run_agent_turn
from app.utils.agent_registry import AGENT_CONFIG
from app.utils.telegram_bridge_commands import (
    build_agent_prompt,
    build_help_text,
    parse_command,
)
from app.utils.telegram_bridge_config import (
    allowed_chat_ids,
    allowed_commands,
    as_bool,
    bot_token,
    conversation_user_id,
    enabled_agent_ids,
    poll_interval_seconds,
    poll_limit,
)
from app.utils.telegram_codes import (
    TELEGRAM_NOT_CONFIGURED,
    TELEGRAM_POLL_CONFLICT,
    TELEGRAM_POLL_FAILED,
)
from app.utils.telegram_bridge_state import load_offset, save_offset
from app.utils.telegram_bridge_transport import (
    TelegramPollConflictError,
    split_telegram_message,
    telegram_api_post,
)

logger = logging.getLogger(__name__)

_poller_task: asyncio.Task[None] | None = None
_poll_locks: dict[str, asyncio.Lock] = {}


@dataclass(frozen=True)
class PollStats:
    agent_id: str
    scanned_updates: int
    processed_commands: int
    sent_replies: int
    skipped_untrusted: int
    last_update_id: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False


async def send_text(agent_id: str, chat_id: str, text: str) -> None:
    token = bot_token(agent_id)
    if not token:
        raise RuntimeError(f"Missing token for agent: {agent_id}")
    for chunk in split_telegram_message(text):
        await telegram_api_post(
            token,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": chunk or "(empty)",
                "disable_web_page_preview": True,
            },
        )


def _poll_lock(agent_id: str) -> asyncio.Lock:
    lock = _poll_locks.get(agent_id)
    if lock is None:
        lock = asyncio.Lock()
        _poll_locks[agent_id] = lock
    return lock


async def poll_once(agent_id: str, *, limit: int | None = None) -> PollStats:
    token = bot_token(agent_id)
    if not token:
        return PollStats(
            agent_id=agent_id,
            scanned_updates=0,
            processed_commands=0,
            sent_replies=0,
            skipped_untrusted=0,
            error_code=TELEGRAM_NOT_CONFIGURED,
            error_message="missing_bot_token",
            retryable=False,
        )

    allowed_chat_ids_set = allowed_chat_ids(agent_id)
    if not allowed_chat_ids_set:
        logger.warning("Telegram polling skipped for %s: empty allowlist", agent_id)
        return PollStats(
            agent_id=agent_id,
            scanned_updates=0,
            processed_commands=0,
            sent_replies=0,
            skipped_untrusted=0,
            error_code=TELEGRAM_NOT_CONFIGURED,
            error_message="empty_allowlist",
            retryable=False,
        )

    allowed_commands_set = allowed_commands(agent_id)
    update_limit = limit if isinstance(limit, int) and limit > 0 else poll_limit()

    async with _poll_lock(agent_id):
        offset = load_offset(agent_id)
        try:
            data = await telegram_api_post(
                token,
                "getUpdates",
                {
                    "offset": offset,
                    "limit": update_limit,
                    "timeout": 0,
                    "allowed_updates": ["message"],
                },
            )
        except TelegramPollConflictError:
            logger.warning(
                "Telegram polling conflict (409) for %s; skipping this cycle",
                agent_id,
            )
            return PollStats(
                agent_id=agent_id,
                scanned_updates=0,
                processed_commands=0,
                sent_replies=0,
                skipped_untrusted=0,
                error_code=TELEGRAM_POLL_CONFLICT,
                error_message="getUpdates_409_conflict",
                retryable=True,
            )

        updates = data.get("result", []) or []
        scanned_updates = len(updates)
        processed_commands = 0
        sent_replies = 0
        skipped_untrusted = 0
        max_update_id = None

        for update in updates:
            update_id = int(update.get("update_id", 0))
            max_update_id = update_id if max_update_id is None else max(max_update_id, update_id)

            message = update.get("message") or {}
            text = str(message.get("text", "")).strip()
            chat = message.get("chat") or {}
            chat_id = str(chat.get("id", "")).strip()

            if not text or not chat_id:
                continue
            if chat_id not in allowed_chat_ids_set:
                skipped_untrusted += 1
                continue

            parsed = parse_command(text)
            if not parsed:
                await send_text(agent_id, chat_id, build_help_text(agent_id))
                sent_replies += 1
                continue

            command, argument = parsed
            if command not in allowed_commands_set:
                await send_text(
                    agent_id,
                    chat_id,
                    f"허용되지 않은 명령: /{command}\n{build_help_text(agent_id)}",
                )
                sent_replies += 1
                continue
            if not argument:
                await send_text(
                    agent_id,
                    chat_id,
                    f"/{command} 명령의 입력이 비어 있어요.\n예시: /{command} 오늘 회의 요약해줘",
                )
                sent_replies += 1
                continue

            processed_commands += 1
            prompt = build_agent_prompt(command, argument)
            try:
                result = await run_agent_turn(
                    agent_id,
                    prompt,
                    user_id=conversation_user_id(agent_id, chat_id),
                    channel="telegram",
                    store_user_message=text,
                )
                await send_text(agent_id, chat_id, result.content)
                sent_replies += 1
            except Exception:
                logger.exception("Telegram command execution failed: agent=%s command=%s", agent_id, command)
                await send_text(
                    agent_id,
                    chat_id,
                    "요청 처리 중 오류가 발생했어요. 잠시 후 다시 시도해 주세요.",
                    )
                sent_replies += 1

        if max_update_id is not None:
            save_offset(agent_id, max_update_id + 1)

    return PollStats(
        agent_id=agent_id,
        scanned_updates=scanned_updates,
        processed_commands=processed_commands,
        sent_replies=sent_replies,
        skipped_untrusted=skipped_untrusted,
        last_update_id=max_update_id,
    )


async def poll_many(agent_ids: list[str], *, limit: int | None = None) -> list[PollStats]:
    stats: list[PollStats] = []
    for agent_id in agent_ids:
        try:
            stats.append(await poll_once(agent_id, limit=limit))
        except Exception:
            logger.exception("Telegram poll failed for agent=%s", agent_id)
            stats.append(
                PollStats(
                    agent_id=agent_id,
                    scanned_updates=0,
                    processed_commands=0,
                    sent_replies=0,
                    skipped_untrusted=0,
                    error_code=TELEGRAM_POLL_FAILED,
                    error_message="internal_error",
                    retryable=True,
                )
            )
    return stats


async def _poll_forever() -> None:
    interval = poll_interval_seconds()
    logger.info("Telegram bridge poller started: interval=%ss", interval)
    while True:
        try:
            for agent_id in enabled_agent_ids():
                try:
                    await poll_once(agent_id)
                except Exception:
                    logger.exception("Telegram polling error: agent=%s", agent_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Telegram poll loop iteration failed")
        await asyncio.sleep(interval)


def ensure_background_poller() -> bool:
    global _poller_task
    if not enabled_agent_ids():
        return False

    if _poller_task is None or _poller_task.done():
        loop = asyncio.get_running_loop()
        _poller_task = loop.create_task(_poll_forever(), name="telegram-bridge-poller")
    return True


async def stop_background_poller() -> None:
    global _poller_task
    if _poller_task is None:
        return
    _poller_task.cancel()
    try:
        await _poller_task
    except asyncio.CancelledError:
        pass
    finally:
        _poller_task = None


def bridge_status() -> dict[str, Any]:
    enabled_agents = enabled_agent_ids()
    configured: list[dict[str, Any]] = []
    for agent_id in AGENT_CONFIG.keys():
        configured.append(
            {
                "agent_id": agent_id,
                "agent_name": str(AGENT_CONFIG[agent_id].get("name", agent_id)),
                "token_configured": bool(bot_token(agent_id)),
                "allow_chat_ids_count": len(allowed_chat_ids(agent_id)),
                "allowed_commands": sorted(allowed_commands(agent_id)),
                "polling_enabled": agent_id in enabled_agents,
            }
        )
    return {
        "bridge_enabled": as_bool(os.getenv("TELEGRAM_BRIDGE_ENABLED", "false")),
        "poll_interval_sec": poll_interval_seconds(),
        "enabled_agents": enabled_agents,
        "agents": configured,
        "background_running": bool(_poller_task and not _poller_task.done()),
    }


def serialize_stats(stats: list[PollStats]) -> list[dict[str, Any]]:
    return [asdict(item) for item in stats]
