# pm transition-state — move an issue through the lifecycle state machine

Sub-procedure of the pm composite skill (`pm.md` in this folder). Per [project-management:DEC-020-methodology-as-executable-commands], this sub-procedure is a thin intent-to-command router: the state-machine rules + cascade live in `workflow.yaml` + the deterministic `scripts/move-issue.py` / `close-issue.py` / `reopen-issue.py` scripts; this file maps user intent to a script invocation and surfaces the result.

## When to use this operation

- The user wants to **move** an issue forward through the lifecycle (Todo → Backlog → In Progress → Review).
- The user wants to **close** an issue (PR-merge-driven closure or explicit won't-do gesture per [project-management:DEC-006-state-machine-and-cascade]).
- The user wants to **reopen** a closed issue (e.g., it regressed).
- The PR of an issue in Review needs its **reviewer verdicts** (the review step below).
- The agent is running a cascade pass after a child's state changed (the scripts handle the cascade internally; this sub-procedure is the entry point).

This operation **does mutate** issue state. Every mutation is gated by the membership predicate (per [project-management:DEC-021-team-membership-gate]) + the schema's authorisation field + the checkbox close-gate (on closure paths) per [project-management:DEC-007-checkbox-validation].

## What the scripts enforce

The deterministic enforcement lives in the three verb-subject scripts. Each reads `workflow.yaml` + `issue-types.yaml` + the adopter's config at every invocation; rule changes propagate automatically without skill edits.

Behaviour summary (the scripts are the source of truth — read them for the exact contract):

- **Membership gate** (DEC-021) — closed mode refuses non-members with the standard refusal template.
- **Transition lookup** — `move-issue.py` looks up the requested transition in `workflow.yaml`'s `transitions:` list and refuses any move not in the schema, with a diagnostic listing the legal targets.
- **Authorisation gate** — user-authorised transitions (Todo → Backlog; Review → Done; Backlog/Todo → Done; In-progress → Done parent close) require `--yes` from the caller as the explicit authorisation signal; bypassable-with-audit transitions accept `--bypass --bypass-reason "..."` to record an audit comment.
- **Forward cascade** (DEC-006) — `move-issue.py` walks the parent chain via the body's parent-ref line and bumps any parent that's behind. Each bump is journaled like the issue's own move, from the state the parent held before, with the child's move as its reason; a bump the engine refuses (a parent in Todo taken straight to In Progress, which the workflow does not declare) warns the same way a direct move's refusal does. Skip with `--no-cascade`.
- **Closure cascade** (DEC-006) — `close-issue.py` surfaces parent-eligibility findings after the close, never auto-closes parents.
- **Checkbox close-gate** (DEC-007) — `close-issue.py --mode=wont-do` refuses if any `- [ ]` box remains unticked in the body. Tick the satisfied criteria with `check-criterion <N> <index>...` (per DEC-038) before re-running the close; reach for `--skip-checkbox-gate` only when a criterion is genuinely won't-do (discouraged).

## How to invoke

Dispatch to the script via the kit-level capability-command dispatcher (per [pkit:COR-021]):

**Move forward:**
```
pkit project-management move-issue <N> --to <todo|backlog|in-progress|review|done> \
  [--bypass --bypass-reason "<text>"] [--no-cascade] [--dry-run] [--yes]
```

**Request the reviewer verdicts** on the PR of an issue in Review (agent review mode, per [project-management:DEC-028-agent-as-approver-paths]):
```
gh pr checks <PR> --watch
pkit project-management review-pr <N>
```
`review-pr` runs once every check on the PR's head commit has passed; `gh pr checks --watch` waits for them, and as a read it is open to the project-manager. The reviewers judge that head, and the merge gate counts no verdict older than the PR's latest commit, so reviewing a head whose CI then fails spends a round of verdicts on a commit the fix replaces. When the PR has no checks configured (`gh pr checks` reports none and exits non-zero), run the review. When a check fails, hand the PR back to the builder and do not run the review. (`<N>` is the issue, `<PR>` its pull request.)

When the verdicts come back, a fix round carries the findings the reviewer marks blocking; each advisory is answered in the PR body or filed as a follow-up, scoped by [create-issue](create-issue.md)'s intent recognition.

**Close (won't-do):**
```
pkit project-management close-issue <N> --mode wont-do --reason "<text>" \
  [--skip-checkbox-gate] [--no-cascade] [--dry-run] [--yes]
```

**Close (PR-merge cascade hook):**
```
pkit project-management close-issue <N> --mode pr-merge [--no-cascade]
```

**Close a leaf done through another Task's merged PR** (the PR never named it, so GitHub did not close it; verified merged, checkbox-gated, reference commented, closed as completed):
```
pkit project-management close-issue <N> --mode pr-merge --pr <M> [--dry-run] [--yes]
```

**Reopen** (removes the state label, so the issue reads as backlog with a milestone and todo without; also repairs an open issue still labelled done):
```
pkit project-management reopen-issue <N> [--reason "<text>"] [--dry-run] [--yes]
```

**Attach an issue to a milestone, or move it to another** (no state change; the first-line milestone ref follows; the reason goes into an audit comment — a Todo issue is scheduled with `promote-issue --milestone` instead):
```
pkit project-management edit-issue <N> --milestone <number|title> | --clear-milestone --reason "<why>" [--dry-run] [--yes]
```

**Close a milestone, rolling its open children forward** (a date-based Milestone, or an `either` one from its due date: each open child moves to the rollforward target through the `edit-issue --milestone` move above, its state kept, with one audit comment naming the close; closed children stay, and a parent on the Milestone moves with its open children. The target is `--target`, else the Milestone's `Rollforward target:` line, else the next-numbered open Milestone of its category — with no candidate or more than one, nothing is moved or closed until the user names it. A content-based close, or an `either` one before its due date, moves nothing: open children hold it unless `--force`. `--dry-run` lists every move. Exit 4 means the Milestone closed but a move failed — re-run the same command to finish):
```
pkit project-management close-milestone <n> [--target <number|title>] [--force] [--dry-run] [--yes]
```

**Tick / untick acceptance criteria** (DEC-038 batch substrate primitives — prefer these over a whole-body `edit-issue` for a checkbox flip; address by 1-based index matching `show-issue --field criteria`, with an optional expected-text guard):
```
pkit project-management check-criterion <N> <index> [expected-text] [<index> [expected-text]] ...
pkit project-management uncheck-criterion <N> <index> [expected-text] ...
pkit project-management check-criterion <N> --section doc-impact <index> ...   # `## Doc impact` boxes (show-issue --field doc-impact)
```

**Set classification field(s)** (DEC-038 — declarative, batch, idempotent; reuses create-issue's classification resolution rather than hand-editing labels):
```
pkit project-management set-field <N> [--priority X] [--workstream Y] [--parent M] [--dry-run] [--yes]
```

Direct-path is equivalent for adopters whose kit predates the dispatcher:
```
.pkit/capabilities/project-management/scripts/move-issue.py 42 --to in-progress
```

## Handling the script's output

- **Success** — the script prints `[ok] transitioned #N: <old> → <new>` (or the equivalent for close/reopen) on the final line. Surface verbatim.
- **Refusal** — surface the script's stderr message verbatim. Refusals carry structured remediation; do not paraphrase.
- **`gh` failure** (exit 3) — surface the stderr; remediation usually lies outside the methodology.

## Intent recognition before invocation

Three judgments belong to the LLM before invoking the script — these are interpretation, not deterministic:

1. **Pick the operation.** Map the user's natural-language intent to `move`, `close`, or `reopen`. "Start work on #42" → move-issue --to in-progress; "won't fix this" → close-issue --mode wont-do; "this regressed" → reopen-issue.
2. **Pick the target state for `move`.** Default to the next-forward state from the issue's current state unless the user names a specific target.
3. **Resolve authorisation prompts.** When the script returns a refusal mentioning `--yes` or `--bypass`, surface the prompt to the user; re-invoke once the user has authorised.

Everything else is the scripts' job — pass the inferred arguments through and surface the result.
