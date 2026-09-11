"""Rate limiting via slowapi, keyed by client IP (honours X-Forwarded-For)."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _key(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_key, headers_enabled=True)
