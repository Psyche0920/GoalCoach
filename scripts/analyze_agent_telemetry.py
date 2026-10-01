"""Analytics script for Agent Telemetry logs.

Dual-Engine implementation:
- Uses DuckDB if installed (for high-speed quantile and rollup calculations).
- Uses Python standard library (json, statistics, collections) as fallback when DuckDB is unavailable.

Usage:
    python scripts/analyze_agent_telemetry.py [--file logs/agent_telemetry.jsonl]
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import duckdb

    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False


def calculate_percentiles(values: list[float]) -> dict[str, float]:
    """Calculate P50, P90, P99, avg, max for a list of numbers."""
    if not values:
        return {"count": 0, "avg": 0.0, "p50": 0.0, "p90": 0.0, "p99": 0.0, "max": 0.0}
    s = sorted(values)
    n = len(s)

    def pct(p: float) -> float:
        idx = max(0, min(n - 1, int(math.ceil(p * n) - 1)))
        return s[idx]

    return {
        "count": n,
        "avg": round(sum(s) / n, 2),
        "p50": round(pct(0.50), 2),
        "p90": round(pct(0.90), 2),
        "p99": round(pct(0.99), 2),
        "max": round(s[-1], 2),
    }


def analyze_with_duckdb(file_path: Path) -> dict[str, Any]:
    """Execute aggregation queries using DuckDB read_json_auto."""
    conn = duckdb.connect()
    sql_path = str(file_path.resolve()).replace("\\", "/")

    totals = conn.execute(
        f"""
        SELECT
            count(*) as total_events,
            count(distinct trace_id) as total_traces,
            count(distinct run_id) as total_runs
        FROM read_json_auto('{sql_path}')
        """
    ).fetchone()

    by_stage = conn.execute(
        f"""
        SELECT stage, count(*) as count
        FROM read_json_auto('{sql_path}')
        GROUP BY stage
        ORDER BY count DESC
        """
    ).fetchall()

    by_agent = conn.execute(
        f"""
        SELECT
            agent_name,
            count(*) filter (WHERE stage = 'completed' or stage = 'failed') as executions,
            count(*) filter (WHERE stage = 'failed') as failures,
            round(avg(execution_latency_ms), 2) as avg_lat,
            round(quantile_cont(execution_latency_ms, 0.50), 2) as p50,
            round(quantile_cont(execution_latency_ms, 0.90), 2) as p90,
            round(quantile_cont(execution_latency_ms, 0.99), 2) as p99,
            round(max(execution_latency_ms), 2) as max_lat
        FROM read_json_auto('{sql_path}')
        WHERE execution_latency_ms is not null
        GROUP BY agent_name
        ORDER BY executions DESC
        """
    ).fetchall()

    by_tool = conn.execute(
        f"""
        SELECT
            tool_name,
            count(*) as calls,
            round(avg(tool_latency_ms), 2) as avg_lat,
            round(quantile_cont(tool_latency_ms, 0.50), 2) as p50,
            round(quantile_cont(tool_latency_ms, 0.90), 2) as p90,
            round(max(tool_latency_ms), 2) as max_lat
        FROM read_json_auto('{sql_path}')
        WHERE tool_name is not null AND tool_latency_ms is not null
        GROUP BY tool_name
        ORDER BY calls DESC
        """
    ).fetchall()

    return {
        "engine": "DuckDB",
        "total_events": totals[0],
        "total_traces": totals[1],
        "total_runs": totals[2],
        "by_stage": by_stage,
        "by_agent": by_agent,
        "by_tool": by_tool,
    }


def analyze_with_stdlib(file_path: Path) -> dict[str, Any]:
    """Fallback aggregation using standard library."""
    total_events = 0
    traces = set()
    runs = set()
    stage_counts: dict[str, int] = defaultdict(int)
    agent_latencies: dict[str, list[float]] = defaultdict(list)
    agent_failures: dict[str, int] = defaultdict(int)
    tool_latencies: dict[str, list[float]] = defaultdict(list)

    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            total_events += 1
            if rec.get("trace_id"):
                traces.add(rec["trace_id"])
            if rec.get("run_id"):
                runs.add(rec["run_id"])

            st = rec.get("stage", "unknown")
            stage_counts[st] += 1

            agent = rec.get("agent_name", "unknown")
            if st == "failed":
                agent_failures[agent] += 1

            if rec.get("execution_latency_ms") is not None:
                agent_latencies[agent].append(float(rec["execution_latency_ms"]))

            tool = rec.get("tool_name")
            if tool and rec.get("tool_latency_ms") is not None:
                tool_latencies[tool].append(float(rec["tool_latency_ms"]))

    by_stage = sorted(stage_counts.items(), key=lambda x: x[1], reverse=True)

    by_agent = []
    for agent, lats in agent_latencies.items():
        stats = calculate_percentiles(lats)
        fails = agent_failures.get(agent, 0)
        by_agent.append(
            (
                agent,
                stats["count"],
                fails,
                stats["avg"],
                stats["p50"],
                stats["p90"],
                stats["p99"],
                stats["max"],
            )
        )
    by_agent.sort(key=lambda x: x[1], reverse=True)

    by_tool = []
    for tool, lats in tool_latencies.items():
        stats = calculate_percentiles(lats)
        by_tool.append(
            (tool, stats["count"], stats["avg"], stats["p50"], stats["p90"], stats["max"])
        )
    by_tool.sort(key=lambda x: x[1], reverse=True)

    return {
        "engine": "Python Stdlib",
        "total_events": total_events,
        "total_traces": len(traces),
        "total_runs": len(runs),
        "by_stage": by_stage,
        "by_agent": by_agent,
        "by_tool": by_tool,
    }


def print_report(data: dict[str, Any], file_path: Path) -> None:
    """Print clean telemetry metrics report."""
    print("=" * 80)
    print(f" GOALCOACH AGENT TELEMETRY REPORT (Engine: {data['engine']})")
    print(f" Source: {file_path}")
    print("=" * 80)
    print(f" Total Events Logged:   {data['total_events']:,}")
    print(f" Unique Traces:         {data['total_traces']:,}")
    print(f" Unique Agent Runs:     {data['total_runs']:,}")
    print("-" * 80)

    print("\nLIFECYCLE STAGE DISTRIBUTION:")
    for stage, count in data["by_stage"]:
        pct = (count / data["total_events"] * 100) if data["total_events"] else 0
        print(f"  • {stage:<18} {count:>8,} events ({pct:>5.1f}%)")

    print("\nAGENT EXECUTION LATENCIES (ms):")
    print(
        f"{'Agent Name':<20} {'Runs':>6} {'Fails':>6} {'Avg (ms)':>10} {'P50':>8} {'P90':>8} {'P99':>8} {'Max':>8}"
    )
    print("-" * 80)
    for row in data["by_agent"]:
        agent, runs, fails, avg, p50, p90, p99, max_lat = row
        print(
            f"{agent:<20} {runs:>6} {fails:>6} {avg:>10.2f} {p50:>8.2f} {p90:>8.2f} {p99:>8.2f} {max_lat:>8.2f}"
        )

    print("\nTOOL CALL PERFORMANCE (ms):")
    print(f"{'Tool Name':<30} {'Calls':>8} {'Avg (ms)':>10} {'P50':>8} {'P90':>8} {'Max':>8}")
    print("-" * 76)
    for row in data["by_tool"]:
        tool, calls, avg, p50, p90, max_lat = row
        print(f"{tool:<30} {calls:>8} {avg:>10.2f} {p50:>8.2f} {p90:>8.2f} {max_lat:>8.2f}")
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze GoalCoach agent telemetry")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("logs/agent_telemetry.jsonl"),
        help="Path to agent telemetry JSONL file",
    )
    args = parser.parse_args()

    if not args.file.exists():
        print(f"Notice: Telemetry log file not found at '{args.file}'. No records to analyze.")
        return

    if args.file.stat().st_size == 0:
        print(f"Notice: Telemetry log file '{args.file}' is empty.")
        return

    if HAS_DUCKDB:
        try:
            data = analyze_with_duckdb(args.file)
        except Exception as exc:  # noqa: BLE001
            print(f"[Warning] DuckDB analysis failed ({exc}), falling back to standard library.")
            data = analyze_with_stdlib(args.file)
    else:
        data = analyze_with_stdlib(args.file)

    print_report(data, args.file)


if __name__ == "__main__":
    main()
