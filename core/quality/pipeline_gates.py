"""core/quality/pipeline_gates.py — Step-level quality gates.

Runs after step2 (extract) and step3 (fact enhancement) to catch
low-quality intermediate results before they propagate downstream.

Returns a GateResult with status and issues list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from core.fact_card import PipelineContext


@dataclass
class GateIssue:
    """A single quality issue found by a gate."""
    rule: str = ""
    severity: str = "warning"  # warning / blocking
    message: str = ""

    def to_dict(self) -> dict:
        return {"rule": self.rule, "severity": self.severity, "message": self.message}


@dataclass
class GateResult:
    """Result of running a quality gate."""
    status: str = "passed"  # passed / warning / blocked
    issues: List[GateIssue] = field(default_factory=list)

    @property
    def blocking_issues(self) -> List[GateIssue]:
        return [i for i in self.issues if i.severity == "blocking"]

    @property
    def warning_issues(self) -> List[GateIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "issues": [i.to_dict() for i in self.issues],
        }


def run_step2_gate(ctx: PipelineContext) -> GateResult:
    """Quality gate after step2 (extract).

    Checks:
    - raw_texts not empty → blocking
    - raw_texts total length >= 100 → blocking
    - fact_card not None → blocking
    - key_facts not empty → blocking
    - parties not empty → warning
    """
    result = GateResult()

    # Rule 1: raw_texts empty
    if not ctx.raw_texts:
        result.issues.append(GateIssue(
            rule="raw_texts_empty",
            severity="blocking",
            message="未从材料中提取到任何文本，请检查文件格式是否受支持",
        ))

    # Rule 2: raw_texts too short
    elif sum(len(t) for t in ctx.raw_texts) < 100:
        total_len = sum(len(t) for t in ctx.raw_texts)
        result.issues.append(GateIssue(
            rule="raw_texts_too_short",
            severity="blocking",
            message=f"提取文本过短（{total_len}字符），可能文件为扫描件或OCR失败",
        ))

    # Rule 3: fact_card is None
    if ctx.fact_card is None:
        result.issues.append(GateIssue(
            rule="fact_card_none",
            severity="blocking",
            message="事实提取未生成 fact_card，提取引擎可能异常",
        ))
    else:
        # Rule 4: key_facts empty
        if not ctx.fact_card.key_facts:
            result.issues.append(GateIssue(
                rule="key_facts_empty",
                severity="blocking",
                message="未提取到任何关键事实，材料内容可能不足",
            ))

        # Rule 5: parties empty (warning only)
        if not ctx.fact_card.parties:
            result.issues.append(GateIssue(
                rule="parties_empty",
                severity="warning",
                message="未识别到当事人信息，后续文书可能缺少当事人",
            ))

    # Determine final status
    if result.blocking_issues:
        result.status = "blocked"
    elif result.warning_issues:
        result.status = "warning"
    else:
        result.status = "passed"

    return result


def run_step3_gate(ctx: PipelineContext) -> GateResult:
    """Quality gate after step3 (fact enhancement).

    Checks:
    - key_facts still empty → blocking
    - court empty → warning
    - parties still empty → warning (not blocking in B1)
    - amount empty → warning
    - all key_facts very short → warning
    """
    result = GateResult()

    if ctx.fact_card is None:
        result.issues.append(GateIssue(
            rule="fact_card_none_after_enhance",
            severity="blocking",
            message="API增强后 fact_card 仍为空",
        ))
        result.status = "blocked"
        return result

    # Rule 1: key_facts still empty
    if not ctx.fact_card.key_facts:
        result.issues.append(GateIssue(
            rule="key_facts_empty_after_enhance",
            severity="blocking",
            message="API增强后仍无关键事实，材料质量可能不足",
        ))

    # Rule 2: court empty (warning)
    if not ctx.fact_card.court:
        result.issues.append(GateIssue(
            rule="court_empty",
            severity="warning",
            message="未识别到法院/管辖信息",
        ))

    # Rule 3: parties still empty (warning, not blocking in B1)
    if not ctx.fact_card.parties:
        result.issues.append(GateIssue(
            rule="parties_empty_after_enhance",
            severity="warning",
            message="API增强后仍未识别到当事人信息",
        ))

    # Rule 4: amount empty (warning)
    if not ctx.fact_card.amount:
        result.issues.append(GateIssue(
            rule="amount_empty",
            severity="warning",
            message="未识别到争议金额",
        ))

    # Rule 5: all key_facts very short (warning)
    if ctx.fact_card.key_facts:
        if all(len(f) < 10 for f in ctx.fact_card.key_facts):
            result.issues.append(GateIssue(
                rule="key_facts_too_short",
                severity="warning",
                message="关键事实描述过短，可能质量不足",
            ))

    # Determine final status
    if result.blocking_issues:
        result.status = "blocked"
    elif result.warning_issues:
        result.status = "warning"
    else:
        result.status = "passed"

    return result
