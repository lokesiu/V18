"""
app/widgets/settings_page.py - AI Settings Page

Settings page for configuring DeepSeek and MiMo AI providers.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QCheckBox,
    QSizePolicy,
)

from qfluentwidgets import (
    HeaderCardWidget, SubtitleLabel, BodyLabel, CaptionLabel,
    PrimaryPushButton, PushButton, FluentIcon, InfoBar,
    RadioButton
)


# ---------------------------------------------------------------------------
# Style constants — unified with main theme
# ---------------------------------------------------------------------------

_INPUT = """
    QLineEdit {
        background-color: #18181e; color: #e0e0e0;
        border: 1px solid #2a2a32; border-radius: 6px;
        padding: 8px 12px; font-size: 13px;
        selection-background-color: #3b82f6; selection-color: #ffffff;
    }
    QLineEdit:focus { border: 1px solid #3b82f6; }
    QLineEdit:disabled { background-color: #141418; color: #505058; }
"""

_COMBO = """
    QComboBox {
        background-color: #18181e; color: #e0e0e0;
        border: 1px solid #2a2a32; border-radius: 6px;
        padding: 8px 12px; font-size: 13px;
    }
    QComboBox:focus { border: 1px solid #3b82f6; }
    QComboBox::drop-down {
        subcontrol-origin: padding; subcontrol-position: center right;
        width: 28px; border: none;
    }
    QComboBox QAbstractItemView {
        background-color: #1c1c22; color: #e0e0e0;
        border: 1px solid #2a2a32;
        selection-background-color: #3b82f6; selection-color: #ffffff;
    }
"""

_BTN = """
    PushButton {
        background-color: #2a2a32; color: #d0d0d8;
        border: 1px solid #3a3a42; border-radius: 6px;
        padding: 8px 16px; font-size: 13px;
    }
    PushButton:hover { border: 1px solid #3b82f6; color: #3b82f6; }
    PushButton:disabled { background-color: #1c1c22; color: #505058; border: 1px solid #2a2a32; }
"""

_SAVE = """
    PrimaryPushButton {
        background-color: #3b82f6; color: #ffffff;
        border: none; border-radius: 6px;
        padding: 8px 20px; font-size: 13px; font-weight: bold;
    }
    PrimaryPushButton:hover { background-color: #5b9aff; }
    PrimaryPushButton:disabled { background-color: #2a2a32; color: #505058; }
"""

_CARD = """
    HeaderCardWidget {
        background-color: #1c1c22; border: 1px solid #2a2a32; border-radius: 8px;
    }
"""

_LABEL = "BodyLabel { color: #b0b0b8; font-size: 13px; }"
_CAPTION = "CaptionLabel { color: #707078; font-size: 12px; }"


class SettingsPage(QWidget):
    """AI Settings page with DeepSeek and MiMo configuration."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        self._mode_radios = []
        layout.addWidget(self._create_work_mode_section())
        layout.addWidget(self._create_deepseek_section())
        layout.addWidget(self._create_mimo_section())
        layout.addStretch()

    def _create_work_mode_section(self) -> QWidget:
        card = HeaderCardWidget()
        card.setTitle("工作模式")
        card.setStyleSheet(_CARD)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        modes = [
            ("基础预览", "无需 API，仅用于演示"),
            ("DeepSeek 单 AI", "文本抽取 + 策略生成"),
            ("MiMo 单 AI", "长上下文 / 多模态增强"),
            ("DeepSeek + MiMo 双 AI", "推荐"),
        ]

        for mode_name, desc in modes:
            row = QHBoxLayout()
            radio = RadioButton(mode_name)
            radio.setStyleSheet("color: #e0e0e0; font-size: 13px;")
            radio.toggled.connect(lambda checked, r=radio: self._on_mode_changed(r) if checked else None)
            self._mode_radios.append(radio)
            row.addWidget(radio)
            label = CaptionLabel(desc)
            label.setStyleSheet(_CAPTION)
            row.addWidget(label)
            row.addStretch()
            layout.addLayout(row)

        if self._mode_radios:
            self._mode_radios[0].setChecked(True)
        return card

    def _on_mode_changed(self, radio):
        pass

    def _create_deepseek_section(self) -> QWidget:
        card = HeaderCardWidget()
        card.setTitle("DeepSeek")
        card.setStyleSheet(_CARD)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        for field_name, placeholder, attr in [
            ("API Key", "sk-...", "ds_key_input"),
            ("Base URL", "https://api.deepseek.com", "ds_url_input"),
        ]:
            lbl = BodyLabel(field_name)
            lbl.setStyleSheet(_LABEL)
            layout.addWidget(lbl)
            inp = QLineEdit()
            inp.setEchoMode(QLineEdit.EchoMode.Password) if "key" in attr.lower() else None
            inp.setPlaceholderText(placeholder)
            if attr == "ds_url_input":
                inp.setText(placeholder)
            inp.setStyleSheet(_INPUT)
            setattr(self, attr, inp)
            layout.addWidget(inp)

        for field_name, items, attr in [
            ("抽取模型", ["deepseek-chat", "deepseek-v4-flash", "deepseek-reasoner"], "ds_extract_combo"),
            ("策略模型", ["deepseek-chat", "deepseek-v4-pro", "deepseek-reasoner"], "ds_strategy_combo"),
        ]:
            lbl = BodyLabel(field_name)
            lbl.setStyleSheet(_LABEL)
            layout.addWidget(lbl)
            combo = QComboBox()
            combo.addItems(items)
            combo.setStyleSheet(_COMBO)
            setattr(self, attr, combo)
            layout.addWidget(combo)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.ds_test_btn = PushButton("测试连接")
        self.ds_test_btn.setIcon(FluentIcon.PLAY)
        self.ds_test_btn.setStyleSheet(_BTN)
        self.ds_test_btn.clicked.connect(self._test_deepseek)
        btn_layout.addWidget(self.ds_test_btn)

        self.ds_status_label = CaptionLabel("未配置")
        self.ds_status_label.setStyleSheet(_CAPTION)
        btn_layout.addWidget(self.ds_status_label)
        btn_layout.addStretch()

        self.ds_save_btn = PrimaryPushButton("保存")
        self.ds_save_btn.setIcon(FluentIcon.SAVE)
        self.ds_save_btn.setStyleSheet(_SAVE)
        self.ds_save_btn.clicked.connect(self._save_deepseek)
        btn_layout.addWidget(self.ds_save_btn)

        layout.addLayout(btn_layout)
        return card

    def _create_mimo_section(self) -> QWidget:
        card = HeaderCardWidget()
        card.setTitle("MiMo")
        card.setStyleSheet(_CARD)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        for field_name, placeholder, attr in [
            ("API Key", "sk-...", "mm_key_input"),
            ("Base URL", "https://api.mimo.ai", "mm_url_input"),
        ]:
            lbl = BodyLabel(field_name)
            lbl.setStyleSheet(_LABEL)
            layout.addWidget(lbl)
            inp = QLineEdit()
            inp.setEchoMode(QLineEdit.EchoMode.Password) if "key" in attr.lower() else None
            inp.setPlaceholderText(placeholder)
            if attr == "mm_url_input":
                inp.setText(placeholder)
            inp.setStyleSheet(_INPUT)
            setattr(self, attr, inp)
            layout.addWidget(inp)

        lbl = BodyLabel("模型")
        lbl.setStyleSheet(_LABEL)
        layout.addWidget(lbl)
        self.mm_model_combo = QComboBox()
        self.mm_model_combo.addItems(["mimo-v2.5-pro", "mimo-v2.5", "mimo-v2-omni", "mimo-v2-flash"])
        self.mm_model_combo.setStyleSheet(_COMBO)
        layout.addWidget(self.mm_model_combo)

        lbl = BodyLabel("使用场景")
        lbl.setStyleSheet(_LABEL)
        layout.addWidget(lbl)
        cases_layout = QHBoxLayout()
        cases_layout.setSpacing(16)
        self.mm_case_checks = {}
        for case in ["复核事实", "多模态材料理解", "长上下文复核", "文书质量审校"]:
            cb = QCheckBox(case)
            cb.setStyleSheet("color: #e0e0e0; font-size: 13px; spacing: 6px;")
            if case in ("复核事实", "长上下文复核", "文书质量审校"):
                cb.setChecked(True)
            self.mm_case_checks[case] = cb
            cases_layout.addWidget(cb)
        cases_layout.addStretch()
        layout.addLayout(cases_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.mm_test_btn = PushButton("测试连接")
        self.mm_test_btn.setIcon(FluentIcon.PLAY)
        self.mm_test_btn.setStyleSheet(_BTN)
        self.mm_test_btn.clicked.connect(self._test_mimo)
        btn_layout.addWidget(self.mm_test_btn)

        self.mm_status_label = CaptionLabel("未配置")
        self.mm_status_label.setStyleSheet(_CAPTION)
        btn_layout.addWidget(self.mm_status_label)
        btn_layout.addStretch()

        self.mm_save_btn = PrimaryPushButton("保存")
        self.mm_save_btn.setIcon(FluentIcon.SAVE)
        self.mm_save_btn.setStyleSheet(_SAVE)
        self.mm_save_btn.clicked.connect(self._save_mimo)
        btn_layout.addWidget(self.mm_save_btn)

        layout.addLayout(btn_layout)
        return card

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load_settings(self):
        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()
            s = store.settings
            self.ds_key_input.setText(s.deepseek.api_key)
            self.ds_url_input.setText(s.deepseek.base_url)
            idx = self.ds_extract_combo.findText(s.deepseek.model_extract)
            if idx >= 0:
                self.ds_extract_combo.setCurrentIndex(idx)
            idx = self.ds_strategy_combo.findText(s.deepseek.model_strategy)
            if idx >= 0:
                self.ds_strategy_combo.setCurrentIndex(idx)
            self.mm_key_input.setText(s.mimo.api_key)
            self.mm_url_input.setText(s.mimo.base_url)
            idx = self.mm_model_combo.findText(s.mimo.model)
            if idx >= 0:
                self.mm_model_combo.setCurrentIndex(idx)
            for case, cb in self.mm_case_checks.items():
                cb.setChecked(case in s.mimo.use_cases)
            self.ds_status_label.setText("已配置" if s.deepseek.is_configured() else "未配置")
            self.mm_status_label.setText("已配置" if s.mimo.is_configured() else "未配置")
        except Exception:
            pass

    def _save_deepseek(self):
        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()
            store.update_deepseek(
                api_key=self.ds_key_input.text(),
                base_url=self.ds_url_input.text(),
                model_extract=self.ds_extract_combo.currentText(),
                model_strategy=self.ds_strategy_combo.currentText(),
            )
            store.save()
            self.ds_status_label.setText("已保存")
            self.ds_status_label.setStyleSheet("color: #22c55e; font-size: 12px;")
            InfoBar.success("保存成功", "DeepSeek 设置已保存", parent=self.window())
            self.settings_changed.emit()
        except Exception as e:
            self.ds_status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
            InfoBar.error("保存失败", str(e), parent=self.window())

    def _save_mimo(self):
        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()
            use_cases = [case for case, cb in self.mm_case_checks.items() if cb.isChecked()]
            store.update_mimo(
                api_key=self.mm_key_input.text(),
                base_url=self.mm_url_input.text(),
                model=self.mm_model_combo.currentText(),
                use_cases=use_cases,
            )
            store.save()
            self.mm_status_label.setText("已保存")
            self.mm_status_label.setStyleSheet("color: #22c55e; font-size: 12px;")
            InfoBar.success("保存成功", "MiMo 设置已保存", parent=self.window())
            self.settings_changed.emit()
        except Exception as e:
            self.mm_status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
            InfoBar.error("保存失败", str(e), parent=self.window())

    # ------------------------------------------------------------------
    # Test connections
    # ------------------------------------------------------------------

    def _test_deepseek(self):
        self.ds_test_btn.setEnabled(False)
        self.ds_status_label.setText("测试中...")
        self.ds_status_label.setStyleSheet("color: #3b82f6; font-size: 12px;")
        try:
            from core.ai.deepseek_client import DeepSeekClient
            client = DeepSeekClient(
                api_key=self.ds_key_input.text(),
                base_url=self.ds_url_input.text(),
            )
            resp = client.test_connection()
            if resp.success:
                self.ds_status_label.setText(f"可用 ({resp.latency_ms}ms)")
                self.ds_status_label.setStyleSheet("color: #22c55e; font-size: 12px;")
            else:
                self.ds_status_label.setText(f"失败: {resp.error}")
                self.ds_status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        except Exception as e:
            self.ds_status_label.setText(f"错误: {e}")
            self.ds_status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        finally:
            self.ds_test_btn.setEnabled(True)

    def _test_mimo(self):
        self.mm_test_btn.setEnabled(False)
        self.mm_status_label.setText("测试中...")
        self.mm_status_label.setStyleSheet("color: #3b82f6; font-size: 12px;")
        try:
            from core.ai.mimo_client import MiMoClient
            client = MiMoClient(
                api_key=self.mm_key_input.text(),
                base_url=self.mm_url_input.text(),
                model=self.mm_model_combo.currentText(),
            )
            resp = client.test_connection()
            if resp.success:
                self.mm_status_label.setText(f"可用 ({resp.latency_ms}ms)")
                self.mm_status_label.setStyleSheet("color: #22c55e; font-size: 12px;")
            else:
                self.mm_status_label.setText(f"失败: {resp.error}")
                self.mm_status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        except Exception as e:
            self.mm_status_label.setText(f"错误: {e}")
            self.mm_status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        finally:
            self.mm_test_btn.setEnabled(True)
