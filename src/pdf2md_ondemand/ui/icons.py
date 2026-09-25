"""Application icon catalog backed by the bundled Lucide SVG assets."""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_ICON_NAMES = {
    "new": "file-plus",
    "open": "file-search",
    "open_folder": "folder-open",
    "save": "save",
    "save_as": "save-plus",
    "close": "x",
    "search": "search",
    "refresh": "refresh-cw",
    "settings": "settings-2",
    "editor": "file-pen-line",
    "preview": "eye",
    "split": "columns-2",
    "workspace": "folder-tree",
    "graph": "network",
    "file": "file-text",
    "folder": "folder",
    "bold": "bold",
    "italic": "italic",
    "heading": "heading",
    "link": "link",
    "code": "code",
    "strikethrough": "strikethrough",
    "bullet_list": "list",
    "ordered_list": "list-ordered",
    "quote": "quote",
    "horizontal_rule": "minus",
    "image": "image",
    "table": "table-2",
    "math": "sigma",
    "mermaid": "workflow",
}


def icon(name: str) -> QIcon:
    """Return a raster-backed icon from the bundled Lucide catalog.

    Rasterizing the SVG while loading keeps the resource context short-lived and
    avoids QIcon retaining a path into an ``importlib.resources`` temporary file.
    """
    try:
        filename = _ICON_NAMES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown application icon: {name}") from exc
    resource = files("pdf2md_ondemand.ui.lucide").joinpath(f"{filename}.svg")
    data = QByteArray(resource.read_bytes())
    renderer = QSvgRenderer(data)
    if not renderer.isValid():
        raise RuntimeError(f"Could not load Lucide icon: {filename}.svg")
    pixmap = QPixmap(QSize(24, 24))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def icon_names() -> frozenset[str]:
    """Return the semantic names exposed by the application catalog."""
    return frozenset(_ICON_NAMES)
