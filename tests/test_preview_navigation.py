"""Preview navigation policy prevents document-controlled browser access."""

from __future__ import annotations

from unittest.mock import Mock

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEnginePage

from pdf2md_ondemand.ui.desktop.preview_view import (
    TRUSTED_PREVIEW_URL,
    PreviewPage,
    navigation_policy,
)


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
    assert (
        PreviewPage.acceptNavigationRequest(
            page,
            QUrl("javascript:alert(1)"),
            QWebEnginePage.NavigationType.NavigationTypeLinkClicked,
            True,
        )
        is False
    )
    page.externalLinkRequested.emit.assert_called_once_with(link.toString())


def test_preview_page_routes_only_clicked_internal_note_links() -> None:
    page = type(
        "PageHarness",
        (),
        {
            "externalLinkRequested": Mock(),
            "internalLinkRequested": Mock(),
        },
    )()
    clicked = QWebEnginePage.NavigationType.NavigationTypeLinkClicked
    link = QUrl("pdf2md-note://open?kind=wikilink&target=notes%2Fone%23heading")

    assert not PreviewPage.acceptNavigationRequest(page, link, clicked, True)
    page.internalLinkRequested.emit.assert_called_once_with(
        "notes/one#heading", "wikilink"
    )
    assert not PreviewPage.acceptNavigationRequest(
        page, link, QWebEnginePage.NavigationType.NavigationTypeOther, True
    )
    page.internalLinkRequested.emit.assert_called_once()


def test_preview_page_never_opens_redirects_or_subframe_external_urls() -> None:
    page = type("PageHarness", (), {"externalLinkRequested": Mock()})()
    redirect = QUrl("https://example.test/redirect")

    assert (
        PreviewPage.acceptNavigationRequest(
            page,
            redirect,
            QWebEnginePage.NavigationType.NavigationTypeOther,
            True,
        )
        is False
    )
    assert (
        PreviewPage.acceptNavigationRequest(
            page,
            redirect,
            QWebEnginePage.NavigationType.NavigationTypeLinkClicked,
            False,
        )
        is False
    )
    assert (
        PreviewPage.acceptNavigationRequest(
            page,
            QUrl("pdf2md-asset://session/image.png"),
            QWebEnginePage.NavigationType.NavigationTypeLinkClicked,
            True,
        )
        is False
    )
    page.externalLinkRequested.emit.assert_not_called()


def test_internal_pages_are_limited_to_preview_shell_and_asset_subresources() -> None:
    page = type("PageHarness", (), {"externalLinkRequested": Mock()})()
    other_navigation = QWebEnginePage.NavigationType.NavigationTypeOther

    assert (
        PreviewPage.acceptNavigationRequest(
            page, QUrl(TRUSTED_PREVIEW_URL), other_navigation, True
        )
        is True
    )
    assert (
        PreviewPage.acceptNavigationRequest(
            page, QUrl("qrc:///other.html"), other_navigation, True
        )
        is False
    )
    assert (
        PreviewPage.acceptNavigationRequest(
            page, QUrl("pdf2md-asset://session/image.png"), other_navigation, False
        )
        is True
    )
    assert (
        PreviewPage.acceptNavigationRequest(
            page, QUrl("pdf2md-asset://session/image.png"), other_navigation, True
        )
        is False
    )


def test_data_url_is_allowed_only_for_one_trusted_set_html_bootstrap() -> None:
    page = type(
        "PageHarness",
        (),
        {"externalLinkRequested": Mock(), "_trusted_bootstrap_pending": True},
    )()
    bootstrap = QUrl("data:text/html;charset=UTF-8,%3Chtml%3Etrusted%3C/html%3E")
    typed = QWebEnginePage.NavigationType.NavigationTypeTyped

    assert PreviewPage.acceptNavigationRequest(page, bootstrap, typed, True) is True
    assert page._trusted_bootstrap_pending is False
    assert PreviewPage.acceptNavigationRequest(page, bootstrap, typed, True) is False
    assert (
        PreviewPage.acceptNavigationRequest(
            page,
            bootstrap,
            QWebEnginePage.NavigationType.NavigationTypeLinkClicked,
            True,
        )
        is False
    )
