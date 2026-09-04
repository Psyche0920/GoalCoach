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
async def test_get_learner_returns_501_stub(client: AsyncClient) -> None:
    response = await client.get("/api/v1/learners/some-learner-id")

    assert response.status_code == 501
    body = response.json()
    assert body["detail"].startswith("TODO(interface): connect LearnerRepository")


@pytest.mark.asyncio
async def test_get_learner_includes_id_in_detail(client: AsyncClient) -> None:
    learner_id = "abc-123"
    response = await client.get(f"/api/v1/learners/{learner_id}")

    assert response.status_code == 501
    assert learner_id in response.json()["detail"]


# ---------------------------------------------------------------------------
# POST /api/v1/answers
# ---------------------------------------------------------------------------

VALID_ANSWER_PAYLOAD = {
    "learner_id": "550e8400-e29b-41d4-a716-446655440000",
    "exercise_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "answer": "你好",
}


@pytest.mark.asyncio
async def test_submit_answer_returns_501_stub(client: AsyncClient) -> None:
    response = await client.post("/api/v1/answers", json=VALID_ANSWER_PAYLOAD)

    assert response.status_code == 501
    body = response.json()
    assert body["detail"].startswith("TODO(interface): connect learning loop")


@pytest.mark.asyncio
async def test_submit_answer_rejects_empty_answer(client: AsyncClient) -> None:
    payload = {**VALID_ANSWER_PAYLOAD, "answer": ""}
    response = await client.post("/api/v1/answers", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_answer_rejects_missing_fields(client: AsyncClient) -> None:
    response = await client.post("/api/v1/answers", json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_answer_rejects_invalid_uuid(client: AsyncClient) -> None:
    payload = {**VALID_ANSWER_PAYLOAD, "learner_id": "not-a-uuid"}
    response = await client.post("/api/v1/answers", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_answer_rejects_invalid_json_body(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/answers",
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
