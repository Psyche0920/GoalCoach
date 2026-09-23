import os
import sqlite3
from pathlib import Path

os.environ["GOALCOACH_OFFLINE_LLM_FALLBACK"] = "true"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.main import app


@pytest.fixture(scope="session", autouse=True)
def ensure_curriculum_db_initialized() -> None:
    """Ensure canonical SQLite Database #1 is seeded before any tests run."""
    db_path = Path("data/database1/goalcoach_hsk1_learning.db")
    sql_path = Path(
        "data/database1/GoalCoach_HSK1_Learning_DB_Package/data/goalcoach_hsk1_learning_db_sqlite.sql"
    )

    need_init = True
    if db_path.exists() and db_path.stat().st_size > 0:
        if sql_path.exists() and sql_path.stat().st_mtime > db_path.stat().st_mtime:
            need_init = True
        else:
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT count(*) FROM curriculum_concepts")
                    if cursor.fetchone()[0] > 0:
                        need_init = False
            except Exception:
                need_init = True

    if need_init and sql_path.exists():
        if db_path.exists():
            db_path.unlink()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sql_path, encoding="utf-8") as f:
            sql_script = f.read()
        with sqlite3.connect(db_path) as conn:
            conn.executescript(sql_script)


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
