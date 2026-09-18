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

---

## CODEX ORCHESTRATION POLICY - COST CONTROL

The project must optimize Codex usage aggressively.

### Default model policy

Use GPT-5.6 Luna with low reasoning by default.

Do not automatically escalate to Terra, Sol, Astra, or higher reasoning effort.

Model escalation requires explicit user instruction.

### Subagent policy

Subagents are optional tools, not mandatory workflow stages.

Default workflow:

1. Main agent understands the requested change.
2. If the relevant code location is unknown, spawn ONE `pdf2md_explorer`.
3. Reuse the explorer findings instead of rediscovering the repository.
4. Spawn ONE `pdf2md_worker` for the narrowly scoped implementation.
5. Validate with deterministic tests.
6. Use `pdf2md_reviewer` only when the change is non-trivial or risky.

Do not spawn agents merely because delegation is available.

### Parallelism

Use at most one subagent at a time.

Do not create parallel workers.

Do not allow subagents to create nested subagents.

### Context economy

Prefer:

- rg/search;
- targeted file reads;
- git diff;
- focused tests;
- existing documentation;

over broad repository scans.

Do not ask each agent to rediscover the same project context.

Do not repeatedly read the entire repository.

### Review economy

For normal changes, review the diff and directly affected tests.

Do not perform a full-project review unless a concrete architectural
or regression risk requires it.

### Testing economy

Prefer, in this order:

1. specific test;
2. affected module tests;
3. related test group;
4. full suite only when justified.

Do not use another reasoning agent when a deterministic test can answer
the question more reliably.

### Current scope restriction

Unless explicitly requested by the user, do not work on the internal
PDF-to-Markdown conversion engine.

Work may continue on:

- application architecture;
- editor;
- preview;
- project lifecycle;
- persistence;
- UI;
- security;
- tests;
- infrastructure;
- integration boundaries.



---

## AUTONOMOUS SEQUENTIAL DEVELOPMENT MODE

When the user asks to continue a phase, milestone, or implementation plan,
operate autonomously and sequentially until the requested scope is complete
or a defined stop condition occurs.

Do NOT ask for user confirmation between normal implementation steps.

### Source of truth

Use the relevant file under `harness/plans/` as the authoritative execution plan.

Use the corresponding files under `harness/context/` for accumulated
technical context.

Do not invent a new roadmap when an existing phase plan already exists.

### Sequential execution loop

Repeat the following process until the phase or requested milestone is complete:

1. Read the current phase plan and relevant context.
2. Identify the next incomplete deliverable.
3. Determine whether code location is already known.
4. If necessary, use exactly one `pdf2md_explorer`.
5. Define a narrow implementation task.
6. Use exactly one `pdf2md_worker`.
7. Run the smallest relevant deterministic tests.
8. If tests fail:
   - diagnose the failure;
   - attempt a targeted correction;
   - rerun the affected tests.
9. For non-trivial or risky changes, use one `pdf2md_reviewer`.
10. Fix blocking reviewer findings.
11. Run the appropriate validation:
    - pytest;
    - Ruff;
    - mypy;
    as relevant to the changed code.
12. Update the phase plan with completed work.
13. Update the phase context with decisions, behavior and residual risks.
14. Inspect `git diff`.
15. Create a Git checkpoint commit for the completed logical unit.
16. Continue automatically with the next incomplete deliverable.

Do not stop merely to report that one intermediate step is complete.

### Git policy

After each coherent and verified implementation unit:

- inspect the diff;
- ensure tests relevant to the unit pass;
- create a descriptive commit;
- continue to the next unit.

Do NOT push automatically.

Do NOT rewrite or amend previous commits unless explicitly instructed.

Do NOT commit failing code.

### Stop conditions

Stop autonomous execution and ask the user only when one of these occurs:

1. A decision would materially change documented architecture.
2. Two reasonable architectural alternatives exist and the existing
   documentation does not resolve the choice.
3. A new production dependency is required.
4. Existing user data or files may be destructively migrated.
5. A destructive Git operation would be required.
6. Required credentials, secrets or external access are unavailable.
7. Tests continue failing after two focused correction attempts.
8. The requested phase or milestone is complete.
9. Work would enter the PDF -> Markdown conversion engine, unless the user
   explicitly included that engine in the requested scope.

Ordinary implementation choices are NOT stop conditions.

### Scope discipline

Do not expand the phase with optional features.

Do not implement future-phase functionality early merely because it is nearby.

Do not refactor unrelated working code.

Prefer finishing one vertical slice before starting another.

### Reporting

During autonomous execution, keep intermediate messages concise.

At completion or a stop condition, report:

- deliverables completed;
- commits created;
- tests and static checks executed;
- remaining incomplete items;
- residual risks;
- exact reason for stopping, if blocked.

---

## GIT CHECKPOINT OVERRIDE FOR SANDBOXED CODEX

The Codex sandbox may prevent writes inside `.git`.

This must NOT block autonomous phase execution.

When Git metadata is read-only:

1. Do NOT attempt to change filesystem permissions.
2. Do NOT modify ACLs.
3. Do NOT use destructive Git operations.
4. Do NOT stop merely because `git add` or `git commit` cannot run.
5. Continue implementing the remaining phase deliverables sequentially.
6. After each logical unit:
   - run the relevant tests;
   - inspect `git diff`;
   - update the phase plan;
   - update the phase context;
   - record the intended checkpoint commit message in the plan/context.
7. Leave all repository changes in the working tree.
8. The human user will create the Git commits outside the Codex sandbox.

Failure to create `.git/index.lock` is NOT a stop condition.

Only stop for the architectural or technical stop conditions defined elsewhere
in this AGENTS.md, or when the requested phase is complete.
