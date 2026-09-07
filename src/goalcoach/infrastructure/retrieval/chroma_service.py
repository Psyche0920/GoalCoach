"""
src/goalcoach/infrastructure/retrieval/chroma_service.py
ChromaDB semantic retrieval service with typed Pydantic payloads and non-blocking queries.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import anyio
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from pydantic import BaseModel, Field

from goalcoach.infrastructure.config import Settings

logger = logging.getLogger(__name__)


class RetrievedCardPayload(BaseModel):
    """Structured response payload returned by semantic retrieval for downstream agents."""

    concept_id: str
    card_id: int
    sequence_no: int
    card_type: str
    chunk_type: str = "full_card"
    content: str
    distance_score: float
    relevance_confidence: float = Field(
        description="Confidence score where 1.0 is exact match, derived from 1 - distance_score."
    )


class ChromaService:
    """Service layer managing semantic retrieval from ChromaDB."""

    def __init__(
        self,
        persist_dir: Path | str | None = None,
        collection_name: str = "hsk1_curriculum",
        embedding_model_name: str = "BAAI/bge-small-zh-v1.5",
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or Settings()
        if persist_dir is None:
            raw_path = Path(self.settings.chroma_persist_directory)
            if raw_path.is_absolute():
                self.persist_dir = raw_path
            else:
                base_dir = Path(__file__).resolve().parents[4]
                self.persist_dir = (base_dir / self.settings.chroma_persist_directory).resolve()
        else:
            self.persist_dir = Path(persist_dir).resolve()

        self.collection_name = collection_name
        self.embedding_model_name = embedding_model_name

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model_name
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def total_documents(self) -> int:
        """Returns the number of indexed card chunks."""
        return self._collection.count()

    def _sync_query(
        self, query_text: str, top_k: int = 3, level: int | None = None
    ) -> list[dict[str, Any]]:
        """Synchronous query filtering on metadata hsk_level."""
        where_filter = {"hsk_level": level} if level else None
        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=where_filter,
            )
            chunks: list[dict[str, Any]] = []
            if results and results.get("documents") and results.get("metadatas"):
                for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                    chunks.append({"content": doc, "metadata": meta})
            return chunks
        except Exception:
            logger.exception("ChromaService _sync_query failure for query '%s'", query_text)
            return []

    async def query_chunks_async(
        self, query_text: str, top_k: int = 3, level: int | None = None
    ) -> list[dict[str, Any]]:
        """Non-blocking asynchronous query wrapping ChromaDB execution in a thread pool."""
        return await anyio.to_thread.run_sync(self._sync_query, query_text, top_k, level)

    def retrieve_remedial_material(
        self,
        semantic_query: str,
        hsk_level: int = 1,
        top_k: int = 2,
    ) -> list[RetrievedCardPayload]:
        """Performs metadata-filtered semantic similarity search returning typed payloads."""
        try:
            results = self._collection.query(
                query_texts=[semantic_query],
                n_results=top_k,
                where={"hsk_level": hsk_level},
            )

            formatted: list[RetrievedCardPayload] = []
            if results and results.get("documents") and results["documents"][0]:
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    dist_val = round(float(dist), 4)
                    confidence = round(max(0.0, 1.0 - dist_val), 4)
                    formatted.append(
                        RetrievedCardPayload(
                            concept_id=str(meta.get("concept_id", "")),
                            card_id=int(meta.get("card_id", 0)),
                            sequence_no=int(meta.get("sequence_no", 0)),
                            card_type=str(meta.get("card_type", "")),
                            chunk_type=str(meta.get("chunk_type", "full_card")),
                            content=doc,
                            distance_score=dist_val,
                            relevance_confidence=confidence,
                        )
                    )
            return formatted

        except Exception:
            logger.exception("ChromaService query execution failure for query '%s'", semantic_query)
            return []

    async def retrieve_remedial_material_async(
        self,
        semantic_query: str,
        hsk_level: int = 1,
        top_k: int = 2,
    ) -> list[RetrievedCardPayload]:
        """Non-blocking asynchronous wrapper offloading CPU-bound Chroma query to a worker thread."""
        return await anyio.to_thread.run_sync(
            self.retrieve_remedial_material,
            semantic_query,
            hsk_level,
            top_k,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    service = ChromaService()
    logger.info("ChromaService active. Total entries: %d", service.total_documents)
    test_results = service.retrieve_remedial_material("student uses 不有 instead of 没有")
    for item in test_results:
        logger.info(
            "Concept: %s | Distance: %f | Confidence: %f",
            item.concept_id,
            item.distance_score,
            item.relevance_confidence,
        )
