from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # App
    APP_NAME: str = "Strix Console"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    # Comma-separated in env; use the `cors_origins` property for the parsed list.
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = "sqlite+pysqlite:///./strix_console.db"

    # Redis / job queue (Phase 0)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "dev-insecure-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # Cookie auth (Phase 1). In production set COOKIE_SECURE=true (HTTPS only).
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"  # lax | strict | none
    COOKIE_DOMAIN: str = ""
    ACCESS_COOKIE_NAME: str = "strix_access"
    REFRESH_COOKIE_NAME: str = "strix_refresh"
    CSRF_COOKIE_NAME: str = "strix_csrf"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # Brute-force protection (Phase 1)
    LOGIN_RATELIMIT: str = "10/minute"
    MAX_FAILED_LOGINS: int = 5
    LOCKOUT_MINUTES: int = 15

    # MFA (Phase 1)
    MFA_ISSUER: str = "Strix Console"
    # Roles for which TOTP MFA is mandatory (comma-separated).
    MFA_REQUIRED_ROLES: str = "admin,manager"

    # First admin
    FIRST_ADMIN_EMAIL: str = "admin@strix.local"
    FIRST_ADMIN_PASSWORD: str = "ChangeMe123!"
    FIRST_ADMIN_NAME: str = "Administrator"

    # Strix engine
    STRIX_REPO_PATH: str = ""
    STRIX_IMAGE: str = "strix-sandbox:0.7.2"
    # Command used to launch a scan (shlex-split). Runs with cwd=STRIX_REPO_PATH.
    # Examples: "strix", "poetry run strix", "python -m strix.interface.main"
    STRIX_LAUNCH_CMD: str = "strix"
    # LLM the Strix engine uses (passed through to the scan subprocess if set).
    STRIX_LLM: str = ""
    # Nominal scan duration (seconds) used only for the progress ramp.
    STRIX_EXPECTED_DURATION: int = 900
    # Max assessments executing concurrently; the rest queue.
    STRIX_MAX_CONCURRENT: int = 3
    # Force the simulated engine even if a repo path is set (useful for demos/CI).
    STRIX_FORCE_SIMULATION: bool = False

    # Alerting: POST a message to this webhook when a finding at/above
    # ALERT_MIN_SEVERITY is discovered. Slack-format if the URL is a Slack hook.
    ALERT_WEBHOOK_URL: str = ""
    ALERT_MIN_SEVERITY: str = "high"  # critical | high | medium | low | info

    # Assistant / RAG
    RAG_BASE_URL: str = "http://localhost:8000"
    ASSISTANT_LLM: str = "openrouter/anthropic/claude-sonnet-5"
    LLM_API_KEY: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @property
    def mfa_required_roles(self) -> set[str]:
        return {r.strip() for r in self.MFA_REQUIRED_ROLES.split(",") if r.strip()}

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
