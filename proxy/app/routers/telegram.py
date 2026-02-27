from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.utils.agent_registry import AGENT_CONFIG, normalize_agent_id
from app.utils.telegram_bridge import (
    bridge_status,
    ensure_background_poller,
    poll_many,
    serialize_stats,
    send_text,
)
from app.utils.telegram_codes import (
    TELEGRAM_BAD_REQUEST,
    TELEGRAM_BRIDGE_DISABLED,
    TELEGRAM_FORBIDDEN,
    TELEGRAM_HEALTH_OK,
    TELEGRAM_INVALID_AGENT,
    TELEGRAM_NETWORK_ERROR,
    TELEGRAM_NOT_CONFIGURED,
    TELEGRAM_POLLER_STARTED,
    TELEGRAM_POLLER_STOPPED,
    TELEGRAM_POLL_OK,
    TELEGRAM_POLL_PARTIAL,
    TELEGRAM_RATE_LIMITED,
    TELEGRAM_SENT,
    TELEGRAM_SEND_FAILED,
    TELEGRAM_UNAUTHORIZED,
    TELEGRAM_UNKNOWN_ERROR,
)
from app.utils.telegram_bridge_transport import TelegramApiHttpError, TelegramApiNetworkError

router = APIRouter()


class TelegramPollRequest(BaseModel):
    agent_id: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


class TelegramSendRequest(BaseModel):
    agent_id: str
    chat_id: str
    message: str = Field(min_length=1)


class TelegramOkResponse(BaseModel):
    status: Literal["ok"] = "ok"
    code: str
    message: str
    retryable: bool


class TelegramErrorDetail(BaseModel):
    status: Literal["error"] = "error"
    code: str
    message: str
    retryable: bool
    telegram_status: int | None = None
    method: str | None = None


class TelegramErrorResponse(BaseModel):
    detail: TelegramErrorDetail


class TelegramHealthResponse(TelegramOkResponse):
    telegram: dict[str, Any]


class TelegramPollResult(BaseModel):
    agent_id: str
    scanned_updates: int
    processed_commands: int
    sent_replies: int
    skipped_untrusted: int
    last_update_id: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False


class TelegramPollResponse(TelegramOkResponse):
    results: list[TelegramPollResult]


class TelegramSendResponse(TelegramOkResponse):
    agent_id: str
    chat_id: str


class TelegramPollerStartResponse(TelegramOkResponse):
    started: bool
    telegram: dict[str, Any]


def _ok_response(
    *,
    code: str,
    message: str,
    retryable: bool = False,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "ok",
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    if extra:
        payload.update(extra)
    return payload


def _send_error_detail(
    *,
    code: str,
    message: str,
    retryable: bool,
    telegram_status: int | None = None,
    method: str | None = None,
) -> dict[str, object]:
    detail: dict[str, object] = {
        "status": "error",
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    if telegram_status is not None:
        detail["telegram_status"] = telegram_status
    if method:
        detail["method"] = method
    return detail


@router.get(
    "/telegram/health",
    response_model=TelegramHealthResponse,
)
async def telegram_health() -> TelegramHealthResponse:
    telegram = bridge_status()
    bridge_enabled = bool(telegram.get("bridge_enabled"))
    enabled_agents = list(telegram.get("enabled_agents", []))
    background_running = bool(telegram.get("background_running"))
    if not bridge_enabled:
        return _ok_response(
            code=TELEGRAM_BRIDGE_DISABLED,
            message="disabled",
            retryable=False,
            extra={"telegram": telegram},
        )
    if not enabled_agents:
        return _ok_response(
            code=TELEGRAM_NOT_CONFIGURED,
            message="no_enabled_agents",
            retryable=False,
            extra={"telegram": telegram},
        )
    if not background_running:
        return _ok_response(
            code=TELEGRAM_POLLER_STOPPED,
            message="poller_not_running",
            retryable=True,
            extra={"telegram": telegram},
        )
    return _ok_response(
        code=TELEGRAM_HEALTH_OK,
        message="ready",
        retryable=False,
        extra={"telegram": telegram},
    )


@router.post(
    "/telegram/poll",
    response_model=TelegramPollResponse,
    responses={400: {"model": TelegramErrorResponse}, 503: {"model": TelegramErrorResponse}},
)
async def telegram_poll(req: TelegramPollRequest) -> TelegramPollResponse:
    target_agents: list[str]
    if req.agent_id:
        agent_id = normalize_agent_id(req.agent_id)
        if agent_id not in AGENT_CONFIG:
            raise HTTPException(
                status_code=400,
                detail=_send_error_detail(
                    code=TELEGRAM_INVALID_AGENT,
                    message=f"unknown_agent:{req.agent_id}",
                    retryable=False,
                ),
            )
        target_agents = [agent_id]
    else:
        enabled = list(bridge_status().get("enabled_agents", []))
        if not enabled:
            raise HTTPException(
                status_code=503,
                detail=_send_error_detail(
                    code=TELEGRAM_NOT_CONFIGURED,
                    message="no_enabled_agents",
                    retryable=False,
                ),
            )
        target_agents = enabled

    stats = await poll_many(target_agents, limit=req.limit)
    serialized = serialize_stats(stats)
    has_error = any(bool(item.get("error_code")) for item in serialized)
    return _ok_response(
        code=TELEGRAM_POLL_PARTIAL if has_error else TELEGRAM_POLL_OK,
        message="partial" if has_error else "polled",
        retryable=has_error,
        extra={"results": serialized},
    )


@router.post(
    "/telegram/send",
    response_model=TelegramSendResponse,
    responses={
        400: {"model": TelegramErrorResponse},
        403: {"model": TelegramErrorResponse},
        429: {"model": TelegramErrorResponse},
        500: {"model": TelegramErrorResponse},
        502: {"model": TelegramErrorResponse},
        503: {"model": TelegramErrorResponse},
    },
)
async def telegram_send(req: TelegramSendRequest) -> TelegramSendResponse:
    agent_id = normalize_agent_id(req.agent_id)
    try:
        await send_text(agent_id, req.chat_id, req.message)
    except TelegramApiHttpError as exc:
        status_code = 502
        retryable = True
        code = TELEGRAM_SEND_FAILED
        if exc.status_code == 400:
            status_code = 400
            retryable = False
            code = TELEGRAM_BAD_REQUEST
        elif exc.status_code == 403:
            status_code = 403
            retryable = False
            code = TELEGRAM_FORBIDDEN
        elif exc.status_code == 429:
            status_code = 429
            retryable = True
            code = TELEGRAM_RATE_LIMITED
        elif exc.status_code == 401:
            status_code = 502
            retryable = False
            code = TELEGRAM_UNAUTHORIZED
        raise HTTPException(
            status_code=status_code,
            detail=_send_error_detail(
                code=code,
                message=exc.detail,
                retryable=retryable,
                telegram_status=exc.status_code,
                method=exc.method,
            ),
        ) from None
    except TelegramApiNetworkError as exc:
        raise HTTPException(
            status_code=502,
            detail=_send_error_detail(
                code=TELEGRAM_NETWORK_ERROR,
                message=exc.reason,
                retryable=True,
                method=exc.method,
            ),
        ) from None
    except RuntimeError as exc:
        message = str(exc)
        if message.startswith("Missing token for agent:"):
            raise HTTPException(
                status_code=503,
                detail=_send_error_detail(
                    code=TELEGRAM_NOT_CONFIGURED,
                    message=message,
                    retryable=False,
                ),
            ) from None
        raise HTTPException(
            status_code=500,
            detail=_send_error_detail(
                code=TELEGRAM_UNKNOWN_ERROR,
                message="unknown_error",
                retryable=True,
            ),
        ) from None
    return _ok_response(
        code=TELEGRAM_SENT,
        message="sent",
        retryable=False,
        extra={"agent_id": agent_id, "chat_id": req.chat_id},
    )


@router.post(
    "/telegram/poller/start",
    response_model=TelegramPollerStartResponse,
    responses={503: {"model": TelegramErrorResponse}},
)
async def telegram_start_poller() -> TelegramPollerStartResponse:
    started = ensure_background_poller()
    telegram = bridge_status()
    if not started:
        raise HTTPException(
            status_code=503,
            detail=_send_error_detail(
                code=TELEGRAM_NOT_CONFIGURED,
                message="no_enabled_agents",
                retryable=False,
            ),
        )
    return _ok_response(
        code=TELEGRAM_POLLER_STARTED,
        message="started",
        retryable=False,
        extra={"started": True, "telegram": telegram},
    )
