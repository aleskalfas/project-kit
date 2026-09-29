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
---

# UC-004 — See every clone's position at once

**Goal:** From any one clone, the operator sees what each of their clones holds, where each is heading, and whether a stabilisation is on.

**Starts when:** The operator wants the whole picture — after a restart, before a release, or before moving work between clones.

**Main path:**

1. In any clone, the operator asks for every instance's position (`brief --all-instances`).
2. The answer comes in seconds. Ownership is read through the same fold every clone uses, on whichever substrate carries it (project-management DEC-043), from one batched read rather than a request per issue.
3. For each instance — by number, and by name where the operator named them (DEC-045) — it shows the issues in flight with their latest intent notes, and where the instance is heading.
4. It shows what no instance owns, and whether a stabilisation is on: for which Milestone, since when, by whom and why.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **1a.** The clone the operator asks from has no instance id. The overview needs none: it reads every instance of the operator's account.
- **3a.** An instance owns nothing and has no name. It does not appear: on the tracker, an instance exists only through what it owns.
- **3b.** An issue carries two owners, because two clones claimed it in the same instant and the one that should back off has not run since. The overview shows it under the owner the fold resolves, the lower instance number (DEC-035).

**Done when:** The operator knows, for every clone, what it holds and where it is heading, without visiting any of them.

**Design:** Situation S4 of the coordination design walk. Built today: the read seam every ownership listing folds through (ADR-041), and the substrate selection, whose default is the comment log (`instance-ownership.yaml`, DEC-043). Intended, not built yet — EPIC #943: `brief --all-instances`.
