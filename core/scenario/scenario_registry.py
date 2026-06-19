"""
core/scenario/scenario_registry.py - Scenario Registry

Manages all available scenarios and provides lookup.
"""
from __future__ import annotations

from typing import Dict, Optional, List

from core.contracts.scenario import Scenario, ScenarioConfig, ScenarioStatus
from core.scenario.defense_scenario import DefenseScenario


class ScenarioRegistry:
    """Registry of all legal scenarios."""

    def __init__(self):
        self._scenarios: Dict[str, Scenario] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register default scenarios."""
        # ACTIVE: Defense (被诉方+应诉答辩)
        self.register(DefenseScenario())

        # COMING SOON: Other scenarios
        self._register_coming_soon(
            identity="投诉方",
            goal="投诉举报",
            display_name="投诉方投诉举报",
            description="针对投诉举报事项，生成投诉书、证据清单等材料",
        )
        self._register_coming_soon(
            identity="起诉方",
            goal="起诉立案",
            display_name="起诉方起诉立案",
            description="针对起诉立案，生成起诉状、证据目录等材料",
        )
        self._register_coming_soon(
            identity="行政复议申请人",
            goal="行政复议",
            display_name="行政复议申请",
            description="针对行政复议，生成复议申请书等材料",
        )
        self._register_coming_soon(
            identity="整理证据",
            goal="证据整理",
            display_name="证据整理",
            description="整理和分类案件证据材料",
        )

    def _register_coming_soon(self, identity: str, goal: str,
                               display_name: str, description: str):
        """Register a coming-soon scenario."""
        from core.contracts.scenario import Scenario as ScenarioABC

        class ComingSoonScenario(ScenarioABC):
            @property
            def config(self) -> ScenarioConfig:
                return ScenarioConfig(
                    identity=identity,
                    goal=goal,
                    display_name=display_name,
                    description=description,
                    status=ScenarioStatus.COMING_SOON,
                )

            def validate_input(self, ctx):
                return [f"场景'{display_name}'暂未开放"]

            def get_quality_rules(self):
                return {}

        self.register(ComingSoonScenario())

    def register(self, scenario: Scenario):
        """Register a scenario."""
        key = f"{scenario.config.identity}_{scenario.config.goal}"
        self._scenarios[key] = scenario

    def get(self, identity: str, goal: str) -> Optional[Scenario]:
        """Get scenario by identity and goal."""
        key = f"{identity}_{goal}"
        return self._scenarios.get(key)

    def get_all(self) -> List[Scenario]:
        """Get all registered scenarios."""
        return list(self._scenarios.values())

    def get_active(self) -> List[Scenario]:
        """Get only active scenarios."""
        return [
            s for s in self._scenarios.values()
            if s.config.status == ScenarioStatus.ACTIVE
        ]

    def get_coming_soon(self) -> List[Scenario]:
        """Get coming-soon scenarios."""
        return [
            s for s in self._scenarios.values()
            if s.config.status == ScenarioStatus.COMING_SOON
        ]

    def is_available(self, identity: str, goal: str) -> bool:
        """Check if a scenario is available."""
        scenario = self.get(identity, goal)
        return scenario is not None and scenario.config.is_available()


# Singleton
_registry: Optional[ScenarioRegistry] = None


def get_scenario_registry() -> ScenarioRegistry:
    """Get singleton scenario registry."""
    global _registry
    if _registry is None:
        _registry = ScenarioRegistry()
    return _registry
