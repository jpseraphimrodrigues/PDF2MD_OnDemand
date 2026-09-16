"""Minimal desktop main window."""

from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """The intentionally empty application window for Phase 0."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF2MD_OnDemand")
        self.resize(960, 640)
