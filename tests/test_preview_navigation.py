"""Preview navigation policy prevents document-controlled browser access."""

from __future__ import annotations

from unittest.mock import Mock

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEnginePage

from pdf2md_ondemand.ui.desktop.preview_view import PreviewPage, navigation_policy


def test_navigation_policy_allows_only_internal_and_external_http_schemes() -> None:
    assert navigation_policy("qrc") == "allow"
    assert navigation_policy("pdf2md-asset") == "allow"
    assert navigation_policy("HTTPS") == "external-confirmation"
    for scheme in ("file", "javascript", "data", "ftp", "mailto", "blob"):
        assert navigation_policy(scheme) == "block"


def test_preview_page_emits_http_links_but_rejects_navigation() -> None:
    page = type("PageHarness", (), {"externalLinkRequested": Mock()})()
    link = QUrl("https://example.test/path")

    allowed = PreviewPage.acceptNavigationRequest(
        page, link, QWebEnginePage.NavigationType.NavigationTypeLinkClicked, True
    )

    assert not allowed
    page.externalLinkRequested.emit.assert_called_once_with(link.toString())
    assert PreviewPage.acceptNavigationRequest(
        page,
        QUrl("javascript:alert(1)"),
        QWebEnginePage.NavigationType.NavigationTypeLinkClicked,
        True,
    ) is False
    page.externalLinkRequested.emit.assert_called_once_with(link.toString())


def test_preview_page_never_opens_redirects_or_subframe_external_urls() -> None:
    page = type("PageHarness", (), {"externalLinkRequested": Mock()})()
    redirect = QUrl("https://example.test/redirect")

    assert PreviewPage.acceptNavigationRequest(
        page,
        redirect,
        QWebEnginePage.NavigationType.NavigationTypeOther,
        True,
    ) is False
    assert PreviewPage.acceptNavigationRequest(
        page,
        redirect,
        QWebEnginePage.NavigationType.NavigationTypeLinkClicked,
        False,
    ) is False
    assert PreviewPage.acceptNavigationRequest(
        page,
        QUrl("pdf2md-asset://session/image.png"),
        QWebEnginePage.NavigationType.NavigationTypeLinkClicked,
        True,
    ) is False
    page.externalLinkRequested.emit.assert_not_called()
