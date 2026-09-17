"""Standalone Markdown editor and preview composition."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QSplitter

from pdf2md_ondemand.adapters.filesystem_document_store import (
    DocumentReadError,
    DocumentWriteError,
    FilesystemDocumentStore,
)
from pdf2md_ondemand.application.asset_sessions import AssetSessionRegistry
from pdf2md_ondemand.application.document_session import DocumentSession
from pdf2md_ondemand.application.open_document import open_document
from pdf2md_ondemand.application.save_document import (
    DestinationExistsError,
    ExternalModificationError,
    UnsavedDocumentError,
    save_document,
    save_document_as,
)
from pdf2md_ondemand.ui.desktop.editor_view import EditorView
from pdf2md_ondemand.ui.desktop.preview_view import PreviewView

PREVIEW_DEBOUNCE_MS = 200


class MainWindow(QMainWindow):
    """Resizable side-by-side Editor and Preview, without document lifecycle."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF2MD_OnDemand")
        self.resize(960, 640)
        self.document_store = FilesystemDocumentStore()
        self.document_session: DocumentSession | None = None
        self.editor_view = EditorView()
        self.asset_sessions = AssetSessionRegistry()
        self.preview_view = PreviewView(self.asset_sessions)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.editor_view)
        self.splitter.addWidget(self.preview_view)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.setCentralWidget(self.splitter)

        self._pending_markdown = ""
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(PREVIEW_DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._render_pending_preview)
        self.editor_view.bridge.contentChanged.connect(self._schedule_preview)
        self.editor_view.bridge.contentChanged.connect(self._update_document_content)
        self._create_file_actions()

    def open_document_at(self, path: Path) -> DocumentSession:
        """Open a Markdown file and make it the current editing session."""
        session = open_document(path, self.document_store)
        self.document_session = session
        self.editor_view.bridge.setContent(session.document.content)
        self.preview_view.set_asset_root(path.parent)
        self._schedule_preview(session.document.content)
        return session

    def save_current_to_disk(self) -> Path:
        """Save the current Editor text using the session's version token."""
        session = self._require_session()
        session.edit(self.editor_view.bridge.getContent())
        return save_document(session, self.document_store)

    def save_as_to(self, path: Path, *, overwrite: bool = False) -> Path:
        """Save the current Editor text to a chosen destination."""
        session = self._require_session()
        session.edit(self.editor_view.bridge.getContent())
        saved_path = save_document_as(
            session, path, self.document_store, overwrite=overwrite
        )
        self.preview_view.set_asset_root(saved_path.parent)
        return saved_path

    def _require_session(self) -> DocumentSession:
        if self.document_session is None:
            raise UnsavedDocumentError("Open a Markdown document first")
        return self.document_session

    def _update_document_content(self, markdown: str) -> None:
        if self.document_session is not None:
            self.document_session.edit(markdown)

    def _create_file_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        self.open_action = QAction("&Open…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self._open_dialog)
        file_menu.addAction(self.open_action)

        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self._save_action)
        file_menu.addAction(self.save_action)

        self.save_as_action = QAction("Save &As…", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self._save_as_dialog)
        file_menu.addAction(self.save_as_action)

    def _open_dialog(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Markdown",
            "",
            "Markdown files (*.md);;All files (*)",
        )
        if not filename:
            return
        try:
            self.open_document_at(Path(filename))
        except DocumentReadError as exc:
            self._show_error("Could not open document", str(exc))

    def _save_action(self) -> None:
        if self.document_session is None:
            self._show_error("Could not save document", "Open a Markdown file first.")
            return
        if self.document_session.document.path is None:
            self._save_as_dialog()
            return
        try:
            self.save_current_to_disk()
        except (
            DocumentReadError,
            DocumentWriteError,
            ExternalModificationError,
        ) as exc:
            self._show_error("Could not save document", str(exc))

    def _save_as_dialog(self) -> None:
        if self.document_session is None:
            self._show_error("Could not save document", "Open a Markdown file first.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Markdown As",
            "",
            "Markdown files (*.md);;All files (*)",
        )
        if not filename:
            return
        path = Path(filename)
        overwrite = False
        if path.exists():
            answer = QMessageBox.question(
                self,
                "Replace existing file?",
                f"{path} already exists. Replace it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            overwrite = True
        try:
            self.save_as_to(path, overwrite=overwrite)
        except (
            DestinationExistsError,
            DocumentReadError,
            DocumentWriteError,
            ExternalModificationError,
        ) as exc:
            self._show_error("Could not save document", str(exc))

    def _show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    def _schedule_preview(self, markdown: str) -> None:
        self._pending_markdown = markdown
        self._preview_timer.start()

    def _render_pending_preview(self) -> None:
        self.preview_view.render_markdown(self._pending_markdown)
