"""Background worker thread for V18 analysis pipeline.

Integrates with core.task_store for task persistence.  All task_store
writes are wrapped in try/except so a DB failure never kills the
pipeline itself.
"""
from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal


# Display names for the 8 pipeline steps (must match core.pipeline.STAGE_NAMES)
PIPELINE_STAGES = [
    "读取材料",
    "提取事实",
    "事实蒸馏",
    "策略推演",
    "蒸馏合并",
    "文书生成",
    "文档渲染",
    "质量检查",
]

# Map step index → step name for task_store
_STEP_INDEX_TO_NAME = {i: name for i, name in enumerate(PIPELINE_STAGES)}


def _safe_task_call(fn, *args, **kwargs):
    """Call a task_store function without letting exceptions propagate."""
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _write_crash_log(label: str, exc: Exception):
    """Write crash traceback to crash_debug.log (append mode)."""
    try:
        with open("crash_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"=== {label} ===\n")
            f.write(f"Time: {datetime.now().isoformat()}\n")
            f.write(f"{'='*60}\n")
            f.write(traceback.format_exc())
            f.write("\n")
    except Exception:
        pass


class AnalysisWorker(QThread):
    """Run the analysis pipeline off the main thread.

    Signals are emitted in real time as each pipeline step executes.
    Task lifecycle is persisted to task_store at each key point.
    """

    progress = Signal(int)
    log = Signal(str)
    finished = Signal(bool, str)
    finished_with_files = Signal(bool, str, list)
    stage_started = Signal(str)
    stage_done = Signal(str)
    stage_failed = Signal(str, str)
    stage_substatus = Signal(str, str)  # (stage_name, substatus_text)
    task_created = Signal(str)          # emits task_id when task is persisted
    error_occurred = Signal(str, str)   # (error_title, error_details)

    def __init__(
        self,
        files: list[str],
        identity: str,
        goal: str,
        purpose: str = "",
    ) -> None:
        super().__init__()
        self.files = files
        self.identity = identity
        self.goal = goal
        self.purpose = purpose
        self._cancelled = False
        self._last_error: str = ""
        self._quality_warnings: list[str] = []
        self._task_id: str = ""
        self._ctx = None  # PipelineContext reference for checkpoint building

    def cancel(self):
        self._cancelled = True

    def _on_step(self, step_index: int, step_name: str, event: str):
        """Callback from pipeline — emits real-time stage signals,
        persists step progress to task_store, writes audit + checkpoint."""
        if event == "start":
            self.stage_started.emit(step_name)
            self.progress.emit(int(((step_index + 0.5) / 8) * 90))
            _safe_task_call(
                self._ts.update_task_step, self._task_id, step_index, "进行中"
            )
            _safe_task_call(
                self._audit.log_step_started, self._task_id, step_index, step_name
            )
        elif event == "done":
            self.stage_done.emit(step_name)
            self.progress.emit(int(((step_index + 1) / 8) * 90))
            _safe_task_call(
                self._audit.log_step_done, self._task_id, step_index, step_name
            )
            # Write checkpoint for steps with recoverable content
            if step_index >= 2:
                self._save_checkpoint(step_index, step_name, "done")
        elif event == "failed":
            self.stage_failed.emit(step_name, "")
            _safe_task_call(
                self._ts.set_task_error, self._task_id, f"{step_name} 失败"
            )
            _safe_task_call(
                self._audit.log_step_failed, self._task_id, step_index, step_name, ""
            )
            # Write failed checkpoint so resume knows where to pick up
            if step_index >= 2:
                self._save_checkpoint(step_index, step_name, "failed")

    def _save_checkpoint(self, step_index: int, step_name: str, status: str):
        """Build ctx_snapshot and persist to checkpoints table."""
        if not self._ctx:
            return
        try:
            from core.checkpoint_builder import build_ctx_snapshot
            snapshot = build_ctx_snapshot(self._ctx)
            self._ts.save_checkpoint(
                self._task_id, step_index, step_name, snapshot, status
            )
            # Mark task as resumable if we have a successful checkpoint
            if status == "done" and step_index >= 2:
                _safe_task_call(self._ts.set_resumable, self._task_id, True)
            # Log checkpoint audit event
            _safe_task_call(
                self._audit.log_checkpoint_saved, self._task_id, step_index, step_name
            )
        except Exception:
            pass  # checkpoint failure must not break pipeline

    def run(self) -> None:
        output_dir = ""
        try:
            # ── Acquire stores ──
            from core.task_store import get_task_store
            from core.audit_store import get_audit_store
            from core.pipeline import AIProviderError
            self._ts = get_task_store()
            self._audit = get_audit_store()

            # ── Create task record ──
            task_rec = _safe_task_call(
                self._ts.create_task,
                identity=self.identity,
                goal=self.goal,
                file_list=self.files,
            )
            if task_rec:
                self._task_id = task_rec.task_id
                self.task_created.emit(self._task_id)
                self.log.emit(f"任务已创建: {self._task_id}")
                _safe_task_call(
                    self._audit.log_task_created,
                    self._task_id, self.identity, self.goal, self.files,
                )

            # ── Prepare output directory ──
            case_label = self._task_id or datetime.now().strftime("case_%Y%m%d_%H%M%S")
            output_dir = str(Path("outputs") / case_label)
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(os.path.join(output_dir, "customer"), exist_ok=True)

            # Update task with output_dir
            _safe_task_call(self._ts.set_task_output, self._task_id, output_dir)
            _safe_task_call(self._audit.log_task_started, self._task_id)

            self.log.emit(f"输出目录: {output_dir}")
            self.progress.emit(5)

            input_dir = str(Path(self.files[0]).parent)

            from core.fact_card import PipelineContext
            from core.pipeline import run_pipeline

            ctx = PipelineContext(
                input_dir=input_dir,
                output_dir=output_dir,
                identity=self.identity,
                goal=self.goal,
                purpose=self.purpose,
                file_list=self.files,
                task_id=self._task_id,
                task_status="进行中",
            )
            self._ctx = ctx  # keep reference for checkpoint building

            # Run pipeline with real-time step callbacks
            ctx = run_pipeline(ctx, on_step=self._on_step)

            # Diagnostic dump — write pipeline state to crash_debug.log
            try:
                with open("crash_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"=== DIAGNOSTIC DUMP ===\n")
                    f.write(f"Time: {datetime.now().isoformat()}\n")
                    f.write(f"Task ID: {self._task_id}\n")
                    f.write(f"Input dir: {ctx.input_dir}\n")
                    f.write(f"File list ({len(ctx.file_list)}): {ctx.file_list[:5]}\n")
                    f.write(f"Raw texts count: {len(ctx.raw_texts)}\n")
                    for i, t in enumerate(ctx.raw_texts[:3]):
                        preview = t[:200] if t else "(empty)"
                        f.write(f"  raw_text[{i}]: {preview}\n")
                    f.write(f"Fact card: {ctx.fact_card is not None}\n")
                    if ctx.fact_card:
                        f.write(f"  key_facts: {len(ctx.fact_card.key_facts)}\n")
                        f.write(f"  parties: {len(ctx.fact_card.parties)}\n")
                    f.write(f"Errors ({len(ctx.errors)}): {ctx.errors[:5]}\n")
                    f.write(f"Rendered files: {getattr(ctx, '_rendered_files', [])}\n")
                    quality_blocked = getattr(ctx, '_quality_blocked', False)
                    f.write(f"Quality blocked: {quality_blocked}\n")
                    f.write(f"{'='*60}\n\n")
            except Exception:
                pass

            # Log quality gate results (non-blocking)
            gate_result = getattr(ctx, "_quality_gate_result", None)
            if gate_result and gate_result.status in ("passed", "warning"):
                stage = "step2" if gate_result.status == "passed" or not any(
                    i.rule.startswith(("court", "parties_after", "amount"))
                    for i in gate_result.issues
                ) else "step3"
                _safe_task_call(
                    self._audit.log_quality_gate,
                    self._task_id, stage, gate_result.status,
                    [i.to_dict() for i in gate_result.issues],
                )

            self.progress.emit(100)

            rendered_files = getattr(ctx, "_rendered_files", [])
            render_failed = getattr(ctx, "_render_failed_files", [])

            # ── Check for quality gate block ──
            quality_blocked = getattr(ctx, "_quality_blocked", False)
            quality_gate_result = getattr(ctx, "_quality_gate_result", None)

            if quality_blocked and quality_gate_result:
                issues_dicts = [i.to_dict() for i in quality_gate_result.issues]
                stage_name = "step2" if any(
                    i.rule.startswith(("raw_texts", "fact_card", "key_facts"))
                    for i in quality_gate_result.issues
                ) else "step3"
                _safe_task_call(
                    self._ts.set_quality_blocked,
                    self._task_id, stage_name, issues_dicts,
                )
                _safe_task_call(
                    self._audit.log_quality_gate,
                    self._task_id, stage_name, "blocked", issues_dicts,
                )
                # Collect warning messages from quality gate
                warning_msgs = [i.message for i in quality_gate_result.issues]
                if rendered_files:
                    # Files exist despite quality block — treat as success with warnings
                    self._quality_warnings = warning_msgs
                    self.log.emit(f"质量门禁预警（有文件）: {'; '.join(warning_msgs)}")
                    self.finished.emit(True, output_dir)
                    self.finished_with_files.emit(True, output_dir, rendered_files)
                else:
                    # No files — true failure
                    self.log.emit(f"质量门禁拦截: {warning_msgs[0] if warning_msgs else '未知'}")
                    self.finished.emit(False, output_dir)
                    self.finished_with_files.emit(False, output_dir, [])
                return

            if ctx.errors:
                # Determine if these are fatal errors or quality warnings
                has_files = len(rendered_files) > 0
                if has_files:
                    # Quality gate warnings — files were generated, just log warnings
                    self._quality_warnings = list(ctx.errors)
                    for err in ctx.errors:
                        self.log.emit(f"预警: {err}")
                    rating, file_count, fact_summary = self._extract_result_data(ctx, output_dir)
                    _safe_task_call(
                        self._ts.complete_task,
                        self._task_id,
                        rating=rating,
                        file_count=len(rendered_files),
                        fact_summary=fact_summary,
                        rendered_files=rendered_files,
                    )
                    _safe_task_call(self._ts.update_task_status, self._task_id, "已完成")
                    _safe_task_call(self._ts.set_resumable, self._task_id, False)
                    _safe_task_call(
                        self._audit.log_task_completed, self._task_id, rating, len(rendered_files)
                    )
                    self.finished.emit(True, output_dir)
                    self.finished_with_files.emit(True, output_dir, rendered_files)
                else:
                    # True failure — no files produced
                    self._quality_warnings = list(ctx.errors)
                    for err in ctx.errors:
                        self.log.emit(f"错误: {err}")
                    error_summary = ctx.errors[-1] if ctx.errors else "未知错误"
                    _safe_task_call(self._ts.set_task_error, self._task_id, error_summary)
                    _safe_task_call(self._audit.log_task_failed, self._task_id, error_summary)
                    self.finished.emit(False, output_dir)
                    self.finished_with_files.emit(False, output_dir, rendered_files)
            elif render_failed:
                # Analysis succeeded but some renders failed — partial completion
                rating, file_count, fact_summary = self._extract_result_data(ctx, output_dir)
                _safe_task_call(
                    self._ts.complete_task,
                    self._task_id,
                    rating=rating,
                    file_count=len(rendered_files),
                    fact_summary=fact_summary,
                    rendered_files=rendered_files,
                )
                _safe_task_call(
                    self._ts.update_task_status, self._task_id, "部分完成"
                )
                _safe_task_call(self._ts.set_resumable, self._task_id, False)
                _safe_task_call(
                    self._audit.log_task_completed, self._task_id, rating, len(rendered_files)
                )
                # Dump full failure details to crash_debug.log
                try:
                    with open("crash_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"\n{'='*60}\n")
                        f.write("=== PARTIAL RENDER FAILURE (render_failed branch) ===\n")
                        f.write(f"Time: {datetime.now().isoformat()}\n")
                        f.write(f"Task ID: {self._task_id}\n")
                        f.write(f"rendered_files ({len(rendered_files)}): {rendered_files}\n")
                        f.write(f"render_failed ({len(render_failed)}): {render_failed}\n")
                        f.write(f"ctx.errors: {getattr(ctx, 'errors', [])}\n")
                        # Dump manifest entries for failed files
                        try:
                            entries = self._ts.manifest_list_entries(self._task_id)
                            failed_entries = [e for e in entries if e.get("status") == "failed"]
                            f.write(f"\nManifest failed entries ({len(failed_entries)}):\n")
                            for e in failed_entries:
                                f.write(f"  file: {e.get('file_name')}\n")
                                f.write(f"    status: {e.get('status')}\n")
                                f.write(f"    error_code: {e.get('error_code')}\n")
                                f.write(f"    error_msg: {e.get('error_msg')}\n")
                        except Exception as me:
                            f.write(f"  (manifest dump failed: {me})\n")
                        f.write(f"\n{'='*60}\n\n")
                except Exception:
                    pass
                self._last_error = f"以下文件渲染失败:\n" + "\n".join(f"  - {f}" for f in render_failed)
                self.log.emit(f"分析完成，但 {len(render_failed)} 个文件渲染失败")
                self.finished.emit(False, output_dir)
                self.finished_with_files.emit(False, output_dir, rendered_files)
            else:
                self.log.emit("分析完成")
                # Log success state
                try:
                    with open("crash_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"\n{'='*60}\n")
                        f.write("=== SUCCESS BRANCH ===\n")
                        f.write(f"Time: {datetime.now().isoformat()}\n")
                        f.write(f"Task ID: {self._task_id}\n")
                        f.write(f"rendered_files ({len(rendered_files)}): {rendered_files}\n")
                        f.write(f"render_failed ({len(render_failed)}): {render_failed}\n")
                        f.write(f"ctx.errors: {getattr(ctx, 'errors', [])}\n")
                        f.write(f"\n{'='*60}\n\n")
                except Exception:
                    pass
                rating, file_count, fact_summary = self._extract_result_data(ctx, output_dir)
                _safe_task_call(
                    self._ts.complete_task,
                    self._task_id,
                    rating=rating,
                    file_count=file_count,
                    fact_summary=fact_summary,
                    rendered_files=rendered_files,
                )
                _safe_task_call(self._ts.set_resumable, self._task_id, False)
                _safe_task_call(
                    self._audit.log_task_completed, self._task_id, rating, file_count
                )
                self.finished.emit(True, output_dir)
                self.finished_with_files.emit(True, output_dir, rendered_files)

        except ImportError as exc:
            _write_crash_log("WORKER ImportError", exc)
            self.log.emit(f"模块导入失败: {exc}")
            self._last_error = f"模块导入失败: {exc}"
            self.stage_failed.emit("读取材料", str(exc))
            _safe_task_call(self._ts.set_task_error, self._task_id, str(exc))
            _safe_task_call(self._audit.log_task_failed, self._task_id, str(exc))
            self.finished.emit(False, output_dir)
            self.finished_with_files.emit(False, output_dir, [])
        except AIProviderError as exc:
            _write_crash_log("WORKER AIProviderError", exc)
            error_msg = f"AI 服务调用失败: {exc}"
            self.log.emit(error_msg)
            self._last_error = error_msg
            self.stage_failed.emit("AI 服务", str(exc))
            _safe_task_call(self._ts.set_task_error, self._task_id, error_msg)
            _safe_task_call(self._audit.log_task_failed, self._task_id, error_msg)
            self.error_occurred.emit("AI 服务调用失败", str(exc))
            self.finished.emit(False, output_dir)
            self.finished_with_files.emit(False, output_dir, [])
        except Exception as exc:
            _write_crash_log("WORKER Exception", exc)
            error_msg = f"分析异常: {type(exc).__name__}: {exc}"
            self.log.emit(error_msg)
            self._last_error = error_msg
            self.stage_failed.emit("读取材料", str(exc))
            _safe_task_call(self._ts.set_task_error, self._task_id, error_msg)
            _safe_task_call(self._audit.log_task_failed, self._task_id, error_msg)
            self.error_occurred.emit("分析过程中出现异常", str(exc))
            self.finished.emit(False, output_dir)
            self.finished_with_files.emit(False, output_dir, [])

    def _extract_result_data(self, ctx, output_dir: str) -> tuple[str, int, str]:
        """Extract rating, file_count, fact_summary from pipeline context."""
        rating = ""
        file_count = 0
        fact_summary = ""

        try:
            if ctx.strategy_card and ctx.strategy_card.sabcd_rating:
                rating = ctx.strategy_card.sabcd_rating
            elif ctx.distilled_card and ctx.distilled_card.strategy_card:
                rating = ctx.distilled_card.strategy_card.sabcd_rating or ""
        except Exception:
            pass

        try:
            customer_dir = Path(output_dir) / "customer"
            if customer_dir.exists():
                file_count = sum(1 for f in customer_dir.iterdir() if f.is_file())
        except Exception:
            pass

        try:
            if ctx.fact_card and ctx.fact_card.key_facts:
                fact_summary = "; ".join(ctx.fact_card.key_facts[:3])
        except Exception:
            pass

        return rating, file_count, fact_summary
