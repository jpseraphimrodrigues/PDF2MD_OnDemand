"""Renderer-independent knowledge graph value objects."""

from dataclasses import dataclass
from enum import StrEnum


class GraphEdgeKind(StrEnum):
    WIKILINK = "wikilink"
    MARKDOWN = "markdown"


class GraphReferenceStatus(StrEnum):
    BROKEN = "broken"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class GraphNode:
    """A Markdown document identified by its workspace-relative POSIX path."""

    id: str
    path: str
    title: str
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """A directed internal Markdown reference."""

    source: str
    target: str
    kind: GraphEdgeKind
    label: str | None = None
    anchor_status: str | None = None
    occurrences: int = 1


@dataclass(frozen=True, slots=True)
class GraphReferenceIssue:
    """A broken or ambiguous reference retained for diagnostics."""

    source: str
    target: str
    kind: GraphEdgeKind
    status: GraphReferenceStatus
    label: str | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeGraph:
    """Immutable, serializable graph projection of an indexed workspace."""

    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    issues: tuple[GraphReferenceIssue, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible payload with no renderer-specific state."""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "path": node.path,
                    "title": node.title,
                    "tags": list(node.tags),
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "kind": edge.kind.value,
                    "label": edge.label,
                    "anchor_status": edge.anchor_status,
                    "occurrences": edge.occurrences,
                }
                for edge in self.edges
            ],
            "issues": [
                {
                    "source": issue.source,
                    "target": issue.target,
                    "kind": issue.kind.value,
                    "status": issue.status.value,
                    "label": issue.label,
                }
                for issue in self.issues
            ],
        }

    def backlinks(self, node_id: str) -> tuple[str, ...]:
        return tuple(
            sorted({edge.source for edge in self.edges if edge.target == node_id})
        )
