"""English command-line interface for the materials workbench."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from pydantic import ValidationError

from goalcoach.materials.agents import ModelSettings, PydanticAgentRunner
from goalcoach.materials.ingestion import IngestionService
from goalcoach.materials.models import Brief, MaterialsError, Source
from goalcoach.materials.publication import PublicationService
from goalcoach.materials.store import Workbench
from goalcoach.materials.workflow import ProductionWorkflow


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Evidence-grounded teaching-material production")
    root.add_argument("--db", type=Path, default=Path("materials-workspace/workbench.db"))
    root.add_argument(
        "--settings-file",
        type=Path,
        help="Separate materials environment file; never defaults to GoalCoach's .env",
    )
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("status")
    usage = commands.add_parser(
        "usage", help="Report recorded token usage and configured-rate cost estimates"
    )
    usage.add_argument("--run-id")
    commands.add_parser(
        "check-model", help="Perform a minimal live structured-output connectivity check"
    )
    serve = commands.add_parser("serve", help="Open a loopback-only human review dashboard")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--output", type=Path, default=Path("materials-workspace/releases"))
    metadata = commands.add_parser(
        "source-metadata", help="Inspect public social metadata without granting content-use rights"
    )
    metadata.add_argument("url")
    ingest = commands.add_parser(
        "import", help="Import an authorized UTF-8 text or subtitle export"
    )
    ingest.add_argument("--source", type=Path, required=True)
    ingest.add_argument("--file", type=Path, required=True)
    input_format = ingest.add_mutually_exclusive_group()
    input_format.add_argument(
        "--subtitles",
        action="store_true",
        help="Import an authorized SRT, VTT or platform subtitle JSON export",
    )
    input_format.add_argument(
        "--pdf-page",
        action="append",
        type=int,
        help="Import an explicit 1-based PDF page; repeat for up to 20 pages",
    )
    collect = commands.add_parser("collect", help="Collect a permitted static HTML or text URL")
    collect.add_argument("--source", type=Path, required=True)
    collect.add_argument("--allow-host", action="append", required=True)
    run = commands.add_parser("run")
    run.add_argument("--brief", type=Path, required=True)
    run.add_argument("--source-id", action="append", required=True)
    run.add_argument("--resume")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("version")
    approve = commands.add_parser("approve")
    approve.add_argument("version")
    approve.add_argument("--hash", required=True)
    approve.add_argument("--reviewer", required=True)
    publish = commands.add_parser("publish")
    publish.add_argument(
        "versions", nargs="+", help="All dependency-complete approved material version IDs"
    )
    publish.add_argument("--output", type=Path, default=Path("materials-workspace/releases"))
    revoke = commands.add_parser("revoke-source")
    revoke.add_argument("source_id")
    revoke.add_argument("--reviewer", required=True)
    return root


async def execute(args: argparse.Namespace) -> None:
    store = Workbench(args.db)
    service = IngestionService(store)
    if args.command == "init":
        print(f"Initialized {store.path}")
    elif args.command == "status":
        print(store.status())
    elif args.command == "usage":
        print(store.usage(args.run_id).model_dump_json(indent=2))
    elif args.command == "source-metadata":
        from goalcoach.materials.sources import SocialMetadataService

        print((await SocialMetadataService().fetch(args.url)).model_dump_json(indent=2))
    elif args.command in {"import", "collect"}:
        source = Source.model_validate_json(args.source.read_text(encoding="utf-8"))
        if args.command == "collect":
            spans = await service.collect(source, frozenset(args.allow_host))
        elif args.pdf_page:
            spans = service.import_pdf(source, args.file, tuple(args.pdf_page))
        elif args.subtitles:
            spans = service.import_subtitles(source, args.file)
        else:
            spans = service.import_file(source, args.file)
        print(f"Imported {len(spans)} evidence spans from {source.source_id}.")
    elif args.command == "run":
        brief = Brief.model_validate_json(args.brief.read_text(encoding="utf-8"))
        settings = ModelSettings.load(args.settings_file)
        runner = PydanticAgentRunner(settings)
        try:
            result = await ProductionWorkflow(store, runner, settings.request_limit).run(
                brief, tuple(args.source_id), args.resume
            )
            print(result.model_dump_json(indent=2))
        finally:
            await runner.close()
    elif args.command == "inspect":
        print(store.packet(args.version).model_dump_json(indent=2))
    elif args.command == "approve":
        store.approve(args.version, args.hash, args.reviewer)
        print("Exact material version approved.")
    elif args.command == "publish":
        print(PublicationService(store).export_many(tuple(args.versions), args.output))
    elif args.command == "revoke-source":
        store.revoke(args.source_id, args.reviewer)
        print("Source revoked; affected versions and releases withdrawn.")
    elif args.command == "check-model":
        from goalcoach.materials.models import Catalog, Role
        from goalcoach.materials.workflow import Feedback

        settings = ModelSettings.load(args.settings_file)
        runner = PydanticAgentRunner(settings)
        check_run: str | None = None
        try:
            check_input = Feedback(
                instructions="Connection check only. Return summary 'Connection verified' and tag 'connectivity'."
            )
            check_run = store.start(check_input.digest())
            await ProductionWorkflow(store, runner, request_limit=1).step(
                check_run, Role.CATALOG, Catalog, (check_input,)
            )
            store.state(check_run, "model_verified")
            print(store.usage(check_run).model_dump_json(indent=2))
            print(
                "Structured-output model connectivity verified; no textbook generation or approval performed."
            )
        except BaseException:
            if check_run is not None:
                store.state(check_run, "interrupted")
            raise
        finally:
            await runner.close()
    elif args.command == "serve":
        import uvicorn

        from goalcoach.materials.dashboard import create_review_app

        server = uvicorn.Server(
            uvicorn.Config(
                create_review_app(store, args.output),
                host="127.0.0.1",
                port=args.port,
                log_level="warning",
            )
        )
        print(f"Human review dashboard: http://127.0.0.1:{args.port}")
        await server.serve()


def main() -> None:
    try:
        asyncio.run(execute(parser().parse_args()))
    except (MaterialsError, OSError, ValidationError) as exc:
        # Do not print validation inputs, provider responses, or credentials.
        print(
            str(exc)
            if isinstance(exc, MaterialsError)
            else f"{type(exc).__name__}: invalid configuration or unreadable input.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
