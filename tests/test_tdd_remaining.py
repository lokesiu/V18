"""TDD tests for step6_template_fill, pipeline init, ai_client, checkpoint_builder."""
import pytest
import sys, os, json
from unittest.mock import patch, MagicMock
sys.path.insert(0, ".")

from core.fact_card import (
    PipelineContext, FactCard, Party, SourceRef, StrategyCard,
    ActionAdvice, DraftDocument, DistilledCard,
)


# ══════════════════════════════════════════════════════════════════════
# step6_template_fill — format helpers and fallback
# ══════════════════════════════════════════════════════════════════════
class TestFormatParties:
    def test_none_fc(self):
        from core.pipeline.step6_template_fill import _format_parties
        assert _format_parties(None) == ""

    def test_no_parties(self):
        from core.pipeline.step6_template_fill import _format_parties
        assert _format_parties(FactCard()) == ""

    def test_with_parties(self):
        from core.pipeline.step6_template_fill import _format_parties
        fc = FactCard(parties=[Party(name="张三", role="被告"), Party(name="李四", role="原告")])
        result = _format_parties(fc)
        assert "张三" in result
        assert "李四" in result


class TestFormatList:
    def test_empty(self):
        from core.pipeline.step6_template_fill import _format_list
        assert _format_list([]) == ""

    def test_none(self):
        from core.pipeline.step6_template_fill import _format_list
        assert _format_list(None) == ""

    def test_with_tags(self):
        from core.pipeline.step6_template_fill import _format_list
        result = _format_list(["【待核对】事实1", "【争议】事实2"])
        assert "待核对" not in result
        assert "争议" not in result
        assert "事实1" in result


class TestFormatSources:
    def test_none_fc(self):
        from core.pipeline.step6_template_fill import _format_sources
        assert _format_sources(None) == ""

    def test_no_refs(self):
        from core.pipeline.step6_template_fill import _format_sources
        assert _format_sources(FactCard()) == ""

    def test_with_refs(self):
        from core.pipeline.step6_template_fill import _format_sources
        fc = FactCard(source_refs=[
            SourceRef(file_name="a.pdf", page=1, excerpt="证据内容"),
            SourceRef(file_name="b.pdf", page=None, excerpt="另一证据"),
        ])
        result = _format_sources(fc)
        assert "a.pdf" in result
        assert "第1页" in result


class TestFormatActionAdvice:
    def test_none_sc(self):
        from core.pipeline.step6_template_fill import _format_action_advice
        assert _format_action_advice(None) == ""

    def test_no_advice(self):
        from core.pipeline.step6_template_fill import _format_action_advice
        assert _format_action_advice(StrategyCard()) == ""

    def test_with_advice(self):
        from core.pipeline.step6_template_fill import _format_action_advice
        sc = StrategyCard(action_advice=[
            ActionAdvice(action="做X", priority="S", reasoning="因为Y"),
        ])
        result = _format_action_advice(sc)
        assert "做X" in result
        assert "S" in result


class TestFormatDraftDocuments:
    def test_none_sc(self):
        from core.pipeline.step6_template_fill import _format_draft_documents
        assert _format_draft_documents(None) == ""

    def test_no_drafts(self):
        from core.pipeline.step6_template_fill import _format_draft_documents
        assert _format_draft_documents(StrategyCard()) == ""

    def test_with_drafts(self):
        from core.pipeline.step6_template_fill import _format_draft_documents
        sc = StrategyCard(draft_documents=[
            DraftDocument(doc_type="答辩状", title="答辩状", content="内容" * 300),
        ])
        result = _format_draft_documents(sc)
        assert "答辩状" in result
        assert "..." in result  # long content gets truncated


class TestGetTemplateFilename:
    def test_known_types(self):
        from core.pipeline.step6_template_fill import _get_template_filename
        assert _get_template_filename("答辩状") == "defense_template"
        assert _get_template_filename("起诉状") == "lawsuit_template"
        assert _get_template_filename("投诉状") == "complaint_template"

    def test_unknown_type(self):
        from core.pipeline.step6_template_fill import _get_template_filename
        assert _get_template_filename("未知类型") == "未知类型"


class TestGetDefaultDocTypes:
    def test_defendant(self):
        from core.pipeline.step6_template_fill import _get_default_doc_types
        docs = _get_default_doc_types("被诉方（被告）")
        assert "答辩状" in docs

    def test_unknown(self):
        from core.pipeline.step6_template_fill import _get_default_doc_types
        docs = _get_default_doc_types("未知")
        assert len(docs) >= 2


class TestGenerateFallbackContent:
    def test_assessment(self, tmp_path):
        from core.pipeline.step6_template_fill import _generate_fallback_content
        ctx = PipelineContext()
        ctx.distilled_card = DistilledCard(
            strategy_card=StrategyCard(situation_assessment="评估内容"),
        )
        result = _generate_fallback_content("案件处境评估报告", ctx)
        assert "评估内容" in result

    def test_action_advice(self, tmp_path):
        from core.pipeline.step6_template_fill import _generate_fallback_content
        ctx = PipelineContext()
        ctx.distilled_card = DistilledCard(
            strategy_card=StrategyCard(action_advice=[
                ActionAdvice(action="做X", priority="S", reasoning="因为Y"),
            ]),
        )
        result = _generate_fallback_content("行动建议书", ctx)
        assert "做X" in result

    def test_action_advice_empty(self, tmp_path):
        from core.pipeline.step6_template_fill import _generate_fallback_content
        ctx = PipelineContext()
        ctx.distilled_card = DistilledCard(
            strategy_card=StrategyCard(action_advice=[]),
        )
        result = _generate_fallback_content("行动建议书", ctx)
        assert "生成中" in result

    def test_evidence_gap(self, tmp_path):
        from core.pipeline.step6_template_fill import _generate_fallback_content
        ctx = PipelineContext()
        ctx.distilled_card = DistilledCard(
            strategy_card=StrategyCard(evidence_gap=["缺口1"]),
        )
        result = _generate_fallback_content("证据闭环补强清单", ctx)
        assert "缺口1" in result

    def test_evidence_gap_empty(self, tmp_path):
        from core.pipeline.step6_template_fill import _generate_fallback_content
        ctx = PipelineContext()
        ctx.distilled_card = DistilledCard(
            strategy_card=StrategyCard(evidence_gap=[]),
        )
        result = _generate_fallback_content("证据闭环补强清单", ctx)
        assert "生成中" in result

    def test_unknown_doc_type(self, tmp_path):
        from core.pipeline.step6_template_fill import _generate_fallback_content
        ctx = PipelineContext()
        ctx.distilled_card = DistilledCard()
        result = _generate_fallback_content("未知类型", ctx)
        assert "未知类型" in result

    def test_no_distilled_card(self, tmp_path):
        from core.pipeline.step6_template_fill import _generate_fallback_content
        ctx = PipelineContext()
        result = _generate_fallback_content("案件处境评估报告", ctx)
        assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════
# step6_template_fill — step6_template_fill main function
# ══════════════════════════════════════════════════════════════════════
class TestStep6TemplateFill:
    def test_no_distilled_card(self, tmp_path):
        from core.pipeline.step6_template_fill import step6_template_fill
        ctx = PipelineContext(output_dir=str(tmp_path))
        ctx.distilled_card = None
        ctx = step6_template_fill(ctx)
        assert len(ctx.errors) > 0

    def test_valid_fill(self, tmp_path):
        from core.pipeline.step6_template_fill import step6_template_fill
        ctx = PipelineContext(
            output_dir=str(tmp_path),
            identity="被诉方（被告）",
            goal="应诉答辩",
        )
        ctx.distilled_card = DistilledCard(
            fact_card=FactCard(case_id="C1", key_facts=["事实"]),
            strategy_card=StrategyCard(sabcd_rating="B"),
        )
        ctx = step6_template_fill(ctx)
        templates = getattr(ctx, "_filled_templates", {})
        assert len(templates) >= 1

    def test_creates_customer_dir(self, tmp_path):
        from core.pipeline.step6_template_fill import step6_template_fill
        out_dir = tmp_path / "new_output"
        ctx = PipelineContext(
            output_dir=str(out_dir),
            identity="被诉方（被告）",
            goal="应诉答辩",
        )
        ctx.distilled_card = DistilledCard(
            fact_card=FactCard(key_facts=["事实"]),
            strategy_card=StrategyCard(),
        )
        ctx = step6_template_fill(ctx)
        assert (out_dir / "customer").exists()


# ══════════════════════════════════════════════════════════════════════
# pipeline/__init__.py — run_pipeline
# ══════════════════════════════════════════════════════════════════════
class TestRunPipeline:
    def test_empty_input(self, tmp_path):
        from core.pipeline import run_pipeline
        ctx = PipelineContext(input_dir=str(tmp_path / "empty"), output_dir=str(tmp_path / "out"))
        os.makedirs(str(tmp_path / "empty"), exist_ok=True)
        ctx = run_pipeline(ctx)
        assert len(ctx.errors) > 0

    def test_valid_input(self, tmp_path):
        from core.pipeline import run_pipeline
        (tmp_path / "test.txt").write_text("原告张三诉被告李四借款合同纠纷" * 30, encoding="utf-8")
        out = tmp_path / "out"
        out.mkdir()
        ctx = PipelineContext(
            input_dir=str(tmp_path),
            output_dir=str(out),
            identity="被诉方（被告）",
            goal="应诉答辩",
        )
        ctx = run_pipeline(ctx)
        assert ctx.fact_card is not None


# ══════════════════════════════════════════════════════════════════════
# ai_client.py — sync API calls (not configured path)
# ══════════════════════════════════════════════════════════════════════
class TestAIClientSync:
    def test_call_api_a_not_configured(self):
        from core.ai_client import AIClient
        from core.ai_config import AIConfig
        client = AIClient(config=AIConfig(api_key=""))
        resp = client.call_api_a("prompt", "context")
        assert resp.success is False
        assert resp.latency_ms == 0

    def test_call_api_b_not_configured(self):
        from core.ai_client import AIClient
        from core.ai_config import AIConfig
        client = AIClient(config=AIConfig(api_key=""))
        resp = client.call_api_b("prompt", "context")
        assert resp.success is False

    def test_async_call_not_configured(self):
        from core.ai_client import AIClient
        from core.ai_config import AIConfig
        client = AIClient(config=AIConfig(api_key=""))
        import asyncio
        resp = asyncio.run(client.async_call("system", "user"))
        assert resp.success is False


# ══════════════════════════════════════════════════════════════════════
# checkpoint_builder.py — edge cases
# ══════════════════════════════════════════════════════════════════════
class TestCheckpointBuilder:
    def test_build_with_all_fields(self):
        from core.checkpoint_builder import build_ctx_snapshot
        ctx = PipelineContext(task_id="T1", identity="被告", goal="应诉答辩")
        ctx.fact_card = FactCard(case_id="C1")
        ctx.strategy_card = StrategyCard(sabcd_rating="B")
        ctx.distilled_card = DistilledCard()
        ctx._rendered_files = ["a.docx", "b.pdf"]
        ctx._filled_templates = {"答辩状": "内容"}
        snapshot = build_ctx_snapshot(ctx)
        data = json.loads(snapshot)
        assert data["task_id"] == "T1"
        assert "fact_card" in data
        assert "strategy_card" in data
        assert "distilled_card" in data
        assert "rendered_files" in data
        assert "filled_templates_keys" in data

    def test_build_with_raw_texts(self):
        from core.checkpoint_builder import build_ctx_snapshot
        ctx = PipelineContext()
        ctx.raw_texts = ["text1", "text2"]
        snapshot = build_ctx_snapshot(ctx)
        data = json.loads(snapshot)
        assert "raw_texts_len" in data
        assert "raw_texts_hash" in data

    def test_restore_full(self):
        from core.checkpoint_builder import build_ctx_snapshot, restore_ctx_from_snapshot
        ctx = PipelineContext(task_id="T1")
        ctx.fact_card = FactCard(case_id="C1")
        ctx.strategy_card = StrategyCard(sabcd_rating="B")
        ctx.distilled_card = DistilledCard()
        ctx._rendered_files = ["a.docx"]
        ctx.errors = ["err1"]
        snapshot = build_ctx_snapshot(ctx)

        ctx2 = PipelineContext()
        ctx2 = restore_ctx_from_snapshot(snapshot, ctx2)
        assert ctx2.fact_card.case_id == "C1"
        assert ctx2.strategy_card.sabcd_rating == "B"
        assert ctx2.distilled_card is not None
        assert "a.docx" in ctx2._rendered_files
        assert "err1" in ctx2.errors
