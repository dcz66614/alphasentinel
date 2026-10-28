# Project AlphaSentinel — Zero-Thinking Agent Execution Plan (确定性执行计划书)

## 1. Grok Bot 5-Agent Roster & Single-Threaded Write Ownership

| Task ID | Assigned Grok Bot | Owned Artifact Path | Deterministic Verification Command |
| :--- | :--- | :--- | :--- |
| TASK-01 | @CommanderBot | scripts/dag_ctl.py | python3 scripts/dag_ctl.py status |
| TASK-02 | @SpecArchitectBot | src/db_schema.py | pytest tests/test_schema.py |
| TASK-03 | @DataEngineBot | src/ingestor.py | pytest tests/test_ingestor.py |
| TASK-04 | @QuantForensicBot | src/forensic_engine.py | pytest tests/test_forensic.py |
| TASK-05 | @UIAndReportBot | src/report_compiler.py | pytest tests/test_reports.py |
| TASK-06 | @UIAndReportBot | src/api_server.py | pytest tests/test_api.py |
| TASK-07 | @UIAndReportBot | src/dashboard.py | python3 -m py_compile src/dashboard.py |
| TASK-08 | @UIAndReportBot | deliverables/PROJECT_CHARTER.docx | python3 scripts/build_four_deliverables.py --verify |
| TASK-09 | @CommanderBot | reports/AlphaSentinel_Executive_Briefing.docx | python3 scripts/run_pipeline.py --verify-all |

## 2. Hard Operational Rules & Guardrails
- **Max Retries**: Every task in `state/dag_state.db` is capped at `max_attempts = 3`.
- **Single-Threaded Writes**: Never edit a file owned by another Bot.
- **Handoff Protocol**: Only post a Group Chat `@BotName` handoff after `dag_ctl.py verify --task TASK-XX` returns exit code 0.
- **Routine Scheduling**: Once TASK-09 passes, @CommanderBot saves the workflow as Skill `AlphaSentinel-Daily-Audit` and schedules Routine at 08:00 UTC weekdays with Auto-review set to `Ask first` for any external publishing.

## 3. Machine Constitution & Operational Commands

```text
Activate Virtualenv: source .venv/bin/activate
Check DAG Status: python scripts/dag_ctl.py status
Run All Tests: pytest tests/ -v --tb=short
Compile Deliverables: python scripts/build_four_deliverables.py --verify
```