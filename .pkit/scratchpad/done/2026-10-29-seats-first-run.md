---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-29
retired: 2026-10-29
produced:
  - https://github.com/aleskalfas/project-kit/pull/2254
---

# Plan: the first end-to-end run of seats (issue #2144), v2

Written on 27 October in a branch folder (`talk-notes/`) as the plan for the first end-to-end run of seats (#2144), which led to project-kit's own seats (#2254).

Goal: one planner and two workers, each an agent session in its own clone of `aleskalfas/pkit-seats-demo`, drain a small backlog through project-kit's seats, shared pool and merge gate. Two runs: a **rehearsal** that tests the chain (expected to break; every break filed), then a **recorded run** from a release, the source of the runbook page and the first figures.

No session of project-kit changes the demo repository: the person runs each step there, or starts agent sessions rooted in its clones. Revised after the critic's review of v1 (26 October).

## 0. Preconditions

- `aleskalfas/pkit-seats-demo` exists (private, README, `main`), created by the maintainer on 26 October.
- **Rehearsal:** project-kit installed from a pinned commit of main holding #2180, #2181, #2182 and #2183.
- **Recorded run:** a release that holds them (2.0.0). The recorded output must name a version that has the commands it shows.
- **One binary everywhere:** `uv tool install` at the named tag (or pinned commit for the rehearsal). Check `command -v pkit` and `pkit --version` from inside each agent session's shell, not only the terminal; the reviewers `pkit agents run` starts must run the same code.
- One GitHub account for all clones (seats told apart by clone keys, DEC-059), `gh auth status` green.
- One Claude account: set `PKIT_REVIEW_PARALLEL=2` and `review.agents.effort` to `medium`, and log every usage limit hit.
- Fixers: decline both grants for this run (no fixer proposals to judge).
- Permission profile: chosen and recorded before the run; every prompt in any terminal is logged as an intervention.

## 1. Set up (the person, about 30 to 45 minutes, a phase of its own)

Order matters:

1. Clone 1 (`planner`): `git clone`, install project-kit and the four capabilities (project-management, software-engineering, software-analysis, living-docs): docs roots first (`pkit config set docs.internal tech-docs`), installs at a terminal, decline the fixers, `pkit pm bootstrap` (labels), members.
2. A minimal pull-request workflow: a placeholder test, `pkit validate`, and `pkit pm check-topology`, so every pull request has a check and lands through `land-work`.
3. Push the install and the workflow to `main` (no issue, no CI yet: the person pushes directly, once).
4. On a branch: the topology, three seats: `planner` (planner, organizer), `worker-1`, `worker-2` (workers, no scope). `create-seats` on the change, `check-topology`, open the pull request, merge it with `gh pr merge` (the topology lands before any seat is taken). Clone 1 then `git fetch`.
5. Clones 2 and 3 (`worker-1`, `worker-2`): `git clone`, never a copy (a copy shares the clone key). `pkit sync`, `pkit status`, `gh auth status` in each.
6. **Clone 4, the landing clone: no seat.** The person lands every pull request there with `pkit pm land-work <N>` at a terminal; its y/N prompt is the authorisation. A clone with no seat is guarded by nothing (DEC-059 point 6), and landing never switches a working clone's branch.

## 2. The assignment: a markdown link checker in Python

- **Foundation (DEC-060), one Feature, one Task at a time:**
  1. Records of the shared choices, one per choice, accepted by the person: packaging and the command's interface (`mdlinks check <paths>`), the report format, exit codes.
  2. The walking skeleton: one file's relative links, text report, exit codes, tests and CI, end to end. Conventions (code and test layout) are settled by its merged code.
- **Slices, planned once the foundation's Feature closes (five Tasks):** anchors inside a file; anchors in other files (depends on the first); a JSON report; an ignore file; a `--version` and `--help` text that shares no files with the others (to show real parallel work). Each slice's `## Dependencies` names `#N`; after the second plan, run `pkit pm next-task --dry-run` in each worker clone and check what each would take.

## 3. The run, in three phases with their own time boxes

Launch each agent session with its seat named, for example `PKIT_AGENT=project-manager <agent-session> --agent project-manager` with an opening prompt "take the seat worker-1 and run the work loop" (the exact line per harness goes in the runbook). Set the variable per launch, never in the shell profile.

1. **Foundation (box: 90 minutes).** The planner takes `planner` and runs the first plan (EPIC with outline, foundation Feature); the person approves at the gate. Worker-1 takes `worker-1`, `next-task` takes the records Task; the person accepts each record (its status flip is a commit that triggers a new review), then lands it in clone 4. Then the skeleton Task, the same way. The person closes the foundation's Feature.
2. **Slices (box: 90 minutes; the figure for comparison).** The planner runs the second plan; the person approves. Start worker-1's and worker-2's `next-task` at the same moment once, and record what each took. Each worker loops; the person lands each pull request in clone 4 as it is ready. When `next-task` exits 5 (nothing ready), the loop stops: the person restarts it when a dependency lands, and each restart counts.
3. **Recovery (scripted, once).** When worker-2's draft pull request for a Task is pushed: stop worker-2's session; the person runs `pkit pm release-seat worker-2 --force --reason "<reason>"` at a terminal (the planner proposes, the person confirms); make the freed Task worker-1's top pick (raise its priority); worker-1's loop takes it over from its remote branch. Do not restart clone 3 with the same key while that Task is open.

Conflicts and fix rounds: when `land-work` stops on a conflict or a reviewer asks for changes, the person tells the owning worker; each such message counts.

When a pkit bug blocks: stop, file it under #2136, and either work around it (logged, kept out of the runbook's normal path) or end the phase.

## 4. What to record

- Each command and its output, scrubbed of machine and folder names.
- Per Task: taken, pull request ready, review done, authorised, merged; worker idle time.
- The person's interventions, defined: approvals at a gate, record acceptances, merges, closing the Feature, the forced release, loop restarts, conflict and fix-round messages, permission prompts.
- Tokens per session, and the reviewers' separately where the harness shows them.
- Controls fixed for a later comparison: the planner's brief word for word, the pkit version, the topology commit, reviewer effort, the permission profile.

## 5. Outputs

- A runbook page in project-kit's user documentation (a guide), with the commands and their output; the demo repository made public afterwards, or the page says its links are private.
- A short report: figures, interventions, rough edges filed.

## Product gaps found while planning (filed)

- #2182: a clone retaking its seat revives its pre-release claims (fix before the run).
- #2183: landing switches a working clone onto the default branch (fix before the run; the landing clone avoids it meanwhile).
- #2184: the work loop does not cover conflicts, fix rounds, or a released seat's pull requests in review.
