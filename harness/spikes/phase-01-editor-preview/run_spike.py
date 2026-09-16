"""Disposable Phase 1 editor/preview architecture experiments."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication, QPlainTextEdit


ROOT = Path(__file__).parent


class NarrowBridge(QObject):
    """A deliberately tiny bridge-shaped object for the WebEngine design."""

    contentChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._content = ""

    @Slot(str)
    def setContent(self, text: str) -> None:
        self._content = text
        self.contentChanged.emit(text)

    @Slot(result=str)
    def getContent(self) -> str:
        return self._content

    @Slot(str, result=str)
    def applyBold(self, selected: str) -> str:
        return f"**{selected}**"


def native_experiment(app: QApplication, source: str) -> dict[str, object]:
    editor = QPlainTextEdit()
    editor.setPlainText(source)
    events: list[str] = []
    editor.textChanged.connect(lambda: events.append(editor.toPlainText()))
    cursor = editor.textCursor()
    cursor.setPosition(source.index("# Título") + len("# Título"))
    editor.setTextCursor(cursor)
    editor.insertPlainText(" editado")
    app.processEvents()
    recovered = editor.toPlainText()
    editor.undo()
    undo_value = editor.toPlainText()
    editor.redo()
    redo_value = editor.toPlainText()
    return {
        "round_trip_preserved": all(
            marker in recovered for marker in ("preserve-me", "unknown-language", "⚡")
        ),
        "change_events": len(events),
        "undo_restores_original": undo_value == source,
        "redo_restores_edit": redo_value == recovered,
        "bold": f"**{source[:5]}**",
    }


def bridge_experiment(source: str) -> dict[str, object]:
    bridge = NarrowBridge()
    preview_updates: list[str] = []
    bridge.contentChanged.connect(preview_updates.append)
    bridge.setContent(source)
    edited = source.replace("# Título", "# Título editado", 1)
    bridge.setContent(edited)
    return {
        "preview_updates": len(preview_updates),
        "unicode_round_trip": bridge.getContent().endswith("⚡\n"),
        "bold": bridge.applyBold("texto"),
        "exposed_methods": ["setContent", "getContent", "applyBold"],
    }


def large_document_experiment(source: str) -> dict[str, object]:
    large = source * 2500
    start = time.perf_counter()
    recovered = large.replace("# Título", "# Título editado", 1)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {
        "lines": large.count("\n"),
        "edit_ms": round(elapsed_ms, 2),
        "content_recovered": "# Título editado" in recovered,
    }


def main() -> None:
    source = (ROOT / "fixture.md").read_text(encoding="utf-8")
    app = QApplication.instance() or QApplication([])
    print("native:", native_experiment(app, source))
    print("web-bridge-model:", bridge_experiment(source))
    print("large-document:", large_document_experiment(source))


if __name__ == "__main__":
    main()
