"""TOTP MFA helpers (pyotp) + one-time recovery codes."""

import secrets

import pyotp

from app.core.config import settings
from app.core.security import sha256
from app.models.user import User


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=settings.MFA_ISSUER)


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=1)


def generate_recovery_codes(n: int = 10) -> list[str]:
    # 10 human-friendly codes like "3f9a-1c7e"
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(n)]


def hash_codes(codes: list[str]) -> str:
    return ",".join(sha256(c) for c in codes)


def consume_recovery_code(user: User, code: str) -> bool:
    """If ``code`` matches an unused recovery hash, remove it and return True."""
    if not user.mfa_recovery_hashes:
        return False
    h = sha256(code.strip())
    hashes = user.mfa_recovery_hashes.split(",")
    if h in hashes:
        hashes.remove(h)
        user.mfa_recovery_hashes = ",".join(hashes)
        return True
    return False


def verify_mfa(user: User, code: str) -> bool:
    """Accept either a valid TOTP code or an unused recovery code (consumed)."""
    if verify_totp(user.mfa_secret or "", code):
        return True
    return consume_recovery_code(user, code)
