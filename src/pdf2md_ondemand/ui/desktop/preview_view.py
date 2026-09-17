"""Markdown preview hosted in a separate, unprivileged WebEngine view."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget


class PreviewView(QWebEngineView):
    """Render Markdown in a local page without a Python WebChannel object."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.load(QUrl.fromLocalFile(str(_frontend_file("preview.html"))))

    def render_markdown(self, markdown: str) -> None:
        """Render source as preview HTML; the input string is left untouched."""
        argument = json.dumps(markdown, ensure_ascii=True)
        self.page().runJavaScript(f"window.renderMarkdown({argument})")


def _frontend_file(name: str) -> Path:
    return Path(__file__).resolve().parents[4] / "frontend" / "src" / name
