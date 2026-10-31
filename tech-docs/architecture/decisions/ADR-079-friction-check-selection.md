---
id: ADR-079
title: A reader can have the whole-repository check judge only the artefacts it names
status: proposed
date: 2026-10-31
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a reader that needs a few artefacts' state can ask `pkit friction check --all` to judge only those, named by their locations. Each is judged by the one judgement the whole check gives it, so the reader pays for their judgements and not for every artefact's. The measures stay the whole repository's, since a reader such as the documentation check reads them, and the document says which artefacts it was asked to judge.
- **Why:** living-docs' documentation check reads its pages' state and the uncovered surface. Judging all of project-kit's artefacts to read its pages took longer than the 30 seconds the backbone gives a query command, on some CI runners ([project-kit#2365](https://github.com/aleskalfas/project-kit/issues/2365)).
- **What it rests on:** an artefact's judgement never reads another artefact's judgement. This record ties the friction engine to that, which the whole-repository check's meaning already implies.

## Context

The whole-repository check judges every artefact at HEAD, each against its own revalidation point (COR-050 point 6). The debt listing and the explanation of one artefact are reading commands beside it (point 13), and the explanation's findings are those the check reports for that artefact. A component that needed the state of a few artefacts had only the whole check to read, through the engine's reading command ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 1), and filtered its document.

living-docs' documentation check fills a data point whose inert policy is `fail`, and the backbone bounds it as it bounds every query command (ADR-057 points 3 and 5). On project-kit's own tree it judged 386 artefacts to read 24 pages. It took about 15 seconds alone on a laptop and crossed 30 seconds on some CI runners. A resolver started late in the run was clipped by the time left, which is the "an anchor's resolver gave no answer" form of the same failure.

No accepted record provides a selection. COR-056 point 5 rules out one by type: no friction check reads a type. Nor can the filler judge only what a change touches: no base named for one run reaches a filler, and a filler does not compare the branch at hand with settled state (COR-052 point 6).

## Decision

**A reader can have the whole-repository check judge only the artefacts it names by location, each by the check's one judgement of an artefact. That judgement never reads another artefact's judgement. What is not one artefact's judgement stays the whole repository's or is not given, and the document says it is a selection.**

### 1. A selection of the whole-repository check

A reader can ask the whole-repository check to judge only the artefacts at the locations it names. Each is judged by the same judgement the whole check and the explanation give it, on one reading of HEAD and its history, and nothing else is judged. Without a selection, the check is the whole-repository check of COR-050 point 6, unchanged. Readers that publish or record the debt read the whole check only: the debt listing, project-kit's tracking report ([ADR-055](ADR-055-first-adopter-analysis-and-living-docs.md) point 5) and the job that writes an artefact's status (COR-050 point 10).

### 2. No judgement reads another's

An artefact's judgement reads HEAD, the history, the artefact's own answers and what its anchors stand on, never another artefact's judgement or state. This is what judging each artefact against its own revalidation point means (COR-050 point 6). An artefact anchor stands on its target's content, never on the target's state (point 5), and truth-chain order orders only the report (point 11).

State a run keeps from one artefact to the next is of three kinds only:
- **A memo** of something computed from history alone, keyed by a commit or a file's version.
- **A resolver's answer** for an anchor's value, kept for the run (COR-050 point 2). The resolver reads the working tree, and a resolver gives the same output for the same input by its declared obligation (ADR-057 point 4), so the answer is the same whichever artefact asked first.
- **Whether an anchor gets an answer at all.** A resolver that overran its bound is not started again in the run (ADR-057 point 3), and a run inside another has less time left for what it does later (ADR-057 point 5).

So where every anchor of an artefact gets an answer in both runs, a selection judges it as the whole check does. Whether an anchor gets an answer depends on its resolver and on the time left, and can differ between two runs in either direction. A change that would let one artefact's judgement read another's supersedes this point first. A test pins, for each artefact of a set of fixtures, that a selection judges it as the whole check does. The set covers a collection entry, a chain of artefact anchors and a deferral.

### 3. What stays whole

A selection narrows the judgements alone. The measures (COR-050 point 8) stay the whole repository's: they are facts about the repository a reader may need, as the documentation check needs the uncovered surface, and judging an artefact computes none of them. A selection still costs reading HEAD, the history and HEAD's answers, and the measures, with every resolver they run.

Which answer files a prune would remove (COR-062 point 8) reads every artefact's answers, so a selection does not give it. The CLI reference lists what the document holds under a selection.

### 4. The interface

- **`--artefact <location>`,** repeatable, and **`--artefacts-from <file>`,** a list of locations one a line, with `-` for standard input. Together they name the union, and an empty list judges none. Standard input that is a terminal is refused.
- **A location, exactly as discovery gives it.** A selection is matched against HEAD's locations as written, so a caller can compare its list with what the check read back. Looking an artefact up by id, with the refusals that brings, is the explanation's.
- **When the list is read** is no part of the contract. The check may read it as late as just before it judges, so a caller may start the check and write the list while it computes it, and no caller relies on when.

### 5. The document says it is a selection

The check's document gains `selection`. For the whole check it is `null`. Under a selection it holds `named`, the locations named, and `absent`, those HEAD holds no artefact at, and the human view's header says the same. A check that is dormant judges nothing and gives `null`. Under a selection, and only there, the document's `prunable` is `null`. The whole check's document changes only by the added key, so its `schema_version` stays 1.

### 6. What a caller owes

A caller that writes the list late and cannot finish it discards the answer. Standard input cannot tell a list cut short from a whole one, so a caller that wrote the list compares `selection.named` with it, as sets, and takes any difference for no answer.

## Rationale

**Why a selection keeps the filler's contract.** The filler is still started with `--json` alone, and its value is a function of state (COR-052 point 6). It computes the list from the working tree, its own input, and the list changes what the filler pays, not what it answers. The check reads locations, never a type, so COR-056 point 5 holds. That a capability decides which artefacts are its own decides nothing about any judgement, by point 2.

**Why an option, not another command.** The work is the whole check's, and so is the document, so its readers keep one shape and one version (COR-004). The explanation already shows that one artefact's judgement has a home of its own. A selection reads as a contradiction of `--all` only until one sees it as a selection of that check.

**Why the late list is no query input.** The rule that a query takes at most one subject (ADR-057 point 3) binds the commands the backbone runs for a component. This is the engine's reading command, which a filler calls (ADR-057 point 1). The backbone never hands a filler a list, and a check left waiting on its input is ended with the outermost run's process group (ADR-057 point 5).

### Alternatives considered

- **Filter the whole check in the filler.** Its time followed every artefact of the repository and crossed the bound.
- **Select by type.** COR-056 point 5 rules it out.
- **Raise the bound, or make it configurable.** ADR-057 keeps one bound, and raising it would weaken every query to hide one cost.
- **A separate reading command.** It would restate the document's contract.
- **The explanation over many artefacts.** Its document carries traces, diffs and bodies, heavier than the check's.
- **Name the pages on the command line, once read.** The filler then waits for its own reading of the pages before the check starts: about 9.8 seconds against 7.4 on project-kit's tree, with a command line that grows with the pages.
- **Leave the measures out of a selection,** as the prune is. The documentation check reads the uncovered surface, so it would need a second reading.
- **A faster YAML loader, or parsed answer files kept between runs.** Either cuts the cost that a selection leaves, below. Neither is ruled out, and each needs a decision of its own: a C loader is a new dependency and parsed differently in a trial, and a store kept between runs needs a place and a rule for when it is stale.

## Implications

- **The engine** takes a selection, and ADR-057 point 2's homes gain the judgement of one artefact.
- **The CLI reference** documents both options, what the document holds under a selection and the `selection` key.
- **living-docs' documentation check** starts the check with `--artefacts-from -` beside its other readings, hands it the pages once it knows them, and compares `selection.named` with them.
- **What a selection leaves.** Reading HEAD's answers, and every version of every answer file in history, in pure Python, grows with each change that adds answer files, in every project. Revisit the cost when the documentation check takes half the bound on project-kit's CI, or its time budget test fails.
