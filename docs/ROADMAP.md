# Roadmap

This roadmap is architectural sequencing, not a release-date commitment.

## Phase 0 — Repository foundation

- `uv` project setup;
- package skeleton based on real responsibilities;
- pytest;
- lint/type policy;
- logging/error conventions;
- basic PySide6 shell;
- CI after local baseline is stable.

## Phase 1 — Standalone Markdown

Deliver:

```text
Open .md -> edit -> preview -> save
```

Includes:

- CodeMirror 6 editor in a dedicated WebEngine view;
- separate markdown-it preview in a dedicated WebEngine view;
- narrow QWebChannel bridge in the editor only;
- preview;
- tabs if justified;
- file change safety;
- toolbar basics;
- Markdown compatibility fixtures.

The first implementation target is standalone-file mode. Workspace/Vault,
multi-tab and rich extensions remain later work unless separately approved.

This phase proves the core product.

## Phase 2 — Rich preview

Add/complete:

- GFM-style extensions;
- math;
- Mermaid;
- syntax highlighting;
- frontmatter;
- callouts;
- security policy for HTML.

## Phase 3 — Workspace

Add:

- open folder;
- file tree;
- recent workspaces;
- portable workspace configuration;
- index lifecycle.

## Phase 4 — Knowledge relationships

Add:

- wikilinks;
- backlinks;
- tags;
- search;
- link validation.

## Phase 5 — Graph 2D

Add:

- graph model;
- renderer adapter;
- select/open/isolate/filter interactions.

## Phase 6 — Operator framework

Introduce only the abstractions needed for actual operators.

Establish:

- context;
- lifecycle;
- progress;
- cancellation;
- result/reporting.

## Phase 7 — PDF → Markdown

Add:

- primary conversion adapter;
- OCR behavior;
- assets;
- conversion dialog;
- fixture/golden corpus.

## Phase 8 — Hardening

Focus on:

- portability;
- external file changes;
- recovery/rebuild;
- larger workspace behavior;
- packaging;
- documentation.

## Post-1.0 candidates

- additional importers;
- deterministic Markdown operators;
- graph 3D;
- local AI integration;
- optional remote AI providers;
- semantic indexing/RAG;
- plugin ecosystem.

Do not pull post-1.0 work into the MVP without an explicit scope decision.
