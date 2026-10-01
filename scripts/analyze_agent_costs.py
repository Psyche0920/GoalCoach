"""Analytics script for Agent Cost Accounting logs.

Dual-Engine implementation:
- Uses DuckDB if installed (for high-speed OLAP vector scans).
- Uses Python standard library (json, collections) as fallback when DuckDB is unavailable.

Usage:
    python scripts/analyze_agent_costs.py [--file logs/cost_accounting.jsonl]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import duckdb

    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False


def analyze_with_duckdb(file_path: Path) -> dict[str, Any]:
    """Execute aggregation queries using DuckDB read_json_auto."""
    conn = duckdb.connect()
    # Normalize Windows path for DuckDB SQL string
    sql_path = str(file_path.resolve()).replace("\\", "/")

    totals = conn.execute(
        f"""
        SELECT
            count(*) as total_calls,
            coalesce(sum(prompt_tokens), 0) as total_input_tokens,
            coalesce(sum(completion_tokens), 0) as total_output_tokens,
            coalesce(sum(total_tokens), 0) as total_tokens,
            coalesce(sum(total_cost_usd), sum(cost_usd), 0.0) as total_cost_usd
        FROM read_json_auto('{sql_path}')
        """
    ).fetchone()

    by_agent = conn.execute(
        f"""
        SELECT
            agent_name,
            count(*) as calls,
            coalesce(sum(total_tokens), 0) as tokens,
            coalesce(sum(total_cost_usd), sum(cost_usd), 0.0) as cost_usd
        FROM read_json_auto('{sql_path}')
        GROUP BY agent_name
        ORDER BY cost_usd DESC
        """
    ).fetchall()

    by_model = conn.execute(
        f"""
        SELECT
            provider,
            model_name,
            count(*) as calls,
            coalesce(sum(total_tokens), 0) as tokens,
            coalesce(sum(total_cost_usd), sum(cost_usd), 0.0) as cost_usd
        FROM read_json_auto('{sql_path}')
        GROUP BY provider, model_name
        ORDER BY cost_usd DESC
        """
    ).fetchall()

    return {
        "engine": "DuckDB",
        "total_calls": totals[0],
        "total_input_tokens": totals[1],
        "total_output_tokens": totals[2],
        "total_tokens": totals[3],
        "total_cost_usd": totals[4],
        "by_agent": by_agent,
        "by_model": by_model,
    }


def analyze_with_stdlib(file_path: Path) -> dict[str, Any]:
    """Fallback aggregation using standard library."""
    total_calls = 0
    total_input = 0
    total_output = 0
    total_tokens = 0
    total_cost = 0.0

    agent_stats: dict[str, list[float]] = defaultdict(lambda: [0, 0, 0.0])  # calls, tokens, cost
    model_stats: dict[tuple[str, str], list[float]] = defaultdict(
        lambda: [0, 0, 0.0]
    )  # calls, tokens, cost

    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            total_calls += 1
            inp = record.get("prompt_tokens", 0) or 0
            out = record.get("completion_tokens", 0) or 0
            toks = record.get("total_tokens", 0) or (inp + out)
            raw_cost = record.get("total_cost_usd", record.get("cost_usd", 0.0))
            cost = float(raw_cost or 0.0)

            total_input += inp
            total_output += out
            total_tokens += toks
            total_cost += cost

            agent = record.get("agent_name", "unknown")
            agent_stats[agent][0] += 1
            agent_stats[agent][1] += toks
            agent_stats[agent][2] += cost

            provider = record.get("provider", "unknown")
            model = record.get("model_name", "unknown")
            model_stats[(provider, model)][0] += 1
            model_stats[(provider, model)][1] += toks
            model_stats[(provider, model)][2] += cost

    by_agent = sorted(
        [(k, int(v[0]), int(v[1]), v[2]) for k, v in agent_stats.items()],
        key=lambda x: x[3],
        reverse=True,
    )
    by_model = sorted(
        [(k[0], k[1], int(v[0]), int(v[1]), v[2]) for k, v in model_stats.items()],
        key=lambda x: x[4],
        reverse=True,
    )

    return {
        "engine": "Python Stdlib",
        "total_calls": total_calls,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost,
        "by_agent": by_agent,
        "by_model": by_model,
    }


def print_report(data: dict[str, Any], file_path: Path) -> None:
    """Print clean summary report."""
    print("=" * 70)
    print(f" GOALCOACH AGENT COST ACCOUNTING REPORT (Engine: {data['engine']})")
    print(f" Source: {file_path}")
    print("=" * 70)
    print(f" Total LLM Calls:       {data['total_calls']}")
    print(f" Total Input Tokens:    {data['total_input_tokens']:,}")
    print(f" Total Output Tokens:   {data['total_output_tokens']:,}")
    print(f" Total Tokens:          {data['total_tokens']:,}")
    print(f" Total Cost:            ${data['total_cost_usd']:.6f} USD")
    print("-" * 70)

    print("\nCOST & TOKENS BY AGENT:")
    print(f"{'Agent Name':<25} {'Calls':>8} {'Total Tokens':>14} {'Cost (USD)':>14}")
    print("-" * 65)
    for agent, calls, tokens, cost in data["by_agent"]:
        print(f"{agent:<25} {calls:>8} {tokens:>14,} ${cost:>13.6f}")

    print("\nCOST & TOKENS BY PROVIDER / MODEL:")
    print(f"{'Provider':<15} {'Model Name':<25} {'Calls':>8} {'Tokens':>12} {'Cost (USD)':>12}")
    print("-" * 76)
    for provider, model, calls, tokens, cost in data["by_model"]:
        print(f"{provider:<15} {model:<25} {calls:>8} {tokens:>12,} ${cost:>11.6f}")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze GoalCoach agent LLM costs")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("logs/cost_accounting.jsonl"),
        help="Path to cost accounting JSONL file",
    )
    args = parser.parse_args()

    if not args.file.exists():
        print(f"Notice: Cost log file not found at '{args.file}'. No records to analyze.")
        return

    if args.file.stat().st_size == 0:
        print(f"Notice: Cost log file '{args.file}' is empty.")
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
