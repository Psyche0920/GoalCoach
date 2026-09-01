"""Deterministic spaced repetition forgetting curve algorithms and retention mathematics."""

from __future__ import annotations

import math
from datetime import datetime, timezone


def calculate_retention(
    retention_at_review: float,
    last_reviewed_at: datetime,
    at: datetime | None = None,
    decay_lambda: float = 0.05,
) -> float:
    """Computes decayed retention probability R = R_0 * exp(-lambda * delta_t).

    Args:
        retention_at_review: Initial retention probability score at the last review event (0.0 - 1.0).
        last_reviewed_at: Timestamp when the concept was last reviewed.
        at: Target evaluation timestamp. Defaults to UTC now if omitted.
        decay_lambda: Concept-specific exponential decay constant (> 0.0). Defaults to 0.05.

    Returns:
        Decayed retention probability clamped strictly to [0.0, 1.0].

    Raises:
        ValueError: If decay_lambda is non-positive.
    """
    if decay_lambda <= 0:
        raise ValueError("decay_lambda must be strictly positive")

    target_time = at or datetime.now(timezone.utc)
    if last_reviewed_at.tzinfo is None:
        last_reviewed_at = last_reviewed_at.replace(tzinfo=timezone.utc)
    if target_time.tzinfo is None:
        target_time = target_time.replace(tzinfo=timezone.utc)

    elapsed_seconds = max(0.0, (target_time - last_reviewed_at).total_seconds())
    elapsed_days = elapsed_seconds / 86_400.0

    decayed = retention_at_review * math.exp(-decay_lambda * elapsed_days)
    return max(0.0, min(1.0, decayed))


def decayed_retention(
    retention_at_review: float,
    last_reviewed_at: datetime,
    at: datetime,
    stability_days: float,
) -> float:
    """Exponential forgetting curve parameterized by memory stability in days.

    Args:
        retention_at_review: Initial retention probability at last review.
        last_reviewed_at: Timestamp when last reviewed.
        at: Evaluation timestamp.
        stability_days: Number of days over which retention decays by a factor of 1/e (> 0.0).

    Returns:
        Decayed retention probability clamped to [0.0, 1.0].

    Raises:
        ValueError: If stability_days is non-positive.
    """
    if stability_days <= 0:
        raise ValueError("stability_days must be positive")
    return calculate_retention(
        retention_at_review=retention_at_review,
        last_reviewed_at=last_reviewed_at,
        at=at,
        decay_lambda=1.0 / stability_days,
    )
