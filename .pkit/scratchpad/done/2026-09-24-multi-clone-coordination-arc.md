---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-09-24
retired: 2026-09-29
produced:
  - tech-docs/analysis/use-case-model/use-cases/coordination/UC-001-resume-after-all-sessions-died.md
  - tech-docs/analysis/use-case-model/use-cases/coordination/UC-002-resume-an-interrupted-task.md
  - tech-docs/analysis/use-case-model/use-cases/coordination/UC-003-find-work-when-the-clone-holds-none.md
  - tech-docs/analysis/use-case-model/use-cases/coordination/UC-004-see-every-clone-at-once.md
  - tech-docs/analysis/use-case-model/use-cases/coordination/UC-005-release-with-unfinished-work.md
  - tech-docs/analysis/use-case-model/use-cases/coordination/UC-006-resolve-a-decision-number-collision.md
  - tech-docs/analysis/use-case-model/use-cases/coordination/UC-007-resume-sessions-during-a-stabilisation.md
  - tech-docs/analysis/use-case-model/use-cases/coordination/UC-008-land-integration-work-during-a-stabilisation.md
  - tech-docs/analysis/use-case-model/use-cases/coordination/UC-009-delegate-a-task-to-a-developer-subagent.md
  - tech-docs/analysis/use-case-model/use-cases/coordination/UC-010-stabilise-a-milestone.md
  - tech-docs/analysis/use-case-model/journeys/JRN-001-restart-after-every-session-died.md
  - tech-docs/analysis/use-case-model/journeys/JRN-002-release-under-stabilisation.md
  - tech-docs/analysis/revalidations/2026-09-29-multi-clone-coordination.md
  - 'EPIC #943'
---

# Multi clone coordination arc

## The question

One person runs several clones of this repo, each with its own `project-manager` session. How does any clone — after every session has been killed — reconstruct where it was and where it was heading, see what is free to pick, know whether a Milestone is in stabilization, and mint decision records without post-merge renumber chores, **from the shared work tracker plus a clone-local id alone**?

This note is the carrier for the *coordination EPIC* between two events: EPIC #885 (scenario-driven validation) delivering the first scenario file, and the coordination EPIC being filed against that file. Retire it with `--produced` pointing at the scenario file and the EPIC.

## Forces

- Losing uncommitted work is acceptable; losing **work direction** is not.
- Ownership ("who has what") is already decided: DEC-035 / 043 / 044 / 045 under EPIC #508 — partly shipped (`set-instance`, `start-work` claims). Routing / ready-frontier is DEC-025 (proposed) under EPIC #564 — parked; nothing here may order "next".
- The engine journal (DEC-049) is a committed, branch-local file — **not** a shared substrate. The recoverable substrate is the tracker (comments, labels, Milestones).
- `pkit release` (backbone, PRJ-002) versions pkit components and must stay capability-agnostic; the pm capability must not know about changesets.
- First-to-`main` owns a decision number. Remote-aware minting was **rejected**: an abandoned branch would strand a number.
- pm verbs are verb-subject, flat (DEC-020); the dispatcher has no nested groups.

## Settled in discussion (2026-09-21 → 24)

- **Position + intent notes.** `brief` (name chosen over `triage`, which collides with DEC-016 pre-close triage and the GitHub idiom; `orient` was the runner-up): mine (in-flight + latest note) · heading (unstarted Backlog children of owned containers, flat, unordered) · free-to-pick (DEC-035 commons + other realms' Backlog marked *reclaimable via `handoff-issue --to-instance self`*, ∩ DEC-045 instance workstreams, ∩ stabilization scope) · stabilization state; `--all-instances` for the human's cross-clone view; assignee fallback with no instance id; seconds-fast (label/assignee/state queries, never a forest walk). `pause-issue <N> --done --next` posts a structured comment (DEC-044 record shape, event `pause`, stamp carries timestamp + instance, never deduped); `start-work --next` writes the first note so direction exists from the first second. Pause is **not a mutation**, so DEC-049's projection knob is out of scope by construction (reciprocal note, not an exemption). Pause ≠ `handoff-issue` (ownership retained) and ≠ COR-034 `blocked` (actor absence; subject still has legal moves).
- **Numbering.** Mint from the fetched default branch (resolved, not hard-coded; offline → local max + warning); `decisions validate --against <ref>` in CI; `decisions renumber <old> <new>` rewrites typed tokens / md links / filename **in files changed on the branch**, *reports* bare ids and out-of-tree mentions (commits, issues, changesets), refuses if `<old>` is on `main` under another slug. Investigation: ~12.5k id mentions in tree, 12 % typed/linked; past real renumbers touched 1–2 files because the record was new on the branch. The provisional-id principle is universal → a COR.
- **Release readiness.** Carrier: a Milestone in a `release` category (DEC-016 already shows it). **No `pkit pm release` family** (collides with backbone `pkit release`). General verbs: `show-milestone [N]`, `gate-milestone-closable <N> --since <ref>` (engine-predicate contract like `gate-pr-merged`; `_decide_close` extracted to `_lib`; read-only, no membership gate, CI-runnable). "Landed since last release" is **derived** from `git log <ref>..main` → PRs → closing issues → open parents — never Milestone tagging (an issue holds one Milestone; tagging collided with Housekeeping buckets). Readiness = Milestone children closed ∧ no open parent of landed work, unless deferred; **deferral = the gate's `--bypass "<reason>"`**, which posts a stamped audit comment on the parent naming the Milestone; the gate sees the stamp and passes, including in CI. project-kit's `release-pr.yml` composes gate → `pkit release apply`; the conditional "when a release Milestone exists" lives in the yml → PRJ-002 amendment.
- **Stabilization** (= feature freeze, not code freeze). `stabilize-milestone <N> --reason` / `--lift` writes `Stabilizing: <timestamp> @<actor> instance:<N> — <reason>` in the Milestone description via **one shared writer** (re-read-before-write, marker-line replace; also used by create-/close-milestone; short ADR for the seam; last-writer-wins accepted for rare human gestures — lost write visible in `brief`, re-runnable). Scope = Milestone children ∪ subtrees ∪ open parents of landed work ∪ *their* subtrees. Guards: `start-work` on a **new front** (nearest Feature/Umbrella ancestor has nothing in flight and nothing landed; a Task without such an ancestor is its own front) → bypassable-with-audit; `done-work` / `merge-pr` to `main` out of scope → bypassable-with-audit; integration-branch targets unaffected; `close-milestone` lifts. Enforcement = one read-only check script shared by the pre-flight and a **required CI status** (ADR-019 shape) so an old clone or raw `gh pr merge` cannot walk through. Hotfix: file the Bug attached to the stabilizing Milestone. Three pre-flights on `done-work` = COR-007 trigger for composite gates — a follow-up COR, not built here.
- **Name:** `stabilize-milestone` over `hold`/`lock`/`focus`/`finalize` (phase, not act; industry term).

## Scenarios walked (S1–S9) — to be authored as the first scenario file (#890)

S1 restart after all sessions died · S2 interrupted mid-task · S3 clone with nothing to do while another owns the filed tree · S4 the human's cross-clone overview · S5 release with unfinished work under stabilization · S6 decision-number collision · S7 sessions killed mid-stabilization · S8 integration branch during stabilization · S9 PM + developer subagent.

**Gaps found:** (A) S3 — free-to-pick empty under whole-tree claim → show reclaimable realms; depends on #521. (B) S4 — `brief` was per-clone → `--all-instances`. (C) S5 — partially-landed parent's remaining Tasks fell out of scope; and Milestone tagging collided with one-Milestone-per-issue → derive "landed", widen scope. (D) S5 — no deferral gesture → stamped bypass on the gate.

## Coordination EPIC — slicing to file after the scenario file lands

- **F1 Position verb + intent notes** (S1 S2 S3 S4 S7 S9): T1.0 pm DEC *recoverable work position* (+ reciprocal DEC-049, DEC-026; positions vs DEC-047 / COR-034 / DEC-044) · T1.1 `pause-issue` + `start-work --next` (on `_lib/audit.py`; comment on #511 to cover `pause`) · T1.2 `brief` · T1.3 agent + skill + storyboard + journal-blind killed-session fixture.
- **F2 Milestone stabilization + release readiness** (S5 S7 S8): T2.0 pm DEC + ADR (description sole-writer seam) + reciprocal DEC-016 · T2.1 `show-milestone` + `gate-milestone-closable` · T2.2 `_lib/stabilization` + `stabilize-milestone` + start-work guard · T2.3 done-work/merge-pr guard + shared check script · T2.4 PRJ-002 amendment (accept before T2.5) · T2.5 `release` category + `release-pr.yml` gate + required status.
- **F3 Cheap-to-lose numbering** (S6; backbone): T3.0 COR *provisional decision numbering* + README · T3.1 minting + `validate --against` · T3.2 `renumber`.
- Side effects: #834 → High; changesets pm minor + backbone minor; no migrations.
- Not under #508: descendants inherit `Integration: integration/508-…`; and this spans backbone + capability + project-side.

## Needs explicit human authorisation (amends accepted records)

COR provisional numbering · DEC-049 reciprocal (content vs projection) · PRJ-002 amendment · DEC-016 refinement. (The scenario-validation COR and its reciprocals are #886.)

## Reviews

`critic` ×2 and `architect` ×1 ran on this arc (2026-09-22/23); their findings are folded in above. Re-run both after the scenario re-walk (#890) before filing.

## Status

Active. Waiting on EPIC #885 (#886–#890). Next: land the core record (#886), tooling (#887, #888), pm adoption (#889), then author the scenario file (#890) and **re-walk S1–S9 against this design — expect new gaps** — then file the coordination EPIC citing the scenarios and retire this note.

## Closing (2026-09-29, amended 2026-09-30 after review)

Retired as produced by the coordination use cases and EPIC #943. The scenarios became project-kit's first analysis artefacts, under `tech-docs/analysis/` (#890): use cases UC-001 to UC-009 for S1 to S9 in order, UC-010 for stabilising a Milestone (the first half of S5, and a goal of its own: a stabilisation may lift with no release), and journeys JRN-001 (S1 → S4 → S3) and JRN-002 (stabilise → release), with the actors and glossary terms they rest on. Where a use case describes design not built yet, its text says so, names the EPIC and Feature that will build it, and says which anchors that Feature must add; its anchors today are the records and code that exist.

The re-walk is recorded in `tech-docs/analysis/revalidations/2026-09-29-multi-clone-coordination.md`, beside gaps A to D. It found six more, E to J, and the `critic` and `architect` review of #890's pull request (2026-09-30) found three more, K1 to K3. None is fixed: each has a proposed fix, pending authorisation, which the slicing above must carry when EPIC #943's Features are filed. Where the review raised alternatives, the record lists them undecided.

- **E** (S1, S4) — proposed: `brief` reads ownership through the ADR-041 seam from one batched read of the open assigned issues and their comments, not from label queries: the default substrate is the comment log. Open: a second query for unowned, unassigned issues; DEC-043's mirror read against ADR-041's fold. → F1 T1.2.
- **F** (S3) — proposed: reclaimable items are a group of their own, not intersected with the instance's workstreams, which would remove exactly what gap A added; an empty position names the filter that emptied it. Open: whether free items are filtered too; two reclaims at once. → F1 T1.2.
- **G** (S5) — proposed: one release-scope computation, read by the gate, the guards and `brief`, dropping a deferred parent with its subtree. Open: the deferral's record; a Task both deferred and a Milestone child; which "open parent" (K4). → F2 T2.1 and T2.2.
- **H** (S6) — proposed: `renumber` refuses when the record already landed, or `<new>` is taken; "refuses if `<old>` is on main under another slug" above was inverted. Open: the slug or the merge-base as the test. → F3 T3.2.
- **I** (S8) — proposed: the new-front test reads "landed" on the branch the work lands on, so continuing an integration arc is no new front. Alternative: leave integration-marked work out of the start guard. → F2 T2.2.
- **J** (S9) — proposed: a worktree inherits its clone's instance id through git's common directory; open whether its own id file wins. → #1140, under EPIC #508, not a Feature of this slicing.
- **K1** (S5, S7) — proposed: the start guard refuses only a new front outside release scope; as written it refused release-scope work too. → F2 T2.2.
- **K2** (S5, S7) — a required status computed per head commit misses a stabilisation or a deferral, which push no commit. The design must choose: re-run open pull requests' status on those tracker events, evaluate at merge time (a merge queue, #1011), or declare the residual gap (ADR-019 point 3). → F2 T2.3 and T2.5.
- **K3** (S5) — proposed: state the rule for a pull request that closes no issue, the release pull request among them — in scope, or release pull requests exempt by project configuration. → F2 T2.3 and T2.5.

Use cases per Feature, for the slicing: F1 — UC-001, UC-002, UC-003, UC-004, UC-009, without their stabilisation parts; F2 — UC-005, UC-007, UC-008, UC-010, and the stabilisation parts of UC-001 (step 5), UC-003 (2a) and UC-004 (step 4); F3 — UC-006. Each Feature adds, as anchors of its use cases, the paths its new commands create, and revalidates them.

**`brief`'s stabilisation part moves into F2.** `brief` shows whether a stabilisation is on and limits what is free to pick to release scope, which needs F2's release-scope computation and the stabilisation fields (T2.1, T2.2); and UC-007 builds on UC-001's position, so F2 needs F1's `brief` (T1.2). Declared as they stood, the two dependencies would make a cycle between F1 and F2. So F1 T1.2 ships `brief` without the stabilisation, and F2 T2.2 adds it to `brief`.

Dependencies across the slicing, to declare when the Features are filed:

- **F2 needs F1.** UC-007 builds on UC-001's position, and F2 T2.2 extends the `brief` that F1 T1.2 ships.
- **F1 needs EPIC #508.** UC-003's claim is `handoff-issue --to-instance self`, #521.
- **EPIC #943 is blocked by EPIC #508's claim work (#508, #521).** The lifecycle commands make no ownership claims today — only `set-instance` reads the instance id — and every position rests on those claims.

Before the Features are filed: the authorisations listed above, and those the revalidation record adds (J refining DEC-035 point 1; never-merged intent notes refining DEC-044 point 2; E and DEC-043's read cost), and the operator's confirmation of the agent-made fixes. The `critic` and `architect` re-run asked for under Reviews ran on #890's pull request (2026-09-30).
