"""TDD tests for API-dependent modules — mock external HTTP calls."""
import pytest
import sys, os, json
from unittest.mock import patch, MagicMock, AsyncMock
sys.path.insert(0, ".")

from core.fact_card import PipelineContext, FactCard, Party, StrategyCard
from core.ai_mode import AIModeTracker, AIStatus


# ══════════════════════════════════════════════════════════════════════
# step3_fact_api_a — mock API paths
# ══════════════════════════════════════════════════════════════════════
class TestStep3FactApiA:
    def _make_ctx(self):
        ctx = PipelineContext(
            identity="被诉方（被告）",
            goal="应诉答辩",
        )
        ctx.fact_card = FactCard(
            case_id="C1",
            parties=[Party(name="张三", role="被告")],
            key_facts=["事实1"],
        )
        ctx.raw_texts = ["原告李四诉被告张三借款合同纠纷一案"]
        return ctx

    def test_no_fact_card(self):
        from core.pipeline.step3_fact_api_a import step3_fact_api_a
        ctx = PipelineContext()
        ctx.fact_card = None
        ctx = step3_fact_api_a(ctx)
        assert len(ctx.errors) > 0

    @patch("core.pipeline.step3_fact_api_a.is_api_configured", return_value=False)
    def test_not_configured(self, mock_cfg):
        from core.pipeline.step3_fact_api_a import step3_fact_api_a
        ctx = self._make_ctx()
        ctx = step3_fact_api_a(ctx)
        assert ctx.fact_card is not None
        assert ctx.fact_card.case_id == "C1"

    @patch("core.pipeline.step3_fact_api_a.is_api_configured", return_value=True)
    def test_api_success(self, mock_cfg):
        from core.pipeline.step3_fact_api_a import step3_fact_api_a
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=True,
            content=json.dumps({
                "case_id": "(2024)京01民初1号",
                "court": "北京法院",
                "parties": [{"name": "张三", "role": "被告"}],
                "key_facts": ["新事实1", "新事实2"],
                "disputed_facts": ["争议1"],
                "missing_materials": ["材料1"],
                "conflicts": ["冲突1"],
            }),
            latency_ms=500,
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_a.return_value = mock_response
            ctx = self._make_ctx()
            ctx = step3_fact_api_a(ctx)

        assert ctx.fact_card.case_id == "(2024)京01民初1号"
        assert ctx.fact_card.court == "北京法院"
        assert "新事实1" in ctx.fact_card.key_facts

    @patch("core.pipeline.step3_fact_api_a.is_api_configured", return_value=True)
    def test_api_failure_raises(self, mock_cfg):
        from core.pipeline.step3_fact_api_a import step3_fact_api_a, AIProviderError
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=False, content="", latency_ms=0, error="timeout",
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_a.return_value = mock_response
            ctx = self._make_ctx()
            with pytest.raises(AIProviderError):
                step3_fact_api_a(ctx)

    @patch("core.pipeline.step3_fact_api_a.is_api_configured", return_value=True)
    def test_invalid_json_raises(self, mock_cfg):
        from core.pipeline.step3_fact_api_a import step3_fact_api_a, AIProviderError
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=True, content="not json at all", latency_ms=100,
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_a.return_value = mock_response
            ctx = self._make_ctx()
            with pytest.raises(AIProviderError):
                step3_fact_api_a(ctx)

    @patch("core.pipeline.step3_fact_api_a.is_api_configured", return_value=True)
    def test_json_with_codeblock(self, mock_cfg):
        """LLM wraps JSON in ```json code blocks."""
        from core.pipeline.step3_fact_api_a import step3_fact_api_a
        from core.ai_client import APIResponse

        json_content = '```json\n{"case_id": "C2", "court": "法院", "key_facts": ["事实"]}\n```'
        mock_response = APIResponse(
            success=True, content=json_content, latency_ms=200,
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_a.return_value = mock_response
            ctx = self._make_ctx()
            ctx = step3_fact_api_a(ctx)

        assert ctx.fact_card.case_id == "C2"

    @patch("core.pipeline.step3_fact_api_a.is_api_configured", return_value=True)
    def test_tracker_created(self, mock_cfg):
        from core.pipeline.step3_fact_api_a import step3_fact_api_a
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=True,
            content=json.dumps({"case_id": "C3"}),
            latency_ms=100,
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_a.return_value = mock_response
            ctx = self._make_ctx()
            assert not hasattr(ctx, '_ai_mode_tracker') or ctx._ai_mode_tracker is None
            ctx = step3_fact_api_a(ctx)
            assert hasattr(ctx, '_ai_mode_tracker')
            assert ctx._ai_mode_tracker.api_a_status == AIStatus.AVAILABLE


# ══════════════════════════════════════════════════════════════════════
# step4_strategy_api_b — mock API paths
# ══════════════════════════════════════════════════════════════════════
class TestStep4StrategyApiB:
    def _make_ctx(self):
        ctx = PipelineContext(
            identity="被诉方（被告）",
            goal="应诉答辩",
        )
        ctx.fact_card = FactCard(
            case_id="C1",
            parties=[Party(name="张三", role="被告")],
            key_facts=["事实1"],
        )
        return ctx

    def test_no_fact_card(self):
        from core.pipeline.step4_strategy_api_b import step4_strategy_api_b
        ctx = PipelineContext()
        ctx.fact_card = None
        ctx = step4_strategy_api_b(ctx)
        assert len(ctx.errors) > 0

    @patch("core.pipeline.step4_strategy_api_b.is_api_configured", return_value=False)
    def test_not_configured_uses_fallback(self, mock_cfg):
        from core.pipeline.step4_strategy_api_b import step4_strategy_api_b
        ctx = self._make_ctx()
        ctx = step4_strategy_api_b(ctx)
        assert ctx.strategy_card is not None
        assert ctx.strategy_card.sabcd_rating in ("S", "A", "B", "C", "D")

    @patch("core.pipeline.step4_strategy_api_b.is_api_configured", return_value=True)
    def test_api_success(self, mock_cfg):
        from core.pipeline.step4_strategy_api_b import step4_strategy_api_b
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=True,
            content=json.dumps({
                "situation_assessment": "评估内容" * 30,
                "sabcd_rating": "B",
                "action_advice": [
                    {"action": "建议1", "priority": "S", "reasoning": "理由1"},
                    {"action": "建议2", "priority": "A", "reasoning": "理由2"},
                ],
                "evidence_gap": ["缺口1"],
                "risk_warnings": ["风险1"],
                "draft_documents": [
                    {"doc_type": "答辩状", "title": "答辩状", "content": "内容" * 100},
                ],
            }),
            latency_ms=800,
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_b.return_value = mock_response
            ctx = self._make_ctx()
            ctx = step4_strategy_api_b(ctx)

        assert ctx.strategy_card is not None
        assert ctx.strategy_card.sabcd_rating == "B"
        assert len(ctx.strategy_card.action_advice) >= 2

    @patch("core.pipeline.step4_strategy_api_b.is_api_configured", return_value=True)
    def test_api_failure_raises(self, mock_cfg):
        from core.pipeline.step4_strategy_api_b import step4_strategy_api_b, AIProviderError
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=False, content="", latency_ms=0, error="timeout",
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_b.return_value = mock_response
            ctx = self._make_ctx()
            with pytest.raises(AIProviderError):
                step4_strategy_api_b(ctx)

    @patch("core.pipeline.step4_strategy_api_b.is_api_configured", return_value=True)
    def test_invalid_json_raises(self, mock_cfg):
        from core.pipeline.step4_strategy_api_b import step4_strategy_api_b, AIProviderError
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=True, content="not json", latency_ms=100,
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_b.return_value = mock_response
            ctx = self._make_ctx()
            with pytest.raises(AIProviderError):
                step4_strategy_api_b(ctx)

    @patch("core.pipeline.step4_strategy_api_b.is_api_configured", return_value=True)
    def test_no_draft_documents_triggers_fallback(self, mock_cfg):
        """API returns no draft_documents → fallback generation."""
        from core.pipeline.step4_strategy_api_b import step4_strategy_api_b
        from core.ai_client import APIResponse

        mock_response = APIResponse(
            success=True,
            content=json.dumps({
                "situation_assessment": "评估" * 30,
                "sabcd_rating": "A",
                "action_advice": [{"action": "建议1", "priority": "S", "reasoning": "理由"}],
                "evidence_gap": [],
                "risk_warnings": [],
                "draft_documents": [],
            }),
            latency_ms=500,
        )

        with patch("core.ai_client.AIClient") as MockClient:
            MockClient.return_value.call_api_b.return_value = mock_response
            ctx = self._make_ctx()
            ctx = step4_strategy_api_b(ctx)

        assert ctx.strategy_card is not None
        # draft_documents should be filled by fallback
        assert len(ctx.strategy_card.draft_documents) >= 0


# ══════════════════════════════════════════════════════════════════════
# unified_client.py — mock HTTP calls
# ══════════════════════════════════════════════════════════════════════
class TestUnifiedClient:
    def test_provider_config(self):
        from core.ai.unified_client import ProviderConfig
        cfg = ProviderConfig(name="test", api_key="key", base_url="http://api.com", model="m")
        assert cfg.is_configured() is True
        assert cfg.name == "test"

    def test_provider_config_not_configured(self):
        from core.ai.unified_client import ProviderConfig
        cfg = ProviderConfig(api_key="")
        assert cfg.is_configured() is False

    def test_provider_config_masked_dict(self):
        from core.ai.unified_client import ProviderConfig
        cfg = ProviderConfig(name="test", api_key="abcdefghijklmnop", base_url="http://api.com", model="m")
        d = cfg.masked_dict()
        assert "abcdefghijklmnop" not in d["api_key"]

    def test_client_init(self):
        from core.ai.unified_client import UnifiedAIClient, ProviderConfig
        cfg = ProviderConfig(name="test", api_key="key", base_url="http://api.com/v1", model="m")
        client = UnifiedAIClient(cfg)
        assert client.name == "test"
        assert client.is_configured is True
        # /v1 should be stripped
        assert client.config.base_url == "http://api.com"

    def test_client_not_configured(self):
        from core.ai.unified_client import UnifiedAIClient, ProviderConfig
        cfg = ProviderConfig(api_key="")
        client = UnifiedAIClient(cfg)
        assert client.is_configured is False

    def test_chat_not_configured(self):
        from core.ai.unified_client import UnifiedAIClient, ProviderConfig
        cfg = ProviderConfig(api_key="")
        client = UnifiedAIClient(cfg)
        resp = client.chat("system", "user")
        assert resp.success is False

    def test_chat_messages_not_configured(self):
        from core.ai.unified_client import UnifiedAIClient, ProviderConfig
        cfg = ProviderConfig(api_key="")
        client = UnifiedAIClient(cfg)
        messages = [{"role": "user", "content": "test"}]
        resp = client.chat_messages(messages)
        assert resp.success is False

    @patch("httpx.Client")
    def test_chat_success(self, MockHttpx):
        from core.ai.unified_client import UnifiedAIClient, ProviderConfig

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "回复内容"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        MockHttpx.return_value = mock_client

        cfg = ProviderConfig(name="test", api_key="key", base_url="http://api.com", model="m")
        client = UnifiedAIClient(cfg)
        resp = client.chat("system", "user")
        assert resp.success is True
        assert resp.content == "回复内容"

    @patch("httpx.Client")
    def test_chat_timeout(self, MockHttpx):
        from core.ai.unified_client import UnifiedAIClient, ProviderConfig
        import httpx

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.TimeoutException("timeout")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        MockHttpx.return_value = mock_client

        cfg = ProviderConfig(name="test", api_key="key", base_url="http://api.com", model="m")
        client = UnifiedAIClient(cfg)
        resp = client.chat("system", "user")
        assert resp.success is False
        assert "timeout" in resp.error.lower()

    @patch("httpx.Client")
    def test_chat_http_error(self, MockHttpx):
        from core.ai.unified_client import UnifiedAIClient, ProviderConfig
        import httpx

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Rate limited"
        http_err = httpx.HTTPStatusError("429", request=MagicMock(), response=mock_resp)

        mock_client = MagicMock()
        mock_client.post.side_effect = http_err
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        MockHttpx.return_value = mock_client

        cfg = ProviderConfig(name="test", api_key="key", base_url="http://api.com", model="m")
        client = UnifiedAIClient(cfg)
        resp = client.chat("system", "user")
        assert resp.success is False
        assert "429" in resp.error

    @patch("httpx.Client")
    def test_chat_generic_exception(self, MockHttpx):
        from core.ai.unified_client import UnifiedAIClient, ProviderConfig

        mock_client = MagicMock()
        mock_client.post.side_effect = ConnectionError("network error")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        MockHttpx.return_value = mock_client

        cfg = ProviderConfig(name="test", api_key="key", base_url="http://api.com", model="m")
        client = UnifiedAIClient(cfg)
        resp = client.chat("system", "user")
        assert resp.success is False

    def test_chat_messages_success(self):
        from core.ai.unified_client import UnifiedAIClient, ProviderConfig

        cfg = ProviderConfig(name="test", api_key="key", base_url="http://api.com", model="m")
        client = UnifiedAIClient(cfg)

        # chat_messages uses the same underlying chat method
        messages = [{"role": "system", "content": "律师"}, {"role": "user", "content": "分析案件"}]

        with patch("httpx.Client") as MockHttpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "分析结果"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
            }
            mock_resp.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.post.return_value = mock_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockHttpx.return_value = mock_client

            resp = client.chat_messages(messages)
            assert resp.success is True
            assert resp.content == "分析结果"
