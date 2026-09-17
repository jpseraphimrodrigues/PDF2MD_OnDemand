"""Storage boundary for standalone documents."""

from pathlib import Path
from typing import Protocol

from pdf2md_ondemand.application.document_session import FileSnapshot
from pdf2md_ondemand.domain.document import Document


class DocumentStore(Protocol):
    def read(self, path: Path) -> tuple[Document, FileSnapshot]: ...

    def version(self, path: Path) -> FileSnapshot | None: ...

    def write_atomic(
        self,
        path: Path,
        document: Document,
        *,
        expected_version: FileSnapshot | None,
        overwrite: bool = False,
    ) -> FileSnapshot: ...
