"""Identity→Goal 联动表单 — 嵌入式，无独立卡片。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSizePolicy,
)

from qfluentwidgets import ComboBox


# ── Data ──────────────────────────────────────────────────────────────
IDENTITY_OPTIONS = ["消费者", "被诉方（被告）", "起诉方（原告）", "复议申请人"]
GOAL_OPTIONS = ["维权投诉", "应诉答辩", "提起起诉", "申请行政复议", "申请再审", "支付令异议", "证据整理"]

IDENTITY_GOAL_MAP: dict[str, str] = {
    "消费者": "维权投诉",
    "被诉方（被告）": "应诉答辩",
    "起诉方（原告）": "提起起诉",
    "复议申请人": "申请行政复议",
}

SCENARIO_NAMES: dict[str, str] = {
    "被诉方（被告）_应诉答辩": "被诉防御反击流",
    "起诉方（原告）_提起起诉": "原告主动进攻流",
    "消费者_维权投诉": "消费者维权冲击流",
    "复议申请人_申请行政复议": "行政复议逆转流",
    "被诉方（被告）_支付令异议": "支付令异议防御流",
    "消费者_支付令异议": "消费者支付令异议",
    "起诉方（原告）_申请再审": "再审申请突破流",
    "被诉方（被告）_申请再审": "被告再审翻盘流",
    "消费者_证据整理": "消费者证据整理",
    "被诉方（被告）_证据整理": "被诉方证据整理",
    "起诉方（原告）_证据整理": "原告方证据整理",
    "复议申请人_证据整理": "复议证据整理",
}

_COMBO_STYLE = """
ComboBox {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 36px;
}
ComboBox:hover { border: 1.5px solid #2563EB; }
ComboBox:focus { border: 1.5px solid #2563EB; }
ComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px; border: none;
}
ComboBox QAbstractItemView {
    background-color: #FFFFFF; color: #0F172A;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    selection-background-color: #2563EB;
    selection-color: #ffffff; outline: none;
}
ComboBox QAbstractItemView::item { padding: 8px 12px; min-height: 28px; }
ComboBox QAbstractItemView::item:disabled {
    color: #94A3B8;
    background: #F8FAFC;
}
"""


class IdentityGoalGrid(QWidget):
    """身份→目的 联动表单，嵌入上传卡片内。"""

    combo_changed = Signal(str, str)
    validity_changed = Signal(bool)  # emits True when selection is valid

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        self._identity = "被诉方（被告）"
        self._goal = "应诉答辩"

        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(0, 4, 0, 0)

        # Grid row: [Label | ComboBox] → [Label | ComboBox]
        grid = QHBoxLayout()
        grid.setSpacing(12)

        # Identity column
        id_col = QVBoxLayout()
        id_col.setSpacing(6)
        id_label = QLabel("身份")
        id_label.setStyleSheet("color: #475569; font-size: 12px; font-weight: 600; border: none; letter-spacing: 0.5px;")
        id_col.addWidget(id_label)

        self.identity_combo = ComboBox(self)
        self.identity_combo.setStyleSheet(_COMBO_STYLE)
        self.identity_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.identity_combo.blockSignals(True)
        self.identity_combo.addItems(IDENTITY_OPTIONS)
        self.identity_combo.blockSignals(False)

        # Set default and disable unavailable options
        self._setup_identity_combo()

        id_col.addWidget(self.identity_combo)
        grid.addLayout(id_col, 1)

        # Arrow (vertically centered with combos)
        arrow_container = QWidget()
        arrow_container.setFixedWidth(32)
        arrow_container.setStyleSheet("background: transparent; border: none;")
        arrow_layout = QVBoxLayout(arrow_container)
        arrow_layout.setContentsMargins(0, 0, 0, 0)
        arrow_layout.addStretch()

        arrow = QLabel("→")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setStyleSheet("""
            QLabel {
                color: #94A3B8;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
                border: none;
                padding: 0;
            }
        """)
        arrow_layout.addWidget(arrow)
        arrow_layout.addStretch()

        grid.addWidget(arrow_container)

        # Goal column
        go_col = QVBoxLayout()
        go_col.setSpacing(6)
        go_label = QLabel("目的")
        go_label.setStyleSheet("color: #475569; font-size: 12px; font-weight: 600; border: none; letter-spacing: 0.5px;")
        go_col.addWidget(go_label)

        self.goal_combo = ComboBox(self)
        self.goal_combo.setStyleSheet(_COMBO_STYLE)
        self.goal_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.goal_combo.blockSignals(True)
        self.goal_combo.addItems(GOAL_OPTIONS)
        self.goal_combo.blockSignals(False)

        # Set default and disable unavailable options
        self._setup_goal_combo()

        # Connect signals AFTER both combos are fully initialized
        self.identity_combo.currentTextChanged.connect(self._on_identity_changed)
        self.goal_combo.currentTextChanged.connect(self._on_goal_changed)

        go_col.addWidget(self.goal_combo)
        grid.addLayout(go_col, 1)

        root.addLayout(grid)

        # Status hint (plain text, theme color)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #0D9488;
                font-size: 12px;
                font-weight: 600;
                padding: 2px 0;
                background: transparent;
                border: none;
            }
        """)
        self._update_status()
        root.addWidget(self.status_label)

    def _setup_identity_combo(self):
        """Set default identity."""
        idx = IDENTITY_OPTIONS.index("被诉方（被告）")
        self.identity_combo.setCurrentIndex(idx)

    def _setup_goal_combo(self):
        """Set default goal."""
        idx = GOAL_OPTIONS.index("应诉答辩")
        self.goal_combo.setCurrentIndex(idx)

    # ── Slots ──────────────────────────────────────────────────────────
    def _on_identity_changed(self, identity: str):
        self._identity = identity
        mapped = IDENTITY_GOAL_MAP.get(identity)
        if mapped and mapped in GOAL_OPTIONS:
            self.goal_combo.blockSignals(True)
            self.goal_combo.setCurrentIndex(GOAL_OPTIONS.index(mapped))
            self.goal_combo.blockSignals(False)
            self._goal = mapped
        self._update_status()
        self.combo_changed.emit(self._identity, self._goal)
        self.validity_changed.emit(self.is_selection_valid())

    def _on_goal_changed(self, goal: str):
        self._goal = goal
        self._update_status()
        self.combo_changed.emit(self._identity, self._goal)
        self.validity_changed.emit(self.is_selection_valid())

    def _update_status(self):
        key = f"{self._identity}_{self._goal}"
        scenario = SCENARIO_NAMES.get(key, self._goal)
        self.status_label.setText(f"当前方案：{scenario}")

    # ── Public API ─────────────────────────────────────────────────────
    def currentIdentity(self) -> str:
        return self._identity

    def currentGoal(self) -> str:
        return self._goal

    def is_selection_valid(self) -> bool:
        """Check if current selection is valid."""
        return self._identity in IDENTITY_OPTIONS and self._goal in GOAL_OPTIONS

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.identity_combo.setEnabled(enabled)
        self.goal_combo.setEnabled(enabled)
