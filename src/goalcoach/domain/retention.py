from __future__ import annotations

import math
from datetime import datetime


def decayed_retention(
    retention_at_review: float,
    last_reviewed_at: datetime,
    at: datetime,
    stability_days: float,
) -> float:
    """Exponential MVP forgetting curve.

    TODO(validation): tune the curve and update rules against learner evidence.
    """
    if stability_days <= 0:
        raise ValueError("stability_days must be positive")
    elapsed_days = max(0.0, (at - last_reviewed_at).total_seconds() / 86_400)
    return max(0.0, min(1.0, retention_at_review * math.exp(-elapsed_days / stability_days)))
