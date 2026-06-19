"""
core/scenario/defense_scenario.py - Defense (被诉方+应诉答辩) Scenario

This is the PRIMARY scenario for V18-RC.
All other scenarios are "coming soon".
"""
from __future__ import annotations

from typing import List, Dict, Any

from core.contracts.scenario import Scenario, ScenarioConfig, ScenarioStatus
from core.fact_card import PipelineContext


class DefenseScenario(Scenario):
    """被诉方 + 应诉答辩 scenario.

    This is the only ACTIVE scenario in V18-RC.
    """

    @property
    def config(self) -> ScenarioConfig:
        return ScenarioConfig(
            identity="被诉方",
            goal="应诉答辩",
            display_name="被诉方应诉答辩",
            description="针对被诉案件，生成答辩状、证据清单、策略建议等完整应诉材料",
            status=ScenarioStatus.ACTIVE,
            template_names=["defense_template"],
            required_doc_types=[
                "答辩状",
                "证据清单",
                "案件评估报告",
                "行动建议书",
                "证据闭环清单",
            ],
            quality_rules=[
                "action_advice_count >= 6",
                "evidence_gap_count >= 5",
                "sabcd_rating_required",
                "situation_assessment_min_length >= 100",
                "no_generic_defense",
                "no_placeholders",
                "no_internal_fields",
            ],
            min_action_advice=6,
            min_evidence_gap=5,
        )

    def validate_input(self, ctx: PipelineContext) -> List[str]:
        """Validate input for defense scenario."""
        errors = []

        if not ctx.identity:
            errors.append("身份未设置")
        elif ctx.identity != "被诉方":
            errors.append(f"身份不匹配: 期望'被诉方', 实际'{ctx.identity}'")

        if not ctx.goal:
            errors.append("目标未设置")
        elif ctx.goal != "应诉答辩":
            errors.append(f"目标不匹配: 期望'应诉答辩', 实际'{ctx.goal}'")

        if not ctx.input_dir:
            errors.append("输入目录未设置")

        return errors

    def get_quality_rules(self) -> Dict[str, Any]:
        """Get defense-specific quality rules."""
        return {
            "min_action_advice": 6,
            "min_evidence_gap": 5,
            "require_sabcd_rating": True,
            "require_situation_assessment": True,
            "min_situation_assessment_length": 100,
            "forbidden_patterns": [
                "文书 1:", "文书 1：",
                "类型:", "类型：",
                "待补充", "{{", "}}",
                "TODO", "暂无", "请自行补充",
                "fact_card", "prompt", "source_id",
            ],
            "require_pdf": True,
            "require_zip": True,
            "zip_must_contain_pdf": True,
            "reject_local_fallback": True,
            "defense_specific": {
                "require_defense_points": True,
                "require_evidence_analysis": True,
                "require_counterarguments": True,
                "min_defense_sections": 3,
            },
        }
