"""
core/ai/deepseek_client.py - DeepSeek API Client

Dedicated client for DeepSeek API with connection testing,
latency tracking, and token usage reporting.
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


class DeepSeekClient:
    """DeepSeek API client."""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com",
                 model_extract: str = "deepseek-chat",
                 model_strategy: str = "deepseek-chat",
                 timeout: int = 60):
        self.api_key = api_key.strip()
        self.base_url = base_url.strip().rstrip("/")
        self.model_extract = model_extract.strip()
        self.model_strategy = model_strategy.strip()
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def extract_facts(self, prompt: str, context: str) -> APIResponse:
        """Call DeepSeek for fact extraction."""
        return self._call(self.model_extract, prompt, context)

    def generate_strategy(self, prompt: str, context: str) -> APIResponse:
        """Call DeepSeek for strategy generation."""
        return self._call(self.model_strategy, prompt, context)

    def test_connection(self) -> APIResponse:
        """Test API connection."""
        return self._call(self.model_extract, "Reply with 'OK'", "Test connection")

    def _call(self, model: str, system_prompt: str, user_content: str) -> APIResponse:
        """Make API call to DeepSeek."""
        if not self.api_key:
            return APIResponse(False, "", 0, model=model, error="API key not configured")

        start = time.time()
        try:
            url = f"{self.base_url}/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
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
                model=model,
                token_usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            )

        except httpx.TimeoutException:
            return APIResponse(False, "", int((time.time() - start) * 1000),
                             model=model, error="Request timeout")
        except httpx.HTTPStatusError as e:
            return APIResponse(False, "", int((time.time() - start) * 1000),
                             model=model, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            return APIResponse(False, "", int((time.time() - start) * 1000),
                             model=model, error=str(e))
