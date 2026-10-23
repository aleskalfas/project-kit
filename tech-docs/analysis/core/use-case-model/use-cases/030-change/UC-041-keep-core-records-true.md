---
id: UC-041
title: Keep each core record true for any project that adopts it
status: active
actor: ACT-methodology-maintainer
other-actors:
  - ACT-ai-agent
  - ACT-merge-authoriser
requirements:
  - REQ-005
  - REQ-021
after:
  - [UC-014]
  - [UC-037]
  - [UC-027]
pkit:
  friction:
    anchors:
      path:
        - .pkit/agents/core/methodology-reviewer.md
        - src/project_kit/decisions_validate.py
        - src/project_kit/cli.py
      record:
        - COR-014
        - COR-001
        - COR-046
        - COR-055#1
        - COR-058#3
      artefact:
        - ACT-methodology-maintainer
        - ACT-ai-agent
        - ACT-merge-authoriser
        - REQ-005
        - REQ-021
        - CONTRIBUTING.md#adding-a-core-record-cor
---

# UC-041 — Keep each core record true for any project that adopts it

**Goal:** Keep each core record true for any project that adopts it.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): as the `methodology-reviewer`, judges the record against the methodology's disciplines. It reports each violation, and changes nothing in the record (REQ-021).
- **Merge authoriser** (`ACT-merge-authoriser`): accepts the core record by their own review, and authorises its merge (UC-040).

**Preconditions:**

- **From UC-014:** The maintainer develops the methodology in its source repository.
- **From UC-037:** The maintainer's change adds a core record, stamped with the namespace `core`, or refines an accepted one in place.
- **From UC-027:** The `methodology-reviewer`'s agent definition is deployed where the harness reads it.

**Assumptions:**

- A project that holds a core record wrong proposes a change to the methodology, and edits no copy of it. Nothing stops such an edit, and the next sync writes over it (COR-001).

**Trigger:** The maintainer's change, which adds or refines a core record, is ready for review.

**Main path:**

1. The maintainer dispatches the `methodology-reviewer` on the core record the change adds or refines.
2. The reviewer judges the record against the methodology's disciplines (`CONTRIBUTING.md`, "Adding a core record (COR)"). It reads each of these:
   - its terms, each defined in an earlier record, plain words, or an outside tool's name
   - its fit for any project that adopts it, by the test of universal applicability (COR-014)
   - its principles among alternatives, never an inventory of current state
   - each thing it names by its role, where the role is what the record means (COR-046)
   - its title and its opening, which state the decision before the detail
   - the present, stated with no amendment log or dated correction
3. The reviewer reports each violation with its discipline, and changes nothing in the record (REQ-021). Its working files lie in the agent workspace.
4. The maintainer revises the record. Content that fits only one project moves to that project's own namespace, such as a PRJ record of the source repository (COR-014).
5. The maintainer runs `pkit decisions validate`. In the source repository a core record is no synced copy, so validation checks its id, its points and its narration (COR-055 point 1).
6. The merge authoriser accepts the record (UC-040), and the change lands (UC-034).

**Variants:**

- **1a.** The change refines a core record in place. Its points keep their ids, and a new point takes the next unused number (COR-058 point 3). So a project's citation of a point stays true across the refinement.
- **2a.** The record cites a later record. That holds only where the record is refined in place, the citation states what the refinement adds, and the record's decision still reads without it.
- **3a.** The reviewer finds no violation. The path goes on at step 5.
- **4a.** The maintainer holds a finding wrong. The maintainer keeps the text, says why in the change, and the path goes on at step 5.
- **4b.** The decision fits only the source repository, such as the name of its tool's binary. The maintainer records it as a PRJ record of the source repository instead, and the use case ends.
- **5a.** A line of the record narrates its own revision. Validation warns of it, naming the file and the line, and the maintainer states the fact plainly (UC-037 variant 7c).

**Postconditions:**

- The core record is accepted on the default branch, and holds nothing that fits only one project.
- Each project that syncs to a release holding the record receives it as a synced copy, which its validation leaves alone (COR-055 point 1).

**Minimal guarantees:**

- The reviewer changes nothing in the record it judges (REQ-021).
- A project's validation never fails on a core record it receives, which it cannot mend (COR-055 point 1).
- `pkit decisions validate` writes nothing, whatever it finds (REQ-005).
