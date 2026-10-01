---
id: UC-010
title: Stabilise a Milestone for a release
status: active
actor: ACT-operator
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/milestone.py
        - .pkit/capabilities/project-management/scripts/start-work.py
        - .pkit/capabilities/project-management/scripts/done-work.py
        - .pkit/capabilities/project-management/scripts/merge-pr.py
        - .pkit/capabilities/project-management/scripts/close-milestone.py
      record:
        - project-management:DEC-016
        - project-management:DEC-014
        - project-management:DEC-044
        - ADR-019
      artefact:
        - ACT-operator
    revalidated:
      at: 2026-10-01T16:34:07Z
      outcome: unchanged
      unchanged-because: on this branch the merge mechanic moved into the backbone's pull-request landing module; the refusal to sync or upgrade under an older pkit that main brought in does not change what this page says about landing a pull request
---

# UC-010 — Stabilise a Milestone for a release

**Goal:** The operator freezes a release Milestone: work in flight continues, nothing new starts outside release scope, and the default branch receives only release scope.

**Starts when:** A release is near, and the operator wants the clones to finish the release scope rather than start more.

**Main path:**

1. The operator stabilises the Milestone (`stabilize-milestone <N> --reason "<why>"`). A `Stabilizing:` line — time, operator, instance and reason — appears in the Milestone's description.
2. From then on, every clone's position shows the stabilisation (UC-001, UC-004).
3. Release scope is the same for every clone, for the guards and for the release: the Milestone's children, and the open parents of work landed on the default branch since the last release, each with its subtree, less what the operator deferred (gap G).
4. Starting a new front outside release scope is refused, and so is landing out-of-scope work on the default branch; either can be bypassed with a reason stamped on the issue (project-management DEC-014).
5. A required CI status runs the same check on every pull request into the default branch (ADR-019), including one whose checks passed before the stabilisation began or before a deferral (gap K2).

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **1a.** The Milestone is stabilised from two clones at once. It ends with one `Stabilizing:` line, and every position shows which one stands; stabilising again is enough to replace it.
- **4a.** A hotfix is needed. The operator files it as a Bug on the stabilising Milestone, which puts it in release scope.
- **4b.** A pull request closes no issue — the release pull request, or a changeset-only, documentation or dependency change. Whether it counts as release scope is not stated yet (gap K3); the release pull request at least must land (UC-005, 7a).
- **5a.** The operator lifts the stabilisation (`stabilize-milestone <N> --lift`), or closes the Milestone after the release (UC-005). The line is removed and the guards stand down.

**Done when:** Every clone knows the Milestone is stabilising, and the default branch accepts only release scope until the stabilisation lifts.

**Design:** Situation S5 of the coordination design walk split in two: this use case stabilises, and the release itself is UC-005. It is a use case of its own, not only a step of the release: its goal is met once the freeze holds, and a stabilisation lifted with no release (5a) completes it. Built today: Milestones and their categories (`_lib/milestone.py`, DEC-016), closing a Milestone (`close-milestone.py`), the bypassable-with-audit severity (DEC-014) and the audit stamp (DEC-044). Intended, not built yet — EPIC #943 (F2): `stabilize-milestone`, and one writer for the Milestone's description, which re-reads it before writing, with the last write winning for this rare gesture (1a); the release-scope computation shared by the guards and the release gate; the guards on `start-work`, `done-work` and `merge-pr`; and the required CI status. The scripts that exist are anchored here; F2 adds the new command's, the writer's, the computation's and the check's paths as anchors and revalidates this use case.

**Gaps** (revalidation `2026-09-29-multi-clone-coordination`):

- **G, at step 3.** A deferral satisfied the release gate but not the guards. Proposed fix (pending authorisation; carried by F2 T2.1 and T2.2 of EPIC #943): one release-scope computation, read by the gate, the guards and `brief`, which drops a deferred parent with its subtree. Open: which wins when a Task lies in a deferred subtree and is also a child of the Milestone; and, from K4, whether "open parent" means the nearest parent or every ancestor, that a Milestone parent takes no comment to record a deferral on, and that a catch-all Umbrella that never closes would hold every release.
- **K1, at step 4.** The start guard as walked refused every new front, including release-scope work — an untouched Feature under the release Milestone, and every Task filed directly under it (project-management DEC-004). Proposed fix (pending authorisation; carried by F2 T2.2 of EPIC #943): refuse a start only when it is a new front and outside release scope.
- **K2, at step 5.** A required status is computed per head commit, and stabilising or deferring pushes no commit, so a pull request that went green before either stays green. Proposed fix (pending authorisation; carried by F2 T2.3 and T2.5 of EPIC #943; the design must choose): re-run open pull requests' status on Milestone edits and deferral events, evaluate at merge time (a merge queue, #1011), or declare the residual gap as ADR-019 point 3 requires.
- **K3, at 4b.** Release scope is defined over issues, and some pull requests close none. Proposed fix (pending authorisation; carried by F2 T2.3 and T2.5 of EPIC #943): state the rule here and in UC-005 — either a pull request closing no issue is in scope, or release pull requests are exempt, by the project's configuration.
