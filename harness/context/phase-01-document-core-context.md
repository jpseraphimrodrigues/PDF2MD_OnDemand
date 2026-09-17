# Phase 1 Document Core Context

## Delivered increment

Implemented the toolkit independent standalone document core:

- `Document` stores a path, exact decoded source, and whether the source had a
  UTF-8 BOM.
- `DocumentSession` tracks the saved baseline, dirty state, and an optimistic
  version token (`FileSnapshot`) containing the SHA-256 of complete file bytes.
- Open/save use cases depend on a `DocumentStore` port.
- `FilesystemDocumentStore` reads UTF-8 (rejecting invalid sequences), retains
  BOM and line endings, and writes through a same-directory temporary file.
- Normal save raises `ExternalModificationError` when the version differs,
  checked both by the use case and immediately before replacement by the adapter.
- Save As defaults to `overwrite=False`; an existing destination raises
  `DestinationExistsError` without changing it or the session. Explicit
  `overwrite=True` permits atomic replacement when the destination version has
  not changed since it was inspected.
- New destinations use an atomic hard-link publication when overwrite is false,
  preventing a concurrently created destination from being silently replaced.

## Evidence

- `uv run pytest tests/test_document_session.py`: 6 passed.
- `uv run ruff check src/pdf2md_ondemand/application src/pdf2md_ondemand/adapters src/pdf2md_ondemand/ports tests/test_document_session.py`: passed.
- `uv run mypy`: passed.

## Limits and next work

The token is content based, so a file rewritten byte-for-byte identically is
treated as the same version. For overwrite of an existing file, a portable
compare-and-swap primitive is unavailable; a small race remains between the
adapter's final version check and `os.replace`. Non-overwrite publication of a
new path is atomic on filesystems that support hard links; filesystems that do
not support them will return a write error rather than silently clobber a file.
Save As overwrite UX and the document core remain unconnected to the editor UI.
