"""Markdown preview hosted in a separate, unprivileged WebEngine view."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, QUrlQuery, Signal
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget

from pdf2md_ondemand.adapters.qt_asset_scheme import (
    SCHEME_NAME,
    PreviewAssetHandler,
)
from pdf2md_ondemand.application.asset_sessions import AssetSessionRegistry

TRUSTED_PREVIEW_URL = "qrc:///pdf2md-preview/index.html"


class PreviewView(QWebEngineView):
    """Render Markdown in a local page without a Python WebChannel object."""

    externalLinkRequested = Signal(str)
    internalLinkRequested = Signal(str, str)

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
        self.preview_page = PreviewPage(self.profile, self.profile)
        self.preview_page.externalLinkRequested.connect(self.externalLinkRequested)
        self.preview_page.internalLinkRequested.connect(self.internalLinkRequested)
        self.setPage(self.preview_page)
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        for attribute in (
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            QWebEngineSettings.WebAttribute.LocalStorageEnabled,
        ):
            settings.setAttribute(attribute, False)
        self._install_frontend_scripts()
        self.loadFinished.connect(self._on_load_finished)
        self.preview_page.load_trusted_html(
            _frontend_file("preview.html").read_text(encoding="utf-8"),
            QUrl(TRUSTED_PREVIEW_URL),
        )
        self.profile.downloadRequested.connect(lambda download: download.cancel())

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

    def _install_frontend_scripts(self) -> None:
        scripts = self.page().scripts()
        for name, source in (
            ("mermaid", _frontend_file("mermaid.js").read_text(encoding="utf-8")),
            ("preview-styles", _styles_script()),
            ("preview", _frontend_file("preview.js").read_text(encoding="utf-8")),
        ):
            script = QWebEngineScript()
            script.setName(name)
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(False)
            script.setSourceCode(source)
            scripts.insert(script)

    def _set_frontend_session(self) -> None:
        session_id = json.dumps(self._asset_session_id, ensure_ascii=True)
        self.page().runJavaScript(f"window.setAssetSessionId({session_id})")

    def _render(self) -> None:
        markdown = json.dumps(self._markdown, ensure_ascii=True)
        self.page().runJavaScript(f"window.renderMarkdown({markdown})")


def _frontend_file(name: str) -> Path:
    """Find packaged assets or generated development bundles."""
    packaged = Path(__file__).resolve().parent / "frontend" / name
    if packaged.is_file():
        return packaged
    source = Path(__file__).resolve().parents[4] / "frontend" / "src" / name
    if name.endswith((".js", ".css")):
        source = source.parents[1] / "dist" / name
    if not source.is_file():
        raise FileNotFoundError(
            f"Frontend asset not found: {source}. Build it with `npm ci` and "
            "`npm run build` from the frontend directory, or reinstall the package."
        )
    return source


def _styles_script() -> str:
    styles = json.dumps(_frontend_file("preview.css").read_text(encoding="utf-8"))
    return (
        "const style = document.createElement('style');"
        f"style.textContent = {styles};"
        "document.documentElement.appendChild(style);"
    )


def navigation_policy(scheme: str) -> str:
    """Return allow, external-confirmation, or block for a navigation scheme."""
    normalized = scheme.lower()
    if normalized in {"qrc", "pdf2md-asset"}:
        return "allow"
    if normalized in {"http", "https"}:
        return "external-confirmation"
    return "block"


class PreviewPage(QWebEnginePage):
    """Keep document links inside the trusted local renderer or ask externally."""

    externalLinkRequested = Signal(str)
    internalLinkRequested = Signal(str, str)

    def __init__(self, profile: QWebEngineProfile, parent: QObject) -> None:
        super().__init__(profile, parent)
        self._trusted_bootstrap_pending = False

    def load_trusted_html(self, html: str, base_url: QUrl) -> None:
        """Load the small app-owned shell; bundles run as Qt-injected scripts."""
        self._trusted_bootstrap_pending = True
        self.setHtml(html, base_url)

    def acceptNavigationRequest(
        self,
        url: QUrl | str,
        navigation_type: QWebEnginePage.NavigationType,
        is_main_frame: bool,
    ) -> bool:
        if isinstance(url, str):
            url = QUrl(url)
        if (
            url.scheme().lower() == "pdf2md-note"
            and is_main_frame
            and navigation_type
            == QWebEnginePage.NavigationType.NavigationTypeLinkClicked
        ):
            query = QUrlQuery(url)
            target = query.queryItemValue(
                "target", QUrl.ComponentFormattingOption.FullyDecoded
            )
            kind = query.queryItemValue(
                "kind", QUrl.ComponentFormattingOption.FullyDecoded
            )
            if target and kind in {"wikilink", "markdown"}:
                self.internalLinkRequested.emit(target, kind)
            return False
        if (
            getattr(self, "_trusted_bootstrap_pending", False)
            and url.scheme().lower() == "data"
            and url.toString().startswith("data:text/html;charset=UTF-8,")
            and is_main_frame
            and navigation_type == QWebEnginePage.NavigationType.NavigationTypeTyped
        ):
            self._trusted_bootstrap_pending = False
            return True
        policy = navigation_policy(url.scheme())
        if policy == "allow":
            if url.scheme().lower() == "pdf2md-asset":
                return not is_main_frame
            return is_main_frame and url == QUrl(TRUSTED_PREVIEW_URL)
        if (
            url == QUrl("about:blank")
            and is_main_frame
            and navigation_type == QWebEnginePage.NavigationType.NavigationTypeOther
        ):
            return True
        if (
            policy == "external-confirmation"
            and is_main_frame
            and navigation_type
            == QWebEnginePage.NavigationType.NavigationTypeLinkClicked
        ):
            self.externalLinkRequested.emit(url.toString())
        return False

    def createWindow(self, window_type: QWebEnginePage.WebWindowType) -> QWebEnginePage:
        del window_type
        return None  # type: ignore[return-value]  # Qt treats nullptr as blocked popup.
