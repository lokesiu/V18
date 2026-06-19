"""
core/ai/provider_registry.py - AI Provider Registry

Manages DeepSeek and MiMo clients, provides unified access.
"""
from __future__ import annotations

from typing import Optional

from core.settings_store import get_settings_store, AISettings
from core.ai.deepseek_client import DeepSeekClient
from core.ai.mimo_client import MiMoClient


class ProviderRegistry:
    """Registry managing AI providers."""

    def __init__(self):
        self._deepseek: Optional[DeepSeekClient] = None
        self._mimo: Optional[MiMoClient] = None
        self._reload()

    def _reload(self):
        """Reload clients from settings."""
        store = get_settings_store()
        s = store.settings

        # DeepSeek
        if s.deepseek.is_configured():
            self._deepseek = DeepSeekClient(
                api_key=s.deepseek.api_key,
                base_url=s.deepseek.base_url,
                model_extract=s.deepseek.model_extract,
                model_strategy=s.deepseek.model_strategy,
                timeout=s.deepseek.timeout,
            )
        else:
            self._deepseek = None

        # MiMo
        if s.mimo.is_configured():
            self._mimo = MiMoClient(
                api_key=s.mimo.api_key,
                base_url=s.mimo.base_url,
                model=s.mimo.model,
                timeout=s.mimo.timeout,
            )
        else:
            self._mimo = None

    def refresh(self):
        """Refresh clients (call after settings change)."""
        self._reload()

    @property
    def deepseek(self) -> Optional[DeepSeekClient]:
        return self._deepseek

    @property
    def mimo(self) -> Optional[MiMoClient]:
        return self._mimo

    def get_ai_mode(self) -> str:
        """Get current AI mode."""
        ds = self._deepseek is not None and self._deepseek.is_configured
        mm = self._mimo is not None and self._mimo.is_configured
        if ds and mm:
            return "dual_ai"
        elif ds:
            return "deepseek_ai"
        elif mm:
            return "mimo_ai"
        else:
            return "local_fallback"

    def is_dual_ai_available(self) -> bool:
        """Check if both providers are available."""
        return self.get_ai_mode() == "dual_ai"


# Singleton
_registry: Optional[ProviderRegistry] = None


def get_provider_registry() -> ProviderRegistry:
    """Get singleton provider registry."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
