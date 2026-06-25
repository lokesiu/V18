# 明证台 / V18 — Master Evidence Platform

> **PySide6 desktop workbench for legal defense document generation**
> A dual-AI pipeline (DeepSeek extract/strategy + MiMo critique/review) running a 9-stage workflow to produce structured legal defense documents from raw case materials.

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue)](.github/workflows/test.yml)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue)](pyproject.toml)
[![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-lightgrey)](pyproject.toml)
[![Status](https://img.shields.io/badge/Status-V18_RC-orange)](CHANGELOG.md)

---

## What is this?

明证台 (Master Evidence Platform) is a Windows desktop application that helps legal professionals:

1. **Ingest** raw case materials (PDFs, DOCX, scans, OCR)
2. **Extract** structured facts via the dual-AI pipeline
3. **Distill** facts into a defense narrative
4. **Render** structured DOCX / PDF / XLSX / ZIP deliverables
5. **Audit** every output through 5 quality gates before delivery

The pipeline uses **two cooperating AI models** that alternate stages — DeepSeek (extract / strategy) and MiMo (critique / review) — with a single `PipelineContext` (defined in `core/fact_card.py`) flowing through all 9 stages.

## Status

**V18 RC** — see [CHANGELOG.md](CHANGELOG.md) for release history. Project knowledge base: [AGENTS.md](AGENTS.md).

## Quick start (Windows)

```powershell
# 1. Clone
git clone <repo-url> V18
cd V18

# 2. Create venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .

# 4. Verify
python scripts/verify_harness.py   # checks .harness/ integrity
python -m pytest tests/ -v          # runs full test suite

# 5. Run the desktop app
python -m app.main_window

# Or use the CLI
python -m core.runner doctor
python -m core.runner analyze --input <case_dir> --identity <id> --goal <goal> --out <out_dir>
```

## Architecture

### High-level flow

```
Documents in  →  extract  →  fact card  →  pipeline  →  render  →  quality gate  →  output
                (API-A)    (DistilledCard)  (9 stages)   (DOCX/PDF/  (5 gates)        (ZIP)
              + regex                     (DeepSeek+    XLSX)
              fallback                      MiMo)
```

### Reins (project-scoped agent team)

The project ships with 4 `reins` (project-scoped agents) that each own a domain. They are loaded automatically when this project is opened. See [`.harness/team.yaml`](.harness/team.yaml) for the full definition.

| Rein | Owns | Routes |
|------|------|--------|
| `gui-rein` | `app/` (PySide6 pages, workers, auth UI) | `gui`, `ui`, `pyside6`, `desktop` |
| `pipeline-rein` | `core/workflow/`, `core/ai/`, extract / distill | `pipeline`, `workflow`, `ai`, `deepseek`, `mimo`, `extract`, `distill` |
| `qa-rein` | `core/quality/`, `tests/` | `quality`, `gate`, `test`, `tdd`, `pytest`, `qa` |
| `render-rein` | `core/render/`, `templates/`, `core/intake.py` | `render`, `docx`, `pdf`, `template`, `jinja2`, `xlsx` |

Invoke a rein: `/<name> <task>` in chat, or `mavis session start --agent <name>`.

## Repository layout

```
V18/
├── app/                      # PySide6 GUI
├── core/                     # Business logic
│   ├── ai/                   # DeepSeek + MiMo clients
│   ├── auth/                 # License + machine_id
│   ├── contracts/            # Abstract interfaces
│   ├── pipeline/             # Step-level orchestrator
│   ├── quality/              # Quality gates + artifact auditors
│   ├── render/               # DOCX / PDF / XLSX / ZIP renderers
│   ├── scenario/             # Defense scenarios
│   └── workflow/             # Dual-AI 9-stage pipeline
├── tests/                    # 45 test files (~965 tests)
├── scripts/                  # Utilities (verify_harness, scan_repo, debug)
├── prompts/                  # AI prompt templates
├── templates/                # DOCX templates
├── docs/                     # Long-form documentation
├── .harness/                 # Reins team config (4 reins)
│   ├── team.yaml
│   └── reins/<name>/AGENTS.md
├── .github/workflows/        # CI
├── AGENTS.md                 # Project knowledge base (read first)
├── pyproject.toml            # Build + tool config
├── requirements*.txt         # Runtime + dev dependencies
└── CHANGELOG.md              # Release history
```

## Testing

```bash
# Quick smoke (~0.2s)
python scripts/verify_harness.py

# Single test module
python -m pytest tests/test_tdd_pipeline.py -v

# Full suite (~3 min on Windows)
python -m pytest tests/ -v

# With coverage (requires pytest-cov)
python -m pytest tests/ --cov=core --cov-report=term --cov-report=html
```

Baseline (commit `6f2ff27+`): 924 passed / 41 failed / 174.88s. The 41 failures are environmental (LibreOffice missing, license state, etc.) — see [AGENTS.md § Testing](AGENTS.md) for the breakdown.

## CI

GitHub Actions runs on every push to `master` and every PR:

1. Install dependencies from `requirements.txt` + `requirements-dev.txt`
2. Smoke pytest (`--maxfail=5 -x`)
3. Full pytest suite
4. `scripts/verify_harness.py` (catches `.harness/` drift)
5. `scripts/scan_repo.py` (catches missing docs / new hardcoded secrets / etc.)

See [`.github/workflows/test.yml`](.github/workflows/test.yml) for details.

## Contributing

Read [AGENTS.md](AGENTS.md) first — it has the full project knowledge base, conventions, and anti-patterns. Then check the rein that owns your area:

- Touching `app/`? Read [`.harness/reins/gui-rein/AGENTS.md`](.harness/reins/gui-rein/AGENTS.md)
- Touching the pipeline? Read [`.harness/reins/pipeline-rein/AGENTS.md`](.harness/reins/pipeline-rein/AGENTS.md)
- Touching quality gates or tests? Read [`.harness/reins/qa-rein/AGENTS.md`](.harness/reins/qa-rein/AGENTS.md)
- Touching renderers? Read [`.harness/reins/render-rein/AGENTS.md`](.harness/reins/render-rein/AGENTS.md)

**NEVER** call `core.runner.main()` or `DualAIOrchestrator` directly from a page class — always through `AnalysisWorker`.
**NEVER** render from `FactCard` directly — always through `distill()` first.
**NEVER** hardcode template paths — use `templates/` and handle `TemplateNotFoundError`.

## License

**Proprietary — All Rights Reserved.** See [LICENSE](LICENSE).

V18 is closed-source commercial software. Distribution, modification, and reverse engineering are prohibited without written permission.

## Support

Internal: see `docs/AUTH.md` for team contact info.

---

**Last updated**: 2026-06-25
**Version**: V18 RC
**Generated by**: Mavis (during init bootstrap, commit 6f2ff27+)
