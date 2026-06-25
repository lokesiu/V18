# scripts/_legacy_root/ — Archived V18 root-directory scripts

**Created**: 2026-06-25 (commit 6f2ff27+1)
**Reason**: The V18 repo root had accumulated ~28 untracked debug/check/audit
scripts that no test imports. They polluted `git status` and obscured the
real entry points. This directory preserves them for reference without
cluttering the project root.

## What's here

| Pattern | Purpose | Count |
|---------|---------|-------|
| `check_*.py` | One-off config / API / case-id / chinese / colon sanity checks | 6 |
| `debug_*.py` | Ad-hoc body-lines / chengying / classify / extract / signature debug | 5 |
| `audit_*.py` | One-shot audit scripts (e.g. chengying V2) | 1 |
| `export_*.py` | One-off DOCX / MiMo-review exporters | 2 |
| `extract_pdf_text.py` | Standalone PDF text extraction | 1 |
| `gen_*.py` | One-off document generators (chengying V2) | 1 |
| `inspect_*.py` | Ad-hoc doc inspector | 1 |
| `regen_*.py` / `regenerate_*.py` | One-shot re-renderers | 3 |
| `show_*.py` | Display helpers (chengying V2) | 1 |
| `test_*.py` | Standalone validation tests (NOT pytest-discovered) | 4 |
| `verify_*.py` | One-shot verification scripts (fix / template / v3 output) | 3 |
| `best_name` | Empty stray file (0 bytes, no extension) | 1 |

**Total**: 28 files (27 .py + 1 empty).

## Are these still useful?

Probably not — the `scripts/` directory (the parent) already has 30+ similar
utilities (`analyze_coverage.py`, `check_all_docs.py`, `fix_issues.py`,
`verify_pdf.py`, etc.) that ARE actively used. The scripts in this archive
were either superseded by the ones in `scripts/`, or were one-off debug aids
that already served their purpose.

If you find you need one of them back:
1. `mv scripts/_legacy_root/<name>.py .` (back to root)
2. Or open it from here and copy the logic

## How this directory is organized

This is a **git-tracked** directory (under `scripts/`) so the move is
auditable. Once you're confident nothing in here is needed, you can:

```bash
git rm -r scripts/_legacy_root/
git commit -m "chore: remove archived root debug scripts"
```

## What we KEPT in the root (and why)

| File | Reason kept |
|------|-------------|
| `launch_app.py` | Real desktop app launcher (used in `run_gui.bat`) |
| `launch_keygen.py` | License keygen GUI launcher |
| `mock_assets.py` | Test fixture loader (may be imported by manual tests) |
| `run_gui.bat` | Windows GUI launcher (developer entry point) |
