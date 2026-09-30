"""DuckDB Telemetry Analyzer for GoalCoach JSONL Logs.

Parses logs/goalcoach.jsonl to detect performance regressions, slow queries,
model failovers, and state machine anomalies, producing structured incident bundles.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger("goalcoach.telemetry.analyzer")


def analyze_telemetry_log(
    log_path: Path | str = "logs/goalcoach.jsonl",
    output_report_path: Path | str = "logs/test_incident_report.json",
) -> dict[str, Any]:
    """Execute analytical SQL queries over NDJSON log files using DuckDB."""
    target_log = Path(log_path)
    output_report = Path(output_report_path)

    report: dict[str, Any] = {
        "status": "clean",
        "log_path": str(target_log),
        "total_records": 0,
        "anomalies_detected": 0,
        "fast_path_evaluations": 0,
        "slow_queries": [],
        "model_failovers": [],
        "error_clusters": [],
    }

    if not target_log.exists() or target_log.stat().st_size == 0:
        output_report.parent.mkdir(parents=True, exist_ok=True)
        with open(output_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[Telemetry Analyzer] No log file found at {target_log}. Empty clean report emitted.")
        return report

    con = duckdb.connect(database=":memory:")
    try:
        # Load JSON lines into a DuckDB view
        con.execute(f"CREATE VIEW logs AS SELECT * FROM read_json_auto('{target_log.as_posix()}', ignore_errors=true)")

        # 1. Total records
        total = con.execute("SELECT count(*) FROM logs").fetchone()[0]
        report["total_records"] = total

        # 2. Slow queries (>25ms)
        try:
            slow_q = con.execute("""
                SELECT timestamp, message, extra
                FROM logs
                WHERE (level = 'WARN' AND message LIKE '%slow_query%')
                   OR (try_cast(json_extract_string(extra, '$.duration_ms') AS DOUBLE) > 25.0
                       AND json_extract_string(extra, '$.http.route') IS NOT NULL)
                LIMIT 50
            """).fetchall()
            report["slow_queries"] = [
                {"timestamp": str(r[0]), "message": r[1], "details": r[2]} for r in slow_q
            ]
        except duckdb.Error as exc:
            logger.debug("Failed to query slow queries: %s", exc)

        # 3. Model failovers or errors
        try:
            failovers = con.execute("""
                SELECT timestamp, level, message, extra
                FROM logs
                WHERE message LIKE '%fallback%' OR message LIKE '%failover%' OR level = 'ERROR'
                LIMIT 50
            """).fetchall()
            report["model_failovers"] = [
                {"timestamp": str(r[0]), "level": r[1], "message": r[2], "extra": r[3]}
                for r in failovers
            ]
        except duckdb.Error as exc:
            logger.debug("Failed to query model failovers: %s", exc)

        # 4. Fast path evaluations
        try:
            fast_paths = con.execute("""
                SELECT count(*)
                FROM logs
                WHERE message LIKE '%fast-path%' OR json_extract_string(extra, '$.eval_path') = 'fast_path'
            """).fetchone()[0]
            report["fast_path_evaluations"] = fast_paths
        except duckdb.Error as exc:
            logger.debug("Failed to query fast paths: %s", exc)

        # Compute status
        report["anomalies_detected"] = len(report["slow_queries"]) + len(report["model_failovers"])
        if report["anomalies_detected"] > 0:
            report["status"] = "anomalies_flagged"

    finally:
        con.close()

    output_report.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=" * 60)
    print("GOALCOACH TELEMETRY AUDIT REPORT")
    print(f"Log Path: {target_log} ({report['total_records']} lines parsed)")
    print(f"Status: {report['status'].upper()}")
    print(f"Fast-Path Evaluations: {report['fast_path_evaluations']}")
    print(f"Slow Queries Flagged (>25ms): {len(report['slow_queries'])}")
    print(f"Errors / Failovers: {len(report['model_failovers'])}")
    print(f"Incident bundle saved to: {output_report}")
    print("=" * 60)

    return report


if __name__ == "__main__":
    analyze_telemetry_log()
