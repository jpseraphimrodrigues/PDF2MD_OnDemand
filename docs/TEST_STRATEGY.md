# Test Strategy

## 1. Objective

Protect user content and architectural boundaries, not merely line coverage.

## 2. Test layers

### Unit

Use for:

- link parsing;
- wikilink resolution;
- path normalization;
- graph construction;
- metadata/frontmatter logic;
- operator decision logic;
- Markdown source transformations.

### Integration

Use for:

- filesystem repositories;
- SQLite indexes;
- editor/renderer bridge boundaries;
- PDF adapter;
- background job orchestration.

### Golden/fixture

Use whenever textual/structural output matters.

Examples:

```text
tests/fixtures/markdown/
tests/fixtures/pdf/
tests/golden/
```

## 3. Markdown compatibility matrix

Maintain fixtures for the features in `MARKDOWN_COMPATIBILITY.md`.

Critical regression:

> unsupported syntax survives open/save unchanged.

## 4. Workspace portability tests

Use temporary directories and simulate moving a workspace root.

Verify:

- relative links still resolve where expected;
- no generated absolute path becomes required;
- index rebuild works after deletion.

## 5. PDF fixture corpus

At minimum:

- native text;
- scan;
- hybrid;
- multi-column paper;
- table;
- equations;
- images/diagrams.

Large copyrighted fixtures should not be committed without appropriate permission.
Use synthetic/public-domain fixtures where possible.

## 6. Data-loss regression rule

Any bug capable of losing or corrupting user-authored content requires a regression test before the fix is considered complete.

## 7. GUI tests

Test core behavior below the GUI whenever possible.

Use GUI tests for actual UI contracts, not to compensate for untestable application logic.

## 8. Performance checks

Formal benchmarking is not required initially, but track obvious regressions in:

- opening large Markdown files;
- indexing medium workspaces;
- graph rendering scale;
- PDF conversion startup/runtime.

Do not optimize without evidence, but do not allow expensive work on the UI thread.
