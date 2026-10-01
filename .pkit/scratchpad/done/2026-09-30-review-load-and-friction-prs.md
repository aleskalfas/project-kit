---
authors:
  - Aleš Kalfas
started: 2026-09-30
retired: 2026-10-01
produced:
  - https://github.com/aleskalfas/project-kit/issues/1178
  - https://github.com/aleskalfas/project-kit/issues/1179
  - https://github.com/aleskalfas/project-kit/issues/1180
  - https://github.com/aleskalfas/project-kit/issues/1181
  - https://github.com/aleskalfas/project-kit/issues/1182
---

# Review load and the friction PR cascade

## The question

Milestone 5 landed about thirty pull requests in two days, nine of them scoped `friction` and six more in the same family (software-analysis reading the friction engine, the default-branch seam, the doc-check gate). Every one went through four local reviewers, most through a `critic` and an `architect` pass, and about half through a second round. Were all of those PRs needed, and is the review load per PR proportionate — or does the process have a shape that multiplies work?

## What was measured

Landed on `main` since the start of this working segment (`d52d510..`): 30 PRs — 15 `feat`, 10 `fix`, 2 `refactor`, 2 `docs`, 1 `chore`. By scope: `friction` 9, `software-analysis` 5, `pm` 3, `release` 3, `agents` 2, one each for `connections`, `analysis`, `visibility`, `dispatcher`, `migrations`, `adr`, `process`, `adapters`.

Where the friction-family PRs came from (origin of the issue, not of the code):

| PR | Issue | Origin | Rounds | Extra passes |
|---|---|---|---|---|
| #1112 | #1012 enforce the documentation source | milestone plan | 1 (+1 merge re-round) | — |
| #1124 | #1113 merge-commit revalidation point | observed pain: every merge of main lost its stamps | 1 | — |
| #1129 | #887 software-analysis stamp and check | milestone plan | 2 | critic, architect |
| #1150 | #1147 `explain` exposes anchor matches | architect follow-up (from #1146) | 2 | critic |
| #1151 | #1136 measures honour `exclude` | architect follow-up (from #1130) | 1 | — |
| #1155 | #1144 nested query runs | architect follow-up (from #1142) | 2 | critic, architect |
| #1158 | #1130 held documents | architect recommendation (from #890/#888) | 2 | critic, methodology |
| #1163 | #1153 + #1152 exclusion changes | critic follow-ups (from #1150, #1151) | 2 | critic, methodology |
| #1164 | #1157 `propose` reads the explanation | consumer half of #1147 | 1 | — |
| #1165 | #1154 `schema_version` on documents | critic follow-up (from #1150) | 1 | — |
| #1166 | #1149 `unanchored-because` in the block | critic + architect follow-up (from #1146) | 2 | methodology |
| #1167 | #1128 one default branch | architect follow-up (from #1127, #1129) | 2 | critic, architect, methodology |
| #1170 | #1160 CRLF front matter | builder observation (from #1156) | 1 | — |

Two of thirteen came from the milestone plan. Ten came from reviewer passes on other PRs. One from a builder's side observation. Each reviewer pass produced two to five filed follow-ups; I built most of them in the same wave.

Per landed PR, roughly: one build (1–1.5 h of one agent), one four-reviewer round (15 min, four agents), a `critic`/`architect`/`methodology` set on anything touching a record or two capabilities (three agents, 5–10 min each), a fix round when they found something (another 1–1.5 h), a second four-reviewer round, and — with several PRs in flight in the same modules — one or two more rounds after merging `main`, because a verdict goes stale on any new commit, including a merge commit that only reconciles revalidation stamps. Around eight to twelve reviewer invocations per PR; two rate-limit exhaustions in two days.

## Were they needed?

Separating the friction-family PRs by what happens without them:

- **Needed for an enforcing gate to be honest** — #1113 (every branch that merged `main` lost its revalidation point; the gate would have failed on correct branches), #1136 (the measures counted what the record says they leave out), #1130 (two capabilities' measures misreported the same files), #1153 (a widened exclusion silently removed unanswered friction), #1160 (a CRLF clone reads every artefact as blockless — Windows adopters), #1128 (three readers judged "settled" against three different commits). Six.
- **Real defects, but not blocking the milestone's outcome** — #1144 (a killed parent leaves fillers running; rare), #1149 (needed by onboarding, not by the milestone), #1154 (hygiene: readers can notice a document change), #1147 + #1157 (one-computation refactor: architecture hygiene the records ask for). Five.
- **Needed and planned** — #1012, #887. Two.

So the friction-family count is not padding: none was invented. What inflated it is that the engine was new and its first real consumers (software-analysis, living-docs, pm's doc-check) exposed the edge cases at once, and the process turned every exposed edge into a Task built *now*. The five "real but deferrable" PRs cost roughly a day of the two.

The reviewers earned their passes on the substance: the `critic` found a cache that pinned a clipped filler's failure for the whole run (#1155), an unbounded held folder that could silence every page in the repository (#1158), a stacked-branch false collision that advised duplicating an artefact (#1156), a widening that erased unanswered debt (#1163), a guard refusing the case it existed for (#1159). None of those would have been caught by the four-reviewer round alone. The inefficiency is not *that* we review; it is how many times we review the same diff, and how follow-ups multiply without triage.

## Where the cost actually goes

1. **Follow-up inflation without a scope gate.** Every reviewer suggestion became a filed Task, and every filed Task that needed no operator decision was dispatched in the same wave. No step asked "does this block a criterion of the milestone?" before building. The architect and critic are asked to list follow-ups, and they do; nothing weighs them.
2. **Stale verdicts on content-free commits.** A merge of `main` that only reconciles revalidation stamps, or a stamp-only re-answer commit, invalidates four verdicts and costs a full round. With five PRs in the same module family in flight, each landing forced the others through this — two or three rounds per PR where one would do.
3. **Uniform reviewer set regardless of diff shape.** A docs-only or stamps-only PR ran the security reviewer; a record-wording PR ran the code reviewer; every record edit ran `critic` *and* `methodology-reviewer` when the second alone would have caught the wording problems. The pm capability has one `review.agents` list; nothing keys it on what the diff touches.
4. **Fix rounds fold advisories into must-fixes.** Critic reports separate "red flags" from "gaps" and "weak reasoning"; my briefs mostly carried all three into the fix round. About half the fix-round items were advisory.
5. **Parallelism inside one module family.** Running five friction PRs at once meant each landing invalidated the others: the cost is superlinear in the number of concurrent PRs on the same files. Parallelism across families (pm, release, software-analysis) cost nothing.
6. **Revalidation stamps conflict on every merge.** The `at` field changes on every answer, so two branches answering the same page always conflict in the front matter. The resolution is mechanical (take `main`'s, re-answer) but it costs a builder or a manual step per merge and produces a stamp-only commit — which then invalidates verdicts (point 2). This is a design cost of writing the stamp into the page.
7. **Every builder runs the full suite** (10–14 min alone) before and after each merge of `main`, and CI runs it again. Correctness insurance, but it is the largest single block of wall-clock time per PR — and it does not parallelise: six builders running the suite at once on one machine each took 43–46 minutes (measured 30 Sep, six worktrees, ~9 400 tests each), so six parallel builders spent ~4.5 machine-hours on tests to learn what CI would have told them in 15 minutes. Two of the six then died on the usage limit while waiting for the result.

## Candidate remedies

Cheap, configuration- or brief-level, no record change:

- **Triage follow-ups before dispatch.** A reviewer's follow-up is filed as a Task but dispatched only if it blocks a milestone criterion or is a correctness defect in a shipped gate; the rest wait for the milestone's close. The project-manager owns this step; it is one question per follow-up. Expected effect: the five deferrable friction PRs would not have been built this week.
- **Fix rounds carry red flags only.** Advisories and weak-reasoning notes go into the PR body's judgment calls or a follow-up note, not into the round. Expected effect: shorter fix rounds, fewer second rounds.
- **Serialize within a module family, parallelize across.** One friction PR in flight at a time; pm, release, software-analysis, docs in parallel beside it. Expected effect: one merge re-round per PR at most.
- **Reviewer set by diff shape** (a `review.agents` matrix keyed on changed paths in the pm project config): docs/stamps-only → `docs-reviewer` + `pm-reviewer`; tests-only → `code-reviewer` + `pm-reviewer`; records-only → `methodology-reviewer` + `pm-reviewer`, with `critic` for a *new* record and `architect` only when the diff spans two capabilities or an ADR; `security-reviewer` when the diff touches subprocess, network, permissions or the hook. This is a DEC refinement in the pm capability (DEC-028's approver paths name the reviewers) — a small record change plus a config schema key.

Structural, each a Task or a record:

- **A verdict survives a content-free commit.** `done-work`'s verdict gate compares the PR's *diff against `main`* at review time with the diff now, not the head SHA; a merge commit that changes nothing outside revalidation stamps, or a stamp-only commit, keeps the verdict. This is DEC-028 territory (when a verdict is stale) — one refinement, a moderate change to the gate.
- **Merge queue (#1011).** Removes the re-merge/re-round treadmill by construction: PRs are merged in sequence on top of each other with CI on the queued result. The largest lever and the one already filed.
- **Stamp merges resolve themselves.** A git merge driver (or a `pkit` merge helper the writers register) that resolves a `revalidated:` block conflict by taking the newer `at` with its answer, so a merge of `main` never needs a person or a builder for stamps. Alternatively, move revalidation stamps out of the page into a ledger file the engine owns — a larger change to COR-050 point 3's "the block travels with the artefact" posture, and the wrong trade if the block's locality is what makes revalidation reviewable. The merge driver is the cheap end.
- **Local test scope.** Builders run the tests of the modules they touched plus the friction check; the full suite runs once, in CI. Expected effect: 20–30 minutes saved per PR; the risk is a semantic conflict CI catches later (it happened twice this session — #1111 vs #140, #1142 vs #890 — both caught by CI, both cheap).

## What is already known

- COR-024 sets the reviewer stack and its ordering; the default is to call them, and skipping is a stated choice. The remedies above keep that: they change *which* reviewers run on *which* diff, not whether a substantive proposal gets opposition.
- DEC-028 (agent-as-approver paths) defines the verdict the merge gate consumes and when it is stale.
- DEC-029 sets the project-manager's dispatch discipline for `critic`/`architect` on multi-issue arcs; it says nothing about follow-up triage.
- #1011 (merge queue) is filed and designed; #1113 fixed the revalidation point but not the stamp conflicts themselves.

## Open questions

- Is a reviewer matrix keyed on paths honest, or does it let a "docs-only" change that alters behaviour (a schema description, a rule set) slip past the code reviewer? The rule-set files are documents *and* behaviour.
- Where does the follow-up triage live — the project-manager's `batch-plan`/`create-issue` flow (a `--after <milestone>` or a `scope:` label), or the reviewer briefs themselves (ask for "blocking before merge" vs "later" as two lists)?
- Does a verdict that survives a merge commit need the four reviewers to see the merged result at all? CI does; the reviewers reviewed the diff, and the diff is unchanged — that is the argument for carry-over.
- The stamp ledger alternative: would moving `revalidated` out of the page break the property that a page's history shows its own revalidations (COR-050 point 3's reviewability)?

## Status

Active. Measured on Milestone 5's second day; remedies not yet decided. The cheap ones (triage, red-flags-only fix rounds, serialize-per-family) need no record and the project-manager can adopt them now; the reviewer matrix and verdict carry-over each need a DEC-028 refinement; #1011 is the structural fix.
