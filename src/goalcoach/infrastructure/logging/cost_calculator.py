"""Deterministic LLM inference cost calculator integrating genai-prices with static fallback rate cards."""

from __future__ import annotations

import logging
from typing import ClassVar

logger = logging.getLogger("goalcoach.agent.cost_calculator")

# Static fallback pricing per 1,000,000 tokens (USD) when offline or model is unknown to genai-prices
_FALLBACK_RATES_PER_MTOK: dict[str, tuple[float, float]] = {
    # model_keyword: (input_price_per_mtok, output_price_per_mtok)
    "qwen/qwen-2.5-72b": (0.12, 0.39),
    "qwen-2.5-72b": (0.12, 0.39),
    "ling-3.0-flash": (0.10, 0.20),
    "default": (0.15, 0.60),
}


class CostCalculator:
    """Calculates input, output, and total inference cost in USD."""

    _genai_prices_available: ClassVar[bool] = True

    @classmethod
    def calculate(
        cls,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cached_tokens: int = 0,
    ) -> tuple[float, float, float]:
        """Calculate (input_cost_usd, output_cost_usd, total_cost_usd).

        Deterministic rules:
        - provider == "ollama" or local providers deterministically return exactly (0.0, 0.0, 0.0).
        - OpenRouter and remote providers leverage genai-prices, falling back to static rate cards
          if the snapshot lookup fails or the system is operating completely offline.
        """
        if not provider or provider.lower() in ("ollama", "local", "deterministic"):
            return 0.0, 0.0, 0.0

        if prompt_tokens <= 0 and completion_tokens <= 0:
            return 0.0, 0.0, 0.0

        # Attempt dynamic pricing via genai_prices
        if cls._genai_prices_available:
            try:
                from genai_prices import Usage, calc_price

                # Note: genai_prices requires input_tokens and output_tokens (NOT prompt_tokens/completion_tokens)
                usage = Usage(input_tokens=prompt_tokens, output_tokens=completion_tokens)
                result = calc_price(usage, model, provider_id=provider.lower())
                input_cost = float(result.input_price)
                output_cost = float(result.output_price)
                total_cost = float(result.total_price)
                return round(input_cost, 8), round(output_cost, 8), round(total_cost, 8)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "Dynamic pricing failed via genai-prices for %s/%s (%s); falling back to rate card.",
                    provider,
                    model,
                    exc,
                )

        # Static rate card fallback
        return cls._calculate_from_rate_card(model, prompt_tokens, completion_tokens)

    @staticmethod
    def _calculate_from_rate_card(
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> tuple[float, float, float]:
        """Compute costs using static rate cards per million tokens."""
        matched_rate: tuple[float, float] = _FALLBACK_RATES_PER_MTOK["default"]
        clean_model = model.lower()
        for key, rate in _FALLBACK_RATES_PER_MTOK.items():
            if key != "default" and key in clean_model:
                matched_rate = rate
                break

        input_rate_per_tok = matched_rate[0] / 1_000_000.0
        output_rate_per_tok = matched_rate[1] / 1_000_000.0

        input_cost = round(prompt_tokens * input_rate_per_tok, 8)
        output_cost = round(completion_tokens * output_rate_per_tok, 8)
        total_cost = round(input_cost + output_cost, 8)

        return input_cost, output_cost, total_cost


__all__ = ["CostCalculator"]
