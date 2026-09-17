"""Save a document session with external-change protection."""

from pathlib import Path

from pdf2md_ondemand.application.document_session import DocumentSession
from pdf2md_ondemand.ports.document_store import DocumentStore


class DocumentSaveError(Exception):
    """Base class for save workflow failures."""


class UnsavedDocumentError(DocumentSaveError):
    """Raised when Save is requested before the document has a path."""


class ExternalModificationError(DocumentSaveError):
    """Raised instead of silently replacing externally changed content."""


class DestinationExistsError(DocumentSaveError):
    """Raised when Save As targets an existing file without overwrite consent."""


def save_document(session: DocumentSession, store: DocumentStore) -> Path:
    path = session.document.path
    if path is None:
        raise UnsavedDocumentError("Save As is required for a new document")
    if session.version is None:
        raise UnsavedDocumentError("Document has no baseline version; use Save As")
    current = store.version(path)
    if current != session.version:
        raise ExternalModificationError(
            f"Document changed outside the application: {path}"
        )
    try:
        version = store.write_atomic(
            path, session.document, expected_version=session.version, overwrite=True
        )
    except FileExistsError as exc:
        raise ExternalModificationError(
            f"Document changed during save: {path}"
        ) from exc
    session.mark_saved(path, version)
    return path


def save_document_as(
    session: DocumentSession,
    path: Path,
    store: DocumentStore,
    *,
    overwrite: bool = False,
) -> Path:
    current = store.version(path)
    if current is not None and not overwrite:
        raise DestinationExistsError(f"Save As destination already exists: {path}")
    try:
        version = store.write_atomic(
            path,
            session.document,
            expected_version=current,
            overwrite=overwrite,
        )
    except FileExistsError as exc:
        if not overwrite:
            raise DestinationExistsError(
                f"Save As destination already exists: {path}"
            ) from exc
        raise ExternalModificationError(
            f"Save As destination changed during save: {path}"
        ) from exc
    session.mark_saved(path, version)
    return path
