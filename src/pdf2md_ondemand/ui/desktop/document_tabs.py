"""UI-level registry for open document sessions and their tab identities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from pdf2md_ondemand.application.document_session import DocumentSession


@dataclass(frozen=True, slots=True)
class DocumentTab:
    """One open document session with a stable, page-local editor key."""

    key: str
    session: DocumentSession


class DocumentTabs:
    """Keep open sessions ordered and prevent duplicate canonical file tabs."""

    def __init__(self) -> None:
        self._tabs: dict[str, DocumentTab] = {}
        self._order: list[str] = []
        self._paths: dict[str, str] = {}

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(self._order)

    def add(self, session: DocumentSession) -> tuple[DocumentTab, bool]:
        """Return the existing tab for a path, or register a new session."""
        path_key = self._path_key(session.document.path)
        if path_key is not None and path_key in self._paths:
            return self._tabs[self._paths[path_key]], False
        tab = DocumentTab(uuid4().hex, session)
        self._tabs[tab.key] = tab
        self._order.append(tab.key)
        if path_key is not None:
            self._paths[path_key] = tab.key
        return tab, True

    def get(self, key: str) -> DocumentTab:
        return self._tabs[key]

    def key_for_session(self, session: DocumentSession) -> str | None:
        return next(
            (key for key in self._order if self._tabs[key].session is session), None
        )

    def move(self, source: int, destination: int) -> None:
        if not (0 <= source < len(self._order) and 0 <= destination < len(self._order)):
            return
        key = self._order.pop(source)
        self._order.insert(destination, key)

    def find_path(self, path: Path) -> DocumentTab | None:
        key = self._paths.get(self._path_key(path) or "")
        return self._tabs[key] if key is not None else None

    def remove(self, key: str) -> DocumentTab:
        tab = self._tabs.pop(key)
        self._order.remove(key)
        path_key = self._path_key(tab.session.document.path)
        if path_key is not None:
            self._paths.pop(path_key, None)
        return tab

    def remove_many(self, keys: tuple[str, ...]) -> tuple[DocumentTab, ...]:
        return tuple(self.remove(key) for key in keys if key in self._tabs)

    def reindex_path(self, key: str, previous_path: Path | None) -> None:
        """Update path identity after Save As without changing editor identity."""
        old_key = self._path_key(previous_path)
        if old_key is not None and self._paths.get(old_key) == key:
            self._paths.pop(old_key)
        new_key = self._path_key(self._tabs[key].session.document.path)
        if new_key is not None:
            existing = self._paths.get(new_key)
            if existing is not None and existing != key:
                raise ValueError("A tab for the destination path is already open")
            self._paths[new_key] = key

    def destination_is_open(self, key: str, path: Path) -> bool:
        """Whether another open tab already owns a Save As destination."""
        owner = self._paths.get(self._path_key(path) or "")
        return owner is not None and owner != key

    def within(self, root: Path) -> tuple[str, ...]:
        """Return tabs whose resolved document paths are inside a root."""
        resolved_root = root.resolve()
        result: list[str] = []
        for key in self._order:
            path = self._tabs[key].session.document.path
            if path is None:
                continue
            try:
                path.resolve().relative_to(resolved_root)
            except ValueError:
                continue
            result.append(key)
        return tuple(result)

    @staticmethod
    def _path_key(path: Path | None) -> str | None:
        if path is None:
            return None
        return os.path.normcase(str(path.resolve()))
