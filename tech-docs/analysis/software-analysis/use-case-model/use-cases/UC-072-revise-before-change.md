---
id: UC-072
title: Revise the analysis before a proposed change is built
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
  - core:ACT-operator
requirements:
  - REQ-052
  - REQ-053
after:
  - [UC-070]
shortfalls:
  - at: 7
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/scripts/_lib/revalidation.py
        - .pkit/capabilities/software-analysis/scripts/_lib/pointers.py
        - .pkit/capabilities/software-analysis/scripts/check-pointers.py
        - .pkit/capabilities/software-analysis/scripts/check-numbers.py
        - .pkit/capabilities/software-analysis/scripts/_lib/shortfalls.py
        - .pkit/capabilities/software-analysis/schemas/revalidation-record.schema.json
        - .pkit/capabilities/software-analysis/skills/analysis-author/revalidation-record.md
        - .pkit/capabilities/software-analysis/skills/analysis-author/use-case.md
      record:
        - software-analysis:DEC-001#1
        - software-analysis:DEC-001#3
        - software-analysis:DEC-001#5
        - software-analysis:DEC-001#6
        - ADR-034#1
        - COR-005
        - COR-013
        - COR-017
        - COR-031
        - COR-050#3
        - COR-054#5
      artefact:
        - REQ-052
        - REQ-053
---

# UC-072 — Revise the analysis before a proposed change is built

**Goal:** Revise the analysis before a proposed change is built, naming the design I reviewed and pinning the text I read.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): may revise the [artefacts](../../../core/glossary.md#term-artefact--artefact) and draft the [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record) for the developer, through the `analysis-author` [skill](../../../core/glossary.md#term-skill--skill). The outcomes stay the developer's (variant 6b).
- **Operator** (`core:ACT-operator`): is asked before `pkit analysis new` or `pkit analysis link` writes in a repository other than the session's own, so no such write happens silently ([core:REQ-012](../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:** **From [UC-070](UC-070-choose-parts.md):** The [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record)'s kind has its parts chosen.

**Assumptions:**

- The [project](../../../core/glossary.md#term-project--project) has software-analysis installed, or registered in place where software-analysis is developed ([COR-017](../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-031](../../../../../.pkit/decisions/core/COR-031-capability-origin.md)). The [adapter](../../../core/glossary.md#term-adapter--adapter) deploys the `analysis-author` [skill](../../../core/glossary.md#term-skill--skill) ([COR-005](../../../../../.pkit/decisions/core/COR-005-bundle-pattern.md) and [COR-013](../../../../../.pkit/decisions/core/COR-013-agent-architecture.md)).
- The [change](../../../core/glossary.md#term-change--change)'s design lies in [decision records](../../../core/glossary.md#term-decision-record--decision-record) and notes in this repository, or in an issue in a tracker ([DEC-001 point 6](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#6-records-only-when-there-is-something-to-say)).
- The [answer](../../../core/glossary.md#term-answer--answer) each revised [artefact](../../../core/glossary.md#term-artefact--artefact) carries is recorded with the core's writers, as `core:UC-002` describes ([COR-050 point 3](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).
- The [backbone](../../../core/glossary.md#term-backbone--backbone) resolves the [default branch](../../../core/glossary.md#term-default-branch--default-branch), on which the [stamp](../../../core/glossary.md#term-stamp--stamp) and `pkit analysis check-pointers` locate each commit ([COR-054 point 5](../../../../../.pkit/decisions/core/COR-054-default-branch.md#5-one-computation-exposed)).

**Trigger:** A [change](../../../core/glossary.md#term-change--change) is proposed and its design written before its code, and the change touches what the [analysis](../../glossary.md#term-analysis--analysis) describes.

**Main path:**

1. The developer reads the [change](../../../core/glossary.md#term-change--change)'s design. For each [design source](../../glossary.md#term-design-source--design-source), the developer notes where it lies and a pointer to the text read. The pointer is a commit the [default branch](../../../core/glossary.md#term-default-branch--default-branch) holds, or the time a tracker's text was read.
2. The developer finds the [analysis](../../glossary.md#term-analysis--analysis) [artefacts](../../../core/glossary.md#term-artefact--artefact) the change touches: the [use cases](../../glossary.md#term-use-case--use-case) whose steps it changes, and the terms, actors and requirements it names.
3. For each, the developer judges whether it still holds against the design, and gives it a [revalidation outcome](../../glossary.md#term-revalidation-outcome--revalidation-outcome) ([DEC-001 point 5](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#5-revalidation)).
4. Where an accepted [decision record](../../../core/glossary.md#term-decision-record--decision-record) decides a step the code lacks until the change lands, the developer writes the step as that decision record decides. The step takes its box and its entry in `shortfalls`, naming that record and the issue that tracks building it (DEC-001 points [1](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#1-what-it-keeps-and-in-what-shape) and 5).
5. The developer records each artefact's [answer](../../../core/glossary.md#term-answer--answer), `updated` where it changed, as `core:UC-002` describes.
6. The developer runs `pkit analysis new revalidation <slug> --trigger planned`, naming the change, each artefact's `--outcome` and `--because`, each gap's `--gap`, and each design source's `--reviewed-against` ([DEC-001 point 6](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#6-records-only-when-there-is-something-to-say)).
7. At its entry, before it writes, the [system](../../../core/glossary.md#term-system--system) checks that the repository it would change is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses ([core:REQ-012](../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).

> [!WARNING]
> **Not built yet:** `pkit analysis new` runs no such check, and writes in whatever repository holds its working directory. [ADR-034 point 1](../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

8. The system checks the request. Each artefact must be one the analysis holds, and each outcome must have its justification. Each regression and gap found must be named by a `--gap`, and each design source must have its form. The system writes the [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record) whole, as `revalidations/<date>-<slug>.md`, naming git's user as who performed it ([REQ-052](../../requirements/functional/REQ-052-record-only-with-something-to-say.md)).
9. The developer runs `pkit analysis validate`. The system holds the revalidation record to its schema and to its kind's [declared structure](../../glossary.md#term-declared-structure--declared-structure). It holds each box to its entry in `shortfalls`, whatever any [rule](../../../core/glossary.md#term-rule--rule)'s status (DEC-001 points 1 and 6, and [REQ-053](../../requirements/functional/REQ-053-structure-binds-where-the-rule-binds.md)).
10. The developer runs `pkit analysis check-pointers`. The system places each commit a design source names on the default branch, finds each held, and passes (DEC-001 point 6).
11. The developer runs `pkit analysis check-numbers`. The system finds no step or variant of a revised use case renumbered or removed, where the append-only rule binds, and passes ([DEC-001 point 3](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#3-identifiers)).
12. The developer commits the revalidation record in the same change as the answers on the artefacts it covers.

**Variants:**

- **1a.** A [design source](../../glossary.md#term-design-source--design-source) lies in this repository and lands with the [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record), such as a design note. Its pointer is `this change`, and the commit that adds the revalidation record pins it ([DEC-001 point 6](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#6-records-only-when-there-is-something-to-say)).
- **1b.** A design source lies outside this repository, such as an issue's body. The revalidation record names it with its link, and its pointer is the time its text was read, in UTC ([DEC-001 point 6](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#6-records-only-when-there-is-something-to-say)).
- **1c.** On the path of 1b, the design source lies in another repository. Its pointer may be a commit's full id there, in place of a time ([DEC-001 point 6](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#6-records-only-when-there-is-something-to-say)).
- **3a.** Every [artefact](../../../core/glossary.md#term-artefact--artefact) the [change](../../../core/glossary.md#term-change--change) touches holds against the design. The revalidation record is written all the same, since a planned [revalidation](../../glossary.md#term-revalidation--revalidation) always leaves one ([DEC-001 point 6](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#6-records-only-when-there-is-something-to-say)).
- **4a.** No accepted [decision record](../../../core/glossary.md#term-decision-record--decision-record) decides the changed step yet, such as a design still under review. The developer revises no [use case](../../glossary.md#term-use-case--use-case) ahead of its code. The revalidation record still reviews the design, and each gap names what will resolve it ([DEC-001 point 5](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#5-revalidation)).
- **6a.** The [analysis](../../glossary.md#term-analysis--analysis) keeps a domain model, and a revised term or view moved a link between terms. The developer runs `pkit analysis link` first, as `UC-071` describes in its variant 3b.
- **6b.** An AI agent runs the [stamp](../../../core/glossary.md#term-stamp--stamp) for the developer. The agent names itself with `--by-agent`, and it names the developer with `--confirmed-by`. The stamp refuses an agent named alone.
- **6c.** A revised artefact adds or rewords a citation of a decision record, a point of one or a [rule](../../../core/glossary.md#term-rule--rule). The developer runs `pkit analysis link` first, as `UC-071` describes in its variant 3d.
- **8a.** The stamp refuses, such as for a planned revalidation record without `--reviewed-against`, a design source its schema refuses, or a gap no `--gap` names. It writes nothing, and says why (`revalidation.py`). The developer mends the command, and the path rejoins at step 6.
- **8b.** A design source names a commit the [default branch](../../../core/glossary.md#term-default-branch--default-branch) does not hold, such as a branch's commit. The [system](../../../core/glossary.md#term-system--system) writes the revalidation record all the same, and warns that `pkit analysis check-pointers` will fail the change ([DEC-001 point 6](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#6-records-only-when-there-is-something-to-say)). The source must name a held commit, or `this change`.
- **10a.** A revalidation record the change adds names a commit the default branch does not hold. The system fails, naming the revalidation record and the design source. The developer names the commit where the design landed, or `this change`, and the path rejoins at step 10.
- **10b.** A shallow clone's history stops before a commit a design source names. The system reports the commit as unknown, and never fails on it ([DEC-001 point 6](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#6-records-only-when-there-is-something-to-say)).
- **11a.** A revised use case renumbers or removes a step or a variant. The system fails, naming the use case and the step. The developer puts the step back under its number, and the path rejoins at step 11.

**Postconditions:** The [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record) names each [design source](../../glossary.md#term-design-source--design-source) with a pointer to the text read, and each [artefact](../../../core/glossary.md#term-artefact--artefact)'s [revalidation outcome](../../glossary.md#term-revalidation-outcome--revalidation-outcome). The artefacts describe the [change](../../../core/glossary.md#term-change--change) as its accepted [decision records](../../../core/glossary.md#term-decision-record--decision-record) decide it, with a box below each step the code does not carry out yet.

**Minimal guarantees:**

- A refused [stamp](../../../core/glossary.md#term-stamp--stamp) leaves every file as it was (`stamp.py`).
- A planned [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record) never lacks its [design sources](../../glossary.md#term-design-source--design-source), and one of any other trigger names none ([DEC-001 point 6](../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#6-records-only-when-there-is-something-to-say)).
- A commit that `pkit analysis check-pointers` cannot locate is reported as unknown, never as a failure (DEC-001 point 6).
- `pkit analysis check-pointers` and `pkit analysis check-numbers` are queries, which edit no file of the [project](../../../core/glossary.md#term-project--project) ([core:REQ-005](../../../core/requirements/quality/REQ-005-reading-writes-nothing.md)).
