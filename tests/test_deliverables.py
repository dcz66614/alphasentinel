"""Deliverable generation and verification tests using temporary directories."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import docx

from scripts.build_four_deliverables import (
    build_and_verify,
    build_deliverables,
    extract_spec_deliverables,
    render_markdown_to_docx,
    verify_deliverables,
)

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_four_deliverables.py"


def test_build_and_verify_programmatic(tmp_path: Path) -> None:
    output_dir = tmp_path / "deliverables_prog"
    paths = build_deliverables(output_dir)

    for key in ("charter_md", "charter_docx", "plan_md", "plan_docx"):
        assert key in paths
        fp = paths[key]
        assert fp.is_file()
        assert fp.stat().st_size >= 100

    assert verify_deliverables(output_dir) == 0


def test_build_and_verify_convenience_function(tmp_path: Path) -> None:
    output_dir = tmp_path / "deliverables_combo"
    exit_code = build_and_verify(output_dir)
    assert exit_code == 0
    assert (output_dir / "PROJECT_CHARTER.docx").is_file()
    assert (output_dir / "AGENT_EXECUTION_PLAN.docx").is_file()


def test_cli_generation_and_verify_in_temp_dir(tmp_path: Path) -> None:
    cli_dir = tmp_path / "cli_deliverables"

    # Step 1: Run generation via CLI
    gen_proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output-dir", str(cli_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert gen_proc.returncode == 0, gen_proc.stdout + gen_proc.stderr
    assert "[OK] All 4 deliverables successfully built" in gen_proc.stdout

    # Step 2: Run verification via CLI (--verify)
    ver_proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output-dir", str(cli_dir), "--verify"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ver_proc.returncode == 0, ver_proc.stdout + ver_proc.stderr
    assert "[OK] Verified deliverable: " in ver_proc.stdout
    assert "PROJECT_CHARTER.docx" in ver_proc.stdout
    assert "AGENT_EXECUTION_PLAN.docx" in ver_proc.stdout


def test_verify_fails_on_empty_directory(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir(parents=True, exist_ok=True)

    # Programmatic check
    assert verify_deliverables(empty_dir) == 1

    # CLI check
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output-dir", str(empty_dir), "--verify"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "[FAIL] Deliverable missing" in proc.stdout


def test_verify_fails_on_corrupt_docx(tmp_path: Path) -> None:
    output_dir = tmp_path / "corrupt_test"
    build_deliverables(output_dir)

    # Overwrite docx with non-zip junk larger than 100 bytes
    (output_dir / "PROJECT_CHARTER.docx").write_bytes(b"NOT_A_VALID_DOCX_FILE_DATA_PADDING_" * 10)

    assert verify_deliverables(output_dir) == 1

    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output-dir", str(output_dir), "--verify"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "[FAIL] Invalid OpenXML .docx archive" in proc.stdout


def test_verify_fails_on_truncated_deliverable(tmp_path: Path) -> None:
    output_dir = tmp_path / "truncated_test"
    build_deliverables(output_dir)

    # Truncate markdown to fewer than 100 bytes
    (output_dir / "PROJECT_CHARTER.md").write_text("# Too short", encoding="utf-8")

    assert verify_deliverables(output_dir) == 1

    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output-dir", str(output_dir), "--verify"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "[FAIL] Deliverable empty or truncated" in proc.stdout


def test_docx_structure_headings_tables_and_code_font(tmp_path: Path) -> None:
    output_dir = tmp_path / "format_check"
    build_deliverables(output_dir)

    charter_docx = docx.Document(str(output_dir / "PROJECT_CHARTER.docx"))
    plan_docx = docx.Document(str(output_dir / "AGENT_EXECUTION_PLAN.docx"))

    # Verify headings exist
    charter_headings = [p.text for p in charter_docx.paragraphs if p.style.name.startswith("Heading")]
    assert len(charter_headings) >= 3
    plan_headings = [p.text for p in plan_docx.paragraphs if p.style.name.startswith("Heading")]
    assert len(plan_headings) >= 2

    # Verify tables exist with formatted header
    assert len(charter_docx.tables) >= 1
    charter_table = charter_docx.tables[0]
    assert len(charter_table.rows) >= 2
    assert any(run.bold for p in charter_table.rows[0].cells[0].paragraphs for run in p.runs)

    assert len(plan_docx.tables) >= 1
    plan_table = plan_docx.tables[0]
    assert len(plan_table.rows) >= 2
    assert any(run.bold for p in plan_table.rows[0].cells[0].paragraphs for run in p.runs)

    # Verify code block font is Courier New
    charter_courier_runs = [
        run for p in charter_docx.paragraphs for run in p.runs if run.font.name == "Courier New"
    ]
    assert len(charter_courier_runs) >= 1

    plan_courier_runs = [
        run for p in plan_docx.paragraphs for run in p.runs if run.font.name == "Courier New"
    ]
    assert len(plan_courier_runs) >= 1


def test_content_fidelity_and_zero_fabricated_numbers(tmp_path: Path) -> None:
    charter_md, plan_md = extract_spec_deliverables()

    # Spec-faithful constants only
    assert "-4.84" in charter_md
    assert "-1.78" in charter_md
    assert "2.99" in charter_md
    assert "1.81" in charter_md
    assert "REQ-ING-01" in charter_md
    assert "REQ-DEL-01" in charter_md
    assert "60.0" in charter_md

    assert "@CommanderBot" in plan_md
    assert "@SpecArchitectBot" in plan_md
    assert "@DataEngineBot" in plan_md
    assert "@QuantForensicBot" in plan_md
    assert "@UIAndReportBot" in plan_md
    assert "TASK-01" in plan_md
    assert "TASK-09" in plan_md
    assert "max_attempts = 3" in plan_md


def test_render_markdown_to_docx_standalone(tmp_path: Path) -> None:
    sample = (
        "# Title\n\n"
        "## Subhead\n\n"
        "- Bullet 1\n\n"
        "| H1 | H2 |\n| :--- | :--- |\n| V1 | V2 |\n\n"
        "```python\nprint(123)\n```\n"
    )
    target = tmp_path / "standalone.docx"
    render_markdown_to_docx(sample, target)
    assert target.is_file()

    doc = docx.Document(str(target))
    assert len(doc.tables) == 1
    assert any(r.font.name == "Courier New" for p in doc.paragraphs for r in p.runs)
