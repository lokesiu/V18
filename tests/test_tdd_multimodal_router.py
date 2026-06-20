"""TDD tests for multimodal_router.py — all routing paths."""
import pytest
import sys, os
from unittest.mock import MagicMock, patch
sys.path.insert(0, ".")

from core.ai.multimodal_router import (
    MultimodalRouter, RouteMode, RouteResult,
    create_router_from_settings,
)
from core.ai.unified_client import UnifiedAIClient, ProviderConfig
from core.ai.multimodal import FileCategory, get_file_summary


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════
def _mock_client(success=True, content="回复内容"):
    """Create a mock UnifiedAIClient."""
    from core.contracts.ai_provider import AIResponse
    client = MagicMock(spec=UnifiedAIClient)
    client.is_configured = True
    client.chat.return_value = AIResponse(
        success=success, content=content, latency_ms=100,
        error=None if success else "timeout",
    )
    client.chat_multimodal.return_value = AIResponse(
        success=success, content=f"[多模态]{content}", latency_ms=200,
        error=None if success else "timeout",
    )
    return client


def _mock_client_not_configured():
    client = MagicMock(spec=UnifiedAIClient)
    client.is_configured = False
    return client


# ══════════════════════════════════════════════════════════════════════
# MultimodalRouter — preview mode
# ══════════════════════════════════════════════════════════════════════
class TestRouterPreview:
    def test_preview_returns_success(self):
        router = MultimodalRouter(mode=RouteMode.PREVIEW)
        result = router.route_request([], "system", "text")
        assert result.success is True
        assert "预览" in result.content
        assert result.mode_used == RouteMode.PREVIEW


# ══════════════════════════════════════════════════════════════════════
# MultimodalRouter — DeepSeek only mode
# ══════════════════════════════════════════════════════════════════════
class TestRouterDeepSeekOnly:
    def test_success(self):
        ds = _mock_client(success=True, content="DeepSeek回复")
        router = MultimodalRouter(deepseek_client=ds, mode=RouteMode.DEEPSEEK_ONLY)
        result = router.route_request(["a.txt"], "system", "分析案件")
        assert result.success is True
        assert result.deepseek_text_used is True
        assert result.mode_used == RouteMode.DEEPSEEK_ONLY

    def test_failure(self):
        ds = _mock_client(success=False)
        router = MultimodalRouter(deepseek_client=ds, mode=RouteMode.DEEPSEEK_ONLY)
        result = router.route_request(["a.txt"], "system", "text")
        assert result.success is False

    def test_not_configured(self):
        ds = _mock_client_not_configured()
        router = MultimodalRouter(deepseek_client=ds, mode=RouteMode.DEEPSEEK_ONLY)
        result = router.route_request([], "system", "text")
        assert result.success is False
        assert "未配置" in result.error

    def test_no_client(self):
        router = MultimodalRouter(deepseek_client=None, mode=RouteMode.DEEPSEEK_ONLY)
        result = router.route_request([], "system", "text")
        assert result.success is False


# ══════════════════════════════════════════════════════════════════════
# MultimodalRouter — MiMo only mode
# ══════════════════════════════════════════════════════════════════════
class TestRouterMimoOnly:
    def test_success(self):
        mm = _mock_client(success=True, content="MiMo回复")
        router = MultimodalRouter(mimo_client=mm, mode=RouteMode.MIMO_ONLY)
        result = router.route_request(["a.jpg"], "system", "分析图片")
        assert result.success is True
        assert result.mimo_multimodal_used is True
        assert result.mode_used == RouteMode.MIMO_ONLY

    def test_failure(self):
        mm = _mock_client(success=False)
        router = MultimodalRouter(mimo_client=mm, mode=RouteMode.MIMO_ONLY)
        result = router.route_request([], "system", "text")
        assert result.success is False

    def test_not_configured(self):
        mm = _mock_client_not_configured()
        router = MultimodalRouter(mimo_client=mm, mode=RouteMode.MIMO_ONLY)
        result = router.route_request([], "system", "text")
        assert result.success is False
        assert "未配置" in result.error


# ══════════════════════════════════════════════════════════════════════
# MultimodalRouter — Dual AI mode
# ══════════════════════════════════════════════════════════════════════
class TestRouterDualAI:
    def test_pure_text_goes_to_deepseek(self):
        ds = _mock_client(success=True, content="DeepSeek文本回复")
        mm = _mock_client(success=True, content="MiMo回复")
        router = MultimodalRouter(deepseek_client=ds, mimo_client=mm, mode=RouteMode.DUAL_AI)
        result = router.route_request(["a.txt", "b.pdf"], "system", "分析文本")
        assert result.success is True
        assert result.deepseek_text_used is True
        # MiMo should NOT be called for pure text
        mm.chat_multimodal.assert_not_called()

    def test_multimodal_mimo_then_deepseek(self, tmp_path):
        """Images → MiMo processes → DeepSeek generates final."""
        img = tmp_path / "evidence.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 10)

        ds = _mock_client(success=True, content="DeepSeek最终分析")
        mm = _mock_client(success=True, content="MiMo图片分析结果")
        router = MultimodalRouter(deepseek_client=ds, mimo_client=mm, mode=RouteMode.DUAL_AI)
        result = router.route_request([str(img)], "system", "分析证据图片")
        assert result.success is True
        assert result.mimo_multimodal_used is True
        assert result.deepseek_text_used is True

    def test_multimodal_mimo_fails(self, tmp_path):
        img = tmp_path / "evidence.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 10)

        ds = _mock_client(success=True)
        mm = _mock_client(success=False)
        router = MultimodalRouter(deepseek_client=ds, mimo_client=mm, mode=RouteMode.DUAL_AI)
        result = router.route_request([str(img)], "system", "分析")
        assert result.success is False
        assert "MiMo" in result.error

    def test_multimodal_deepseek_not_configured_returns_mimo(self, tmp_path):
        """When DeepSeek not configured, return MiMo result directly."""
        img = tmp_path / "evidence.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 10)

        ds = _mock_client_not_configured()
        mm = _mock_client(success=True, content="MiMo分析结果")
        router = MultimodalRouter(deepseek_client=ds, mimo_client=mm, mode=RouteMode.DUAL_AI)
        result = router.route_request([str(img)], "system", "分析")
        assert result.success is True
        assert result.mimo_multimodal_used is True
        assert result.deepseek_text_used is False

    def test_pure_text_deepseek_not_configured(self):
        ds = _mock_client_not_configured()
        mm = _mock_client()
        router = MultimodalRouter(deepseek_client=ds, mimo_client=mm, mode=RouteMode.DUAL_AI)
        result = router.route_request(["a.txt"], "system", "text")
        assert result.success is False
        assert "DeepSeek" in result.error

    def test_unknown_mode(self):
        router = MultimodalRouter(mode="unknown_mode")
        result = router.route_request([], "system", "text")
        assert result.success is False
        assert "Unknown" in result.error


# ══════════════════════════════════════════════════════════════════════
# MultimodalRouter — _build_enhanced_prompt
# ══════════════════════════════════════════════════════════════════════
class TestBuildEnhancedPrompt:
    def test_contains_original(self):
        router = MultimodalRouter()
        result = router._build_enhanced_prompt("原始提示", "多模态结果")
        assert "原始提示" in result
        assert "多模态结果" in result

    def test_contains_multimodal_context(self):
        router = MultimodalRouter()
        result = router._build_enhanced_prompt("提示", "图片分析内容")
        assert "图片分析内容" in result


# ══════════════════════════════════════════════════════════════════════
# get_file_summary
# ══════════════════════════════════════════════════════════════════════
class TestGetFileSummary:
    def test_empty(self):
        s = get_file_summary([])
        assert s["total"] == 0
        assert s["has_images"] is False
        assert s["has_audio"] is False

    def test_mixed_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("test", encoding="utf-8")
        (tmp_path / "b.jpg").write_bytes(b"fake")
        (tmp_path / "c.mp3").write_bytes(b"fake")
        s = get_file_summary([
            str(tmp_path / "a.txt"),
            str(tmp_path / "b.jpg"),
            str(tmp_path / "c.mp3"),
        ])
        assert s["total"] == 3
        assert s["text_count"] == 1
        assert s["image_count"] == 1
        assert s["audio_count"] == 1
        assert s["has_images"] is True
        assert s["has_audio"] is True

    def test_only_text(self, tmp_path):
        (tmp_path / "a.pdf").write_bytes(b"fake")
        s = get_file_summary([str(tmp_path / "a.pdf")])
        assert s["has_images"] is False
        assert s["has_audio"] is False


# ══════════════════════════════════════════════════════════════════════
# create_router_from_settings
# ══════════════════════════════════════════════════════════════════════
class TestCreateRouterFromSettings:
    def test_both_configured(self):
        with patch("core.settings_store.get_settings_store") as mock_store:
            mock_s = MagicMock()
            mock_s.deepseek.is_configured.return_value = True
            mock_s.deepseek.api_key = "ds_key"
            mock_s.deepseek.base_url = "https://api.deepseek.com"
            mock_s.deepseek.model_extract = "deepseek-chat"
            mock_s.mimo.is_configured.return_value = True
            mock_s.mimo.api_key = "mm_key"
            mock_s.mimo.base_url = "https://api.mimo.ai"
            mock_s.mimo.model = "mimo-v2.5-pro"
            mock_store.return_value.settings = mock_s

            router = create_router_from_settings()
            assert router.mode == RouteMode.DUAL_AI

    def test_only_deepseek(self):
        with patch("core.settings_store.get_settings_store") as mock_store:
            mock_s = MagicMock()
            mock_s.deepseek.is_configured.return_value = True
            mock_s.deepseek.api_key = "ds_key"
            mock_s.deepseek.base_url = "https://api.deepseek.com"
            mock_s.deepseek.model_extract = "deepseek-chat"
            mock_s.mimo.is_configured.return_value = False
            mock_store.return_value.settings = mock_s

            router = create_router_from_settings()
            assert router.mode == RouteMode.DEEPSEEK_ONLY

    def test_only_mimo(self):
        with patch("core.settings_store.get_settings_store") as mock_store:
            mock_s = MagicMock()
            mock_s.deepseek.is_configured.return_value = False
            mock_s.mimo.is_configured.return_value = True
            mock_s.mimo.api_key = "mm_key"
            mock_s.mimo.base_url = "https://api.mimo.ai"
            mock_s.mimo.model = "mimo-v2.5-pro"
            mock_store.return_value.settings = mock_s

            router = create_router_from_settings()
            assert router.mode == RouteMode.MIMO_ONLY

    def test_neither_configured(self):
        with patch("core.settings_store.get_settings_store") as mock_store:
            mock_s = MagicMock()
            mock_s.deepseek.is_configured.return_value = False
            mock_s.mimo.is_configured.return_value = False
            mock_store.return_value.settings = mock_s

            router = create_router_from_settings()
            assert router.mode == RouteMode.PREVIEW
