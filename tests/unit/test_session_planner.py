"""Unit tests for the Adaptive Session Planner component and session tree traversal."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from goalcoach.agents.grader_component import GraderComponent
from goalcoach.agents.session_planner import (
    SessionPlanner,
    deterministic_build_session_tree,
)
from goalcoach.agents.teaching_agent import TeachingWorker
from goalcoach.application.orchestrator import DeterministicOrchestrator
from goalcoach.application.progress_service import ProgressService
from goalcoach.domain.enums import EventType, PlanStatus
from goalcoach.domain.models import Exercise, GradingResult, RubricScores, SessionTree, SessionTreeNode
from goalcoach.infrastructure.persistence.content_service import ContentService
from goalcoach.infrastructure.persistence.database import (
    create_learner_schema,
    create_session_factory,
)
from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    SqliteLearnerRepository,
)
from tests.fakes import FakeGraderComponent, FakePlanningWorker

CONTENT_DB_PATH = Path("data/database1/goalcoach_hsk1_learning.db")


@pytest.fixture
def content_service() -> ContentService:
    if not CONTENT_DB_PATH.exists():
        pytest.skip(f"Curriculum DB missing at {CONTENT_DB_PATH}")
    factory = create_session_factory(f"sqlite:///{CONTENT_DB_PATH}")
    repo = ContentRepository(factory)
    return ContentService(repo)


@pytest.fixture
def temp_learner_repo(tmp_path: Path) -> SqliteLearnerRepository:
    db_file = tmp_path / "test_session_planner.db"
    factory = create_session_factory(f"sqlite:///{db_file}")
    create_learner_schema(factory)
    return SqliteLearnerRepository(factory)


def test_deterministic_session_tree_structure(content_service: ContentService) -> None:
    """Verifies that deterministic tree builder produces a valid adaptive branching DAG."""
    exercises = content_service.get_exercises_for_concept("hsk1_c01", limit=10)
    assert len(exercises) >= 3

    tree: SessionTree = deterministic_build_session_tree("hsk1_c01", exercises)
    assert tree.concept_id == "hsk1_c01"
    assert tree.root_node_id in tree.nodes

    root = tree.nodes[tree.root_node_id]
    assert root.on_correct is not None
    assert root.on_incorrect is not None

    # Check left branch (correct -> step_pass)
    left_node_id = root.on_correct
    assert left_node_id in tree.nodes
    left_node = tree.nodes[left_node_id]
    assert left_node.on_correct is not None  # Challenge step

    # Check right branch (incorrect -> step_remedial)
    right_node_id = root.on_incorrect
    assert right_node_id in tree.nodes
    right_node = tree.nodes[right_node_id]
    assert right_node.on_correct is not None

    # Verify all exercise IDs in the tree are genuine database exercises
    valid_ids = {e.exercise_id for e in exercises}
    for node in tree.nodes.values():
        assert node.exercise_id in valid_ids


@pytest.mark.asyncio
async def test_session_planner_with_content_service(content_service: ContentService) -> None:
    """Verifies that SessionPlanner coordinates planning and grounds all exercises."""
    planner = SessionPlanner()
    tree = await planner.plan_session_tree("hsk1_c02", content_service)

    assert tree.concept_id == "hsk1_c02"
    assert tree.root_node_id in tree.nodes
    assert len(tree.nodes) >= 2

    # Check every node's exercise exists in DB
    for node in tree.nodes.values():
        ex = content_service.get_exercise(node.exercise_id)
        assert ex is not None
        assert ex.concept_id == "hsk1_c02"


@pytest.mark.asyncio
async def test_orchestrator_adaptive_tree_all_correct_flow(
    content_service: ContentService,
    temp_learner_repo: SqliteLearnerRepository,
) -> None:
    """Full closed-loop test: Learner answers correctly through the Left Branch to complete mastery."""
    progress_service = ProgressService(learner_repo=temp_learner_repo)
    planning_worker = FakePlanningWorker()
    teaching_worker = TeachingWorker()  # Real worker with SessionPlanner
    grader_worker = FakeGraderComponent()

    orchestrator = DeterministicOrchestrator(
        learner_repo=temp_learner_repo,
        content_service=content_service,
        progress_service=progress_service,
        planning_worker=planning_worker,
        teaching_worker=teaching_worker,
        grader_worker=grader_worker,
    )

    learner_id = f"learner_{uuid4().hex[:8]}"

    # 1. Goal created
    await orchestrator.handle_event(
        event_type=EventType.GOAL_CREATED,
        learner_id=learner_id,
        payload={"title": "Master HSK 1"},
    )

    # 2. Session started -> SessionPlanner creates tree and provides root node
    start_res = await orchestrator.handle_event(
        event_type=EventType.SESSION_STARTED,
        learner_id=learner_id,
        payload={},
    )
    assert start_res.teaching_action is not None
    root_payload = start_res.teaching_action.exercise_payload
    assert root_payload is not None
    root_exercise_id = root_payload["exercise_id"]

    # Verify session tree is active in state
    state = await temp_learner_repo.get(learner_id)
    assert state.active_session is not None
    assert state.active_session.session_tree is not None
    assert state.active_session.current_node_id == state.active_session.session_tree.root_node_id

    # 3. Answer root exercise correctly -> should branch left to step_pass
    content_ex = content_service.get_exercise(root_exercise_id)
    ans_val = content_ex.accepted_answers[0] if content_ex.accepted_answers else "Hello"

    ans1_res = await orchestrator.handle_event(
        event_type=EventType.ANSWER_SUBMITTED,
        learner_id=learner_id,
        payload={
            "exercise_id": root_exercise_id,
            "concept_id": "hsk1_c01",
            "answer": ans_val,
            "time_spent_seconds": 30,
        },
    )
    assert ans1_res.grading_result is not None
    assert ans1_res.grading_result.passed_gates is True
    # Should have navigated to next node (Left branch)
    assert ans1_res.teaching_action is not None
    next_payload = ans1_res.teaching_action.exercise_payload
    assert next_payload is not None
    assert ans1_res.teaching_action.metadata.get("branch_taken") == "left"


@pytest.mark.asyncio
async def test_orchestrator_adaptive_tree_mistake_recovery_flow(
    content_service: ContentService,
    temp_learner_repo: SqliteLearnerRepository,
) -> None:
    """Full closed-loop test: Learner makes a mistake on root -> branches Right to remedial."""
    progress_service = ProgressService(learner_repo=temp_learner_repo)
    planning_worker = FakePlanningWorker()
    teaching_worker = TeachingWorker()
    grader_worker = FakeGraderComponent()

    orchestrator = DeterministicOrchestrator(
        learner_repo=temp_learner_repo,
        content_service=content_service,
        progress_service=progress_service,
        planning_worker=planning_worker,
        teaching_worker=teaching_worker,
        grader_worker=grader_worker,
    )

    learner_id = f"learner_{uuid4().hex[:8]}"

    await orchestrator.handle_event(
        event_type=EventType.GOAL_CREATED,
        learner_id=learner_id,
        payload={"title": "Master HSK 1"},
    )

    start_res = await orchestrator.handle_event(
        event_type=EventType.SESSION_STARTED,
        learner_id=learner_id,
        payload={},
    )
    root_exercise_id = start_res.teaching_action.exercise_payload["exercise_id"]

    # Submit WRONG answer -> should branch Right to remedial
    ans1_res = await orchestrator.handle_event(
        event_type=EventType.ANSWER_SUBMITTED,
        learner_id=learner_id,
        payload={
            "exercise_id": root_exercise_id,
            "concept_id": "hsk1_c01",
            "answer": "WRONG_ANSWER_123",
            "time_spent_seconds": 25,
        },
    )
    assert ans1_res.grading_result is not None
    assert ans1_res.grading_result.passed_gates is False
    assert ans1_res.teaching_action is not None
    assert ans1_res.teaching_action.metadata.get("branch_taken") == "right"
