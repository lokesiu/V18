"""app/pages/settings_page.py — 设置页面.

彻底重构：使用纯垂直布局的 VerticalFormCard，放弃 SettingCard。
参考 Dify 等主流 AI 软件的配置界面风格。
"""
from __future__ import annotations

from PySide6.QtCore import Signal, Qt, QThread, QTimer
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QComboBox, QCheckBox,
    QLabel, QFrame, QSizePolicy, QPushButton, QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor, QIcon

from qfluentwidgets import (
    SettingCardGroup, ExpandLayout, SimpleCardWidget,
    FluentIcon, ScrollArea, IconWidget,
    CaptionLabel, BodyLabel, SubtitleLabel,
    InfoBar, ComboBox,
)


# ── Stylesheets ───────────────────────────────────────────────────────

_INPUT_STYLE = """
    QLineEdit {
        padding: 8px 12px;
        border: 1px solid #D1D5DB;
        border-radius: 8px;
        background-color: #FFFFFF;
        color: #1F2937;
        font-size: 13px;
    }
    QLineEdit:focus {
        border-color: #3b82f6;
        border-width: 2px;
    }
    QLineEdit:hover {
        border-color: #9CA3AF;
    }
"""

_COMBO_STYLE = """
    QComboBox {
        padding: 8px 12px;
        border: 1px solid #D1D5DB;
        border-radius: 8px;
        background-color: #FFFFFF;
        color: #1F2937;
        font-size: 13px;
    }
    QComboBox:hover {
        border-color: #9CA3AF;
    }
    QComboBox:focus {
        border-color: #3b82f6;
    }
"""

_CHECKBOX_STYLE = """
    QCheckBox {
        spacing: 8px;
        color: #1F2937;
        background: transparent;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 2px solid #D1D5DB;
        border-radius: 3px;
        background-color: #FFFFFF;
    }
    QCheckBox::indicator:checked {
        background-color: #3b82f6;
        border-color: #3b82f6;
    }
    QCheckBox::indicator:hover {
        border-color: #3b82f6;
    }
"""

_CARD_STYLE = """
    QFrame#VerticalFormCard {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
    }
"""

_TOGGLE_STYLE = """
    QPushButton {
        background: transparent;
        border: none;
        color: #6B7280;
        font-size: 12px;
        text-align: left;
        padding: 4px 0;
    }
    QPushButton:hover {
        color: #3b82f6;
    }
    QPushButton:checked {
        color: #3b82f6;
    }
"""


# ── Async Test Connection Worker ──────────────────────────────────────

class _TestConnectionWorker(QThread):
    """异步测试 API 连接的工作线程"""
    finished = Signal(bool, str, int)  # success, error_msg, latency_ms

    def __init__(self, provider_type: str, api_key: str, base_url: str, model: str):
        super().__init__()
        self.provider_type = provider_type
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def _build_url(self) -> str:
        """构建正确的 API URL，避免重复 /v1"""
        base = self.base_url.rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    def run(self):
        import httpx

        url = self._build_url()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "1"}],
            "max_tokens": 1,
        }

        start = __import__("time").time()
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(url, json=payload, headers=headers)

            latency = int((__import__("time").time() - start) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                if "choices" in data:
                    self.finished.emit(True, "", latency)
                else:
                    self.finished.emit(False, "响应格式异常", latency)
            elif resp.status_code == 401:
                self.finished.emit(False, "API Key 错误或未授权", latency)
            else:
                try:
                    err = resp.json().get("error", {}).get("message", "")
                except Exception:
                    err = resp.text[:100]
                self.finished.emit(False, f"HTTP {resp.status_code}: {err}", latency)

        except httpx.TimeoutException:
            latency = int((__import__("time").time() - start) * 1000)
            self.finished.emit(False, "请求超时", latency)
        except Exception as e:
            latency = int((__import__("time").time() - start) * 1000)
            self.finished.emit(False, str(e)[:80], latency)


# ── Vertical Form Card (纯垂直布局) ──────────────────────────────────

class VerticalFormCard(QFrame):
    """纯垂直布局的表单卡片，彻底避免水平挤压问题"""

    def __init__(self, icon, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("VerticalFormCard")
        self.setStyleSheet(_CARD_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        # Main vertical layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # ── Header ──
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(12)

        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(20, 20)
        header_layout.addWidget(icon_widget)

        title_lbl = SubtitleLabel(title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 600; background: transparent;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        self.main_layout.addWidget(header)

        # ── Separator ──
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #F3F4F6; max-height: 1px;")
        self.main_layout.addWidget(separator)

        # ── Content area (vertical) ──
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(12)
        self.content_layout.setContentsMargins(20, 16, 20, 20)

        self.main_layout.addWidget(self.content_widget)

    def _add_form_field(self, label_text: str, widget: QWidget) -> QWidget:
        """Add a label + widget pair vertically."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = CaptionLabel(label_text)
        lbl.setStyleSheet("font-weight: 500; color: #374151; background: transparent;")
        layout.addWidget(lbl)
        layout.addWidget(widget)

        self.content_layout.addWidget(container)
        return container

    def _add_widget(self, widget: QWidget):
        """Add a widget directly to content layout."""
        self.content_layout.addWidget(widget)

    def _add_separator(self):
        """Add a thin separator line."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #F3F4F6; max-height: 1px;")
        self.content_layout.addWidget(sep)


# ── Provider Config Card ─────────────────────────────────────────────

class _ProviderConfigCard(VerticalFormCard):
    """AI Provider 配置 - 纯垂直布局"""

    def __init__(self, icon, name: str, default_url: str,
                 model_items: list[str], parent=None):
        super().__init__(icon, name, f"配置 {name} API", parent)

        self.provider_name = name.lower()
        self._worker = None
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._restore_status)

        # API Key input
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-...")
        self.key_input.setFixedHeight(38)
        self.key_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.key_input.setStyleSheet(_INPUT_STYLE)
        self._add_form_field("API Key", self.key_input)

        # Account type indicator (for MiMo, hidden by default)
        self.account_label = CaptionLabel("")
        self.account_label.setStyleSheet("color: #6B7280; font-size: 11px; background: transparent;")
        self.account_label.setVisible(False)
        self._add_widget(self.account_label)

        # Advanced settings toggle
        self.advanced_toggle = QPushButton("  ▶ 高级设置")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setChecked(False)
        self.advanced_toggle.setStyleSheet(_TOGGLE_STYLE)
        self.advanced_toggle.toggled.connect(self._on_toggle)
        self._add_widget(self.advanced_toggle)

        # Advanced settings container (hidden by default)
        self.advanced_container = QWidget()
        self.advanced_container.setStyleSheet("background: transparent;")
        self.advanced_container.setVisible(False)
        adv_layout = QVBoxLayout(self.advanced_container)
        adv_layout.setSpacing(12)
        adv_layout.setContentsMargins(0, 0, 0, 0)

        # Base URL
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(default_url)
        self.url_input.setText(default_url)
        self.url_input.setFixedHeight(38)
        self.url_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.url_input.setStyleSheet(_INPUT_STYLE)

        url_container = QWidget()
        url_container.setStyleSheet("background: transparent;")
        url_layout = QVBoxLayout(url_container)
        url_layout.setSpacing(6)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_lbl = CaptionLabel("Base URL")
        url_lbl.setStyleSheet("font-weight: 500; color: #374151; background: transparent;")
        url_layout.addWidget(url_lbl)
        url_layout.addWidget(self.url_input)
        adv_layout.addWidget(url_container)

        # Model selection
        self.model_combo = ComboBox()
        self.model_combo.addItems(model_items)
        self.model_combo.setFixedHeight(38)
        self.model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.model_combo.setStyleSheet(_COMBO_STYLE)

        model_container = QWidget()
        model_container.setStyleSheet("background: transparent;")
        model_layout = QVBoxLayout(model_container)
        model_layout.setSpacing(6)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_lbl = CaptionLabel("模型")
        model_lbl.setStyleSheet("font-weight: 500; color: #374151; background: transparent;")
        model_layout.addWidget(model_lbl)
        model_layout.addWidget(self.model_combo)
        adv_layout.addWidget(model_container)

        self._add_widget(self.advanced_container)

        # ── Action bar ──
        self._add_separator()
        action_bar = QWidget()
        action_bar.setStyleSheet("background: transparent;")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 4, 0, 0)
        action_layout.setSpacing(12)

        self.test_btn = QPushButton("  ▷ 测试连接")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px 14px;
                color: #374151;
                font-size: 12px;
            }
            QPushButton:hover {
                border-color: #3b82f6;
                color: #3b82f6;
            }
        """)
        action_layout.addWidget(self.test_btn)

        self.status_label = CaptionLabel("未配置")
        self.status_label.setStyleSheet("color: #6B7280; background: transparent;")
        action_layout.addWidget(self.status_label)

        action_layout.addStretch()

        self.save_btn = QPushButton("  💾 保存")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
        """)
        action_layout.addWidget(self.save_btn)

        self._add_widget(action_bar)

        # ── Connect signals ──
        self.test_btn.clicked.connect(self._on_test_clicked)
        self.save_btn.clicked.connect(self._on_save_clicked)

    def _on_toggle(self, checked: bool):
        """Toggle advanced settings visibility."""
        self.advanced_container.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self.advanced_toggle.setText(f"  {arrow} 高级设置")

    def get_key(self) -> str:
        return self.key_input.text()

    def get_url(self) -> str:
        return self.url_input.text()

    def get_model(self) -> str:
        return self.model_combo.currentText()

    def _on_test_clicked(self):
        """测试连接按钮点击处理"""
        api_key = self.get_key().strip()
        base_url = self.get_url().strip()
        model = self.get_model()

        if not api_key:
            self._set_status("❌ 请输入 API Key", "#EF4444")
            return

        # 禁用按钮，防止重复点击
        self.test_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self._set_status("测试中...", "#F59E0B")

        # 启动异步测试
        self._worker = _TestConnectionWorker(self.provider_name, api_key, base_url, model)
        self._worker.finished.connect(self._on_test_finished)
        self._worker.start()

    def _on_test_finished(self, success: bool, error_msg: str, latency_ms: int):
        """测试连接完成回调"""
        self.test_btn.setEnabled(True)
        self.save_btn.setEnabled(True)

        if success:
            self._set_status(f"✅ 连接成功 ({latency_ms}ms)", "#10B981")
        else:
            self._set_status(f"❌ 连接失败: {error_msg[:30]}", "#EF4444")

        # 3秒后恢复状态
        self._status_timer.start(3000)

    def _on_save_clicked(self):
        """保存按钮点击处理"""
        api_key = self.get_key().strip()
        base_url = self.get_url().strip()
        model = self.get_model()

        if not api_key:
            self._set_status("❌ 请输入 API Key", "#EF4444")
            return

        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()

            if self.provider_name == "deepseek":
                store.update_deepseek(api_key=api_key, base_url=base_url, model_extract=model)
            else:
                store.update_mimo(api_key=api_key, base_url=base_url, model=model)

            store.save()
            self._set_status("保存成功 ✓", "#10B981")

            # 3秒后恢复状态
            self._status_timer.start(3000)

        except Exception as e:
            self._set_status(f"❌ 保存失败: {str(e)[:30]}", "#EF4444")

    def _set_status(self, text: str, color: str):
        """设置状态标签文本和颜色"""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; background: transparent;")

    def _restore_status(self):
        """恢复状态标签为已配置/未配置"""
        if self.get_key().strip():
            self._set_status("已配置", "#6B7280")
        else:
            self._set_status("未配置", "#6B7280")


# ── Custom Model Card ─────────────────────────────────────────────────

class _CustomModelCard(VerticalFormCard):
    """自定义第三方模型 - 纯垂直布局，无折叠"""

    def __init__(self, parent=None):
        super().__init__(
            FluentIcon.CONNECT, "自定义模型",
            "支持 OpenAI 接口规范的第三方模型", parent,
        )

        self._worker = None
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._restore_status)

        # API Key
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-...")
        self.key_input.setFixedHeight(38)
        self.key_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.key_input.setStyleSheet(_INPUT_STYLE)
        self._add_form_field("API Key", self.key_input)

        # Base URL
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.example.com/v1")
        self.url_input.setFixedHeight(38)
        self.url_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.url_input.setStyleSheet(_INPUT_STYLE)
        self._add_form_field("Base URL", self.url_input)

        # Model name
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("gpt-4o / claude-3 / ...")
        self.model_input.setFixedHeight(38)
        self.model_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.model_input.setStyleSheet(_INPUT_STYLE)
        self._add_form_field("模型名称", self.model_input)

        # ── Action bar ──
        self._add_separator()
        action_bar = QWidget()
        action_bar.setStyleSheet("background: transparent;")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 4, 0, 0)
        action_layout.setSpacing(12)

        self.test_btn = QPushButton("  ▷ 测试连接")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px 14px;
                color: #374151;
                font-size: 12px;
            }
            QPushButton:hover {
                border-color: #3b82f6;
                color: #3b82f6;
            }
        """)
        action_layout.addWidget(self.test_btn)

        self.status_label = CaptionLabel("未配置")
        self.status_label.setStyleSheet("color: #6B7280; background: transparent;")
        action_layout.addWidget(self.status_label)

        action_layout.addStretch()

        self.save_btn = QPushButton("  💾 保存")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
        """)
        action_layout.addWidget(self.save_btn)

        self._add_widget(action_bar)

        # ── Connect signals ──
        self.test_btn.clicked.connect(self._on_test_clicked)
        self.save_btn.clicked.connect(self._on_save_clicked)

    def get_key(self) -> str:
        return self.key_input.text()

    def get_url(self) -> str:
        return self.url_input.text()

    def get_model(self) -> str:
        return self.model_input.text()

    def _on_test_clicked(self):
        """测试连接按钮点击处理"""
        api_key = self.get_key().strip()
        base_url = self.get_url().strip()
        model = self.get_model()

        if not api_key:
            self._set_status("❌ 请输入 API Key", "#EF4444")
            return

        if not base_url:
            self._set_status("❌ 请输入 Base URL", "#EF4444")
            return

        # 禁用按钮，防止重复点击
        self.test_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self._set_status("测试中...", "#F59E0B")

        # 启动异步测试（自定义模型使用 openai 兼容接口）
        self._worker = _TestConnectionWorker("custom", api_key, base_url, model)
        self._worker.finished.connect(self._on_test_finished)
        self._worker.start()

    def _on_test_finished(self, success: bool, error_msg: str, latency_ms: int):
        """测试连接完成回调"""
        self.test_btn.setEnabled(True)
        self.save_btn.setEnabled(True)

        if success:
            self._set_status(f"✅ 连接成功 ({latency_ms}ms)", "#10B981")
        else:
            self._set_status(f"❌ 连接失败: {error_msg[:30]}", "#EF4444")

        # 3秒后恢复状态
        self._status_timer.start(3000)

    def _on_save_clicked(self):
        """保存按钮点击处理"""
        api_key = self.get_key().strip()
        base_url = self.get_url().strip()
        model = self.get_model()

        if not api_key:
            self._set_status("❌ 请输入 API Key", "#EF4444")
            return

        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()

            store.update_custom(api_key=api_key, base_url=base_url, model=model)
            store.save()

            self._set_status("保存成功 ✓", "#10B981")

            # 3秒后恢复状态
            self._status_timer.start(3000)

        except Exception as e:
            self._set_status(f"❌ 保存失败: {str(e)[:30]}", "#EF4444")

    def _set_status(self, text: str, color: str):
        """设置状态标签文本和颜色"""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; background: transparent;")

    def _restore_status(self):
        """恢复状态标签为已配置/未配置"""
        if self.get_key().strip():
            self._set_status("已配置", "#6B7280")
        else:
            self._set_status("未配置", "#6B7280")


# ── Work Mode Card ────────────────────────────────────────────────────

class _WorkModeCard(VerticalFormCard):
    """工作模式选择 - 下拉框"""

    def __init__(self, parent=None):
        super().__init__(
            FluentIcon.TILES, "工作模式", "选择 AI 工作模式", parent,
        )

        self.mode_combo = ComboBox()
        self.mode_combo.setFixedHeight(38)
        self.mode_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.mode_combo.addItems([
            "基础预览 - 无需 API，仅用于演示",
            "DeepSeek 单 AI - 文本抽取 + 策略生成",
            "MiMo 单 AI - 长上下文 / 多模态增强",
            "DeepSeek (主文本) + MiMo (多模态) 双 AI - 推荐",
        ])
        self.mode_combo.setCurrentIndex(0)
        self._add_form_field("AI 工作模式", self.mode_combo)

    def currentMode(self) -> str:
        return self.mode_combo.currentText()


# ── Use Case Card ─────────────────────────────────────────────────────

class _UseCaseCard(VerticalFormCard):
    """使用场景选择"""

    def __init__(self, parent=None):
        super().__init__(
            FluentIcon.CHECKBOX, "使用场景", "选择 MiMo 的应用范围", parent,
        )
        self._checks: dict[str, QCheckBox] = {}

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid_layout = QHBoxLayout(container)
        grid_layout.setSpacing(20)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        for case in ["复核事实", "多模态材料理解", "长上下文复核", "文书质量审校"]:
            cb = QCheckBox(case)
            if case in ("复核事实", "多模态材料理解", "长上下文复核", "文书质量审校"):
                cb.setChecked(True)
            cb.setStyleSheet(_CHECKBOX_STYLE)
            self._checks[case] = cb
            grid_layout.addWidget(cb)

        grid_layout.addStretch()
        self._add_widget(container)

    def get_checks(self) -> dict[str, QCheckBox]:
        return self._checks


# ── Card Group Wrapper ────────────────────────────────────────────────

class _CardGroup(QWidget):
    """Wrap VerticalFormCard with group header for ExpandLayout compatibility"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Group title
        self.title_label = SubtitleLabel(title)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #1F2937;")
        layout.addWidget(self.title_label)

        # Card container
        self.card_container = QWidget()
        self.card_container.setStyleSheet("background: transparent;")
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setSpacing(12)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.card_container)

    def addCard(self, card: QWidget):
        """Add a card to this group."""
        self.card_layout.addWidget(card)


# ── Settings Page ─────────────────────────────────────────────────────

class SettingsPage(QWidget):
    """设置页面 — 极简配置与智能默认"""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self.load_settings()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("settingsScrollWidget")

        layout = QVBoxLayout(content)
        layout.setSpacing(24)
        layout.setContentsMargins(36, 28, 36, 36)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title
        self._titleLabel = QLabel("设置", self)
        self._titleLabel.setObjectName("settingsTitle")
        self._titleLabel.setStyleSheet(
            "font: 33px 'Microsoft YaHei Light'; color: #1F2937; background: transparent;"
        )

        # ── Work Mode Group ──
        mode_group = _CardGroup("基本设置")
        self._mode_card = _WorkModeCard()
        mode_group.addCard(self._mode_card)
        layout.addWidget(mode_group)

        # ── DeepSeek Group ──
        ds_group = _CardGroup("DeepSeek")
        self._ds_card = _ProviderConfigCard(
            FluentIcon.SEND, "DeepSeek",
            default_url="https://api.deepseek.com",
            model_items=["deepseek-v4-flash", "deepseek-v4-pro"],
        )
        # 默认选中 deepseek-v4-flash
        self._ds_card.model_combo.setCurrentIndex(0)
        ds_group.addCard(self._ds_card)
        layout.addWidget(ds_group)

        # ── MiMo Group ──
        mm_group = _CardGroup("MiMo")
        self._mm_card = _ProviderConfigCard(
            FluentIcon.SEND, "MiMo",
            default_url="https://api.mimo.ai/v1",
            model_items=["mimo-v2.5", "mimo-v2.5-pro"],
        )
        # 默认选中 mimo-v2.5
        self._mm_card.model_combo.setCurrentIndex(0)
        mm_group.addCard(self._mm_card)

        # Use case card
        self._mm_usecase_card = _UseCaseCard()
        mm_group.addCard(self._mm_usecase_card)
        layout.addWidget(mm_group)

        # ── Custom Model Group ──
        custom_group = _CardGroup("自定义模型")
        self._custom_card = _CustomModelCard()
        custom_group.addCard(self._custom_card)
        layout.addWidget(custom_group)

        # Stretch at bottom
        layout.addStretch(1)

        # ── Mount ──
        scroll.setWidget(content)
        scroll.setViewportMargins(0, 60, 0, 20)
        root.addWidget(scroll)

    def _connect_signals(self):
        """Connect signals for smart detection."""
        self._mm_card.key_input.textChanged.connect(self._detect_mimo_plan)
        self._mode_card.mode_combo.currentIndexChanged.connect(self._on_work_mode_changed)

    def _detect_mimo_plan(self, text: str):
        """Detect MiMo account type from API key prefix and auto-route Base URL."""
        label = self._mm_card.account_label
        url_input = self._mm_card.url_input
        text = text.strip()

        if text.startswith("tp-"):
            # Token Plan 账户 - 切换到专属网关
            label.setText("  ★ Plan 账户")
            label.setStyleSheet(
                "color: #8B5CF6; font-size: 11px; font-weight: 600; background: transparent;"
            )
            label.setVisible(True)
            url_input.setText("https://token-plan-cn.xiaomimimo.com/v1")
        elif text.startswith("sk-"):
            # 普通按量付费账户
            label.setText("  标准账户")
            label.setStyleSheet("color: #6B7280; font-size: 11px; background: transparent;")
            label.setVisible(True)
            url_input.setText("https://api.mimo.ai/v1")
        else:
            # 为空或其他前缀
            label.setVisible(False)
            if not text:
                url_input.setText("https://api.mimo.ai/v1")

    def _on_work_mode_changed(self, index: int):
        """工作模式切换时自动保存"""
        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()

            # 将下拉框索引映射到工作模式字符串
            mode_map = {
                0: "基础预览",
                1: "DeepSeek单AI",
                2: "MiMo单AI",
                3: "DeepSeek+MiMo双AI",
            }
            mode = mode_map.get(index, "基础预览")
            store.set_work_mode(mode)
            store.save()
            self.settings_changed.emit()
        except Exception:
            pass

    # ── Aliases for backward compatibility ─────────────────────────────

    @property
    def ds_key_input(self):
        return self._ds_card.key_input

    @property
    def ds_url_input(self):
        return self._ds_card.url_input

    @property
    def ds_model_combo(self):
        return self._ds_card.model_combo

    @property
    def mm_key_input(self):
        return self._mm_card.key_input

    @property
    def mm_url_input(self):
        return self._mm_card.url_input

    @property
    def mm_model_combo(self):
        return self._mm_card.model_combo

    @property
    def mm_case_checks(self):
        return self._mm_usecase_card.get_checks()

    @property
    def custom_key_input(self):
        return self._custom_card.key_input

    @property
    def custom_url_input(self):
        return self._custom_card.url_input

    @property
    def custom_model_input(self):
        return self._custom_card.model_input

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_titleLabel'):
            self._titleLabel.move(36, 12)

    # ── Load / Save ───────────────────────────────────────────────────

    def load_settings(self):
        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()
            s = store.settings

            # Mode - 优先使用保存的工作模式
            mode_map = {
                "基础预览": 0,
                "DeepSeek单AI": 1,
                "MiMo单AI": 2,
                "DeepSeek+MiMo双AI": 3,
            }
            idx = mode_map.get(s.work_mode, 0)
            self._mode_card.mode_combo.setCurrentIndex(idx)

            # DeepSeek
            self.ds_key_input.setText(s.deepseek.api_key)
            self.ds_url_input.setText(s.deepseek.base_url)
            idx = self.ds_model_combo.findText(s.deepseek.model_extract)
            if idx >= 0:
                self.ds_model_combo.setCurrentIndex(idx)

            # MiMo
            self.mm_key_input.setText(s.mimo.api_key)
            self.mm_url_input.setText(s.mimo.base_url)
            idx = self.mm_model_combo.findText(s.mimo.model)
            if idx >= 0:
                self.mm_model_combo.setCurrentIndex(idx)
            for case, cb in self.mm_case_checks.items():
                cb.setChecked(case in s.mimo.use_cases)

            # Custom model
            self.custom_key_input.setText(s.custom.api_key)
            self.custom_url_input.setText(s.custom.base_url)
            self.custom_model_input.setText(s.custom.model)

            # Update status labels
            self._update_status_labels()

        except Exception:
            pass

    def _update_status_labels(self):
        """更新所有卡片的状态标签"""
        # DeepSeek
        if self.ds_key_input.text().strip():
            self._ds_card._set_status("已配置", "#6B7280")

        # MiMo
        if self.mm_key_input.text().strip():
            self._mm_card._set_status("已配置", "#6B7280")

        # Custom
        if self.custom_key_input.text().strip():
            self._custom_card._set_status("已配置", "#6B7280")

    def get_settings_dict(self) -> dict:
        """Get current settings as dict."""
        return {
            "work_mode": self._mode_card.mode_combo.currentIndex(),
            "deepseek": {
                "api_key": self.ds_key_input.text(),
                "base_url": self.ds_url_input.text(),
                "model": self.ds_model_combo.currentText(),
            },
            "mimo": {
                "api_key": self.mm_key_input.text(),
                "base_url": self.mm_url_input.text(),
                "model": self.mm_model_combo.currentText(),
                "use_cases": [c for c, cb in self.mm_case_checks.items() if cb.isChecked()],
            },
            "custom": {
                "api_key": self.custom_key_input.text(),
                "base_url": self.custom_url_input.text(),
                "model": self.custom_model_input.text(),
            },
        }
