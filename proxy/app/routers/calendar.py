from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.utils.calendar_reader import (
    calendar_is_configured,
    calendar_is_enabled,
    default_window_next_days,
    list_calendar_events,
    load_calendar_config,
)

router = APIRouter()
KST = timezone(timedelta(hours=9))
logger = logging.getLogger(__name__)


class CalendarEventsRequest(BaseModel):
    time_min: Optional[datetime] = None
    time_max: Optional[datetime] = None
    max_results: int = Field(default=10, ge=1, le=50)


class CalendarEventsResponse(BaseModel):
    enabled: bool
    configured: bool
    calendar_id: str
    timezone: str
    time_min: str
    time_max: str
    count: int
    events: list[dict[str, Any]]


@router.get("/calendar/health")
async def calendar_health():
    cfg = load_calendar_config()
    return {
        "enabled": calendar_is_enabled(cfg),
        "configured": calendar_is_configured(cfg),
        "calendar_id": cfg.calendar_id,
        "timezone": cfg.timezone_name,
        "readonly_mode": True,
        "mask_sensitive": cfg.mask_sensitive,
    }


@router.post("/calendar/events", response_model=CalendarEventsResponse)
async def calendar_events(req: CalendarEventsRequest):
    cfg = load_calendar_config()
    enabled = calendar_is_enabled(cfg)
    configured = calendar_is_configured(cfg)

    if not enabled:
        raise HTTPException(status_code=400, detail="Google Calendar readonly integration is disabled")
    if not configured:
        raise HTTPException(status_code=400, detail="Google Calendar readonly integration is not fully configured")

    start, end = req.time_min, req.time_max
    if not start or not end:
        default_start, default_end = default_window_next_days(days=7)
        start = start or default_start
        end = end or default_end

    try:
        events = await list_calendar_events(
            time_min=start,
            time_max=end,
            max_results=req.max_results,
            config=cfg,
        )
    except Exception as exc:
        logger.exception("Calendar fetch failed")
        raise HTTPException(status_code=502, detail="Calendar fetch failed") from exc

    return CalendarEventsResponse(
        enabled=enabled,
        configured=configured,
        calendar_id=cfg.calendar_id,
        timezone=cfg.timezone_name,
        time_min=start.astimezone(KST).isoformat(),
        time_max=end.astimezone(KST).isoformat(),
        count=len(events),
        events=events,
    )
