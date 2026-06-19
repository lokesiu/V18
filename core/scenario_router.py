"""
scenario_router.py - Identity/Goal Routing

Validates user identity and goal, routes to appropriate document types,
and provides SABCD rating factors for strategy assessment.
"""
from __future__ import annotations
from typing import List, Dict, Any

from core.fact_card import PipelineContext


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_IDENTITIES = ["消费者", "投诉方", "起诉方", "起诉方（原告）", "被诉方", "被诉方（被告）", "复议申请人", "行政复议申请人", "整理证据"]
VALID_GOALS = ["维权投诉", "投诉举报", "提起起诉", "起诉立案", "应诉答辩", "申请行政复议", "行政复议", "证据整理"]

IDENTITY_GOAL_MAP = {
    "消费者": "维权投诉",
    "投诉方": "投诉举报",
    "起诉方": "起诉立案",
    "起诉方（原告）": "提起起诉",
    "被诉方": "应诉答辩",
    "被诉方（被告）": "应诉答辩",
    "复议申请人": "申请行政复议",
    "行政复议申请人": "行政复议",
    "整理证据": "证据整理",
}

# Normalize identity to canonical form for lookup
def _normalize_identity(identity: str) -> str:
    """Normalize identity variants to canonical form."""
    if identity in ("起诉方（原告）",):
        return "起诉方"
    if identity in ("消费者",):
        return "投诉方"
    if identity in ("复议申请人",):
        return "行政复议申请人"
    if identity in ("被诉方",):
        return "被诉方（被告）"
    return identity

IDENTITY_DOC_TYPES = {
    "投诉方": ["投诉状", "证据目录", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
    "起诉方": ["起诉状", "证据目录", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
    "被诉方（被告）": ["答辩状", "证据目录", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
    "行政复议申请人": ["行政复议申请书", "证据目录", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
    "整理证据": ["证据目录", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
}

# SABCD rating definitions
SABCD_LEVELS = {
    "S": "证据充分、事实清楚、法律依据明确，胜诉/成功概率极高",
    "A": "证据较充分、主要事实清楚，有明确法律依据，成功概率高",
    "B": "证据部分充分、部分事实需要补充，有一定法律依据，成功概率中等",
    "C": "证据不足、事实存在争议，法律依据不够明确，成功概率较低",
    "D": "证据严重不足、事实不清，缺乏法律依据，成功概率极低",
}


def validate_identity(identity: str) -> bool:
    """Validate that the identity is one of the allowed values."""
    return identity in VALID_IDENTITIES


def validate_goal(goal: str) -> bool:
    """Validate that the goal is one of the allowed values."""
    return goal in VALID_GOALS


def get_expected_doc_types(identity: str) -> List[str]:
    """
    Returns list of document types to generate based on identity.
    
    Args:
        identity: The user's role in the case
        
    Returns:
        List of document type names, empty list for 整理证据
    """
    canonical = _normalize_identity(identity)
    return IDENTITY_DOC_TYPES.get(canonical, IDENTITY_DOC_TYPES.get(identity, []))


def get_sabcd_factors(identity: str, goal: str) -> Dict[str, Any]:
    """
    Returns factors for SABCD rating assessment.
    
    The SABCD rating evaluates the strength of the case based on:
    - S: Strong (evidence + facts + law all aligned)
    - A: Above average (mostly aligned with minor gaps)
    - B: Balanced (mixed strength, needs work)
    - C: Concerning (significant weaknesses)
    - D: Dire (fundamental problems)
    
    Args:
        identity: The user's role
        goal: The user's goal
        
    Returns:
        Dictionary with factors to evaluate
    """
    canonical = _normalize_identity(identity)
    factors = {
        "identity": identity,
        "goal": goal,
        "criteria": [],
        "weight_distribution": {},
    }

    # Base criteria depend on identity/goal combination
    if canonical == "投诉方":
        factors["criteria"] = [
            "投诉事实是否清楚",
            "证据是否充分",
            "被投诉方信息是否明确",
            "投诉依据的法律法规",
            "投诉渠道是否正确",
        ]
        factors["weight_distribution"] = {
            "事实清楚": 0.25,
            "证据充分": 0.30,
            "信息明确": 0.15,
            "法律依据": 0.20,
            "渠道正确": 0.10,
        }

    elif canonical == "起诉方":
        factors["criteria"] = [
            "诉讼请求是否明确具体",
            "事实与理由是否充分",
            "证据链是否完整",
            "管辖法院是否正确",
            "诉讼时效是否在期限内",
            "法律依据是否准确",
        ]
        factors["weight_distribution"] = {
            "请求明确": 0.20,
            "事实充分": 0.20,
            "证据完整": 0.25,
            "管辖正确": 0.10,
            "时效合规": 0.10,
            "法律准确": 0.15,
        }

    elif canonical == "被诉方（被告）":
        factors["criteria"] = [
            "答辩观点是否有事实依据",
            "反驳证据是否充分",
            "法律依据是否正确",
            "是否发现对方证据漏洞",
            "反诉可能性评估",
        ]
        factors["weight_distribution"] = {
            "事实依据": 0.25,
            "证据充分": 0.25,
            "法律正确": 0.20,
            "漏洞发现": 0.15,
            "反诉可能": 0.15,
        }

    elif canonical == "行政复议申请人":
        factors["criteria"] = [
            "复议请求是否明确",
            "原行政行为是否违法或不当",
            "证据是否支持复议理由",
            "复议时效是否合规",
            "是否穷尽行政救济",
        ]
        factors["weight_distribution"] = {
            "请求明确": 0.20,
            "行为违法": 0.25,
            "证据支持": 0.25,
            "时效合规": 0.15,
            "救济穷尽": 0.15,
        }

    elif canonical == "整理证据":
        factors["criteria"] = [
            "证据数量是否充足",
            "证据类型是否多样",
            "证据链是否完整",
            "证据来源是否可靠",
            "证据形式是否合规",
        ]
        factors["weight_distribution"] = {
            "数量充足": 0.15,
            "类型多样": 0.15,
            "链完整": 0.30,
            "来源可靠": 0.20,
            "形式合规": 0.20,
        }

    # Add general assessment guidance
    factors["rating_guide"] = {
        "S": "所有 criteria 得分 ≥ 90%",
        "A": "大多数 criteria 得分 ≥ 75%",
        "B": "criteria 得分在 50%-75% 之间",
        "C": "criteria 得分在 30%-50% 之间",
        "D": "criteria 得分 < 30% 或关键 criteria 严重不足",
    }

    return factors


def route_scenario(ctx: PipelineContext) -> PipelineContext:
    """
    Main routing entry point.
    
    Validates identity and goal, sets up context for downstream processing.
    """
    ctx.log("开始场景路由...")

    # Validate identity
    if not validate_identity(ctx.identity):
        ctx.add_error(f"无效的身份: {ctx.identity}，有效值: {VALID_IDENTITIES}")
        return ctx

    # Auto-set goal based on identity if not provided
    if not ctx.goal:
        ctx.goal = IDENTITY_GOAL_MAP.get(ctx.identity, "")
        ctx.log(f"根据身份自动设置目标: {ctx.goal}")

    # Validate goal
    if not validate_goal(ctx.goal):
        ctx.add_error(f"无效的目标: {ctx.goal}，有效值: {VALID_GOALS}")
        return ctx

    # Get document types for this scenario
    doc_types = get_expected_doc_types(ctx.identity)
    ctx.log(f"身份: {ctx.identity}")
    ctx.log(f"目标: {ctx.goal}")
    ctx.log(f"待生成文档: {doc_types if doc_types else '无（仅整理证据）'}")

    # Get SABCD factors
    factors = get_sabcd_factors(ctx.identity, ctx.goal)
    ctx.log(f"SABCD评估标准: {len(factors['criteria'])} 项")

    return ctx
