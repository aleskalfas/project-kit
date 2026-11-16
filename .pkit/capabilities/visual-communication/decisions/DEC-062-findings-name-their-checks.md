---
id: DEC-062
title: A findings record names the checks a reader relies on having run
status: proposed
date: 2026-11-16
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a piece's findings record keeps what its last render found, and a record written by an older release still counts as the piece's findings until the piece is rendered again. So when a release adds a check, a record written before it holds none of its findings, and reads exactly like a record whose render ran the check and found nothing. Where a reader does something else when a check did not run, that difference matters. The record now names each such check that ran. A record that does not name a check does not tell whether it ran, and is never read as "ran, found nothing".

## Context

[visual-communication:DEC-046-faults-lower-grades] point 3 adds two checks that measure the boxes of siblings: edges that nearly line up, and boxes that overlap. It decides that where they ran, the reviewer does no sums over the frames, and where they did not, it reads the offsets from the frames. The reviewer learns what the checks found from the findings record.

The words it uses:
- **The findings record** is the file each render of a piece that is not final keeps beside the piece: the key, a fingerprint of every file its scenes were computed from, and what computing them found ([visual-communication:DEC-005-engine-and-plugins] point 13).
- **A check** is a measurement a command makes on every render, with no judgement ([visual-communication:DEC-002-files-and-validation] point 7). Its *label* is the name its findings carry.
- **The reviewer** is the capability's agent that reads the images of a piece's pages and reports ([visual-communication:DEC-015-viewing-step-and-reviewer]).

The key holds no version of the engine, so a record written by an older release still verifies, and the check reads its findings until a person renders the piece again (DEC-005 point 13). That is right for the check: a new release reaches a piece only at a render a person runs. But it leaves the record silent on which checks ran. A record written before the checks of boxes verifies, holds no finding of theirs, and reads as one written after them that found nothing. A reviewer that read it so would skip the sums that no check made.

## Decision

### 1. The record names each check a reader relies on having run

- **What it names.** The findings record may hold `checks`: the label of each check that the render that wrote it ran, among the checks a reader relies on having run, each once, in the order of their labels.
- **A check a reader relies on having run** is one whose running changes what a reader of the record does, beyond reading the findings it holds. The checks of boxes are such checks, `near-alignment` and `box-overlap`, since the reviewer does its own sums over the frames where they did not run (DEC-046 point 3). A check whose findings are all that a reader acts on is not one.
- **Who writes it.** Each command that writes the record names every such check it ran. A check that did not run for some reason a render can have is not named, so the field never says more than ran.
- **A new check of this kind** joins the field in the change that adds it, and the page that lists the checks says which checks the field may name.

### 2. A record that does not name a check does not tell whether it ran

- **A check the field does not name,** in a record that holds the field or in one without it, is read as not known to have run. Nothing is known of what it would have found, and it is never read as having run and found nothing.
- **So a reader that relies on a check measures for itself** where the record does not name it, as the reviewer reads the offsets from the frames where the checks of boxes did not run (DEC-046 point 3).
- **The check reads the field for nothing.** A record that verifies stays the check's findings for its piece, field or none, as DEC-005 point 13 decides.

### 3. The field is an addition

- **The format number stays as it is.** The field is optional, and a record without it is read, so it is an addition ([visual-communication:DEC-003-change-over-time] point 1).
- **The key does not take it.** The key fingerprints the files the scenes were computed from. The field says what the engine ran on them. Putting the engine's version, or the checks, into the key would make every record stale at each release, which DEC-005 point 13 rules out.

## Rationale

The reviewer must tell a check that found nothing from a check that never ran, and the record is all it reads of the checks. Naming the checks that ran says it in the record itself, and a record without the field already means what point 2 reads it as: it was written before any check the field names.

The field names only the checks a reader relies on having run. Every check added in a release is missing from records written before it, but only where a reader acts otherwise when the check did not run does a missing finding mislead. Naming every check would make the field a list of the engine's checks, and bind every change that adds one to it, with no reader who needs it.

### Alternatives considered

- **A finding that says the checks ran.** One fact on every piece, saying that the checks of boxes ran. It adds no field, but it is no finding: it reports nothing about the piece, and `pkit validate` would print it on every piece at every run. It would also blur what a finding is, something a check found.
- **The engine's version in the record.** A reader would have to know which release brought which check, which no file it reads says. Naming the checks says it directly.
- **The engine's version in the key.** Every record would stop verifying at each release, and the check would compute every piece's scenes again. That is what DEC-005 point 13 decides against.
- **The reviewer measures every time.** It would do the sums the checks make, so the checks would spare it nothing. DEC-046 point 3 decides that it does not where they ran.

## Implications

- **The findings record's schema** takes `checks`, optional: a list of labels, each once.
- **The commands that write the record,** `pkit visual render` and `pkit visual upgrade`, write `near-alignment` and `box-overlap` in it, from the release that ships the checks of boxes.
- **The capability's list of checks** (`checks.md`) lists the field under "The findings record", says which checks it may name, and says how a record that does not name one reads.
- **The reviewer's body** reads the field where it reads the findings of the checks of boxes, in the change that teaches it those findings: where the field names both, it does no sums over the frames; elsewhere it reads the offsets from them.
- **No accepted record is edited.** DEC-005 point 13 names what the record is for and how its key is made, and lists no fields, so the field adds to it and changes nothing it decides.
