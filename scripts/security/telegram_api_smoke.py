#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[2]
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def load_internal_token() -> str:
    token = os.getenv("LLM_PROXY_INTERNAL_TOKEN", "").strip()
    if token:
        return token

    env_path = ROOT_DIR / ".env.local"
    if not env_path.exists():
        return ""

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "LLM_PROXY_INTERNAL_TOKEN":
            return value.strip().strip('"').strip("'")
    return ""


def api_request(method: str, path: str, token: str, body: dict | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"x-internal-token": token}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=payload, headers=headers, method=method)

    try:
        with urlopen(req, timeout=20) as resp:
            status = int(resp.status)
            text = resp.read().decode("utf-8")
    except HTTPError as exc:
        status = int(exc.code)
        text = exc.read().decode("utf-8")
    except URLError as exc:
        raise RuntimeError(f"request failed: {path} ({exc})") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid json response: {path} status={status} body={text[:240]}") from exc
    return status, data


def assert_true(cond: bool, message: str, payload: dict | None = None) -> None:
    if cond:
        return
    print(f"[FAIL] {message}")
    if payload is not None:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(1)


def main() -> int:
    token = load_internal_token()
    assert_true(bool(token), "LLM_PROXY_INTERNAL_TOKEN not found (env or .env.local)")

    print("[1/5] GET /api/telegram/health")
    status, data = api_request("GET", "/api/telegram/health", token)
    assert_true(status == 200, f"health status={status}", data)
    assert_true(
        {"status", "code", "message", "retryable", "telegram"}.issubset(data.keys()),
        "health schema mismatch",
        data,
    )
    print("[OK] health")

    print("[2/5] POST /api/telegram/poll (all enabled agents)")
    status, data = api_request("POST", "/api/telegram/poll", token, {"limit": 3})
    assert_true(status == 200, f"poll status={status}", data)
    assert_true(
        data.get("status") == "ok" and isinstance(data.get("results"), list),
        "poll response mismatch",
        data,
    )
    for item in data.get("results", []):
        assert_true(
            {"agent_id", "scanned_updates", "processed_commands", "sent_replies", "skipped_untrusted", "retryable"}.issubset(item.keys()),
            "poll result schema mismatch",
            data,
        )
    print("[OK] poll ok")

    print("[3/5] POST /api/telegram/poll (invalid agent)")
    status, data = api_request(
        "POST",
        "/api/telegram/poll",
        token,
        {"agent_id": "invalid-agent", "limit": 3},
    )
    assert_true(status == 400, f"poll invalid status={status}", data)
    detail = data.get("detail", {})
    assert_true(
        isinstance(detail, dict) and detail.get("status") == "error" and {"code", "message", "retryable"}.issubset(detail.keys()),
        "poll invalid error schema mismatch",
        data,
    )
    print("[OK] poll invalid agent error format")

    print("[4/5] POST /api/telegram/send (invalid chat_id)")
    status, data = api_request(
        "POST",
        "/api/telegram/send",
        token,
        {"agent_id": "ace", "chat_id": "invalid", "message": "smoke"},
    )
    assert_true(status in {400, 403, 429, 502}, f"send invalid status={status}", data)
    detail = data.get("detail", {})
    assert_true(
        isinstance(detail, dict) and detail.get("status") == "error" and {"code", "message", "retryable"}.issubset(detail.keys()),
        "send invalid error schema mismatch",
        data,
    )
    print("[OK] send invalid error format")

    print("[5/5] POST /api/telegram/poller/start")
    status, data = api_request("POST", "/api/telegram/poller/start", token, {})
    if status == 200:
        assert_true(
            {"status", "code", "message", "retryable", "started", "telegram"}.issubset(data.keys()),
            "poller start success schema mismatch",
            data,
        )
        print("[OK] poller start success format")
    elif status == 503:
        detail = data.get("detail", {})
        assert_true(
            isinstance(detail, dict) and detail.get("status") == "error" and detail.get("code") == "TELEGRAM_NOT_CONFIGURED",
            "poller start error schema mismatch",
            data,
        )
        print("[OK] poller start not-configured format")
    else:
        assert_true(False, f"poller start status={status}", data)

    print("[DONE] telegram api smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
