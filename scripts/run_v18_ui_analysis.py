"""Run V18 UI analysis and capture finished/failed screenshot.

This script:
1. Starts the V18 MainWindow
2. Selects sample_case.txt as input
3. Selects identity and goal
4. Clicks start analysis
5. Waits for completion
6. Captures screenshot (finished or failed)

Usage:
    python scripts/run_v18_ui_analysis.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


def run_analysis_and_capture() -> tuple[bool, str]:
    """Run analysis and capture screenshot.
    
    Returns:
        Tuple of (success: bool, screenshot_path: str)
    """
    app = QApplication(sys.argv)
    
    # Create and show window
    window = MainWindow()
    window.show()
    
    # Wait for window to render
    for _ in range(10):
        app.processEvents()
        time.sleep(0.1)
    
    # Set sample file
    sample_file = str(Path("raw_materials/sample_case.txt").resolve())
    if not Path(sample_file).exists():
        print(f"ERROR: Sample file not found: {sample_file}")
        return False, ""
    
    window.upload_card.selected_files = [sample_file]
    window.upload_card._update_display()
    window.upload_card.files_selected.emit([sample_file])
    
    # Set identity (起诉方 is already selected by default)
    # Set goal (起诉立案 is already selected by default)
    
    app.processEvents()
    time.sleep(0.5)
    
    # Click start analysis
    print("Starting analysis...")
    window.start_btn.click()
    
    # Wait for analysis to complete (max 120 seconds)
    max_wait = 120
    start_time = time.time()
    last_stage = ""
    
    while time.time() - start_time < max_wait:
        app.processEvents()
        time.sleep(0.5)
        
        # Check if finished
        if window.status_badge.badge.text() in ("已完成", "失败"):
            break
        
        # Print progress
        current_stage = window.status_badge.badge.text()
        if current_stage != last_stage:
            print(f"  Status: {current_stage}")
            last_stage = current_stage
    
    # Wait a bit more for UI to settle
    time.sleep(1.0)
    app.processEvents()
    
    # Determine result
    final_status = window.status_badge.badge.text()
    success = final_status == "已完成"
    
    # Capture screenshot
    screen = app.primaryScreen()
    if screen is None:
        print("ERROR: No screen available")
        return False, ""
    
    pixmap = screen.grabWindow(window.winId())
    
    if pixmap.isNull():
        print("ERROR: Failed to capture window")
        return False, ""
    
    # Save screenshot
    if success:
        output_path = "reports/screenshots/v18_ui_finished.png"
    else:
        output_path = "reports/screenshots/v18_ui_failed.png"
    
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    saved = pixmap.save(str(output), "PNG")
    
    if saved:
        file_size = output.stat().st_size
        print(f"\nScreenshot saved: {output}")
        print(f"File size: {file_size:,} bytes")
        print(f"Final status: {final_status}")
        return success, str(output)
    else:
        print(f"ERROR: Failed to save screenshot")
        return False, ""


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("V18 UI Real Analysis Test")
    print("=" * 60)
    
    try:
        success, screenshot_path = run_analysis_and_capture()
        
        print("\n" + "=" * 60)
        if success:
            print("[SUCCESS] Analysis completed successfully")
            print(f"Screenshot: {screenshot_path}")
            return 0
        else:
            print("[FAILED] Analysis failed or timed out")
            if screenshot_path:
                print(f"Screenshot: {screenshot_path}")
            return 1
            
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
