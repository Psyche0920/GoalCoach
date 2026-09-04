"""
scripts/vector_store.py
Object-Oriented Manager to bootstrap and refresh the Chroma vector store via CardChunkFactory.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.retrieval.chunk_factory import CardChunk, CardChunkFactory

os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class CurriculumVectorStore:
    """Manages SQLite curriculum extraction and persistent ChromaDB indexing using CardChunkFactory."""

    def __init__(
        self,
        base_dir: Path | None = None,
        collection_name: str = "hsk1_curriculum",
        embedding_model: str = "BAAI/bge-small-zh-v1.5",
        split_examples: bool = False,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.base_dir = (base_dir or PROJECT_ROOT).resolve()
        self.sqlite_dir = self.base_dir / "data" / "database1"
        self.vector_store_dir = (self.base_dir / self.settings.vector_store_path).resolve()
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.chunk_factory = CardChunkFactory(max_tokens=300, split_examples=split_examples)

        self.sqlite_path = (
            Path(self.settings.content_database_path)
            if Path(self.settings.content_database_path).is_absolute()
            else (self.base_dir / self.settings.content_database_path).resolve()
        )

        self._client: chromadb.PersistentClient | None = None
        self._collection: chromadb.Collection | None = None

    def resolve_sqlite_path(self) -> Path:
        if self.sqlite_path.exists():
            return self.sqlite_path

        # If .db is missing (e.g. freshly cloned repo), bootstrap from raw SQL seed package
        sql_seed = (
            self.base_dir
            / "data"
            / "database1"
            / "GoalCoach_HSK1_Learning_DB_Package"
            / "data"
            / "goalcoach_hsk1_learning_db_sqlite.sql"
        )
        if sql_seed.exists():
            logger.info(
                "SQLite DB missing at %s. Bootstrapping from SQL seed: %s",
                self.sqlite_path,
                sql_seed,
            )
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self.sqlite_path)) as conn:
                conn.executescript(sql_seed.read_text(encoding="utf-8"))
            logger.info("Successfully bootstrapped SQLite database at %s", self.sqlite_path)
            return self.sqlite_path

        raise FileNotFoundError(f"Curriculum SQLite DB not found at: {self.sqlite_path}")

    def fetch_cards(self, db_path: Path) -> list[tuple[Any, ...]]:
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                try:
                    query = """                                                                                                                                                                                       
                    SELECT                                                                                                                                                                                            
                        concept_id, sequence_no, title_zh, title_en, communicative_goal,                                                                                                                              
                        card_id, card_type, prompt_zh, explanation_en, example_zh, example_en                                                                                                                         
                    FROM v_teaching_modules                                                                                                                                                                           
                    WHERE card_id IS NOT NULL;                                                                                                                                                                        
                    """
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    logger.info("Loaded %d cards from v_teaching_modules.", len(rows))
                    return rows
                except sqlite3.OperationalError:
                    query = """                                                                                                                                                                                       
                    SELECT                                                                                                                                                                                            
                        concept_id, 0, '', '', '',                                                                                                                                                                    
                        card_id, card_type, prompt_zh, explanation_en, example_zh, example_en                                                                                                                         
                    FROM teaching_cards;                                                                                                                                                                              
                    """
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    logger.info("Loaded %d cards from fallback table 'teaching_cards'.", len(rows))
                    return rows
        except sqlite3.Error:
            logger.exception("Database extraction failed from %s", db_path)
            raise

    def get_or_create_collection(self) -> chromadb.Collection:
        if self._collection is not None:
            return self._collection

        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.vector_store_dir))
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model
        )

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def sync(self, refresh: bool = False) -> tuple[str, int]:
        sqlite_path = self.resolve_sqlite_path()
        logger.info("SQLite Source: %s", sqlite_path)
        logger.info("Vector Store Path: %s", self.vector_store_dir)

        if refresh:
            self.vector_store_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.vector_store_dir))
            try:
                self._client.delete_collection(name=self.collection_name)
                logger.info(
                    "Deleted existing collection '%s' for clean refresh.", self.collection_name
                )
            except ValueError:
                pass
            self._collection = None

        collection = self.get_or_create_collection()
        status = "existing" if collection.count() > 0 else "new"

        rows = self.fetch_cards(sqlite_path)
        if not rows:
            raise RuntimeError(f"No records found in {sqlite_path}")

        all_chunks: list[CardChunk] = []
        for row in rows:
            all_chunks.extend(self.chunk_factory.create_chunks_from_row(row))

        ids = [c.chunk_id for c in all_chunks]
        documents = [c.text for c in all_chunks]
        metadatas = [c.metadata for c in all_chunks]

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        total_count = collection.count()
        logger.info(
            "Vector Store sync complete. Status: %s -> Final Count: %d chunks.", status, total_count
        )
        return status, total_count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed or refresh the GoalCoach ChromaDB vector store."
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Wipe and recreate collection before indexing from SQLite curriculum.",
    )
    args = parser.parse_args()

    store = CurriculumVectorStore()
    store.sync(refresh=args.refresh)
