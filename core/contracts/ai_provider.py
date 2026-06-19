"""
core/contracts/ai_provider.py - Unified AI Provider Interface

All AI providers (DeepSeek, MiMo, Custom) must implement this interface.
Ensures consistent behavior across providers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class AIMode(Enum):
    """AI operation mode."""
    REAL_AI = "real_ai"              # All API calls successful
    MIXED = "mixed"                  # Some API calls failed
    LOCAL_FALLBACK = "local_fallback"  # No API calls, local rules only
    DUAL_AI = "dual_ai"              # Multiple providers used


@dataclass
class AIResponse:
    """Standardized AI response from any provider."""
    success: bool
    content: str
    provider: str = ""               # deepseek / mimo / custom
    model: str = ""                  # Model used
    latency_ms: int = 0              # Request latency
    token_usage: Optional[Dict[str, int]] = None  # prompt/completion/total
    error: Optional[str] = None      # Error message if failed
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "token_usage": self.token_usage,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class AIProvider(ABC):
    """Abstract base class for all AI providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'deepseek', 'mimo', 'custom')."""
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Whether the provider has valid credentials."""
        ...

    @abstractmethod
    def chat(self, system_prompt: str, user_content: str,
             model: Optional[str] = None, temperature: float = 0.3,
             max_tokens: int = 4096) -> AIResponse:
        """Send a chat completion request.

        Args:
            system_prompt: System message content.
            user_content: User message content.
            model: Model override (uses default if None).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            AIResponse with result or error.
        """
        ...

    @abstractmethod
    def test_connection(self) -> AIResponse:
        """Test API connectivity.

        Returns:
            AIResponse with success=True if connected.
        """
        ...

    def extract_facts(self, prompt: str, context: str) -> AIResponse:
        """Convenience method for fact extraction.

        Default implementation calls chat() directly.
        Override for provider-specific optimization.
        """
        return self.chat(system_prompt=prompt, user_content=context)

    def generate_strategy(self, prompt: str, context: str) -> AIResponse:
        """Convenience method for strategy generation.

        Default implementation calls chat() directly.
        Override for provider-specific optimization.
        """
        return self.chat(system_prompt=prompt, user_content=context)

    def critique(self, prompt: str, context: str) -> AIResponse:
        """Convenience method for critique/review.

        Default implementation calls chat() directly.
        Override for provider-specific optimization.
        """
        return self.chat(system_prompt=prompt, user_content=context)
