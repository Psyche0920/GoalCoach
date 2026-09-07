"""
apps/api/dependencies.py
FastAPI dependency injectors for persistence repositories and ChromaDB service.
"""

from __future__ import annotations

from typing import cast

from fastapi import Request

from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    SqliteLearnerRepository,
)
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService

_default_content_repo: ContentRepository | None = None
_default_chroma_service: ChromaService | None = None


def get_learner_repo(request: Request) -> SqliteLearnerRepository:
    """Resolve learner repository from application state or create standard instance."""
    if hasattr(request.app.state, "learner_repository"):
        return cast(SqliteLearnerRepository, request.app.state.learner_repository)

    from goalcoach.infrastructure.config import Settings
    from goalcoach.infrastructure.persistence.database import (
        create_learner_schema,
        create_session_factory,
    )

    settings = Settings()
    factory = create_session_factory(settings.database_url)
    create_learner_schema(factory)
    return SqliteLearnerRepository(factory)


def get_content_repo(request: Request) -> ContentRepository:
    """Resolve content repository from application state or create singleton."""
    global _default_content_repo
    if hasattr(request.app.state, "content_repository"):
        return cast(ContentRepository, request.app.state.content_repository)

    if _default_content_repo is None:
        from goalcoach.infrastructure.config import Settings
        from goalcoach.infrastructure.persistence.database import create_session_factory

        settings = Settings()
        factory = create_session_factory(settings.content_database_url)
        _default_content_repo = ContentRepository(factory)
    return _default_content_repo


def get_chroma_service(request: Request) -> ChromaService:
    """Resolve ChromaService singleton from application state or initialize."""
    global _default_chroma_service
    if hasattr(request.app.state, "chroma_service"):
        return cast(ChromaService, request.app.state.chroma_service)

    if _default_chroma_service is None:
        _default_chroma_service = ChromaService()
    return _default_chroma_service
