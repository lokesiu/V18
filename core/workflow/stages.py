"""
core/workflow/stages.py - Stage Definitions
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class StageDefinition:
    """Definition of a workflow stage."""
    name: str
    display_name: str
    requires_ai: bool = False
    ai_provider: str = ""  # deepseek / mimo / none
    depends_on: List[str] = field(default_factory=list)


# 9-stage dual AI workflow
DUAL_AI_STAGES = [
    StageDefinition(
        name="intake",
        display_name="读取材料",
        requires_ai=False,
        ai_provider="none",
        depends_on=[],
    ),
    StageDefinition(
        name="deepseek_extract",
        display_name="DeepSeek 事实抽取",
        requires_ai=True,
        ai_provider="deepseek",
        depends_on=["intake"],
    ),
    StageDefinition(
        name="mimo_critique",
        display_name="MiMo 事实复核",
        requires_ai=True,
        ai_provider="mimo",
        depends_on=["deepseek_extract"],
    ),
    StageDefinition(
        name="distill_facts",
        display_name="蒸馏案件事实",
        requires_ai=False,
        ai_provider="none",
        depends_on=["mimo_critique"],
    ),
    StageDefinition(
        name="deepseek_strategy",
        display_name="DeepSeek 生成策略",
        requires_ai=True,
        ai_provider="deepseek",
        depends_on=["distill_facts"],
    ),
    StageDefinition(
        name="mimo_review",
        display_name="MiMo 审校策略",
        requires_ai=True,
        ai_provider="mimo",
        depends_on=["deepseek_strategy"],
    ),
    StageDefinition(
        name="final_distill",
        display_name="模板蒸馏",
        requires_ai=False,
        ai_provider="none",
        depends_on=["mimo_review"],
    ),
    StageDefinition(
        name="render",
        display_name="生成 DOCX/PDF/XLSX/ZIP",
        requires_ai=False,
        ai_provider="none",
        depends_on=["final_distill"],
    ),
    StageDefinition(
        name="quality_gate",
        display_name="质量门禁",
        requires_ai=False,
        ai_provider="none",
        depends_on=["render"],
    ),
]
