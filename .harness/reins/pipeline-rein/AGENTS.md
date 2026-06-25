# Pipeline Rein — Dual AI Workflow Engine

**Domain:** `core/workflow/`, `core/ai/`, `core/extract.py`, `core/distiller.py`

## OVERVIEW

The dual-AI pipeline runs 9 stages, alternating DeepSeek (extract/strategy) and MiMo (critique/review). `PipelineContext` (defined in `core/fact_card.py`) is the single source of truth passed through all stages.

## WHERE TO LOOK

| Component | File | Notes |
|----------|------|-------|
| Orchestrator | `core/workflow/dual_ai_orchestrator.py` | `DualAIOrchestrator` — 9-stage dual AI |
| Stage definitions | `core/workflow/stages.py` | `DUAL_AI_STAGES` list |
| Event bus | `core/workflow/events.py` | `EventBus` — pub/sub for pipeline events |
| AI manifest | `core/ai/ai_manifest.py` | `DualAIManifest` — stage-to-model mapping |
| DeepSeek client | `core/ai/deepseek_client.py` | API-B LLM calls |
| MiMo client | `core/ai/mimo_client.py` | API-C LLM calls |
| Multimodal router | `core/ai/multimodal_router.py` | Routes to PDF/image models |
| Provider registry | `core/ai/provider_registry.py` | Registry for AIProvider implementations |
| Extractor | `core/extract.py` | `extract_facts()` — API-A + regex fallback |
| Distiller | `core/distiller.py` | `distill()` — fact_card + strategy_card → distilled_card |
| Scenario router | `core/scenario_router.py` | Route cases to defense scenarios |
| Contracts | `core/contracts/` | WorkflowStage, AIProvider, Scenario interfaces |

## CONVENTIONS

- **PipelineContext is sacred**: all stages read/write to this single object
- **Alternating AI**: odd stages → DeepSeek, even stages → MiMo
- **Event-driven**: stages publish to `EventBus`, GUI workers subscribe
- **API-A fallback**: `core/extract.py` always has a regex path when API-A is unavailable
- **Scenario-based routing**: cases are routed by `core/scenario_router.py` before pipeline starts

## ANTI-PATTERNS

- **NEVER** create a new dataclass for inter-stage communication — add to PipelineContext in `core/fact_card.py`
- **NEVER** call LLM APIs directly in stages — use `deepseek_client` or `mimo_client` instances
- **NEVER** skip the distiller — rendering must use distilled_card, never raw fact_card
