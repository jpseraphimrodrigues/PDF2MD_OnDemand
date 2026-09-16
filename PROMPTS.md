# Codex Prompt Library

These are reusable prompts for conversations with Codex. They are deliberately procedural so that implementation does not outrun the project specification.

---

## Prompt 01 — Repository orientation

```text
Read AGENTS.md, CONSTITUTION.md, GOALS.md, docs/PRODUCT_SPEC.md,
docs/ARCHITECTURE.md and the rest of docs/ that materially apply.

Do not modify code yet.

Give me:
1. your current model of the product;
2. the architectural invariants you must preserve;
3. the current repository state;
4. inconsistencies or missing decisions you found;
5. the smallest sensible next development phase.

Separate confirmed facts, inferences and unresolved questions.
Do not propose features outside the documented scope.
```

---

## Prompt 02 — Plan a new feature

```text
We are going to implement: <FEATURE>.

First read all applicable repository instructions and architecture documents.
Do not code yet.

Create an execution plan under harness/plans/ using PLANS.md.

The plan must:
- state user-visible acceptance criteria;
- identify affected architectural layers;
- preserve Markdown as source of truth;
- avoid putting business logic in the GUI;
- identify data-safety risks;
- name tests before implementation;
- identify any uncertain dependency choice that needs a spike.

After creating the plan, summarize the main design decision and stop.
```

---

## Prompt 03 — Implement an approved plan

```text
Implement the approved plan: <PLAN FILE>.

Read AGENTS.md, CONSTITUTION.md and the complete plan first.

Work phase by phase.
After each meaningful phase:
- run the relevant tests;
- fix regressions before continuing;
- keep changes inside the planned scope.

Do not replace libraries, alter architecture or expand scope without documenting
why the existing plan is insufficient.

At the end report:
1. files changed;
2. behavior implemented;
3. tests/commands actually executed and their results;
4. remaining risks or incomplete items;
5. whether documentation needs updating.
```

---

## Prompt 04 — Architecture review

```text
Audit the current repository against AGENTS.md, CONSTITUTION.md and
docs/ARCHITECTURE.md.

Do not modify code.

Look specifically for:
- PySide/GUI code containing domain or application logic;
- third-party library objects leaking across boundaries;
- absolute paths stored in user content;
- SQLite becoming authoritative;
- operators coupled directly to MainWindow;
- blocking work on the UI thread;
- hidden global state;
- destructive Markdown normalization;
- unnecessary dependencies;
- modules with multiple unrelated responsibilities.

Report findings by severity with file and symbol references.
Do not invent violations merely to produce findings.
```

---

## Prompt 05 — Bug investigation

```text
Investigate this bug: <BUG>.

Do not patch immediately.

1. Reproduce or identify the failing path.
2. State the root cause with evidence.
3. Identify the smallest safe fix.
4. Add or specify a regression test.
5. Check whether the root cause reveals an architectural violation.

Then implement only the justified fix and run the relevant tests.
Do not refactor unrelated code.
```

---

## Prompt 06 — Dependency evaluation

```text
Evaluate whether <LIBRARY> should be added for <RESPONSIBILITY>.

Do not install it yet.

Check:
- license compatibility with a fully open-source/free project;
- offline operation;
- maintenance/activity;
- Python/Qt/platform compatibility;
- package size/runtime impact;
- whether we already have a dependency serving the same role;
- whether it can be isolated behind an adapter;
- exit strategy if the library is abandoned.

Compare it with at least one credible alternative.
Conclude with a factual trade-off table, not enthusiasm.
```

---

## Prompt 07 — Markdown compatibility test

```text
Audit our Markdown editing/rendering behavior against
docs/MARKDOWN_COMPATIBILITY.md.

Build or update fixtures covering:
- CommonMark basics;
- GFM tables/tasks/strikethrough;
- fenced code;
- YAML frontmatter;
- inline/block math;
- Mermaid;
- wikilinks;
- callouts;
- images including SVG;
- raw HTML according to our security policy;
- an unknown fenced language/directive.

The critical invariant is that unsupported syntax is preserved in source.
Do not make the renderer rewrite the document.
```

---

## Prompt 08 — PDF operator work

```text
Work only on the PDF -> Markdown operator.

Read docs/OPERATORS.md and docs/PDF_OPERATOR.md first.

The editor/workspace core must not depend on the PDF engine.

Use representative fixtures and report conversion quality separately for:
- native text PDF;
- scanned PDF;
- mixed/hybrid PDF;
- multi-column academic paper;
- tables;
- formulas;
- embedded images.

Do not add multiple production engines unless evidence from the fixtures
shows the current adapter cannot satisfy an identified requirement.
```

---

## Prompt 09 — Pre-commit review

```text
Review the current diff as if you were rejecting unsafe code.

Check:
- scope;
- architecture boundaries;
- user-file safety;
- portability;
- error handling;
- cancellation for slow work;
- tests;
- documentation;
- license/dependency impact.

Then run the relevant test suite.

If everything is acceptable, propose a concise conventional commit message.
Do not commit until explicitly requested.
```

---

## Prompt 10 — Commit approved work

```text
Re-read the current diff and test results.
If the diff contains unrelated or unverified changes, stop and report them.

Otherwise commit only the approved work using a concise conventional commit
message that describes the actual change.

After the commit, show:
- commit hash;
- commit subject;
- clean/dirty working tree status.
```
