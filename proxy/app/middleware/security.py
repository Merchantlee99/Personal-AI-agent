from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _to_int(value: str, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value.strip())
    except Exception:
        return default
    return max(minimum, min(maximum, parsed))


class SecurityMiddleware(BaseHTTPMiddleware):
    """Low-friction protections for internal API usage."""

    def __init__(self, app):
        super().__init__(app)
        self.internal_token = os.getenv("LLM_PROXY_INTERNAL_TOKEN", "").strip()
        raw_bypass = os.getenv("LLM_PROXY_AUTH_BYPASS_PATHS", "")
        self.auth_bypass_paths = {
            path.strip()
            for path in raw_bypass.split(",")
            if path.strip()
        }
        self.rate_limit_enabled = _as_bool(os.getenv("LLM_PROXY_RATE_LIMIT_ENABLED", "true"), default=True)
        self.rate_limit_rpm = _to_int(os.getenv("LLM_PROXY_RATE_LIMIT_RPM", "240"), default=240, minimum=30, maximum=5000)
        self.max_body_bytes = _to_int(
            os.getenv("LLM_PROXY_MAX_BODY_BYTES", "1048576"),
            default=1_048_576,
            minimum=8_192,
            maximum=16_777_216,
        )
        self._window_seconds = 60.0
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _check_rate_limit(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            while bucket and (now - bucket[0]) > self._window_seconds:
                bucket.popleft()
            if len(bucket) >= self.rate_limit_rpm:
                return False
            bucket.append(now)
            return True

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        is_api_path = path.startswith("/api/")
        is_bypassed = path in self.auth_bypass_paths

        if is_api_path:
            content_length = request.headers.get("content-length", "").strip()
            if content_length.isdigit() and int(content_length) > self.max_body_bytes:
                return JSONResponse({"detail": "Request body too large"}, status_code=413)

            if self.internal_token and not is_bypassed:
                supplied = request.headers.get("x-internal-token", "").strip()
                if supplied != self.internal_token:
                    return JSONResponse({"detail": "Unauthorized"}, status_code=401)

            if self.rate_limit_enabled:
                client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown")
                key = f"{client_ip}:{path}"
                if not self._check_rate_limit(key):
                    return JSONResponse({"detail": "Too many requests"}, status_code=429)

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if is_api_path:
            response.headers["Cache-Control"] = "no-store"
        return response
