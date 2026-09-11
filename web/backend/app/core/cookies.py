"""Helpers to set/clear the auth cookie trio (access, refresh, CSRF)."""

from fastapi import Response

from app.core.config import settings

_ACCESS_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
_REFRESH_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


def _common() -> dict:
    kw = {
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/",
    }
    if settings.COOKIE_DOMAIN:
        kw["domain"] = settings.COOKIE_DOMAIN
    return kw


def set_auth_cookies(response: Response, access: str, refresh: str, csrf: str) -> None:
    common = _common()
    # httpOnly tokens: not readable by JS (XSS-hardened)
    response.set_cookie(settings.ACCESS_COOKIE_NAME, access, max_age=_ACCESS_MAX_AGE, httponly=True, **common)
    response.set_cookie(settings.REFRESH_COOKIE_NAME, refresh, max_age=_REFRESH_MAX_AGE, httponly=True, **common)
    # CSRF cookie MUST be readable by JS so the SPA can echo it in a header (double-submit)
    response.set_cookie(settings.CSRF_COOKIE_NAME, csrf, max_age=_REFRESH_MAX_AGE, httponly=False, **common)


def clear_auth_cookies(response: Response) -> None:
    common = {"path": "/"}
    if settings.COOKIE_DOMAIN:
        common["domain"] = settings.COOKIE_DOMAIN
    for name in (settings.ACCESS_COOKIE_NAME, settings.REFRESH_COOKIE_NAME, settings.CSRF_COOKIE_NAME):
        response.delete_cookie(name, **common)
