"""Tests for pipeline steps."""
import pytest
import sys
sys.path.insert(0, "D:\\codex\\V18")

from core.fact_card import PipelineContext


def test_pipeline_context_creation():
    ctx = PipelineContext(input_dir="test", identity="被诉方")
    assert ctx.input_dir == "test"
    assert ctx.identity == "被诉方"


def test_scenario_router_validation():
    from core.scenario_router import validate_identity, validate_goal
    assert validate_identity("被诉方（被告）") == True
    assert validate_identity("被诉方") == True
    assert validate_identity("invalid") == False
    assert validate_goal("应诉答辩") == True
    assert validate_goal("invalid") == False
