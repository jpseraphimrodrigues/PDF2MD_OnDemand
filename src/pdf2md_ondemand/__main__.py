"""Desktop application composition root."""

from PySide6.QtWidgets import QApplication

from pdf2md_ondemand.adapters.qt_asset_scheme import register_asset_scheme
from pdf2md_ondemand.ui.desktop.main_window import MainWindow


def main() -> int:
    """Create the desktop shell and run its event loop."""
    register_asset_scheme()
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
