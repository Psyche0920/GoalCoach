"""Unit and integration tests for FastAPI learning endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import create_app
from goalcoach.infrastructure.config import Settings


@pytest.fixture
def app():
    settings = Settings(
        database_url="sqlite:///:memory:",
        content_database_url="sqlite:///./data/database1/goalcoach_hsk1_learning.db",
    )
    return create_app(settings)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_curriculum_concepts(client: AsyncClient):
    res = await client.get("/api/v1/curriculum/concepts")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 120
    # Check camelCase keys
    first = data[0]
    assert "conceptId" in first
    assert "hskLevel" in first
    assert "titleZh" in first


@pytest.mark.asyncio
async def test_curriculum_concepts_level_filter(client: AsyncClient):
    res = await client.get("/api/v1/curriculum/concepts?level=2")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(c["hskLevel"] == 2 for c in data)


@pytest.mark.asyncio
async def test_curriculum_concept_details(client: AsyncClient):
    # Fetch list first to get valid conceptId
    list_res = await client.get("/api/v1/curriculum/concepts")
    concept_id = list_res.json()[0]["conceptId"]

    res = await client.get(f"/api/v1/curriculum/concepts/{concept_id}")
    assert res.status_code == 200
    data = res.json()
    assert "concept" in data
    assert "cards" in data
    assert "exercises" in data
    assert data["concept"]["conceptId"] == concept_id


@pytest.mark.asyncio
async def test_learner_aggregate_and_routing(client: AsyncClient):
    learner_id = "test_learner_001"
    res = await client.get(f"/api/v1/learners/{learner_id}")
    assert res.status_code == 200
    data = res.json()
    assert "state" in data
    assert "nextAction" in data
    assert "overallProgress" in data
    assert "progressSummary" in data
    assert data["state"]["learnerId"] == learner_id


@pytest.mark.asyncio
async def test_today_plan_generation(client: AsyncClient):
    learner_id = "test_learner_plan_001"
    res = await client.get(f"/api/v1/learners/{learner_id}/today-plan")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_submit_answer_via_events(client: AsyncClient):
    # Look up an exercise from the database
    list_res = await client.get("/api/v1/curriculum/concepts")
    concept_id = list_res.json()[0]["conceptId"]
    details_res = await client.get(f"/api/v1/curriculum/concepts/{concept_id}")
    exercises = details_res.json().get("exercises", [])

    if exercises:
        ex = exercises[0]
        accepted = ex["acceptedAnswers"][0] if ex["acceptedAnswers"] else "你好"
        submission_payload = {
            "event_type": "ANSWER_SUBMITTED",
            "learner_id": "test_learner_001",
            "payload": {
                "exercise_id": ex["id"],
                "concept_id": concept_id,
                "answer": accepted,
            },
        }
        res = await client.post("/api/v1/events", json=submission_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["gradingResult"] is not None
        assert data["gradingResult"]["passedGates"] is True


@pytest.mark.asyncio
async def test_tts_empty_validation(client: AsyncClient):
    res = await client.get("/api/tts?text=   ")
    assert res.status_code == 400
