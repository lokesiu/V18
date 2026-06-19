"""Option card component for V18."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout

from qfluentwidgets import (
    CardWidget, SubtitleLabel, PillPushButton, FluentIcon
)


class OptionCard(CardWidget):
    """Card with pill button options for identity/goal selection."""

    selection_changed = Signal(str)

    def __init__(self, title: str, options: list[str], parent=None):
        super().__init__(parent)
        self.options = options
        self.buttons: list[PillPushButton] = []
        self._current = options[0] if options else ""
        self._setup_ui(title, options)

    def _setup_ui(self, title: str, options: list[str]):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        label = SubtitleLabel(title)
        layout.addWidget(label)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        for option in options:
            btn = PillPushButton(option)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, o=option: self._on_select(o))
            self.buttons.append(btn)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Select first by default
        if self.buttons:
            self.buttons[0].setChecked(True)

    def _on_select(self, option: str):
        """Handle option selection."""
        self._current = option
        for btn in self.buttons:
            btn.setChecked(btn.text() == option)
        self.selection_changed.emit(option)

    def currentText(self) -> str:
        """Get currently selected option."""
        return self._current

    def setCurrentText(self, text: str):
        """Set current selection."""
        if text in self.options:
            self._on_select(text)
