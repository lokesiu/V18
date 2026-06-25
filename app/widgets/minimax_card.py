"""app/widgets/minimax_card.py — MiniMax provider card for AI settings.

A self-contained card widget for configuring the MiniMax (MiniMax / 稀宇科技)
AI provider. Designed to be dropped into the AI settings page next to the
existing DeepSeek and MiMo cards.

Features:
    - API Key + Base URL fields (password-masked key)
    - Model selector (MiniMax-M2.7 / MiniMax-M2.5 / MiniMax-M1 / MiniMax-Text-01)
    - "申请 API Key" hyperlink button — opens platform.minimaxi.com in browser
    - "查看教程" button — opens in-app tutorial dialog
    - "测试连接" button — verifies the API is reachable
    - "保存" button — persists settings via settings_store
    - Status indicator (未配置 / 测试中 / 可用 / 失败)

Usage (from settings_page.py, after the MiMo card):
    from app.widgets.minimax_card import MiniMaxCard
    layout.addWidget(self.minimax_card := MiniMaxCard())

The card emits a generic "settings_changed" signal via a chained QObject
signal so the parent can react (e.g., update the AI status badge in the
header). The card also auto-loads from settings_store on construction.

WIP NOTE: app/pages/settings_page.py is currently in WIP. The
corresponding SettingsPage (line 102 in app/widgets/settings_page.py)
calls ``_create_mimo_section()`` then stops. To integrate this card,
add it to the layout in _setup_ui() of either settings page:

    layout.addWidget(self.minimax_card := MiniMaxCard())
"""
from __future__ import annotations

import time
from typing import Optional

import httpx
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
)

from qfluentwidgets import (
    HeaderCardWidget, SubtitleLabel, BodyLabel, CaptionLabel,
    PrimaryPushButton, PushButton, HyperlinkButton, FluentIcon, InfoBar,
)

from app.style_constants import Colors, Spacing, Typography
from app.widgets.api_tutorial_dialog import ApiTutorialDialog


# ---------------------------------------------------------------------------
# Constants — keep in sync with official MiniMax docs (2025)
# ---------------------------------------------------------------------------
MINIMAX_DEFAULT_BASE_URL = "https://api.minimaxi.com/v1"
MINIMAX_CHAT_ENDPOINT = "/text/chatcompletion_v2"
MINIMAX_API_KEY_URL = "https://platform.minimaxi.com/usercenter/apikeys"
MINIMAX_TUTORIAL_URL = "https://platform.minimaxi.com/docs"

MINIMAX_MODELS = [
    "MiniMax-M2.7",      # current flagship (2026)
    "MiniMax-M2.5",      # stable production
    "MiniMax-M1",        # 1M context reasoning
    "MiniMax-Text-01",   # legacy / fallback
]

MINIMAX_DESCRIPTION = "MiniMax 稀宇科技 旗舰模型 (M2.7 / M2.5 / M1 / Text-01)"

# Styles — keep consistent with app/widgets/settings_page.py palette
_INPUT = (
    f"QLineEdit {{"
    f"  background-color: #18181e; color: #e0e0e0;"
    f"  border: 1px solid #2a2a32; border-radius: 6px;"
    f"  padding: 8px 12px; font-size: 13px;"
    f"  selection-background-color: #3b82f6; selection-color: #ffffff;"
    f"}}"
    f"QLineEdit:focus {{ border: 1px solid #3b82f6; }}"
    f"QLineEdit:disabled {{ background-color: #141418; color: #505058; }}"
)
_COMBO = (
    f"QComboBox {{"
    f"  background-color: #18181e; color: #e0e0e0;"
    f"  border: 1px solid #2a2a32; border-radius: 6px;"
    f"  padding: 8px 12px; font-size: 13px;"
    f"}}"
    f"QComboBox:focus {{ border: 1px solid #3b82f6; }}"
    f"QComboBox::drop-down {{"
    f"  subcontrol-origin: padding; subcontrol-position: center right;"
    f"  width: 28px; border: none;"
    f"}}"
    f"QComboBox QAbstractItemView {{"
    f"  background-color: #1c1c22; color: #e0e0e0;"
    f"  border: 1px solid #2a2a32;"
    f"  selection-background-color: #3b82f6; selection-color: #ffffff;"
    f"}}"
)
_BTN = (
    f"PushButton {{"
    f"  background-color: #2a2a32; color: #d0d0d8;"
    f"  border: 1px solid #3a3a42; border-radius: 6px;"
    f"  padding: 8px 16px; font-size: 13px;"
    f"}}"
    f"PushButton:hover {{ border: 1px solid #3b82f6; color: #3b82f6; }}"
    f"PushButton:disabled {{ background-color: #1c1c22; color: #505058; border: 1px solid #2a2a32; }}"
)
_SAVE = (
    f"PrimaryPushButton {{"
    f"  background-color: #3b82f6; color: #ffffff;"
    f"  border: none; border-radius: 6px;"
    f"  padding: 8px 20px; font-size: 13px; font-weight: bold;"
    f"}}"
    f"PrimaryPushButton:hover {{ background-color: #5b9aff; }}"
    f"PrimaryPushButton:disabled {{ background-color: #2a2a32; color: #505058; }}"
)
_LINK_BTN = (
    f"HyperlinkButton {{"
    f"  background-color: transparent;"
    f"  color: #3b82f6;"
    f"  border: 1px solid #2a2a32;"
    f"  border-radius: 6px;"
    f"  padding: 6px 12px;"
    f"  font-size: 12px;"
    f"  text-decoration: none;"
    f"}}"
    f"HyperlinkButton:hover {{"
    f"  background-color: rgba(59, 130, 246, 0.1);"
    f"  border-color: #3b82f6;"
    f"  color: #5b9aff;"
    f"}}"
)
_CARD = (
    f"HeaderCardWidget {{"
    f"  background-color: #1c1c22; border: 1px solid #2a2a32; border-radius: 8px;"
    f"}}"
)
_LABEL = "BodyLabel { color: #b0b0b8; font-size: 13px; }"
_CAP_GRAY = "CaptionLabel { color: #707078; font-size: 12px; }"
_CAP_ACCENT = "CaptionLabel { color: #3b82f6; font-size: 12px; }"


class MiniMaxCard(HeaderCardWidget):
    """Self-contained MiniMax provider card.

    Mirrors the layout of the DeepSeek / MiMo cards in
    ``app/widgets/settings_page.py`` for visual consistency. Loads from and
    persists to ``core.settings_store`` if available; otherwise operates in
    standalone mode (in-memory only — useful for the WIP drop-in period).
    """

    settings_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("MiniMax")
        self.setStyleSheet(_CARD)
        self._build_ui()
        self._load_settings()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # HeaderCardWidget.viewLayout is a QHBoxLayout (header + body).
        # To get a vertical body we wrap our content in a QWidget and add
        # that to viewLayout — that's the only way QHBoxLayout accepts a
        # QVBoxLayout's children.
        from PySide6.QtWidgets import QWidget
        body = QWidget()
        outer = QVBoxLayout(body)
        outer.setSpacing(12)
        outer.setContentsMargins(0, 0, 0, 0)  # view already has 24px margins

        # Provider description + external links row
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        desc = CaptionLabel(MINIMAX_DESCRIPTION)
        desc.setStyleSheet(_CAP_GRAY)
        desc.setWordWrap(True)
        header_row.addWidget(desc, 1)

        # "申请 API Key" hyperlink button → external browser
        self.apply_btn = HyperlinkButton(
            text="🔑  申请 API Key",
            url=MINIMAX_API_KEY_URL,
            parent=self,
        )
        self.apply_btn.setStyleSheet(_LINK_BTN)
        self.apply_btn.setToolTip(f"在浏览器中打开 {MINIMAX_API_KEY_URL}")
        header_row.addWidget(self.apply_btn)

        # "查看教程" in-app tutorial
        self.tutorial_btn = PushButton("📖  查看教程")
        self.tutorial_btn.setIcon(FluentIcon.QUESTION)
        self.tutorial_btn.setStyleSheet(_BTN)
        self.tutorial_btn.clicked.connect(self._show_tutorial)
        header_row.addWidget(self.tutorial_btn)

        outer.addLayout(header_row)

        # API Key field
        lbl = BodyLabel("API Key")
        lbl.setStyleSheet(_LABEL)
        outer.addWidget(lbl)
        self.mm_key_input = QLineEdit()
        self.mm_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.mm_key_input.setPlaceholderText("eyJ...  (在 platform.minimaxi.com 创建)")
        self.mm_key_input.setStyleSheet(_INPUT)
        outer.addWidget(self.mm_key_input)

        # Base URL field
        lbl = BodyLabel("Base URL")
        lbl.setStyleSheet(_LABEL)
        outer.addWidget(lbl)
        self.mm_url_input = QLineEdit()
        self.mm_url_input.setText(MINIMAX_DEFAULT_BASE_URL)
        self.mm_url_input.setPlaceholderText(MINIMAX_DEFAULT_BASE_URL)
        self.mm_url_input.setStyleSheet(_INPUT)
        outer.addWidget(self.mm_url_input)

        # Model selector
        lbl = BodyLabel("默认模型")
        lbl.setStyleSheet(_LABEL)
        outer.addWidget(lbl)
        self.mm_model_combo = QComboBox()
        self.mm_model_combo.addItems(MINIMAX_MODELS)
        self.mm_model_combo.setCurrentText("MiniMax-M2.7")
        self.mm_model_combo.setStyleSheet(_COMBO)
        self.mm_model_combo.setToolTip(
            "M2.7: 当前旗舰 (推荐)\n"
            "M2.5: 稳定生产\n"
            "M1: 1M 上下文推理 (长文档)\n"
            "Text-01: 老版本 (回退)"
        )
        outer.addWidget(self.mm_model_combo)

        # Use-case note (MiniMax's strengths)
        note = CaptionLabel(
            "推荐场景: 长文书分析、案件事实梳理、多模态材料理解"
        )
        note.setStyleSheet(_CAP_GRAY)
        note.setWordWrap(True)
        outer.addWidget(note)

        # Action row: test + status + save
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.mm_test_btn = PushButton("测试连接")
        self.mm_test_btn.setIcon(FluentIcon.PLAY)
        self.mm_test_btn.setStyleSheet(_BTN)
        self.mm_test_btn.clicked.connect(self._test_connection)
        btn_layout.addWidget(self.mm_test_btn)

        self.mm_status_label = CaptionLabel("未配置")
        self.mm_status_label.setStyleSheet(_CAP_GRAY)
        btn_layout.addWidget(self.mm_status_label)

        btn_layout.addStretch()

        self.mm_save_btn = PrimaryPushButton("保存")
        self.mm_save_btn.setIcon(FluentIcon.SAVE)
        self.mm_save_btn.setStyleSheet(_SAVE)
        self.mm_save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.mm_save_btn)

        outer.addLayout(btn_layout)

        # Attach the body widget to the card's view (QHBoxLayout)
        self.viewLayout.addWidget(body)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _show_tutorial(self) -> None:
        dialog = ApiTutorialDialog(
            title="如何获取 MiniMax API Key",
            steps=[
                "访问 MiniMax 开放平台 "
                f"<a href='{MINIMAX_API_KEY_URL}' style='color:#3b82f6;'>{MINIMAX_API_KEY_URL}</a>",
                "注册账号并完成实名认证 (个人/企业均可)",
                "进入「账户管理 → API Keys」,点击「创建新的 API Key」",
                "为 Key 命名 (如 'V18-Production'),勾选需要的权限范围",
                "<b>复制显示的 Key</b> — 创建后 Key 仅显示一次,请立即保存",
                "回到 V18 设置页,粘贴到 MiniMax 卡片,点击「测试连接」验证",
            ],
            url=MINIMAX_API_KEY_URL,
            warning=(
                "API Key 仅在创建时完整显示一次。丢失后需重新创建。"
                "请勿将 Key 提交到 Git 仓库或分享给他人。"
            ),
            tip=(
                "新用户通常有免费额度,可在「账户管理 → 余额」查看。"
                "按量付费,无最低消费。V18 默认使用 M2.7 模型。"
            ),
            parent=self.window(),
        )
        dialog.exec()

    def _test_connection(self) -> None:
        """Make a minimal API call to verify connectivity."""
        self.mm_test_btn.setEnabled(False)
        self._set_status("测试中...", "info")
        try:
            api_key = self.mm_key_input.text().strip()
            base_url = self.mm_url_input.text().strip().rstrip("/")
            model = self.mm_model_combo.currentText()

            if not api_key:
                self._set_status("未配置", "muted")
                InfoBar.warning(
                    "未配置",
                    "请先填写 API Key",
                    parent=self.window(),
                )
                return

            start = time.time()
            url = f"{base_url}{MINIMAX_CHAT_ENDPOINT}"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 8,
                "temperature": 0.0,
            }
            with httpx.Client(timeout=15) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            latency = int((time.time() - start) * 1000)
            # MiniMax returns {"base_resp": {"status_code": 0, "status_msg": "success"}}
            base_resp = data.get("base_resp", {})
            status_code = base_resp.get("status_code", -1)
            if status_code == 0 or "choices" in data:
                self._set_status(f"可用 ({latency}ms · {model})", "success")
                InfoBar.success(
                    "连接成功",
                    f"延迟 {latency}ms · 模型 {model}",
                    parent=self.window(),
                )
            else:
                msg = base_resp.get("status_msg", "未知错误")
                self._set_status(f"失败: {msg}", "error")
                InfoBar.error("连接失败", msg, parent=self.window())
        except httpx.TimeoutException:
            self._set_status("失败: 请求超时 (15s)", "error")
            InfoBar.error("连接失败", "请求超时,请检查网络", parent=self.window())
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            detail = ""
            try:
                detail = e.response.json().get("base_resp", {}).get("status_msg", "")
            except Exception:
                pass
            msg = f"HTTP {code}" + (f" · {detail}" if detail else "")
            self._set_status(f"失败: {msg}", "error")
            InfoBar.error("连接失败", msg, parent=self.window())
        except Exception as e:
            self._set_status(f"错误: {e}", "error")
            InfoBar.error("连接错误", str(e), parent=self.window())
        finally:
            self.mm_test_btn.setEnabled(True)

    def _save_settings(self) -> None:
        """Persist to settings_store if available; otherwise in-memory."""
        api_key = self.mm_key_input.text().strip()
        base_url = self.mm_url_input.text().strip() or MINIMAX_DEFAULT_BASE_URL
        model = self.mm_model_combo.currentText()

        saved_to_disk = False
        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()
            store.update_minimax(
                api_key=api_key,
                base_url=base_url,
                model=model,
            )
            store.save()
            saved_to_disk = True
        except (ImportError, AttributeError):
            # settings_store doesn't have update_minimax yet — that's OK
            pass
        except Exception as e:
            self._set_status(f"保存失败: {e}", "error")
            InfoBar.error("保存失败", str(e), parent=self.window())
            return

        if saved_to_disk:
            self._set_status("已保存", "success")
            InfoBar.success("保存成功", "MiniMax 设置已保存", parent=self.window())
        else:
            self._set_status("已暂存 (待 settings_store 支持)", "muted")
            InfoBar.info(
                "已暂存",
                "MiniMax 卡片需要在 settings_store 增加 update_minimax() 方法后落盘",
                parent=self.window(),
            )
        self.settings_changed.emit()

    def _load_settings(self) -> None:
        """Try to load existing settings; silently no-op if not available."""
        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()
            s = store.settings
            mm = getattr(s, "minimax", None)
            if mm is None:
                return
            if getattr(mm, "api_key", ""):
                self.mm_key_input.setText(mm.api_key)
            if getattr(mm, "base_url", ""):
                self.mm_url_input.setText(mm.base_url)
            model = getattr(mm, "model", "")
            if model:
                idx = self.mm_model_combo.findText(model)
                if idx >= 0:
                    self.mm_model_combo.setCurrentIndex(idx)
            if getattr(mm, "is_configured", lambda: False)():
                self._set_status("已配置", "muted")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------
    def _set_status(self, text: str, kind: str = "muted") -> None:
        self.mm_status_label.setText(text)
        if kind == "success":
            self.mm_status_label.setStyleSheet("color: #22c55e; font-size: 12px;")
        elif kind == "error":
            self.mm_status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        elif kind == "info":
            self.mm_status_label.setStyleSheet("color: #3b82f6; font-size: 12px;")
        else:
            self.mm_status_label.setStyleSheet(_CAP_GRAY)


__all__ = ["MiniMaxCard", "MINIMAX_DEFAULT_BASE_URL", "MINIMAX_MODELS"]
