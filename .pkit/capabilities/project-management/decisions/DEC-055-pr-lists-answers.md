---
id: DEC-055
title: A pull request lists the answers its change wrote
status: proposed
date: 2026-10-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

An agent building a change may give the answers its own change owes — the revalidations and deferrals the change check asks of it — without asking anyone first. Those answers become a person's decision only when the person who authorises the merge is shown every one of them, word for word, from the change check's own list, and then authorises it; an authorisation given before the list was shown accepts none of them (COR-050 point 3). The change check gives that list in its machine-readable output (COR-050 point 12).

This capability is where a pull request's merge is authorised: the person reads the pull request's description, and `land-work` stops on a `ready:` line whose command they authorise. If nothing puts the list there, the rule rests on an agent copying it by hand, and an authorisation given after the list was shown looks the same as one given before.

## Decision

**A pull request's description carries the change check's list of the answers its change wrote, written by this capability and never by an agent, and `land-work` merges such a change on a `--yes` only when the list for the head it merges was already in the description.**

1. **The list.** This capability writes the answers a change wrote into the pull request's description, in a section of its own, `## Friction answers`, between its markers. The list is the change check's own list of the answers the change wrote, derived at the pull request's head against where that head left its base. Each entry gives the artefact, the answer, and the justification or reason word for word; it marks an answer the check did not ask for, one the diff does not bear out, one edited without a revalidation, and each deferral a revalidation kept. The section is replaced whole whenever it is written and is never composed by an agent. A change that wrote no answers has no such section.
2. **Who writes it.** `open-pr` writes it when the pull request is opened; `edit-pr` carries it across every edit of the body; `land-work` re-derives it before the merge.
3. **The authorisation.** `land-work` prints every answer above its `ready:` line. Where the change wrote answers, a run given `--yes` merges only if it names the head and found the list for that head already in the description; one that had to write the list merges nothing and stops ready. At a terminal without `--yes`, the merge prompt follows the printed answers.
4. **Never input.** No reader of the description treats the section as input: not the closing references, not the mapping's override, not the placeholder check, not the Doc impact requirement. Nothing in the section closes an issue. The squash commit carries it as it carries the rest of the description.
5. **What this does not verify.** That a person read the list. `land-work` holds that a `--yes` run merged only a head whose list was already in the description, and did not write it itself. `done-work` and `merge-pr` run directly are not held: after a fix round the description may carry the list of an earlier head, or none. A merge made outside these commands is not held either.

## Rationale

**Why the description.** It is what the person reads before authorising the merge, and the squash commit carries it, so the answers that landed stay beside the change in the default branch's history.

**Why the capability writes it from the check.** What the person is shown must be the check's list, never an account the agent composed (COR-050 point 3). A section derived from the check's document at the pull request's head, and replaced whole on every write, cannot drift from the artefacts and keeps no entry of an earlier head.

**Why `land-work` derives it again.** The head that merges is often not the head the pull request was opened at: a fix round rewrites answers and adds others. Deriving at the head `land-work` pinned, and comparing with the description, makes "the list in the description" mean the list for the head that merges.

**Why a `--yes` run that had to write the list stops.** That `--yes` was given before the list for this head was in the description, so the person cannot have been shown it, and under COR-050 point 3 such an authorisation accepts none of the answers. Stopping ready costs one more run; merging would act on an authorisation that covers nothing. Naming the head ties the authorisation to the one list that head has.

**Why a reason that reads as a closing reference is refused, not escaped.** The host reads closing references in the description and the squash commit with its own parser, which this capability cannot make skip a section. Such a reason would close an issue at merge, so it is never written: the artefact's words are reworded.

**Why nothing reads the section as input.** Each reader of the description answers a question the description's author answers — which issues the change closes, which documents it accounts for, whether the template was filled. The section is written by a command from the artefacts' words; letting it answer those questions would let words written for an artefact meet obligations they were never written for.

### Alternatives considered

- **The list inside `## Doc impact`.** Rejected. That section is read for the mapping's override and for closing references, so the artefacts' words would become input there.
- **A pull-request comment.** Rejected. The description is the one place the person reads before authorising and the one the squash commit carries; a comment is a second place, and a later comment does not replace an earlier one.
- **A stamp trusted without deriving.** Rejected. A marker naming the head a list is for, trusted as written, accepts a list edited by hand or left from an earlier head; deriving again and comparing does not.
- **Spilling an over-long list elsewhere.** Rejected. The person would authorise the merge from a description that does not hold what they accept. A list the description cannot hold stops the landing, and the change is split or the anchor narrowed.

## Implications

- `open-pr` derives the list at the pushed head and never refuses to open over it: a list it cannot derive, or cannot write, is left out with a warning, and `land-work` writes it or refuses. `edit-pr` derives nothing.
- `land-work` gains a step between the review and the merge that derives the list, prints it, and writes it into the description; it refuses a reason that reads as a closing reference. The capability README documents the section and the step.
- Every reader of the description named in point 4 strips the section before it reads.
- `open-pr --doc-impact-from-friction` fills an unwritten `## Doc impact` with one line pointing at the section, naming no path and no reason, so it can meet no mapping obligation.
- [project-management:DEC-053-doc-check-slot] point 2 names this section as where the answers are listed. A line of it meets no obligation there.
