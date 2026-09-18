"""Qt URL scheme registration and restricted Preview request handler."""

from __future__ import annotations

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QUrl
from PySide6.QtWebEngineCore import (
    QWebEngineUrlRequestJob,
    QWebEngineUrlScheme,
    QWebEngineUrlSchemeHandler,
)

from pdf2md_ondemand.adapters.asset_path_resolver import (
    AssetPathError,
    resolve_asset_path,
)
from pdf2md_ondemand.application.asset_sessions import AssetSessionRegistry

SCHEME_NAME = b"pdf2md-asset"


def register_asset_scheme() -> None:
    """Register the local secure scheme; call before QApplication/profile setup."""
    existing = QWebEngineUrlScheme.schemeByName(SCHEME_NAME)
    if existing.name() == SCHEME_NAME:
        return
    scheme = QWebEngineUrlScheme(SCHEME_NAME)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    scheme.setFlags(
        QWebEngineUrlScheme.Flag.SecureScheme
        | QWebEngineUrlScheme.Flag.LocalScheme
    )
    QWebEngineUrlScheme.registerScheme(scheme)


class PreviewAssetHandler(QWebEngineUrlSchemeHandler):
    """Serve only registry-authorized raster files; never enumerate folders."""

    def __init__(
        self, sessions: AssetSessionRegistry, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._sessions = sessions

    def requestStarted(self, job: QWebEngineUrlRequestJob) -> None:
        url = job.requestUrl()
        if url.query() or url.fragment():
            job.fail(QWebEngineUrlRequestJob.Error.UrlInvalid)
            return
        try:
            encoded_path = url.path(QUrl.ComponentFormattingOption.FullyEncoded)
            if encoded_path.startswith("/"):
                encoded_path = encoded_path[1:]
            session = self._sessions.get(url.host())
            path = resolve_asset_path(session.root, encoded_path)
            content_type = _CONTENT_TYPES[path.suffix.lower()]
            data = path.read_bytes()
        except (AssetPathError, OSError, KeyError):
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return

        device = QBuffer(job)
        device.setData(QByteArray(data))
        device.open(QIODevice.OpenModeFlag.ReadOnly)
        job.reply(QByteArray(content_type.encode("ascii")), device)


_CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
