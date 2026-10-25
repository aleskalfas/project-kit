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
        - COR-006
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
    revalidated:
      at: 2026-10-25T05:24:14Z
      outcome: unchanged
      unchanged-because: The change makes the help of pkit process graph say how its presets combine, as the command does it, and the command keeps the same edges. No step here filters that graph, so the use case holds.
---

# UC-041 — Keep each core record true for any project that adopts it

**Goal:** Keep each core record true for any project that adopts it.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): as the `methodology-reviewer`, judges the record against the [methodology](../../../glossary.md#term-methodology--methodology)'s disciplines. It reports each violation, and changes nothing in the record (REQ-021).
- **Merge authoriser** (`ACT-merge-authoriser`): accepts the core record by their own review, and authorises its merge (UC-040).

**Preconditions:**

- **From UC-014:** The maintainer develops the [methodology](../../../glossary.md#term-methodology--methodology) in its [source repository](../../../glossary.md#term-source-repository--source-repository).
- **From UC-037:** The maintainer's [change](../../../glossary.md#term-change--change) adds a core record, stamped with the namespace `core`, or refines an accepted one in place.
- **From UC-027:** The `methodology-reviewer`'s [agent definition](../../../glossary.md#term-agent-definition--agent-definition) is deployed where the [harness](../../../glossary.md#term-harness--harness) reads it.

**Assumptions:**

- A [project](../../../glossary.md#term-project--project) that holds a core record wrong proposes an edit to the [methodology](../../../glossary.md#term-methodology--methodology), and edits no copy of it. Nothing stops such an edit, and the next [sync](../../../glossary.md#term-sync--sync) writes over it (COR-001).
- The `methodology-reviewer` changes nothing in the record it judges, as its [agent definition](../../../glossary.md#term-agent-definition--agent-definition) says. Nothing at run time checks what it changed (REQ-021).

**Trigger:** The maintainer's [change](../../../glossary.md#term-change--change), which adds or refines a core record, is ready for review.

**Main path:**

1. The maintainer dispatches the `methodology-reviewer` on the core record the [change](../../../glossary.md#term-change--change) adds or refines.
2. The [reviewer](../../../glossary.md#term-reviewer--reviewer) judges the record against the [methodology](../../../glossary.md#term-methodology--methodology)'s disciplines (`CONTRIBUTING.md`, "Adding a core record (COR)"). It reads each of these:
   - its terms: each is defined in an earlier record, is a plain word, or names an outside tool
   - its fit for any [project](../../../glossary.md#term-project--project) that adopts it, by the test of universal applicability (COR-014)
   - its principles among alternatives, never an inventory of current state
   - its content placed in the kind of [artefact](../../../glossary.md#term-artefact--artefact) that carries it, such as a procedure in a [skill](../../../glossary.md#term-skill--skill) rather than in a record (COR-006)
   - each thing it names by the part it plays, where that part is what the record means (COR-046)
   - its title and its opening, which state the decision before the detail
   - the present, stated with no amendment log or dated correction
3. The reviewer reports each violation with its discipline, and changes nothing in the record (REQ-021). Its working files lie in the [agent workspace](../../../glossary.md#term-agent-workspace--agent-workspace).
4. The maintainer revises the record. Content that fits only one project moves to that project's own namespace, such as a PRJ record of the [source repository](../../../glossary.md#term-source-repository--source-repository) (COR-014).
5. The maintainer runs `pkit decisions validate`. In the source repository a core record is no [synced copy](../../../glossary.md#term-synced-copy--synced-copy), so [validation](../../../glossary.md#term-validation--validation) checks its id, its points and its narration (COR-055 [point](../../../glossary.md#term-point--point) 1).
6. The merge authoriser accepts the record (UC-040), and the change lands (UC-034).

**Variants:**

- **1a.** The [change](../../../glossary.md#term-change--change) refines a core record in place. Its points keep their ids, and a new [point](../../../glossary.md#term-point--point) takes the next unused number (COR-058 point 3). So a [project](../../../glossary.md#term-project--project)'s citation of a point stays true across the refinement.
- **2a.** The record cites a later record. The [reviewer](../../../glossary.md#term-reviewer--reviewer) flags the citation, unless the record is refined in place and the citation states what the refinement adds. The record's own decision must still read without the later one.
- **3a.** The reviewer finds no violation. The path goes on at step 5.
- **4a.** The maintainer holds a [finding](../../../glossary.md#term-finding--finding) wrong. The maintainer keeps the text, says why in the change, and the path goes on at step 5.
- **4b.** The decision fits only the [source repository](../../../glossary.md#term-source-repository--source-repository), such as the name of its tool's binary. The maintainer records it as a PRJ record of the source repository instead, and the use case ends.
- **5a.** A line of the record narrates its own revision. [Validation](../../../glossary.md#term-validation--validation) warns of it, naming the file and the line, and the maintainer states the fact plainly (UC-037 variant 7c).

**Postconditions:**

- The core record is accepted on the [default branch](../../../glossary.md#term-default-branch--default-branch), and holds nothing that fits only one [project](../../../glossary.md#term-project--project).
- Each [point](../../../glossary.md#term-point--point) of the record stands under an id it keeps for good, so a project's citation of it stays true (COR-058 point 3).

**Minimal guarantees:**

- A [project](../../../glossary.md#term-project--project)'s [validation](../../../glossary.md#term-validation--validation) never fails on a core record it receives, which it cannot mend (COR-055 [point](../../../glossary.md#term-point--point) 1).
- `pkit decisions validate` writes nothing, whatever it finds (REQ-005).
