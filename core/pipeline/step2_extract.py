"""
step2_extract.py - Pipeline Step 2: Fact Extraction

Parses the raw texts collected in Step 1 to build a structured FactCard
containing parties, key facts, disputed facts, missing materials, and
source references.

Critical step - extraction failure means downstream steps cannot proceed.
"""
from __future__ import annotations

from core.fact_card import PipelineContext, FactCard
from core.extract import extract_facts


def step2_extract(ctx: PipelineContext) -> PipelineContext:
    """Extract structured facts from raw_texts into ctx.fact_card.

    Delegates to core.extract.extract_facts which:
    - Analyzes ctx.raw_texts using NLP / rule-based extraction
    - Builds a FactCard with parties, key_facts, disputed_facts, etc.
    - Populates ctx.fact_card with the result

    Args:
        ctx: PipelineContext with raw_texts and file_list populated from Step 1.

    Returns:
        PipelineContext with fact_card populated,
        or errors appended if extraction failed.
    """
    ctx.log("Step 2: 事实提取 - 从原始文本中提取结构化事实信息")

    if not ctx.raw_texts:
        ctx.add_error("无原始文本可供提取 (raw_texts 为空)，请先执行 Step 1")
        return ctx

    # Ensure fact_card exists as a base object
    if ctx.fact_card is None:
        ctx.fact_card = FactCard()

    # Set identity on the fact card from context
    ctx.fact_card.identity = ctx.identity

    try:
        extract_facts(ctx)
    except ValueError as exc:
        ctx.add_error(f"事实提取数据格式错误: {exc}")
        return ctx
    except RuntimeError as exc:
        ctx.add_error(f"事实提取引擎运行失败: {exc}")
        return ctx
    except Exception as exc:
        ctx.add_error(f"事实提取过程中发生未知错误: {exc}")
        return ctx

    # Validate extracted fact card
    if ctx.fact_card is None:
        ctx.add_error("事实提取完成但 fact_card 仍为空")
        return ctx

    fact_count = len(ctx.fact_card.key_facts)
    party_count = len(ctx.fact_card.parties)
    source_count = len(ctx.fact_card.source_refs)
    missing_count = len(ctx.fact_card.missing_materials)

    ctx.log(
        f"Step 2 完成: 提取到 {party_count} 个当事人, "
        f"{fact_count} 条关键事实, "
        f"{source_count} 条来源引用, "
        f"{missing_count} 项缺失材料"
    )

    # Log extracted parties
    for party in ctx.fact_card.parties:
        ctx.log(f"  当事人: {party.name} ({party.role})")

    # Log any missing materials as warnings
    for material in ctx.fact_card.missing_materials:
        ctx.log(f"  缺失材料: {material}")

    # Log conflicts
    for conflict in ctx.fact_card.conflicts:
        ctx.log(f"  事实冲突: {conflict}")

    return ctx
