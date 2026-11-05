---
id: ADR-080
title: An anchor is over-broad by how often it asks its artefact for an answer
status: accepted
date: 2026-11-04
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** the whole-repository check warns of an anchor that asks its artefact for an answer too often. It reads the last 100 commits on the first-parent line, and counts those in which each anchor flagged its artefact. An anchor that flagged it in more than half of them is over-broad. An artefact may be asked in more than 10 of them for a revalidation that left it as it was. Then the anchors behind most of those asks are over-broad too, named in one finding for the artefact where a person reads the findings. The first is COR-050 point 7's ground. This record adds the second to point 7, and sets the numbers of both. It also warns, from HEAD alone, of an artefact that anchors a record or a document whole beside anchors on its parts.
- **Why:** the warning measured the share of tracked files a path anchor matches. An anchor on one busy page matches one file, so it never tripped, however many answers it asked ([project-kit#2636](https://github.com/aleskalfas/project-kit/issues/2636)).
- **The cost:** the documentation check's filler reads the whole check, so it counts too, though it never reads the count. That adds about 5 percent to its time, well within the budget a test holds it to.

**Why an ADR.** [COR-050](../../../.pkit/decisions/core/COR-050-anchors-and-friction.md) point 7 warns of an anchor broad enough to match most changes. This record adds a second ground, refined into point 7 with its acceptance: the anchors behind most of the many changes that ask one artefact for a revalidation that leaves its content as it was. Point 7 leaves open which changes are read, how an anchor is read as matching one, and how often is often. The window, the reading and the numbers fix what the backbone reports, and later work narrows anchors by them.

## Context

**What the warning is for.** COR-050 point 7 warns of an anchor broad enough to match most changes, "because it would make every change a revalidation and teach people to update markers blindly". An artefact owes one answer for each change, whichever of its anchors flagged it. So an artefact often asked for revalidations that leave it as it was teaches the same habit, whichever anchors ask.

**What it measured.** A path anchor was over-broad when it matched more than half of the tracked files. An anchor of a registered kind was judged by the files its resolver names. A record or an artefact anchor was never judged. The file share stood in for the share of changes, because HEAD alone could answer it.

**What it missed.** On 4 November, before the glossary Task [project-kit#2634](https://github.com/aleskalfas/project-kit/issues/2634) landed, 26 glossary terms anchored the visual-communication README whole. The README anchored its capability's other pages whole. Each edit of a page asked for the README's answer, and each edit of the README asked for 26. The file share saw one file each time.

## Decision

**Of the last 100 commits on the first-parent line, an anchor is over-broad when it flagged its artefact in more than half of them. Where an artefact is asked in more than 10 of them for a revalidation that left it as it was, its anchors are named over-broad too. They are named by their share of those asks, the largest first, until the asks in which only named anchors asked are more than half of the artefact's asks, in one finding for the artefact where a person reads the findings. Apart from both bars, an anchor on a record or a document whole beside anchors on its parts is warned of from HEAD alone.**

### 1. The reading: the commits in which an anchor flagged its artefact

- **Flagged.** An anchor flagged its artefact in a commit where what it stands on differs between the commit's first parent and the commit. That is COR-050 point 5's rule, read for one commit.
- **Every kind alike.** Path, record, artefact and registered anchors are all counted, by the one rule.
- **Through artefacts.** An artefact or record anchor flags where the content of what it stands on changed, which is a part for a section or point anchor (COR-050 point 5). So a target whose content the commit changed passes the flag on, and one it left as it was stops it, as in the change check. The target's content counts, not its revalidation's outcome.
- **The anchor as HEAD declares it.** Each commit is read as the whole check reads HEAD: HEAD's anchors, exclusions, places and derived links. The count is that of the anchor as it stands.
- **What it reads.** Each file the window's commits touched that an anchor stands on, both versions, through the check's own readings. For the second bar, also each version of the artefact the window holds, and what each commit wrote in both homes of the artefact's answers: its data and the answer files.
- **What a commit wrote.** The answer reader reads whether one commit, against its first parent, wrote a revalidation of the artefact ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 2). It did where it wrote a value of `at`, in the artefact's data or in an answer file it added or rewrote, that the artefact's answers never carried at the first parent or before. A change may rewrite an answer file it added itself, as a fix round does ([COR-062](../../../.pkit/decisions/core/COR-062-answers-in-own-files.md) point 3). Where its commits land one by one, the rewrite is a commit of its own. So an answer moved out of the data, an answer file renamed or put back, and a value written back, as a revert writes it, revalidate nothing (COR-050 point 3).
- **Where it reads otherwise than the change check.** The change check reads the answers live at a change's head against its base's values. The count reads what each commit wrote. Reading which answers are live after each would read every commit's answers whole, near the cost of the change check run on each commit, which the Alternatives reject. So one commit that adds both a revalidation and an answer that replaces it with a value written back reads here as a revalidation. The change check finds the ask still owed. A test pins it.
- **Where it reads inexactly.** Its reading can differ from what the person met:
  - **Where the two checks part.** COR-050's "Where the two checks part" names two cases where the whole check reports an artefact stale after a merge. This record reads each such merge as an ask answered as it was. One is a line of work that revalidates, then changes an anchor again, and lands with its commits kept. The other is a conflict resolved by keeping the line of work's revalidation in the block.
  - **A revalidation no anchor asked for.** One made for another reason, after a flag, answers the flag, as an asked one does.
  - **HEAD's anchors.** A commit made before an anchor was declared is read with it, so an ask that no check made then counts.
- **Not counted.** An artefact that owes no answer, excluded or received by sync, is never asked for one (COR-050 point 7, COR-062 point 9), so none of its anchors is over-broad. A dead anchor stands on nothing at HEAD to count. Nor is an anchor whose kind nothing resolves counted, nor one whose resolver gave no answer.

### 2. The window: the last 100 commits on the first-parent line

- **A commit on the line** is a commit on the line of first parents that leads to HEAD, compared with its first parent. It is the count's unit. A change, in this record, is the work one pull request carries.
- **Where the two are one.** Where the default branch lands each change as one commit, by a squash or a merge commit, each commit on the line is one change.
- **Where they are not.** Where it lands a change by a rebase or a fast-forward, each commit of the change is on the line. On a branch, each of the branch's own commits is on the line too.
- **Both bars move with it.** There, the first bar can under-report: an anchor that flagged its artefact in 20 of 30 changes flagged it in 20 of 100 commits. The second bar needs a revalidation after a flag, wherever in the change it sits. It counts each commit of the change that flagged the artefact before one, so three such commits count three asks where their squash counts one.
- **A merge** on the line is compared with its first parent. What it merged is what it changed, the answers its branch wrote among it, so it reads as a squash of its branch would.
- **Not counted:** the root commit and a shallow clone's cut. The clone holds no parent to compare them with.
- **A shorter line,** of a young repository or cut by a shallow clone, is not judged by the first bar. A share of a few commits says nothing of the line. The second bar reads what the line holds. Where a shallow clone cut it, the message says so, and how many commits it holds.
- **Outside the scope of a reason COR-050 gives.** Its "Why a change is a difference between two states" refuses to count commits, since how a change lands would then decide its debt. That reason governs what an artefact owes, and the count decides nothing an artefact owes. It is reported only, never failed (COR-050 point 12), and holds nothing open ([ADR-055](ADR-055-first-adopter-analysis-and-living-docs.md) point 5).

### 3. The bars, and the finding

- **Most of the window's commits.** An anchor that flagged its artefact in more than half of the window's commits is over-broad, judged only where the line holds the whole window. The flags count every commit of the window, those before the artefact was there among them, since they measure the anchor's breadth. This bar is each anchor's own.
- **An ask that left the artefact as it was.** It is a commit in which an anchor of the artefact flagged it, with the artefact there at the first parent. The artefact's next revalidation on the line is in that commit or a later one in the window, and no commit from the flag to it changed the artefact's content. Content is read by the check's own reading of an artefact's content (COR-050 point 5).
- **Counted for the artefact.** Each such commit counts once, however many of the artefact's anchors flagged it there. Splitting an anchor into anchors on its parts leaves the count as it was.
- **What is no such ask.**
  - **A flag no revalidation follows** in the window is owed still, and is not counted. Where each change is one commit, a commit that flagged the artefact and did not revalidate it left the ask as debt. A later revalidation answers it, such as a sweep that answers debt `unchanged`, and it counts then.
  - **A deferral** is an answer (COR-050 point 5) that leaves the revalidation owing. The check reports the drift rightly, so a deferral alone is no ask that changed nothing. A revalidation that follows it as it was makes the ask one.
  - **A flag an update answered,** the content changed between the flag and the revalidation, is not counted.
- **What it does not tell apart.** The check cannot tell a careful revalidation from a blind one (COR-050 point 3), so it counts the asks revalidations answered, never their words.
- **The anchors it names.** Where an artefact has more than 10 asks, its anchors are named in order of their share of them, the largest first.
  - A tie goes to the anchor the artefact declares first.
  - They are named until the asks in which only named anchors asked are more than half of the artefact's asks. Narrowing the named anchors together then brings the count to half or below.
  - The named anchors are thus behind most of the asks. Most is point 7's word for the first ground, reused here for a rule that names anchors, not one that warns.
  - The order names the largest shares, not always the fewest anchors that would do.
  - An artefact with one anchor has that anchor named.
- **The findings** keep one kind, `over-broad`. They are reported and never failed (COR-050 point 12).
  - **The first bar** gives one finding for each anchor over it. Its message gives the anchor's flags and the window's size, and the artefact's asks.
  - **The second bar** gives one finding for the artefact where a person reads the findings, in the human views of the check and of the explanation. It gives the artefact's asks and the window's size, then the named anchors with their shares, the largest first.
  - **Beside a named anchor** stands the narrower anchor, where one exists (below).
  - **Its last line** is the advice for the artefact as a whole. Narrow the named anchors where a narrower one exists. Where none does, split the artefact or what the anchors stand on, or remove an anchor the artefact does not rest on.
  - **An anchor over both bars** is in both findings.
  - **The machine-readable documents** list each named anchor as a finding of its own, with its own message, as they list every finding. Each gives the bar it crossed, `flags` or `asks`, and a second bar's finding gives its share. The second bar's findings on one artefact stand together, after its other findings, in the order the bar names them. Their count of `over-broad` findings counts each named anchor, where the human summary counts the artefact's finding once. The grouping is the human views'.
- **What an anchor's own message says to do.** A path anchor on several files: narrow it. One on a single file: anchor the record's points, the document's sections or lead, or a narrower value of a registered kind. A whole record: anchor its points. A whole document: its sections or its lead. A section: its sub-sections. An anchor of a registered kind: a narrower value.
- **Where nothing names less,** the message says so. It says to remove the anchor unless the artefact rests on all of it. Or split what the anchor stands on into parts an anchor can name, or the artefact into parts that each rest on less, as a hub needs. A single file where a kind is registered gets the same offer, for where no kind names a part of it.
- **What names nothing less:** a record's point, a lead, a section that holds no sub-section, a collection entry, and a file that is neither a record nor a document where no kind is registered.
- **What stands beside a named anchor.** Only a narrower anchor the check knows exists: a glob's files, a record's points, a document's sections or lead, or a section's sub-sections. The check cannot tell whether a registered kind names a part of a file, so nothing stands beside such an anchor.

### 4. Where it runs

The count runs in every whole-repository check. The explanation of one artefact's friction marks each over-broad anchor of it, and shows the second bar's findings as one, as the check's own view does. The doc check's filler reads the whole check ([ADR-079](ADR-079-exact-fast-paths.md) point 2), so it pays for the count, which it never reads. Sparing it would take an option on the check's command and a change to the filler that runs it, for about 5 percent of the filler's time.

### 5. A whole anchor beside anchors on its parts

An artefact may anchor a record or a document whole, and parts of it too, a pair in the words of this point. Whatever flags a part anchor then also flags the whole anchor, so the part anchors ask nothing the whole anchor does not. The check warns of each such whole anchor. It reads HEAD alone, with no history and no number.

- **The whole anchor,** in COR-050 point 2's terms:
  - a record anchor on a whole record
  - an artefact anchor on a whole document, a record's own file among them
  - a path anchor on that single file
- **The anchors on its parts,** in the same terms:
  - a record anchor on a live point of the record
  - an artefact anchor on a section or the lead of the document
- **What the part anchors still do.**
  - **A deferral.** Each names one anchor (COR-050 point 4), so a part anchor keeps one to that part. The whole anchor, flagged too, needs its own.
  - **A revisit.** A link's target is an anchor (COR-050 point 16), so a part anchor names one part for a revisit.
  - **A dead anchor.** A part anchor goes dead when its point or heading does (COR-050 point 7). The whole anchor does not.
  - **The explanation.** A stale part anchor shows what changed in its part alone (COR-050 point 13).
- **What is left out.**
  - A glob or a folder, which stands on files and names neither a record nor a document.
  - A value of a registered kind, on either side. Such a kind names no part (COR-050 points 2 and 5), and the check cannot tell whether a value names a part of a file (point 3).
  - A section beside its own sub-section. COR-050 point 2 calls both parts, so neither is a whole anchor.
  - An anchor reported dead, ambiguous, refused or unresolved, and one on a retired point, which stands on nothing.
  - A path anchor beside a broader one, and a collection entry beside a path anchor on its file. Neither names a part.
  - An artefact that owes no answer, whose anchors ask for none (point 1).
- **The finding.** Its kind is `whole-and-parts`, one finding for each whole anchor, naming the anchors on parts beside it.
- **The advice.** Its message gives two moves and what each costs, the safe one first.
  - **Remove the part anchors.** This loses no flag and no ask, but gives up what they still do.
  - **Remove the whole anchor.** This narrows what asks the artefact, and misses a change outside those parts. So it suits only an artefact that rests on those parts alone.
  - **Either move** changes the anchor list, which owes a revalidation (COR-050 point 6).
- **Reported only.** It never fails (COR-050 point 12), and it owes no answer.
- **The tracking issue.** It never holds project-kit's tracking issue open. It is a finding the check reports as owing nothing, which [ADR-055](ADR-055-first-adopter-analysis-and-living-docs.md) point 5 counts among the four kinds that need no answer. The issue's body lists it with the other findings that owe nothing.
- **Where it runs.** In every whole-repository check, and in the explanation of one artefact's friction.

## Rationale

**Why commits, not files.** A file share asks how much an anchor covers, not how often it asks. An anchor on one busy page covers little and asks often. Counting commits measures what a person meets: answers asked.

**Why HEAD's anchor.** A person acts on the anchor as it stands. Narrowed, it is measured narrowed at once, and a broad anchor added today is measured on its first check. Reading each commit's own anchors would need two discoveries per commit: the change check run 100 times.

**Why the first-parent line.** On a default branch that lands by squash or merge commit, a change asks its answers once, in its pull request, and lands as one commit on the line. Every commit of a merged branch would count one pull request's work several times.

**Why 100 commits.** The window is read from the log already in hand, so a larger one costs only the files it touches. With 100, one commit is one percent. On this repository 100 commits span five or six days. In a slower project they span months. A window of days would hold too few commits there, and too many here.

**Why the first bar is half.** COR-050 point 7 warns of an anchor "broad enough to match most changes". Read in its own words, most is more than half. Where each change lands as one commit on the line, the bar meets point 7's first ground exactly. Where the commits of a change land one by one, by rebase or fast-forward, it can under-report (point 2).

**Why the first bar needs the whole window.** In a few commits, more than half comes by chance: 1 of 1, or 2 of 3. A young repository's first commits would warn of anchors no later history bears out. The second bar counts asks, not a share, so it reads a short line too.

**Why the second bar is counted for the artefact.** Point 7's second ground is the artefact's: the anchors behind most of the many changes that ask one artefact for a revalidation that leaves its content as it was. It counts asks, not revalidations: one sweep that answers three asks `unchanged` is one revalidation and three asks. An artefact answers once for each change, whichever of its anchors flagged it.
- **Counted for each anchor apart,** the warning would measure neither the asks one artefact meets nor the artefacts one edit asks. Splitting an anchor into section anchors would silence it, with the asks as many as before, and the message's own advice invites that split.
- **Counted for the artefact,** it measures the asks one artefact meets, and a split leaves them as they were. Each anchor's share says which to narrow first. How many artefacts one edit asks is not decided here (Implications).

**Why an ask is counted by the next revalidation.** A change's answer may sit in a commit of its own, as a rebase lands it. A sweep may answer a pile of debt `unchanged` later, as warning mode, the default, lets a project do. Either way, the revalidation that answers a flag lies in a later commit than the flag. Read by the artefact's next revalidation, such asks count as they would were the answer in the flag's commit.

**Why the naming stops on the asks it clears.** Narrowing the named anchors together leaves the asks in which an unnamed anchor asked, half of them or fewer. Where two anchors always ask together, narrowing the first alone leaves the count as it was, so the rule names both.

**Why one finding for the artefact.** A hub's asks come from commits that each touch several of its anchors, so the second bar names many of them. Reported one by one, its findings at `a4c963be` are 105, one for each anchor it names of the 221 that asked, most with nothing narrower to offer. A person given 105 warnings acts on few of them, and the warning becomes the noise it exists to remove. One finding for each artefact makes them 17 at `a4c963be` and 39 at `4c5a72d8`, naming the same anchors. Each names what a person acts on: the artefact, and its anchors in the order to narrow them.

**Why the name covers both grounds.** `over-broad` is COR-050's name for the anchor point 7 warns of, on either ground. The message and the machine-readable document's `bar` name the bar crossed, so one kind is enough, and a reader needs no new one.

**Why standing debt is left out.** An ask nothing has revalidated yet, or that a deferral answered, is drift the check reports rightly, not an ask that changed nothing. Counted, it would tell a project in warning mode to narrow an anchor that is reporting drift. So an ask counts only once a revalidation answers it. The whole check parses every version of every answer file for the revalidation points already, so this reading parses none again. To tell whether a value is new, it walks the artefact's versions as the walk that finds its revalidation point does.

**Why more than 10.** A judgement, fitted to the incident. In a full window, it is more than one commit in ten asking the artefact for a revalidation that leaves it as it was. At more than 15, the incident's glossary terms would not be named. In a shorter window, 10 is a larger share. Over this repository's history, at five points, every artefact:

| Tree of | Artefacts | Most flags by one anchor | Anchors over the first bar | Artefacts over the second bar | Anchors it names | What it names |
|---|---|---|---|---|---|---|
| 24 October, `55c2c824` | 319 | 15 | none | 7 | 14 | six use cases, 12 to 15 asks, each its anchor on the whole command-line module, three with one more and one with four more; the rule RS-SAN-001, 11, its anchor on software-analysis's DEC-001 whole |
| 27 October, `7dc9cae4` | 362 | 23 | none | 45 | 80 | 37 use cases and two journeys, 11 to 21 asks, most their anchor on the command-line module alone; the root README, 29, twelve anchors; the adapters and schemas READMEs, two permissions READMEs and CONTRIBUTING.md, 13 to 21 |
| 31 October, `3f1e276b` | 397 | 22 | none | 47 | 74 | 38 use cases and two journeys, 11 to 20 asks, most the command-line module alone; the root README, 28, five anchors; CONTRIBUTING.md and a permissions README, 22, two each; a requirement and three READMEs, 11 to 17 |
| 4 November, before #2634, `4c5a72d8` | 528 | 18 | none | 39 | 118 | the visual-communication README, 19 asks, 15 anchors, its four whole-page anchors among them; four of its pages, 13 to 22, 8 to 22 anchors each; the 26 glossary terms, 12 to 15, each its anchor on the README alone; the root README, a journey, five use cases and a permissions README, 11 to 16 |
| 4 November, `main` at `a4c963be`, with this change | 530 | 14 | none | 17 | 105 | the visual-communication README and four of its pages, 13 to 20 asks, 7 to 17 anchors each, mostly a section, a record's point or one module; the root README, 14, seven anchors; seven glossary terms, 11 to 14, one or two modules, a schema or a record's point each; a journey, two use cases and a permissions README, 11 to 12 |

- **The first bar names nothing here.** The most any anchor flagged was 23 of 100. It is point 7's first ground, met wherever an anchor reaches it.
- **The second bar names hubs.** Each is an artefact whose anchors together ask it most often. Before `a4c963be`, the anchor with the largest share is mostly one a reviewer would call broad: the whole command-line module, a whole record, a page or the README whole. At `a4c963be` it is mostly a section, a record's point or one busy module, and the shares are spread more thinly.
- **On a hub it names many anchors.** Naming each anchor that asked in one of the asks would name 53, 295, 277, 244 and 221 at the five trees, and the rule names 14, 80, 74, 118 and 105. A hub's asks come from commits that each touch several of what it anchors. So the asks in which only named anchors asked stay few until many are named. At `a4c963be` it names 7 to 17 of the 19 to 35 anchors that asked each visual-communication page, some with a share of one.
- **The incident sits well over the bar.** On 4 November before #2634, the visual-communication README was asked 19 times, 9 over the bar. Its anchors on its capability's pages files.md, checks.md, components.md and outputs.md asked 8, 8, 6 and 4 of them, and all four are named. Each glossary term was asked 12 to 15 times, 12 of them by its anchor on the README whole, the one anchor it names.
- **Advice a person can act on.** At `a4c963be`, 10 of the 105 named anchors get a narrower anchor that names less: a section's sub-sections, or a record's points. Another 41 are a record's point, a section that holds no sub-section, or an artefact with no part. The other 54 are each a single file no registered kind here names a part of. For those 95, the artefact's finding offers the split or the removal. Most named anchors are already as narrow as an anchor goes, so the recorded trigger to revisit, below, is near.
- **The use cases on the command-line module.** At `a4c963be`, 42 artefacts, most of them use cases, still anchor the whole command-line module. The list names it on two of them. The window holds only 3 commits that changed the module, so it asks few answers there. The count measures how often an anchor asks, not how much it covers (What dropping the file share costs).
- **An anchor whose asks bring updates.** project-management's README anchored the capability's scripts with a glob that flagged 23 commits on 27 October. The README changed in 22 of them, so neither bar names it.
- **Lower and higher bars.** At more than 5 asks, 47, 73, 81, 89 and 68 artefacts cross it. At more than 15, 0, 30, 14, 4 and 3 do, and no glossary term of the incident would be named.

**What it costs.** Measured on 4 November's `main`, `a4c963be`, with this change, its naming step included:
- **What it read.** 2,023 anchor values, against the 1,760 paths the window's commits touched. The window held no merge, so one further git process for all the window's merges is not measured.
- **What it cost the filler.** 13.26 units with the count and 12.59 without, in ADR-079 point 2's units, a fixed parse of YAML text. Each is the median of five runs, alternated, and a second run gave 13.81 and 13.09. The code before the count, which read the file share and cached no headings, took 14.59 and 15.08 in two runs on the same tree. The count costs 0.67 units, about 5 percent of the filler's time.
- **Against the budget.** The budget test holds the filler to 32 units (ADR-079 point 2). It passes, with about 18 units to spare.
- **What it leans on.** The bounded caches of a body's headings and of a heading's slug (ADR-079 point 1). Without them, the count would cost 5.93 units: 21.12 with it, against 15.19 without.
- **What its cost grows with.** The distinct anchor values, times the paths the window's commits touched. For each artefact flagged in more than 10 commits, it reads each version of it the window holds. For each value of `at` a commit wrote for one, it walks the artefact's versions as its revalidation point's walk does. The window's merges add a git process and the paths they bring.

**What dropping the file share costs.** The file share named a broad path anchor before any change touched what it matched. The count names an anchor only once commits have flagged its artefact. A new anchor on a quiet tree is warned of only once that tree changes. A broad anchor in a young project is named by the first bar once its line holds 100 commits, or by the second once its artefact's asks cross it.

**Why this record alone decides the pair.** COR-050 point 7 grounds its over-broad warning in a harm, the habit of updating markers blindly. This warning states no harm, only redundancy, so it needs no core footing. COR-050 point 12 already reports the whole-repository check's findings only, whichever their kind.

**Why ADR-055 point 5 holds as written.** That point counts four kinds that need no answer, and one of them is a finding the check reports as owing nothing. This finding is one, as `left-out` is, so the count stands.

**Why the finding is keyed on the whole anchor.** One finding for each whole anchor and its parts is the shortest list: 48 at `4c5a72d8`, where one for each pair of anchors gives 141. Neither anchor of a pair is wrong by itself, so the key says nothing of which to remove. The message gives both moves.

**Why the pair reads HEAD alone.** The pair is a fact of one block, so history adds nothing. The bars count how often an anchor asked, so they name a whole anchor only where it asks often. The pair stands however seldom it flags.

**Why a kind of its own.** `over-broad` says how often an anchor asks, and its count moves as the window slides. This finding has no count and no bar, and it stands until a block changes. So `bar` keeps its meaning, and a reader can tell the two apart.

**Why it owes no answer.** The pair makes nothing untrue. An artefact owes one answer for each change, whichever anchor flagged it, so the part anchors add no answer to a change.

**What a pair kept on purpose costs.** A person may keep a pair for what its part anchors still do. It then warns for ever, and nothing records that it is meant. That cost is accepted for now, since the finding owes nothing and holds nothing open.

**What it names here.** At `4c5a72d8`, 4 November before #2634, it names 48 whole anchors on 37 artefacts. The visual-communication README's anchors on `checks.md`, `files.md`, `outputs.md` and the starter README are among them. At `96ab08b0` it names 43 on 35. At both trees, 33 are a whole record beside points of it, and the rest a whole document beside its sections.

**What the warning costs.** Measured on `96ab08b0` with this change, in ADR-079 point 2's units. The filler took 15.69 units with the warning and 15.51 without, each the median of ten runs, alternated. That difference lies inside the runs' spread, of 1 to 1.6 units. Timed at each of its 530 calls, in five runs, the warning's own reading took 0.18 units of a run of about 15.5, about 1 percent. The budget test holds the filler to 32 units, so it passes with about 16 to spare.

### Alternatives considered

- **One bar at more than 10 flags.** It reads "most" as a tenth of the window.
- **A finding for each anchor the second bar names.** It gives 105 findings at `a4c963be` and 118 at `4c5a72d8`, most with nothing narrower to offer. A hub's asks come from commits that touch several of its anchors, so its list is long, and passed over.
- **The second bar counted for each anchor apart.** It names an anchor that asks often on its own. It misses an artefact asked often by several anchors, and a split into section anchors silences it with the asks as many.
- **Each anchor that asked in one of the asks.** It names 221 anchors on 17 artefacts at `a4c963be`, many with a share of one, and a warning that long is passed over.
- **The top anchor only, with every share in the message.** It names one anchor of each artefact. Where two anchors drive the asks together, it names one, and narrowing that one alone changes nothing.
- **Naming until the named anchors asked in more than half of the asks.** It stops before an anchor that asked beside the named ones in each of their asks. Narrowing the named ones alone then leaves the count as it was.
- **An ask counted only where its own commit revalidated.** It misses an answer in a commit of its own, as a rebase lands it, and a sweep that answers debt later.
- **The file share beside the count.** It names an anchor before history shows it, but only a path or registered anchor. It keeps two measures of one thing.
- **The change check run on each commit.** It is exact to what each change asked then. It costs two discoveries per commit, about 100 times the check's own discovery.
- **A window of days.** Its size would follow the project's pace, not its changes.
- **The answers each change asked.** It names a change, not an anchor, and a person narrows anchors.
- **Each anchor's share of its artefact's flags.** It names the anchor that asks most of one artefact, but cannot tell a broad anchor from a busy artefact.
- **A bar on the share of flags that left the artefact as it was.** With few flags it is noisy.
- **Counting `unchanged` answers.** COR-050 point 3 never reads the outcome to compute staleness, which it recomputes from git. Reading the content keeps the count on the same footing. An `updated` answer that left the content as it was would go uncounted, too.
- **The pair reported under `over-broad`, with a third `bar`.** It keeps one kind, but `bar` names a count crossed, and this finding counts nothing.
- **A finding for each pair of anchors.** It gives 141 findings at `4c5a72d8` and 110 at `96ab08b0`, where one for each whole anchor gives 48 and 43.
- **A glob, and a value of a registered kind, read as a whole or a part.** It reads a kind as naming a part, which COR-050 point 2 says it does not. It names no more at either tree.

## Implications

- **The finding's words.** `over-broad` keeps its kind, and its message gives the counts, the bar crossed and what to do. The machine-readable documents of the check and of the explanation add three keys to each finding. `bar` is `flags` or `asks` for an over-broad finding, and `null` for any other. `share` is a second bar's finding's share of its artefact's asks, and `null` for any other. `parts` lists the anchors on parts a `whole-and-parts` finding names, and is `null` for any other. A key added leaves their version as it was.
- **Where the bars are stated.** The CLI README's `over-broad` row states both bars with their numbers, their reference home outside this record. The backbone's changeset states them too, for the release.
- **The tracking issue.** An over-broad anchor never holds project-kit's tracking issue open ([ADR-055](ADR-055-first-adopter-analysis-and-living-docs.md) point 5). Its count moves as the window slides, with no anchor changed. A person may judge an anchor fine, and nothing records that, so an issue it held open would stay open for good. The issue's body lists the anchor in words of its own, with no count and no window's size, since they move with most pushes. The check's message and the explanation of one artefact's friction give both. The body gives the second bar's anchors on one artefact as one entry, as the check's own view does.
- **A busy narrow anchor.** A page anchored on one module that changes often, without changing the page, can cross the second bar. The warning names it, and a person judges it. Where nothing names less of the module, the message offers the removal or the split.
- **A document's data in a sidecar** ([COR-063](../../../.pkit/decisions/core/COR-063-document-sidecars.md)). A revalidation in an artefact's data is read only in commits that touched the artefact's own file. Once the module that reads a document's data from either home lands ([ADR-070](ADR-070-document-sidecar-place.md) point 7, [project-kit#2077](https://github.com/aleskalfas/project-kit/issues/2077)), a revalidation written only into a sidecar is read too.
- **Records refined in place,** atomically with this record's acceptance:
  - COR-050 point 7: the second ground, the anchors behind most of the many changes that ask one artefact for a revalidation that leaves its content as it was
  - ADR-055 point 5: an over-broad anchor never holds the tracking issue open
- **Not decided here:**
  - counting a branch's commits as one change;
  - evidence, in the explanation of one artefact's friction, of the commits an anchor flagged;
  - one reading of renames for every kind;
  - how many artefacts anchor each target;
  - recording a person's judgement that an anchor is fine as it is;
  - telling the person who answers an ask in the change check how often that anchor has asked, since on project-kit the warning reaches only the tracking issue;
  - recording a person's judgement that a pair of a whole anchor and its parts is meant;
  - warning of a whole anchor beside anchors on its parts in the change check, where a change adds the pair.
- **Recorded trigger to revisit.** Any of these:
  - the doc check's budget test fails with the count among the causes;
  - anchors over a bar turn out narrow in most reviews;
  - an adopter reports the bars as too eager.
