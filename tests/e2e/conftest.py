"""Playwright E2E fixtures and lifecycle orchestrator.

Manages background test daemons, browser contexts, and strict console error interception.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

# Ensure unprivileged shared libraries are discoverable by Playwright Chromium
_lib_dir = Path.home() / ".local" / "lib" / "playwright_shared_libs"
if _lib_dir.exists():
    _cur_ld = os.environ.get("LD_LIBRARY_PATH", "")
    if str(_lib_dir) not in _cur_ld:
        os.environ["LD_LIBRARY_PATH"] = f"{_lib_dir}:{_cur_ld}" if _cur_ld else str(_lib_dir)

import pytest
from playwright.sync_api import BrowserContext, Page

from tests.harness.server_runner import TestServerRunner

logger = logging.getLogger("goalcoach.test.e2e")


@pytest.fixture(scope="session")
def test_servers() -> Generator[TestServerRunner, None, None]:
    """Ensure both FastAPI backend and Vite frontend are running with an ephemeral DB."""
    runner = TestServerRunner(
        api_port=8000,
        web_port=3000,
        db_path=Path(f"/tmp/test_goalcoach_e2e_{uuid4().hex[:8]}.db"),
        log_path=Path("logs/goalcoach.jsonl"),
    )
    runner.start(timeout_seconds=60.0)
    yield runner
    runner.stop()


@pytest.fixture(autouse=True)
def seed_default_goal(test_servers: TestServerRunner) -> None:
    """Ensure learner_001 has a valid goal configured before testing UI flows."""
    import httpx

    try:
        httpx.post(
            "http://127.0.0.1:8000/api/v1/events",
            json={
                "event_type": "GOAL_CREATED",
                "learner_id": "learner_001",
                "payload": {
                    "title": "HSK 1 Complete Goal",
                    "target_hsk_level": 1,
                    "daily_available_minutes": 20,
                    "timezone": "UTC",
                },
            },
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        logger.debug("Seeding default goal skipped or failed: %s", exc)


@pytest.fixture
def browser_context(
    context: BrowserContext,
    test_servers: TestServerRunner,
) -> Generator[BrowserContext, None, None]:
    """Configures browser tracing and headers for E2E tests."""
    context.set_extra_http_headers(
        {
            "X-Test-Run-ID": f"e2e_{uuid4().hex[:8]}",
            "X-Learner-Persona": "AutonomousPlaywrightAgent",
        }
    )
    yield context


@pytest.fixture
def test_page(
    browser_context: BrowserContext,
) -> Generator[tuple[Page, list[str]], None, None]:
    """Page fixture with zero-tolerance browser console error interception."""
    page = browser_context.new_page()
    console_errors: list[str] = []

    def handle_console_message(msg: Any) -> None:
        if msg.type == "error":
            # Ignore expected benign browser warnings like missing favicon or TTS cancelled
            text = str(msg.text)
            if "favicon.ico" not in text:
                console_errors.append(f"[Console Error] {text}")

    def handle_page_error(err: Any) -> None:
        console_errors.append(f"[Page Crash] {err}")

    page.on("console", handle_console_message)
    page.on("pageerror", handle_page_error)

    yield page, console_errors

    page.close()
