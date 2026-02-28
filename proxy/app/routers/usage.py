from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.utils.usage_store import usage_summary_payload

router = APIRouter()


class ProviderUsageSummary(BaseModel):
    provider: str
    request_count: int
    error_count: int
    error_rate: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    settled_cost_usd: Optional[float] = None


class UsageSummaryResponse(BaseModel):
    day_kst: str
    generated_at: str
    settled_cost_note: str
    providers: List[ProviderUsageSummary]


@router.get("/usage/summary", response_model=UsageSummaryResponse)
async def usage_summary(day_kst: str | None = Query(default=None, min_length=10, max_length=10)):
    payload = usage_summary_payload(day_kst)
    return UsageSummaryResponse.model_validate(payload)

