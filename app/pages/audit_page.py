"""app/pages/audit_page.py — 审计日志页（增强版）."""
from __future__ import annotations

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QHeaderView,
    QComboBox, QTableWidgetItem,
)

from qfluentwidgets import (
    SubtitleLabel, CaptionLabel, PushButton, FluentIcon,
    TableWidget, ScrollArea, SearchLineEdit, Dialog,
)

_BTN_STYLE = (
    "PushButton { background-color: #FFFFFF; color: #374151; "
    "border: 1px solid #D1D5DB; border-radius: 6px; padding: 6px 14px; }"
    "PushButton:hover { border: 1px solid #3b82f6; background-color: #EFF6FF; }"
)

_COMBO_STYLE = (
    "QComboBox { background-color: #FFFFFF; color: #1F2937; "
    "border: 1px solid #D1D5DB; border-radius: 6px; padding: 4px 8px; font-size: 12px; }"
    "QComboBox:hover { border-color: #3b82f6; }"
    "QComboBox QAbstractItemView { background-color: #FFFFFF; color: #1F2937; "
    "border: 1px solid #D1D5DB; selection-background-color: #3b82f6; }"
)

_SEVERITY_COLORS = {
    "error": "#ef4444",
    "warning": "#f59e0b",
    "info": "#b0b0b8",
}


class AuditPage(QWidget):
    """审计日志 — 支持搜索、筛选、详情展开."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_entries: list[dict] = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 28, 32, 28)

        # ── Header ──
        header = QHBoxLayout()
        header.setSpacing(12)
        title = SubtitleLabel("审计日志")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # ── Filter row ──
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.search_box = SearchLineEdit()
        self.search_box.setPlaceholderText("搜索任务ID / 消息...")
        self.search_box.setFixedWidth(220)
        self.search_box.setStyleSheet(
            "SearchLineEdit { background-color: #FFFFFF; color: #1F2937; "
            "border: 1px solid #D1D5DB; border-radius: 6px; }"
            "SearchLineEdit:focus { border-color: #3b82f6; }"
        )
        self.search_box.textChanged.connect(self._apply_filters)
        filter_row.addWidget(self.search_box)

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["全部级别", "info", "warning", "error"])
        self.severity_combo.setStyleSheet(_COMBO_STYLE)
        self.severity_combo.setFixedWidth(100)
        self.severity_combo.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self.severity_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItem("全部事件")
        self.type_combo.setStyleSheet(_COMBO_STYLE)
        self.type_combo.setFixedWidth(140)
        self.type_combo.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self.type_combo)

        filter_row.addStretch()

        self.refresh_btn = PushButton("刷新")
        self.refresh_btn.setIcon(FluentIcon.SYNC)
        self.refresh_btn.setStyleSheet(_BTN_STYLE)
        filter_row.addWidget(self.refresh_btn)

        layout.addLayout(filter_row)

        # ── Table container ──
        table_container = QWidget()
        table_container.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
        """)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)
        
        self.table = TableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["时间", "任务ID", "阶段", "事件", "详情"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(
            "TableWidget { background-color: #FFFFFF; color: #1F2937; "
            "border: none; border-radius: 8px; }"
            "QHeaderView::section { background-color: #F3F4F6; color: #374151; "
            "border: none; border-bottom: 1px solid #E5E7EB; padding: 10px 12px; font-weight: bold; }"
            "TableWidget::item { padding: 8px 12px; }"
            "TableWidget::item:selected { background-color: #EFF6FF; color: #1F2937; }"
        )
        self.table.doubleClicked.connect(self._show_detail)
        table_layout.addWidget(self.table)
        
        # ── Empty state (inside table container, centered) ──
        self._empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setContentsMargins(20, 40, 20, 40)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._empty_label = CaptionLabel("暂无审计记录")
        self._empty_label.setStyleSheet("color: #6B7280; font-size: 13px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._empty_label)
        
        table_layout.addWidget(self._empty_widget)
        self._empty_widget.setVisible(False)
        
        layout.addWidget(table_container, 1)

        scroll.setWidget(content)
        root.addWidget(scroll)

    # ── Data loading ──────────────────────────────────────────────────
    def load_entries(self, entries: list[dict]):
        """Load audit entries and populate type filter."""
        self._all_entries = entries

        # Update type combo options
        types = sorted(set(e.get("event_type", "") for e in entries if e.get("event_type")))
        current = self.type_combo.currentText()
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        self.type_combo.addItem("全部事件")
        for t in types:
            self.type_combo.addItem(t)
        # Restore selection
        idx = self.type_combo.findText(current)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.type_combo.blockSignals(False)

        self._apply_filters()

    def _apply_filters(self):
        """Apply search + severity + type filters to entries."""
        search_text = self.search_box.text().strip().lower()
        severity = self.severity_combo.currentText()
        event_type = self.type_combo.currentText()

        filtered = self._all_entries

        if search_text:
            filtered = [
                e for e in filtered
                if search_text in e.get("task_id", "").lower()
                or search_text in e.get("message", "").lower()
                or search_text in e.get("stage_name", "").lower()
            ]

        if severity and severity != "全部级别":
            filtered = [e for e in filtered if e.get("severity") == severity]

        if event_type and event_type != "全部事件":
            filtered = [e for e in filtered if e.get("event_type") == event_type]

        self._render_table(filtered)

    def _render_table(self, entries: list[dict]):
        """Render entries into the table."""
        self.table.setRowCount(0)

        if not entries:
            self._empty_widget.setVisible(True)
            self.table.setVisible(False)
            return

        self._empty_widget.setVisible(False)
        self.table.setVisible(True)

        for e in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)

            time_str = e.get("created_at", "")
            task_id = e.get("task_id", "")
            stage = e.get("stage_name", "")
            event_type = e.get("event_type", "")
            severity = e.get("severity", "info")
            message = e.get("message", "")
            detail = e.get("detail", {})

            # Time
            time_item = QTableWidgetItem(time_str)
            self.table.setItem(row, 0, time_item)

            # Task ID (short)
            id_display = task_id[:16] if len(task_id) > 16 else task_id
            id_item = QTableWidgetItem(id_display)
            id_item.setToolTip(task_id)
            self.table.setItem(row, 1, id_item)

            # Stage
            self.table.setItem(row, 2, QTableWidgetItem(stage))

            # Event type with severity color
            event_item = QTableWidgetItem(event_type)
            color = _SEVERITY_COLORS.get(severity, "#b0b0b8")
            event_item.setForeground(Qt.GlobalColor.white)
            from PySide6.QtGui import QColor
            event_item.setForeground(QColor(color))
            self.table.setItem(row, 3, event_item)

            # Message (truncated)
            msg_display = message[:100] + ("..." if len(message) > 100 else "")
            msg_item = QTableWidgetItem(msg_display)
            msg_item.setToolTip(message)
            # Store full detail for dialog
            msg_item.setData(Qt.ItemDataRole.UserRole, json.dumps(detail, ensure_ascii=False) if isinstance(detail, dict) else str(detail))
            self.table.setItem(row, 4, msg_item)

    # ── Detail dialog ─────────────────────────────────────────────────
    def _show_detail(self, index):
        """Show full event detail on double-click."""
        row = index.row()
        event_item = self.table.item(row, 3)
        msg_item = self.table.item(row, 4)
        time_item = self.table.item(row, 0)
        id_item = self.table.item(row, 1)

        if not event_item or not msg_item:
            return

        event_type = event_item.text()
        message = msg_item.toolTip() or msg_item.text()
        detail_raw = msg_item.data(Qt.ItemDataRole.UserRole) or ""
        task_id = id_item.toolTip() if id_item else ""
        time_str = time_item.text() if time_item else ""

        # Format detail
        try:
            detail_obj = json.loads(detail_raw)
            detail_formatted = json.dumps(detail_obj, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            detail_formatted = str(detail_raw)

        title = f"审计事件详情 — {event_type}"
        body = (
            f"时间: {time_str}\n"
            f"任务ID: {task_id}\n"
            f"事件: {event_type}\n\n"
            f"消息:\n{message}\n\n"
            f"详情:\n{detail_formatted[:1000]}"
        )

        dlg = Dialog(title, body, parent=self.window())
        dlg.exec()
