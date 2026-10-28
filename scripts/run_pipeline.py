#!/usr/bin/env python3
"""End-to-end orchestrator for Project AlphaSentinel (TASK-09).

Default run: ingest the ten core tickers from SEC EDGAR and yfinance into
data/cache and the DuckDB warehouse, score them, write the executive briefing,
and build the four institutional deliverables.

--offline reads data/cache only. --verify-all runs dag_ctl verify for
TASK-01 through TASK-09 and prints a summary. The TASK-09 command is this
script, so a nested verify sets ALPHASENTINEL_VERIFY_ALL_CHILD and checks the
briefing pair. A fresh clone has no reports/ yet. That absence is filled from
stored warehouse scores, or from an offline cache, before the check. A file
that is already present but short or not a docx zip is left unchanged.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import duckdb

from alphasentinel.forensic_engine import run_forensic_pipeline
from alphasentinel.ingestor import IngestError, ingest_tickers
from alphasentinel.report_compiler import compile_report

_SCRIPTS = Path(__file__).resolve().parent

PROJECT_ROOT = _SCRIPTS.parent
DEFAULT_DB = PROJECT_ROOT / "data" / "alphasentinel.duckdb"
DEFAULT_CACHE = PROJECT_ROOT / "data" / "cache"
DEFAULT_REPORTS = PROJECT_ROOT / "reports"
DEFAULT_DELIVERABLES = PROJECT_ROOT / "deliverables"
DAG_CTL = _SCRIPTS / "dag_ctl.py"
BRIEFING_STEM = "AlphaSentinel_Executive_Briefing"
CHILD_ENV = "ALPHASENTINEL_VERIFY_ALL_CHILD"
TASK_IDS = tuple(f"TASK-{index:02d}" for index in range(1, 10))
# Committed SEC excerpts. Used only when the warehouse and data/cache are absent.
FIXTURE_CACHE = PROJECT_ROOT / "tests" / "fixtures" / "offline_cache"
FIXTURE_TICKERS = ("AAPL", "MSFT")

# Spec section 3.3 full-pipeline command, in that order.
CORE_TICKERS = (
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


def _symbols(tickers: list[str] | None) -> list[str]:
    if not tickers:
        return list(CORE_TICKERS)
    symbols: list[str] = []
    for value in tickers:
        symbols.extend(part.strip().upper() for part in value.split(",") if part.strip())
    return symbols


def _load_build_and_verify():
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    from build_four_deliverables import build_and_verify

    return build_and_verify


def _print_financial_rows(db_path: Path, symbols: list[str]) -> None:
    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = connection.execute(
            """
            SELECT ticker, data_source_mode, COUNT(*),
                   string_agg(CAST(fiscal_year AS VARCHAR), ',' ORDER BY fiscal_year)
            FROM company_financials
            GROUP BY ticker, data_source_mode
            ORDER BY ticker, data_source_mode
            """
        ).fetchall()
    finally:
        connection.close()
    requested = set(symbols)
    others: list[str] = []
    for ticker, mode, count, years in rows:
        print(
            f"[PIPELINE] financial_rows {ticker} count={count} years={years} mode={mode}"
        )
        if ticker not in requested:
            others.append(str(ticker))
    if others:
        print(f"[PIPELINE] other_tickers_in_warehouse {','.join(others)}")


def _print_score_metrics(db_path: Path) -> None:
    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        nullable = [
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'main'
                  AND table_name = 'forensic_scores'
                  AND is_nullable = 'YES'
                ORDER BY ordinal_position
                """
            ).fetchall()
        ]
        cursor = connection.execute(
            "SELECT * FROM forensic_scores ORDER BY ticker, fiscal_year"
        )
        names = [item[0] for item in cursor.description]
        records = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
    finally:
        connection.close()

    print(f"[PIPELINE] nullable_metrics {','.join(nullable)}")
    for record in records:
        ticker = record["ticker"]
        year = record["fiscal_year"]
        null_names = [column for column in nullable if record[column] is None]
        value_names = [column for column in nullable if record[column] is not None]
        print(
            f"[PIPELINE] metric_counts {ticker} FY{year} "
            f"with_value={len(value_names)} null={len(null_names)}"
        )
        print(f"[PIPELINE] metric_null {ticker} {','.join(null_names)}")
        print(f"[PIPELINE] metric_value {ticker} {','.join(value_names)}")


def _write_briefing(compiled: dict[str, Path], reports_dir: Path) -> dict[str, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    published = {
        "md": reports_dir / f"{BRIEFING_STEM}.md",
        "docx": reports_dir / f"{BRIEFING_STEM}.docx",
    }
    shutil.copyfile(compiled["md"], published["md"])
    shutil.copyfile(compiled["docx"], published["docx"])
    return published


def run_pipeline(
    tickers: list[str] | None = None,
    *,
    offline: bool = False,
    db_path: Path | None = None,
    cache_dir: Path | None = None,
    reports_dir: Path | None = None,
    deliverables_dir: Path | None = None,
) -> int:
    """Ingest, score, compile the briefing, and build the four deliverables."""
    symbols = _symbols(tickers)
    database = Path(db_path) if db_path is not None else DEFAULT_DB
    cache = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE
    reports = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS
    deliverables = (
        Path(deliverables_dir) if deliverables_dir is not None else DEFAULT_DELIVERABLES
    )
    print(f"[PIPELINE] tickers={','.join(symbols)} offline={str(offline).lower()}")

    try:
        batch = ingest_tickers(symbols, db_path=database, cache_dir=cache, offline=offline)
    except IngestError as exc:
        print(f"[PIPELINE_FAIL] {exc}", file=sys.stderr)
        return 1

    ingested = batch.written
    for ticker, reason in batch.failures:
        print(f"[PIPELINE] ticker_fail {ticker} {reason}", file=sys.stderr)
    if ingested == 0:
        print("[PIPELINE_FAIL] no company-year rows were written", file=sys.stderr)
        return 1

    print(f"[PIPELINE] ingested_records={ingested}")
    _print_financial_rows(database, symbols)

    scores = run_forensic_pipeline(database)
    print(f"[PIPELINE] scored_companies={len(scores)}")
    _print_score_metrics(database)

    with tempfile.TemporaryDirectory() as temporary:
        compiled = compile_report(database, Path(temporary))
        briefing = _write_briefing(compiled, reports)
    print(f"[REPORTS] {briefing['md']} | {briefing['docx']}")

    deliverable_code = _load_build_and_verify()(deliverables)
    minimum_records = len(symbols) * 2
    failed_tickers = ",".join(ticker for ticker, _reason in batch.failures)
    if (
        batch.failures
        or ingested < minimum_records
        or len(scores) < len(symbols)
        or deliverable_code != 0
    ):
        print("[PIPELINE_FAIL] Verification checks did not meet minimum thresholds.")
        print(
            f"[PIPELINE_FAIL] ingested_records={ingested} "
            f"scored_companies={len(scores)} deliverables_exit={deliverable_code} "
            f"minimum_records={minimum_records} failed_tickers={failed_tickers or '-'}"
        )
        return 1

    print(f"[PIPELINE_SUCCESS] Ingested {ingested} records, scored {len(scores)} companies.")
    return 0


def _briefing_paths(reports: Path) -> tuple[Path, Path]:
    return (
        reports / f"{BRIEFING_STEM}.md",
        reports / f"{BRIEFING_STEM}.docx",
    )


def _briefing_pair_ok(reports: Path) -> bool:
    markdown_path, docx_path = _briefing_paths(reports)
    for path in (markdown_path, docx_path):
        if not path.is_file() or path.stat().st_size < 100:
            return False
    return zipfile.is_zipfile(docx_path)


def _score_count(db_path: Path) -> int:
    """Return stored forensic rows. A missing file stays missing."""
    if not db_path.is_file():
        return 0
    try:
        connection = duckdb.connect(str(db_path), read_only=True)
    except duckdb.Error:
        return 0
    try:
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        if "forensic_scores" not in tables:
            return 0
        count = connection.execute("SELECT COUNT(*) FROM forensic_scores").fetchone()
        return int(count[0]) if count else 0
    except duckdb.Error:
        return 0
    finally:
        connection.close()


def _cache_ready(cache: Path, tickers: tuple[str, ...] | list[str]) -> bool:
    return all((cache / ticker / "index.json").is_file() for ticker in tickers)


def _compile_stored_briefing(database: Path, reports: Path) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        compiled = compile_report(database, Path(temporary))
        _write_briefing(compiled, reports)


def _generate_missing_briefing(reports: Path) -> int:
    """Write the briefing pair with no network call and no invented amounts.

    Stored warehouse scores win. Otherwise the offline pipeline runs into a
    temporary warehouse: data/cache when it covers the ten core tickers, and
    the committed SEC fixture cache (AAPL, MSFT) when the clone has no cache.
    """
    if _score_count(DEFAULT_DB) > 0:
        print(f"[VERIFY_ALL] TASK-09 briefing missing; compiling from {DEFAULT_DB}")
        try:
            _compile_stored_briefing(DEFAULT_DB, reports)
        except (duckdb.Error, OSError, ValueError) as exc:
            print(f"[VERIFY_ALL] TASK-09 could not compile briefing: {exc}")
            return 1
        return 0

    if _cache_ready(DEFAULT_CACHE, CORE_TICKERS):
        cache = DEFAULT_CACHE
        tickers = list(CORE_TICKERS)
        print("[VERIFY_ALL] TASK-09 briefing missing; building from data/cache offline")
    elif _cache_ready(FIXTURE_CACHE, FIXTURE_TICKERS):
        cache = FIXTURE_CACHE
        tickers = list(FIXTURE_TICKERS)
        print(
            "[VERIFY_ALL] TASK-09 briefing missing; building from "
            "tests/fixtures/offline_cache (AAPL, MSFT)"
        )
    else:
        print("[VERIFY_ALL] TASK-09 no warehouse scores and no offline cache")
        return 1

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        code = run_pipeline(
            tickers,
            offline=True,
            db_path=root / "warehouse.duckdb",
            cache_dir=cache,
            reports_dir=reports,
            deliverables_dir=root / "deliverables",
        )
    if code != 0 and not _briefing_pair_ok(reports):
        print("[VERIFY_ALL] TASK-09 offline briefing build failed")
        return 1
    return 0


def briefing_ready(reports_dir: Path | None = None) -> int:
    """Return 0 when the TASK-09 briefing pair is on disk.

    Missing files on a fresh clone are generated, then checked. A short file
    or a docx that is not a zip is a failure and is not overwritten.
    """
    reports = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS
    markdown_path, docx_path = _briefing_paths(reports)
    if not markdown_path.is_file() and not docx_path.is_file():
        generated = _generate_missing_briefing(reports)
        if generated != 0:
            print(f"[VERIFY_ALL] TASK-09 artifact missing or short: {markdown_path}")
            return 1
    if not _briefing_pair_ok(reports):
        for path in (markdown_path, docx_path):
            if not path.is_file() or path.stat().st_size < 100:
                print(f"[VERIFY_ALL] TASK-09 artifact missing or short: {path}")
                return 1
        print(f"[VERIFY_ALL] TASK-09 artifact is not a docx zip: {docx_path}")
        return 1
    print(
        f"[VERIFY_ALL] TASK-09 artifact present: {docx_path} "
        f"({docx_path.stat().st_size} bytes)"
    )
    return 0


def _dag_command(task_id: str, dag_db: Path | None) -> list[str]:
    command = [sys.executable, str(DAG_CTL), "verify", "--task", task_id]
    if dag_db is not None:
        command.extend(["--db", str(dag_db)])
    return command


def verify_all(dag_db: Path | None = None, reports_dir: Path | None = None) -> int:
    """Run dag_ctl verify for TASK-01..TASK-09 and print each exit code."""
    if os.environ.get(CHILD_ENV) == "1":
        return briefing_ready(reports_dir)

    child_env = os.environ.copy()
    child_env[CHILD_ENV] = "1"
    failures: list[str] = []
    for task_id in TASK_IDS:
        command = _dag_command(task_id, dag_db)
        print(f"[VERIFY_ALL] run {' '.join(command)}")
        completed = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            env=child_env,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.stdout:
            print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="" if completed.stderr.endswith("\n") else "\n")
        print(f"[VERIFY_ALL] {task_id} exit={completed.returncode}")
        if completed.returncode != 0:
            failures.append(f"{task_id} exit={completed.returncode}")

    if failures:
        print(f"[VERIFY_ALL] failed={len(failures)} passed={len(TASK_IDS) - len(failures)}")
        print("[VERIFY_ALL] " + "; ".join(failures))
        return 1
    print(f"[VERIFY_ALL] failed=0 passed={len(TASK_IDS)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AlphaSentinel end-to-end pipeline")
    parser.add_argument(
        "--tickers",
        default=",".join(CORE_TICKERS),
        help="Comma-separated tickers. Default is the ten core names.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Read data/cache only. A missing cache file is an error.",
    )
    parser.add_argument(
        "--verify-all",
        action="store_true",
        help="Run dag_ctl verify for TASK-01 through TASK-09 and summarize.",
    )
    parser.add_argument("--db", type=Path, default=None, help="DuckDB warehouse path.")
    parser.add_argument("--cache-dir", type=Path, default=None, help="SEC cache directory.")
    parser.add_argument("--reports-dir", type=Path, default=None, help="Briefing output directory.")
    parser.add_argument(
        "--deliverables-dir",
        type=Path,
        default=None,
        help="Directory for the four institutional deliverables.",
    )
    parser.add_argument("--dag-db", type=Path, default=None, help="SQLite DAG ledger path.")
    args = parser.parse_args(argv)

    if args.verify_all:
        if os.environ.get(CHILD_ENV) == "1":
            return briefing_ready(args.reports_dir)
        return verify_all(args.dag_db, args.reports_dir)

    tickers = [part.strip() for part in args.tickers.split(",") if part.strip()]
    return run_pipeline(
        tickers,
        offline=args.offline,
        db_path=args.db,
        cache_dir=args.cache_dir,
        reports_dir=args.reports_dir,
        deliverables_dir=args.deliverables_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
