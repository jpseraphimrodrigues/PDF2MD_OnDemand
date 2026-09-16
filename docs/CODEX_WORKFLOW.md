# Codex Development Workflow

## 1. Purpose

Use Codex as an implementation agent under persistent repository constraints.

Do not rely on chat history as the architectural source of truth.

The repository documents are the durable context.

## 2. Persistent instruction hierarchy

The root `AGENTS.md` contains repository-wide coding-agent instructions.

Topic documents provide product and architecture details.

For subcomponents that later need special rules, a deeper `AGENTS.md` may be added to that directory.

## 3. Session start

For a fresh Codex session, use `PROMPTS.md` Prompt 01 or an equivalent instruction.

The agent should establish repository state before changing code.

## 4. Feature workflow

Preferred sequence:

```text
Intent
  ↓
Spec/acceptance criteria
  ↓
Execution plan
  ↓
Small implementation phases
  ↓
Tests/evidence
  ↓
Review
  ↓
Commit
```

Do not jump from "idea" directly to a large patch.

## 5. Spec Kit

Spec Kit may be introduced to formalize spec-driven development.

If adopted, preserve the same constitution and project constraints rather than creating a competing rule set.

A suitable initial workflow is:

```text
constitution
-> specify
-> clarify when needed
-> plan
-> checklist when useful
-> tasks
-> analyze
-> implement
-> converge
```

The exact Codex invocation syntax depends on the installed Spec Kit integration/version.

## 6. Chat decisions

When a design decision is made outside the repository and affects future implementation:

- update the relevant permanent `.md`;
- add a concise entry to `docs/DECISIONS.md` if it changes architecture/product policy.

Do not expect a later agent session to remember an earlier chat.

## 7. Scope control

Each Codex task should have one principal objective.

Bad:

```text
Build editor, vault, graph, PDF converter and AI.
```

Better:

```text
Implement Phase 1 standalone Markdown open/edit/save path according to
harness/plans/phase-01-standalone-markdown.md.
```

## 8. Evidence

Codex must distinguish:

- code inspected;
- tests actually run;
- assumptions;
- unresolved items.

"Should work" is not completion evidence.

## 9. Commits

Prefer small coherent commits aligned to a verified phase.

Do not let the agent automatically sweep unrelated working-tree changes into a commit.

## 10. Architecture drift

Periodically run the architecture-review prompt from `PROMPTS.md`.

This is particularly important after:

- GUI expansion;
- new operators;
- indexing work;
- AI integration;
- major dependency changes.
