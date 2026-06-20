"""TDD tests for all identity/goal combinations — coverage gaps."""
import pytest
import sys, os
sys.path.insert(0, ".")

from core.fact_card import PipelineContext, FactCard, Party, StrategyCard, DistilledCard
from core.scenario_router import (
    validate_identity, validate_goal, get_expected_doc_types,
    _normalize_identity, route_scenario, IDENTITY_GOAL_MAP,
)


ALL_IDENTITIES = [
    ("消费者", "维权投诉"),
    ("投诉方", "投诉举报"),
    ("起诉方", "起诉立案"),
    ("起诉方（原告）", "提起起诉"),
    ("被诉方", "应诉答辩"),
    ("被诉方（被告）", "应诉答辩"),
    ("复议申请人", "申请行政复议"),
    ("行政复议申请人", "行政复议"),
    ("整理证据", "证据整理"),
]


class TestAllIdentityRouting:
    """Test routing for every identity/goal combination."""

    @pytest.mark.parametrize("identity,goal", ALL_IDENTITIES)
    def test_identity_valid(self, identity, goal):
        assert validate_identity(identity) is True

    @pytest.mark.parametrize("identity,goal", ALL_IDENTITIES)
    def test_goal_valid(self, identity, goal):
        assert validate_goal(goal) is True

    @pytest.mark.parametrize("identity,goal", ALL_IDENTITIES)
    def test_route_no_errors(self, identity, goal):
        ctx = PipelineContext(identity=identity, goal=goal)
        ctx = route_scenario(ctx)
        assert len(ctx.errors) == 0, f"Route error for {identity}/{goal}: {ctx.errors}"

    @pytest.mark.parametrize("identity,goal", ALL_IDENTITIES)
    def test_get_doc_types(self, identity, goal):
        docs = get_expected_doc_types(identity)
        assert len(docs) > 0, f"No doc types for {identity}"

    @pytest.mark.parametrize("identity,goal", ALL_IDENTITIES)
    def test_doc_types_have_common(self, identity, goal):
        docs = get_expected_doc_types(identity)
        assert "案件处境评估报告" in docs
        assert "行动建议书" in docs
        assert "证据目录" in docs


class TestIdentitySpecificDocs:
    """Test that each identity generates its specific document type."""

    def test_defendant_has_defense(self):
        docs = get_expected_doc_types("被诉方（被告）")
        assert "答辩状" in docs

    def test_plaintiff_has_complaint(self):
        docs = get_expected_doc_types("起诉方")
        assert "起诉状" in docs

    def test_complainant_has_complaint(self):
        docs = get_expected_doc_types("投诉方")
        assert "投诉状" in docs

    def test_review_applicant_has_application(self):
        docs = get_expected_doc_types("行政复议申请人")
        assert "行政复议申请书" in docs

    def test_evidence整理_no_special_doc(self):
        docs = get_expected_doc_types("整理证据")
        assert "答辩状" not in docs
        assert "起诉状" not in docs


class TestStep7IdentityDocs:
    """Test step7 render identity-specific extra documents."""

    def test_all_identities_get_extra_doc(self):
        from core.pipeline.step7_render import _get_identity_extra_doc
        expected = {
            "投诉方": "投诉状",
            "起诉方": "起诉状",
            "被诉方（被告）": "答辩状",
            "行政复议申请人": "行政复议申请书",
        }
        for identity, doc_type in expected.items():
            result = _get_identity_extra_doc(identity)
            assert result is not None, f"No extra doc for {identity}"
            assert result[1] == doc_type, f"Wrong doc type for {identity}: {result[1]}"

    def test_整理证据_no_extra_doc(self):
        from core.pipeline.step7_render import _get_identity_extra_doc
        result = _get_identity_extra_doc("整理证据")
        assert result is None

    def test_brief_defendant_gets_extra_doc(self):
        from core.pipeline.step7_render import _get_identity_extra_doc
        result = _get_identity_extra_doc("被诉方")
        assert result is not None
        assert result[1] == "答辩状"


class TestStep6DefaultDocs:
    """Test step6 default doc generation for all identities."""

    def test_all_identities_get_default_docs(self):
        from core.pipeline.step6_llm_generate import _get_default_docs
        for identity, _ in ALL_IDENTITIES:
            docs = _get_default_docs(identity)
            assert len(docs) > 0, f"No default docs for {identity}"


class TestFullPipelinePerIdentity:
    """Test full pipeline execution for each identity (no API, local fallback)."""

    def _run_mini_pipeline(self, identity: str, goal: str, tmp_path):
        """Run a minimal pipeline for testing."""
        # Create test input
        (tmp_path / "test.txt").write_text(
            "原告张三诉被告李四借款合同纠纷一案。借款金额10万元。" * 30,
            encoding="utf-8",
        )
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        ctx = PipelineContext(
            input_dir=str(tmp_path),
            output_dir=str(out_dir),
            identity=identity,
            goal=goal,
        )

        # Step 1: intake
        from core.intake import run_intake
        ctx = run_intake(ctx)
        assert len(ctx.raw_texts) > 0

        # Step 2: extract
        from core.extract import extract_facts
        ctx.fact_card = FactCard()
        ctx.fact_card.identity = identity
        ctx = extract_facts(ctx)
        assert ctx.fact_card is not None

        # Step 3: skip (no API)

        # Step 4: strategy (local fallback)
        from core.pipeline.step4_strategy_reasoning import _create_fallback
        ctx.strategy_card = _create_fallback(ctx)
        assert ctx.strategy_card is not None

        # Step 5: distill
        from core.distiller import distill
        ctx = distill(ctx)
        assert ctx.distilled_card is not None

        return ctx

    def test_defendant_pipeline(self, tmp_path):
        ctx = self._run_mini_pipeline("被诉方（被告）", "应诉答辩", tmp_path)
        assert ctx.distilled_card.fact_card.identity == "被诉方（被告）"

    def test_plaintiff_pipeline(self, tmp_path):
        ctx = self._run_mini_pipeline("起诉方", "起诉立案", tmp_path)
        assert ctx.distilled_card.fact_card.identity == "起诉方"

    def test_complainant_pipeline(self, tmp_path):
        ctx = self._run_mini_pipeline("投诉方", "投诉举报", tmp_path)
        assert ctx.distilled_card.fact_card.identity == "投诉方"

    def test_review_pipeline(self, tmp_path):
        ctx = self._run_mini_pipeline("行政复议申请人", "行政复议", tmp_path)
        assert ctx.distilled_card.fact_card.identity == "行政复议申请人"

    def test_evidence_pipeline(self, tmp_path):
        ctx = self._run_mini_pipeline("整理证据", "证据整理", tmp_path)
        assert ctx.distilled_card.fact_card.identity == "整理证据"


class TestPostprocessPerIdentity:
    """Test postprocess handles all identities without crashing."""

    @pytest.mark.parametrize("identity,goal", ALL_IDENTITIES)
    def test_postprocess_no_crash(self, identity, goal):
        from core.pipeline.step7_postprocess import postprocess_documents
        ctx = PipelineContext(identity=identity, goal=goal)
        ctx.fact_card = FactCard(identity=identity, parties=[Party(name="A", role="原告")])
        ctx._llm_generated_docs = {
            "答辩状": "内容",
            "案件处境评估报告": "内容",
            "行动建议书": "内容",
        }
        result = postprocess_documents(ctx)
        assert isinstance(result, dict)
