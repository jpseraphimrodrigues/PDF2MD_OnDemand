"""Open a document into an editable session."""

from pathlib import Path

from pdf2md_ondemand.application.document_session import DocumentSession
from pdf2md_ondemand.ports.document_store import DocumentStore


def open_document(path: Path, store: DocumentStore) -> DocumentSession:
    document, snapshot = store.read(path)
    return DocumentSession.opened(document, snapshot)
