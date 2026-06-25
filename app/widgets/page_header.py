"""app/widgets/page_header.py — Unified page header.

Replaces ad-hoc SubtitleLabel + HBoxLayout header patterns scattered
across pages with a consistent component.

Features:
  - Title (left-aligned, 18px bold)
  - Optional subtitle / description (12px gray, under title)
  - Optional right-side action area (e.g. buttons)
  - Optional breadcrumb (top, 12px gray)
  - Consistent spacing and dividers

Usage:
    header = PageHeader(
        title="审计日志",
        subtitle="系统运行日志，可按时间/级别/类型筛选",
        actions=[(self.refresh_btn, "刷新")],
    )
    layout.addWidget(header)
"""
from __future__ import annotations

from typing import Optional, Sequence, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy,
)

from qfluentwidgets import (
    SubtitleLabel, CaptionLabel,
)

from app.style_constants import Colors, Spacing, Typography


class PageHeader(QWidget):
    """Standard page header with title, subtitle, and optional actions."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        breadcrumb: str = "",
        actions: Sequence[Tuple[QWidget, str]] = (),
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._setup_ui(title=title, subtitle=subtitle, breadcrumb=breadcrumb, actions=actions)

    def _setup_ui(
        self,
        title: str,
        subtitle: str,
        breadcrumb: str,
        actions: Sequence[Tuple[QWidget, str]],
    ) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(Spacing.XS)

        # Optional breadcrumb
        if breadcrumb:
            self._breadcrumb = CaptionLabel(breadcrumb)
            self._breadcrumb.setStyleSheet(
                f"color: {Colors.TEXT_MUTED};"
                f" font-size: {Typography.FONT_SIZE_XS}px;"
                f" font-weight: {Typography.WEIGHT_MEDIUM};"
                f" background: transparent;"
            )
            outer.addWidget(self._breadcrumb)

        # Main row: title + actions
        main_row = QHBoxLayout()
        main_row.setContentsMargins(0, 0, 0, 0)
        main_row.setSpacing(Spacing.MD)

        # Title column (title + subtitle)
        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(Spacing.XS)

        self._title = SubtitleLabel(title)
        self._title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY};"
            f" font-size: {Typography.FONT_SIZE_2XL}px;"
            f" font-weight: {Typography.WEIGHT_BOLD};"
            f" background: transparent;"
        )
        title_col.addWidget(self._title)

        if subtitle:
            self._subtitle = CaptionLabel(subtitle)
            self._subtitle.setStyleSheet(
                f"color: {Colors.TEXT_MUTED};"
                f" font-size: {Typography.FONT_SIZE_SM}px;"
                f" background: transparent;"
            )
            title_col.addWidget(self._subtitle)

        main_row.addLayout(title_col)
        main_row.addStretch()

        # Action buttons (right side)
        if actions:
            actions_row = QHBoxLayout()
            actions_row.setContentsMargins(0, 0, 0, 0)
            actions_row.setSpacing(Spacing.SM)
            for widget, _label in actions:
                actions_row.addWidget(widget)
            main_row.addLayout(actions_row)

        outer.addLayout(main_row)

        # Bottom divider
        outer.addSpacing(Spacing.SM)
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {Colors.BORDER};")
        outer.addWidget(divider)

    # Convenience setters so the caller can update fields after creation
    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def set_subtitle(self, subtitle: str) -> None:
        if hasattr(self, "_subtitle"):
            self._subtitle.setText(subtitle)


__all__ = ["PageHeader"]
