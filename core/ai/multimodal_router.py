"""
core/ai/multimodal_router.py - 多模态智能路由器

实现"DeepSeek + MiMo 双 AI"模式下的智能路由逻辑：
- 纯文本请求 → DeepSeek
- 包含图像/音频 → MiMo 处理多模态 → DeepSeek 生成最终结果
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from core.ai.multimodal import (
    FileCategory, classify_files, get_file_summary,
    MultimodalRequestBuilder, transcribe_audio_files,
    encode_image_base64, build_vision_message,
)
from core.ai.unified_client import UnifiedAIClient, AIResponse

logger = logging.getLogger(__name__)


# ── 路由模式 ──────────────────────────────────────────────────────────

class RouteMode:
    """AI 路由模式"""
    PREVIEW = "preview"           # 基础预览（本地）
    DEEPSEEK_ONLY = "deepseek"    # DeepSeek 单 AI
    MIMO_ONLY = "mimo"            # MiMo 单 AI
    DUAL_AI = "dual_ai"           # DeepSeek + MiMo 双 AI


@dataclass
class RouteResult:
    """路由结果"""
    success: bool
    content: str
    mode_used: str
    mimo_multimodal_used: bool = False
    deepseek_text_used: bool = False
    error: Optional[str] = None


# ── 多模态路由器 ──────────────────────────────────────────────────────

class MultimodalRouter:
    """多模态智能路由器
    
    根据上传文件类型和工作模式，智能调度 DeepSeek 和 MiMo：
    
    双 AI 模式下：
    1. 纯文本文件 → 直接交给 DeepSeek 处理
    2. 包含图像/音频 → MiMo 先处理多模态 → 结果作为上下文 → DeepSeek 生成最终结果
    """
    
    def __init__(
        self,
        deepseek_client: Optional[UnifiedAIClient] = None,
        mimo_client: Optional[UnifiedAIClient] = None,
        mode: str = RouteMode.DEEPSEEK_ONLY,
    ):
        self.deepseek = deepseek_client
        self.mimo = mimo_client
        self.mode = mode
    
    def route_request(
        self,
        file_paths: list[str],
        system_prompt: str,
        text_prompt: str,
        image_prompt: str = "请分析这些证据图片，提取关键法律事实和证据信息。",
        **kwargs,
    ) -> RouteResult:
        """路由请求到合适的 AI 模型
        
        Args:
            file_paths: 上传的文件路径列表
            system_prompt: 系统提示词
            text_prompt: 用户文本提示
            image_prompt: 图像分析提示词
            **kwargs: 其他参数
            
        Returns:
            RouteResult
        """
        # 获取文件分类摘要
        summary = get_file_summary(file_paths)
        has_multimodal = summary["has_images"] or summary["has_audio"]
        
        logger.info(
            "Routing request: mode=%s, files=%d, images=%d, audio=%d",
            self.mode, summary["total"], summary["image_count"], summary["audio_count"],
        )
        
        # 根据模式路由
        if self.mode == RouteMode.PREVIEW:
            return self._route_preview(file_paths, system_prompt, text_prompt)
        elif self.mode == RouteMode.DEEPSEEK_ONLY:
            return self._route_deepseek_only(file_paths, system_prompt, text_prompt, image_prompt)
        elif self.mode == RouteMode.MIMO_ONLY:
            return self._route_mimo_only(file_paths, system_prompt, text_prompt, image_prompt)
        elif self.mode == RouteMode.DUAL_AI:
            return self._route_dual_ai(file_paths, system_prompt, text_prompt, image_prompt, summary)
        else:
            return RouteResult(False, "", self.mode, error=f"Unknown mode: {self.mode}")
    
    def _route_preview(self, file_paths, system_prompt, text_prompt) -> RouteResult:
        """预览模式（不调用 API）"""
        return RouteResult(
            success=True,
            content="[预览模式] 本地分析完成。请配置 API 密钥以启用完整功能。",
            mode_used=RouteMode.PREVIEW,
        )
    
    def _route_deepseek_only(self, file_paths, system_prompt, text_prompt, image_prompt) -> RouteResult:
        """DeepSeek 单 AI 模式"""
        if not self.deepseek or not self.deepseek.is_configured:
            return RouteResult(False, "", RouteMode.DEEPSEEK_ONLY, error="DeepSeek 未配置")
        
        response = self.deepseek.chat(system_prompt, text_prompt)
        return RouteResult(
            success=response.success,
            content=response.content,
            mode_used=RouteMode.DEEPSEEK_ONLY,
            deepseek_text_used=True,
            error=response.error,
        )
    
    def _route_mimo_only(self, file_paths, system_prompt, text_prompt, image_prompt) -> RouteResult:
        """MiMo 单 AI 模式（支持多模态）"""
        if not self.mimo or not self.mimo.is_configured:
            return RouteResult(False, "", RouteMode.MIMO_ONLY, error="MiMo 未配置")
        
        response = self.mimo.chat_multimodal(
            file_paths=file_paths,
            system_prompt=system_prompt,
            text_prompt=text_prompt,
            image_prompt=image_prompt,
        )
        return RouteResult(
            success=response.success,
            content=response.content,
            mode_used=RouteMode.MIMO_ONLY,
            mimo_multimodal_used=True,
            error=response.error,
        )
    
    def _route_dual_ai(
        self, file_paths, system_prompt, text_prompt, image_prompt, summary
    ) -> RouteResult:
        """双 AI 模式：DeepSeek (文本) + MiMo (多模态)
        
        路由逻辑：
        1. 纯文本 → DeepSeek 直接处理
        2. 包含图像/音频 → MiMo 处理多模态 → 结果喂给 DeepSeek
        """
        has_multimodal = summary["has_images"] or summary["has_audio"]
        
        # 情况1：纯文本，直接交给 DeepSeek
        if not has_multimodal:
            logger.info("Dual AI: pure text → DeepSeek")
            if not self.deepseek or not self.deepseek.is_configured:
                return RouteResult(False, "", RouteMode.DUAL_AI, error="DeepSeek 未配置")
            
            response = self.deepseek.chat(system_prompt, text_prompt)
            return RouteResult(
                success=response.success,
                content=response.content,
                mode_used=RouteMode.DUAL_AI,
                deepseek_text_used=True,
                error=response.error,
            )
        
        # 情况2：包含多模态，MiMo 先处理 → DeepSeek 生成
        logger.info("Dual AI: multimodal detected → MiMo process → DeepSeek generate")
        
        # Step 1: MiMo 处理多模态附件
        multimodal_context = self._process_multimodal_with_mimo(
            file_paths, image_prompt, summary
        )
        
        if not multimodal_context["success"]:
            return RouteResult(
                False, "", RouteMode.DUAL_AI,
                mimo_multimodal_used=True,
                error=f"MiMo 多模态处理失败: {multimodal_context['error']}",
            )
        
        # Step 2: 将多模态结果作为上下文，喂给 DeepSeek
        enhanced_prompt = self._build_enhanced_prompt(
            text_prompt, multimodal_context["content"]
        )
        
        if not self.deepseek or not self.deepseek.is_configured:
            # 如果 DeepSeek 未配置，直接返回 MiMo 的结果
            return RouteResult(
                success=True,
                content=multimodal_context["content"],
                mode_used=RouteMode.DUAL_AI,
                mimo_multimodal_used=True,
            )
        
        response = self.deepseek.chat(system_prompt, enhanced_prompt)
        return RouteResult(
            success=response.success,
            content=response.content,
            mode_used=RouteMode.DUAL_AI,
            mimo_multimodal_used=True,
            deepseek_text_used=True,
            error=response.error,
        )
    
    def _process_multimodal_with_mimo(
        self, file_paths: list[str], image_prompt: str, summary: dict
    ) -> dict:
        """使用 MiMo 处理多模态附件
        
        Returns:
            {"success": bool, "content": str, "error": str}
        """
        if not self.mimo or not self.mimo.is_configured:
            return {"success": False, "content": "", "error": "MiMo 未配置"}
        
        results = []
        
        # 处理图像
        if summary["has_images"]:
            logger.info("Processing %d images with MiMo Vision", summary["image_count"])
            image_response = self.mimo.chat_multimodal(
                file_paths=summary["files"]["image"],
                system_prompt="你是法律证据分析专家。请仔细分析图片中的内容，提取关键信息。",
                text_prompt=image_prompt,
            )
            if image_response.success:
                results.append(f"[图像分析结果]\n{image_response.content}")
            else:
                logger.warning("Image processing failed: %s", image_response.error)
        
        # 处理音频
        if summary["has_audio"]:
            logger.info("Processing %d audio files with MiMo", summary["audio_count"])
            audio_text = transcribe_audio_files(
                summary["files"]["audio"],
                self.mimo._config.api_key,
                self.mimo._config.base_url,
            )
            if audio_text:
                results.append(f"[音频转写结果]\n{audio_text}")
        
        if results:
            return {
                "success": True,
                "content": "\n\n".join(results),
                "error": None,
            }
        else:
            return {
                "success": False,
                "content": "",
                "error": "多模态处理未产生有效结果",
            }
    
    def _build_enhanced_prompt(self, original_prompt: str, multimodal_context: str) -> str:
        """构建增强的提示词，包含多模态分析结果"""
        return f"""{original_prompt}

---
以下是多模态附件（图片/音频）的分析结果，请结合这些信息进行综合分析：

{multimodal_context}
---

请基于以上所有信息，完成法律分析任务。"""


# ── 工厂函数 ──────────────────────────────────────────────────────────

def create_router_from_settings() -> MultimodalRouter:
    """从设置创建路由器实例"""
    from core.settings_store import get_settings_store
    from core.ai.unified_client import UnifiedAIClient, ProviderConfig
    
    store = get_settings_store()
    s = store.settings
    
    # 根据设置确定模式
    mode_map = {
        0: RouteMode.PREVIEW,
        1: RouteMode.DEEPSEEK_ONLY,
        2: RouteMode.MIMO_ONLY,
        3: RouteMode.DUAL_AI,
    }
    
    # 获取当前工作模式（需要从 UI 或设置中读取）
    # 这里简化为根据配置自动判断
    ds_configured = s.deepseek.is_configured()
    mm_configured = s.mimo.is_configured()
    
    if ds_configured and mm_configured:
        mode = RouteMode.DUAL_AI
    elif ds_configured:
        mode = RouteMode.DEEPSEEK_ONLY
    elif mm_configured:
        mode = RouteMode.MIMO_ONLY
    else:
        mode = RouteMode.PREVIEW
    
    # 创建客户端
    ds_client = None
    if ds_configured:
        ds_client = UnifiedAIClient(ProviderConfig(
            name="deepseek",
            api_key=s.deepseek.api_key,
            base_url=s.deepseek.base_url,
            model=s.deepseek.model_extract,
        ))
    
    mm_client = None
    if mm_configured:
        mm_client = UnifiedAIClient(ProviderConfig(
            name="mimo",
            api_key=s.mimo.api_key,
            base_url=s.mimo.base_url,
            model=s.mimo.model,
        ))
    
    return MultimodalRouter(
        deepseek_client=ds_client,
        mimo_client=mm_client,
        mode=mode,
    )
