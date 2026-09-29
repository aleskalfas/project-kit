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

- **2a.** A stabilisation is on. Both lists hold only release scope, since nothing new starts outside it.
- **3a.** A reclaimable item lies in a workstream the operator routed to another instance. It is listed all the same, marked as outside this instance's workstreams: routing is a hint, and claiming such an item is a deliberate act the clash guard warns about (DEC-045).
- **4a.** Both lists are empty. The position says what emptied them — nothing unstarted anywhere, the workstream routing, or the stabilisation — so the operator can act on the cause.
- **5a.** Two clones claim the same item in the same instant. Each re-reads after writing; the lower instance number keeps it and the other backs off (DEC-035).

**Done when:** The clone is working on an item it now owns, or the operator knows why there is nothing it may take.

**Design:** Situation S3 of the coordination design walk. Built today: the ownership read seam (ADR-041) and handoff between people (`handoff-issue`, DEC-026). Intended, not built yet — EPIC #943: the free and reclaimable lists of `brief`; the claim itself, `handoff-issue --to-instance self`, is #521 (DEC-035 point 4).
