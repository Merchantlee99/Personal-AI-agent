from __future__ import annotations

import os
from json import JSONDecodeError
from typing import Any

import httpx


class TelegramPollConflictError(RuntimeError):
    """Raised when Telegram getUpdates has another active consumer."""


class TelegramApiHttpError(RuntimeError):
    """Raised when Telegram API returns HTTP/application errors."""

    def __init__(self, method: str, status_code: int, detail: str):
        self.method = method
        self.status_code = int(status_code)
        self.detail = detail
        super().__init__(
            f"telegram api http error ({method}): status={self.status_code} body={detail}"
        )


class TelegramApiNetworkError(RuntimeError):
    """Raised when Telegram API call fails at the network layer."""

    def __init__(self, method: str, reason: str):
        self.method = method
        self.reason = reason
        super().__init__(f"telegram api network error ({method}): {reason}")


def telegram_api_url(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


async def telegram_api_post(token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    timeout = float(os.getenv("TELEGRAM_HTTP_TIMEOUT_SEC", "30"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(telegram_api_url(token, method), json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if method == "getUpdates" and status == 409:
                raise TelegramPollConflictError("telegram polling conflict (getUpdates 409)") from None
            body = (exc.response.text or "").strip().replace("\n", " ")
            body = body[:240]
            raise TelegramApiHttpError(method, status, body) from None
        except httpx.HTTPError as exc:
            raise TelegramApiNetworkError(method, exc.__class__.__name__) from None

    try:
        data = response.json()
    except JSONDecodeError:
        body = (response.text or "").strip().replace("\n", " ")
        body = body[:240]
        raise TelegramApiHttpError(method, response.status_code, f"invalid_json:{body}") from None

    if not data.get("ok", False):
        status = int(data.get("error_code") or 502)
        detail = str(data.get("description") or "telegram_api_error")
        raise TelegramApiHttpError(method, status, detail[:240])
    return data


def split_telegram_message(text: str, max_length: int = 3500) -> list[str]:
    body = text.strip()
    if not body:
        return [""]
    if len(body) <= max_length:
        return [body]

    chunks: list[str] = []
    remaining = body
    while len(remaining) > max_length:
        split_at = remaining.rfind("\n", 0, max_length)
        if split_at <= 0:
            split_at = max_length
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks
