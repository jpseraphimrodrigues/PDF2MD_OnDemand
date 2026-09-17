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
    assert invokables == {
        "setContent",
        "getContent",
        "applyCommand",
        "contentChanged",
        "commandRequested",
    }
    assert isinstance(bridge, QObject)


def test_editor_bridge_forwards_only_supported_format_commands() -> None:
    bridge = EditorBridge()
    requested: list[str] = []
    bridge.commandRequested.connect(requested.append)

    for command in ("bold", "italic", "heading", "link", "code"):
        bridge.applyCommand(command)
    bridge.applyCommand("execute arbitrary JavaScript")

    assert requested == ["bold", "italic", "heading", "link", "code"]


def test_editor_view_round_trips_initial_and_edited_unicode() -> None:
    app = QApplication.instance() or QApplication([])
    view = EditorView("ação Ω")
    changed: list[str] = []
    view.bridge.contentChanged.connect(changed.append)
    initial: list[str | None] = []
    after_command: list[str | None] = []
    after_undo: list[str | None] = []

    def check_after_undo() -> None:
        view.page().runJavaScript(
            "window.editorApi.getContent()",
            lambda value: (after_undo.append(value), app.quit()),
        )

    def undo_command(_value: object) -> None:
        QTimer.singleShot(100, check_after_undo)

    def check_after_command() -> None:
        view.page().runJavaScript(
            "window.editorApi.getContent()",
            lambda value: (
                after_command.append(value),
                view.page().runJavaScript("window.editorApi.undo()", undo_command),
            ),
        )

    def apply_toolbar_command(value: str | None) -> None:
        initial.append(value)
        view.bridge.applyCommand("bold")
        QTimer.singleShot(150, check_after_command)

    def page_loaded(ok: bool) -> None:
        assert ok
        view.page().runJavaScript(
            "window.editorApi.getContent()",
            apply_toolbar_command,
        )

    view.loadFinished.connect(page_loaded)
    QTimer.singleShot(8000, app.quit)
    view.show()
    app.exec()
    assert initial == ["ação Ω"]
    assert after_command == ["****ação Ω"]
    assert after_undo == ["ação Ω"]

    assert view.bridge.getContent() == "ação Ω"
    assert changed == ["****ação Ω", "ação Ω"]
    view.bridge.setContent("editado 日本語")
    assert changed == ["****ação Ω", "ação Ω", "editado 日本語"]
