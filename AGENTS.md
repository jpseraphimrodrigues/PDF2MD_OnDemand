# AGENTS.md — Repository Instructions for Coding Agents

These instructions apply to the entire repository unless a deeper `AGENTS.md` overrides them for a subdirectory.

## 1. Read before changing code

Before proposing or implementing a change, read:

1. `CONSTITUTION.md`
2. `GOALS.md`
3. `docs/PRODUCT_SPEC.md`
4. `docs/ARCHITECTURE.md`
5. Any topic-specific document relevant to the requested change
6. `PLANS.md` when the change is architectural, cross-cutting, or larger than a small local fix

Do not infer product behavior from the repository name. **PDF conversion is an operator, not the core product.**

## 2. Product identity

PDF2MD_OnDemand is a local-first Markdown workspace.

The immutable conceptual hierarchy is:

```text
Markdown Workspace
├── Standalone file mode
├── Workspace/Vault mode
├── Editor
├── Preview
├── Knowledge graph
└── Operators
    └── PDF -> Markdown
```

The application must remain useful even if all operators are disabled.

## 3. Non-negotiable architectural rules

### A. Markdown is the source of truth

User-authored knowledge lives in ordinary files.

Do not make SQLite, an ORM, a proprietary file, a web service or an internal object database the authoritative source of note content.

### B. Indexes are rebuildable

SQLite, search indexes, graph indexes, thumbnails, embeddings and caches are derived data.

Deleting `.pdf2md/` must not destroy user knowledge.

### C. Standalone-file mode is first-class

Opening `example.md` must not require:

- creating a workspace;
- creating a database;
- importing the file;
- moving the file;
- logging in;
- enabling AI.

### D. A workspace is an ordinary directory

The user selects any directory on:

- local disk;
- external disk;
- USB drive;
- synchronized folder;
- network storage, subject to filesystem capabilities.

No mandatory proprietary workspace container.

### E. Preserve unknown syntax

If the editor or preview does not understand a Markdown extension, preserve the source exactly.

Rendering failure is acceptable.
Destructive normalization is not.

### F. GUI does not own business logic

UI components call application use cases/interfaces.

Do not place conversion, indexing, parsing, graph construction or filesystem policy inside widgets or windows.

### G. External engines are adapters

Docling, OCR engines, renderers, graph libraries and future AI backends are implementation details behind interfaces.

Do not leak third-party objects across architectural boundaries.

### H. Core functionality is local and free

No core feature may require:

- paid API;
- subscription;
- account;
- cloud-only processing;
- telemetry service.

Optional integrations may exist later, but local alternatives must remain possible.

### I. Long work must not block the UI thread

PDF processing, OCR, indexing and other expensive tasks must run through background job infrastructure with progress, cancellation and error reporting.

### J. Prefer boring, testable architecture

Do not introduce microservices, distributed systems, message brokers, web servers or dependency-heavy frameworks without a demonstrated requirement.

## 4. Proposed technical direction

Treat this as the current default, not permission to couple layers:

- Language: Python
- Desktop shell: PySide6
- Embedded web rendering: Qt WebEngine
- Markdown editor surface: CodeMirror 6 or equivalent modular editor
- Markdown parsing/render pipeline: standards-oriented and plugin-based
- Mathematics: MathJax-compatible rendering
- Diagrams: Mermaid
- Graph 2D: Cytoscape.js or equivalent adapter
- Local derived index: SQLite
- PDF ingestion: Docling as initial engine, behind an adapter
- Tests: pytest plus golden/fixture-based document tests
- Project/environment management: `uv`

If an implementation spike shows a proposed component is unsuitable, document the evidence and update the decision record before replacing it.

## 5. Dependency policy

Before adding a runtime dependency:

1. Explain what responsibility it owns.
2. Confirm its license is compatible with this fully open-source project.
3. Prefer dependencies that work offline.
4. Avoid duplicate libraries solving the same responsibility.
5. Hide replaceable dependencies behind adapters when they represent infrastructure.

Do not add a second major framework merely to implement one minor feature.

## 6. Coding rules

- Use clear module boundaries.
- Prefer typed interfaces/protocols at architectural boundaries.
- Keep domain/application logic independent of PySide6.
- Keep filesystem paths portable.
- Store Markdown links/assets using relative paths whenever feasible.
- Avoid global mutable state.
- Use explicit error types for domain/application failures.
- Make operations cancellable when they may be slow.
- Keep functions and modules focused on one responsibility.
- Do not create generic abstractions without at least one real use case.

## 7. Testing rules

Every behavior change requires appropriate tests.

Minimum expectations:

- unit tests for pure logic;
- integration tests for adapters;
- filesystem tests using temporary directories;
- golden tests for Markdown transformations;
- document fixtures for PDF conversion;
- regression test for every fixed bug when practical.

Never use only GUI clicking as proof that core logic works.

## 8. Data safety

Any operation that can modify multiple user files must provide one of:

- preview/dry-run;
- reversible transaction strategy;
- backup/snapshot strategy;
- narrowly scoped confirmed change.

Operators must not silently rewrite an entire vault.

## 9. Work protocol

For a small, obvious, local fix:
- inspect;
- implement;
- test;
- report.

For a new feature, cross-cutting change or significant refactor:
- inspect the relevant docs/code;
- identify constraints and risks;
- create/update an execution plan;
- implement in small verified phases;
- run tests after each meaningful phase;
- update documentation when behavior or architecture changes.

If the request conflicts with `CONSTITUTION.md`, stop implementation and explain the conflict.

## 10. Definition of done

A change is not complete because the code runs once.

It is complete when:

- the requested behavior exists;
- architectural boundaries remain intact;
- relevant tests pass;
- error paths are handled;
- user data safety was considered;
- documentation reflects material changes;
- no unrelated functionality was silently changed.
