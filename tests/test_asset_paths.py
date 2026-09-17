"""Filesystem authorization tests for Preview raster assets."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineUrlScheme,
)
from PySide6.QtWidgets import QApplication

from pdf2md_ondemand.adapters.asset_path_resolver import (
    AssetPathError,
    resolve_asset_path,
)
from pdf2md_ondemand.adapters.qt_asset_scheme import (
    SCHEME_NAME,
    register_asset_scheme,
)
from pdf2md_ondemand.application.asset_sessions import AssetSessionRegistry
from pdf2md_ondemand.ui.desktop.preview_view import PreviewView


def test_resolves_encoded_raster_only_inside_document_root(tmp_path: Path) -> None:
    image = tmp_path / "photos" / "a b.PNG"
    image.parent.mkdir()
    image.write_bytes(b"png")

    assert resolve_asset_path(tmp_path, "photos/a%20b.PNG") == image.resolve()


@pytest.mark.parametrize(
    "relative_path",
    [
        "",
        "../outside.png",
        "%2e%2e/outside.png",
        "/outside.png",
        "C:/outside.png",
        "\\\\server\\share\\outside.png",
        "file:///outside.png",
        "image%ZZ.png",
        "folder/",
        "folder.svg",
    ],
)
def test_rejects_invalid_or_unsupported_asset_paths(
    tmp_path: Path, relative_path: str
) -> None:
    with pytest.raises(AssetPathError):
        resolve_asset_path(tmp_path, relative_path)


def test_rejects_directory_and_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "document"
    root.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"image")
    with pytest.raises(AssetPathError):
        resolve_asset_path(root, ".")

    try:
        (root / "escape.png").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not available")
    with pytest.raises(AssetPathError):
        resolve_asset_path(root, "escape.png")


def test_asset_session_can_be_revoked(tmp_path: Path) -> None:
    image = tmp_path / "asset.webp"
    image.write_bytes(b"image")
    sessions = AssetSessionRegistry()
    session_id = sessions.create(tmp_path)

    assert sessions.get(session_id).root == tmp_path.resolve()
    sessions.invalidate(session_id)
    with pytest.raises(ValueError, match="expired"):
        sessions.get(session_id)


def test_custom_asset_scheme_is_registered_secure_and_without_local_access() -> None:
    register_asset_scheme()

    scheme = QWebEngineUrlScheme.schemeByName(SCHEME_NAME)
    flags = scheme.flags()
    assert scheme.name() == SCHEME_NAME
    assert scheme.syntax() == QWebEngineUrlScheme.Syntax.Host
    assert flags & QWebEngineUrlScheme.Flag.SecureScheme
    assert flags & QWebEngineUrlScheme.Flag.LocalScheme
    assert not flags & QWebEngineUrlScheme.Flag.LocalAccessAllowed


def test_preview_uses_isolated_profile_with_restricted_settings() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
    app = QApplication.instance() or QApplication([])
    sessions = AssetSessionRegistry()
    preview = PreviewView(sessions)
    profile = preview.profile

    assert profile is not QWebEngineProfile.defaultProfile()
    assert profile.urlSchemeHandler(SCHEME_NAME) is preview.asset_handler
    assert QWebEngineProfile.defaultProfile().urlSchemeHandler(SCHEME_NAME) is None
    for attribute in (
        QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
        QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
        QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
        QWebEngineSettings.WebAttribute.LocalStorageEnabled,
    ):
        assert not preview.settings().testAttribute(attribute)

    assert preview.page().profile() is profile
    preview.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
