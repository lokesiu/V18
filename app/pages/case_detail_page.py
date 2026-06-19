"""app/pages/case_detail_page.py — 案件详情页（案件控制台）.

No hardcoded styles — let QFluentWidgets Theme.DARK handle everything.
"""
from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QListWidget,
)

from qfluentwidgets import (
    HeaderCardWidget,
    StrongBodyLabel, BodyLabel, CaptionLabel,
    PushButton, FluentIcon, TabWidget,
    ScrollArea, InfoBar,
)

from app.widgets.progress_timeline import ProgressTimeline
from app.widgets.result_card import ResultCard
from app.widgets.notice import InlineNotice


# ── Status Badge ──────────────────────────────────────────────────────

def _make_status_badge(status: str) -> CaptionLabel:
    badge = CaptionLabel(status)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setFixedWidth(72)
    return badge


# ── Case Detail Page ──────────────────────────────────────────────────

class CaseDetailPage(QWidget):
    """案件详情 — 案件控制台."""

    back_requested = Signal()
    reanalyze_requested = Signal()
    retry_render_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._task_id = ""
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
        layout.setSpacing(20)
        layout.setContentsMargins(48, 20, 48, 48)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_summary_card())

        self.result_card = ResultCard()
        self.result_card.reanalyze_clicked.connect(self.reanalyze_requested.emit)
        layout.addWidget(self.result_card)

        self._quality_notice = InlineNotice(kind="error", title="", description="", parent=self)
        layout.addWidget(self._quality_notice)

        layout.addWidget(self._build_tabs())
        layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        header.setFixedHeight(56)
        h = QHBoxLayout(header)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(16)

        self.back_btn = PushButton("返回")
        self.back_btn.setIcon(FluentIcon.LEFT_ARROW)
        self.back_btn.clicked.connect(self.back_requested.emit)
        h.addWidget(self.back_btn)

        self._title_label = StrongBodyLabel("案件详情")
        h.addWidget(self._title_label, 1)

        self._status_badge = _make_status_badge("待处理")
        h.addWidget(self._status_badge)

        self._updated_label = CaptionLabel("")
        h.addWidget(self._updated_label)

        self._retry_btn = PushButton("重试失败文件")
        self._retry_btn.setIcon(FluentIcon.SYNC)
        self._retry_btn.clicked.connect(self._on_retry_clicked)
        self._retry_btn.setVisible(False)
        h.addWidget(self._retry_btn)

        self._open_dir_btn = PushButton("打开目录")
        self._open_dir_btn.setIcon(FluentIcon.FOLDER)
        self._open_dir_btn.setVisible(False)
        h.addWidget(self._open_dir_btn)

        return header

    def _build_summary_card(self) -> QWidget:
        card = HeaderCardWidget()
        card.setTitle("案件摘要")
        card.setBorderRadius(8)
        body = QVBoxLayout()
        body.setSpacing(12)
        card.viewLayout.addLayout(body)

        self._summary_fields: dict[str, BodyLabel] = {}
        for label_text in ["身份", "目的", "文件数", "评级", "输出目录", "更新时间"]:
            row = QHBoxLayout()
            row.setSpacing(12)
            lbl = CaptionLabel(label_text)
            lbl.setFixedWidth(64)
            row.addWidget(lbl)
            val = BodyLabel("—")
            row.addWidget(val, 1)
            body.addLayout(row)
            self._summary_fields[label_text] = val
        return card

    def _build_tabs(self) -> QWidget:
        self.tab_view = TabWidget()

        # Style the tab bar to look like modern navigation
        self.tab_view.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background: #FFFFFF;
            }
            QTabBar::tab {
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 500;
                color: #64748B;
                background: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                margin: 0 4px;
            }
            QTabBar::tab:selected {
                color: #2563EB;
                border-bottom: 2px solid #2563EB;
            }
            QTabBar::tab:hover {
                color: #1E293B;
            }
            QTabBar::close-button {
                image: none;
                width: 0px;
                height: 0px;
            }
        """)

        self._materials_tab = self._build_materials_tab()
        self.tab_view.addTab(self._materials_tab, "材料", FluentIcon.DOCUMENT)
        self._analysis_tab = self._build_analysis_tab()
        self.tab_view.addTab(self._analysis_tab, "分析过程", FluentIcon.SPEED_HIGH)
        self._delivery_tab = self._build_delivery_tab()
        self.tab_view.addTab(self._delivery_tab, "文书交付", FluentIcon.ZIP_FOLDER)
        self._audit_tab = self._build_audit_tab()
        self.tab_view.addTab(self._audit_tab, "审计记录", FluentIcon.HISTORY)

        # Remove close buttons from tabs
        self.tab_view.setTabsClosable(False)

        return self.tab_view

    def _build_materials_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Use QListWidget for clean file display
        self._materials_list_widget = QListWidget()
        self._materials_list_widget.setStyleSheet("""
            QListWidget {
                border: none;
                background: transparent;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #F1F5F9;
                color: #334155;
                background: transparent;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
            QListWidget::item:hover {
                background: #F8FAFC;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self._materials_list_widget)

        return widget

    def _build_analysis_tab(self) -> QWidget:
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        self.progress_timeline = ProgressTimeline()
        self.progress_timeline.setVisible(True)
        layout.addWidget(self.progress_timeline)
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_delivery_tab(self) -> QWidget:
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        self._manifest_widget = QWidget()
        self._manifest_widget.setVisible(False)
        mf_layout = QVBoxLayout(self._manifest_widget)
        mf_layout.setContentsMargins(0, 0, 0, 0)
        mf_layout.setSpacing(4)
        self._manifest_list = QVBoxLayout()
        mf_layout.addLayout(self._manifest_list)
        layout.addWidget(self._manifest_widget)
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_audit_tab(self) -> QWidget:
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)
        self._audit_entries = QVBoxLayout()
        layout.addLayout(self._audit_entries)
        self._audit_empty = CaptionLabel("暂无审计记录")
        self._audit_entries.addWidget(self._audit_empty)
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    # ── Public API ────────────────────────────────────────────────────
    def load_task(self, task: dict):
        self._task_id = task.get("task_id", "")
        self._title_label.setText(f"案件详情 — {self._task_id[:16]}")

        status = task.get("status", "未知")
        self._status_badge.setText(status)

        updated = str(task.get("updated_at", ""))
        self._updated_label.setText(updated[-16:] if len(updated) > 16 else updated)

        field_map = {
            "身份": task.get("identity", "—"),
            "目的": task.get("goal", "—"),
            "文件数": str(len(task.get("file_list", []))),
            "评级": task.get("rating", "—") or "—",
            "输出目录": task.get("output_dir", "—") or "—",
            "更新时间": updated,
        }
        for k, v in field_map.items():
            if k in self._summary_fields:
                self._summary_fields[k].setText(str(v) if v else "—")

        rendered_files = task.get("rendered_files", [])
        if rendered_files and status in ("已完成", "部分完成"):
            self.result_card.show_results(
                case_type=task.get("identity", ""),
                rating=task.get("rating", "N/A"),
                file_count=len(rendered_files),
                output_dir=task.get("output_dir", ""),
                rendered_files=rendered_files,
            )
        else:
            self.result_card.hide_results()

        quality_blocked = task.get("quality_blocked", 0)
        if quality_blocked:
            self._quality_notice.hide_notice()
        else:
            self._quality_notice.hide_notice()

        self._retry_btn.setVisible(status in ("部分完成", "失败"))
        self._open_dir_btn.setVisible(bool(task.get("output_dir", "")))

        current_step = task.get("current_step", 0)
        self._update_progress(current_step, status)

        self._load_materials(task.get("file_list", []))
        self._load_manifest(self._task_id)
        self._load_audit_events(self._task_id)

    def _update_progress(self, current_step: int, status: str):
        pct = int((current_step / 8) * 100) if status != "失败" else int(((current_step + 0.5) / 8) * 100)
        self.progress_timeline.progress_bar.setValue(pct)
        step_names = ["读取材料", "提取事实", "事实蒸馏", "策略推演", "蒸馏合并", "文书生成", "文档渲染", "质量检查"]
        if status in ("已完成", "部分完成"):
            self.progress_timeline.finish_all("done")
        elif status == "失败":
            stage_name = step_names[min(current_step, 7)]
            self.progress_timeline.error_notice.show_notice(
                title=f"{stage_name}失败",
                description=f"分析在「{stage_name}」步骤失败，请检查材料后重试。",
            )

        for i in range(8):
            if i < current_step:
                self.progress_timeline.set_stage_status(i, "done")
            elif i == current_step:
                st = "failed" if status in ("失败", "质量拦截") else "running" if status == "进行中" else "done"
                self.progress_timeline.set_stage_status(i, st)
            else:
                self.progress_timeline.set_stage_status(i, "waiting")

    def _show_quality_notice(self, stage: str, issues: list):
        if not issues:
            self._quality_notice.hide_notice()
            return
        stage_label = "事实提取" if stage == "step2" else "事实增强"
        msgs = []
        for issue in issues:
            msg = issue.get("message", "")
            msgs.append(f"• {msg}")
        self._quality_notice.show_notice(title=f"质量门禁拦截 — {stage_label}", description="\n".join(msgs))

    def _load_materials(self, files: list[str]):
        self._materials_list_widget.clear()

        if not files:
            self._materials_list_widget.addItem("暂无材料信息")
            return

        from pathlib import Path
        for f in files:
            name = Path(f).name
            self._materials_list_widget.addItem(name)

    def _load_manifest(self, task_id: str):
        while self._manifest_list.count():
            item = self._manifest_list.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        try:
            from core.pipeline.step7_render_manifest import get_manifest_entries
            entries = get_manifest_entries(task_id)
        except Exception:
            entries = []
        if not entries:
            self._manifest_widget.setVisible(False)
            return
        self._manifest_widget.setVisible(True)
        _ICONS = {"success": "✅", "failed": "❌", "pending": "⏳", "skipped": "⏭️"}
        for entry in entries:
            fname = entry.get("file_name", "")
            estatus = entry.get("status", "pending")
            fsize = entry.get("file_size", 0)
            icon = _ICONS.get(estatus, "?")
            size_str = f"{fsize:,} B" if fsize > 0 else ""
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(4, 1, 4, 1)
            rl.setSpacing(6)
            rl.addWidget(CaptionLabel(icon))
            rl.addWidget(CaptionLabel(fname), 1)
            if size_str:
                rl.addWidget(CaptionLabel(size_str))
            self._manifest_list.addWidget(row)

    def _load_audit_events(self, task_id: str):
        while self._audit_entries.count():
            item = self._audit_entries.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        try:
            from core.audit_store import get_audit_store
            aus = get_audit_store()
            events = aus.get_events_for_task(task_id)
        except Exception:
            events = []
        if not events:
            self._audit_empty = CaptionLabel("暂无审计记录")
            self._audit_entries.addWidget(self._audit_empty)
            return
        for e in events:
            d = e.to_dict()
            time_str = d.get("created_at", "")[-8:]
            message = d.get("message", "")
            row_w = QWidget()
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(4, 2, 4, 2)
            rl.setSpacing(8)
            tl = CaptionLabel(time_str)
            tl.setFixedWidth(60)
            rl.addWidget(tl)
            rl.addWidget(CaptionLabel(message[:100]), 1)
            self._audit_entries.addWidget(row_w)

    def _on_retry_clicked(self):
        if not self._task_id:
            return
        self._retry_btn.setEnabled(False)
        self._retry_btn.setText("重试中...")
        try:
            from core.pipeline.step7_render_manifest import retry_render
            result = retry_render(self._task_id, emit_log=lambda m: None)
            self._load_manifest(self._task_id)
            try:
                from core.task_store import get_task_store
                task = get_task_store().get_task(self._task_id)
                if task:
                    self.load_task(task.to_dict())
            except Exception:
                pass
            InfoBar.success("重试完成", f"成功: {result.get('succeeded', 0)}", parent=self.window())
        except Exception as exc:
            InfoBar.error("重试失败", str(exc), parent=self.window())
        finally:
            self._retry_btn.setEnabled(True)
            self._retry_btn.setText("重试失败文件")

    def get_progress_timeline(self):
        return self.progress_timeline

    def get_result_card(self):
        return self.result_card
