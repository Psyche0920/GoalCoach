"""Progress & Mastery Agent.

This component answers “What is the learner's current state?” It updates mastery,
retention, recurring errors, review dates, and overall progress after grading.

Its numerical updates are deterministic and should run outside the critical learner
response path. TODO(validation): confirm mastery thresholds, evidence requirements,
forgetting-curve parameters, and plan-invalidation policy.
"""

from goalcoach.agents.interfaces import ProgressTracker
from goalcoach.domain.retention import decayed_retention

__all__ = ["ProgressTracker", "decayed_retention"]
