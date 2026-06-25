"""app/pages/settings_page.py — 设置页面 (主流 AI 产品风格).

设计参考 Dify / Cursor / Claude Desktop:
  - 字段平铺,无"高级设置"折叠 — 用户一眼看完所有可配置项
  - 输入即保存 (debounce 800ms),不打断用户
  - 保存即自动测,右上角状态徽章实时更新
  - 模型下拉可编辑,既能选预设也能输自定义值
  - 工作模式 Segmented Control 4 段切换,不用下拉

不再包含:
  - License Key 生成器(注册机) — 这是销售工具,通过 launch_keygen.py 独立运行
  - "使用场景" 4 个 checkbox — 多余,反正 MiMo 配了就是全场景
  - "测试" + "保存" 两段式按钮 — 改自动
  - "高级设置" 折叠 — 全部字段默认展开
"""
from __future__ import annotations

import time

from PySide6.QtCore import Signal, Qt, QThread, QTimer, QSize
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QComboBox,
    QLabel, QFrame, QSizePolicy, QPushButton, QButtonGroup,
)
from PySide6.QtGui import QIcon

from qfluentwidgets import (
    SettingCardGroup, ExpandLayout, ScrollArea, FluentIcon,
    CaptionLabel, BodyLabel, StrongBodyLabel, SubtitleLabel,
    InfoBar, EditableComboBox, ToolButton, HyperlinkLabel,
)


# ── 状态徽章颜色 ────────────────────────────────────────────────────────

_STATUS_COLORS = {
    "unconfigured": ("#9CA3AF", "未配置"),
    "testing": ("#F59E0B", "测试中…"),
    "ok": ("#10B981", "已连接"),
    "fail": ("#EF4444", "连接失败"),
}


# ── Provider 元数据 ─────────────────────────────────────────────────────

_PROVIDER_META = {
    "deepseek": {
        "name": "DeepSeek",
        "default_url": "https://api.deepseek.com",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat"],
        "apply_url": "https://platform.deepseek.com/api_keys",
        "desc": "国产高质量文本模型,适合法律文书抽取与策略生成。",
    },
    "mimo": {
        "name": "MiMo",
        "default_url": "https://api.mimo.ai/v1",
        "models": ["mimo-v2.5", "mimo-v2.5-pro", "mimo-v2.5-tts"],
        "apply_url": "https://api.mimo.ai/",
        "desc": "小米大模型,擅长长上下文与多模态,可作主控/复核/语音。",
    },
    "custom": {
        "name": "自定义 OpenAI 兼容",
        "default_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "deepseek-chat"],
        "apply_url": "",
        "desc": "任何 OpenAI 兼容接口的第三方模型(本地 LLM、其他云厂商等)。",
    },
}


# ── 异步测试 Worker ────────────────────────────────────────────────────

class _TestWorker(QThread):
    """异步测试 API 连接的工作线程."""

    finished = Signal(str, bool, str, int)  # provider, success, error_msg, latency_ms

    def __init__(self, provider: str, api_key: str, base_url: str, model: str):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _build_url(self) -> str:
        base = (self.base_url or "").rstrip("/")
        if not base:
            return ""
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    def run(self):
        import httpx

        url = self._build_url()
        if not url:
            self.finished.emit(self.provider, False, "Base URL 为空", 0)
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model or "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }

        start = time.time()
        try:
            with httpx.Client(timeout=20) as client:
                resp = client.post(url, json=payload, headers=headers)
            latency = int((time.time() - start) * 1000)

            if self._cancelled:
                return

            if resp.status_code == 200:
                data = resp.json()
                if "choices" in data:
                    self.finished.emit(self.provider, True, "", latency)
                else:
                    self.finished.emit(self.provider, False, "响应格式异常", latency)
            elif resp.status_code == 401:
                self.finished.emit(self.provider, False, "API Key 无效", latency)
            elif resp.status_code == 403:
                self.finished.emit(self.provider, False, "无权访问(403)", latency)
            elif resp.status_code == 404:
                self.finished.emit(self.provider, False, "模型不存在(404)", latency)
            elif resp.status_code == 429:
                self.finished.emit(self.provider, False, "请求过快(429)", latency)
            else:
                try:
                    err = resp.json().get("error", {}).get("message", "")
                except Exception:
                    err = resp.text[:100]
                self.finished.emit(self.provider, False, f"HTTP {resp.status_code}: {err[:40]}", latency)

        except httpx.TimeoutException:
            self.finished.emit(self.provider, False, "请求超时", int((time.time() - start) * 1000))
        except Exception as e:
            self.finished.emit(self.provider, False, str(e)[:50], int((time.time() - start) * 1000))


# ── 状态徽章组件 ────────────────────────────────────────────────────────

class _StatusBadge(QWidget):
    """右上角的小圆点 + 文字状态徽章."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)
        self._dot.setStyleSheet(
            "background-color: #9CA3AF; border-radius: 4px; border: none;"
        )
        layout.addWidget(self._dot)

        self._text = CaptionLabel("未配置")
        self._text.setStyleSheet("color: #6B7280; font-size: 12px; background: transparent;")
        layout.addWidget(self._text)

        self._latency = CaptionLabel("")
        self._latency.setStyleSheet("color: #9CA3AF; font-size: 11px; background: transparent;")
        layout.addWidget(self._latency)

    def set_state(self, state: str, latency_ms: int = 0):
        color, text = _STATUS_COLORS.get(state, _STATUS_COLORS["unconfigured"])
        self._dot.setStyleSheet(
            f"background-color: {color}; border-radius: 4px; border: none;"
        )
        self._text.setText(text)
        self._text.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 500; background: transparent;")

        if state == "ok" and latency_ms > 0:
            self._latency.setText(f"· {latency_ms}ms")
            self._latency.setStyleSheet("color: #9CA3AF; font-size: 11px; background: transparent;")
        elif state == "fail":
            self._latency.setText("")
        else:
            self._latency.setText("")


# ── Provider 配置卡 (平铺) ─────────────────────────────────────────────

class _ProviderCard(QFrame):
    """单个 AI Provider 的配置卡 — 字段全部平铺,无折叠."""

    api_key_changed = Signal(str, str)   # provider, new_key
    url_changed = Signal(str, str)
    model_changed = Signal(str, str)

    def __init__(self, provider: str, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.meta = _PROVIDER_META[provider]

        self.setObjectName(f"ProviderCard_{provider}")
        self.setStyleSheet(f"""
            QFrame#{self.objectName()} {{
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
            }}
        """)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(800)
        self._save_timer.timeout.connect(self._do_save)

        self._worker: _TestWorker | None = None
        self._last_tested = {"latency": 0, "error": ""}
        self._is_loading_settings = False  # 防止 load_settings 触发自动保存

        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(14)

        # ── Header: provider 名 + 状态徽章 ──
        header = QHBoxLayout()
        header.setSpacing(8)

        name_label = StrongBodyLabel(self.meta["name"])
        name_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #111827; background: transparent;")
        header.addWidget(name_label)

        if self.meta.get("apply_url"):
            apply_btn = HyperlinkLabel(self.meta["apply_url"], "🔗 申请 Key")
            apply_btn.setUrl(self.meta["apply_url"])
            header.addSpacing(8)
            header.addWidget(apply_btn)

        header.addStretch()

        self.badge = _StatusBadge()
        header.addWidget(self.badge)
        layout.addLayout(header)

        # ── 描述 ──
        desc = CaptionLabel(self.meta["desc"])
        desc.setStyleSheet("color: #6B7280; font-size: 12px; background: transparent;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── API Key 行 ──
        key_row = QHBoxLayout()
        key_row.setSpacing(8)

        key_col = QVBoxLayout()
        key_col.setSpacing(4)
        key_col.addWidget(self._field_label("API Key"))
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-... (粘贴你的 API Key)")
        self.key_input.setFixedHeight(36)
        self.key_input.setStyleSheet(self._input_style())
        key_col.addWidget(self.key_input)
        key_row.addLayout(key_col, 1)

        # 眼睛按钮
        self.eye_btn = ToolButton(FluentIcon.VIEW)
        self.eye_btn.setFixedSize(36, 36)
        self.eye_btn.setToolTip("显示/隐藏 Key")
        self.eye_btn.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self.eye_btn, 0, Qt.AlignmentFlag.AlignBottom)

        layout.addLayout(key_row)

        # ── Base URL 行 ──
        layout.addWidget(self._field_label("Base URL"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(self.meta["default_url"])
        self.url_input.setText(self.meta["default_url"])
        self.url_input.setFixedHeight(36)
        self.url_input.setStyleSheet(self._input_style())
        layout.addWidget(self.url_input)

        # ── 模型 行 ──
        layout.addWidget(self._field_label("模型"))
        self.model_combo = EditableComboBox()
        self.model_combo.addItems(self.meta["models"])
        self.model_combo.setFixedHeight(36)
        self.model_combo.setStyleSheet(self._input_style())
        layout.addWidget(self.model_combo)

        # ── Connect signals ──
        self.key_input.textChanged.connect(self._on_field_changed)
        self.url_input.textChanged.connect(self._on_field_changed)
        self.model_combo.currentTextChanged.connect(self._on_field_changed)

    def _field_label(self, text: str) -> QLabel:
        lbl = CaptionLabel(text)
        lbl.setStyleSheet("color: #374151; font-size: 12px; font-weight: 500; background: transparent;")
        return lbl

    def _input_style(self) -> str:
        return """
            QLineEdit, QComboBox {
                padding: 0 12px;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                background-color: #FFFFFF;
                color: #1F2937;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #3B82F6;
            }
            QLineEdit:hover, QComboBox:hover {
                border-color: #9CA3AF;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """

    def _toggle_key_visibility(self):
        if self.key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.eye_btn.setIcon(FluentIcon.HIDE)
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.eye_btn.setIcon(FluentIcon.VIEW)

    def _on_field_changed(self, *_):
        if self._is_loading_settings:
            return
        self._save_timer.start()  # debounce 800ms

    def _do_save(self):
        """800ms debounce 后保存到 store + 触发测试."""
        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()

            api_key = self.key_input.text().strip()
            base_url = self.url_input.text().strip() or self.meta["default_url"]
            model = self.model_combo.currentText().strip()

            if self.provider == "deepseek":
                store.update_deepseek(api_key=api_key, base_url=base_url, model_extract=model)
            elif self.provider == "mimo":
                store.update_mimo(api_key=api_key, base_url=base_url, model=model)
            elif self.provider == "custom":
                store.update_custom(api_key=api_key, base_url=base_url, model=model)
            store.save()

            self.api_key_changed.emit(self.provider, api_key)
            self.url_changed.emit(self.provider, base_url)
            self.model_changed.emit(self.provider, model)

            # 触发自动测试
            if api_key and base_url and model:
                self._start_test(api_key, base_url, model)
            else:
                self.badge.set_state("unconfigured")
        except Exception:
            pass

    def _start_test(self, api_key: str, base_url: str, model: str):
        # 取消上一个测试
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(50)

        self.badge.set_state("testing")
        self._worker = _TestWorker(self.provider, api_key, base_url, model)
        self._worker.finished.connect(self._on_test_done)
        self._worker.start()

    def _on_test_done(self, provider: str, success: bool, error_msg: str, latency_ms: int):
        if provider != self.provider:
            return
        self._last_tested = {"latency": latency_ms, "error": error_msg}
        if success:
            self.badge.set_state("ok", latency_ms)
        else:
            self.badge.set_state("fail")
            self.badge._text.setText(f"失败:{error_msg[:24]}")
            self.badge._text.setStyleSheet(
                "color: #EF4444; font-size: 12px; font-weight: 500; background: transparent;"
            )

    # ── 公开 API ──

    def load_values(self, api_key: str, base_url: str, model: str):
        """从 store 加载值到 UI (不触发自动保存)."""
        self._is_loading_settings = True
        try:
            self.key_input.setText(api_key or "")
            self.url_input.setText(base_url or self.meta["default_url"])
            if model:
                # EditableComboBox: 优先 setCurrentText,找不到再 setText(自定义值)
                idx = self.model_combo.findText(model)
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)
                else:
                    self.model_combo.setText(model)
            # 初始状态
            if api_key and base_url and model:
                self.badge.set_state("testing")
                self._start_test(api_key, base_url, model)
            else:
                self.badge.set_state("unconfigured")
        finally:
            self._is_loading_settings = False

    def retest(self):
        """外部触发重新测试."""
        api_key = self.key_input.text().strip()
        base_url = self.url_input.text().strip() or self.meta["default_url"]
        model = self.model_combo.currentText().strip()
        if api_key and base_url and model:
            self._start_test(api_key, base_url, model)


# ── 工作模式卡 ──

class _WorkModeCard(QFrame):
    """工作模式选择 — Segmented Control 风格."""

    mode_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WorkModeCard")
        self.setStyleSheet("""
            QFrame#WorkModeCard {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(12)

        title = StrongBodyLabel("工作模式")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #111827; background: transparent;")
        layout.addWidget(title)

        # 4 个 Segmented 选项
        seg_row = QHBoxLayout()
        seg_row.setSpacing(0)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        self._modes = [
            ("basic", "基础预览", "无需 API,只能演示界面"),
            ("deepseek", "DeepSeek", "单 AI · 文本抽取+策略"),
            ("mimo", "MiMo", "单 AI · 长上下文/多模态"),
            ("dual", "双 AI 协作", "DeepSeek + MiMo · 推荐"),
        ]
        self._buttons: dict[str, QPushButton] = {}

        for i, (key, label, _) in enumerate(self._modes):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._seg_style())
            self._group.addButton(btn, i)
            self._buttons[key] = btn
            seg_row.addWidget(btn)
            if i < len(self._modes) - 1:
                # 加个细分隔(让分段更明显)
                pass

        layout.addLayout(seg_row)

        # 说明文字
        self._desc_label = CaptionLabel("")
        self._desc_label.setStyleSheet("color: #6B7280; font-size: 12px; background: transparent;")
        self._desc_label.setWordWrap(True)
        layout.addWidget(self._desc_label)

        self._group.idClicked.connect(self._on_id_clicked)
        self.set_mode("dual")  # 默认推荐

    def _seg_style(self) -> str:
        return """
            QPushButton {
                background-color: #F3F4F6;
                color: #6B7280;
                border: 1px solid #E5E7EB;
                border-right: none;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:first-child {
                border-top-left-radius: 6px;
                border-bottom-left-radius: 6px;
            }
            QPushButton:last-child {
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                border-right: 1px solid #E5E7EB;
            }
            QPushButton:hover:!checked {
                background-color: #E5E7EB;
                color: #374151;
            }
            QPushButton:checked {
                background-color: #3B82F6;
                color: #FFFFFF;
                border-color: #3B82F6;
                font-weight: 600;
            }
        """

    def _on_id_clicked(self, btn_id: int):
        key, label, desc = self._modes[btn_id]
        self._desc_label.setText(desc)
        self.mode_changed.emit(key)

    def set_mode(self, key: str):
        """根据 key 选中对应段."""
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)
        # 更新说明
        for k, _, desc in self._modes:
            if k == key:
                self._desc_label.setText(desc)
                break

    def current_mode(self) -> str:
        for k, btn in self._buttons.items():
            if btn.isChecked():
                return k
        return "dual"


# ── Footer 工具条 ─────────────────────────────────────────────────────

class _FooterBar(QFrame):
    """底部工具条:测试所有 / 清空所有."""

    def __init__(self, retest_callback, clear_callback, parent=None):
        super().__init__(parent)
        self.setObjectName("FooterBar")
        self.setStyleSheet("""
            QFrame#FooterBar {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(10)

        title = StrongBodyLabel("数据管理")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #111827; background: transparent;")
        layout.addWidget(title)

        layout.addStretch()

        test_all_btn = QPushButton("  ↻  测试所有连接")
        test_all_btn.setFixedHeight(34)
        test_all_btn.setStyleSheet(self._outline_btn_style())
        test_all_btn.clicked.connect(retest_callback)
        layout.addWidget(test_all_btn)

        clear_btn = QPushButton("  ⊘  清空所有配置")
        clear_btn.setFixedHeight(34)
        clear_btn.setStyleSheet(self._danger_btn_style())
        clear_btn.clicked.connect(clear_callback)
        layout.addWidget(clear_btn)

    def _outline_btn_style(self) -> str:
        return """
            QPushButton {
                background: transparent;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 0 14px;
                color: #374151;
                font-size: 13px;
            }
            QPushButton:hover {
                border-color: #3B82F6;
                color: #3B82F6;
            }
        """

    def _danger_btn_style(self) -> str:
        return """
            QPushButton {
                background: transparent;
                border: 1px solid #FCA5A5;
                border-radius: 6px;
                padding: 0 14px;
                color: #DC2626;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
                border-color: #DC2626;
            }
        """


# ── SettingsPage 主类 ──────────────────────────────────────────────────

class SettingsPage(QWidget):
    """设置页面 — 主流 AI 产品风格."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.load_settings()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        layout.setContentsMargins(36, 28, 36, 36)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── 标题 ──
        title = SubtitleLabel("设置")
        title.setStyleSheet(
            "font: 30px 'Microsoft YaHei Light'; color: #111827; "
            "background: transparent; font-weight: 300;"
        )
        layout.addWidget(title)

        subtitle = CaptionLabel("配置 AI 模型和工作模式")
        subtitle.setStyleSheet("color: #6B7280; font-size: 13px; background: transparent;")
        layout.addWidget(subtitle)

        # ── 工作模式 ──
        self._mode_card = _WorkModeCard()
        layout.addWidget(self._mode_card)

        # ── AI 提供商 ──
        self._cards: dict[str, _ProviderCard] = {}
        for key in ("deepseek", "mimo", "custom"):
            card = _ProviderCard(key)
            self._cards[key] = card
            layout.addWidget(card)

        # ── 底部工具条 ──
        footer = _FooterBar(
            retest_callback=self._retest_all,
            clear_callback=self._clear_all,
        )
        layout.addWidget(footer)

        layout.addStretch(1)

        # ── Mount ──
        scroll.setWidget(content)
        scroll.setViewportMargins(0, 12, 0, 12)
        root.addWidget(scroll)

        # ── 信号 ──
        self._mode_card.mode_changed.connect(self._on_mode_changed)
        for card in self._cards.values():
            card.api_key_changed.connect(self._on_provider_field_changed)
            card.url_changed.connect(self._on_provider_field_changed)
            card.model_changed.connect(self._on_provider_field_changed)

    def _on_mode_changed(self, mode_key: str):
        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()
            key_map = {
                "basic": "基础预览",
                "deepseek": "DeepSeek单AI",
                "mimo": "MiMo单AI",
                "dual": "DeepSeek+MiMo双AI",
            }
            store.set_work_mode(key_map.get(mode_key, "基础预览"))
            store.save()
            self.settings_changed.emit()
        except Exception:
            pass

    def _on_provider_field_changed(self, *_):
        self.settings_changed.emit()

    def _retest_all(self):
        for card in self._cards.values():
            card.retest()
        InfoBar.info(
            "正在测试",
            "3 个 provider 并行测试,稍候刷新状态",
            duration=2000,
            parent=self.window(),
        )

    def _clear_all(self):
        from qfluentwidgets import MessageBox
        confirm = MessageBox(
            "清空所有 AI 配置",
            "将清空 DeepSeek / MiMo / 自定义模型的 API Key、Base URL 和模型选择。\n清空后立即生效,可随时重新配置。",
            self.window(),
        )
        if not confirm.exec():
            return

        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()
            store.update_deepseek(api_key="", base_url=_PROVIDER_META["deepseek"]["default_url"], model_extract="")
            store.update_mimo(api_key="", base_url=_PROVIDER_META["mimo"]["default_url"], model="")
            store.update_custom(api_key="", base_url="", model="")
            store.save()
            # 重新加载 UI
            self.load_settings()
            self.settings_changed.emit()
            InfoBar.success("已清空", "所有 AI 配置已重置", duration=2000, parent=self.window())
        except Exception as e:
            InfoBar.error("清空失败", str(e)[:50], parent=self.window())

    # ── Load / Save ──

    def load_settings(self):
        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()
            s = store.settings

            # Mode
            mode_key_map = {
                "基础预览": "basic",
                "DeepSeek单AI": "deepseek",
                "MiMo单AI": "mimo",
                "DeepSeek+MiMo双AI": "dual",
            }
            self._mode_card.set_mode(mode_key_map.get(s.work_mode, "dual"))

            # Providers
            self._cards["deepseek"].load_values(
                s.deepseek.api_key, s.deepseek.base_url, s.deepseek.model_extract,
            )
            self._cards["mimo"].load_values(
                s.mimo.api_key, s.mimo.base_url, s.mimo.model,
            )
            self._cards["custom"].load_values(
                s.custom.api_key, s.custom.base_url, s.custom.model,
            )
        except Exception:
            pass

    # ── 兼容旧代码的 property aliases ──

    @property
    def ds_key_input(self):
        return self._cards["deepseek"].key_input

    @property
    def ds_url_input(self):
        return self._cards["deepseek"].url_input

    @property
    def ds_model_combo(self):
        return self._cards["deepseek"].model_combo

    @property
    def mm_key_input(self):
        return self._cards["mimo"].key_input

    @property
    def mm_url_input(self):
        return self._cards["mimo"].url_input

    @property
    def mm_model_combo(self):
        return self._cards["mimo"].model_combo

    @property
    def custom_key_input(self):
        return self._cards["custom"].key_input

    @property
    def custom_url_input(self):
        return self._cards["custom"].url_input

    @property
    def custom_model_input(self):
        return self._cards["custom"].model_combo

    def get_settings_dict(self) -> dict:
        return {
            "work_mode": self._mode_card.current_mode(),
            "deepseek": {
                "api_key": self._cards["deepseek"].key_input.text(),
                "base_url": self._cards["deepseek"].url_input.text(),
                "model": self._cards["deepseek"].model_combo.currentText(),
            },
            "mimo": {
                "api_key": self._cards["mimo"].key_input.text(),
                "base_url": self._cards["mimo"].url_input.text(),
                "model": self._cards["mimo"].model_combo.currentText(),
            },
            "custom": {
                "api_key": self._cards["custom"].key_input.text(),
                "base_url": self._cards["custom"].url_input.text(),
                "model": self._cards["custom"].model_combo.currentText(),
            },
        }
