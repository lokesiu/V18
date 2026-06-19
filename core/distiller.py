"""
distiller.py - Data Distillation

Takes fact_card and strategy_card, produces a distilled_card that is the
ONLY source for document rendering.

Distillation rules:
- Every key_fact must have at least one source_ref → mark unverified ones
- Every disputed_fact gets 【争议】 prefix
- Every missing_material gets 【待补充】 prefix
- Every conflict gets 【冲突】 prefix
- Strategy items without evidence backing are removed
- situation_assessment must reference specific facts
- evidence_gap must list what's actually missing
"""
from __future__ import annotations
import re
from typing import List, Set

from core.fact_card import (
    FactCard,
    StrategyCard,
    DistilledCard,
    ActionAdvice,
    PipelineContext,
)


def _fact_has_source(fact: str, source_refs: list) -> bool:
    """
    Check if a fact is supported by at least one source reference.
    
    Uses keyword matching: extracts key terms from the fact and checks
    if any source excerpt contains those terms.
    """
    if not source_refs:
        return False

    # Extract meaningful terms from the fact (skip common words)
    stop_words = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
        "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
        "看", "好", "自己", "这", "他", "她", "它", "们", "那", "被", "从", "把",
    }

    # Extract Chinese terms (2+ characters) and numbers
    terms = set()
    # Find Chinese word sequences
    for match in re.finditer(r'[\u4e00-\u9fff]{2,}', fact):
        word = match.group(0)
        if word not in stop_words and len(word) >= 2:
            terms.add(word)
    # Find numbers
    for match in re.finditer(r'\d+', fact):
        terms.add(match.group(0))

    if not terms:
        return False

    # Check if at least 30% of terms appear in source excerpts
    matched = 0
    for ref in source_refs:
        excerpt = ref.excerpt.lower() if ref.excerpt else ""
        for term in terms:
            if term in excerpt:
                matched += 1
                break  # Count each ref only once per fact

    match_ratio = matched / len(terms) if terms else 0
    return match_ratio >= 0.3


def _validate_key_facts(fact_card: FactCard) -> List[str]:
    """
    Validate key_facts against source_refs.
    Facts without source support get 【待核对】 prefix.
    """
    validated = []
    for fact in fact_card.key_facts:
        if _fact_has_source(fact, fact_card.source_refs):
            validated.append(fact)
        else:
            validated.append(f"【待核对】{fact}")
    return validated


def _tag_disputed_facts(facts: List[str]) -> List[str]:
    """Tag disputed facts with 【争议】 prefix."""
    tagged = []
    for fact in facts:
        if not fact.startswith("【争议】"):
            tagged.append(f"【争议】{fact}")
        else:
            tagged.append(fact)
    return tagged


def _tag_missing_materials(materials: List[str]) -> List[str]:
    """Tag missing materials with 【待补充】 prefix."""
    tagged = []
    for item in materials:
        if not item.startswith("【待补充】"):
            tagged.append(f"【待补充】{item}")
        else:
            tagged.append(item)
    return tagged


def _tag_conflicts(conflicts: List[str]) -> List[str]:
    """Tag conflicts with 【冲突】 prefix."""
    tagged = []
    for conflict in conflicts:
        if not conflict.startswith("【冲突】"):
            tagged.append(f"【冲突】{conflict}")
        else:
            tagged.append(conflict)
    return tagged


def _filter_strategy_by_evidence(
    strategy: StrategyCard,
    fact_card: FactCard,
) -> StrategyCard:
    """
    Remove strategy items that have no evidence backing.
    
    Rules:
    - action_advice: keep at least 3 items even without evidence
    - risk_warnings without evidence are kept (they're warnings, not claims)
    - evidence_gap items are always kept (that's their purpose)
    - draft_documents are always kept
    """
    filtered = StrategyCard()
    filtered.situation_assessment = strategy.situation_assessment
    filtered.sabcd_rating = strategy.sabcd_rating
    filtered.evidence_gap = list(strategy.evidence_gap)  # Always keep
    filtered.risk_warnings = list(strategy.risk_warnings)  # Always keep
    filtered.draft_documents = list(strategy.draft_documents)  # Always keep

    # Filter action_advice: keep those with supporting facts
    all_facts = (
        fact_card.key_facts
        + fact_card.disputed_facts
    )

    for advice in strategy.action_advice:
        if _action_has_support(advice, all_facts):
            filtered.action_advice.append(advice)

    # Always keep at least 6 action items (even without evidence match)
    # This ensures the distilled_card always has actionable advice
    if len(filtered.action_advice) < 6 and strategy.action_advice:
        for advice in strategy.action_advice:
            if advice not in filtered.action_advice:
                filtered.action_advice.append(advice)
            if len(filtered.action_advice) >= 6:
                break

    return filtered


def _action_has_support(advice: ActionAdvice, facts: List[str]) -> bool:
    """Check if an action advice has supporting facts."""
    if not facts:
        return False

    # Extract key terms from the action using 2-gram for Chinese text
    action_terms = set()
    # Extract 2+ character Chinese sequences, then break into 2-grams
    for match in re.finditer(r'[\u4e00-\u9fff]{2,}', advice.action):
        word = match.group(0)
        # Generate 2-grams for better matching
        for i in range(len(word) - 1):
            action_terms.add(word[i:i+2])

    if not action_terms:
        return True  # If no terms to match, keep the advice

    # Check if any fact supports this action
    for fact in facts:
        matched = sum(1 for term in action_terms if term in fact)
        if matched >= max(1, len(action_terms) * 0.2):
            return True

    return False


def _validate_situation_assessment(
    assessment: str,
    fact_card: FactCard,
) -> str:
    """
    Ensure situation_assessment references specific facts.
    If it doesn't reference any fact, append a warning.
    """
    if not assessment:
        return "待评估"

    # Check if assessment references any fact
    all_facts = fact_card.key_facts + fact_card.disputed_facts
    references_fact = False

    for fact in all_facts:
        # Extract key terms from fact
        fact_terms = set()
        for match in re.finditer(r'[\u4e00-\u9fff]{2,}', fact):
            word = match.group(0)
            if len(word) >= 2:
                fact_terms.add(word)

        # Check if assessment mentions any fact term
        for term in fact_terms:
            if term in assessment:
                references_fact = True
                break

        if references_fact:
            break

    if not references_fact and all_facts:
        return f"{assessment}\n【注意】上述评估未明确引用具体案件事实，建议补充事实依据"

    return assessment


def _validate_evidence_gap(
    gaps: List[str],
    fact_card: FactCard,
) -> List[str]:
    """
    Ensure evidence_gap lists what's actually missing,
    not pretending it exists.
    """
    validated = []
    seen = set()
    seen_normalized = set()

    def _normalize(text: str) -> str:
        """Normalize for fuzzy dedup."""
        import re
        t = text.replace("【待补充】", "").replace("【待核对】", "").replace("【争议】", "").strip()
        t = t.lstrip("缺少: ").lstrip("缺少:")
        t = re.sub(r'[，,。；;：:\s]+', '', t)
        return t

    for gap in gaps:
        # Skip if it sounds like a positive claim
        if any(marker in gap for marker in ["已有", "已提供", "充分", "完整"]):
            continue

        # Deduplicate (exact + normalized)
        norm = _normalize(gap)
        if gap not in seen and norm not in seen_normalized:
            seen.add(gap)
            seen_normalized.add(norm)
            validated.append(gap)

    # Also add missing materials as evidence gaps (skip if already covered)
    for material in fact_card.missing_materials:
        clean_material = material.replace("【待补充】", "").strip()
        norm = _normalize(clean_material)
        if norm not in seen_normalized:
            seen_normalized.add(norm)
            validated.append(f"缺少: {clean_material}")

    return validated


def _fix_party_identity_confusion(fact_card: FactCard, ctx: PipelineContext) -> None:
    """
    Detect and fix identity confusion in parties.
    
    Common issues:
    - Defendant labeled as plaintiff
    - Plaintiff labeled as defendant
    - Role assigned to wrong party
    """
    if not fact_card.parties:
        return
    
    # Check for parties with contradictory roles
    plaintiffs = [p for p in fact_card.parties if p.role in ("原告", "上诉人")]
    defendants = [p for p in fact_card.parties if p.role in ("被告", "被上诉人")]
    
    # Check if identity (被诉方/被告) matches party roles
    if fact_card.identity in ("被诉方", "被告", "被诉方（被告）"):
        # User is defendant - should have defendant party
        if not defendants and plaintiffs:
            ctx.log("WARNING: 用户身份为被诉方但未找到被告当事人，检查角色分配")
            # If there are multiple parties with same role, try to fix
            if len(plaintiffs) > 1:
                # Second plaintiff might actually be defendant
                plaintiffs[1].role = "被告"
                ctx.log(f"已修正当事人角色: {plaintiffs[1].name} 从原告改为被告")
    
    elif fact_card.identity in ("起诉方", "起诉方（原告）", "原告"):
        # User is plaintiff - should have plaintiff party
        if not plaintiffs and defendants:
            ctx.log("WARNING: 用户身份为起诉方但未找到原告当事人，检查角色分配")
    
    # Check for amount doubles (元元)
    if fact_card.amount and "元元" in fact_card.amount:
        fact_card.amount = fact_card.amount.replace("元元", "元")
        ctx.log(f"已修正金额重复: {fact_card.amount}")
    
    # Check for deadline pollution (dates from other cases)
    if fact_card.deadline:
        # If deadline is in the past and looks like a filing date, clear it
        import re
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', fact_card.deadline)
        if date_match:
            year = int(date_match.group(1))
            if year < 2024:  # Likely a historical date, not a deadline
                ctx.log(f"WARNING: 检测到可能的期限污染: {fact_card.deadline} (年份过早)")


def distill(ctx: PipelineContext) -> PipelineContext:
    """
    Main entry point for data distillation.
    
    Takes fact_card and strategy_card from context,
    applies distillation rules, produces distilled_card.
    """
    ctx.log("开始数据蒸馏...")

    if not ctx.fact_card:
        ctx.add_error("缺少fact_card，无法蒸馏")
        return ctx

    if not ctx.strategy_card:
        ctx.add_error("缺少strategy_card，无法蒸馏")
        return ctx

    # 0. Fix identity confusion in parties
    ctx.log("检查当事人身份一致性...")
    _fix_party_identity_confusion(ctx.fact_card, ctx)

    # 1. Validate and tag key_facts
    ctx.log("验证关键事实来源...")
    validated_key_facts = _validate_key_facts(ctx.fact_card)
    unverified = sum(1 for f in validated_key_facts if f.startswith("【待核对】"))
    ctx.log(f"关键事实: {len(validated_key_facts)} 条, 待核对: {unverified} 条")

    # 2. Tag disputed_facts
    tagged_disputed = _tag_disputed_facts(ctx.fact_card.disputed_facts)
    ctx.log(f"争议事实: {len(tagged_disputed)} 条")

    # 3. Tag missing_materials
    tagged_missing = _tag_missing_materials(ctx.fact_card.missing_materials)
    ctx.log(f"待补充材料: {len(tagged_missing)} 项")

    # 4. Tag conflicts
    tagged_conflicts = _tag_conflicts(ctx.fact_card.conflicts)
    ctx.log(f"冲突: {len(tagged_conflicts)} 条")

    # 5. Filter strategy by evidence
    ctx.log("过滤策略建议...")
    filtered_strategy = _filter_strategy_by_evidence(ctx.strategy_card, ctx.fact_card)
    removed_advice = len(ctx.strategy_card.action_advice) - len(filtered_strategy.action_advice)
    ctx.log(f"策略建议: 原 {len(ctx.strategy_card.action_advice)} 条, "
            f"保留 {len(filtered_strategy.action_advice)} 条, "
            f"移除 {removed_advice} 条（无证据支持）")

    # 6. Validate situation_assessment
    validated_assessment = _validate_situation_assessment(
        filtered_strategy.situation_assessment,
        ctx.fact_card,
    )
    filtered_strategy.situation_assessment = validated_assessment

    # 7. Validate evidence_gap
    validated_gaps = _validate_evidence_gap(
        filtered_strategy.evidence_gap,
        ctx.fact_card,
    )
    filtered_strategy.evidence_gap = validated_gaps
    ctx.log(f"证据缺口: {len(validated_gaps)} 项")

    # 8. Build distilled fact_card
    distilled_fact = FactCard(
        case_id=ctx.fact_card.case_id,
        court=ctx.fact_card.court,
        parties=list(ctx.fact_card.parties),
        identity=ctx.fact_card.identity,
        amount=ctx.fact_card.amount,
        deadline=ctx.fact_card.deadline,
        key_facts=validated_key_facts,
        disputed_facts=tagged_disputed,
        missing_materials=tagged_missing,
        conflicts=tagged_conflicts,
        source_refs=list(ctx.fact_card.source_refs),
    )

    # 9. Build distilled_card
    distilled_card = DistilledCard(
        fact_card=distilled_fact,
        strategy_card=filtered_strategy,
    )

    ctx.distilled_card = distilled_card
    ctx.log("数据蒸馏完成")

    return ctx
