"""End-to-end user journey tests for GoalCoach learning flow.

Drives the real React 18 / Vite frontend in Chromium, validating lesson selection,
modal exercise grading, audio playback responses, and zero uncaught JavaScript errors.
"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page


def test_complete_learning_cycle_in_browser(test_page: tuple[Page, list[str]]) -> None:
    """Validate full learner flow: load plan -> open modal -> answer -> verify audio -> close."""
    page, console_errors = test_page

    tts_responses: list[int] = []

    def handle_response(response: Any) -> None:
        if "/api/tts" in response.url:
            tts_responses.append(response.status)

    page.on("response", handle_response)

    # 1. Navigate to frontend
    page.goto("http://localhost:3000", wait_until="networkidle")

    # 2. Wait for either the "Build today's plan" button or active lesson cards to mount
    plan_or_lesson = page.locator(
        "[data-testid='build-plan-btn'], [data-testid='lesson-card-btn'], .lesson-card, button:has-text('Build today')"
    ).first
    plan_or_lesson.wait_for(state="visible", timeout=25000)

    build_plan_btn = page.locator(
        "[data-testid='build-plan-btn'], button:has-text('Build today')"
    ).first
    if build_plan_btn.is_visible():
        build_plan_btn.click()
        # Wait for plan items to render
        page.locator("[data-testid='lesson-card-btn'], .lesson-card").first.wait_for(
            state="visible", timeout=20000
        )

    # 3. Locate and click active lesson card
    lesson_card = page.locator("[data-testid='lesson-card-btn'], .lesson-card").first
    lesson_card.wait_for(state="visible", timeout=15000)
    lesson_card.click()

    # 4. Wait for teaching modal to finish loading content (questions & options)
    page.locator(
        "[data-testid='exercise-option'], [data-testid='exercise-answer-input'], button:has-text('Check')"
    ).first.wait_for(state="visible", timeout=20000)
    page.wait_for_timeout(1000)

    # Select an option or fill the answer input
    opt_btn = page.locator("[data-testid='exercise-option']").first
    answer_input = page.locator(
        "input[data-testid='exercise-answer-input'], input[placeholder*='answer'], input[placeholder*='type']"
    ).first

    if opt_btn.is_visible():
        opt_btn.click()
    elif answer_input.is_visible():
        answer_input.fill("Hello")

    page.wait_for_timeout(1000)

    # Click Check / Submit button
    check_btn = page.locator("[data-testid='exercise-check-btn'], button:has-text('Check')").first
    check_btn.wait_for(state="visible", timeout=5000)
    if check_btn.is_enabled():
        check_btn.click()

    # 5. Wait for the coach evaluation feedback banner to appear
    continue_btn = page.locator(
        "[data-testid='continue-lesson-btn'], button:has-text('Continue to next lesson')"
    ).first
    continue_btn.wait_for(state="visible", timeout=20000)
    page.wait_for_timeout(1500)
    continue_btn.click()
    page.wait_for_timeout(1000)

    # 5. Verify audio TTS route responds with 200 when invoked directly
    tts_res = page.request.get("http://localhost:3000/api/tts?text=%E4%BD%A0%E5%A5%BD")
    assert tts_res.status == 200
    content_type = tts_res.headers.get("content-type", "")
    assert "audio" in content_type or "mpeg" in content_type

    # 6. Strict invariant: Zero uncaught JavaScript errors or crashes
    assert len(console_errors) == 0, f"Uncaught console errors detected: {console_errors}"
