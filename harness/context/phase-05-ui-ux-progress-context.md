# Phase 5 Context — UI/UX Progress

## Baseline

- Implemented on `feature/ui-ux-progress`, branched from `main` at `aa9e579`.
- `MainWindow` owns one active `DocumentSession`; `EditorView` has one CodeMirror
  `EditorView` and exposes content plus a narrow formatting-command bridge.
- The main workspace tree and native `QGraphicsView` graph are QDockWidgets;
  editor/Preview share a horizontal `QSplitter`.
- Editor and Preview use separate WebEngine views and frontend bundles.

## User decisions

- Light-first, neutral, focused visual direction; existing English interface labels.
- Full navigation refresh and multi-document tabs.
- Each tab keeps its document, dirty state, CodeMirror undo/redo history, selection,
  cursor and scroll position. Opening an existing path focuses its tab.
- Closing a dirty tab/workspace/app requires explicit Save, Discard or Cancel.
- Closing/switching a workspace closes its documents after resolving changes;
  tabs outside it remain open. Cancellation must not partially close tabs.
- Remember window and panel layout locally.
- Compare Plotly to the current native renderer; keep Qt unless Plotly gives a clear
  offline, safe, loadable improvement.

## Implementation notes

- Keep document-tab coordination in UI. Do not put view state or theme into the
  domain/application document contracts.
- `QSettings` must use application scope, never workspace scope.
- CodeMirror switching must suppress the update listener while restoring a prior
  `EditorState`, or the newly active `DocumentSession` can be overwritten by the
  previous tab's content.
- Capture `EditorView.scrollDOM` offsets separately from `EditorState`.
- Workspace close should first resolve all dirty in-scope documents, then perform
  saves/closes; on Cancel no tab/workspace state changes.
- Plotly comparison is a prototype only until the documented acceptance gate passes.

## Validation log

### 2026-09-18

- Added `DocumentTabs` as UI-only session registry; Markdown and application
  document contracts remain unchanged.
- The editor bridge exposes only explicit `switchDocument`, `closeDocumentState`
  `getDocumentKey` and keyed `setDocumentContent` additions; no generic Python
  object bridge was added. A late edit updates its still-open source session; it
  cannot overwrite the different active CodeMirror document, and closed-tab keys
  are ignored by the window.
- CodeMirror state is stored by tab key, including `EditorState` and scroll offsets.
  Real Qt WebEngine smoke test verifies two independent undo histories and that
  switching emits no false text updates.
- Workspace close/switch recomputes ownership after Save As, so a document saved
  outside the previous root stays open. Cancel leaves workspace and tabs intact.
- QSettings stores geometry, size/state, splitter sizes and panel visibility.
  Closing workspace hides workspace-specific docks without overwriting their
  preferred visibility. Settings are application-scoped in the entry point.
- Validation: focused Python tests 26 passed; frontend `npm test` 11 passed; Ruff
- Final validation: full pytest suite 77 passed, 2 skipped; frontend `npm test`
  11 passed; Ruff and mypy focused checks passed.
- Native graph measurement, with cyclic fixtures and offscreen Qt, produced 21.25,
  92.29 and 184.86 ms at 100, 500 and 1,000 nodes. Plotly was absent from the
  environment and no dependency was added, so its equivalent offline prototype
  and visual/asset comparison remain `DEFERRED_ENVIRONMENT_VALIDATION`.
- Manual Windows visual inspection remains outstanding. `npm test` must be run from
  `frontend`; the first attempted invocation from repository root was invalid and
  was rerun successfully from the correct directory.
