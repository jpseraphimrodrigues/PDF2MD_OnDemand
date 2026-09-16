# Project Constitution

Version: 0.1  
Status: Binding architectural principles

This document defines invariants that must survive implementation choices.

## Principle I — Markdown sovereignty

Markdown files are the canonical representation of user-authored knowledge.

The application may derive indexes, metadata, caches, thumbnails, embeddings and graph structures, but those artifacts must not become required to recover the user's notes.

**Test:** deleting generated application data must leave the user's Markdown and assets intact and usable.

## Principle II — Portable by directory

A knowledge workspace is an ordinary filesystem directory selected by the user.

The same directory should be openable from another computer, subject only to path availability and compatible filesystem semantics.

The application must not depend on a fixed drive letter or absolute internal links.

## Principle III — Standalone simplicity

The simplest valid workflow is:

```text
Open .md -> read/edit/preview -> save
```

No vault, project creation, account, database initialization or AI configuration may be required.

Advanced features must layer on top of this workflow rather than replace it.

## Principle IV — Open formats, open source, no mandatory paid service

The project is fully open source and free.

Core functionality must be operable locally and offline after installation.

User content must be stored in open or broadly interoperable formats.

Optional external integrations must not make the core dependent on paid infrastructure.

## Principle V — Preservation over interpretation

Markdown is an extensible ecosystem.

The program must preserve syntax it cannot interpret.

Unknown fenced blocks, frontmatter fields, custom directives and extension syntax must not be removed or normalized merely because the current renderer does not support them.

## Principle VI — Separation of responsibilities

The architecture must distinguish:

- domain concepts;
- application use cases;
- infrastructure;
- adapters;
- GUI;
- renderers;
- operators.

Changing the GUI must not require rewriting the document model.
Changing a PDF engine must not require changing the editor.
Changing a graph renderer must not require changing link discovery.

## Principle VII — Operators are optional extensions

PDF → Markdown is the first major operator, not the application core.

The workspace must function when the PDF operator is absent.

Future operators may include deterministic Markdown transformations, importers, knowledge tools and AI-assisted operations.

## Principle VIII — Derived state is disposable

The `.pdf2md/` directory may contain generated application state such as:

```text
.pdf2md/
├── index.sqlite
├── cache/
├── thumbnails/
└── embeddings/
```

The system must provide a path to rebuild derived state from canonical files whenever feasible.

## Principle IX — Safe modification

Reading and rendering may be automatic.

Bulk mutation of user content must be explicit, narrow and recoverable.

No operator may silently rewrite an entire workspace.

## Principle X — AI-ready, not AI-dependent

The project should produce structured, clean Markdown that is useful to future AI workflows.

However:

- AI is not required for basic editing;
- AI is not required for graph construction;
- AI is not required for opening a vault;
- AI is not required for PDF conversion when deterministic/local tooling is sufficient.

AI features must enter through replaceable operator/backend interfaces.

## Principle XI — Simplicity is a feature

Do not solve hypothetical scale.

Prefer a single desktop process with clear modules until evidence requires otherwise.

Architectural extensibility means replaceable responsibilities, not maximum abstraction.

## Principle XII — Testable core

Core behaviors must be testable without launching the GUI.

Important workflows should be callable through application services and, where useful, a CLI.

## Amendment rule

A change that violates a principle in this document must not be hidden inside implementation work.

The constitution must be deliberately amended, with the reason recorded in `docs/DECISIONS.md`.
