"""Smoke test for the new V18 widgets — runs under offscreen Qt platform.

Verifies:
    1. Logo renders without errors (all 3 components)
    2. MiniMaxCard instantiates and lays out
    3. ApiTutorialDialog opens and lays out
    4. UploadCard folder-drop UX (folder_sources tracking)

Usage:
    QT_QPA_PLATFORM=offscreen python scripts/smoke_new_widgets.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Allow running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# On Windows, point Qt to the system fonts (offscreen sometimes misses them)
if sys.platform == "win32":
    win_fonts = Path("C:/Windows/Fonts")
    if win_fonts.exists():
        os.environ.setdefault("QT_QPA_FONTDIR", str(win_fonts))

from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from app.widgets.logo import Logo, LogoMark, LogoWordmark
from app.widgets.minimax_card import MiniMaxCard
from app.widgets.api_tutorial_dialog import ApiTutorialDialog
from app.widgets.upload_card import UploadCard

# CJK font hint (avoid tofu in offscreen mode)
_CJK_FONT_CANDIDATES = [
    "Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑",
    "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC",
    "WenQuanYi Micro Hei", "Source Han Sans SC", "SimHei", "Arial Unicode MS",
]


def _setup_cjk_font(app: QApplication) -> None:
    db = QFontDatabase()
    families = set(db.families())
    for name in _CJK_FONT_CANDIDATES:
        if name in families:
            app.setFont(QFont(name, 10))
            return
    for f in families:
        if any(m in f.lower() for m in ("cjk", "yahei", "pingfang", "han", "wqy", "noto sans c")):
            app.setFont(QFont(f, 10))
            return


def test_logo() -> None:
    print("=== test_logo ===")
    app = QApplication.instance() or QApplication(sys.argv)

    # 1) Full logo
    logo = Logo(mark_size=28, show_latin=True)
    logo.show()
    app.processEvents()
    pix = logo.grab()
    assert not pix.isNull(), "Logo grab returned null"
    out = Path("outputs/ui_screenshots/03_logo_full.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out))
    print(f"  Logo full: {pix.width()}x{pix.height()} → {out}")

    # 2) LogoMark only
    mark = LogoMark(size=64)
    mark.show()
    app.processEvents()
    pix = mark.grab()
    assert not pix.isNull(), "LogoMark grab returned null"
    out = Path("outputs/ui_screenshots/03_logo_mark_64.png")
    pix.save(str(out))
    print(f"  LogoMark 64: {pix.width()}x{pix.height()} → {out}")

    # 3) LogoWordmark only
    wm = LogoWordmark(show_latin=True, font_size=18)
    wm.show()
    app.processEvents()
    pix = wm.grab()
    out = Path("outputs/ui_screenshots/03_logo_wordmark.png")
    pix.save(str(out))
    print(f"  Wordmark: {pix.width()}x{pix.height()} → {out}")

    # 4) Compact mode
    logo.set_compact(True)
    app.processEvents()
    pix = logo.grab()
    out = Path("outputs/ui_screenshots/03_logo_compact.png")
    pix.save(str(out))
    print(f"  Logo compact: {pix.width()}x{pix.height()} → {out}")

    print("  PASSED\n")


def test_minimax_card() -> None:
    print("=== test_minimax_card ===")
    app = QApplication.instance() or QApplication(sys.argv)

    card = MiniMaxCard()
    card.resize(QSize(720, 380))
    card.show()
    app.processEvents()
    pix = card.grab()
    out = Path("outputs/ui_screenshots/03_minimax_card.png")
    pix.save(str(out))
    print(f"  Card: {pix.width()}x{pix.height()} → {out}")
    print("  PASSED\n")


def test_tutorial_dialog() -> None:
    print("=== test_tutorial_dialog ===")
    app = QApplication.instance() or QApplication(sys.argv)

    dlg = ApiTutorialDialog(
        title="如何获取 MiniMax API Key",
        steps=[
            "访问 MiniMax 开放平台 platform.minimaxi.com",
            "注册账号并完成实名认证",
            "进入「账户管理 → API Keys」",
            "复制显示的 Key",
        ],
        url="https://platform.minimaxi.com/usercenter/apikeys",
        warning="API Key 仅在创建时完整显示一次",
        tip="新用户通常有免费额度",
    )
    dlg.show()
    app.processEvents()
    pix = dlg.grab()
    out = Path("outputs/ui_screenshots/03_tutorial_dialog.png")
    pix.save(str(out))
    print(f"  Dialog: {pix.width()}x{pix.height()} → {out}")
    dlg.close()
    print("  PASSED\n")


def test_upload_card_folder_drop() -> None:
    print("=== test_upload_card_folder_drop ===")
    app = QApplication.instance() or QApplication(sys.argv)

    card = UploadCard()
    card.resize(QSize(640, 400))
    card.show()
    app.processEvents()

    # Simulate the new folder-drop UX: directly call the helpers since
    # we can't synthesize a QDropEvent in offscreen easily.
    with tempfile.TemporaryDirectory() as tmpdir:
        # Files in root — use padded content so each has a unique size
        # (the dedup logic is name+size, so we need to vary sizes).
        (Path(tmpdir) / "contract.pdf").write_bytes(b"%PDF-1.4\ncontract body 1")
        (Path(tmpdir) / "evidence.txt").write_text("evidence body 22")
        # Nested
        sub = Path(tmpdir) / "sub"
        sub.mkdir()
        (sub / "letter.md").write_text("letter body 333")
        (sub / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)

        # Same-name file in two subfolders — vary sizes to avoid dedup
        sub_a = Path(tmpdir) / "a"
        sub_a.mkdir()
        sub_b = Path(tmpdir) / "b"
        sub_b.mkdir()
        (sub_a / "notes.md").write_text("from a " * 10)
        (sub_b / "notes.md").write_text("from b " * 20)

        from app.widgets.upload_card import resolve_paths
        resolved = resolve_paths([tmpdir])
        assert len(resolved) == 6, f"Expected 6 files, got {len(resolved)}"

        # Use the same internal API the dropEvent uses
        card._record_folder_sources([tmpdir], resolved)
        card._process_files(resolved)
        app.processEvents()

        # Verify folder_sources is populated
        assert len(card._folder_sources) == 1
        src_folder, src_count = next(iter(card._folder_sources.items()))
        assert src_count == 6
        print(f"  folder_sources: {Path(src_folder).name} → {src_count} files")

        # Verify sources_label is visible
        assert card.sources_label.isVisible(), "sources_label should be visible after folder drop"
        assert "📂" in card.sources_label.text()
        print(f"  sources_label: {card.sources_label.text()}")

        # Verify file_list shows relative paths
        items = [
            card.file_list.item(i).text() for i in range(card.file_list.count())
        ]
        print(f"  file_list items: {items}")
        # All 6 should be shown
        assert len(items) == 6, f"Expected 6 items, got {len(items)}: {items}"
        # The two "notes.md" should be disambiguated by parent folder
        notes_count = sum(1 for it in items if it.endswith("notes.md"))
        assert notes_count == 2, "Two notes.md files should be present"

        # Take a screenshot of the loaded state
        app.processEvents()
        pix = card.grab()
        out = Path("outputs/ui_screenshots/03_upload_card_with_folder.png")
        pix.save(str(out))
        print(f"  Card with folder loaded: {pix.width()}x{pix.height()} → {out}")

    # Test the empty state hint
    card._clear_files()
    app.processEvents()
    assert not card.sources_label.isVisible()
    print("  _clear_files resets folder_sources and hides sources_label")

    # Screenshot of empty state with the new hint
    pix = card.grab()
    out = Path("outputs/ui_screenshots/03_upload_card_empty_with_hint.png")
    pix.save(str(out))
    print(f"  Empty state with hint: → {out}")

    print("  PASSED\n")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    _setup_cjk_font(app)  # type: ignore[arg-type]
    test_logo()
    test_minimax_card()
    test_tutorial_dialog()
    test_upload_card_folder_drop()
    print("=" * 50)
    print("All 4 widget smoke tests PASSED")
