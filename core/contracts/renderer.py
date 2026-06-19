"""
core/contracts/renderer.py - Renderer Interface

Defines the contract for document renderers.
All renderers (DOCX, PDF, XLSX, ZIP) must implement Renderer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RenderFormat(Enum):
    """Output format."""
    DOCX = "docx"
    PDF = "pdf"
    XLSX = "xlsx"
    ZIP = "zip"


@dataclass
class RenderResult:
    """Result of a render operation."""
    success: bool
    output_path: str = ""
    format: RenderFormat = RenderFormat.DOCX
    file_size: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output_path": self.output_path,
            "format": self.format.value,
            "file_size": self.file_size,
            "error": self.error,
        }


class Renderer(ABC):
    """Abstract base class for document renderers."""

    @property
    @abstractmethod
    def format(self) -> RenderFormat:
        """Output format this renderer produces."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Renderer identifier."""
        ...

    @abstractmethod
    def render(self, content: dict, output_path: str) -> RenderResult:
        """Render content to file.

        Args:
            content: Content dictionary with template data.
            output_path: Output file path.

        Returns:
            RenderResult with success status and file info.
        """
        ...
