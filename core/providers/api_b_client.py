"""
api_b_client.py - API-B Client for Strategy Generation

Calls API-B to generate legal strategy based on fact cards.
Falls back to local rule-based generation when API is unavailable.
NEVER raises exceptions - always returns a valid StrategyCard.
"""
from __future__ import annotations

import os
import logging
from typing import List

from core.fact_card import (
    FactCard,
    StrategyCard,
    ActionAdvice,
    DraftDocument,
)

logger = logging.getLogger(__name__)


class ApiBClient:
    """API-B client for strategy generation."""

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key or os.environ.get("V18_API_B_KEY", "")
        self.base_url = base_url or os.environ.get("V18_API_B_URL", "")
        self._available = bool(self.api_key and self.base_url)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_strategy(
        self,
        fact_card: FactCard,
        identity: str,
        goal: str,
    ) -> StrategyCard:
        """Call API-B to generate strategy. Returns StrategyCard.

        If API is available, sends fact_card + identity + goal.
        If API is unavailable, generates a basic strategy from fact_card.
        NEVER raises - always returns a StrategyCard.
        """
        if self._available:
            try:
                strategy = self._call_api(fact_card, identity, goal)
                if strategy is not None:
                    return strategy
            except Exception as exc:
                logger.warning(
                    "API-B call failed, falling back to local generation: %s", exc
                )

        return self._local_generate(fact_card, identity, goal)

    # ------------------------------------------------------------------
    # Internal: API call (stub – real implementation depends on API spec)
    # ------------------------------------------------------------------

    def _call_api(
        self,
        fact_card: FactCard,
        identity: str,
        goal: str,
    ) -> StrategyCard | None:
        """Attempt to call the remote API-B endpoint.

        Returns StrategyCard on success, None on failure.
        This is a stub that can be replaced with actual HTTP calls.
        """
        # Placeholder for actual HTTP call:
        # import httpx
        # payload = {
        #     "fact_card": fact_card.to_dict(),
        #     "identity": identity,
        #     "goal": goal,
        # }
        # resp = httpx.post(
        #     f"{self.base_url}/generate_strategy",
        #     json=payload,
        #     headers={"Authorization": f"Bearer {self.api_key}"},
        #     timeout=60,
        # )
        # resp.raise_for_status()
        # data = resp.json()
        # return StrategyCard.from_dict(data)
        return None

    # ------------------------------------------------------------------
    # Internal: Local rule-based strategy generation
    # ------------------------------------------------------------------

    def _local_generate(
        self,
        fact_card: FactCard,
        identity: str,
        goal: str,
    ) -> StrategyCard:
        """Generate a basic strategy from the fact card using local rules."""
        situation = self._build_situation(fact_card, identity, goal)
        actions = self._build_actions(fact_card, identity)
        evidence_gaps = self._build_evidence_gaps(fact_card)
        risk_warnings = self._build_risk_warnings(fact_card)
        rating = self._compute_rating(fact_card)
        drafts = self._build_draft_documents(fact_card, identity, goal)

        return StrategyCard(
            situation_assessment=situation,
            action_advice=actions,
            evidence_gap=evidence_gaps,
            draft_documents=drafts,
            risk_warnings=risk_warnings,
            sabcd_rating=rating,
        )

    # ------------------------------------------------------------------
    # Component builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_situation(fact_card: FactCard, identity: str, goal: str) -> str:
        """Summarize key facts, identity, and amount into a situation assessment."""
        parts: List[str] = []

        parts.append(f"当事人身份：{identity or '未指定'}。")
        parts.append(f"处理目标：{goal or '未指定'}。")

        if fact_card.case_id:
            parts.append(f"案件编号：{fact_card.case_id}。")
        if fact_card.court:
            parts.append(f"管辖机关：{fact_card.court}。")
        if fact_card.amount:
            parts.append(f"涉及金额：{fact_card.amount}。")
        if fact_card.deadline:
            parts.append(f"关键期限：{fact_card.deadline}。")

        if fact_card.parties:
            party_descs = [f"{p.role}{p.name}" for p in fact_card.parties if p.name]
            if party_descs:
                parts.append(f"案件当事人：{'、'.join(party_descs)}。")

        if fact_card.key_facts:
            top_facts = fact_card.key_facts[:5]
            parts.append("核心事实摘要：" + "；".join(top_facts) + "。")

        if fact_card.conflicts:
            parts.append(
                f"存在{len(fact_card.conflicts)}项事实冲突，需要重点关注。"
            )

        if fact_card.missing_materials:
            parts.append(
                f"现有{len(fact_card.missing_materials)}项材料缺失，建议尽快补充。"
            )

        if not parts:
            parts.append("信息不足，无法形成完整的处境评估。建议补充更多案件材料。")

        return "\n".join(parts)

    @staticmethod
    def _build_actions(fact_card: FactCard, identity: str) -> List[ActionAdvice]:
        """Generate action advice based on the user's identity."""
        actions: List[ActionAdvice] = []

        identity_lower = (identity or "").strip()

        if identity_lower in ("投诉方", "投诉人", "消费者"):
            actions.append(
                ActionAdvice(
                    action="整理投诉材料，确保投诉事实清楚、证据充分",
                    priority="S",
                    reasoning="投诉材料的完整性直接决定投诉能否被受理",
                )
            )
            actions.append(
                ActionAdvice(
                    action="收集并固定关键证据（合同、付款凭证、沟通记录等）",
                    priority="S",
                    reasoning="证据是投诉成功的核心要素",
                )
            )
            actions.append(
                ActionAdvice(
                    action="撰写投诉状，明确投诉请求和事实理由",
                    priority="A",
                    reasoning="投诉状的逻辑性和说服力影响处理结果",
                )
            )
            actions.append(
                ActionAdvice(
                    action="向相关主管部门提交投诉并保留提交凭证",
                    priority="A",
                    reasoning="书面提交并保留回执是后续维权的基础",
                )
            )
            actions.append(
                ActionAdvice(
                    action="持续跟进投诉处理进展，必要时补充材料",
                    priority="B",
                    reasoning="投诉处理周期较长，需定期关注进展",
                )
            )
            actions.append(
                ActionAdvice(
                    action="评估是否需要同时向多个部门投诉或申请行政调解",
                    priority="B",
                    reasoning="多渠道维权可以增加解决机会",
                )
            )

        elif identity_lower in ("起诉方", "起诉方（原告）", "原告"):
            actions.append(
                ActionAdvice(
                    action="核实诉讼时效，确保未超过法定期限",
                    priority="S",
                    reasoning="超过时效将丧失胜诉权",
                )
            )
            actions.append(
                ActionAdvice(
                    action="整理证据材料并制作证据目录",
                    priority="S",
                    reasoning="证据是诉讼请求能否获得支持的关键",
                )
            )
            actions.append(
                ActionAdvice(
                    action="撰写起诉状，明确诉讼请求、事实与理由",
                    priority="S",
                    reasoning="起诉状是法院受理案件的基础文件",
                )
            )
            actions.append(
                ActionAdvice(
                    action="确定管辖法院并准备立案材料",
                    priority="A",
                    reasoning="选择有管辖权的法院有利于案件审理",
                )
            )
            actions.append(
                ActionAdvice(
                    action="评估是否需要申请财产保全或行为保全",
                    priority="B",
                    reasoning="保全措施可防止对方转移资产或继续侵权",
                )
            )
            actions.append(
                ActionAdvice(
                    action="准备庭审陈述和质证意见",
                    priority="A",
                    reasoning="庭审表现直接影响案件结果",
                )
            )

        elif identity_lower in ("被诉方", "被告", "被诉方（被告）"):
            actions.append(
                ActionAdvice(
                    action="仔细研究对方起诉状，梳理争议焦点",
                    priority="S",
                    reasoning="准确识别争议焦点是有效应诉的前提",
                )
            )
            actions.append(
                ActionAdvice(
                    action="收集反驳证据，针对对方主张逐一回应",
                    priority="S",
                    reasoning="充分的反驳证据是胜诉的基础",
                )
            )
            actions.append(
                ActionAdvice(
                    action="撰写答辩状，在法定期限内提交法院",
                    priority="S",
                    reasoning="未按时提交答辩状不影响诉讼权利但不利于表达立场",
                )
            )
            actions.append(
                ActionAdvice(
                    action="评估反诉的可能性和必要性",
                    priority="A",
                    reasoning="反诉可以一并解决相关纠纷，降低诉讼成本",
                )
            )
            actions.append(
                ActionAdvice(
                    action="准备出庭应诉材料和质证意见",
                    priority="A",
                    reasoning="庭审中的表现直接影响案件结果",
                )
            )
            actions.append(
                ActionAdvice(
                    action="评估和解或调解的可能性，制定谈判策略",
                    priority="B",
                    reasoning="和解可以节省诉讼成本和时间，降低败诉风险",
                )
            )
            actions.append(
                ActionAdvice(
                    action="核实原告证据的真实性和完整性",
                    priority="A",
                    reasoning="原告证据瑕疵可以作为抗辩依据",
                )
            )

        elif identity_lower in ("行政复议申请人", "复议申请人"):
            actions.append(
                ActionAdvice(
                    action="核实行政复议申请期限（一般60日内）",
                    priority="S",
                    reasoning="超过申请期限将丧失复议权利",
                )
            )
            actions.append(
                ActionAdvice(
                    action="收集行政行为违法或不当的证据",
                    priority="S",
                    reasoning="证据是复议成功的关键",
                )
            )
            actions.append(
                ActionAdvice(
                    action="撰写行政复议申请书",
                    priority="S",
                    reasoning="申请书需要明确复议请求和事实理由",
                )
            )
            actions.append(
                ActionAdvice(
                    action="确定复议机关并按时提交申请",
                    priority="A",
                    reasoning="向正确的机关提交才能被受理",
                )
            )
            actions.append(
                ActionAdvice(
                    action="准备复议听证材料",
                    priority="A",
                    reasoning="听证是复议程序的重要环节",
                )
            )

        elif identity_lower in ("整理证据", "证据整理"):
            actions.append(
                ActionAdvice(
                    action="按照证据类型分类整理所有材料",
                    priority="S",
                    reasoning="分类整理有助于快速检索和使用",
                )
            )
            actions.append(
                ActionAdvice(
                    action="制作证据目录，标注每份证据的证明目的",
                    priority="S",
                    reasoning="证据目录是法庭审理的重要参考",
                )
            )
            actions.append(
                ActionAdvice(
                    action="检查证据原件与复印件是否一致",
                    priority="A",
                    reasoning="证据真实性是被采信的前提",
                )
            )
            actions.append(
                ActionAdvice(
                    action="对关键证据进行公证或鉴定",
                    priority="B",
                    reasoning="公证和鉴定可以增强证据的证明力",
                )
            )
            actions.append(
                ActionAdvice(
                    action="评估证据链的完整性，识别缺失环节",
                    priority="A",
                    reasoning="完整的证据链才能有效证明案件事实",
                )
            )

        else:
            # Generic fallback for unknown identity
            actions.append(
                ActionAdvice(
                    action="整理并核实案件基本事实",
                    priority="S",
                    reasoning="事实清楚是处理任何法律事务的基础",
                )
            )
            actions.append(
                ActionAdvice(
                    action="收集和固定相关证据材料",
                    priority="S",
                    reasoning="证据充分是维护权益的关键",
                )
            )
            actions.append(
                ActionAdvice(
                    action="咨询专业律师获取针对性建议",
                    priority="A",
                    reasoning="专业律师可以提供更有针对性的法律意见",
                )
            )
            actions.append(
                ActionAdvice(
                    action="评估案件风险和可能的结果",
                    priority="A",
                    reasoning="风险评估有助于制定合理的应对策略",
                )
            )
            actions.append(
                ActionAdvice(
                    action="准备所有必要的法律文书",
                    priority="B",
                    reasoning="文书准备充分有利于案件处理",
                )
            )

        # Add deadline-related action if deadline exists
        if fact_card.deadline:
            actions.insert(
                0,
                ActionAdvice(
                    action=f"注意关键期限 {fact_card.deadline}，确保在此之前完成所有准备工作",
                    priority="S",
                    reasoning="错过法定期限可能导致权利丧失",
                ),
            )

        return actions

    @staticmethod
    def _build_evidence_gaps(fact_card: FactCard) -> List[str]:
        """List missing materials from fact_card as evidence gaps."""
        gaps: List[str] = []
        if fact_card.missing_materials:
            gaps.extend(fact_card.missing_materials)

        # Add generic gaps if list is short
        if len(gaps) < 2:
            gaps.append("当事人身份证明文件")
        if len(gaps) < 3:
            gaps.append("与案件相关的合同或协议原件")

        return gaps

    @staticmethod
    def _build_risk_warnings(fact_card: FactCard) -> List[str]:
        """Generate risk warnings based on conflicts and missing info."""
        warnings: List[str] = []

        if fact_card.conflicts:
            for conflict in fact_card.conflicts:
                warnings.append(f"事实冲突风险：{conflict}")

        if fact_card.missing_materials:
            warnings.append(
                f"材料缺失风险：当前缺少{len(fact_card.missing_materials)}项关键材料，"
                "可能影响案件处理效果。"
            )

        if not fact_card.case_id:
            warnings.append("案件信息不完整：未识别到案件编号，请核实。")

        if not fact_card.amount:
            warnings.append("金额未明确：涉及金额未识别，可能影响诉讼策略选择。")

        if fact_card.deadline:
            warnings.append(f"期限提醒：请密切关注 {fact_card.deadline} 前需完成的事项。")

        return warnings

    @staticmethod
    def _compute_rating(fact_card: FactCard) -> str:
        """Compute S/A/B/C/D rating based on fact card completeness.

        S: no issues
        A: minor gaps
        B: some conflicts
        C: major conflicts
        D: critical info missing
        """
        issues = 0

        # Critical info
        if not fact_card.case_id:
            issues += 2
        if not fact_card.court:
            issues += 1
        if not fact_card.parties:
            issues += 2
        if not fact_card.amount:
            issues += 1

        # Conflicts are weighted heavily
        issues += len(fact_card.conflicts) * 2

        # Missing materials
        issues += len(fact_card.missing_materials)

        if issues == 0:
            return "S"
        elif issues <= 2:
            return "A"
        elif issues <= 5:
            return "B"
        elif issues <= 8:
            return "C"
        else:
            return "D"

    @staticmethod
    def _build_draft_documents(
        fact_card: FactCard,
        identity: str,
        goal: str,
    ) -> List[DraftDocument]:
        """Build basic draft document templates based on identity and goal."""
        drafts: List[DraftDocument] = []
        identity_lower = (identity or "").strip()

        if identity_lower in ("投诉方", "投诉人", "消费者"):
            drafts.append(
                DraftDocument(
                    doc_type="投诉状",
                    title="投诉状",
                    content=_投诉状模板(fact_card),
                )
            )
        elif identity_lower in ("起诉方", "起诉方（原告）", "原告"):
            drafts.append(
                DraftDocument(
                    doc_type="起诉状",
                    title="民事起诉状",
                    content=_起诉状模板(fact_card),
                )
            )
        elif identity_lower in ("被诉方", "被告", "被诉方（被告）"):
            drafts.append(
                DraftDocument(
                    doc_type="答辩状",
                    title="民事答辩状",
                    content=_答辩状模板(fact_card),
                )
            )
        elif identity_lower in ("行政复议申请人", "复议申请人"):
            drafts.append(
                DraftDocument(
                    doc_type="行政复议申请书",
                    title="行政复议申请书",
                    content=_行政复议模板(fact_card),
                )
            )
        elif identity_lower in ("整理证据", "证据整理"):
            drafts.append(
                DraftDocument(
                    doc_type="证据目录",
                    title="证据目录",
                    content=_证据目录模板(fact_card),
                )
            )

        return drafts


# ======================================================================
# Document template helpers (private module-level functions)
# ======================================================================

def _extract_user_info(fact_card: FactCard) -> dict:
    """Extract detailed user info (ID, address, phone) from source_refs.
    
    Returns dict keyed by party name with gender, birth, address, id_number, phone.
    """
    import re
    info = {}
    if not fact_card.source_refs:
        return info
    
    for ref in fact_card.source_refs:
        excerpt = ref.excerpt or ""
        # Find name + ID pattern: "姓名，性别，...身份证号：XXX，电话：XXX"
        for party in fact_card.parties:
            if party.name and party.name in excerpt:
                if party.name not in info:
                    info[party.name] = {}
                # Extract gender
                m = re.search(r'([男女])', excerpt)
                if m:
                    info[party.name]['gender'] = m.group(1)
                # Extract birth date
                m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日出生', excerpt)
                if m:
                    info[party.name]['birth'] = f"{m.group(1)}年{m.group(2)}月{m.group(3)}日"
                # Extract address
                m = re.search(r'住([^\s，,。；]+)', excerpt)
                if m:
                    info[party.name]['address'] = m.group(1)
                # Extract ID number
                m = re.search(r'身份证号[：:]?\s*(\d{17}[\dX])', excerpt)
                if m:
                    info[party.name]['id_number'] = m.group(1)
                # Extract phone
                m = re.search(r'(?:电话|联系电话)[：:]?\s*(1[3-9]\d{9})', excerpt)
                if m:
                    info[party.name]['phone'] = m.group(1)
    return info


def _投诉状模板(fact_card: FactCard) -> str:
    """Generate complaint template text with case-specific content."""
    # Extract party info
    complainants = [p for p in fact_card.parties if p.role in ("投诉人", "原告")]
    respondents = [p for p in fact_card.parties if p.role in ("被投诉人", "被告")]
    
    complainant_info = ""
    if complainants:
        c = complainants[0]
        complainant_info = f"投诉人：{c.name}"
    else:
        complainant_info = "投诉人：请填写姓名"
    
    respondent_info = ""
    if respondents:
        r = respondents[0]
        respondent_info = f"被投诉人：{r.name}"
    else:
        respondent_info = "被投诉人：请填写姓名"
    
    # Build facts section
    facts_lines = []
    if fact_card.key_facts:
        for i, fact in enumerate(fact_card.key_facts[:6], 1):
            clean_fact = fact.replace("【待核对】", "").replace("【争议】", "").strip()
            if clean_fact and len(clean_fact) > 5:
                facts_lines.append(f"  {i}. {clean_fact}")
    facts_text = "\n".join(facts_lines) if facts_lines else \
        "  请根据实际情况详细描述投诉事实"
    
    amount_str = f"赔偿损失{fact_card.amount}" if fact_card.amount else "赔偿相关损失"
    
    # Evidence section
    evidence_lines = []
    if fact_card.source_refs:
        for i, ref in enumerate(fact_card.source_refs, 1):
            evidence_lines.append(f"  证据{i}：{ref.file_name}")
    evidence_text = "\n".join(evidence_lines) if evidence_lines else \
        "  请列明相关证据材料"
    
    return (
        f"投诉状\n\n"
        f"致：相关主管部门\n\n"
        f"{complainant_info}\n"
        f"{respondent_info}\n\n"
        f"案件编号：{fact_card.case_id or '请补充案号'}\n\n"
        f"投诉事实与理由：\n"
        f"{facts_text}\n\n"
        f"投诉请求：\n"
        f"  1. 依法查处被投诉人的违法行为；\n"
        f"  2. 维护投诉人的合法权益；\n"
        f"  3. {amount_str}；\n\n"
        f"证据清单：\n"
        f"{evidence_text}\n\n"
        f"以上投诉内容真实，请贵单位依法处理。\n\n"
        f"投诉人签名：_______________\n"
        f"日期：_______________\n"
    )


def _起诉状模板(fact_card: FactCard) -> str:
    """Generate complaint (lawsuit) template text with case-specific content."""
    # Extract party info
    plaintiffs = [p for p in fact_card.parties if p.role in ("原告", "上诉人")]
    defendants = [p for p in fact_card.parties if p.role in ("被告", "被上诉人")]
    
    # Build plaintiff info
    plaintiff_info = ""
    if plaintiffs:
        p = plaintiffs[0]
        plaintiff_info = f"原告：{p.name}"
    else:
        plaintiff_info = "原告：请填写姓名"
    
    # Build defendant info
    defendant_info = ""
    if defendants:
        d = defendants[0]
        defendant_info = f"被告：{d.name}"
    else:
        defendant_info = "被告：请填写姓名"
    
    # Build facts section
    facts_lines = []
    if fact_card.key_facts:
        for i, fact in enumerate(fact_card.key_facts[:6], 1):
            clean_fact = fact.replace("【待核对】", "").replace("【争议】", "").strip()
            if clean_fact and len(clean_fact) > 5:
                facts_lines.append(f"  {i}. {clean_fact}")
    facts_text = "\n".join(facts_lines) if facts_lines else \
        "  请根据实际情况详细描述事实与理由"
    
    # Evidence section
    evidence_lines = []
    if fact_card.source_refs:
        for i, ref in enumerate(fact_card.source_refs, 1):
            evidence_lines.append(f"  证据{i}：{ref.file_name}")
    evidence_text = "\n".join(evidence_lines) if evidence_lines else \
        "  请列明相关证据"
    
    case_reason = "合同纠纷" if any("合同" in f for f in fact_card.key_facts) else "民事纠纷"
    
    return (
        f"民事起诉状\n\n"
        f"{plaintiff_info}\n"
        f"{defendant_info}\n\n"
        f"案由：{case_reason}\n\n"
        f"诉讼请求：\n"
        f"  1. 判令被告向原告支付{'人民币' + fact_card.amount if fact_card.amount else '相应款项'}；\n"
        f"  2. 判令被告承担本案全部诉讼费用。\n\n"
        f"事实与理由：\n"
        f"{facts_text}\n\n"
        f"证据清单：\n"
        f"{evidence_text}\n\n"
        f"综上所述，原告的诉讼请求合法有据，恳请贵院依法支持。\n\n"
        f"此致\n{fact_card.court or '________人民法院'}\n\n"
        f"具状人：_______________\n"
        f"日期：_______________\n"
    )


def _答辩状模板(fact_card: FactCard) -> str:
    """Generate defense statement template text.
    
    Produces a case-specific defense document based on actual fact card data.
    """
    def _is_company(name: str) -> bool:
        return any(kw in name for kw in ('公司', '有限', '集团', '企业', '工厂', '商行', '商店', '事务所'))

    # Extract plaintiff and defendant info
    plaintiffs = [p for p in fact_card.parties if p.role in ("原告", "上诉人")]
    defendants = [p for p in fact_card.parties if p.role in ("被告", "被上诉人")]
    
    # Extract detailed user info from source_refs
    user_info = _extract_user_info(fact_card)
    
    # Build party info sections with actual data
    defendant_info = ""
    if defendants:
        d = defendants[0]
        if _is_company(d.name):
            defendant_info = (
                f"答辩人（被告）：{d.name}\n"
                f"住所地：____\n"
                f"统一社会信用代码：____\n"
                f"法定代表人：____，职务：____"
            )
        else:
            info = user_info.get(d.name, {})
            if info:
                defendant_info = (
                    f"答辩人（被告）：{d.name}，{info.get('gender', '____')}，"
                    f"{info.get('birth', '____年____月____日')}出生，"
                    f"{info.get('ethnicity', '汉族')}，"
                    f"住{info.get('address', '____')}"
                    f"，身份证号：{info.get('id_number', '____')}"
                    f"，联系电话：{info.get('phone', '____')}"
                )
            else:
                defendant_info = f"答辩人（被告）：{d.name}"
    else:
        defendant_info = "答辩人（被告）：____"
    
    plaintiff_info = ""
    for i, p in enumerate(plaintiffs):
        if _is_company(p.name):
            line = (
                f"被答辩人（原告）：{p.name}\n"
                f"住所地：____\n"
                f"法定代表人：____"
            )
        else:
            info = user_info.get(p.name, {})
            if info:
                line = (
                    f"被答辩人（原告）：{p.name}，{info.get('gender', '____')}，"
                    f"{info.get('birth', '____年____月____日')}出生，"
                    f"{info.get('ethnicity', '汉族')}，"
                    f"住{info.get('address', '____')}"
                    f"，身份证号：{info.get('id_number', '____')}"
                    f"，联系电话：{info.get('phone', '____')}"
                )
            else:
                line = f"被答辩人（原告）：{p.name}"
        plaintiff_info += line + "\n"
    
    # Build case info
    case_id_line = f"案号：{fact_card.case_id}" if fact_card.case_id else "案号：____"
    case_reason = "合同纠纷" if any("合同" in f for f in fact_card.key_facts) else "民事纠纷"
    
    # Build specific defense points based on key_facts
    defense_points = []
    if fact_card.key_facts:
        for i, fact in enumerate(fact_card.key_facts[:8], 1):
            # Clean up fact text - strip all distiller tags
            clean_fact = fact.replace("【待核对】", "").replace("【争议】", "").replace("【待补充】", "").replace("【冲突】", "").strip()
            if clean_fact and len(clean_fact) > 5:
                defense_points.append(f"关于第{i}项事实：{clean_fact}")
    
    defense_text = "\n".join(f"  {p}" for p in defense_points) if defense_points else \
        "  请根据案件材料补充具体答辩意见"
    
    # Build amount-related defense
    amount_defense = ""
    if fact_card.amount:
        amount_defense = (
        f"关于诉讼标的金额{fact_card.amount}的意见：\n"
        "  答辩人对原告主张的金额有异议，具体答辩意见如下：\n"
        "  1. 请原告提供完整的计算依据和证据支持；\n"
        "  2. 请核实已还款项是否已在主张金额中扣除；\n"
        "  3. 请核实利息/违约金计算标准是否符合合同约定和法律规定。"
    )
    else:
        amount_defense = "关于诉讼标的金额的意见：\n  请根据实际情况补充对金额的答辩意见"
    
    # Build evidence section
    evidence_lines = []
    if fact_card.source_refs:
        for i, ref in enumerate(fact_card.source_refs, 1):
            evidence_lines.append(f"  证据{i}：{ref.file_name}")
            if ref.excerpt:
                evidence_lines.append(f"    证明目的：{ref.excerpt[:100]}")
    evidence_text = "\n".join(evidence_lines) if evidence_lines else \
        "  请列明答辩人拟提交的证据材料"
    
    # Build missing materials as evidence gaps
    evidence_gaps = []
    if fact_card.missing_materials:
        for mat in fact_card.missing_materials[:5]:
            clean_mat = mat.replace("【待补充】", "").replace("【待核对】", "").replace("【争议】", "").replace("【冲突】", "").strip()
            if clean_mat:
                evidence_gaps.append(f"  - {clean_mat}")
    gaps_text = "\n".join(evidence_gaps) if evidence_gaps else ""
    
    gaps_section = ""
    if gaps_text:
        gaps_section = f"\n四、需要补充的证据材料\n{gaps_text}\n"
    
    return (
        f"民事答辩状\n\n"
        f"{defendant_info}\n"
        f"{plaintiff_info}\n\n"
        f"{case_id_line}\n"
        f"案由：{case_reason}\n\n"
        f"答辩人因{plaintiffs[0].name if plaintiffs else '原告'}诉答辩人{case_reason}一案，"
        f"现依法提出如下答辩意见：\n\n"
        f"一、案件基本事实\n"
        f"  根据案件材料，本案基本事实如下：\n"
        + "".join(f"  {i+1}. {f.replace('【待核对】', '').replace('【争议】', '').replace('【待补充】', '').replace('【冲突】', '').strip()}\n" 
                   for i, f in enumerate(fact_card.key_facts[:6]) if f.strip())
        + f"\n二、答辩意见\n"
        f"{defense_text}\n\n"
        f"三、关于诉讼标的金额\n"
        f"{amount_defense}\n"
        f"{gaps_section}\n"
        f"五、证据目录\n"
        f"{evidence_text}\n\n"
        f"六、答辩请求\n"
        f"  1. 请求法院依法查明案件事实；\n"
        f"  2. 请求法院依法公正裁判；\n"
        f"  3. 本案诉讼费用由原告承担。\n\n"
        f"综上所述，答辩人的答辩意见合法有据，请贵院依法审查并采纳。\n\n"
        f"此致\n{fact_card.court or '________人民法院'}\n\n"
        f"答辩人：_______________\n"
        f"日期：_______________\n\n"
        f"附：\n"
        f"1. 本答辩状副本一份；\n"
        f"2. 相关证据材料。"
    )


def _行政复议模板(fact_card: FactCard) -> str:
    """Generate administrative reconsideration application template."""
    # Extract applicant info
    applicants = [p for p in fact_card.parties if p.role in ("申请人",)]
    respondents = [p for p in fact_card.parties if p.role in ("被申请人",)]
    
    applicant_info = f"申请人：{applicants[0].name}" if applicants else "申请人：请填写姓名"
    respondent_info = f"被申请人：{respondents[0].name}" if respondents else f"被申请人：{fact_card.court or '请填写行政机关名称'}"
    
    # Build facts
    facts_lines = []
    if fact_card.key_facts:
        for i, fact in enumerate(fact_card.key_facts[:6], 1):
            clean_fact = fact.replace("【待核对】", "").replace("【争议】", "").strip()
            if clean_fact and len(clean_fact) > 5:
                facts_lines.append(f"  {i}. {clean_fact}")
    facts_text = "\n".join(facts_lines) if facts_lines else \
        "  请根据实际情况详细描述行政行为及相关事实"
    
    return (
        f"行政复议申请书\n\n"
        f"{applicant_info}\n"
        f"{respondent_info}\n\n"
        f"行政复议请求：\n"
        f"  1. 撤销被申请人作出的具体行政行为；\n"
        f"  2. 责令被申请人重新作出具体行政行为。\n\n"
        f"事实与理由：\n"
        f"{facts_text}\n\n"
        f"综上，被申请人的行政行为违反法律规定，损害了申请人的合法权益。\n"
        f"依据《中华人民共和国行政复议法》的相关规定，特申请行政复议。\n\n"
        f"此致\n\n"
        f"申请人签名：_______________\n"
        f"日期：_______________\n"
    )


def _证据目录模板(fact_card: FactCard) -> str:
    """Generate evidence catalog template text."""
    case_id = fact_card.case_id or '________'
    lines = [
        "证据目录\n",
        f"案件编号：{case_id}\n",
        "序号 | 证据名称 | 证据类型 | 证明目的",
        "-" * 60,
    ]

    if fact_card.source_refs:
        for i, ref in enumerate(fact_card.source_refs, 1):
            purpose = ref.excerpt[:80] if ref.excerpt else "证明相关事实"
            lines.append(f"  {i}  | {ref.file_name} | 书证 | {purpose}")
    else:
        lines.append("  1  | 请补充证据名称 | 书证 | 请补充证明目的")

    # Add missing materials as suggested evidence
    if fact_card.missing_materials:
        lines.append("")
        lines.append("建议补充的证据材料：")
        for i, mat in enumerate(fact_card.missing_materials[:5], 1):
            clean_mat = mat.replace("【待补充】", "").replace("【待核对】", "").replace("【争议】", "").replace("【冲突】", "").strip()
            if clean_mat:
                lines.append(f"  {i}. {clean_mat}")

    lines.append("")
    lines.append("整理人：_______________")
    lines.append("整理日期：_______________")
    return "\n".join(lines)
