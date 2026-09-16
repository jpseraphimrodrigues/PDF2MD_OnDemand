"""Additional final-spike measurements; disposable and non-production."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter
from PySide6.QtWebEngineWidgets import QWebEngineView
from run_spike import FinalSpike, ROOT, SOURCE

def js(page, expression, label):
    page.runJavaScript(expression, lambda value: print(label, repr(value)))

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    app = QApplication.instance() or QApplication(sys.argv)
    spike = FinalSpike(); window = QMainWindow(); window.setCentralWidget(spike.widget()); window.resize(1200, 700); window.show()
    def tests():
        base = "texto"
        for command in ["bold", "italic", "code", "link"]:
            js(spike.editor_page, f"window.editorApi.setContent({json.dumps(base)}); window.editorApi.select(0, 5); window.editorApi.applyCommand('{command}'); window.editorApi.getContent()", command)
        js(spike.editor_page, "window.editorApi.setContent('Título'); window.editorApi.select(0, 6); window.editorApi.applyCommand('heading'); window.editorApi.getContent()", "heading")
        js(spike.editor_page, "window.editorApi.setContent('abcdef'); window.editorApi.select(2, 5); JSON.stringify(window.editorApi.selection())", "selection")
        js(spike.editor_page, "window.editorApi.getContent().slice(2,5)", "selected-text")
        js(spike.editor_page, "window.editorApi.search('cde') && !window.editorApi.search('missing')", "search")
        js(spike.editor_page, "window.editorApi.setContent('original'); window.editorApi.select(8,8); window.editorApi.setContent('original edit'); window.editorApi.undo(); window.editorApi.getContent()", "undo")
        js(spike.editor_page, "window.editorApi.redo(); window.editorApi.getContent()", "redo")
        for lines, label in [(10000, "medium"), (75000, "large")]:
            data = ("# heading\\ntext **bold**\\n```code\\nX\\n```\\n" * (lines // 4))[:lines * 12]
            started = time.perf_counter(); js(spike.editor_page, f"window.editorApi.setContent({json.dumps(data)}); window.editorApi.getContent().length", label + " editor length")
            print(label, "python dispatch ms", round((time.perf_counter()-started)*1000, 2))
    QTimer.singleShot(1200, tests); QTimer.singleShot(4000, app.quit)
    code = app.exec(); print("events=", spike.change_count, "renders=", spike.render_count, "exit=", code); return code

if __name__ == "__main__": raise SystemExit(main())
