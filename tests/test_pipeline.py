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


def test_one_ticker_failure_still_writes_the_briefing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from alphasentinel.db_schema import init_db
    from alphasentinel.ingestor import IngestBatch

    module = _load()
    database = tmp_path / "warehouse.duckdb"
    init_db(database)

    def fake_ingest(_tickers, **_kwargs):
        return IngestBatch(
            2,
            (("META", "incomplete 10-K periods (2025-12-31: shares_outstanding)"),),
        )

    def fake_score(_db):
        return [{"ticker": "AAPL"}]

    def fake_compile(_db, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        markdown = directory / "brief.md"
        document = directory / "brief.docx"
        markdown.write_text("briefing\n" + ("x" * 200), encoding="utf-8")
        with zipfile.ZipFile(document, "w") as archive:
            archive.writestr("word/document.xml", "y" * 200)
        return {"md": markdown, "docx": document}

    def fake_build_loader():
        def build(dest: Path) -> int:
            dest.mkdir(parents=True, exist_ok=True)
            for name in DELIVERABLE_NAMES:
                (dest / name).write_text("z" * 120, encoding="utf-8")
            return 0

        return build

    monkeypatch.setattr(module, "ingest_tickers", fake_ingest)
    monkeypatch.setattr(module, "run_forensic_pipeline", fake_score)
    monkeypatch.setattr(module, "compile_report", fake_compile)
    monkeypatch.setattr(module, "_load_build_and_verify", fake_build_loader)

    code = module.run_pipeline(
        ["AAPL", "META"],
        offline=True,
        db_path=database,
        cache_dir=tmp_path / "cache",
        reports_dir=tmp_path / "reports",
        deliverables_dir=tmp_path / "deliverables",
    )
    captured = capsys.readouterr()

    assert code == 1
    assert (
        "[PIPELINE] ticker_fail META incomplete 10-K periods "
        "(2025-12-31: shares_outstanding)"
    ) in captured.err
    assert "failed_tickers=META" in captured.out
    assert "[PIPELINE] ingested_records=2" in captured.out
    briefing = tmp_path / "reports" / "AlphaSentinel_Executive_Briefing.md"
    assert briefing.is_file()
    assert briefing.stat().st_size >= 100


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


def test_invalid_briefing_is_not_replaced(tmp_path: Path) -> None:
    module = _load()
    markdown = tmp_path / "AlphaSentinel_Executive_Briefing.md"
    document = tmp_path / "AlphaSentinel_Executive_Briefing.docx"
    markdown.write_text("short", encoding="utf-8")
    document.write_bytes(b"not a zip")

    assert module.briefing_ready(tmp_path) == 1
    assert markdown.read_text(encoding="utf-8") == "short"
    assert document.read_bytes() == b"not a zip"


def test_missing_briefing_is_built_from_offline_fixtures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load()

    def fail_download(*_args, **_kwargs):
        raise AssertionError("briefing build called the network")

    monkeypatch.setattr("alphasentinel.ingestor.download_ticker", fail_download)
    monkeypatch.setattr("alphasentinel.ingestor._download_bytes", fail_download)
    monkeypatch.setattr(module, "DEFAULT_DB", tmp_path / "missing.duckdb")
    monkeypatch.setattr(module, "DEFAULT_CACHE", tmp_path / "empty-cache")

    reports = tmp_path / "reports"
    assert module.briefing_ready(reports) == 0
    briefing = reports / "AlphaSentinel_Executive_Briefing.md"
    text = briefing.read_text(encoding="utf-8")
    assert "AAPL" in text
    assert "MSFT" in text
    assert "数据不足（数据库字段为 NULL）" in text
    assert zipfile.is_zipfile(reports / "AlphaSentinel_Executive_Briefing.docx")
    assert not (ROOT / "reports" / "from-test").exists()


def test_nested_verify_all_checks_the_briefing(tmp_path: Path) -> None:
    module = _load()
    environment = os.environ.copy()
    environment[module.CHILD_ENV] = "1"
    command = [sys.executable, str(SCRIPT), "--verify-all", "--reports-dir", str(tmp_path)]

    missing = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert missing.returncode == 0, missing.stdout + missing.stderr
    assert "TASK-09 artifact present" in missing.stdout
    briefing = tmp_path / "AlphaSentinel_Executive_Briefing.md"
    assert briefing.is_file()
    assert briefing.stat().st_size >= 100

    briefing.write_text("short", encoding="utf-8")
    (tmp_path / "AlphaSentinel_Executive_Briefing.docx").write_bytes(b"not a zip")
    rejected = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert rejected.returncode == 1
    assert briefing.read_text(encoding="utf-8") == "short"

    _write_briefing(tmp_path)
    present = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert present.returncode == 0, present.stdout + present.stderr
    assert "TASK-09 artifact present" in present.stdout
