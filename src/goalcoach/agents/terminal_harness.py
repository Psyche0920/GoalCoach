"""Interactive Rich Terminal Harness demonstrating the GoalCoach closed-loop agentic learning system.

Runs the complete closed-loop lifecycle:
1. Initialize persistent state (SQLite WAL).
2. GOAL_CREATED -> Planning Agent generates daily plan.
3. SESSION_STARTED -> Teaching Agent emits TeachingAction.
4. Learner responds (or requests help).
5. ANSWER_SUBMITTED -> Grader evaluates against rubric -> Progress Service mutates state.
6. If needs_replanning == True -> Orchestrator triggers Planning Agent to re-allocate budget.
7. Render live Rich state tables.
"""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from goalcoach.agents.grader_component import GraderComponent
from goalcoach.agents.planning_agent import PlanningWorker
from goalcoach.agents.teaching_agent import TeachingWorker
from goalcoach.application.orchestrator import DeterministicOrchestrator
from goalcoach.application.progress_service import ProgressService
from goalcoach.domain.enums import EventType
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.persistence.content_service import ContentService
from goalcoach.infrastructure.persistence.database import (
    create_learner_schema,
    create_session_factory,
)
from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    SqliteLearnerRepository,
)

console = Console()


def render_state_table(state) -> Table:
    """Render a formatted Rich table displaying current learner state metrics."""
    table = Table(
        title="[bold green]Authoritative Learner State (SQLite WAL)[/bold green]", show_header=True
    )
    table.add_column("Concept ID", style="cyan")
    table.add_column("Mastery", justify="right", style="magenta")
    table.add_column("Retention", justify="right", style="yellow")
    table.add_column("Interval (Days)", justify="right")
    table.add_column("Evidence", justify="right")
    table.add_column("Next Review", justify="center")

    for cid, m in state.mastery.items():
        next_rev = m.next_review_at.strftime("%Y-%m-%d") if m.next_review_at else "Now"
        table.add_row(
            cid,
            f"{m.mastery_score:.2f}",
            f"{m.retention_score:.2f}",
            f"{m.interval_days:.1f}",
            str(m.evidence_count),
            next_rev,
        )

    if not state.mastery:
        table.add_row("No concepts studied yet", "0.00", "1.00", "1.0", "0", "N/A")

    return table


def render_error_table(state) -> Table | None:
    """Render table of logged recurring error codes."""
    if not state.error_profile:
        return None
    table = Table(title="[bold red]Detected Error Taxonomy Profile[/bold red]", show_header=True)
    table.add_column("Error Code", style="red")
    table.add_column("Target Concept", style="cyan")
    table.add_column("Occurrences", justify="right", style="bold yellow")

    for err in state.error_profile:
        table.add_row(err.code, err.concept_id, str(err.occurrences))
    return table


async def main() -> None:
    console.print(
        Panel.fit(
            "[bold green]GoalCoach: Closed State-Driven Agentic System[/bold green]\n"
            "[dim]HSK1 Adaptive Closed Loop Prototype[/dim]",
            border_style="green",
        )
    )

    settings = Settings()
    learner_factory = create_session_factory(settings.database_url)
    create_learner_schema(learner_factory)
    learner_repo = SqliteLearnerRepository(learner_factory)

    content_factory = create_session_factory(settings.content_database_url)
    content_repo = ContentRepository(content_factory)
    content_service = ContentService(content_repo)

    progress_service = ProgressService(learner_repo=learner_repo)
    planning_worker = PlanningWorker()
    teaching_worker = TeachingWorker()
    grader_worker = GraderComponent()

    orchestrator = DeterministicOrchestrator(
        learner_repo=learner_repo,
        content_service=content_service,
        progress_service=progress_service,
        planning_worker=planning_worker,
        teaching_worker=teaching_worker,
        grader_worker=grader_worker,
    )

    learner_id = "terminal_learner_001"

    # Step 1: GOAL_CREATED
    with console.status("[bold cyan]Configuring Goal & Planning Curriculum...[/bold cyan]"):
        goal_response = await orchestrator.handle_event(
            event_type=EventType.GOAL_CREATED,
            learner_id=learner_id,
            payload={
                "title": "HSK 1 Complete Goal",
                "target_hsk_level": 1,
                "daily_available_minutes": 20,
                "context_interests": ["Travel", "Daily Life"],
            },
        )

    console.print(
        Panel(
            f"[bold]Daily Plan Generated:[/bold] {goal_response.daily_plan.rationale}\n"
            f"[dim]Total Minutes: {sum(it.estimated_minutes for it in goal_response.daily_plan.items)}m[/dim]",
            title="[bold green]Planning Agent Output[/bold green]",
            border_style="cyan",
        )
    )

    # Study loop
    while True:
        # Step 2: SESSION_STARTED
        with console.status("[bold cyan]Starting Learning Session...[/bold cyan]"):
            turn_response = await orchestrator.handle_event(
                event_type=EventType.SESSION_STARTED,
                learner_id=learner_id,
                payload={},
            )

        teaching_action = turn_response.teaching_action
        concept_id = teaching_action.concept_id
        exercise_payload = teaching_action.exercise_payload
        if not exercise_payload or not exercise_payload.get("exercise_id"):
            raise RuntimeError(f"Teaching action for {concept_id} has no curriculum exercise")

        console.print(
            Panel(
                f"[bold yellow]Modality:[/bold yellow] {teaching_action.action_kind.value}\n\n"
                f"{teaching_action.content}\n\n"
                f"[dim]Pinyin: {teaching_action.pinyin or 'N/A'}[/dim]",
                title=f"[bold cyan]Coach Baobao (Focus: {concept_id})[/bold cyan]",
                border_style="yellow",
            )
        )

        console.print(
            Panel(
                f"[bold]{exercise_payload.get('instruction', '')}[/bold]\n\n"
                f"{exercise_payload.get('prompt', '')}",
                title="[bold green]Practice[/bold green]",
                border_style="green",
            )
        )

        console.print(
            "[dim]Commands: Type your Chinese answer, or 'help' for guidance, or 'exit' to quit.[/dim]"
        )
        user_input = Prompt.ask("\n[bold green]Your Input[/bold green]").strip()

        if user_input.lower() in ("exit", "quit"):
            console.print(
                "[bold yellow]Exiting study session. All progress saved to SQLite WAL.[/bold yellow]"
            )
            break

        if user_input.lower() == "help":
            with console.status("[bold cyan]Coach is adapting strategy...[/bold cyan]"):
                help_response = await orchestrator.handle_event(
                    event_type=EventType.HELP_REQUESTED,
                    learner_id=learner_id,
                    payload={
                        "concept_id": concept_id,
                        "learner_query": "I am confused, please give me a hint.",
                    },
                )
            help_action = help_response.teaching_action
            if help_action.exercise_payload:
                exercise_payload = help_action.exercise_payload
            console.print(
                Panel(
                    f"[bold yellow]Adapted Modality:[/bold yellow] {help_action.action_kind.value}\n\n"
                    f"{help_action.content}",
                    title=f"[bold magenta]Coach Guidance ({concept_id})[/bold magenta]",
                    border_style="magenta",
                )
            )
            user_input = Prompt.ask("\n[bold green]Your Answer[/bold green]").strip()
            if user_input.lower() in ("exit", "quit"):
                break

        # Step 3: ANSWER_SUBMITTED
        with console.status("[bold cyan]Grading submission & reducing state...[/bold cyan]"):
            answer_response = await orchestrator.handle_event(
                event_type=EventType.ANSWER_SUBMITTED,
                learner_id=learner_id,
                payload={
                    "exercise_id": str(exercise_payload["exercise_id"]),
                    "concept_id": concept_id,
                    "answer": user_input,
                },
            )

        grade = answer_response.grading_result
        badge = (
            "[bold green]PASS[/bold green]" if grade.passed_gates else "[bold red]FAIL[/bold red]"
        )
        console.print(
            Panel(
                f"Status: {badge} (Grammar: {grade.scores.grammatical_correctness:.2f}, Semantic: {grade.scores.semantic_precision:.2f})\n\n"
                f"{grade.feedback}\n"
                f"[dim]Detected Errors: {grade.detected_errors or 'None'}[/dim]",
                title=f"[bold]Grading Evidence ({grade.grader_version})[/bold]",
                border_style="green" if grade.passed_gates else "red",
            )
        )

        # Check if replanning occurred
        if answer_response.replanned:
            console.print(
                Panel(
                    "[bold yellow]ALERT: Repeated error threshold reached![/bold yellow]\n"
                    "The Planning Agent has automatically adapted today's queue to slot targeted remediation.",
                    border_style="yellow",
                )
            )

        # Render State Tables
        state = answer_response.state
        console.print(render_state_table(state))
        err_table = render_error_table(state)
        if err_table:
            console.print(err_table)


if __name__ == "__main__":
    asyncio.run(main())
