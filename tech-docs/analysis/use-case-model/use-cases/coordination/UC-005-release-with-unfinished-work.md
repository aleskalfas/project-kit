---
id: UC-005
title: Cut a release while unfinished work remains
status: active
actor: ACT-operator
pkit:
  friction:
    anchors:
      path:
        - .github/workflows/release-pr.yml
        - src/project_kit/release.py
        - .pkit/capabilities/project-management/scripts/_lib/milestone.py
      record:
        - project-management:DEC-016
        - project-management:DEC-014
        - project-management:DEC-044
        - PRJ-002
        - ADR-019
      artefact:
        - ACT-operator
---

# UC-005 — Cut a release while unfinished work remains

**Goal:** The operator releases what is ready while other work is unfinished, and no unfinished work the operator did not accept goes out with the release.

**Starts when:** A release Milestone is stabilising (UC-010) and the operator wants to cut the release.

**Main path:**

1. The operator reads the Milestone's readiness (`show-milestone <N>`): its children, and the open parents of work that has landed on the default branch since the last release.
2. The clones finish the release scope still in flight; the stabilisation keeps everything else off the default branch.
3. For an open parent the release will not wait for — a Feature with some Tasks landed and others not — the operator defers it with a reason (`gate-milestone-closable <N> --since <last release> --bypass "<reason>"`). A stamped audit comment on the parent names the Milestone and the reason.
4. The deferred parent leaves release scope for the release gate and the stabilisation guards alike: its remaining Tasks wait until the stabilisation lifts.
5. The release step runs the same gate, and it passes: the Milestone's children are closed, and every open parent of landed work is deferred.
6. The release step prepares the release (`pkit release apply`) and opens the release pull request for review (PRJ-002).
7. After the release, closing the Milestone lifts the stabilisation.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **2a.** A defect turns up in the release scope. It is filed as a Bug on the stabilising Milestone, and so becomes release scope.
- **5a.** Release scope is still unfinished and not deferred. The gate refuses and names what is open, and no release pull request is opened; the path resumes at step 2.
- **5b.** No release Milestone exists. The release step runs as it does today, without the gate.

**Done when:** The release carries the finished release scope and the landed part of each parent the operator deferred — each deferral stamped with its reason — and no other unfinished work.

**Design:** Situation S5 of the coordination design walk; stabilising the Milestone is UC-010. Built today: the release step that versions from changesets and opens a release pull request for review (`release-pr.yml`, PRJ-002), Milestone categories (project-management DEC-016), the bypassable-with-audit severity (DEC-014) and the audit stamp (DEC-044). Intended, not built yet — EPIC #943: `show-milestone`, `gate-milestone-closable` with its deferral, a `release` Milestone category, and the gate in `release-pr.yml` behind a required status (ADR-019). What has landed is derived from the default branch's history, never from tagging issues with the Milestone, since an issue holds only one Milestone.
