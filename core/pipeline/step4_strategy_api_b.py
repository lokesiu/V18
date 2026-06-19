"""
step4_strategy_api_b.py - Pipeline Step 4: API-B Strategy Generation

Calls API-B (legal strategy analysis service) to generate a StrategyCard
containing situation assessment, action advice, evidence gaps, draft
documents, and risk warnings.

Non-critical step - on API failure, creates a basic StrategyCard with
local rule-based generation.
"""
from __future__ import annotations

import json
from core.fact_card import (
    PipelineContext,
    StrategyCard,
    ActionAdvice,
    DraftDocument,
)
from core.ai_config import get_ai_config, is_api_configured
from core.ai_mode import AIModeTracker, AIStatus


class AIProviderError(Exception):
    """Custom exception for AI provider failures."""
    pass


def _create_fallback_strategy_card(ctx: PipelineContext) -> StrategyCard:
    """Create a basic StrategyCard using local rules when API-B fails."""
    from core.providers.api_b_client import ApiBClient
    client = ApiBClient()
    if ctx.fact_card is None:
        return StrategyCard()
    return client._local_generate(ctx.fact_card, ctx.identity, ctx.goal)


def step4_strategy_api_b(ctx: PipelineContext) -> PipelineContext:
    """Call API-B to generate legal strategy from the enhanced fact card.
    
    Uses real DeepSeek API when configured, falls back to local generation.
    Tracks API call status and latency in ai_mode_tracker.
    """
    ctx.log("Step 4: API-B 策略生成 - 调用外部服务生成法律策略方案")

    if ctx.fact_card is None:
        ctx.add_error("fact_card 为空，无法生成策略方案")
        return ctx

    # Get or create AI mode tracker
    tracker = getattr(ctx, '_ai_mode_tracker', None)
    if tracker is None:
        tracker = AIModeTracker()
        ctx._ai_mode_tracker = tracker  # type: ignore[attr-defined]

    # Check if API is configured
    if not is_api_configured():
        ctx.log("Step 4: API-B 未配置，使用本地规则生成")
        tracker.api_b_status = AIStatus.NOT_CONFIGURED
        ctx.strategy_card = _create_fallback_strategy_card(ctx)
        _log_strategy_summary(ctx)
        return ctx

    # Try real API call
    try:
        from core.ai_client import AIClient
        
        # Build prompt for strategy generation
        prompt = f"""你是一个法律策略分析专家。请根据以下事实卡片和当事人身份，生成法律策略方案。

当事人身份：{ctx.identity}
处理目标：{ctx.goal}

要求输出JSON格式：
{{
  "situation_assessment": "处境评估（200字以上，包含案件事实、法律关系、风险分析）",
  "action_advice": [
    {{"action": "具体行动", "priority": "S/A/B/C/D", "reasoning": "理由"}}
  ],
  "evidence_gap": ["证据缺口1", "证据缺口2"],
  "risk_warnings": ["风险提示1"],
  "sabcd_rating": "S/A/B/C/D",
  "draft_documents": [
    {{
      "doc_type": "文书类型（如答辩状、起诉状等）",
      "title": "文书标题",
      "content": "完整的文书正文（500字以上，包含首部、事实与理由、法律依据、结尾等完整结构）"
    }}
  ]
}}

请确保：
1. 行动建议至少5条，每条包含优先级、具体动作、理由
2. 证据缺口要具体明确
3. 风险提示要针对案件
4. 评级要基于事实依据
5. draft_documents必须包含至少一份完整的法律文书，内容要详实、有实质性法律论证，不要使用占位符

请确保输出是有效的JSON格式。"""

        # Prepare fact card context
        fact_context = json.dumps(ctx.fact_card.to_dict(), ensure_ascii=False, indent=2)
        
        # Call API
        tracker.start_api_b()
        client = AIClient()
        response = client.call_api_b(prompt, fact_context)
        tracker.end_api_b(success=response.success, latency_ms=response.latency_ms)
        
        if response.success and response.content:
            # Parse API response
            try:
                # Try to extract JSON from response
                content = response.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                data = json.loads(content)
                
                # Build strategy card from API response
                action_advice = []
                for item in data.get("action_advice", []):
                    action_advice.append(ActionAdvice(
                        action=item.get("action", ""),
                        priority=item.get("priority", "B"),
                        reasoning=item.get("reasoning", ""),
                    ))
                
                draft_documents = []
                for item in data.get("draft_documents", []):
                    draft_documents.append(DraftDocument(
                        doc_type=item.get("doc_type", ""),
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                    ))
                
                ctx.strategy_card = StrategyCard(
                    situation_assessment=data.get("situation_assessment", ""),
                    action_advice=action_advice,
                    evidence_gap=data.get("evidence_gap", []),
                    draft_documents=draft_documents,
                    risk_warnings=data.get("risk_warnings", []),
                    sabcd_rating=data.get("sabcd_rating", "B"),
                )
                
                # Ensure draft_documents are always generated
                if not ctx.strategy_card.draft_documents:
                    fallback = _create_fallback_strategy_card(ctx)
                    ctx.strategy_card.draft_documents = fallback.draft_documents
                    ctx.log("  API-B 未返回文书草稿，使用本地模板生成")
                
                ctx.log(f"Step 4 完成: API-B 策略生成成功 - "
                       f"评级 {ctx.strategy_card.sabcd_rating}, "
                       f"{len(action_advice)} 条行动建议, "
                       f"{len(data.get('evidence_gap', []))} 项证据缺口")
                
            except json.JSONDecodeError as e:
                ctx.log(f"WARNING: API-B 返回的JSON格式无效: {e}")
                tracker.api_b_status = AIStatus.FAILED
                raise AIProviderError(f"MiMo API 返回的JSON格式无效: {e}")
        else:
            ctx.log(f"WARNING: API-B 调用失败: {response.error}")
            tracker.api_b_status = AIStatus.FAILED
            raise AIProviderError(f"MiMo API 请求失败: {response.error}")
            
    except AIProviderError:
        raise
    except Exception as exc:
        ctx.log(f"WARNING: API-B 策略生成异常: {exc}")
        tracker.api_b_status = AIStatus.FAILED
        raise AIProviderError(f"MiMo API 请求异常: {exc}")

    _log_strategy_summary(ctx)
    return ctx


def _log_strategy_summary(ctx: PipelineContext):
    """Log strategy card summary."""
    if ctx.strategy_card:
        for i, advice in enumerate(ctx.strategy_card.action_advice, 1):
            ctx.log(f"  行动建议 {i} [{advice.priority}]: {advice.action}")
        for gap in ctx.strategy_card.evidence_gap:
            ctx.log(f"  证据缺口: {gap}")
        for warning in ctx.strategy_card.risk_warnings:
            ctx.log(f"  风险提示: {warning}")
