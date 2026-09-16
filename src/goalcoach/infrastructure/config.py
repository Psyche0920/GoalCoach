import os

from typing import Self
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Disable third-party telemetry globally for clean offline and test execution
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


class Settings(BaseSettings):
    """Configuration for hosted/local model switching and optional infrastructure."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GOALCOACH_")

    environment: str = "development"
    database_url: str = "sqlite:///./goalcoach.db"
    content_database_url: str = "sqlite:///./data/database1/goalcoach_hsk1_learning.db"
    planning_item_minutes: int = Field(default=5, gt=0, le=120)
    content_database_path: str = "./data/database1/goalcoach_hsk1_learning.db"
    vector_store_path: str = "./data/database2/chroma_db"
    chroma_persist_directory: str = "./data/database2/chroma_db"

    @model_validator(mode="after")
    def _sync_vector_paths(self) -> Self:
        if (
            self.vector_store_path != "./data/database2/chroma_db"
            and self.chroma_persist_directory == "./data/database2/chroma_db"
        ):
            self.chroma_persist_directory = self.vector_store_path
        elif (
            self.chroma_persist_directory != "./data/database2/chroma_db"
            and self.vector_store_path == "./data/database2/chroma_db"
        ):
            self.vector_store_path = self.chroma_persist_directory
        return self

    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = Field(default=30, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    llm_max_cost_usd_per_week: float = Field(default=50, gt=0)
    fallback_llm_base_url: str = "http://localhost:11434/v1"
    fallback_llm_model: str | None = None
    enable_ollama_fallback: bool = False
    enable_background_updates: bool = True
    enable_vector_retrieval: bool = False
    enable_langgraph: bool = False
