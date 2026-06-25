"""app/widgets/empty_state.py — Reusable empty-state component.

A clean "nothing here yet" panel for tables, lists, and detail panes.
Replaces ad-hoc "暂无数据" labels scattered across pages with a
visually consistent experience.

Features:
  - Big icon
  - Title (e.g. "暂无案件")
  - Optional description / hint
  - Optional primary action button
  - Optional secondary action
  - Centered in its parent by default

Usage:
    layout.addWidget(EmptyState(
        icon=FluentIcon.DOCUMENT,
        title="暂无案件",
        description="点击「新建案件」开始处理",
        action_text="新建案件",
        on_action=lambda: print("new case"),
    ))
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy

from qfluentwidgets import (
    FluentIcon as FIF,
    IconWidget,
    BodyLabel,
    CaptionLabel,
    PrimaryPushButton,
    PushButton,
)

from app.style_constants import Colors, Spacing, Typography, Styles


class EmptyState(QWidget):
    """Polished empty-state placeholder."""

    def __init__(
        self,
        icon: FIF = FIF.DOCUMENT,
        title: str = "暂无数据",
        description: str = "",
        action_text: Optional[str] = None,
        on_action: Optional[Callable[[], None]] = None,
        secondary_text: Optional[str] = None,
        on_secondary: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
        icon_size: int = 48,
    ) -> None:
        super().__init__(parent)
        self._setup_ui(
            icon=icon,
            title=title,
            description=description,
            action_text=action_text,
            on_action=on_action,
            secondary_text=secondary_text,
            on_secondary=on_secondary,
            icon_size=icon_size,
        )

    def _setup_ui(
        self,
        icon: FIF,
        title: str,
        description: str,
        action_text: Optional[str],
        on_action: Optional[Callable[[], None]],
        secondary_text: Optional[str],
        on_secondary: Optional[Callable[[], None]],
        icon_size: int,
    ) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(Spacing.XL2, Spacing.XL3, Spacing.XL2, Spacing.XL3)
        outer.setSpacing(0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        self._icon = IconWidget(icon)
        self._icon.setFixedSize(icon_size, icon_size)
        icon_layout = QHBoxLayout()
        icon_layout.addStretch()
        icon_layout.addWidget(self._icon)
        icon_layout.addStretch()
        outer.addLayout(icon_layout)

        # Spacer
        outer.addSpacing(Spacing.MD)

        # Title
        self._title = BodyLabel(title)
        self._title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY};"
            f" font-size: {Typography.FONT_SIZE_LG}px;"
            f" font-weight: {Typography.WEIGHT_SEMIBOLD};"
            f" background: transparent;"
        )
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout = QHBoxLayout()
        title_layout.addStretch()
        title_layout.addWidget(self._title)
        title_layout.addStretch()
        outer.addLayout(title_layout)

        # Description (optional)
        if description:
            outer.addSpacing(Spacing.SM)
            self._description = CaptionLabel(description)
            self._description.setStyleSheet(
                f"color: {Colors.TEXT_MUTED};"
                f" font-size: {Typography.FONT_SIZE_SM}px;"
                f" background: transparent;"
            )
            self._description.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._description.setWordWrap(True)
            desc_layout = QHBoxLayout()
            desc_layout.addStretch()
            desc_layout.addWidget(self._description)
            desc_layout.addStretch()
            outer.addLayout(desc_layout)

        # Action buttons (optional)
        if action_text or secondary_text:
            outer.addSpacing(Spacing.LG)
            button_row = QHBoxLayout()
            button_row.setSpacing(Spacing.SM)
            button_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
            button_row.addStretch()

            if secondary_text and on_secondary:
                self._secondary_btn = PushButton(secondary_text)
                self._secondary_btn.clicked.connect(on_secondary)
                button_row.addWidget(self._secondary_btn)

            if action_text and on_action:
                self._action_btn = PrimaryPushButton(action_text)
                self._action_btn.setStyleSheet(Styles.primary_button())
                self._action_btn.clicked.connect(on_action)
                button_row.addWidget(self._action_btn)

            button_row.addStretch()
            outer.addLayout(button_row)

        # Don't set our own size policy / stretch — let the parent layout
        # decide. This way EmptyState plays nicely with both QVBoxLayout
        # siblings (gets minimum space) and direct centering containers.


__all__ = ["EmptyState"]
