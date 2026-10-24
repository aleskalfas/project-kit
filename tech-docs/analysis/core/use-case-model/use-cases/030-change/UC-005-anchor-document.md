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
    revalidated:
      at: 2026-10-24T04:58:24Z
      outcome: unchanged
      unchanged-because: Friction's reading of derived links now holds when forms clash or a placed file is renamed. How a writer says what a document rests on is unchanged.
---

# UC-005 — Say what my document rests on

**Goal:** Say what each of my documents rests on, so a change there reaches me.

**Other actors:** None.

**Preconditions:**

- **From UC-014 or UC-049:** The project runs the system: it is the methodology's source repository, or the system is installed in it.
- **From UC-021, UC-023 or UC-016:** Places that hold anchored artefacts are declared. They are the project's own, in its backbone configuration, or those of a capability the manifest records (COR-050 point 1).

**Assumptions:**

- The anchors name everything the document rests on. A change to something no anchor names asks the document nothing (COR-050 point 6).

**Trigger:** The developer writes a document that describes something in the repository, or finds that one rests on more than its anchors name.

**Main path:**

1. The developer lists the document's anchors in the `friction` block of its `pkit` front matter. Each names a path, a record or one of its points, or another artefact, one of its sections or its lead.
2. The developer runs `pkit validate`. Its `friction` member checks the block's shape and the cycles between artefacts. It checks each anchor on a part of a record or a document too.
3. The developer runs `pkit friction check`. A document new in the change counts as revalidated, and an anchor the change added that resolves to nothing is a `dead-anchor`, an error (REQ-020).
4. The change lands on the default branch.
5. In each later change that modifies what one of its anchors names, the change check asks the document for an answer (UC-002).

**Variants:**

- **1a.** The document lies in no declared place, so nothing reads its anchors. `pkit friction artefacts` lists the places. The developer adds the document's path to `friction.places`, and the path rejoins at step 1.
- **1b.** Nothing the repository holds makes the document true, such as a person's part in the work. A person accepts a reason for having no anchors, word for word, before it is written as `unanchored-because` (COR-050 points 1 and 3). The use case ends.
- **1c.** The document already carries anchors, and the developer changes the list. The change check asks the document for a revalidation in the same change (COR-050 point 6), and the path goes on at step 2.
- **1d.** A stamp writes the anchors, such as the command an installed capability offers to create an artefact of its kind. The path goes on at step 2.
- **1e.** An anchor names a kind a capability registers, with the command that resolves it. The check asks that command which files the anchor stands on, offline and within thirty seconds (COR-050 point 2, REQ-006 and REQ-007). A command that gives no answer leaves the anchor `no-answer`, never read as unchanged (REQ-004). The path goes on at step 2.
- **2a.** Validation finds a fault in the block, and fails, naming it. The path rejoins at step 1. The faults it fails on are these:
  - a malformed block, or `unanchored-because` beside anchors
  - a cycle between artefacts
  - a dead, ambiguous or refused anchor on a part
- **2b.** A documentation root the backbone configuration declares does not exist yet. Validation warns of it, and does not fail on it (REQ-015).
- **3a.** An anchor names a kind that no installed component resolves. The check reports an `unresolved-kind`. The developer installs the capability that resolves it, or removes the anchor.
- **3b.** An artefact anchor names an id that two artefacts share. The check warns of it as `shared-id`, and never fails on it (COR-050 point 7). The warning names the artefacts that share the id, and the one the anchor stands on. The developer gives them ids no two share, or names a document by its path, and the path rejoins at step 2.
- **5a.** An anchor matches more than half the tracked files. `pkit friction check --all` warns of it as `over-broad`, since it would make every change a revalidation, and never fails on it (COR-050 point 7).

**Postconditions:** The document carries anchors naming what makes it true. The change check asks it for an answer in each change that modifies what one of them names.

**Minimal guarantees:**

- A dead anchor is an error, never silence, so a mistyped anchor never reads as a document nothing changed (COR-050 point 7 and REQ-020).
- A document in a declared place with no anchors is counted as unanchored, or listed apart with the reason a person accepted. It is never hidden (COR-050 point 8).
- Validation fails a malformed block wherever the project runs it, in either friction mode (COR-050 point 12).
