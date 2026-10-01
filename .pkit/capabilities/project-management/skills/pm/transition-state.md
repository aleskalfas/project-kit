# pm transition-state — move an issue through the lifecycle state machine

Sub-procedure of the pm composite skill (`pm.md` in this folder). Per [project-management:DEC-020-methodology-as-executable-commands], this sub-procedure is a thin intent-to-command router: the state-machine rules + cascade live in `workflow.yaml` + the deterministic `scripts/move-issue.py` / `close-issue.py` / `reopen-issue.py` scripts; this file maps user intent to a script invocation and surfaces the result.

## When to use this operation

- The user wants to **move** an issue forward through the lifecycle (Todo → Backlog → In Progress → Review).
- The user wants to **close** an issue (PR-merge-driven closure or explicit won't-do gesture per [project-management:DEC-006-state-machine-and-cascade]).
- The user wants to **reopen** a closed issue (e.g., it regressed).
- The PR of an issue in Review needs its **reviewer verdicts**, or landing — checks, verdicts, merge (the review step below).
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

**Land the PR** of an issue in Review — wait for its checks, request the reviewer verdicts it still needs (agent review mode, per [project-management:DEC-028-agent-as-approver-paths]), merge — with one verb, run twice: once to check and review, once to merge on the user's authorisation.
```
pkit project-management land-work <N> [--wait-minutes <M> | --no-wait]
pkit project-management land-work <N> --yes --expect-head <sha>
```
`land-work` pins the PR's head and runs `review-pr` only once every check on that head has passed: the reviewers judge that head, and a later commit that changes what a reviewer checks makes its verdict stale (the freshness rule: the [capability README](../../README.md), "When a verdict stays fresh"), so reviewing a head whose CI then fails would spend a round of verdicts on a commit the fix replaces. Run it first without `--yes`: it merges nothing (a PR that has already merged it completes, as `done-work` does — the issue moves to Done, the closure cascade runs and the branch is cleaned up), and when the checks, the review and `done-work`'s gates all pass it stops on a `ready:` line naming the head and the command that merges it. Review → Done is user-authorised (the authorisation gate above): show the user the verdicts and the advisories the review step printed, and run the `ready:` line's command — `--yes --expect-head <sha>` — only on the user's authorisation. That authorisation is for that head and never extends to a later one; `--expect-head` stops the run if the PR has moved. The last line of a run says why it stopped. The exit codes are listed once, in the [capability README](../../README.md)'s "Landing a pull request in one command"; act on each:
- **0** — merged, and the issue done.
- **1** — hand the PR back to the builder with the last line: unpushed or diverged commits, a draft, a conflict with the base, a failed check, a `CHANGES_REQUESTED` (its blocking findings printed above the line, each with its reviewer), or a `done-work` refusal.
- **2** — nothing was changed: fix the invocation, or run the same command again once GitHub answers.
- **3** — the head moved, or is not the one authorised: report it to the user and stop. Do not run `land-work` again on your own: the new head needs its checks, its review and its own authorisation.
- **4** — queued, or the merge is unconfirmed: run the same command again once it merges.
- **5** — the checks are still running, or none has been reported: run again to keep waiting. Never fall back to `review-pr <N>` and `done-work <N>` because a wait ran out: `done-work`'s own gate does not wait for a check nobody reported, so that would merge a head no check ran on. That path is only for a project known to run no checks on pull requests.
- **6** — a reviewer could not run: run again once it can.
- **7** — a step failed that a re-run completes (a request that failed, a PR that merged meanwhile, a step after the merge): run the same command again.
- **8** — ready, not merged: show the user the verdicts and ask; on the authorisation, run the `ready:` line's command.

To request the verdicts without merging, run `pkit project-management review-pr <N>` once the checks on the PR's head have passed. In a project that runs no checks on pull requests, `land-work` has no run to wait for: land with `review-pr <N>` and then `done-work <N>`. (`<N>` is the issue.)

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
