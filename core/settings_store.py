"""
core/settings_store.py - Persistent Settings Storage

Stores AI configuration (DeepSeek + MiMo) in local JSON file.
Supports masked key display and auto-trim.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# Settings file location
_SETTINGS_DIR = Path.home() / ".明证台"
_SETTINGS_FILE = _SETTINGS_DIR / "settings.json"


def _mask_key(key: str) -> str:
    """Mask API key for display: show first 6 + last 4 chars."""
    if not key or len(key) < 12:
        return "***" if key else ""
    return f"{key[:6]}...{key[-4:]}"


@dataclass
class DeepSeekSettings:
    """DeepSeek API configuration."""
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model_extract: str = "deepseek-chat"
    model_strategy: str = "deepseek-chat"
    timeout: int = 60

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    def masked_dict(self) -> dict:
        return {
            "api_key": _mask_key(self.api_key),
            "base_url": self.base_url,
            "model_extract": self.model_extract,
            "model_strategy": self.model_strategy,
            "timeout": self.timeout,
            "is_configured": self.is_configured(),
        }


@dataclass
class MiMoSettings:
    """MiMo API configuration."""
    api_key: str = ""
    base_url: str = "https://api.mimo.ai"
    model: str = "mimo-v2.5-pro"
    use_cases: list = field(default_factory=lambda: [
        "复核事实", "长上下文复核", "文书质量审校"
    ])
    timeout: int = 60

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    def masked_dict(self) -> dict:
        return {
            "api_key": _mask_key(self.api_key),
            "base_url": self.base_url,
            "model": self.model,
            "use_cases": self.use_cases,
            "timeout": self.timeout,
            "is_configured": self.is_configured(),
        }


@dataclass
class CustomSettings:
    """Custom model configuration."""
    api_key: str = ""
    base_url: str = ""
    model: str = ""

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())


@dataclass
class AISettings:
    """Complete AI settings."""
    work_mode: str = "基础预览"  # 基础预览 / DeepSeek单AI / MiMo单AI / DeepSeek+MiMo双AI
    deepseek: DeepSeekSettings = field(default_factory=DeepSeekSettings)
    mimo: MiMoSettings = field(default_factory=MiMoSettings)
    custom: CustomSettings = field(default_factory=CustomSettings)

    def get_ai_mode(self) -> str:
        """Determine AI mode from settings."""
        ds = self.deepseek.is_configured()
        mm = self.mimo.is_configured()
        if ds and mm:
            return "dual_ai"
        elif ds:
            return "deepseek_ai"
        elif mm:
            return "mimo_ai"
        else:
            return "local_fallback"

    def to_dict(self) -> dict:
        return {
            "work_mode": self.work_mode,
            "deepseek": self.deepseek.masked_dict(),
            "mimo": self.mimo.masked_dict(),
            "ai_mode": self.get_ai_mode(),
        }


class SettingsStore:
    """Persistent settings storage."""

    def __init__(self):
        self._settings = AISettings()
        self._load()

    def _load(self):
        """Load settings from file."""
        if not _SETTINGS_FILE.exists():
            return

        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Load work mode
            self._settings.work_mode = data.get("work_mode", "基础预览")

            # Load DeepSeek settings
            ds = data.get("deepseek", {})
            self._settings.deepseek = DeepSeekSettings(
                api_key=ds.get("api_key", "").strip(),
                base_url=ds.get("base_url", "https://api.deepseek.com").strip(),
                model_extract=ds.get("model_extract", "deepseek-chat").strip(),
                model_strategy=ds.get("model_strategy", "deepseek-chat").strip(),
                timeout=int(ds.get("timeout", 60)),
            )

            # Load MiMo settings
            mm = data.get("mimo", {})
            self._settings.mimo = MiMoSettings(
                api_key=mm.get("api_key", "").strip(),
                base_url=mm.get("base_url", "https://api.mimo.ai").strip(),
                model=mm.get("model", "mimo-v2.5-pro").strip(),
                use_cases=mm.get("use_cases", ["复核事实", "长上下文复核", "文书质量审校"]),
                timeout=int(mm.get("timeout", 60)),
            )

            # Load Custom model settings
            cm = data.get("custom", {})
            self._settings.custom = CustomSettings(
                api_key=cm.get("api_key", "").strip(),
                base_url=cm.get("base_url", "").strip(),
                model=cm.get("model", "").strip(),
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Failed to load settings: %s", e)

    def save(self):
        """Save settings to file."""
        _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

        data = {
            "work_mode": self._settings.work_mode,
            "deepseek": {
                "api_key": self._settings.deepseek.api_key.strip(),
                "base_url": self._settings.deepseek.base_url.strip(),
                "model_extract": self._settings.deepseek.model_extract.strip(),
                "model_strategy": self._settings.deepseek.model_strategy.strip(),
                "timeout": self._settings.deepseek.timeout,
            },
            "mimo": {
                "api_key": self._settings.mimo.api_key.strip(),
                "base_url": self._settings.mimo.base_url.strip(),
                "model": self._settings.mimo.model.strip(),
                "use_cases": self._settings.mimo.use_cases,
                "timeout": self._settings.mimo.timeout,
            },
            "custom": {
                "api_key": self._settings.custom.api_key.strip(),
                "base_url": self._settings.custom.base_url.strip(),
                "model": self._settings.custom.model.strip(),
            },
        }

        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @property
    def settings(self) -> AISettings:
        return self._settings

    def update_deepseek(self, api_key: str = None, base_url: str = None,
                        model_extract: str = None, model_strategy: str = None,
                        timeout: int = None):
        """Update DeepSeek settings."""
        if api_key is not None:
            self._settings.deepseek.api_key = api_key.strip()
        if base_url is not None:
            self._settings.deepseek.base_url = base_url.strip()
        if model_extract is not None:
            self._settings.deepseek.model_extract = model_extract.strip()
        if model_strategy is not None:
            self._settings.deepseek.model_strategy = model_strategy.strip()
        if timeout is not None:
            self._settings.deepseek.timeout = timeout

    def update_mimo(self, api_key: str = None, base_url: str = None,
                    model: str = None, use_cases: list = None,
                    timeout: int = None):
        """Update MiMo settings."""
        if api_key is not None:
            self._settings.mimo.api_key = api_key.strip()
        if base_url is not None:
            self._settings.mimo.base_url = base_url.strip()
        if model is not None:
            self._settings.mimo.model = model.strip()
        if use_cases is not None:
            self._settings.mimo.use_cases = use_cases
        if timeout is not None:
            self._settings.mimo.timeout = timeout

    def update_custom(self, api_key: str = None, base_url: str = None, model: str = None):
        """Update Custom model settings."""
        if api_key is not None:
            self._settings.custom.api_key = api_key.strip()
        if base_url is not None:
            self._settings.custom.base_url = base_url.strip()
        if model is not None:
            self._settings.custom.model = model.strip()

    def set_work_mode(self, mode: str):
        """Set work mode."""
        self._settings.work_mode = mode

    def get_status_label(self) -> str:
        """Get human-readable status label."""
        ds = self._settings.deepseek.is_configured()
        mm = self._settings.mimo.is_configured()
        if ds and mm:
            return "AI 深度分析：双 AI 已启用"
        elif ds:
            return "AI 深度分析：DeepSeek 已启用"
        elif mm:
            return "AI 深度分析：MiMo 已启用"
        else:
            return "当前仅基础预览，不能正式交付"


# Singleton
_store: Optional[SettingsStore] = None


def get_settings_store() -> SettingsStore:
    """Get singleton settings store."""
    global _store
    if _store is None:
        _store = SettingsStore()
    return _store
