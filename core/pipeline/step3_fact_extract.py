"""
step3_fact_extract.py - Phase 1: 事实蒸馏 (Fact Distillation)

精简 Prompt，只提取时间线/当事人/资金流水/诉讼请求。
Pydantic 强制结构输出，防止 LLM 幻觉破坏下游 Context_Object。
"""
from __future__ import annotations

import json
import logging

from core.fact_card import PipelineContext, FactCard, Party, SourceRef
from core.ai_config import is_api_configured
from core.ai_mode import AIModeTracker, AIStatus
from core.pipeline.schemas import FactExtractionResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个法律事实提取器。你的唯一任务是从案卷材料中提取结构化事实。

严格规则：
1. 仅提取案件的时间线、原被告基本信息、资金流水和诉讼请求
2. 不要进行法律分析或给出意见
3. 不要编造或推测任何不在材料中的事实
4. 金额必须精确到分，日期必须精确到日
5. 每个提取项必须可追溯到原始材料

输出必须严格符合 JSON Schema，不要输出任何多余文字。"""


def step3_fact_extract(ctx: PipelineContext) -> PipelineContext:
    """Phase 1: 事实蒸馏 — LLM 结构化事实提取。"""
    ctx.log("Step 3: 事实蒸馏 — 调用 LLM 提取结构化事实")

    if not ctx.raw_texts:
        ctx.add_error("无原始文本可供提取 (raw_texts 为空)")
        return ctx

    tracker = getattr(ctx, '_ai_mode_tracker', None)
    if tracker is None:
        tracker = AIModeTracker()
        ctx._ai_mode_tracker = tracker

    if not is_api_configured():
        ctx.log("Step 3: API 未配置，跳过 LLM 事实蒸馏，保留规则提取结果")
        tracker.api_a_status = AIStatus.NOT_CONFIGURED
        return ctx

    try:
        from core.ai_client import AIClient

        combined_text = "\n\n---\n\n".join(ctx.raw_texts)
        if len(combined_text) > 60000:
            combined_text = combined_text[:60000]
            ctx.log("  原始文本过长，截断至 60000 字符")

        schema_hint = FactExtractionResult.model_json_schema()
        user_msg = (
            f"以下是本案全部案卷材料，请提取结构化事实。\n\n"
            f"## 案卷材料\n\n{combined_text}\n\n"
            f"## 输出 JSON Schema\n\n"
            f"```json\n{json.dumps(schema_hint, ensure_ascii=False, indent=2)}\n```"
        )

        tracker.start_api_a()
        client = AIClient()
        response = client.call_api_a(SYSTEM_PROMPT, user_msg)
        tracker.end_api_a(success=response.success, latency_ms=response.latency_ms)

        if not response.success or not response.content:
            raise RuntimeError(f"LLM 事实蒸馏失败: {response.error}")

        result = _parse_and_validate(response.content, ctx)
        if result is None:
            raise RuntimeError("LLM 返回无法解析为 FactExtractionResult")

        _apply_to_context(result, ctx)
        ctx.log(
            f"Step 3 完成: {len(result.parties)} 个当事人, "
            f"{len(result.timeline)} 个时间线事件, "
            f"{len(result.key_facts)} 条关键事实, "
            f"{len(result.fund_flows)} 笔资金流水"
        )

    except Exception as exc:
        ctx.log(f"WARNING: 事实蒸馏异常: {exc}")
        tracker.api_a_status = AIStatus.FAILED
        from core.pipeline import AIProviderError
        raise AIProviderError(f"事实蒸馏失败: {exc}")

    return ctx


def _parse_and_validate(raw: str, ctx: PipelineContext) -> FactExtractionResult | None:
    """从 LLM 原始输出中解析 Pydantic 模型。"""
    content = raw.strip()
    for tag in ("```json", "```"):
        if tag in content:
            start = content.index(tag) + len(tag)
            end = content.index("```", start) if "```" in content[start:] else len(content)
            content = content[start:end].strip()
            break

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("LLM 输出非法 JSON，尝试容错解析")
        data = _try_salvage_json(content)
        if data is None:
            return None

    try:
        return FactExtractionResult.model_validate(data)
    except Exception as exc:
        logger.warning("Pydantic 校验失败: %s", exc)
        return None


def _try_salvage_json(raw: str) -> dict | None:
    """尝试从残缺 JSON 中挽救数据。"""
    import re
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
    return None


def _apply_to_context(result: FactExtractionResult, ctx: PipelineContext):
    """将 Pydantic 结果映射到 PipelineContext.fact_card。"""
    fc = ctx.fact_card or FactCard()
    fc.case_id = result.case_id
    fc.court = result.court
    fc.parties = [Party(name=p.name, role=p.role) for p in result.parties]
    fc.key_facts = result.key_facts
    fc.disputed_facts = result.disputed_facts
    fc.missing_materials = result.missing_materials
    fc.conflicts = result.conflicts
    fc.identity = ctx.identity

    ctx.fact_card = fc

    ctx._fact_extraction_result = result  # type: ignore[attr-defined]
