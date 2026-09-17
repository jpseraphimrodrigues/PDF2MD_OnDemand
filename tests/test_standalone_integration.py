"""Offline integration of the standalone open/edit/preview/save workflow."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

from pdf2md_ondemand.adapters.qt_asset_scheme import register_asset_scheme
from pdf2md_ondemand.ui.desktop.main_window import MainWindow


def _application() -> QApplication:
    app = QApplication.instance()
    if app is None:
        register_asset_scheme()
        app = QApplication([])
    return app


def _wait_for_js(
    app: QApplication,
    view: QWebEngineView,
    script: str,
    predicate: Callable[[object], bool],
    *,
    timeout_ms: int = 15000,
) -> object:
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(50)
    latest: list[object] = []

    def poll() -> None:
        def receive(value: object) -> None:
            latest[:] = [value]
            if predicate(value):
                loop.quit()

        view.page().runJavaScript(script, receive)

    timer.timeout.connect(poll)
    timer.start()
    QTimer.singleShot(timeout_ms, loop.quit)
    poll()
    loop.exec()
    timer.stop()
    app.processEvents()
    assert latest and predicate(latest[-1]), (
        "JavaScript did not reach expected state: "
        f"{latest!r}; URL={view.url().toString()!r}; "
        f"loaded={getattr(view, '_page_loaded', None)!r}"
    )
    return latest[-1]


def test_open_edit_preview_debounce_and_save_round_trip(tmp_path: Path) -> None:
    app = _application()
    path = tmp_path / "nota Ω.md"
    initial = "# Original Ω\n\nConteúdo inicial.\n"
    path.write_bytes(initial.encode("utf-8"))

    window = MainWindow()
    window.show()
    session = window.open_document_at(path)
    assert session is not None
    _wait_for_js(
        app,
        window.editor_view,
        "window.editorApi.getContent()",
        lambda value: value == initial,
    )

    edited = "# Editado 東京\n\n**conteúdo novo**.\n"
    script = f"window.editorApi.setContent({json.dumps(edited, ensure_ascii=True)})"
    _wait_for_js(app, window.editor_view, script, lambda value: value is True)
    _wait_for_js(
        app,
        window.preview_view,
        "JSON.stringify({renderer: typeof window.renderMarkdown, "
        "location: location.href, body: document.body.innerHTML})",
        lambda value: isinstance(value, str) and "conteúdo novo" in value,
        timeout_ms=10000,
    )

    assert window.editor_view.bridge.getContent() == edited
    assert window.document_session is not None and window.document_session.dirty
    window.save_current_to_disk()
    assert path.read_bytes() == edited.encode("utf-8")
    assert window.document_session is not None and not window.document_session.dirty
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
