from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for hosted/local model switching and optional infrastructure."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GOALCOACH_")

    environment: str = "development"
    database_url: str = "sqlite:///./goalcoach.db"
    content_database_url: str = "sqlite:///./data/database1/goalcoach_hsk1_learning.db"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = Field(default=30, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    llm_max_cost_usd_per_week: float = Field(default=50, gt=0)
    fallback_llm_base_url: str = "http://localhost:11434/v1"
    fallback_llm_model: str | None = None
    enable_background_updates: bool = True
    enable_vector_retrieval: bool = False
    enable_langgraph: bool = False
