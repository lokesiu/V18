"""Inline notice widget for error/warning/info states."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy

from qfluentwidgets import PushButton, FluentIcon


# Theme tokens - Light theme (no more black backgrounds)
_STYLES = {
    "error": {
        "bg": "#FEF2F2",
        "border": "#FECACA",
        "text": "#DC2626",
        "muted": "#991B1B",
    },
    "warning": {
        "bg": "#FFFBEB",
        "border": "#FDE68A",
        "text": "#D97706",
        "muted": "#92400E",
    },
    "info": {
        "bg": "#EFF6FF",
        "border": "#BFDBFE",
        "text": "#2563EB",
        "muted": "#1E40AF",
    },
}


class InlineNotice(QWidget):
    """Compact inline notice for error/warning/info states.

    Structure:
        [icon] title
               description
               [action button]
    """

    action_clicked = Signal()

    def __init__(
        self,
        kind: str = "info",
        title: str = "",
        description: str = "",
        action_text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._kind = kind
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._build(kind, title, description, action_text)
        self.setVisible(False)

    def _build(self, kind: str, title: str, desc: str, action_text: str):
        s = _STYLES.get(kind, _STYLES["info"])

        self.setStyleSheet(
            f"background-color: {s['bg']}; "
            f"border: 1px solid {s['border']}; "
            f"border-radius: 6px;"
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        # Icon column
        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        icon_label.setStyleSheet(f"color: {s['text']}; font-size: 16px; font-weight: bold;")
        icons = {"error": "✕", "warning": "!", "info": "i"}
        icon_label.setText(icons.get(kind, "i"))
        root.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        self._title_label = QLabel(title)
        self._title_label.setWordWrap(True)
        self._title_label.setStyleSheet(
            f"color: {s['text']}; font-size: 13px; font-weight: 600; border: none; background: transparent;"
        )
        text_col.addWidget(self._title_label)

        self._desc_label = QLabel(desc)
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet(
            f"color: {s['muted']}; font-size: 12px; border: none; background: transparent;"
        )
        if desc:
            text_col.addWidget(self._desc_label)
        else:
            self._desc_label.setVisible(False)

        if action_text:
            self._action_btn = PushButton(action_text)
            self._action_btn.setStyleSheet(
                f"QPushButton {{ background-color: {s['border']}; color: {s['text']}; "
                f"border: none; border-radius: 4px; padding: 4px 12px; font-size: 12px; }}"
                f"QPushButton:hover {{ background-color: {s['text']}; color: #ffffff; }}"
            )
            self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._action_btn.clicked.connect(self.action_clicked.emit)
            text_col.addWidget(self._action_btn, 0, Qt.AlignmentFlag.AlignLeft)
        else:
            self._action_btn = None

        root.addLayout(text_col, 1)

    def show_notice(self, title: str = "", description: str = "", action_text: str = ""):
        """Update content and show."""
        if title:
            self._title_label.setText(title)
        if description:
            self._desc_label.setText(description)
            self._desc_label.setVisible(True)
        if action_text and self._action_btn is not None:
            self._action_btn.setText(action_text)
        self.setVisible(True)

    def hide_notice(self):
        self.setVisible(False)

    def update_kind(self, kind: str):
        """Change the notice kind (error/warning/info) and restyle."""
        s = _STYLES.get(kind, _STYLES["info"])
        self.setStyleSheet(
            f"background-color: {s['bg']}; "
            f"border: 1px solid {s['border']}; "
            f"border-radius: 6px;"
        )
        icons = {"error": "✕", "warning": "!", "info": "i"}
        # Update icon
        for child in self.findChildren(QLabel):
            if child.width() == 20 and child.height() == 20:
                child.setText(icons.get(kind, "i"))
                child.setStyleSheet(f"color: {s['text']}; font-size: 16px; font-weight: bold; border: none; background: transparent;")
                break
        self._title_label.setStyleSheet(
            f"color: {s['text']}; font-size: 13px; font-weight: 600; border: none; background: transparent;"
        )
        self._desc_label.setStyleSheet(
            f"color: {s['muted']}; font-size: 12px; border: none; background: transparent;"
        )
