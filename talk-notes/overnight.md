# Night of 27–28 October: what waits for you, and what was done

Get well. Nothing that needs you was done without you; each item below says what it needs. This file is updated through the night.

## Waits for you, in the order I'd take them

1. ~~Authorise~~ **Landed** [#2194](https://github.com/aleskalfas/project-kit/pull/2194)** (COR-065, COR-066, COR-067, accepted by you this morning). **Ready:** all three reviewers approved at the latest head, their person findings settled (kept). The landing lists the top lines it adds to COR-006 and COR-025 for you to judge.
2. ~~Authorise~~ **Landed** [#2169](https://github.com/aleskalfas/project-kit/pull/2169)** (records hygiene: 20 project-management records refined in place, no decision changed). **Ready:** caught up with main, and ADR-041 restated by the architect as the code now stands (the seat commands call the ownership seam); reviewers approve, person findings settled (kept). Whichever of #2169 and #2194 lands second needs one small catch-up. The architect found three places where ADR-041 and the code part, which need your decision: [#2214](https://github.com/aleskalfas/project-kit/issues/2214).
3. **Accepted by you; landing** DEC-004 in [#2197](https://github.com/aleskalfas/project-kit/pull/2197), reworked as you asked: the skeleton is built first, and you accept its convention entries once, with the skeleton's change, before the slices. **Ready:** critic and methodology-reviewer confirmed, the three PR reviewers approve. Note: the rework put a new rule into project-management DEC-060 (whoever lands a skeleton's change merges only after its entries are accepted), a decision of its own to judge with DEC-004.
4. **Release candidates ([#2211](https://github.com/aleskalfas/project-kit/issues/2211)):** the design is ready ([the note](https://github.com/aleskalfas/project-kit/blob/docs/2211-release-candidates/.pkit/scratchpad/active/2026-10-27-release-candidates.md)), following your decision that a candidate consumes no changesets. It needs eight decisions from you, listed on #2211 with a recommendation each; in short: a candidate's versions live only in its tag (never on main); components get `rcN` versions too; floors wait for the final; a candidate runs its release's migrations, and testers following every candidate re-run them; from 1.x you install a candidate with one explicit command, and nothing moves a project to a candidate unasked; a dispatch-only workflow publishes it as a GitHub pre-release; the final is cut from the last candidate's commit. To keep rc1 possible this week, the records are being drafted tonight on those recommendations, **proposed**, for you to accept or adjust. Nothing is built before you do.
4b. **Authorise [#2219](https://github.com/aleskalfas/project-kit/pull/2219)** (closes #2217 and #2221): rolling back an upgrade means reverting its commit, since 2.0.0's answer move edits files outside `.pkit/`. The docs first contradicted ADR-049 point 3 and ADR-065 ("check out `.pkit/`"), so under COR-065 the architect refined both records in this PR, and the commands' messages now name `git revert`. **Ready:** five reviewers approve, person findings settled (kept). It refines two accepted records, so it waits for you. Worth having in rc1.
5. **[#1990](https://github.com/aleskalfas/project-kit/issues/1990)** (guardrails against wrapped commands and git configuration) and **[#2026](https://github.com/aleskalfas/project-kit/issues/2026)** (the harness's scratch directory): the architect's recommendation is recorded on each, for your choice. #1990: refine ADR-025 so a deny reads the command a wrapper runs (`find -exec`, `xargs`, `sh -c`, `env`…), and git configuration a command sets or writes (`git -c`, `git config alias.*`) counts; grants stay as written. #2026: option B, the adapter tells every agent the workspace replaces the harness's scratch directory, no record change.
6. Smaller: the two deny rules of your 17 October decision ([#1678](https://github.com/aleskalfas/project-kit/issues/1678)'s scope); the two README answers left from #2205; [#2175](https://github.com/aleskalfas/project-kit/pull/2175) (close or keep).

## New for you since your last message

- **The fixers cannot run yet ([#2225](https://github.com/aleskalfas/project-kit/issues/2225)).** After #2194 landed, `fix-drift` started the living-docs fixer on four stale pages, and every run was refused: the Claude Code adapter's tested range for confined runs is empty until its author runs the probe (`python3 .pkit/adapters/claude-code/probe-confined-run.py --start-claude --keep`). It starts one real Claude Code run that signs in and spends, so it is yours to run, by design. Until then the grant does nothing.
- **Release-candidate records: [#2224](https://github.com/aleskalfas/project-kit/pull/2224)** (closes #2223, under #2211), proposed: PRJ-002, PRJ-004, a new ADR-072, and refinements of ADR-049, ADR-063, ADR-064, ADR-065. Reviewed by the critic and the methodology-reviewer. Note: it and #2219 both refine ADR-049 point 3; whichever lands second reconciles the wording.

## Done today with you

- Accepted COR-065, COR-066 and COR-067 (#2194).
- Both fixers granted (living-docs for pages, analysis-resolver for the analysis), [#2210](https://github.com/aleskalfas/project-kit/pull/2210).
- Scratchpad on what an answer is, kept active to continue: [the note](https://github.com/aleskalfas/project-kit/blob/docs/scratchpad-reconciliation/.pkit/scratchpad/active/2026-10-27-answers-as-reconciliation.md).

## In progress tonight

- [#2212](https://github.com/aleskalfas/project-kit/issues/2212) and [#2213](https://github.com/aleskalfas/project-kit/issues/2213): shipped pages anchor what they mention (the part of #2131 that needs no decision; passing mentions listed for you to mark).

- [#2217](https://github.com/aleskalfas/project-kit/issues/2217): the 2.0.0 answer move edits files outside `.pkit/`, so the docs and notes say how to roll back an upgrade (revert its commit).

## Landed tonight

- [#2210](https://github.com/aleskalfas/project-kit/pull/2210): both fixers granted. After each merge they now propose fixes for stale pages and analysis artefacts; tonight the only debt is 7 deferrals waiting on their follow-ups, so nothing to propose yet.
- [#2215](https://github.com/aleskalfas/project-kit/pull/2215) (#2213): seven shipped pages anchor what they mention, 69 anchors, prose unchanged; 68 passing mentions listed for you to mark.
- [#2216](https://github.com/aleskalfas/project-kit/pull/2216) (#2212): the adapter, permissions and process pages anchor what they mention (prose unchanged); passing mentions listed for you.
- [#2220](https://github.com/aleskalfas/project-kit/pull/2220) (#2218): the review run's timing test no longer fails on a loaded CI runner.

## Found tonight, for you

- **Anchor cycles** (on [#2131](https://github.com/aleskalfas/project-kit/issues/2131)): pages that rest on each other cannot anchor each other, since a cycle fails validation. 43 grounding mentions stay uncovered until you choose a way out (one direction gives way, a mark, or COR-050 allows section-level cycles).


## The talk

- [Building blocks](building-blocks.md): block 1 (decisions) and block 2 (rules, drafted for you to react to).
- [Working notes](working-notes.md), [the trial install](trial-run.md), [the demo run plan](demo-run-plan.md).

## Release

- Plan: test 2.0.0 as a release candidate first; the final follows later. #2211 designs candidates as a supported channel.
- The upgrade rehearsal from 1.149.0 found 2.0.0 safe; its two fixes landed.
