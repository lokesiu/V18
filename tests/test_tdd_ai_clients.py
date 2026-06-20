"""TDD tests for AI provider registry and clients — no API calls needed."""
import pytest
import sys
sys.path.insert(0, ".")

from core.ai.provider_registry import ProviderRegistry, get_provider_registry
from core.ai.deepseek_client import DeepSeekClient, APIResponse as DSResponse
from core.ai.mimo_client import MiMoClient, APIResponse as MiMoResponse


# ══════════════════════════════════════════════════════════════════════
# DeepSeekClient
# ══════════════════════════════════════════════════════════════════════
class TestDeepSeekClient:
    def test_not_configured(self):
        c = DeepSeekClient(api_key="")
        assert c.is_configured is False

    def test_configured(self):
        c = DeepSeekClient(api_key="test_key_123")
        assert c.is_configured is True

    def test_default_values(self):
        c = DeepSeekClient(api_key="k")
        assert c.base_url == "https://api.deepseek.com"
        assert c.model_extract == "deepseek-chat"
        assert c.model_strategy == "deepseek-chat"
        assert c.timeout == 60

    def test_custom_values(self):
        c = DeepSeekClient(
            api_key="k",
            base_url="https://custom.api.com/",
            model_extract="model-a",
            model_strategy="model-b",
            timeout=30,
        )
        assert c.base_url == "https://custom.api.com"
        assert c.model_extract == "model-a"
        assert c.model_strategy == "model-b"
        assert c.timeout == 30

    def test_extract_facts_not_configured(self):
        c = DeepSeekClient(api_key="")
        resp = c.extract_facts("prompt", "context")
        assert resp.success is False
        assert "not configured" in resp.error.lower()

    def test_generate_strategy_not_configured(self):
        c = DeepSeekClient(api_key="")
        resp = c.generate_strategy("prompt", "context")
        assert resp.success is False

    def test_test_connection_not_configured(self):
        c = DeepSeekClient(api_key="")
        resp = c.test_connection()
        assert resp.success is False

    def test_api_response_fields(self):
        resp = DSResponse(success=True, content="ok", latency_ms=50, model="m")
        assert resp.success is True
        assert resp.content == "ok"
        assert resp.model == "m"
        assert resp.token_usage is None
        assert resp.error is None


# ══════════════════════════════════════════════════════════════════════
# MiMoClient
# ══════════════════════════════════════════════════════════════════════
class TestMiMoClient:
    def test_not_configured(self):
        c = MiMoClient(api_key="")
        assert c.is_configured is False

    def test_configured(self):
        c = MiMoClient(api_key="test_key")
        assert c.is_configured is True

    def test_default_values(self):
        c = MiMoClient(api_key="k")
        assert c.base_url == "https://api.mimo.ai"
        assert c.model == "mimo-v2.5-pro"
        assert c.timeout == 60

    def test_custom_values(self):
        c = MiMoClient(
            api_key="k",
            base_url="https://custom.mimo.ai/",
            model="custom-model",
            timeout=30,
        )
        assert c.base_url == "https://custom.mimo.ai"
        assert c.model == "custom-model"
        assert c.timeout == 30

    def test_critique_facts_not_configured(self):
        c = MiMoClient(api_key="")
        resp = c.critique_facts("{}", "text")
        assert resp.success is False

    def test_review_strategy_not_configured(self):
        c = MiMoClient(api_key="")
        resp = c.review_strategy("{}", "{}")
        assert resp.success is False

    def test_test_connection_not_configured(self):
        c = MiMoClient(api_key="")
        resp = c.test_connection()
        assert resp.success is False

    def test_api_response_fields(self):
        resp = MiMoResponse(success=True, content="ok", latency_ms=50, model="m")
        assert resp.success is True
        assert resp.content == "ok"
        assert resp.model == "m"


# ══════════════════════════════════════════════════════════════════════
# ProviderRegistry
# ══════════════════════════════════════════════════════════════════════
class TestProviderRegistry:
    def test_init(self):
        reg = ProviderRegistry()
        assert reg is not None

    def test_deepseek_property(self):
        reg = ProviderRegistry()
        ds = reg.deepseek
        # May or may not be configured depending on settings
        assert ds is None or hasattr(ds, 'is_configured')

    def test_mimo_property(self):
        reg = ProviderRegistry()
        mm = reg.mimo
        assert mm is None or hasattr(mm, 'is_configured')

    def test_get_ai_mode(self):
        reg = ProviderRegistry()
        mode = reg.get_ai_mode()
        assert mode in ("dual_ai", "deepseek_ai", "mimo_ai", "local_fallback")

    def test_is_dual_ai_available(self):
        reg = ProviderRegistry()
        result = reg.is_dual_ai_available()
        assert isinstance(result, bool)
        # Should match get_ai_mode
        if reg.get_ai_mode() == "dual_ai":
            assert result is True
        else:
            assert result is False

    def test_refresh(self):
        reg = ProviderRegistry()
        # refresh should not raise
        reg.refresh()
        mode = reg.get_ai_mode()
        assert mode in ("dual_ai", "deepseek_ai", "mimo_ai", "local_fallback")

    def test_singleton(self):
        r1 = get_provider_registry()
        r2 = get_provider_registry()
        assert r1 is r2


# ══════════════════════════════════════════════════════════════════════
# ProviderRegistry with mock settings
# ══════════════════════════════════════════════════════════════════════
class TestProviderRegistryWithMockSettings:
    def test_deepseek_only(self, monkeypatch):
        """When only DeepSeek is configured."""
        from core.settings_store import SettingsStore, AISettings, DeepSeekSettings, MiMoSettings
        store = SettingsStore()
        store.update_deepseek(api_key="test_ds_key")
        store.update_mimo(api_key="")

        reg = ProviderRegistry()
        # Override the registry's internal state
        reg._deepseek = DeepSeekClient(api_key="test_ds_key")
        reg._mimo = None

        assert reg.get_ai_mode() == "deepseek_ai"
        assert reg.is_dual_ai_available() is False

    def test_mimo_only(self):
        """When only MiMo is configured."""
        reg = ProviderRegistry()
        reg._deepseek = None
        reg._mimo = MiMoClient(api_key="test_mimo_key")

        assert reg.get_ai_mode() == "mimo_ai"
        assert reg.is_dual_ai_available() is False

    def test_dual_ai(self):
        """When both are configured."""
        reg = ProviderRegistry()
        reg._deepseek = DeepSeekClient(api_key="test_ds_key")
        reg._mimo = MiMoClient(api_key="test_mimo_key")

        assert reg.get_ai_mode() == "dual_ai"
        assert reg.is_dual_ai_available() is True

    def test_neither_configured(self):
        """When neither is configured."""
        reg = ProviderRegistry()
        reg._deepseek = None
        reg._mimo = None

        assert reg.get_ai_mode() == "local_fallback"
        assert reg.is_dual_ai_available() is False

    def test_deepseek_empty_key(self):
        """DeepSeek with empty key is not configured."""
        reg = ProviderRegistry()
        reg._deepseek = DeepSeekClient(api_key="")
        reg._mimo = None

        assert reg.get_ai_mode() == "local_fallback"
