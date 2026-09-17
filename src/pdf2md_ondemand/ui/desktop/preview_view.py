"""Markdown preview hosted in a separate, unprivileged WebEngine view."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget

from pdf2md_ondemand.adapters.qt_asset_scheme import (
    SCHEME_NAME,
    PreviewAssetHandler,
)
from pdf2md_ondemand.application.asset_sessions import AssetSessionRegistry


class PreviewView(QWebEngineView):
    """Render Markdown in a local page without a Python WebChannel object."""

    def __init__(
        self,
        sessions: AssetSessionRegistry,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sessions = sessions
        self._asset_session_id: str | None = None
        self._markdown = ""
        self._page_loaded = False
        self.profile = QWebEngineProfile(self)
        self.asset_handler = PreviewAssetHandler(sessions, self.profile)
        self.profile.installUrlSchemeHandler(SCHEME_NAME, self.asset_handler)
        self.setPage(QWebEnginePage(self.profile, self.profile))
        settings = self.settings()
        for attribute in (
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            QWebEngineSettings.WebAttribute.LocalStorageEnabled,
        ):
            settings.setAttribute(attribute, False)
        self.loadFinished.connect(self._on_load_finished)
        shell = _frontend_file("preview.html").read_text(encoding="utf-8")
        bundle = _frontend_file("../dist/preview.js").read_text(encoding="utf-8")
        shell = shell.replace(
            '<script src="../dist/preview.js"></script>',
            f"<script>{bundle}</script>",
        )
        self.setHtml(shell, QUrl("qrc:///pdf2md-preview/index.html"))

    def render_markdown(self, markdown: str) -> None:
        """Render source as preview HTML; the input string is left untouched."""
        self._markdown = markdown
        if self._page_loaded:
            self._render()

    def set_asset_root(self, markdown_parent: Path | None) -> None:
        """Replace or revoke the Preview's current document asset session."""
        if self._asset_session_id is not None:
            self._sessions.invalidate(self._asset_session_id)
        self._asset_session_id = (
            self._sessions.create(markdown_parent)
            if markdown_parent is not None
            else None
        )
        if self._page_loaded:
            self._set_frontend_session()
            self._render()

    def _on_load_finished(self, succeeded: bool) -> None:
        self._page_loaded = succeeded
        if succeeded:
            self._set_frontend_session()
            self._render()

    def _set_frontend_session(self) -> None:
        session_id = json.dumps(self._asset_session_id, ensure_ascii=True)
        self.page().runJavaScript(f"window.setAssetSessionId({session_id})")

    def _render(self) -> None:
        markdown = json.dumps(self._markdown, ensure_ascii=True)
        self.page().runJavaScript(f"window.renderMarkdown({markdown})")


def _frontend_file(name: str) -> Path:
    return Path(__file__).resolve().parents[4] / "frontend" / "src" / name
