import json
from pathlib import Path

from pdf2md_ondemand.application.build_graph import build_knowledge_graph
from pdf2md_ondemand.application.query_graph import GraphQuery, query_graph
from pdf2md_ondemand.application.workspace_session import (
    MarkdownMetadata,
    MarkdownReference,
    NoteSnapshot,
    ResolvedReference,
    WorkspaceSession,
    WorkspaceSnapshot,
)
from pdf2md_ondemand.domain.graph import GraphEdgeKind, GraphReferenceStatus


def _snapshot() -> WorkspaceSnapshot:
    a = NoteSnapshot(
        Path("á space/source.md"), "", MarkdownMetadata("Source", (), ("tag",), ())
    )
    b = NoteSnapshot(Path("target.md"), "", MarkdownMetadata("Target", (), (), ()))
    orphan = NoteSnapshot(Path("orphan.md"), "", MarkdownMetadata("Orphan", (), (), ()))
    links = (
        ResolvedReference(
            a.relative_path,
            MarkdownReference("wikilink", "target", "alias", 0, 1),
            b.relative_path,
            "resolved",
        ),
        ResolvedReference(
            a.relative_path,
            MarkdownReference("markdown", "target.md", None, 2, 3),
            b.relative_path,
            "resolved",
        ),
        ResolvedReference(
            a.relative_path,
            MarkdownReference("markdown", "target.md", None, 10, 11),
            b.relative_path,
            "resolved",
        ),
        ResolvedReference(
            a.relative_path,
            MarkdownReference("wikilink", "missing", None, 4, 5),
            None,
            "broken",
        ),
        ResolvedReference(
            a.relative_path,
            MarkdownReference("wikilink", "ambiguous", None, 6, 7),
            None,
            "ambiguous",
        ),
        ResolvedReference(
            a.relative_path,
            MarkdownReference("markdown", "https://example.test", None, 8, 9),
            None,
            "external",
        ),
    )
    return WorkspaceSnapshot((orphan, b, a), links, ())


def test_graph_projection_is_deterministic_and_keeps_orphans_and_issues() -> None:
    graph = build_knowledge_graph(_snapshot())
    json.dumps(graph.to_dict(), ensure_ascii=False)
    assert graph == build_knowledge_graph(_snapshot())
    assert [node.id for node in graph.nodes] == [
        "orphan.md",
        "target.md",
        "á space/source.md",
    ]
    assert len(graph.edges) == 2
    assert {edge.kind for edge in graph.edges} == {
        GraphEdgeKind.WIKILINK,
        GraphEdgeKind.MARKDOWN,
    }
    markdown_edge = next(
        edge for edge in graph.edges if edge.kind == GraphEdgeKind.MARKDOWN
    )
    assert markdown_edge.occurrences == 2
    assert {issue.status for issue in graph.issues} == {
        GraphReferenceStatus.BROKEN,
        GraphReferenceStatus.AMBIGUOUS,
    }
    assert graph.backlinks("target.md") == ("á space/source.md",)


def test_graph_projection_does_not_mutate_workspace_snapshot() -> None:
    snapshot = _snapshot()
    before = repr(snapshot)
    build_knowledge_graph(snapshot)
    assert repr(snapshot) == before


def test_graph_query_filters_tags_types_and_orphans() -> None:
    graph = build_knowledge_graph(_snapshot())
    filtered = query_graph(
        graph,
        GraphQuery(tags=frozenset({"TAG"}), include_orphans=False),
    )
    assert [node.id for node in filtered.nodes] == ["á space/source.md"]
    assert filtered.edges == ()
    assert len(filtered.issues) == 2


def test_graph_query_selects_undirected_neighborhood_by_radius() -> None:
    graph = build_knowledge_graph(_snapshot())
    one_hop = query_graph(graph, GraphQuery(selected_node="target.md", radius=1))
    assert {node.id for node in one_hop.nodes} == {"target.md", "á space/source.md"}
    assert len(one_hop.edges) == 2
    zero_hop = query_graph(graph, GraphQuery(selected_node="target.md", radius=0))
    assert [node.id for node in zero_hop.nodes] == ["target.md"]
    absent = query_graph(graph, GraphQuery(selected_node="missing.md"))
    assert absent.nodes == ()


def test_graph_query_can_hide_issues_by_type() -> None:
    graph = build_knowledge_graph(_snapshot())
    filtered = query_graph(
        graph,
        GraphQuery(issue_statuses=frozenset({GraphReferenceStatus.BROKEN})),
    )
    assert len(filtered.issues) == 1


def test_workspace_session_projects_published_index_snapshot() -> None:
    class Index:
        def load(self) -> WorkspaceSnapshot:
            return _snapshot()

        def rebuild(self) -> WorkspaceSnapshot:
            return _snapshot()

    session = WorkspaceSession.open(Path("workspace"), Index())
    graph = session.knowledge_graph()
    assert len(graph.nodes) == 3
    session.close()
    try:
        session.knowledge_graph()
    except RuntimeError:
        pass
    else:
        raise AssertionError("closed workspace must not provide a graph")
