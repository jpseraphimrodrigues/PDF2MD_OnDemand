"""Pure graph selection, neighborhood, and filter queries."""

from dataclasses import dataclass

from pdf2md_ondemand.domain.graph import (
    GraphEdgeKind,
    GraphReferenceStatus,
    KnowledgeGraph,
)


@dataclass(frozen=True, slots=True)
class GraphQuery:
    text: str = ""
    tags: frozenset[str] = frozenset()
    edge_kinds: frozenset[GraphEdgeKind] = frozenset()
    issue_statuses: frozenset[GraphReferenceStatus] = frozenset()
    include_orphans: bool = True
    selected_node: str | None = None
    radius: int | None = None


def query_graph(
    graph: KnowledgeGraph, query: GraphQuery = GraphQuery()
) -> KnowledgeGraph:
    """Return a deterministic induced graph satisfying the query options."""
    nodes_by_id = {node.id: node for node in graph.nodes}
    candidates = set(nodes_by_id)
    needle = query.text.strip().casefold()
    if needle:
        candidates = {
            node_id
            for node_id in candidates
            if needle in nodes_by_id[node_id].title.casefold()
            or needle in node_id.casefold()
        }
    if query.tags:
        wanted = {tag.casefold() for tag in query.tags}
        candidates = {
            node_id
            for node_id in candidates
            if wanted.intersection(tag.casefold() for tag in nodes_by_id[node_id].tags)
        }
    if not query.include_orphans:
        connected = {edge.source for edge in graph.edges} | {
            edge.target for edge in graph.edges
        }
        candidates.intersection_update(connected)

    edges = tuple(
        edge
        for edge in graph.edges
        if edge.source in candidates
        and edge.target in candidates
        and (not query.edge_kinds or edge.kind in query.edge_kinds)
    )
    issues = tuple(
        issue
        for issue in graph.issues
        if issue.source in candidates
        and (not query.issue_statuses or issue.status in query.issue_statuses)
    )

    if query.selected_node is not None:
        if (
            query.selected_node not in nodes_by_id
            or query.selected_node not in candidates
        ):
            candidates = set()
            edges = ()
            issues = ()
        elif query.radius is not None:
            if query.radius < 0:
                raise ValueError("Graph neighborhood radius cannot be negative")
            reached = {query.selected_node}
            frontier = {query.selected_node}
            for _ in range(query.radius):
                frontier = {
                    neighbor
                    for edge in edges
                    for node_id, neighbor in (
                        (edge.source, edge.target),
                        (edge.target, edge.source),
                    )
                    if node_id in frontier and neighbor not in reached
                }
                reached.update(frontier)
            candidates.intersection_update(reached)
            edges = tuple(
                edge
                for edge in edges
                if edge.source in candidates and edge.target in candidates
            )
            issues = tuple(issue for issue in issues if issue.source in candidates)

    return KnowledgeGraph(
        tuple(node for node in graph.nodes if node.id in candidates),
        edges,
        issues,
    )
