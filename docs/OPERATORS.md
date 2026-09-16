# Operator Model

## 1. Definition

An operator is a tool that performs a bounded action using a document or workspace context.

Operators are not the editor core.

## 2. Categories

Potential categories:

```text
operators/
├── importers/
├── markdown/
├── knowledge/
└── ai/
```

These categories are organizational, not separate runtime services.

## 3. First operator

The first major operator is:

```text
PDF -> Markdown
```

Its job ends when it has produced normal Markdown and associated assets.

The resulting note must not require the PDF operator to remain readable/editable.

## 4. Future deterministic operators

Examples:

- format/normalize selected Markdown;
- generate table of contents;
- split note;
- merge notes;
- extract metadata;
- validate links;
- repair relative asset paths;
- create/update frontmatter;
- generate link reports.

Bulk modification must follow data-safety rules.

## 5. Future AI operators

Examples:

- summarize selected content;
- restructure a note;
- suggest related notes;
- extract entities;
- ask a note;
- ask a workspace;
- generate metadata.

AI operators must remain optional.

A provider interface should allow local models and optional remote providers without making either class mandatory.

## 6. Context

An operator should receive a narrow context, for example:

```text
StandaloneDocumentContext
WorkspaceContext
SelectionContext
```

Do not give every operator unrestricted access to the full GUI and filesystem.

## 7. Results

Operator results should be explicit.

Possible result forms:

- new file;
- proposed patch;
- generated assets;
- report;
- derived metadata;
- no-op with reason.

Where user content will be modified, prefer previewable changes.

## 8. Discovery/registry

Do not build a sophisticated external plugin marketplace in the MVP.

Start with an internal registry/interface once at least two concrete operators need common lifecycle behavior.

External plugin loading can be designed later from evidence.
