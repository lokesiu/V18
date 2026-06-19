"""Result card component for V18."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QSizePolicy, QWidget,
    QApplication, QTextBrowser, QFrame, QListWidgetItem,
)

from qfluentwidgets import (
    SimpleCardWidget, SubtitleLabel, BodyLabel, CaptionLabel,
    PrimaryPushButton, PushButton, FluentIcon, InfoBar, ListWidget,
)


class ResultCard(SimpleCardWidget):
    """Card displaying analysis results or error states."""

    reanalyze_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.output_dir: str = ""
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._setup_ui()

    def _setup_ui(self):
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setSpacing(12)
        self._main_layout.setContentsMargins(24, 20, 24, 20)

        self._title = SubtitleLabel("分析结果")
        self._title.setStyleSheet("font-size: 14px; font-weight: 600; color: #0F172A;")
        self._main_layout.addWidget(self._title)

        self._content_layout = QVBoxLayout()
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(12)
        self._main_layout.addLayout(self._content_layout)

    def _clear_content(self):
        """Remove all widgets from the dynamic content area."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
            sub = item.layout()
            if sub:
                while sub.count():
                    sub_item = sub.takeAt(0)
                    sw = sub_item.widget()
                    if sw:
                        sw.setParent(None)
                        sw.deleteLater()

    def show_results(
        self,
        case_type: str,
        rating: str,
        file_count: int,
        output_dir: str,
        rendered_files: list[str] | None = None,
        warnings: list[str] | None = None,
    ):
        self.output_dir = output_dir
        self._clear_content()

        # ① Warning box (if any)
        if warnings:
            warning_box = self._build_warning_box(warnings)
            self._content_layout.addWidget(warning_box)

        # ② Info labels
        info = QWidget()
        info.setStyleSheet("background: transparent;")
        info_lay = QVBoxLayout(info)
        info_lay.setContentsMargins(0, 0, 0, 0)
        info_lay.setSpacing(4)
        for text in (
            f"案件类型：{case_type}",
            f"综合评级：{rating}",
            f"输出文件：{file_count} 个",
            f"输出目录：{output_dir}",
        ):
            lbl = BodyLabel(text)
            lbl.setStyleSheet("color: #475569; font-size: 12px;")
            info_lay.addWidget(lbl)
        self._content_layout.addWidget(info)

        # ③ File list (minimum height 150)
        if rendered_files:
            file_list = self._build_file_list(rendered_files)
            self._content_layout.addWidget(file_list)

        # ④ Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        open_btn = PrimaryPushButton("打开输出文件夹")
        open_btn.setIcon(FluentIcon.FOLDER)
        open_btn.clicked.connect(self._open_output_folder)
        btn_row.addWidget(open_btn)

        copy_btn = PushButton("复制路径")
        copy_btn.setIcon(FluentIcon.COPY)
        copy_btn.clicked.connect(self._copy_path)
        btn_row.addWidget(copy_btn)

        if not warnings:
            re_btn = PushButton("重新分析")
            re_btn.setIcon(FluentIcon.SYNC)
            re_btn.clicked.connect(self.reanalyze_clicked.emit)
            btn_row.addWidget(re_btn)

        btn_row.addStretch()
        self._content_layout.addLayout(btn_row)

        self._title.setText("分析结果")
        self.setVisible(True)
        self.update()
        self.adjustSize()

    def show_export_error(
        self,
        title: str = "文档生成失败",
        description: str = "",
        output_dir: str = "",
        error_details: str = "",
    ):
        if not description:
            description = "文档渲染过程中出现错误。"
        if output_dir:
            self.output_dir = output_dir

        self._clear_content()

        err_box = QFrame()
        err_box.setStyleSheet(
            "QFrame { background-color: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 16px; }"
        )
        lay = QVBoxLayout(err_box)
        lay.setSpacing(8)

        t = BodyLabel(title)
        t.setStyleSheet("color: #991B1B; font-weight: 600; font-size: 14px;")
        lay.addWidget(t)

        d = BodyLabel(description)
        d.setStyleSheet("color: #991B1B; font-size: 12px;")
        d.setWordWrap(True)
        lay.addWidget(d)

        if error_details:
            tb = QTextBrowser()
            tb.setMinimumHeight(80)
            tb.setMaximumHeight(160)
            tb.setPlainText(error_details)
            tb.setStyleSheet(
                "QTextBrowser { background: #FEE2E2; border: 1px solid #FECACA; "
                "border-radius: 4px; color: #991B1B; font-size: 11px; "
                "font-family: Consolas, monospace; padding: 8px; }"
            )
            lay.addWidget(tb)

        re = PushButton("重新分析")
        re.setIcon(FluentIcon.SYNC)
        re.clicked.connect(self.reanalyze_clicked.emit)
        lay.addWidget(re, 0, Qt.AlignmentFlag.AlignLeft)

        self._content_layout.addWidget(err_box)

        if rendered_files := (self._get_last_rendered_files()):
            self._content_layout.addWidget(self._build_file_list(rendered_files))

        self._title.setText("分析结果")
        self.setVisible(True)
        self.update()
        self.adjustSize()

    def show_error(self, title: str = "分析失败", description: str = "", error_details: str = ""):
        self.show_export_error(title=title, description=description, error_details=error_details)

    def hide_results(self):
        self._clear_content()
        self.setVisible(False)

    # ── Builders ──────────────────────────────────────────────────────

    def _build_warning_box(self, warnings: list[str]) -> QFrame:
        box = QFrame()
        box.setStyleSheet(
            "QFrame { background-color: #FFFBEB; border: 1px solid #FDE68A; "
            "border-radius: 8px; padding: 12px; }"
        )
        lay = QVBoxLayout(box)
        lay.setSpacing(6)

        hdr = BodyLabel(f"质量预警 — {len(warnings)} 项未通过")
        hdr.setStyleSheet("color: #92400E; font-weight: 600; font-size: 12px;")
        lay.addWidget(hdr)

        tb = QTextBrowser()
        tb.setMinimumHeight(100)
        tb.setMaximumHeight(200)
        tb.setPlainText("\n".join(f"• {w}" for w in warnings))
        tb.setStyleSheet(
            "QTextBrowser { background: #FEF3C7; border: 1px solid #FDE68A; "
            "border-radius: 4px; color: #92400E; font-size: 11px; "
            "font-family: Consolas, monospace; padding: 6px; }"
        )
        lay.addWidget(tb)
        return box

    def _build_file_list(self, files: list[str]) -> QWidget:
        container = QFrame()
        container.setStyleSheet(
            "QFrame { background: #F8FAFC; border: 1px solid #E2E8F0; "
            "border-radius: 8px; padding: 8px; }"
        )
        container.setMinimumHeight(120)
        lay = QVBoxLayout(container)
        lay.setSpacing(4)
        lay.setContentsMargins(8, 8, 8, 8)

        hdr = BodyLabel(f"已生成文件（{len(files)} 个）")
        hdr.setStyleSheet("color: #334155; font-weight: 600; font-size: 12px;")
        lay.addWidget(hdr)

        list_widget = ListWidget()
        list_widget.setMinimumHeight(120)
        for f in files:
            item = QListWidgetItem(Path(f).name)
            list_widget.addItem(item)
        lay.addWidget(list_widget)

        self._last_rendered_files = files
        return container

    def _get_last_rendered_files(self) -> list[str]:
        return getattr(self, "_last_rendered_files", [])

    # ── Actions ───────────────────────────────────────────────────────

    def _open_output_folder(self):
        if self.output_dir and Path(self.output_dir).exists():
            subprocess.Popen(["explorer", self.output_dir])

    def _copy_path(self):
        if self.output_dir:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(self.output_dir)
                InfoBar.success("已复制", "路径已复制到剪贴板", parent=self.window())
