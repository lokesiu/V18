"""
core/ai/multimodal.py - 多模态附件处理模块

提供文件类型嗅探、图像 Base64 编码、音频转写等功能，
为 MiMo 等支持 OpenAI 规范的模型构建多模态请求。
"""
from __future__ import annotations

import base64
import logging
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


# ── 文件类型枚举 ──────────────────────────────────────────────────────

class FileCategory(Enum):
    """附件分类"""
    TEXT = "text"        # PDF, Word, TXT, MD
    IMAGE = "image"      # PNG, JPG, JPEG
    AUDIO = "audio"      # MP3, WAV, M4A
    UNKNOWN = "unknown"


# ── 文件类型映射 ──────────────────────────────────────────────────────

TEXT_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.md'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac'}


# ── 文件类型检测 ──────────────────────────────────────────────────────

def classify_file(file_path: str | Path) -> FileCategory:
    """根据文件后缀分类文件类型
    
    Args:
        file_path: 文件路径
        
    Returns:
        FileCategory 枚举值
    """
    ext = Path(file_path).suffix.lower()
    
    if ext in TEXT_EXTENSIONS:
        return FileCategory.TEXT
    elif ext in IMAGE_EXTENSIONS:
        return FileCategory.IMAGE
    elif ext in AUDIO_EXTENSIONS:
        return FileCategory.AUDIO
    else:
        return FileCategory.UNKNOWN


def classify_files(file_paths: list[str]) -> dict[FileCategory, list[str]]:
    """批量分类文件
    
    Args:
        file_paths: 文件路径列表
        
    Returns:
        按类别分组的文件字典
    """
    result: dict[FileCategory, list[str]] = {
        FileCategory.TEXT: [],
        FileCategory.IMAGE: [],
        FileCategory.AUDIO: [],
        FileCategory.UNKNOWN: [],
    }
    
    for fp in file_paths:
        category = classify_file(fp)
        result[category].append(fp)
    
    return result


# ── 图像 Base64 编码 ──────────────────────────────────────────────────

def encode_image_base64(file_path: str | Path) -> Optional[str]:
    """将图像文件编码为 Base64 字符串
    
    Args:
        file_path: 图像文件路径
        
    Returns:
        Base64 编码的字符串，失败返回 None
    """
    try:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Image file not found: {file_path}")
            return None
        
        # 获取 MIME 类型
        mime_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
        }
        mime_type = mime_map.get(path.suffix.lower(), 'image/jpeg')
        
        # 读取并编码
        with open(path, 'rb') as f:
            image_data = f.read()
        
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"
        
    except Exception as e:
        logger.error(f"Failed to encode image {file_path}: {e}")
        return None


# ── Vision API 消息构建 ────────────────────────────────────────────────

def build_vision_message(
    image_paths: list[str],
    prompt: str = "请分析这张证据图片的内容，提取关键信息。",
) -> dict:
    """构建 OpenAI Vision API 格式的消息
    
    Args:
        image_paths: 图像文件路径列表
        prompt: 用户提示词
        
    Returns:
        OpenAI Vision API 格式的消息字典
    """
    content = [{"type": "text", "text": prompt}]
    
    for img_path in image_paths:
        base64_url = encode_image_base64(img_path)
        if base64_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": base64_url}
            })
    
    return {"role": "user", "content": content}


def build_multimodal_messages(
    system_prompt: str,
    text_content: str,
    image_paths: Optional[list[str]] = None,
    image_prompt: str = "请分析这些证据图片的内容，提取关键信息。",
) -> list[dict]:
    """构建包含图像的多模态消息列表
    
    Args:
        system_prompt: 系统提示词
        text_content: 文本内容
        image_paths: 图像文件路径列表（可选）
        image_prompt: 图像分析提示词
        
    Returns:
        OpenAI 格式的消息列表
    """
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # 添加文本内容
    if text_content:
        messages.append({"role": "user", "content": text_content})
    
    # 添加图像内容
    if image_paths:
        vision_msg = build_vision_message(image_paths, image_prompt)
        messages.append(vision_msg)
    
    return messages


# ── 音频转写 ──────────────────────────────────────────────────────────

class AudioTranscriber:
    """音频转写器 - 调用 Whisper 兼容接口"""
    
    def __init__(self, api_key: str, base_url: str, model: str = "whisper-1"):
        """
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 转写模型名称
        """
        self.api_key = api_key.strip()
        self.base_url = base_url.strip().rstrip("/")
        self.model = model
    
    def transcribe(self, audio_path: str | Path, language: str = "zh") -> Optional[str]:
        """转写音频文件为文本
        
        Args:
            audio_path: 音频文件路径
            language: 音频语言代码（默认中文）
            
        Returns:
            转写后的文本，失败返回 None
        """
        try:
            path = Path(audio_path)
            if not path.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return None
            
            url = f"{self.base_url}/v1/audio/transcriptions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            
            # 获取 MIME 类型
            mime_map = {
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.m4a': 'audio/mp4',
                '.ogg': 'audio/ogg',
                '.flac': 'audio/flac',
            }
            mime_type = mime_map.get(path.suffix.lower(), 'audio/mpeg')
            
            # 上传文件进行转写
            with open(path, 'rb') as f:
                files = {
                    'file': (path.name, f, mime_type)
                }
                data = {
                    'model': self.model,
                    'language': language,
                }
                
                with httpx.Client(timeout=120) as client:
                    resp = client.post(url, headers=headers, files=files, data=data)
                    resp.raise_for_status()
                    result = resp.json()
            
            return result.get('text', '')
            
        except Exception as e:
            logger.error(f"Audio transcription failed for {audio_path}: {e}")
            return None


def transcribe_audio_files(
    audio_paths: list[str],
    api_key: str,
    base_url: str,
    model: str = "whisper-1",
) -> str:
    """批量转写音频文件并合并结果
    
    Args:
        audio_paths: 音频文件路径列表
        api_key: API 密钥
        base_url: API 基础 URL
        model: 转写模型名称
        
    Returns:
        合并后的转写文本
    """
    transcriber = AudioTranscriber(api_key, base_url, model)
    results = []
    
    for audio_path in audio_paths:
        text = transcriber.transcribe(audio_path)
        if text:
            filename = Path(audio_path).name
            results.append(f"[音频文件: {filename}]\n{text}")
    
    return "\n\n".join(results)


# ── 统一多模态请求构建 ────────────────────────────────────────────────

class MultimodalRequestBuilder:
    """多模态请求构建器
    
    根据上传的文件自动构建合适的 API 请求。
    """
    
    def __init__(self, api_key: str, base_url: str, model: str):
        """
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
    
    def build_request(
        self,
        file_paths: list[str],
        system_prompt: str,
        text_prompt: str,
        image_prompt: str = "请分析这些证据图片的内容，提取关键法律信息。",
    ) -> tuple[list[dict], str]:
        """根据文件类型构建请求
        
        Args:
            file_paths: 文件路径列表
            system_prompt: 系统提示词
            text_prompt: 文本分析提示词
            image_prompt: 图像分析提示词
            
        Returns:
            (messages, model) 元组
        """
        # 分类文件
        classified = classify_files(file_paths)
        
        # 处理文本文件（提取内容）
        text_content = self._extract_text_content(classified[FileCategory.TEXT])
        
        # 处理音频文件（转写为文本）
        audio_text = ""
        if classified[FileCategory.AUDIO]:
            audio_text = transcribe_audio_files(
                classified[FileCategory.AUDIO],
                self.api_key,
                self.base_url,
            )
        
        # 合并所有文本
        full_text = text_prompt
        if text_content:
            full_text += f"\n\n--- 文档内容 ---\n{text_content}"
        if audio_text:
            full_text += f"\n\n--- 音频转写 ---\n{audio_text}"
        
        # 构建消息
        has_images = bool(classified[FileCategory.IMAGE])
        
        if has_images:
            # 多模态请求（包含图像）
            messages = build_multimodal_messages(
                system_prompt=system_prompt,
                text_content=full_text,
                image_paths=classified[FileCategory.IMAGE],
                image_prompt=image_prompt,
            )
        else:
            # 纯文本请求
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_text},
            ]
        
        return messages, self.model
    
    def _extract_text_content(self, text_files: list[str]) -> str:
        """从文本文件中提取内容
        
        Args:
            text_files: 文本文件路径列表
            
        Returns:
            提取的文本内容
        """
        contents = []
        
        for file_path in text_files:
            try:
                path = Path(file_path)
                if not path.exists():
                    continue
                
                # 简单文本文件直接读取
                if path.suffix.lower() in {'.txt', '.md'}:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        contents.append(f"[{path.name}]\n{f.read()}")
                
                # PDF 和 Word 文件需要额外处理（这里简化为占位）
                elif path.suffix.lower() == '.pdf':
                    contents.append(f"[{path.name}] (PDF 文件，需要专用解析器)")
                elif path.suffix.lower() in {'.docx', '.doc'}:
                    contents.append(f"[{path.name}] (Word 文件，需要专用解析器)")
                    
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
        
        return "\n\n".join(contents)


# ── 便捷函数 ──────────────────────────────────────────────────────────

def get_file_summary(file_paths: list[str]) -> dict:
    """获取文件分类摘要
    
    Args:
        file_paths: 文件路径列表
        
    Returns:
        包含各类文件数量和列表的字典
    """
    classified = classify_files(file_paths)
    
    return {
        "total": len(file_paths),
        "text_count": len(classified[FileCategory.TEXT]),
        "image_count": len(classified[FileCategory.IMAGE]),
        "audio_count": len(classified[FileCategory.AUDIO]),
        "unknown_count": len(classified[FileCategory.UNKNOWN]),
        "has_images": bool(classified[FileCategory.IMAGE]),
        "has_audio": bool(classified[FileCategory.AUDIO]),
        "files": {
            "text": classified[FileCategory.TEXT],
            "image": classified[FileCategory.IMAGE],
            "audio": classified[FileCategory.AUDIO],
        }
    }
