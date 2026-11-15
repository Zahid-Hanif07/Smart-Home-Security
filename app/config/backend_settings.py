import os
from typing import List, Optional
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    """Configuration settings for FastAPI Backend & Supabase Integration."""

    SUPABASE_URL: str = Field(default="https://demo-project.supabase.co")
    SUPABASE_ANON_KEY: str = Field(default="dummy_anon_key")

    @field_validator("SUPABASE_URL", mode="before")
    @classmethod
    def sanitize_supabase_url(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip().rstrip("/")
            for suffix in ["/rest/v1", "/v1", "/rest"]:
                if v.endswith(suffix):
                    v = v[:-len(suffix)].rstrip("/")
        return v
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="")
    SUPABASE_JWT_SECRET: str = Field(default="")
    # Dedicated key for short-lived desktop device-session JWTs. Never reuse
    # Supabase credentials for this purpose; leave empty to fail closed.
    DEVICE_SESSION_SIGNING_SECRET: str = Field(default="")
    # One-time paired desktop credential, kept server-side in the desktop's
    # environment configuration and never included in settings repr output.
    DEVICE_CREDENTIAL: Optional[SecretStr] = Field(default=None, repr=False)

    FASTAPI_HOST: str = Field(default="0.0.0.0")
    FASTAPI_PORT: int = Field(default=8085)
    API_BASE_URL: str = Field(default="http://127.0.0.1:8085")
    SECURITY_HOME_ID: Optional[str] = Field(default=None)
    SUPABASE_ACCESS_TOKEN: Optional[str] = Field(default=None)
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8085", "http://127.0.0.1:8085"]
    )
    STREAM_ENABLED: bool = Field(default=True)
    STREAM_JPEG_QUALITY: int = Field(default=80)
    STREAM_FPS: int = Field(default=15)
    API_RATE_LIMIT_PER_MINUTE: int = Field(default=1200, ge=60, le=10000)

    # Environment identifier.  Controls safety guards.
    # Accepted values: "development" (default), "staging", "production".
    # WARNING: setting ENVIRONMENT=production disables the in-memory fallback
    # even if TEST_ISOLATED_MODE=1 is present — see is_memory_fallback_enabled().
    ENVIRONMENT: str = Field(default="development")

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def normalise_environment(cls, v: str) -> str:
        cleaned = str(v).strip().lower()
        allowed = {"development", "staging", "production"}
        if cleaned not in allowed:
            raise ValueError(
                f"ENVIRONMENT must be one of {sorted(allowed)}; got '{v}'. "
                "Set ENVIRONMENT=development for local development and tests."
            )
        return cleaned


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def restrict_wildcard_origins(cls, value):
        """Remove wildcard CORS because credentialed requests are enabled."""
        if isinstance(value, str):
            # pydantic-settings parses JSON list values before validation in
            # normal configurations; retain support for comma-separated lists.
            value = [part.strip() for part in value.split(",") if part.strip()]
        if not isinstance(value, (list, tuple)):
            return value
        origins = [str(origin).strip() for origin in value if str(origin).strip() != "*"]
        return origins or ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8085", "http://127.0.0.1:8085"]


settings = BackendSettings()
