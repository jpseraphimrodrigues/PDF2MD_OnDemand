"""Contracts for the editor's deliberately narrow WebChannel surface."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication

from pdf2md_ondemand.ui.desktop.editor_bridge import EditorBridge
from pdf2md_ondemand.ui.desktop.editor_view import EditorView


def test_editor_bridge_exposes_only_text_getter_setter_and_change_signal() -> None:
    bridge = EditorBridge("starting Ω")
    changed: list[str] = []
    bridge.contentChanged.connect(changed.append)

    assert bridge.getContent() == "starting Ω"
    bridge.setContent("edited 日本語")
    bridge.setContent("edited 日本語")

    assert bridge.getContent() == "edited 日本語"
    assert changed == ["edited 日本語"]

    meta = bridge.metaObject()
    invokables = {
        bytes(meta.method(index).name()).decode()
        for index in range(meta.methodOffset(), meta.methodCount())
        if meta.method(index).methodType().name in {"Slot", "Signal"}
    }
    assert invokables == {"setContent", "getContent", "contentChanged"}
    assert isinstance(bridge, QObject)


def test_editor_view_round_trips_initial_and_edited_unicode() -> None:
    app = QApplication.instance() or QApplication([])
    view = EditorView("ação Ω")
    changed: list[str] = []
    view.bridge.contentChanged.connect(changed.append)
    result: list[str | None] = []

    def page_loaded(ok: bool) -> None:
        assert ok
        view.page().runJavaScript(
            "window.editorApi.getContent()",
            lambda value: (result.append(value), app.quit()),
        )

    view.loadFinished.connect(page_loaded)
    QTimer.singleShot(8000, app.quit)
    view.show()
    app.exec()
    assert result == ["ação Ω"]

    assert view.bridge.getContent() == "ação Ω"
    view.bridge.setContent("editado 日本語")
    assert changed == ["editado 日本語"]
