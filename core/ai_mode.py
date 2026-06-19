"""
core/ai_mode.py - AI Mode Tracking Module

Tracks whether the system is using real AI or local fallback.
Provides mode tracking for pipeline runs.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AIMode(Enum):
    """AI operation mode."""
    REAL_AI = "real_ai"          # All API calls successful
    MIXED = "mixed"              # Some API calls failed, some succeeded
    LOCAL_FALLBACK = "local_fallback"  # No API calls, using local rules


class AIStatus(Enum):
    """API configuration status."""
    NOT_CONFIGURED = "not_configured"      # No API key
    CONFIGURED_NOT_TESTED = "configured_not_tested"  # API key exists but not tested
    AVAILABLE = "available"                # API tested and working
    FAILED = "failed"                      # API test failed


@dataclass
class AIModeTracker:
    """Tracks AI mode for a pipeline run."""
    
    # Configuration
    ai_mode: AIMode = AIMode.LOCAL_FALLBACK
    api_a_status: AIStatus = AIStatus.NOT_CONFIGURED
    api_b_status: AIStatus = AIStatus.NOT_CONFIGURED
    
    # Timing
    api_a_latency_ms: int = 0
    api_b_latency_ms: int = 0
    
    # Model info
    model_name: str = ""
    prompt_version: str = "v1"
    
    # Token usage (if available)
    token_usage: Optional[dict] = None
    
    # Timestamps
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    def start_api_a(self):
        """Mark API-A call start."""
        self._api_a_start = datetime.now()
    
    def end_api_a(self, success: bool, latency_ms: int = 0):
        """Mark API-A call end."""
        self.api_a_latency_ms = latency_ms
        if success:
            self.api_a_status = AIStatus.AVAILABLE
        else:
            self.api_a_status = AIStatus.FAILED
        self._update_mode()
    
    def start_api_b(self):
        """Mark API-B call start."""
        self._api_b_start = datetime.now()
    
    def end_api_b(self, success: bool, latency_ms: int = 0):
        """Mark API-B call end."""
        self.api_b_latency_ms = latency_ms
        if success:
            self.api_b_status = AIStatus.AVAILABLE
        else:
            self.api_b_status = AIStatus.FAILED
        self._update_mode()
    
    def _update_mode(self):
        """Update AI mode based on API statuses."""
        a_ok = self.api_a_status == AIStatus.AVAILABLE
        b_ok = self.api_b_status == AIStatus.AVAILABLE
        
        if a_ok and b_ok:
            self.ai_mode = AIMode.REAL_AI
        elif a_ok or b_ok:
            self.ai_mode = AIMode.MIXED
        else:
            self.ai_mode = AIMode.LOCAL_FALLBACK
    
    def finish(self):
        """Mark pipeline run as finished."""
        self.end_time = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for manifest."""
        return {
            "ai_mode": self.ai_mode.value,
            "api_a_status": self.api_a_status.value,
            "api_b_status": self.api_b_status.value,
            "api_a_latency_ms": self.api_a_latency_ms,
            "api_b_latency_ms": self.api_b_latency_ms,
            "model_name": self.model_name,
            "prompt_version": self.prompt_version,
            "token_usage": self.token_usage,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }
    
    def save_manifest(self, output_dir: str):
        """Save ai_run_manifest.json to _internal subdirectory."""
        internal_dir = os.path.join(output_dir, "_internal")
        manifest_path = os.path.join(internal_dir, "ai_run_manifest.json")
        os.makedirs(internal_dir, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


def get_ai_mode_label(mode: AIMode) -> str:
    """Get human-readable label for AI mode."""
    labels = {
        AIMode.REAL_AI: "AI 深度分析",
        AIMode.MIXED: "混合模式",
        AIMode.LOCAL_FALLBACK: "基础预览",
    }
    return labels.get(mode, "未知")


def get_ai_mode_description(mode: AIMode) -> str:
    """Get description for AI mode."""
    descriptions = {
        AIMode.REAL_AI: "已启用 AI 深度分析",
        AIMode.MIXED: "部分功能使用 AI，部分使用本地规则",
        AIMode.LOCAL_FALLBACK: "未配置 API，当前仅可基础预览",
    }
    return descriptions.get(mode, "未知模式")
