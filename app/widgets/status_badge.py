"""Status badge component — compact analysis state indicator."""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QWidget

from qfluentwidgets import InfoBadge


class StatusBadge(QWidget):
    """Status badge showing current analysis state."""

    STATUS_CONFIG = {
        "待分析": ("待分析", QColor(112, 112, 120)),
        "分析中": ("分析中", QColor(59, 130, 246)),
        "已完成": ("已完成", QColor(34, 197, 94)),
        "需人工核对": ("需人工核对", QColor(234, 179, 8)),
        "失败": ("失败", QColor(239, 68, 68)),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.set_status("待分析")

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.badge = InfoBadge("待分析")
        layout.addWidget(self.badge)

    def set_status(self, status: str):
        text, color = self.STATUS_CONFIG.get(
            status, ("待分析", QColor(112, 112, 120))
        )
        self.badge.setText(text)
        self.badge.setCustomBackgroundColor(color, color)
