"""scripts/smoke_settings_page.py — 烟测新 settings_page.

Offscreen 渲染,5 张截图。Mock 掉 _TestWorker 避免真发 HTTP 请求。
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer, Qt, QThread
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.pages.settings_page import SettingsPage, _TestWorker
from core.settings_store import get_settings_store

OUT = ROOT / "outputs" / "ui_screenshots"
OUT.mkdir(parents=True, exist_ok=True)


# ── Mock _TestWorker: 不同 provider 不同结果 ─────────────────────────
_FAKE_RESULTS = {
    "deepseek": (True, "", 287),       # 已连接 · 287ms
    "mimo": (True, "", 412),           # 已连接 · 412ms
    "custom": (False, "API Key 无效", 0),  # 失败
}

# 替换 run() 直接同步 emit 模拟结果
def _fake_run(self):
    import time as _t
    _t.sleep(0.05)
    provider = self.provider
    ok, err, lat = _FAKE_RESULTS.get(provider, (True, "", 200))
    self.finished.emit(provider, ok, err, lat)

_TestWorker.run = _fake_run


def grab(page: SettingsPage, name: str):
    path = OUT / f"04_{name}.png"
    pix = page.grab()
    pix.save(str(path), "PNG")
    print(f"  saved {path} ({pix.width()}x{pix.height()})", flush=True)


def wait(app, seconds: float):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    page = SettingsPage()
    page.resize(820, 1400)
    page.show()
    wait(app, 0.2)
    print("SettingsPage constructed OK", flush=True)

    # ── 1. 空状态 ──
    print("\n[1] Empty state", flush=True)
    store = get_settings_store()
    store.update_deepseek(api_key="", base_url="", model_extract="")
    store.update_mimo(api_key="", base_url="", model="")
    store.update_custom(api_key="", base_url="", model="")
    store.save()
    page.load_settings()
    wait(app, 0.3)
    grab(page, "settings_empty")

    # ── 2. 部分配置 (DeepSeek + MiMo, 模拟已连接) ──
    print("\n[2] Partial config (DeepSeek+MiMo connected, custom empty)", flush=True)
    store.update_deepseek(
        api_key="sk-ds-test-fake-1234567890abcdef",
        base_url="https://api.deepseek.com",
        model_extract="deepseek-v4-flash",
    )
    store.update_mimo(
        api_key="sk-mimo-test-fake-1234567890abcdef",
        base_url="https://api.mimo.ai/v1",
        model="mimo-v2.5",
    )
    store.update_custom(api_key="", base_url="", model="")
    store.save()
    page.load_settings()
    wait(app, 0.4)
    grab(page, "settings_partial_config")

    # ── 3. Dual 模式 (默认) ──
    print("\n[3] Dual mode", flush=True)
    page._mode_card.set_mode("dual")
    wait(app, 0.2)
    grab(page, "settings_dual_mode")

    # ── 4. 全部都配置了 + custom 失败 ──
    print("\n[4] All filled, custom failed", flush=True)
    store.update_custom(
        api_key="sk-custom-fake-1234567890",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
    )
    store.save()
    page.load_settings()
    wait(app, 0.4)
    grab(page, "settings_all_filled")

    # ── 5. 眼睛按钮(明文) ──
    print("\n[5] Key visible (eye toggle)", flush=True)
    page._cards["deepseek"]._toggle_key_visibility()
    page._cards["mimo"]._toggle_key_visibility()
    page._cards["custom"]._toggle_key_visibility()
    wait(app, 0.2)
    grab(page, "settings_key_visible")

    # ── 6. Basic 模式 ──
    print("\n[6] Basic mode", flush=True)
    page._mode_card.set_mode("basic")
    wait(app, 0.2)
    grab(page, "settings_basic_mode")

    # ── Cleanup: 把 store 里的 fake key 清掉,避免污染后续测试 ──
    print("\n[cleanup] Removing fake keys from settings_store", flush=True)
    store.update_deepseek(api_key="", base_url="https://api.deepseek.com", model_extract="deepseek-v4-flash")
    store.update_mimo(api_key="", base_url="https://api.mimo.ai/v1", model="mimo-v2.5")
    store.update_custom(api_key="", base_url="", model="")
    store.save()

    print("\nAll done.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
