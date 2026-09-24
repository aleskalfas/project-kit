---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-09-24
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
