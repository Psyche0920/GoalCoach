import os
from urllib.parse import quote, urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Disable third-party telemetry globally for clean offline and test execution
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


class Settings(BaseSettings):
    """Configuration for hosted/local model switching and optional infrastructure."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GOALCOACH_", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./goalcoach.db"
    content_database_url: str = "sqlite:///./data/database1/goalcoach_hsk1_learning.db"
    content_database_path: str = "./data/database1/goalcoach_hsk1_learning.db"
    learner_database_path: str = "./goalcoach.db"
    supabase_url: str = "https://yiklbqnojmijxtvlryqr.supabase.co"
    supabase_db_password: str | None = None
    supabase_db_user: str = "postgres"
    supabase_db_host: str | None = None
    supabase_db_port: int = 5432
    planning_item_minutes: int = Field(default=5, gt=0, le=120)
    enable_prerequisites: bool = False

    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = Field(default=30, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    llm_max_cost_usd_per_week: float = Field(default=50, gt=0)
    offline_llm_fallback: bool = True
    fallback_llm_base_url: str = "http://localhost:11434/v1"
    fallback_llm_model: str | None = None
    enable_ollama_fallback: bool = False

    @property
    def resolved_database_url(self) -> str:
        """Use Supabase Postgres when its password is configured locally."""
        if self.supabase_db_password is None or self.database_url != "sqlite:///./goalcoach.db":
            return self.database_url

        project_ref = urlparse(self.supabase_url).hostname.split(".", maxsplit=1)[0]
        host = self.supabase_db_host or f"db.{project_ref}.supabase.co"
        formatted_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
        return (
            f"postgresql+psycopg://{quote(self.supabase_db_user, safe='')}:"
            f"{quote(self.supabase_db_password, safe='')}@{formatted_host}:"
            f"{self.supabase_db_port}/postgres?sslmode=require"
        )
