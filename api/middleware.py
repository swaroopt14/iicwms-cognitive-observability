"""
IICWMS Production Middleware
==============================
Request lifecycle middleware for production-grade API:

1. RequestIDMiddleware   — Assigns unique request ID to every request
2. TimingMiddleware      — Measures and logs request latency
3. SecurityMiddleware    — Adds security headers (OWASP best practices)
4. ErrorHandlerMiddleware — Catches unhandled exceptions, returns structured errors
5. RateLimitMiddleware   — Simple in-memory rate limiter per IP
"""

import time
import uuid
import logging
import traceback
from collections import defaultdict
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger("chronos.middleware")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. REQUEST ID — Traceability for every request
# ═══════════════════════════════════════════════════════════════════════════════

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique X-Request-ID to every request.
    If the client sends one, we use it. Otherwise, we generate one.
    This is essential for distributed tracing and log correlation.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TIMING — Performance visibility
# ═══════════════════════════════════════════════════════════════════════════════

class TimingMiddleware(BaseHTTPMiddleware):
    """
    Measures request duration and adds X-Response-Time header.
    Logs slow requests (>500ms) as warnings.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"

        request_id = getattr(request.state, "request_id", "???")
        path = request.url.path
        method = request.method

        if duration_ms > 500:
            logger.warning(
                f"[{request_id}] SLOW {method} {path} → {response.status_code} in {duration_ms:.0f}ms"
            )
        else:
            logger.info(
                f"[{request_id}] {method} {path} → {response.status_code} in {duration_ms:.0f}ms"
            )

        return response


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SECURITY HEADERS — OWASP baseline
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to every response (OWASP baseline):
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security (HSTS)
    - Cache-Control for API responses
    - Referrer-Policy
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

        return response


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ERROR HANDLER — No raw stack traces in production
# ═══════════════════════════════════════════════════════════════════════════════

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Catches unhandled exceptions and returns a structured JSON error.
    In production, stack traces are logged but never exposed to the client.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(
                f"[{request_id}] Unhandled exception on {request.method} {request.url.path}: "
                f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred. The team has been notified.",
                    "request_id": request_id,
                },
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. RATE LIMITER — Simple sliding-window per IP
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory rate limiter using sliding window per client IP.
    Returns 429 Too Many Requests when limit is exceeded.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old entries
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > cutoff
        ]

        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Limit: {self.max_requests} per {self.window_seconds}s",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)
