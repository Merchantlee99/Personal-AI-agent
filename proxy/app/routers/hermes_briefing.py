from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from app.utils.webhook_auth import verify_n8n_signed_webhook

router = APIRouter()

KST = timezone(timedelta(hours=9))
USER_INBOX_DIR = Path("/app/shared_data/agent_comms/inbox/user")


class HermesDailyBriefingRequest(BaseModel):
    title: str = "Hermes Daily Trend Briefing"
    source: str = "n8n_schedule"
    period_start: str = ""
    period_end: str = ""
    translation_required_count: int = 0
    source_stats: dict[str, int] = Field(default_factory=dict)
    digest_text: str
    articles: list[dict[str, Any]] = Field(default_factory=list)


class HermesDailyBriefingResponse(BaseModel):
    status: str
    notification_id: str | None = None
    queued_path: str | None = None
    message: str | None = None


def _now_kst() -> datetime:
    return datetime.now(KST)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _extract_anthropic_text(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []):
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n".join(parts).strip()


def _build_fallback_content(req: HermesDailyBriefingRequest) -> str:
    header = [
        "## Hermes 자동 브리핑 (Fallback)",
        "",
        f"- 기준 구간: {req.period_start or '-'} ~ {req.period_end or '-'}",
        f"- 수집 소스: {req.source}",
        "",
    ]
    return ("\n".join(header) + req.digest_text).strip()


async def _render_hermes_briefing(req: HermesDailyBriefingRequest) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return _build_fallback_content(req)

    articles = req.articles[:20]
    article_lines: list[str] = []
    for index, item in enumerate(articles, start=1):
        title = str(item.get("title", "")).strip()
        source = str(item.get("source", "")).strip()
        link = str(item.get("url", "")).strip()
        published = str(item.get("published_at", "")).strip()
        summary = str(item.get("summary", "")).strip()
        locale = str(item.get("locale", "")).strip()
        category = str(item.get("category", "")).strip()
        needs_translation = bool(item.get("needs_translation", False))
        article_lines.append(f"{index}. {title}")
        if source:
            article_lines.append(f"   - source: {source}")
        if category:
            article_lines.append(f"   - category: {category}")
        if locale:
            article_lines.append(f"   - locale: {locale}")
        if needs_translation:
            article_lines.append("   - translation_required: true")
        if published:
            article_lines.append(f"   - published_at: {published}")
        if link:
            article_lines.append(f"   - url: {link}")
        if summary:
            article_lines.append(f"   - summary: {summary}")

    prompt = (
        "아래는 지난 24시간 기술/트렌드 수집 결과다.\n"
        "사용자(상인)에게 전달할 Hermes 아침 브리핑을 한국어로 작성해라.\n"
        "출력 규칙:\n"
        "- 첫 줄은 한 문장 결론\n"
        "- 섹션은 정확히 HOT / INSIGHT / MONITOR 순서\n"
        "- 각 항목은 최대 1~2줄, 근거 URL 포함\n"
        "- locale=global 또는 translation_required=true 항목은 반드시 한국어로 번역 요약하고, 원문 핵심 키워드를 괄호로 병기\n"
        "- 한국어 출처(locale=ko)는 불필요한 재번역 없이 핵심만 요약\n"
        "- 마지막에 '오늘의 액션 3개'를 번호 목록으로 작성\n"
        "- 과장 금지, 불확실 항목은 '⚠️ 확인 필요' 표기\n\n"
        f"[기간]\n{req.period_start or '-'} ~ {req.period_end or '-'}\n\n"
        f"[번역 필요 건수]\n{req.translation_required_count}\n\n"
        f"[소스별 건수]\n{json.dumps(req.source_stats, ensure_ascii=False)}\n\n"
        f"[원문 Digest]\n{req.digest_text}\n\n"
        f"[기사 목록]\n{chr(10).join(article_lines) if article_lines else '-'}"
    )

    try:
        client = AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1800,
            temperature=0.4,
            system="You are Hermes, a PM-oriented trend tracker. Be concise, factual, actionable.",
            messages=[{"role": "user", "content": prompt}],
        )
        content = _extract_anthropic_text(response)
        return content or _build_fallback_content(req)
    except Exception:
        return _build_fallback_content(req)


@router.post("/hermes/daily-briefing", response_model=HermesDailyBriefingResponse)
async def enqueue_hermes_daily_briefing(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    auth_result = verify_n8n_signed_webhook(
        payload,
        timestamp_header=request.headers.get("x-webhook-timestamp", ""),
        signature_header=request.headers.get("x-webhook-signature", ""),
    )
    if not auth_result.ok:
        raise HTTPException(status_code=401, detail=f"Webhook auth failed: {auth_result.message}")

    try:
        req = HermesDailyBriefingRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())

    if len(req.articles) == 0:
        return HermesDailyBriefingResponse(
            status="skipped",
            message="No RSS articles in the last 24h. Briefing not queued.",
        )

    content = await _render_hermes_briefing(req)
    now = _now_kst()
    notification_id = str(uuid.uuid4())
    filename = f"hermes_user_{now.strftime('%Y%m%d_%H%M%S')}_{notification_id[:8]}.json"
    output_path = USER_INBOX_DIR / filename

    payload = {
        "id": notification_id,
        "agent_id": "dolphin",
        "agent_name": "Hermes",
        "type": "daily_briefing",
        "source": req.source,
        "title": req.title,
        "content": content,
        "period_start": req.period_start,
        "period_end": req.period_end,
        "created_at": now.isoformat(timespec="seconds"),
    }
    _write_json_atomic(output_path, payload)

    return HermesDailyBriefingResponse(
        status="queued",
        notification_id=notification_id,
        queued_path=str(output_path),
    )
