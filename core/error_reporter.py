"""core/error_reporter.py — V18 crash / error reporter.

Local-first error reporting for V18. Designed for legal industry deployment
where customer case data MUST NOT leave the host machine.

What this module does:
  1. Captures all unhandled exceptions via sys.excepthook
  2. Writes structured crash logs to outputs/crash_logs/ (rotated)
  3. Scrubs obviously-sensitive patterns (phone, ID, email) before writing
  4. Provides a `report_error()` API for caught exceptions
  5. Provides a `format_user_friendly_error()` for UI dialogs

What this module does NOT do:
  - Send anything over the network (no Sentry, no telemetry)
  - Capture customer case data (only stack traces + function names)
  - Auto-email or auto-upload logs (user must opt in)

Usage in production:
    # In core/runner.py main():
    from core.error_reporter import install_crash_handler
    install_crash_handler()

    # Anywhere a caught exception is interesting:
    from core.error_reporter import report_error
    try:
        risky_operation()
    except Exception:
        report_error("pipeline_step3_failed", exc_info=True)

    # When the UI shows a crash dialog:
    from core.error_reporter import format_user_friendly_error
    msg = format_user_friendly_error(exc)
    QMessageBox.critical(self, "出错了", msg)
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Default log directory; can be overridden by V18_LOG_DIR env var
_DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent / "outputs" / "crash_logs"


# ---------------------------------------------------------------------------
# Sensitive-data scrubber
# ---------------------------------------------------------------------------

# Patterns we NEVER want in a crash log, even on-disk
# These are conservative; we err on the side of scrubbing
_SCRUB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # ORDER MATTERS: longer/more-specific patterns MUST come first, otherwise
    # shorter patterns (e.g. 11-digit phone) will eat the start of a 18-digit
    # ID card and leave the rest unscrubbed.
    # Chinese ID card: 18 digits, possibly with X (check FIRST)
    (re.compile(r"\d{17}[\dXx]"), "[ID_CARD]"),
    # Chinese mobile: 11 digits, possibly with separators
    (re.compile(r"1[3-9]\d{9}"), "[PHONE]"),
    # Email
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    # Bearer tokens (anything that looks like a credential)
    (re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[\w-]{16,}"), r"\1=[REDACTED]"),
    # Long hex strings (likely keys)
    (re.compile(r"\b[a-f0-9]{32,}\b"), "[HEX_KEY]"),
)


def _scrub_sensitive(text: str) -> str:
    """Remove obviously-sensitive patterns from a string before logging."""
    for pattern, replacement in _SCRUB_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# Crash log format
# ---------------------------------------------------------------------------


class _JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON for easy post-hoc analysis."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": _scrub_sensitive(record.getMessage()),
        }
        if record.exc_info:
            # Format the exception traceback and scrub it too
            exc_text = "".join(traceback.format_exception(*record.exc_info))
            payload["exc"] = _scrub_sensitive(exc_text)
        if record.stack_info:
            payload["stack"] = _scrub_sensitive(record.stack_info)
        # Include any extra structured fields attached via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in payload:
                continue
            if key in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "asctime", "taskName",
            ):
                continue
            try:
                # Only JSON-serializable extras
                json.dumps(value)
                # Scrub string values for sensitive data
                if isinstance(value, str):
                    payload[key] = _scrub_sensitive(value)
                else:
                    payload[key] = value
            except (TypeError, ValueError):
                payload[key] = str(value)
        return json.dumps(payload, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _resolve_log_dir() -> Path:
    """Resolve the crash log directory, creating it if needed."""
    import os

    raw = os.environ.get("V18_LOG_DIR")
    if raw:
        log_dir = Path(raw)
    else:
        log_dir = _DEFAULT_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_crash_logger(name: str = "v18.crash") -> logging.Logger:
    """Return a logger that writes JSON crash records to outputs/crash_logs/.

    Idempotent: repeated calls return the same configured logger.
    """
    logger = logging.getLogger(name)
    if getattr(logger, "_v18_crash_configured", False):
        return logger
    logger.setLevel(logging.DEBUG)
    log_dir = _resolve_log_dir()
    # Rotate daily, keep 14 days
    handler = logging.handlers.TimedRotatingFileHandler(
        log_dir / "v18.log",
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    # Also keep a stderr handler at WARNING+ for dev visibility
    stderr = logging.StreamHandler(sys.stderr)
    stderr.setLevel(logging.WARNING)
    stderr.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(stderr)
    logger.propagate = False  # don't bubble to root logger (avoids double-logging)
    logger._v18_crash_configured = True  # type: ignore[attr-defined]
    return logger


def report_error(
    event: str,
    *,
    exc_info: bool = True,
    level: int = logging.ERROR,
    **fields: Any,
) -> None:
    """Report a caught exception or notable event.

    Args:
        event: short event name (e.g. "pipeline_step3_failed").
        exc_info: if True, attach current exception via sys.exc_info().
        level: log level (default ERROR).
        **fields: structured fields to attach to the log record.

    Example:
        try:
            risky()
        except Exception:
            report_error("risky_failed", case_id=case.id)
    """
    logger = get_crash_logger()
    extra: dict[str, Any] = {"event": event, **fields}
    logger.log(level, event, exc_info=exc_info, extra=extra)


def install_crash_handler() -> None:
    """Install sys.excepthook + threading.excepthook so unhandled exceptions get logged.

    Safe to call multiple times — guarded by an attribute.
    """
    logger = get_crash_logger()

    if getattr(sys, "_v18_crash_hook_installed", False):
        return

    def _excepthook(exc_type: type, exc_value: BaseException, exc_tb: Any) -> None:
        # Log the exception
        logger.critical(
            "unhandled_exception",
            exc_info=(exc_type, exc_value, exc_tb),
            extra={"event": "unhandled_exception", "exc_type": exc_type.__name__},
        )
        # Call the previous hook (Python's default prints to stderr)
        if hasattr(sys, "__excepthook__"):
            sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    # Also install for threads
    try:
        import threading

        if not getattr(threading, "_v8_thread_hook_installed", False):
            def _thread_excepthook(args: Any) -> None:
                logger.critical(
                    "thread_unhandled_exception",
                    exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
                    extra={"event": "thread_unhandled_exception", "thread": args.thread.name},
                )
            threading.excepthook = _thread_excepthook
            threading._v8_thread_hook_installed = True  # type: ignore[attr-defined]
    except ImportError:
        # Python < 3.8 doesn't have threading.excepthook
        pass

    sys._v18_crash_hook_installed = True  # type: ignore[attr-defined]
    logger.info("crash_handler_installed", extra={"event": "crash_handler_installed"})


def format_user_friendly_error(exc: BaseException) -> str:
    """Format an exception for display in a UI dialog.

    Scrubs stack traces (which may contain customer data) and shows
    a short, friendly message instead. The full detail is in the crash log.

    Example return:
        "操作失败: FileNotFoundError\n\n完整错误已保存到日志文件。"
    """
    exc_name = type(exc).__name__
    # Truncate message to first 200 chars
    msg = str(exc).strip() or "(无错误信息)"
    if len(msg) > 200:
        msg = msg[:200] + "..."
    return f"操作失败: {exc_name}: {msg}\n\n完整错误已保存到日志文件。"


def get_log_dir() -> Path:
    """Return the current crash log directory (for UI display / 'open logs' button)."""
    return _resolve_log_dir()


__all__ = [
    "get_crash_logger",
    "report_error",
    "install_crash_handler",
    "format_user_friendly_error",
    "get_log_dir",
]
