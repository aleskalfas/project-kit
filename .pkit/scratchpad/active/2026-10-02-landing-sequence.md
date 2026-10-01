---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-02
---

# Landing sequence — one `pkit pull-request land` for every caller

The design note of the landing series (#1220 and the issues it was split into). It states
the question, what is decided, how landing works today, the specification the series
builds, the order of the pull requests, and the scenario table that pins every caller's
behaviour before any of it moves.

## The question

Three commands land a pull request on GitHub. project-management's `done-work` and
`merge-pr` share one copy of the landing sequence (`_lib/pr_merge.land`); the backbone's
`pkit release merge` has another (`release.merge_release_pr`); `land-work` lands through
`done-work`. Each copy reads the PR, refuses what it must, merges or enqueues, reads
again, waits for the merge queue, takes the PR out of the queue when its head moved, and
deletes the head branch. The backbone's `pkit pull-request` noun already holds the
single requests (`read`, `squash-defaults`, `merge`, `enqueue`, `wait`, `dequeue`), but
the sequence over them is written twice, and the two copies differ — some differences by
design, some by accident. The defect that started this work (#1200) was a mistake in a
sequence, not in a primitive.

How should the sequence live once, in the backbone, with each caller's choices as
options, guarded against acting on another repository, deleting a head branch only at
the head that merged, and recovering from a request that gets no answer?

## What is decided

**[ADR-061](../../../tech-docs/architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md)**
(accepted) places the acts that land a pull request in the backbone's `pull-request`
command: GitHub only, through `gh`, provisionally (#1222 raises the placement for a core
decision). The JSON documents are the contract, and no caller decides on an exit code.
Every caller keeps five obligations: merged means the service says merged; a PR whose
head moved is taken out of the queue; an unconfirmed merge is reported as unconfirmed;
the head branch is deleted only after the merge; the remote head branch is deleted only
at the head that merged. Point 5 says the move of the sequence into the command is due;
point 6 says the command guards the changes it makes; point 8 says a direct merge is to
carry the PR body.

The architect refined ADR-061 for this series; the refinement is committed with the
guard pull request (#1254), as its own commit. It gives the command the deletion of a
merged PR's head branch (only while its tip is the head the caller names), lets the
command apply the callers' choices as options to the reading it takes just before a
request, runs the guard once at the start of a landing, and requires a line written
before each request so that a caller left without an answer can tell whether a request
was made.

The maintainer delegated five choices, decided as follows:

- **The steps move into the command.** `pkit pull-request land` performs the sequence;
  the callers state their choices as options and keep their gates, their wording, and
  what follows a merge.
- **No release is cut before the guard lands.** `pkit pull-request` has not shipped in a
  release yet. Until the guard pull request merges, no release goes out, so the
  unguarded-mutation gap ADR-061 point 6 describes never reaches an adopter, and nothing
  in the series needs a migration.
- **No title-changed refusal.** The command makes no rule about a title or a body that
  changed since the caller's gates read them. A caller that needs one checks the merge
  commit after the merge.
- **An already-queued PR in a queue that does not make COR-009's commit:**
  project-management refuses it (and the PR stays queued), `pkit release merge` warns and
  waits. The command takes this as an option, `--queued-bad-shape refuse|warn`.
- **The guard runs at entry.** Every landing that is not a dry run runs the guard once,
  before its first reading — not just before its first request, which on an
  already-queued PR can be a dequeue half an hour into a wait, with nobody left to answer
  a question.

## How a pull request lands today

**The noun.** `src/project_kit/pull_request_landing.py`, wired in `cli.py`: `read`,
`squash-defaults`, `merge --subject [--head] [--admin]` (`--match-head-commit`, never
`--delete-branch`, no body), `enqueue` (`--auto --match-head-commit`), `dequeue` (read,
request, read again), and `wait`, which streams `reading` documents and ends with
`ended: merged|queued|left|head-moved`, declaring a PR out of the queue only on two
readings running, and waiting as long as the queue estimates plus two minutes, at most
thirty. `run_gh` has no timeout: only project-management bounds the calls
(`merge_queue.TIMEOUT_SECONDS`, `_answers`), so `pkit release merge`, which imports the
module, can hang on a `gh` that never answers.

**The two copies.**

| Step | project-management (`done-work`, `merge-pr`) | `pkit release merge` | Difference |
|---|---|---|---|
| Cross-repository guard | `session_guard.enforce` | none | accident (ADR-061 point 6) |
| The caller's own read of the PR, for its gates | yes | yes | the caller's |
| Queue read before the gates, and refusal | a reading and `queue_refusal` before any gate, in the order: admin, bypass-ci, squash method, dropped head, squash defaults | one reading: merged → clean-up; queued → warn on a bad squash shape and wait, skipping the gates; otherwise the gates, then refuse on squash method, defaults, dropped head | skipping the gates on a queued PR is release's by design; the refusal order is an accident; project-management refuses an already-queued bad-shape PR but leaves it queued, where it can still merge |
| A second reading just before the request | yes (`land`) | no | accident |
| Already merged at that reading | merged; warn when at another head | clean-up | same |
| Already queued | wait | wait | same |
| Dropped head | refused unless `--force` | refused unless `--force` | the caller's option |
| Enqueue or direct merge, pinned | `--admin` possible; no answer → `_unanswered` (one reading: merged, queued, or neither); refused → failed | no `--admin`; refused → error; no unanswered path, no timeout | accident |
| Body on a direct merge | not passed | not passed | ADR-061 point 8 gap |
| Read again after a direct merge, wait if not merged | yes | yes | same |
| Head moved → dequeue | `_wait` | `_await_the_queue` | same |
| Left the queue unmerged | the caller works out whether a queue was seen | the same derivation, again | same, twice |
| Merged at another head | warn, proceed | warn, proceed | the reporting is the caller's |
| Remote branch deletion | `pr_merge.delete_remote_branch` | `release._gh_delete_remote_branch` | two copies; neither checks the tip |
| Local clean-up | `cleanup_local`, back to the default branch | `_git_cleanup_local`, back to the PR's base | two copies; base or default by design |

**The guard today.** The comparison lives only in project-management's
`_lib/session_guard.py` (`evaluate`: the git common directory or the normalised origin of
the target, against `CLAUDE_PROJECT_DIR`; `enforce`; about forty scripts call it; its
prompt goes through `input()`, to standard output). The backbone holds no comparison.
Nothing guards `pkit pull-request merge|enqueue|dequeue` or `pkit release merge`.

**Processes per `done-work` landing.** On the queue path, six `pkit pull-request` starts
(1.8–3.0 s of start-up); without a queue, four; one more when the head moves; plus
`pkit repository base` once.

**Consumers and what is pinned.** `land-work` reads the PR after `done-work` through
`merge_queue.read` and a raw `gh pr view`. Tests reach the backbone through
`tests/pull_request_backbone.in_process`, and many verb tests patch `pr_merge`'s and
`merge_queue`'s functions. To keep: the exit codes (done-work 0/1/2/3/4, merge-pr
0/1/2/3/4, release 0/1/3/4); the steps after a merge only once GitHub reports it merged;
an unanswered request never taken for a failed one; the two-readings rule; the strict
decoding of a reading; the "no such command" message for an older backbone;
`schema_version` 1; the fork refusal on deletes and the merged-head guard on local
deletes; project-management's wait constants equal to the backbone's.

## The specification

### Fit rules every pull request holds to

- **F1. `gh` stays in the command's own process group.** project-management starts
  `pkit` in a session of its own and ends it with a group kill. `command_runner` starts
  an outermost run in a new session, which would take a `gh` out of the group the kill
  reaches. One bounded-start function in `command_runner` for `gh`: the caller's process
  group; on overrun the child alone is killed and its pipes are closed unread. No third
  runner.
- **F2. Which backbone answers the comparison.** The router picks the backbone from the
  working directory, so the capability's guard runs the comparison from its own project
  root and passes the target directory as an argument.
- **F3. The normaliser has a second consumer** (the bootstrap gate): the comparison's
  document carries the target's identity, so the bootstrap gate reads the same answer.
- **F4.** `merge` and `enqueue` lose their last caller once project-management lands
  through `land`; removing them is free before a release. Decided in the pull request
  that moves project-management; `dequeue` stays.
- Nobody decides on an exit code of the noun; `schema_version` stays 1 (every change is
  an addition); no release before the guard, so no migration.

### The command

`pkit pull-request land N --head SHA --subject TEXT [--seconds S] [--allow-dropped-head]
[--admin] [--direct-only] [--queued-bad-shape refuse|warn] [--allow-foreign-repo]
[--dry-run] [--json]`. `refuse` is the default. There is no refusal of a changed subject
or body.

project-management passes `--allow-dropped-head` for `--force`, `--admin` for `--admin`,
`--direct-only` for `--bypass-ci`, and shape `refuse`. `pkit release merge` passes
`--allow-dropped-head` for `--force` and shape `warn`; skipping its gates on a queued PR
stays its own, read from its own dry run.

The sequence: the guard at entry, one reading, the first matching row of the table
below, the request, then settle and wait. `H` is `--head`.

| PR state at the reading | no option | `--admin` | `--direct-only` | shape bad, `refuse` | shape bad, `warn` | `--allow-dropped-head` |
|---|---|---|---|---|---|---|
| unreadable | none → `unreadable` | same | same | same | same | same |
| merged at H | none → `merged` | same | same | same | same | same |
| merged at another head | none → `merged-at-another-head` | same | same | same | same | same |
| closed | none → `closed` | same | same | same | same | same |
| queued at another head | `dequeue` → `head-moved` | same | same | same | same | same |
| open, not queued, head ≠ H | none → `head-moved` | same | same | same | same | same |
| queued at H | wait | none → `refused` `admin-on-queue` | none → `refused` `queue-not-allowed` | none → `refused` `queue-not-squash` or `squash-defaults`; the PR stays queued | wait, with a `warnings[]` entry | as no option |
| dropped at H, queue base | none → `refused` `dropped-head` | `refused` `admin-on-queue` | `refused` `queue-not-allowed` | `refused` (shape) | `refused` (shape; `warn` relaxes only the queued row) | `enqueue` → wait |
| open, not queued, queue base | `enqueue` → wait | `refused` `admin-on-queue` | `refused` `queue-not-allowed` | `refused` (shape) | `refused` (shape) | as no option |
| open, direct base | `merge` (subject, body, pinned) → read → `merged`, else wait | `merge --admin` | as no option | shape not read | shape not read | as no option |

- One refusal order: `admin-on-queue`, `queue-not-allowed`, `queue-not-squash`,
  `dropped-head`, `squash-defaults` (the defaults read last). Defaults that cannot be read
  end `unreadable` with `reason_kind: squash-defaults`; under `warn` on a queued PR they
  are a warning.
- A wait ends `merged`, `merged-at-another-head`, `queued`, `unconfirmed`, `head-moved`
  (with the dequeue's outcome), `dropped` (a queue was seen) or `not-merged` (none was).
  A request `gh` refuses ends `failed`.
- A dry run follows the same table and makes no request and asks nothing. A cell with a
  request or a wait ends `planned` with `would: merge|enqueue|wait|dequeue`; every other
  cell ends as it would.

### Documents

Version 1, every field an addition. Events: `reading`, `requesting {request, head}`,
`requested {request, outcome}` (`outcome` null when `gh` was ended at its bound), `end`.
The end document carries `dry_run`, `ended`, `reason_kind`, `reason`, `would`, `path`,
`checked_head`, `merged_head`, `merge_commit`, `dequeue`, `reading`, `warnings[]`,
`bound_seconds`, the shape `{squashes, title, message, conforms, unreadable}`, and the
guard `{verdict: same-repo|diverged|overridden|undetermined, undetermined_kind, anchor,
target}`. Decoding is strict per kind: an unknown `ended` or a missing key is no answer.
A test pins that no caller reads the exit code.

### Requests and recovery

Every `gh` call is bounded, each bound strictly below the bound project-management puts
on the subcommand (pinned by a test). `requesting` is written and flushed before the
request is sent (a test kills the process between the two). A request that got no answer,
inside the command: read; merged → continue as merged; queued → wait; neither → a second
reading after the interval; neither again → `failed` with `reason_kind: not-made`; any
unreadable reading → `unconfirmed`.

With no end document, project-management ends the process group, then runs `land
--dry-run` with the same options: `merged*` → the merge; `would: wait` → queued;
`would: dequeue` → run `dequeue`, then head-moved (the "take it out yourself" message
comes from that outcome); anything else → unconfirmed if a `requesting` for a merge or
an enqueue was seen without a refused outcome, otherwise failed-with-retry.
project-management never concludes "not made" itself.

### The guard

A module `project_kit/session_guard.py`. `evaluate(target_dir, anchor)` is pure.
`clear(target_dir, confirmed, interactive)` returns a clearance saying how it passed
(`same-repo`, `undetermined`, `flag`, `terminal`) or refuses. Every mutating function
requires a clearance and a `cwd`; the guard and the default `gh` runner take the same
`cwd`, so an import can neither skip the guard nor aim it elsewhere. `land` clears once
at entry and hands the clearance down. `pkit release merge` clears at its own entry
(covering its deletion and local clean-up) and gains `--allow-foreign-repo`. The prompt
goes to standard error. No terminal → `refused` with `reason_kind: foreign-repository`.

project-management passes `--allow-foreign-repo` exactly when its own `enforce` passed by
flag or at a terminal, so `enforce` returns how it passed; a disagreement between the two
comparisons fails closed. With no anchor there is no session to compare with: `pkit
release merge` in a pipeline needs no flag, and the verdict reads `undetermined`, never
`same-repo`. A git fault warns and proceeds, as today. A dry run always carries the
`guard` field; `diverged` with no confirmation ends `refused` `foreign-repository`, with
a note that a terminal run would ask. `CLAUDE_PROJECT_DIR` appears in `src/` once, as a
named constant labelled as Claude Code's anchor; the documents name only the anchor and
the target. A set `GH_REPO` redirects `gh` away from the working directory's remote and
neither guard compares it: the CLI reference names it as a residual gap, or the guard
compares it.

**The comparison exposed:** `pkit repository session [--target DIR] [--json]` — a
reading only (no prompt, no override), local and network-free; its document carries
`verdict`, `undetermined_kind`, `anchor`, `target` and the target's identity (F3). It
works outside a project tree; the capability runs it from its own project root with
`--target` (F2).

### `delete-branch`

`pkit pull-request delete-branch N --expect SHA [--allow-foreign-repo] [--json]` —
guarded; refuses unless the PR is merged and not cross-repository; deletes only while
the tip equals `--expect`, otherwise ends `kept` with the tip, or `gone`. To verify first,
with one real call: whether GraphQL `updateRefs` with `beforeOid` deletes atomically
(compare-and-delete). If it does not, read then delete, and name the race in the
reference.

### The body on a direct merge

The command reads the body in the reading it takes just before the request. To verify
first: whether an explicit body drops the `Co-authored-by:` trailers the service
composes; if it does, let the service compose where the defaults read `PR_BODY`, and pass
the body only otherwise. The CLI reference names the gap that body gates judge an earlier
body, on both paths. No title rule in the backbone.

### How each caller words the ends

**CLOSED** is a fact: done-work exit 3, not worth a retry; merge-pr exit 1; release exit
0, "nothing to merge".

| `ended` | done-work (kind, exit) | merge-pr | release |
|---|---|---|---|
| `merged`, `merged-at-another-head` | the steps after the merge: merged 0, or follow-up owed | 0 | 0 |
| `queued`, `unconfirmed` | queued / unconfirmed, 4 | 4 | 4 |
| `refused` | refused, 1 | 1 | 1 |
| `unreadable` | unreadable, 2 | 3 | 1 |
| `failed` | refused, 3, retry | 3 | 1 |
| `head-moved` | head-moved, 3 | 3 | 3 |
| `dropped`, `not-merged` | refused, 3 | 3 | 3 |

**land-work:** a head that moved before any request reaches `EXIT_HEAD_MOVED` directly;
`_request_failed` stays for `failed`; `closed` maps to `EXIT_NEEDS_CHANGE`;
`DoneWorkRun` carries the merge commit and the reading (required; it replaces
`_as_commit`'s raw `gh pr view`).

### The bound

The dry run's document carries `bound_seconds`, the sum of the inner bounds for the
options given; project-management bounds the `land` process by that plus its start-up
margin, with a fallback constant pinned by a test.

### Criterion 4, restated

#1220's "one process per landing" is not reachable: project-management's own record
requires the reading before its gates. Restated: the requests, the wait and the dequeue
of one landing run in one `pkit pull-request land` process, and a `done-work` landing
starts `pkit` at most five times on either path (the comparison, the pre-gate dry run,
the landing, the branch deletion, the default branch), pinned by a test that counts the
starts.

## The pull requests, in order

| Issue | Contents | Changesets | Record |
|---|---|---|---|
| #1253 | Tests only: one fake of the hosting service and the scenario table, a `today` cell per caller, green on current code | none | none |
| #1254 | The guard: the backbone's comparison and clearance; `merge`, `enqueue`, `dequeue` and `pkit release merge` guarded, with `--allow-foreign-repo`; `enforce` reports how it passed; the confirmation passed on; the parity test; the gap statement removed from the CLI reference | backbone minor; project-management patch with `requires_backbone: release` | the ADR-061 refinement, as its own commit |
| #1255 | `delete-branch --expect`; the reading gains `head_ref` and `cross_repository`; both callers delete through it | backbone minor; project-management patch with `requires_backbone: release` | DEC-013's paragraph refined |
| #1256 | Bounded `gh` (F1); an unanswered request reported as unanswered, never as refused; the two-readings rule in the module; release gains the unanswered path; project-management's `_unanswered` stops concluding "not made" on one reading | backbone minor; project-management patch with `requires_backbone: release` | none |
| #1257 | The body on a direct merge, once the GitHub facts are verified | backbone minor | none |
| #1258 | `land`, the dry run, the events, the table, the shape facts, `bound_seconds`; release through it | backbone minor | none |
| #1220 | project-management through `land`: the client, `pr_merge.land` as an adapter, `queue_refusal` replaced by the dry run, the recovery rule, the `DoneWorkRun` fields, land-work's mapping, the start-count test; F4 decided | project-management minor with `requires_backbone: release` | none |
| #1259 | `pkit repository session`; the capability's guard and bootstrap gate read it (F2, F3); the copy and the parity test retired | backbone minor; project-management patch with `requires_backbone: release` | a second ADR-061 commit retiring the "until" clauses; a forward pointer in ADR-034 |

## The scenario table

`tests/test_landing_scenarios.py`, on the shared fake `tests/hosting_fake.py`. Each row
runs `done-work`, `merge-pr`, `pkit release merge` and `land-work` through their real
entry points, and records for each what happens today: the outcome, the landing's
requests to the service in order, whether the steps after the merge ran, and what became
of the remote and the local head branch. A pull request of the series that changes a
cell adds the cell it expects as that row's `after` entry; the test holds the caller to
it, and `today` keeps what the caller did before.

The rows: no queue; a queue that merges within the wait; a queue with the PR's checks
pending; a PR already queued; a wait that runs out; a direct merge `gh` only enqueued;
auto-merge holding the PR on a base with no queue; a queue switched on after the first
reading; a base changed after the first reading; `--admin` and `--bypass-ci` on a queued
base; a queue that does not squash; squash defaults that are not the convention; squash
defaults that cannot be read; an already-queued PR in a queue that does not squash; a
dropped head, without and with `--force`; a head that moves while queued (the dequeue
accepted, or failing); a PR queued at another head on a re-run; a PR merged by someone
else before the run, by the queue after an earlier run, meanwhile at the checked head,
and meanwhile at another head; two landings racing, on a direct base and on a queue; a
PR closed before the run and meanwhile; a request unanswered, then merged, queued or
neither; a request made, then reported failed by `gh`; readings failing after a direct
merge and after an enqueue; a rate limit mid-wait; auto-merge not allowed; a process
killed after `requesting` (not drivable today); the remote tip equal, moved, gone, a
fork's, protected, another open PR's, and a reused name; a foreign repository refused,
flagged, and confirmed at a terminal; no session anchor; a backbone without the noun
(today's form of a `pkit` without `land`); a wait ending in a way project-management
does not know; a reading without a deciding key.

Differences between the copies the table found beyond the as-built table above:

- **A PR someone else merged directly, before the run.** done-work and land-work complete
  it (the issue moves to Done, the branch is deleted); merge-pr refuses it (exit 1);
  release cleans up (exit 0).
- **Squash defaults that cannot be read.** project-management ends unreadable (done-work
  2, merge-pr 3); release refuses (exit 1).
- **Auto-merge holding the PR on a base with no queue.** project-management merges
  directly; release reads the hold as the queue, skips its gates, warns that "the merge
  queue" merges by an unreported method, and waits for GitHub's merge.
- **A retarget or a queue switched on after the first reading.** project-management's
  second reading catches it; release enqueues into a queue that merges by MERGE, or has
  its direct merge enqueued with squash defaults it never read.
- **A request `gh` reports failed after the service made it** (a 502 after the merge).
  Both copies take it for a failed request and run nothing after the merge; land-work
  then reads the PR merged and asks for a re-run.
- **Two landings racing on a queue.** `gh` refuses the second enqueue of a queued PR:
  both copies report a failed request while the PR sits in the queue, and land-work's
  re-read (`gh pr view`, which does not show the queue) says "not merged".
- **A foreign repository at a terminal.** land-work's guard asks, then done-work's asks
  again: two questions for one landing.
- **Deleting a branch another open PR uses**, or a reused name, closes that PR in every
  copy: the tip is not checked.

Two of the fake's answers rest on gh 2.x's merge command as read, not on a live call:
`gh pr merge` on a PR already merged does not merge it again and exits 0; on a PR
already in the queue it changes nothing and exits 1.

## Findings that shaped the specification

- A recovery that reads "no accepted request" as "nothing was made" can be wrong when
  the process dies between sending and writing: hence `requesting` before each request,
  and "not made" only from two readings.
- Guarding only before the first request leaves an already-queued landing to ask, or
  refuse, half an hour into a wait: hence the guard at entry.
- Passing the confirmation through only when project-management lands through `land`
  would break its confirmed cross-repository landings in between: hence the pass-through
  in the guard pull request.
- Turning project-management's refusal of an already-queued bad-shape PR into a warning
  would change what DEC-026 says: hence the shape choice as an option of the call.
- `subject-changed` closed a window of seconds and left the queue's thirty minutes open:
  dropped.
- land-work was missing from the mapping, and "one process per landing" is not reachable
  while project-management reads before its gates: hence land-work's mapping and
  criterion 4 restated.
- About a third of the rows are not applicable today or encode accidents: hence `today`
  and `after` cells, and a land-work column.
