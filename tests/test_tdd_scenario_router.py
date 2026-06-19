"""TDD tests for core/scenario_router.py — routing and validation edge cases."""
import pytest
import sys
sys.path.insert(0, ".")

from core.scenario_router import (
    validate_identity, validate_goal, get_expected_doc_types,
    get_sabcd_factors, _normalize_identity, route_scenario,
    VALID_IDENTITIES, VALID_GOALS, IDENTITY_GOAL_MAP, IDENTITY_DOC_TYPES,
)
from core.fact_card import PipelineContext


class TestValidateIdentity:
    def test_all_valid_identities(self):
        for ident in VALID_IDENTITIES:
            assert validate_identity(ident), f"Should be valid: {ident}"

    def test_invalid(self):
        assert not validate_identity("不存在的身份")
        assert not validate_identity("")
        assert not validate_identity("被告")  # not in list

    def test_brief_defendant_valid(self):
        assert validate_identity("被诉方")

    def test_full_defendant_valid(self):
        assert validate_identity("被诉方（被告）")


class TestValidateGoal:
    def test_all_valid_goals(self):
        for goal in VALID_GOALS:
            assert validate_goal(goal), f"Should be valid: {goal}"

    def test_invalid(self):
        assert not validate_goal("不存在的目标")
        assert not validate_goal("")


class TestNormalizeIdentity:
    def test_brief_maps_to_full(self):
        assert _normalize_identity("被诉方") == "被诉方（被告）"

    def test_full_unchanged(self):
        assert _normalize_identity("被诉方（被告）") == "被诉方（被告）"

    def test_plaintiff_variants(self):
        assert _normalize_identity("起诉方（原告）") == "起诉方"

    def test_consumer_maps(self):
        assert _normalize_identity("消费者") == "投诉方"

    def test_review_applicant(self):
        assert _normalize_identity("复议申请人") == "行政复议申请人"

    def test_unknown_unchanged(self):
        assert _normalize_identity("整理证据") == "整理证据"


class TestGetExpectedDocTypes:
    def test_defendant_has_defense(self):
        docs = get_expected_doc_types("被诉方（被告）")
        assert "答辩状" in docs

    def test_brief_defendant_same_as_full(self):
        docs_brief = get_expected_doc_types("被诉方")
        docs_full = get_expected_doc_types("被诉方（被告）")
        assert docs_brief == docs_full

    def test_plaintiff_has_complaint(self):
        docs = get_expected_doc_types("起诉方")
        assert "起诉状" in docs

    def test_unknown_returns_empty(self):
        docs = get_expected_doc_types("未知身份")
        assert docs == []

    def test_all_identities_have_common_docs(self):
        for ident in ["投诉方", "起诉方", "被诉方（被告）", "行政复议申请人"]:
            docs = get_expected_doc_types(ident)
            assert "案件处境评估报告" in docs, f"{ident} missing 案件处境评估报告"
            assert "行动建议书" in docs, f"{ident} missing 行动建议书"
            assert "证据目录" in docs, f"{ident} missing 证据目录"


class TestGetSabcdFactors:
    def test_returns_criteria(self):
        factors = get_sabcd_factors("被诉方（被告）", "应诉答辩")
        assert len(factors["criteria"]) > 0
        assert len(factors["weight_distribution"]) > 0

    def test_all_identities_have_factors(self):
        for ident in VALID_IDENTITIES:
            goal = IDENTITY_GOAL_MAP.get(ident, "应诉答辩")
            factors = get_sabcd_factors(ident, goal)
            assert len(factors["criteria"]) > 0, f"No criteria for {ident}"


class TestRouteScenario:
    def test_valid_route(self):
        ctx = PipelineContext(identity="被诉方（被告）", goal="应诉答辩")
        ctx = route_scenario(ctx)
        assert len(ctx.errors) == 0

    def test_invalid_identity_adds_error(self):
        ctx = PipelineContext(identity="不存在", goal="应诉答辩")
        ctx = route_scenario(ctx)
        assert len(ctx.errors) > 0

    def test_auto_goal(self):
        ctx = PipelineContext(identity="被诉方（被告）", goal="")
        ctx = route_scenario(ctx)
        assert ctx.goal == "应诉答辩"

    def test_brief_defendant_routes(self):
        ctx = PipelineContext(identity="被诉方", goal="应诉答辩")
        ctx = route_scenario(ctx)
        assert len(ctx.errors) == 0
