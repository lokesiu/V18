"""
core/contracts/__init__.py - PID Interface Contracts

Defines the unified interfaces for all PID modules.
These contracts ensure backward compatibility while enabling
the PID productization reorganization.
"""
from core.contracts.ai_provider import AIProvider, AIResponse, AIMode
from core.contracts.workflow_stage import WorkflowStage, StageResult, StageEvent
from core.contracts.quality_gate import QualityGate, QualityResult, QualityCheck
from core.contracts.renderer import Renderer, RenderResult
from core.contracts.scenario import Scenario, ScenarioConfig

__all__ = [
    "AIProvider", "AIResponse", "AIMode",
    "WorkflowStage", "StageResult", "StageEvent",
    "QualityGate", "QualityResult", "QualityCheck",
    "Renderer", "RenderResult",
    "Scenario", "ScenarioConfig",
]
