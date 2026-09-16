# Decision Log

Use this file for concise architecture/product decisions until the number of decisions justifies separate ADR files.

---

## D-001 — Product core is Markdown workspace

**Status:** Accepted

PDF conversion is an operator, not the core architecture.

Core product:

```text
Editor + Preview + Knowledge Workspace/Graph
```

---

## D-002 — Standalone file mode is mandatory

**Status:** Accepted

A `.md` file can be opened, edited, previewed and saved without a workspace.

---

## D-003 — Markdown files are authoritative

**Status:** Accepted

SQLite and future semantic indexes are derived/rebuildable.

---

## D-004 — Workspaces are ordinary directories

**Status:** Accepted

No mandatory proprietary project container.

---

## D-005 — Fully open source and free

**Status:** Accepted

No mandatory paid API or subscription for core behavior.

Dependency licensing must be checked before adoption.

---

## D-006 — Unknown Markdown syntax is preserved

**Status:** Accepted

Unsupported rendering must not trigger destructive rewriting.

---

## D-007 — Python desktop architecture

**Status:** Accepted as initial direction

Python with PySide6 is the current implementation direction.

Web technologies may be embedded for editor/preview/graph surfaces behind narrow bridges.

---

## D-008 — SQLite travels with a workspace only as derived state

**Status:** Accepted

A workspace may keep `.pdf2md/index.sqlite`.

Deleting it must not delete knowledge.

---

## D-009 — Initial graph is 2D

**Status:** Accepted

3D is later work and must not shape the graph domain model.

---

## D-010 — PDF engine is replaceable

**Status:** Accepted

Docling is the initial preferred engine candidate behind an adapter.

The core must not import or expose Docling types.

---

---

## D-011 — Canonical project identity

**Status:** Accepted

The canonical project name is `PDF2MD_OnDemand`. The Python distribution is
`pdf2md-ondemand`, the package is `pdf2md_ondemand`, the future CLI command is
`pdf2md`, and derived workspace state lives in `.pdf2md/`. `PDF2ME_OnDemand`
is not a valid project name.

---

## D-012 — Python environment and initial tooling

**Status:** Accepted

The project uses `uv` exclusively with CPython 3.13, `.python-version` set to
`3.13`, `requires-python = ">=3.13,<3.14"`, a `uv`-managed `.venv`, and a
versioned `uv.lock`. Runtime dependency is PySide6. Development dependencies
are pytest, pytest-cov, ruff and mypy. Ruff owns linting and formatting; mypy
owns static type checking. No minimum coverage percentage is imposed.

Poetry, pipenv, conda, requirements.txt, black, isort, flake8, pylint, tox,
hatch and pre-commit are excluded from the initial tooling.

---

## D-013 — Phase 0 scope

**Status:** Accepted

Phase 0 is foundation-only. `uv run pdf2md` must construct `QApplication` and
`MainWindow` and allow a minimal desktop window to open and close. Markdown,
editor, preview, workspace/vault, SQLite, relationships, graph, PDF/OCR,
operators, jobs, Mermaid, MathJax, CodeMirror, WebEngine, CI and packaging are
explicitly deferred.

## Open decisions

These require implementation spikes/evidence before final choice:

1. Exact embedded editor library and integration details.
2. Exact Markdown parser/render pipeline.
3. Exact MathJax/KaTeX packaging choice.
4. Exact HTML sanitization policy/library.
5. Exact graph renderer adapter implementation.
6. Workspace note identity policy beyond path-based linking.
7. Autosave default and conflict UX.
8. Packaging strategy for Windows/Linux.
