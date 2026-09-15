import asyncio

from goalcoach.agents.tools.retrieval_tools import AgentDeps
from goalcoach.application.teaching_loop import run_teaching_session
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.persistence.database import create_session_factory
from goalcoach.infrastructure.persistence.repositories import ContentRepository
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService
from goalcoach.domain.models import (
    LearnerState,
    LearningGoal,
    TeachingSession,
)

async def main() -> None:
    settings = Settings()

    session_factory = create_session_factory(
        settings.content_database_url
    )

    content_repo = ContentRepository(session_factory)

    concept_id = "hsk1_c20"

    concept = content_repo.get_concept(concept_id)

    if concept is None:
        raise ValueError(f"Concept not found: {concept_id}")

    print(f"Teaching concept: {concept.concept_id}")

    learner_state = LearnerState(
        display_name="Test Learner",
        goal=LearningGoal(
            title="Learn Chinese for Travel",
            target_hsk_level=1,
        ),
    )

    chroma_service = ChromaService(settings=settings)

    deps = AgentDeps(
        learner_state=learner_state,
        content_repo=content_repo,
        chroma_service=chroma_service,
    )

    session = TeachingSession(
        learner_id=learner_state.learner_id,
        concept_id=concept_id,
    )

    result = await run_teaching_session(
        deps=deps,
        session=session,
    )

    print(f"\nSession ended: {result.status}")

if __name__ == "__main__":
    asyncio.run(main())
