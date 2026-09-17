"""The Phase 1 Markdown regression fixture survives an exact file round-trip."""

from __future__ import annotations

from pathlib import Path

from pdf2md_ondemand.adapters.filesystem_document_store import FilesystemDocumentStore
from pdf2md_ondemand.application.open_document import open_document
from pdf2md_ondemand.application.save_document import save_document_as


def test_regression_fixture_round_trips_without_source_normalization(
    tmp_path: Path,
) -> None:
    fixture = (
        Path(__file__).parents[1]
        / "frontend"
        / "test"
        / "fixtures"
        / "phase1-regression.md"
    )
    source_bytes = fixture.read_bytes()
    source_path = tmp_path / "source.md"
    source_path.write_bytes(source_bytes)
    store = FilesystemDocumentStore()
    session = open_document(source_path, store)
    destination = tmp_path / "round-trip.md"

    save_document_as(session, destination, store)

    assert destination.read_bytes() == source_bytes
    assert session.document.content.encode("utf-8") == source_bytes
