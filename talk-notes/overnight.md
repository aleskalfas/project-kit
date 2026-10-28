# 28–29 October: state of play

Updated through the night. Each item says what it needs.

## For you in the morning

1. **Start the workers. Pools are live.** In each worker clone, **first** `git pull` (code older than the pools guard does not know `pools` and would take from the whole Backlog), then "run the work loop". worker-1 is still held by the clone at `agent-4005752ec23ae290:~/work`; worker-2 is free, so the second clone takes it with `uv run pkit pm take-seat worker-2 --agent project-manager` after its pull. They take only Tasks in milestone #8 (Milestone 6: Release 2.0.0), which now carries `Pool: alpha`. `seats` shows: `alpha: #8 Milestone 6: Release 2.0.0`, and warns of 6 older Backlog Tasks in no pool, which no worker takes (as intended).
2. **Decided on your behalf overnight**, within what we agreed (say if any is wrong; each is easy to change):
   - A pool binds what a worker takes of its own choosing (`next-task`). You directing a worker to a particular Task stays your act and only warns, so DEC-045 point 5 is unchanged.
   - The guard is wide: code that meets any key it does not know, at any depth, or a value it cannot read, takes nothing.
   - Rollforward stays within a pool (and an unpooled milestone rolls only into unpooled ones); a target in another pool is named in the close's consent prompt.
   - A Task leaving a pool asks nothing (it narrows); bringing one in, or moving it between pools, asks your consent, logged on the Task.

## Pools ([#2256](https://github.com/aleskalfas/project-kit/issues/2256), PR [#2257](https://github.com/aleskalfas/project-kit/pull/2257))

- Records: DEC-061 "Pools of workers" (new, partially supersedes DEC-059), refinements to DEC-059, DEC-016, DEC-006, DEC-025. Two fix rounds closed the critic's, the architect's and the methodology reviewer's findings (no red flag, no blocker, no escalation left). **Accepted on your word** ("finish the pools on my behalf … we agreed on all important"), quoted in the acceptance commit c1c4de924. The architect writes ADR-072 (the pool lookup) and rewords ADR-041 in the same PR.
- **Landed** as 18614be: the guard, the `Pool:` line, consent, topology, `next-task`, rollforward, reports, docs. All five reviewers approved after one docs fix round (UC-063 brought up to pools; a wrong glossary link). The fixers found nothing to propose.
- **Our setup landed** as ece5f8a ([#2264](https://github.com/aleskalfas/project-kit/issues/2264), PR [#2267](https://github.com/aleskalfas/project-kit/pull/2267)): `pools: [alpha]`, both workers serving alpha. Then milestone #8 marked `Pool: alpha` through `set-pool`, on your word, logged in its description.
- Two reviewer advisories filed into milestone #8 for the workers: [#2265](https://github.com/aleskalfas/project-kit/issues/2265) a milestone close that cannot read the topology must not roll Tasks into another pool unseen; [#2266](https://github.com/aleskalfas/project-kit/issues/2266) `start-work`'s help names its pool behaviour.
- Choices the builder made where the records were silent (say if any is wrong): a Task milestone write that cannot read the topology or the milestones asks your consent, as if the milestone were pooled; only `create-issue` hands its `--yes` to the milestone hook, so a scripted move into a pool is refused off a terminal; a writer refuses a pool the topology does not declare; every topology problem now stops taking work, an empty scope included; `back-fill`'s bulk milestone write is left as is.
- Decided on your behalf: the rule-set reviewer's question whether "…, says what it did not understand, and the use case ends" needs a list. Kept as written: it is the form every use case uses.
- The design as decided: [design-pools.md](design-pools.md). The research behind it: [research-work-routing.md](research-work-routing.md).

## Milestone 6: Release 2.0.0 (the workers' pool)

#2255 reviewers start from the project root · #2248 flaky timing test · #2258 the rule on when a record starts (after #2261) · #2259 a clean context per Task · #2260 rules keep their numbers · #2261 the rules trimmed (after #2260) · #2262 a size budget for the rules (after #2261) · #2263 a scratchpad note in one state · #2265 a close over an unreadable topology stays in its pool · #2266 `start-work`'s help on pools.

## Observing the workers (28 October)

- Both took a seat and one Task each from milestone #8 (worker-1 #2260, worker-2 #2259); no overlap.
- worker-1 listed the Tasks on request, recommended #2260, and took it on "go", skipping `next-task`. Inside its pool, so the code's check had nothing to warn of. Open question: should a seated worker choose work at all, or only take what `next-task` hands it? Watching before deciding.

## The talk

- [Building blocks](building-blocks.md): block 1 decisions, block 2 rules and block 3 scratchpad notes have your notes; block 4 skills is drafted, waiting for your reaction.
- Block 2's slicing of rules is deferred: [scratchpad note](https://github.com/aleskalfas/project-kit/blob/docs/scratchpad-rules-sliced/.pkit/scratchpad/active/2026-10-28-rules-sliced-by-files.md).

## Landed on 27–28 October

#2194 (COR-065/066/067), #2197, #2219, #2227, #2230 (the delegate), #2231 (the landing guard), #2233 (releases by hand), #2235, #2237 (`friction prune`, `friction resolve` retired), #2249 (271 old answer files pruned), #2254 (seats: planner, worker-1, worker-2).

## Parked

- #2224 release-candidate records: waits for your acceptance (and the `CLAUDE.md` sentence in its "To accept"); then the rc1 build. Its new ADR-072 collides with the pools ADR-072 in #2257, which lands first: #2224 renumbers its ADR when taken up (the decisions check-diff flags it).
- #2240 guardrails and #2242 watched fixers: a fix round each.
- The cleanup triage #2243–#2247 waits for the project's structure; the board (#2247) after it.
