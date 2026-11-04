---
id: DEC-008
title: SAN's diagram rules bind from a later major than its judgement rules
status: accepted
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** `SAN`'s two diagram rules, a diagram's facts and a text alternative, bind from a later major of `SAN` than the one that accepts its twelve judgement rules. Each major is a review for each adopter that follows it, so one that follows both reviews two. This overturns the passages of the record on the analysis's diagrams that put the diagram rules in the judgement rules' major.

## Context

The record on the analysis's diagrams gives `SAN` two rules, a diagram's facts and a text alternative ([software-analysis:DEC-003-analysis-diagrams] point 10). It has them join the major that accepts `SAN`'s other proposed rules, so adopters review one major, not two (COR-051 point 7).

Those other rules are the twelve judgement rules, RS-SAN-003 to RS-SAN-014. On 3 November the analyses the methodology ships with had been judged against them and mended, and the capability's maintainer accepted them ([project-kit#1727](https://github.com/aleskalfas/project-kit/issues/1727)). On that date the diagram rules were not built ([project-kit#1806](https://github.com/aleskalfas/project-kit/issues/1806)). Their checkable part needs a validator. The change that moves a pin to the major that accepts them owns each break their text settles (COR-060 point 1), so the analyses are judged and mended against them first. Other work rests on the twelve, such as the living documentation built on the analysis.

The capability's maintainer chose on 3 November, on [project-kit#1727](https://github.com/aleskalfas/project-kit/issues/1727), to accept the twelve without waiting for the diagram rules.

## Decision

The two diagram rules of [software-analysis:DEC-003-analysis-diagrams] point 10 bind from a later major of `SAN` than the one that accepts the twelve judgement rules. That later major is the first after the two rules join `SAN` as proposed rules and the analyses are judged and mended against them.

### What this overturns, and what stands

This record partially supersedes DEC-003. Each overturned passage stays in DEC-003 as it stood.
- **Overturned:**
  - point 10's heading, that the rules bind at `SAN`'s next major after the record
  - in point 10, "They join the major that accepts `SAN`'s other proposed rules, so adopters review one major, not two"
  - in the Rationale, "Why the rules wait for a major", that the rules share one major with `SAN`'s other proposed rules
  - in the Rationale's alternatives, the rejection of "the rules accepted in a major of their own" for its cost. This record accepts that cost.
  - in the Implications, "Projects", that a project adopts the rules at `SAN`'s next major
- **Stands:**
  - the two rules' text and their origin in DEC-003
  - their checkable part on a Mermaid fence, and images left to a reviewer
  - that until a major accepts them, they bind nothing
  - that a diagram's labels are statements of its artefact, which a judgement rule reads. It binds with the twelve, since RS-SAN-008 and RS-SAN-011 read those labels.
  - every other point of DEC-003, point 8 among them

## Rationale

The twelve rules were judged and mended, and other work rests on them. Holding them for the diagram rules would delay that work by a build and another round of judging and mending.

The cost is a second major for each adopter that follows both. When it ships, each set pinned at the twelve's major falls behind. No rule of `SAN` binds through it, and validation fails, until its project reviews the major and moves the pin (COR-051 point 7). The mends are no greater: the change that moves the pin owns each break the diagram rules settle in either case (COR-060 point 1).

### Alternatives considered

- **The twelve and the two diagram rules together, in one major,** as DEC-003 point 10 decides. Rejected: it saves each adopter one review, at the cost of delaying the twelve by a build and a round of mends.
- **The diagram rules in a method rule set of their own,** which an adopter inherits beside `SAN`. Accepting them would leave a `SAN` pin standing. Not taken: it also overturns DEC-003 point 10's "`SAN` gains two rules", and adds a set each adopter inherits.

## Implications

- **`SAN` 2.0.0** accepts RS-SAN-003 to RS-SAN-014, and not the diagram rules.
- **The diagram rules** join `SAN` as proposed rules ([project-kit#1806](https://github.com/aleskalfas/project-kit/issues/1806)), which needs only a minor version of `SAN`. A later major accepts them, and project-kit's own set moves its pin to it ([project-kit#2625](https://github.com/aleskalfas/project-kit/issues/2625)).
- **DEC-003** stays accepted, and its top line reads that this record partially supersedes it, naming point 10.
- **DEC-005's rule** joins the twelve's major, as DEC-005 says. Nothing in DEC-005 changes.
- **The software-analysis README and the `analysis-author` skill** say nothing of the diagram rules' major, so neither changes. The README describes the diagram rules once [project-kit#1806](https://github.com/aleskalfas/project-kit/issues/1806) adds them.
