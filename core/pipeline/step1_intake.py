"""
step1_intake.py - Pipeline Step 1: File Intake

Scans the input directory for documents (PDF, DOCX, XLSX, images, TXT),
extracts raw text content, and populates PipelineContext.raw_texts and
PipelineContext.file_list.

Critical step - if no files are found or intake fails, pipeline stops.
"""
from __future__ import annotations

from core.fact_card import PipelineContext
from core.intake import run_intake


def step1_intake(ctx: PipelineContext) -> PipelineContext:
    """Scan input_dir, extract text from all supported files into ctx.raw_texts.

    Delegates to core.intake.run_intake which:
    - Walks ctx.input_dir for supported file types
    - Extracts text content from each file
    - Populates ctx.raw_texts (extracted text per file)
    - Populates ctx.file_list (list of file paths)

    Args:
        ctx: PipelineContext with input_dir set.

    Returns:
        PipelineContext with raw_texts and file_list populated,
        or errors appended if intake failed.
    """
    ctx.log("Step 1: 文件采集 - 扫描输入目录并提取文本内容")

    if not ctx.input_dir:
        ctx.add_error("未指定输入目录 (input_dir)，无法执行文件采集")
        return ctx

    try:
        run_intake(ctx)
    except FileNotFoundError as exc:
        ctx.add_error(f"输入目录不存在: {ctx.input_dir} - {exc}")
        return ctx
    except PermissionError as exc:
        ctx.add_error(f"无权访问输入目录: {ctx.input_dir} - {exc}")
        return ctx
    except Exception as exc:
        ctx.add_error(f"文件采集过程中发生未知错误: {exc}")
        return ctx

    file_count = len(ctx.file_list)
    text_count = len(ctx.raw_texts)
    real_text_count = sum(1 for t in ctx.raw_texts if not t.startswith("["))
    ctx.log(f"Step 1 完成: 发现 {file_count} 个文件, 提取 {text_count} 段文本内容 ({real_text_count} 段有效文本)")

    if file_count == 0:
        ctx.add_error(f"输入目录中未发现任何支持的文件: {ctx.input_dir}")
        return ctx

    if text_count == 0 and file_count > 0:
        ctx.add_error(f"发现 {file_count} 个文件但未能提取到任何文本内容，文件可能已损坏或格式不支持")
        return ctx

    # Log summary of discovered files
    for i, fpath in enumerate(ctx.file_list, 1):
        ctx.log(f"  文件 {i}: {fpath}")

    return ctx
