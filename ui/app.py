from __future__ import annotations

"""
Minimal PySide6 UI shell.

The UI loads lazily to avoid import errors when PySide6 is not installed. A
RuntimeError is raised with guidance instead of failing on import.
"""

from typing import Optional


def run_ui(app_title: str, status_text: str = "Idle") -> None:
    try:
        from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QSplitter, QTextEdit, QTreeView, QWidget
        from PySide6.QtCore import Qt
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("PySide6 is required for the UI but is not installed.") from exc

    class MainWindow(QMainWindow):
        def __init__(self, title: str, status: str) -> None:
            super().__init__()
            self.setWindowTitle(title)
            self.resize(1200, 800)

            left = QTreeView()
            right = QTextEdit()
            bottom = QLabel(status)
            bottom.setObjectName("statusLabel")

            splitter = QSplitter(Qt.Horizontal)
            splitter.addWidget(left)
            splitter.addWidget(right)

            container = QWidget()
            container_layout = QSplitter(Qt.Vertical)
            container_layout.addWidget(splitter)
            container_layout.addWidget(bottom)

            container_layout.setStretchFactor(0, 4)
            container_layout.setStretchFactor(1, 1)

            self.setCentralWidget(container_layout)

    app: Optional[QApplication] = QApplication.instance()
    app = app or QApplication([])
    window = MainWindow(app_title, status_text)
    window.show()
    app.exec()
