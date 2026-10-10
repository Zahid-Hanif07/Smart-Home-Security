import os
from typing import List, Optional
from pydantic import Field, field_validator
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
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="dummy_service_role_key")
    SUPABASE_JWT_SECRET: str = Field(default="demo_jwt_secret_key_for_testing_123456789")

    FASTAPI_HOST: str = Field(default="0.0.0.0")
    FASTAPI_PORT: int = Field(default=8085)
    API_BASE_URL: str = Field(default="http://127.0.0.1:8085")
    SECURITY_HOME_ID: Optional[str] = Field(default=None)
    SUPABASE_ACCESS_TOKEN: Optional[str] = Field(default=None)
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8085", "http://127.0.0.1:8085", "*"]
    )
    STREAM_ENABLED: bool = Field(default=True)
    STREAM_JPEG_QUALITY: int = Field(default=80)
    STREAM_FPS: int = Field(default=15)


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = BackendSettings()
