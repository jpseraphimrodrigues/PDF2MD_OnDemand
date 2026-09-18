"""Contracts for the editor's deliberately narrow WebChannel surface."""

from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

from PySide6.QtCore import QEventLoop, QObject, QTimer
from PySide6.QtWidgets import QApplication

from pdf2md_ondemand.adapters.qt_asset_scheme import register_asset_scheme
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
        "setDocumentContent",
        "getContent",
        "applyCommand",
        "switchDocument",
        "closeDocumentState",
        "getDocumentKey",
        "contentChanged",
        "commandRequested",
        "documentSwitchRequested",
        "documentCloseRequested",
        "documentContentChanged",
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


def test_editor_bridge_switch_and_close_do_not_emit_content_edits() -> None:
    bridge = EditorBridge("first")
    changed: list[str] = []
    switched: list[tuple[str, str]] = []
    closed: list[str] = []
    bridge.contentChanged.connect(changed.append)
    bridge.documentSwitchRequested.connect(
        lambda key, text: switched.append((key, text))
    )
    bridge.documentCloseRequested.connect(closed.append)

    bridge.switchDocument("tab-b", "second")
    bridge.closeDocumentState("tab-a")

    assert bridge.getContent() == "second"
    assert changed == []
    assert switched == [("tab-b", "second")]
    assert closed == ["tab-a"]


def test_editor_bridge_keeps_late_content_keyed_to_its_origin_document() -> None:
    bridge = EditorBridge("first")
    changed: list[str] = []
    keyed: list[tuple[str, str]] = []
    bridge.contentChanged.connect(changed.append)
    bridge.documentContentChanged.connect(lambda key, text: keyed.append((key, text)))
    bridge.switchDocument("tab-a", "first")
    bridge.switchDocument("tab-b", "second")

    bridge.setDocumentContent("tab-a", "late first edit")
    bridge.setDocumentContent("tab-b", "second edit")

    assert bridge.getContent() == "second edit"
    assert changed == ["second edit"]
    assert keyed == [
        ("tab-a", "late first edit"),
        ("tab-b", "second edit"),
    ]


def test_editor_view_round_trips_initial_and_edited_unicode() -> None:
    register_asset_scheme()
    app = QApplication.instance() or QApplication([])
    view = EditorView("ação Ω")
    loop = QEventLoop()
    changed: list[str] = []
    view.bridge.contentChanged.connect(changed.append)
    initial: list[str | None] = []
    after_command: list[str | None] = []
    after_undo: list[str | None] = []

    def check_after_undo() -> None:
        view.page().runJavaScript(
            "window.editorApi.getContent()",
            lambda value: (after_undo.append(value), loop.quit()),
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
        QTimer.singleShot(
            250,
            lambda: view.page().runJavaScript(
                "window.editorApi.getContent()", apply_toolbar_command
            ),
        )

    view.loadFinished.connect(page_loaded)
    QTimer.singleShot(8000, loop.quit)
    view.show()
    loop.exec()
    assert initial == ["ação Ω"]
    assert after_command == ["****ação Ω"]
    assert after_undo == ["ação Ω"]

    assert view.bridge.getContent() == "ação Ω"
    assert changed == ["****ação Ω", "ação Ω"]
    view.bridge.setContent("editado 日本語")
    assert changed == ["****ação Ω", "ação Ω", "editado 日本語"]
    assert QApplication.instance() is app


def test_code_mirror_switch_restores_document_history_and_does_not_emit_edit() -> None:
    register_asset_scheme()
    app = QApplication.instance() or QApplication([])
    initial_content = "alpha\n" + "line\n" * 100
    view = EditorView(initial_content)
    loop = QEventLoop()
    results: dict[str, object] = {}
    changed: list[str] = []
    view.bridge.contentChanged.connect(changed.append)

    def read_a_after_undo(_result: object) -> None:
        view.page().runJavaScript(
            "window.editorApi.getContent()",
            lambda value: (results.update(a_undo=value), finish_after_b()),
        )

    def finish_after_b() -> None:
        view.bridge.switchDocument("tab-b", "beta")
        view.page().runJavaScript(
            "window.editorApi.undo()",
            lambda _undone: view.page().runJavaScript(
                "window.editorApi.getContent()",
                lambda value: (results.update(b_restored=value), loop.quit()),
            ),
        )

    def back_to_a() -> None:
        view.bridge.switchDocument("tab-a", str(results["a_edited"]))
        QTimer.singleShot(120, read_a_view_state)

    def read_a_view_state() -> None:
        view.page().runJavaScript(
            "JSON.stringify({selection: window.editorApi.selection(), "
            "scrollTop: document.querySelector('.cm-scroller').scrollTop})",
            lambda value: (
                results.update(a_view_state=json.loads(value)),
                view.page().runJavaScript("window.editorApi.undo()", read_a_after_undo),
            ),
        )

    def make_a_edit() -> None:
        view.page().runJavaScript(
            "window.editorApi.select(2, 4); window.editorApi.applyCommand('bold');"
            "document.querySelector('.cm-scroller').scrollTop = 250;"
            "JSON.stringify({content: window.editorApi.getContent(), "
            "selection: window.editorApi.selection(), "
            "scrollTop: document.querySelector('.cm-scroller').scrollTop})",
            lambda value: after_a_edit(json.loads(value)),
        )

    def after_a_edit(value: dict[str, object]) -> None:
        results["a_edited"] = value["content"]
        results["a_before_state"] = value
        QTimer.singleShot(150, capture_stable_a_state)

    def capture_stable_a_state() -> None:
        view.page().runJavaScript(
            "JSON.stringify({selection: window.editorApi.selection(), "
            "scrollTop: document.querySelector('.cm-scroller').scrollTop})",
            lambda value: switch_to_b(json.loads(value)),
        )

    def switch_to_b(state: dict[str, object]) -> None:
        results["a_before_state"] = state
        view.bridge.switchDocument("tab-b", "beta")
        view.page().runJavaScript(
            "window.editorApi.applyCommand('bold')",
            lambda _edited: (
                view.bridge.switchDocument("tab-a", str(results["a_edited"])),
                QTimer.singleShot(100, back_to_a),
            ),
        )

    def begin(ok: bool) -> None:
        assert ok
        view.bridge.switchDocument("tab-a", initial_content)
        QTimer.singleShot(500, make_a_edit)

    view.loadFinished.connect(begin)
    QTimer.singleShot(8000, loop.quit)
    view.show()
    loop.exec()

    assert str(results["a_edited"]).startswith("al**ph**a\nline")
    assert str(results["a_undo"]).startswith("alpha\nline")
    view_state = results["a_view_state"]
    before_state = results["a_before_state"]
    assert view_state["selection"] == before_state["selection"]
    assert view_state["scrollTop"] >= 200
    assert view_state["scrollTop"] == before_state["scrollTop"]
    assert results["b_restored"] == "beta"
    assert changed == [
        results["a_edited"],
        "****beta",
        results["a_undo"],
    ]
    assert QApplication.instance() is app
