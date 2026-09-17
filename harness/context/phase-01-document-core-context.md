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

## Frontend build increment (2026-09-17)

Phase 1 step 2 is complete. Production-oriented frontend sources now live under
`frontend/src/`: isolated CodeMirror Editor page and markdown-it Preview page,
with `package.json`/`package-lock.json` and an esbuild command producing local
`dist/editor.js` and `dist/preview.js`. `frontend/.gitignore` excludes generated
`dist/` and `node_modules/`; only sources and lockfile are versioned. Runtime
Python does not invoke Node/npm. The Editor HTML references the local Qt
WebChannel resource and its local bundle; the Preview references only its local
bundle. No remote code loading/fetch/XHR/WebSocket was found in source or built
bundles. HTTP(S) strings remain for Markdown link handling and comments.

Validation: from `frontend/`, `npm ci` and `npm run build` passed. In Python,
`uv run pytest` (8 passed), `uv run ruff check src tests`, and `uv run mypy`
passed. Integration and runtime packaging are still pending in subsequent steps.
