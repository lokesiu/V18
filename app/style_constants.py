"""app/style_constants.py — V18 design system constants.

Centralized color, spacing, typography, and radius values used across the
desktop app. Created as part of the UI polish pass to eliminate magic
strings duplicated in stylesheets.

Usage:
    from app.style_constants import Colors, Spacing, Typography

    button.setStyleSheet(f"background-color: {Colors.BLUE_500};")

If you change a value here, search the codebase for hard-coded uses of
the same color/space and update them too. Run `python scripts/scan_ui.py`
(planned) to find stragglers.
"""
from __future__ import annotations


class Colors:
    """Color palette used throughout V18. Aliased to common Tailwind values.

    Hex strings (so they can be substituted directly into stylesheets).
    Use the UPPER_SNAKE_CASE constants; the lower_case names below are
    convenience aliases.
    """

    # Neutrals (gray scale)
    WHITE = "#FFFFFF"
    GRAY_50 = "#F8FAFC"
    GRAY_100 = "#F1F5F9"
    GRAY_200 = "#E2E8F0"
    GRAY_300 = "#CBD5E1"
    GRAY_400 = "#94A3B8"
    GRAY_500 = "#64748B"
    GRAY_600 = "#475569"
    GRAY_700 = "#334155"
    GRAY_800 = "#1E293B"
    GRAY_900 = "#0F172A"

    # Brand / action
    BLUE_50 = "#EFF6FF"
    BLUE_100 = "#DBEAFE"
    BLUE_200 = "#BFDBFE"
    BLUE_400 = "#60A5FA"
    BLUE_500 = "#3B82F6"
    BLUE_600 = "#2563EB"
    BLUE_700 = "#1D4ED8"
    BLUE_800 = "#1E40AF"

    # Status colors
    GREEN_100 = "#DCFCE7"
    GREEN_500 = "#22C55E"
    GREEN_600 = "#16A34A"
    GREEN_700 = "#15803D"

    AMBER_100 = "#FEF3C7"
    AMBER_500 = "#F59E0B"
    AMBER_600 = "#D97706"

    RED_50 = "#FEF2F2"
    RED_100 = "#FEE2E2"
    RED_200 = "#FECACA"
    RED_500 = "#EF4444"
    RED_600 = "#DC2626"
    RED_700 = "#B91C1C"

    PURPLE_500 = "#8B5CF6"
    PURPLE_600 = "#7C3AED"

    # Semantic aliases
    TEXT_PRIMARY = GRAY_900
    TEXT_SECONDARY = GRAY_600
    TEXT_MUTED = GRAY_500
    TEXT_DISABLED = GRAY_400
    TEXT_INVERSE = WHITE

    SURFACE = WHITE
    SURFACE_SOFT = GRAY_50
    SURFACE_RAISED = WHITE
    SURFACE_OVERLAY = "rgba(15, 23, 42, 0.6)"

    BORDER = GRAY_200
    BORDER_STRONG = GRAY_300
    BORDER_FOCUS = BLUE_500

    PRIMARY = BLUE_600
    PRIMARY_HOVER = BLUE_700
    PRIMARY_PRESSED = BLUE_800
    PRIMARY_SOFT = BLUE_50

    SUCCESS = GREEN_600
    WARNING = AMBER_500
    DANGER = RED_600
    INFO = BLUE_500


class Spacing:
    """8-point grid spacing scale."""

    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XL2 = 32
    XL3 = 48
    XL4 = 64

    # Specific layout values used throughout the app
    CARD_PADDING = 32
    SECTION_GAP = 24
    FIELD_GAP = 8
    INLINE_GAP = 12

    # Border radius
    RADIUS_SM = 4
    RADIUS_MD = 6
    RADIUS_LG = 8
    RADIUS_XL = 12
    RADIUS_PILL = 999


class Typography:
    """Typography scale."""

    # Font sizes
    FONT_SIZE_XS = 11
    FONT_SIZE_SM = 12
    FONT_SIZE_BASE = 13
    FONT_SIZE_MD = 14
    FONT_SIZE_LG = 15
    FONT_SIZE_XL = 16
    FONT_SIZE_2XL = 18
    FONT_SIZE_3XL = 22
    FONT_SIZE_4XL = 28

    # Font weights
    WEIGHT_NORMAL = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700

    # Line heights (used rarely; Qt usually handles internally)
    LINE_HEIGHT_TIGHT = 1.25
    LINE_HEIGHT_NORMAL = 1.5
    LINE_HEIGHT_RELAXED = 1.75


class Sizing:
    """Component sizes (icons, controls)."""

    ICON_XS = 12
    ICON_SM = 14
    ICON_MD = 16
    ICON_LG = 20
    ICON_XL = 24
    ICON_2XL = 32

    CONTROL_HEIGHT_SM = 28
    CONTROL_HEIGHT_MD = 36
    CONTROL_HEIGHT_LG = 44
    CONTROL_HEIGHT_XL = 48

    BORDER_THIN = 1
    BORDER_THICK = 2


# Convenience: pre-formatted stylesheet fragments to avoid duplicating strings.
class Styles:
    """Reusable stylesheet fragments. Use f-strings to interpolate values."""

    @staticmethod
    def primary_button() -> str:
        return (
            f"PrimaryPushButton {{"
            f"  background-color: {Colors.PRIMARY};"
            f"  color: {Colors.TEXT_INVERSE};"
            f"  font-size: {Typography.FONT_SIZE_MD}px;"
            f"  font-weight: {Typography.WEIGHT_SEMIBOLD};"
            f"  border: none;"
            f"  border-radius: {Spacing.RADIUS_LG}px;"
            f"  padding: 10px 32px;"
            f"}}"
            f"PrimaryPushButton:hover {{ background-color: {Colors.PRIMARY_HOVER}; }}"
            f"PrimaryPushButton:pressed {{ background-color: {Colors.PRIMARY_PRESSED}; }}"
            f"PrimaryPushButton:disabled {{"
            f"  background-color: {Colors.GRAY_400};"
            f"  color: {Colors.GRAY_300};"
            f"}}"
        )

    @staticmethod
    def card_surface() -> str:
        return (
            f"QWidget {{"
            f"  background-color: {Colors.SURFACE};"
            f"  border: {Sizing.BORDER_THIN}px solid {Colors.BORDER};"
            f"  border-radius: {Spacing.RADIUS_XL}px;"
            f"}}"
        )

    @staticmethod
    def focus_border() -> str:
        return f"border: 1.5px solid {Colors.BORDER_FOCUS};"


__all__ = ["Colors", "Spacing", "Typography", "Sizing", "Styles"]
