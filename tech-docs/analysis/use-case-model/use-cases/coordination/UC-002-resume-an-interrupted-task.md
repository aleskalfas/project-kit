---
id: UC-002
title: Resume a task after its session was interrupted
status: active
actor: ACT-clone-session
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/audit.py
        - .pkit/capabilities/project-management/scripts/start-work.py
      record:
        - project-management:DEC-044
        - project-management:DEC-026
        - project-management:DEC-049
        - COR-034
      artefact:
        - ACT-clone-session
    revalidated:
      at: 2026-10-01T20:50:05Z
      outcome: unchanged
      unchanged-because: "start-work still moves the issue into progress as step 1 says; #1242 now only shares its early check, read from labels and milestone as before, with review-work, and start-work --next stays unbuilt, so the use case holds"
---

# UC-002 — Resume a task after its session was interrupted

**Goal:** Work a session was doing when it stopped goes on later, in the same clone and the same direction, without the clone giving the work up.

**Starts when:** A session working on an in-flight issue is stopped — the operator redirects it, its context runs out, or it is killed.

**Main path:**

1. When the session started the issue, it wrote where it was heading as the issue's first intent note (`start-work --next`).
2. Asked to stop, the session commits what it can and writes an intent note on the issue — what is done, what comes next (`pause-issue <N> --done … --next …`).
3. The issue stays in progress and stays the clone's.
4. Later, a session in the same clone reads the clone's position (UC-001) and finds the issue with that note as its latest.
5. The session continues on the issue's branch from the note's next step.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **2a.** The session is killed before it can write a note. The latest note — from step 1 or an earlier pause — still gives the direction, and the branch's commits show the progress; uncommitted work is lost.
- **3a.** The operator wants another clone to take the work instead. That is a handoff (`handoff-issue`, project-management DEC-026), not a pause, and ownership moves.
- **3b.** The work cannot move until someone else acts. That is a block (COR-034), not a pause.

**Done when:** The work continues from its latest intent note, and while it waited the issue never showed as unowned or blocked.

**Design:** Situation S2 of the coordination design walk. Built today: `start-work` moves the issue into progress (DEC-026), and the audit stamp the notes will carry (`_lib/audit.py`, DEC-044). Intended, not built yet — EPIC #943 (F1): `start-work --next`, in `start-work.py`, anchored here, and `pause-issue`, whose path F1 adds as an anchor when it lands, revalidating this use case. A note is never merged with an earlier one, which refines how DEC-044 point 2 dedups a re-posted stamp and waits for authorisation. A pause changes no state of the issue: its note is the record itself, not a projection of a change, so the journal's projection setting does not reach it (DEC-049).
