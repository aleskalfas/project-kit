---
id: UC-001
title: Resume a clone after every session died
status: active
actor: ACT-clone-session
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
        - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
        - .pkit/capabilities/project-management/scripts/_lib/audit.py
        - .pkit/capabilities/project-management/scripts/create-issue.py
        - .pkit/capabilities/project-management/scripts/start-work.py
      record:
        - project-management:DEC-035
        - project-management:DEC-043
        - project-management:DEC-044
        - project-management:DEC-045
        - project-management:DEC-049
        - ADR-041
      artefact:
        - ACT-clone-session
    revalidated:
      at: 2026-10-01T21:34:00Z
      outcome: unchanged
      unchanged-because: "create-issue's report of its native sub-issue link changed again (#808): it says itself that it recorded the textual ref, names link-parent when the link fails, and names the containment: textual way out when GitHub refused it; filing, claiming and resuming work are untouched, so the use case still holds"
---

# UC-001 — Resume a clone after every session died

**Goal:** A new session in a clone learns what the clone was doing and where it was heading, although every earlier session is gone and uncommitted work may be lost.

**Starts when:** The operator starts a new session in a clone after every session in every clone was killed.

**Main path:**

1. The session reads its clone's instance id from the clone-local file, which outlived the sessions.
2. The session asks for the clone's position (`brief`), and gets an answer in seconds, whichever substrate carries ownership.
3. The position lists what is **mine**: the issues in flight that this instance owns, each with its latest intent note — what was done, what comes next.
4. It lists where the clone was **heading**: the unstarted Backlog children of the containers this instance owns, flat and unordered.
5. It lists what is **free to pick**, and whether a stabilisation is on.
6. The session takes up an issue in flight from its latest intent note, on the issue's branch, and carries on.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **1a.** The clone has no instance id — it is a fresh clone, or the file was lost. The position falls back to the operator's assigned issues, unsigned, and says to set the id (`set-instance`); the path resumes at step 2 once it is set.
- **3a.** An issue in flight has no intent note, because it was started before notes existed. The position shows it without a direction; the session reads the issue's body and its branch instead.
- **6a.** Uncommitted work on the issue's branch died with the session. The intent note still gives the direction, and the session redoes the lost part: losing uncommitted work is accepted, losing direction is not.
- **6b.** Nothing is in flight. The session starts the next item the clone was heading to, or finds work (UC-003).

**Done when:** The session is working on the clone's own work again, in the direction its latest intent note gave. The direction came from nothing but the tracker and the clone's instance id; the issue's branch gave only the committed progress, and, for an issue with no note (3a), what the branch shows of where it was going.

**Design:** Situation S1 of the coordination design walk. Built today: the clone-local instance id (`set-instance`, project-management DEC-035) and the read seam that folds an issue's ownership events into its owner (ADR-041). Intended, not built yet: the position command `brief` and intent notes are EPIC #943's (F1), except the stabilisation in step 5, which F2 adds to `brief`; the claims the lifecycle commands make — a clone claiming what it files and what it starts (DEC-035 point 3) — are EPIC #508's, with the signed listings of #521, and land in `create-issue.py` and `start-work.py`, anchored here. F1 adds `brief`'s path as an anchor and revalidates this use case. The engine journal is not read: it lives in one clone's working tree, so it is no shared record (DEC-049).

**Gaps** (revalidation `2026-09-29-multi-clone-coordination`):

- **E, at step 2.** The design walked made `brief` fast with label queries, which cannot see owners on the default comment-log substrate (DEC-043). Proposed fix (pending authorisation; carried by F1 T1.2 of EPIC #943): `brief` folds ownership through the ADR-041 seam from one batched read of the operator's open assigned issues with their comments. Open: the free-to-pick list needs unowned and unassigned issues, which that read does not return, so a second query; and whether DEC-043's "the comment log is read only to reconcile" or ADR-041's fold of the log governs the read.
