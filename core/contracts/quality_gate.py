"""
core/contracts/quality_gate.py - Quality Gate Interface

Defines the contract for quality checks.
All quality gates must implement QualityGate.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class CheckSeverity(Enum):
    """Check severity level."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"  # Blocks delivery


@dataclass
class QualityCheck:
    """Result of a single quality check."""
    check_name: str
    passed: bool
    severity: CheckSeverity = CheckSeverity.ERROR
    message: str = ""
    details: str = ""
    remediation: str = ""  # How to fix

    def to_dict(self) -> dict:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "remediation": self.remediation,
        }


@dataclass
class QualityResult:
    """Aggregated quality gate result."""
    gate_name: str
    checks: List[QualityCheck] = field(default_factory=list)
    ai_mode: str = ""  # real_ai / mixed / local_fallback

    @property
    def passed(self) -> bool:
        """All checks must pass."""
        return all(c.passed for c in self.checks)

    @property
    def critical_failures(self) -> List[QualityCheck]:
        """Critical failures that block delivery."""
        return [
            c for c in self.checks
            if not c.passed and c.severity == CheckSeverity.CRITICAL
        ]

    @property
    def has_critical_failure(self) -> bool:
        """Whether there are any critical failures."""
        return len(self.critical_failures) > 0

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    def summary(self) -> str:
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c.passed)
        critical = len(self.critical_failures)
        return (
            f"Quality Gate [{self.gate_name}]: "
            f"{passed}/{total} passed, {critical} critical failures"
        )

    def to_dict(self) -> dict:
        return {
            "gate_name": self.gate_name,
            "passed": self.passed,
            "ai_mode": self.ai_mode,
            "total_checks": len(self.checks),
            "passed_checks": sum(1 for c in self.checks if c.passed),
            "critical_failures": len(self.critical_failures),
            "checks": [c.to_dict() for c in self.checks],
        }


class QualityGate(ABC):
    """Abstract base class for quality gates."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Gate identifier."""
        ...

    @abstractmethod
    def run_checks(self, case_dir: str, ai_mode: str = "") -> QualityResult:
        """Run all quality checks on a case directory.

        Args:
            case_dir: Path to case output directory.
            ai_mode: Current AI mode (real_ai/mixed/local_fallback).

        Returns:
            QualityResult with all check results.
        """
        ...
