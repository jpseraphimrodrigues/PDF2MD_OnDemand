"""Disposable preview security, URL and isolation checks."""
from __future__ import annotations
import json, sys
from pathlib import Path
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

ROOT = Path(__file__).parent
MARKDOWN = """<b>HTML TEST</b>

<script>window.__malicious_test = \"EXECUTED\";</script>

[HTTPS](https://example.com)
[FILE](file:///C:/Windows/System32)
[JS](javascript:alert(1))
[DATA](data:text/html,<script>alert(1)</script>)

![Teste](assets/test.png)"""

class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source): print(f"JS[{level.name}] {line}: {message}")

class Check:
    def __init__(self):
        self.view = QWebEngineView(); self.page = Page(self.view); self.view.setPage(self.page)
        self.page.loadFinished.connect(self.loaded); self.page.setUrl(QUrl.fromLocalFile(str(ROOT / "preview.html")))
    def loaded(self, ok):
        print("preview loadFinished=", ok)
        self.page.runJavaScript(f"window.renderMarkdown({json.dumps(MARKDOWN)})", lambda _: self.inspect())
    def inspect(self):
        expression = "JSON.stringify({html:document.querySelector('#preview').innerHTML, malicious:typeof window.__malicious_test, hasBridge:typeof window.editorBridge})"
        self.page.runJavaScript(expression, lambda value: print("preview inspection=", value))

def main():
    sys.stdout.reconfigure(encoding="utf-8"); app = QApplication.instance() or QApplication(sys.argv)
    assets = ROOT / "assets"; assets.mkdir(exist_ok=True); image = QImage(2, 2, QImage.Format.Format_RGB32); image.fill(QColor("#3b82f6")); image.save(str(assets / "test.png"))
    check = Check(); check.view.show(); QTimer.singleShot(1500, app.quit); return app.exec()

if __name__ == "__main__": raise SystemExit(main())
