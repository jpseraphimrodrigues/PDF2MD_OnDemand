from pathlib import Path

import pytest

from pdf2md_ondemand.adapters.filesystem_document_store import (
    DocumentReadError,
    FilesystemDocumentStore,
)
from pdf2md_ondemand.application.open_document import open_document
from pdf2md_ondemand.application.save_document import (
    DestinationExistsError,
    ExternalModificationError,
    save_document,
    save_document_as,
)


def test_open_edit_save_preserves_exact_source_and_newlines(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    source = "---\r\ntitle: x\r\n---\r\n\n:::custom\r\n  *unknown*\r\n"
    path.write_bytes(b"\xef\xbb\xbf" + source.encode("utf-8"))
    store = FilesystemDocumentStore()

    session = open_document(path, store)
    assert session.document.content == source
    assert session.document.utf8_bom is True
    assert session.dirty is False

    changed = source + "Unicode: caf\u00e9\n"
    session.edit(changed)
    assert session.dirty is True
    save_document(session, store)
    assert path.read_bytes() == b"\xef\xbb\xbf" + changed.encode("utf-8")
    assert session.dirty is False


def test_invalid_utf8_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "invalid.md"
    path.write_bytes(b"\xff")
    with pytest.raises(DocumentReadError):
        open_document(path, FilesystemDocumentStore())


def test_external_change_prevents_save_and_save_as_is_atomic(tmp_path: Path) -> None:
    original = tmp_path / "original.md"
    original.write_text("base", encoding="utf-8")
    target = tmp_path / "copy.md"
    store = FilesystemDocumentStore()
    session = open_document(original, store)
    session.edit("mine")
    original.write_text("outside", encoding="utf-8")

    with pytest.raises(ExternalModificationError):
        save_document(session, store)
    assert original.read_text(encoding="utf-8") == "outside"

    save_document_as(session, target, store)
    assert target.read_text(encoding="utf-8") == "mine"
    assert session.document.path == target
    assert session.dirty is False


def test_save_as_existing_destination_requires_explicit_overwrite(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.md"
    source.write_bytes(b"\xef\xbb\xbfbase\r\n:::unknown\r\n")
    target = tmp_path / "target.md"
    target.write_bytes(b"keep me\r\n")
    store = FilesystemDocumentStore()
    session = open_document(source, store)
    changed = session.document.content + "new\r\n"
    session.edit(changed)

    with pytest.raises(DestinationExistsError):
        save_document_as(session, target, store)
    assert target.read_bytes() == b"keep me\r\n"
    assert session.document.path == source
    assert session.dirty is True

    save_document_as(session, target, store, overwrite=True)
    assert target.read_bytes() == b"\xef\xbb\xbf" + changed.encode("utf-8")
    assert session.document.path == target
    assert session.dirty is False


def test_save_as_detects_destination_created_after_version_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.md"
    source.write_text("base", encoding="utf-8")
    target = tmp_path / "target.md"
    store = FilesystemDocumentStore()
    session = open_document(source, store)
    session.edit("mine")

    original_write = store.write_atomic

    def create_target_then_write(
        path: Path,
        document: object,
        *,
        expected_version: object,
        overwrite: bool = False,
    ) -> object:
        target.write_text("outside", encoding="utf-8")
        return original_write(
            path,
            document,  # type: ignore[arg-type]
            expected_version=expected_version,  # type: ignore[arg-type]
            overwrite=overwrite,
        )

    monkeypatch.setattr(store, "write_atomic", create_target_then_write)
    with pytest.raises(DestinationExistsError):
        save_document_as(session, target, store)
    assert target.read_text(encoding="utf-8") == "outside"


def test_save_detects_version_change_between_check_and_atomic_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "note.md"
    path.write_text("base", encoding="utf-8")
    store = FilesystemDocumentStore()
    session = open_document(path, store)
    session.edit("mine")

    original_write = store.write_atomic

    def modify_then_write(
        target: Path,
        document: object,
        *,
        expected_version: object,
        overwrite: bool = False,
    ) -> object:
        target.write_text("outside", encoding="utf-8")
        return original_write(
            target,
            document,  # type: ignore[arg-type]
            expected_version=expected_version,  # type: ignore[arg-type]
            overwrite=overwrite,
        )

    monkeypatch.setattr(store, "write_atomic", modify_then_write)
    with pytest.raises(ExternalModificationError):
        save_document(session, store)
    assert path.read_text(encoding="utf-8") == "outside"
