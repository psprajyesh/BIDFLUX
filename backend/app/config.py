"""Application settings, read from the environment.

Every value has a working local-development default so the demo runs with no
configuration. Nothing secret is stored here: the app has no auth and no API keys.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing import Annotated

BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DB_PATH = (BACKEND_DIR / "bidflux.db").as_posix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "BIDFLUX API"
    api_version: str = "1.0.0"
    app_env: str = "development"

    database_url: str = f"sqlite:///{_DEFAULT_DB_PATH}"

    storage_dir: Path = BACKEND_DIR / "storage"

    #: Exact origins permitted to call this API. Never use "*" in production.
    # NoDecode keeps pydantic-settings from JSON-decoding the raw env value, so
    #: CORS_ORIGINS="https://a.example,https://b.example" reaches the validator.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    max_upload_mb: int = 10

    #: "mock" -> simulated AI services, flagged in responses and UI. The only
    #: mode this build ships with.
    #: "disabled" -> reserved: disables simulated extraction, but the build has
    #: no manual requirement-entry UI, so workflows stall unless that path exists.
    ai_mode: str = "mock"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string as well as a JSON list."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return value
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def ai_enabled(self) -> bool:
        return self.ai_mode.lower() == "mock"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
