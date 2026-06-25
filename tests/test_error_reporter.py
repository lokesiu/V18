"""tests/test_error_reporter.py — verify core/error_reporter.py works.

Tests:
  - report_error() writes a JSON record to the log file
  - Sensitive data (phone, ID, email) is scrubbed
  - install_crash_handler() captures uncaught exceptions
  - format_user_friendly_error() returns a UI-safe string
  - get_log_dir() returns an existing path
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Path setup: add project root so 'core' is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.error_reporter import (  # noqa: E402
    _scrub_sensitive,
    format_user_friendly_error,
    get_crash_logger,
    get_log_dir,
    install_crash_handler,
    report_error,
)


@pytest.fixture
def tmp_log_dir(tmp_path: Path):
    """Redirect V18_LOG_DIR to a temp directory for the test."""
    log_dir = tmp_path / "crash_logs"
    log_dir.mkdir()
    with patch.dict(os.environ, {"V18_LOG_DIR": str(log_dir)}):
        # Reset the configuration flag so the logger picks up the new path
        import core.error_reporter as er
        existing = er.get_crash_logger()
        existing._v18_crash_configured = False  # type: ignore[attr-defined]
        # Also drop all handlers so the new path takes effect
        for h in list(existing.handlers):
            existing.removeHandler(h)
        yield log_dir


class TestScrubSensitive:
    def test_scrubs_chinese_phone(self) -> None:
        assert _scrub_sensitive("联系 13800138000 找我") == "联系 [PHONE] 找我"

    def test_scrubs_id_card(self) -> None:
        assert _scrub_sensitive("身份证 110101199003078888") == "身份证 [ID_CARD]"

    def test_scrubs_email(self) -> None:
        assert _scrub_sensitive("邮箱 foo@bar.com") == "邮箱 [EMAIL]"

    def test_scrubs_api_key(self) -> None:
        assert _scrub_sensitive("api_key=abcdefghijklmnop") == "api_key=[REDACTED]"

    def test_passes_normal_text(self) -> None:
        text = "normal log message with no secrets"
        assert _scrub_sensitive(text) == text


class TestReportError:
    def test_writes_json_log(self, tmp_log_dir: Path) -> None:
        report_error("test_event", exc_info=False, foo="bar")
        # Read back
        log_file = tmp_log_dir / "v18.log"
        assert log_file.exists()
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        # At least one record
        assert any("test_event" in line for line in lines)
        # The last one is ours — parse it
        last = json.loads(lines[-1])
        assert last["event"] == "test_event"
        assert last["foo"] == "bar"
        assert last["level"] == "ERROR"

    def test_captures_exception(self, tmp_log_dir: Path) -> None:
        try:
            raise ValueError("test boom")
        except ValueError:
            report_error("exception_caught")
        log_file = tmp_log_dir / "v18.log"
        content = log_file.read_text(encoding="utf-8")
        assert "ValueError" in content
        assert "test boom" in content

    def test_scrubs_sensitive_in_logs(self, tmp_log_dir: Path) -> None:
        report_error("user_login", exc_info=False, phone="13800138000", idcard="110101199003078888")
        log_file = tmp_log_dir / "v18.log"
        content = log_file.read_text(encoding="utf-8")
        assert "13800138000" not in content
        assert "110101199003078888" not in content
        assert "[PHONE]" in content
        assert "[ID_CARD]" in content


class TestInstallCrashHandler:
    def test_install_idempotent(self) -> None:
        install_crash_handler()
        first = sys.excepthook
        install_crash_handler()
        second = sys.excepthook
        assert first is second

    def test_handler_logs_unhandled_exception(self, tmp_log_dir: Path) -> None:
        install_crash_handler()
        # Simulate an unhandled exception by directly calling excepthook
        try:
            raise RuntimeError("simulated unhandled")
        except RuntimeError as e:
            sys.excepthook(RuntimeError, e, e.__traceback__)
        log_file = tmp_log_dir / "v18.log"
        content = log_file.read_text(encoding="utf-8")
        assert "simulated unhandled" in content
        assert "unhandled_exception" in content


class TestFormatUserFriendlyError:
    def test_includes_exc_name(self) -> None:
        exc = FileNotFoundError("missing file")
        msg = format_user_friendly_error(exc)
        assert "FileNotFoundError" in msg
        assert "missing file" in msg
        assert "日志文件" in msg  # user-facing reference to log file

    def test_truncates_long_message(self) -> None:
        long_msg = "x" * 1000
        exc = ValueError(long_msg)
        msg = format_user_friendly_error(exc)
        assert len(msg) < 500  # Should be truncated
        assert "..." in msg


class TestGetLogDir:
    def test_returns_existing_dir(self) -> None:
        log_dir = get_log_dir()
        assert log_dir.exists()
        assert log_dir.is_dir()
