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

- **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.
- **From UC-021, UC-023 or UC-016:** Places that hold anchored [artefacts](../../../glossary.md#term-artefact--artefact) are declared. They are the project's own, in its [backbone configuration](../../../glossary.md#term-backbone-configuration--backbone-configuration), or those of a [capability](../../../glossary.md#term-capability--capability) the [manifest](../../../glossary.md#term-manifest--manifest) records ([COR-050 point 1](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#1-artefacts)).

**Assumptions:**

- The anchors name everything the document rests on. A [change](../../../glossary.md#term-change--change) to something no [anchor](../../../glossary.md#term-anchor--anchor) names asks the document nothing ([COR-050 point 6](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#6-friction-in-two-checks)).

**Trigger:** The developer writes a document that describes something in the repository, or finds that one rests on more than its anchors name.

**Main path:**

1. The developer lists the document's anchors in the `friction` block of its `pkit` front matter. Each names a path, a record or one of its points, or another [artefact](../../../glossary.md#term-artefact--artefact), one of its sections or its lead.
2. The developer runs `pkit validate`. Its `friction` member checks the block's shape and the cycles between artefacts. It checks each [anchor](../../../glossary.md#term-anchor--anchor) on a part of a record or a document too.
3. The developer runs `pkit friction check`. A document new in the [change](../../../glossary.md#term-change--change) counts as revalidated, and an anchor the change added that resolves to nothing is a `dead-anchor`, an error (REQ-020).
4. The change lands on the [default branch](../../../glossary.md#term-default-branch--default-branch).
5. In each later change that modifies what one of its anchors names, the [change check](../../../glossary.md#term-change-check--change-check) asks the document for an [answer](../../../glossary.md#term-answer--answer) (UC-002).

**Variants:**

- **1a.** The document lies in no declared [place](../../../glossary.md#term-place--place), so nothing reads its anchors. `pkit friction artefacts` lists the places. The developer adds the document's path to `friction.places`, and the path rejoins at step 1.
- **1b.** Nothing the repository holds makes the document true, such as a person's part in the work. A person accepts a reason for having no anchors, word for word, before it is written as `unanchored-because` (COR-050 points [1](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#1-artefacts) and [3](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)). A delegate a person named may decide it instead ([COR-064 point 1](../../../../../../.pkit/decisions/core/COR-064-answer-delegate.md#1-the-answers-a-delegate-decides)). The use case ends.
- **1c.** The document already carries anchors, and the developer changes the list. The [change check](../../../glossary.md#term-change-check--change-check) asks the document for a revalidation in the same [change](../../../glossary.md#term-change--change) ([COR-050 point 6](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#6-friction-in-two-checks)), and the path goes on at step 2.
- **1d.** A [stamp](../../../glossary.md#term-stamp--stamp) writes the anchors, such as the command an installed [capability](../../../glossary.md#term-capability--capability) offers to create an [artefact](../../../glossary.md#term-artefact--artefact) of its kind. The path goes on at step 2.
- **1e.** An [anchor](../../../glossary.md#term-anchor--anchor) names a kind a capability registers, with the command that resolves it. The check asks that command which files the anchor stands on, offline and within thirty seconds ([COR-050 point 2](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#2-anchors), REQ-006 and REQ-007). A command that gives no result leaves the anchor `no-answer`, never read as unchanged (REQ-004). The path goes on at step 2.
- **2a.** [Validation](../../../glossary.md#term-validation--validation) finds a fault in the block, and fails, naming it. The path rejoins at step 1. The faults it fails on are these:
  - a malformed block, or `unanchored-because` beside anchors
  - a cycle between artefacts
  - a dead, ambiguous or refused anchor on a part
- **2b.** A [documentation root](../../../glossary.md#term-documentation-root--documentation-root) the [backbone configuration](../../../glossary.md#term-backbone-configuration--backbone-configuration) declares does not exist yet. Validation warns of it, and does not fail on it (REQ-015).
- **3a.** An anchor names a kind that no installed [component](../../../glossary.md#term-component--component) resolves. The check reports an `unresolved-kind`. The developer installs the capability that resolves it, or removes the anchor.
- **3b.** An artefact anchor names an id that two artefacts share. The check warns of it as `shared-id`, and never fails on it ([COR-050 point 7](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#7-dead-anchors-excluded-paths-and-over-broad-anchors)). The warning names the artefacts that share the id, and the one the anchor stands on. The developer gives them ids no two share, or names a document by its path, and the path rejoins at step 2.
- **5a.** An anchor matches more than half the tracked files. `pkit friction check --all` warns of it as `over-broad`, since it would make every change a revalidation, and never fails on it ([COR-050 point 7](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#7-dead-anchors-excluded-paths-and-over-broad-anchors)).

**Postconditions:** The document carries anchors naming what makes it true. The [change check](../../../glossary.md#term-change-check--change-check) asks it for an [answer](../../../glossary.md#term-answer--answer) in each [change](../../../glossary.md#term-change--change) that modifies what one of them names.

**Minimal guarantees:**

- A dead [anchor](../../../glossary.md#term-anchor--anchor) is an error, never silence, so a mistyped anchor never reads as a document nothing changed ([COR-050 point 7](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#7-dead-anchors-excluded-paths-and-over-broad-anchors) and REQ-020).
- A document in a declared [place](../../../glossary.md#term-place--place) with no anchors is counted as unanchored, or listed apart with its accepted reason. It is never hidden ([COR-050 point 8](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#8-two-measures-not-failures)).
- [Validation](../../../glossary.md#term-validation--validation) fails a malformed block wherever the [project](../../../glossary.md#term-project--project) runs it, in either [friction](../../../glossary.md#term-friction--friction) mode ([COR-050 point 12](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#12-warning-or-enforcing-and-who-owns-which-finding)).
