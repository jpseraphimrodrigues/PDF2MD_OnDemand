"""Final disposable end-to-end editor/preview experiment."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

ROOT = Path(__file__).parent
SOURCE = (ROOT / "fixture.md").read_text(encoding="utf-8")

class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source): print(f"JS[{level.name}] {line}: {message}")

class Bridge(QObject):
    contentChanged = Signal(str); readySignal = Signal()
    @Slot()
    def editorReady(self): print("editorReady() from JS"); self.readySignal.emit()
    @Slot(str)
    def receiveContent(self, text): self.contentChanged.emit(text)

class FinalSpike:
    def __init__(self):
        self.editor = QWebEngineView(); self.preview = QWebEngineView()
        self.editor_page = Page(self.editor); self.preview_page = Page(self.preview)
        self.editor.setPage(self.editor_page); self.preview.setPage(self.preview_page)
        self.bridge = Bridge(self.editor); self.channel = QWebChannel(self.editor_page)
        self.channel.registerObject("editorBridge", self.bridge); self.editor_page.setWebChannel(self.channel)
        self.bridge.contentChanged.connect(self.changed); self.bridge.readySignal.connect(self.ready)
        self.render_count = 0; self.change_count = 0; self.last = ""
        self.timer = QTimer(); self.timer.setSingleShot(True); self.timer.setInterval(200); self.timer.timeout.connect(self.render)
        self._settings(self.editor, True); self._settings(self.preview, False)
        self.editor.loadFinished.connect(lambda ok: print("editor loadFinished=", ok))
        self.preview.loadFinished.connect(self.preview_loaded)
        self.editor.setUrl(QUrl.fromLocalFile(str(ROOT / "editor.html")))
        self.preview.setUrl(QUrl.fromLocalFile(str(ROOT / "preview.html")))
    def _settings(self, view, editor):
        s = view.settings(); A = QWebEngineSettings.WebAttribute
        for attr, value in [(A.JavascriptEnabled, True), (A.LocalStorageEnabled, False), (A.LocalContentCanAccessRemoteUrls, False), (A.LocalContentCanAccessFileUrls, True), (A.JavascriptCanOpenWindows, False)]: s.setAttribute(attr, value)
    def preview_loaded(self, ok):
        print("preview loadFinished=", ok)
        self.preview.page().runJavaScript("typeof window.renderMarkdown", lambda value: print("renderMarkdown=", value))
    def ready(self):
        payload = json.dumps(SOURCE, ensure_ascii=False)
        self.editor_page.runJavaScript(f"window.editorApi.setContent({payload}); window.editorApi.getContent()", lambda value: print("Python→CodeMirror→Python:", value == SOURCE))
    def changed(self, text): self.change_count += 1; self.last = text; self.timer.start()
    def render(self):
        self.render_count += 1; self.preview_page.runJavaScript(f"window.renderMarkdown({json.dumps(self.last, ensure_ascii=False)})")
    def widget(self):
        split = QSplitter(); split.addWidget(self.editor); split.addWidget(self.preview); return split

def main():
    sys.stdout.reconfigure(encoding="utf-8"); app = QApplication.instance() or QApplication(sys.argv)
    spike = FinalSpike(); window = QMainWindow(); window.setCentralWidget(spike.widget()); window.resize(1200, 700); window.show()
    QTimer.singleShot(3500, app.quit); code = app.exec(); print("events=", spike.change_count, "renders=", spike.render_count, "exit=", code); return code

if __name__ == "__main__": raise SystemExit(main())
