"""Configuration and environment settings for the thesis API shell."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Sequence
from pydantic import Field, SecretStr, field_validator
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
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://final-thesis-frontend.vercel.app",
            "https://fin-ai.eddiephung.me",
        ],
        alias="CORS_ORIGINS",
    )
    cors_origin_regex: str | None = Field(
        default=r"^https?://([a-zA-Z0-9-]+\.)?(vercel\.app|eddiephung\.me)(:[0-9]+)?$|^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
        alias="CORS_ORIGIN_REGEX",
    )
    app_revision: str | None = Field(default=None, alias="APP_REVISION")
    render_git_commit: str | None = Field(default=None, alias="RENDER_GIT_COMMIT")
    sqlite_db_path: str = Field(
        default="data/processed/finance_master_v2.sqlite",
        alias="SQLITE_DB_PATH",
    )
    analysis_runs_db_path: str = Field(
        default="data/runtime/analysis_runs.sqlite",
        alias="ANALYSIS_RUNS_DB_PATH",
    )
    expected_dataset_snapshot_id: str | None = Field(
        default=None,
        alias="EXPECTED_DATASET_SNAPSHOT_ID",
    )
    expected_sqlite_sha256: str | None = Field(
        default=None,
        alias="EXPECTED_SQLITE_SHA256",
    )
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_storage_bucket: str | None = Field(
        default=None,
        alias="SUPABASE_STORAGE_BUCKET",
    )
    supabase_storage_object: str | None = Field(
        default=None,
        alias="SUPABASE_STORAGE_OBJECT",
    )
    supabase_service_role_key: SecretStr | None = Field(
        default=None,
        alias="SUPABASE_SERVICE_ROLE_KEY",
    )
    run_history_remote_prefix: str = Field(
        default="run-history/",
        alias="RUN_HISTORY_REMOTE_PREFIX",
    )
    openai_base_url: str = Field(
        default="https://superup.codelypixverse.com/v1",
        alias="OPENAI_BASE_URL",
    )
    openai_model: str = Field(
        default="deepseek-v4-pro-0813",
        alias="OPENAI_MODEL",
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    planner_mode: str = Field(default="model_with_fallback", alias="PLANNER_MODE")
    analysis_arm: str = Field(default="hierarchical_with_critique", alias="ANALYSIS_ARM")
    # Explicit opt-in only.  The Gold reporting-scope authority is an
    # independently pinned sidecar and is never discovered from the data tree.
    gold_scope_authority_path: Path | None = Field(default=None, alias="GOLD_SCOPE_AUTHORITY_PATH")
    user_uploads_dir: str = Field(
        default_factory=lambda: os.path.join(tempfile.gettempdir(), "user_uploads"),
        alias="USER_UPLOADS_DIR",
    )

    def get_user_uploads_dir(self) -> Path:
        """Resolve writable directory for user-supplied onboarding uploads."""
        p = Path(self.user_uploads_dir).expanduser()
        if not p.is_absolute():
            repo_root = Path(__file__).resolve().parents[2]
            p = (repo_root / p).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_sqlite_path(self) -> Path:
        """Resolve canonical SQLite database path."""
        p = Path(self.sqlite_db_path)
        if p.is_absolute() and p.exists():
            return p
        if p.exists():
            return p.resolve()
        repo_root = Path(__file__).resolve().parents[2]
        repo_path = repo_root / self.sqlite_db_path
        if repo_path.exists():
            return repo_path.resolve()
        return p.resolve()

    def get_analysis_runs_path(self, *, dataset_path: Path | None = None) -> Path:
        """Resolve the writable operational store and reject aliases to accepted data."""
        raw_path = Path(self.analysis_runs_db_path).expanduser()
        if raw_path.is_absolute():
            runs_path = raw_path.resolve(strict=False)
        else:
            runs_path = (Path(__file__).resolve().parents[2] / raw_path).resolve(strict=False)
        accepted_path = (dataset_path or self.get_sqlite_path()).expanduser().resolve(strict=False)
        aliases = runs_path == accepted_path
        if not aliases and runs_path.exists() and accepted_path.exists():
            try:
                aliases = os.path.samefile(runs_path, accepted_path)
            except OSError:
                aliases = False
        if aliases:
            raise ValueError("analysis_runs_store_aliases_dataset")
        return runs_path

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
