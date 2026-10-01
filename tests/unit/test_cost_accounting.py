"""Unit tests for precision inference cost calculation and session budget tracking."""

from __future__ import annotations

import pytest

from goalcoach.infrastructure.logging.budget_tracker import BudgetTracker
from goalcoach.infrastructure.logging.cost_calculator import CostCalculator


def test_ollama_zero_cost() -> None:
    """Verify local Ollama inference always resolves deterministically to exactly $0.0."""
    in_cost, out_cost, total_cost = CostCalculator.calculate(
        provider="ollama",
        model="unsloth/gemma-4-12b-it-GGUF",
        prompt_tokens=1500,
        completion_tokens=400,
    )
    assert in_cost == 0.0
    assert out_cost == 0.0
    assert total_cost == 0.0


def test_zero_tokens_zero_cost() -> None:
    """Verify zero tokens produce zero cost."""
    in_cost, out_cost, total_cost = CostCalculator.calculate(
        provider="openrouter",
        model="qwen/qwen-2.5-72b-instruct",
        prompt_tokens=0,
        completion_tokens=0,
    )
    assert in_cost == 0.0
    assert out_cost == 0.0
    assert total_cost == 0.0


def test_openrouter_cost_calculation() -> None:
    """Verify OpenRouter models compute precision float costs via genai-prices."""
    # 1,000 prompt tokens and 500 completion tokens for Qwen 2.5 72B
    in_cost, out_cost, total_cost = CostCalculator.calculate(
        provider="openrouter",
        model="qwen/qwen-2.5-72b-instruct",
        prompt_tokens=1000,
        completion_tokens=500,
    )
    assert in_cost > 0.0
    assert out_cost > 0.0
    assert round(in_cost + out_cost, 8) == round(total_cost, 8)
    # Expected: $0.12/MTok input -> 1000 * 0.00000012 = 0.00012
    # Expected: $0.39/MTok output -> 500 * 0.00000039 = 0.000195
    # Total = 0.000315
    assert abs(total_cost - 0.000315) < 1e-6


def test_rate_card_fallback_unknown_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify static rate-card fallback executes when dynamic lookup fails."""
    # Simulate genai-prices failure
    monkeypatch.setattr(CostCalculator, "_genai_prices_available", False)

    in_cost, out_cost, total_cost = CostCalculator.calculate(
        provider="openrouter",
        model="custom-finetuned-ling",
        prompt_tokens=2000,
        completion_tokens=1000,
    )
    assert in_cost > 0.0
    assert out_cost > 0.0
    assert round(in_cost + out_cost, 8) == round(total_cost, 8)


def test_budget_tracker_accumulation_and_threshold() -> None:
    """Verify BudgetTracker accumulates spend and flags ceiling violations."""
    session_id = "test-session-budget-123"
    BudgetTracker.reset(session_id)

    # Accumulate 0.20 (limit is 0.50)
    cum_1, exceeded_1 = BudgetTracker.accumulate(session_id, 0.20, limit_usd=0.50)
    assert cum_1 == 0.20
    assert exceeded_1 is False

    # Accumulate another 0.25 (total 0.45, still under 0.50)
    cum_2, exceeded_2 = BudgetTracker.accumulate(session_id, 0.25, limit_usd=0.50)
    assert cum_2 == 0.45
    assert exceeded_2 is False

    # Accumulate 0.10 (total 0.55, exceeds 0.50 limit)
    cum_3, exceeded_3 = BudgetTracker.accumulate(session_id, 0.10, limit_usd=0.50)
    assert cum_3 == 0.55
    assert exceeded_3 is True

    # Check getter
    assert BudgetTracker.get_cost(session_id) == 0.55

    # Reset
    BudgetTracker.reset(session_id)
    assert BudgetTracker.get_cost(session_id) == 0.0
