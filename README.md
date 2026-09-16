# PDF2MD_OnDemand

> Local-first, open-source Markdown workspace for writing, reading, organizing and transforming knowledge.

## What the project is

PDF2MD_OnDemand is **not primarily a PDF converter**.

Its core is a simple Markdown workspace with three first-class capabilities:

1. **Editor + Preview** — open any standalone `.md` file and read/edit it immediately.
2. **Knowledge Workspace** — open a folder as a portable knowledge vault with links, backlinks, search and graph.
3. **Operators** — optional tools that act on Markdown or import content into Markdown. The first major operator is **PDF → Markdown**.

The long-term direction is to make Markdown files easy to create, maintain, relate and prepare for AI workflows without locking the user into a proprietary database or cloud service.

## Core principles

- 100% open source and free.
- Local-first and offline-capable for all core functions.
- Markdown files are the source of truth.
- A vault is just a normal directory chosen by the user.
- A standalone `.md` file must work without creating a vault or project.
- SQLite, caches, embeddings and generated indexes are disposable and rebuildable.
- Unknown Markdown syntax must be preserved, never rewritten destructively.
- GUI, domain logic, renderers, importers and operators must remain decoupled.
- No paid API, subscription or proprietary service may be required for core functionality.
- Files must remain useful even if PDF2MD_OnDemand no longer exists.

## Primary use cases

### Standalone Markdown

Open:

```text
notes.md
```

Read, edit, preview and save. Nothing else is required.

### Knowledge workspace

Open any directory:

```text
MyKnowledge/
├── notes/
├── assets/
├── attachments/
└── .pdf2md/
```

The application adds navigation, backlinks, wikilinks, tags, search and graph.

### PDF → Markdown

Run the PDF converter only when needed:

```text
PDF -> analysis/OCR/layout -> Markdown + assets
```

The resulting Markdown becomes an ordinary file and does not depend on the converter afterward.

## Documentation map

Read in this order when working on the repository:

1. `AGENTS.md`
2. `CONSTITUTION.md`
3. `GOALS.md`
4. `docs/PRODUCT_SPEC.md`
5. `docs/ARCHITECTURE.md`
6. The topic-specific documents under `docs/`
7. `PLANS.md` for significant implementation work
8. `PROMPTS.md` for reusable Codex prompts

## Current status

Architecture and product conception phase. Implementation has not yet been authorized by these documents.
