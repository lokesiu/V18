# CHANGELOG — V18 / 明证台

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Convention**: `type: subject` per commit (types: `feat`, `fix`, `refactor`,
`test`, `chore`, `docs`).

---

## [Unreleased] — 2026-06-25

### Added
- **CI workflow** (`.github/workflows/test.yml`): GitHub Actions runs pytest
  + harness self-test on every push to `master` and every PR
- **Harness self-test** (`scripts/verify_harness.py`): 13-check validator
  for `.harness/team.yaml` + reins + AGENTS.md coherence
- **Repo hygiene scanner** (`scripts/scan_repo.py`): detects missing docs,
  hardcoded secrets, new `print()` calls in `core/`
- **Dependency manifests**: `requirements.txt` (30 runtime deps) +
  `requirements-dev.txt` (pytest, pytest-cov, ruff, mypy, pyinstaller)
- **`pyproject.toml`**: PEP 621 build config with 5 CLI entry points
  (`v18-doctor`, `v18-analyze`, `v18-inspect`, `v18-package`,
  `v18-selfcheck`), ruff + mypy tool config
- **README.md** (6.8 KB): project intro, quick-start, reins overview,
  contributing guide
- **LICENSE** (2.3 KB): placeholder proprietary license — replace with
  actual legal terms before public distribution
- **AGENTS.md** additions: `REIN TEAM` table, `TESTING` baseline (924
  passed / 41 failed), `CI` workflow, `REPO HYGIENE` rules
- **`.gitignore` hardening**: `.coverage`, `htmlcov/`, `reports/`,
  `test_run/`, `screenshots/`, `.omo/`, `.opencode/`, `.continue/`,
  `run_*.log`, `*_debug.log`, `test_*.png`

### Changed
- **`team.yaml`**: `render-rein` now has `skills: [docx, pdf]`
- **Root cleanup**: 28 untracked debug scripts moved to
  `scripts/_legacy_root/` with a `README.md` explaining how to restore

---

## [18.0.0-rc1] — 2026-06-20 to 2026-06-25

### Test coverage ramp (62% → 87%)

- `780c6c2` — refactor: extract shared text_utils, fix regex compilation,
  fix match ratio bug
- `25862d9` — fix: remove debug prints, add settings load logging
- `acd0332` — test: step2/step5 exception paths via sys.modules (10 new,
  62%/60% → 86%/97%)
- `357bce5` — test: pipeline orchestrator exception paths (7 new, 62% → 83%)
- `3a39a21` — test: mock HTTP for deepseek/mimo/multimodal/unified (36 new,
  85% → 87%)
- `9ffb325` — test: pipeline steps exception paths + multimodal +
  ai_client (18 new, 84% → 85%)
- `056ec78` — test: multimodal_router full routing coverage (23 new, 28% → 95%)
- `cd921ed` — test: dual_ai_orchestrator + multimodal + events/stages (27 new,
  80% → 83%)
- `5ed1275` — test: mock API paths for step3/step4/unified_client (25 new,
  78% → 80%)
- `d19cb92` — test: template_fill + pipeline init + ai_client + checkpoint
  (37 new, 77% → 78%)
- `3319468` — test: step6_llm_generate mock API coverage (28 new, 40% → 93%)
- `1b3a7ee` — test: settings_store + audit_store coverage (47 new, 67%/60%
  → 91%/91%)
- `5ca43a2` — test: AI provider registry + clients (28 new, 39%/44%/42%
  → 95%/65%/67%)
- `0d67317` — test: defense_quality_gate full branch coverage (30 new, 49%
  → 92%)
- `f2268a4` — test: intake.py file routing + image handling (25 new, 50%
  → 77%)
- `6a3758c` — test: scenario registry + defense scenario (31 new, 36%/43%
  → 100%)
- `01db43e` — test: runner.py CLI commands coverage (19 new, 32% → 85%)
- `e9adaa5` — test: pdf_converter branch coverage (24 new, 46% → 77%)
- `833e7af` — test: step7_render main function + exception paths (22 new,
  71% → 89%)

### Init bootstrap (2026-06-25)

- `6f2ff27` — chore: bootstrap AGENTS.md + .harness/ multi-agent team
  (4 reins) + carry WIP

---

## Pre-history

V18 development prior to 2026-06-20 was tracked in a different VCS. This
CHANGELOG only covers git-tracked history. For project knowledge, see
[AGENTS.md](AGENTS.md) and [`.harness/`](.harness/).
