---
name: analysis-author
description: Author the software analysis — an actor, a glossary term, a use case, a journey, or a revalidation record — through `pkit analysis new`, choosing the slug, the area, the actor and the steps, what each artefact anchors to (code, decisions) or why an actor or term stays unanchored, and whether a revalidation leaves a record at all. Composite skill per COR-020, paired with `pkit analysis new`; one sub-procedure per kind. Use when adding to a project's analysis, or recording a revalidation that found something.
metadata:
  wraps_commands:
    - pkit analysis new
    - pkit analysis validate
    - pkit analysis check-numbers
composes:
  - actor.md
  - term.md
  - use-case.md
  - journey.md
  - revalidation-record.md
gates:
  - COR-005
  - COR-020
  - COR-049
  - COR-050
reads:
  records:
    - COR-008
  paths:
    - .pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md
    - .pkit/capabilities/software-analysis/README.md
    - .pkit/project/config.yaml
---

# Authoring the software analysis

This is the **software-analysis** capability's authoring skill. It covers the five things a project writes into its analysis — an actor, a glossary term, a use case, a journey, and a revalidation record — each stamped by `pkit analysis new`. The command owns the file's correctness: its id, its place, the anchors the rule asks for. This skill owns the choices behind it: which slug, which actor, which steps, what the artefact rests on, and whether a revalidation has anything to record (COR-005's skill and command pairing).

The rule is [software-analysis:DEC-001-software-analysis-discipline]; the layout, every field and every command are in `.pkit/capabilities/software-analysis/README.md`.

## Acceptance gate

Verify each record in `gates:` is `accepted`; halt if any is `proposed` or `superseded`.

- **COR-005** — skill and command pairing: every operation here writes through `pkit analysis new`, never by hand.
- **COR-020** — the composite folder form this skill follows.
- **COR-049** — documentation roots: the analysis lives under the internal root, and its location is recorded the first time something is stamped.
- **COR-050** — anchors and friction: the block every artefact carries, and the answers that clear friction.

## Pick the operation

| You want to | Sub-procedure | Command |
|---|---|---|
| Name a role that uses the system, and what it needs | `actor.md` | `pkit analysis new actor <slug>` |
| Pin down a domain word, or rename one | `term.md` | `pkit analysis new term <slug>` |
| Describe one actor's goal and how the system fulfils it | `use-case.md` | `pkit analysis new use-case <slug> --actor <ACT-id>` |
| Describe a path an actor takes across several use cases | `journey.md` | `pkit analysis new journey <slug> --actor <ACT-id> --step <UC-id> …` |
| Record a revalidation that found something, or was planned | `revalidation-record.md` | `pkit analysis new revalidation <slug> …` |

For a part of the product not yet described, go in that order: actors first (a use case names one), then use cases, then the journeys through them; terms whenever a word needs pinning down. Open the matching sub-procedure in this folder and follow it; the framing below applies to all of them.

Judging whether existing artefacts still hold after a change is the capability's `analysis-resolver` agent's work. This skill writes what it, or you, decided.

## Shared framing

### Stamp, never copy

The stamp gives a use case or journey the next free number — on the default branch and in the working tree — refuses an actor's or term's id already held, puts each artefact in its place, writes the anchors the rule asks for, adds a collection entry where its id sorts, and records the analysis location the first time. A copied template gets none of that right. The body keeps the template's `<…>` placeholders for you to fill.

### Choosing the slug

A slug is a word: a lowercase letter, then lowercase letters, digits and hyphens.

- **An actor's or term's slug is its id for ever** (`ACT-<slug>`, `TERM-<slug>`), and an id is never used again, even after it is withdrawn. Name the role or the word as the domain says it, in the singular: `tester`, `release-manager`, `sandbox`. The display name (`--name`) may change later; the slug may not.
- **A use case's or journey's number is its id**; the slug only names the file. Name the goal, verb first: `run-suite`, `export-report`, `first-run`.

### What an artefact anchors to

An anchor says *if this changes, check me*. Anchor what makes the artefact true, and nothing broader:

- **`--path <glob>`** — the code that embodies it: the entry point and the files that do the behaviour, not a whole tree. An anchor matching more than half the tracked files is reported as over-broad, because it would make every change a revalidation.
- **`--record <id>`** — a decision it relies on: an architecture decision, a capability's decision, a project record.
- **Artefact anchors are the stamp's.** A use case anchors to its actor, and a journey to the use cases of its steps, so a changed actor flags its use cases and a changed use case the journeys through it. Never write them by hand.

**Quote the code you describe.** When a use case's step names a command, a flag, a function or a message, write it in backticks. What an artefact quotes from the code it anchors to is how a revalidation tells a change that leaves the description true from one that removes what it says — the resolver agent's first reading of a flagged artefact rests on it.

The code the analysis ought to cover is the project's to declare, as the declared surface in the friction key of `.pkit/project/config.yaml`; what no artefact anchors to there is reported as uncovered surface.

### An actor or term nothing embodies

An actor or term that no code and no decision embodies — a sponsor, an outside regulator, a word of the business the software never names — is stamped with `--unanchored-because "<why nothing embodies it>"` instead of anchors: the stamp writes it as `unanchored-because` in the artefact's friction block, the core's key. An unanchored artefact is reported as a measure and never fails a check; the reason is what onboarding accepts, and the core's measure lists the artefact apart with it rather than counting it (`pkit friction check --all`). A use case or a journey is never unanchored: it always rests on its actor, or its steps.

### After stamping

1. **Fill the body** — every `<…>` placeholder, and an actor's `needs` or a term's `definition`.
2. **Check it** — `pkit analysis validate`, the capability's check (it runs inside `pkit validate` too), then `pkit friction check`, the core's change check: an artefact new in a change counts as revalidated, and an anchor that resolves to nothing fails.
3. **Before merging a use case or journey** — `pkit analysis check-numbers`: a number the default branch gave another file since your branch left it is renumbered, and the stamp gives the next free one.
4. **Commit** per COR-008, one artefact or one revalidation per commit where you can.

### Withdrawing, never deleting

An artefact is withdrawn, never deleted: set its `status` to `withdrawn` and keep the file or the entry, so that records and journeys citing it still resolve. Its id is never used again. An artefact in force never rests on a withdrawn one — withdraw or re-point the use cases of an actor before withdrawing the actor, or the check refuses them.
