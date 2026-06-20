"""TDD tests for pipeline steps — exception paths and edge cases."""
import pytest
import sys, os
from unittest.mock import patch, MagicMock
sys.path.insert(0, ".")

from core.fact_card import (
    PipelineContext, FactCard, Party, SourceRef, StrategyCard, DistilledCard,
)


# ══════════════════════════════════════════════════════════════════════
# step1_intake — exception paths
# ══════════════════════════════════════════════════════════════════════
class TestStep1Intake:
    def _get_mod(self):
        import sys
        return sys.modules.get("core.pipeline.step1_intake")

    def test_file_not_found_error(self):
        from core.pipeline.step1_intake import step1_intake
        mod = self._get_mod()
        with patch.object(mod, 'run_intake', side_effect=FileNotFoundError("dir not found")):
            ctx = PipelineContext(input_dir="/nonexistent")
            ctx = step1_intake(ctx)
            assert len(ctx.errors) > 0

    def test_permission_error(self):
        from core.pipeline.step1_intake import step1_intake
        mod = self._get_mod()
        with patch.object(mod, 'run_intake', side_effect=PermissionError("no access")):
            ctx = PipelineContext(input_dir="/denied")
            ctx = step1_intake(ctx)
            assert len(ctx.errors) > 0

    def test_generic_exception(self):
        from core.pipeline.step1_intake import step1_intake
        mod = self._get_mod()
        with patch.object(mod, 'run_intake', side_effect=RuntimeError("unexpected")):
            ctx = PipelineContext(input_dir="/dir")
            ctx = step1_intake(ctx)
            assert len(ctx.errors) > 0


# ══════════════════════════════════════════════════════════════════════
# step2_extract — integration tests (module import makes patching hard)
# ══════════════════════════════════════════════════════════════════════
class TestStep2Extract:
    def test_no_raw_texts(self):
        from core.pipeline.step2_extract import step2_extract
        ctx = PipelineContext()
        ctx = step2_extract(ctx)
        assert len(ctx.errors) > 0

    def test_with_raw_texts(self):
        from core.pipeline.step2_extract import step2_extract
        ctx = PipelineContext(raw_texts=["原告张三诉被告李四借款10万元"])
        ctx = step2_extract(ctx)
        assert ctx.fact_card is not None


# ══════════════════════════════════════════════════════════════════════
# step3_fact_extract — mock API paths
# ══════════════════════════════════════════════════════════════════════
class TestStep3FactExtract:
    @patch("core.pipeline.step3_fact_extract.is_api_configured", return_value=False)
    def test_not_configured_skips(self, mock_cfg):
        from core.pipeline.step3_fact_extract import step3_fact_extract
        ctx = PipelineContext(raw_texts=["text"])
        ctx.fact_card = FactCard(key_facts=["事实"])
        ctx = step3_fact_extract(ctx)
        assert ctx.fact_card is not None

    @patch("core.pipeline.step3_fact_extract.is_api_configured", return_value=True)
    def test_api_success(self, mock_cfg):
        from core.pipeline.step3_fact_extract import step3_fact_extract
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=True,
            content='{"case_id":"C2","court":"法院","key_facts":["新事实"]}',
            latency_ms=300,
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_a.return_value = mock_response
            ctx = PipelineContext(raw_texts=["text"])
            ctx.fact_card = FactCard()
            ctx = step3_fact_extract(ctx)

        assert ctx.fact_card.case_id == "C2"

    @patch("core.pipeline.step3_fact_extract.is_api_configured", return_value=True)
    def test_api_failure(self, mock_cfg):
        from core.pipeline.step3_fact_extract import step3_fact_extract
        from core.pipeline import AIProviderError
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=False, content="", latency_ms=0, error="timeout",
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_a.return_value = mock_response
            ctx = PipelineContext(raw_texts=["text"])
            ctx.fact_card = FactCard()
            with pytest.raises(AIProviderError):
                step3_fact_extract(ctx)

    @patch("core.pipeline.step3_fact_extract.is_api_configured", return_value=True)
    def test_tracker_created(self, mock_cfg):
        from core.pipeline.step3_fact_extract import step3_fact_extract
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=True, content='{"case_id":"C3"}', latency_ms=100,
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_a.return_value = mock_response
            ctx = PipelineContext(raw_texts=["text"])
            ctx.fact_card = FactCard()
            ctx = step3_fact_extract(ctx)

        assert hasattr(ctx, '_ai_mode_tracker')


# ══════════════════════════════════════════════════════════════════════
# step5_distill — integration tests
# ══════════════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════════════
# ai_client.py — not-configured paths
# ══════════════════════════════════════════════════════════════════════
class TestAIClient:
    def test_call_api_a_not_configured(self):
        from core.ai_client import AIClient
        from core.ai_config import AIConfig
        client = AIClient(config=AIConfig(api_key=""))
        resp = client.call_api_a("p", "c")
        assert resp.success is False
        assert resp.latency_ms == 0

    def test_call_api_b_not_configured(self):
        from core.ai_client import AIClient
        from core.ai_config import AIConfig
        client = AIClient(config=AIConfig(api_key=""))
        resp = client.call_api_b("p", "c")
        assert resp.success is False

    def test_test_api_connection_not_configured(self, monkeypatch):
        from core.ai_client import test_api_connection
        from core.ai_config import AIConfig
        original_is_configured = AIConfig.is_configured
        AIConfig.is_configured = property(lambda self: False)
        try:
            result = test_api_connection()
            assert result is False
        finally:
            AIConfig.is_configured = original_is_configured


# ══════════════════════════════════════════════════════════════════════
# multimodal.py — more utility functions
# ══════════════════════════════════════════════════════════════════════
class TestMultimodalMore:
    def test_build_multimodal_messages(self):
        from core.ai.multimodal import build_multimodal_messages
        msgs = build_multimodal_messages("律师", "文本内容", image_paths=None)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_build_multimodal_messages_with_images(self, tmp_path):
        from core.ai.multimodal import build_multimodal_messages
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 10)
        msgs = build_multimodal_messages("律师", "文本", image_paths=[str(img)])
        assert len(msgs) == 3

    def test_encode_image_base64_gif(self, tmp_path):
        from core.ai.multimodal import encode_image_base64
        img = tmp_path / "test.gif"
        img.write_bytes(b"GIF89a" + b"\x00" * 10)
        result = encode_image_base64(str(img))
        assert result is not None
        assert "image/gif" in result


# ══════════════════════════════════════════════════════════════════════
# pipeline/__init__.py — integration
# ══════════════════════════════════════════════════════════════════════
class TestPipelineInit:
    def test_run_pipeline_logs_errors(self, tmp_path):
        from core.pipeline import run_pipeline
        (tmp_path / "empty.txt").write_text("", encoding="utf-8")
        ctx = PipelineContext(
            input_dir=str(tmp_path),
            output_dir=str(tmp_path / "out"),
            identity="被诉方（被告）",
            goal="应诉答辩",
        )
        ctx = run_pipeline(ctx)
        assert len(ctx.logs) > 0
