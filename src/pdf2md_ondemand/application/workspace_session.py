"""In-memory lifecycle for a selected Markdown workspace."""

import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdf2md_ondemand.ports.workspace_index import WorkspaceIndex


@dataclass(frozen=True, slots=True)
class WorkspaceEntry:
    """A directory or Markdown file in the workspace tree."""

    name: str
    relative_path: Path
    is_directory: bool
    children: tuple["WorkspaceEntry", ...] = ()


class WorkspaceDiscoveryError(OSError):
    """Workspace root could not be read."""


@dataclass(frozen=True, slots=True)
class MarkdownHeading:
    level: int
    text: str
    anchor: str
    line: int


@dataclass(frozen=True, slots=True)
class MarkdownReference:
    kind: str
    target: str
    label: str | None
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class MarkdownMetadata:
    title: str
    headings: tuple[MarkdownHeading, ...]
    tags: tuple[str, ...]
    references: tuple[MarkdownReference, ...]


@dataclass(frozen=True, slots=True)
class NoteSnapshot:
    relative_path: Path
    source: str
    metadata: MarkdownMetadata


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    source_path: Path
    reference: MarkdownReference
    target_path: Path | None
    status: str
    anchor_status: str | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceSnapshot:
    notes: tuple[NoteSnapshot, ...]
    references: tuple[ResolvedReference, ...]
    backlinks: tuple[tuple[Path, tuple[Path, ...]], ...]


@dataclass(frozen=True, slots=True)
class WorkspaceSearchResult:
    path: Path
    title: str
    line: int
    snippet: str


def search_workspace(
    snapshot: WorkspaceSnapshot, query: str, limit: int = 100
) -> tuple[WorkspaceSearchResult, ...]:
    """Case-insensitive substring search, ordered by portable relative path."""
    needle = query.strip().casefold()
    if not needle or limit <= 0:
        return ()
    results: list[WorkspaceSearchResult] = []
    for note in sorted(
        snapshot.notes, key=lambda item: item.relative_path.as_posix().casefold()
    ):
        for line_number, line in enumerate(note.source.splitlines(), start=1):
            position = line.casefold().find(needle)
            if position < 0:
                continue
            start = max(0, position - 40)
            end = min(len(line), position + len(query) + 60)
            snippet = line[start:end]
            if start:
                snippet = "…" + snippet
            if end < len(line):
                snippet += "…"
            results.append(
                WorkspaceSearchResult(
                    note.relative_path, note.metadata.title, line_number, snippet
                )
            )
            if len(results) >= limit:
                return tuple(results)
    return tuple(results)


def open_workspace_search_result(root: Path, result: WorkspaceSearchResult) -> Path:
    """Return a confined note path suitable for the existing open-document use case."""
    candidate = (Path(root).resolve() / result.path).resolve()
    workspace_root = Path(root).resolve()
    if (
        not candidate.is_relative_to(workspace_root)
        or candidate.suffix.casefold() != ".md"
    ):
        raise ValueError("Search result points outside the Markdown workspace")
    return candidate


def build_workspace_snapshot(root: Path) -> WorkspaceSnapshot:
    """Read and extract every discovered note into an immutable memory snapshot."""
    notes: list[NoteSnapshot] = []
    for entry in _walk_entries(discover_markdown(root)):
        path = Path(root) / entry.relative_path
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        metadata = extract_markdown_metadata(source, path.stem)
        notes.append(NoteSnapshot(entry.relative_path, source, metadata))
    return WorkspaceSnapshot(tuple(notes), (), ())


def resolve_workspace_references(
    snapshot: WorkspaceSnapshot,
) -> WorkspaceSnapshot:
    """Resolve local note links deterministically and derive backlinks."""
    by_path = {
        note.relative_path.as_posix().casefold(): note for note in snapshot.notes
    }
    by_stem: dict[str, list[NoteSnapshot]] = {}
    for note in snapshot.notes:
        by_stem.setdefault(note.relative_path.stem.casefold(), []).append(note)
    resolved: list[ResolvedReference] = []
    backlink_sources: dict[Path, set[Path]] = {}
    for note in snapshot.notes:
        for reference in note.metadata.references:
            raw_target = reference.target.strip()
            is_external = bool(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw_target))
            if is_external or raw_target.startswith("//"):
                resolved.append(
                    ResolvedReference(note.relative_path, reference, None, "external")
                )
                continue
            target_text, separator, fragment = raw_target.partition("#")
            if reference.kind == "wikilink" and not target_text:
                target_text = note.relative_path.as_posix()
            candidate_path = Path(target_text)
            if reference.kind == "wikilink" and candidate_path.suffix == "":
                exact = by_path.get((candidate_path.as_posix() + ".md").casefold())
                candidates = (
                    [exact]
                    if exact
                    else by_stem.get(candidate_path.name.casefold(), [])
                )
            else:
                normalized = (note.relative_path.parent / candidate_path).as_posix()
                candidate = by_path.get(normalized.casefold())
                candidates = [candidate] if candidate else []
            candidates = [
                candidate for candidate in candidates if candidate is not None
            ]
            if len(candidates) > 1:
                resolved.append(
                    ResolvedReference(note.relative_path, reference, None, "ambiguous")
                )
                continue
            if not candidates:
                resolved.append(
                    ResolvedReference(note.relative_path, reference, None, "broken")
                )
                continue
            target = candidates[0]
            anchor_status = None
            if separator:
                anchors = {heading.anchor for heading in target.metadata.headings}
                anchor_status = (
                    "resolved" if fragment.casefold() in anchors else "broken"
                )
            resolved.append(
                ResolvedReference(
                    note.relative_path,
                    reference,
                    target.relative_path,
                    "resolved",
                    anchor_status,
                )
            )
            backlink_sources.setdefault(target.relative_path, set()).add(
                note.relative_path
            )
    backlinks = tuple(
        (path, tuple(sorted(sources, key=lambda item: item.as_posix().casefold())))
        for path, sources in sorted(
            backlink_sources.items(),
            key=lambda pair: pair[0].as_posix().casefold(),
        )
    )
    return WorkspaceSnapshot(snapshot.notes, tuple(resolved), backlinks)


def _walk_entries(
    entries: tuple[WorkspaceEntry, ...],
) -> Iterable[WorkspaceEntry]:
    for entry in entries:
        if entry.is_directory:
            yield from _walk_entries(entry.children)
        else:
            yield entry


_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_TAG = re.compile(r"(?<![\w/])#([\w][\w/-]*)", re.UNICODE)
_WIKILINK = re.compile(r"!?\[\[([^\]]+)\]\]")
_MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")
_INLINE_CODE = re.compile(r"(`+).*?\1")


def extract_markdown_metadata(
    source: str, fallback_title: str = ""
) -> MarkdownMetadata:
    """Extract a stable metadata snapshot without changing Markdown source.

    Frontmatter support is intentionally scalar/list-only and does not attempt
    general YAML parsing, so unknown YAML remains untouched and uninterpreted.
    """
    lines = source.splitlines(keepends=True)
    frontmatter: list[str] = []
    body_start = 0
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() in {"---", "..."}:
                frontmatter = lines[1:index]
                body_start = index + 1
                break

    title: str | None = None
    frontmatter_tags: list[str] = []
    for line in frontmatter:
        match = re.match(r"^\s*(title|tags)\s*:\s*(.*?)\s*$", line)
        if not match:
            continue
        key, value = match.groups()
        if key == "title" and value:
            title = value.strip("\"'")
        elif key == "tags":
            if value.startswith("[") and value.endswith("]"):
                frontmatter_tags.extend(
                    part.strip().strip("\"'")
                    for part in value[1:-1].split(",")
                    if part.strip()
                )
            elif value:
                frontmatter_tags.append(value.strip("\"'"))

    headings: list[MarkdownHeading] = []
    tags: list[str] = list(frontmatter_tags)
    references: list[MarkdownReference] = []
    slug_counts: dict[str, int] = {}
    in_fence = False
    offset = sum(len(line) for line in lines[:body_start])
    h1_title: str | None = None
    for line_number, line in enumerate(lines[body_start:], start=body_start + 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            offset += len(line)
            continue
        if in_fence:
            offset += len(line)
            continue
        heading_match = _HEADING.match(line.rstrip("\r\n"))
        if heading_match:
            level, heading_text = len(heading_match.group(1)), heading_match.group(2)
            plain = re.sub(r"[`*_~]", "", heading_text).strip()
            base = re.sub(r"[^\w-]+", "-", plain.casefold(), flags=re.UNICODE)
            base = base.strip("-")
            count = slug_counts.get(base, 0)
            slug_counts[base] = count + 1
            anchor = base if count == 0 else f"{base}-{count}"
            headings.append(MarkdownHeading(level, plain, anchor, line_number))
            if level == 1 and h1_title is None:
                h1_title = plain
        line_without_code = _INLINE_CODE.sub("", line)
        tags.extend(match.group(1) for match in _TAG.finditer(line_without_code))
        for pattern, kind in ((_WIKILINK, "wikilink"), (_MARKDOWN_LINK, "markdown")):
            for match in pattern.finditer(line_without_code):
                if kind == "wikilink":
                    pieces = match.group(1).split("|", 1)
                    target = pieces[0].strip()
                    label = pieces[1].strip() if len(pieces) == 2 else None
                else:
                    target, label = match.group(2).strip(), match.group(1)
                references.append(
                    MarkdownReference(
                        kind,
                        target,
                        label,
                        offset + match.start(),
                        offset + match.end(),
                    )
                )
        offset += len(line)
    return MarkdownMetadata(
        title or h1_title or fallback_title,
        tuple(headings),
        tuple(dict.fromkeys(tags)),
        tuple(sorted(references, key=lambda ref: ref.start)),
    )


def discover_markdown(
    root: Path, ignored_directories: Iterable[str] = ()
) -> tuple[WorkspaceEntry, ...]:
    """Build a deterministic Markdown tree without following directory symlinks."""
    root = Path(os.path.abspath(Path(root).expanduser()))
    ignored = {".pdf2md", *ignored_directories}
    try:
        if not root.is_dir():
            raise NotADirectoryError(str(root))
        return _scan_directory(root, root, ignored)
    except OSError as exc:
        raise WorkspaceDiscoveryError(str(exc)) from exc


def _scan_directory(
    root: Path, directory: Path, ignored: set[str]
) -> tuple[WorkspaceEntry, ...]:
    entries: list[WorkspaceEntry] = []
    try:
        children = sorted(
            directory.iterdir(),
            key=lambda path: (
                not path.is_dir(),
                path.name.casefold(),
                path.name,
            ),
        )
    except OSError:
        return ()
    for path in children:
        try:
            if path.is_symlink():
                continue
            relative = path.relative_to(root)
            if path.is_dir():
                if path.name in ignored:
                    continue
                entries.append(
                    WorkspaceEntry(
                        path.name, relative, True, _scan_directory(root, path, ignored)
                    )
                )
            elif path.is_file() and path.suffix.casefold() == ".md":
                entries.append(WorkspaceEntry(path.name, relative, False))
        except OSError:
            continue
    return tuple(entries)


@dataclass(frozen=True, slots=True)
class WorkspaceRoot:
    """Lexical identity of a workspace root, independent of filesystem access."""

    path: Path

    def __post_init__(self) -> None:
        path = Path(os.path.abspath(Path(self.path).expanduser()))
        object.__setattr__(self, "path", path)


@dataclass(slots=True)
class WorkspaceSession:
    """Application-level workspace state, intentionally separate from documents."""

    root: WorkspaceRoot
    is_open: bool = True
    _pending_paths: set[Path] | None = None

    @classmethod
    def open(cls, root: Path) -> "WorkspaceSession":
        return cls(WorkspaceRoot(root))

    def close(self) -> None:
        self.is_open = False
        self._pending_paths = None

    def queue_changes(self, paths: Iterable[Path]) -> tuple[Path, ...]:
        """Coalesce watcher events; the caller schedules processing after debounce."""
        if not self.is_open:
            return ()
        if self._pending_paths is None:
            self._pending_paths = set()
        self._pending_paths.update(Path(path) for path in paths)
        return tuple(sorted(self._pending_paths, key=lambda path: path.as_posix()))

    def take_pending_changes(self) -> tuple[Path, ...]:
        if not self.is_open or not self._pending_paths:
            return ()
        pending = tuple(sorted(self._pending_paths, key=lambda path: path.as_posix()))
        self._pending_paths.clear()
        return pending

    def reconcile(self, index: "WorkspaceIndex") -> WorkspaceSnapshot:
        """Run a full scan through a workspace index after event loss or on demand."""
        return index.rebuild()
