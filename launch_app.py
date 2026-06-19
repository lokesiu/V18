"""Launch V18 as a desktop application.

FluentWindow handles its own title bar and navigation.
No custom TitleBar wrapper needed.
"""
from __future__ import annotations

import sys
import time
from typing import Optional

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPainter, QLinearGradient


# ── Backend health check ──────────────────────────────────────────────
def wait_for_backend(
    host: str = "127.0.0.1",
    port: int = 8501,
    timeout: float = 5.0,
    interval: float = 0.1,
) -> bool:
    import socket
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=interval):
                return True
        except OSError:
            time.sleep(interval)
    return False


# ── Splash screen ─────────────────────────────────────────────────────
class _SplashScreen(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(400, 260)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(16)

        title = QLabel("明证台")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e0e0e0; font-size: 28px; font-weight: bold;")
        root.addWidget(title)

        self._subtitle = QLabel("正在启动…")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setStyleSheet("color: #707078; font-size: 13px;")
        root.addWidget(self._subtitle)

        self._dot_label = QLabel("")
        self._dot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dot_label.setStyleSheet("color: #3b82f6; font-size: 18px;")
        root.addWidget(self._dot_label)

        self._dot_count = 0
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._animate_dots)
        self._dot_timer.start(400)

    def _animate_dots(self):
        self._dot_count = (self._dot_count + 1) % 4
        self._dot_label.setText("●" * self._dot_count if self._dot_count else "○")

    def set_status(self, text: str) -> None:
        self._subtitle.setText(text)

    def finish(self, target: QWidget) -> None:
        self._dot_timer.stop()
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self.close)
        anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor("#141418"))
        gradient.setColorAt(1.0, QColor("#0e0e12"))
        painter.fillRect(self.rect(), gradient)


def _center_on_screen(app: QApplication, w: int, h: int) -> tuple[int, int]:
    screen = app.primaryScreen()
    if screen is None:
        return 100, 100
    geo = screen.availableGeometry()
    x = (geo.width() - w) // 2 + geo.x()
    y = (geo.height() - h) // 2 + geo.y()
    return x, y


def main() -> None:
    app = QApplication(sys.argv)

    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # Splash
    splash = _SplashScreen()
    splash.set_status("正在启动…")
    x, y = _center_on_screen(app, 400, 260)
    splash.move(x, y)
    splash.show()
    app.processEvents()

    # Health check (optional, fast timeout)
    wait_for_backend(timeout=2.0)

    # Build main window — FluentWindow has its own title bar
    from app.main_window import MainWindow
    window = MainWindow()
    window.resize(1300, 850)
    cx, cy = _center_on_screen(app, 1300, 850)
    window.move(cx, cy)
    window.show()

    splash.finish(window)
    splash.close()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
