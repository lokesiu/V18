"""
core/scenario/__init__.py - Legal Scenario Registry

Manages all legal scenarios and their configurations.
"""
from core.scenario.defense_scenario import DefenseScenario
from core.scenario.scenario_registry import get_scenario_registry

__all__ = ["DefenseScenario", "get_scenario_registry"]
