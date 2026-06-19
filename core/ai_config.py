"""
core/ai_config.py - AI Configuration Module

Manages AI API configuration for DeepSeek integration.
Reads from environment variables and provides configuration status.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AIConfig:
    """AI API configuration."""
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model_extract: str = "deepseek-chat"
    model_strategy: str = "deepseek-chat"
    timeout: int = 60
    
    @property
    def is_configured(self) -> bool:
        """Check if API is configured."""
        return bool(self.api_key)
    
    def to_dict(self) -> dict:
        """Convert to dictionary (masking API key)."""
        return {
            "api_key": f"{self.api_key[:8]}..." if self.api_key else "",
            "base_url": self.base_url,
            "model_extract": self.model_extract,
            "model_strategy": self.model_strategy,
            "timeout": self.timeout,
            "is_configured": self.is_configured,
        }


def get_ai_config() -> AIConfig:
    """Get AI configuration from environment variables.
    
    Environment variables:
        DEEPSEEK_API_KEY: API key for DeepSeek
        DEEPSEEK_BASE_URL: Base URL for API (default: https://api.deepseek.com)
        DEEPSEEK_MODEL_EXTRACT: Model for fact extraction (default: deepseek-chat)
        DEEPSEEK_MODEL_STRATEGY: Model for strategy generation (default: deepseek-chat)
        DEEPSEEK_TIMEOUT: Request timeout in seconds (default: 60)
    
    Returns:
        AIConfig instance with configuration from environment.
    """
    return AIConfig(
        api_key=os.environ.get("DEEPSEEK_API_KEY", "").strip(),
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
        model_extract=os.environ.get("DEEPSEEK_MODEL_EXTRACT", "deepseek-chat").strip(),
        model_strategy=os.environ.get("DEEPSEEK_MODEL_STRATEGY", "deepseek-chat").strip(),
        timeout=int(os.environ.get("DEEPSEEK_TIMEOUT", "60")),
    )


def is_api_configured() -> bool:
    """Check if API is configured."""
    return get_ai_config().is_configured


def get_api_status() -> str:
    """Get API configuration status.
    
    Returns:
        Status string: 'not_configured', 'configured', or 'error'
    """
    config = get_ai_config()
    if not config.api_key:
        return "not_configured"
    return "configured"
