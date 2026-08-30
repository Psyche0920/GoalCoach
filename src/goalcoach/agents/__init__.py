"""Named GoalCoach components from the project proposal.

The orchestrator lives in ``goalcoach.application`` because it is a deterministic
controller, not an LLM agent.
"""

from .interfaces import GoalPlanner, Grader, ProgressTracker, Retriever, Teacher

__all__ = ["GoalPlanner", "Grader", "ProgressTracker", "Retriever", "Teacher"]
