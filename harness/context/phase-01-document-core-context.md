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

## Editor bridge increment (2026-09-17)

Phase 1 step 3 is implemented. `EditorView` hosts the local CodeMirror page and
retains its `QWebChannel` and `EditorBridge`; the bridge exposes only
`setContent(str)`, `getContent() -> str`, and `contentChanged(str)`. The frontend
initializes from the Python-held source after WebChannel callback and routes
CodeMirror changes back through `setContent`. A headless QWebEngine test verifies
initial Unicode round-trip and the bridge contract; separate tests ensure the
QObject surface is narrow. Validation: targeted pytest (2 passed), Ruff,
mypy, and frontend esbuild build passed. Qt headless emitted expected missing
font/GPU warnings. Generated `frontend/dist` is ignored, so frontend build must
be run before app launch. Selection/cursor integration and runtime packaging
remain for later phase steps.

## Preview renderer increment (2026-09-17)

Phase 1 step 4 is implemented. `PreviewView` uses a separate QWebEngineView
with no QWebChannel and no registered Python QObject. `render_markdown` passes
JSON-serialized Markdown to the local `window.renderMarkdown` API. The frontend
uses markdown-it with `html: false`, `linkify: true`, and `typographer: false`.
An npm test builds the actual bundle and executes it with a minimal DOM shim;
it verifies headings/emphasis, raw script escaping, and unchanged input source.
Validation: `npm test` passed; previous Editor tests, Ruff and mypy passed.
Preview's actual WebEngine page and security/navigation/assets are still to be
covered in later steps.

## Split UI increment (2026-09-17)

Phase 1 step 6 is implemented. `MainWindow` now composes `EditorView` and
`PreviewView` in a horizontal `QSplitter` and debounces Editor content changes
for 200 ms before rendering the most recent Markdown. A deterministic test uses
widget substitutes to verify composition and debounce; Editor's WebEngine
round-trip and Preview's actual bundle behavior have separate coverage.
Validation: focused pytest (3 passed), Ruff, mypy, and `npm test` passed.
Open/Save, dirty state, toolbar, and asset/navigation policies remain later work.

## Autonomous execution stop (2026-09-17)

The run completed steps 2, 3, 4, and 6, with checkpoints. It stopped before
step 5 because the documented production boundary for document assets remains
undecided: Qt's `QWebEngineUrlSchemeHandler` versus a custom URL scheme and,
more materially, the authorized root for assets in a standalone document. This
choice governs filesystem isolation and path portability and affects the
upcoming Open/Save integration. Resume by deciding and recording the scheme /
handler plus whether a standalone note may reference only its parent directory
or an independently selected asset root. No asset resolution was implemented.

## Asset boundary decision (D-015, 2026-09-17)

The user resolved the step 5 architectural question. Use a registered
`pdf2md-asset` custom scheme backed by `QWebEngineUrlSchemeHandler`, installed
only into the Preview's dedicated `QWebEngineProfile`. URLs are
`pdf2md-asset://<document-session-id>/<relative-path>`. Each active document
session authorizes only the containing directory of its Markdown file and can
be invalidated. Resolve decoded/normalized paths canonically and reject absolute,
drive, UNC, file URLs, `..` escapes, and symlink targets outside the root. The
handler is read-only, serves regular files only, has no directory listing, and
allows PNG/JPG/JPEG/GIF/WebP only; arbitrary SVG and user-selected external roots
are out of scope. Scheme registration must happen at startup before profile
creation. D-015 records this binding choice.

## Preview asset handler increment (2026-09-17)

Phase 1 step 5 is implemented per D-015. `pdf2md-asset` is registered in the
entrypoint before QApplication; `PreviewView` owns an off-the-record dedicated
`QWebEngineProfile` with `PreviewAssetHandler`, while the default/Editor profile
has no handler. The Preview page and generated trusted bundle are combined via
`setHtml` under a QRC base URL, allowing `LocalContentCanAccessFileUrls=False`.
Remote URL access, JS window opening and LocalStorage are also disabled.

`AssetSessionRegistry` creates/revokes per-document UUID sessions rooted at the
Markdown parent directory. The path resolver decodes UTF-8, rejects absolute,
drive, UNC, backslash, malformed paths, traversal and unsupported extensions,
then resolves canonically under root and accepts regular files only. Handler
serves read-only PNG/JPG/JPEG/GIF/WebP MIME types, no listing. Renderer rewrites
safe relative images only when a session exists and replaces invalid/no-session
or non-HTTP(S) non-relative sources with `about:blank`; raw HTML remains off.

Validation after the final layering change: focused pytest 19 passed, 1 skipped
(symlink creation denied by Windows environment); Ruff and mypy passed; npm test
passed. One offscreen QWebEngine run observed an actual GIF response through the
scheme handler. The asynchronous network callback test was removed as flaky, so
a deterministic end-to-end asset request is residual validation risk. Runtime
startup requires `npm run build` because generated `frontend/dist` remains
ignored; the Preview trusted bundle is embedded in the local QRC-base shell.

## Open/Save UI increment (2026-09-17)

Phase 1 step 7 and the UI integration portion of step 1 are complete.
`MainWindow` provides Open, Save, and Save As actions backed by the existing
application use cases and filesystem adapter. Successful open switches the
session, Editor text, and Preview asset root; failed read leaves the current
session untouched. Save checks the optimistic version token. Save As asks before
overwrite, and the adapter detects external destination changes before replace.
A pathless session routes Save to Save As. Targeted pytest (29 passed, 1 skipped
for restricted Windows symlink creation), Ruff, and mypy passed. Close/open dirty
confirmation is intentionally the next step (8); no destructive data-loss
prompt exists yet.

## Dirty-state lifecycle increment (2026-09-17)

Phase 1 step 8 is implemented. Before opening another file or closing the
window, dirty sessions prompt Save/Discard/Cancel. Save routes through the
existing save flow; any cancelled Save As or write/version conflict blocks the
transition. Discard is explicit; Cancel leaves the current session/content
intact. The window title shows the current basename and `*` while dirty, and
updates after successful save/open. Focused pytest (14 passed), Ruff, and mypy
passed. No autosave or multi-tab behavior was added.

## Markdown toolbar increment (2026-09-17)

Phase 1 step 9 is implemented. Qt toolbar actions for Bold, Italic, Heading,
Link, and Code pass only whitelisted command names through `EditorBridge`; the
frontend maps each to one CodeMirror transaction. Empty formatting selections
place the caret between markers. Empty Link inserts `[text](url)` and selects
`text`; selected Link wraps the selection and selects the `url` placeholder.
Heading adds `# ` at the current line start. Programmatic source synchronization
is annotated outside history; formatting remains undoable by CodeMirror's native
history. Headless QWebEngine proves bold + undo preserves the original Unicode
source. Focused pytest (18 passed), `npm test` (4 passed), Ruff, and mypy passed.

## Preview navigation security increment (2026-09-17)

Phase 1 step 10 is implemented. `PreviewPage` blocks unknown/dangerous schemes,
permits internal QRC/custom asset resources only in non-main-frame navigation,
and emits an external request only for an HTTP(S) `NavigationTypeLinkClicked` in
the main frame. The main window asks the user before passing the URL to
`QDesktopServices`; redirects, automatic HTTP(S) navigations, and external
subframes are blocked silently. Main-frame navigation to `pdf2md-asset` is also
blocked. Preview downloads are cancelled, popups rejected, and local file,
remote access, LocalStorage, and JS window opening are disabled. Raw HTML stays
disabled by markdown-it; JS is enabled only for the trusted bundled app shell.
Focused pytest (27 passed, 1 skipped due to Windows symlink restriction), Ruff,
mypy, and `npm test` (4 passed) passed. Policy/UI tests are unit-level; real
Chromium click/redirect navigation has not been exercised end-to-end.
