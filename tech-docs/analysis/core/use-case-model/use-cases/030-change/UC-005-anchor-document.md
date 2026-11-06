---
id: UC-005
title: Say what my document rests on
status: active
actor: ACT-developer
other-actors: []
requirements:
  - REQ-004
  - REQ-005
  - REQ-006
  - REQ-007
  - REQ-015
  - REQ-020
after:
  - [UC-014, UC-049]
  - [UC-021, UC-023, UC-016]
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/friction_discovery.py
        - src/project_kit/friction_validate.py
        - src/project_kit/friction_check.py
        - src/project_kit/friction_repository.py
      record:
        - ADR-080#5
        - COR-050#1
        - COR-050#2
        - COR-050#3
        - COR-064#1
        - COR-050#6
        - COR-050#7
        - COR-050#8
        - COR-050#12
      artefact:
        - ACT-developer
        - REQ-004
        - REQ-005
        - REQ-006
        - REQ-007
        - REQ-015
        - REQ-020
---

# UC-005 — Say what my document rests on

**Goal:** Say what each of my documents rests on, so a change there reaches me.

**Other actors:** None.

**Preconditions:**

- **From [UC-014](../010-develop/UC-014-develop-methodology.md) or [UC-049](../050-adopt/UC-049-install-system.md):** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.
- **From [UC-021](../020-set-up/UC-021-declare-backbone-configuration.md), [UC-023](../020-set-up/UC-023-add-or-remove-capability.md) or [UC-016](../010-develop/UC-016-keep-capability.md):** Places that hold anchored [artefacts](../../../glossary.md#term-artefact--artefact) are declared. They are the project's own, in its [backbone configuration](../../../glossary.md#term-backbone-configuration--backbone-configuration), or those of a [capability](../../../glossary.md#term-capability--capability) the [manifest](../../../glossary.md#term-manifest--manifest) records ([COR-050 point 1](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#1-artefacts)).

**Assumptions:**

- The anchors name everything the document rests on. A [change](../../../glossary.md#term-change--change) to something no [anchor](../../../glossary.md#term-anchor--anchor) names asks the document nothing ([COR-050 point 6](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#6-friction-in-two-checks)).

**Trigger:** The developer writes a document that describes something in the repository, or finds that one rests on more than its anchors name.

**Main path:**

1. The developer lists the document's anchors in the `friction` block of its `pkit` front matter. Each names a path, a record or one of its points, or another [artefact](../../../glossary.md#term-artefact--artefact), one of its sections or its lead.
2. The developer runs `pkit validate`. Its `friction` member checks the block's shape and the cycles between artefacts. It checks each [anchor](../../../glossary.md#term-anchor--anchor) on a part of a record or a document too.
3. The developer runs `pkit friction check`. A document new in the [change](../../../glossary.md#term-change--change) counts as revalidated, and an anchor the change added that resolves to nothing is a `dead-anchor`, an error ([REQ-020](../../../requirements/functional/030-change/REQ-020-dead-anchor-error.md)).
4. The change lands on the [default branch](../../../glossary.md#term-default-branch--default-branch).
5. In each later change that modifies what one of its anchors names, the [change check](../../../glossary.md#term-change-check--change-check) asks the document for an [answer](../../../glossary.md#term-answer--answer) ([UC-002](UC-002-answer-stale.md)).

**Variants:**

- **1a.** The document lies in no declared [place](../../../glossary.md#term-place--place), so nothing reads its anchors. `pkit friction artefacts` lists the places. The developer adds the document's path to `friction.places`, and the path rejoins at step 1.
- **1b.** Nothing the repository holds makes the document true, such as a person's part in the work. A person accepts a reason for having no anchors, word for word, before it is written as `unanchored-because` (COR-050 points [1](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#1-artefacts) and [3](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)). A delegate a person named may decide it instead ([COR-064 point 1](../../../../../../.pkit/decisions/core/COR-064-answer-delegate.md#1-the-answers-a-delegate-decides)). The use case ends.
- **1c.** The document already carries anchors, and the developer changes the list. The [change check](../../../glossary.md#term-change-check--change-check) asks the document for a [revalidation answer](../../../glossary.md#term-revalidation-answer--revalidation-answer) in the same [change](../../../glossary.md#term-change--change) ([COR-050 point 6](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#6-friction-in-two-checks)), and the path goes on at step 2.
- **1d.** A [stamp](../../../glossary.md#term-stamp--stamp) writes the anchors, such as the command an installed [capability](../../../glossary.md#term-capability--capability) offers to create an [artefact](../../../glossary.md#term-artefact--artefact) of its kind. The path goes on at step 2.
- **1e.** A capability, not the [backbone](../../../glossary.md#term-backbone--backbone), resolves an [anchor](../../../glossary.md#term-anchor--anchor) the developer lists, through a [query command](../../../glossary.md#term-query-command--query-command) the capability registers. The check asks that command which files the anchor stands on, offline and within thirty seconds ([COR-050 point 2](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#2-anchors), [REQ-006](../../../requirements/quality/REQ-006-command-time-bound.md) and [REQ-007](../../../requirements/constraints/REQ-007-offline-same-answer.md)). A command that gives no result leaves the anchor `no-answer`, never read as unchanged ([REQ-004](../../../requirements/quality/REQ-004-missing-answer-never-clean.md)). The path goes on at step 2.
- **2a.** [Validation](../../../glossary.md#term-validation--validation) finds a fault in the block, and fails, naming it. The path rejoins at step 1. The faults it fails on are these:
  - a malformed block, or `unanchored-because` beside anchors
  - a cycle between artefacts
  - a [dead anchor](../../../glossary.md#term-dead-anchor--dead-anchor) on a part, or an ambiguous or refused one
- **2b.** A [documentation root](../../../glossary.md#term-documentation-root--documentation-root) the [backbone configuration](../../../glossary.md#term-backbone-configuration--backbone-configuration) declares does not exist yet. Validation warns of it, and does not fail on it ([REQ-015](../../../requirements/functional/REQ-015-missing-root-warns.md)).
- **3a.** An anchor of the document names a kind no installed [component](../../../glossary.md#term-component--component) registers. The check reports an `unresolved-kind`. The developer installs the capability that registers that kind, or removes the anchor.
- **3b.** An artefact anchor names an id that two artefacts share. The check warns of it as `shared-id`, and never fails on it ([COR-050 point 7](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#7-dead-anchors-excluded-paths-and-over-broad-anchors)). The warning names the artefacts that share the id, and the one the anchor stands on. The developer gives them ids no two share, or names a document by its path, and the path rejoins at step 2.
- **5a.** An anchor asks the document for an [answer](../../../glossary.md#term-answer--answer) too often, alone or with the document's other anchors. `pkit friction check --all` warns of it as `over-broad`, and never fails on it ([COR-050 point 7](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#7-dead-anchors-excluded-paths-and-over-broad-anchors)).
- **5b.** The document anchors a [decision record](../../../glossary.md#term-decision-record--decision-record) or another document whole, and parts of that target too. `pkit friction check --all` warns of the document as `whole-and-parts`, and that [finding](../../../glossary.md#term-finding--finding) owes no answer ([ADR-080 point 5](../../../../../architecture/decisions/ADR-080-over-broad-anchor-flags.md#5-a-whole-anchor-beside-anchors-on-its-parts)). The developer takes one of these moves:
  - Removes the anchors on the target's parts.
  - Removes the whole anchor, where the document rests on those parts alone.
  - Keeps both.

**Postconditions:** The document carries anchors naming what makes it true. The [change check](../../../glossary.md#term-change-check--change-check) asks it for an [answer](../../../glossary.md#term-answer--answer) in each [change](../../../glossary.md#term-change--change) that modifies what one of them names.

**Minimal guarantees:**

- A [dead anchor](../../../glossary.md#term-dead-anchor--dead-anchor) is an error, never silence, so a mistyped [anchor](../../../glossary.md#term-anchor--anchor) never reads as a document nothing changed ([COR-050 point 7](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#7-dead-anchors-excluded-paths-and-over-broad-anchors) and [REQ-020](../../../requirements/functional/030-change/REQ-020-dead-anchor-error.md)).
- A document in a declared [place](../../../glossary.md#term-place--place) with no anchors is counted as unanchored, or listed apart with its accepted reason. It is never hidden ([COR-050 point 8](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#8-two-measures-not-failures)).
- [Validation](../../../glossary.md#term-validation--validation) fails a malformed block wherever the [project](../../../glossary.md#term-project--project) runs it, whatever its [friction mode](../../../glossary.md#term-friction-mode--friction-mode) ([COR-050 point 12](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#12-warning-or-enforcing-and-who-owns-which-finding)).
