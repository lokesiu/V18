"""
core/workflow/events.py - Workflow Event Definitions
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional


@dataclass
class WorkflowEvent:
    """Event emitted during workflow execution."""
    stage_name: str
    status: str = "pending"  # pending / running / done / failed / skipped
    display_name: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    latency_ms: int = 0
    model_name: str = ""
    token_usage: Optional[dict] = None
    error: Optional[str] = None
    is_ai: bool = False
    ai_provider: str = ""  # deepseek / mimo / none


class EventBus:
    """Simple event bus for workflow events."""

    def __init__(self):
        self._listeners: List[Callable[[WorkflowEvent], None]] = []

    def subscribe(self, listener: Callable[[WorkflowEvent], None]):
        """Subscribe to events."""
        self._listeners.append(listener)

    def emit(self, event: WorkflowEvent):
        """Emit an event to all listeners."""
        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                pass  # Don't let listener errors break workflow
