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
- **`--area <word>`** — a folder per functional area, when the project groups use cases. Moving a use case to another area later never changes its id; a move renames the file, so revalidate it in the same change (COR-050 point 3). The word may open with a number and a hyphen, such as `010-develop`. The number gives one valid order in which the areas build on each other, and is no part of the id (DEC-001 point 2).

## 4. Decide what it rests on

- **`--path`** — the code the use case exercises: the entry point and the files doing the behaviour its steps describe. Also the file of each architecture view that realises it, where the project keeps one. Where a place holds the view, write an artefact anchor on it instead.
- **`--record`** — the records it rests on, and the records that answer it. Those are each record whose decision the use case rests on, and each record made to meet what it asks. That may be a project record, an architecture record, or a record a component ships.
- **Only from the use case.** Records carry no drivers: no record anchors the use case it answers, or any other analysis artefact. What a record serves is worked out from the analysis's anchors, and never stored (DEC-001 point 11).
- **`--requirement`** — each requirement the use case must meet, of any of the three kinds, once for each: a quality it must reach, a rule that holds across use cases, a limit it works within. Each must be in the analysis and in force. Stamp a missing one first (`requirement.md`). The stamp writes each in `requirements`, and anchors it. So a changed requirement flags the use case (DEC-002 point 7).
  - **List it here, never on the requirement.** A requirement names no use case. What meets it is worked out from the lists, and `pkit analysis met-by` shows it.
  - **The cost.** Any change to a requirement's content flags each use case that lists it, a reworded reason included. So list a requirement the use case must meet, not one it only touches.

The anchor to each actor and to each requirement is written by the stamp.

## 5. Stamp it

```
pkit analysis new use-case <slug> --actor <ACT-id> [--other-actor <ACT-id>]... [--requirement <REQ-id>]... [--title "<Title>"] [--area <area>] [--path <glob>]... [--record <id>]...
```

It takes the next free number on the default branch and in the working tree.

## 6. Fill it

Each part holds its hint, which says what goes there and gives an example. Fill each part as its hint says, and delete the hint. Where a step names a command, a flag, a function or a message, quote it in backticks (the shared framing's "Quote the code you describe"). The goal and each minimal guarantee name their source (the shared framing's "Name the source of what the system must do"). Write each concept by its term (the shared framing's "Use the glossary's terms").

**Preconditions.** Open each line with its producers, the use cases in force that make it true, such as `**From UC-003:**` or `**From UC-059, or Environment:**`. What the environment gives alone is an assumption, written in *Assumptions* only. A use case that needs no other one reads `None.` there. You may also list the producers in the front matter as `after`, one entry for each line, in its order, such as `after: [[UC-003], [UC-059, environment]]` (DEC-001 point 1). `after` draws no anchor. Where `RS-SAN-009` binds, the check holds it to the analysis, the words and the areas' numbers. `pkit analysis diagram chain` draws it.

## 7. Show what the system does not do yet

Write each step and variant as the accepted records decide it (DEC-001 point 1). Where the system does not carry one out yet, keep it and add a box below it. Only an accepted record grounds such a step. Without one, write the step as the code does it. A proposed record decides nothing yet: accept it first, or leave the step out.

1. **Find the record and the issue.** Name the accepted record that decides the behaviour, and its point where it has one. Name the issue that tracks building it. Where no issue tracks it, file one first.
2. **Anchor the record.** It is among the use case's record anchors, written as the entry writes it, with its point where it names one. So a change to the record flags the use case.
3. **Write the box.** Put it right below the item of the step or variant, at the top level of *Main path* or *Variants*, with a blank line above and below it. Never indent it into the item, so the step's words stay as journeys and evidence cite them. Say what the system does not do yet, then name the record and the issue.
4. **List it in `shortfalls`.** One entry for each box: its step or variant, `at`, its issue in one word, and its record. Quote an issue that opens with `#`, since YAML reads the rest of the line as a comment. A variant's `at` is its number and letter, such as `"2a"`. A step may carry several boxes, one for each entry.

A box below step 2, its record an architecture record's point 2:

```markdown
**Main path:**

1. The analyst chooses `Export`.
2. The system writes the report to a file, and signs it.

> [!WARNING]
> **Not built yet:** the system writes the file unsigned. ADR-006 point 2 decides
> that each export is signed, and #12 tracks it.

3. The system says where the file is.
```

Its entry, with the record among the use case's record anchors:

```yaml
shortfalls:
  - at: 2
    issue: "#12"
    record: ADR-006#2
pkit:
  friction:
    anchors:
      record: [ADR-006#2]
```

The check holds each box to an entry and each entry to a box, whatever any rule's status. Each entry's record must be one of the use case's record anchors, and accepted. The overview lists every entry under "Not built yet".

- **A regression.** A step the system no longer carries out keeps its words (DEC-001 point 5). Where an accepted record decides it, add its box, naming the defect's issue, and record the revalidation as `updated`. Any other regressed step takes no box.
- **Closing one.** The change that builds the behaviour removes the box and its entry, in the pull request that closes the issue.

Then run the checks in the shared framing's "After stamping", `pkit analysis validate --preview` first, and `pkit analysis check-numbers` before merging.

## Later

Steps and variants are **only ever added**, never renumbered or removed: journeys and evidence cite a step by its number, and a variant by its step's number and its letter.

- **A new step** takes a number higher than every number of its use case, even when it goes between two steps. The path keeps its order, and no number moves.
- **A new variant** takes a letter after every letter of its step.
- **A step that no longer happens** stays in place, under its number. A variant does the same, under its letter.
- **The check.** `pkit analysis check-numbers` compares each use case with the same use case where your branch left its base, the default branch unless you name another, and fails on a step or a variant renumbered or removed. It fails only where the append-only rule, `RS-SAN-002`, is accepted and binds. While that rule is proposed, run it with `--preview`: it reports what it would fail, and never fails.

`requirements` is the source of the use case's requirement anchors. To change it, edit it and those anchors together. The check names the anchors to write when they differ. A use case in force never lists a withdrawn requirement. So the change that withdraws one takes it off each list, with its anchor.

A use case no actor pursues any more is withdrawn, never deleted.
