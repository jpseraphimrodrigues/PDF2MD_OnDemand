# Architecture

## 1. Architectural objective

Enable independent evolution of:

- GUI;
- Markdown editor;
- preview renderer;
- workspace indexing;
- knowledge graph;
- importers/operators;
- persistence/cache infrastructure.

The architecture should be modular without becoming framework-heavy.

## 2. Dependency direction

```text
┌──────────────────────────────────────────────┐
│                    UI                        │
│ PySide6 shell / editor host / preview / graph│
└──────────────────────┬───────────────────────┘
                       │ calls
                       ▼
┌──────────────────────────────────────────────┐
│              Application layer               │
│ use cases / orchestration / jobs / commands  │
└──────────────────────┬───────────────────────┘
                       │ depends on
                       ▼
┌──────────────────────────────────────────────┐
│               Domain + Ports                 │
│ Note / Workspace / Link / Graph / Operator   │
│ interfaces for replaceable dependencies      │
└──────────────────────┬───────────────────────┘
                       ▲
                       │ implemented by
┌──────────────────────┴───────────────────────┐
│                 Adapters                     │
│ filesystem / SQLite / renderer / PDF engine  │
└──────────────────────────────────────────────┘
```

Domain code must not import the GUI or concrete engines.

## 3. Suggested package shape

```text
src/pdf2md/
├── domain/
│   ├── note.py
│   ├── workspace.py
│   ├── link.py
│   ├── graph.py
│   └── operator.py
│
├── application/
│   ├── open_document.py
│   ├── save_document.py
│   ├── open_workspace.py
│   ├── index_workspace.py
│   ├── build_graph.py
│   └── run_operator.py
│
├── ports/
│   ├── note_repository.py
│   ├── workspace_index.py
│   ├── markdown_renderer.py
│   ├── graph_provider.py
│   └── document_converter.py
│
├── adapters/
│   ├── filesystem/
│   ├── sqlite/
│   ├── markdown/
│   ├── graph/
│   └── converters/
│
├── operators/
│   ├── importers/
│   └── markdown/
│
├── infrastructure/
│   ├── config/
│   ├── jobs/
│   └── logging/
│
├── ui/
│   └── desktop/
│
└── cli/
```

This is a target organization, not permission to create empty abstraction files.

## 4. Document model

A note should be represented independently of the editor widget.

Conceptually:

```text
Note
├── identity (optional stable ID)
├── path
├── title
├── raw source
├── frontmatter
├── headings
├── outgoing links
├── tags
└── referenced assets
```

`raw source` matters because source preservation is a product invariant.

Derived parsing information may be lazily computed or indexed.

## 5. Workspace model

A workspace is:

```text
Workspace
├── root path
├── configuration
├── note discovery policy
├── asset policy
└── derived index handle
```

Do not equate a workspace with SQLite.

## 6. Identity and paths

Prefer relative paths inside workspace-derived relationships.

If stable note IDs are introduced, they must remain optional from the user's perspective.

Do not require proprietary IDs to resolve ordinary Markdown links.

## 7. Editor/renderer boundary

The editor edits source text.

The preview renders source text.

The renderer must not mutate the editor source as a side effect.

If a web-based editor/preview is embedded with Qt WebEngine, define a narrow bridge rather than exposing arbitrary Python objects to JavaScript.

## 8. Graph boundary

The graph domain should expose a serializable DTO-like structure:

```text
Graph
├── nodes
└── edges
```

A rendering adapter maps it into Cytoscape.js or a future renderer.

The knowledge/index layer must not contain Cytoscape-specific state.

## 9. Operator boundary

Conceptually:

```python
class Operator:
    metadata
    can_run(context) -> bool
    run(context, options, progress, cancellation) -> result
```

Exact API is deferred until the first two real operators justify it.

Avoid designing a plugin framework solely from hypothetical future use.

## 10. Background work

Use a job/task abstraction for operations that may block:

- PDF conversion;
- OCR;
- workspace indexing;
- thumbnail generation;
- future embeddings.

Required capabilities should include:

- progress;
- cancellation where underlying operations allow it;
- structured result/error;
- safe UI handoff.

## 11. Configuration

Separate:

### Application preferences

Belong to the application/user environment.

Examples:
- theme;
- window state;
- recent files/workspaces.

### Workspace configuration

Belongs with the portable workspace only when it affects workspace semantics.

Examples:
- ignored directories;
- asset policy;
- link resolution options.

Avoid storing machine-specific absolute paths in portable workspace configuration.

## 12. CLI

Core/application workflows should be callable without GUI when useful.

Potential examples:

```text
pdf2md open/check <file>
pdf2md index <workspace>
pdf2md convert <pdf>
pdf2md rebuild-index <workspace>
```

The CLI is not required to mirror every UI action.
Its purpose is testability, automation and operational recovery.
