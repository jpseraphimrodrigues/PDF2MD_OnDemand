"""Desktop application composition root."""

from importlib.resources import files

from PySide6.QtWidgets import QApplication

from pdf2md_ondemand.adapters.qt_asset_scheme import register_asset_scheme
from pdf2md_ondemand.ui.desktop.main_window import MainWindow


def main() -> int:
    """Create the desktop shell and run its event loop."""
    register_asset_scheme()
    app: QApplication | None = QApplication.instance()  # type: ignore[assignment]
    if app is None:
        app = QApplication([])
    app.setOrganizationName("PDF2MD")
    app.setApplicationName("PDF2MD_OnDemand")
    app.setStyle("Fusion")
    theme_path = files("pdf2md_ondemand.ui.desktop").joinpath("themes/light.qss")
    app.setStyleSheet(theme_path.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
