"""GoalCoach's state-aware reasoning agents and isolated grader component."""

from goalcoach.agents.grader_component import GraderComponent
from goalcoach.agents.planning_agent import PlanningWorker
from goalcoach.agents.teaching_agent import TeachingWorker

TeachingAgent = TeachingWorker
GradingAgent = GraderComponent

__all__ = [
    "GraderComponent",
    "GradingAgent",
    "PlanningWorker",
    "TeachingAgent",
    "TeachingWorker",
]
