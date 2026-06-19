"""
core/ai/mimo_client.py - MiMo API Client

Dedicated client for MiMo API with connection testing,
fact critique, and strategy review capabilities.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """API response with metadata."""
    success: bool
    content: str
    latency_ms: int
    model: str = ""
    token_usage: Optional[dict] = None
    error: Optional[str] = None


class MiMoClient:
    """MiMo API client."""

    def __init__(self, api_key: str, base_url: str = "https://api.mimo.ai",
                 model: str = "mimo-v2.5-pro", timeout: int = 60):
        self.api_key = api_key.strip()
        self.base_url = base_url.strip().rstrip("/")
        self.model = model.strip()
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def critique_facts(self, fact_card_json: str, raw_texts: str) -> APIResponse:
        """Call MiMo to critique and enhance fact extraction."""
        prompt = """你是法律事实复核专家。请复核以下事实抽取结果，找出遗漏、冲突和错误。

要求：
1. 检查当事人身份是否正确
2. 检查金额是否准确
3. 检查期限是否合理
4. 找出遗漏的关键事实
5. 发现材料中的冲突

输出JSON格式：
{
  "critique_notes": ["问题1", "问题2"],
  "additional_facts": ["补充事实1"],
  "identity_corrections": [{"field": "parties", "corrected": "修正内容"}],
  "amount_corrections": "修正后的金额",
  "missing_evidence": ["缺失证据1"],
  "conflicts_found": ["冲突1"]
}"""
        context = f"事实卡片:\n{fact_card_json}\n\n原始材料:\n{raw_texts[:8000]}"
        return self._call(prompt, context)

    def review_strategy(self, strategy_json: str, fact_json: str) -> APIResponse:
        """Call MiMo to review strategy quality."""
        prompt = """你是法律策略审校专家。请审校以下法律策略方案的质量。

检查：
1. 行动建议是否具体、可执行
2. 证据缺口是否全面
3. 评级理由是否充分
4. 风险提示是否针对案件
5. 是否存在泛化建议

输出JSON格式：
{
  "quality_score": 0-100,
  "issues": ["问题1"],
  "suggestions": ["建议1"],
  "is_generic": false,
  "missing_aspects": ["遗漏方面1"]
}"""
        context = f"策略方案:\n{strategy_json}\n\n事实卡片:\n{fact_json}"
        return self._call(prompt, context)

    def test_connection(self) -> APIResponse:
        """Test API connection."""
        return self._call("Reply with 'OK'", "Test connection")

    def _call(self, system_prompt: str, user_content: str) -> APIResponse:
        """Make API call to MiMo."""
        if not self.api_key:
            return APIResponse(False, "", 0, model=self.model, error="API key not configured")

        start = time.time()
        try:
            url = f"{self.base_url}/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
            }

            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            latency = int((time.time() - start) * 1000)

            return APIResponse(
                success=True,
                content=content,
                latency_ms=latency,
                model=self.model,
                token_usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            )

        except httpx.TimeoutException:
            return APIResponse(False, "", int((time.time() - start) * 1000),
                             model=self.model, error="Request timeout")
        except httpx.HTTPStatusError as e:
            return APIResponse(False, "", int((time.time() - start) * 1000),
                             model=self.model, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            return APIResponse(False, "", int((time.time() - start) * 1000),
                             model=self.model, error=str(e))
