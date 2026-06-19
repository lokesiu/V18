"""
step3_fact_api_a.py - Pipeline Step 3: API-A Fact Enhancement

Calls API-A (structured fact analysis service) to enrich the FactCard
with additional structured data, cross-references, and deeper analysis.

Non-critical step - graceful degradation if API is unavailable.
The existing fact_card from Step 2 is preserved as fallback.
"""
from __future__ import annotations

import json
from core.fact_card import PipelineContext
from core.ai_config import get_ai_config, is_api_configured
from core.ai_mode import AIModeTracker, AIStatus


class AIProviderError(Exception):
    """Custom exception for AI provider failures."""
    pass


def step3_fact_api_a(ctx: PipelineContext) -> PipelineContext:
    """Call API-A to enhance the fact card with deeper structured analysis.
    
    Uses real DeepSeek API when configured, falls back to local extraction.
    Tracks API call status and latency in ai_mode_tracker.
    """
    ctx.log("Step 3: API-A 事实增强 - 调用外部服务对事实卡片进行结构化增强")

    if ctx.fact_card is None:
        ctx.add_error("fact_card 为空，无法执行 API-A 增强")
        return ctx

    # Get or create AI mode tracker
    tracker = getattr(ctx, '_ai_mode_tracker', None)
    if tracker is None:
        tracker = AIModeTracker()
        ctx._ai_mode_tracker = tracker  # type: ignore[attr-defined]

    # Check if API is configured
    if not is_api_configured():
        ctx.log("Step 3: API-A 未配置，使用本地提取结果")
        tracker.api_a_status = AIStatus.NOT_CONFIGURED
        return ctx

    # Try real API call
    try:
        from core.ai_client import AIClient
        from core.providers.api_a_client import ApiAClient
        
        # Build prompt for fact extraction
        prompt = """你是一个法律事实提取专家。请从以下案件材料中提取结构化信息。

要求输出JSON格式：
{
  "case_id": "案号",
  "court": "法院名称",
  "parties": [{"name": "姓名", "role": "角色"}],
  "amount": "金额",
  "deadline": "期限",
  "key_facts": ["关键事实1", "关键事实2"],
  "disputed_facts": ["争议事实1"],
  "missing_materials": ["缺失材料1"],
  "conflicts": ["冲突1"]
}

请确保输出是有效的JSON格式。"""

        # Combine raw texts
        combined_text = "\n\n".join(ctx.raw_texts) if ctx.raw_texts else ""
        
        # Call API
        tracker.start_api_a()
        client = AIClient()
        response = client.call_api_a(prompt, combined_text)
        tracker.end_api_a(success=response.success, latency_ms=response.latency_ms)
        
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
                
                # Update fact card with API results
                if "case_id" in data and data["case_id"]:
                    ctx.fact_card.case_id = data["case_id"]
                if "court" in data and data["court"]:
                    ctx.fact_card.court = data["court"]
                if "amount" in data and data["amount"]:
                    ctx.fact_card.amount = data["amount"]
                if "deadline" in data and data["deadline"]:
                    ctx.fact_card.deadline = data["deadline"]
                if "key_facts" in data and data["key_facts"]:
                    ctx.fact_card.key_facts = data["key_facts"]
                if "disputed_facts" in data and data["disputed_facts"]:
                    ctx.fact_card.disputed_facts = data["disputed_facts"]
                if "missing_materials" in data and data["missing_materials"]:
                    ctx.fact_card.missing_materials = data["missing_materials"]
                if "conflicts" in data and data["conflicts"]:
                    ctx.fact_card.conflicts = data["conflicts"]
                
                ctx.log(f"Step 3 完成: API-A 增强成功 - "
                       f"{len(ctx.fact_card.key_facts)} 条关键事实, "
                       f"{len(ctx.fact_card.source_refs)} 条来源引用")
                
            except json.JSONDecodeError as e:
                ctx.log(f"WARNING: API-A 返回的JSON格式无效: {e}")
                tracker.api_a_status = AIStatus.FAILED
                raise AIProviderError(f"DeepSeek API 返回的JSON格式无效: {e}")
        else:
            ctx.log(f"WARNING: API-A 调用失败: {response.error}")
            tracker.api_a_status = AIStatus.FAILED
            raise AIProviderError(f"DeepSeek API 请求失败: {response.error}")
            
    except AIProviderError:
        raise
    except Exception as exc:
        ctx.log(f"WARNING: API-A 增强过程中发生异常: {exc}")
        tracker.api_a_status = AIStatus.FAILED
        raise AIProviderError(f"DeepSeek API 请求异常: {exc}")

    return ctx
