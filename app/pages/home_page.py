"""app/pages/home_page.py — 首页：极简上传工作台."""
from __future__ import annotations

from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QSpacerItem

from qfluentwidgets import (
    SubtitleLabel, CaptionLabel,
    PrimaryPushButton, PushButton, FluentIcon,
    InfoBar, PlainTextEdit,
)

from app.widgets.upload_card import UploadCard
from app.widgets.identity_goal_grid import IdentityGoalGrid
from app.widgets.ai_status_card import AiStatusCard


# ── Home Page ─────────────────────────────────────────────────────────

class HomePage(QWidget):
    """极简上传工作台."""

    analysis_requested = Signal(list, str, str, str)
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._notice_timer = QTimer(self)
        self._notice_timer.setSingleShot(True)
        self._notice_timer.timeout.connect(self._hide_notice)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        root.addWidget(self._build_header())

        # Main content — top-aligned, compact margins so the upload
        # section feels focused rather than floating in dead space.
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(36, 24, 36, 24)
        content_layout.setSpacing(0)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Upload section (core area)
        content_layout.addWidget(self._build_upload_section())

        # Bottom elastic stretch (replaces the old symmetric 2x spacer).
        # Keeps the section glued to the top while still allowing the
        # window to grow without empty space at the top.
        content_layout.addStretch(1)

        root.addWidget(content)

    def _connect_signals(self):
        """Connect signals for dynamic UI updates."""
        self.identity_goal_grid.validity_changed.connect(self._on_validity_changed)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        header.setFixedHeight(48)
        header.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E2E8F0;
            }
        """)
        h = QHBoxLayout(header)
        h.setContentsMargins(16, 0, 16, 0)
        h.setSpacing(12)

        page_title = SubtitleLabel("首页")
        page_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #0F172A; border: none;")
        h.addWidget(page_title)

        h.addStretch(1)

        self.ai_status_card = AiStatusCard()
        self.ai_status_card.update_from_settings()
        if self.ai_status_card.label.text() == "预览模式":
            self.ai_status_card.setVisible(False)
        h.addWidget(self.ai_status_card)

        self.gear_btn = PushButton()
        self.gear_btn.setIcon(FluentIcon.SETTING)
        self.gear_btn.setFixedSize(32, 32)
        self.gear_btn.setStyleSheet("""
            PushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            PushButton:hover {
                background-color: #F3F4F6;
            }
        """)
        self.gear_btn.clicked.connect(self.settings_requested.emit)
        h.addWidget(self.gear_btn)
        return header

    def _build_upload_section(self) -> QWidget:
        """Build the main upload section with large drop area."""
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        container.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(container)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 22, 28, 22)

        title = SubtitleLabel("上传材料")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #0F172A; border: none; letter-spacing: 0.5px;")
        layout.addWidget(title)

        self.upload_card = UploadCard()
        # Cap the upload card so the section doesn't balloon on tall windows.
        self.upload_card.setMaximumHeight(280)
        self.upload_card.setMinimumHeight(200)
        layout.addWidget(self.upload_card)

        self.identity_goal_grid = IdentityGoalGrid()
        layout.addWidget(self.identity_goal_grid)

        purpose_label = CaptionLabel("具体目的（可选）")
        purpose_label.setStyleSheet("color: #64748B; font-size: 12px; border: none; font-weight: 500;")
        layout.addWidget(purpose_label)

        self.purpose_input = PlainTextEdit()
        self.purpose_input.setPlaceholderText("请简要描述您的具体需求,例如:帮我整理证据材料,找出对我有利的证据...")
        self.purpose_input.setMaximumHeight(60)
        self.purpose_input.setStyleSheet("""
            PlainTextEdit {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: #0F172A;
                selection-background-color: #BFDBFE;
            }
            PlainTextEdit:focus {
                border: 1.5px solid #2563EB;
                background-color: #FFFFFF;
            }
        """)
        layout.addWidget(self.purpose_input)

        self._notice_label = CaptionLabel("")
        self._notice_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._notice_label.setStyleSheet("""
            QLabel {
                color: #DC2626;
                font-size: 12px;
                font-weight: 500;
                background-color: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 6px;
                padding: 6px 10px;
            }
        """)
        self._notice_label.setVisible(False)
        layout.addWidget(self._notice_label)

        self.start_btn = PrimaryPushButton("开始分析")
        self.start_btn.setIcon(FluentIcon.PLAY)
        self.start_btn.setFixedHeight(42)
        self.start_btn.setStyleSheet("""
            PrimaryPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
                border: none;
                border-radius: 8px;
                padding: 8px 28px;
            }
            PrimaryPushButton:hover {
                background-color: #1D4ED8;
            }
            PrimaryPushButton:pressed {
                background-color: #1E40AF;
            }
            PrimaryPushButton:disabled {
                background-color: #94A3B8;
                color: #CBD5E1;
            }
        """)
        self.start_btn.clicked.connect(self._on_start)
        layout.addWidget(self.start_btn)

        return container

    def _on_validity_changed(self, valid: bool):
        """Update button state based on selection validity."""
        if valid:
            self.start_btn.setEnabled(True)
            self.start_btn.setText("开始分析")
            self._hide_notice()
        else:
            self.start_btn.setEnabled(False)
            self.start_btn.setText("场景暂未开放")

    def _show_notice(self, message: str, auto_hide_ms: int = 3000):
        """Show notice message above button, auto-hide after delay."""
        self._notice_label.setText(message)
        self._notice_label.setVisible(True)
        self._notice_timer.start(auto_hide_ms)

    def _hide_notice(self):
        """Hide the notice label."""
        self._notice_label.setVisible(False)
        self._notice_timer.stop()

    def _on_start(self):
        files = self.upload_card.selected_files
        if not files:
            self._show_notice("请先上传案件材料")
            return
        identity = self.identity_goal_grid.currentIdentity()
        goal = self.identity_goal_grid.currentGoal()
        purpose = self.purpose_input.toPlainText().strip()
        self._hide_notice()
        self.analysis_requested.emit(files, identity, goal, purpose)

    def reset_quick_start(self):
        self.upload_card._clear_files()
        self._hide_notice()

    def set_quick_start_enabled(self, enabled: bool):
        self.upload_card.setEnabled(enabled)
        self.identity_goal_grid.setEnabled(enabled)
        self.start_btn.setEnabled(enabled and self.identity_goal_grid.is_selection_valid())
