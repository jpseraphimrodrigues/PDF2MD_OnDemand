# Phase 4 — Rich preview rendering

## Objective

Render Mermaid diagrams, TeX math, and conventional blockquote callouts in the
Markdown preview using local, packaged frontend assets. A rendering error must
leave the Markdown-rendered source visible, and rendering must never modify
document source.

## Existing state

- `frontend/src/preview.js` uses markdown-it with raw HTML disabled.
- Mermaid fences currently render as ordinary code blocks.
- Math delimiters currently remain literal text.
- Blockquote callout markers are currently shown as plain text.
- `PreviewView` embeds the locally built preview bundle in its isolated,
  unprivileged WebEngine page.
- `pdf2md_build.py` packages built frontend files into the Python distribution.

## Constraints

- Follow D-014: no CDN or network access at runtime; no Python bridge in Preview.
- Follow D-015: do not enable arbitrary SVG document assets or widen filesystem
  access.
- Preserve source text and unknown fenced blocks.
- Keep renderers behind the preview boundary and pass untrusted note text as
  data to trusted local rendering code.
- Mermaid must use strict security mode and disable diagram click behavior.
- New frontend runtime packages require compatible licenses and offline
  packaging.

## Risks and unknowns

- Mermaid output is SVG generated from untrusted text; strict security settings
  and fallback-to-source behavior are required.
- MathJax typesetting is asynchronous; rapid edits must not let an older render
  replace a newer preview.
- Packaging must include all runtime assets and work without Node after build.
- SVG image files referenced by Markdown remain blocked under D-015.

## Proposed design

- Use Mermaid's local browser bundle with `securityLevel: "strict"`,
  `startOnLoad: false`, and no click binding.
- Use KaTeX's local renderer with MathJax-compatible TeX delimiters: `$...$`,
  `$$...$$`, `\\(...\\)`, and `\\[...\\]`.
- Recognize the interoperable `> [!TYPE] Optional title` blockquote convention
  for common callout types. Unknown markers remain ordinary blockquotes.
- `renderMarkdown` first renders Markdown, then asynchronously renders Mermaid
  fences and typesets math. A generation token discards stale async work.
- Leave Mermaid source code in place when parsing fails. MathJax failure leaves
  the source delimiters/text visible.
- Copy required vendor bundles to frontend build output and package them with
  the preview. No runtime network access or new Python dependency.

## Files expected to change

- `frontend/package.json`, `frontend/package-lock.json`
- `frontend/build.mjs` (or an equivalent build script for local vendor assets)
- `frontend/src/preview.js`, `frontend/src/preview.html`
- `frontend/test/preview.test.cjs` and visual compatibility fixtures
- `src/pdf2md_ondemand/ui/desktop/preview_view.py`
- `pdf2md_build.py`
- `MANIFEST.in`
- `docs/DECISIONS.md`, `docs/MARKDOWN_COMPATIBILITY.md`
- This plan and `harness/context/phase-04-rich-preview-context.md`

## Implementation and validation

1. Add the licensed offline renderer packages and deterministic local build
   outputs; validate the built bundles load in the preview test harness.
2. Add async Mermaid/math rendering with strict rendering policy, stale-result
   protection, and visible fallback source; test successful, failed, and
   superseded renders.
3. Verify packaging includes all vendor assets and run frontend tests/build,
   focused Python preview tests, Ruff, and mypy as applicable.

## Data safety

Rendering is read-only. No Markdown files are rewritten. SVG input files stay
blocked as required by D-015.

## Completion evidence

- Added Mermaid 11.17.2 (MIT) and KaTeX 0.18.1 (MIT), bundled for offline use.
- Mermaid uses strict security, bounded text/edge counts, no click binding,
  source fallback on parse errors, and a revision guard for rapid edits.
- KaTeX renders inline `$...$` and `\\(...\\)`, and display `$$...$$` and
  `\\[...\\]`; invalid TeX keeps visible source.
- Added blockquote callouts for known `[!TYPE]` markers, optional titles, and
  safe text-only title insertion; unknown markers remain unchanged.
- Added package license notices, font data URLs, and source-distribution
  inclusion for the license-copy build script.
- Pinned transitive `lodash-es` to 4.18.1 after audit found the previous
  version vulnerable and 4.18.0 deprecated. npm reported zero vulnerabilities.
- `npm run build`: passed. `node test/preview.test.cjs`: 7 passed.
  `node test/editor_commands.test.cjs`: 3 passed.
- `ruff check src/pdf2md_ondemand/ui/desktop/preview_view.py pdf2md_build.py
  pyproject.toml`: passed. `mypy`: passed for 29 source files.
- `pytest tests/test_preview_navigation.py`: 6 passed (pytest cache warning
  only).
- `uv build --out-dir frontend/dist/wheels`: passed after adding
  `frontend/scripts/*.cjs` to `MANIFEST.in`. Wheel inspection confirmed Mermaid,
  Preview CSS, and the consolidated third-party notices file; temporary output was
  removed.
- `DEFERRED_ENVIRONMENT_VALIDATION`: visual Mermaid/math/callout check in a
  running Qt WebEngine window remains pending because of known offscreen
  WebEngine instability.
- Residual: bundles add about 4.7 MB before wheel compression; measure Preview
  load latency on a normal desktop host.

### Preview startup regression fix (2026-09-18)

- Cause: Mermaid, Preview JavaScript, and KaTeX CSS were concatenated into the
  HTML passed to `QWebEnginePage.setHtml`. Qt serializes that HTML through a
  `data:` URL; the resulting multi-megabyte URL did not load reliably and left
  the Preview pane blank.
- Fix: keep the app-owned HTML shell small and inject the local Mermaid bundle,
  KaTeX CSS, and Preview bundle through named `QWebEngineScript` entries at
  `DocumentReady`. This avoids a large `data:` URL and does not enable local
  file access or alter document asset handling.
- Regression evidence: offscreen Qt WebEngine reported `loadFinished=True`,
  `typeof window.renderMarkdown === "function"`, and rendered `Preview is alive`
  into the Preview DOM.
- Validation: `pytest tests/test_preview_navigation.py tests/test_asset_paths.py
  tests/test_main_window.py -q` passed (36 passed, 1 environment skip); Ruff and
  mypy passed for affected Python files.
- Intended checkpoint: `fix: restore rich preview startup`.
