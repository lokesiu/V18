"""app/widgets/api_tutorial_dialog.py — 通用 API Key 申请教程弹窗.

A polished, scrollable tutorial dialog explaining how to obtain an API
key from a third-party provider. Used by the AI provider cards
(DeepSeek / MiMo / MiniMax) in the settings page.

Features:
    - Step-by-step numbered instructions
    - In-dialog "复制链接" and "打开网页" buttons
    - Markdown-rendered body via QTextBrowser
    - Consistent with V18 design system
    - Modal but resizable (min 640 × 520)

Usage:
    dialog = ApiTutorialDialog(
        title="如何获取 MiniMax API Key",
        steps=[
            "访问火山引擎控制台 https://console.volcengine.com/",
            "注册/登录账号,完成实名认证",
            "进入「API Key 管理」页面,点击「创建 API Key」",
            "复制生成的 API Key (格式: sk-...)",
            "回到 V18 设置页,粘贴到 MiniMax 卡片中,点击「测试连接」",
        ],
        url="https://platform.minimax.chat/usercenter/apikeys",
        warning="API Key 仅创建时显示一次,请妥善保存。",
        parent=self,
    )
    dialog.exec()
"""
from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QDialog, QWidget, QLabel

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, CaptionLabel,
    PushButton, PrimaryPushButton, FluentIcon, InfoBar,
    ScrollArea, TextBrowser,
)

from app.style_constants import Colors, Spacing, Typography


def _build_step_html(steps: Sequence[str]) -> str:
    """Build the steps list as an ordered HTML list."""
    items = "".join(
        f"<li style='margin-bottom: 12px; line-height: 1.7;'>{step}</li>"
        for step in steps
    )
    return f"<ol style='padding-left: 24px; margin: 0;'>{items}</ol>"


class ApiTutorialDialog(QDialog):
    """Generic API key tutorial dialog.

    Shows step-by-step instructions, the target URL, and a "复制链接"/"打开网页"
    action pair. Designed to live behind a "查看教程" button on provider cards.
    """

    def __init__(
        self,
        title: str,
        steps: Sequence[str],
        url: str,
        warning: Optional[str] = None,
        tip: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._url = url
        self._parent_window = parent.window() if parent else None
        self.setWindowTitle(title)
        self.setMinimumSize(640, 520)
        self.setSizeGripEnabled(True)
        self._setup_ui(title=title, steps=steps, warning=warning, tip=tip)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_ui(
        self,
        title: str,
        steps: Sequence[str],
        warning: Optional[str],
        tip: Optional[str],
    ) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.XL2, Spacing.XL, Spacing.XL2, Spacing.XL)
        root.setSpacing(Spacing.LG)

        # Header
        header = QHBoxLayout()
        header.setSpacing(Spacing.MD)

        icon_label = QLabel("📖")
        icon_label.setStyleSheet(
            f"font-size: 28px; background: transparent; border: none;"
        )
        header.addWidget(icon_label)

        title_label = SubtitleLabel(title)
        title_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY};"
            f" font-size: {Typography.FONT_SIZE_XL}px;"
            f" font-weight: {Typography.WEIGHT_SEMIBOLD};"
            f" background: transparent;"
        )
        header.addWidget(title_label)
        header.addStretch()
        root.addLayout(header)

        # Divider
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {Colors.BORDER}; border: none;")
        root.addWidget(divider)

        # Scroll area for the body
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"ScrollArea {{"
            f"  background-color: {Colors.SURFACE_SOFT};"
            f"  border: 1px solid {Colors.BORDER};"
            f"  border-radius: {Spacing.RADIUS_LG}px;"
            f"}}"
        )
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        scroll_layout.setSpacing(Spacing.MD)

        # Step list
        steps_browser = TextBrowser()
        steps_browser.setOpenExternalLinks(True)
        steps_browser.setStyleSheet(
            f"QTextBrowser {{"
            f"  background-color: transparent;"
            f"  border: none;"
            f"  color: {Colors.TEXT_PRIMARY};"
            f"  font-size: {Typography.FONT_SIZE_BASE}px;"
            f"  selection-background-color: {Colors.BLUE_200};"
            f"}}"
        )
        steps_html = _build_step_html(steps)
        steps_browser.setHtml(
            f"<div style='color: {Colors.TEXT_PRIMARY}; "
            f"font-family: \"Microsoft YaHei UI\", \"Microsoft YaHei\", \"微软雅黑\";'>"
            f"{steps_html}"
            f"</div>"
        )
        scroll_layout.addWidget(steps_browser)

        # URL block
        url_label = CaptionLabel("官方申请地址")
        url_label.setStyleSheet(
            f"color: {Colors.TEXT_MUTED};"
            f" font-size: {Typography.FONT_SIZE_SM}px;"
            f" font-weight: {Typography.WEIGHT_MEDIUM};"
            f" background: transparent;"
        )
        scroll_layout.addWidget(url_label)

        url_browser = TextBrowser()
        url_browser.setOpenExternalLinks(False)
        url_browser.setStyleSheet(
            f"QTextBrowser {{"
            f"  background-color: {Colors.WHITE};"
            f"  border: 1px solid {Colors.BORDER};"
            f"  border-radius: {Spacing.RADIUS_MD}px;"
            f"  padding: 8px 12px;"
            f"  color: {Colors.PRIMARY};"
            f"  font-family: 'Consolas', 'Monaco', monospace;"
            f"  font-size: {Typography.FONT_SIZE_BASE}px;"
            f"}}"
        )
        url_browser.setPlainText(self._url)
        url_browser.setFixedHeight(44)
        scroll_layout.addWidget(url_browser)

        # Warning (optional)
        if warning:
            warn_label = BodyLabel(f"⚠️  {warning}")
            warn_label.setStyleSheet(
                f"color: {Colors.RED_700};"
                f" font-size: {Typography.FONT_SIZE_SM}px;"
                f" background-color: {Colors.RED_50};"
                f" border: 1px solid {Colors.RED_200};"
                f" border-radius: {Spacing.RADIUS_MD}px;"
                f" padding: 8px 12px;"
            )
            warn_label.setWordWrap(True)
            scroll_layout.addWidget(warn_label)

        # Tip (optional)
        if tip:
            tip_label = BodyLabel(f"💡  {tip}")
            tip_label.setStyleSheet(
                f"color: {Colors.GREEN_700};"
                f" font-size: {Typography.FONT_SIZE_SM}px;"
                f" background-color: {Colors.GREEN_100};"
                f" border: 1px solid {Colors.GREEN_500};"
                f" border-radius: {Spacing.RADIUS_MD}px;"
                f" padding: 8px 12px;"
            )
            tip_label.setWordWrap(True)
            scroll_layout.addWidget(tip_label)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        root.addWidget(scroll, 1)

        # Action row
        action_row = QHBoxLayout()
        action_row.setSpacing(Spacing.MD)

        copy_btn = PushButton("复制链接")
        copy_btn.setIcon(FluentIcon.COPY)
        copy_btn.clicked.connect(self._copy_url)
        action_row.addWidget(copy_btn)

        action_row.addStretch()

        close_btn = PrimaryPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        action_row.addWidget(close_btn)

        open_btn = PushButton("打开网页")
        open_btn.setIcon(FluentIcon.LINK)
        open_btn.clicked.connect(self._open_url)
        action_row.addWidget(open_btn)

        root.addLayout(action_row)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _copy_url(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._url)
        if self._parent_window:
            InfoBar.success(
                "已复制",
                "链接已复制到剪贴板",
                parent=self._parent_window,
                duration=2000,
            )

    def _open_url(self) -> None:
        QDesktopServices.openUrl(QUrl(self._url))


__all__ = ["ApiTutorialDialog"]
