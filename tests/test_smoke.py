"""Phase 0 smoke tests."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from pdf2md_ondemand import __version__
from pdf2md_ondemand.ui.desktop.main_window import MainWindow


def test_package_imports() -> None:
    assert __version__ == "0.1.0"


def test_main_window_can_be_created() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle() == "PDF2MD_OnDemand"
    window.close()
    app.processEvents()
