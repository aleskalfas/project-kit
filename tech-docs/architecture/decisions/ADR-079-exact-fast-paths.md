---
id: ADR-079
title: A fast path gives exactly its reading's result or hands its input on, and the doc-check filler reads a selection of the check within a budget
status: accepted
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** any reading of the `pkit` binary may take a fast path, a second way of computing it, on one condition. The fast path gives exactly what the reading gives, or hands its input to the reading. A reading takes one where its cost grows with the repository, its history and its answers. living-docs' doc-check filler reads a selection of the whole-repository friction check: the check judges the filler's pages alone, each exactly as the whole check judges it, and its measures stay the whole repository's. A test fails the build once the filler's cost passes a budget, set at two-thirds of the filler's 30-second bound on the slower of CI's runners.
- **Why:** on CI the filler overran its bound, and both the doc check and `pkit validate` failed ([project-kit#2410](https://github.com/aleskalfas/project-kit/issues/2410)). With the fast paths alone, its cost passed the budget on most pull requests' runs ([project-kit#3509](https://github.com/aleskalfas/project-kit/issues/3509)).
- **What lasts:** the exact reading of YAML text is ruamel.yaml's pure-Python loader. The answer writer is held to the form the fast reader takes. The declared floor of ruamel.yaml rises to the oldest version the fast reader is tested against. The whole-repository check takes, as an option of its command, the artefacts it judges.
- **The measure:** on 4 November's tree, on a laptop, the median wall time of the whole check fell from 14.3 to 5.2 seconds, and of the filler from 14.7 to 5.8. On CI, where the filler had taken up to 30 seconds, it took about 7 on the runners measured. On 24 November's tree, the selection took the filler's cost from about 36 units to about 27, in process on a laptop.
- **What comes next:** the next step is weighed in a record of its own, when the budget test fails or the filler gives no answer within its bound, in project-kit's runs or as an adopter reports it (point 2).

**Why an ADR.** Point 1 sets a rule that later work builds on: how any reading of the binary may be sped up without a second home for any computation ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 2). Point 3 applies it to YAML text, whose exact reading, declared dependency and written form other work builds on. Point 2 adds to the backbone's command-line surface a selection of the whole-repository check, which a capability's filler calls, and whose shape [COR-004](../../../.pkit/decisions/core/COR-004-cli-surface.md) governs. The filler's reading of the selection follows from that, so the choice is the backbone's.

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

**The other way.** #2365 drafted a selection of the whole check that judges the filler's pages alone, built in #2412. #2410 asks that the filler leave half its bound on CI; #2365 asks that it answer within a third. The whole check's wall time in process on 3 November's tree, laptop:

| | Whole check |
|---|---|
| Before | 14.2 s |
| A selection alone | 8.9 s |
| Fast paths alone | 4.5 s |
| Both | 2.9 s |

A selection still reads HEAD, the history and HEAD's answers, and computes the measures (COR-050 point 8). It saves the judging of the other artefacts: 5.3 seconds before the fast paths, 1.6 after.

**Over the budget.** With the fast paths alone, the filler read the whole check, and the budget test held it to 32 units. On 24 November, four pull requests' runs on CI counted 32.3, 35.1, 33.7 and 34.2 units, and a rerun of the last failed too (#3509). On that day's tree, in process on a laptop, the whole check took 12.2 seconds of processor time, and a selection of the filler's 65 pages took 7.8. The pages' own judgements were most of what the selection kept: the CLI reference's alone took about a third of them.

## Decision

**Any reading of the binary may take a fast path, which gives the exact reading's result or hands its input to the exact reading. The doc-check filler reads a selection of the whole-repository check, which judges its pages alone, and a test fails the build once the filler's cost passes two-thirds of its bound. YAML text has one fast reader, of the plain block form.**

### 1. A fast path gives the exact result, or hands its input on

A *fast path* is a reading computed a second way, by a parse, a match or a search of its own. The reading it speeds is its *exact reading*. Any reading of the binary may take one, on one rule: the fast path gives exactly what the exact reading gives, or hands its input to the exact reading. A fast path that keeps the rule only carries out this record, so it needs no record of its own ([COR-065](../../../.pkit/decisions/core/COR-065-records-and-projection.md) point 3).
- **Exactly.** The same value, of the same types, with each mapping's keys and each list's members in the same order. An index over a listing so gives the members the pattern reading gives over every member, in its order. Where the exact reading fails, the fast path fails the same way, with the same error and message.
- **Its tests.** A fast path lands with tests that compare it with its exact reading, on inputs at the edges of its form at least, and they stay.
- **Not a fast path: a cache on the whole input.** A cache keyed on the whole input computes nothing a second way. It may keep a result for the life of the process, keyed on content, if it hands each caller its own copy of a value the caller may change.
- **A cache on part of the input is one.** A cache keyed on less than the whole input hands one input's result to another, so the rule binds it.
- **Not a fast path: the same reading run faster,** in parallel, say, or reading git in batches. It computes nothing a second way.
- **A prefilter.** A prefilter narrows what it searches only to the part of an input the parse reads data from. Where it cannot cut that part, it searches the whole input.
- **No dependency.** A fast path adds no dependency, since the project keeps its dependencies minimal ([PRJ-003](../../../.pkit/decisions/project/PRJ-003-implementation-language.md)).

Tests sample the difference and cannot prove it nil. What keeps a fast path exact beyond them is that it hands on every input it is not sure of.

**No second home.** A fast path is part of the reading it speeds, so each home of ADR-057 point 2 still computes its answer once. A fast path that several homes share is a home of its own, listed in ADR-057 point 2, as the fast reader of YAML text is (point 3).

### 2. The filler reads a selection of the check, within a budget

The filler reads its pages' states from a selection of the whole-repository check that judges its pages alone, and the uncovered surface from the measures of the same run.
- **The selection.** The whole check takes, as an option of its command, the locations of the artefacts it judges, and judges no other. Each is judged by the check's one judgement of an artefact, exactly as the whole check judges it. That judgement reads HEAD, the history, the artefact's own answers and what its anchors stand on, and never another artefact's judgement. A test holds, over a set of fixtures, that a selection judges each artefact as the whole check does.
- **What stays whole.** The measures (COR-050 point 8) and the count of answer files stay the whole repository's, since the filler reads the uncovered surface. Which answer files a prune would remove is a reading of every artefact's answers, so a selection does not give it. The check's document says what it was asked to judge, and the CLI reference states what the document holds under a selection.
- **Handed late.** The check may read the list as late as just before it judges, so the filler starts it beside its other readings and hands it the pages once it knows them. When the check reads the list is no part of its contract. The filler compares what the check says it was asked to judge with the pages it handed, and takes any difference for no answer.
- **The budget.** A test runs the filler on project-kit's own tree, and fails the build once the filler's cost passes a budget. The budget is about the cost at which the filler would take two-thirds of its bound, 20 seconds, on the slower of CI's runners.
- **Counted in units.** The cost is the filler's processor time, counted in units of a fixed parse by the exact reading of YAML text. So a slow runner and a fast one count alike.
- **On every run.** Answers alone grow the cost, so the short check runs the test too ([ADR-067](ADR-067-answers-only-short-check.md) point 8).
- **The next step.** A selection judges the pages, whose answers grow with each revalidation. So the next step is weighed in a record of its own when either holds:
  - the test fails, its budget passed;
  - the filler gives no answer within its bound, in project-kit's runs or as an adopter reports it.
- **The budget's number** is the test's. It is set again only to keep it at two-thirds of the bound, never to put the next step off.

### 3. YAML text has one fast reader, of the plain block form

- **The exact reading.** The exact reading of YAML text is ruamel.yaml's pure-Python safe loader, `YAML(typ="safe", pure=True)`, reading the text alone. A loader left to pick libyaml, through ruamel's compiled binding, reads YAML 1.1. So no fallback handed to the fast reader leaves `pure` unset.
- **One fast reader.** The binary holds one fast reader of YAML text. Every module of the binary that reads YAML text by a fast path calls it, and none writes its own.
- **The plain block form.** The fast reader takes this form alone. It is block mappings, each key plain and on a line of its own, and block sequences. Each value is on one line: a plain or quoted scalar, or a flow collection of those. Blank lines and comments may stand between. The loader's own resolver and constructor give every value its type.
- **Every doubt handed on.** On any doubt and any failure, the fast reader gives the text whole to the caller's own call of the loader. So every error raised is the loader's own.
- **No round trip.** A round-trip load, which keeps comments and order, has no fast path.
- **The loader's versions.** The fast reader copies how the loader reads its form, so it is on only under a version of ruamel.yaml the tests held it to. Under any other, the loader reads every text: an untested version is a doubt, handed on. It is off too where the installed loader lacks a part it takes as the binary loads.
- **The loader's range.** The declared range of ruamel.yaml starts at the oldest version the fast reader is held to, and sets no upper bound. An install below that floor would read every text at the loader's speed, as before the fast paths, and no later release would name its version tested. A newer version is a doubt a later release clears by testing it.
- **The form the backbone writes.** The answer writer writes answer files in the plain block form, so the reading that grows keeps the fast path. A test holds the writer to it. A second test holds every answer file of the project's own tree to it. An answer file edited by hand into another form still reads exactly, but fails that test.

## Rationale

**Why two-thirds of the bound.** The test must fail before the bound does, on any runner. Set on the slower of CI's runners, it fails while a run half again as slow as theirs still answers within the bound, and it sits above what a crowded run counts. Half the bound, #2410's criterion for the filler's time, would leave the filler less room to grow before the test fails, 1.4 times its cost on 4 November's tree against 1.9.

**Why a test that fails.** A warning that fails nothing is passed over, by an agent above all. So the filler's time would grow back to its bound unseen, as it did before #2410. A test fails the change that passes the budget, while the filler still answers.

**Why units.** Processor time counted in units of a fixed parse is about the same on a slow runner and a fast one. So the test gives one verdict for one tree. A budget in wall time would fail on a slow runner and pass on a fast one.

**Why one rule, and no record for each reading.** A fast path that keeps the rule changes no result: it gives the exact reading's, or the exact reading runs. So it decides nothing a record would weigh, and a record for each would weigh the same rule again. A second way that gives another result is no fast path. It changes what a reading gives, and the record that decides that reading decides it.

**The selection's lasting cost, and what it buys.** A selection adds an interface to the CLI, whose shape COR-004 governs, and which a capability's filler calls. The CLI reference documents it. Once a component's command calls it, a change to it breaks that component: a surface change, with its migration ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)). A selection does not bar a judgement that reads another's: such a judgement widens what a selection reads. On 4 November's tree, after the fast paths, it saved 1.6 seconds of 4.5, little for that cost while the budget held. On 24 November's tree it saved 4.4 seconds of 12.2, and the filler's cost fell within its budget. It composes with the fast paths: they speed the readings of YAML text that a selection makes, and a selection leaves out the judgements the filler does not read.

**Why an option of the whole check.** The work is the whole check's, and so is the document, so its readers keep one shape and one version (COR-004). A selection judges each artefact as the whole check does, and the document says which artefacts it was asked to judge, so a reader never takes a selection for the whole check.

**Why the list may come late.** The filler reads which documents are its pages beside the check. A check that took the pages only once the filler knew them would start after that reading, and the filler's time would be the two readings' added. One that reads the list just before it judges starts at once, so telling the pages costs it little time or none. A caller that hands the list on a stream cannot tell from the stream a list cut short from a whole one, so it reads back what the check was asked to judge.

**The larger saving.** On 4 November's tree the fast paths saved 9.7 seconds of the check, and a selection 5.3. The fast paths change no interface of the CLI and no document. They speed every reader of the same YAML, the change check and validation among them. Their own lasting cost is code: some 400 lines that copy the loader's reading of the block form, held exact under each tested version, and a writer's form that tests hold fixed.

**Why the rule keeps the fast paths exact.** A fast path that hands every doubt on can differ from the exact reading only where it misreads an input it is sure of. So the YAML form is kept narrow, the plain block form of point 3. Tests compare the two readers over texts at the form's edges, and over texts made at random and cut short. Before landing, every YAML text in the repository's history, 9266 of them, read the same through both readers. The whole check's document, and four other commands' output, were the same before and after.

**Why the fast reader is held to tested versions, and the install is not.** The install resolves ruamel.yaml afresh, not from the lock, so it takes the newest version in range. Under a version no test compared, the fast reader could misread what that version reads anew, and nothing at load would see it. So point 3 turns it off there, and every text reads exactly, at the loader's speed. A bound on the install would buy no more exactness. It would hold the install off the loader's fixes until a release of the backbone widened it. What the bound leaves open costs only speed, until a release names the version tested.

**Growth postponed, not changed.** The fast paths cut the cost of reading what grows, the answer files' YAML. They do not change how it grows: answer bytes grow with the square of revalidations (COR-062 point 4). The selection leaves out the other artefacts' judgements, and the pages' own answers grow the same way. So both put off the budget's failure and do not remove it.

**PRJ-003.** PRJ-003 keeps dependencies minimal. It names a subcommand in a compiled language as a candidate for a hot path that crosses 500 ms cold. The whole check is such a hot path. That candidate is declined here: the fast paths met the bound in Python with no dependency added, where a compiled subcommand would bring a second language and its release work.

### Alternatives considered

- **The whole check, every artefact judged.** It adds no interface to the CLI, and the fast paths alone kept it within the budget on 4 November's tree. It pays for every artefact's judgement to read the pages', and passed the budget on 24 November's.
- **A reading command of its own.** It would restate the check's document and its contract, where an option of the check keeps one shape and one version.
- **The pages named on the command line, once read.** The check would start only once the filler had read its pages, and the command line would grow with the pages.
- **A selection by type.** The backbone would judge the documents of a type the filler names. No friction check reads a type ([COR-056](../../../.pkit/decisions/core/COR-056-artefact-types.md) point 5), and the filler's pages are what its walk tells, not a type.
- **A warning past half the bound.** The check aggregator would warn when the doc check's line took more than 15 seconds, and fail nothing. A warning is passed over, so the growth would reach the bound unseen.
- **A longer bound.** It changes ADR-057 point 3 for every query command, to fit one. The bound is one of the query contract's four limits.
- **A faster loader**, libyaml through its binding. It reads YAML 1.1, so some texts read differently, and it is a compiled dependency, which PRJ-003's minimal dependencies weigh against.
- **A cache kept across runs.** To be a cache on the whole input, it would be keyed on a version's object id and every other input of its reading: the place, the settings, the binary's version and the loader's. A key on the object id alone would make it a fast path that can hand out a stale result. Either way it is state to keep, and each project's CI must be set up to keep it.
- **Judging in parallel.** Workers would multiply the check's memory on runners with few cores, and order its findings by more code. It was not measured.
- **A runner that warns when any query nears its bound.** It would make such limits seen, for every query command in every project. It refines ADR-057 point 3, so it is a record of its own.

## Implications

- **The filler reads a selection of the check.** It hands the check its pages, and reads their states and the measures from the check's machine-readable document. The CLI reference documents the selection and what the document holds under it. The living-docs README, "The documentation check", says what the filler reads, and that its time grows with the repository's history and answer files.
- **ADR-057 point 2** lists the fast reader of YAML text among the homes, as its refinement per point 3.
- **The loader's version.** The fast reader is held to the ruamel.yaml version the lock pins, where the declared range starts. A release of ruamel.yaml turns it off on every install that resolves it, and the whole check runs at the loader's speed there. Moving the lock to it fails a test until the two readers are compared under it, and it is named tested.
- **A sidecar's data** ([COR-063](../../../.pkit/decisions/core/COR-063-document-sidecars.md)). When the backbone reads data from a sidecar, the prefilter takes its cut from the one module where a document's data lies, once that module lands ([ADR-070](ADR-070-document-sidecar-place.md) point 7). A sidecar's YAML goes through the same fast reader as front matter.
- **A change that grows the filler's cost past the budget** fails its own build, and the test names the next step as a record to weigh (point 2).
- **Recorded trigger to revisit.** Point 2's two: the budget test fails, or the filler gives no answer within its bound, here or as an adopter reports.
- **What that record weighs.** Shrinking what grows, the answer files' `read` lists, is COR-062's to change, and is weighed beside the readings a selection makes.
