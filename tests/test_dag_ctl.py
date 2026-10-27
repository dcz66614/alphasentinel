from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "dag_ctl.py"


@pytest.fixture()
def db_path() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "dag_state.db"


def run_dag(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def set_verify_cmd(db: Path, task_id: str, verify_cmd: str) -> None:
    with closing(sqlite3.connect(str(db))) as conn:
        conn.execute(
            "UPDATE dag_tasks SET verify_cmd = ? WHERE task_id = ?",
            (verify_cmd, task_id),
        )
        conn.commit()


def get_task(db: Path, task_id: str) -> sqlite3.Row:
    with closing(sqlite3.connect(str(db))) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM dag_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
    assert row is not None
    return row


def success_cmd() -> str:
    return f'"{sys.executable}" -c "print(1)"'


def failure_cmd() -> str:
    return f'"{sys.executable}" -c "raise SystemExit(1)"'


def test_init_creates_nine_pending_tasks(db_path: Path) -> None:
    result = run_dag("init", "--db", str(db_path))
    assert result.returncode == 0, result.stdout + result.stderr
    assert db_path.exists()

    with closing(sqlite3.connect(str(db_path))) as conn:
        rows = conn.execute("SELECT * FROM dag_tasks ORDER BY seq").fetchall()

    assert [row[0] for row in rows] == [f"TASK-{i:02d}" for i in range(1, 10)]
    assert all(row[6] == "PENDING" for row in rows)
    assert all(row[7] == 0 for row in rows)
    assert all(row[8] is None for row in rows)


def test_init_is_idempotent(db_path: Path) -> None:
    assert run_dag("init", "--db", str(db_path)).returncode == 0
    assert run_dag("init", "--db", str(db_path)).returncode == 0

    with closing(sqlite3.connect(str(db_path))) as conn:
        count = conn.execute("SELECT COUNT(*) FROM dag_tasks").fetchone()[0]
    assert count == 9


def test_status_prints_table(db_path: Path) -> None:
    assert run_dag("init", "--db", str(db_path)).returncode == 0
    result = run_dag("status", "--db", str(db_path))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "TASK_ID" in result.stdout
    assert "TASK-01" in result.stdout
    assert "TASK-09" in result.stdout
    assert "PENDING" in result.stdout
    assert "@CommanderBot" in result.stdout


def test_verify_rejects_when_dependency_not_passed(db_path: Path) -> None:
    assert run_dag("init", "--db", str(db_path)).returncode == 0
    set_verify_cmd(db_path, "TASK-02", success_cmd())

    result = run_dag("verify", "--task", "TASK-02", "--db", str(db_path))

    assert result.returncode == 2
    assert "TASK-01" in result.stdout
    row = get_task(db_path, "TASK-02")
    assert row["status"] == "PENDING"
    assert row["attempts"] == 0


def test_verify_success_marks_passed(db_path: Path) -> None:
    assert run_dag("init", "--db", str(db_path)).returncode == 0
    set_verify_cmd(db_path, "TASK-01", success_cmd())

    result = run_dag("verify", "--task", "TASK-01", "--db", str(db_path))

    assert result.returncode == 0, result.stdout + result.stderr
    row = get_task(db_path, "TASK-01")
    assert row["status"] == "PASSED"
    assert row["attempts"] == 0
    assert row["last_exit_code"] == 0


def test_verify_failure_increments_attempts_then_blocks(db_path: Path) -> None:
    assert run_dag("init", "--db", str(db_path)).returncode == 0
    set_verify_cmd(db_path, "TASK-01", failure_cmd())

    first = run_dag("verify", "--task", "TASK-01", "--db", str(db_path))
    assert first.returncode == 1
    row = get_task(db_path, "TASK-01")
    assert row["status"] == "FAILED"
    assert row["attempts"] == 1
    assert row["last_exit_code"] == 1

    second = run_dag("verify", "--task", "TASK-01", "--db", str(db_path))
    assert second.returncode == 1
    row = get_task(db_path, "TASK-01")
    assert row["status"] == "FAILED"
    assert row["attempts"] == 2

    third = run_dag("verify", "--task", "TASK-01", "--db", str(db_path))
    assert third.returncode == 3
    row = get_task(db_path, "TASK-01")
    assert row["status"] == "BLOCKED"
    assert row["attempts"] == 3

    fourth = run_dag("verify", "--task", "TASK-01", "--db", str(db_path))
    assert fourth.returncode == 3
    row = get_task(db_path, "TASK-01")
    assert row["status"] == "BLOCKED"
    assert row["attempts"] == 3


def test_seeded_artifacts_and_verify_commands(db_path: Path) -> None:
    assert run_dag("init", "--db", str(db_path)).returncode == 0

    expected = {
        "TASK-01": ("scripts/dag_ctl.py", "python scripts/dag_ctl.py status"),
        "TASK-02": (
            "src/alphasentinel/db_schema.py",
            "python -m pytest -q tests/test_schema.py",
        ),
        "TASK-03": (
            "src/alphasentinel/ingestor.py",
            "python -m pytest -q tests/test_ingestor.py",
        ),
        "TASK-04": (
            "src/alphasentinel/forensic_engine.py",
            "python -m pytest -q tests/test_forensic.py",
        ),
        "TASK-05": (
            "src/alphasentinel/report_compiler.py",
            "python -m pytest -q tests/test_reports.py",
        ),
        "TASK-06": (
            "src/alphasentinel/api_server.py",
            "python -m pytest -q tests/test_api.py",
        ),
        "TASK-07": (
            "src/alphasentinel/dashboard.py",
            "python -m py_compile src/alphasentinel/dashboard.py",
        ),
        "TASK-08": (
            "deliverables/PROJECT_CHARTER.docx",
            "python scripts/build_four_deliverables.py --verify",
        ),
        "TASK-09": (
            "reports/AlphaSentinel_Executive_Briefing.docx",
            "python scripts/run_pipeline.py --verify-all",
        ),
    }

    for task_id, (artifact, verify_cmd) in expected.items():
        row = get_task(db_path, task_id)
        assert row["artifact"] == artifact
        assert row["verify_cmd"] == verify_cmd
        assert "python3" not in row["verify_cmd"]


def test_verify_unknown_task_fails(db_path: Path) -> None:
    assert run_dag("init", "--db", str(db_path)).returncode == 0

    result = run_dag("verify", "--task", "TASK-99", "--db", str(db_path))

    assert result.returncode == 1
    assert "not found" in result.stdout
