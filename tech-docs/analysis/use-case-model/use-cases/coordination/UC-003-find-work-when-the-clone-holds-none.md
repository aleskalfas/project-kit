---
id: UC-003
title: Find work when the clone holds none
status: active
actor: ACT-clone-session
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
        - .pkit/capabilities/project-management/scripts/handoff-issue.py
      record:
        - project-management:DEC-035
        - project-management:DEC-045
        - project-management:DEC-026
      artefact:
        - ACT-clone-session
    revalidated:
      at: 2026-10-01T09:12:51Z
      outcome: unchanged
      unchanged-because: DEC-026 now says how done-work merges through a merge queue (#1011); the handoff this use case cites DEC-026 for is unchanged
---

# UC-003 — Find work when the clone holds none

**Goal:** A clone that holds no work finds something it may take up, or learns why nothing is free.

**Starts when:** A clone session has nothing in flight and nothing it was heading to, while another clone of the same person owns a whole filed tree of unstarted work.

**Main path:**

1. The session reads the clone's position (`brief`).
2. The position lists what is **free to pick**: issues no instance owns, limited to the workstreams this instance handles where the operator has named instances (project-management DEC-045).
3. Beside them it lists what is **reclaimable**: unstarted Backlog items another instance owns, each with its owner, its workstream and the command that claims it (`handoff-issue <N> --to-instance self`).
4. The session chooses an item. A free one it starts; a reclaimable one it claims first.
5. The claim makes the issue this instance's, and the session starts the work (UC-002, step 1).

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **2a.** A stabilisation is on. Both lists hold only release scope, since nothing new starts outside it — and release-scope work stays free to pick even where starting it opens a new front (gap K1).
- **3a.** A reclaimable item lies in a workstream the operator routed to another instance. It is listed all the same, marked as outside this instance's workstreams: routing is a hint, and claiming such an item is a deliberate act the clash guard warns about (DEC-045).
- **4a.** Both lists are empty. The position says what emptied them — nothing unstarted anywhere, the workstream routing, or the stabilisation — so the operator can act on the cause.
- **5a.** Two clones claim the same free item in the same instant. The lower instance number keeps it and the other backs off (DEC-035 point 6). Two clones reclaiming the same item from a third instance at once is a case that point does not cover (see gap F below).

**Done when:** The clone is working on an item it now owns, or the operator knows why there is nothing it may take.

**Design:** Situation S3 of the coordination design walk. Built today: the ownership read seam (ADR-041) and handoff between people (`handoff-issue`, DEC-026). Intended, not built yet: the free and reclaimable lists of `brief` are EPIC #943's (F1), which adds `brief`'s path as an anchor and revalidates this use case, and limiting them to release scope (2a) is F2's; the claim itself, `handoff-issue --to-instance self`, is #521 under EPIC #508 (DEC-035 point 4), in `handoff-issue.py`, anchored here.

**Gaps** (revalidation `2026-09-29-multi-clone-coordination`):

- **A, at step 3** (found while the design was made). Nothing was free while another clone owned the filed tree; the reclaimable list is its fix, part of the design walked.
- **F, at steps 2 and 3.** The design walked intersected the free and reclaimable items with this instance's workstreams, which removes exactly the other clone's realm, and so undoes gap A's fix. Proposed fix (pending authorisation; carried by F1 T1.2 of EPIC #943): reclaimable items form a group of their own, not filtered by routing and marked when outside this instance's workstreams (3a), and an empty position names the filter that emptied it (4a). Open: whether free items are then filtered by routing while reclaimable ones are not (step 2 as walked), or both are left unfiltered and marked, or both filtered; and what settles two reclaims of the same item at once (5a), which DEC-035 point 6's tie-break, written for claiming an unowned issue, does not cover.
- **K1, at 2a.** The start guard as walked refused every new front, including release-scope work, while this variant offers it as free to pick. Proposed fix (pending authorisation; carried by F2 T2.2 of EPIC #943): refuse a start only when it is a new front and outside release scope.
