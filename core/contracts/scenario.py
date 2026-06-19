"""
core/contracts/scenario.py - Scenario Interface

Defines the contract for legal scenarios.
Each scenario (defense, complaint, lawsuit, etc.) must implement Scenario.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

from core.fact_card import PipelineContext


class ScenarioStatus(Enum):
    """Scenario availability status."""
    ACTIVE = "active"              # Fully supported
    BETA = "beta"                  # Available for testing
    COMING_SOON = "coming_soon"    # UI visible, not functional
    DISABLED = "disabled"          # Hidden


@dataclass
class ScenarioConfig:
    """Configuration for a legal scenario."""
    identity: str                   # e.g., "被诉方"
    goal: str                       # e.g., "应诉答辩"
    display_name: str               # e.g., "被诉方应诉答辩"
    description: str                # User-facing description
    status: ScenarioStatus = ScenarioStatus.ACTIVE
    template_names: List[str] = field(default_factory=list)
    required_doc_types: List[str] = field(default_factory=list)
    quality_rules: List[str] = field(default_factory=list)
    min_action_advice: int = 6
    min_evidence_gap: int = 5
    coming_soon_message: str = "该场景正在打磨中，当前内测版优先支持被诉方应诉答辩。"

    def is_available(self) -> bool:
        """Whether this scenario can be used."""
        return self.status in (ScenarioStatus.ACTIVE, ScenarioStatus.BETA)

    def to_dict(self) -> dict:
        return {
            "identity": self.identity,
            "goal": self.goal,
            "display_name": self.display_name,
            "description": self.description,
            "status": self.status.value,
            "template_names": self.template_names,
            "required_doc_types": self.required_doc_types,
            "is_available": self.is_available(),
        }


class Scenario(ABC):
    """Abstract base class for legal scenarios."""

    @property
    @abstractmethod
    def config(self) -> ScenarioConfig:
        """Scenario configuration."""
        ...

    @abstractmethod
    def validate_input(self, ctx: PipelineContext) -> List[str]:
        """Validate input for this scenario.

        Returns:
            List of error messages (empty if valid).
        """
        ...

    @abstractmethod
    def get_quality_rules(self) -> Dict[str, Any]:
        """Get scenario-specific quality rules.

        Returns:
            Dictionary of quality rules and thresholds.
        """
        ...

    def get_coming_soon_message(self) -> str:
        """Get message for coming-soon scenarios."""
        return self.config.coming_soon_message
