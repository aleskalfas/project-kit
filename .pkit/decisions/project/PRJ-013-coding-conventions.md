---
id: PRJ-013
title: project-kit writes names, docstrings and comments plainly in each module's manner, and its conventions corpus holds coding conventions only
status: accepted
date: 2026-11-04
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a change to project-kit's code writes its names, docstrings and comments plainly and precisely, in the manner of the module it changes. Where there is no module to follow, ordinary good engineering judgement sets the manner. No convention requires a docstring. Each of these is a judgement, so a reviewer raises a departure as advisory and never blocks on it. The page the agents' overlay names as project-kit's conventions corpus holds coding conventions only. The producer and the reviewers read all it holds as rules for the code.

## Context

The software-engineering capability's producer agent writes code to the project's conventions corpus, the documents the agents' overlay names as `project-conventions` ([software-engineering:DEC-001-producer-agent-and-conventions-seam] point 2). Its definition holds no coding opinion of its own, since those live only in the corpus (point 3). The capability's code-review panel reads the project's own rules from the same corpus ([software-engineering:DEC-002-code-review-panel] point 4). It blocks only on an objective failure of a change, and raises softer findings as advisory (point 3). project-kit runs that panel on its own pull requests ([PRJ-009](PRJ-009-self-adopt-code-review-panel.md)).

project-kit named no corpus. Instead, each builder's brief repeated the convention: follow the code around you, with plain, precise names and docstrings. The reviewers never read that brief, so they had no rule to judge a change by. #2641 gives project-kit a corpus of one page. A convention that later work builds on starts with its record ([COR-065](../core/COR-065-records-and-projection.md) point 3), and this record decides the conventions that page states.

## Decision

**A change to project-kit's code writes its names, docstrings and comments plainly and precisely, in the manner of the module it changes. No convention requires a docstring. Both are judgements, so a departure is advisory. The corpus the overlay names is one page, which holds coding conventions only.**

### 1. Names, docstrings and comments are plain and precise, in the module's manner

A change to project-kit's code, its tests or its scripts writes its names, docstrings and comments plainly and precisely. It writes them in the manner of the module it changes, but a module with cryptic names licenses none in the change. Where there is no module to follow, as in a new module, test file or script, this point gives no manner. Ordinary good engineering judgement sets it there, as it does where the corpus is empty ([software-engineering:DEC-001-producer-agent-and-conventions-seam] point 5).

### 2. No convention requires a docstring

Point 1 says how a docstring is written, never where one must be. Code with no docstring breaks no convention, and whether code needs one is judged in each change.

### 3. Points 1 and 2 are judgements

Whether a name, docstring or comment is plain and precise in its module's manner is a judgement. So is whether code needs a docstring. A reviewer raises a finding under point 1 or 2 as an `[advisory]` finding ([project-management:DEC-028-agent-as-approver-paths], "Finding tags"), never as a block.

### 4. The corpus holds coding conventions only

The overlay names one page as project-kit's conventions corpus, and the page holds coding conventions only. The producer and the panel read only what the overlay names ([software-engineering:DEC-001-producer-agent-and-conventions-seam] point 2, [software-engineering:DEC-002-code-review-panel] point 4). So the page may point to a coding convention that an accepted record or another document holds. That convention keeps its home, and its force, there. An instruction on how to work, such as which checks a builder runs, lives outside the corpus.

## Rationale

**Why the module's manner.** A change written in its module's manner reads as part of it, whoever wrote it. The tree's code already differs by kind, such as the package, the capabilities' scripts, the permission hook and the tests. A manner written once for the whole tree would fit each kind less well than its own modules do. The norm stands apart from its reference, so a module's cryptic names do not spread with each change. The mechanical style is settled already: ruff lays out and lints the code, and pyright checks its types ([PRJ-010](PRJ-010-type-checking-mode.md)).

**Why no convention requires a docstring.** The panel's `docs-reviewer` reads from the corpus the docstring style a project requires. Its definition also has it block new public surface left undocumented, where the corpus declares a documentation convention. Point 1 names docstrings, so without point 2 it could be read as such a convention.

**Why a departure is advisory.** Whether a name is plain is a judgement, on which the panel never blocks, for the reasons [software-engineering:DEC-002-code-review-panel] gives for point 3. Naming the `[advisory]` tag rules out a `[person]` finding too. That finding is no block either, yet it holds a landing authorised up front ([project-management:DEC-055-pr-lists-answers] point 3).

**Why coding conventions only.** The producer self-checks its code against the corpus ([software-engineering:DEC-001-producer-agent-and-conventions-seam] point 4), and the panel judges a change by it. An instruction on how to work is nothing the code can meet, so it has no place among rules for the code. A convention held elsewhere keeps its one home, as that record's "Why conventions-thin" and [COR-065](../core/COR-065-records-and-projection.md) point 1 keep content in one place.

### Alternatives considered

- **No corpus, with the conventions left in each builder's brief.** Rejected: the reviewers never read a brief, and a brief is written again for each session.
- **The overlay names the documents that hold conventions now,** `CONTRIBUTING.md` and `tests/README.md`, beside the page or in its place, as [ADR-013](../../../tech-docs/architecture/decisions/ADR-013-conventions-discovery-seam.md) point 3 allows. Rejected: an overlay entry is a whole file, and both mix in sections on how to work, which the reviewers would read as rules.
- **The conventions as a rule set** ([COR-051](../core/COR-051-rule-sets.md)). Not taken. A convention starts with its record (COR-065 point 3). An accepted rule whose origin states it only stands in for one (COR-065 point 1, core rule 23). [software-engineering:DEC-004-skeleton-conventions-in-corpus] points 2 and 3 provide for a corpus that is no rule set. A rule set scoped over the code would bring every code file under a rule. The rule-set reviewer would then be drawn onto each code pull request, and core rule 24 would hold every builder to those rules. A finding under point 1 or 2 could become a `[person]` finding, the opposite of point 3.

## Implications

- **The corpus page,** `tech-docs/coding-conventions.md`, anchors points 1 to 4 and states each convention as this record decides it.
- **The agents' overlay** names that page, and only that page, as `project-conventions`.
- **Nothing checks point 1.**
- **Not decided here:** how a later convention joins the page, beyond COR-065 point 3, under which each starts with its record. A rule set may become due at the first convention a person should judge, or once the page holds more than a handful.
