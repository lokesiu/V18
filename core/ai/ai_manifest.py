"""
core/ai/ai_manifest.py - Dual AI Manifest Tracking

Enhanced manifest tracking for dual AI pipeline runs.
Tracks 4 API stages: deepseek_extract, mimo_critique, deepseek_strategy, mimo_review.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class StageRecord:
    """Record for a single API stage."""
    status: str = "pending"  # pending / running / success / failed / skipped
    latency_ms: int = 0
    model_name: str = ""
    token_usage: Optional[dict] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "latency_ms": self.latency_ms,
            "model_name": self.model_name,
            "token_usage": self.token_usage,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


@dataclass
class DualAIManifest:
    """Manifest tracking dual AI pipeline execution."""

    # Overall mode
    ai_mode: str = "local_fallback"

    # Stage records
    deepseek_extract: StageRecord = field(default_factory=StageRecord)
    mimo_critique: StageRecord = field(default_factory=StageRecord)
    deepseek_strategy: StageRecord = field(default_factory=StageRecord)
    mimo_review: StageRecord = field(default_factory=StageRecord)

    # Timing
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    def start_stage(self, stage: str):
        """Mark stage as started."""
        record = self._get_stage(stage)
        if record:
            record.status = "running"
            record.start_time = datetime.now()

    def end_stage(self, stage: str, success: bool, latency_ms: int = 0,
                  model_name: str = "", token_usage: Optional[dict] = None,
                  error: Optional[str] = None):
        """Mark stage as completed."""
        record = self._get_stage(stage)
        if record:
            record.status = "success" if success else "failed"
            record.latency_ms = latency_ms
            record.model_name = model_name
            record.token_usage = token_usage
            record.error = error
            record.end_time = datetime.now()
        self._update_mode()

    def skip_stage(self, stage: str, reason: str = ""):
        """Mark stage as skipped."""
        record = self._get_stage(stage)
        if record:
            record.status = "skipped"
            record.error = reason or "Provider not configured"

    def _get_stage(self, stage: str) -> Optional[StageRecord]:
        """Get stage record by name."""
        stages = {
            "deepseek_extract": self.deepseek_extract,
            "mimo_critique": self.mimo_critique,
            "deepseek_strategy": self.deepseek_strategy,
            "mimo_review": self.mimo_review,
        }
        return stages.get(stage)

    def _update_mode(self):
        """Update overall AI mode based on stage statuses."""
        ds_ok = self.deepseek_extract.status == "success"
        mm_ok = self.mimo_critique.status == "success"
        ds_strat = self.deepseek_strategy.status == "success"
        mm_rev = self.mimo_review.status == "success"

        if ds_ok and mm_ok and ds_strat and mm_rev:
            self.ai_mode = "dual_ai"
        elif ds_ok and ds_strat:
            self.ai_mode = "deepseek_ai"
        elif mm_ok and mm_rev:
            self.ai_mode = "mimo_ai"
        elif ds_ok or mm_ok or ds_strat or mm_rev:
            self.ai_mode = "mixed"
        else:
            self.ai_mode = "local_fallback"

    def finish(self):
        """Mark manifest as finished."""
        self.end_time = datetime.now()
        self._update_mode()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "ai_mode": self.ai_mode,
            "deepseek_extract_status": self.deepseek_extract.status,
            "deepseek_extract_latency_ms": self.deepseek_extract.latency_ms,
            "deepseek_extract_model": self.deepseek_extract.model_name,
            "mimo_critique_status": self.mimo_critique.status,
            "mimo_critique_latency_ms": self.mimo_critique.latency_ms,
            "mimo_critique_model": self.mimo_critique.model_name,
            "deepseek_strategy_status": self.deepseek_strategy.status,
            "deepseek_strategy_latency_ms": self.deepseek_strategy.latency_ms,
            "deepseek_strategy_model": self.deepseek_strategy.model_name,
            "mimo_review_status": self.mimo_review.status,
            "mimo_review_latency_ms": self.mimo_review.latency_ms,
            "mimo_review_model": self.mimo_review.model_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "stages": {
                "deepseek_extract": self.deepseek_extract.to_dict(),
                "mimo_critique": self.mimo_critique.to_dict(),
                "deepseek_strategy": self.deepseek_strategy.to_dict(),
                "mimo_review": self.mimo_review.to_dict(),
            },
        }

    def save(self, output_dir: str):
        """Save manifest to _internal subdirectory."""
        internal_dir = os.path.join(output_dir, "_internal")
        path = os.path.join(internal_dir, "ai_run_manifest.json")
        os.makedirs(internal_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
