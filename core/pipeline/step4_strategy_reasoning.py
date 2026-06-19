"""
step4_strategy_reasoning.py - Phase 2: 策略推演 (Strategy Reasoning)

演绎推理 + 归纳推理，分析核心争议焦点，输出救济路径和实体抗辩思路。
不生成文书草稿 — 文书由 Step 6 独立生成。
"""
from __future__ import annotations

import json
import logging

from core.fact_card import PipelineContext, StrategyCard, ActionAdvice
from core.ai_config import is_api_configured
from core.ai_mode import AIModeTracker, AIStatus
from core.pipeline.schemas import StrategyReasoningResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一名资深诉讼律师和法律策略分析师。根据已提炼的案件事实，进行深度策略推演。

分析框架：
1. 【演绎推理】从法律规范出发，将本案事实代入构成要件，逐项分析
2. 【归纳推理】从本案事实模式出发，检索类案裁判规律，归纳胜败关键
3. 【救济路径】评估一审/二审/再审各阶段的可行性和风险
4. 【实体抗辩】针对对方每项请求，提出具体抗辩思路

评级标准：
- S: 证据充分、事实清楚、法律依据明确，胜诉概率极高
- A: 证据较充分、主要事实清楚，成功概率高
- B: 证据部分充分、部分事实需要补充，成功概率中等
- C: 证据不足、事实存在争议，成功概率较低
- D: 证据严重不足、事实不清，成功概率极低

严禁使用省略号或占位符。每条建议必须具体、可操作。
输出必须严格符合 JSON Schema。"""


def step4_strategy_reasoning(ctx: PipelineContext) -> PipelineContext:
    """Phase 2: 策略推演 — LLM 演绎+归纳推理。"""
    ctx.log("Step 4: 策略推演 — 调用 LLM 进行演绎推理与归纳推理")

    if ctx.fact_card is None:
        ctx.add_error("fact_card 为空，无法执行策略推演")
        return ctx

    tracker = getattr(ctx, '_ai_mode_tracker', None)
    if tracker is None:
        tracker = AIModeTracker()
        ctx._ai_mode_tracker = tracker

    if not is_api_configured():
        ctx.log("Step 4: API 未配置，使用本地规则生成")
        tracker.api_b_status = AIStatus.NOT_CONFIGURED
        ctx.strategy_card = _create_fallback(ctx)
        return ctx

    try:
        from core.ai_client import AIClient

        fact_data = ctx.fact_card.to_dict()
        extra = getattr(ctx, '_fact_extraction_result', None)
        if extra:
            fact_data["timeline"] = [t.model_dump() for t in extra.timeline]
            fact_data["fund_flows"] = [f.model_dump() for f in extra.fund_flows]
            fact_data["claims"] = extra.claims

        schema_hint = StrategyReasoningResult.model_json_schema()
        user_msg = (
            f"## 当事人身份\n{ctx.identity}\n\n"
            f"## 处理目标\n{ctx.goal}\n\n"
            f"## 事实卡片\n```json\n{json.dumps(fact_data, ensure_ascii=False, indent=2)}\n```\n\n"
            f"## 输出 JSON Schema\n```json\n{json.dumps(schema_hint, ensure_ascii=False, indent=2)}\n```"
        )

        tracker.start_api_b()
        client = AIClient()
        response = client.call_api_b(SYSTEM_PROMPT, user_msg)
        tracker.end_api_b(success=response.success, latency_ms=response.latency_ms)

        if not response.success or not response.content:
            raise RuntimeError(f"LLM 策略推演失败: {response.error}")

        result = _parse_and_validate(response.content, ctx)
        if result is None:
            raise RuntimeError("LLM 返回无法解析为 StrategyReasoningResult")

        _apply_to_context(result, ctx)
        ctx.log(
            f"Step 4 完成: 评级 {result.sabcd_rating}, "
            f"{len(result.core_disputes)} 个争议焦点, "
            f"{len(result.relief_paths)} 条救济路径, "
            f"{len(result.entity_defense)} 条抗辩思路"
        )

    except Exception as exc:
        ctx.log(f"WARNING: 策略推演异常: {exc}")
        tracker.api_b_status = AIStatus.FAILED
        from core.pipeline import AIProviderError
        raise AIProviderError(f"策略推演失败: {exc}")

    return ctx


def _parse_and_validate(raw: str, ctx: PipelineContext) -> StrategyReasoningResult | None:
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
        import re
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return None
        else:
            return None

    try:
        return StrategyReasoningResult.model_validate(data)
    except Exception as exc:
        logger.warning("Pydantic 校验失败: %s", exc)
        return None


def _apply_to_context(result: StrategyReasoningResult, ctx: PipelineContext):
    """将 Pydantic 结果映射到 PipelineContext.strategy_card。"""
    sc = StrategyCard()
    sc.situation_assessment = result.situation_assessment
    sc.sabcd_rating = result.sabcd_rating
    sc.evidence_gap = result.evidence_gap
    sc.risk_warnings = result.risk_warnings

    for advice_text in result.action_advice:
        sc.action_advice.append(ActionAdvice(
            action=advice_text,
            priority="B",
            reasoning="",
        ))

    ctx.strategy_card = sc
    ctx._strategy_reasoning_result = result  # type: ignore[attr-defined]


def _create_fallback(ctx: PipelineContext) -> StrategyCard:
    """API 未配置时的本地降级。"""
    from core.providers.api_b_client import ApiBClient
    client = ApiBClient()
    return client._local_generate(ctx.fact_card, ctx.identity, ctx.goal)
