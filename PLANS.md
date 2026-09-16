# Execution Plans

Use an execution plan for:

- new subsystems;
- significant refactors;
- cross-layer features;
- dependency replacements;
- persistent data/index changes;
- background job infrastructure;
- editor/preview bridge changes;
- workspace indexing;
- graph engine work;
- PDF conversion pipeline changes.

A trivial local bug fix does not require a formal plan unless risk is high.

## Required plan structure

Create plans under:

```text
harness/
└── plans/
    └── phase-NN-short-name.md
```

Each plan must be self-contained.

### 1. Objective

What observable user or system behavior will exist when the phase is complete?

### 2. Existing state

Name the relevant current modules and behavior.
Do not assume the reader remembers prior sessions.

### 3. Constraints

List applicable constitutional and architectural constraints.

### 4. Risks and unknowns

Separate:

- confirmed facts;
- implementation inferences;
- unresolved hypotheses.

If a library choice is uncertain, require a spike instead of silently committing to it.

### 5. Proposed design

Describe responsibilities and dependency direction.

Name interfaces/ports before concrete adapters when the dependency is replaceable.

### 6. Files expected to change

List planned creation/modification points.
This list is a forecast, not permission to edit unrelated files.

### 7. Implementation phases

Use small phases with independently verifiable results.

For each phase define:

- change;
- validation;
- expected result.

### 8. Tests

Specify:

- unit tests;
- integration tests;
- fixtures/golden tests;
- manual UI check only where UI behavior itself is under test.

### 9. Data safety

If user files can change, explain rollback/backup/dry-run behavior.

### 10. Completion evidence

Record commands run and relevant outcomes.

Do not claim tests passed unless they were executed.

## Context record

For material phases, write:

```text
harness/context/phase-NN-short-name-context.md
```

Record only decisions or evidence that a later session would otherwise need to rediscover.
