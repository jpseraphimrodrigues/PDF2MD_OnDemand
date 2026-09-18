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
    """Locate the packaged frontend or its source checkout equivalent."""
    packaged = Path(__file__).resolve().parent / "frontend" / name
    if packaged.is_file():
        return packaged
    source = Path(__file__).resolve().parents[4] / "frontend" / "src" / name
    if not source.is_file():
        raise FileNotFoundError(
            f"Frontend asset not found: {source}. Build it with `npm ci` and "
            "`npm run build` from the frontend directory, or reinstall the package."
        )
    return source
