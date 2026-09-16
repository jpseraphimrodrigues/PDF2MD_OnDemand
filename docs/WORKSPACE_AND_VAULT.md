# Workspace and Vault

## 1. Terminology

Internal architecture should prefer **Workspace**.

The UI may use **Vault** if that terminology proves clearer to users.

A workspace is an ordinary directory containing user files.

## 2. No mandatory folder schema

The application must be able to open:

```text
ExistingFolder/
├── a.md
├── subfolder/
│   └── b.md
└── image.png
```

without forcing the user to migrate files.

For newly created workspaces, the application may propose:

```text
MyWorkspace/
├── notes/
├── assets/
├── attachments/
└── .pdf2md/
```

## 3. Portable application state

Generated workspace state may live under:

```text
.pdf2md/
```

Potential contents:

```text
.pdf2md/
├── workspace.json
├── index.sqlite
├── cache/
└── thumbnails/
```

This directory is application-generated and must be safe to rebuild where feasible.

## 4. SQLite role

SQLite is useful for:

- file index;
- parsed headings;
- tags;
- outgoing links;
- backlinks;
- graph edges;
- search support;
- file signatures/timestamps;
- future derived metadata.

SQLite is not authoritative note storage.

## 5. Recovery

The application should eventually expose:

```text
Workspace -> Check integrity
Workspace -> Rebuild index
Workspace -> Clear cache
```

Removing or corrupting `index.sqlite` must not imply note loss.

## 6. Removable drives

Portable workspaces may be stored on USB/removable media.

Account for:

- drive letter changes;
- device removal during operation;
- interrupted writes;
- slower random I/O;
- filesystem limitations.

Use relative internal paths.
Prefer atomic save patterns for note writes where feasible.

## 7. Synchronized folders

Users may place workspaces in OneDrive, Google Drive or similar synchronized directories.

The project does not implement synchronization itself in the initial scope.

The editor should eventually detect external file changes and avoid silently overwriting conflicting content.

## 8. Git compatibility

A workspace should remain friendly to Git.

Avoid:

- unnecessary binary state mixed with notes;
- absolute machine-specific paths;
- nondeterministic rewriting of Markdown;
- gratuitous formatting changes.

Generated `.pdf2md/` content should have a documented recommended `.gitignore` policy.
Some workspace configuration may be worth versioning; caches/indexes normally are not.
