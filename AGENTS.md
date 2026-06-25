# 明证台 V18 Beta — PROJECT KNOWLEDGE BASE

**Generated:** 2026-06-23
**Commit:** 780c6c2 (refactor: extract shared text_utils, fix regex compilation, fix match ratio bug)
**Branch:** master

## OVERVIEW

明证台 (Master Evidence Platform) — A PySide6 legal document workbench that runs a dual-AI pipeline (DeepSeek extract/strategy + MiMo critique/review) through a 9-stage pipeline to generate structured legal defense documents.

## STRUCTURE

```
D:\codex\V18/
├── app/                    # PySide6 GUI (FluentWindow, pages/, widgets/)
├── core/                   # Business logic — AI clients, pipeline, renderers, auth
│   ├── ai/                 # DeepSeek + MiMo clients, multimodal router
│   ├── auth/               # License, keygen, machine_id auth
│   ├── contracts/          # Abstract interfaces (WorkflowStage, Renderer, QualityGate, Scenario, AIProvider)
│   ├── pipeline/            # Pipeline orchestrator (step-level)
│   ├── providers/          # Provider registry
│   ├── quality/            # Quality gates, artifact auditors, doc checkers
│   ├── render/             # DOCX, PDF, XLSX, ZIP renderers
│   ├── scenario/           # Scenario registry and defense scenarios
│   └── workflow/           # Dual AI orchestrator, event bus, stage definitions
├── tests/                  # TDD tests (test_tdd_*.py pattern)
├── scripts/                # One-off analysis, smoke tests, debug scripts
├── prompts/                # AI prompt templates
├── templates/              # DOCX template files
├── test_run_judgment/      # End-to-end judgment pipeline scripts
└── root-level .py files    # Debug, verify, export, smoke scripts
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| GUI window / pages | `app/main_window.py` | PySide6 FluentWindow, 6 pages |
| Pipeline entry | `core/runner.py` | CLI: doctor/analyze/inspect/package/selfcheck |
| Dual AI orchestrator | `core/workflow/dual_ai_orchestrator.py` | 9-stage dual AI pipeline |
| AI clients | `core/ai/deepseek_client.py`, `core/ai/mimo_client.py` | Both implement AIProvider contract |
| Fact extraction | `core/extract.py` | API-A (LLM) + regex fallback |
| Data contracts | `core/fact_card.py` | PipelineContext, FactCard, Party, SourceRef — shared by ALL stages |
| Document rendering | `core/render/docx_renderer.py`, `core/render/pdf_converter.py`, `core/render/xlsx_renderer.py` | Jinja2 + docxtpl templates |
| Quality gates | `core/quality/pipeline_gates.py`, `core/quality/defense_quality_gate.py` | Step-level + final gate |
| Distillation | `core/distiller.py` | fact_card → distilled_card for rendering |
| Auth system | `core/auth/auth_store.py`, `core/auth/license.py` | Machine ID + license key |
| Scenario routing | `core/scenario_router.py`, `core/scenario/scenario_registry.py` | Route cases to defense scenarios |

## CODE MAP

Core shared contracts all stages depend on:

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `PipelineContext` | dataclass | `core/fact_card.py` | The ONE shared state object passed through all pipeline stages |
| `FactCard` | dataclass | `core/fact_card.py` | Extracted structured facts |
| `StrategyCard` | dataclass | `core/fact_card.py` | DeepSeek strategy output |
| `DistilledCard` | dataclass | `core/fact_card.py` | Distilled output for rendering |
| `WorkflowStage` | ABC | `core/contracts/workflow_stage.py` | Abstract interface all stages implement |
| `StageResult` | dataclass | `core/contracts/workflow_stage.py` | Per-stage execution result |
| `Renderer` | ABC | `core/contracts/renderer.py` | Abstract renderer interface |
| `QualityGate` | ABC | `core/contracts/quality_gate.py` | Abstract gate interface |
| `DualAIOrchestrator` | class | `core/workflow/dual_ai_orchestrator.py` | Orchestrates 9-stage dual AI pipeline |
| `DUAL_AI_STAGES` | list | `core/workflow/stages.py` | Stage definitions (step1–step9) |
| `EventBus` | class | `core/workflow/events.py` | Pub/sub event bus for pipeline events |
| `extract_facts()` | function | `core/extract.py` | Main extraction entry point (API-A or regex fallback) |
| `distill()` | function | `core/distiller.py` | fact_card + strategy_card → distilled_card |

## CONVENTIONS (THIS PROJECT)

- **PipelineContext is the ONLY shared state** — never pass loose dicts between stages
- **TDD tests**: `tests/test_tdd_*.py` — tests live alongside implementation, named `test_tdd_<module>.py`
- **Contracts first**: new features should define abstract interfaces in `core/contracts/` before implementation
- **No bare AI calls outside ai/**: all LLM calls go through `core/ai/unified_client.py` or specific clients
- **Chinese-first**: docstrings, comments, and user-facing strings are in Simplified Chinese
- **Dual AI stages**: stage N uses DeepSeek → stage N+1 uses MiMo → alternate
- **Regex fallback**: `core/extract.py` always falls back to regex when API is unavailable
- **Quality gates run at step boundaries**: pipeline halts on blocking issues

## ANTI-PATTERNS (THIS PROJECT)

- **NEVER** skip quality gates — blocking issues must be resolved before render
- **NEVER** call DeepSeek/MiMo directly in stages — go through `deepseek_client` / `mimo_client` instances
- **NEVER** render from fact_card directly — always go through `distiller.py` first
- **NEVER** hardcode template paths — use `templates/` directory and `TemplateNotFoundError` handling
- **NEVER** use non-JSON serialization for PipelineContext — must support inter-process persistence

## COMMANDS

```bash
# GUI
python -m app.main_window

# CLI
python -m core.runner doctor
python -m core.runner analyze --input DIR --identity ID --goal GOAL --out DIR
python -m core.runner inspect --case DIR
python -m core.runner package --case DIR
python -m core.runner selfcheck --case DIR

# Tests
pytest tests/ -v
pytest tests/test_tdd_pipeline.py -v
```

## NOTES

- V18 RC release candidate — `build/` and `dist/` contain packaged executables
- `.pytest_cache/` and `__pycache__/` are gitignored — don't include in outputs
- `test_run_judgment/` is a separate end-to-end judgment workflow, not the main pipeline
- `screenshots/` — UI QA screenshots for visual regression
- `outputs/` — runtime output directory for generated documents

## REIN TEAM

Project-scoped agents under `.harness/reins/`. Each rein owns one domain. Reins are loaded automatically when this project is opened; they are NOT global agents.

| Rein | Domain | Routes | Skills |
|------|--------|--------|--------|
| `gui-rein` | `app/` | `gui`, `ui`, `pyside6`, `desktop` | — |
| `pipeline-rein` | `core/workflow/`, `core/ai/`, `core/extract.py`, `core/distiller.py` | `pipeline`, `workflow`, `ai`, `deepseek`, `mimo`, `extract`, `distill` | — |
| `qa-rein` | `core/quality/`, `tests/` | `quality`, `gate`, `test`, `tdd`, `pytest`, `qa` | — |
| `render-rein` | `core/render/`, `templates/`, `core/intake.py` | `render`, `docx`, `pdf`, `template`, `jinja2`, `xlsx` | `docx`, `pdf` |

Full definitions in `.harness/team.yaml`. To invoke a rein: `/<name> <task>` in chat, or `mavis session start --agent <name>`.
