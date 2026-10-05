---
authors:
  - Aleš Kalfas
started: 2026-10-01
---

# Review load after the fixes

## The question

`2026-09-30-review-load-and-friction-prs` (retired to `done/`) measured why thirty PRs cost 8–12 reviewer invocations each and produced five Tasks (#1178–#1182) plus the parked `friction resolve` helper (#1181). Four of the five landed on 1 October (#1180 procedures, #1178 not-code floor + fresh-verdict skip, #1182 parallel suite, #1179 per-reviewer freshness — approved, merging), and the operator made the CI `checks` job a required status on `main` (the #1008 operator step; #1011, the merge queue, is being built on it). This note measures what changed, what has not changed yet, and what to measure once the remaining two land.

## Data

Collected 1 October ~06:00 UTC from GitHub for every PR merged since #1100 (48 PRs): verdict comments posted by the local reviewers (one per reviewer per run), review rounds (verdicts clustered within 20 minutes), merge commits on the PR branch (merges of `main`), completed `checks` workflow runs and their wall-clock minutes, hours from PR open to merge. Collector: `.agent-workspace/stats/collect.py` (not committed).

| Period | PRs | Verdicts per PR (mean / median) | Rounds per PR | PRs with ≥2 rounds | Merges of main per PR | CI runs per PR | CI minutes per run (mean / median) | Hours open (median) |
|---|---|---|---|---|---|---|---|---|
| A — #1100–#1129, 29 Sep, before the collision wave | 18 | 8.4 / 8 | 1.2 | 4 | 1.4 | 2.4 | 6.3 / 6.2 | 0.3 |
| B — #1133–#1170, 30 Sep, the friction wave | 20 | 8.2 / 8 | 1.9 | 14 | 1.7 | 1.9 | 17.0 / 15.1 | 1.3 |
| C — #1171–#1191, 1 Oct, the fix wave itself | 10 | 11.6 / 10 | 2.5 | 7 | 2.0 | 3.8 | 24.6 / 26.6 | 1.9 |

Period C is the fixes being built under the worst case the first note described: six PRs in flight, five of them touching the same pm README stamp, so every landing sent the others through a merge of `main`, a CI run and a review round. It is the control group for the treadmill, not a measurement of the fixes.

Two individual PRs from the fix wave, opened after #1178 landed:

| PR | What it is | Required reviewers | Verdicts | Rounds | CI minutes |
|---|---|---|---|---|---|
| #1193 | PRJ-010, a record plus one README stamp | **2** (pm, docs) | 4 | 2 | 10, 11, 13 |
| #1192 | the freshness rule, code + records | 4 | 8 | 2 | 11, 14 |

CI on `main` (push runs of the `checks` workflow): 31 and 28 minutes for the two runs before #1191 landed; 13, 13, 14 and 8 minutes for the four after.

## What changed

- **CI time halved or better.** Period B/C runs took 15–30 minutes (the suite grew from ~9 370 to ~9 630 tests through the day, and six parallel builders plus CI shared the machines); after #1182 (`pytest -n auto`, two full suites per machine) a run is 8–14 minutes on CI and 11 minutes locally where it was 35. This is the one effect already visible in the aggregate.
- **A record or docs PR no longer draws the code-review panel.** #1193 required two reviewers, not four, because its `none` changeset no longer satisfies the `touches-code` floor (#1178). Period B's record-wording PRs all drew four.
- **A re-run names what it re-runs.** #1192's last round printed, per reviewer, the head it had reviewed and the files changed since, and skipped nobody only because the fix touched code — under #1178 a reviewer whose verdict is fresh is not re-invoked; under #1179 (merging) a verdict survives a clean merge of `main` and a floor-only approval survives changes outside its floors.
- **Follow-ups are triaged.** Today's reviewer passes produced fourteen Tasks; seven were dispatched (#1178, #1179, #1180, #1182, #1185, #1188, #1194 waits on acceptance) and seven were filed without a milestone and parked (#1181, #1183, #1190, #1195, #1196, #1177, #1175). Yesterday every filed Task was built in the same wave.
- **Fix rounds carry blocking findings only.** Every fix brief today listed the must-fix and red-flag items; advisories went into PR bodies or the parked Tasks above. Not measurable from GitHub; recorded as practice (#1180).

## Landed after the measurement (1 Oct, 06:00–10:30 UTC)

#1192 (#1179, per-reviewer verdict freshness), #1193 (PRJ-010 accepted), #1197 (#1008, the friction gate as a required status with its escape hatch documented), #1202 (#1194, the type-checking gate: tests on standard outright, the package behind a 1 891-finding ratchet) and #1199 (#1011, the merge verbs land through GitHub's merge queue; `checks` runs on the queue's prospective merge). The queue itself is switched on by the operator once #1200 (the release step's own merge copy) lands and the squash title/body defaults are set. From #1192 on, `review-pr` prints which verdicts it keeps and why it re-runs the others — e.g. on #1199's last round only the two code-floor reviewers re-ran after a code fix.

## First PRs reviewed under the fixes (measured 1 Oct ~13:00 UTC)

| PR | Verdicts | Rounds | Reviewers | Merges of main | CI runs | CI minutes (avg) | Hours open | Why more than one round |
|---|---|---|---|---|---|---|---|---|
| #1197 friction gate live | 4 | 1 | 4 | 0 | 1 | 13.5 | 0.3 | — |
| #1202 type-checking gate | 4 | 1 | 4 | 1 | 1 | 14.2 | 0.3 | — |
| #1193 PRJ-010 record | 6 | 3 | 2 | 0 | 4 | 11.7 | 4.1 | two revisions of the record after critic and methodology findings; waited for the operator's acceptance |
| #1192 verdict freshness | 12 | 3 | 4 | 1 | 3 | 12.9 | 4.0 | architect + critic findings (ordering defect, floor scoping), then a COR-054 violation CI caught |
| #1199 merge queue | 12 | 3 | 4 | 1 | 4 | 14.2 | 1.9 | architect + critic findings (enqueue treated as merge), then a code-reviewer block |

Against the 30 September wave (8.2 verdicts, 1.9 rounds, 1.7 merges of `main`, 17-minute CI runs, 1.3 hours open) and the fix wave (11.6, 2.5, 2.0, 25 minutes, 1.9 hours): a PR with no findings now lands in one round, one CI run and about twenty minutes; no round in this table was caused by a merge of `main` or a stamp conflict — every extra round answers a reviewer's blocking finding; CI is 12–14 minutes; merges of `main` per PR fell from 2.0 to 0.6. Five PRs is a small sample, and two of them are the fixes themselves.

## The freshness rule observed (1 Oct afternoon)

#1208 took two merges of `main` with hand-resolved README stamps while it waited. After each, `show-pr` read `code-reviewer: APPROVED, security-reviewer: APPROVED, pm-reviewer: APPROVED (stale), docs-reviewer: APPROVED (stale)`, and the next `review-pr` printed `fresh verdict APPROVED — not re-run` for the two code-floor reviewers and re-ran only the other two. Under the 30 September rule each of those merges would have cost four reviewer runs. The stamp conflicts themselves were still resolved by the workspace script — eleven times on 1 October — which is what `pkit friction resolve` (#1181) and the merge queue (#1011, built; not yet switched on) remove.

Parallel wave, 1 October afternoon: eight Tasks dispatched together across separate module families; first PR open after 10 minutes, five merged within about three hours (#1205, #1216, #1209, #1208, and #1218 pending), none blocked by another except through README stamps.

## What has not changed yet

- **Verdicts and rounds per PR did not fall in the aggregate** (8 → 8 → 12). The two mechanisms that cut them — the fresh-verdict skip and per-reviewer freshness — landed at 03:00 and are merging now; every PR in the table was reviewed before them or while colliding with them.
- **The merge-of-main treadmill is intact until #1011.** Eight of the ten fix-wave PRs merged `main` at least once, two of them five times, each merge costing a CI run and (before #1179) a review round. The merge queue runs the gate on the queued merge commit and removes the manual re-merge; its operator precondition (the required status) is now set.
- **Revalidation stamps still conflict on every concurrent landing** — the one cost the first note named that no Task fixed (#1181 is parked; the merge driver was rejected under COR-050 point 3). Today's conflicts were resolved by a local script that takes `main`'s block and re-answers; that is a workspace tool, not project tooling (COR-007 says extract it when it recurs — it recurred nine times today).

## Further inefficiencies seen on 1 October, and what is being done

Watching the day's fifteen landings, the remaining cost is no longer review volume; it is hand-work around the gate and waiting.

| Cost seen | Evidence | Remedy | State |
|---|---|---|---|
| The CI → review → merge sequence is strung together by hand | the same polling chain typed 20+ times; three variants failed (review started before CI registered a run; a merge attempted on an unpushed head; an output filter hid a refusal) | one verb, `pkit pm land <issue>` | #1203, High; starts after #1200 (same files) |
| Stamp conflicts resolved with a throwaway script | nine merges of `main` needed the "take main's block, re-answer" script; one wrong answer (`updated` on an unchanged page) failed CI | `pkit friction resolve` — the mechanical half as project tooling, never writing a revalidation itself | #1181, building |
| CI's tail | last 8% of tests take 8.5 of 11.5 minutes (adopter-repository fixtures, 10–15 s a test) | build the fixture once per module/session | #1204, building |
| Design defects found after the build | #1179 (ordering defect, floor scoping) and #1011 (an enqueue treated as a merge) each cost two fix rounds because critic and architect first saw the design as finished code | for a Task that changes a gate's semantics, run `critic` on a half-page design note before dispatching the builder — a change to the reviewer-invocation threshold (DEC-029 / CLAUDE.md), the operator's call | proposed here, not filed |
| Builders lost to the usage limit | three waves died mid-run (30 Sep 22:20, 1 Oct 03:20, 1 Oct 13:20); recovery cost 20–40 minutes each | briefs now say "commit and push early"; smaller Tasks; nothing in the methodology can raise the limit | practice |
| `done-work` cannot finish a PR the queue merges later | exit 4 leaves the issue closed by GitHub but labelled Review until a second run | completion from the workflow on merge | #1201, after #1200 |
| The release step has its own merge copy | would close a queued release PR | one merge mechanic in the backbone | #1200, building — the last blocker before the queue is switched on |
| Noise that hides signal | `done-work` warns `git branch -D … used by worktree` on every merge from a worktree; `promote-issue` warns `backlog → backlog` on every promotion | fix the causes | #1183 building; the branch-delete warning not yet filed |

Parallelism from here: Tasks are dispatched together when their implementation notes name different files (the same-module rule, #1180). On 1 October afternoon eight builders run at once across friction, backbone config, pm lifecycle, pm milestone, agent bodies, tests, records and the release step; the four Tasks that touch the gate's files (#1195, #1196, #1201, #1203) wait for #1200 and then run one at a time.

## The remaining treadmill has one cause: three tree-wide pages

By the evening of 1 October the review cost of a merge of `main` was gone (fresh verdicts are kept; only the reviewers a change reaches re-run) and the conflict itself was one command (`pkit friction resolve`, #1181, used on its first afternoon). What still forced a merge per landing was that three pages — the CLI reference, the pm README and the kit README — are each anchored to a whole tree, so almost every pull request answers them and collides on their revalidation block. That is a documentation-structure cost, taken up in `2026-10-01-brownfield-onboarding` (split tree-wide pages by the unit their reader looks up), not a process one.

## What to measure next

Once #1179 and #1011 have been in place for a week of normal (non-collision) work:

1. Verdicts per PR and rounds per PR for PRs with a merge of `main` — the expected value is one round, zero re-rounds for a clean merge.
2. Reviewer re-runs after a docs-only or stamp-only fix — expected two (pm, docs), not four.
3. Merges of `main` per PR — expected zero once the queue merges in sequence.
4. Hours from PR open to merge, which the treadmill dominated today.
5. Whether stamp conflicts still occur with the queue (they should not: the queue serialises landings, and a PR's revalidation answer is written against the base the queue merges onto).

## Status

Active. Re-measure after a week; if the expected values hold, fold the result into the done note's successor and retire this one.
