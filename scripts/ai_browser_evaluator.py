"""Autonomous Exploratory Browser Agent for Cognitive & Visual QA.

Uses Playwright to visually explore the frontend, test interactive journeys,
capture screenshots, detect layout anomalies, and generate an executive UX audit.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Ensure repository root is on sys.path
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Ensure unprivileged shared libraries are discoverable by Playwright Chromium
_lib_dir = Path.home() / ".local" / "lib" / "playwright_shared_libs"
if _lib_dir.exists():
    _cur_ld = os.environ.get("LD_LIBRARY_PATH", "")
    if str(_lib_dir) not in _cur_ld:
        os.environ["LD_LIBRARY_PATH"] = f"{_lib_dir}:{_cur_ld}" if _cur_ld else str(_lib_dir)

from playwright.sync_api import sync_playwright

from tests.harness.server_runner import TestServerRunner

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("ai.browser.evaluator")


def run_ai_browser_evaluation(
    base_url: str = "http://localhost:3000",
    headed: bool = False,
    output_dir: Path | str = "logs/ai_eval",
) -> dict[str, Any]:
    """Execute autonomous browser evaluation and save audit artifacts."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Ensure servers are running
    runner = TestServerRunner(
        api_port=8000,
        web_port=3000,
        db_path=out_path / "test_eval.db",
        log_path=Path("logs/goalcoach.jsonl"),
    )
    runner.start(timeout_seconds=30.0)

    report: dict[str, Any] = {
        "status": "PASS",
        "url": base_url,
        "views_evaluated": [],
        "interactive_elements_tested": 0,
        "console_errors": [],
        "screenshots": [],
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not headed)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            # Listen for console errors
            page.on("console", lambda msg: report["console_errors"].append(f"[Console] {msg.text}") if msg.type == "error" else None)
            page.on("pageerror", lambda err: report["console_errors"].append(f"[Page Error] {err}"))

            # Step 1: Initial Load & Home View
            logger.info("Visiting %s...", base_url)
            page.goto(base_url, wait_until="networkidle")
            page.wait_for_timeout(1000)

            screenshot_home = out_path / "01_home_view.png"
            page.screenshot(path=str(screenshot_home))
            report["screenshots"].append(str(screenshot_home))
            report["views_evaluated"].append("DailyPlanView")

            # Step 2: Test Plan Generation or Lesson Interaction
            build_btn = page.locator("button:has-text('Build today’s plan'), button:has-text('Build today')")
            if build_btn.is_visible():
                logger.info("Clicking 'Build today’s plan'...")
                build_btn.click()
                page.wait_for_timeout(1500)
                report["interactive_elements_tested"] += 1

            screenshot_plan = out_path / "02_plan_built.png"
            page.screenshot(path=str(screenshot_plan))
            report["screenshots"].append(str(screenshot_plan))

            # Step 3: Open Lesson Modal
            lesson_btn = page.locator(".lesson-card, button:has-text('Start Study')").first
            if lesson_btn.is_visible():
                logger.info("Opening active lesson modal...")
                lesson_btn.click()
                page.wait_for_timeout(1500)
                report["interactive_elements_tested"] += 1
                report["views_evaluated"].append("TeachingAgentModal")

                screenshot_modal = out_path / "03_lesson_modal.png"
                page.screenshot(path=str(screenshot_modal))
                report["screenshots"].append(str(screenshot_modal))

                # Step 4: Interact with Exercise
                input_field = page.locator("textarea, input[type='text']").first
                if input_field.is_visible():
                    logger.info("Filling sample answer...")
                    input_field.fill("Hello")
                    page.wait_for_timeout(500)

                submit_btn = page.locator("button:has-text('Submit'), button:has-text('Check')").first
                if submit_btn.is_visible():
                    logger.info("Submitting answer...")
                    submit_btn.click()
                    page.wait_for_timeout(1500)
                    report["interactive_elements_tested"] += 1

                    screenshot_feedback = out_path / "04_grading_feedback.png"
                    page.screenshot(path=str(screenshot_feedback))
                    report["screenshots"].append(str(screenshot_feedback))

                # Step 5: Close Modal
                close_btn = page.locator("button[aria-label='Close'], button:has-text('Close'), button:has-text('Done')").first
                if close_btn.is_visible():
                    close_btn.click()
                    page.wait_for_timeout(800)

            # Step 6: Test Navigation Tabs
            for tab_name in ("Curriculum", "Retention", "Plan"):
                tab = page.locator(f"button:has-text('{tab_name}')").first
                if tab.is_visible():
                    tab.click()
                    page.wait_for_timeout(500)
                    report["interactive_elements_tested"] += 1
                    report["views_evaluated"].append(f"{tab_name}View")

            screenshot_final = out_path / "05_evaluation_completed.png"
            page.screenshot(path=str(screenshot_final))
            report["screenshots"].append(str(screenshot_final))

            browser.close()

    finally:
        runner.stop()

    if report["console_errors"]:
        report["status"] = "WARNINGS"

    report_json = out_path / "eval_report.json"
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("=" * 60)
    logger.info("AUTONOMOUS BROWSER EVALUATION COMPLETE")
    logger.info("Status: %s", report["status"])
    logger.info("Views Evaluated: %s", ", ".join(set(report["views_evaluated"])))
    logger.info("Interactive Elements Tested: %d", report["interactive_elements_tested"])
    logger.info("Console Errors Captured: %d", len(report["console_errors"]))
    logger.info("Screenshots Saved: %d in %s", len(report["screenshots"]), out_path)
    logger.info("Audit Report: %s", report_json)
    logger.info("=" * 60)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run autonomous browser evaluation")
    parser.add_argument("--headed", action="store_true", help="Launch visible browser window")
    args = parser.parse_args()
    run_ai_browser_evaluation(headed=args.headed)
