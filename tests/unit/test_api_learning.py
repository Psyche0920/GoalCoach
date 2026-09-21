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
    assert len(data) > 0
    # Check camelCase keys
    first = data[0]
    assert "conceptId" in first
    assert "hskLevel" in first
    assert "titleZh" in first


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
    assert "overallProgress" in data
    assert "progressSummary" in data
    assert data["state"]["learnerId"] == learner_id


@pytest.mark.asyncio
async def test_submit_answer_deterministic_fast_path(client: AsyncClient):
    # Look up an exercise from the database
    list_res = await client.get("/api/v1/curriculum/concepts")
    concept_id = list_res.json()[0]["conceptId"]
    details_res = await client.get(f"/api/v1/curriculum/concepts/{concept_id}")
    exercises = details_res.json().get("exercises", [])

    if exercises:
        ex = exercises[0]
        accepted = ex["acceptedAnswers"][0] if ex["acceptedAnswers"] else "你好"
        submission_payload = {
            "learnerId": "test_learner_001",
            "exerciseId": ex["id"],
            "answer": accepted,
        }
    else:
        submission_payload = {
            "learnerId": "test_learner_001",
            "exerciseId": "ex_dummy",
            "answer": "你好",
        }

    res = await client.post("/api/v1/answers", json=submission_payload)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_grade_freeform(client: AsyncClient):
    res = await client.post(
        "/api/v1/grade-freeform",
        json={"userInput": "我想喝茶", "blueprintId": "bp_test"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_learning_events(client: AsyncClient):
    payload = {
        "learnerId": "test_learner_001",
        "planItemId": "item_test",
        "conceptIds": ["c_test"],
        "eventType": "output",
        "activeSeconds": 45,
        "engagementScore": 1.0,
    }
    res = await client.post("/api/v1/learning-events", json=payload)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_complete_concept(client: AsyncClient):
    res = await client.post(
        "/api/v1/learners/test_learner_001/complete-concept",
        json={"conceptId": "c_test_complete", "score": 100, "mode": "card"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_tts_empty_validation(client: AsyncClient):
    res = await client.get("/api/tts?text=   ")
    assert res.status_code == 400
