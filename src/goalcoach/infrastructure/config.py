import os

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

    log_level: str = "INFO"
    log_format: str = "auto"
    log_to_file: bool = True
    log_file_path: str = "./logs/goalcoach.log"
    backend_log_path: str = "./logs/backend.jsonl"
    agent_telemetry_log_path: str = "./logs/agent_telemetry.jsonl"
    cost_accounting_log_path: str = "./logs/cost_accounting.jsonl"
    session_cost_limit_usd: float = Field(default=0.50, gt=0.0)
    enable_agent_telemetry: bool = True
    async_logging_queue_size: int = Field(default=10000, gt=100)
    log_slow_query_threshold_ms: float = 25.0

    def resolve_log_path(self, path_str: str) -> str:
        """Resolve log paths relative to repository root to prevent CWD drift under Uvicorn."""
        from pathlib import Path

        p = Path(path_str)
        if p.is_absolute():
            return str(p)
        # Anchor relative to project root (4 levels up from this file: infrastructure -> goalcoach -> src -> repo root)
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        return str((root_dir / p).resolve())
