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
        - .pkit/capabilities/project-management/scripts/close-milestone.py
        - .pkit/capabilities/project-management/project/config.yaml
      record:
        - project-management:DEC-016
        - project-management:DEC-014
        - project-management:DEC-044
        - PRJ-002
        - ADR-019
      artefact:
        - ACT-operator
    revalidated:
      at: 2026-10-02T01:25:06Z
      outcome: unchanged
      unchanged-because: pkit release merge deletes the release pull request's head branch through the backbone's deletion, only at the head that merged; what a release lands, its scope, its gate and the release pull request's merge path are unchanged, so it holds
---

# UC-005 — Cut a release while unfinished work remains

**Goal:** The operator releases what is ready while other work is unfinished, and no unfinished work the operator did not accept goes out with the release.

**Starts when:** A release Milestone is stabilising (UC-010) and the operator wants to cut the release.

**Main path:**

1. The operator reads the Milestone's readiness (`show-milestone <N>`): its children, and the open parents of work that has landed on the default branch since the last release.
2. The clones finish the release scope still in flight; the stabilisation keeps everything else off the default branch.
3. For an open parent the release will not wait for — a Feature with some Tasks landed and others not — the operator defers it explicitly, with a reason. The deferral is recorded on the parent, naming the Milestone and the reason.
4. The deferred parent leaves release scope for the release gate and the stabilisation guards alike: its remaining Tasks wait until the stabilisation lifts.
5. The release step runs the same gate, and it passes: the Milestone's children are closed, and every open parent of landed work is deferred.
6. The release step prepares the release (`pkit release apply`) and opens the release pull request for review (PRJ-002).
7. The release pull request lands, and after the release, closing the Milestone lifts the stabilisation.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **2a.** A defect turns up in the release scope. It is filed as a Bug on the stabilising Milestone, and so becomes release scope.
- **5a.** Release scope is still unfinished and not deferred. The gate refuses and names what is open, and no release pull request is opened; the path resumes at step 2.
- **5b.** No release Milestone exists. The release step runs as it does today, without the gate.
- **7a.** The release pull request closes no issue, and so is outside release scope as scope is defined over issues. It must land all the same, or the stabilisation holds back the release it exists for (gap K3).

**Done when:** The release carries the finished release scope and the landed part of each parent the operator deferred — each deferral recorded with its reason — and no other unfinished work.

**Design:** Situation S5 of the coordination design walk; stabilising the Milestone is UC-010. Built today: the release step that versions from changesets and opens a release pull request for review (`release-pr.yml`, PRJ-002), Milestone categories (project-management DEC-016, declared in the project's `config.yaml`), closing a Milestone (`close-milestone.py`), the bypassable-with-audit severity (DEC-014) and the audit stamp (DEC-044). Intended, not built yet — EPIC #943 (F2): `show-milestone`, `gate-milestone-closable` with its deferral, the release-scope computation, a `release` Milestone category, and the gate in `release-pr.yml` behind a required status (ADR-019). The paths that exist today are anchored here; F2 adds the new commands' and the computation's paths as anchors and revalidates this use case. What has landed is derived from the default branch's history, never from tagging issues with the Milestone, since an issue holds only one Milestone.

**Gaps** (revalidation `2026-09-29-multi-clone-coordination`):

- **C, at step 1** (found while the design was made). A partly landed parent fell out of scope; deriving what landed and widening scope to its open parents is the fix, part of the design walked.
- **D, at step 3** (found while the design was made). There was no way to release without a parent that would not finish; the fix in the design walked was the gate's bypass, `gate-milestone-closable --bypass "<reason>"`, stamping an audit comment on the parent.
- **G, at step 4.** The deferral satisfied the gate but not the guards, so a deferred parent's remaining Tasks could land during the freeze. Proposed fix (pending authorisation; carried by F2 T2.1 and T2.2 of EPIC #943): one release-scope computation, read by the gate, the guards and `brief`, which drops a deferred parent with its subtree. Open: how a deferral is recorded — the gate's bypass, or a revocable audit event of its own; which wins when a Task lies in a deferred subtree and is also a child of the Milestone; and, from K4, whether "open parent" means the nearest parent or every ancestor, that a Milestone parent — the shortcut hierarchy's Tasks filed directly under it — takes no comment to record a deferral on, and that a catch-all Umbrella that never closes would hold every release.
- **K2, at step 4.** A required status is computed per head commit, and a deferral pushes no commit, so a pull request that went green before it keeps its status. Proposed fix (pending authorisation; carried by F2 T2.3 and T2.5 of EPIC #943; the design must choose): re-run open pull requests' status on deferral and Milestone events, evaluate at merge time (a merge queue, #1011), or declare the residual gap as ADR-019 point 3 requires.
- **K3, at steps 6 and 7.** Release scope is defined over issues, and the release pull request closes none — nor do changeset-only, documentation and dependency pull requests — so the landing guard and the required status either refuse the release pull request, a deadlock, or leave it undefined. Proposed fix (pending authorisation; carried by F2 T2.3 and T2.5 of EPIC #943): state the rule here and in UC-010 — either a pull request closing no issue is in scope, or release pull requests are exempt, by the project's configuration.
