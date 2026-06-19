"""
core/contracts/workflow_stage.py - Workflow Stage Interface

Defines the contract for pipeline stages.
All stages must implement WorkflowStage.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List

from core.fact_card import PipelineContext


class StageStatus(Enum):
    """Stage execution status."""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """Result of a stage execution."""
    stage_name: str
    status: StageStatus = StageStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    latency_ms: int = 0
    error: Optional[str] = None
    ai_provider: str = ""            # deepseek / mimo / none
    ai_model: str = ""               # Model used (if AI stage)
    token_usage: Optional[dict] = None

    @property
    def is_success(self) -> bool:
        return self.status == StageStatus.DONE

    @property
    def is_ai_stage(self) -> bool:
        return self.ai_provider != ""

    def to_dict(self) -> dict:
        return {
            "stage_name": self.stage_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "ai_provider": self.ai_provider,
            "ai_model": self.ai_model,
            "token_usage": self.token_usage,
        }


@dataclass
class StageEvent:
    """Event emitted during stage execution."""
    stage_name: str
    status: StageStatus
    display_name: str = ""
    progress: float = 0.0            # 0.0 to 1.0
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


# Type alias for event listeners
EventListener = Callable[[StageEvent], None]


class WorkflowStage(ABC):
    """Abstract base class for workflow stages."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stage identifier (e.g., 'intake', 'extract', 'review')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable stage name for UI display."""
        ...

    @property
    def requires_ai(self) -> bool:
        """Whether this stage requires AI calls."""
        return False

    @property
    def ai_provider(self) -> str:
        """Which AI provider this stage uses ('deepseek', 'mimo', 'none')."""
        return "none"

    @property
    def depends_on(self) -> List[str]:
        """Stage names that must complete before this stage."""
        return []

    @abstractmethod
    def execute(self, ctx: PipelineContext,
                on_event: Optional[EventListener] = None) -> PipelineContext:
        """Execute the stage.

        Args:
            ctx: Pipeline context with all accumulated data.
            on_event: Optional callback for progress events.

        Returns:
            Updated PipelineContext with stage results.
        """
        ...

    def _emit(self, on_event: Optional[EventListener],
              status: StageStatus, message: str = "", progress: float = 0.0):
        """Helper to emit events."""
        if on_event:
            on_event(StageEvent(
                stage_name=self.name,
                status=status,
                display_name=self.display_name,
                progress=progress,
                message=message,
            ))
