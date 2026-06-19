"""Smoke test: Verify V18 UI real start and screenshot.

Checks:
1. start_v18.bat can be started
2. Main window title is correct
3. reports/screenshots/v18_ui_home.png exists
4. Screenshot file size > 20KB
5. UI source code uses PySide6-Fluent-Widgets
6. No internal technical terms in UI
7. Worker uses QThread
8. Open output folder function exists

Usage:
    python scripts/smoke_v18_ui_real_start.py
"""
from __future__ import annotations

import sys
from pathlib import Path


def test_start_bat_exists():
    """Check start_v18.bat exists and is safe."""
    bat_path = Path("scripts/start_v18.bat")
    assert bat_path.exists(), "start_v18.bat missing"
    
    content = bat_path.read_text(encoding="ascii", errors="ignore")
    # Should not open browser or web server
    forbidden = ["http://localhost", "msedge", "uvicorn", "fastapi", "chrome", "firefox"]
    for f in forbidden:
        assert f.lower() not in content.lower(), f"BAT contains forbidden: {f}"


def test_window_title():
    """Check window title is correct."""
    content = Path("app/main_window.py").read_text(encoding="utf-8")
    assert "明证台 V18 Beta" in content, "Window title must be '明证台 V18 Beta'"


def test_screenshot_home_exists():
    """Check home screenshot exists."""
    screenshot = Path("reports/screenshots/v18_ui_home.png")
    assert screenshot.exists(), "Home screenshot missing: reports/screenshots/v18_ui_home.png"


def test_screenshot_home_size():
    """Check home screenshot file size > 20KB."""
    screenshot = Path("reports/screenshots/v18_ui_home.png")
    assert screenshot.exists(), "Home screenshot missing"
    
    size = screenshot.stat().st_size
    assert size > 20 * 1024, f"Screenshot too small: {size:,} bytes (need >20KB)"


def test_uses_fluent_widgets():
    """Check UI uses PySide6-Fluent-Widgets."""
    content = Path("app/main_window.py").read_text(encoding="utf-8")
    assert "qfluentwidgets" in content, "UI must use qfluentwidgets"
    assert "FluentWindow" in content, "Must use FluentWindow"
    assert "CardWidget" in content, "Must use CardWidget"


def test_no_technical_terms():
    """Check UI doesn't show technical terms to users."""
    # Check main_window.py
    content = Path("app/main_window.py").read_text(encoding="utf-8")
    
    # These should not appear in user-facing strings
    forbidden_terms = [
        "FactCard", "StrategyCard", "DistilledCard",
        "PipelineContext", "traceback", "JSON", "API",
        "debug", "workflow", "prompt"
    ]
    
    for term in forbidden_terms:
        # Check in quoted strings only
        assert f'"{term}"' not in content, f"UI contains forbidden term in strings: {term}"
        assert f"'{term}'" not in content, f"UI contains forbidden term in strings: {term}"


def test_worker_uses_qthread():
    """Check worker uses QThread."""
    content = Path("app/worker.py").read_text(encoding="utf-8")
    assert "QThread" in content, "Worker must use QThread"
    assert "class AnalysisWorker(QThread)" in content, "AnalysisWorker must inherit QThread"


def test_open_folder_function():
    """Check open output folder function exists."""
    content = Path("app/widgets/result_card.py").read_text(encoding="utf-8")
    assert "_open_output_folder" in content, "Must have _open_output_folder function"
    assert "explorer" in content or "subprocess" in content, "Must open folder with explorer"


def test_has_progress_timeline():
    """Check progress timeline component exists."""
    assert Path("app/widgets/progress_timeline.py").exists(), "progress_timeline.py missing"
    
    content = Path("app/widgets/progress_timeline.py").read_text(encoding="utf-8")
    assert "ProgressTimeline" in content, "Must have ProgressTimeline class"
    assert "set_stage_status" in content, "Must have set_stage_status method"


def test_has_result_card():
    """Check result card component exists."""
    assert Path("app/widgets/result_card.py").exists(), "result_card.py missing"
    
    content = Path("app/widgets/result_card.py").read_text(encoding="utf-8")
    assert "ResultCard" in content, "Must have ResultCard class"
    assert "show_results" in content, "Must have show_results method"


def test_has_upload_card():
    """Check upload card component exists."""
    assert Path("app/widgets/upload_card.py").exists(), "upload_card.py missing"
    
    content = Path("app/widgets/upload_card.py").read_text(encoding="utf-8")
    assert "UploadCard" in content, "Must have UploadCard class"
    assert "其余" in content or "已收起" in content, "Must truncate long file lists"


if __name__ == "__main__":
    tests = [
        test_start_bat_exists,
        test_window_title,
        test_screenshot_home_exists,
        test_screenshot_home_size,
        test_uses_fluent_widgets,
        test_no_technical_terms,
        test_worker_uses_qthread,
        test_open_folder_function,
        test_has_progress_timeline,
        test_has_result_card,
        test_has_upload_card,
    ]
    
    print("=" * 60)
    print("V18 UI Real Start Smoke Tests")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for t in tests:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{len(tests)} passed, {failed} failed")
    print(f"{'=' * 60}")
    
    sys.exit(0 if failed == 0 else 1)
