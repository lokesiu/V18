"""
core.pipeline - Pipeline Orchestrator (CoT Multi-Step Architecture)

Phase 1: 事实蒸馏 (step1→step2→step3)
Phase 2: 策略推演 (step4)
Phase 3: 独立文书生成 (step5→step6→step7→step8)

Steps 1-2 are critical - pipeline stops on error.
Steps 3-8 degrade gracefully, logging warnings but continuing.
"""
from __future__ import annotations

from typing import Callable, Optional

from core.fact_card import PipelineContext
from core.pipeline.step1_intake import step1_intake
from core.pipeline.step2_extract import step2_extract
from core.pipeline.step3_fact_extract import step3_fact_extract
from core.pipeline.step4_strategy_reasoning import step4_strategy_reasoning
from core.pipeline.step5_distill import step5_distill
from core.pipeline.step6_llm_generate import step6_llm_generate
from core.pipeline.step7_render import step7_render
from core.pipeline.step8_quality_gate import step8_quality_gate


class AIProviderError(Exception):
    """Custom exception for AI provider failures - triggers fail-fast."""
    pass


PIPELINE_STEPS = [
    ("step1_intake", step1_intake),
    ("step2_extract", step2_extract),
    ("step3_fact_extract", step3_fact_extract),
    ("step4_strategy_reasoning", step4_strategy_reasoning),
    ("step5_distill", step5_distill),
    ("step6_llm_generate", step6_llm_generate),
    ("step7_render", step7_render),
    ("step8_quality_gate", step8_quality_gate),
]

CRITICAL_STEPS = {1, 2}

STAGE_NAMES = {
    "step1_intake": "读取材料",
    "step2_extract": "提取事实",
    "step3_fact_extract": "事实蒸馏",
    "step4_strategy_reasoning": "策略推演",
    "step5_distill": "蒸馏合并",
    "step6_llm_generate": "文书生成",
    "step7_render": "文档渲染",
    "step8_quality_gate": "质量检查",
}


def run_pipeline(
    ctx: PipelineContext,
    on_step: Optional[Callable[[int, str, str], None]] = None,
) -> PipelineContext:
    """Run all 8 pipeline steps sequentially. Stop on critical failure."""
    total_steps = len(PIPELINE_STEPS)
    ctx.log(f"=== 明证台 V18 CoT Pipeline 启动 ===")
    ctx.log(f"输入目录: {ctx.input_dir}")
    ctx.log(f"输出目录: {ctx.output_dir}")
    ctx.log(f"身份: {ctx.identity}")
    ctx.log(f"目标: {ctx.goal}")
    ctx.log(f"共 {total_steps} 个步骤 (3阶段CoT架构)")

    for i, (step_name, step_fn) in enumerate(PIPELINE_STEPS):
        step_num = i + 1
        display_name = STAGE_NAMES.get(step_name, step_name)
        ctx.log(f"--- Pipeline Step {step_num}/{total_steps}: {step_name} ---")

        if on_step:
            on_step(i, display_name, "start")

        try:
            ctx = step_fn(ctx)
        except KeyboardInterrupt:
            ctx.log(f"Pipeline 被用户中断于 Step {step_num}")
            ctx.add_error(f"Pipeline 被用户中断于 Step {step_num}: {step_name}")
            if on_step:
                on_step(i, display_name, "failed")
            break
        except MemoryError:
            ctx.add_error(f"Step {step_num} ({step_name}): 内存不足，Pipeline 终止")
            ctx.log(f"CRITICAL: 内存不足于 Step {step_num}，停止 Pipeline")
            if on_step:
                on_step(i, display_name, "failed")
            break
        except AIProviderError as exc:
            ctx.add_error(f"AI 服务调用失败: {exc}")
            ctx.log(f"CRITICAL: AI 服务调用失败于 Step {step_num}，停止 Pipeline")
            if on_step:
                on_step(i, display_name, "failed")
            break
        except Exception as exc:
            ctx.add_error(
                f"Step {step_num} ({step_name}): 未捕获异常 - {type(exc).__name__}: {exc}"
            )
            if on_step:
                on_step(i, display_name, "failed")
            if step_num in CRITICAL_STEPS:
                ctx.log(f"CRITICAL: Step {step_num} 未捕获异常，停止 Pipeline")
                break
            else:
                ctx.log(f"WARNING: Step {step_num} 未捕获异常，但非关键步骤，继续执行")

        if ctx.errors and step_num in CRITICAL_STEPS:
            ctx.log(f"CRITICAL: Step {step_num} 产生错误，停止 Pipeline")
            if on_step:
                on_step(i, display_name, "failed")
            break

        if on_step:
            on_step(i, display_name, "done")

        if step_name in ("step2_extract", "step3_fact_extract"):
            gate_result = _run_quality_gate(ctx, step_name)
            if gate_result is not None:
                ctx._quality_gate_result = gate_result  # type: ignore[attr-defined]
                if gate_result.status == "blocked":
                    ctx.log(f"质量门禁拦截于 {display_name}，Pipeline 终止")
                    ctx.add_error(f"质量门禁拦截: {gate_result.blocking_issues[0].message}")
                    ctx._quality_blocked = True  # type: ignore[attr-defined]
                    break

    ctx.log(f"=== Pipeline 执行完成 ===")
    ctx.log(f"总日志条目: {len(ctx.logs)}")
    ctx.log(f"总错误数: {len(ctx.errors)}")

    if ctx.errors:
        ctx.log("错误摘要:")
        for idx, error in enumerate(ctx.errors, 1):
            ctx.log(f"  {idx}. {error}")
    else:
        ctx.log("所有步骤执行成功，无错误")

    if ctx.fact_card:
        ctx.log(f"FactCard: {len(ctx.fact_card.key_facts)} 条关键事实")
    if ctx.strategy_card:
        ctx.log(f"StrategyCard: {ctx.strategy_card.sabcd_rating} 评级")
    if ctx.distilled_card:
        ctx.log(f"DistilledCard: 已生成")
    llm_docs = getattr(ctx, '_llm_generated_docs', {})
    if llm_docs:
        ctx.log(f"LLM文书: {len(llm_docs)} 份已生成")

    return ctx


def _run_quality_gate(ctx: PipelineContext, step_name: str):
    """Run the appropriate quality gate for the given step."""
    try:
        from core.quality.pipeline_gates import run_step2_gate, run_step3_gate

        if step_name == "step2_extract":
            result = run_step2_gate(ctx)
        elif step_name == "step3_fact_extract":
            result = run_step3_gate(ctx)
        else:
            return None

        if result.status == "passed":
            ctx.log(f"  质量门禁通过: {step_name}")
        elif result.status == "warning":
            for issue in result.warning_issues:
                ctx.log(f"  质量警告: {issue.message}")
        elif result.status == "blocked":
            for issue in result.blocking_issues:
                ctx.log(f"  质量拦截: {issue.message}")

        return result

    except Exception as exc:
        ctx.log(f"  质量门禁检查异常: {exc}")
        return None
