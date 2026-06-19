"""
core/workflow/dual_ai_orchestrator.py - Dual AI Workflow Orchestrator

Runs 9-stage pipeline with DeepSeek extract+strategy, MiMo critique+review.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from core.fact_card import PipelineContext, FactCard, StrategyCard, DistilledCard
from core.workflow.events import EventBus, WorkflowEvent
from core.workflow.stages import DUAL_AI_STAGES

logger = logging.getLogger(__name__)


class DualAIOrchestrator:
    """Orchestrates dual AI workflow."""

    def __init__(self, deepseek_client=None, mimo_client=None, event_bus: Optional[EventBus] = None):
        self.ds = deepseek_client
        self.mm = mimo_client
        self.bus = event_bus or EventBus()

    def run(self, ctx: PipelineContext) -> PipelineContext:
        """Run full 9-stage dual AI pipeline."""
        from core.ai.ai_manifest import DualAIManifest
        manifest = DualAIManifest()

        for stage_def in DUAL_AI_STAGES:
            event = WorkflowEvent(
                stage_name=stage_def.name,
                display_name=stage_def.display_name,
                is_ai=stage_def.requires_ai,
                ai_provider=stage_def.ai_provider,
            )

            # Check if AI provider available
            if stage_def.requires_ai:
                provider = self.ds if stage_def.ai_provider == "deepseek" else self.mm
                if provider is None or not provider.is_configured:
                    manifest.skip_stage(stage_def.name, f"{stage_def.ai_provider} not configured")
                    event.status = "skipped"
                    self.bus.emit(event)
                    ctx.log(f"  跳过 {stage_def.display_name}: {stage_def.ai_provider} 未配置")
                    continue

            event.status = "running"
            self.bus.emit(event)
            manifest.start_stage(stage_def.name)

            try:
                if stage_def.name == "intake":
                    self._run_intake(ctx)
                elif stage_def.name == "deepseek_extract":
                    self._run_deepseek_extract(ctx, manifest)
                elif stage_def.name == "mimo_critique":
                    self._run_mimo_critique(ctx, manifest)
                elif stage_def.name == "distill_facts":
                    self._run_distill_facts(ctx)
                elif stage_def.name == "deepseek_strategy":
                    self._run_deepseek_strategy(ctx, manifest)
                elif stage_def.name == "mimo_review":
                    self._run_mimo_review(ctx, manifest)
                elif stage_def.name == "final_distill":
                    self._run_final_distill(ctx)
                elif stage_def.name == "render":
                    self._run_render(ctx)
                elif stage_def.name == "quality_gate":
                    self._run_quality_gate(ctx)

                event.status = "done"
                self.bus.emit(event)

            except Exception as e:
                event.status = "failed"
                event.error = str(e)
                self.bus.emit(event)
                ctx.log(f"  ERROR: {stage_def.display_name} 失败: {e}")
                if stage_def.name in ("intake",):
                    break  # Critical stage

        manifest.finish()
        manifest.save(ctx.output_dir)
        ctx.log(f"Dual AI 完成: ai_mode={manifest.ai_mode}")
        return ctx

    def _run_intake(self, ctx: PipelineContext):
        """Stage 1: File intake."""
        from core.intake import run_intake
        run_intake(ctx)

    def _run_deepseek_extract(self, ctx: PipelineContext, manifest):
        """Stage 2: DeepSeek fact extraction."""
        import time
        prompt = """你是法律事实提取专家。从以下材料中提取结构化信息。
输出JSON：{"case_id":"","court":"","parties":[{"name":"","role":""}],"amount":"","deadline":"","key_facts":[],"disputed_facts":[],"missing_materials":[]}"""
        text = "\n\n".join(ctx.raw_texts)[:8000] if ctx.raw_texts else ""

        start = time.time()
        resp = self.ds.extract_facts(prompt, text)
        latency = int((time.time() - start) * 1000)

        manifest.end_stage("deepseek_extract", resp.success, latency,
                          resp.model, resp.token_usage, resp.error)

        if resp.success and resp.content:
            try:
                content = resp.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                data = json.loads(content)
                if ctx.fact_card is None:
                    ctx.fact_card = FactCard()
                if data.get("case_id"):
                    ctx.fact_card.case_id = data["case_id"]
                if data.get("court"):
                    ctx.fact_card.court = data["court"]
                if data.get("amount"):
                    ctx.fact_card.amount = data["amount"]
                if data.get("key_facts"):
                    ctx.fact_card.key_facts = data["key_facts"]
                if data.get("parties"):
                    from core.fact_card import Party
                    ctx.fact_card.parties = [Party(**p) for p in data["parties"]]
                if data.get("missing_materials"):
                    ctx.fact_card.missing_materials = data["missing_materials"]
                ctx.log(f"  DeepSeek 事实抽取成功: {len(ctx.fact_card.key_facts)} 条")
            except Exception as e:
                ctx.log(f"  WARNING: DeepSeek 返回解析失败: {e}")

    def _run_mimo_critique(self, ctx: PipelineContext, manifest):
        """Stage 3: MiMo fact critique."""
        import time
        fc_json = json.dumps(ctx.fact_card.to_dict(), ensure_ascii=False) if ctx.fact_card else "{}"
        text = "\n\n".join(ctx.raw_texts)[:8000] if ctx.raw_texts else ""

        start = time.time()
        resp = self.mm.critique_facts(fc_json, text)
        latency = int((time.time() - start) * 1000)

        manifest.end_stage("mimo_critique", resp.success, latency,
                          resp.model, resp.token_usage, resp.error)

        if resp.success:
            ctx.log(f"  MiMo 事实复核完成: {latency}ms")

    def _run_distill_facts(self, ctx: PipelineContext):
        """Stage 4: Distill facts (merge + clean)."""
        from core.distiller import _fix_party_identity_confusion
        if ctx.fact_card:
            _fix_party_identity_confusion(ctx.fact_card, ctx)
        ctx.log("  事实蒸馏完成")

    def _run_deepseek_strategy(self, ctx: PipelineContext, manifest):
        """Stage 5: DeepSeek strategy generation."""
        import time
        prompt = f"""你是法律策略专家。根据以下事实卡片生成策略方案。
当事人身份：{ctx.identity}
处理目标：{ctx.goal}
输出JSON：{{"situation_assessment":"","action_advice":[{{"action":"","priority":"S/A/B/C/D","reasoning":""}}],"evidence_gap":[],"risk_warnings":[],"sabcd_rating":"S/A/B/C/D"}}"""
        fc_json = json.dumps(ctx.fact_card.to_dict(), ensure_ascii=False) if ctx.fact_card else "{}"

        start = time.time()
        resp = self.ds.generate_strategy(prompt, fc_json)
        latency = int((time.time() - start) * 1000)

        manifest.end_stage("deepseek_strategy", resp.success, latency,
                          resp.model, resp.token_usage, resp.error)

        if resp.success and resp.content:
            try:
                content = resp.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                data = json.loads(content)
                from core.fact_card import ActionAdvice
                actions = [ActionAdvice(**a) for a in data.get("action_advice", [])]
                ctx.strategy_card = StrategyCard(
                    situation_assessment=data.get("situation_assessment", ""),
                    action_advice=actions,
                    evidence_gap=data.get("evidence_gap", []),
                    risk_warnings=data.get("risk_warnings", []),
                    sabcd_rating=data.get("sabcd_rating", "B"),
                )
                ctx.log(f"  DeepSeek 策略生成成功: {len(actions)} 条建议")
            except Exception as e:
                ctx.log(f"  WARNING: DeepSeek 策略解析失败: {e}")
                # Fallback
                from core.providers.api_b_client import ApiBClient
                client = ApiBClient()
                ctx.strategy_card = client._local_generate(ctx.fact_card, ctx.identity, ctx.goal)

    def _run_mimo_review(self, ctx: PipelineContext, manifest):
        """Stage 6: MiMo strategy review."""
        import time
        sc_json = json.dumps(ctx.strategy_card.to_dict(), ensure_ascii=False) if ctx.strategy_card else "{}"
        fc_json = json.dumps(ctx.fact_card.to_dict(), ensure_ascii=False) if ctx.fact_card else "{}"

        start = time.time()
        resp = self.mm.review_strategy(sc_json, fc_json)
        latency = int((time.time() - start) * 1000)

        manifest.end_stage("mimo_review", resp.success, latency,
                          resp.model, resp.token_usage, resp.error)

        if resp.success:
            ctx.log(f"  MiMo 策略审校完成: {latency}ms")

    def _run_final_distill(self, ctx: PipelineContext):
        """Stage 7: Final distillation."""
        from core.distiller import distill
        distill(ctx)

    def _run_render(self, ctx: PipelineContext):
        """Stage 8: Template rendering."""
        from core.pipeline.step6_template_fill import step6_template_fill
        from core.pipeline.step7_render import step7_render
        ctx = step6_template_fill(ctx)
        ctx = step7_render(ctx)

    def _run_quality_gate(self, ctx: PipelineContext):
        """Stage 9: Quality gate."""
        from core.pipeline.step8_quality_gate import step8_quality_gate
        ctx = step8_quality_gate(ctx)
