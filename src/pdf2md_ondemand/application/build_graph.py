"""Project the workspace's resolved Markdown references into a graph DTO."""

import posixpath
from collections import Counter
from pathlib import Path

from pdf2md_ondemand.application.workspace_session import WorkspaceSnapshot
from pdf2md_ondemand.domain.graph import (
    GraphEdge,
    GraphEdgeKind,
    GraphNode,
    GraphReferenceIssue,
    GraphReferenceStatus,
    KnowledgeGraph,
)


def build_knowledge_graph(snapshot: WorkspaceSnapshot) -> KnowledgeGraph:
    """Build a deterministic graph without reading files or parsing Markdown."""
    nodes = tuple(
        sorted(
            (
                GraphNode(
                    _relative_id(note.relative_path),
                    _relative_id(note.relative_path),
                    note.metadata.title,
                    note.metadata.tags,
                )
                for note in snapshot.notes
            ),
            key=lambda node: (node.id.casefold(), node.id),
        )
    )
    node_ids = {node.id for node in nodes}
    edge_counts: Counter[tuple[str, str, GraphEdgeKind, str | None, str | None]] = (
        Counter()
    )
    issues: set[GraphReferenceIssue] = set()
    for reference in snapshot.references:
        source = _relative_id(reference.source_path)
        kind = GraphEdgeKind(reference.reference.kind)
        if reference.status == "resolved" and reference.target_path is not None:
            target = _relative_id(reference.target_path)
            if source in node_ids and target in node_ids:
                edge_counts[
                    (
                        source,
                        target,
                        kind,
                        reference.reference.label,
                        reference.anchor_status,
                    )
                ] += 1
        elif reference.status in {"broken", "ambiguous"} and source in node_ids:
            issues.add(
                GraphReferenceIssue(
                    source,
                    reference.reference.target,
                    kind,
                    GraphReferenceStatus(reference.status),
                    reference.reference.label,
                )
            )
    return KnowledgeGraph(
        nodes,
        tuple(
            GraphEdge(*key, occurrences=count)
            for key, count in sorted(
                edge_counts.items(),
                key=lambda item: (item[0][0], item[0][1], item[0][2], item[0][3] or ""),
            )
        ),
        tuple(
            sorted(issues, key=lambda issue: (issue.source, issue.target, issue.status))
        ),
    )


def _relative_id(path: Path) -> str:
    if path.is_absolute():
        raise ValueError("Graph node paths must be workspace relative")
    normalized = posixpath.normpath(path.as_posix())
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError("Graph node paths cannot escape the workspace")
    return normalized
