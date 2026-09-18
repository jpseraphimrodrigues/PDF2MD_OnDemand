"""Small native Qt 2D renderer for a workspace graph DTO."""

from math import atan2, cos, pi, sin

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QMouseEvent,
    QPainter,
    QPen,
    QPolygonF,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from pdf2md_ondemand.application.query_graph import GraphQuery, query_graph
from pdf2md_ondemand.domain.graph import GraphEdgeKind, KnowledgeGraph


class _NodeItem(QGraphicsEllipseItem):
    def __init__(
        self, node_id: str, title: str, path: str, selected: bool, orphan: bool
    ) -> None:
        super().__init__(-92, -30, 184, 60)
        self.node_id = node_id
        fill = "#bfdbfe" if selected else "#fef3c7" if orphan else "#f1f5f9"
        outline = "#1d4ed8" if selected else "#d97706" if orphan else "#64748b"
        self.setBrush(QBrush(QColor(fill)))
        pen = QPen(QColor(outline), 3 if selected else 2)
        if orphan:
            pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        label = QGraphicsTextItem(title[:32], self)
        label.setTextWidth(168)
        label.setPos(-84, -23)
        label.setDefaultTextColor(QColor("#111827"))
        sublabel = QGraphicsTextItem(
            f"{'Orphan · ' if orphan else ''}{path[-26:]}", self
        )
        sublabel.setTextWidth(168)
        sublabel.setPos(-84, 1)
        sublabel.setDefaultTextColor(QColor("#475569" if not orphan else "#92400e"))
        self.setToolTip(
            f"{title}\n{path}\n{'No resolved links' if orphan else 'Connected note'}"
        )
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)


class GraphCanvas(QGraphicsView):
    nodeActivated = Signal(str)
    nodeSelected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._node_items: dict[str, _NodeItem] = {}
        self._scene.selectionChanged.connect(self._selection_changed)

    def set_graph(
        self,
        graph: KnowledgeGraph,
        selected_node: str | None = None,
        orphan_ids: frozenset[str] = frozenset(),
    ) -> None:
        self._scene.clear()
        self._node_items.clear()
        count = len(graph.nodes)
        positions: dict[str, QPointF] = {}
        radius = max(150.0, 38.0 * count)
        for index, node in enumerate(graph.nodes):
            angle = 2 * pi * index / max(1, count)
            position = QPointF(cos(angle) * radius, sin(angle) * radius)
            positions[node.id] = position
        for edge in graph.edges:
            start, end = positions.get(edge.source), positions.get(edge.target)
            if start is not None and end is not None:
                line = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
                color = (
                    QColor("#2563eb")
                    if edge.kind.value == "wikilink"
                    else QColor("#0f766e")
                )
                edge_label = (
                    "Broken anchor"
                    if edge.anchor_status == "broken"
                    else "Wikilink"
                    if edge.kind == GraphEdgeKind.WIKILINK
                    else "Markdown"
                )
                if edge.label:
                    edge_label += f": {edge.label}"
                if edge.occurrences > 1 and edge.anchor_status != "broken":
                    edge_label += f" ×{edge.occurrences}"
                if edge.anchor_status == "broken":
                    color = QColor("#dc2626")
                pen = QPen(color, 1.5)
                if (
                    edge.kind == GraphEdgeKind.MARKDOWN
                    or edge.anchor_status == "broken"
                ):
                    pen.setStyle(Qt.PenStyle.DashLine)
                line.setPen(pen)
                line.setZValue(-1)
                self._scene.addItem(line)
                angle = atan2(end.y() - start.y(), end.x() - start.x())
                tip = start + (end - start) * 0.72
                size = 8.0
                arrow = QPolygonF(
                    [
                        tip,
                        tip
                        - QPointF(
                            cos(angle - pi / 6) * size,
                            sin(angle - pi / 6) * size,
                        ),
                        tip
                        - QPointF(
                            cos(angle + pi / 6) * size,
                            sin(angle + pi / 6) * size,
                        ),
                    ]
                )
                marker = QGraphicsPolygonItem(arrow)
                marker.setBrush(QBrush(color))
                marker.setPen(QPen(color))
                marker.setZValue(-1)
                self._scene.addItem(marker)
                edge_text = QGraphicsTextItem(edge_label)
                edge_text.setDefaultTextColor(color)
                edge_text.setPos(
                    (start.x() + end.x()) / 2,
                    (start.y() + end.y()) / 2,
                )
                edge_text.setZValue(-1)
                self._scene.addItem(edge_text)
        for node in graph.nodes:
            item = _NodeItem(
                node.id,
                node.title or node.path,
                node.path,
                node.id == selected_node,
                node.id in orphan_ids,
            )
            item.setPos(positions[node.id])
            self._scene.addItem(item)
            self._node_items[node.id] = item
        if selected_node in self._node_items:
            self._node_items[selected_node].setSelected(True)
        if graph.nodes:
            self._scene.setSceneRect(
                self._scene.itemsBoundingRect().adjusted(-80, -80, 80, 80)
            )
        else:
            self._scene.setSceneRect(-200, -120, 400, 240)
            text = self._scene.addText("No Markdown documents in this workspace")
            text.setDefaultTextColor(QColor("#475569"))
            text.setPos(-text.boundingRect().width() / 2, -10)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        item = self.itemAt(event.position().toPoint())
        while item is not None and not isinstance(item, _NodeItem):
            item = item.parentItem()
        if isinstance(item, _NodeItem):
            self.nodeActivated.emit(item.node_id)
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        event.accept()

    def _selection_changed(self) -> None:
        selected = self._scene.selectedItems()
        if selected and isinstance(selected[0], _NodeItem):
            self.nodeSelected.emit(selected[0].node_id)


class GraphView(QWidget):
    nodeActivated = Signal(str)
    nodeSelected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas = GraphCanvas(self)
        self._graph = KnowledgeGraph((), (), ())
        self._current_node: str | None = None
        self.text_filter = QLineEdit(self)
        self.text_filter.setPlaceholderText("Filter title or path")
        self.tag_filter = QLineEdit(self)
        self.tag_filter.setPlaceholderText("Tags (comma separated)")
        self.orphans_filter = QCheckBox("Show orphans", self)
        self.orphans_filter.setChecked(True)
        self.wikilinks_filter = QCheckBox("Wikilinks", self)
        self.wikilinks_filter.setChecked(True)
        self.markdown_filter = QCheckBox("Markdown links", self)
        self.markdown_filter.setChecked(True)
        self.issue_count = QLabel(self)
        self._orphan_ids: frozenset[str] = frozenset()
        controls = QHBoxLayout()
        for widget in (
            self.text_filter,
            self.tag_filter,
            self.orphans_filter,
            self.wikilinks_filter,
            self.markdown_filter,
            self.issue_count,
        ):
            controls.addWidget(widget)
        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self.canvas)
        self.canvas.nodeActivated.connect(self.nodeActivated)
        self.canvas.nodeSelected.connect(self.nodeSelected)
        self.text_filter.textChanged.connect(self._apply_filters)
        self.tag_filter.textChanged.connect(self._apply_filters)
        self.orphans_filter.toggled.connect(self._apply_filters)
        self.wikilinks_filter.toggled.connect(self._apply_filters)
        self.markdown_filter.toggled.connect(self._apply_filters)

    def set_graph(
        self, graph: KnowledgeGraph, selected_node: str | None = None
    ) -> None:
        self._graph = graph
        self._current_node = selected_node
        connected = {edge.source for edge in graph.edges} | {
            edge.target for edge in graph.edges
        }
        self._orphan_ids = frozenset(
            node.id for node in graph.nodes if node.id not in connected
        )
        self.orphans_filter.setText(f"Show orphans ({len(self._orphan_ids)})")
        self._apply_filters()

    def clear_graph(self) -> None:
        self._graph = KnowledgeGraph((), (), ())
        self._current_node = None
        self._apply_filters()

    def select_node(self, node_id: str | None) -> None:
        self._current_node = node_id
        for key, item in self.canvas._node_items.items():
            item.setSelected(key == node_id)

    def _apply_filters(self, *_args: object) -> None:
        tags = frozenset(
            tag.strip() for tag in self.tag_filter.text().split(",") if tag.strip()
        )
        kinds = frozenset(
            kind
            for kind, enabled in (
                (GraphEdgeKind.WIKILINK, self.wikilinks_filter.isChecked()),
                (GraphEdgeKind.MARKDOWN, self.markdown_filter.isChecked()),
            )
            if enabled
        )
        visible = query_graph(
            self._graph,
            GraphQuery(
                text=self.text_filter.text(),
                tags=tags,
                edge_kinds=kinds,
                include_orphans=self.orphans_filter.isChecked(),
            ),
        )
        self.issue_count.setText(f"Broken/ambiguous links: {len(visible.issues)}")
        self.canvas.set_graph(visible, self._current_node, self._orphan_ids)
