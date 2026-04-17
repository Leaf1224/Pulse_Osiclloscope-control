from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtCore import QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget


def default_ui_path() -> Path:
    return Path(__file__).resolve().parent / "ui" / "main_window.ui"


def load_ui(ui_path: Path) -> QWidget:
    loader = QUiLoader()
    ui_file = QFile(str(ui_path))
    if not ui_file.open(QFile.ReadOnly):
        raise RuntimeError(f"Cannot open UI file: {ui_path}")
    try:
        widget = loader.load(ui_file)
    finally:
        ui_file.close()

    if widget is None:
        raise RuntimeError(f"Failed to load UI file: {ui_path}")
    return widget


class LivePreviewWindow(QMainWindow):
    def __init__(self, ui_path: Path, poll_interval_ms: int = 700) -> None:
        super().__init__()
        self.ui_path = ui_path
        self.poll_interval_ms = poll_interval_ms
        self._last_mtime_ns = 0
        self._last_error: str | None = None
        self._loaded_once = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._reload_if_changed)
        self._timer.start(self.poll_interval_ms)

        self._reload(force=True)

    def _current_mtime_ns(self) -> int:
        try:
            return self.ui_path.stat().st_mtime_ns
        except FileNotFoundError:
            return 0

    def _reload_if_changed(self) -> None:
        current_mtime_ns = self._current_mtime_ns()
        if current_mtime_ns != self._last_mtime_ns:
            self._reload(force=False)

    def _reload(self, force: bool) -> None:
        current_mtime_ns = self._current_mtime_ns()
        try:
            widget = load_ui(self.ui_path)
        except Exception as exc:
            message = str(exc)
            if force or message != self._last_error:
                self.setWindowTitle(f"Qt Preview - 載入失敗: {message}")
                self._last_error = message
            return

        previous_size = self.size()
        previous_pos = self.pos()
        previous_title = self.windowTitle()

        if isinstance(widget, QMainWindow):
            inner = widget
            central = inner.takeCentralWidget()
            if central is None:
                central = QWidget()
            self.setCentralWidget(central)
            self.setMenuBar(inner.menuBar())
            self.setStatusBar(inner.statusBar())
            title = inner.windowTitle() or f"{self.ui_path.name} - Live Preview"
        else:
            self.setCentralWidget(widget)
            title = f"{self.ui_path.name} - Live Preview"

        self.setWindowTitle(title)

        if self._loaded_once:
            self.resize(previous_size)
            self.move(previous_pos)
        else:
            if self.width() < 100 or self.height() < 100:
                self.resize(1200, 800)
            self._loaded_once = True

        self._last_mtime_ns = current_mtime_ns
        self._last_error = None

        if previous_title and previous_title != title:
            self.update()


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview a Qt Designer .ui file")
    parser.add_argument("--ui", default=str(default_ui_path()), help="Path to .ui file")
    parser.add_argument("--once", action="store_true", help="Load once only, disable live reload")
    parser.add_argument("--interval-ms", type=int, default=700, help="Live reload polling interval in milliseconds")
    args = parser.parse_args()

    ui_path = Path(args.ui).expanduser().resolve()
    if not ui_path.exists():
        raise SystemExit(f"UI file not found: {ui_path}")

    app = QApplication(sys.argv)
    if args.once:
        widget = load_ui(ui_path)
        if isinstance(widget, QMainWindow):
            window = widget
        else:
            window = QMainWindow()
            window.setCentralWidget(widget)
            window.resize(1200, 800)
            window.setWindowTitle(f"{ui_path.name} - Preview")
    else:
        window = LivePreviewWindow(ui_path, poll_interval_ms=max(200, args.interval_ms))

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
