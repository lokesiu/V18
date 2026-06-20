"""TDD tests for deepseek_client, mimo_client, multimodal HTTP paths."""
import pytest
import sys, os, base64
from unittest.mock import patch, MagicMock
sys.path.insert(0, ".")

from core.ai.deepseek_client import DeepSeekClient, APIResponse as DSResponse
from core.ai.mimo_client import MiMoClient, APIResponse as MiMoResponse


# ══════════════════════════════════════════════════════════════════════
# DeepSeekClient._call — mock HTTP
# ══════════════════════════════════════════════════════════════════════
class TestDeepSeekClientCall:
    @patch("httpx.Client")
    def test_call_success(self, MockHttpx):
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

        client = DeepSeekClient(api_key="test_key")
        resp = client.extract_facts("system prompt", "user content")
        assert resp.success is True
        assert resp.content == "回复内容"
        assert resp.model == "deepseek-chat"

    @patch("httpx.Client")
    def test_call_timeout(self, MockHttpx):
        import httpx
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.TimeoutException("timeout")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        MockHttpx.return_value = mock_client

        client = DeepSeekClient(api_key="test_key")
        resp = client.extract_facts("system", "user")
        assert resp.success is False
        assert "timeout" in resp.error.lower()

    @patch("httpx.Client")
    def test_call_http_error(self, MockHttpx):
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

        client = DeepSeekClient(api_key="test_key")
        resp = client.extract_facts("system", "user")
        assert resp.success is False
        assert "429" in resp.error

    @patch("httpx.Client")
    def test_call_generic_exception(self, MockHttpx):
        mock_client = MagicMock()
        mock_client.post.side_effect = ConnectionError("network error")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        MockHttpx.return_value = mock_client

        client = DeepSeekClient(api_key="test_key")
        resp = client.extract_facts("system", "user")
        assert resp.success is False

    def test_call_no_api_key(self):
        client = DeepSeekClient(api_key="")
        resp = client.extract_facts("system", "user")
        assert resp.success is False

    def test_generate_strategy_success(self):
        with patch("httpx.Client") as MockHttpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "策略内容"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            }
            mock_resp.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.post.return_value = mock_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockHttpx.return_value = mock_client

            client = DeepSeekClient(api_key="key")
            resp = client.generate_strategy("system", "user")
            assert resp.success is True
            assert resp.model == "deepseek-chat"


# ══════════════════════════════════════════════════════════════════════
# MiMoClient._call — mock HTTP
# ══════════════════════════════════════════════════════════════════════
class TestMiMoClientCall:
    @patch("httpx.Client")
    def test_call_success(self, MockHttpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "MiMo回复"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        MockHttpx.return_value = mock_client

        client = MiMoClient(api_key="test_key")
        resp = client.critique_facts('{"key_facts":[]}', "原始文本")
        assert resp.success is True
        assert resp.content == "MiMo回复"

    @patch("httpx.Client")
    def test_call_timeout(self, MockHttpx):
        import httpx
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.TimeoutException("timeout")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        MockHttpx.return_value = mock_client

        client = MiMoClient(api_key="test_key")
        resp = client.critique_facts("{}", "text")
        assert resp.success is False

    @patch("httpx.Client")
    def test_call_http_error(self, MockHttpx):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Server error"
        http_err = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_resp)

        mock_client = MagicMock()
        mock_client.post.side_effect = http_err
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        MockHttpx.return_value = mock_client

        client = MiMoClient(api_key="test_key")
        resp = client.review_strategy("{}", "{}")
        assert resp.success is False

    def test_call_no_api_key(self):
        client = MiMoClient(api_key="")
        resp = client.critique_facts("{}", "text")
        assert resp.success is False

    def test_review_strategy_success(self):
        with patch("httpx.Client") as MockHttpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "审校结果"}}],
                "usage": {},
            }
            mock_resp.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.post.return_value = mock_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockHttpx.return_value = mock_client

            client = MiMoClient(api_key="key")
            resp = client.review_strategy("{}", "{}")
            assert resp.success is True


# ══════════════════════════════════════════════════════════════════════
# multimodal.py — uncovered functions
# ══════════════════════════════════════════════════════════════════════
class TestMultimodalFunctions:
    def test_get_file_summary(self):
        from core.ai.multimodal import get_file_summary
        s = get_file_summary([])
        assert s["total"] == 0
        assert s["has_images"] is False

    def test_classify_files_mixed(self, tmp_path):
        from core.ai.multimodal import classify_files, FileCategory
        (tmp_path / "a.txt").write_text("test", encoding="utf-8")
        (tmp_path / "b.jpg").write_bytes(b"fake")
        (tmp_path / "c.mp3").write_bytes(b"fake")
        result = classify_files([
            str(tmp_path / "a.txt"),
            str(tmp_path / "b.jpg"),
            str(tmp_path / "c.mp3"),
        ])
        assert len(result[FileCategory.TEXT]) == 1
        assert len(result[FileCategory.IMAGE]) == 1
        assert len(result[FileCategory.AUDIO]) == 1

    def test_encode_image_base64_bmp(self, tmp_path):
        from core.ai.multimodal import encode_image_base64
        img = tmp_path / "test.bmp"
        img.write_bytes(b"BM" + b"\x00" * 100)
        result = encode_image_base64(str(img))
        assert result is not None
        assert "image/bmp" in result

    def test_encode_image_base64_tiff(self, tmp_path):
        from core.ai.multimodal import encode_image_base64
        img = tmp_path / "test.tiff"
        img.write_bytes(b"II" + b"\x00" * 100)
        result = encode_image_base64(str(img))
        assert result is not None
        assert "image/tiff" in result

    def test_build_vision_message_multiple_images(self, tmp_path):
        from core.ai.multimodal import build_vision_message
        for i in range(3):
            (tmp_path / f"img{i}.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 10)
        paths = [str(tmp_path / f"img{i}.jpg") for i in range(3)]
        msg = build_vision_message(paths, "分析图片")
        assert len(msg["content"]) >= 4  # text + 3 images

    def test_build_multimodal_messages_text_only(self):
        from core.ai.multimodal import build_multimodal_messages
        msgs = build_multimodal_messages("律师", "文本", image_paths=None)
        assert len(msgs) == 2

    def test_build_multimodal_messages_empty_images(self):
        from core.ai.multimodal import build_multimodal_messages
        msgs = build_multimodal_messages("律师", "文本", image_paths=[])
        assert len(msgs) == 2


# ══════════════════════════════════════════════════════════════════════
# MultiProviderClient
# ══════════════════════════════════════════════════════════════════════
class TestMultiProviderClient:
    def test_add_and_get_provider(self):
        from core.ai.unified_client import MultiProviderClient, UnifiedAIClient, ProviderConfig
        client = MultiProviderClient()
        provider = UnifiedAIClient(ProviderConfig(name="test", api_key="key", base_url="http://api.com", model="m"))
        client.add_provider(provider)
        assert client.get_provider("test") is provider
        assert client.get_provider("nonexistent") is None

    def test_get_available(self):
        from core.ai.unified_client import MultiProviderClient, UnifiedAIClient, ProviderConfig
        client = MultiProviderClient()
        p1 = UnifiedAIClient(ProviderConfig(name="p1", api_key="key", base_url="http://api.com", model="m"))
        p2 = UnifiedAIClient(ProviderConfig(name="p2", api_key="", base_url="http://api.com", model="m"))
        client.add_provider(p1)
        client.add_provider(p2)
        available = client.get_available()
        assert "p1" in available
        assert "p2" not in available

    def test_call_specific_provider(self):
        from core.ai.unified_client import MultiProviderClient, UnifiedAIClient, ProviderConfig
        from core.contracts.ai_provider import AIResponse

        client = MultiProviderClient()
        provider = MagicMock()
        provider.name = "test"
        provider.is_configured = True
        provider.chat.return_value = AIResponse(success=True, content="ok", latency_ms=10)
        client.add_provider(provider)

        resp = client.call("test", "system", "user")
        assert resp.success is True

    def test_call_provider_not_found(self):
        from core.ai.unified_client import MultiProviderClient
        client = MultiProviderClient()
        resp = client.call("nonexistent", "system", "user")
        assert resp.success is False
        assert "not found" in resp.error

    def test_call_any_with_preferred(self):
        from core.ai.unified_client import MultiProviderClient, UnifiedAIClient, ProviderConfig
        from core.contracts.ai_provider import AIResponse

        client = MultiProviderClient()
        p1 = MagicMock()
        p1.name = "preferred"
        p1.is_configured = True
        p1.chat.return_value = AIResponse(success=True, content="preferred reply", latency_ms=10)
        client.add_provider(p1)

        resp = client.call_any("system", "user", preferred="preferred")
        assert resp.success is True

    def test_call_any_fallback(self):
        from core.ai.unified_client import MultiProviderClient
        from core.contracts.ai_provider import AIResponse

        client = MultiProviderClient()
        p1 = MagicMock()
        p1.name = "p1"
        p1.is_configured = True
        p1.chat.return_value = AIResponse(success=True, content="p1 reply", latency_ms=10)
        client.add_provider(p1)

        resp = client.call_any("system", "user")
        assert resp.success is True

    def test_call_any_no_providers(self):
        from core.ai.unified_client import MultiProviderClient
        client = MultiProviderClient()
        resp = client.call_any("system", "user")
        assert resp.success is False

    def test_get_ai_mode(self):
        from core.ai.unified_client import MultiProviderClient, UnifiedAIClient, ProviderConfig
        client = MultiProviderClient()
        assert client.get_ai_mode() == "local_fallback"

        p1 = UnifiedAIClient(ProviderConfig(name="p1", api_key="key", base_url="http://api.com", model="m"))
        client.add_provider(p1)
        assert "ai" in client.get_ai_mode()

    def test_get_multi_provider_client_singleton(self):
        from core.ai.unified_client import get_multi_provider_client
        c1 = get_multi_provider_client()
        c2 = get_multi_provider_client()
        assert c1 is c2

    def test_chat_multimodal_not_configured(self):
        from core.ai.unified_client import UnifiedAIClient, ProviderConfig
        client = UnifiedAIClient(ProviderConfig(api_key=""))
        resp = client.chat_multimodal(file_paths=[], system_prompt="s", text_prompt="t")
        assert resp.success is False


# ══════════════════════════════════════════════════════════════════════
# MultimodalRequestBuilder
# ══════════════════════════════════════════════════════════════════════
class TestMultimodalRequestBuilder:
    def test_text_only(self, tmp_path):
        from core.ai.multimodal import MultimodalRequestBuilder
        txt = tmp_path / "doc.txt"
        txt.write_text("文档内容", encoding="utf-8")
        builder = MultimodalRequestBuilder(api_key="key", base_url="http://api.com", model="m")
        messages, model = builder.build_request(
            file_paths=[str(txt)],
            system_prompt="律师",
            text_prompt="分析",
        )
        assert len(messages) >= 2
        assert model == "m"

    def test_with_images(self, tmp_path):
        from core.ai.multimodal import MultimodalRequestBuilder
        img = tmp_path / "evidence.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 10)
        builder = MultimodalRequestBuilder(api_key="key", base_url="http://api.com", model="m")
        messages, model = builder.build_request(
            file_paths=[str(img)],
            system_prompt="律师",
            text_prompt="分析图片",
        )
        assert len(messages) >= 2

    def test_empty_files(self):
        from core.ai.multimodal import MultimodalRequestBuilder
        builder = MultimodalRequestBuilder(api_key="key", base_url="http://api.com", model="m")
        messages, model = builder.build_request(
            file_paths=[],
            system_prompt="律师",
            text_prompt="分析",
        )
        assert len(messages) == 2

    def test_extract_text_content(self, tmp_path):
        from core.ai.multimodal import MultimodalRequestBuilder
        txt = tmp_path / "a.txt"
        txt.write_text("内容ABC", encoding="utf-8")
        builder = MultimodalRequestBuilder(api_key="key", base_url="http://api.com", model="m")
        result = builder._extract_text_content([str(txt)])
        assert "内容ABC" in result

    def test_extract_text_content_empty(self):
        from core.ai.multimodal import MultimodalRequestBuilder
        builder = MultimodalRequestBuilder(api_key="key", base_url="http://api.com", model="m")
        result = builder._extract_text_content([])
        assert result == ""


# ══════════════════════════════════════════════════════════════════════
# AudioTranscriber
# ══════════════════════════════════════════════════════════════════════
class TestAudioTranscriber:
    def test_transcribe_nonexistent(self):
        from core.ai.multimodal import AudioTranscriber
        t = AudioTranscriber(api_key="key", base_url="http://api.com", model="m")
        result = t.transcribe("/nonexistent/audio.mp3")
        assert result is None

    def test_transcribe_empty_api_key(self, tmp_path):
        from core.ai.multimodal import AudioTranscriber
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"fake audio")
        t = AudioTranscriber(api_key="", base_url="http://api.com", model="m")
        # Should fail gracefully
        result = t.transcribe(str(audio))
        assert result is None or isinstance(result, str)


# ══════════════════════════════════════════════════════════════════════
# transcribe_audio_files
# ══════════════════════════════════════════════════════════════════════
class TestTranscribeAudioFiles:
    def test_empty_list(self):
        from core.ai.multimodal import transcribe_audio_files
        result = transcribe_audio_files([], "key", "http://api.com")
        assert result == ""
