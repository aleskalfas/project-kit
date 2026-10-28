# Design: pools of workers, a milestone joining a pool by a line in its description (for review)

Decided in conversation with the maintainer on 28 October, point by point, after a critic review of an earlier version (pools whose topic and gate lived in state issues, set by the organizer agent; rejected: the authorisation was not real, a new kind of state for a person's weekly decision, and more than the needs). Not yet written into any record or code. It replaces the per-seat milestone scope that PR #2257 built (`feat/2256-a-seats-scope-may-name`). Background: `talk-notes/research-work-routing.md` on branch `docs/talk-notes` (local copy `/Users/kalfas/Documents/Projects/bee/git-public/project-kit-2/.claude/worktrees/talk-notes/talk-notes/research-work-routing.md`).

## The needs

project-kit runs seats (project-management DEC-059): planners and workers, each agent in its own clone. Workers take the next ready Task from one shared pool (every Backlog Task with no owner); the old, untriaged backlog sits in Backlog, so a worker would take June's work. The maintainer needs:

1. workers to take only what a person put into their pool;
2. several planners at once, each on its own line of work, so he need not switch topics inside one session;
3. no change to the committed topology when a line of work finishes or a new one starts;
4. control of capacity: more clones on what matters most, one on housekeeping, and so on (the reason workers are dedicated to pools rather than shared by all lines).

## The design

1. **Pools are named in the topology, with neutral names** (`pools: [alpha, bravo]`), and **a worker names the pools it serves** (`pools: [alpha]`; one or more). Moving capacity between lines is an edit of a worker's `pools`, through a pull request, like any topology change.
2. **A milestone joins a pool through a line in its GitHub description,** `Pool: alpha`, beside the `Close trigger:` line DEC-016 already reads there. GitHub milestones carry no labels. A milestone is in at most one pool, and a Task in at most one milestone, so a Task is in at most one pool. `create-milestone` gains `--pool`, and editing a milestone's pool goes through the same consent as other held acts (a person at a terminal, or `--yes` on the person's word, with the reason logged); the organizer agent may run it only that way.
3. **A pool's topic is its open milestones** (their titles and descriptions). Finishing a topic is closing its milestone; a new topic is a new milestone marked with the pool. The topology does not change.
4. **How `next-task` finds a Task for a worker:** read the topology from the default branch (the seat's pools); read the repository's open milestones once and map each `Pool:` line to its pool; read the open issues once (as today); keep the Tasks that are ready as today (Backlog, dependencies closed, no other owner) **and whose own milestone** (not an ancestor's) is one of the seat's pools' milestones **and** that fall in the seat's scope (workstreams, types), which narrows inside the pools and never widens; rank as today (own Tasks first, then priority, then lowest number) and start the first.
5. **Planners.** Several planner seats are allowed (only the organizer is limited to one). A planner files into a milestone the person approves in the plan's gate (the plan's Milestone column), so its Tasks enter that milestone's pool. A seat that plans and builds is a lead; the lead's loop is not built yet.
6. **Defaults and failures.** No pools declared: today's behaviour (Backlog is the gate; one shared pool). Pools declared: a worker that names no pool takes nothing; a milestone listing that cannot be read takes nothing (exit 3), never falling back to the whole Backlog. `next-task` says "pool alpha has no open milestone" rather than a bare "nothing ready".
7. **Checks and reports.** `check-topology` refuses a seat that names an undeclared pool. `seats` and `take-seat` show each pool's open milestones (number and title) and warn of a pool no seat builds for, a pool with no open milestone, a worker naming no pool. `close-milestone` asks the person where its open Tasks roll forward when the next milestone is in another pool or none.
8. **First, before pools ship:** code that meets a topology key or `schema_version` it does not know refuses to take work, so a clone running older code does not take the whole Backlog (version skew between the topology on the default branch and each clone's code).
9. `settings.release_mode: tolerant` stays.

## Related, separate

A worker builds each Task in a clean context (filed as its own Task in Milestone 6): the seat's session takes the Task and starts a fresh helper to build it.

## Records it touches (as we understand them)

DEC-059: overturned in part, not refined: "one pool every seat shares" (point 7, title, "Why one shared pool") and the rejected alternative of a scope that reserves work for its seat, now accepted as pools; refined: points 1, 2, 4 (taking a seat by role with several planners), 7. DEC-016: the `Pool:` line, and rollforward across pools. DEC-006: a Task scheduled with an audited reason and no milestone reaches no worker where pools are declared. DEC-025 open question 7: answered, per pool. DEC-045 points 4 and 5: the expected owner. DEC-004: a Task's own milestone.
