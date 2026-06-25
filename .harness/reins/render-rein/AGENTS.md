# Render Rein — Document Output Generation

**Domain:** `core/render/`, `core/fact_card.py` (DistilledCard), `templates/`

## OVERVIEW

Document rendering takes `DistilledCard` (never raw `FactCard`) and produces DOCX, PDF, XLSX, and ZIP outputs using Jinja2 templates. All renderers implement the `Renderer` ABC from `core/contracts/renderer.py`.

## WHERE TO LOOK

| Renderer | File | Notes |
|----------|------|-------|
| DOCX renderer | `core/render/docx_renderer.py` | docxtpl + Jinja2 template filling |
| PDF converter | `core/render/pdf_converter.py` | LibreOffice conversion pipeline |
| XLSX renderer | `core/render/xlsx_renderer.py` | openpyxl-based spreadsheet output |
| ZIP builder | `core/render/zip_builder.py` | Packages all artifacts into deliverable ZIP |
| Renderer interface | `core/contracts/renderer.py` | `Renderer` ABC — `render(ctx, out_path)` |
| Distillation | `core/distiller.py` | `distill()` must run BEFORE rendering |
| Data contracts | `core/fact_card.py` | `DistilledCard` dataclass — the ONLY render input |
| Templates | `templates/` | DOCX template files (Jinja2-style) |
| Intake | `core/intake.py` | `intake()` — prepares raw input for pipeline |

## CONVENTIONS

- **DistilledCard only**: `distill()` in `core/distiller.py` MUST be called before any renderer
- **Renderer ABC**: all renderers implement `core.contracts.renderer.Renderer`
- **Template safety**: catch `TemplateNotFoundError` and `jinja2.TemplateNotFound`
- **Chinese fonts**: PDF must handle SimHei/fallback for CJK characters
- **ZIP ordering**: package the ZIP in deterministic order for reproducibility

## ANTI-PATTERNS

- **NEVER** render from FactCard or StrategyCard directly — always distill first
- **NEVER** hardcode template file paths — use `templates/` directory
- **NEVER** include raw customer documents in the output ZIP without filtering
