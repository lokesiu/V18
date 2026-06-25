"""AI Status Card Widget — compact colored status indicator.

Shows the current AI configuration status as a small colored pill with text.
Designed to sit in a page header without taking much space.

v2 change: previously the badge displayed the raw mode key (e.g. "dual" →
truncated to "qual"), which was visually broken. Now the badge is a fixed
small colored dot, and the label shows the full text in the same color.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from app.style_constants import Colors


class AiStatusCard(QWidget):
    """Compact AI status indicator."""

    # Mode key → (display text, accent color)
    STATUS_CONFIG: dict[str, tuple[str, str]] = {
        "未配置": ("未配置", Colors.GRAY_500),
        "deepseek": ("DeepSeek", Colors.BLUE_500),
        "mimo": ("MiMo", Colors.PURPLE_500),
        "dual": ("双 AI", Colors.GREEN_500),
        "preview": ("预览模式", Colors.AMBER_500),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.set_status("未配置")

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Colored dot (replaces the previous broken InfoBadge)
        self.dot = QLabel()
        self.dot.setFixedSize(QSize(8, 8))
        self.dot.setStyleSheet(
            f"background-color: {Colors.GRAY_400}; border-radius: 4px;"
        )
        layout.addWidget(self.dot, Qt.AlignmentFlag.AlignVCenter)

        self.label = QLabel("")
        self.label.setStyleSheet(
            f"color: {Colors.GRAY_500}; font-size: 12px; font-weight: 500;"
        )
        layout.addWidget(self.label, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()

        # Set a sensible size hint so it doesn't get squeezed in tight headers
        self.setMinimumWidth(80)

    def set_status(self, mode: str) -> None:
        """Update the status display.

        Args:
            mode: One of the keys in STATUS_CONFIG (or any string for fallback).
        """
        text, color = self.STATUS_CONFIG.get(mode, self.STATUS_CONFIG["未配置"])
        self.label.setText(text)
        # Update both dot and label color so they match
        self.dot.setStyleSheet(
            f"background-color: {color}; border-radius: 4px;"
        )
        self.label.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 500;"
        )

    def update_from_settings(self) -> None:
        """Read current AI configuration from settings store and update display."""
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
