#!/usr/bin/env python3
"""Deterministic SQLite DAG state ledger for AlphaSentinel task packets."""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "state" / "dag_state.db"

INITIAL_TASKS = [
    (
        "TASK-01",
        1,
        "@CommanderBot",
        "[]",
        "scripts/dag_ctl.py",
        "python scripts/dag_ctl.py status",
    ),
    (
        "TASK-02",
        2,
        "@SpecArchitectBot",
        '["TASK-01"]',
        "src/alphasentinel/db_schema.py",
        "python -m pytest -q tests/test_schema.py",
    ),
    (
        "TASK-03",
        3,
        "@DataEngineBot",
        '["TASK-02"]',
        "src/alphasentinel/ingestor.py",
        "python -m pytest -q tests/test_ingestor.py",
    ),
    (
        "TASK-04",
        4,
        "@QuantForensicBot",
        '["TASK-03"]',
        "src/alphasentinel/forensic_engine.py",
        "python -m pytest -q tests/test_forensic.py",
    ),
    (
        "TASK-05",
        5,
        "@UIAndReportBot",
        '["TASK-04"]',
        "src/alphasentinel/report_compiler.py",
        "python -m pytest -q tests/test_reports.py",
    ),
    (
        "TASK-06",
        6,
        "@UIAndReportBot",
        '["TASK-04"]',
        "src/alphasentinel/api_server.py",
        "python -m pytest -q tests/test_api.py",
    ),
    (
        "TASK-07",
        7,
        "@UIAndReportBot",
        '["TASK-05","TASK-06"]',
        "src/alphasentinel/dashboard.py",
        "python -m py_compile src/alphasentinel/dashboard.py",
    ),
    (
        "TASK-08",
        8,
        "@UIAndReportBot",
        '["TASK-07"]',
        "deliverables/PROJECT_CHARTER.docx",
        "python scripts/build_four_deliverables.py --verify",
    ),
    (
        "TASK-09",
        9,
        "@CommanderBot",
        '["TASK-08"]',
        "reports/AlphaSentinel_Executive_Briefing.docx",
        "python scripts/run_pipeline.py --verify-all",
    ),
]

MAX_ATTEMPTS = 3


def get_conn(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> int:
    conn = get_conn(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dag_tasks (
                task_id TEXT PRIMARY KEY,
                seq INTEGER NOT NULL,
                owner TEXT NOT NULL,
                depends_on TEXT NOT NULL,
                artifact TEXT NOT NULL,
                verify_cmd TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_exit_code INTEGER
            )
            """
        )
        for task_id, seq, owner, depends_on, artifact, verify_cmd in INITIAL_TASKS:
            conn.execute(
                """
                INSERT OR IGNORE INTO dag_tasks
                    (task_id, seq, owner, depends_on, artifact, verify_cmd,
                     status, attempts, last_exit_code)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 0, NULL)
                """,
                (task_id, seq, owner, depends_on, artifact, verify_cmd),
            )
        conn.commit()
    finally:
        conn.close()
    print(f"[DAG_CTL] Initialized SQLite DAG state ledger at {db_path}")
    return 0


def ensure_db(db_path: Path) -> None:
    if not db_path.exists():
        init_db(db_path)


def fetch_task(conn: sqlite3.Connection, task_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM dag_tasks WHERE task_id = ?", (task_id,)).fetchone()


def verify_task(task_id: str, db_path: Path) -> int:
    ensure_db(db_path)
    conn = get_conn(db_path)
    try:
        row = fetch_task(conn, task_id)
        if row is None:
            print(f"[ERROR] Task {task_id} not found.")
            return 1

        try:
            deps = json.loads(row["depends_on"])
        except (TypeError, json.JSONDecodeError):
            print(f"[ERROR] Task {task_id} has invalid depends_on JSON.")
            return 1

        for dep_id in deps:
            dep_row = fetch_task(conn, dep_id)
            dep_status = dep_row["status"] if dep_row else "UNKNOWN"
            if dep_status != "PASSED":
                print(
                    f"[REJECTED] {task_id} dependency {dep_id} is {dep_status}, "
                    "expected PASSED."
                )
                return 2

        if row["status"] == "BLOCKED":
            print(f"[BLOCKED] {task_id} exhausted max_attempts ({MAX_ATTEMPTS}).")
            return 3

        verify_cmd = row["verify_cmd"]
        print(f"[VERIFYING] {task_id}: {verify_cmd}")
        proc = subprocess.run(
            verify_cmd,
            shell=True,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )

        if proc.returncode == 0:
            conn.execute(
                """
                UPDATE dag_tasks
                SET status = 'PASSED', last_exit_code = 0
                WHERE task_id = ?
                """,
                (task_id,),
            )
            conn.commit()
            print(f"[PASSED] {task_id} verified.")
            return 0

        attempts = row["attempts"] + 1
        status = "BLOCKED" if attempts >= MAX_ATTEMPTS else "FAILED"
        conn.execute(
            """
            UPDATE dag_tasks
            SET status = ?, attempts = ?, last_exit_code = ?
            WHERE task_id = ?
            """,
            (status, attempts, proc.returncode, task_id),
        )
        conn.commit()
        detail = (proc.stdout + "\n" + proc.stderr).strip()[-2000:]
        print(f"[{status}] {task_id} failed verification (exit={proc.returncode}).")
        if detail:
            print(detail)
        return 3 if status == "BLOCKED" else 1
    finally:
        conn.close()


def print_status(db_path: Path) -> int:
    ensure_db(db_path)
    conn = get_conn(db_path)
    try:
        rows = conn.execute("SELECT * FROM dag_tasks ORDER BY seq ASC").fetchall()
    finally:
        conn.close()

    columns = (
        "TASK_ID",
        "SEQ",
        "OWNER",
        "STATUS",
        "ATTEMPTS",
        "DEPENDS_ON",
        "ARTIFACT",
    )
    print(
        f"{columns[0]:<8} | {columns[1]:>3} | {columns[2]:<18} | {columns[3]:<8} | "
        f"{columns[4]:>8} | {columns[5]:<22} | {columns[6]}"
    )
    print("-" * 120)
    for row in rows:
        attempts = f"{row['attempts']}/{MAX_ATTEMPTS}"
        print(
            f"{row['task_id']:<8} | {row['seq']:>3} | {row['owner']:<18} | "
            f"{row['status']:<8} | {attempts:>8} | {row['depends_on']:<22} | "
            f"{row['artifact']}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AlphaSentinel DAG controller")
    parser.add_argument("action", choices=["init", "status", "verify"])
    parser.add_argument("--task", help="Task ID to verify (e.g., TASK-01)")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite ledger path (default: {DEFAULT_DB_PATH})",
    )
    args = parser.parse_args(argv)

    if args.action == "init":
        return init_db(args.db)
    if args.action == "status":
        return print_status(args.db)
    if not args.task:
        print("[ERROR] verify requires --task TASK-XX")
        return 1
    return verify_task(args.task, args.db)


if __name__ == "__main__":
    sys.exit(main())
