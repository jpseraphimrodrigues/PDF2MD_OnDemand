"""Narrow text-only bridge between the editor page and Qt."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot


class EditorBridge(QObject):
    """Expose only Markdown text synchronization to the editor WebView."""

    contentChanged = Signal(str)
    commandRequested = Signal(str)

    _COMMANDS = frozenset({"bold", "italic", "heading", "link", "code"})

    def __init__(self, content: str = "", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._content = content

    @Slot(str)
    def setContent(self, content: str) -> None:
        if content == self._content:
            return
        self._content = content
        self.contentChanged.emit(content)

    @Slot(result=str)
    def getContent(self) -> str:
        return self._content

    @Slot(str)
    def applyCommand(self, command: str) -> None:
        """Forward only the supported formatting commands to CodeMirror."""
        if command in self._COMMANDS:
            self.commandRequested.emit(command)
