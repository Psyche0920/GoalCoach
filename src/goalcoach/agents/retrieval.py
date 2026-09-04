"""
src/goalcoach/agents/retrieval.py
Retrieval Agent: dispatches queries deterministically between SQLite and ChromaDB.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from pydantic import BaseModel, Field

from goalcoach.domain.models import RetrievalRequest
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService, RetrievedCardPayload

logger = logging.getLogger(__name__)


class RetrievalQuery(BaseModel):
    """Input contract for backward-compatible agent calls."""

    concept_id: str | None = Field(
        default=None,
        description="Known target concept ID. If provided, bypasses vector search and uses SQLite.",
    )
    semantic_query: str | None = Field(
        default=None,
        description="Natural language error description or semantic gap to query in ChromaDB.",
    )
    hsk_level: int = Field(default=1, description="Target HSK scope.")
    top_k: int = Field(default=2, description="Maximum number of candidate cards to return.")


class RemedialMaterial(BaseModel):
    """Output contract passed downstream to TeachingAgent."""

    source: str = Field(description="'sqlite_exact' or 'chromadb_semantic'")
    concept_id: str
    card_id: int | None = None
    title_zh: str | None = None
    title_en: str | None = None
    content: str
    confidence: float = 1.0


class RetrievalAgent:
    """Hybrid Retrieval Router adhering to the GoalCoach deterministic routing specification."""

    def __init__(
        self,
        sqlite_path: Path | str | None = None,
        chroma_service: ChromaService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or Settings()
        base_dir = Path(__file__).resolve().parents[3]
        if sqlite_path:
            self.sqlite_path = Path(sqlite_path).resolve()
        else:
            self.sqlite_path = (base_dir / self.settings.content_database_path).resolve()

        self.chroma_service = chroma_service or ChromaService(settings=self.settings)

    def _fetch_from_sqlite(self, concept_id: str) -> list[RemedialMaterial]:
        """Performs fast, exact SQL lookup when the concept_id is known."""
        if not self.sqlite_path.exists():
            logger.warning("SQLite curriculum database not found at %s", self.sqlite_path)
            return []

        try:
            with sqlite3.connect(str(self.sqlite_path)) as conn:
                cursor = conn.cursor()
                query = """                                                                                                                                                                                           
                SELECT concept_id, card_id, title_zh, title_en, prompt_zh, explanation_en, example_zh, example_en                                                                                                     
                FROM v_teaching_modules                                                                                                                                                                               
                WHERE concept_id = ?                                                                                                                                                                                  
                LIMIT 1;                                                                                                                                                                                              
                """
                cursor.execute(query, (concept_id,))
                row = cursor.fetchone()
                if not row:
                    return []

                cid, card_id, t_zh, t_en, prompt, expl, ex_zh, ex_en = row
                text = (
                    f"Concept: {t_zh} ({t_en})\n"
                    f"Pattern: {prompt or ''}\n"
                    f"Explanation: {expl or ''}\n"
                    f"Example: {ex_zh or ''} ({ex_en or ''})"
                )

                return [
                    RemedialMaterial(
                        source="sqlite_exact",
                        concept_id=str(cid),
                        card_id=int(card_id) if card_id is not None else None,
                        title_zh=t_zh,
                        title_en=t_en,
                        content=text,
                        confidence=1.0,
                    )
                ]
        except sqlite3.Error:
            logger.exception("SQLite exact retrieval failed for concept %s", concept_id)
            return []

    def retrieve_sync(self, request: RetrievalQuery | RetrievalRequest) -> list[RemedialMaterial]:
        """Synchronous implementation routing the retrieval request based on available deterministic signals."""
        concept_id = request.concept_id if request.concept_id else None
        semantic_query = getattr(request, "semantic_query", None) or getattr(
            request, "semantic_need", None
        )
        hsk_level = getattr(request, "hsk_level", 1) or 1
        top_k = getattr(request, "top_k", 2)

        # Route 1: Exact concept known -> bypass ChromaDB, use SQL
        if concept_id:
            exact_results = self._fetch_from_sqlite(concept_id)
            if exact_results:
                return exact_results

        # Route 2: Semantic gap / unknown error -> execute ChromaDB search if enabled
        if semantic_query:
            if not self.settings.enable_vector_retrieval:
                logger.info(
                    "Vector retrieval is disabled via config (enable_vector_retrieval=False)."
                )
                return []

            chroma_matches: list[RetrievedCardPayload] = (
                self.chroma_service.retrieve_remedial_material(
                    semantic_query=semantic_query,
                    hsk_level=hsk_level,
                    top_k=top_k,
                )
            )

            return [
                RemedialMaterial(
                    source="chromadb_semantic",
                    concept_id=match.concept_id,
                    card_id=match.card_id,
                    content=match.content,
                    confidence=match.relevance_confidence,
                )
                for match in chroma_matches
            ]

        return []

    async def retrieve(self, request: RetrievalQuery | RetrievalRequest) -> list[RemedialMaterial]:
        """Asynchronous, non-blocking retrieval routing satisfying the Retriever protocol."""
        import anyio

        return await anyio.to_thread.run_sync(self.retrieve_sync, request)
