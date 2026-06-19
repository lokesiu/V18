"""TDD tests for AI config, mode, client, and schemas."""
import pytest
import sys, os
sys.path.insert(0, ".")


class TestAIConfig:
    def test_default_config(self):
        from core.ai_config import AIConfig
        c = AIConfig()
        assert c.base_url == "https://api.deepseek.com"
        assert c.model_extract == "deepseek-chat"
        assert c.timeout == 60
        assert c.is_configured is False

    def test_configured(self):
        from core.ai_config import AIConfig
        c = AIConfig(api_key="test_key")
        assert c.is_configured is True

    def test_to_dict_masks_key(self):
        from core.ai_config import AIConfig
        c = AIConfig(api_key="abcdefghijklmnop")
        d = c.to_dict()
        assert "abcdefghijklmnop" not in d["api_key"]
        assert "..." in d["api_key"]

    def test_get_ai_config(self):
        from core.ai_config import get_ai_config
        c = get_ai_config()
        assert isinstance(c.api_key, str)

    def test_is_api_configured(self):
        from core.ai_config import is_api_configured
        result = is_api_configured()
        assert isinstance(result, bool)

    def test_get_api_status(self):
        from core.ai_config import get_api_status
        status = get_api_status()
        assert status in ("not_configured", "configured")


class TestAIMode:
    def test_default_mode(self):
        from core.ai_mode import AIModeTracker, AIMode
        t = AIModeTracker()
        assert t.ai_mode == AIMode.LOCAL_FALLBACK

    def test_api_a_success(self):
        from core.ai_mode import AIModeTracker, AIMode, AIStatus
        t = AIModeTracker()
        t.start_api_a()
        t.end_api_a(success=True, latency_ms=100)
        assert t.api_a_status == AIStatus.AVAILABLE
        assert t.api_a_latency_ms == 100

    def test_api_b_success(self):
        from core.ai_mode import AIModeTracker, AIMode, AIStatus
        t = AIModeTracker()
        t.start_api_b()
        t.end_api_b(success=True, latency_ms=200)
        assert t.api_b_status == AIStatus.AVAILABLE

    def test_both_success_real_ai(self):
        from core.ai_mode import AIModeTracker, AIMode
        t = AIModeTracker()
        t.end_api_a(success=True)
        t.end_api_b(success=True)
        assert t.ai_mode == AIMode.REAL_AI

    def test_one_success_mixed(self):
        from core.ai_mode import AIModeTracker, AIMode
        t = AIModeTracker()
        t.end_api_a(success=True)
        t.end_api_b(success=False)
        assert t.ai_mode == AIMode.MIXED

    def test_both_failed_local(self):
        from core.ai_mode import AIModeTracker, AIMode
        t = AIModeTracker()
        t.end_api_a(success=False)
        t.end_api_b(success=False)
        assert t.ai_mode == AIMode.LOCAL_FALLBACK

    def test_finish(self):
        from core.ai_mode import AIModeTracker
        t = AIModeTracker()
        t.finish()
        assert t.end_time is not None

    def test_to_dict(self):
        from core.ai_mode import AIModeTracker
        t = AIModeTracker()
        d = t.to_dict()
        assert "ai_mode" in d
        assert "start_time" in d

    def test_save_manifest(self, tmp_path):
        from core.ai_mode import AIModeTracker
        import json
        t = AIModeTracker()
        t.save_manifest(str(tmp_path))
        path = tmp_path / "_internal" / "ai_run_manifest.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "ai_mode" in data

    def test_get_labels(self):
        from core.ai_mode import get_ai_mode_label, get_ai_mode_description, AIMode
        for mode in AIMode:
            assert len(get_ai_mode_label(mode)) > 0
            assert len(get_ai_mode_description(mode)) > 0


class TestSchemas:
    def test_fact_extraction_result(self):
        from core.pipeline.schemas import FactExtractionResult
        r = FactExtractionResult()
        assert r.case_id == ""
        assert r.parties == []

    def test_fact_extraction_with_data(self):
        from core.pipeline.schemas import FactExtractionResult, ExtractedParty, TimelineEvent
        r = FactExtractionResult(
            case_id="C1",
            parties=[ExtractedParty(name="A", role="原告")],
            timeline=[TimelineEvent(date="2024-01-01", event="签约")],
        )
        assert r.case_id == "C1"
        assert len(r.parties) == 1
        assert r.parties[0].name == "A"

    def test_strategy_reasoning_result(self):
        from core.pipeline.schemas import StrategyReasoningResult
        r = StrategyReasoningResult(
            situation_assessment="评估",
            sabcd_rating="B",
        )
        assert r.sabcd_rating == "B"

    def test_model_json_schema(self):
        from core.pipeline.schemas import FactExtractionResult, StrategyReasoningResult
        s1 = FactExtractionResult.model_json_schema()
        assert "properties" in s1
        s2 = StrategyReasoningResult.model_json_schema()
        assert "properties" in s2


class TestAIClient:
    def test_not_configured(self):
        from core.ai_client import AIClient
        from core.ai_config import AIConfig
        client = AIClient(config=AIConfig(api_key=""))
        resp = client.call_api_a("prompt", "context")
        assert resp.success is False
        assert "not configured" in resp.error.lower() or resp.error

    def test_call_api_b_not_configured(self):
        from core.ai_client import AIClient
        from core.ai_config import AIConfig
        client = AIClient(config=AIConfig(api_key=""))
        resp = client.call_api_b("prompt", "context")
        assert resp.success is False

    def test_api_response_fields(self):
        from core.ai_client import APIResponse
        r = APIResponse(success=True, content="test", latency_ms=50)
        assert r.success is True
        assert r.content == "test"
        assert r.token_usage is None
        assert r.error is None
