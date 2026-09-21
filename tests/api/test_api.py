from __future__ import annotations

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/v1/learners/{learner_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_learner_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/v1/learners/some-learner-id")

    assert response.status_code == 200
    body = response.json()
    assert "state" in body
    assert "nextAction" in body


@pytest.mark.asyncio
async def test_get_learner_includes_id_in_response(client: AsyncClient) -> None:
    learner_id = "abc-123"
    response = await client.get(f"/api/v1/learners/{learner_id}")

    assert response.status_code == 200
    assert response.json()["state"]["learnerId"] == learner_id


# ---------------------------------------------------------------------------
# GET /api/v1/curriculum/concepts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_curriculum_concepts_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/v1/curriculum/concepts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# POST /api/v1/events
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_event_session_started(client: AsyncClient) -> None:
    payload = {
        "event_type": "SESSION_STARTED",
        "learner_id": "api-test-user-001",
        "payload": {},
    }
    response = await client.post("/api/v1/events", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "learnerId" in data
    assert "eventType" in data


@pytest.mark.asyncio
async def test_post_event_rejects_missing_fields(client: AsyncClient) -> None:
    response = await client.post("/api/v1/events", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_event_rejects_invalid_json_body(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/events",
        content="not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 404 for unknown routes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_route_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/nonexistent")

    assert response.status_code == 404
