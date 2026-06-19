"""core/task_store.py — Minimal SQLite task persistence.

Provides CRUD for analysis tasks. No external dependencies beyond
the Python standard library (sqlite3 is built-in).
"""
from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# ── DB location ────────────────────────────────────────────────────────
_DB_DIR = Path.home() / ".明证台"
_DB_PATH = _DB_DIR / "tasks.db"


# ── Row dataclass ──────────────────────────────────────────────────────
@dataclass
class TaskRecord:
    task_id: str = ""
    identity: str = ""
    goal: str = ""
    status: str = "待处理"        # 待处理 / 进行中 / 已完成 / 失败 / 已取消
    current_step: int = 0         # 0-based step index (0..7)
    created_at: str = ""
    updated_at: str = ""
    output_dir: str = ""
    error_message: str = ""
    retry_count: int = 0
    rating: str = ""
    file_count: int = 0
    fact_summary: str = ""
    file_list_json: str = "[]"    # JSON-encoded list of input file paths
    rendered_files_json: str = "[]"  # JSON-encoded list of rendered file paths
    # ── ACL reserved fields (E) ──
    owner_id: str = "local_user"   # single-user desktop default
    org_id: str = ""               # reserved for future multi-tenant
    visibility: str = "private"    # private / team / public
    resumable: int = 0             # 0=not resumable, 1=resumable
    # ── Quality gate fields (B) ──
    quality_blocked: int = 0       # 0=normal, 1=blocked by quality gate
    quality_issues_json: str = "[]"  # JSON: list of issue dicts
    quality_gate_stage: str = ""   # which gate blocked: step2 / step3

    def to_dict(self) -> dict:
        import json
        d = {
            "task_id": self.task_id,
            "identity": self.identity,
            "goal": self.goal,
            "status": self.status,
            "current_step": self.current_step,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "output_dir": self.output_dir,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "rating": self.rating,
            "file_count": self.file_count,
            "fact_summary": self.fact_summary,
            "file_list": json.loads(self.file_list_json) if self.file_list_json else [],
            "rendered_files": json.loads(self.rendered_files_json) if self.rendered_files_json else [],
            "owner_id": self.owner_id,
            "org_id": self.org_id,
            "visibility": self.visibility,
            "quality_blocked": self.quality_blocked,
            "quality_issues": json.loads(self.quality_issues_json) if self.quality_issues_json else [],
            "quality_gate_stage": self.quality_gate_stage,
        }
        return d


# ── SQL ────────────────────────────────────────────────────────────────
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id          TEXT PRIMARY KEY,
    identity         TEXT NOT NULL DEFAULT '',
    goal             TEXT NOT NULL DEFAULT '',
    status           TEXT NOT NULL DEFAULT '待处理',
    current_step     INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL DEFAULT '',
    updated_at       TEXT NOT NULL DEFAULT '',
    output_dir       TEXT NOT NULL DEFAULT '',
    error_message    TEXT NOT NULL DEFAULT '',
    retry_count      INTEGER NOT NULL DEFAULT 0,
    rating           TEXT NOT NULL DEFAULT '',
    file_count       INTEGER NOT NULL DEFAULT 0,
    fact_summary     TEXT NOT NULL DEFAULT '',
    file_list_json   TEXT NOT NULL DEFAULT '[]',
    rendered_files_json TEXT NOT NULL DEFAULT '[]',
    owner_id         TEXT NOT NULL DEFAULT 'local_user',
    org_id           TEXT NOT NULL DEFAULT '',
    visibility       TEXT NOT NULL DEFAULT 'private',
    resumable        INTEGER NOT NULL DEFAULT 0,
    quality_blocked  INTEGER NOT NULL DEFAULT 0,
    quality_issues_json TEXT NOT NULL DEFAULT '[]',
    quality_gate_stage TEXT NOT NULL DEFAULT ''
);
"""

_CREATE_CHECKPOINTS = """
CREATE TABLE IF NOT EXISTS checkpoints (
    task_id      TEXT NOT NULL,
    step_index   INTEGER NOT NULL,
    step_name    TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'done',
    ctx_snapshot TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (task_id, step_index)
);
"""

_CREATE_RENDER_MANIFEST = """
CREATE TABLE IF NOT EXISTS render_manifest (
    task_id      TEXT NOT NULL,
    file_name    TEXT NOT NULL,
    file_type    TEXT NOT NULL DEFAULT '',
    source_file  TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'pending',
    error_code   TEXT NOT NULL DEFAULT '',
    error_msg    TEXT NOT NULL DEFAULT '',
    file_size    INTEGER NOT NULL DEFAULT 0,
    attempt      INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL DEFAULT '',
    updated_at   TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (task_id, file_name)
);
"""

# Columns that may not exist in older databases — additive migration
_ACL_MIGRATION_COLUMNS = [
    ("owner_id", "TEXT NOT NULL DEFAULT 'local_user'"),
    ("org_id", "TEXT NOT NULL DEFAULT ''"),
    ("visibility", "TEXT NOT NULL DEFAULT 'private'"),
    ("resumable", "INTEGER NOT NULL DEFAULT 0"),
    ("quality_blocked", "INTEGER NOT NULL DEFAULT 0"),
    ("quality_issues_json", "TEXT NOT NULL DEFAULT '[]'"),
    ("quality_gate_stage", "TEXT NOT NULL DEFAULT ''"),
]


# ── Connection helper ──────────────────────────────────────────────────
def _ensure_db():
    _DB_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def _conn():
    _ensure_db()
    c = sqlite3.connect(str(_DB_PATH), timeout=10)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _row_to_record(row: sqlite3.Row) -> TaskRecord:
    return TaskRecord(**dict(row))


# ── Public API ─────────────────────────────────────────────────────────
def _migrate_acl_columns(cursor):
    """Add ACL columns if they don't exist (idempotent ALTER TABLE)."""
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(tasks)").fetchall()}
    for col_name, col_def in _ACL_MIGRATION_COLUMNS:
        if col_name not in existing:
            try:
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_def}")
            except sqlite3.OperationalError:
                pass  # column already exists (race condition safety)


def init_db():
    """Create the tasks table if it doesn't exist, then migrate."""
    with _conn() as c:
        c.execute(_CREATE_TABLE)
        c.execute(_CREATE_CHECKPOINTS)
        c.execute(_CREATE_RENDER_MANIFEST)
        _migrate_acl_columns(c)


def create_task(
    identity: str,
    goal: str,
    file_list: list[str] | None = None,
    output_dir: str = "",
) -> TaskRecord:
    """Insert a new task and return its record."""
    import json
    init_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    task_id = datetime.now().strftime("case_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
    rec = TaskRecord(
        task_id=task_id,
        identity=identity,
        goal=goal,
        status="待处理",
        current_step=0,
        created_at=now,
        updated_at=now,
        output_dir=output_dir,
        file_list_json=json.dumps(file_list or [], ensure_ascii=False),
    )
    with _conn() as c:
        c.execute(
            """INSERT INTO tasks
               (task_id, identity, goal, status, current_step,
                created_at, updated_at, output_dir, file_list_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rec.task_id, rec.identity, rec.goal, rec.status,
             rec.current_step, rec.created_at, rec.updated_at,
             rec.output_dir, rec.file_list_json),
        )
    return rec


def update_task_status(task_id: str, status: str):
    """Update task status and updated_at."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "UPDATE tasks SET status=?, updated_at=? WHERE task_id=?",
            (status, now, task_id),
        )


def update_task_step(task_id: str, step: int, status: str = "进行中"):
    """Update current_step and status."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "UPDATE tasks SET current_step=?, status=?, updated_at=? WHERE task_id=?",
            (step, status, now, task_id),
        )


def set_task_output(task_id: str, output_dir: str):
    """Set the output directory for a task."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "UPDATE tasks SET output_dir=?, updated_at=? WHERE task_id=?",
            (output_dir, now, task_id),
        )


def set_task_error(task_id: str, error_message: str):
    """Mark task as failed with error message."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "UPDATE tasks SET status='失败', error_message=?, updated_at=? WHERE task_id=?",
            (error_message, now, task_id),
        )


def complete_task(task_id: str, rating: str = "", file_count: int = 0,
                   fact_summary: str = "", rendered_files: list[str] | None = None):
    """Mark task as completed with results."""
    import json
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rendered_json = json.dumps(rendered_files or [], ensure_ascii=False)
    with _conn() as c:
        c.execute(
            """UPDATE tasks SET status='已完成', rating=?, file_count=?,
               fact_summary=?, rendered_files_json=?, current_step=8, updated_at=?
               WHERE task_id=?""",
            (rating, file_count, fact_summary, rendered_json, now, task_id),
        )


def cancel_task(task_id: str):
    """Mark task as cancelled."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "UPDATE tasks SET status='已取消', updated_at=? WHERE task_id=?",
            (now, task_id),
        )


def increment_retry(task_id: str):
    """Increment retry_count."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "UPDATE tasks SET retry_count=retry_count+1, updated_at=? WHERE task_id=?",
            (now, task_id),
        )


def set_quality_blocked(task_id: str, stage: str, issues: list[dict]):
    """Mark task as quality-blocked with issues."""
    import json
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    issues_json = json.dumps(issues, ensure_ascii=False)
    with _conn() as c:
        c.execute(
            """UPDATE tasks SET quality_blocked=1, quality_gate_stage=?,
               quality_issues_json=?, status='质量拦截', updated_at=?
               WHERE task_id=?""",
            (stage, issues_json, now, task_id),
        )


def get_task(task_id: str) -> TaskRecord | None:
    """Get a single task by id."""
    init_db()
    with _conn() as c:
        row = c.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
    return _row_to_record(row) if row else None


def list_recent(limit: int = 5) -> list[TaskRecord]:
    """Get most recent tasks ordered by created_at descending."""
    init_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_record(r) for r in rows]


def list_all(status: str | None = None, query: str | None = None) -> list[TaskRecord]:
    """List all tasks, optionally filtered by status and/or text query."""
    init_db()
    sql = "SELECT * FROM tasks WHERE 1=1"
    params: list = []
    if status and status != "全部":
        sql += " AND status=?"
        params.append(status)
    if query:
        sql += " AND (task_id LIKE ? OR identity LIKE ? OR goal LIKE ? OR fact_summary LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like, like, like])
    sql += " ORDER BY created_at DESC"
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    return [_row_to_record(r) for r in rows]


def count_by_status() -> dict[str, int]:
    """Return counts grouped by status."""
    init_db()
    with _conn() as c:
        rows = c.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status").fetchall()
    return {r["status"]: r["cnt"] for r in rows}


def set_resumable(task_id: str, resumable: bool = True):
    """Set the resumable flag on a task."""
    with _conn() as c:
        c.execute(
            "UPDATE tasks SET resumable=?, updated_at=? WHERE task_id=?",
            (1 if resumable else 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), task_id),
        )


# ── Checkpoint CRUD ───────────────────────────────────────────────────
def save_checkpoint(
    task_id: str,
    step_index: int,
    step_name: str,
    ctx_snapshot: str,
    status: str = "done",
):
    """Save or overwrite a checkpoint for (task_id, step_index).  Idempotent."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            """INSERT OR REPLACE INTO checkpoints
               (task_id, step_index, step_name, status, ctx_snapshot, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (task_id, step_index, step_name, status, ctx_snapshot, now),
        )


def get_checkpoint(task_id: str, step_index: int) -> dict | None:
    """Get checkpoint for a specific step."""
    init_db()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM checkpoints WHERE task_id=? AND step_index=?",
            (task_id, step_index),
        ).fetchone()
    return dict(row) if row else None


def get_latest_checkpoint(task_id: str) -> dict | None:
    """Get the checkpoint with the highest step_index for a task."""
    init_db()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM checkpoints WHERE task_id=? ORDER BY step_index DESC LIMIT 1",
            (task_id,),
        ).fetchone()
    return dict(row) if row else None


def list_checkpoints(task_id: str) -> list[dict]:
    """List all checkpoints for a task, ordered by step_index."""
    init_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM checkpoints WHERE task_id=? ORDER BY step_index",
            (task_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def clear_checkpoints(task_id: str):
    """Delete all checkpoints for a task."""
    with _conn() as c:
        c.execute("DELETE FROM checkpoints WHERE task_id=?", (task_id,))


# ── Render Manifest CRUD ─────────────────────────────────────────────
def manifest_init_entry(task_id: str, file_name: str, file_type: str,
                         source_file: str = ""):
    """Insert or reset a manifest entry to pending."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            """INSERT OR REPLACE INTO render_manifest
               (task_id, file_name, file_type, source_file, status,
                error_code, error_msg, file_size, attempt, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'pending', '', '', 0, 1, ?, ?)""",
            (task_id, file_name, file_type, source_file, now, now),
        )


def manifest_mark_success(task_id: str, file_name: str, file_size: int = 0):
    """Mark a manifest entry as successfully rendered."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            """UPDATE render_manifest SET status='success', file_size=?,
               error_code='', error_msg='', updated_at=?
               WHERE task_id=? AND file_name=?""",
            (file_size, now, task_id, file_name),
        )


def manifest_mark_failed(task_id: str, file_name: str,
                          error_code: str = "", error_msg: str = ""):
    """Mark a manifest entry as failed."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            """UPDATE render_manifest SET status='failed',
               error_code=?, error_msg=?, attempt=attempt+1, updated_at=?
               WHERE task_id=? AND file_name=?""",
            (error_code, error_msg, now, task_id, file_name),
        )


def manifest_mark_skipped(task_id: str, file_name: str, reason: str = ""):
    """Mark a manifest entry as skipped."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            """UPDATE render_manifest SET status='skipped',
               error_msg=?, updated_at=?
               WHERE task_id=? AND file_name=?""",
            (reason, now, task_id, file_name),
        )


def manifest_get_entry(task_id: str, file_name: str) -> dict | None:
    """Get a single manifest entry."""
    init_db()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM render_manifest WHERE task_id=? AND file_name=?",
            (task_id, file_name),
        ).fetchone()
    return dict(row) if row else None


def manifest_list_entries(task_id: str) -> list[dict]:
    """List all manifest entries for a task."""
    init_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM render_manifest WHERE task_id=? ORDER BY file_name",
            (task_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def manifest_list_failed(task_id: str) -> list[dict]:
    """List failed manifest entries for a task."""
    init_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM render_manifest WHERE task_id=? AND status='failed' ORDER BY file_name",
            (task_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def manifest_summary(task_id: str) -> dict:
    """Return counts by status for a task's manifest."""
    init_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT status, COUNT(*) as cnt FROM render_manifest WHERE task_id=? GROUP BY status",
            (task_id,),
        ).fetchall()
    return {r["status"]: r["cnt"] for r in rows}


# ── Singleton accessor ─────────────────────────────────────────────────
_store = None

class TaskStore:
    """Thin wrapper exposing the module-level functions as methods."""

    init_db = staticmethod(init_db)
    create_task = staticmethod(create_task)
    update_task_status = staticmethod(update_task_status)
    update_task_step = staticmethod(update_task_step)
    set_task_output = staticmethod(set_task_output)
    set_task_error = staticmethod(set_task_error)
    complete_task = staticmethod(complete_task)
    cancel_task = staticmethod(cancel_task)
    increment_retry = staticmethod(increment_retry)
    get_task = staticmethod(get_task)
    list_recent = staticmethod(list_recent)
    list_all = staticmethod(list_all)
    count_by_status = staticmethod(count_by_status)
    set_resumable = staticmethod(set_resumable)
    set_quality_blocked = staticmethod(set_quality_blocked)
    save_checkpoint = staticmethod(save_checkpoint)
    get_checkpoint = staticmethod(get_checkpoint)
    get_latest_checkpoint = staticmethod(get_latest_checkpoint)
    list_checkpoints = staticmethod(list_checkpoints)
    clear_checkpoints = staticmethod(clear_checkpoints)
    manifest_init_entry = staticmethod(manifest_init_entry)
    manifest_mark_success = staticmethod(manifest_mark_success)
    manifest_mark_failed = staticmethod(manifest_mark_failed)
    manifest_mark_skipped = staticmethod(manifest_mark_skipped)
    manifest_get_entry = staticmethod(manifest_get_entry)
    manifest_list_entries = staticmethod(manifest_list_entries)
    manifest_list_failed = staticmethod(manifest_list_failed)
    manifest_summary = staticmethod(manifest_summary)


def get_task_store() -> TaskStore:
    global _store
    if _store is None:
        _store = TaskStore()
        _store.init_db()
    return _store
