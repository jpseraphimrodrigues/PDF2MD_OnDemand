"""Executable B1/B2 WebEngine and QWebChannel experiment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtWidgets import QApplication, QSplitter
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

ROOT = Path(__file__).parent
SOURCE = (ROOT / "fixture.md").read_text(encoding="utf-8") if (ROOT / "fixture.md").exists() else "# título\n"


class EditorBridge(QObject):
    contentChanged = Signal(str)
    ready = Signal()

    @Slot()
    def documentReady(self) -> None:
        self.ready.emit()

    @Slot(str)
    def receiveContent(self, text: str) -> None:
        self.contentChanged.emit(text)


class PreviewBridge(QObject):
    ready = Signal()

    @Slot()
    def previewReady(self) -> None:
        self.ready.emit()


class Harness:
    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.editor = QWebEngineView()
        self.preview = QWebEngineView()
        self.editor.setObjectName("editorWebView")
        self.preview.setObjectName("previewWebView")
        self._configure(self.editor, editor=True)
        self._configure(self.preview, editor=False)
        self.editor_bridge = EditorBridge()
        self.preview_bridge = PreviewBridge()
        self.editor_channel = QWebChannel(self.editor.page())
        self.preview_channel = QWebChannel(self.preview.page())
        self.editor_channel.registerObject("editorBridge", self.editor_bridge)
        self.preview_channel.registerObject("previewBridge", self.preview_bridge)
        self.editor.page().setWebChannel(self.editor_channel)
        self.preview.page().setWebChannel(self.preview_channel)
        self.editor_bridge.contentChanged.connect(self._debounced_preview)
        self.preview_bridge.ready.connect(self._preview_ready)
        self.renders = 0
        self.last_content = ""
        self.pending = QTimer()
        self.pending.setSingleShot(True)
        self.pending.setInterval(150)
        self.pending.timeout.connect(self._render)
        self.editor.loadFinished.connect(self._editor_loaded)
        self.preview.loadFinished.connect(self._preview_loaded)
        self.editor.setUrl(QUrl.fromLocalFile(str(ROOT / "editor.html")))
        self.preview.setUrl(QUrl.fromLocalFile(str(ROOT / "preview.html")))

    def _configure(self, view: QWebEngineView, *, editor: bool) -> None:
        settings = view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, not editor)

    def _preview_ready(self) -> None:
        self.last_content = SOURCE
        self._render()

    def _editor_loaded(self, ok: bool) -> None:
        print("editor shell loaded:", ok)
        self.editor.page().runJavaScript("[typeof qt, typeof QWebChannel, typeof qt?.webChannelTransport]", print)

    def _preview_loaded(self, ok: bool) -> None:
        print("preview shell loaded:", ok)
        self.preview.page().runJavaScript("[typeof qt, typeof QWebChannel, typeof qt?.webChannelTransport]", print)

    def _debounced_preview(self, text: str) -> None:
        self.last_content = text
        self.pending.start()

    def _render(self) -> None:
        self.renders += 1
        payload = json.dumps(self.last_content, ensure_ascii=False)
        self.preview.page().runJavaScript(f"window.renderMarkdown({payload})")

    def b1_widget(self) -> QSplitter:
        split = QSplitter()
        split.addWidget(self.editor)
        split.addWidget(self.preview)
        return split


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    harness = Harness(app)
    window = harness.b1_widget()
    window.resize(1200, 700)
    window.show()
    QTimer.singleShot(4000, app.quit)
    result = app.exec()
    print("B1 two QWebEngineView event loop exit:", result)
    print("debounced preview renders:", harness.renders)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
