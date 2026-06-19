"""Pydantic models for structured LLM output enforcement."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class ExtractedParty(BaseModel):
    name: str = Field(description="当事人姓名或名称")
    role: str = Field(description="角色：原告/被告/申请人/被申请人/第三人")


class TimelineEvent(BaseModel):
    date: str = Field(description="日期，格式 YYYY-MM-DD 或 YYYY年MM月DD日")
    event: str = Field(description="事件描述")


class FundFlow(BaseModel):
    date: str = Field(description="资金流转日期")
    amount: str = Field(description="金额，含币种")
    direction: str = Field(description="流向：转入/转出")
    counterparty: str = Field(description="交易对手方")
    evidence: str = Field(description="对应证据：银行流水/转账凭证等")


class FactExtractionResult(BaseModel):
    """Step 3: 事实蒸馏结构化输出。"""
    case_id: str = Field(default="", description="案号")
    court: str = Field(default="", description="管辖法院")
    case_type: str = Field(default="", description="案由：借款合同纠纷/民间借贷纠纷等")
    parties: List[ExtractedParty] = Field(default_factory=list, description="当事人列表")
    timeline: List[TimelineEvent] = Field(default_factory=list, description="案件时间线")
    fund_flows: List[FundFlow] = Field(default_factory=list, description="资金流水")
    claims: List[str] = Field(default_factory=list, description="原告诉讼请求")
    key_facts: List[str] = Field(default_factory=list, description="关键事实要点")
    disputed_facts: List[str] = Field(default_factory=list, description="存在争议的事实")
    missing_materials: List[str] = Field(default_factory=list, description="缺失的材料")
    conflicts: List[str] = Field(default_factory=list, description="事实矛盾/冲突")


class LegalAnalysis(BaseModel):
    """法律分析条目。"""
    issue: str = Field(description="争议焦点")
    applicable_law: str = Field(description="适用法律条文")
    analysis: str = Field(description="法律分析")
    conclusion: str = Field(description="结论")


class ReliefPath(BaseModel):
    """救济路径。"""
    level: str = Field(description="救济层级：一审/二审/再审/执行")
    strategy: str = Field(description="具体策略")
    deadline: str = Field(default="", description="期限要求")
    probability: str = Field(default="", description="成功概率评估")


class StrategyReasoningResult(BaseModel):
    """Step 4: 策略推演结构化输出。"""
    situation_assessment: str = Field(default="", description="案件处境综合评估")
    sabcd_rating: str = Field(default="", description="评级：S/A/B/C/D")
    rating_reasoning: str = Field(default="", description="评级理由")
    core_disputes: List[LegalAnalysis] = Field(default_factory=list, description="核心争议焦点分析")
    relief_paths: List[ReliefPath] = Field(default_factory=list, description="救济路径")
    entity_defense: List[str] = Field(default_factory=list, description="实体抗辩思路")
    action_advice: List[str] = Field(default_factory=list, description="具体操作建议")
    evidence_gap: List[str] = Field(default_factory=list, description="证据缺口")
    risk_warnings: List[str] = Field(default_factory=list, description="风险提示")
