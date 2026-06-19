"""
step5_distill.py - Pipeline Step 5: Fact + Strategy Distillation

Merges the FactCard (from Steps 2-3) with the StrategyCard (from Step 4)
into a single DistilledCard. Validates that all claims have source
references and that the combined data is internally consistent.
"""
from __future__ import annotations

from core.fact_card import PipelineContext, DistilledCard
from core.distiller import distill


def step5_distill(ctx: PipelineContext) -> PipelineContext:
    """Merge fact_card + strategy_card into distilled_card, validate sources.

    Delegates to core.distiller.distill which:
    - Combines ctx.fact_card and ctx.strategy_card into a DistilledCard
    - Cross-validates facts against strategy recommendations
    - Ensures every key fact and action item has source references
    - Produces the final distilled data structure used for template filling

    Args:
        ctx: PipelineContext with fact_card and strategy_card populated.

    Returns:
        PipelineContext with distilled_card populated.
    """
    ctx.log("Step 5: 蒸馏合并 - 将事实卡片与策略卡片合并为蒸馏卡片")

    if ctx.fact_card is None:
        ctx.add_error("fact_card 为空，无法执行蒸馏合并")
        return ctx

    if ctx.strategy_card is None:
        ctx.add_error("strategy_card 为空，无法执行蒸馏合并")
        return ctx

    try:
        distill(ctx)
    except ValueError as exc:
        ctx.add_error(f"蒸馏合并数据格式错误: {exc}")
        return ctx
    except TypeError as exc:
        ctx.add_error(f"蒸馏合并类型错误: {exc}")
        return ctx
    except Exception as exc:
        ctx.add_error(f"蒸馏合并过程中发生未知错误: {exc}")
        return ctx

    if ctx.distilled_card is None:
        ctx.add_error("蒸馏合并完成但 distilled_card 仍为空")
        return ctx

    # Validate source coverage
    fc = ctx.distilled_card.fact_card
    sc = ctx.distilled_card.strategy_card

    fact_source_count = len(fc.source_refs) if fc else 0
    key_facts_count = len(fc.key_facts) if fc else 0
    advice_count = len(sc.action_advice) if sc else 0
    gap_count = len(sc.evidence_gap) if sc else 0
    draft_count = len(sc.draft_documents) if sc else 0

    ctx.log(
        f"Step 5 完成: 蒸馏卡片生成成功 - "
        f"{key_facts_count} 条关键事实, "
        f"{fact_source_count} 条来源引用, "
        f"{advice_count} 条行动建议, "
        f"{gap_count} 项证据缺口, "
        f"{draft_count} 份文书草稿"
    )

    # Validate source references coverage
    unsourced_facts = []
    if fc and fc.key_facts and fc.source_refs:
        # Check if each fact has at least one source reference mention
        for fact in fc.key_facts:
            has_source = any(
                fact[:10] in ref.excerpt or ref.excerpt[:10] in fact
                for ref in fc.source_refs
            )
            if not has_source:
                unsourced_facts.append(fact[:50])

    if unsourced_facts:
        ctx.log(f"WARNING: {len(unsourced_facts)} 条关键事实缺少来源引用:")
        for fact_preview in unsourced_facts[:5]:
            ctx.log(f"  - {fact_preview}...")

    # Log evidence gap summary
    if sc and sc.evidence_gap:
        ctx.log("证据缺口清单:")
        for gap in sc.evidence_gap:
            ctx.log(f"  - {gap}")

    # Save distilled card to _internal subfolder if output_dir is available
    if ctx.output_dir:
        import os
        internal_dir = os.path.join(ctx.output_dir, "_internal")
        distilled_path = os.path.join(internal_dir, "distilled_card.json")
        try:
            os.makedirs(internal_dir, exist_ok=True)
            ctx.distilled_card.save(distilled_path)
            ctx.log(f"蒸馏卡片已保存: {distilled_path}")
        except OSError as exc:
            ctx.log(f"WARNING: 无法保存蒸馏卡片到 {distilled_path}: {exc}")

    return ctx
