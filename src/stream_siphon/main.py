from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .config import APP_NAME, ORG_NAME
from .ui.main_window import MainWindow


def _load_stylesheet(app: QApplication) -> None:
    style_path = Path(__file__).resolve().parent / "ui" / "styles.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    _load_stylesheet(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
