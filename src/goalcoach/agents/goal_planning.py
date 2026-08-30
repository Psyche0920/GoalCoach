"""Goal Planning Agent.

Responsibilities:
- decompose a new or changed goal into milestones;
- create the initial diagnostic plan;
- regenerate daily plans from mastery, retention, errors, review dates, and study time;
- balance review, remediation, and new content.

TODO(interface): implement ``GoalPlanner`` after planning cadence and curriculum data are
confirmed. Simple planning should remain deterministic; use an LLM only when flexible
reasoning demonstrably improves the plan.
"""

from goalcoach.agents.interfaces import GoalPlanner

__all__ = ["GoalPlanner"]
