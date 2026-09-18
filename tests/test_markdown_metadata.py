from pathlib import Path
from uuid import uuid4

from pdf2md_ondemand.application.workspace_session import (
    build_workspace_snapshot,
    extract_markdown_metadata,
    open_workspace_search_result,
    resolve_workspace_references,
    search_workspace,
)


def test_metadata_precedence_frontmatter_headings_and_tags() -> None:
    source = """---
title: 'Front Ω'
tags: [research, work/notes]
unknown: keep me
---
# Heading One
# Heading One
inline #local
`#not-a-tag` and `[[hidden]]`
```md
[[also-hidden]] #hidden
```
"""
    result = extract_markdown_metadata(source, "basename")
    assert result.title == "Front Ω"
    assert [heading.anchor for heading in result.headings] == [
        "heading-one",
        "heading-one-1",
    ]
    assert result.tags == ("research", "work/notes", "local")
    assert result.references == ()
    assert source.startswith("---\ntitle: 'Front Ω'")


def test_extracts_link_targets_aliases_fragments_and_positions() -> None:
    source = "See [[folder/Note#Part|Alias]] and [label](../a%20b.md#top).\n"
    result = extract_markdown_metadata(source)
    assert [(ref.kind, ref.target, ref.label) for ref in result.references] == [
        ("wikilink", "folder/Note#Part", "Alias"),
        ("markdown", "../a%20b.md#top", "label"),
    ]
    assert [source[ref.start : ref.end] for ref in result.references] == [
        "[[folder/Note#Part|Alias]]",
        "[label](../a%20b.md#top)",
    ]


def test_title_falls_back_to_h1_then_basename() -> None:
    assert extract_markdown_metadata("# Título\n", "file").title == "Título"
    assert extract_markdown_metadata("## Not H1\n", "file").title == "file"


def test_workspace_snapshot_resolves_links_and_derives_backlinks() -> None:
    root = Path("_test-workspace-") / uuid4().hex
    (root / "a").mkdir(parents=True)
    (root / "b").mkdir()
    try:
        (root / "source.md").write_text(
            "[[Target#Part]] [[Missing]] [[Twin]] [[https://example.com]]",
            encoding="utf-8",
        )
        (root / "a" / "Target.md").write_text("# Part", encoding="utf-8")
        (root / "a" / "Twin.md").write_text("# One", encoding="utf-8")
        (root / "b" / "Twin.md").write_text("# Two", encoding="utf-8")
        snapshot = resolve_workspace_references(build_workspace_snapshot(root))
        assert [reference.status for reference in snapshot.references] == [
            "resolved",
            "broken",
            "ambiguous",
            "external",
        ]
        assert snapshot.references[0].anchor_status == "resolved"
        assert snapshot.backlinks == ((Path("a/Target.md"), (Path("source.md"),)),)
    finally:
        import shutil

        shutil.rmtree(root, ignore_errors=True)


def test_workspace_search_is_casefolded_ordered_and_openable() -> None:
    root = Path("_test-workspace-") / uuid4().hex
    root.mkdir(parents=True)
    (root / "z.md").write_text("CAFÉ meets query", encoding="utf-8")
    (root / "a.md").write_text("before Query after", encoding="utf-8")
    try:
        snapshot = build_workspace_snapshot(root)
        results = search_workspace(snapshot, "query")
        assert [result.path for result in results] == [Path("a.md"), Path("z.md")]
        assert results[0].line == 1 and "Query" in results[0].snippet
        assert open_workspace_search_result(root, results[0]) == (
            root / "a.md"
        ).resolve()
        assert search_workspace(snapshot, " ") == ()
    finally:
        import shutil

        shutil.rmtree(root, ignore_errors=True)
