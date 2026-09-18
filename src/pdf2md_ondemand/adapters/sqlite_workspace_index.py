"""SQLite adapter for disposable and rebuildable workspace snapshots."""

import hashlib
import json
import sqlite3
from pathlib import Path

from pdf2md_ondemand.application.workspace_session import (
    MarkdownHeading,
    MarkdownMetadata,
    MarkdownReference,
    NoteSnapshot,
    ResolvedReference,
    WorkspaceSnapshot,
    build_workspace_snapshot,
    resolve_workspace_references,
)

SCHEMA_VERSION = 1


class SQLiteWorkspaceIndex:
    """Store derived metadata under `.pdf2md/index.sqlite3` and rebuild on demand."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.directory = self.root / ".pdf2md"
        self.database = self.directory / "index.sqlite3"

    def rebuild(self) -> WorkspaceSnapshot:
        snapshot = resolve_workspace_references(build_workspace_snapshot(self.root))
        self._publish(snapshot)
        return snapshot

    def reindex(self, _changed_paths: tuple[Path, ...]) -> WorkspaceSnapshot:
        """Reconcile changed paths via a full deterministic scan and atomic publish."""
        return self.rebuild()

    def _publish(self, snapshot: WorkspaceSnapshot) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS notes (
                    path TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    title TEXT NOT NULL,
                    headings TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    references_json TEXT NOT NULL,
                    source TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS resolved (
                    source_path TEXT NOT NULL,
                    reference_index INTEGER NOT NULL,
                    target_path TEXT,
                    status TEXT NOT NULL,
                    anchor_status TEXT,
                    PRIMARY KEY (source_path, reference_index)
                );
                CREATE TABLE IF NOT EXISTS backlinks (
                    target_path TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    PRIMARY KEY (target_path, source_path)
                );
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            for table in ("notes", "resolved", "backlinks"):
                connection.execute(f"DELETE FROM {table}")
            for note in snapshot.notes:
                connection.execute(
                    "INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        note.relative_path.as_posix(),
                        hashlib.sha256(note.source.encode("utf-8")).hexdigest(),
                        note.metadata.title,
                        json.dumps(
                            [heading.__dict__ if hasattr(heading, "__dict__") else {
                                "level": heading.level,
                                "text": heading.text,
                                "anchor": heading.anchor,
                                "line": heading.line,
                            } for heading in note.metadata.headings],
                            ensure_ascii=False,
                        ),
                        json.dumps(note.metadata.tags, ensure_ascii=False),
                        json.dumps(
                            [
                                {
                                    "kind": ref.kind,
                                    "target": ref.target,
                                    "label": ref.label,
                                    "start": ref.start,
                                    "end": ref.end,
                                }
                                for ref in note.metadata.references
                            ],
                            ensure_ascii=False,
                        ),
                        note.source,
                    ),
                )
            for note in snapshot.notes:
                refs = note.metadata.references
                for index, ref in enumerate(refs):
                    resolved = next(
                        item
                        for item in snapshot.references
                        if (
                            item.source_path == note.relative_path
                            and item.reference == ref
                        )
                    )
                    connection.execute(
                        "INSERT INTO resolved VALUES (?, ?, ?, ?, ?)",
                        (
                            note.relative_path.as_posix(),
                            index,
                            (
                                resolved.target_path.as_posix()
                                if resolved.target_path
                                else None
                            ),
                            resolved.status,
                            resolved.anchor_status,
                        ),
                    )
            for target, sources in snapshot.backlinks:
                connection.executemany(
                    "INSERT INTO backlinks VALUES (?, ?)",
                    [(target.as_posix(), source.as_posix()) for source in sources],
                )
            connection.execute(
                "INSERT OR REPLACE INTO metadata VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            connection.commit()
        finally:
            connection.close()

    def load(self) -> WorkspaceSnapshot:
        connection = sqlite3.connect(self.database)
        try:
            version = connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if version is None or int(version[0]) != SCHEMA_VERSION:
                raise ValueError(
                    "Workspace index schema version is missing or unsupported"
                )
            notes: list[NoteSnapshot] = []
            for row in connection.execute(
                "SELECT path, title, headings, tags, references_json, source "
                "FROM notes ORDER BY path"
            ):
                path, title, headings_json, tags_json, references_json, source = row
                headings = tuple(
                    MarkdownHeading(**item) for item in json.loads(headings_json)
                )
                references = tuple(
                    MarkdownReference(**item) for item in json.loads(references_json)
                )
                notes.append(
                    NoteSnapshot(
                        Path(path),
                        source,
                        MarkdownMetadata(
                            title, headings, tuple(json.loads(tags_json)), references
                        ),
                    )
                )
            reference_rows = connection.execute(
                "SELECT source_path, reference_index, target_path, status, "
                "anchor_status "
                "FROM resolved ORDER BY source_path, reference_index"
            ).fetchall()
            refs_by_source = {
                note.relative_path: note.metadata.references for note in notes
            }
            resolved = tuple(
                ResolvedReference(
                    Path(source),
                    refs_by_source[Path(source)][index],
                    Path(target) if target else None,
                    status,
                    anchor_status,
                )
                for source, index, target, status, anchor_status in reference_rows
            )
            backlinks: dict[Path, list[Path]] = {}
            for target, source in connection.execute(
                "SELECT target_path, source_path FROM backlinks "
                "ORDER BY target_path, source_path"
            ):
                backlinks.setdefault(Path(target), []).append(Path(source))
        finally:
            connection.close()
        return WorkspaceSnapshot(
            tuple(notes),
            resolved,
            tuple(
                (path, tuple(sources))
                for path, sources in sorted(
                    backlinks.items(), key=lambda item: item[0].as_posix().casefold()
                )
            ),
        )
