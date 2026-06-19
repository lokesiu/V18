"""TDD tests for pipeline steps and postprocess/render modules."""
import pytest
import sys, os
sys.path.insert(0, ".")

from core.fact_card import PipelineContext, FactCard, StrategyCard, DistilledCard, Party


class TestStep1Intake:
    def test_no_input_dir(self):
        from core.pipeline.step1_intake import step1_intake
        ctx = PipelineContext(input_dir="")
        ctx = step1_intake(ctx)
        assert len(ctx.errors) > 0

    def test_empty_dir(self, tmp_path):
        from core.pipeline.step1_intake import step1_intake
        ctx = PipelineContext(input_dir=str(tmp_path))
        ctx = step1_intake(ctx)
        assert len(ctx.errors) > 0

    def test_valid_dir(self, tmp_path):
        from core.pipeline.step1_intake import step1_intake
        (tmp_path / "a.txt").write_text("内容" * 50, encoding="utf-8")
        ctx = PipelineContext(input_dir=str(tmp_path))
        ctx = step1_intake(ctx)
        assert len(ctx.file_list) >= 1


class TestStep2Extract:
    def test_no_raw_texts(self):
        from core.pipeline.step2_extract import step2_extract
        ctx = PipelineContext()
        ctx = step2_extract(ctx)
        assert len(ctx.errors) > 0

    def test_with_raw_texts(self):
        from core.pipeline.step2_extract import step2_extract
        ctx = PipelineContext(raw_texts=["原告张三诉被告李四借款合同纠纷一案"])
        ctx = step2_extract(ctx)
        assert ctx.fact_card is not None


class TestStep3FactExtract:
    def test_no_raw_texts(self):
        from core.pipeline.step3_fact_extract import step3_fact_extract
        ctx = PipelineContext()
        ctx = step3_fact_extract(ctx)
        assert len(ctx.errors) > 0

    def test_no_api_skips(self):
        from core.pipeline.step3_fact_extract import step3_fact_extract
        ctx = PipelineContext(raw_texts=["测试文本"])
        ctx.fact_card = FactCard(key_facts=["事实"])
        ctx = step3_fact_extract(ctx)
        # Should skip gracefully if API not configured
        assert ctx.fact_card is not None


class TestStep4StrategyReasoning:
    def test_no_fact_card(self):
        from core.pipeline.step4_strategy_reasoning import step4_strategy_reasoning
        ctx = PipelineContext()
        ctx = step4_strategy_reasoning(ctx)
        assert len(ctx.errors) > 0

    def test_no_api_uses_fallback(self):
        from core.pipeline.step4_strategy_reasoning import step4_strategy_reasoning
        ctx = PipelineContext(identity="被诉方（被告）", goal="应诉答辩")
        ctx.fact_card = FactCard(
            case_id="C1",
            parties=[Party(name="A", role="原告")],
            key_facts=["事实1"],
        )
        ctx = step4_strategy_reasoning(ctx)
        assert ctx.strategy_card is not None


class TestStep5Distill:
    def test_no_fact_card(self):
        from core.pipeline.step5_distill import step5_distill
        ctx = PipelineContext()
        ctx.strategy_card = StrategyCard()
        ctx = step5_distill(ctx)
        assert len(ctx.errors) > 0

    def test_no_strategy_card(self):
        from core.pipeline.step5_distill import step5_distill
        ctx = PipelineContext()
        ctx.fact_card = FactCard()
        ctx = step5_distill(ctx)
        assert len(ctx.errors) > 0

    def test_valid_distill(self, tmp_path):
        from core.pipeline.step5_distill import step5_distill
        ctx = PipelineContext(output_dir=str(tmp_path))
        ctx.fact_card = FactCard(
            case_id="C1",
            key_facts=["事实1"],
            parties=[Party(name="A", role="原告")],
        )
        ctx.strategy_card = StrategyCard(
            sabcd_rating="B",
            situation_assessment="评估",
            action_advice=[],
        )
        ctx = step5_distill(ctx)
        assert ctx.distilled_card is not None


class TestStep6LlmGenerate:
    def test_no_distilled_card(self):
        from core.pipeline.step6_llm_generate import step6_llm_generate
        ctx = PipelineContext()
        ctx = step6_llm_generate(ctx)
        assert len(ctx.errors) > 0

    def test_no_api_skips(self):
        from core.pipeline.step6_llm_generate import step6_llm_generate
        ctx = PipelineContext(identity="被诉方（被告）")
        ctx.distilled_card = DistilledCard(
            fact_card=FactCard(key_facts=["事实"]),
            strategy_card=StrategyCard(sabcd_rating="B"),
        )
        ctx = step6_llm_generate(ctx)
        assert hasattr(ctx, '_llm_generated_docs')


class TestStep6TemplateFill:
    def test_no_distilled_card(self):
        from core.pipeline.step6_template_fill import step6_template_fill
        ctx = PipelineContext()
        ctx = step6_template_fill(ctx)
        assert len(ctx.errors) > 0

    def test_valid_fill(self, tmp_path):
        from core.pipeline.step6_template_fill import step6_template_fill
        ctx = PipelineContext(
            identity="被诉方（被告）",
            goal="应诉答辩",
            output_dir=str(tmp_path),
        )
        ctx.distilled_card = DistilledCard(
            fact_card=FactCard(case_id="C1", key_facts=["事实"]),
            strategy_card=StrategyCard(sabcd_rating="B"),
        )
        ctx = step6_template_fill(ctx)
        assert hasattr(ctx, '_filled_templates')


class TestStep7Postprocess:
    def test_empty_docs(self):
        from core.pipeline.step7_postprocess import postprocess_documents
        ctx = PipelineContext()
        result = postprocess_documents(ctx)
        assert result == {}

    def test_defense_postprocess(self):
        from core.pipeline.step7_postprocess import postprocess_documents
        ctx = PipelineContext()
        ctx.fact_card = FactCard(
            identity="被诉方（被告）",
            parties=[Party(name="张三", role="原告")],
        )
        ctx._llm_generated_docs = {
            "答辩状": "民事答辩状\n被答辩人（原告）：张三，住址：____",
        }
        result = postprocess_documents(ctx)
        assert "答辩状" in result

    def test_other_doc_passthrough(self):
        from core.pipeline.step7_postprocess import postprocess_documents
        ctx = PipelineContext()
        ctx._llm_generated_docs = {"案件处境评估报告": "内容不变"}
        result = postprocess_documents(ctx)
        assert result["案件处境评估报告"] == "内容不变"


class TestStep7RenderManifest:
    def test_get_manifest_empty(self):
        from core.pipeline.step7_render_manifest import get_manifest_entries
        entries = get_manifest_entries("nonexistent_task")
        assert entries == []

    def test_is_retryable(self):
        from core.pipeline.step7_render_manifest import is_retryable
        assert is_retryable("PermissionError") is True
        assert is_retryable("RENDER_FAILED") is True
        assert is_retryable("FileNotFoundError") is False
        assert is_retryable("ModuleNotFoundError") is False
        assert is_retryable("ENOSPC") is False
        assert is_retryable("UnknownError") is True  # default: allow retry

    def test_is_retryable_enospc_msg(self):
        from core.pipeline.step7_render_manifest import is_retryable
        assert is_retryable("OSError", "No space left on device") is False

    def test_is_retryable_missing_file_msg(self):
        from core.pipeline.step7_render_manifest import is_retryable
        assert is_retryable("OSError", "No such file or directory") is False


class TestStep8QualityGate:
    def test_no_customer_dir(self):
        from core.pipeline.step8_quality_gate import step8_quality_gate
        ctx = PipelineContext(output_dir="/nonexistent")
        ctx = step8_quality_gate(ctx)
        assert len(ctx.errors) > 0

    def test_pass_with_valid_files(self, tmp_path):
        from core.pipeline.step8_quality_gate import step8_quality_gate
        from core.render.docx_renderer import render_docx_from_text
        from core.render.xlsx_renderer import render_xlsx

        customer = tmp_path / "customer"
        customer.mkdir()

        # Create valid DOCX
        render_docx_from_text("答辩状\n测试内容" * 50, str(customer / "06_答辩状.docx"))
        render_docx_from_text("报告\n测试内容" * 50, str(customer / "01_报告.docx"))

        # Create valid XLSX
        render_xlsx(FactCard(), str(customer / "04_证据目录.xlsx"))

        ctx = PipelineContext(output_dir=str(tmp_path))
        ctx = step8_quality_gate(ctx)
        # DOCX/XLSX checks should pass


class TestRunner:
    def test_doctor(self):
        from core.runner import cmd_doctor
        result = cmd_doctor()
        assert isinstance(result, bool)

    def test_inspect_nonexistent(self):
        from core.runner import cmd_inspect
        result = cmd_inspect("/nonexistent")
        assert result is False
