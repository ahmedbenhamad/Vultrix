"""Security headers, CSRF protection, and request-ID logging."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

_access_logger = logging.getLogger("strix.access")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach an X-Request-ID to every response and emit a structured access log."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = rid
        _access_logger.info(
            'rid=%s %s %s -> %s %.1fms', rid, request.method, request.url.path,
            response.status_code, elapsed_ms,
        )
        return response

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Credential-establishing endpoints: exempt from CSRF (the credentials/refresh
# token are themselves the proof, and a stale cookie shouldn't block re-login).
_CSRF_EXEMPT_SUFFIXES = ("/auth/login", "/auth/refresh")


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF: for cookie-authenticated unsafe requests, the
    ``X-CSRF-Token`` header must equal the (non-httpOnly) CSRF cookie. Requests
    authenticated purely by an ``Authorization: Bearer`` header (no auth cookie)
    are exempt — bearer tokens aren't sent automatically by browsers.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in _UNSAFE_METHODS and not request.url.path.endswith(_CSRF_EXEMPT_SUFFIXES):
            has_cookie_auth = (
                settings.ACCESS_COOKIE_NAME in request.cookies
                or settings.REFRESH_COOKIE_NAME in request.cookies
            )
            if has_cookie_auth:
                cookie_csrf = request.cookies.get(settings.CSRF_COOKIE_NAME)
                header_csrf = request.headers.get(settings.CSRF_HEADER_NAME)
                if not cookie_csrf or cookie_csrf != header_csrf:
                    return JSONResponse(
                        status_code=403, content={"detail": "CSRF token missing or invalid"}
                    )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        # API is JSON-only; a strict CSP is safe (docs UI relaxes it per-route if needed).
        h.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        if settings.is_production:
            h.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
            )
        return response
