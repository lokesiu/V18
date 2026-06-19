"""Capture V18 UI screenshot for manual verification.

This script:
1. Starts the V18 MainWindow
2. Waits for rendering to complete
3. Captures a screenshot
4. Saves to reports/screenshots/v18_ui_home.png

Usage:
    python scripts/capture_v18_ui_screenshot.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QScreen
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


def capture_screenshot(output_path: str = "reports/screenshots/v18_ui_home.png") -> bool:
    """Start V18 UI and capture screenshot.
    
    Args:
        output_path: Path to save the screenshot
        
    Returns:
        True if screenshot was saved successfully
    """
    app = QApplication(sys.argv)
    
    # Create and show window
    window = MainWindow()
    window.show()
    
    # Wait for window to fully render
    # Process events to ensure UI is fully painted
    for _ in range(10):
        app.processEvents()
        time.sleep(0.1)
    
    # Additional wait for animations to complete
    time.sleep(1.0)
    app.processEvents()
    
    # Capture the window
    screen = app.primaryScreen()
    if screen is None:
        print("ERROR: No screen available")
        return False
    
    # Grab the window
    pixmap = screen.grabWindow(window.winId())
    
    if pixmap.isNull():
        print("ERROR: Failed to capture window")
        return False
    
    # Ensure output directory exists
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    # Save screenshot
    success = pixmap.save(str(output), "PNG")
    
    if success:
        file_size = output.stat().st_size
        print(f"Screenshot saved: {output}")
        print(f"File size: {file_size:,} bytes")
        
        if file_size < 20 * 1024:  # Less than 20KB
            print("WARNING: Screenshot file is suspiciously small (<20KB)")
            return False
        
        return True
    else:
        print(f"ERROR: Failed to save screenshot to {output}")
        return False


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("V18 UI Screenshot Capture")
    print("=" * 60)
    
    try:
        success = capture_screenshot()
        
        if success:
            print("\n[SUCCESS] Screenshot captured successfully")
            print("Path: reports/screenshots/v18_ui_home.png")
            return 0
        else:
            print("\n[FAILED] Screenshot capture failed")
            print("\nManual screenshot instructions:")
            print("1. Run: scripts\\start_v18.bat")
            print("2. Wait for window to appear")
            print("3. Press Win+Shift+S to open Snipping Tool")
            print("4. Select the V18 window")
            print("5. Save to: reports\\screenshots\\v18_ui_home.png")
            return 1
            
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        print("\nManual screenshot instructions:")
        print("1. Run: scripts\\start_v18.bat")
        print("2. Wait for window to appear")
        print("3. Press Win+Shift+S to open Snipping Tool")
        print("4. Select the V18 window")
        print("5. Save to: reports\\screenshots\\v18_ui_home.png")
        return 1


if __name__ == "__main__":
    sys.exit(main())
