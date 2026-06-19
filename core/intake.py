"""
intake.py - File Discovery and Reading

Scans the input directory for legal documents and extracts text content.
Supports: PDF, DOCX, DOC, TXT, JPG, PNG
Uses pypdf for PDF, python-docx for DOCX, plain open() for TXT.
Images are noted but not OCR'd at this stage.
"""
from __future__ import annotations
import os
import glob as globmod
from pathlib import Path
from typing import List

from core.fact_card import PipelineContext


# Supported file extensions and their types
SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "doc",
    ".txt": "txt",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
}


def scan_input_dir(input_dir: str) -> List[str]:
    """
    Find all supported files in the input directory.
    Searches recursively through subdirectories.
    Returns list of absolute file paths sorted by name.
    """
    if not os.path.isdir(input_dir):
        return []

    found_files: List[str] = []
    for ext in SUPPORTED_EXTENSIONS:
        pattern = os.path.join(input_dir, "**", f"*{ext}")
        matches = globmod.glob(pattern, recursive=True)
        found_files.extend(matches)

    # Also search for uppercase extensions
    for ext in SUPPORTED_EXTENSIONS:
        pattern = os.path.join(input_dir, "**", f"*{ext.upper()}")
        matches = globmod.glob(pattern, recursive=True)
        found_files.extend(matches)

    # Deduplicate (in case both .pdf and .PDF match) and sort
    unique_files = sorted(set(os.path.abspath(f) for f in found_files))
    return unique_files


def read_text_file(path: str) -> str:
    """Read a .txt file and return its content as a string."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def read_docx_text(path: str) -> str:
    """
    Extract all text from a .docx file using python-docx.
    Falls back to basic XML extraction if python-docx fails.
    """
    try:
        from docx import Document
        doc = Document(path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    if cell_text:
                        paragraphs.append(cell_text)
        return "\n".join(paragraphs)
    except ImportError:
        # Fallback: try to read raw XML from the docx zip
        import zipfile
        import xml.etree.ElementTree as ET

        try:
            with zipfile.ZipFile(path, "r") as z:
                with z.open("word/document.xml") as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                    texts = []
                    for t in root.iter(f"{{{ns['w']}}}t"):
                        if t.text:
                            texts.append(t.text)
                    return " ".join(texts)
        except Exception:
            return f"[无法读取DOCX文件: {os.path.basename(path)}]"


def read_pdf_text(path: str) -> str:
    """
    Extract text from a PDF file using pypdf.
    Returns extracted text with page separators.
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages_text.append(f"--- 第{i + 1}页 ---\n{text.strip()}")
        return "\n\n".join(pages_text)
    except ImportError:
        return f"[无法读取PDF文件: pypdf未安装 - {os.path.basename(path)}]"
    except Exception as e:
        return f"[PDF读取失败: {os.path.basename(path)} - {str(e)}]"


def read_image_placeholder(path: str) -> str:
    """
    Return a placeholder for image files.
    OCR is not implemented at this stage - images are noted for later processing.
    """
    filename = os.path.basename(path)
    return f"[图片文件: {filename} - 需要OCR处理才能提取文字内容]"


def ocr_images_via_api(image_paths: list[str]) -> dict[str, str]:
    """Use vision API to OCR image files and return {path: text} mapping."""
    try:
        from core.settings_store import get_settings_store
        store = get_settings_store()
        s = store.settings

        provider = None
        vision_model = ""
        if s.mimo.is_configured():
            from core.ai.unified_client import UnifiedAIClient, ProviderConfig
            provider = UnifiedAIClient(ProviderConfig(
                name="mimo",
                api_key=s.mimo.api_key,
                base_url=s.mimo.base_url,
                model=s.mimo.model,
                timeout=s.mimo.timeout,
            ))
            vision_model = s.mimo.model
        elif s.deepseek.is_configured():
            from core.ai.unified_client import UnifiedAIClient, ProviderConfig
            provider = UnifiedAIClient(ProviderConfig(
                name="deepseek",
                api_key=s.deepseek.api_key,
                base_url=s.deepseek.base_url,
                model="deepseek-chat",
                timeout=s.deepseek.timeout,
            ))
            vision_model = "deepseek-chat"

        if not provider or not provider.is_configured:
            return {}

        from core.ai.multimodal import encode_image_base64
        results = {}
        batch_size = 3

        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i + batch_size]
            content = [{"type": "text", "text": "请逐张分析这些证据图片，提取所有可见文字内容、当事人信息、日期、金额等关键法律信息。对每张图片分别输出，标注文件名。"}]

            for img_path in batch:
                b64 = encode_image_base64(img_path)
                if b64:
                    content.append({"type": "image_url", "image_url": {"url": b64}})

            if len(content) <= 1:
                continue

            messages = [
                {"role": "system", "content": "你是一个法律文档OCR助手。请精确提取图片中的所有文字内容。"},
                {"role": "user", "content": content},
            ]

            response = provider.chat_messages(messages, model=vision_model, temperature=0.1, max_tokens=4096)
            if response.success and response.content:
                parts = response.content.split("---")
                for j, img_path in enumerate(batch):
                    if j < len(parts):
                        results[img_path] = parts[j].strip()
                    else:
                        results[img_path] = response.content.strip()

        return results
    except Exception:
        return {}


def read_file(path: str) -> str:
    """
    Read a file based on its extension.
    Returns the extracted text content or an error message.
    """
    ext = os.path.splitext(path)[1].lower()
    file_type = SUPPORTED_EXTENSIONS.get(ext, "unknown")

    try:
        if file_type == "txt":
            return read_text_file(path)
        elif file_type == "docx":
            return read_docx_text(path)
        elif file_type == "pdf":
            return read_pdf_text(path)
        elif file_type == "image":
            return read_image_placeholder(path)
        elif file_type == "doc":
            # Legacy .doc format - attempt with python-docx (may fail)
            try:
                return read_docx_text(path)
            except Exception:
                return f"[无法读取DOC文件: {os.path.basename(path)} - 请转换为DOCX格式]"
        else:
            return f"[不支持的文件格式: {ext} - {os.path.basename(path)}]"
    except Exception as e:
        return f"[文件读取错误: {os.path.basename(path)} - {str(e)}]"


def run_intake(ctx: PipelineContext) -> PipelineContext:
    """
    Main entry point for the intake pipeline stage.
    
    1. Scans input_dir for supported files
    2. Reads text content from each file
    3. Populates ctx.raw_texts and ctx.file_list
    4. Logs each file found and processed
    5. Skips unreadable files with warning
    """
    ctx.log(f"开始扫描输入目录: {ctx.input_dir}")

    if not os.path.isdir(ctx.input_dir):
        ctx.add_error(f"输入目录不存在: {ctx.input_dir}")
        return ctx

    files = scan_input_dir(ctx.input_dir)

    if not files:
        ctx.add_error(f"输入目录中未找到支持的文件: {ctx.input_dir}")
        return ctx

    ctx.log(f"找到 {len(files)} 个文件")

    ctx.file_list = files
    ctx.raw_texts = []

    image_files = [f for f in files
                   if os.path.splitext(f)[1].lower() in {'.jpg', '.jpeg', '.png'}]
    text_files = [f for f in files if f not in image_files]

    for file_path in text_files:
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        file_type = SUPPORTED_EXTENSIONS.get(ext, "unknown")

        ctx.log(f"读取文件: {filename} (类型: {file_type})")

        text = read_file(file_path)

        if text.startswith("[") and text.endswith("]"):
            ctx.log(f"警告: {filename} - {text}")
            ctx.raw_texts.append(text)
        else:
            ctx.raw_texts.append(text)
            word_count = len(text)
            ctx.log(f"成功读取: {filename} ({word_count} 字符)")

    if image_files:
        ctx.log(f"检测到 {len(image_files)} 个图片文件，正在通过 Vision API 提取文字...")
        ocr_results = ocr_images_via_api(image_files)

        for img_path in image_files:
            filename = os.path.basename(img_path)
            if img_path in ocr_results and ocr_results[img_path].strip():
                text = ocr_results[img_path]
                ctx.raw_texts.append(text)
                ctx.log(f"OCR 成功: {filename} ({len(text)} 字符)")
            else:
                placeholder = read_image_placeholder(img_path)
                ctx.raw_texts.append(placeholder)
                ctx.log(f"OCR 失败/跳过: {filename}，使用占位符")

    ctx.log(f"文件读取完成: 成功 {sum(1 for t in ctx.raw_texts if not t.startswith('['))} 个, "
            f"失败/跳过 {sum(1 for t in ctx.raw_texts if t.startswith('['))} 个")

    return ctx
