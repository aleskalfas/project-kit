---
authors:
  - Ales Kalfas <kalfas.ales@gmail.com>
started: 2026-06-12
---

# project-management: `done-work.py` crashes on every invocation; workflow gaps surfaced by the manual fallback

This note is a **handoff document**: written in an adopting project (`example-adopter`) but intended to be copied into the `pkit` repo's `.pkit/scratchpad/active/` and developed there. It reports one outright bug (a `NameError` that makes `done-work.py` unrunnable for any input) plus two workflow/state findings discovered while executing the script's contract manually. Mostly a bug report; sections 4-5 carry two small design questions.

The note is self-contained — a developer opening it inside pkit should not need the adopter-side conversation.

---

## 1. Environment

- Adopter: `example-adopter` (github.com/aleskalfas/example-adopter), single-repo, label-fallback mode (`has_projects_v2_board: false`).
- Backbone 1.66.0; project-management capability **v0.23.1** (schema_version 2 package).
- Trigger: first real merge through the capability — Task #3 / PR #4, agent-mode review with 5 APPROVED verdict comments posted, user merge authorization given in-session.

## 2. The crash (hard bug)

Any invocation of `done-work.py` crashes before the approval gate is even evaluated:

```
$ uv run .pkit/capabilities/project-management/scripts/done-work.py 3 --yes
Traceback (most recent call last):
  File ".../scripts/done-work.py", line 585, in <module>
    sys.exit(main())
  File ".../scripts/done-work.py", line 133, in main
    issue = _gh_get_issue(args.issue_number, config)
            ^^^^^^^^^^^^^
NameError: name '_gh_get_issue' is not defined
```

### Diagnosis (verified in the shipped tree)

- `done-work.py` **calls** `_gh_get_issue` exactly once (line 133) and **never defines it**; nothing of that name exists in `scripts/_lib/` either (`_lib/gh.py` exports `gh_env`, `gh_owner_flag`, `gh_run`, `load_adopter_config`, …).
- Sibling scripts each carry their own **module-local copy** of the helper — e.g. `close-issue.py` defines `def _gh_get_issue(issue_number, config)` at line 303 and calls it twice. At least six scripts use a get-issue helper of this shape.
- So the definition was evidently lost from `done-work.py` in a refactor/copy slip while siblings kept theirs. The script cannot run **at all** — this is not an edge case; the happy path is dead.

### Suggested fix (pkit's call)

1. Minimal: restore the module-local `_gh_get_issue` in `done-work.py` (copy from `close-issue.py:303`).
2. Better: the helper is duplicated across ≥6 scripts — promote it to `scripts/_lib/gh.py` and import everywhere (the `_lib` split exists for exactly this).
3. Regression guard: a smoke test that at minimum **imports / dry-runs every script entry point** (`self-test.py` looks like the natural home; CI upstream should run it per capability). A `NameError` on the main path means no test currently executes `done-work.py` even once.

## 3. What the manual fallback executed (a spec checklist for the fix)

With the script dead, the adopter executed its DEC-026 contract by hand. The steps — useful as the regression test's assertion list:

1. Approval gate: verified APPROVED reviewer verdict comments on PR #4 (agent mode per DEC-027/028).
2. `gh pr merge 4 --squash --delete-branch` — squash subject = PR title per git-conventions.
3. `git checkout main && git pull`.
4. Issue #3 auto-closed via the PR's `Closes #3`.
5. **State-label reconciliation — the step the script owns and nothing else did** (see finding 4.1).
6. Cascade pass on the parent Feature (see finding 4.2).

## 4. Two findings from the fallback (small design questions)

### 4.1 Closed issue kept its stale `state:review` label; the engine disagreed with the label

After the merge auto-closed #3, its labels still said `state:review`. Yet `move-issue.py 3 --to done` refused with:

```
error: no transition 'done' → 'done' declared in workflow.yaml for 'task'.
  legal targets from 'done': <none>
```

i.e. the **engine** already considered #3 to be at `done` (presumably derived from closed-ness) while the **label substrate** — the canonical state carrier in label-fallback mode per DEC-019 — still said `review`. The adopter reconciled by hand (`gh issue edit 3 --remove-label state:review --add-label state:done`).

Questions for pkit: where exactly does label reconciliation belong (done-work only? any close path? a repair sub-command)? And should engine-state derivation and label substrate disagreeing be a validator finding (`check-mesh.py`?) rather than silent?

### 4.2 Feature in `review` has no legal exit when its children close but its criteria remain open

The parent Feature (#2) had cascaded to `state:review` (when its only Task went to review). After the Task merged and closed, the Feature's honest state is "work continues" — more Tasks coming, acceptance criteria unticked. But:

```
$ move-issue.py 2 --to in-progress
error: no transition 'review' → 'in-progress' declared in workflow.yaml for 'feature'.
  legal targets from 'review': done
```

`workflow.yaml` gives features exactly one exit from `review`: `done`. A feature whose children all closed while the feature itself is far from done is stuck in `review` (the adopter left it there; presumably the next child's `start-work` cascade rescues it — unverified).

Questions for pkit: add a `review → in-progress` edge for container types (feature/umbrella/epic)? Or make the cascade smarter — a container only enters `review` when *its own* close-conditions are near (e.g. all children done AND criteria ticked), not whenever a child is in review? The second seems truer to DEC-006's intent; the first is the cheap patch.

## 5. Secondary observation

`move-issue.py`'s CLI takes `--to <state>` (named flag) while the adopter-facing error hints in other scripts' output suggest positional usage; trivial, but a consistency pass over the scripts' argument conventions would be cheap to bundle with the `_lib` promotion in section 2.

## 6. References and retirement criteria

- Capability: project-management v0.23.1, scripts `done-work.py`, `close-issue.py` (the surviving helper, line 303), `_lib/gh.py`, `move-issue.py`, `check-mesh.py`; schemas `workflow.yaml` (feature.review edges), `mandatory-issue-state.yaml` (DEC-019 label substrate).
- DEC-026 (work-ownership lifecycle — done-work's contract), DEC-006 (state machine + cascade), DEC-019 (mandatory issue state), DEC-027/028 (review modes / approval paths).
- Adopter evidence: PR #4 + its 5 verdict comments; issue #3 (label history); issue #2 (stuck in review).

To `done/`: `done-work.py` runs end-to-end on a real merge in an adopter (gate → squash → close → label reconciliation → cascade); a smoke/self-test executes every script entry point; the 4.1/4.2 questions answered (implemented or explicitly declined with rationale).
To `dropped/`: superseded by a larger rework of the scripts layer.
