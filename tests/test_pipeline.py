"""Pipeline orchestration against fixture cache files. No network."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_pipeline.py"
FIXTURE_CACHE = ROOT / "tests" / "fixtures" / "offline_cache"
DELIVERABLE_NAMES = (
    "PROJECT_CHARTER.md",
    "PROJECT_CHARTER.docx",
    "AGENT_EXECUTION_PLAN.md",
    "AGENT_EXECUTION_PLAN.docx",
)


def _load():
    spec = importlib.util.spec_from_file_location("run_pipeline", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_briefing(directory: Path) -> None:
    markdown = directory / "AlphaSentinel_Executive_Briefing.md"
    markdown.write_text("briefing\n" + ("x" * 120), encoding="utf-8")
    document = directory / "AlphaSentinel_Executive_Briefing.docx"
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("word/document.xml", "y" * 200)


def test_core_tickers_match_spec_order() -> None:
    module = _load()
    assert module.CORE_TICKERS == (
        "NVDA",
        "MSFT",
        "AAPL",
        "META",
        "GOOGL",
        "AMZN",
        "TSLA",
        "CRM",
        "PLTR",
        "ORCL",
    )


def test_offline_run_uses_fixture_cache_and_skips_download(tmp_path: Path, monkeypatch) -> None:
    module = _load()

    def fail_download(*_args, **_kwargs):
        raise AssertionError("offline pipeline called the network")

    monkeypatch.setattr("alphasentinel.ingestor.download_ticker", fail_download)
    monkeypatch.setattr("alphasentinel.ingestor._download_bytes", fail_download)

    code = module.run_pipeline(
        ["AAPL", "MSFT"],
        offline=True,
        db_path=tmp_path / "warehouse.duckdb",
        cache_dir=FIXTURE_CACHE,
        reports_dir=tmp_path / "reports",
        deliverables_dir=tmp_path / "deliverables",
    )

    assert code == 0
    briefing_md = tmp_path / "reports" / "AlphaSentinel_Executive_Briefing.md"
    briefing_docx = tmp_path / "reports" / "AlphaSentinel_Executive_Briefing.docx"
    assert briefing_md.is_file()
    assert "AAPL" in briefing_md.read_text(encoding="utf-8")
    assert "MSFT" in briefing_md.read_text(encoding="utf-8")
    assert zipfile.is_zipfile(briefing_docx)
    for name in DELIVERABLE_NAMES:
        artifact = tmp_path / "deliverables" / name
        assert artifact.is_file()
        assert artifact.stat().st_size >= 100


def test_offline_cli_prints_row_and_metric_counts(tmp_path: Path) -> None:
    database = tmp_path / "warehouse.duckdb"
    reports = tmp_path / "reports"
    deliverables = tmp_path / "deliverables"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--offline",
            "--tickers",
            "AAPL,MSFT",
            "--db",
            str(database),
            "--cache-dir",
            str(FIXTURE_CACHE),
            "--reports-dir",
            str(reports),
            "--deliverables-dir",
            str(deliverables),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[PIPELINE] tickers=AAPL,MSFT offline=true" in result.stdout
    assert "[PIPELINE] ingested_records=4" in result.stdout
    assert "[PIPELINE] financial_rows AAPL count=2" in result.stdout
    assert "[PIPELINE] financial_rows MSFT count=2" in result.stdout
    assert "mode=CACHE_SEC" in result.stdout
    assert "[PIPELINE] scored_companies=2" in result.stdout
    assert "metric_counts AAPL" in result.stdout
    assert "metric_counts MSFT" in result.stdout
    assert "piotroski_f_score" in result.stdout
    assert "[PIPELINE_SUCCESS] Ingested 4 records, scored 2 companies." in result.stdout
    assert (reports / "AlphaSentinel_Executive_Briefing.docx").is_file()


def test_offline_missing_cache_fails(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--offline",
            "--tickers",
            "AAPL",
            "--db",
            str(tmp_path / "warehouse.duckdb"),
            "--cache-dir",
            str(tmp_path / "empty-cache"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--deliverables-dir",
            str(tmp_path / "deliverables"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 1
    assert "PIPELINE_FAIL" in result.stderr
    assert not (tmp_path / "reports" / "AlphaSentinel_Executive_Briefing.docx").exists()


def test_verify_all_invokes_task_01_through_09(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load()
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        assert kwargs["cwd"] == str(ROOT)
        assert kwargs["env"][module.CHILD_ENV] == "1"
        return subprocess.CompletedProcess(command, 0, stdout="[PASSED]\n", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    code = module.verify_all(tmp_path / "dag.db")

    assert code == 0
    tasks = [command[command.index("--task") + 1] for command in calls]
    assert tasks == [f"TASK-{index:02d}" for index in range(1, 10)]
    assert all(command[0] == sys.executable for command in calls)
    assert all(str(tmp_path / "dag.db") in command for command in calls)


def test_verify_all_summarizes_a_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load()

    def fake_run(command, **_kwargs):
        task_id = command[command.index("--task") + 1]
        code = 1 if task_id == "TASK-04" else 0
        return subprocess.CompletedProcess(command, code, stdout="[FAILED]\n", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    code = module.verify_all(tmp_path / "dag.db")

    assert code == 1


def test_nested_verify_all_checks_the_briefing(tmp_path: Path) -> None:
    module = _load()
    assert module.briefing_ready(tmp_path) == 1

    environment = os.environ.copy()
    environment[module.CHILD_ENV] = "1"
    missing = subprocess.run(
        [sys.executable, str(SCRIPT), "--verify-all", "--reports-dir", str(tmp_path)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert missing.returncode == 1

    _write_briefing(tmp_path)
    present = subprocess.run(
        [sys.executable, str(SCRIPT), "--verify-all", "--reports-dir", str(tmp_path)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert present.returncode == 0, present.stdout + present.stderr
    assert "TASK-09 artifact present" in present.stdout
