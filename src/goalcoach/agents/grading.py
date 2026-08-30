"""Chinese free-form Grader component.

The proposal treats grading as a reasoning-heavy component, though not necessarily a
separate autonomous agent. It must return the six rubric dimensions, gating decision,
confidence, detected errors, evidence, and grader version as structured output.

TODO(interface): implement ``Grader`` only with schema validation and test it against
the human-labelled HSK1 benchmark before allowing grades to drive mastery.
"""

from goalcoach.agents.interfaces import Grader

__all__ = ["Grader"]
