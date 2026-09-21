# Changelog

All notable changes to the GoalCoach project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-09-20

### Removed
- **Vector Database (ChromaDB) Decommissioning**: Fully removed ChromaDB and all associated vector retrieval components in accordance with PRD Principle 6 ("Zero Heavy Vector DB Overload"):
  - Removed `src/goalcoach/infrastructure/retrieval/` directory (`chroma_service.py`, `chunk_factory.py`, and `__init__.py`).
  - Removed `src/goalcoach/agents/retrieval.py` (`RetrievalAgent` and `RemedialMaterial`).
  - Removed `scripts/vector_store.py` (offline ChromaDB extraction and indexing script).
  - Removed `tests/integration/test_vector_pipeline.py` (vector pipeline test suite).
  - Removed `docs/vector-database.md` engineering specification.
  - Removed local `data/database2/chroma_db` directory and cleaned `.gitignore`.
- **Heavy ML Dependencies**: Removed `chromadb>=0.6.3`, `sentence-transformers>=3.0.0`, and `posthog<3` from `pyproject.toml` (`[project.optional-dependencies.retrieval]`).
- **Dependency Pruning**: Pruned 38 transitive packages via `uv lock` (including PyTorch/torch, transformers, sentence-transformers, onnxruntime, flatbuffers, and CUDA libraries), reducing resolved dependencies from 244 to 187 packages and drastically reducing CI install overhead.
- **Retriever Protocol**: Removed unused `Retriever` protocol from `src/goalcoach/agents/interfaces.py` and `src/goalcoach/agents/__init__.py`.

### Changed
- **Deterministic Curriculum Retrieval**: Refactored `search_hsk_curriculum` in `src/goalcoach/agents/tools/retrieval_tools.py` to query the SQLite `ContentRepository` deterministically without ChromaDB fallback.
- **FastAPI Tutoring Chat Endpoint**: Decoupled `apps/api/routes/tutoring.py` and `apps/api/dependencies.py` from ChromaDB; removed `get_chroma_service` dependency injection and `ChromaService` startup instantiation in `apps/api/main.py`.
- **Configuration Simplification**: Removed `vector_store_path`, `chroma_persist_directory`, `_sync_vector_paths` validator, and `enable_vector_retrieval` flag from `src/goalcoach/infrastructure/config.py`.
- **Settings Resilience**: Configured `extra="ignore"` on `SettingsConfigDict` in `src/goalcoach/infrastructure/config.py` to prevent fatal startup validation crashes from deprecated environment variables.
- **PRD Documentation**: Updated Principle 6 in `docs/GOALCOACH_MVP_PRD.md` to record that the vector database has been permanently decommissioned in favor of deterministic `ContentService` querying SQLite Database #1.

### Fixed
- **Curriculum & Learning Content Licensing Rectification**: Corrected the license for the imported HSK curriculum and vocabulary learning materials in `data/`:
  - Identified dual-licensing structure in the upstream [wuxialearn](https://github.com/wuxialearn) project: while application client code is under MIT, language frequency dictionary and learning datasets are governed by **CC BY-NC-SA 4.0** ([WuxiaLearn Frequency Dictionary LICENSE](https://github.com/wuxialearn/Chinese-English-Frequency-Dictionary/blob/master/LICENSE)).
  - Replaced the erroneous root MIT copy in `data/LICENSE` with the complete **CC BY-NC-SA 4.0** license text and proper attribution to `wuxialearn`.
  - Updated `data/database1/GoalCoach_HSK1_Learning_DB_Package/data/goalcoach_hsk1_learning_db_sqlite.sql` header comments to reference CC BY-NC-SA 4.0 and `data/LICENSE`.
  - Updated `docs/dev/goalcoach_hsk1_learning.db.md` with explicit attribution and licensing boundaries separating application software (MIT) from educational content (CC BY-NC-SA 4.0).
- **CI Integration Test Failures from Expanded Curriculum**:
  - **Prerequisite Count Assertion**: Updated `test_loads_all_prerequisite_relationships` in `tests/integration/test_content_repository.py` to assert the 125 total prerequisite rules present in the expanded HSK 1–6 dataset, while preserving the invariant that HSK 1 concepts retain their 18 prerequisite rules.
  - **Exercise Exhaustion Graceful Fallback**: Updated `test_edge_case_exercise_exhaustion_graceful_fallback` in `tests/integration/test_remediation_loop.py` to dynamically query all exercises for `hsk1_c01` (8 exercises in the expanded dataset) before simulating exercise exhaustion.
- **PydanticAI Test Suite**: Decoupled `tests/integration/test_pydantic_ai_pipeline.py` from ChromaDB mocks; updated tests to verify deterministic exact match and unknown concept fallback.
- **CI Workflow Configuration**: Removed obsolete `GOALCOACH_ENABLE_VECTOR_RETRIEVAL: "true"` environment variable from `.github/workflows/ci.yml`.

### Verification & Validation Results
- **`uv lock --check`**: PASSED (187 packages cleanly synchronized).
- **`uv run ruff check src/ apps/ tests/`**: PASSED (0 errors).
- **`uv run ruff format --check src/ apps/ tests/`**: PASSED (58 files formatted).
- **`uv run pytest tests/unit/ -v`**: PASSED (67/67 tests passed in 0.62s).
- **`uv run pytest tests/integration/ -v`**: PASSED (27/27 tests passed in 47.47s).
- **Total Test Suite**: 94/94 tests passing (100% pass rate).
