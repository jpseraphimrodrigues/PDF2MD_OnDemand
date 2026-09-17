"""CodeMirror editor hosted in a dedicated Qt WebEngine view."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget

from pdf2md_ondemand.ui.desktop.editor_bridge import EditorBridge


class EditorView(QWebEngineView):
    """Local CodeMirror page with a text-only QWebChannel bridge."""

    def __init__(self, content: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bridge = EditorBridge(content, self)
        self.channel = QWebChannel(self.page())
        self.channel.registerObject("editorBridge", self.bridge)
        self.page().setWebChannel(self.channel)
        self.settings().setAttribute(
            self.settings().WebAttribute.JavascriptEnabled, True
        )
        self.load(QUrl.fromLocalFile(str(_frontend_file("editor.html"))))


def _frontend_file(name: str) -> Path:
    """Locate the checked-in frontend shell and its generated local bundle."""
    return Path(__file__).resolve().parents[4] / "frontend" / "src" / name
