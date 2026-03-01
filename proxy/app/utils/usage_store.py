from __future__ import annotations

import sqlite3
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

DB_PATH_DEFAULT = "/app/shared_data/agent_comms/history/usage.sqlite3"
KST = timezone(timedelta(hours=9))
_DB_LOCK = Lock()

PRICE_PER_MILLION_BY_MODEL: dict[str, dict[str, float]] = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "gemini-2.5-pro": {"input": 3.5, "output": 10.5},
}

PRICE_PER_MILLION_BY_PROVIDER: dict[str, dict[str, float]] = {
    "anthropic": {"input": 3.0, "output": 15.0},
    "openai": {"input": 5.0, "output": 15.0},
    "gemini": {"input": 3.5, "output": 10.5},
}


def _db_path() -> Path:
    raw = os.getenv("AGENT_USAGE_DB_PATH", DB_PATH_DEFAULT).strip() or DB_PATH_DEFAULT
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
                CREATE TABLE IF NOT EXISTS llm_usage_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  created_at TEXT NOT NULL,
                  day_kst TEXT NOT NULL,
                  agent_id TEXT NOT NULL,
                  provider TEXT NOT NULL,
                  model TEXT NOT NULL,
                  success INTEGER NOT NULL,
                  input_tokens INTEGER NOT NULL DEFAULT 0,
                  output_tokens INTEGER NOT NULL DEFAULT 0,
                  total_tokens INTEGER NOT NULL DEFAULT 0,
                  estimated_cost_usd REAL NOT NULL DEFAULT 0,
                  settled_cost_usd REAL,
                  error_code TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_llm_usage_events_day_provider
                ON llm_usage_events (day_kst, provider)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_llm_usage_events_day_agent
                ON llm_usage_events (day_kst, agent_id)
                """
            )
            conn.commit()
        finally:
            conn.close()


def _safe_int(value: int | None) -> int:
    if value is None:
        return 0
    return value if value > 0 else 0


def estimate_cost_usd(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICE_PER_MILLION_BY_MODEL.get(model) or PRICE_PER_MILLION_BY_PROVIDER.get(provider) or {
        "input": 0.0,
        "output": 0.0,
    }
    estimated = (input_tokens / 1_000_000) * float(pricing["input"]) + (
        output_tokens / 1_000_000
    ) * float(pricing["output"])
    return round(max(estimated, 0.0), 6)


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def record_usage_event(
    *,
    agent_id: str,
    provider: str,
    model: str,
    success: bool,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    settled_cost_usd: float | None = None,
    error_code: str = "",
) -> None:
    _ensure_schema()

    clean_input = _safe_int(input_tokens)
    clean_output = _safe_int(output_tokens)
    clean_total = _safe_int(total_tokens) or (clean_input + clean_output)
    estimated = estimate_cost_usd(provider, model, clean_input, clean_output) if success else 0.0

    now = datetime.now(timezone.utc).isoformat()
    day_kst = _today_kst()

    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO llm_usage_events (
                  created_at,
                  day_kst,
                  agent_id,
                  provider,
                  model,
                  success,
                  input_tokens,
                  output_tokens,
                  total_tokens,
                  estimated_cost_usd,
                  settled_cost_usd,
                  error_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    day_kst,
                    agent_id,
                    provider,
                    model,
                    1 if success else 0,
                    clean_input,
                    clean_output,
                    clean_total,
                    estimated,
                    settled_cost_usd,
                    (error_code or "").strip()[:80],
                ),
            )
            conn.commit()
        finally:
            conn.close()


def daily_usage_summary(day_kst: str | None = None) -> list[dict[str, object]]:
    _ensure_schema()
    target_day = (day_kst or "").strip() or _today_kst()
    with _DB_LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT
                  provider,
                  COUNT(*) AS request_count,
                  SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS error_count,
                  SUM(input_tokens) AS input_tokens,
                  SUM(output_tokens) AS output_tokens,
                  SUM(total_tokens) AS total_tokens,
                  SUM(estimated_cost_usd) AS estimated_cost_usd,
                  CASE
                    WHEN SUM(CASE WHEN settled_cost_usd IS NOT NULL THEN 1 ELSE 0 END) > 0
                    THEN SUM(COALESCE(settled_cost_usd, 0))
                    ELSE NULL
                  END AS settled_cost_usd
                FROM llm_usage_events
                WHERE day_kst = ?
                GROUP BY provider
                ORDER BY provider ASC
                """,
                (target_day,),
            ).fetchall()
        finally:
            conn.close()

    result: list[dict[str, object]] = []
    for row in rows:
        request_count = int(row["request_count"] or 0)
        error_count = int(row["error_count"] or 0)
        error_rate = (error_count / request_count * 100) if request_count > 0 else 0.0
        settled = row["settled_cost_usd"]
        result.append(
            {
                "provider": str(row["provider"] or "").strip().lower(),
                "request_count": request_count,
                "error_count": error_count,
                "error_rate": round(error_rate, 2),
                "input_tokens": int(row["input_tokens"] or 0),
                "output_tokens": int(row["output_tokens"] or 0),
                "total_tokens": int(row["total_tokens"] or 0),
                "estimated_cost_usd": round(float(row["estimated_cost_usd"] or 0.0), 6),
                "settled_cost_usd": None if settled is None else round(float(settled), 6),
            }
        )
    return result


def usage_summary_payload(day_kst: str | None = None) -> dict[str, object]:
    target_day = (day_kst or "").strip() or _today_kst()
    return {
        "day_kst": target_day,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "settled_cost_note": "정산 비용은 provider 청구 API 연동 전까지 null입니다.",
        "providers": daily_usage_summary(target_day),
    }
