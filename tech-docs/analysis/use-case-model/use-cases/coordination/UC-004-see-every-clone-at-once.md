---
id: UC-004
title: See every clone's position at once
status: active
actor: ACT-operator
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
        - .pkit/capabilities/project-management/schemas/instance-ownership.yaml
      record:
        - project-management:DEC-035
        - project-management:DEC-043
        - project-management:DEC-045
        - ADR-041
      artefact:
        - ACT-operator
    revalidated:
      at: 2026-09-30T23:02:19Z
      outcome: unchanged
      unchanged-because: "#840's lint and format pass reshapes the anchored code without changing what it does, so this page still describes it as it is"
---

# UC-004 — See every clone's position at once

**Goal:** From any one clone, the operator sees what each of their clones holds, where each is heading, and whether a stabilisation is on.

**Starts when:** The operator wants the whole picture — after a restart, before a release, or before moving work between clones.

**Main path:**

1. In any clone, the operator asks for every instance's position (`brief --all-instances`).
2. The answer comes in seconds, whichever substrate carries ownership (project-management DEC-043), and it agrees with what each clone calls its own.
3. For each instance — by number, and by name where the operator named them (DEC-045) — it shows the issues in flight with their latest intent notes, and where the instance is heading.
4. It shows what no instance owns, and whether a stabilisation is on: for which Milestone, since when, by whom and why.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **1a.** The clone the operator asks from has no instance id. The overview needs none: it reads every instance of the operator's account.
- **3a.** An instance owns nothing and has no name. It does not appear: on the tracker, an instance exists only through what it owns.
- **3b.** An issue carries two owners, because two clones claimed it in the same instant and the one that should back off has not run since. The overview shows it under the lower instance number, the owner DEC-035 point 6 keeps.

**Done when:** The operator knows, for every clone, what it holds and where it is heading, without visiting any of them.

**Design:** Situation S4 of the coordination design walk. Built today: the read seam every ownership listing folds through (ADR-041), and the substrate selection, whose default is the comment log (`instance-ownership.yaml`, DEC-043). Intended, not built yet — EPIC #943 (F1): `brief --all-instances`, except the stabilisation in step 4, which F2 adds to `brief`. F1 adds `brief`'s path as an anchor and revalidates this use case.

**Gaps** (revalidation `2026-09-29-multi-clone-coordination`):

- **B, at step 1** (found while the design was made). The position was per clone, so the operator had to visit each; `--all-instances` is its fix, part of the design walked.
- **E, at step 2.** The design walked answered from label queries, which cannot see owners on the default comment-log substrate (DEC-043), so the overview and a clone could disagree. Proposed fix (pending authorisation; carried by F1 T1.2 of EPIC #943): the overview and every clone fold ownership through the one ADR-041 seam, from one batched read of the operator's open assigned issues with their comments. Open: what no instance owns (step 4) needs unowned and unassigned issues, so a second query; and whether DEC-043's "the comment log is read only to reconcile" or ADR-041's fold of the log governs the read.
