"""Path identity and workspace membership rules for UI document tabs."""

from pathlib import Path

from pdf2md_ondemand.application.document_session import DocumentSession, FileSnapshot
from pdf2md_ondemand.domain.document import Document
from pdf2md_ondemand.ui.desktop.document_tabs import DocumentTabs


def _session(path: Path | None, content: str = "") -> DocumentSession:
    return DocumentSession.opened(Document(path, content), None)


def test_add_reuses_resolved_path_and_keeps_independent_untitled_sessions(
    tmp_path: Path,
) -> None:
    source = tmp_path / "note.md"
    source.write_text("note", encoding="utf-8")
    alias = tmp_path / "folder" / ".." / "note.md"
    tabs = DocumentTabs()

    first, created = tabs.add(_session(source, "first"))
    reused, created_again = tabs.add(_session(alias, "duplicate"))
    blank_a, blank_a_created = tabs.add(_session(None))
    blank_b, blank_b_created = tabs.add(_session(None))

    assert created and not created_again
    assert reused is first
    assert blank_a_created and blank_b_created
    assert blank_a.key != blank_b.key
    assert tabs.keys == (first.key, blank_a.key, blank_b.key)


def test_reindex_path_and_workspace_membership_use_resolved_paths(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    inside = workspace / "nested" / "note.md"
    inside.parent.mkdir()
    inside.write_text("note", encoding="utf-8")
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    tabs = DocumentTabs()
    inside_tab, _ = tabs.add(_session(inside))
    outside_tab, _ = tabs.add(_session(outside))
    pathless_tab, _ = tabs.add(_session(None))

    assert tabs.within(workspace) == (inside_tab.key,)
    old_path = inside_tab.session.document.path
    destination = workspace / "renamed.md"
    inside_tab.session.edit("updated")
    inside_tab.session.mark_saved(destination, version=_version())
    tabs.reindex_path(inside_tab.key, old_path)

    assert tabs.find_path(destination) is inside_tab
    assert tabs.find_path(inside) is None
    assert tabs.within(workspace) == (inside_tab.key,)
    assert outside_tab.key in tabs.keys
    assert pathless_tab.key in tabs.keys


def _version():
    return FileSnapshot("saved")
