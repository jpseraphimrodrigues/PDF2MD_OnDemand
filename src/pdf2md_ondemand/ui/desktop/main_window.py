"""Standalone Markdown editor and preview composition."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from PySide6.QtCore import QSettings, QSignalBlocker, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabBar,
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
    create_markdown_file,
    discover_markdown,
    resolve_standalone_markdown_link,
    search_workspace,
)
from pdf2md_ondemand.domain.document import Document
from pdf2md_ondemand.ui.desktop.document_tabs import DocumentTabs
from pdf2md_ondemand.ui.desktop.editor_view import EditorView
from pdf2md_ondemand.ui.desktop.graph_view import GraphView
from pdf2md_ondemand.ui.desktop.preview_view import PreviewView

PREVIEW_DEBOUNCE_MS = 200


class MainWindow(QMainWindow):
    """Tabbed Markdown workspace with a shared Editor/Preview work surface."""

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self._settings = settings or QSettings()
        self._preferred_workspace_visible = self._settings.value(
            "panels/workspaceVisible", True, type=bool
        )
        self._preferred_graph_visible = self._settings.value(
            "panels/graphVisible", True, type=bool
        )
        self._suppress_layout_update = True
        self.setWindowTitle("PDF2MD_OnDemand")
        self.resize(960, 640)
        self.document_store = FilesystemDocumentStore()
        self.document_session: DocumentSession | None = None
        self.document_tabs = DocumentTabs()
        self._active_tab_key: str | None = None
        self.workspace_session: WorkspaceSession | None = None
        self.editor_view = EditorView()
        self.asset_sessions = AssetSessionRegistry()
        self.preview_view = PreviewView(self.asset_sessions)
        self.preview_view.externalLinkRequested.connect(self._confirm_external_link)
        self.preview_view.internalLinkRequested.connect(
            self._open_preview_internal_link
        )
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.editor_view)
        self.splitter.addWidget(self.preview_view)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderHidden(True)
        self.file_tree.itemDoubleClicked.connect(self._open_tree_item)
        self.file_tree.currentItemChanged.connect(self._tree_selection_changed)
        self.workspace_search = QLineEdit()
        self.workspace_search.setPlaceholderText("Search workspace")
        self.workspace_search.setClearButtonEnabled(True)
        self.workspace_search.returnPressed.connect(self._run_workspace_search)
        self.workspace_search_results = QListWidget()
        self.workspace_search_results.itemDoubleClicked.connect(
            self._open_search_result
        )
        self.workspace_sidebar = QWidget()
        sidebar_layout = QVBoxLayout(self.workspace_sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)
        sidebar_layout.addWidget(self.file_tree)
        sidebar_layout.addWidget(self.workspace_search)
        sidebar_layout.addWidget(self.workspace_search_results)
        self._workspace_dock = QDockWidget("Workspace", self)
        self._workspace_dock.setWidget(self.workspace_sidebar)
        self._workspace_dock.setObjectName("workspaceDock")
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._workspace_dock)
        self._workspace_dock.hide()
        self._workspace_dock.visibilityChanged.connect(
            self._workspace_visibility_changed
        )
        self.graph_view = GraphView(self)
        self.graph_view.nodeActivated.connect(self._open_graph_node)
        self.graph_view.nodeSelected.connect(self._select_graph_node)
        self._graph_dock = QDockWidget("Knowledge Graph", self)
        self._graph_dock.setObjectName("knowledgeGraphDock")
        self._graph_dock.setWidget(self.graph_view)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._graph_dock)
        self._graph_dock.hide()
        self._graph_dock.visibilityChanged.connect(self._graph_visibility_changed)
        self.tab_bar = QTabBar(self)
        self.tab_bar.setObjectName("documentTabs")
        self.tab_bar.setDocumentMode(True)
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.currentChanged.connect(self._tab_changed)
        self.tab_bar.tabCloseRequested.connect(self._close_tab_at)
        self.tab_bar.tabMoved.connect(self._tab_moved)
        self.splitter.setHandleWidth(5)
        central = QWidget(self)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.tab_bar)
        central_layout.addWidget(self.splitter, 1)
        self.setCentralWidget(central)

        self._pending_markdown = ""
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(PREVIEW_DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._render_pending_preview)
        self.editor_view.bridge.documentContentChanged.connect(
            self._document_content_changed
        )
        self._create_file_actions()
        self._create_format_toolbar()
        self._restore_layout()
        self._update_window_title()

    def open_document_at(self, path: Path) -> DocumentSession | None:
        """Open a new tab, or activate the existing tab for the resolved path."""
        existing = self.document_tabs.find_path(path)
        if existing is not None:
            self._activate_document_tab(existing.key)
            return existing.session
        session = open_document(path, self.document_store)
        tab, _created = self.document_tabs.add(session)
        self._insert_tab(tab.key)
        self._activate_document_tab(tab.key)
        return session

    def new_document_tab(self) -> DocumentSession:
        """Create a blank pathless document that can later be saved with Save As."""
        session = DocumentSession.opened(Document(None, ""), None)
        tab, _created = self.document_tabs.add(session)
        self._insert_tab(tab.key)
        self._activate_document_tab(tab.key)
        return session

    def save_current_to_disk(self) -> Path:
        """Save the current Editor text using the session's version token."""
        session = self._require_session()
        previous_path = session.document.path
        session.edit(self.editor_view.bridge.getContent())
        path = save_document(session, self.document_store)
        if self._active_tab_key is not None:
            self.document_tabs.reindex_path(self._active_tab_key, previous_path)
            self._update_tab_label(self._active_tab_key)
        self._update_window_title()
        self._refresh_graph_after_save(path)
        return path

    def save_as_to(self, path: Path, *, overwrite: bool = False) -> Path:
        """Save the current Editor text to a chosen destination."""
        session = self._require_session()
        key = self._active_tab_key
        if key is None:
            raise UnsavedDocumentError("Open a Markdown document first")
        if self.document_tabs.destination_is_open(key, path):
            raise DestinationExistsError(f"A tab for this path is already open: {path}")
        previous_path = session.document.path
        session.edit(self.editor_view.bridge.getContent())
        return self._save_session_as(session, key, previous_path, path, overwrite)

    def _save_session_as(
        self,
        session: DocumentSession,
        key: str | None,
        previous_path: Path | None,
        path: Path,
        overwrite: bool,
    ) -> Path:
        if key is not None and self.document_tabs.destination_is_open(key, path):
            raise DestinationExistsError(f"A tab for this path is already open: {path}")
        saved_path = save_document_as(
            session, path, self.document_store, overwrite=overwrite
        )
        if key is not None:
            self.document_tabs.reindex_path(key, previous_path)
            self._update_tab_label(key)
        if key == self._active_tab_key:
            self.preview_view.set_asset_root(saved_path.parent)
        self._update_window_title()
        self._refresh_graph_after_save(saved_path)
        return saved_path

    def _require_session(self) -> DocumentSession:
        if self.document_session is None:
            raise UnsavedDocumentError("Open a Markdown document first")
        return self.document_session

    def _document_content_changed(self, key: str, markdown: str) -> None:
        if key not in self.document_tabs.keys:
            return
        session = self.document_tabs.get(key).session
        session.edit(markdown)
        self._update_tab_label(key)
        if key == self._active_tab_key:
            self._schedule_preview(markdown)
            self._update_window_title()

    def _insert_tab(self, key: str) -> None:
        self.document_tabs.get(key)
        index = self.tab_bar.addTab("")
        self.tab_bar.setTabData(index, key)
        self._update_tab_label(key)

    def _activate_document_tab(self, key: str) -> None:
        index = self._tab_index(key)
        if index < 0:
            return
        if self.tab_bar.currentIndex() == index:
            self._tab_changed(index)
        else:
            self.tab_bar.setCurrentIndex(index)

    def _tab_index(self, key: str | None) -> int:
        if key is None:
            return -1
        return next(
            (
                index
                for index in range(self.tab_bar.count())
                if self.tab_bar.tabData(index) == key
            ),
            -1,
        )

    def _tab_changed(self, index: int) -> None:
        if index < 0 or index >= self.tab_bar.count():
            old_key = self._active_tab_key
            self._active_tab_key = None
            self.document_session = None
            if old_key is not None:
                self.editor_view.bridge.closeDocumentState(old_key)
            self.preview_view.set_asset_root(None)
            self._schedule_preview("")
            self.graph_view.select_node(None)
            self._update_window_title()
            return
        key = self.tab_bar.tabData(index)
        if not isinstance(key, str):
            return
        tab = self.document_tabs.get(key)
        self._active_tab_key = key
        self.document_session = tab.session
        self.editor_view.bridge.switchDocument(key, tab.session.document.content)
        path = tab.session.document.path
        self.preview_view.set_asset_root(path.parent if path is not None else None)
        self._schedule_preview(tab.session.document.content)
        self._sync_graph_selection()
        self._update_window_title()

    def _tab_moved(self, source: int, destination: int) -> None:
        self.document_tabs.move(source, destination)

    def _update_tab_label(self, key: str | None) -> None:
        index = self._tab_index(key)
        if index < 0 or key is None:
            return
        session = self.document_tabs.get(key).session
        path = session.document.path
        label = path.name if path is not None else "Untitled"
        if session.dirty:
            label += " •"
        self.tab_bar.setTabText(index, label)
        self.tab_bar.setTabToolTip(
            index, str(path) if path is not None else "Unsaved note"
        )

    def _close_tab_at(self, index: int) -> None:
        if index < 0 or index >= self.tab_bar.count():
            return
        key = self.tab_bar.tabData(index)
        if isinstance(key, str):
            self._close_tabs((key,))

    def _close_tabs(self, keys: tuple[str, ...]) -> bool:
        keys = tuple(key for key in keys if key in self.document_tabs.keys)
        if not keys or not self._resolve_dirty_tabs(keys):
            return not keys
        self._remove_tabs_without_prompt(keys)
        return True

    def _remove_tabs_without_prompt(self, keys: tuple[str, ...]) -> None:
        keys = tuple(key for key in keys if key in self.document_tabs.keys)
        if not keys:
            return
        old_order = self.document_tabs.keys
        old_active = self._active_tab_key
        if old_active in keys:
            old_index = old_order.index(old_active)
        else:
            old_index = -1
        blocker = QSignalBlocker(self.tab_bar)
        indices = sorted((self._tab_index(key) for key in keys), reverse=True)
        for index in indices:
            self.tab_bar.removeTab(index)
        removed = self.document_tabs.remove_many(keys)
        del blocker
        remaining = self.document_tabs.keys
        next_key = old_active if old_active in remaining else None
        if next_key is None and remaining:
            next_key = remaining[min(max(old_index, 0), len(remaining) - 1)]
        for tab in removed:
            self.editor_view.bridge.closeDocumentState(tab.key)
        if next_key is None:
            self._tab_changed(-1)
        else:
            self._activate_document_tab(next_key)

    def _resolve_dirty_tabs(self, keys: tuple[str, ...]) -> bool:
        decisions: list[tuple[DocumentSession, QMessageBox.StandardButton]] = []
        for key in keys:
            session = self.document_tabs.get(key).session
            if not session.dirty:
                continue
            answer = QMessageBox.warning(
                self,
                "Unsaved changes",
                (
                    f"Save changes to {session.document.path or 'Untitled'} "
                    "before closing?"
                ),
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                return False
            decisions.append((session, answer))
        for session, answer in decisions:
            if answer == QMessageBox.StandardButton.Save and not self._save_session(
                session
            ):
                return False
        return True

    def _save_session(self, session: DocumentSession) -> bool:
        key = self.document_tabs.key_for_session(session)
        if key == self._active_tab_key:
            session.edit(self.editor_view.bridge.getContent())
        if session.document.path is None:
            return self._save_as_dialog(session)
        try:
            path = save_document(session, self.document_store)
        except (
            DocumentReadError,
            DocumentWriteError,
            ExternalModificationError,
        ) as exc:
            self._show_error("Could not save document", str(exc))
            return False
        self._update_tab_label(key)
        self._update_window_title()
        self._refresh_graph_after_save(path)
        return True

    def _create_file_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        self.new_tab_action = QAction("New Tab", self)
        self.new_tab_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_tab_action.triggered.connect(self.new_document_tab)
        file_menu.addAction(self.new_tab_action)
        self.new_note_action = QAction("New Markdown File…", self)
        self.new_note_action.triggered.connect(self._new_markdown_file)
        file_menu.addAction(self.new_note_action)
        self.close_note_action = QAction("Close Tab", self)
        self.close_note_action.triggered.connect(self.close_note)
        file_menu.addAction(self.close_note_action)
        file_menu.addSeparator()
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
        self.rebuild_workspace_index_action.triggered.connect(
            self._rebuild_workspace_index
        )
        file_menu.addAction(self.rebuild_workspace_index_action)
        self.show_graph_action = QAction("Knowledge Graph", self)
        self.show_graph_action.setCheckable(True)
        self.show_graph_action.toggled.connect(self._toggle_graph)
        file_menu.addAction(self.show_graph_action)

        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self._save_action)
        file_menu.addAction(self.save_action)

        self.save_as_action = QAction("Save &As…", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self._save_as_dialog)
        file_menu.addAction(self.save_as_action)

        view_menu = self.menuBar().addMenu("&View")
        self.show_preview_action = QAction("Show Preview", self)
        self.show_preview_action.setCheckable(True)
        self.show_preview_action.setChecked(True)
        self.show_preview_action.toggled.connect(self.preview_view.setVisible)
        view_menu.addAction(self.show_preview_action)
        view_menu.addAction(self._workspace_dock.toggleViewAction())
        view_menu.addAction(self._graph_dock.toggleViewAction())

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
        previous_workspace = self.workspace_session
        previous_root = previous_workspace.root.path if previous_workspace else None
        if previous_root is not None and previous_root.resolve() == root.resolve():
            assert previous_workspace is not None
            previous_workspace.reconcile()
            self._populate_tree(entries)
            self._refresh_graph()
            return previous_workspace
        closing_keys = (
            self.document_tabs.within(previous_root)
            if previous_root is not None
            else ()
        )
        if closing_keys and not self._resolve_dirty_tabs(closing_keys):
            return None
        try:
            session = WorkspaceSession.open(
                root, index=SQLiteWorkspaceIndex(Path(root))
            )
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            self._show_error("Could not open workspace", str(exc))
            return None
        if previous_workspace is not None:
            previous_workspace.close()
        closing_keys = (
            self.document_tabs.within(previous_root)
            if previous_root is not None
            else ()
        )
        if closing_keys:
            self._remove_tabs_without_prompt(closing_keys)
        self.workspace_session = session
        self._populate_tree(entries)
        self.graph_view.clear_graph()
        self._workspace_dock.setVisible(bool(self._preferred_workspace_visible))
        self._graph_dock.setVisible(bool(self._preferred_graph_visible))
        self.show_graph_action.setChecked(bool(self._preferred_graph_visible))
        self._refresh_graph(rebuild=True)
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
        """Close workspace-owned tabs and context after resolving dirty sessions."""
        if self.workspace_session is None:
            return False
        closing_keys = self.document_tabs.within(self.workspace_session.root.path)
        if closing_keys and not self._resolve_dirty_tabs(closing_keys):
            return False
        closing_keys = self.document_tabs.within(self.workspace_session.root.path)
        self._remove_tabs_without_prompt(closing_keys)
        self.workspace_session.close()
        self.workspace_session = None
        self.file_tree.clear()
        self._suppress_layout_update = True
        self._workspace_dock.hide()
        self._graph_dock.hide()
        self._suppress_layout_update = False
        self.graph_view.clear_graph()
        self.show_graph_action.setChecked(False)
        self.workspace_search.clear()
        self.workspace_search_results.clear()
        self._update_window_title()
        return True

    def _new_markdown_file(self) -> None:
        if self.workspace_session is None:
            self._show_error("New Markdown File", "Open a workspace first.")
            return
        filename, accepted = QInputDialog.getText(
            self, "New Markdown File", "Filename:"
        )
        if not accepted or not filename.strip():
            return
        try:
            path = create_markdown_file(self.workspace_session.root.path, filename)
            self.workspace_session.reconcile()
            self._populate_tree(discover_markdown(self.workspace_session.root.path))
            self._refresh_graph()
            self.open_document_at(path)
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            self._show_error("Could not create Markdown file", str(exc))

    def close_note(self) -> bool:
        """Close the active tab after resolving its unsaved content."""
        if self._active_tab_key is None:
            return False
        return self._close_tabs((self._active_tab_key,))

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
        self._workspace_dock.show()
        self.workspace_search.setFocus()

    def _run_workspace_search(self) -> None:
        if self.workspace_session is None:
            return
        query = self.workspace_search.text().strip()
        self.workspace_search_results.clear()
        if not query:
            return
        try:
            snapshot = SQLiteWorkspaceIndex(self.workspace_session.root.path).load()
            results = search_workspace(snapshot, query)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self._show_error("Workspace search", f"Rebuild the index first: {exc}")
            return
        for result in results:
            item = QListWidgetItem(
                f"{result.title} · {result.path}:{result.line}\n{result.snippet}"
            )
            item.setData(Qt.ItemDataRole.UserRole, result.path)
            item.setToolTip(f"{result.path}:{result.line}")
            self.workspace_search_results.addItem(item)

    def _open_search_result(self, item: QListWidgetItem) -> None:
        if self.workspace_session is None:
            return
        relative = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(relative, str):
            return
        try:
            self.open_document_at(self.workspace_session.root.path / relative)
        except DocumentReadError as exc:
            self._show_error("Could not open search result", str(exc))

    def _toggle_graph(self, visible: bool) -> None:
        if visible and self.workspace_session is None:
            self.show_graph_action.setChecked(False)
            self._show_error("Knowledge Graph", "Open a workspace first.")
            return
        self._graph_dock.setVisible(visible)

    def _refresh_graph(self, *, rebuild: bool = False) -> None:
        session = self.workspace_session
        if session is None:
            return
        try:
            if rebuild:
                session.reconcile()
            graph = session.knowledge_graph()
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            self._show_error(
                "Knowledge Graph", f"Could not refresh workspace graph: {exc}"
            )
            return
        self.graph_view.set_graph(graph, self._current_workspace_node_id())

    def _refresh_graph_after_save(self, path: Path) -> None:
        if self.workspace_session is None:
            return
        try:
            path.resolve().relative_to(self.workspace_session.root.path.resolve())
        except ValueError:
            self._sync_graph_selection()
            return
        self._refresh_graph(rebuild=True)

    def _current_workspace_node_id(self) -> str | None:
        if self.workspace_session is None or self.document_session is None:
            return None
        path = self.document_session.document.path
        if path is None:
            return None
        try:
            return (
                path.resolve()
                .relative_to(self.workspace_session.root.path.resolve())
                .as_posix()
            )
        except ValueError:
            return None

    def _sync_graph_selection(self) -> None:
        self.graph_view.select_node(self._current_workspace_node_id())

    def _select_graph_node(self, node_id: str) -> None:
        for item in self.file_tree.findItems(
            "", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive
        ):
            if item.data(0, Qt.ItemDataRole.UserRole) == node_id:
                self.file_tree.setCurrentItem(item)
                break

    def _tree_selection_changed(
        self, item: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        if item is not None and not item.data(0, Qt.ItemDataRole.UserRole + 1):
            self.graph_view.select_node(item.data(0, Qt.ItemDataRole.UserRole))

    def _open_graph_node(self, node_id: str) -> None:
        if self.workspace_session is None:
            return
        try:
            self.open_document_at(self.workspace_session.root.path / node_id)
        except DocumentReadError as exc:
            self._show_error("Could not open document", str(exc))

    def _rebuild_workspace_index(self) -> None:
        if self.workspace_session is None:
            self._show_error("Workspace index", "Open a workspace first.")
            return
        try:
            self.workspace_session.reconcile()
            entries = discover_markdown(self.workspace_session.root.path)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self._show_error("Workspace index", str(exc))
            return
        self._populate_tree(entries)
        self._refresh_graph()
        note_count = sum(1 for _item in self._workspace_paths(entries))
        QMessageBox.information(
            self,
            "Workspace index",
            f"Workspace index rebuilt. {note_count} Markdown files indexed.",
        )

    def _workspace_paths(self, entries: tuple[WorkspaceEntry, ...]) -> Iterator[Path]:
        for entry in entries:
            if entry.is_directory:
                yield from self._workspace_paths(entry.children)
            else:
                yield entry.relative_path

    def _save_action(self) -> bool:
        session = self.document_session
        if session is None:
            self._show_error("Could not save document", "Open a Markdown file first.")
            return False
        return self._save_session(session)

    def _save_as_dialog(self, session: DocumentSession | None = None) -> bool:
        session = session or self.document_session
        if session is None:
            self._show_error("Could not save document", "Open a Markdown file first.")
            return False
        key = self.document_tabs.key_for_session(session)
        if key == self._active_tab_key:
            session.edit(self.editor_view.bridge.getContent())
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
            self._save_session_as(session, key, session.document.path, path, overwrite)
        except (
            DestinationExistsError,
            DocumentReadError,
            DocumentWriteError,
            ExternalModificationError,
        ) as exc:
            self._show_error("Could not save document", str(exc))
            return False
        return True

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._resolve_dirty_tabs(self.document_tabs.keys):
            self._save_layout()
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
            title = f"{workspace}{session.document.path.name}{marker} - PDF2MD_OnDemand"
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

    def _open_preview_internal_link(self, target: str, kind: str) -> None:
        if self.document_session is None or self.document_session.document.path is None:
            self._show_error(
                "Internal link", "Save the current note before following links."
            )
            return
        source_path = self.document_session.document.path.resolve()
        destination: Path | None = None
        if self.workspace_session is not None:
            root = self.workspace_session.root.path.resolve()
            try:
                source_relative = source_path.relative_to(root)
            except ValueError:
                source_relative = None
            if source_relative is not None:
                try:
                    reference = self.workspace_session.resolve_link(
                        source_relative, target, kind
                    )
                    if (
                        reference.status == "resolved"
                        and reference.target_path is not None
                    ):
                        candidate = (root / reference.target_path).resolve()
                        if (
                            candidate.is_relative_to(root)
                            and candidate.suffix.casefold() == ".md"
                        ):
                            destination = candidate
                    elif reference.status == "ambiguous":
                        self._show_error(
                            "Internal link", f"Link target is ambiguous: {target}"
                        )
                        return
                except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                    self._show_error("Internal link", str(exc))
                    return
            else:
                try:
                    destination = resolve_standalone_markdown_link(
                        source_path, target, kind
                    )
                except (OSError, ValueError) as exc:
                    self._show_error("Internal link", str(exc))
                    return
        else:
            try:
                destination = resolve_standalone_markdown_link(
                    source_path, target, kind
                )
            except (OSError, ValueError) as exc:
                self._show_error("Internal link", str(exc))
                return
        if destination is None:
            self._show_error("Internal link", f"Markdown target not found: {target}")
            return
        try:
            self.open_document_at(destination)
        except DocumentReadError as exc:
            self._show_error("Could not open linked note", str(exc))

    def _schedule_preview(self, markdown: str) -> None:
        self._pending_markdown = markdown
        self._preview_timer.start()

    def _render_pending_preview(self) -> None:
        self.preview_view.render_markdown(self._pending_markdown)

    def _restore_layout(self) -> None:
        geometry = self._settings.value("window/geometry")
        state = self._settings.value("window/state")
        if geometry is not None:
            self.restoreGeometry(geometry)
            self.resize(self.size().expandedTo(self.minimumSizeHint()))
        saved_size = self._settings.value("window/size")
        if saved_size is not None:
            self.resize(saved_size)
        if state is not None:
            self.restoreState(state)
        sizes = self._settings.value("window/editorPreviewSplitter")
        if isinstance(sizes, list) and len(sizes) == 2:
            self.splitter.setSizes([int(sizes[0]), int(sizes[1])])
        preview_visible = self._settings.value("panels/previewVisible", True, type=bool)
        blocker = QSignalBlocker(self.show_preview_action)
        self.show_preview_action.setChecked(bool(preview_visible))
        self.preview_view.setVisible(bool(preview_visible))
        del blocker
        if self.workspace_session is None:
            self._workspace_dock.hide()
            self._graph_dock.hide()
        self._suppress_layout_update = False

    def _save_layout(self) -> None:
        if self.size().width() > 0 and self.size().height() > 0:
            self._settings.setValue("window/size", self.size())
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/state", self.saveState())
        self._settings.setValue("window/editorPreviewSplitter", self.splitter.sizes())
        self._settings.setValue(
            "panels/workspaceVisible", self._preferred_workspace_visible
        )
        self._settings.setValue("panels/graphVisible", self._preferred_graph_visible)
        self._settings.setValue(
            "panels/previewVisible", self.show_preview_action.isChecked()
        )
        self._settings.sync()

    def _workspace_visibility_changed(self, visible: bool) -> None:
        if not self._suppress_layout_update and self.workspace_session is not None:
            self._preferred_workspace_visible = visible

    def _graph_visibility_changed(self, visible: bool) -> None:
        if not self._suppress_layout_update and self.workspace_session is not None:
            self._preferred_graph_visible = visible
            blocker = QSignalBlocker(self.show_graph_action)
            self.show_graph_action.setChecked(visible)
            del blocker
