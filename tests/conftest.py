import sqlite3
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.dependencies import (
    get_grader_component,
    get_planning_worker,
    get_teaching_worker,
)
from apps.api.main import create_app
from goalcoach.infrastructure.config import Settings
from tests.fakes import FakeGraderComponent, FakePlanningWorker, FakeTeachingWorker


@pytest.fixture(scope="session", autouse=True)
def ensure_curriculum_db_initialized() -> None:
    """Ensure canonical SQLite Database #1 is seeded before any tests run."""
    db_path = Path("data/database1/goalcoach_hsk1_learning.db")
    sql_path = Path(
        "data/database1/GoalCoach_HSK1_Learning_DB_Package/data/goalcoach_hsk1_learning_db_sqlite.sql"
    )

    need_init = True
    if db_path.exists() and db_path.stat().st_size > 0:
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM curriculum_concepts")
                if cursor.fetchone()[0] > 0:
                    need_init = False
        except sqlite3.DatabaseError:
            need_init = True

    if need_init and sql_path.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sql_path, encoding="utf-8") as f:
            sql_script = f.read()
        with sqlite3.connect(db_path) as conn:
            conn.executescript(sql_script)


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> AsyncClient:
    application = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite:///{tmp_path / 'api-test.db'}",
            content_database_url="sqlite:///./data/database1/goalcoach_hsk1_learning.db",
        )
    )
    application.dependency_overrides[get_planning_worker] = FakePlanningWorker
    application.dependency_overrides[get_teaching_worker] = FakeTeachingWorker
    application.dependency_overrides[get_grader_component] = FakeGraderComponent
    async with application.router.lifespan_context(application):
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
