"""Editing state independent of any GUI toolkit."""

from dataclasses import dataclass
from pathlib import Path

from pdf2md_ondemand.domain.document import Document


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    """Opaque optimistic concurrency token for one observed file version."""

    sha256: str


@dataclass(slots=True)
class DocumentSession:
    document: Document
    baseline_content: str
    version: FileSnapshot | None

    @classmethod
    def opened(
        cls, document: Document, version: FileSnapshot | None
    ) -> "DocumentSession":
        return cls(document, document.content, version)

    @property
    def dirty(self) -> bool:
        return self.document.content != self.baseline_content

    def edit(self, content: str) -> None:
        self.document = Document(self.document.path, content, self.document.utf8_bom)

    def mark_saved(self, path: Path, version: FileSnapshot) -> None:
        self.document = Document(path, self.document.content, self.document.utf8_bom)
        self.baseline_content = self.document.content
        self.version = version
