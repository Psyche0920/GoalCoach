# API Endpoint Testing Guide

## Quick Start

```bash
.venv/bin/python -m pytest tests/api/test_api.py -v
```

## Project Conventions

- **Framework**: pytest + pytest-asyncio (auto mode)
- **HTTP Client**: httpx `AsyncClient` with `ASGITransport` (in-memory, no real server)
- **Test location**: `tests/api/test_api.py`
- **Shared fixtures**: `tests/conftest.py`

---

## Fixture Setup

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from apps.api.main import app

@pytest.fixture
def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")
```

---

## Test Patterns

### 1. Success Response

```python
@pytest.mark.asyncio
async def test_get_learner_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/v1/learners/some-id")

    assert response.status_code == 200
    assert response.json()["learner_id"] == "some-id"
```

### 2. Stub / Not-Yet-Implemented (501)

```python
@pytest.mark.asyncio
async def test_get_learner_returns_501_stub(client: AsyncClient) -> None:
    response = await client.get("/api/v1/learners/some-id")

    assert response.status_code == 501
    assert "TODO" in response.json()["detail"]
```

### 3. POST with Valid Body

```python
@pytest.mark.asyncio
async def test_submit_answer_returns_501(client: AsyncClient) -> None:
    payload = {
        "learner_id": "550e8400-e29b-41d4-a716-446655440000",
        "exercise_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "answer": "你好",
    }
    response = await client.post("/api/v1/answers", json=payload)

    assert response.status_code == 501
```

### 4. Validation Error (422) — Missing Fields

```python
@pytest.mark.asyncio
async def test_submit_answer_rejects_empty_body(client: AsyncClient) -> None:
    response = await client.post("/api/v1/answers", json={})

    assert response.status_code == 422
```

### 5. Validation Error (422) — Invalid Field Value

```python
@pytest.mark.asyncio
async def test_submit_answer_rejects_empty_answer(client: AsyncClient) -> None:
    payload = {
        "learner_id": "550e8400-e29b-41d4-a716-446655440000",
        "exercise_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "answer": "",  # min_length=1 required
    }
    response = await client.post("/api/v1/answers", json=payload)

    assert response.status_code == 422
```

### 6. Validation Error (422) — Wrong Type

```python
@pytest.mark.asyncio
async def test_submit_answer_rejects_invalid_uuid(client: AsyncClient) -> None:
    payload = {
        "learner_id": "not-a-uuid",  # must be valid UUID
        "exercise_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "answer": "你好",
    }
    response = await client.post("/api/v1/answers", json=payload)

    assert response.status_code == 422
```

### 7. Malformed Request Body

```python
@pytest.mark.asyncio
async def test_submit_answer_rejects_invalid_json(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/answers",
        content="not json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
```

### 8. 404 for Unknown Routes

```python
@pytest.mark.asyncio
async def test_unknown_route_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/nonexistent")

    assert response.status_code == 404
```

---

## Response Body Assertions

```python
# Check specific field
assert response.json()["status"] == "ok"

# Check field exists
assert "detail" in response.json()

# Check nested field
assert response.json()["scores"]["grammatical_correctness"] >= 0.0

# Check list length
assert len(response.json()["items"]) == 3

# Check error detail message contains something
assert "TODO" in response.json()["detail"]
```

---

## Common HTTP Status Codes

| Code | Meaning | When to Expect |
|------|---------|----------------|
| 200 | OK | Successful GET/PUT |
| 201 | Created | Successful POST |
| 404 | Not Found | Unknown route or missing resource |
| 422 | Unprocessable Entity | Pydantic validation error |
| 501 | Not Implemented | Stub endpoint (TODO) |

---

## Adding a New Endpoint Test

1. Read the endpoint definition in `apps/api/main.py`
2. Check the request/response models in `src/goalcoach/domain/models.py`
3. Add a test function following the patterns above
4. Run: `.venv/bin/python -m pytest tests/api/test_api.py -v`

---

## Checklist for Each Endpoint

- [ ] Happy path returns correct status code
- [ ] Response body matches `response_model`
- [ ] Missing required fields return 422
- [ ] Invalid field types return 422
- [ ] Boundary values tested (empty strings, zero, max length)
- [ ] Path parameters work correctly
- [ ] Query parameters validated (if any)
- [ ] Auth required? Test 401/403 (when implemented)
