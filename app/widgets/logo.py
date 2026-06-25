"""app/widgets/logo.py — 明证台 (MingZhengTai) vector LOGO widget.

A self-contained vector LOGO for the V18 desktop app. Designed to replace
the literal "明证台" text label that currently lives in the navigation
title bar (see app/main_window.py around the title bar area, WIP).

Design concept:
    - Mark: a stylized "M" (Ming) formed by a balanced pillar + a "shield"
      outline that subtly evokes a courtroom / evidence / justice
      motif, plus a single scale-balance dot.
    - Wordmark: 致简 (concise) Chinese 2-char "明证台" typeset in heavy
      weight for legibility, with optional Latin subtitle "MINGZHENGTAI"
      below for marketing pages.
    - Renders crisply at any DPI (vector — uses QPainterPath, no raster).
    - Theme-aware: reads FluentWindow's text color when available, falls
      back to a neutral palette that reads on both light and dark.

Usage:
    from app.widgets.logo import Logo, LogoMark, LogoWordmark

    # Full logo (mark + wordmark, horizontal layout)
    self.title_label = Logo()

    # Or just the icon mark
    self.icon_only = LogoMark(size=24)

    # Or just the wordmark text
    self.text_only = LogoWordmark(font_size=18)

The widget is fully self-contained — drop it into a QHBoxLayout and you're
done. No external resources required.

WIP NOTE: To swap into app/main_window.py (currently WIP), replace the
title text with the Logo widget. See docs/LOGO_SWAP.md for the exact
diff once WIP is unfrozen.
"""
from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import Qt, QSize, QRectF, QPointF
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QFont, QFontMetrics, QPen, QBrush,
    QLinearGradient, QPaintEvent, QResizeEvent,
)
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QSizePolicy, QVBoxLayout

from app.style_constants import Colors, Typography


# ---------------------------------------------------------------------------
# Color tokens — theme-aware (light + dark)
# ---------------------------------------------------------------------------
class LogoColors:
    """Palette for the vector LOGO. Stable across themes."""

    # Primary — "明证台" (litigation / evidence) brand red-amber, evoking
    # the traditional red seal (印章) used to mark legal documents.
    BRAND_RED = "#B91C1C"
    BRAND_RED_DARK = "#7F1D1D"
    BRAND_GOLD = "#D97706"
    BRAND_GOLD_LIGHT = "#F59E0B"

    # Neutrals
    INK = "#0F172A"          # text on light bg
    INK_INVERSE = "#F8FAFC"  # text on dark bg
    SHIELD_STROKE = "#334155"

    # Accent dot (the scale balance ball)
    ACCENT_BLUE = "#2563EB"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def _build_mark_path() -> QPainterPath:
    """Build the M-shaped shield mark as a single QPainterPath.

    Composition:
        - Outer shield outline (truncated at the bottom — like a "M" peak)
        - A central vertical pillar (the "stem" of the M)
        - Two diagonal flanks forming the M's outer strokes
        - A small accent dot at the top-right corner (the "scale balance")
    """
    path = QPainterPath()

    # Shield outline — hexagon-ish, slightly pointed at the top
    # Coordinates are in a 24x24 grid, will be scaled to actual size
    # Path: M 4 3 L 12 1 L 20 3 L 22 9 L 19 21 L 12 23 L 5 21 L 2 9 Z
    path.moveTo(4.5, 3.0)
    path.lineTo(12.0, 1.0)
    path.lineTo(19.5, 3.0)
    path.lineTo(22.0, 9.0)
    path.lineTo(19.0, 21.0)
    path.lineTo(12.0, 23.0)
    path.lineTo(5.0, 21.0)
    path.lineTo(2.0, 9.0)
    path.closeSubpath()

    return path


def _build_m_subpath() -> QPainterPath:
    """Build the inner "M" character that sits inside the shield."""
    path = QPainterPath()
    # The M occupies roughly the central 60% of the shield.
    # Two outer pillars + a V dip in the middle.
    # M starts at (6.5, 19), goes up to (6.5, 8), then down to (12, 14)
    # (the V's valley), up to (17.5, 8), down to (17.5, 19).
    path.moveTo(6.5, 19.0)
    path.lineTo(6.5, 8.0)
    path.lineTo(12.0, 14.5)
    path.lineTo(17.5, 8.0)
    path.lineTo(17.5, 19.0)
    return path


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------
class LogoMark(QWidget):
    """Just the icon mark — the M-in-shield glyph. Square aspect."""

    def __init__(
        self,
        size: int = 28,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._size = size
        self.setFixedSize(QSize(size, size))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def sizeHint(self) -> QSize:
        return QSize(self._size, self._size)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Scale the 24x24 design grid to the widget size with a small
        # padding so the stroke doesn't get clipped.
        pad = max(1.0, self._size * 0.04)
        scale = (self._size - 2 * pad) / 24.0
        painter.translate(pad, pad)
        painter.scale(scale, scale)

        # Gradient fill for the shield body
        gradient = QLinearGradient(0, 0, 24, 24)
        gradient.setColorAt(0.0, QColor(LogoColors.BRAND_RED))
        gradient.setColorAt(1.0, QColor(LogoColors.BRAND_RED_DARK))

        # Draw shield outline (filled with gradient)
        shield = _build_mark_path()
        painter.fillPath(shield, QBrush(gradient))

        # Draw inner M (white / inverse ink)
        m_path = _build_m_subpath()
        pen = QPen(QColor(255, 255, 255))
        pen.setWidthF(2.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(m_path)

        # Scale balance accent dot (top-right)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(LogoColors.BRAND_GOLD))
        painter.drawEllipse(QPointF(19.5, 4.0), 1.6, 1.6)

        painter.end()


class LogoWordmark(QLabel):
    """The 致简 wordmark "明证台" + optional Latin subtitle.

    A plain QLabel subclass so it can be dropped into any layout. Uses a
    custom QSS to get the right weight without depending on a specific
    font being installed.
    """

    def __init__(
        self,
        show_latin: bool = True,
        font_size: int = 16,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._show_latin = show_latin
        self._font_size = font_size
        self._build()

    def _build(self) -> None:
        if self._show_latin:
            html = (
                f"<div style='line-height: 1.05;'>"
                f"  <span style='"
                f'    font-family: "Source Han Sans SC", "Noto Sans CJK SC", '
                f'"Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑", sans-serif;'
                f"    font-size: {self._font_size}px;"
                f"    font-weight: 700;"
                f"    color: {Colors.TEXT_PRIMARY};"
                f"    letter-spacing: 2px;"
                f"  '>明证台</span>"
                f"  <div style='"
                f"    font-size: 9px;"
                f"    color: {Colors.TEXT_MUTED};"
                f"    letter-spacing: 1.5px;"
                f"    margin-top: 2px;"
                f"    font-weight: 500;"
                f"  '>MINGZHENGTAI · V18</div>"
                f"</div>"
            )
        else:
            html = (
                f"<span style='"
                f'  font-family: "Source Han Sans SC", "Noto Sans CJK SC", '
                f'"Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑", sans-serif;'
                f"  font-size: {self._font_size}px;"
                f"  font-weight: 700;"
                f"  color: {Colors.TEXT_PRIMARY};"
                f"  letter-spacing: 2px;"
                f"'>明证台</span>"
            )
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setText(html)
        self.setStyleSheet("background: transparent; border: none;")
        self.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

    def set_compact(self, compact: bool = True) -> None:
        """Toggle between full wordmark and compact (no subtitle)."""
        if compact != (not self._show_latin):
            self._show_latin = not compact
            self._build()


class Logo(QWidget):
    """Full LOGO: mark + wordmark, side by side.

    Designed to be a drop-in replacement for the title text in
    app/main_window.py. The size hint is driven by the mark size;
    the wordmark scales to match.
    """

    def __init__(
        self,
        mark_size: int = 28,
        show_latin: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._mark_size = mark_size
        self._show_latin = show_latin
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        self._mark = LogoMark(size=self._mark_size)
        layout.addWidget(self._mark)

        self._wordmark = LogoWordmark(
            show_latin=self._show_latin,
            font_size=self._mark_size // 2 + 8,
        )
        layout.addWidget(self._wordmark)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_compact(self, compact: bool = True) -> None:
        """Toggle the Latin subtitle visibility (e.g., for narrow sidebars)."""
        self._wordmark.set_compact(compact)


__all__ = ["Logo", "LogoMark", "LogoWordmark"]
