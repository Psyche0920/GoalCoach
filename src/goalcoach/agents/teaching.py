"""Teaching Agent.

Generates or selects open-ended exercises, explains concepts, conducts dialogues,
adapts difficulty within a session, and provides immediate feedback. It consumes the
active plan and retrieved material but does not directly mutate learner persistence.

TODO(interface): implement ``Teacher`` using a validated structured model output and a
local fallback path.
"""

from goalcoach.agents.interfaces import Teacher

__all__ = ["Teacher"]
