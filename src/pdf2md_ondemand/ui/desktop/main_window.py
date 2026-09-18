"""Standalone Markdown editor and preview composition."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pdf2md_ondemand.adapters.filesystem_document_store import (
    DocumentReadError,
    DocumentWriteError,
    FilesystemDocumentStore,
)
from pdf2md_ondemand.adapters.sqlite_workspace_index import SQLiteWorkspaceIndex
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
from pdf2md_ondemand.application.workspace_session import (
    WorkspaceDiscoveryError,
    WorkspaceEntry,
    WorkspaceSession,
    discover_markdown,
    open_workspace_search_result,
    search_workspace,
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
        self.workspace_session: WorkspaceSession | None = None
        self.editor_view = EditorView()
        self.asset_sessions = AssetSessionRegistry()
        self.preview_view = PreviewView(self.asset_sessions)
        self.preview_view.externalLinkRequested.connect(self._confirm_external_link)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.editor_view)
        self.splitter.addWidget(self.preview_view)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderHidden(True)
        self.file_tree.itemDoubleClicked.connect(self._open_tree_item)
        self.workspace_sidebar = QWidget()
        sidebar_layout = QVBoxLayout(self.workspace_sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.addWidget(self.file_tree)
        self._workspace_dock = QDockWidget("Workspace", self)
        self._workspace_dock.setWidget(self.workspace_sidebar)
        self._workspace_dock.setObjectName("workspaceDock")
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._workspace_dock)
        self._workspace_dock.hide()
        self.setCentralWidget(self.splitter)

        self._pending_markdown = ""
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(PREVIEW_DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._render_pending_preview)
        self.editor_view.bridge.contentChanged.connect(self._schedule_preview)
        self.editor_view.bridge.contentChanged.connect(self._update_document_content)
        self._create_file_actions()
        self._create_format_toolbar()
        self._update_window_title()

    def open_document_at(self, path: Path) -> DocumentSession | None:
        """Switch to a Markdown file after resolving any dirty session."""
        if not self._confirm_unsaved_changes():
            return None
        session = open_document(path, self.document_store)
        self.document_session = session
        self.editor_view.bridge.setContent(session.document.content)
        self.preview_view.set_asset_root(path.parent)
        self._schedule_preview(session.document.content)
        self._update_window_title()
        return session

    def save_current_to_disk(self) -> Path:
        """Save the current Editor text using the session's version token."""
        session = self._require_session()
        session.edit(self.editor_view.bridge.getContent())
        path = save_document(session, self.document_store)
        self._update_window_title()
        return path

    def save_as_to(self, path: Path, *, overwrite: bool = False) -> Path:
        """Save the current Editor text to a chosen destination."""
        session = self._require_session()
        session.edit(self.editor_view.bridge.getContent())
        saved_path = save_document_as(
            session, path, self.document_store, overwrite=overwrite
        )
        self.preview_view.set_asset_root(saved_path.parent)
        self._update_window_title()
        return saved_path

    def _require_session(self) -> DocumentSession:
        if self.document_session is None:
            raise UnsavedDocumentError("Open a Markdown document first")
        return self.document_session

    def _update_document_content(self, markdown: str) -> None:
        if self.document_session is not None:
            self.document_session.edit(markdown)
            self._update_window_title()

    def _create_file_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        self.open_action = QAction("&Open…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self._open_dialog)
        file_menu.addAction(self.open_action)
        self.open_folder_action = QAction("Open Folder…", self)
        self.open_folder_action.triggered.connect(self._open_folder_dialog)
        file_menu.addAction(self.open_folder_action)
        self.close_workspace_action = QAction("Close Workspace", self)
        self.close_workspace_action.triggered.connect(self.close_workspace)
        file_menu.addAction(self.close_workspace_action)
        self.search_workspace_action = QAction("Search Workspace…", self)
        self.search_workspace_action.triggered.connect(self._search_workspace_dialog)
        file_menu.addAction(self.search_workspace_action)
        self.rebuild_workspace_index_action = QAction("Rebuild Workspace Index", self)
        self.rebuild_workspace_index_action.triggered.connect(self._rebuild_workspace_index)
        file_menu.addAction(self.rebuild_workspace_index_action)

        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self._save_action)
        file_menu.addAction(self.save_action)

        self.save_as_action = QAction("Save &As…", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self._save_as_dialog)
        file_menu.addAction(self.save_as_action)

    def _create_format_toolbar(self) -> None:
        self.format_toolbar = QToolBar("Markdown", self)
        self.addToolBar(self.format_toolbar)
        labels = {
            "bold": "Bold",
            "italic": "Italic",
            "heading": "Heading",
            "link": "Link",
            "code": "Code",
        }
        self.format_actions: dict[str, QAction] = {}
        for command, label in labels.items():
            action = QAction(label, self)
            action.triggered.connect(
                lambda _checked=False, name=command: self._dispatch_editor_command(name)
            )
            self.format_toolbar.addAction(action)
            self.format_actions[command] = action

    def _dispatch_editor_command(self, command: str) -> None:
        self.editor_view.bridge.applyCommand(command)

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

    def open_workspace_at(self, root: Path) -> WorkspaceSession | None:
        """Switch workspace only after discovery succeeds and dirty state resolves."""
        try:
            entries = discover_markdown(root)
        except WorkspaceDiscoveryError as exc:
            self._show_error("Could not open workspace", str(exc))
            return None
        if not self._confirm_unsaved_changes():
            return None
        session = WorkspaceSession.open(root)
        self.workspace_session = session
        self._populate_tree(entries)
        self._workspace_dock.show()
        self.setWindowTitle(f"{session.root.path.name} - PDF2MD_OnDemand")
        return session

    def _populate_tree(self, entries: tuple[WorkspaceEntry, ...]) -> None:
        self.file_tree.clear()

        def add(
            parent: QTreeWidget | QTreeWidgetItem, nodes: tuple[WorkspaceEntry, ...]
        ) -> None:
            for node in nodes:
                item = QTreeWidgetItem([node.name])
                item.setData(0, Qt.ItemDataRole.UserRole, str(node.relative_path))
                item.setData(0, Qt.ItemDataRole.UserRole + 1, node.is_directory)
                parent.addTopLevelItem(item) if isinstance(
                    parent, QTreeWidget
                ) else parent.addChild(item)
                if node.is_directory:
                    add(item, node.children)

        add(self.file_tree, entries)

    def _open_folder_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Open Markdown Workspace")
        if folder:
            self.open_workspace_at(Path(folder))

    def close_workspace(self) -> bool:
        """Leave workspace context while retaining the currently open document."""
        if self.workspace_session is None or not self._confirm_unsaved_changes():
            return False
        self.workspace_session.close()
        self.workspace_session = None
        self.file_tree.clear()
        self._workspace_dock.hide()
        self._update_window_title()
        return True

    def _open_tree_item(self, item: QTreeWidgetItem, _column: int) -> None:
        if self.workspace_session is None or item.data(0, Qt.ItemDataRole.UserRole + 1):
            return
        try:
            self.open_document_at(
                self.workspace_session.root.path
                / item.data(0, Qt.ItemDataRole.UserRole)
            )
        except DocumentReadError as exc:
            self._show_error("Could not open document", str(exc))

    def _search_workspace_dialog(self) -> None:
        if self.workspace_session is None:
            self._show_error("Workspace search", "Open a workspace first.")
            return
        query, accepted = QInputDialog.getText(self, "Search Workspace", "Text:")
        if not accepted or not query:
            return
        try:
            snapshot = SQLiteWorkspaceIndex(self.workspace_session.root.path).load()
            results = search_workspace(snapshot, query)
        except (OSError, ValueError) as exc:
            self._show_error("Workspace search", f"Rebuild the index first: {exc}")
            return
        if not results:
            QMessageBox.information(self, "Workspace search", "No matches found.")
            return
        result = results[0]
        answer = QMessageBox.question(
            self,
            "Workspace search result",
            (
                f"{result.title} — {result.path}:{result.line}\n"
                f"{result.snippet}\n\nOpen it?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.open_document_at(
                open_workspace_search_result(self.workspace_session.root.path, result)
            )

    def _rebuild_workspace_index(self) -> None:
        if self.workspace_session is None:
            self._show_error("Workspace index", "Open a workspace first.")
            return
        try:
            SQLiteWorkspaceIndex(self.workspace_session.root.path).rebuild()
        except (OSError, ValueError) as exc:
            self._show_error("Workspace index", str(exc))
            return
        QMessageBox.information(self, "Workspace index", "Index rebuilt.")

    def _save_action(self) -> bool:
        if self.document_session is None:
            self._show_error("Could not save document", "Open a Markdown file first.")
            return False
        if self.document_session.document.path is None:
            return self._save_as_dialog()
        try:
            self.save_current_to_disk()
        except (
            DocumentReadError,
            DocumentWriteError,
            ExternalModificationError,
        ) as exc:
            self._show_error("Could not save document", str(exc))
            return False
        return True

    def _save_as_dialog(self) -> bool:
        if self.document_session is None:
            self._show_error("Could not save document", "Open a Markdown file first.")
            return False
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Markdown As",
            "",
            "Markdown files (*.md);;All files (*)",
        )
        if not filename:
            return False
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
                return False
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
            return False
        return True

    def _confirm_unsaved_changes(self) -> bool:
        """Allow a document transition only after Save or explicit Discard."""
        session = self.document_session
        if session is None or not session.dirty:
            return True
        choice = QMessageBox.warning(
            self,
            "Unsaved changes",
            "Save changes before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if choice == QMessageBox.StandardButton.Save:
            return self._save_action()
        return choice == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_unsaved_changes():
            event.accept()
        else:
            event.ignore()

    def _update_window_title(self) -> None:
        session = self.document_session
        if session is None or session.document.path is None:
            title = (
                f"{self.workspace_session.root.path.name} - PDF2MD_OnDemand"
                if self.workspace_session is not None
                else "PDF2MD_OnDemand"
            )
        else:
            marker = "*" if session.dirty else ""
            workspace = (
                f"{self.workspace_session.root.path.name} / "
                if self.workspace_session is not None
                else ""
            )
            title = (
                f"{workspace}{session.document.path.name}{marker} "
                "- PDF2MD_OnDemand"
            )
        self.setWindowTitle(title)

    def _show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    def _confirm_external_link(self, url: str) -> None:
        answer = QMessageBox.question(
            self,
            "Open external link?",
            f"Open this link in your browser?\n\n{url}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl(url))

    def _schedule_preview(self, markdown: str) -> None:
        self._pending_markdown = markdown
        self._preview_timer.start()

    def _render_pending_preview(self) -> None:
        self.preview_view.render_markdown(self._pending_markdown)
