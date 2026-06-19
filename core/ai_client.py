"""
core/ai_client.py - Real API Client Module

Provides real API integration with DeepSeek for fact extraction and strategy generation.
Tracks latency and token usage.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

import asyncio
import httpx

from core.ai_config import AIConfig, get_ai_config

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """API response with metadata."""
    success: bool
    content: str
    latency_ms: int
    token_usage: Optional[dict] = None
    error: Optional[str] = None


class AIClient:
    """Real API client for DeepSeek integration."""
    
    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or get_ai_config()
    
    def call_api_a(self, prompt: str, context: str) -> APIResponse:
        """Call API-A for fact extraction.
        
        Args:
            prompt: The extraction prompt
            context: Raw text context
            
        Returns:
            APIResponse with extracted facts
        """
        if not self.config.is_configured:
            return APIResponse(
                success=False,
                content="",
                latency_ms=0,
                error="API not configured",
            )
        
        return self._call_api(
            model=self.config.model_extract,
            prompt=prompt,
            context=context,
            timeout=self.config.timeout,
        )
    
    def call_api_b(self, prompt: str, context: str) -> APIResponse:
        """Call API-B for strategy generation.
        
        Args:
            prompt: The strategy prompt
            context: Fact card context
            
        Returns:
            APIResponse with generated strategy
        """
        if not self.config.is_configured:
            return APIResponse(
                success=False,
                content="",
                latency_ms=0,
                error="API not configured",
            )
        
        return self._call_api(
            model=self.config.model_strategy,
            prompt=prompt,
            context=context,
            timeout=self.config.timeout,
        )
    
    def _call_api(
        self,
        model: str,
        prompt: str,
        context: str,
        timeout: int,
    ) -> APIResponse:
        """Make API call to DeepSeek.
        
        Args:
            model: Model name
            prompt: System prompt
            context: User message content
            timeout: Request timeout
            
        Returns:
            APIResponse with result
        """
        start_time = time.time()
        
        try:
            url = f"{self.config.base_url}/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": context},
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
            }
            
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Extract token usage
                usage = data.get("usage", {})
                token_usage = {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                logger.info(
                    "API call successful: model=%s, latency=%dms, tokens=%d",
                    model, latency_ms, token_usage["total_tokens"],
                )
                
                return APIResponse(
                    success=True,
                    content=content,
                    latency_ms=latency_ms,
                    token_usage=token_usage,
                )
                
        except httpx.TimeoutException:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning("API call timeout: model=%s, latency=%dms", model, latency_ms)
            return APIResponse(
                success=False,
                content="",
                latency_ms=latency_ms,
                error="Request timeout",
            )
        except httpx.HTTPStatusError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning("API call HTTP error: model=%s, status=%d", model, e.response.status_code)
            return APIResponse(
                success=False,
                content="",
                latency_ms=latency_ms,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning("API call failed: model=%s, error=%s", model, str(e))
            return APIResponse(
                success=False,
                content="",
                latency_ms=latency_ms,
                error=str(e),
            )

    async def async_call(
        self,
        system_prompt: str,
        user_content: str,
        model: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        timeout: int = 0,
    ) -> APIResponse:
        """Async API call for concurrent document generation."""
        if not self.config.is_configured:
            return APIResponse(
                success=False, content="", latency_ms=0,
                error="API not configured",
            )

        model = model or self.config.model_strategy
        timeout = timeout or self.config.timeout
        start_time = time.time()

        try:
            url = f"{self.config.base_url}/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                token_usage = {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }
                latency_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    "Async API call: model=%s, latency=%dms, tokens=%d",
                    model, latency_ms, token_usage["total_tokens"],
                )
                return APIResponse(
                    success=True, content=content,
                    latency_ms=latency_ms, token_usage=token_usage,
                )

        except httpx.TimeoutException:
            latency_ms = int((time.time() - start_time) * 1000)
            return APIResponse(
                success=False, content="", latency_ms=latency_ms,
                error="Request timeout",
            )
        except httpx.HTTPStatusError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return APIResponse(
                success=False, content="", latency_ms=latency_ms,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return APIResponse(
                success=False, content="", latency_ms=latency_ms,
                error=str(e),
            )


def test_api_connection() -> bool:
    """Test API connection.
    
    Returns:
        True if API is accessible and responding
    """
    config = get_ai_config()
    if not config.is_configured:
        return False
    
    try:
        url = f"{config.base_url}/v1/models"
        headers = {"Authorization": f"Bearer {config.api_key}"}
        
        with httpx.Client(timeout=10) as client:
            response = client.get(url, headers=headers)
            return response.status_code == 200
    except Exception:
        return False
