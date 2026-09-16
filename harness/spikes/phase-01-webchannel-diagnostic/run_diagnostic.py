"""Minimal, disposable QWebChannel diagnostic."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWidgets import QApplication
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

ROOT = Path(__file__).parent


class DiagnosticPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level: QWebEnginePage.JavaScriptConsoleMessageLevel, message: str, line: int, source: str) -> None:
        print(f"JS console level={level.name} line={line}: {message} ({source})")


class Bridge(QObject):
    contentChanged = Signal(str)
    readySignal = Signal()

    @Slot()
    def editorReady(self) -> None:
        print("JS -> Python: editorReady()")
        self.readySignal.emit()

    @Slot(str)
    def receiveContent(self, text: str) -> None:
        self.contentChanged.emit(text)

    @Slot(str)
    def ready(self, source: str) -> None:
        print(f"JS -> Python: ready({source!r})")

    @Slot(str, result=str)
    def ping(self, value: str) -> str:
        result = f"pong: {value}"
        print(f"JS -> Python: ping({value!r}) -> {result!r}")
        return result


class Diagnostic:
    def __init__(self) -> None:
        self.view = QWebEngineView()
        self.page = DiagnosticPage(self.view)
        self.view.setPage(self.page)
        self.channel = QWebChannel(self.page)
        self.bridge = Bridge(self.channel)
        self.channel.registerObject("bridge", self.bridge)
        self.bridge.contentChanged.connect(lambda text: print(f"CodeMirror -> Python: {text!r}"))
        self.page.setWebChannel(self.channel)
        self.page.loadFinished.connect(self.loaded)
        self.bridge.readySignal.connect(self._editor_ready)
        self.page.load(QUrl.fromLocalFile(str(ROOT / "editor.html")))

    def _editor_ready(self) -> None:
        text = "ação Ω "
        expression = f"window.editorApi.setContent({text!r}); window.editorApi.getContent()"
        self.page.runJavaScript(expression, lambda value: print(f"Python -> CodeMirror -> Python: {value!r}"))

    def loaded(self, ok: bool) -> None:
        print(f"HTML loadFinished={ok}")
        expressions = {
            "typeof qt": "typeof qt",
            "typeof QWebChannel": "typeof QWebChannel",
            "typeof qt.webChannelTransport": "typeof qt === 'undefined' ? 'qt-undefined' : typeof qt.webChannelTransport",
            "document.readyState": "document.readyState",
            "location.href": "location.href",
        }
        for label, expression in expressions.items():
            self.page.runJavaScript(expression, lambda value, name=label: print(f"{name} -> {value}"))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    app = QApplication.instance() or QApplication(sys.argv)
    diagnostic = Diagnostic()
    diagnostic.view.show()
    app.processEvents()
    from PySide6.QtCore import QTimer

    QTimer.singleShot(2500, app.quit)
    result = app.exec()
    print(f"event loop exit={result}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
