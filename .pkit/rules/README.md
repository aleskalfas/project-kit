---
variant: specialized
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/rules/core.md
        - .pkit/rule-sets/ops.md
        - .pkit/adapters/claude-code/merge-claude-md.sh
        - src/project_kit/install.py
        - src/project_kit/loaded_rule_sets.py
      record: [COR-001, COR-014, "COR-051#6", "COR-064#1", "COR-064#2", COR-068, ADR-075]
      artefact: [".pkit/schemas/README.md#rule-set-files"]
---

# Rules

Operational rules and tool hygiene patterns the kit ships for any project that adopts it. Every agent session loads two files: `core.md`, the kit's rules, and `project.md`, your project's own, which you own (COR-014).

## Layout

```
.pkit/rules/
├── README.md                             # this file
├── core.md                               # kit's universal hard rules + tool hygiene, generated
└── project.md                            # your project's own operational rules (adopter-owned)

.pkit/rule-sets/
├── README.md                             # the folder's signpost
└── ops.md                                # OPS, the set core.md is generated from
```

`core.md` is **kit-owned** (propagation per COR-001): refreshed on every sync, not editable by adopters. To extend the rules in your project, add them to `project.md` — sync never touches it — and your root `CLAUDE.md` includes both `@.pkit/rules/core.md` and `@.pkit/rules/project.md`, so kit and project rules compose naturally.

## Where the rules are kept

The kit's rules are a *loaded rule set*: a rule set whose accepted rules bind on the work of every session that loads the file generated from it ([COR-068](../decisions/core/COR-068-loaded-rule-sets.md)). Each rule has what a rule of any set has: a permanent id, a status, an origin, and a successor when it retires.

- **The set** is `OPS`, at `.pkit/rule-sets/ops.md`, shipped and synced with the backbone. Its front matter carries `loaded: true`, and each rule's status and origin. Each rule keeps the number it had: core rule 19 is `backbone:RS-OPS-019`, cited either way (the schemas README, "Rule-set files").
- **The loaded file** is `core.md`, where the include reads it. It holds the set's accepted rules under the set's sections, each headed `### N. Title (RS-OPS-0NN)` with its statement, and none of the set's data: no front matter, no origin, no retired rule.
- **It is generated.** `pkit rule-sets generate` writes `core.md` from `OPS` where the set is authored, in the methodology's source. A change to a rule regenerates the file in the same change, and `pkit validate` fails there on a `core.md` that differs from its set. In your project the two arrive together by sync. You neither generate nor edit `core.md`, and the command refuses to.
- **Citations of a rule** by layer and number, such as "core rule 19", or by id are read by `pkit validate`. One that names a missing, superseded or withdrawn rule is a warning (the CLI reference, `validate`).
- **A rule a project chooses to bind on its own files** goes in an ordinary rule set, not in a loaded one (COR-068 point 1). Core rule 24 has every session follow the rules such sets bind on what its change owns, as `pkit rule-sets altered` lists them.

## Converting your `project.md` into a loaded set

Your `project.md` is a plain file. It is loaded as it stands, and nothing checks its numbers or its origins, nor a citation such as "project rule 4" (COR-068 point 7). You may convert it into a loaded set of your own, when you choose:

1. Write the set as a rule-set file in `rule-sets/` under your internal documentation root (`docs/rule-sets/` by default). Give it a name of its own and `loaded: true`, and copy your rules into it, one section per rule, `### RS-<SET>-NNN — Title`, keeping each rule's number. The folder, its default and the form of a rule's heading are the schemas reference's, [Rule-set files](../schemas/README.md#rule-set-files).
2. Give each rule its origin: the record that decides it, or the decider's words (COR-051 point 5). Only you know who decided each rule and why, so no command or migration converts the file for you.
3. Run `pkit rule-sets generate`. It writes `.pkit/rules/project.md` from your set.
4. Run `pkit validate`. From then on it fails on a `project.md` out of step with your set, and reads each citation of your rules by "project rule N".

A project has one loaded set of its own, beside the kit's. It takes no scope, inheritance or extension point: its rules bind on sessions' work, not on files.

## What goes in `core.md`

Seven categories:

- **Hard rules** — invariants whose violation breaks the methodology. The no-shared-files invariant, the acceptance gate, paired-skill / `pkit new` for kit-shipped artifacts, migrations idempotency, etc.
- **Tool hygiene** — operational practices that keep work consistent. Pause for destructive ops, conventional commits, surface-change → version-bump, validate before assuming state, work with the permission layer, keep intermediate files in the agent workspace.
- **Communicating with the user** — one decision at a time, with a recommendation. Reference by meaning, then identifier.
- **Working across repositories** — a session mutates only its own repository's context.
- **Answers on artefacts** — a reviewer checks the answers your change owes, and a person, or the delegate they named, decides any other answer on an artefact.
- **When a step fails** — retry once a step that failed for a cause outside your own work, then stop and report.
- **Before changing files** — look up the accepted records their anchors lead to, and read those tied to them directly; before a choice later work will build on, draft the record that decides it, for a person to accept; and follow the rule sets' rules on what your change owns.

Each rule is terse — one statement plus a pointer to the COR / area README that owns the rationale, or, where none does, to the issue that decided the rule. The rules file is read by every agent at session start (via `CLAUDE.md`'s `@<path>` include); it is operational, not expository.

`core.md` itself follows core rule 13 (the `@`-include authoring convention): no top-level heading, opens with an italic preface, sections start at H2. The host `CLAUDE.md` owns the H1 and places the `@<path>` line after its intro paragraph, so the included sections become natural sub-sections of the host. This pattern applies to any future kit-shipped file intended for `@`-include.

## What does NOT go in `core.md`

- **Rationale.** That lives in the cited COR / PRJ / area README. A rule none of them holds cites the issue that decided it. The rules file points; it does not re-state.
- **Project-kit-internal mechanics.** Things like the project-kit's own version-bump policy (PRJ-002) belong in the project's own records and CLAUDE.md, not in the kit-shipped rules adopters receive. The rules file uses project-neutral phrasing — adopters never see project-kit-specific content there.
- **Adopter-specific rules.** Those go in the adopter's `project.md`.
