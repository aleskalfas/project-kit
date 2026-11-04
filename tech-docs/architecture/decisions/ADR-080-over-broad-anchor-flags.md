---
id: ADR-080
title: The over-broad warning counts the changes in which an anchor flagged its artefact
status: proposed
date: 2026-11-04
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** the whole-repository check warns of an anchor that asks its artefact for an answer too often. It counts, over the last 100 changes on the first-parent line, the changes in which the anchor flagged its artefact. An anchor that flagged it in more than 10 of them is over-broad. Every kind of anchor is counted, and an anchor on another artefact flags where that artefact changed.
- **Why:** the warning measured the share of tracked files a path anchor matches. An anchor on one busy page matches one file, so it never tripped, however many answers it asked ([project-kit#2636](https://github.com/aleskalfas/project-kit/issues/2636)).
- **The cost:** on this repository's tree the count takes about 0.3 seconds of processor time. The doc check's filler stays within its budget ([ADR-079](ADR-079-exact-fast-paths.md) point 2).

**Why an ADR.** The measure, its window and its threshold fix what the backbone reports, and later work narrows anchors by it. [COR-050](../../../.pkit/decisions/core/COR-050-anchors-and-friction.md) point 7 asks for the warning and leaves how it is measured open.

## Context

**What the warning is for.** COR-050 point 7 warns of an anchor broad enough to match most changes. Such an anchor makes every change a revalidation, and teaches people to answer blindly.

**What it measured.** A path anchor was over-broad when it matched more than half of the tracked files. An anchor of a registered kind was judged by the files its resolver names. A record or an artefact anchor was never judged. The file share stood in for the share of changes, because HEAD alone could answer it.

**What it missed.** On 4 November, before the glossary Task of [project-kit#2631](https://github.com/aleskalfas/project-kit/issues/2631) landed, 26 glossary terms anchored the visual-communication README. The README anchored its capability's other pages whole. Each edit of a page asked for the README's answer, and each edit of the README asked for 26. The file share saw one file each time.

## Decision

**The warning counts, for each anchor, the changes among the last 100 on the first-parent line in which it flagged its artefact. An anchor that flagged it in more than 10 is over-broad.**

### 1. The measure: the changes in which an anchor flagged its artefact

- **Flagged.** An anchor flagged its artefact in a change where what it stands on differs between the change's first parent and the change. That is COR-050 point 5's rule, read for one change.
- **Every kind.** Path, record, artefact and registered anchors are all counted. The rule is no kind's.
- **Through artefacts.** An artefact or record anchor flags where what it leads to changed. A target revalidated as updated in the same change passes the flag on. An `unchanged` revalidation stops it, as in the change check.
- **The anchor as HEAD declares it.** Each change is read as the whole check reads HEAD: HEAD's anchors, exclusions, places and derived links. The count is that of the anchor as it stands.
- **Not counted.** An artefact that owes no answer, excluded or received by sync, is never flagged. None of its anchors is over-broad.
- **The file share** is no longer read.

### 2. The window: the last 100 changes on the first-parent line

- **A change** is a commit on the line of first parents that leads to HEAD, compared with its first parent. On the default branch, that line holds one change for each pull request merged, squashed or not.
- **A merge** on the line is compared with its first parent. What it merged is its change.
- **Not a change:** the root commit and a shallow clone's cut. The clone holds no parent to compare them with.
- **A shorter line** gives a smaller window. On another branch, the line starts with the branch's own commits.

### 3. The threshold: more than 10 of the window's changes

- **The bar.** An anchor is over-broad when it flagged its artefact in more than a tenth of a full window: more than 10 of 100 changes.
- **A shorter history** is held to the same count of 10, not to a tenth of what it holds.
- **The finding** names the count and the window's size. It is reported and never failed, as COR-050 point 12 says.

### 4. Where it runs, and what it costs

- **Where.** In every whole-repository check, as before. The doc check's filler reads it there, and `pkit friction explain` marks the anchor.
- **What it reads.** Each change is listed in the one log the check reads already. A merge on the line adds one `git diff-tree` run for all of the window's merges.
- **What it compares.** For each file a change touched that an anchor stands on, the two versions, through the check's own readings. Each anchor value is counted once for the run.
- **What it costs.** On 4 November's tree, about 0.3 seconds of processor time, a unit of the filler's 32. The cost grows with the window's changes and the files they touch, not with the history's length.
- **Within the budget.** The count needs a document's headings and slugs read once per version, so they are kept for the life of the process. That saves the rest of the check more than the count costs. The filler measured about 16 units before and 15 after.

## Rationale

**Why changes, not files.** A file share asks how much an anchor covers, not how often it asks. An anchor on one busy page covers little and asks often. Counting changes measures what a person feels: answers asked.

**Why HEAD's anchor.** A person acts on the anchor as it stands. Narrowed, it is measured narrowed at once, and a broad anchor added today is warned of on its first check. Reading each change's own anchors would need two discoveries per change: the change check run 100 times.

**Why the first-parent line.** A change asks its answers once, in its pull request. Every commit of a merged branch would count one pull request's work several times.

**Why 100 changes.** The window is read from the log already in hand, so a larger one costs only the files it touches. With 100, one change is one percent. On this repository 100 changes span five or six days. In a slower project they span months. A window of days would hold too few changes there, and too many here.

**Why more than 10.** This repository's history sets the bar. Over it, at four points of history:

| Tree of | Anchors | Over 10 of 100 | What they are |
|---|---|---|---|
| 21 October | 1,350 | 24 | 17 use cases anchoring the whole command-line module, and software-analysis's whole-tree globs |
| 27 October | 3,798 | 42 | 39 use cases on that module, two pages on the CLI reference's surface section, project-management's scripts glob |
| 31 October | 4,306 | 45 | 40 use cases on that module, the same section, project-management's globs over its scripts and its records |
| 4 November, before #2634 | 6,591 | 36 | the glossary terms' README anchors and the README's whole-page anchors, below |

- **Each is broad.** A reviewer would call each such anchor broad: a whole module, a whole tree, a hub section or page.
- **Before #2634.** The 26 glossary terms' anchors on the README flagged 13 changes each. The README's whole-page anchors flagged 18 on the files page, 16 on the checks page and 11 on the outputs page. Its anchor on the components page flagged exactly 10, at the bar.
- **The rest, that day.** Outside the visual-communication capability, no anchor flagged more than 7.
- **Lower and higher bars.** At more than 5, 83 anchors were over the bar that day, many of them narrow anchors on busy code. At more than 15, three were, and no glossary term.

**Why "most" reads as a tenth.** COR-050 point 7 names the harm: every change a revalidation, answered blindly. In a repository of many parts, no anchor short of the whole tree flags most of all changes. At the four points above, the most any anchor flagged was 23 of 100. So the bar reads "most" by its reason: an anchor asked so often that its answers turn blind.

**Why one count for a short history.** In a project's first few changes nearly everything changes. A tenth of five changes is less than one, so every anchor that flagged once would be over-broad.

**What dropping the file share costs.** A project with 10 changes or fewer is warned of nothing. A path anchor on the whole tree flags every change after that, so it is warned of from its eleventh.

### Alternatives considered

- **The file share beside the count.** It names an anchor before history shows it, but only a path or registered anchor. It keeps two measures of one thing.
- **The change check run on each change.** It is exact to what each change asked then. It costs two discoveries per change, about 100 times the check's own discovery.
- **A window of days.** Its size would follow the project's pace, not its changes.
- **The answers each change asked.** It names a change, not an anchor, and a person narrows anchors.
- **Each anchor's share of its artefact's flags.** It names the anchor that asks most of one artefact, but cannot tell a broad anchor from a busy artefact.

## Implications

- **The finding's words.** `over-broad` keeps its kind, and its message names the count and the window. The machine-readable document adds no key, so its version stays.
- **The friction reference** describes the warning in the whole-repository check's findings. The lifecycle README's resolver section, software-analysis's analysis-author skill and the published body say the same.
- **COR-050 point 7** still says "most changes". Point 3 above reads it by its reason. A refinement of its words is the maintainers' to make.
- **A busy narrow anchor.** A page anchored on a module that changes in most of its capability's work can cross the bar. The warning names it, and a person judges it.
- **Recorded trigger to revisit.** The doc check's budget test fails with the count among the causes, or anchors over the bar turn out narrow in most reviews.
