"""AI Status Card Widget — compact status indicator."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout

from qfluentwidgets import InfoBadge, BodyLabel


class AiStatusCard(QWidget):
    """Compact AI status indicator."""

    STATUS_CONFIG = {
        "未配置": ("未配置", QColor(112, 112, 120)),
        "deepseek": ("DeepSeek", QColor(59, 130, 246)),
        "mimo": ("MiMo", QColor(139, 92, 246)),
        "dual": ("双 AI", QColor(34, 197, 94)),
        "preview": ("预览模式", QColor(234, 179, 8)),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.set_status("未配置")

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.badge = InfoBadge("")
        layout.addWidget(self.badge)

        self.label = BodyLabel("")
        self.label.setStyleSheet("color: #707078; font-size: 12px;")
        layout.addWidget(self.label)
        layout.addStretch()

    def set_status(self, mode: str):
        text, color = self.STATUS_CONFIG.get(mode, self.STATUS_CONFIG["未配置"])
        self.label.setText(text)
        self.badge.setText(mode)
        self.badge.setCustomBackgroundColor(color, color)

    def update_from_settings(self):
        try:
            from core.settings_store import get_settings_store
            store = get_settings_store()
            label = store.get_status_label()

            if "双 AI" in label:
                self.set_status("dual")
            elif "DeepSeek" in label:
                self.set_status("deepseek")
            elif "MiMo" in label:
                self.set_status("mimo")
            elif "基础预览" in label:
                self.set_status("preview")
            else:
                self.set_status("未配置")
        except Exception:
            self.set_status("未配置")
