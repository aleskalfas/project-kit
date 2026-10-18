# Adding a use case

A use case is one actor's goal and how the system fulfils it. It is a file, `UC-NNN-<slug>.md`, numbered within the project whatever area it sits in.

## 1. One actor, one goal

Two actors with the same goal are two use cases, or the goal belongs to a third actor they both are. A goal that takes the actor through several use cases, with seams between them, is a journey over those use cases — write the use cases first.

## 2. Name the actor, and the other actors

The actor must be in the analysis and in force; stamp it first (`actor.md`) if it is not. The stamp refuses an actor that is missing or withdrawn.

Name each other actor who takes part with `--other-actor <ACT-id>`: one the use case serves, informs or must protect, never its own actor. Each is written in `other-actors` and anchored, so a change to that actor flags the use case. Each must be in the analysis and in force too.

## 3. Choose the slug, the title and the area

- **Slug** — the goal, verb first: `run-suite`, `export-report`. It names the file only.
- **`--title`** — the goal as the heading reads it: `Export the report as a file`. The heading is `# UC-NNN — <title>`, and the check keeps the two in step.
- **`--area <word>`** — a folder per functional area, when the project groups use cases. Moving a use case to another area later never changes its id; a move renames the file, so revalidate it in the same change (COR-050 point 3).

## 4. Decide what it rests on

- **`--path`** — the code the use case exercises: the entry point and the files doing the behaviour its steps describe. Also the file of each architecture view that realises it, where the project keeps one. Where a place holds the view, write an artefact anchor on it instead.
- **`--record`** — the records it rests on, and the records that answer it. Those are each record whose decision the use case rests on, and each record made to meet what it asks. That may be a project record, an architecture record, or a record a component ships.
- **Only from the use case.** Records carry no drivers: no record anchors the use case it answers, or any other analysis artefact. What a record serves is worked out from the analysis's anchors, and never stored (DEC-001 point 11).

The anchor to each actor is written by the stamp.

## 5. Stamp it

```
pkit analysis new use-case <slug> --actor <ACT-id> [--other-actor <ACT-id>]... [--title "<Title>"] [--area <area>] [--path <glob>]... [--record <id>]...
```

It takes the next free number on the default branch and in the working tree.

## 6. Fill it

Each part holds its hint, which says what goes there and gives an example. Fill each part as its hint says, and delete the hint. Where a step names a command, a flag, a function or a message, quote it in backticks (the shared framing's "Quote the code you describe"). The goal and each minimal guarantee name their source (the shared framing's "Name the source of what the system must do").

Then run the checks in the shared framing's "After stamping", `pkit analysis validate --preview` first, and `pkit analysis check-numbers` before merging.

## Later

Steps and variants are **only ever added**, never renumbered or removed: journeys and evidence cite a step by its number, and a variant by its step's number and its letter.

- **A new step** takes a number higher than every number of its use case, even when it goes between two steps. The path keeps its order, and no number moves.
- **A new variant** takes a letter after every letter of its step.
- **A step that no longer happens** stays in place, under its number. A variant does the same, under its letter.
- **The check.** `pkit analysis check-numbers` compares each use case with the same use case where your branch left its base, the default branch unless you name another, and fails on a step or a variant renumbered or removed. It fails only where the append-only rule, `RS-SAN-002`, is accepted and binds. While that rule is proposed, run it with `--preview`: it reports what it would fail, and never fails.

A use case no actor pursues any more is withdrawn, never deleted.
