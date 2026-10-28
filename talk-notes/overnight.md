# 28–29 October: state of play

Updated through the night. Each item says what it needs.

## For you in the morning

1. **Start the workers**, once pools have landed (see below): `git pull` in both worker clones, then "run the work loop" in each. They take only Tasks in milestone #8 (Milestone 6: Release 2.0.0), which carries `Pool: alpha`.
2. **Decided on your behalf overnight**, within what we agreed (say if any is wrong; each is easy to change):
   - A pool binds what a worker takes of its own choosing (`next-task`). You directing a worker to a particular Task stays your act and only warns, so DEC-045 point 5 is unchanged.
   - The guard is wide: code that meets any key it does not know, at any depth, or a value it cannot read, takes nothing.
   - Rollforward stays within a pool (and an unpooled milestone rolls only into unpooled ones); a target in another pool is named in the close's consent prompt.
   - A Task leaving a pool asks nothing (it narrows); bringing one in, or moving it between pools, asks your consent, logged on the Task.

## Pools ([#2256](https://github.com/aleskalfas/project-kit/issues/2256), PR [#2257](https://github.com/aleskalfas/project-kit/pull/2257))

- Records: DEC-061 "Pools of workers" (new, partially supersedes DEC-059), refinements to DEC-059, DEC-016, DEC-006, DEC-025. Critic: faithful to the design; a fix round closes its findings. Then the architect and the methodology reviewer, then acceptance on your word ("finish the pools on my behalf … we agreed on all important"), quoted in the PR.
- Then phase 2, the code; the PR's reviewers; landing.
- Then a small PR: `pools: [alpha]` in our seats file, both workers serving alpha, and milestone #8 marked `Pool: alpha`.
- The design as decided: [design-pools.md](design-pools.md). The research behind it: [research-work-routing.md](research-work-routing.md).

## Milestone 6: Release 2.0.0 (the workers' pool)

#2255 reviewers start from the project root · #2248 flaky timing test · #2258 the rule on when a record starts (after #2261) · #2259 a clean context per Task · #2260 rules keep their numbers · #2261 the rules trimmed (after #2260) · #2262 a size budget for the rules (after #2261) · #2263 a scratchpad note in one state.

## The talk

- [Building blocks](building-blocks.md): block 1 decisions, block 2 rules and block 3 scratchpad notes have your notes; block 4 skills is drafted, waiting for your reaction.
- Block 2's slicing of rules is deferred: [scratchpad note](https://github.com/aleskalfas/project-kit/blob/docs/scratchpad-rules-sliced/.pkit/scratchpad/active/2026-10-28-rules-sliced-by-files.md).

## Landed on 27–28 October

#2194 (COR-065/066/067), #2197, #2219, #2227, #2230 (the delegate), #2231 (the landing guard), #2233 (releases by hand), #2235, #2237 (`friction prune`, `friction resolve` retired), #2249 (271 old answer files pruned), #2254 (seats: planner, worker-1, worker-2).

## Parked

- #2224 release-candidate records: waits for your acceptance (and the `CLAUDE.md` sentence in its "To accept"); then the rc1 build.
- #2240 guardrails and #2242 watched fixers: a fix round each.
- The cleanup triage #2243–#2247 waits for the project's structure; the board (#2247) after it.
