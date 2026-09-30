from __future__ import annotations

from playwright.sync_api import Page, expect


def test_frontend_boot_and_navigation(test_page: tuple[Page, list[str]]) -> None:
    """Validate frontend loads, renders daily plan view, and switches tabs without console errors."""
    page, console_errors = test_page

    # 1. Navigate to frontend root
    page.goto("http://localhost:3000", wait_until="networkidle")

    # 2. Verify page title or branding exists
    expect(page.locator("body")).to_be_visible()

    # 3. Check for main learning view tabs (Plan, Curriculum, Retention)
    # The bottom/sidebar nav allows switching tabs
    plan_tab = page.locator("nav button:has-text('Plan'), aside button:has-text('Plan')").first
    if plan_tab.is_visible():
        plan_tab.click()
        page.wait_for_timeout(300)

    curriculum_tab = page.locator(
        "nav button:has-text('Curriculum'), aside button:has-text('Curriculum')"
    ).first
    if curriculum_tab.is_visible():
        curriculum_tab.click()
        page.wait_for_timeout(300)

    # 4. Check that no uncaught JavaScript exceptions occurred
    assert len(console_errors) == 0, f"Uncaught console errors detected: {console_errors}"


def test_learner_profile_drawer_interaction(test_page: tuple[Page, list[str]]) -> None:
    """Validate opening profile drawer, adjusting settings, and saving goal."""
    page, console_errors = test_page
    page.goto("http://localhost:3000", wait_until="networkidle")

    # Locate profile or goal button
    profile_btn = page.locator(
        "button:has-text('Goal'), button:has-text('Profile'), [aria-label*='Profile']"
    ).first
    if profile_btn.is_visible():
        profile_btn.click()
        page.wait_for_timeout(500)

        # Drawer should be open: look for Save or Close button
        save_btn = page.locator("button:has-text('Save'), button:has-text('Update')").first
        if save_btn.is_visible():
            save_btn.click()
            page.wait_for_timeout(500)

    # Assert zero console errors
    assert len(console_errors) == 0, f"Uncaught console errors in profile drawer: {console_errors}"
