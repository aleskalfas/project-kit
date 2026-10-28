---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-28
---

# Which operational rules reach which session

## The question

Every session, helpers included, loads every operational rule (`.pkit/rules/core.md` and the project's `project.md`, through the `CLAUDE.md` includes). Not every session needs every rule. Can a rule reach only the sessions that need it, while each rule is still written once, in one place, with one path for future rules?

Deferred on 28 October: the rules get permanent numbers (#2260), are trimmed (#2261) and held to a size budget (#2262) first. This note keeps what was learned for when slicing is taken up again.

## Forces

- COR-065: decisions are the source and the system their projection; the rules are the projection of the decisions into every session (point 7: records are read to change the system, not loaded to run it).
- The file grows: 13 rules and 925 words in June, 22 rules and about 2 500 words on 27 October. But eight of the nine rules added since June are ones every session needs; growth is in the floor, which a budget controls better than slicing.
- One place to write each rule, one path for a new one (the maintainer): rules folded into skills scatter where rules are written.
- Rules are where enforcement starts; a rule that does not reach a session fails silently, and the agent cannot miss what it was never shown.

## Lines tried and why each fell

- **Fold work rules into the skills that do the work.** Scatters where rules are written; a rule held in a skill binds only while the skill runs. Rejected by the maintainer.
- **Tag rules with the permission model's privileges; an agent gets the rules of the privileges it holds.** The coupling is real: a grant decides whether a call may run without asking, is chosen per project and machine and checked per call, while a rule's audience is chosen by its author. Traced over 26 rules, a privilege picked the right audience for about 3. Steering rules point the other way (they are for agents that lack a grant). It fails toward fewer rules where no profile is active.
- **Per-agent slices projected into each agent's deployed body.** The main session, where commits, migrations and records happen, and seat workers, which are main sessions, load `CLAUDE.md` whole, as do most helpers; slicing for helpers misses where the work is.
- **Scope rules by the files they govern, delivered as Claude Code path-scoped rules (`.claude/rules/` with `paths:`).** A critic found: a scoped rule loads only on a Read or Edit of a matching file, so where the violating act is the first touch (creating a file, `git mv`, `rm`, a commit, a `pkit` writer) the rule arrives late or never; it does not reach confined runs (`--setting-sources ""`), helpers in their own worktree, sessions after compaction (scoped rules reload only on demand), or the reviewers, which read diffs through the shell; nothing notices a rule that did not load; making `core.md` the floor makes every other consumer of it fail toward fewer rules.

## What would make slicing sound, if it is taken up

- **A test for scoping a rule:** the act that breaks it is always preceded, in the same session, by a read of a matching file, and a deterministic check catches it if the rule never loaded. Otherwise the rule stays in the floor, or its sentence goes into the output of the command that runs at the moment it binds (`migrations check-diff`, `friction check`, `pkit new`).
- **Delivery by lookup, not only by the harness:** the lookup rule 22 already runs (`pkit refs records-for` over the files a change will commit), or a sibling `pkit rules for <paths>`, lists the scoped rules too; reviewers run it on the diff's paths; the agent resolver appends them to confined runs. Path-scoped harness files become an extra.
- **`core.md` keeps the full set,** and the floor is a generated include, so any consumer that reads `core.md` fails toward more rules.
- **One scheme with COR-051,** whose rule sets already have permanent ids and path scopes, or a stated reason for a second.
- **Notice a rule that did not load:** an `InstructionsLoaded` hook logging loads, or a diff-time listing of the scoped rules a change's paths match.

## Open questions

- Does slicing pay for itself once the rules are trimmed and budgeted?
- Do capabilities get operational rules of their own, and how are they namespaced?
- In project-kit itself nearly every session touches `.pkit/**`, `src/` or `tests/`; rules 1 and 4 forbid editing what is the work here. Does the methodology's own repository need its own floor?
