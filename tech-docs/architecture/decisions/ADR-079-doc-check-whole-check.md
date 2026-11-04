---
id: ADR-079
title: Fast paths that give the exact result speed the backbone's readings, and the doc-check filler keeps the whole check
status: proposed
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** the backbone may read YAML, history and file listings by faster paths, on one condition. Each fast path gives exactly what the slow one gives, or hands its input to the slow one. With them, living-docs' doc-check filler goes on reading the whole-repository friction check, every artefact judged, inside the 30-second bound for a query command.
- **Why:** on CI the filler overran its bound, and both the doc check and `pkit validate` failed ([project-kit#2410](https://github.com/aleskalfas/project-kit/issues/2410)).
- **The measure:** on 4 November's tree, on a laptop, the median wall time of the whole check fell from 14.3 to 5.2 seconds, and of the filler from 14.7 to 5.8.
- **The choice it leaves a person:** point 2 declines, for now, the selection of the check drafted for [project-kit#2365](https://github.com/aleskalfas/project-kit/issues/2365), which judges the filler's pages alone. #2410 asks that the filler leave half its bound on CI; #2365 asks that it answer within a third. The fast paths alone may meet a third on most runners, but not on the slowest. Point 1 stands whichever way that goes.
- **When to reopen it:** when the doc check's line on any of `main`'s CI runs takes more than 15 seconds, or the filler gives no answer within its bound (Implications). On the slowest runners that may come within weeks.

**Why an ADR.** Point 1 sets a rule that later work builds on: how the backbone's readings may be sped up without a second home for any computation ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 2). Point 2 sets which reading of the friction engine a capability's filler takes, a boundary between a capability and the backbone.

## Context

**What the filler reads.** living-docs' filler for the doc-check point reads its pages' states and the uncovered surface from the whole-repository check (living-docs README, "The documentation check"). project-management declares the point's inert policy `fail` ([project-management:DEC-053](../../../.pkit/capabilities/project-management/decisions/DEC-053-doc-check-slot.md)), so a filler that does not answer leaves the point unresolved ([COR-052](../../../.pkit/decisions/core/COR-052-slots.md) point 6). A query command has 30 seconds, and a run inside another has the time its caller has left (ADR-057 points 3 and 5).

**What happened.** On 3 November, the doc check's line on `main`'s CI run took 30.04 seconds and passed. The line runs the filler and the work around it, and the filler answered just inside its bound. Pull requests' runs were killed at the bound, in the doc check and in `pkit validate`, which runs the filler too. Runners differ: [project-kit#2412](https://github.com/aleskalfas/project-kit/pull/2412) found `main`'s doc check at 18 to 21 seconds on most runners, and 26 to 29 on slow ones. A runner takes about 1.2 to 2 times a laptop's time.

**Where the time went.** A profile of the whole check on project-kit's tree, before:
- **YAML, about 70% under the profiler.** The pure-Python loader, ruamel.yaml, read 4.6 MB of answer files and 3.8 MB of front matter, at about 1.3 MB a second. The answer files are 3.8 MB at HEAD; the history's earlier versions make up the rest.
- **The same texts again.** Each reader of a settings text parsed it anew.
- **The history walk.** It sought a time in each version's whole bytes, bodies included: 214 MB.
- **Path anchors.** Each was matched against every file at HEAD and every path in history.

**What grows.** The whole check's CPU time in process on `main`'s tree, laptop, one run each:

| Tree of | Before | After |
|---|---|---|
| 27 October | 9.1 s | 3.7 s |
| 31 October | 10.0 s | 3.1 s |
| 3 November | 12.5 s | 3.9 s |

Each answer file names the earlier answer files on its artefact ([COR-062](../../../.pkit/decisions/core/COR-062-answers-in-own-files.md) point 4). So an artefact's answer bytes grow with the square of its revalidations. Answer files grew from 2.5 MB to 3.8 MB between 31 October and 3 November.

**The other way.** #2365 drafted a selection of the whole check that judges the filler's pages alone, built in #2412. The whole check's wall time in process on 3 November's tree, laptop:

| | Whole check |
|---|---|
| Before | 14.2 s |
| A selection alone | 8.9 s |
| Fast paths alone | 4.5 s |
| Both | 2.9 s |

A selection still reads HEAD, the history and HEAD's answers, and computes the measures (COR-050 point 8). It saves the judging of the other artefacts: 5.3 seconds before the fast paths, 1.6 after.

## Decision

**The backbone's readings may take fast paths, each giving the exact reading's result or handing its input to the exact reading. With them, the doc-check filler reads the whole-repository check while it leaves the filler half its bound.**

### 1. A fast path gives the exact result, or hands its input on

The backbone may speed two kinds of reading by a fast path: a safe load of YAML text, and the friction engine's readings of history and of file listings. Any other reading is sped this way only by a record of its own. A fast path gives exactly what its exact reading gives, or hands its input to the exact reading:
- **YAML text.** The exact reading is ruamel.yaml's safe loader. The binary holds one fast reader of YAML text. A home that reads YAML text by a fast path calls it, and none writes its own. It takes only a form it is sure of. On any doubt and any failure it gives the text whole to the caller's own call of the loader, so every error raised is the loader's own. A round-trip load, which keeps comments and order, has no fast path.
- **The form the backbone writes.** The answer writer writes answer files in the form the fast reader takes, so the reading that grows keeps the fast path. A test holds the writer to it.
- **A prefilter.** A prefilter narrows what it searches only to the part of an input the parse reads data from. Where it cannot cut that part, it searches the whole input.
- **An index.** An index over a listing gives the same members, in the same order, as the one pattern reading gives over every member.
- **A repeat.** A text parsed once in a run is handed to each caller as its own copy.

Tests compare each fast path with its exact reading: on inputs at the edges of its form, on inputs made at random, and on the project's own tree. Tests sample the difference and cannot prove it nil. What keeps a fast path exact beyond them is that it hands on every input it is not sure of.

**No second home.** A fast path is part of the reading it speeds. Each home of ADR-057 point 2 still computes its answer once. For YAML text it calls the one fast reader, behind which the loader stays the exact reading. A fast path adds no dependency, as [PRJ-003](../../../.pkit/decisions/project/PRJ-003-implementation-language.md) asks.

### 2. The filler reads the whole check

The filler reads its pages' states and the uncovered surface from the whole-repository check, every artefact judged. No selection of the check is built for it while the doc check's line on `main`'s CI runs takes no more than half the filler's bound, 15 seconds. The line runs the filler and the work around it, so it bounds the filler's own time from above.

## Rationale

**Why half the bound.** It is #2410's criterion. It leaves room for a runner twice as slow as the one measured, the widest spread seen between runners.

**The selection's lasting cost.** A selection ties the engine to a rule that bounds every future judgement: that no judgement reads another's. It would rule out, say, a judgement that marks an artefact stale because an artefact it rests on is stale. It also adds an interface to the check. After the fast paths, it saves 1.6 seconds of 4.5. That cost buys little while the bound is met, and the selection composes with the fast paths whenever it is needed.

**The larger saving.** On the same tree the fast paths saved 9.7 seconds of the check, and a selection saves 5.3. The fast paths change no interface and no document. They speed every reader of the same YAML, the change check and validation among them.

**Why the rule keeps the fast paths exact.** A fast path that hands every doubt on can differ from the exact reading only where it misreads an input it is sure of. So the YAML form is kept narrow: YAML's own plain block form, with the loader's resolver and constructor giving every type. Tests compare the two readers over texts at the form's edges, and over texts made at random and cut short. Before landing, every YAML text in the repository's history, 9266 of them, read the same through both readers. The whole check's document, and four other commands' output, were the same before and after.

**Growth postponed, not changed.** The fast paths cut the cost of reading what grows, the answer files' YAML. They do not change how it grows: answer bytes still grow with the square of revalidations (COR-062 point 4). So they move the trigger later and do not remove it.

**PRJ-003.** PRJ-003 keeps dependencies minimal, and names a subcommand in a compiled language as the remedy for a hot path that crosses 500 ms cold. The whole check is such a hot path. That remedy is declined here: the fast paths met the bound in Python with no dependency added, where a compiled subcommand would bring a second language and its release work.

### Alternatives considered

- **A selection that judges the filler's pages alone** (#2365). It adds an interface to the check and a rule the engine is held to. Its saving after the fast paths is the smaller one. It is the first way weighed when point 2's condition fails.
- **Both now.** The check would take 2.9 seconds, inside #2365's third of the bound on the runners seen. It pays the selection's lasting cost now, for a margin #2410's half does not yet need. A person may prefer it, given how soon the slowest runners may cross the trigger.
- **A longer bound.** It changes ADR-057 point 3 for every query command, to fit one. The bound is one of the query contract's four limits.
- **A faster loader**, libyaml through its binding. It reads YAML 1.1, so some texts read differently, and it is a compiled dependency, which PRJ-003's minimal dependencies weigh against.
- **A cache kept across runs.** Keyed by git's object ids, which never change, it would be exact under point 1. But it is state to keep, and each project's CI must be set up to keep it.
- **Judging in parallel.** Workers would multiply the check's memory on runners with few cores, and order its findings by more code. It was not measured.
- **A warning in the check aggregator** when the doc check's line passes 15 seconds. It would give point 2's condition a signal instead of a reading by eye. It is project tooling, not built here; a person may ask for it with this record.
- **A runner that warns when any query nears its bound.** It would make such limits seen, for every query command in every project. It refines ADR-057 point 3, so it is a record of its own.

## Implications

- **The filler and its README stay as they are.** It reads `pkit friction check --all --json`.
- **The loader's version.** Tests hold the fast reader to the ruamel.yaml version the lock pins, and an install may resolve another within the declared range. The fast reader takes its types from the installed loader, but reads the form's syntax itself, and reads parts of the loader when the binary loads. So on another version its exactness is untested, and a version without those parts fails at load.
- **A sidecar's data** ([COR-063](../../../.pkit/decisions/core/COR-063-document-sidecars.md), [ADR-070](ADR-070-document-sidecar-place.md)). When the backbone reads data from a sidecar, the prefilter takes its cut from the one home of where a document's data lies, and searches a sidecar whole until then. A sidecar's YAML goes through the same fast reader as front matter.
- **The check aggregator prints each line's time,** so the doc check's time is one line of the CI log.
- **Recorded trigger to revisit.** The doc check's line on any of `main`'s CI runs takes more than 15 seconds. Or the filler gives no answer within its bound, here or as an adopter reports.
- **How soon.** The filler's 5.8 seconds on a laptop, runners 1.2 to 2 times slower and about a second of work around the filler put the line at about 8 to 13 seconds on CI. The growth since the fast paths, measured with single runs over a week, is too noisy to fix a date. On the slowest runners, the trigger may fire within weeks. Nothing warns before then: the maintainer reads the doc check's line.
- **Reopened,** a new measurement weighs the selection first, then both, a warning, and shrinking what grows, the answer files' `read` lists, which is COR-062's to change.
