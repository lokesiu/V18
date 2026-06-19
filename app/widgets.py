"""Thin wrapper around PySide6 widgets used by the app.

Kept minimal – re-exports the subset of PySide6 classes that the rest of
the ``app`` package imports.  Add convenience helpers here as the UI grows.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

__all__ = [
    "Qt",
    "QFont",
    "QComboBox",
    "QFileDialog",
    "QHBoxLayout",
    "QLabel",
    "QMainWindow",
    "QProgressBar",
    "QPushButton",
    "QTextEdit",
    "QVBoxLayout",
    "QWidget",
]


def make_heading(text: str, *, size: int = 14) -> QLabel:
    """Return a bold section-heading label."""
    label = QLabel(text)
    font = QFont()
    font.setPointSize(size)
    font.setBold(True)
    label.setFont(font)
    return label


def make_body_label(text: str = "") -> QLabel:
    """Return a normal-weight body label."""
    label = QLabel(text)
    label.setWordWrap(True)
    return label
