"""Composition contract for the standalone editor and preview panes."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEventLoop, QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QSplitter, QWidget
from pytest import MonkeyPatch

from pdf2md_ondemand.application.document_session import DocumentSession
from pdf2md_ondemand.domain.document import Document
from pdf2md_ondemand.ui.desktop import main_window


class _Bridge(QObject):
    contentChanged = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._content = ""

    def setContent(self, content: str) -> None:
        if content != self._content:
            self._content = content
            self.contentChanged.emit(content)

    def getContent(self) -> str:
        return self._content


class _Editor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.bridge = _Bridge(self)


class _Preview(QWidget):
    def __init__(self, sessions) -> None:
        super().__init__()
        self.rendered: list[str] = []
        self.asset_root: Path | None = None

    def render_markdown(self, markdown: str) -> None:
        self.rendered.append(markdown)

    def set_asset_root(self, root: Path | None) -> None:
        self.asset_root = root


def _make_window(monkeypatch: MonkeyPatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(main_window, "EditorView", _Editor)
    monkeypatch.setattr(main_window, "PreviewView", _Preview)
    return app, main_window.MainWindow()


def test_main_window_splits_panes_and_debounces_latest_editor_content(
    monkeypatch: MonkeyPatch,
) -> None:
    app, window = _make_window(monkeypatch)
    assert isinstance(window.splitter, QSplitter)
    assert window.splitter.count() == 2
    assert window.splitter.orientation() == Qt.Orientation.Horizontal

    window.editor_view.bridge.contentChanged.emit("primeiro")
    window.editor_view.bridge.contentChanged.emit("último Ω")
    assert window.preview_view.rendered == []

    loop = QEventLoop()
    QTimer.singleShot(main_window.PREVIEW_DEBOUNCE_MS + 30, loop.quit)
    loop.exec()

    assert window.preview_view.rendered == ["último Ω"]
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

    pathless = DocumentSession.opened(Document(None, "untitled"), None)
    window.document_session = pathless
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

    assert window.open_document_at(target) is None
    assert window.document_session is session
    assert window.editor_view.bridge.getContent() == "unsaved edit"
    assert window.windowTitle() == "original.md* - PDF2MD_OnDemand"

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
