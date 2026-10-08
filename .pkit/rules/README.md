---
variant: specialized
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/rules/core.md
        - .pkit/adapters/claude-code/merge-claude-md.sh
        - src/project_kit/install.py
      record: [COR-001, COR-014]
    revalidated:
      at: 2026-10-08T08:34:57Z
      outcome: unchanged
      unchanged-because: the change rewrites only the install advice in init's closing next steps; how init places core.md and project.md, which this page describes, is untouched
---

# Rules

Operational rules and tool hygiene patterns the kit ships for any project that adopts it. The kit-shipped content is the single file `core.md`; an adopter's own operational rules live beside it in `project.md`, which the adopter owns (COR-014).

## Layout

```
.pkit/rules/
├── README.md                             # this file
├── core.md                               # kit's universal hard rules + tool hygiene
└── project.md                            # your project's own operational rules (adopter-owned)
```

`core.md` is **kit-owned** (propagation per COR-001): refreshed on every sync, not editable by adopters. To extend the rules in your project, add them to `project.md` — sync never touches it — and your root `CLAUDE.md` includes both `@.pkit/rules/core.md` and `@.pkit/rules/project.md`, so kit and project rules compose naturally.

## What goes in `core.md`

Five categories:

- **Hard rules** — invariants whose violation breaks the methodology. The no-shared-files invariant, the acceptance gate, paired-skill / `pkit new` for kit-shipped artifacts, migrations idempotency, etc.
- **Tool hygiene** — operational practices that keep work consistent. Pause for destructive ops, conventional commits, surface-change → version-bump, validate before assuming state, work with the permission layer, keep intermediate files in the agent workspace.
- **Communicating with the user** — one decision at a time; reference by meaning, then identifier.
- **Working across repositories** — a session mutates only its own repository's context.
- **Answers on artefacts** — an answer you write on an artefact is a person's decision: show it to them word for word.

Each rule is terse — one statement plus a pointer to the COR / area README that owns the rationale. The rules file is read by every agent at session start (via `CLAUDE.md`'s `@<path>` include); it is operational, not expository.

`core.md` itself follows rule 13 (the `@`-include authoring convention): no top-level heading, opens with an italic preface, sections start at H2. The host `CLAUDE.md` owns the H1 and places the `@<path>` line after its intro paragraph, so the included sections become natural sub-sections of the host. This pattern applies to any future kit-shipped file intended for `@`-include.

## What does NOT go in `core.md`

- **Rationale.** That lives in the cited COR / PRJ / area README. The rules file points; it does not re-state.
- **Project-kit-internal mechanics.** Things like the project-kit's own version-bump policy (PRJ-002) belong in the project's own records and CLAUDE.md, not in the kit-shipped rules adopters receive. The rules file uses project-neutral phrasing — adopters never see project-kit-specific content there.
- **Adopter-specific rules.** Those go in the adopter's `project.md`.
