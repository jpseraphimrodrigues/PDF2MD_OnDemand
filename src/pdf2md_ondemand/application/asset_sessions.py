"""Per-document authorization contexts for local Preview assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class AssetSession:
    """A revocable authorization to read raster files under one directory."""

    session_id: str
    root: Path


class AssetSessionRegistry:
    """Manage independent asset roots for currently open Markdown documents."""

    def __init__(self) -> None:
        self._sessions: dict[str, AssetSession] = {}

    def create(self, markdown_parent: Path) -> str:
        root = markdown_parent.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("asset session root must be a directory")
        session_id = uuid4().hex
        self._sessions[session_id] = AssetSession(session_id, root)
        return session_id

    def invalidate(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def get(self, session_id: str) -> AssetSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("unknown or expired asset session")
        return session
