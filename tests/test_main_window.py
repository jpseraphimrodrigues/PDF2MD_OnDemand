"""Composition contract for the standalone editor and preview panes."""

from __future__ import annotations

from PySide6.QtCore import QEventLoop, QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QSplitter, QWidget
from pytest import MonkeyPatch

from pdf2md_ondemand.ui.desktop import main_window


class _Bridge(QObject):
    contentChanged = Signal(str)


class _Editor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.bridge = _Bridge(self)


class _Preview(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.rendered: list[str] = []

    def render_markdown(self, markdown: str) -> None:
        self.rendered.append(markdown)


def test_main_window_splits_panes_and_debounces_latest_editor_content(
    monkeypatch: MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(main_window, "EditorView", _Editor)
    monkeypatch.setattr(main_window, "PreviewView", _Preview)
    window = main_window.MainWindow()
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
