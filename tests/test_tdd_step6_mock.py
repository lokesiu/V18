"""TDD tests for step6_llm_generate.py — mock API calls for full coverage."""
import pytest
import sys, os
from unittest.mock import patch, AsyncMock, MagicMock
sys.path.insert(0, ".")

from core.fact_card import (
    PipelineContext, FactCard, Party, DistilledCard, StrategyCard,
    ActionAdvice, SourceRef,
)
from core.ai_mode import AIModeTracker


# ══════════════════════════════════════════════════════════════════════
# _distill_llm_output
# ══════════════════════════════════════════════════════════════════════
class TestDistillLlmOutput:
    def test_empty_content(self):
        from core.pipeline.step6_llm_generate import _distill_llm_output
        assert _distill_llm_output("") == ""
        assert _distill_llm_output(None) is None

    def test_markdown_bold_removed(self):
        from core.pipeline.step6_llm_generate import _distill_llm_output
        result = _distill_llm_output("**粗体**文本")
        assert "**" not in result
        assert "粗体" in result

    def test_markdown_heading_removed(self):
        from core.pipeline.step6_llm_generate import _distill_llm_output
        result = _distill_llm_output("### 标题")
        assert "###" not in result
        assert "标题" in result

    def test_llm_opening_removed(self):
        from core.pipeline.step6_llm_generate import _distill_llm_output
        result = _distill_llm_output("好的，以下是答辩状。\n\n正文")
        assert "好的" not in result
        assert "正文" in result

    def test_vague_law_citation_removed(self):
        from core.pipeline.step6_llm_generate import _distill_llm_output
        result = _distill_llm_output("依据《民法典》相关规定处理")
        assert "相关规定" not in result

    def test_multiple_newlines_collapsed(self):
        from core.pipeline.step6_llm_generate import _distill_llm_output
        result = _distill_llm_output("a\n\n\n\n\nb")
        assert "\n\n\n" not in result


# ══════════════════════════════════════════════════════════════════════
# _build_context_object
# ══════════════════════════════════════════════════════════════════════
class TestBuildContextObject:
    def test_basic_context(self):
        from core.pipeline.step6_llm_generate import _build_context_object
        ctx = PipelineContext(identity="被诉方", goal="应诉答辩")
        ctx.fact_card = FactCard(
            case_id="C1",
            court="法院",
            parties=[Party(name="张三", role="被告"), Party(name="李四", role="原告")],
            key_facts=["事实1"],
            disputed_facts=["争议1"],
            conflicts=["冲突1"],
            missing_materials=["材料1"],
        )
        ctx.strategy_card = StrategyCard(
            sabcd_rating="B",
            situation_assessment="评估",
            action_advice=[ActionAdvice(action="做X", priority="S")],
            evidence_gap=["缺口1"],
            risk_warnings=["风险1"],
        )
        result = _build_context_object(ctx)
        assert "被诉方" in result
        assert "C1" in result
        assert "法院" in result
        assert "张三" in result
        assert "事实1" in result

    def test_context_with_source_refs(self):
        from core.pipeline.step6_llm_generate import _build_context_object
        ctx = PipelineContext(identity="被诉方", goal="应诉答辩")
        ctx.fact_card = FactCard(
            parties=[Party(name="张三", role="被告")],
            source_refs=[SourceRef(excerpt="申请人：张三，男，1990年1月1日出生")],
        )
        result = _build_context_object(ctx)
        assert "张三" in result

    def test_context_plaintiff_identity(self):
        from core.pipeline.step6_llm_generate import _build_context_object
        ctx = PipelineContext(identity="起诉方", goal="起诉立案")
        ctx.fact_card = FactCard(
            parties=[Party(name="原告名", role="原告")],
        )
        result = _build_context_object(ctx)
        assert "起诉方" in result
        assert "原告名" in result

    def test_context_no_fact_card(self):
        from core.pipeline.step6_llm_generate import _build_context_object
        ctx = PipelineContext(identity="被诉方", goal="应诉答辩")
        result = _build_context_object(ctx)
        assert "被诉方" in result

    def test_context_with_extra_result(self):
        from core.pipeline.step6_llm_generate import _build_context_object
        from core.pipeline.schemas import FactExtractionResult, TimelineEvent, FundFlow
        ctx = PipelineContext(identity="被诉方", goal="应诉答辩")
        ctx.fact_card = FactCard()
        ctx._fact_extraction_result = FactExtractionResult(
            timeline=[TimelineEvent(date="2024-01-01", event="签约")],
            fund_flows=[FundFlow(date="2024-01", amount="10万", direction="转入", counterparty="张三", evidence="流水")],
            claims=["偿还借款"],
        )
        result = _build_context_object(ctx)
        assert "签约" in result
        assert "10万" in result
        assert "偿还借款" in result

    def test_context_with_strategy_reasoning(self):
        from core.pipeline.step6_llm_generate import _build_context_object
        from core.pipeline.schemas import StrategyReasoningResult, LegalAnalysis, ReliefPath
        ctx = PipelineContext(identity="被诉方", goal="应诉答辩")
        ctx.fact_card = FactCard()
        ctx.strategy_card = StrategyCard()
        ctx._strategy_reasoning_result = StrategyReasoningResult(
            core_disputes=[LegalAnalysis(issue="争议焦点", applicable_law="法条", analysis="分析", conclusion="结论")],
            relief_paths=[ReliefPath(level="一审", strategy="策略")],
            entity_defense=["抗辩1"],
        )
        result = _build_context_object(ctx)
        assert "争议焦点" in result
        assert "一审" in result
        assert "抗辩1" in result


# ══════════════════════════════════════════════════════════════════════
# _get_default_docs
# ══════════════════════════════════════════════════════════════════════
class TestGetDefaultDocs:
    def test_defendant(self):
        from core.pipeline.step6_llm_generate import _get_default_docs
        docs = _get_default_docs("被诉方（被告）")
        assert "答辩状" in docs

    def test_plaintiff(self):
        from core.pipeline.step6_llm_generate import _get_default_docs
        docs = _get_default_docs("起诉方")
        assert "起诉状" in docs

    def test_unknown(self):
        from core.pipeline.step6_llm_generate import _get_default_docs
        docs = _get_default_docs("未知")
        assert len(docs) >= 2


# ══════════════════════════════════════════════════════════════════════
# _generic_prompt
# ══════════════════════════════════════════════════════════════════════
class TestGenericPrompt:
    def test_contains_doc_type(self):
        from core.pipeline.step6_llm_generate import _generic_prompt
        prompt = _generic_prompt("答辩状")
        assert "答辩状" in prompt


# ══════════════════════════════════════════════════════════════════════
# step6_llm_generate — mocked API
# ══════════════════════════════════════════════════════════════════════
class TestStep6LlmGenerateMocked:
    def _make_ctx(self):
        ctx = PipelineContext(
            identity="被诉方（被告）",
            goal="应诉答辩",
        )
        ctx.fact_card = FactCard(
            case_id="C1",
            parties=[Party(name="张三", role="被告"), Party(name="李四", role="原告")],
            key_facts=["事实1"],
        )
        ctx.strategy_card = StrategyCard(sabcd_rating="B", situation_assessment="评估")
        ctx.distilled_card = DistilledCard(
            fact_card=ctx.fact_card,
            strategy_card=ctx.strategy_card,
        )
        return ctx

    @patch("core.pipeline.step6_llm_generate.is_api_configured", return_value=True)
    @patch("core.pipeline.step6_llm_generate.asyncio.run")
    def test_api_success(self, mock_run, mock_configured):
        """API configured and returns docs."""
        from core.pipeline.step6_llm_generate import step6_llm_generate
        mock_run.return_value = {
            "答辩状": "民事答辩状\n正文内容",
            "案件处境评估报告": "评估报告\n内容",
        }
        ctx = self._make_ctx()
        ctx = step6_llm_generate(ctx)
        docs = getattr(ctx, "_llm_generated_docs", {})
        assert len(docs) >= 1
        assert "答辩状" in docs

    @patch("core.pipeline.step6_llm_generate.is_api_configured", return_value=True)
    @patch("core.pipeline.step6_llm_generate.asyncio.run")
    def test_api_partial_failure(self, mock_run, mock_configured):
        """Some docs fail, some succeed."""
        from core.pipeline.step6_llm_generate import step6_llm_generate
        mock_run.return_value = {
            "答辩状": "内容",
            # 其他文档失败，不出现在结果中
        }
        ctx = self._make_ctx()
        ctx = step6_llm_generate(ctx)
        docs = getattr(ctx, "_llm_generated_docs", {})
        assert "答辩状" in docs

    @patch("core.pipeline.step6_llm_generate.is_api_configured", return_value=False)
    def test_api_not_configured(self, mock_configured):
        """API not configured → skip."""
        from core.pipeline.step6_llm_generate import step6_llm_generate
        ctx = self._make_ctx()
        ctx = step6_llm_generate(ctx)
        docs = getattr(ctx, "_llm_generated_docs", {})
        assert docs == {}

    def test_no_distilled_card(self):
        """No distilled_card → error."""
        from core.pipeline.step6_llm_generate import step6_llm_generate
        ctx = PipelineContext()
        ctx.distilled_card = None
        ctx = step6_llm_generate(ctx)
        assert len(ctx.errors) > 0

    @patch("core.pipeline.step6_llm_generate.is_api_configured", return_value=True)
    @patch("core.pipeline.step6_llm_generate.asyncio.run")
    def test_api_exception(self, mock_run, mock_configured):
        """API raises exception → AIProviderError."""
        from core.pipeline.step6_llm_generate import step6_llm_generate
        from core.pipeline import AIProviderError
        mock_run.side_effect = RuntimeError("API down")
        ctx = self._make_ctx()
        with pytest.raises(AIProviderError):
            step6_llm_generate(ctx)

    @patch("core.pipeline.step6_llm_generate.is_api_configured", return_value=True)
    @patch("core.pipeline.step6_llm_generate.asyncio.run")
    def test_tracker_created_if_missing(self, mock_run, mock_configured):
        """AIModeTracker created if not on ctx."""
        from core.pipeline.step6_llm_generate import step6_llm_generate
        mock_run.return_value = {"答辩状": "内容"}
        ctx = self._make_ctx()
        assert not hasattr(ctx, '_ai_mode_tracker') or ctx._ai_mode_tracker is None
        ctx = step6_llm_generate(ctx)
        assert hasattr(ctx, '_ai_mode_tracker')

    @patch("core.pipeline.step6_llm_generate.is_api_configured", return_value=True)
    @patch("core.pipeline.step6_llm_generate.asyncio.run")
    def test_existing_tracker_reused(self, mock_run, mock_configured):
        """Existing AIModeTracker on ctx is reused."""
        from core.pipeline.step6_llm_generate import step6_llm_generate
        mock_run.return_value = {"答辩状": "内容"}
        ctx = self._make_ctx()
        tracker = AIModeTracker()
        ctx._ai_mode_tracker = tracker
        ctx = step6_llm_generate(ctx)
        assert ctx._ai_mode_tracker is tracker


# ══════════════════════════════════════════════════════════════════════
# _generate_all_docs — async mock
# ══════════════════════════════════════════════════════════════════════
class TestGenerateAllDocs:
    @pytest.mark.asyncio
    async def test_success(self):
        from core.pipeline.step6_llm_generate import _generate_all_docs
        from core.ai_mode import AIModeTracker
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=True, content="文书内容", latency_ms=100,
        )

        mock_client = MagicMock()
        mock_client.async_call = AsyncMock(return_value=mock_response)

        tracker = AIModeTracker()
        ctx = PipelineContext()

        with patch("core.ai_client.AIClient", return_value=mock_client):
            results = await _generate_all_docs(
                ["答辩状", "案件处境评估报告"],
                "上下文",
                tracker,
                ctx,
            )
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_failure_logged(self):
        from core.pipeline.step6_llm_generate import _generate_all_docs
        from core.ai_mode import AIModeTracker
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=False, content="", latency_ms=0, error="timeout",
        )

        mock_client = MagicMock()
        mock_client.async_call = AsyncMock(return_value=mock_response)

        tracker = AIModeTracker()
        ctx = PipelineContext()

        with patch("core.ai_client.AIClient", return_value=mock_client):
            results = await _generate_all_docs(
                ["答辩状"],
                "上下文",
                tracker,
                ctx,
            )
        # Failed doc should not be in results
        assert len(results) == 0


# ══════════════════════════════════════════════════════════════════════
# DOC_PROMPTS constant
# ══════════════════════════════════════════════════════════════════════
class TestDocPrompts:
    def test_all_expected_types_have_prompts(self):
        from core.pipeline.step6_llm_generate import DOC_PROMPTS
        expected = ["案件处境评估报告", "行动建议书", "证据闭环补强清单", "答辩状", "起诉状", "投诉状", "行政复议申请书"]
        for doc_type in expected:
            assert doc_type in DOC_PROMPTS, f"Missing prompt for {doc_type}"

    def test_prompts_are_strings(self):
        from core.pipeline.step6_llm_generate import DOC_PROMPTS
        for k, v in DOC_PROMPTS.items():
            assert isinstance(v, str)
            assert len(v) > 50


class TestTemplateOnlyDocs:
    def test_contains_evidence_catalog(self):
        from core.pipeline.step6_llm_generate import TEMPLATE_ONLY_DOCS
        assert "证据目录" in TEMPLATE_ONLY_DOCS
