"""Standalone Markdown editor and preview composition."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QSplitter

from pdf2md_ondemand.ui.desktop.editor_view import EditorView
from pdf2md_ondemand.ui.desktop.preview_view import PreviewView

PREVIEW_DEBOUNCE_MS = 200


class MainWindow(QMainWindow):
    """Resizable side-by-side Editor and Preview, without document lifecycle."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF2MD_OnDemand")
        self.resize(960, 640)
        self.editor_view = EditorView()
        self.preview_view = PreviewView()
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.editor_view)
        self.splitter.addWidget(self.preview_view)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.setCentralWidget(self.splitter)

        self._pending_markdown = ""
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(PREVIEW_DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._render_pending_preview)
        self.editor_view.bridge.contentChanged.connect(self._schedule_preview)

    def _schedule_preview(self, markdown: str) -> None:
        self._pending_markdown = markdown
        self._preview_timer.start()

    def _render_pending_preview(self) -> None:
        self.preview_view.render_markdown(self._pending_markdown)
