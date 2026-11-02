---
id: UC-070
title: Choose the parts of each kind of analysis artefact as I adopt software analysis
status: active
actor: core:ACT-adopter
other-actors:
  - core:ACT-ai-agent
  - core:ACT-operator
requirements:
  - REQ-050
  - REQ-051
  - REQ-053
shortfalls:
  - at: 5
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/skills/analysis-author/choose-templates.md
        - .pkit/capabilities/software-analysis/schemas/artefact-kinds.yaml
        - .pkit/capabilities/software-analysis/schemas/structures.schema.json
        - .pkit/capabilities/software-analysis/scripts/_lib/project_structure.py
        - .pkit/capabilities/software-analysis/scripts/new.py
        - .pkit/capabilities/software-analysis/scripts/validate.py
      record:
        - software-analysis:DEC-001#1
        - ADR-034#1
        - COR-005
        - COR-013
        - COR-017
        - COR-023
        - COR-031
        - COR-051#7
      artefact:
        - REQ-050
        - REQ-051
        - REQ-053
---

# UC-070 — Choose the parts of each kind of analysis artefact as I adopt software analysis

**Goal:** Choose the parts of each kind of analysis artefact as I adopt software analysis, keeping, relabelling or adding to the shipped ones.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): walks the choice through the `analysis-author` [skill](../../../../core/glossary.md#term-skill--skill). It writes an entry of the [project](../../../../core/glossary.md#term-project--project)'s own structures only once the adopter accepts it ([REQ-050](../../../requirements/functional/REQ-050-agent-proposes.md)).
- **Operator** (`core:ACT-operator`): is asked before `pkit analysis new` writes in a repository other than the session's own, so no such write happens silently ([core:REQ-012](../../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:** None.

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has software-analysis installed, or registered in place where software-analysis is developed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-031](../../../../../../.pkit/decisions/core/COR-031-capability-origin.md)). The [adapter](../../../../core/glossary.md#term-adapter--adapter) deploys the `analysis-author` [skill](../../../../core/glossary.md#term-skill--skill) ([COR-005](../../../../../../.pkit/decisions/core/COR-005-bundle-pattern.md) and [COR-013](../../../../../../.pkit/decisions/core/COR-013-agent-architecture.md)).
- Installing the [capability](../../../../core/glossary.md#term-capability--capability) created the project's [rule set](../../../../core/glossary.md#term-rule-set--rule-set) `ANALYSIS`, which inherits `SAN`, where no rule set of the project's own inherited it (COR-017).
- The [backbone](../../../../core/glossary.md#term-backbone--backbone) answers where each [rule](../../../../core/glossary.md#term-rule--rule) binds, through `pkit rule-sets reach`, and where a proposed rule would bind with `--preview` ([COR-051 point 7](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind)).
- `pkit validate` checks `structures.yaml` against its schema, with the project's other data ([COR-023](../../../../../../.pkit/decisions/core/COR-023-schema-binds-inline.md)).

**Trigger:** The adopter has installed software-analysis, and is about to write the first [artefact](../../../../core/glossary.md#term-artefact--artefact) or record of a kind.

**Main path:**

1. The adopter asks an AI agent to walk each kind's parts with the `analysis-author` [skill](../../../../core/glossary.md#term-skill--skill)'s `choose-templates.md`. The agent takes one kind at a time, in the order the skill gives.
2. The agent finds the [project](../../../../core/glossary.md#term-project--project)'s own [rule set](../../../../core/glossary.md#term-rule-set--rule-set) that inherits `SAN`, through which the format [rule](../../../../core/glossary.md#term-rule--rule) binds on the [analysis](../../../glossary.md#term-analysis--analysis) ([COR-051 point 7](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind)).
3. For the kind, the agent shows the adopter its shipped parts. The kind's template, rendered from its [declared structure](../../../glossary.md#term-declared-structure--declared-structure), shows each part with its [hint](../../../glossary.md#term-hint--hint) and its example.
4. The adopter picks a real case of the project. The agent stamps a [candidate](../../../glossary.md#term-candidate--candidate) of the kind with `pkit analysis new`, and commits nothing.
5. At its entry, before it writes, the [system](../../../../core/glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses ([core:REQ-012](../../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).

> [!WARNING]
> **Not built yet:** `pkit analysis new` runs no such check, and writes in whatever repository holds its working directory. [ADR-034 point 1](../../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

6. The system writes the candidate whole, each part holding its hint. A [use case](../../../glossary.md#term-use-case--use-case), a journey or a requirement takes the next free number ([REQ-051](../../../requirements/functional/REQ-051-id-names-one-artefact.md)).
7. The agent fills each part as its hint says, and runs `pkit analysis validate --preview`.
8. The system holds the candidate to its kind's declared structure where the format rule binds. Where a proposed rule would bind, it reports what that rule would find as `preview:`, and never fails on it ([DEC-001 point 1](../../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#1-what-it-keeps-and-in-what-shape) and [REQ-053](../../../requirements/functional/REQ-053-structure-binds-where-the-rule-binds.md)).
9. The adopter reads the filled candidate part by part, and chooses: keep the shipped parts, relabel a part, or add parts of the project's own.
10. Where the adopter changes a part, the agent proposes the entry for `.pkit/capabilities/software-analysis/project/structures.yaml`, and writes it once the adopter accepts it ([REQ-050](../../../requirements/functional/REQ-050-agent-proposes.md)):
    - a new label, hint or example, under `relabel` or `front-matter`, which names no rule
    - a [tightening](../../../glossary.md#term-tightening--tightening) under `tighten`, which names a rule of the project's own, written first as `proposed`
11. The adopter runs `pkit validate`. The [capability](../../../../core/glossary.md#term-capability--capability)'s check, which `pkit validate` runs, holds the file to the kind's shipped structure, and reports nothing.
12. The agent sets the first candidate aside, outside the analysis, and stamps the candidate again. The [stamp](../../../../core/glossary.md#term-stamp--stamp) writes the project's parts, each added part's hint naming its rule. The agent fills it and previews it.
13. The adopter compares the two candidates side by side, and keeps the entries that read better.
14. The adopter keeps the candidate that describes the project truly, deletes any other, and commits the candidate with `structures.yaml`. The path goes on at step 3 for the next kind.

**Variants:**

- **2a.** No [rule set](../../../../core/glossary.md#term-rule-set--rule-set) of the [project](../../../../core/glossary.md#term-project--project)'s own inherits `SAN`. The agent writes one as the [capability](../../../../core/glossary.md#term-capability--capability)'s README shows, with a scope that selects the [analysis](../../../glossary.md#term-analysis--analysis) by its types. Without it, the preview shows nothing of a [candidate](../../../glossary.md#term-candidate--candidate)'s structure ([DEC-001 point 1](../../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#1-what-it-keeps-and-in-what-shape)).
- **3a.** The kind is the [revalidation record](../../../glossary.md#term-revalidation-record--revalidation-record)'s. Its template shows each part's example alone, since its [stamp](../../../../core/glossary.md#term-stamp--stamp) writes every part from its command line. The adopter may relabel its parts, and adds none, since no [rule](../../../../core/glossary.md#term-rule--rule) binds on a record ([DEC-001 point 1](../../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#1-what-it-keeps-and-in-what-shape)).
- **3b.** The kind is one of the three kinds of requirement, which share their fields and every part but one. The agent shows the three together, and the path goes on at step 4 for each in turn.
- **4a.** The kind needs another [artefact](../../../../core/glossary.md#term-artefact--artefact) first. A journey needs two [use cases](../../../glossary.md#term-use-case--use-case) of its actor, and a domain-model view needs the terms it explains. The agent stamps those first.
- **9a.** The adopter keeps the shipped parts. The agent writes nothing for the kind, and the path goes on at step 14.
- **9b.** The adopter finds a shipped part wrong. Mending the part is an edit to the capability, so the adopter asks for it with `pkit report change-request`, through the `report-author` [skill](../../../../core/glossary.md#term-skill--skill). The project keeps the part meanwhile ([DEC-001 point 1](../../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#1-what-it-keeps-and-in-what-shape)).
- **10a.** The adopter would drop, loosen or reorder a shipped part, or add a form or a kind. No entry can say so, and the agent proposes none ([DEC-001 point 1](../../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#1-what-it-keeps-and-in-what-shape)).
- **10b.** The [tightening](../../../glossary.md#term-tightening--tightening) would add to the revalidation record's kind. The file's schema refuses it, since no rule binds on a record. The adopter may relabel the record's parts instead ([DEC-001 point 1](../../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#1-what-it-keeps-and-in-what-shape)).
- **11a.** The file breaks, such as by a key its schema does not take, or a part its kind does not hold. The [system](../../../../core/glossary.md#term-system--system) reports each fault as an error where it lies, and applies none of the file. The stamp refuses while the fault stands. The adopter mends the file, and the path rejoins at step 11.
- **11b.** A tightening names a rule that is no rule of the project's own, which is an error. One whose rule is superseded or withdrawn is reported with the rule that replaces it, and binds nothing. The rest of the file applies.
- **12a.** The tightening's rule is proposed. The added part binds nothing yet, and the preview places it where the rule would bind ([DEC-001 point 1](../../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#1-what-it-keeps-and-in-what-shape)).
- **14a.** Neither candidate describes the project truly. The adopter deletes both before committing, so neither takes an id, and the path goes on at step 3 for the next kind.

**Postconditions:** Each kind's parts are chosen: the shipped parts kept, or the [project](../../../../core/glossary.md#term-project--project)'s relabels and [tightenings](../../../glossary.md#term-tightening--tightening) in its own `structures.yaml`. Each tightening names the [rule](../../../../core/glossary.md#term-rule--rule) that asks for it.

**Minimal guarantees:**

- No entry drops, loosens or reorders a shipped part, since the file's schema takes no key for it ([DEC-001 point 1](../../../../../../.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md#1-what-it-keeps-and-in-what-shape)).
- A file that breaks applies none of itself, so no [candidate](../../../glossary.md#term-candidate--candidate) is checked against half of it (`project_structure.py`).
- A refused [stamp](../../../../core/glossary.md#term-stamp--stamp) leaves every file as it was (`stamp.py`).
- `pkit analysis validate` is a query, which changes no file of the [project](../../../../core/glossary.md#term-project--project) ([core:REQ-005](../../../../core/requirements/quality/REQ-005-reading-writes-nothing.md) and `validate.py`).
