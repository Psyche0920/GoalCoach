import asyncio
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from goalcoach.domain.models import LearnerState, LearningGoal, ConceptMastery
from goalcoach.infrastructure.llm.pydantic_ai_models import get_openrouter_model

console = Console()

class TurnResponse(BaseModel):
    reply: str = Field(description="Explanations, exercises, or feedback with Pinyin")
    concept_id: str = Field(description="Active HSK concept key being targeted")
    is_evaluating_answer: bool = Field(description="True if evaluating user's previous attempt")
    passed: bool | None = Field(default=None, description="True if answer was correct")
    hint_given: bool = Field(default=False)

@dataclass
class TutorDeps:
    state: LearnerState

agent = Agent(
    model=get_openrouter_model(),
    deps_type=TutorDeps,
    result_type=TurnResponse,
    system_prompt=(
        "You are the GoalCoach Chinese Teacher, an adaptive HSK1 Chinese tutor. ",
        "Always interact with the student in English, but provide Chinese examples with Pinyin. ",
        "Lead the student through their targeted daily concepts. ",
        "Do not lecture at length: present a concept, provide an example with Pinyin, ",
        "and immediately ask the student to formulate a sentence. ",
        "If they make an error, supply an intuitive hint rather than giving the solution.",
    ),
)

@agent.tool
def get_current_focus(ctx: RunContext[TutorDeps]) -> str:
    """Fetches the concept needing immediate remediation or next study."""
    # Deterministic prioritization based on state
    weak_concepts = [
        c.concept_id for c in ctx.deps.state.mastery.values() if c.mastery_score < 0.70
    ]
    return f"Priority concepts for this session: {weak_concepts or ['hsk1_greeting']}"

async def main():
    console.print(Panel("[bold green]GoalCoach: Teaching Agent Terminal Prototype[/bold green]"))
    
    # Initialize mock state
    mock_state = LearnerState(
        goal=LearningGoal(title="HSK1", target_hsk_level=1),
        mastery={"hsk1_question_ma": ConceptMastery(concept_id="hsk1_question_ma", mastery_score=0.4)},
    )
    deps = TutorDeps(state=mock_state)

    # Initial tutor prompt
    prompt = "Initialize session based on my weak concepts."
    message_history = []

    while True:
        with console.status("[bold cyan]Tutor is thinking...[/bold cyan]"):
            result = await agent.run(prompt, deps=deps, message_history=message_history)
            message_history = result.all_messages()
            data: TurnResponse = result.data

        # Update deterministic state if grading occurred
        if data.is_evaluating_answer and data.passed is not None:
            score_delta = 0.25 if data.passed else -0.10
            current = mock_state.mastery.get(data.concept_id)
            if current:
                current.mastery_score = max(0.0, min(1.0, current.mastery_score + score_delta))

        # Display Turn
        console.print(Panel(data.reply, title=f"[bold]Tutor (Focus: {data.concept_id})[/bold]"))
        
        # Display Current State Metrics
        table = Table(title="Learner State Tracking", show_header=True)
        table.add_column("Concept")
        table.add_column("Mastery Score")
        for cid, m in mock_state.mastery.items():
            table.add_row(cid, f"{m.mastery_score:.2f}")
        console.print(table)

        user_input = Prompt.ask("\n[bold yellow]Your Response[/bold yellow]")
        if user_input.lower() in ("exit", "quit"):
            break
        prompt = user_input

if __name__ == "__main__":
    asyncio.run(main())