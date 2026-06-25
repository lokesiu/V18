# QA Rein — Quality Gates & Artifact Auditing

**Domain:** `core/quality/`, `tests/`, artifact validation

## OVERVIEW

明证台 has a layered quality system: step-level `pipeline_gates` catch bad intermediates, final `defense_quality_gate` validates the complete output, and specialized checkers (visible_docx, package_leak, artifact_auditor) verify deliverable correctness.

## WHERE TO LOOK

| Component | File | Notes |
|----------|------|-------|
| Step-level gates | `core/quality/pipeline_gates.py` | Runs after step2 (extract) and step3 (enhance) |
| Final defense gate | `core/quality/defense_quality_gate.py` | Validates complete defense document |
| Visible DOCX check | `core/quality/visible_docx_checker.py` | Checks rendered DOCX opens without errors |
| Package leak scan | `core/quality/package_leak_scanner.py` | Ensures no customer data in build artifacts |
| Final artifact audit | `core/quality/final_artifact_auditor.py` | Checks output completeness |
| Gate interface | `core/contracts/quality_gate.py` | `QualityGate` ABC — implement for new gates |
| TDD tests | `tests/test_tdd_*.py` | Tests alongside implementation |
| Acceptance tests | `tests/test_acceptance_*.py` | End-to-end acceptance criteria |
| Golden case | `tests/test_golden_case_passes_defense_gate.py` | Golden path regression test |

## CONVENTIONS

- **Blocking issues halt the pipeline** — must resolve before render stage
- **Warning issues are logged** but don't halt
- **Every new pipeline stage should have a corresponding gate** in `core/quality/`
- **TDD tests**: `test_tdd_<module>.py` files live alongside their implementation
- **No false passes**: quality gates must never pass when the document is invalid

## ANTI-PATTERNS

- **NEVER** suppress `GateResult.status == "blocked"` without user action
- **NEVER** skip running quality gates in CI
- **NEVER** hardcode pass/fail — gates must be deterministic and testable
