# GUI Rein — 明证台 PySide6 Interface

**Domain:** `app/` — PySide6 FluentWindow GUI

## OVERVIEW

明证台 desktop GUI built with PySide6 + qfluentwidgets. MainWindow hosts 6 pages (Home, CaseList, CaseDetail, Settings, Audit, Activation). Workers run the pipeline off the main thread.

## WHERE TO LOOK

| Component | File | Notes |
|----------|------|-------|
| Main window | `app/main_window.py` | FluentWindow with NavigationInterface |
| Home page | `app/pages/home_page.py` | Upload + identity/goal selection |
| Case list | `app/pages/case_list_page.py` | File browser with case cards |
| Case detail | `app/pages/case_detail_page.py` | Pipeline progress + result display |
| Settings | `app/pages/settings_page.py` | AI config, path settings |
| Activation | `app/pages/activation_page.py` | License key activation |
| Worker | `app/worker.py` | AnalysisWorker runs pipeline, emits progress |
| Auth | `core/auth/auth_store.py` | Session auth state |
| AI config | `core/ai_config.py` | Per-session AI configuration |

## CONVENTIONS

- **Workers**: pipeline runs in `AnalysisWorker` (QThread), never block main thread
- **Navigation**: qfluentwidgets NavigationInterface with FluentIcon
- **Theme**: qfluentwidgets Theme.DARK / Theme.LIGHT
- **Status**: use `InfoBar` from qfluentwidgets for user-facing messages
- **Pipeline stages**: `app/worker.py` defines `PIPELINE_STAGES` list used for progress display

## ANTI-PATTERNS

- **NEVER** call `core.runner.main()` or `DualAIOrchestrator` directly from a page class — always through `AnalysisWorker`
- **NEVER** show raw exception messages to users — catch and display via InfoBar
