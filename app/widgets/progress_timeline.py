"""Progress timeline component for V18."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSizePolicy

from qfluentwidgets import (
    SimpleCardWidget, SubtitleLabel, BodyLabel, CaptionLabel,
    FluentIcon, ProgressBar
)

from app.widgets.notice import InlineNotice


# Must match core.pipeline.STAGE_NAMES order
STAGES = [
    ("读取材料", FluentIcon.DOCUMENT),
    ("提取事实", FluentIcon.LABEL),
    ("事实蒸馏", FluentIcon.SEARCH),
    ("策略推演", FluentIcon.VIEW),
    ("蒸馏合并", FluentIcon.CHECKBOX),
    ("文书生成", FluentIcon.EDIT),
    ("文档渲染", FluentIcon.ZIP_FOLDER),
    ("质量检查", FluentIcon.ACCEPT),
]


class ProgressTimeline(SimpleCardWidget):
    """Visual timeline showing pipeline stage progress."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.stage_widgets: list[QWidget] = []
        self._stage_name_to_index: dict[str, int] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(24, 20, 24, 16)

        title = SubtitleLabel("分析进度")
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #0F172A;")
        layout.addWidget(title)

        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        for idx, (stage_name, icon) in enumerate(STAGES):
            stage_widget = self._create_stage_item(stage_name, icon)
            self.stage_widgets.append(stage_widget)
            self._stage_name_to_index[stage_name] = idx
            layout.addWidget(stage_widget)

        # Inline error notice for stage failures
        self.error_notice = InlineNotice(
            kind="error",
            title="",
            description="",
            parent=self,
        )
        layout.addWidget(self.error_notice)

    def _create_stage_item(self, name: str, icon: FluentIcon) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        # Status dot (replaces icon label for cleaner look)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(
            "background-color: #D1D5DB; border-radius: 4px;"
        )
        layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)

        # Name
        name_label = BodyLabel(name)
        name_label.setMinimumWidth(80)
        layout.addWidget(name_label, 1)

        # Sub-status (e.g., "正在生成 PDF")
        sub_label = CaptionLabel("")
        sub_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        sub_label.setVisible(False)
        layout.addWidget(sub_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # Status text
        status_label = CaptionLabel("等待")
        status_label.setStyleSheet("color: #9CA3AF;")
        status_label.setFixedWidth(60)
        status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(status_label)

        widget._name_label = name_label
        widget._status_label = status_label
        widget._dot = dot
        widget._sub_label = sub_label

        return widget

    def reset(self):
        self.progress_bar.setValue(0)
        for i in range(len(self.stage_widgets)):
            self._set_visual(i, "waiting", "")
        self.error_notice.hide_notice()

    def finish_all(self, status: str = "done"):
        """Mark all stages as done (or failed) and set progress to 100%."""
        for i in range(len(self.stage_widgets)):
            cur = self.stage_widgets[i]._status_label.text()
            if cur not in ("完成", "失败"):
                self._set_visual(i, status, "")
        self.progress_bar.setValue(100)

    def finish_remaining_as(self, status: str = "done"):
        """Mark only non-terminal stages (waiting/running) as the given status."""
        for i in range(len(self.stage_widgets)):
            cur = self.stage_widgets[i]._status_label.text()
            if cur in ("等待", "进行中"):
                self._set_visual(i, status, "")
        self._update_progress()

    def set_stage_status(self, index: int, status: str):
        self._set_visual(index, status, "")
        self._update_progress()

    def set_stage_by_name(self, name: str, status: str, substatus: str = ""):
        """Set stage status by display name (from pipeline callback)."""
        idx = self._stage_name_to_index.get(name)
        if idx is not None:
            self._set_visual(idx, status, substatus)
            self._update_progress()

    def set_stage_failed_with_detail(self, index: int, error: str):
        self._set_visual(index, "failed", "")
        self._update_progress()
        if index < len(self.stage_widgets):
            stage_name = STAGES[index][0] if index < len(STAGES) else "未知阶段"
            self.error_notice.show_notice(
                title=f"{stage_name}失败",
                description=error if error else "该阶段处理过程中出现异常，请检查材料后重试。",
            )

    def set_stage_failed_by_name(self, name: str, error: str):
        """Show failure by stage display name."""
        idx = self._stage_name_to_index.get(name)
        if idx is not None:
            self._set_visual(idx, "failed", "")
            self._update_progress()
            self.error_notice.show_notice(
                title=f"{name}失败",
                description=error if error else "该阶段处理过程中出现异常，请检查材料后重试。",
            )

    def _set_visual(self, index: int, status: str, substatus: str):
        if index < 0 or index >= len(self.stage_widgets):
            return

        widget = self.stage_widgets[index]
        name_label = widget._name_label
        status_label = widget._status_label
        dot = widget._dot
        sub_label = widget._sub_label

        # Sub-status
        if substatus:
            sub_label.setText(substatus)
            sub_label.setVisible(True)
        else:
            sub_label.setVisible(False)

        if status == "waiting":
            status_label.setText("等待")
            status_label.setStyleSheet("color: #9CA3AF;")
            name_label.setStyleSheet("color: #6B7280;")
            dot.setStyleSheet("background-color: #D1D5DB; border-radius: 4px;")
            widget.setStyleSheet("")
        elif status == "running":
            status_label.setText("进行中")
            status_label.setStyleSheet("color: #2563EB; font-weight: 600;")
            name_label.setStyleSheet("color: #1F2937; font-weight: 600;")
            dot.setStyleSheet("background-color: #3b82f6; border-radius: 4px;")
            widget.setStyleSheet("background: #EFF6FF; border-radius: 4px;")
        elif status == "done":
            status_label.setText("完成")
            status_label.setStyleSheet("color: #16A34A;")
            name_label.setStyleSheet("color: #4B5563;")
            dot.setStyleSheet("background-color: #22c55e; border-radius: 4px;")
            widget.setStyleSheet("")
        elif status == "failed":
            status_label.setText("失败")
            status_label.setStyleSheet("color: #DC2626;")
            name_label.setStyleSheet("color: #DC2626;")
            dot.setStyleSheet("background-color: #EF4444; border-radius: 4px;")
            widget.setStyleSheet("background: #FEF2F2; border-radius: 4px;")

    def _update_progress(self):
        done_count = sum(
            1 for w in self.stage_widgets
            if w._status_label.text() in ("完成", "失败")
        )
        total = len(STAGES)
        self.progress_bar.setValue(int((done_count / total) * 100))
