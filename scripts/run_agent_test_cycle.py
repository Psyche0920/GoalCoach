"""GoalCoach Unified Test Cycle Orchestrator.

Sequentially executes:
1. Tier 1: In-Process Synthetic Learner Swarm (tests/harness/)
2. Tier 2: Playwright Browser Agent E2E Suite (tests/e2e/)
3. Tier 3: DuckDB Telemetry Log Analysis (scripts/analyze_telemetry.py)

Exits 0 on success, non-zero on failure with clean terminal output.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_command_with_echo(cmd: list[str], cwd: Path | None = None) -> int:
    """Print and execute command, streaming output to console."""
    import os
    env = os.environ.copy()
    lib_dir = Path.home() / ".local" / "lib" / "playwright_shared_libs"
    if lib_dir.exists():
        cur = env.get("LD_LIBRARY_PATH", "")
        if str(lib_dir) not in cur:
            env["LD_LIBRARY_PATH"] = f"{lib_dir}:{cur}" if cur else str(lib_dir)

    print(f"\n[RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, check=False)
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute full GoalCoach test cycle")
    parser.add_argument("--headed", action="store_true", help="Launch visible Chromium browser for E2E tests")
    parser.add_argument("--slowmo", type=int, default=0, help="Slow down browser operations by specified milliseconds")
    parser.add_argument("--skip-e2e", action="store_true", help="Skip browser E2E tests (Swarm only)")
    parser.add_argument("--skip-swarm", action="store_true", help="Skip synthetic swarm tests")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent

    print("\n" + "=" * 65)
    print("      GOALCOACH HYBRID TESTING CYCLE ORCHESTRATOR      ")
    print("=" * 65)

    # 1. Tier 1: Synthetic Learner Swarm
    if not args.skip_swarm:
        print("\n>>> TIER 1: In-Process Synthetic Learner Swarm (ASGI Fuzzing)...")
        swarm_code = run_command_with_echo(["uv", "run", "pytest", "tests/harness/", "-v"], cwd=root_dir)
        if swarm_code != 0:
            print("\n❌ Synthetic swarm tests failed. Aborting pipeline.")
            sys.exit(swarm_code)
        print("✅ Synthetic swarm tests passed successfully.")

    # 2. Tier 2: Playwright Browser Agent
    if not args.skip_e2e:
        print("\n>>> TIER 2: Playwright Browser Agent E2E Tests...")
        e2e_cmd = ["uv", "run", "pytest", "tests/e2e/", "-v"]
        if args.headed:
            e2e_cmd.append("--headed")
            slowmo = args.slowmo if args.slowmo > 0 else 800
            e2e_cmd.extend(["--slowmo", str(slowmo)])
        elif args.slowmo > 0:
            e2e_cmd.extend(["--slowmo", str(args.slowmo)])
        e2e_code = run_command_with_echo(e2e_cmd, cwd=root_dir)
        if e2e_code != 0:
            print("\n❌ Playwright browser tests failed. Analyzing telemetry...")
            # Still run telemetry analyzer to provide debugging incident report
            run_command_with_echo(["uv", "run", "python", "scripts/analyze_telemetry.py"], cwd=root_dir)
            sys.exit(e2e_code)
        print("✅ Playwright browser tests passed successfully.")

    # 3. Tier 3: DuckDB Telemetry Analysis
    print("\n>>> TIER 3: DuckDB Telemetry Analysis & Incident Detection...")
    analysis_code = run_command_with_echo(["uv", "run", "python", "scripts/analyze_telemetry.py"], cwd=root_dir)

    print("\n" + "=" * 65)
    print("       ALL TEST SUITES & TELEMETRY AUDITS COMPLETED       ")
    print("=" * 65 + "\n")
    sys.exit(analysis_code)


if __name__ == "__main__":
    main()
