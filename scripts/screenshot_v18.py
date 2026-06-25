"""Take screenshots of V18 main window pages.

Usage: python scripts/screenshot_v18.py
Output: outputs/ui_screenshots/*.png
"""
import os
import sys
import time
from pathlib import Path

# Make app importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# On Windows, tell Qt where system fonts are (offscreen sometimes misses them)
if sys.platform == "win32":
    win_fonts = Path("C:/Windows/Fonts")
    if win_fonts.exists():
        os.environ.setdefault("QT_QPA_FONTDIR", str(win_fonts))

from PySide6.QtCore import QTimer, QSize
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


# CJK font fallback chain (Windows-first; macOS/Linux fallbacks follow)
_CJK_FONT_CANDIDATES = [
    "Microsoft YaHei UI",  # Windows 10/11 best CJK
    "Microsoft YaHei",
    "微软雅黑",
    "PingFang SC",         # macOS Chinese
    "Hiragino Sans GB",    # macOS Chinese alt
    "Noto Sans CJK SC",    # Linux / cross-platform
    "WenQuanYi Micro Hei", # Linux
    "Source Han Sans SC",  # Adobe open-source
    "SimHei",              # Windows XP/7 fallback
    "Arial Unicode MS",    # last-ditch
]


def _pick_cjk_font() -> QFont | None:
    """Return a QFont for the first available CJK font, or None."""
    db = QFontDatabase()
    families = set(db.families())
    for name in _CJK_FONT_CANDIDATES:
        if name in families:
            return QFont(name, 10)
    # Fallback: any font whose family contains common CJK markers
    for f in families:
        if any(m in f.lower() for m in ("cjk", "yahei", "pingfang", "han", "wqy", "noto sans c")):
            return QFont(f, 10)
    return None


def main() -> int:
    out_dir = Path("outputs/ui_screenshots")
    out_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # cross-platform consistent look

    # Apply a CJK-capable font at the application level so all QLabels,
    # buttons, etc. render Chinese correctly (fixes tofu / 方块).
    cjk_font = _pick_cjk_font()
    if cjk_font is not None:
        app.setFont(cjk_font)
        print(f"  applied CJK font: {cjk_font.family()}")
    else:
        print("  WARNING: no CJK font found — Chinese text will render as tofu")
        print(f"  Available families (sample): {sorted(QFontDatabase().families())[:10]}")


    w = MainWindow()
    w.resize(1280, 800)
    w.show()
    # Process events to let the window settle
    for _ in range(5):
        app.processEvents()
        time.sleep(0.1)

    # Take screenshot of the whole main window
    pix = w.grab()
    out_main = out_dir / "01_main_window.png"
    pix.save(str(out_main), "PNG")
    print(f"  saved: {out_main} ({pix.width()}x{pix.height()})")

    # Try to navigate to each page (if there's a stacked widget)
    # Check what child widgets the main window has
    pages_tried = []
    for attr in dir(w):
        if attr.startswith("_") or attr in ("grab", "show", "hide", "close"):
            continue
        try:
            child = getattr(w, attr)
            if hasattr(child, "grab") and callable(child.grab):
                # Look for a stacked widget or pages
                if "page" in attr.lower() or "view" in attr.lower():
                    try:
                        child.show()
                        app.processEvents()
                        time.sleep(0.1)
                        cpix = child.grab()
                        out = out_dir / f"02_{attr}.png"
                        cpix.save(str(out), "PNG")
                        pages_tried.append(out)
                        print(f"  saved: {out} ({cpix.width()}x{cpix.height()})")
                    except Exception as e:
                        pass
        except Exception:
            pass

    if not pages_tried:
        # Maybe pages are inside a stacked widget
        for child_name in dir(w):
            if child_name.startswith("_"):
                continue
            child = getattr(w, child_name, None)
            if child and hasattr(child, "count") and hasattr(child, "widget"):
                # Looks like a QStackedWidget
                try:
                    n = child.count()
                    for i in range(n):
                        page = child.widget(i)
                        if page is None:
                            continue
                        child.setCurrentIndex(i)
                        app.processEvents()
                        time.sleep(0.1)
                        cpix = w.grab()
                        out = out_dir / f"02_{child_name}_{i}.png"
                        cpix.save(str(out), "PNG")
                        pages_tried.append(out)
                        print(f"  saved: {out} ({cpix.width()}x{cpix.height()})")
                except Exception as e:
                    pass

    print(f"\n  Total screenshots: 1 main + {len(pages_tried)} pages")
    print(f"  Output dir: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
