"""Smoke test: Verify V18 desktop app can start."""
import sys
from pathlib import Path


def test_desktop_files_exist():
    """Check required UI files exist."""
    assert Path("app/main_window.py").exists(), "main_window.py missing"
    assert Path("scripts/start_v18.bat").exists(), "start_v18.bat missing"


def test_bat_file_safe():
    """Check bat file doesn't have forbidden content."""
    bat_content = Path("scripts/start_v18.bat").read_text(encoding="ascii", errors="ignore")
    forbidden = ["http://localhost", "msedge", "uvicorn", "fastapi"]
    for f in forbidden:
        assert f.lower() not in bat_content.lower(), f"BAT contains forbidden: {f}"


def test_ui_has_pyside6():
    """Check UI files use PySide6."""
    content = Path("app/main_window.py").read_text(encoding="utf-8")
    assert "PySide6" in content, "UI must use PySide6"


def test_ui_has_controls():
    """Check UI has required controls."""
    content = Path("app/main_window.py").read_text(encoding="utf-8")
    assert "选择材料" in content or "QFileDialog" in content, "Must have file selection"
    assert "投诉方" in content or "QComboBox" in content, "Must have identity selection"
    assert "开始分析" in content or "QPushButton" in content, "Must have start button"


if __name__ == "__main__":
    tests = [test_desktop_files_exist, test_bat_file_safe, test_ui_has_pyside6, test_ui_has_controls]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} smoke tests passed")
    sys.exit(0 if passed == len(tests) else 1)
