"""Upload card component for V18 - Simplified with clean state management."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Set, Optional

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QWidget, QDialog,
    QListWidget, QListWidgetItem, QDialogButtonBox, QPushButton,
    QSizePolicy, QStackedWidget,
)

from qfluentwidgets import (
    CaptionLabel, PushButton, FluentIcon, InfoBar
)

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.doc', '.txt', '.md',
    '.png', '.jpg', '.jpeg', '.m4a', '.mp3', '.wav',
}

# Image extensions that trigger OCR processing
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}

# Legacy formats that can be converted
CONVERTIBLE_EXTENSIONS = {'.doc'}


def resolve_paths(paths: list[str]) -> list[str]:
    """Unified path resolver: handles files and folders recursively.

    Args:
        paths: List of file/folder paths (absolute or relative)

    Returns:
        Deduplicated list of absolute file paths with supported extensions
    """
    result_set: Set[str] = set()

    for path_str in paths:
        p = Path(path_str).resolve()

        if p.is_file():
            # Single file: check extension and add
            if p.suffix.lower() in SUPPORTED_EXTENSIONS:
                result_set.add(str(p))

        elif p.is_dir():
            # Directory: walk recursively and collect all supported files
            for root, dirs, files in os.walk(str(p)):
                for fname in files:
                    fpath = Path(root) / fname
                    if fpath.suffix.lower() in SUPPORTED_EXTENSIONS:
                        result_set.add(str(fpath.resolve()))

    return sorted(result_set)


def _scan_folder(folder: str, progress_callback=None) -> list[str]:
    """Recursively scan folder for supported files."""
    result = []
    folder_path = Path(folder)

    all_files = list(folder_path.rglob("*"))
    total = len(all_files)

    current = 0
    for f in all_files:
        current += 1
        if progress_callback:
            progress_callback(current, total)

        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            result.append(str(f))

    return sorted(set(result))


def _deduplicate_files(files: list[str]) -> list[str]:
    """Deduplicate files by path and by (name, size)."""
    seen_paths: Set[str] = set()
    seen_name_size: Set[tuple[str, int]] = set()
    result = []

    for f in files:
        norm_path = str(Path(f).resolve())
        if norm_path in seen_paths:
            continue

        try:
            p = Path(f)
            name = p.name.lower()
            size = p.stat().st_size
            key = (name, size)
            if key in seen_name_size:
                continue
            seen_name_size.add(key)
        except OSError:
            pass

        seen_paths.add(norm_path)
        result.append(f)

    return result


def _safe_process_file(filepath: str) -> tuple[Optional[str], Optional[str]]:
    """Safely process a file, returning path or warning."""
    try:
        p = Path(filepath)

        if not p.exists():
            return None, f"文件不存在: {p.name}"

        if not os.access(filepath, os.R_OK):
            return None, f"文件无法读取: {p.name}"

        size = p.stat().st_size
        if size == 0:
            return None, f"文件为空: {p.name}"

        text_extensions = {'.txt', '.md', '.doc', '.docx', '.pdf'}
        if p.suffix.lower() in text_extensions:
            try:
                with open(filepath, 'rb') as f:
                    f.read(1024)
            except Exception:
                return None, f"文件损坏: {p.name}"

        if p.suffix.lower() == '.pdf':
            try:
                with open(filepath, 'rb') as f:
                    header = f.read(5)
                    if header != b'%PDF-':
                        return None, f"PDF格式异常: {p.name}"
            except Exception:
                return None, f"PDF读取失败: {p.name}"

        return filepath, None

    except Exception as e:
        return None, f"处理失败 {Path(filepath).name}: {str(e)}"


def _find_converter() -> Optional[str]:
    """Find available document converter."""
    if shutil.which('pandoc'):
        return 'pandoc'
    elif shutil.which('libreoffice') or shutil.which('soffice'):
        return 'libreoffice'
    return None


def _convert_doc_to_docx(filepath: str, converter: str) -> Optional[str]:
    """Convert .doc file to .docx."""
    try:
        source = Path(filepath)
        if source.suffix.lower() != '.doc':
            return None

        target = source.with_suffix('.docx')

        if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
            return str(target)

        if converter == 'pandoc':
            cmd = ['pandoc', str(source), '-o', str(target), '--to=docx']
        elif converter in ('libreoffice', 'soffice'):
            cmd = [
                converter,
                '--headless',
                '--convert-to', 'docx',
                '--outdir', str(source.parent),
                str(source)
            ]
        else:
            return None

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0 and target.exists():
            return str(target)
        else:
            return None

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return None


def _convert_legacy_formats(files: list[str]) -> tuple[list[str], list[str]]:
    """Auto-convert legacy formats."""
    converter = _find_converter()
    result = []
    warnings = []

    for filepath in files:
        p = Path(filepath)

        if p.suffix.lower() == '.doc':
            if converter:
                converted = _convert_doc_to_docx(filepath, converter)
                if converted:
                    result.append(converted)
                    continue
                else:
                    warnings.append(f"转换失败: {p.name}")
            else:
                warnings.append(f"未找到转换工具: {p.name}")

        result.append(filepath)

    return result, warnings


class MaterialListDialog(QDialog):
    """Dialog showing full material list."""

    def __init__(self, files: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("材料清单")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        list_widget = QListWidget()
        for i, f in enumerate(files, 1):
            name = Path(f).name
            size = Path(f).stat().st_size if Path(f).exists() else 0
            size_str = f"{size:,} bytes" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
            list_widget.addItem(f"{i}. {name} ({size_str})")
        layout.addWidget(list_widget)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.close)
        layout.addWidget(btn_box)


class UploadCard(QWidget):
    """Upload component with clean state management using QStackedWidget."""

    files_selected = Signal(list)
    scanning_progress = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_files: list[str] = []
        self.warnings: list[str] = []
        self._is_scanning = False
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(280)
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main stacked widget for state switching
        self.stacked = QStackedWidget()
        self.stacked.setStyleSheet("background: transparent;")

        # State A: Empty state (drop zone)
        self.empty_state = self._build_empty_state()
        self.stacked.addWidget(self.empty_state)

        # State B: Files loaded state
        self.loaded_state = self._build_loaded_state()
        self.stacked.addWidget(self.loaded_state)

        layout.addWidget(self.stacked)

        # Start with empty state
        self.stacked.setCurrentIndex(0)

    def _build_empty_state(self) -> QWidget:
        """Build the empty state with drop zone."""
        widget = QWidget()
        widget.setCursor(Qt.CursorShape.PointingHandCursor)
        widget.setStyleSheet("""
            QWidget {
                border: 1.5px dashed #CBD5E1;
                border-radius: 10px;
                background-color: #F8FAFC;
            }
            QWidget:hover {
                border-color: #2563EB;
                background-color: #EFF6FF;
            }
        """)
        widget.mousePressEvent = lambda _: self._select_files()

        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("📁")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 40px; background: transparent; border: none;")
        layout.addWidget(icon_label)

        main_text = QLabel("拖拽或点击上传案卷材料")
        main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_text.setStyleSheet("""
            QLabel {
                color: #1E293B;
                font-size: 15px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(main_text)

        sub_text = QLabel("支持 PDF、Word、TXT、MD、图片、音频等格式")
        sub_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_text.setStyleSheet("""
            QLabel {
                color: #94A3B8;
                font-size: 12px;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(sub_text)

        return widget

    def _build_loaded_state(self) -> QWidget:
        """Build the loaded state with file list."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                border: 1.5px solid #BFDBFE;
                border-radius: 10px;
                background-color: #F0F7FF;
            }
        """)

        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self.summary_label = QLabel("")
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_label.setStyleSheet("""
            QLabel {
                color: #1E40AF;
                font-size: 16px;
                font-weight: 700;
                background: transparent;
                border: none;
                padding: 4px 0;
            }
        """)
        layout.addWidget(self.summary_label)

        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(180)
        self.file_list.setStyleSheet("""
            QListWidget {
                border: none;
                background: transparent;
                font-size: 12px;
                padding: 2px;
            }
            QListWidget::item {
                padding: 5px 10px;
                border-bottom: 1px solid #DBEAFE;
                color: #1E3A5F;
                background: transparent;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
            QListWidget::item:hover {
                background: #DBEAFE;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.file_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        add_more_btn = PushButton("添加更多")
        add_more_btn.setIcon(FluentIcon.ADD)
        add_more_btn.clicked.connect(self._select_files)
        btn_layout.addWidget(add_more_btn)

        clear_btn = PushButton("清空")
        clear_btn.setIcon(FluentIcon.DELETE)
        clear_btn.clicked.connect(self._clear_files)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()

        view_btn = PushButton("查看清单")
        view_btn.setIcon(FluentIcon.LIBRARY)
        view_btn.clicked.connect(self._view_material_list)
        btn_layout.addWidget(view_btn)

        layout.addLayout(btn_layout)

        return widget

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            return

        # Collect all paths (files and folders)
        raw_paths = [url.toLocalFile() for url in urls if url.toLocalFile()]

        # Use unified resolver to handle files and folders recursively
        resolved_files = resolve_paths(raw_paths)

        if resolved_files:
            self._process_files(resolved_files)

        event.acceptProposedAction()

    def _process_files(self, files: list[str]):
        """Process and add files."""
        processed_files = []
        warnings = []

        for filepath in files:
            safe_path, warning = _safe_process_file(filepath)
            if warning:
                warnings.append(warning)
            elif safe_path:
                processed_files.append(safe_path)

        # Auto-convert legacy formats
        if processed_files:
            converted_files, conversion_warnings = _convert_legacy_formats(processed_files)
            warnings.extend(conversion_warnings)

            # Deduplicate and merge
            old_count = len(self.selected_files)
            combined = self.selected_files + converted_files
            self.selected_files = _deduplicate_files(combined)
            self.warnings.extend(warnings)

            # Update display
            self._update_display()
            self.files_selected.emit(self.selected_files)

            new_count = len(self.selected_files) - old_count
            if new_count > 0:
                InfoBar.success(
                    "添加成功",
                    f"新增 {new_count} 个文件",
                    parent=self.window(),
                )

    def _select_files(self):
        """Open file dialog to select materials."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择案件材料",
            "",
            "所有支持的文件 (*.pdf *.docx *.doc *.txt *.md *.png *.jpg *.jpeg *.m4a *.mp3 *.wav);;"
            "PDF (*.pdf);;Word (*.docx *.doc);;文本 (*.txt *.md);;"
            "图片 (*.png *.jpg *.jpeg);;音频 (*.m4a *.mp3 *.wav)",
        )
        if files:
            self._process_files(list(files))

    def _clear_files(self):
        """Clear selected files."""
        self.selected_files = []
        self.warnings = []
        self._update_display()
        self.files_selected.emit([])

    def _view_material_list(self):
        """Show full material list in dialog."""
        if self.selected_files:
            dialog = MaterialListDialog(self.selected_files, self)
            dialog.exec()

    def _update_display(self):
        """Update display based on file count."""
        count = len(self.selected_files)

        if count == 0:
            # Switch to empty state
            self.stacked.setCurrentIndex(0)
        else:
            # Switch to loaded state
            self.summary_label.setText(f"已成功加载 {count} 份文件")

            # Update file list with only filenames (no full paths)
            self.file_list.clear()
            for filepath in self.selected_files:
                name = os.path.basename(filepath)
                self.file_list.addItem(name)

            self.stacked.setCurrentIndex(1)
