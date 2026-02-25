from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

KST = timezone(timedelta(hours=9))
TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API_ROOT = "https://www.googleapis.com/calendar/v3"


@dataclass
class CalendarConfig:
    enabled: bool
    client_id: str
    client_secret: str
    refresh_token: str
    calendar_id: str
    timezone_name: str
    default_max_results: int
    mask_sensitive: bool


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_calendar_config() -> CalendarConfig:
    enabled = _as_bool(os.getenv("GOOGLE_CALENDAR_READONLY_ENABLED", ""), default=False)
    default_max_results_raw = os.getenv("GOOGLE_CALENDAR_MAX_RESULTS", "10").strip()
    try:
        default_max_results = int(default_max_results_raw)
    except ValueError:
        default_max_results = 10
    default_max_results = max(1, min(default_max_results, 50))

    return CalendarConfig(
        enabled=enabled,
        client_id=os.getenv("GOOGLE_CALENDAR_CLIENT_ID", "").strip(),
        client_secret=os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET", "").strip(),
        refresh_token=os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN", "").strip(),
        calendar_id=os.getenv("GOOGLE_CALENDAR_ID", "primary").strip() or "primary",
        timezone_name=os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Asia/Seoul").strip() or "Asia/Seoul",
        default_max_results=default_max_results,
        mask_sensitive=_as_bool(os.getenv("GOOGLE_CALENDAR_MASK_SENSITIVE", "true"), default=True),
    )


def calendar_is_configured(config: CalendarConfig | None = None) -> bool:
    cfg = config or load_calendar_config()
    return bool(cfg.client_id and cfg.client_secret and cfg.refresh_token)


def calendar_is_enabled(config: CalendarConfig | None = None) -> bool:
    cfg = config or load_calendar_config()
    return cfg.enabled


def _mask_sensitive_text(text: str) -> str:
    if not text:
        return text

    masked = text
    # Emails
    masked = re.sub(
        r"\b([A-Za-z0-9._%+-]{2})[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b",
        r"\1***@\2",
        masked,
    )
    # URLs
    masked = re.sub(r"https?://[^\s)]+", "[link-masked]", masked)
    # Phone numbers (very loose)
    masked = re.sub(r"\b(?:\+?\d[\d -]{7,}\d)\b", "[phone-masked]", masked)
    return masked


def _mask_event(event: dict[str, Any], mask_sensitive: bool) -> dict[str, Any]:
    if not mask_sensitive:
        return event

    masked = dict(event)
    for field in ("summary", "description", "location", "htmlLink"):
        value = masked.get(field)
        if isinstance(value, str):
            masked[field] = _mask_sensitive_text(value)

    attendees = masked.get("attendees")
    if isinstance(attendees, list):
        normalized_attendees = []
        for attendee in attendees:
            if not isinstance(attendee, dict):
                continue
            item = dict(attendee)
            email = item.get("email")
            if isinstance(email, str):
                item["email"] = _mask_sensitive_text(email)
            normalized_attendees.append(item)
        masked["attendees"] = normalized_attendees
    return masked


async def _fetch_access_token(config: CalendarConfig) -> str:
    payload = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "refresh_token": config.refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(TOKEN_URL, data=payload)
        response.raise_for_status()
        data = response.json()
    token = str(data.get("access_token", "")).strip()
    if not token:
        raise ValueError("Google OAuth token response missing access_token")
    return token


async def list_calendar_events(
    *,
    time_min: datetime,
    time_max: datetime,
    max_results: int | None = None,
    config: CalendarConfig | None = None,
) -> list[dict[str, Any]]:
    cfg = config or load_calendar_config()
    if not cfg.enabled:
        raise ValueError("Google Calendar readonly integration is disabled")
    if not calendar_is_configured(cfg):
        raise ValueError("Google Calendar readonly integration is not fully configured")

    access_token = await _fetch_access_token(cfg)
    calendar_id_encoded = quote(cfg.calendar_id, safe="")
    url = f"{GOOGLE_CALENDAR_API_ROOT}/calendars/{calendar_id_encoded}/events"
    limit = max_results if max_results is not None else cfg.default_max_results
    limit = max(1, min(limit, 50))

    params = {
        "timeMin": time_min.isoformat(),
        "timeMax": time_max.isoformat(),
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": str(limit),
        "timeZone": cfg.timezone_name,
    }
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()

    items = payload.get("items", [])
    if not isinstance(items, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        event = {
            "id": item.get("id"),
            "status": item.get("status"),
            "summary": item.get("summary") or "(제목 없음)",
            "description": item.get("description") or "",
            "location": item.get("location") or "",
            "htmlLink": item.get("htmlLink") or "",
            "start": item.get("start") or {},
            "end": item.get("end") or {},
            "attendees": item.get("attendees") or [],
        }
        normalized.append(_mask_event(event, cfg.mask_sensitive))
    return normalized


def _format_event_time(start_obj: dict[str, Any], end_obj: dict[str, Any]) -> str:
    start_date = start_obj.get("date")
    if isinstance(start_date, str):
        return f"{start_date} (all-day)"

    start_date_time = str(start_obj.get("dateTime", "")).strip()
    end_date_time = str(end_obj.get("dateTime", "")).strip()
    if start_date_time:
        if end_date_time:
            return f"{start_date_time} ~ {end_date_time}"
        return start_date_time
    return "(시간 미정)"


def events_to_context(events: list[dict[str, Any]]) -> str:
    if not events:
        return "해당 기간에 일정이 없습니다."

    lines: list[str] = []
    for index, event in enumerate(events, start=1):
        summary = str(event.get("summary", "(제목 없음)"))
        location = str(event.get("location", "")).strip()
        when = _format_event_time(
            event.get("start", {}) if isinstance(event.get("start"), dict) else {},
            event.get("end", {}) if isinstance(event.get("end"), dict) else {},
        )
        line = f"{index}. {summary} | {when}"
        if location:
            line += f" | 장소: {location}"
        lines.append(line)
    return "\n".join(lines)


def default_window_next_days(days: int = 7) -> tuple[datetime, datetime]:
    now = datetime.now(KST)
    end = now + timedelta(days=max(days, 1))
    return now, end
