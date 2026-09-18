"""Composition contract for the standalone editor and preview panes."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEventLoop, QObject, QSettings, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QSplitter, QWidget
from pytest import MonkeyPatch

from pdf2md_ondemand.adapters.qt_asset_scheme import register_asset_scheme
from pdf2md_ondemand.ui.desktop import main_window


class _Bridge(QObject):
    contentChanged = Signal(str)
    documentContentChanged = Signal(str, str)
    commandRequested = Signal(str)
    documentSwitchRequested = Signal(str, str)
    documentCloseRequested = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._content = ""
        self._key = ""

    def setContent(self, content: str) -> None:
        if content != self._content:
            self._content = content
            self.contentChanged.emit(content)
            if self._key:
                self.documentContentChanged.emit(self._key, content)

    def switchDocument(self, key: str, content: str) -> None:
        self._key = key
        self.setContent(content)

    def closeDocumentState(self, key: str) -> None:
        self.documentCloseRequested.emit(key)

    def getDocumentKey(self, callback=None):
        if callback:
            callback(self._key)
        return self._key

    def getContent(self) -> str:
        return self._content

    def applyCommand(self, command: str) -> None:
        if command in {"bold", "italic", "heading", "link", "code"}:
            self.commandRequested.emit(command)


class _Editor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.bridge = _Bridge(self)


class _Preview(QWidget):
    externalLinkRequested = Signal(str)
    internalLinkRequested = Signal(str, str)

    def __init__(self, sessions) -> None:
        super().__init__()
        self.rendered: list[str] = []
        self.asset_root: Path | None = None

    def render_markdown(self, markdown: str) -> None:
        self.rendered.append(markdown)

    def set_asset_root(self, root: Path | None) -> None:
        self.asset_root = root


def _make_window(monkeypatch: MonkeyPatch):
    register_asset_scheme()
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(main_window, "EditorView", _Editor)
    monkeypatch.setattr(main_window, "PreviewView", _Preview)
    return app, main_window.MainWindow()


def test_workspace_tree_opens_note_and_preserves_cancelled_dirty_document(
    monkeypatch: MonkeyPatch,
) -> None:
    from uuid import uuid4

    root = Path("_test-workspace-") / uuid4().hex
    root.mkdir(parents=True)
    note = root / "note.md"
    note.write_text("workspace note", encoding="utf-8")
    app, window = _make_window(monkeypatch)
    try:
        assert window.open_workspace_at(root) is not None
        assert window.file_tree.topLevelItemCount() == 1
        assert [node.id for node in window.graph_view._graph.nodes] == ["note.md"]
        published_graph = window.graph_view._graph
        graph_errors: list[str] = []
        with monkeypatch.context() as patcher:

            def fail_reconcile(_session):
                raise OSError("index unavailable")

            patcher.setattr(type(window.workspace_session), "reconcile", fail_reconcile)
            patcher.setattr(
                window, "_show_error", lambda _title, text: graph_errors.append(text)
            )
            window._refresh_graph(rebuild=True)
        assert window.graph_view._graph is published_graph
        assert graph_errors and "index unavailable" in graph_errors[0]
        monkeypatch.setattr(main_window.QMessageBox, "information", lambda *_args: None)
        added = root / "added.md"
        added.write_text("new outside edit", encoding="utf-8")
        window._rebuild_workspace_index()
        assert window.file_tree.topLevelItemCount() == 2
        assert {node.id for node in window.graph_view._graph.nodes} == {
            "note.md",
            "added.md",
        }
        added.unlink()
        window._rebuild_workspace_index()
        assert window.file_tree.topLevelItemCount() == 1
        assert [node.id for node in window.graph_view._graph.nodes] == ["note.md"]
        original = root / "original.md"
        original.write_text("base", encoding="utf-8")
        session = window.open_document_at(original)
        assert session is not None
        window.editor_view.bridge.setContent("dirty")
        monkeypatch.setattr(
            main_window.QMessageBox,
            "warning",
            lambda *_args: QMessageBox.StandardButton.Cancel,
        )
        window._open_graph_node("note.md")
        assert window.document_session is not session
        assert window.editor_view.bridge.getContent() == "workspace note"
        assert window.graph_view._current_node == "note.md"
        item = window.file_tree.topLevelItem(0)
        window._open_tree_item(item, 0)
        assert window.document_session is not session
        assert window.editor_view.bridge.getContent() == "workspace note"
        monkeypatch.setattr(
            main_window.QMessageBox,
            "warning",
            lambda *_args: QMessageBox.StandardButton.Discard,
        )
        window._open_tree_item(item, 0)
        assert window.document_session is not None
        assert window.document_session.document.path == note.resolve()
        assert window.editor_view.bridge.getContent() == "workspace note"
    finally:
        window.close()
        app.processEvents()
        import shutil

        shutil.rmtree(root, ignore_errors=True)


def test_main_window_splits_panes_and_debounces_latest_editor_content(
    monkeypatch: MonkeyPatch,
) -> None:
    app, window = _make_window(monkeypatch)
    assert isinstance(window.splitter, QSplitter)
    assert window.splitter.count() == 2
    assert window.splitter.orientation() == Qt.Orientation.Horizontal

    window._schedule_preview("primeiro")
    window._schedule_preview("último Ω")
    assert window.preview_view.rendered == []

    loop = QEventLoop()
    QTimer.singleShot(main_window.PREVIEW_DEBOUNCE_MS + 30, loop.quit)
    loop.exec()

    assert window.preview_view.rendered == ["último Ω"]
    window.close()
    app.processEvents()


def test_graph_canvas_renders_typed_edges_and_selectable_nodes(
    monkeypatch: MonkeyPatch,
) -> None:
    from pdf2md_ondemand.domain.graph import (
        GraphEdge,
        GraphEdgeKind,
        GraphNode,
        KnowledgeGraph,
    )

    app, window = _make_window(monkeypatch)
    graph = KnowledgeGraph(
        (
            GraphNode("a.md", "a.md", "A", ()),
            GraphNode("b.md", "b.md", "B", ()),
            GraphNode("lonely.md", "lonely.md", "Lonely", ()),
        ),
        (GraphEdge("a.md", "b.md", GraphEdgeKind.WIKILINK),),
        (),
    )
    window.graph_view.set_graph(graph)
    assert len(window.graph_view.canvas._node_items) == 3
    assert len(window.graph_view.canvas._scene.items()) == 6
    assert "(1)" in window.graph_view.orphans_filter.text()
    window.graph_view.orphans_filter.setChecked(False)
    assert len(window.graph_view.canvas._node_items) == 2
    window.graph_view.orphans_filter.setChecked(True)
    assert len(window.graph_view.canvas._node_items) == 3
    window.graph_view.select_node("b.md")
    assert window.graph_view._current_node == "b.md"
    window.close()
    app.processEvents()


def test_preview_wikilink_uses_workspace_navigation_flow(
    monkeypatch: MonkeyPatch,
) -> None:
    from shutil import rmtree
    from uuid import uuid4

    root = Path("_test-workspace-") / uuid4().hex
    root.mkdir(parents=True)
    source = root / "source.md"
    target = root / "target.md"
    source.write_text("[[target|Open target]]", encoding="utf-8")
    target.write_text("# Target", encoding="utf-8")
    app, window = _make_window(monkeypatch)
    try:
        assert window.open_workspace_at(root) is not None
        assert window.open_document_at(source) is not None
        window._open_preview_internal_link("target", "wikilink")
        assert window.document_session is not None
        assert window.document_session.document.path == target.resolve()
    finally:
        window.close()
        app.processEvents()
        rmtree(root, ignore_errors=True)


def test_standalone_preview_link_still_works_with_workspace_open(
    monkeypatch: MonkeyPatch,
) -> None:
    from shutil import rmtree
    from uuid import uuid4

    base = Path("_test-preview-standalone-") / uuid4().hex
    workspace = base / "workspace"
    workspace.mkdir(parents=True)
    source = base / "source.md"
    target = base / "target.md"
    source.write_text("[Open](target.md)", encoding="utf-8")
    target.write_text("# Target", encoding="utf-8")
    (workspace / "inside.md").write_text("# Inside", encoding="utf-8")
    app, window = _make_window(monkeypatch)
    try:
        assert window.open_workspace_at(workspace) is not None
        assert window.open_document_at(source) is not None
        window._open_preview_internal_link("target.md", "markdown")
        assert window.document_session is not None
        assert window.document_session.document.path == target.resolve()
    finally:
        window.close()
        app.processEvents()
        rmtree(base, ignore_errors=True)


def test_minimal_workspace_note_and_preview_workflow(
    monkeypatch: MonkeyPatch,
) -> None:
    from shutil import rmtree
    from uuid import uuid4

    root = Path("_test-workspace-") / uuid4().hex
    root.mkdir(parents=True)
    app, window = _make_window(monkeypatch)
    try:
        assert window.open_workspace_at(root) is not None
        monkeypatch.setattr(
            main_window.QInputDialog,
            "getText",
            lambda *_args: ("fresh note", True),
        )
        window._new_markdown_file()
        note = root / "fresh note.md"
        assert note.is_file()
        assert window.document_session is not None
        assert window.document_session.document.path == note.resolve()
        assert window.file_tree.topLevelItemCount() == 1
        assert [node.id for node in window.graph_view._graph.nodes] == ["fresh note.md"]

        window.show_preview_action.setChecked(False)
        assert window.preview_view.isHidden()
        window.show_preview_action.setChecked(True)
        assert not window.preview_view.isHidden()
        assert window.close_note()
        assert window.document_session is None
        assert window.workspace_session is not None
    finally:
        window.close()
        app.processEvents()
        rmtree(root, ignore_errors=True)


def test_format_toolbar_actions_dispatch_narrow_bridge_commands(
    monkeypatch: MonkeyPatch,
) -> None:
    app, window = _make_window(monkeypatch)
    commands: list[str] = []
    window.editor_view.bridge.commandRequested.connect(commands.append)

    assert set(window.format_actions) == {"bold", "italic", "heading", "link", "code"}
    for action in window.format_actions.values():
        action.trigger()

    assert commands == ["bold", "italic", "heading", "link", "code"]
    window.close()
    app.processEvents()


def test_external_link_requires_confirmation_before_opening_browser(
    monkeypatch: MonkeyPatch,
) -> None:
    app, window = _make_window(monkeypatch)
    prompts: list[str] = []
    opened: list[str] = []
    monkeypatch.setattr(
        main_window.QMessageBox,
        "question",
        lambda *args: prompts.append(args[2]) or QMessageBox.StandardButton.No,
    )
    monkeypatch.setattr(
        main_window.QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toString()) or True,
    )

    window.preview_view.externalLinkRequested.emit("https://example.test/")
    assert prompts and "https://example.test/" in prompts[0]
    assert opened == []

    monkeypatch.setattr(
        main_window.QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )
    window.preview_view.externalLinkRequested.emit("https://example.test/")
    assert opened == ["https://example.test/"]
    window.close()
    app.processEvents()


def test_open_save_and_save_as_sync_editor_session_and_asset_root(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    app, window = _make_window(monkeypatch)
    source = tmp_path / "note.md"
    initial = "---\r\ntitle: x\r\n---\r\n:::unknown\r\n"
    source.write_bytes(b"\xef\xbb\xbf" + initial.encode("utf-8"))

    session = window.open_document_at(source)
    assert session.document.content == initial
    assert not session.dirty
    assert window.editor_view.bridge.getContent() == initial
    assert window.preview_view.asset_root == tmp_path
    assert window.windowTitle() == "note.md - PDF2MD_OnDemand"

    changed = initial + "Unicode: Ω\n"
    window.editor_view.bridge.setContent(changed)
    assert session.dirty
    assert window.windowTitle() == "note.md* - PDF2MD_OnDemand"
    assert window.save_current_to_disk() == source
    assert source.read_bytes() == b"\xef\xbb\xbf" + changed.encode("utf-8")
    assert not session.dirty
    assert window.windowTitle() == "note.md - PDF2MD_OnDemand"

    copy = tmp_path / "copy.md"
    assert window.save_as_to(copy) == copy
    assert copy.read_bytes() == source.read_bytes()
    assert session.document.path == copy
    assert window.preview_view.asset_root == tmp_path
    assert not session.dirty

    window.close()
    app.processEvents()


def test_save_as_existing_destination_requires_dialog_confirmation(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    app, window = _make_window(monkeypatch)
    source = tmp_path / "source.md"
    source.write_text("original", encoding="utf-8")
    target = tmp_path / "target.md"
    target.write_text("keep", encoding="utf-8")
    session = window.open_document_at(source)
    window.editor_view.bridge.setContent("replacement")
    monkeypatch.setattr(
        main_window.QFileDialog,
        "getSaveFileName",
        lambda *_args: (str(target), ""),
    )
    monkeypatch.setattr(
        main_window.QMessageBox,
        "question",
        lambda *_args: main_window.QMessageBox.StandardButton.No,
    )

    window._save_as_dialog()

    assert target.read_text(encoding="utf-8") == "keep"
    assert session.document.path == source
    assert session.dirty

    monkeypatch.setattr(
        main_window.QMessageBox,
        "question",
        lambda *_args: main_window.QMessageBox.StandardButton.Yes,
    )
    window._save_as_dialog()
    assert target.read_text(encoding="utf-8") == "replacement"
    assert session.document.path == target
    assert not session.dirty

    window.close()
    app.processEvents()


def test_external_modification_is_reported_and_save_is_cancelled(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    app, window = _make_window(monkeypatch)
    path = tmp_path / "note.md"
    path.write_text("original", encoding="utf-8")
    session = window.open_document_at(path)
    window.editor_view.bridge.setContent("mine")
    path.write_text("external", encoding="utf-8")
    errors: list[tuple[str, str]] = []
    monkeypatch.setattr(
        main_window.QMessageBox,
        "critical",
        lambda _parent, title, message: errors.append((title, message)),
    )

    window._save_action()

    assert path.read_text(encoding="utf-8") == "external"
    assert session.dirty
    assert errors and "changed outside" in errors[0][1]

    monkeypatch.setattr(
        main_window.QMessageBox,
        "warning",
        lambda *_args: main_window.QMessageBox.StandardButton.Discard,
    )
    window.close()
    app.processEvents()


def test_open_dialog_and_save_button_route_pathless_session_to_save_as(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    app, window = _make_window(monkeypatch)
    source = tmp_path / "opened.md"
    source.write_text("opened", encoding="utf-8")
    monkeypatch.setattr(
        main_window.QFileDialog,
        "getOpenFileName",
        lambda *_args: (str(source), ""),
    )

    window._open_dialog()

    assert window.document_session is not None
    assert window.document_session.document.path == source
    assert window.editor_view.bridge.getContent() == "opened"

    pathless = window.new_document_tab()
    window.editor_view.bridge.setContent("new content")
    destination = tmp_path / "new.md"
    monkeypatch.setattr(
        main_window.QFileDialog,
        "getSaveFileName",
        lambda *_args: (str(destination), ""),
    )

    window._save_action()

    assert destination.read_text(encoding="utf-8") == "new content"
    assert pathless.document.path == destination
    assert not pathless.dirty

    window.close()
    app.processEvents()


def test_open_discard_replaces_dirty_session_and_updates_title(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    app, window = _make_window(monkeypatch)
    original = tmp_path / "original.md"
    target = tmp_path / "target.md"
    original.write_text("base", encoding="utf-8")
    target.write_text("new document", encoding="utf-8")
    window.open_document_at(original)
    window.editor_view.bridge.setContent("unsaved edit")
    monkeypatch.setattr(
        main_window.QFileDialog,
        "getOpenFileName",
        lambda *_args: (str(target), ""),
    )
    monkeypatch.setattr(
        main_window.QMessageBox,
        "warning",
        lambda *_args: main_window.QMessageBox.StandardButton.Discard,
    )

    window._open_dialog()

    assert window.document_session is not None
    assert window.document_session.document.path == target
    assert window.editor_view.bridge.getContent() == "new document"
    assert window.windowTitle() == "target.md - PDF2MD_OnDemand"
    assert original.read_text(encoding="utf-8") == "base"
    window.close()
    app.processEvents()


def test_cancel_open_and_close_preserves_dirty_document(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    app, window = _make_window(monkeypatch)
    original = tmp_path / "original.md"
    target = tmp_path / "target.md"
    original.write_text("base", encoding="utf-8")
    target.write_text("target", encoding="utf-8")
    session = window.open_document_at(original)
    assert session is not None
    window.editor_view.bridge.setContent("unsaved edit")
    monkeypatch.setattr(
        main_window.QMessageBox,
        "warning",
        lambda *_args: main_window.QMessageBox.StandardButton.Cancel,
    )

    target_session = window.open_document_at(target)
    assert target_session is not None
    assert window.document_session is target_session
    assert window.editor_view.bridge.getContent() == "target"
    window._activate_document_tab(window.document_tabs.key_for_session(session))
    assert window.editor_view.bridge.getContent() == "unsaved edit"

    window.show()
    assert not window.close()
    assert window.isVisible()
    assert session.dirty
    assert window.editor_view.bridge.getContent() == "unsaved edit"
    window.hide()
    app.processEvents()


def test_close_save_failure_cancels_close_and_keeps_external_content(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    app, window = _make_window(monkeypatch)
    path = tmp_path / "note.md"
    path.write_text("base", encoding="utf-8")
    session = window.open_document_at(path)
    assert session is not None
    window.editor_view.bridge.setContent("mine")
    path.write_text("external", encoding="utf-8")
    errors: list[str] = []
    monkeypatch.setattr(
        main_window.QMessageBox,
        "warning",
        lambda *_args: main_window.QMessageBox.StandardButton.Save,
    )
    monkeypatch.setattr(
        main_window.QMessageBox,
        "critical",
        lambda _parent, _title, message: errors.append(message),
    )
    window.show()

    assert not window.close()
    assert window.isVisible()
    assert path.read_text(encoding="utf-8") == "external"
    assert session.dirty
    assert errors and "changed outside" in errors[0]
    window.hide()
    app.processEvents()


def test_layout_round_trips_with_isolated_qsettings(
    tmp_path: Path, monkeypatch
) -> None:
    register_asset_scheme()
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(main_window, "EditorView", _Editor)
    monkeypatch.setattr(main_window, "PreviewView", _Preview)
    settings_path = tmp_path / "ui.ini"
    settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    first = main_window.MainWindow(settings)
    first.show()
    app.processEvents()
    first.resize(1111, 777)
    first.splitter.setSizes([700, 411])
    first.show_preview_action.setChecked(False)
    first._save_layout()
    first._save_layout()
    first.close()
    app.processEvents()

    restored = main_window.MainWindow(
        QSettings(str(settings_path), QSettings.Format.IniFormat)
    )
    assert restored._settings.value("window/size").width() == 1111
    assert restored._settings.value("window/size").height() == 777
    assert not restored.show_preview_action.isChecked()
    restored.close()
    app.processEvents()


def test_opening_documents_creates_tabs_and_reuses_resolved_path(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    app, window = _make_window(monkeypatch)
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    monkeypatch.setattr(
        main_window.QMessageBox,
        "warning",
        lambda *_args: QMessageBox.StandardButton.Discard,
    )
    try:
        first_session = window.open_document_at(first)
        first_key = window._active_tab_key
        assert first_key is not None
        second_session = window.open_document_at(second)
        assert second_session is not first_session
        assert window.tab_bar.count() == 2
        assert window.editor_view.bridge.getContent() == "second"
        window.editor_view.bridge.documentContentChanged.emit(first_key, "late edit")
        assert first_session.dirty
        assert first_session.document.content == "late edit"
        assert window.editor_view.bridge.getContent() == "second"
        assert window.open_document_at(first.resolve()) is first_session
        assert window._active_tab_key == first_key
        assert window.tab_bar.count() == 2
    finally:
        window.close()
        app.processEvents()


def test_workspace_close_removes_owned_tabs_and_preserves_external_tabs(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    app, window = _make_window(monkeypatch)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    inside = workspace / "inside.md"
    outside = tmp_path / "outside.md"
    inside.write_text("inside", encoding="utf-8")
    outside.write_text("outside", encoding="utf-8")
    try:
        window.open_workspace_at(workspace)
        inside_session = window.open_document_at(inside)
        outside_session = window.open_document_at(outside)
        assert window.close_workspace()
        assert window.workspace_session is None
        assert inside_session not in [
            tab.session for tab in window.document_tabs._tabs.values()
        ]
        assert outside_session in [
            tab.session for tab in window.document_tabs._tabs.values()
        ]
        assert window.document_session is outside_session
    finally:
        window.close()
        app.processEvents()


def test_cancelled_workspace_close_keeps_tabs_and_workspace(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    app, window = _make_window(monkeypatch)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    inside = workspace / "inside.md"
    inside.write_text("inside", encoding="utf-8")
    try:
        window.open_workspace_at(workspace)
        session = window.open_document_at(inside)
        window.editor_view.bridge.setContent("dirty")
        monkeypatch.setattr(
            main_window.QMessageBox,
            "warning",
            lambda *_args: QMessageBox.StandardButton.Cancel,
        )
        assert not window.close_workspace()
        assert window.workspace_session is not None
        assert session in [tab.session for tab in window.document_tabs._tabs.values()]
        assert session.dirty
    finally:
        monkeypatch.setattr(
            main_window.QMessageBox,
            "warning",
            lambda *_args: QMessageBox.StandardButton.Discard,
        )
        window.close()
        app.processEvents()
