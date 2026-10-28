# Design: pools in the topology of seats (for review)

Decided in conversation with the maintainer on 28 October, point by point; not yet written into any record or code. It replaces the per-seat milestone scope that PR #2257 built (`feat/2256-a-seats-scope-may-name`), which an earlier critic review found wanting (a project-wide gate held per seat; the title-number trap; closed milestones emptying a pool silently). Background research: `talk-notes/research-work-routing.md` on branch `docs/talk-notes` (also at `/Users/kalfas/Documents/Projects/bee/git-public/project-kit-2/.claude/worktrees/talk-notes/talk-notes/research-work-routing.md`).

## The need

project-kit runs seats (project-management DEC-059): a planner and workers, each agent in its own clone. Workers take the next ready Task from one shared pool (every Backlog Task with no owner). The old, untriaged backlog sits in Backlog, so a worker would take June's work. The maintainer wants (1) workers to take only what was put into their pool, (2) several planners at once, each on its own line of work, so he need not switch topics inside one session, (3) no change to the committed topology when a line of work finishes.

## The design

1. **Pools with neutral, stable names** in the topology (`project/topology.yaml`, committed, read from the default branch): `pools: {alpha: {state_issue: N}, bravo: {state_issue: M}}`. A name never says what the pool is about, so it never changes when its work does (like seat names).
2. **Each pool's current topic and milestones live in the pool's state issue** (DEC-058), not in the topology. *Topic*: one line saying what the pool's work is. *Milestones*: the pool's gate, named by their GitHub milestone number (not the number a milestone's title carries under DEC-016).
3. **Who sets them:** `pkit pm set-pool <name> --topic "…" --milestones <n>…`, run by the organizer seat's clone on the person's word in the conversation, or by a person in any clone. Every other seat is refused, so no worker or ordinary planner widens its own pool. The pool's state issue logs each change with who authorised it and why. It takes effect at once, with no pull request, like putting a Task into a milestone.
4. **Seats name their pools.** A planner names one pool (`pool: alpha`): what it files goes into that pool's milestone (the planner picks one where the pool has several). A worker names one or more (`pools: [alpha, bravo]`) and ranks across them by priority, then number. Seats keep their own state issues (who holds the seat), unchanged.
5. **A seat's scope narrows inside its pools, never widens** (workstreams, types), as today.
6. **A Task reaches a worker** when it is ready as today (Backlog, dependencies closed, no other owner), its own milestone (the Task's, not an ancestor's) is one of its pools' milestones, and it falls in the seat's scope.
7. **Defaults.** No pools declared: today's behaviour (Backlog is the gate; one shared pool). Pools declared: a worker that names no pool takes nothing (fails closed).
8. **Reporting.** `take-seat`, `seats` and `next-task` show each pool's topic and each milestone's title and whether it is open. Warnings: a seat naming an unknown pool; a seat whose scope can match nothing; a pool no seat builds for (no worker and no lead); a pool whose milestones are all closed or missing; a planner naming no pool.
9. **Roles stay fixed.** A planner never builds. A seat that plans and builds is a lead (DEC-059 point 2); the lead's work loop is not built yet. Several planners are allowed (only the organizer is limited to one).
10. `settings.release_mode: tolerant` stays as it is.

## Records it touches (as we understand them)

DEC-059 (points 2, 7 and the rationale: "one shared pool" becomes a pool per line of work; who sets a pool), DEC-058 (a new kind of state: a pool's topic and gate), DEC-025 open question 7 (does the active milestone gate the frontier; this answers it, per pool), DEC-006 (a milestone as a gate on top of Backlog, the person's scheduling act), DEC-016 (which milestone number), DEC-004 (a Task's own milestone vs its EPIC's).
