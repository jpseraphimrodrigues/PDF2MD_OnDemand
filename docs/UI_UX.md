# UI / UX Direction

## 1. Primary constraint

The application must remain simple despite advanced capabilities.

A first-time user should understand two primary actions:

```text
Open File
Open Folder
```

## 2. Standalone file UI

Conceptual layout:

```text
┌───────────────────────────────────────────────────────────┐
│ File  Edit  Insert  View  Tools                          │
├───────────────────────────────────────────────────────────┤
│ B I H1 H2 Link Image Table Code Math Mermaid ...         │
├────────────────────────────┬──────────────────────────────┤
│                            │                              │
│          EDITOR            │           PREVIEW            │
│                            │                              │
├────────────────────────────┴──────────────────────────────┤
│ Markdown | UTF-8 | Ln | Col                              │
└───────────────────────────────────────────────────────────┘
```

The user must not see vault/index/database concepts here.

## 3. Workspace UI

Opening a folder progressively adds:

- file tree;
- tabs;
- backlinks;
- search;
- graph access.

Do not permanently consume large screen space for advanced panels when unused.

## 4. Preview modes

The product may support:

- editor only;
- split editor/preview;
- preview only.

External-browser preview may be considered later, but embedded preview should be the primary experience if technically reliable.

## 5. Graph

The graph should be a navigation tool, not decoration.

Minimum useful interactions:

- select;
- inspect;
- isolate;
- filter;
- open note;
- navigate neighbors.

Avoid prioritizing visual effects over readability.

## 6. Long operations

PDF conversion and indexing require:

- visible progress;
- cancellation when feasible;
- non-blocking UI;
- understandable failure message.

## 7. Destructive actions

Bulk rename, move, link rewrite or operator edits must clearly communicate affected files.

Do not hide multi-file modifications behind an innocuous toolbar action.
