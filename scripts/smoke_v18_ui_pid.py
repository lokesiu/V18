"""Smoke test: Verify V18 UI PID implementation."""
import sys
from pathlib import Path


def test_ui_files_exist():
    """Check required UI files exist."""
    assert Path("app/main_window.py").exists(), "main_window.py missing"
    assert Path("app/worker.py").exists(), "worker.py missing"
    assert Path("app/widgets").is_dir(), "widgets/ directory missing"


def test_widget_files_exist():
    """Check widget files exist."""
    widgets = ["upload_card.py", "option_card.py", "progress_timeline.py",
               "result_card.py", "status_badge.py"]
    for w in widgets:
        assert Path(f"app/widgets/{w}").exists(), f"{w} missing"


def test_uses_fluent_widgets():
    """Check UI uses PySide6-Fluent-Widgets."""
    content = Path("app/main_window.py").read_text(encoding="utf-8")
    assert "qfluentwidgets" in content, "UI must use qfluentwidgets"
    assert "FluentWindow" in content, "Must use FluentWindow"


def test_window_title():
    """Check window title is correct."""
    content = Path("app/main_window.py").read_text(encoding="utf-8")
    assert "明证台 V18 Beta" in content, "Window title must be '明证台 V18 Beta'"


def test_no_technical_terms():
    """Check UI doesn't show technical terms to users."""
    content = Path("app/main_window.py").read_text(encoding="utf-8")
    # These should not appear in user-facing strings
    forbidden_in_strings = ["FactCard", "StrategyCard", "DistilledCard"]
    for term in forbidden_in_strings:
        assert f'"{term}"' not in content, f"UI contains forbidden term in strings: {term}"


def test_has_progress_component():
    """Check UI has progress timeline component."""
    assert Path("app/widgets/progress_timeline.py").exists(), "progress_timeline.py missing"


def test_has_upload_component():
    """Check UI has upload card."""
    assert Path("app/widgets/upload_card.py").exists(), "upload_card.py missing"


def test_has_result_component():
    """Check UI has result card."""
    assert Path("app/widgets/result_card.py").exists(), "result_card.py missing"


def test_upload_card_no_long_filename():
    """Check upload card truncates filenames."""
    content = Path("app/widgets/upload_card.py").read_text(encoding="utf-8")
    assert "其余" in content or "已收起" in content, "Must truncate long file lists"


def test_worker_has_stage_events():
    """Check worker emits stage events."""
    content = Path("app/worker.py").read_text(encoding="utf-8")
    assert "stage_started" in content, "Worker must emit stage_started"
    assert "stage_done" in content, "Worker must emit stage_done"


if __name__ == "__main__":
    tests = [
        test_ui_files_exist,
        test_widget_files_exist,
        test_uses_fluent_widgets,
        test_window_title,
        test_no_technical_terms,
        test_has_progress_component,
        test_has_upload_component,
        test_has_result_component,
        test_upload_card_no_long_filename,
        test_worker_has_stage_events,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
        except Exception as e:
            print(f"  [ERROR] {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
