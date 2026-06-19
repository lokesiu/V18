"""core/pipeline/step7_render_manifest.py — Manifest-aware render wrapper.

Wraps each file render in step7 with manifest tracking:
- Before render: check if file already succeeded (skip if so)
- After render: mark success/failed in manifest
- On partial failure: mark task as '部分完成'

Also provides retry_render(task_id) for re-rendering failed files.

Does NOT modify the underlying renderers.
"""
from __future__ import annotations

import os
import time
import traceback
from typing import Callable, Optional

from core.fact_card import PipelineContext

MAX_RETRY = 3

# ── Error classification ─────────────────────────────────────────────
_RETRYABLE_ERRORS = {
    "PermissionError",      # file locked
    "WinError",             # Windows file lock
    "OSError",              # transient IO (but not errno 28=ENOSPC)
    "TimeoutError",         # converter timeout
    "ConnectionError",      # network-dependent converter
    "RENDER_FAILED",        # renderer returned False (may be transient)
    "EMPTY_FILE",           # file was empty (may be transient)
    "ZIP_WRITE_ERROR",      # zip temporary failure
}

_NON_RETRYABLE_ERRORS = {
    "FileNotFoundError",    # source file missing
    "ModuleNotFoundError",  # converter module not installed
    "ImportError",          # converter module not installed
    "ENOSPC",               # disk full
    "TEMPLATE_MISSING",     # template data missing
    "SOURCE_MISSING",       # source DOCX missing for PDF conversion
    "ENVIRONMENT_ERROR",    # PDF converter not available
}


def is_retryable(error_code: str, error_msg: str = "") -> bool:
    """Determine if an error is retryable."""
    if error_code in _NON_RETRYABLE_ERRORS:
        return False
    # Check for disk full in message
    if "No space left" in error_msg or "ENOSPC" in error_msg:
        return False
    # Check for missing source file
    if "No such file" in error_msg or "找不到" in error_msg:
        return False
    # Check for environment issues
    if "not installed" in error_msg or "not found" in error_msg:
        return False
    if error_code in _RETRYABLE_ERRORS:
        return True
    # Default: allow retry for unknown errors
    return True


# ── File size helper ──────────────────────────────────────────────────
def _file_size(path: str) -> int:
    """Get file size, return 0 if not found."""
    try:
        return os.path.getsize(path) if os.path.exists(path) else 0
    except OSError:
        return 0


# ── Core render with manifest ────────────────────────────────────────
def render_with_manifest(
    ctx: PipelineContext,
    task_id: str,
    file_name: str,
    file_type: str,
    render_fn: Callable[[], bool],
    output_path: str,
    source_file: str = "",
    ts=None,
) -> bool:
    """Render a single file with manifest tracking.

    Args:
        ctx: PipelineContext for logging.
        task_id: Task ID for manifest.
        file_name: e.g. "01_案件处境评估报告.docx"
        file_type: e.g. "docx", "pdf", "xlsx", "zip"
        render_fn: Callable that renders the file and returns True/False.
        output_path: Expected output file path.
        source_file: For PDF, the source DOCX path.
        ts: TaskStore instance.

    Returns:
        True if render succeeded or was skipped (already succeeded).
    """
    if ts is None:
        from core.task_store import get_task_store
        ts = get_task_store()

    # ── Check existing manifest entry ──
    entry = ts.manifest_get_entry(task_id, file_name)

    if entry and entry.get("status") == "success":
        # Verify file still exists on disk
        if os.path.exists(output_path) and _file_size(output_path) > 0:
            ctx.log(f"  跳过 {file_name} (已完成且文件存在)")
            return True
        else:
            # File was deleted externally — reset to pending
            ctx.log(f"  {file_name} 已完成但文件不存在，重新渲染")
            ts.manifest_init_entry(task_id, file_name, file_type, source_file)

    # ── Initialize manifest entry if not exists ──
    if not entry:
        ts.manifest_init_entry(task_id, file_name, file_type, source_file)

    # ── Execute render ──
    try:
        success = render_fn()
    except Exception as exc:
        success = False
        ctx.log(f"  渲染异常 {file_name}: {exc}")
        try:
            with open("crash_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"=== RENDER EXCEPTION: {file_name} ===\n")
                f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*60}\n")
                f.write(traceback.format_exc())
                f.write("\n")
        except Exception:
            pass
        ts.manifest_mark_failed(
            task_id, file_name,
            error_code=type(exc).__name__,
            error_msg=str(exc)[:200],
        )
        return False

    if success:
        # Verify file was actually created
        size = _file_size(output_path)
        if size > 0:
            ts.manifest_mark_success(task_id, file_name, file_size=size)
            ctx.log(f"  渲染成功: {file_name} ({size:,} bytes)")
            return True
        else:
            ts.manifest_mark_failed(
                task_id, file_name,
                error_code="EMPTY_FILE",
                error_msg="渲染函数返回成功但文件为空或不存在",
            )
            ctx.log(f"  渲染失败 {file_name}: 文件为空")
            return False
    else:
        ts.manifest_mark_failed(
            task_id, file_name,
            error_code="RENDER_FAILED",
            error_msg="渲染函数返回失败",
        )
        ctx.log(f"  渲染失败: {file_name}")
        return False


# ── Query helpers ─────────────────────────────────────────────────────
def get_manifest_summary(task_id: str, ts=None) -> dict:
    """Get render manifest summary for a task."""
    if ts is None:
        from core.task_store import get_task_store
        ts = get_task_store()
    return ts.manifest_summary(task_id)


def get_manifest_entries(task_id: str, ts=None) -> list[dict]:
    """Get all manifest entries for a task."""
    if ts is None:
        from core.task_store import get_task_store
        ts = get_task_store()
    return ts.manifest_list_entries(task_id)


# ── Retry logic ──────────────────────────────────────────────────────
def _check_source_dependency(entry: dict, customer_dir: str) -> tuple[bool, str]:
    """Check if source file dependency exists for a manifest entry.

    Returns (ok, reason). ok=False means skip this retry.
    """
    source = entry.get("source_file", "")
    if not source:
        return True, ""

    # Source is a DOCX path for PDF conversion
    if not os.path.exists(source):
        return False, f"源文件不存在: {os.path.basename(source)}"

    if _file_size(source) == 0:
        return False, f"源文件为空: {os.path.basename(source)}"

    return True, ""


def retry_render(
    task_id: str,
    ts=None,
    audit=None,
    emit_log: Optional[Callable[[str], None]] = None,
) -> dict:
    """Retry rendering failed files for a task.

    Args:
        task_id: Task ID to retry.
        ts: TaskStore instance.
        audit: AuditStore instance.
        emit_log: Optional log callback.

    Returns:
        Dict with results: {retried, succeeded, failed, skipped, final_status}
    """
    if ts is None:
        from core.task_store import get_task_store
        ts = get_task_store()
    if audit is None:
        from core.audit_store import get_audit_store
        audit = get_audit_store()

    def log(msg: str):
        if emit_log:
            emit_log(msg)

    # Get task info
    task = ts.get_task(task_id)
    if not task:
        return {"error": "task_not_found"}

    task_dict = task.to_dict()
    output_dir = task_dict.get("output_dir", "")
    customer_dir = os.path.join(output_dir, "customer") if output_dir else ""

    # Get failed entries
    failed_entries = ts.manifest_list_failed(task_id)
    if not failed_entries:
        log("没有失败文件需要重试")
        return {"retried": 0, "succeeded": 0, "failed": 0, "skipped": 0,
                "final_status": task_dict.get("status", "")}

    log(f"开始重试 {len(failed_entries)} 个失败文件")
    audit.log_event(task_id, "retry_started", severity="info",
                    message=f"开始重试 {len(failed_entries)} 个失败文件")

    results = {"retried": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    for entry in failed_entries:
        fname = entry.get("file_name", "")
        ftype = entry.get("file_type", "")
        error_code = entry.get("error_code", "")
        error_msg = entry.get("error_msg", "")
        attempt = entry.get("attempt", 1)

        # ── Check max retries ──
        if attempt >= MAX_RETRY:
            log(f"  跳过 {fname}: 已达最大重试次数 ({MAX_RETRY})")
            ts.manifest_mark_skipped(task_id, fname, f"已达最大重试次数 ({MAX_RETRY})")
            results["skipped"] += 1
            audit.log_event(task_id, "file_retry_skipped", stage_name=ftype,
                            severity="warning",
                            message=f"跳过 {fname}: 已达最大重试次数",
                            detail={"file_name": fname, "attempt": attempt})
            continue

        # ── Check if error is retryable ──
        if not is_retryable(error_code, error_msg):
            log(f"  跳过 {fname}: 不可重试错误 ({error_code})")
            ts.manifest_mark_skipped(task_id, fname, f"不可重试错误: {error_code}")
            results["skipped"] += 1
            audit.log_event(task_id, "file_retry_skipped", stage_name=ftype,
                            severity="warning",
                            message=f"跳过 {fname}: 不可重试 ({error_code})",
                            detail={"file_name": fname, "error_code": error_code})
            continue

        # ── Check source dependency ──
        ok, reason = _check_source_dependency(entry, customer_dir)
        if not ok:
            log(f"  跳过 {fname}: {reason}")
            ts.manifest_mark_skipped(task_id, fname, reason)
            results["skipped"] += 1
            audit.log_event(task_id, "file_retry_skipped", stage_name=ftype,
                            severity="warning",
                            message=f"跳过 {fname}: {reason}",
                            detail={"file_name": fname, "reason": reason})
            continue

        # ── Retry render ──
        results["retried"] += 1
        log(f"  重试 {fname} (第 {attempt + 1} 次)")
        audit.log_event(task_id, "file_retry_started", stage_name=ftype,
                        severity="info",
                        message=f"重试 {fname} (第 {attempt + 1} 次)",
                        detail={"file_name": fname, "attempt": attempt + 1})

        output_path = os.path.join(customer_dir, fname) if customer_dir else ""

        # Build render function based on file type
        render_fn = _build_retry_render_fn(fname, ftype, output_path, task_dict)
        if render_fn is None:
            log(f"  跳过 {fname}: 无法构建渲染函数")
            ts.manifest_mark_skipped(task_id, fname, "无法构建渲染函数")
            results["skipped"] += 1
            continue

        # Execute with small delay to avoid file lock contention
        time.sleep(0.5)

        try:
            success = render_fn()
        except Exception as exc:
            success = False
            log(f"  重试异常 {fname}: {exc}")
            ts.manifest_mark_failed(task_id, fname,
                                    error_code=type(exc).__name__,
                                    error_msg=str(exc)[:200])
            audit.log_event(task_id, "file_retry_failed", stage_name=ftype,
                            severity="error",
                            message=f"重试失败 {fname}: {exc}",
                            detail={"file_name": fname, "error": str(exc)[:200]})
            results["failed"] += 1
            continue

        if success:
            size = _file_size(output_path)
            if size > 0:
                ts.manifest_mark_success(task_id, fname, file_size=size)
                log(f"  重试成功: {fname} ({size:,} bytes)")
                audit.log_event(task_id, "file_retry_succeeded", stage_name=ftype,
                                severity="info",
                                message=f"重试成功: {fname} ({size:,} bytes)",
                                detail={"file_name": fname, "file_size": size})
                results["succeeded"] += 1
            else:
                ts.manifest_mark_failed(task_id, fname,
                                        error_code="EMPTY_FILE",
                                        error_msg="重试后文件仍为空")
                log(f"  重试失败 {fname}: 文件为空")
                audit.log_event(task_id, "file_retry_failed", stage_name=ftype,
                                severity="error",
                                message=f"重试失败 {fname}: 文件为空",
                                detail={"file_name": fname})
                results["failed"] += 1
        else:
            ts.manifest_mark_failed(task_id, fname,
                                    error_code="RETRY_FAILED",
                                    error_msg="重试渲染函数返回失败")
            log(f"  重试失败: {fname}")
            audit.log_event(task_id, "file_retry_failed", stage_name=ftype,
                            severity="error",
                            message=f"重试失败 {fname}",
                            detail={"file_name": fname})
            results["failed"] += 1

    # ── Determine final status ──
    summary = ts.manifest_summary(task_id)
    success_count = summary.get("success", 0)
    failed_count = summary.get("failed", 0)
    total_count = sum(summary.values())

    if failed_count == 0 and success_count > 0:
        final_status = "已完成"
        ts.update_task_status(task_id, "已完成")
        log("所有文件渲染成功，任务状态更新为 已完成")
        audit.log_event(task_id, "retry_completed", severity="info",
                        message="重试完成: 所有文件成功")
    elif success_count > 0:
        final_status = "部分完成"
        ts.update_task_status(task_id, "部分完成")
        log(f"重试完成: {success_count}/{total_count} 个文件成功")
        audit.log_event(task_id, "retry_completed", severity="warning",
                        message=f"重试完成: 仍有 {failed_count} 个文件失败")
    else:
        final_status = "失败"
        ts.update_task_status(task_id, "失败")
        log("重试完成: 所有文件仍然失败")
        audit.log_event(task_id, "retry_completed", severity="error",
                        message="重试完成: 所有文件仍然失败")

    results["final_status"] = final_status
    return results


def _build_retry_render_fn(
    file_name: str,
    file_type: str,
    output_path: str,
    task_dict: dict,
) -> Optional[Callable[[], bool]]:
    """Build a render function for retry based on file type and manifest info.

    Returns None if the render function cannot be constructed.
    """
    output_dir = task_dict.get("output_dir", "")
    customer_dir = os.path.join(output_dir, "customer") if output_dir else ""

    if not output_dir or not customer_dir:
        return None

    if file_type == "docx":
        return _build_docx_retry_fn(file_name, output_path, task_dict)
    elif file_type == "pdf":
        return _build_pdf_retry_fn(file_name, output_path, task_dict)
    elif file_type == "xlsx":
        return _build_xlsx_retry_fn(file_name, output_path, task_dict)
    elif file_type == "zip":
        return _build_zip_retry_fn(output_path, customer_dir)
    else:
        return None


def _build_docx_retry_fn(file_name: str, output_path: str, task_dict: dict) -> Optional[Callable]:
    """Build retry function for DOCX files."""
    # For DOCX files, we need the filled templates or strategy card
    # Since we can't easily reconstruct PipelineContext, use fallback content
    identity = task_dict.get("identity", "")
    goal = task_dict.get("goal", "")

    def render():
        from core.pipeline.step7_render import _render_docx_from_content, _render_strategy_docx
        from core.pipeline.step6_template_fill import _generate_fallback_content
        from core.fact_card import PipelineContext
        # Create minimal context for fallback
        ctx = PipelineContext(identity=identity, goal=goal)
        # Try to load distilled card from output_dir
        output_dir = task_dict.get("output_dir", "")
        distilled_path = os.path.join(output_dir, "_internal", "distilled_card.json") if output_dir else ""
        if os.path.exists(distilled_path):
            try:
                from core.fact_card import DistilledCard
                ctx.distilled_card = DistilledCard.load(distilled_path)
                if ctx.distilled_card.fact_card:
                    ctx.fact_card = ctx.distilled_card.fact_card
                if ctx.distilled_card.strategy_card:
                    ctx.strategy_card = ctx.distilled_card.strategy_card
            except Exception:
                pass

        # Determine doc type from file name: "06_答辩状_程颖颖案.docx" -> "答辩状"
        parts = file_name.split("_")
        doc_type = parts[1] if len(parts) >= 2 else file_name.rsplit(".", 1)[0]

        # Try strategy card content first
        if ctx.strategy_card and doc_type in ("案件处境评估报告", "行动建议书", "证据闭环补强清单"):
            return _render_strategy_docx(ctx.strategy_card, doc_type, output_path, ctx)

        # Fallback to generated content
        content = _generate_fallback_content(doc_type, ctx)
        return _render_docx_from_content(content, output_path, ctx)

    return render


def _build_pdf_retry_fn(file_name: str, output_path: str, task_dict: dict) -> Optional[Callable]:
    """Build retry function for PDF files."""
    output_dir = task_dict.get("output_dir", "")
    customer_dir = os.path.join(output_dir, "customer") if output_dir else ""
    source_docx = os.path.join(customer_dir, file_name.replace(".pdf", ".docx"))

    if not os.path.exists(source_docx):
        return None  # Source DOCX missing, can't retry

    def render():
        from core.render.pdf_converter import convert_to_pdf
        return convert_to_pdf(source_docx, output_path)

    return render


def _build_xlsx_retry_fn(file_name: str, output_path: str, task_dict: dict) -> Optional[Callable]:
    """Build retry function for XLSX files."""
    output_dir = task_dict.get("output_dir", "")

    def render():
        from core.render.xlsx_renderer import render_xlsx
        from core.fact_card import FactCard
        # Try to load fact card
        distilled_path = os.path.join(output_dir, "_internal", "distilled_card.json") if output_dir else ""
        if os.path.exists(distilled_path):
            try:
                from core.fact_card import DistilledCard
                dc = DistilledCard.load(distilled_path)
                if dc.fact_card:
                    return render_xlsx(dc.fact_card, output_path)
            except Exception:
                pass
        return False

    return render


def _build_zip_retry_fn(output_path: str, customer_dir: str) -> Optional[Callable]:
    """Build retry function for ZIP file."""
    def render():
        from core.render.zip_builder import build_zip
        try:
            build_zip(customer_dir, output_path)
            return os.path.exists(output_path) and _file_size(output_path) > 0
        except Exception:
            # Manual fallback
            from core.pipeline.step7_render import _manual_build_zip
            _manual_build_zip(customer_dir, output_path)
            return os.path.exists(output_path) and _file_size(output_path) > 0

    return render
