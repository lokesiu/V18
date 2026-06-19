"""core/audit_store.py — Audit event persistence.

Records workflow events (step lifecycle, AI calls, quality blocks,
user actions) to a dedicated ``audit_events`` table in the same
SQLite database used by task_store.

Design principles:
- All writes are fire-and-forget; failures are swallowed so they
  never break the main pipeline.
- Events are append-only; no UPDATE or DELETE in normal operation.
- The table is independent from ``tasks`` — a task can be deleted
  while its audit trail is preserved (or vice versa).
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# ── DB location — shared with task_store ────────────────────────────────
_DB_DIR = Path.home() / ".明证台"
_DB_PATH = _DB_DIR / "tasks.db"


# ── Event dataclass ────────────────────────────────────────────────────
@dataclass
class AuditEvent:
    id: int = 0
    task_id: str = ""
    event_type: str = ""       # task_created, step_started, step_done, step_failed,
                               # ai_call, quality_blocked, quality_resolved,
                               # render_file_done, render_file_failed,
                               # task_completed, task_failed, user_retry, user_cancel
    stage_name: str = ""
    severity: str = "info"     # info / warning / error
    message: str = ""
    detail_json: str = "{}"
    created_at: str = ""

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "stage_name": self.stage_name,
            "severity": self.severity,
            "message": self.message,
            "created_at": self.created_at,
        }
        try:
            d["detail"] = json.loads(self.detail_json) if self.detail_json else {}
        except (json.JSONDecodeError, TypeError):
            d["detail"] = {}
        return d


# ── SQL ────────────────────────────────────────────────────────────────
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS audit_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT NOT NULL DEFAULT '',
    event_type  TEXT NOT NULL,
    stage_name  TEXT NOT NULL DEFAULT '',
    severity    TEXT NOT NULL DEFAULT 'info',
    message     TEXT NOT NULL DEFAULT '',
    detail_json TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT ''
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_events(task_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type);",
    "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_events(created_at);",
]


# ── Connection helper ──────────────────────────────────────────────────
@contextmanager
def _conn():
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH), timeout=10)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _row_to_event(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(**dict(row))


# ── Schema init ────────────────────────────────────────────────────────
def init_audit_db():
    """Create audit_events table and indexes (idempotent)."""
    with _conn() as c:
        c.execute(_CREATE_TABLE)
        for idx_sql in _CREATE_INDEXES:
            c.execute(idx_sql)


# ── Core write ─────────────────────────────────────────────────────────
def log_event(
    task_id: str,
    event_type: str,
    stage_name: str = "",
    severity: str = "info",
    message: str = "",
    detail: dict | None = None,
) -> None:
    """Append one audit event.  Silently no-ops on any error."""
    try:
        init_audit_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        detail_json = json.dumps(detail or {}, ensure_ascii=False)
        with _conn() as c:
            c.execute(
                """INSERT INTO audit_events
                   (task_id, event_type, stage_name, severity, message, detail_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (task_id, event_type, stage_name, severity, message, detail_json, now),
            )
    except Exception:
        pass  # audit must never crash the caller


# ── Convenience writers ────────────────────────────────────────────────
def log_task_created(task_id: str, identity: str, goal: str, file_list: list[str]):
    log_event(
        task_id, "task_created", severity="info",
        message=f"任务创建: {identity} · {goal}",
        detail={"identity": identity, "goal": goal, "file_count": len(file_list)},
    )


def log_task_started(task_id: str):
    log_event(task_id, "task_started", severity="info", message="Pipeline 开始执行")


def log_step_started(task_id: str, step_index: int, step_name: str):
    log_event(
        task_id, "step_started", stage_name=step_name, severity="info",
        message=f"步骤 {step_index + 1}/8 开始: {step_name}",
        detail={"step_index": step_index},
    )


def log_step_done(task_id: str, step_index: int, step_name: str, latency_ms: int = 0):
    log_event(
        task_id, "step_done", stage_name=step_name, severity="info",
        message=f"步骤 {step_index + 1}/8 完成: {step_name}",
        detail={"step_index": step_index, "latency_ms": latency_ms},
    )


def log_step_failed(task_id: str, step_index: int, step_name: str, error: str):
    log_event(
        task_id, "step_failed", stage_name=step_name, severity="error",
        message=f"步骤 {step_index + 1}/8 失败: {step_name}",
        detail={"step_index": step_index, "error": error},
    )


def log_ai_call(
    task_id: str,
    stage_name: str,
    model_name: str,
    latency_ms: int,
    token_usage: dict | None = None,
    prompt_summary: str = "",
    response_summary: str = "",
    error: str | None = None,
):
    """Record an AI provider call."""
    detail = {
        "model_name": model_name,
        "latency_ms": latency_ms,
        "token_usage": token_usage or {},
        "prompt_summary": prompt_summary[:200],
        "response_summary": response_summary[:500],
        "error": error,
    }
    severity = "error" if error else "info"
    msg = f"AI 调用: {model_name} ({latency_ms}ms)"
    if error:
        msg += f" — 失败: {error}"
    log_event(task_id, "ai_call", stage_name=stage_name, severity=severity,
              message=msg, detail=detail)


def log_quality_blocked(task_id: str, step_index: int, issues: list[dict]):
    log_event(
        task_id, "quality_blocked", severity="warning",
        message=f"质量门禁拦截: {len(issues)} 个问题",
        detail={"step_index": step_index, "issues": issues},
    )


def log_quality_resolved(task_id: str, step_index: int):
    log_event(
        task_id, "quality_resolved", severity="info",
        message=f"质量门禁已由用户确认继续",
        detail={"step_index": step_index},
    )


def log_render_file_done(task_id: str, file_name: str, file_type: str,
                          file_size: int, latency_ms: int = 0):
    log_event(
        task_id, "render_file_done", stage_name="生成文档", severity="info",
        message=f"渲染成功: {file_name}",
        detail={"file_name": file_name, "file_type": file_type,
                "file_size": file_size, "latency_ms": latency_ms},
    )


def log_render_file_failed(task_id: str, file_name: str, file_type: str, error: str):
    log_event(
        task_id, "render_file_failed", stage_name="生成文档", severity="error",
        message=f"渲染失败: {file_name}",
        detail={"file_name": file_name, "file_type": file_type, "error": error},
    )


def log_task_completed(task_id: str, rating: str, file_count: int):
    log_event(
        task_id, "task_completed", severity="info",
        message=f"任务完成: rating={rating}, {file_count} 个文件",
        detail={"rating": rating, "file_count": file_count},
    )


def log_task_failed(task_id: str, error_message: str):
    log_event(
        task_id, "task_failed", severity="error",
        message=f"任务失败: {error_message}",
        detail={"error_message": error_message},
    )


def log_user_retry(task_id: str, from_step: int, retry_count: int):
    log_event(
        task_id, "user_retry", severity="info",
        message=f"用户触发重试: 从步骤 {from_step + 1} 开始 (第 {retry_count} 次)",
        detail={"from_step": from_step, "retry_count": retry_count},
    )


def log_user_cancel(task_id: str):
    log_event(task_id, "user_cancel", severity="info", message="用户取消任务")


def log_quality_gate(task_id: str, stage: str, status: str, issues: list[dict]):
    """Record a quality gate result."""
    blocking = [i for i in issues if i.get("severity") == "blocking"]
    warnings = [i for i in issues if i.get("severity") == "warning"]

    if status == "blocked":
        severity = "error"
        msgs = [i.get("message", "") for i in blocking]
        message = f"质量门禁拦截 [{stage}]: {'; '.join(msgs)}"
    elif status == "warning":
        severity = "warning"
        msgs = [i.get("message", "") for i in warnings]
        message = f"质量门禁警告 [{stage}]: {'; '.join(msgs)}"
    else:
        severity = "info"
        message = f"质量门禁通过 [{stage}]"

    log_event(
        task_id, f"quality_{status}", stage_name=stage, severity=severity,
        message=message, detail={"stage": stage, "status": status, "issues": issues},
    )


def log_checkpoint_saved(task_id: str, step_index: int, step_name: str):
    """Record a checkpoint save."""
    log_event(
        task_id, "checkpoint_saved", stage_name=step_name, severity="info",
        message=f"Checkpoint 已保存: 步骤 {step_index + 1} ({step_name})",
        detail={"step_index": step_index, "step_name": step_name},
    )


def log_manifest_skipped(task_id: str, file_name: str, reason: str):
    """Record a manifest file skip (e.g. no data available)."""
    log_event(
        task_id, "manifest_skipped", stage_name="生成文档", severity="info",
        message=f"跳过渲染: {file_name} — {reason}",
        detail={"file_name": file_name, "reason": reason},
    )


# ── Read ───────────────────────────────────────────────────────────────
def get_events_for_task(task_id: str, event_type: str | None = None,
                         severity: str | None = None) -> list[AuditEvent]:
    """Get audit events for a specific task, optionally filtered."""
    init_audit_db()
    sql = "SELECT * FROM audit_events WHERE task_id=?"
    params: list = [task_id]
    if event_type:
        sql += " AND event_type=?"
        params.append(event_type)
    if severity:
        sql += " AND severity=?"
        params.append(severity)
    sql += " ORDER BY created_at, id"
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    return [_row_to_event(r) for r in rows]


def list_recent_events(limit: int = 100) -> list[AuditEvent]:
    """Get most recent audit events across all tasks."""
    init_audit_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM audit_events ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_event(r) for r in rows]


def list_events_filtered(
    task_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list[AuditEvent]:
    """List events with optional filters including text search."""
    init_audit_db()
    sql = "SELECT * FROM audit_events WHERE 1=1"
    params: list = []
    if task_id:
        sql += " AND task_id LIKE ?"
        params.append(f"%{task_id}%")
    if event_type:
        sql += " AND event_type=?"
        params.append(event_type)
    if severity:
        sql += " AND severity=?"
        params.append(severity)
    if search:
        sql += " AND (message LIKE ? OR task_id LIKE ? OR stage_name LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
    params.append(limit)
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    return [_row_to_event(r) for r in rows]


def count_events_by_type() -> dict[str, int]:
    """Return event counts grouped by event_type."""
    init_audit_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT event_type, COUNT(*) as cnt FROM audit_events GROUP BY event_type"
        ).fetchall()
    return {r["event_type"]: r["cnt"] for r in rows}


def list_event_types() -> list[str]:
    """Return distinct event_type values."""
    init_audit_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT DISTINCT event_type FROM audit_events ORDER BY event_type"
        ).fetchall()
    return [r["event_type"] for r in rows]


# ── Singleton ──────────────────────────────────────────────────────────
_store = None


class AuditStore:
    """Thin wrapper exposing module-level functions as methods."""

    init_audit_db = staticmethod(init_audit_db)
    log_event = staticmethod(log_event)
    log_task_created = staticmethod(log_task_created)
    log_task_started = staticmethod(log_task_started)
    log_step_started = staticmethod(log_step_started)
    log_step_done = staticmethod(log_step_done)
    log_step_failed = staticmethod(log_step_failed)
    log_ai_call = staticmethod(log_ai_call)
    log_quality_blocked = staticmethod(log_quality_blocked)
    log_quality_resolved = staticmethod(log_quality_resolved)
    log_render_file_done = staticmethod(log_render_file_done)
    log_render_file_failed = staticmethod(log_render_file_failed)
    log_task_completed = staticmethod(log_task_completed)
    log_task_failed = staticmethod(log_task_failed)
    log_user_retry = staticmethod(log_user_retry)
    log_user_cancel = staticmethod(log_user_cancel)
    log_quality_gate = staticmethod(log_quality_gate)
    log_checkpoint_saved = staticmethod(log_checkpoint_saved)
    log_manifest_skipped = staticmethod(log_manifest_skipped)
    get_events_for_task = staticmethod(get_events_for_task)
    list_recent_events = staticmethod(list_recent_events)
    list_events_filtered = staticmethod(list_events_filtered)
    count_events_by_type = staticmethod(count_events_by_type)
    list_event_types = staticmethod(list_event_types)


def get_audit_store() -> AuditStore:
    global _store
    if _store is None:
        _store = AuditStore()
        _store.init_audit_db()
    return _store
