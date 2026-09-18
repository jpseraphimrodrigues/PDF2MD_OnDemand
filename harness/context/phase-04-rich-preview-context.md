# Phase 4 — Rich preview context

## Scope

Implement offline Mermaid diagrams, TeX math, and conventional callouts in the
isolated Markdown preview. Keep source visible on errors, preserve Markdown
input byte-for-byte, and prevent stale asynchronous renders from replacing
newer content.

## Confirmed existing behavior

- Mermaid fences currently render as escaped `<pre><code>`.
- Math delimiters remain ordinary Markdown text.
- Blockquote callout markers are currently plain text.
- Raw HTML is disabled in markdown-it.
- Preview JavaScript is app-owned and has no QWebChannel bridge.
- D-015 blocks SVG document assets and confines image reads to raster formats.

## Resolved implementation choices

- Mermaid uses its MIT-licensed browser renderer with strict security settings.
- KaTeX uses the MathJax-compatible TeX delimiters and local HTML/MathML
  rendering, with MIT licensing.
- Mermaid and KaTeX are bundled locally; runtime use is offline.
- Callouts use the documented `> [!TYPE] Optional title` blockquote convention;
  unrecognized types are unchanged.
- SVG document assets remain disallowed under D-015. Mermaid-generated SVG is
  renderer output under strict security, not an SVG file loaded from the workspace.

## Validation record

- `npm run build`: passed; bundles Mermaid, KaTeX CSS/fonts, and license texts.
- `node test/preview.test.cjs`: 7 passed (math, callouts, Mermaid success,
  failure fallback, security configuration, and stale-render handling).
- `node test/editor_commands.test.cjs`: 3 passed.
- `ruff check ...preview_view.py pdf2md_build.py pyproject.toml`: passed.
- `mypy`: passed across 29 source files.
- `pytest tests/test_preview_navigation.py`: 6 passed.
- `npm install` reported zero known vulnerabilities with `lodash-es@4.18.1`.
- `uv build --out-dir frontend/dist/wheels`: passed after `MANIFEST.in` was
  updated to include the frontend license-copy script. Wheel inspection found
  Mermaid, Preview CSS, and the consolidated third-party notices file; temporary output
  was removed.
- `DEFERRED_ENVIRONMENT_VALIDATION`: visual check in a running Qt WebEngine
  window remains pending because the known offscreen WebEngine host is unstable.

## Preview blank-pane regression (2026-09-18)

The rich preview bundles were concatenated into HTML passed to `setHtml`, which
Qt loads through a `data:` URL. Once Mermaid and KaTeX CSS were added, the HTML
payload became several megabytes and failed to initialize consistently. The
Preview now keeps its HTML shell small and installs named, app-owned
`QWebEngineScript` entries for Mermaid, styles, and the renderer at
`DocumentReady`. File access settings remain disabled and workspace image assets
remain served only by `pdf2md-asset`.

An offscreen WebEngine smoke check loaded the shell, found
`window.renderMarkdown`, and confirmed rendered text in `#preview`. The attached
blank-pane report is therefore covered by a direct startup and rendering check;
full visual rendering should still be verified on the normal desktop host.

## Residual risks

- Local Mermaid and KaTeX CSS/font bundles add about 4.7 MB before wheel
  compression; measure Preview load latency on a normal desktop host.
- User-provided SVG images remain disallowed under D-015. Mermaid-generated
  SVG is renderer output under strict security configuration.
