"""Persistence boundary for derived workspace snapshots."""

from typing import Protocol

from pdf2md_ondemand.application.workspace_session import WorkspaceSnapshot


class WorkspaceIndex(Protocol):
    def rebuild(self) -> WorkspaceSnapshot: ...

    def load(self) -> WorkspaceSnapshot: ...
