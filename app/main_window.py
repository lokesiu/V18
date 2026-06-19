"""明证台 V18 Beta — Multi-page legal workbench."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget

from qfluentwidgets import (
    FluentWindow, setTheme, Theme,
    InfoBar,
    FluentIcon, NavigationItemPosition,
)

from app.worker import AnalysisWorker, PIPELINE_STAGES
from app.pages.home_page import HomePage
from app.pages.case_list_page import CaseListPage
from app.pages.case_detail_page import CaseDetailPage
from app.pages.settings_page import SettingsPage
from app.pages.audit_page import AuditPage


# ── Main Window ───────────────────────────────────────────────────────
class MainWindow(FluentWindow):
    """明证台 — Multi-page Legal Workbench"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("明证台")
        self.setMinimumSize(960, 680)

        # Follow system theme — no manual override
        setTheme(Theme.AUTO)

        self.worker: AnalysisWorker | None = None
        self._current_task_id: str = ""
        self._setup_pages()

    # ── Page Setup ────────────────────────────────────────────────────
    def _setup_pages(self) -> None:
        # Create pages
        self.home_page = HomePage()
        self.case_list_page = CaseListPage()
        self.case_detail_page = CaseDetailPage()
        self.settings_page_widget = SettingsPage()
        self.audit_page = AuditPage()

        # Set objectName BEFORE addSubInterface (required by qfluentwidgets)
        self.home_page.setObjectName("home_page")
        self.case_list_page.setObjectName("case_list_page")
        self.case_detail_page.setObjectName("case_detail_page")
        self.settings_page_widget.setObjectName("settings_page")
        self.audit_page.setObjectName("audit_page")

        # Add to navigation — order determines nav position
        self.addSubInterface(self.home_page, FluentIcon.HOME, "首页")
        self.addSubInterface(self.case_list_page, FluentIcon.LABEL, "案件列表")
        self.addSubInterface(self.audit_page, FluentIcon.HISTORY, "审计日志")
        self.addSubInterface(
            self.settings_page_widget, FluentIcon.SETTING, "设置",
            NavigationItemPosition.BOTTOM,
        )

        # Case detail is accessible via case selection, hidden from nav
        self._case_detail_nav = self.addSubInterface(
            self.case_detail_page, FluentIcon.DOCUMENT, "案件详情"
        )
        self._case_detail_nav.setVisible(False)

        # Wire up signals
        self._connect_signals()

        # Load initial data
        self._load_initial_data()

    def _hide_nav_item(self, page: QWidget):
        """Hide a page from the left navigation bar."""
        if hasattr(self, '_case_detail_nav') and self._case_detail_nav:
            self._case_detail_nav.setVisible(False)

    def _show_nav_item(self, page: QWidget):
        """Show a page in the left navigation bar."""
        if hasattr(self, '_case_detail_nav') and self._case_detail_nav:
            self._case_detail_nav.setVisible(True)

    def _connect_signals(self):
        # Home page signals
        self.home_page.analysis_requested.connect(self._start_analysis)
        self.home_page.settings_requested.connect(
            lambda: self.switchTo(self.settings_page_widget)
        )

        # Case list signals
        self.case_list_page.case_selected.connect(self._navigate_to_case)
        self.case_list_page.refresh_btn.clicked.connect(self._refresh_recent_cases)

        # Case detail signals
        self.case_detail_page.back_requested.connect(
            lambda: self.switchTo(self.home_page)
        )

        # Settings signals
        self.settings_page_widget.settings_changed.connect(self._on_settings_changed)

        # Audit page signals
        self.audit_page.refresh_btn.clicked.connect(self._refresh_audit)

    def _load_initial_data(self):
        """Load initial data for pages."""
        # Load recent cases (will be empty until task_store exists)
        self._refresh_recent_cases()

    def _refresh_recent_cases(self):
        """Refresh recent cases from task store."""
        try:
            from core.task_store import get_task_store
            ts = get_task_store()
            all_tasks = ts.list_all()
            all_dicts = [r.to_dict() for r in all_tasks]
            self.case_list_page.load_cases(all_dicts)
        except Exception:
            self.case_list_page.load_cases([])

    # ── Navigation ────────────────────────────────────────────────────
    def _navigate_to_case(self, task_id: str):
        """Navigate to case detail page for the given task_id."""
        self._current_task_id = task_id

        # Load task data
        task_data = self._load_task_data(task_id)
        if task_data:
            self.case_detail_page.load_task(task_data)

        # Show case detail in nav and switch to it
        self._case_detail_nav.setVisible(True)
        self.switchTo(self.case_detail_page)

    def _load_task_data(self, task_id: str) -> dict | None:
        """Load task data from store or outputs directory."""
        try:
            from core.task_store import get_task_store
            ts = get_task_store()
            rec = ts.get_task(task_id)
            if rec:
                return rec.to_dict()
        except Exception:
            pass
        # Fallback: scan outputs directory
        return self._scan_output_for_task(task_id)

    def _scan_output_for_task(self, task_id: str) -> dict | None:
        """Fallback: scan outputs directory for a case matching task_id."""
        outputs = Path("outputs")
        if not outputs.exists():
            return None
        for d in sorted(outputs.iterdir(), reverse=True):
            if d.is_dir() and task_id.startswith(d.name[:8]):
                return self._build_task_from_output_dir(d)
        return None

    def _build_task_from_output_dir(self, case_dir: Path) -> dict:
        """Build a task dict from an output directory."""
        task = {
            "task_id": case_dir.name,
            "identity": "被诉方（被告）",
            "goal": "应诉答辩",
            "status": "未知",
            "rating": "N/A",
            "created_at": case_dir.stat().st_mtime,
            "updated_at": case_dir.stat().st_mtime,
            "output_dir": str(case_dir),
            "file_list": [],
            "rendered_files": [],
            "current_step": 0,
            "fact_summary": "",
        }

        # Check for distilled card (in _internal subfolder)
        card_path = case_dir / "_internal" / "distilled_card.json"
        if card_path.exists():
            try:
                with open(card_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                task["rating"] = data.get("strategy_card", {}).get("sabcd_rating", "N/A")
                fc = data.get("fact_card", {})
                if fc.get("identity"):
                    task["identity"] = fc["identity"]
                key_facts = fc.get("key_facts", [])
                if key_facts:
                    task["fact_summary"] = "; ".join(key_facts[:3])
                task["status"] = "已完成"
                task["current_step"] = 8
            except Exception:
                pass

        # Check for rendered files
        customer_dir = case_dir / "customer"
        if customer_dir.exists():
            task["rendered_files"] = [str(f) for f in customer_dir.iterdir() if f.is_file()]
            if task["rendered_files"]:
                task["status"] = "已完成"

        return task

    # ── Analysis Flow ─────────────────────────────────────────────────
    def _start_analysis(self, files: list[str], identity: str, goal: str, purpose: str = ""):
        """Start analysis from home page request."""
        # Disable home page quick start
        self.home_page.set_quick_start_enabled(False)

        # Create worker
        self.worker = AnalysisWorker(files, identity, goal, purpose=purpose)
        self.worker.task_created.connect(self._on_task_created)
        self.worker.stage_started.connect(self._on_stage_started)
        self.worker.stage_done.connect(self._on_stage_done)
        self.worker.stage_failed.connect(self._on_stage_failed)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.finished_with_files.connect(self._on_finished_with_files)
        self.worker.error_occurred.connect(self._on_error_occurred)
        self.worker.start()

        # Navigate to a temporary case detail view (will update when task_created fires)
        temp_task = {
            "task_id": "创建中...",
            "identity": identity,
            "goal": goal,
            "status": "进行中",
            "rating": "—",
            "created_at": "—",
            "updated_at": "—",
            "output_dir": "",
            "file_list": files,
            "rendered_files": [],
            "current_step": 0,
        }
        self.case_detail_page.load_task(temp_task)
        self.case_detail_page.progress_timeline.reset()
        self._case_detail_nav.setVisible(True)
        self.switchTo(self.case_detail_page)

        InfoBar.info("开始分析", "案件分析已启动", parent=self)

    def _on_task_created(self, task_id: str):
        """Called when worker has persisted the task to task_store."""
        self._current_task_id = task_id
        # Update case detail title with real task_id
        self.case_detail_page._title_label.setText(f"案件详情 — {task_id[:16]}")

    def _on_stage_started(self, stage: str):
        self.case_detail_page.progress_timeline.set_stage_by_name(stage, "running")

    def _on_stage_done(self, stage: str):
        self.case_detail_page.progress_timeline.set_stage_by_name(stage, "done")

    def _on_stage_failed(self, stage: str, error: str):
        self.case_detail_page.progress_timeline.set_stage_failed_by_name(stage, error)

    def _on_error_occurred(self, error_title: str, error_details: str):
        """Handle error signal from worker - show error in timeline notice."""
        self.case_detail_page.progress_timeline.error_notice.show_notice(
            title=error_title,
            description=error_details,
        )

    def _on_progress(self, value: int):
        pass

    def _on_finished(self, success: bool, output_dir: str):
        self.home_page.set_quick_start_enabled(True)

    def _on_finished_with_files(self, success: bool, output_dir: str, rendered_files: list[str]):
        timeline = self.case_detail_page.progress_timeline

        if success:
            # Force-complete all timeline stages
            timeline.finish_all("done")

            # Check for quality warnings from worker
            warnings = []
            has_warnings = False
            if self.worker and hasattr(self.worker, '_quality_warnings'):
                warnings = self.worker._quality_warnings
                has_warnings = bool(warnings)

            if has_warnings:
                self.case_detail_page._status_badge.setText("已完成")
            else:
                self.case_detail_page._status_badge.setText("已完成")

            rating, _ = self._read_result_data(output_dir)
            self.case_detail_page.result_card.show_results(
                case_type=self.home_page.identity_goal_grid.currentIdentity(),
                rating=rating,
                file_count=len(rendered_files),
                output_dir=output_dir,
                rendered_files=rendered_files,
                warnings=warnings,
            )
            if not has_warnings:
                InfoBar.success("分析完成", "所有文档已生成", parent=self)
        else:
            # Force-stop: mark non-terminal stages as failed
            timeline.finish_remaining_as("failed")
            self.case_detail_page._status_badge.setText("失败")

            # Get detailed error info from task store
            error_details = self._get_failure_details(output_dir)

            if rendered_files:
                self.case_detail_page.result_card.show_export_error(
                    title="部分文档生成失败",
                    description=f"已生成 {len(rendered_files)} 个文件，但部分文档渲染失败。",
                    output_dir=output_dir,
                    error_details=error_details,
                )
            else:
                self.case_detail_page.result_card.show_error(
                    title="分析失败",
                    description="分析过程中出现错误。请检查材料文件后重试。",
                    error_details=error_details,
                )

        # Refresh case lists
        self._refresh_recent_cases()

    def _get_failure_details(self, output_dir: str) -> str:
        """Get detailed failure information from task store manifest."""
        details_parts = []
        try:
            from core.task_store import get_task_store
            ts = get_task_store()
            if hasattr(self, '_current_task_id') and self._current_task_id:
                entries = ts.manifest_list_entries(self._current_task_id)
                failed = [e for e in entries if e.get("status") == "failed"]
                if failed:
                    lines = []
                    for e in failed:
                        fname = e.get("file_name", "?")
                        err_code = e.get("error_code", "")
                        err_msg = e.get("error_msg", "")
                        lines.append(f"  - {fname}: [{err_code}] {err_msg}")
                    details_parts.append("失败文件:\n" + "\n".join(lines))
        except Exception as e:
            details_parts.append(f"获取任务详情失败: {e}")

        # Also check worker error log
        if self.worker and hasattr(self.worker, '_last_error') and self.worker._last_error:
            details_parts.append(f"Worker 错误: {self.worker._last_error}")

        return "\n\n".join(details_parts) if details_parts else ""

    def _read_result_data(self, output_dir: str) -> tuple[str, int]:
        rating = "N/A"
        file_count = 0
        try:
            out_path = Path(output_dir)
            card_path = out_path / "_internal" / "distilled_card.json"
            if card_path.exists():
                with open(card_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                rating = data.get("strategy_card", {}).get("sabcd_rating", "N/A")
            customer_dir = out_path / "customer"
            if customer_dir.exists() and customer_dir.is_dir():
                file_count = sum(1 for _ in customer_dir.iterdir())
        except Exception:
            pass
        return rating, file_count

    # ── Audit ─────────────────────────────────────────────────────────
    def _refresh_audit(self):
        """Refresh audit page with latest events from audit_store."""
        try:
            from core.audit_store import get_audit_store
            aus = get_audit_store()
            events = aus.list_recent_events(200)
            entries = [e.to_dict() for e in events]
            self.audit_page.load_entries(entries)
        except Exception:
            self.audit_page.load_entries([])

    # ── Settings ──────────────────────────────────────────────────────
    def _on_settings_changed(self):
        self.home_page.ai_status_card.update_from_settings()


# ── Entry point ───────────────────────────────────────────────────────
def main() -> None:
    app = QApplication(sys.argv)

    # CJK font hint
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
