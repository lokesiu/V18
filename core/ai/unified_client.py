"""
core/ai/unified_client.py - Unified OpenAI-Compatible Client

Single client interface for ALL AI providers (DeepSeek, MiMo, Custom).
Replaces separate DeepSeekClient and MiMoClient with unified interface.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

import httpx

from core.contracts.ai_provider import AIProvider, AIResponse, AIMode

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""
    name: str = ""                   # deepseek / mimo / custom
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    timeout: int = 60
    temperature: float = 0.3
    max_tokens: int = 4096

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    def masked_dict(self) -> dict:
        return {
            "name": self.name,
            "api_key": f"{self.api_key[:6]}...{self.api_key[-4:]}" if len(self.api_key) > 10 else "***",
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
            "is_configured": self.is_configured(),
        }


class UnifiedAIClient(AIProvider):
    """Unified OpenAI-compatible client for all providers.

    Usage:
        client = UnifiedAIClient(ProviderConfig(
            name="deepseek",
            api_key="sk-...",
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
        ))
        response = client.chat("You are a lawyer", "Analyze this case...")
    """

    def __init__(self, config: ProviderConfig):
        self._config = config
        # Auto-strip keys
        self._config.api_key = config.api_key.strip()
        base = config.base_url.strip().rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        self._config.base_url = base
        self._config.model = config.model.strip()

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def is_configured(self) -> bool:
        return self._config.is_configured()

    @property
    def config(self) -> ProviderConfig:
        return self._config

    def chat(self, system_prompt: str, user_content: str,
             model: Optional[str] = None, temperature: float = 0.3,
             max_tokens: int = 4096) -> AIResponse:
        """Send chat completion request to OpenAI-compatible endpoint."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        return self.chat_messages(messages, model, temperature, max_tokens)

    def chat_messages(self, messages: list[dict],
                      model: Optional[str] = None, temperature: float = 0.3,
                      max_tokens: int = 4096) -> AIResponse:
        """Send chat completion with pre-built messages (supports multimodal).

        Args:
            messages: OpenAI format message list (can contain image_url content)
            model: Model override
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
        """
        if not self.is_configured:
            return AIResponse(
                success=False,
                content="",
                provider=self.name,
                error="API key not configured",
            )

        use_model = model or self._config.model
        start = time.time()

        try:
            url = f"{self._config.base_url}/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": use_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            with httpx.Client(timeout=self._config.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            latency = int((time.time() - start) * 1000)

            logger.info(
                "AI call successful: provider=%s, model=%s, latency=%dms, tokens=%d",
                self.name, use_model, latency, usage.get("total_tokens", 0),
            )

            return AIResponse(
                success=True,
                content=content,
                provider=self.name,
                model=use_model,
                latency_ms=latency,
                token_usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            )

        except httpx.TimeoutException:
            latency = int((time.time() - start) * 1000)
            logger.warning("AI call timeout: provider=%s, model=%s", self.name, use_model)
            return AIResponse(
                success=False, content="", provider=self.name,
                model=use_model, latency_ms=latency, error="Request timeout",
            )
        except httpx.HTTPStatusError as e:
            latency = int((time.time() - start) * 1000)
            logger.warning("AI call HTTP error: provider=%s, status=%d", self.name, e.response.status_code)
            return AIResponse(
                success=False, content="", provider=self.name,
                model=use_model, latency_ms=latency,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.warning("AI call failed: provider=%s, error=%s", self.name, str(e))
            return AIResponse(
                success=False, content="", provider=self.name,
                model=use_model, latency_ms=latency, error=str(e),
            )

    def chat_multimodal(self, file_paths: list[str],
                        system_prompt: str, text_prompt: str,
                        image_prompt: str = "请分析这些证据图片的内容，提取关键法律信息。",
                        **kwargs) -> AIResponse:
        """Chat with multimodal content (images, audio, text files).

        Args:
            file_paths: List of file paths to process
            system_prompt: System prompt
            text_prompt: Text analysis prompt
            image_prompt: Image analysis prompt
            **kwargs: Additional args passed to chat_messages
        """
        from core.ai.multimodal import MultimodalRequestBuilder

        builder = MultimodalRequestBuilder(
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            model=self._config.model,
        )

        messages, model = builder.build_request(
            file_paths=file_paths,
            system_prompt=system_prompt,
            text_prompt=text_prompt,
            image_prompt=image_prompt,
        )

        return self.chat_messages(messages, model=model, **kwargs)

    def test_connection(self) -> AIResponse:
        """Test API connectivity."""
        return self.chat("Reply with 'OK'", "Test connection")


class MultiProviderClient:
    """Manages multiple AI providers with unified access.

    Usage:
        client = MultiProviderClient()
        client.add_provider(UnifiedAIClient(ProviderConfig(name="deepseek", ...)))
        client.add_provider(UnifiedAIClient(ProviderConfig(name="mimo", ...)))

        # Use specific provider
        response = client.call("deepseek", "system", "user")

        # Use any available provider
        response = client.call_any("system", "user")
    """

    def __init__(self):
        self._providers: Dict[str, UnifiedAIClient] = {}

    def add_provider(self, provider: UnifiedAIClient):
        """Add a provider."""
        self._providers[provider.name] = provider

    def get_provider(self, name: str) -> Optional[UnifiedAIClient]:
        """Get provider by name."""
        return self._providers.get(name)

    def get_available(self) -> List[str]:
        """Get names of configured providers."""
        return [
            name for name, p in self._providers.items()
            if p.is_configured
        ]

    def call(self, provider_name: str, system_prompt: str,
             user_content: str, **kwargs) -> AIResponse:
        """Call specific provider."""
        provider = self._providers.get(provider_name)
        if not provider:
            return AIResponse(
                success=False, content="",
                error=f"Provider '{provider_name}' not found",
            )
        return provider.chat(system_prompt, user_content, **kwargs)

    def call_any(self, system_prompt: str, user_content: str,
                 preferred: Optional[str] = None, **kwargs) -> AIResponse:
        """Call any available provider (preferred first)."""
        # Try preferred first
        if preferred and preferred in self._providers:
            provider = self._providers[preferred]
            if provider.is_configured:
                response = provider.chat(system_prompt, user_content, **kwargs)
                if response.success:
                    return response

        # Try all available
        for name, provider in self._providers.items():
            if name == preferred:
                continue  # Already tried
            if provider.is_configured:
                response = provider.chat(system_prompt, user_content, **kwargs)
                if response.success:
                    return response

        return AIResponse(
            success=False, content="",
            error="No configured providers available",
        )

    def get_ai_mode(self) -> str:
        """Get current AI mode based on configured providers."""
        available = self.get_available()
        if len(available) >= 2:
            return "dual_ai"
        elif len(available) == 1:
            return f"{available[0]}_ai"
        else:
            return "local_fallback"


# Singleton
_client: Optional[MultiProviderClient] = None


def get_multi_provider_client() -> MultiProviderClient:
    """Get singleton multi-provider client."""
    global _client
    if _client is None:
        _client = MultiProviderClient()
        # Auto-configure from settings
        _auto_configure(_client)
    return _client


def _auto_configure(client: MultiProviderClient):
    """Auto-configure providers from settings store."""
    try:
        from core.settings_store import get_settings_store
        store = get_settings_store()
        s = store.settings

        # DeepSeek
        if s.deepseek.is_configured():
            client.add_provider(UnifiedAIClient(ProviderConfig(
                name="deepseek",
                api_key=s.deepseek.api_key,
                base_url=s.deepseek.base_url,
                model=s.deepseek.model_extract,
                timeout=s.deepseek.timeout,
            )))

        # MiMo
        if s.mimo.is_configured():
            client.add_provider(UnifiedAIClient(ProviderConfig(
                name="mimo",
                api_key=s.mimo.api_key,
                base_url=s.mimo.base_url,
                model=s.mimo.model,
                timeout=s.mimo.timeout,
            )))
    except Exception as e:
        logger.warning("Failed to auto-configure providers: %s", e)
