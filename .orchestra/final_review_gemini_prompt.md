You are the FINAL read-only reviewer (Gemini) for the AlphaSentinel project. Working directory: C:\Users\Du200\Projects\alphasentinel\.orchestra\review_final (detached at 3a8478d = current master, all tasks A00-A10 merged).
Spec: C:\Users\Du200\Projects\alphasentinel\docs\spec\ (the .txt file is the authoritative spec, TASK-01..TASK-07). Task history: C:\Users\Du200\Projects\alphasentinel\.orchestra\IMPLEMENTATION_LOG.md and C:\Users\Du200\Projects\alphasentinel\.orchestra\TASKBOARD.md; per-task reports C:\Users\Du200\Projects\alphasentinel\.orchestra\A*_report.md.
Do:
1. Run: uv sync; uv run python -m pytest -q; uv run ruff check . (record exact results).
2. Check every spec requirement of TASK-01..07 against the code; list each as MET / PARTIAL / MISSING with file references.
3. Check data honesty: no fabricated, random, zero-filled or interpolated financial values; missing SEC data must stay NULL and be documented.
4. Check deliverables/ (reports, docs) are consistent with the real pipeline output, and that README explains how to install and run on Windows and Linux.
5. List concrete, prioritized fix items (blocker / major / minor).
STRICT RULES: Do NOT modify, create or delete any file except one: write your full review (in Chinese or English) to C:\Users\Du200\Projects\alphasentinel\.orchestra\FINAL_REVIEW_gemini.md. Do not git commit. Do not call paid APIs. End the review with a single line: VERDICT: PASS or VERDICT: FAIL.