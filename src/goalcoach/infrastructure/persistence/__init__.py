"""SQLAlchemy persistence adapters."""

from goalcoach.infrastructure.persistence.database import create_session_factory
from goalcoach.infrastructure.persistence.repositories import ContentRepository

__all__ = ["ContentRepository", "create_session_factory"]
