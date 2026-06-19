"""app/pages/case_list_page.py — 案件列表页."""
from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QHeaderView,
)

from qfluentwidgets import (
    SimpleCardWidget, SubtitleLabel, BodyLabel, CaptionLabel,
    PrimaryPushButton, PushButton, FluentIcon, TableWidget,
    ScrollArea, SearchLineEdit,
)


_STATUS_COLORS = {
    "已完成": "#22c55e",
    "部分完成": "#f59e0b",
    "进行中": "#3b82f6",
    "失败": "#ef4444",
    "已取消": "#707078",
    "待重试": "#f59e0b",
    "质量拦截": "#ef4444",
}


class CaseListPage(QWidget):
    """案件列表 — 全部案件管理."""

    case_selected = Signal(str)  # task_id

    def __init__(self, parent=None):
        super().__init__(parent)
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
        layout.setSpacing(16)
        layout.setContentsMargins(32, 28, 32, 28)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)
        title = SubtitleLabel("案件列表")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937;")
        header.addWidget(title)
        header.addStretch()

        self.search_box = SearchLineEdit()
        self.search_box.setPlaceholderText("搜索案件...")
        self.search_box.setFixedWidth(220)
        self.search_box.setStyleSheet(
            "SearchLineEdit { background-color: #FFFFFF; color: #1F2937; "
            "border: 1px solid #D1D5DB; border-radius: 6px; }"
        )
        header.addWidget(self.search_box)

        self.refresh_btn = PushButton("刷新")
        self.refresh_btn.setIcon(FluentIcon.SYNC)
        self.refresh_btn.setStyleSheet(
            "PushButton { background-color: #FFFFFF; color: #374151; "
            "border: 1px solid #D1D5DB; border-radius: 6px; padding: 6px 14px; }"
            "PushButton:hover { border: 1px solid #3b82f6; background-color: #EFF6FF; }"
        )
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self._filter_btns: dict[str, PushButton] = {}
        for label in ["全部", "进行中", "已完成", "失败"]:
            btn = PushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(
                "PushButton { background-color: #FFFFFF; color: #374151; "
                "border: 1px solid #D1D5DB; border-radius: 6px; padding: 4px 12px; font-size: 12px; }"
                "PushButton:checked { background-color: #3b82f6; color: #ffffff; border-color: #3b82f6; }"
                "PushButton:hover { border: 1px solid #3b82f6; background-color: #EFF6FF; }"
            )
            if label == "全部":
                btn.setChecked(True)
            self._filter_btns[label] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # Table container
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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["案件ID", "摘要", "身份", "状态", "评级", "创建时间"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
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
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        table_layout.addWidget(self.table)
        
        # Empty state (inside table container)
        self._empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setContentsMargins(20, 40, 20, 40)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._empty_label = CaptionLabel("暂无案件记录")
        self._empty_label.setStyleSheet("color: #6B7280; font-size: 13px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._empty_label)
        
        table_layout.addWidget(self._empty_widget)
        self._empty_widget.setVisible(False)
        
        layout.addWidget(table_container, 1)

        scroll.setWidget(content)
        root.addWidget(scroll)

        self._cases: list[dict] = []

        # Wire up search and filter
        self.search_box.textChanged.connect(self._on_search)
        for label, btn in self._filter_btns.items():
            btn.clicked.connect(lambda checked, l=label: self._on_filter_clicked(l))

    def load_cases(self, cases: list[dict]):
        """Load cases into table. Each dict from TaskRecord.to_dict()."""
        self._cases = cases
        self.table.setRowCount(0)

        if not cases:
            self._empty_widget.setVisible(True)
            self.table.setVisible(False)
            return

        self._empty_widget.setVisible(False)
        self.table.setVisible(True)

        for c in cases:
            row = self.table.rowCount()
            self.table.insertRow(row)

            task_id = c.get("task_id", "")
            # Build summary from available fields
            summary = c.get("fact_summary", "") or f"{c.get('identity', '')} · {c.get('goal', '')}"
            if not summary.strip():
                summary = task_id
            identity = c.get("identity", "")
            status = c.get("status", "未知")
            rating = c.get("rating", "") or "—"
            created_at = c.get("created_at", "")

            from PySide6.QtWidgets import QTableWidgetItem

            id_item = QTableWidgetItem(task_id[:16] if len(task_id) > 16 else task_id)
            id_item.setToolTip(task_id)
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(summary))
            self.table.setItem(row, 2, QTableWidgetItem(identity))

            status_item = QTableWidgetItem(status)
            color = _STATUS_COLORS.get(status, "#b0b0b8")
            status_item.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row, 3, status_item)
            self.table.setItem(row, 4, QTableWidgetItem(rating))
            self.table.setItem(row, 5, QTableWidgetItem(created_at))

            # Store task_id in first column for retrieval
            id_item.setData(Qt.ItemDataRole.UserRole, task_id)

    def _on_row_double_clicked(self, index):
        row = index.row()
        id_item = self.table.item(row, 0)
        if id_item:
            task_id = id_item.data(Qt.ItemDataRole.UserRole)
            if task_id:
                self.case_selected.emit(task_id)

    def filter_by_status(self, status: str):
        if status == "全部":
            self.load_cases(self._cases)
            return
        filtered = [c for c in self._cases if c.get("status") == status]
        self.load_cases(filtered)

    def _on_search(self, text: str):
        """Filter cases by search text across all fields."""
        if not text.strip():
            self.load_cases(self._cases)
            return
        text_lower = text.lower()
        filtered = [
            c for c in self._cases
            if text_lower in c.get("task_id", "").lower()
            or text_lower in c.get("identity", "").lower()
            or text_lower in c.get("goal", "").lower()
            or text_lower in c.get("fact_summary", "").lower()
            or text_lower in c.get("status", "").lower()
        ]
        self._apply_filters(filtered)

    def _on_filter_clicked(self, status: str):
        """Handle filter button click — uncheck others, apply filter."""
        for label, btn in self._filter_btns.items():
            btn.setChecked(label == status)
        self._apply_filters(self._cases)

    def _apply_filters(self, base_cases: list[dict]):
        """Apply current search + status filter to a base list."""
        # Determine active status filter
        active_status = "全部"
        for label, btn in self._filter_btns.items():
            if btn.isChecked():
                active_status = label
                break

        cases = base_cases
        if active_status != "全部":
            cases = [c for c in cases if c.get("status") == active_status]

        # Apply search text
        search_text = self.search_box.text().strip().lower()
        if search_text:
            cases = [
                c for c in cases
                if search_text in c.get("task_id", "").lower()
                or search_text in c.get("identity", "").lower()
                or search_text in c.get("goal", "").lower()
                or search_text in c.get("fact_summary", "").lower()
            ]

        self.load_cases(cases)
