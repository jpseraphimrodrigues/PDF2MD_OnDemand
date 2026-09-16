# Product Specification

## 1. Product definition

PDF2MD_OnDemand is a desktop Markdown workspace designed around ordinary files.

The core product is:

```text
Editor <-> Preview <-> Knowledge Graph
```

PDF → Markdown is an optional import/operator capability.

## 2. Operating modes

### 2.1 Standalone file mode

The user opens one `.md` file.

Required behavior:

- immediate editing;
- preview;
- save/save as;
- normal editing commands;
- no workspace creation;
- no mandatory SQLite database;
- no knowledge graph initialization.

Optional rendering dependencies may initialize in the background as needed.

### 2.2 Workspace/Vault mode

The user opens a directory.

Required behavior:

- browse files;
- open multiple Markdown files;
- navigate links;
- inspect backlinks;
- search;
- view graph;
- maintain derived index;
- remain portable.

A workspace is not imported into the app.
The selected directory remains authoritative.

## 3. Core editor capabilities

The editor should support:

- plain text Markdown editing;
- syntax highlighting;
- multi-tab editing;
- undo/redo;
- find/replace;
- line/column status;
- UTF-8;
- toolbar actions that insert standard/portable Markdown;
- optional autosave with conservative defaults;
- open/save conflict detection when files change externally.

The toolbar must generate text syntax, not hidden rich-text state.

## 4. Preview capabilities

Initial target:

- CommonMark-compatible core syntax;
- GFM-like tables, task lists, autolinks and strikethrough;
- fenced code with syntax highlighting;
- images;
- SVG;
- links;
- YAML frontmatter handling;
- mathematical notation;
- Mermaid diagrams;
- wikilinks;
- callouts/admonitions;
- controlled raw HTML rendering.

See `MARKDOWN_COMPATIBILITY.md`.

## 5. Workspace knowledge features

### Wikilinks

Support at minimum:

```text
[[Note]]
[[Note|Alias]]
[[Note#Heading]]
```

Exact resolution rules must be deterministic and documented.

### Backlinks

For the active note, show notes that reference it.

### Tags

Recognize conventional Markdown tags such as:

```text
#research
#engineering/power
```

Avoid interpreting headings as tags.

### Graph

The initial graph is 2D.

Minimum interactions:

- pan/zoom;
- select node;
- open corresponding note;
- show direct neighbors;
- isolate a selection/subgraph;
- filter by basic node/link attributes.

3D is explicitly later work.

## 6. Portable workspace

Recommended shape:

```text
MyWorkspace/
├── notes/
├── assets/
├── attachments/
└── .pdf2md/
    ├── index.sqlite
    ├── cache/
    └── thumbnails/
```

The names `notes/`, `assets/` and `attachments/` are recommended defaults, not mandatory user directory structure.

The application must support existing folders containing Markdown without forcing reorganization.

## 7. Operators

Operators act on files/workspace context but are not core editor responsibilities.

The first major operator is PDF → Markdown.

Future operators may include:

- normalize formatting;
- table of contents;
- link suggestions;
- note split/merge;
- metadata extraction;
- deterministic restructuring;
- AI-assisted transformations;
- other importers.

## 8. AI readiness

The program must facilitate future AI use by keeping notes:

- structured;
- accessible;
- text-first;
- linkable;
- metadata-friendly;
- portable.

AI-specific indexes such as chunks/embeddings are derived data and must not become canonical.

## 9. User experience constraint

Feature richness must not make the first-run workflow complicated.

The application should be understandable around two actions:

```text
Open File
Open Folder
```

Everything else is progressive capability.
