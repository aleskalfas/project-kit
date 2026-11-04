---
id: PRJ-013
title: project-kit's code follows the code around each change, and its conventions corpus holds coding conventions only
status: proposed
date: 2026-11-04
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a change to project-kit's code follows the code around it. Its names, docstrings and comments are written as plainly and precisely as the module it changes writes its own. The conventions say how a docstring is written, never where one must be. A departure from them is a judgement call, which a reviewer raises as advisory and never blocks on. The page the agents' overlay names as project-kit's conventions corpus holds coding conventions only, since the code reviewers judge a change by every rule it holds.

## Context

The software-engineering capability's producer agent writes code to the project's conventions corpus, the documents the agents' overlay names as `project-conventions` ([software-engineering:DEC-001-producer-agent-and-conventions-seam] point 2). Its definition holds no coding opinion of its own, since those live only in the corpus (point 3). The capability's code-review panel reads the project's own rules from the same corpus ([software-engineering:DEC-002-code-review-panel] point 4). It blocks only on an objective failure of a change, and raises softer findings as advisory (point 3).

project-kit named no corpus. Instead, each builder's brief repeated the convention: follow the code around you, and write plain, precise names and docstrings as the existing code writes them. The reviewers never read that brief, so they had no rule to judge a change by. #2641 gives project-kit a corpus of one page. A convention that later work builds on starts with its record ([COR-065](../core/COR-065-records-and-projection.md) point 3), and this record decides the conventions that page states.

## Decision

**project-kit's code follows the code around each change, in its names, docstrings and comments. The conventions owe no docstring, and a departure from them is advisory. The corpus the overlay names is one page, which holds coding conventions only.**

### 1. Code follows the code around the change

A change to project-kit's code, its tests or its scripts follows the code around it. It writes its names, docstrings and comments as plainly and precisely as the module it changes writes its own.

### 2. The conventions owe no docstring

The conventions say how a docstring is written, never where one must be. Code with no docstring breaks none of them.

### 3. A departure is advisory

A departure from these conventions is a judgement call. A reviewer raises it as an advisory finding, never as a block ([software-engineering:DEC-002-code-review-panel] point 3).

### 4. The corpus holds coding conventions only

The overlay names one page as project-kit's conventions corpus. The page holds coding conventions only. A coding convention that an accepted record or another document already holds keeps its home there, and the page points to it. An instruction on how to work, such as which checks a builder runs, lives outside the corpus.

## Rationale

**Why the code around the change.** A change that follows its module reads as part of it, whoever wrote it. A project-wide list of naming rules would be an inventory, and would drift from the code it describes. The mechanical style is settled already: ruff lays out and lints the code, and pyright checks its types ([PRJ-010](PRJ-010-type-checking-mode.md)).

**Why no docstring is owed.** More than half of project-kit's functions have no docstring. A convention that asked for one would make each of them a breach, raised on every change that touches it. Whether a function needs a docstring is judged in each change.

**Why a departure is advisory.** Whether a name is plain and precise is a judgement. A reviewer that blocks on a judgement turns the merge gate into a veto on taste, which the panel's threshold exists to prevent ([software-engineering:DEC-002-code-review-panel] point 3).

**Why coding conventions only.** The panel judges a change by every rule the corpus holds ([software-engineering:DEC-002-code-review-panel] point 4). An instruction on how to work, placed there, would become a rule that a reviewer holds a change to. A convention held in two places drifts, so one held elsewhere keeps its home and the page points to it.

### Alternatives considered

- **No corpus, with the conventions left in each builder's brief.** Rejected: the reviewers never read a brief, and a brief is written again for each session.
- **The conventions as a rule set** ([COR-051](../core/COR-051-rule-sets.md)). Not taken: a few one-line conventions need no versions, scopes or origins of their own, and this record gives them the acceptance a rule set's entries would have.
- **The corpus as `CONTRIBUTING.md`'s "Running checks".** Rejected: that section holds instructions on how to work, which the reviewers would read as rules.

## Implications

- **The corpus page,** `tech-docs/coding-conventions.md`, anchors points 1 to 4 and states each convention as this record decides it.
- **The agents' overlay** names that page, and only that page, as `project-conventions`.
- **Nothing checks point 1.** The software-engineer conforms to it, and the panel's reviewers raise a departure as advisory (point 3).
