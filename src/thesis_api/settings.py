"""Configuration and environment settings for the thesis API shell."""

from __future__ import annotations

import os
from typing import Sequence
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="final-thesis-api", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    cors_origins: list[str] | str = Field(
        default_factory=lambda: ["http://localhost:5173"],
        alias="CORS_ORIGINS",
    )
    cors_origin_regex: str | None = Field(default=None, alias="CORS_ORIGIN_REGEX")
    app_revision: str | None = Field(default=None, alias="APP_REVISION")
    render_git_commit: str | None = Field(default=None, alias="RENDER_GIT_COMMIT")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    @field_validator("cors_origins", mode="plain")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return ["http://localhost:5173"]
            if value.startswith("[") and value.endswith("]"):
                import json

                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return [str(item).strip() for item in value if str(item).strip()]
        return ["http://localhost:5173"]

    def get_revision(self) -> str:
        """Resolve current commit SHA or revision."""
        if self.app_revision and self.app_revision.strip():
            return self.app_revision.strip()
        if self.render_git_commit and self.render_git_commit.strip():
            return self.render_git_commit.strip()
        return "development"

    def get_version_metadata(self) -> dict[str, str]:
        """Return safe public deployment metadata without exposing secrets."""
        return {
            "service": self.app_name,
            "environment": self.app_env,
            "revision": self.get_revision(),
        }


def get_settings() -> Settings:
    """Return a settings instance."""
    return Settings()
