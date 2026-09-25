"""Tests for the semantic Lucide icon catalog."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from pdf2md_ondemand.ui.icons import icon, icon_names


def test_catalog_icons_load_as_valid_qicons() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    names = icon_names()
    assert {"open", "save", "workspace", "graph", "bold"} <= names
    assert all(not icon(name).isNull() for name in names)


def test_unknown_icon_name_is_rejected() -> None:
    try:
        icon("not-a-real-icon")
    except ValueError as exc:
        assert "Unknown application icon" in str(exc)
    else:
        raise AssertionError("unknown icon name was accepted")
