---
authors:
  - Ales Kalfas <ales.kalfas@apoco.com>
started: 2026-06-17
---

# project-management: `start-work.py` assumes a Backlog start state; a just-filed Task (Todo) is left with a created branch but no transition

This note is a **handoff document**: written in an adopting project (`trip-planner-agent`) but intended to be copied into the `pkit` repo's `.pkit/scratchpad/active/` and developed there. It reports one bug in `start-work.py` — the script hard-assumes the issue is already in `backlog` and does a single `move-issue --to in-progress` hop, which the state machine refuses for an issue still in `todo`. Because the refusal happens *after* the branch + assignee side-effects, the operation half-completes: a real branch exists, the assignee is set, but the lifecycle state never advances. This is exactly the partial-state outcome DEC-017's hard-gate discipline is meant to avoid.

The note is self-contained — a developer opening it inside pkit should not need the adopter-side conversation.

---

## 1. Environment

- Adopter: `trip-planner-agent` (github.com/aleskalfas/trip-planner-agent), single-repo, label-fallback mode (`has_projects_v2_board: false`).
- Backbone 1.89.0; project-management capability **v0.23.2** (schema_version 2 package).
- Trigger: the canonical "file a Task, then start work on it" flow. Task #101 filed via `create-issue.py` (lands in `todo` — no `state:*` label), then `start-work.py 101 --yes`.

## 2. The bug

`start-work.py 101 --yes` produced:

```
error: no transition 'todo' → 'in-progress' declared in workflow.yaml for 'task'.
  legal targets from 'todo': backlog, done
start-work: #101
  branch:    docs/101-author-the-writable-layer-schemas
  assignee:  aleskalfas
  created branch: docs/101-author-the-writable-layer-schemas
```

The branch was created and the assignee set, but the issue stayed in `todo`. The operator had to finish by hand:

```
move-issue.py 101 --to backlog --yes && move-issue.py 101 --to in-progress --yes
```

### Diagnosis (verified in the shipped tree)

- `start-work.py` composes over `move-issue` with a **single** target hop: `_invoke_move_issue(args.issue_number, "in-progress", ...)` (line 184). It never moves through `backlog` first.
- Its docstring states the assumption outright — *"Transitions an issue Backlog → In Progress"* (lines 10-11) and *"transition Backlog → In Progress"* (line 70). The script is written for an issue **already in `backlog`**.
- But `create-issue.py` files into `todo` (no `state:*` label; absence = `todo`). `workflow.yaml` declares `todo → backlog` (command `promote-issue`, authorisation `user`) and `todo → done`, but **no `todo → in-progress`** edge. So the very common "file then immediately start" sequence always trips the missing edge.
- **Ordering makes it worse.** The side-effects run *before* the transition: branch creation at line 170, assignee at line 176, then `move-issue` at line 184. When `move-issue` exits non-zero, `start-work` returns that code (lines 185-186) — but the branch and assignee are already committed. Caller sees a failure exit, yet the repo and the issue are in a half-changed state. (The reversed print order in the capture above — error before the `start-work:` header — is just stderr/stdout interleaving under a pipe; the substantive issue is the partial mutation, not the ordering of the lines.)

### Suggested fix (pkit's call)

1. **Make `start-work` drive the full path to `in-progress`, not one hop.** Detect the issue's current state and walk the legal chain (`todo → backlog → in-progress`) — or, cleaner, give `move-issue` a "resolve a legal path to the target state and walk it" capability and have `start-work` ask for `in-progress` from wherever the issue is. A freshly-filed Task starting work is the *normal* path, not an edge case.
2. **Respect the `todo → backlog` authorisation.** That edge is `authorisation: user` (it's the scheduling/triage gesture, `promote-issue`). If `start-work` auto-walks through it, decide deliberately whether starting work implies promotion authority, or whether `start-work` should require the issue to be promoted first and refuse cleanly (with the `promote-issue` remediation hint) rather than half-acting.
3. **Order side-effects after the transition, or make the operation atomic / idempotent on re-run.** Do the (refusable) state transition first; only create the branch + set assignee once the transition is known to succeed. As it stands, a failed `start-work` leaves a branch behind that a re-run then has to treat as the idempotent path — which works, but only by luck of the existing-branch check.
4. **Regression guard:** a test that files an issue (→ `todo`) and runs `start-work` end-to-end, asserting the issue reaches `in-progress`. The current happy-path assumption (already in `backlog`) is almost certainly what the tests exercise, which is why the file-then-start path slips through.

## 3. Relationship to the earlier `done-work` note

This is the same class of finding as `2026-06-12-pm-done-work-crash.md` §4.1/§4.2 and its 2026-06-15 update: the lifecycle scripts make state-position assumptions that hold on a curated path but not on the ordinary one, and a durable side-effect (there: a merge; here: a branch) lands while the lifecycle transition strands. Worth fixing together as a "scripts assume a state they don't verify" sweep over `start-work` / `move-issue` / `done-work`.

## 4. References and retirement criteria

- Capability: project-management v0.23.2, scripts `start-work.py` (lines 10-11, 70, 170-186), `move-issue.py`, `create-issue.py`; schema `workflow.yaml` (`todo` transitions, lines 86-92 and 189-194).
- DEC-026 (work-ownership lifecycle — start-work's contract), DEC-006 (state machine + cascade), DEC-017 (prerequisites / no mid-operation partial state), DEC-019 (mandatory issue state / label substrate).
- Adopter evidence: Task #101 (filed into `todo`, branch `docs/101-author-the-writable-layer-schemas` created by the failed run, state advanced manually afterward).

To `done/`: `start-work` takes a freshly-filed (`todo`) issue to `in-progress` in one invocation — either by walking the legal path or by refusing cleanly with no side-effects when promotion is owed — and a regression test exercises the file-then-start path.
To `dropped/`: folded into a broader rework of the lifecycle scripts layer.
