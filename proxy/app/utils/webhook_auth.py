from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class WebhookAuthResult:
    ok: bool
    message: str


def verify_n8n_signed_webhook(
    payload: dict,
    *,
    timestamp_header: str,
    signature_header: str,
) -> WebhookAuthResult:
    """
    Verify n8n webhook with HMAC SHA-256 + timestamp.

    Signature format:
      - raw hex: <hex>
      - prefixed: sha256=<hex>
    Canonical base string:
      "<unix_timestamp>.<canonical_json_payload>"
    """

    secret = os.getenv("N8N_WEBHOOK_SIGNING_SECRET", "").strip()
    required_default = bool(secret)
    required = _as_bool(
        os.getenv("N8N_WEBHOOK_SIGNATURE_REQUIRED"),
        default=required_default,
    )
    if not required:
        return WebhookAuthResult(ok=True, message="signature check disabled")
    if not secret:
        return WebhookAuthResult(ok=False, message="signing secret not configured")

    ts_raw = (timestamp_header or "").strip()
    sig_raw = (signature_header or "").strip()
    if not ts_raw or not sig_raw:
        return WebhookAuthResult(ok=False, message="missing signature headers")

    if sig_raw.startswith("sha256="):
        sig_raw = sig_raw.split("=", 1)[1].strip()

    try:
        ts = int(ts_raw)
    except ValueError:
        return WebhookAuthResult(ok=False, message="invalid timestamp header")

    max_skew = int(os.getenv("N8N_WEBHOOK_MAX_SKEW_SEC", "300").strip() or "300")
    now = int(time.time())
    if abs(now - ts) > max_skew:
        return WebhookAuthResult(ok=False, message="timestamp skew exceeded")

    canonical = _canonical_json(payload)
    base = f"{ts}.{canonical}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig_raw):
        return WebhookAuthResult(ok=False, message="signature mismatch")

    return WebhookAuthResult(ok=True, message="ok")
