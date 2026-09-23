# GoalCoach Feature Implementation Reference: Code Changes & Line Mapping

**Date:** 2026-09-23  
**Scope:** Technical documentation detailing which files were modified and the exact line numbers responsible for three core features:
1. **Mix and Match (Matching) Exercise Engine**
2. **HSK Level Unlock (Levels 1–6)**
3. **Bite-Size Teaching (Ultra-Concise Micro-Pedagogy)**

---

## 1. Mix and Match (Word & Meaning Pairs)

The mix-and-match feature dynamically synthesizes vocabulary matching exercises from database teaching cards, formats paired options (Chinese words with pinyin on the left; English meanings on the right), and grades user submissions via a deterministic sub-millisecond fast path.

### Responsible Files & Exact Lines

| File | Responsible Lines | Description & Responsibility |
| :--- | :--- | :--- |
| [`src/goalcoach/domain/models.py`] | Lines **226–240** (`Exercise` class) | Extended `options` on `Exercise` to accept dictionary structure `dict[str, Any]` (containing `"left"` and `"right"` columns) in addition to list options. |
| [`apps/web/src/types.ts`] | Lines **103**, **116** (`Exercise` & `ExerciseType`) | Added `'matching'` to `ExerciseType` union and typed `options` with `{ left: Array<{ id: string; word: string; pinyin?: string }>; right: Array<{ id: string; meaning: string }> }`. |
| [`src/goalcoach/infrastructure/persistence/content_service.py`] | Lines **60–68** (`get_exercise`) | Supported dynamically resolved exercises ending in `_match_auto` so runtime answer submission can retrieve synthesized exercises for grading. |
| [`src/goalcoach/infrastructure/persistence/content_service.py`] | Lines **70–86** (`get_exercises_for_concept`) | Restricts matching exercise generation **strictly to vocabulary concepts** or concepts with `len(vocabulary_focus) >= 3`. Prepends the synthesized matching exercise to the exercise queue. |
| [`src/goalcoach/infrastructure/persistence/content_service.py`] | Lines **96–107** (`get_or_synthesize_matching_exercise`) | Queries existing matching exercises from the repository or delegates to `synthesize_matching_exercise()`. |
| [`src/goalcoach/infrastructure/persistence/content_service.py`] | Lines **108–265** (`synthesize_matching_exercise`) | Core synthesis engine: <br>• Lines **125–133** (`_is_clean_vocab_word`): Filters out grammar templates, placeholders (`A`, `B`, `+`, `...`, `~`), and punctuation.<br>• Lines **135–149** (`_is_valid_english_meaning`): Ensures meanings contain ASCII alphabetic characters, do not equal the Chinese word, and are not predominantly Hanzi.<br>• Lines **151–161**: Collects vocabulary cards while skipping cards marked `grammar`, `pattern`, `rule`, or `structure`.<br>• Lines **163–193**: Resolves `vocabulary_focus` words against cards; searches same-level cards if concept cards lack English definitions.<br>• Lines **195–214**: Backfills from same-level vocabulary cards to reach required pair count.<br>• Lines **218–264**: Constructs randomized left/right pair maps, shorthand answers (`1C 2A 3D...`), and builds `ContentExercise`. |
| [`src/goalcoach/agents/grader_component.py`] | Lines **71–98** (`parse_matching_pairs`) | Multi-format input parser: parses shorthand (`1C 2A 3D 4B 5E`), hyphenated (`1-C, 2-A`), colon-separated (`1:C 2:A`), comma-separated letter sequences (`C, A, D, B, E`), or JSON dictionaries into normalized `{left_id: right_id}`. |
| [`src/goalcoach/agents/grader_component.py`] | Lines **107–178** (`_grade_matching_exercise`) | Deterministic `<1ms` fast-path evaluation: compares student pairs with expected pairs, applies an 80% passing threshold (e.g. 4/5 correct passes), sets `semantic_precision`, and tags `ERR_VOCAB_MATCH` on failure. |
| [`src/goalcoach/agents/grader_component.py`] | Lines **217–226** (`grade`) | Fast-path routing branch detecting matching exercises and executing deterministic evaluation without calling an LLM. |
| [`src/goalcoach/application/orchestrator.py`] | Lines **487–497** (`_deterministic_fallback_grade`) | Fallback grading branch in orchestrator invoking `GraderComponent._grade_matching_exercise` when grader worker is not directly injected. |
| [`src/goalcoach/agents/terminal_harness.py`] | Lines **167–196** (Practice display) | Detects matching options dictionary and formats two-column side-by-side display (`Chinese Words` with non-empty pinyin vs. `Meanings`). |
| [`src/goalcoach/agents/terminal_harness.py`] | Lines **207–210** (Command prompt) | Prompts user with matching submission instructions (e.g. `1C 2A 3E 4B 5D`). |
| [`src/goalcoach/agents/terminal_harness.py`] | Lines **246–265** (Help guidance display) | Renders matching two-column table inside Coach Guidance panel when user types `help`. |
| [`tests/unit/test_matching_exercise.py`] | Lines **30–203** | Comprehensive unit tests for parser formats, HSK 1/2 synthesis, grader fast-path, grammar structure exclusion, and English-only meaning assertions. |

---

## 2. HSK Level Unlock Till Level 6

Previously, the learning engine was artificially restricted to HSK level 1 through hardcoded filters. Database #1 contains 126 curriculum concepts spanning all six HSK levels (HSK 1: 20, HSK 2: 19, HSK 3: 20, HSK 4: 33, HSK 5: 19, HSK 6: 15). The unlock decoupled hardcoded level 1 constraints across the repository, service, adaptive planner, orchestrator, and REST API.

### Responsible Files & Exact Lines

| File | Responsible Lines | Description & Responsibility |
| :--- | :--- | :--- |
| [`src/goalcoach/infrastructure/persistence/repositories.py`] | Lines **37–54** (`ContentRepository.list_concepts`) | Added optional `hsk_level: int \| None = None` and `max_hsk_level: int \| None = None` parameters. Supports querying all 126 concepts, a specific level, or a progressive range `1..max_level` ordered stably by `(CurriculumConcept.hsk_level, CurriculumConcept.sequence_no)`. |
| [`src/goalcoach/infrastructure/persistence/content_service.py`] | Lines **34–41** (`ContentService.list_all_concepts`) | Added optional `hsk_level` and `max_hsk_level` parameters, delegating to `self._repo.list_concepts()`. |
| [`src/goalcoach/domain/models.py`] | Line **54** (`LearningGoal.target_hsk_level`) | Validates target milestone level from 1 to 6 (`ge=1, le=6`). |
| [`src/goalcoach/domain/models.py`] | Line **234** (`Exercise.hsk_level`) | Domain exercise model holds target HSK level (`ge=1, le=6`). |
| [`src/goalcoach/agents/planning_agent.py`] | Lines **62–82** (`resolve_active_level`) | Dynamically resolves the learner's active reachable HSK level window based on their current mastery ($\ge 0.50$). Locks the learner to their current level until earlier levels are mastered. |
| [`src/goalcoach/agents/planning_agent.py`] | Lines **84–101** (`get_curriculum_catalog`) | Parameterizes catalog tool with `resolve_active_level` to supply concepts up to the active reachable level window (`max_hsk_level=active_level`). |
| [`src/goalcoach/agents/planning_agent.py`] | Lines **137–161** (`PlanningWorker.create_plan`) | Guides LLM prompt with active reachable level and validates generated items against reachable active concepts (`valid_active_ids`). |
| [`src/goalcoach/agents/planning_agent.py`] | Lines **218–225** (`_heuristic_fallback`) | Deterministic fallback plan generator pulls concepts matching `resolve_active_level` to schedule unmastered concepts within the active window. |
| [`src/goalcoach/application/orchestrator.py`] | Lines **284–296** (`_handle_answer_submitted`) | Dynamically resolves `exercise.hsk_level` from `concept.hsk_level` rather than defaulting or forcing level 1. |
| [`apps/api/routes/learning_loop.py`] | Lines **262–264** (`get_learner_aggregate`) | Filters curriculum concepts by learner's `target_hsk_level` for accurate progress summaries. |
| [`apps/api/routes/learning_loop.py`] | Lines **348–350** (`complete_concept_endpoint`) | Computes updated progress summary against learner's `target_hsk_level`. |
| [`apps/api/routes/learning_loop.py`] | Lines **363–370** (`list_curriculum_concepts`) | Exposes `GET /api/v1/curriculum/concepts` with optional query param `level: int \| None = Query(default=None, ge=1, le=6)` allowing frontend to fetch concepts by level. |
| [`tests/integration/test_content_repository.py`] | Lines **30–75** | Tests verifying `list_concepts()` returns 120+ concepts across all 6 levels, and level filtering returns level-specific concepts. |
| [`tests/unit/test_api_learning.py`] | Lines **40–65** | Tests verifying `GET /api/v1/curriculum/concepts?level=2` returns only HSK 2 concepts. |
| [`tests/unit/test_matching_exercise.py`] | Lines **232–265** | Unit tests verifying `resolve_active_level` unlocks progressively from HSK 1 to HSK 2 to HSK 3 upon mastery. |

---
