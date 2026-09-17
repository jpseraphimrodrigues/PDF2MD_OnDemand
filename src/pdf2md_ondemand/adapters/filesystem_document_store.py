"""UTF-8 filesystem adapter with atomic replacement and content snapshots."""

import hashlib
import os
import tempfile
from pathlib import Path
from typing import NoReturn

from pdf2md_ondemand.application.document_session import FileSnapshot
from pdf2md_ondemand.domain.document import Document


class DocumentReadError(Exception):
    """A document could not be read or decoded as UTF-8."""


class DocumentWriteError(Exception):
    """A document could not be safely written."""


class FilesystemDocumentStore:
    def read(self, path: Path) -> tuple[Document, FileSnapshot]:
        try:
            raw = path.read_bytes()
            bom = raw.startswith(b"\xef\xbb\xbf")
            content = raw[3:].decode("utf-8") if bom else raw.decode("utf-8")
            path.stat()
        except (OSError, UnicodeDecodeError) as exc:
            raise DocumentReadError(f"Could not read UTF-8 document: {path}") from exc
        document = Document(path, content, bom)
        return document, self._version(raw)

    def version(self, path: Path) -> FileSnapshot | None:
        try:
            raw = path.read_bytes()
            path.stat()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise DocumentReadError(f"Could not inspect document: {path}") from exc
        return self._version(raw)

    def write_atomic(
        self,
        path: Path,
        document: Document,
        *,
        expected_version: FileSnapshot | None,
        overwrite: bool = False,
    ) -> FileSnapshot:
        encoded = document.content.encode("utf-8")
        if document.utf8_bom:
            encoded = b"\xef\xbb\xbf" + encoded
        temp_path: Path | None = None
        current_version = self.version(path)
        if current_version != expected_version:
            self._raise_version_conflict(path, overwrite)
        if not overwrite and expected_version is not None:
            raise FileExistsError(path)
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.",
                                             suffix=".tmp", delete=False) as temp:
                temp_path = Path(temp.name)
                temp.write(encoded)
                temp.flush()
                os.fsync(temp.fileno())
            if overwrite:
                os.replace(temp_path, path)
            else:
                os.link(temp_path, path)
                temp_path.unlink()
        except OSError as exc:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise DocumentWriteError(
                f"Could not atomically save document: {path}"
            ) from exc
        return self._version(encoded)

    @staticmethod
    def _version(raw: bytes) -> FileSnapshot:
        return FileSnapshot(hashlib.sha256(raw).hexdigest())

    @staticmethod
    def _raise_version_conflict(path: Path, overwrite: bool) -> NoReturn:
        if overwrite:
            raise FileExistsError(f"Destination version changed: {path}")
        raise FileExistsError(path)
