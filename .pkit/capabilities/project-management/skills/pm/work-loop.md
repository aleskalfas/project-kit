# pm work-loop — take your seat, and run its role's loop

Sub-procedure of the pm composite skill (`pm.md` in this folder). It follows [project-management:DEC-059-topology-of-seats] points 4, 7 and 8, and the seat's direction in [project-management:DEC-029-project-manager-agent-shape]. A project that runs several agents at once declares a topology of seats, and each clone holds at most one seat. The seat's role sets what its agent does: a planner slices the work and files it, and a worker builds it. The commands are the [capability README](../../README.md)'s, under "Topologies of seats" and "Taking the next ready Task".

## When to use this operation

- **At the start of each session,** before any other operation. Step 1 finds the seat this clone holds, and takes a seat where the session was started for one.
- **While you hold a seat,** for as long as the session runs the seat's role. Each round of a loop ends where the next begins.

A session that holds no seat leaves this procedure after step 1. It infers its direction from the request, and the other sub-procedures serve it as before.

## 1. Take your seat

1. **List the seats:** `pkit pm seats`. It reads the topology from the default branch, names the commit it read, and marks the seat this clone holds with `← this clone`. A clone that has not fetched the default branch reads the commit it last fetched (DEC-059 point 1).
   - **The default branch declares no topology:** you hold no seat. Leave this procedure.
   - **Exit 3:** a state issue, the listing of open issues, a Task's comments or the open pull requests could not be read. The seats it listed above the error still stand: go on with them.
   - **Exit 1 or 2:** the default branch cannot be resolved, membership was refused, or the capability is not ready. Say what it printed, and take no seat (DEC-059 point 1). Where the session was started for a seat, stop there.
2. **Decide whether to take a seat.** Take one only where the session was started for one: this clone holds a seat, whoever started the session named a seat or a role, or the session's `PKIT_AGENT` names your agent definition. Otherwise take none. Say which seats are free, offer one where a person directs the session, and leave this procedure.
3. **Take the seat:** `pkit pm take-seat [<name>] [--role <role>] --agent <definition>`. The definition is the name of the agent definition you follow, such as `project-manager`. Leave `--agent` out where `PKIT_AGENT` names it already.
   - **This clone holds a seat:** pass no name and no role. The command takes that seat up, as each new session in the clone does. Where the person named another seat, ask them first which this clone holds, since a clone holds one seat.
   - **Whoever started the session named a seat or a role:** pass it.
   - **Only `PKIT_AGENT` says so:** pass neither, and the command takes the first free seat of your definition.
4. **Read what it printed.**
   - **0:** you hold the seat, as the instance it names. Its `role:` line says which loop you run.
   - **1, another clone took the seat first:** take another free seat of that role, or stop, as you judge (DEC-059 point 4).
   - **1, this clone holds another seat, or one of another agent definition:** say so, and stop. Which seat the clone holds is the person's to settle.
   - **1, no free seat matches:** you hold none. Say so, and stop, since a session started for a seat files and builds nothing without one (DEC-059 point 6).
   - **2:** no agent definition was named. Pass `--agent`, and run the command again.
   - **3:** GitHub failed. Run the command once more, then stop and report what failed.
5. **Run your role's loop.** The role sets your direction in place of inference from the request. A planner's seat acts in PM direction and runs step 2, and a worker's seat acts in Implementer direction and runs step 3. A lead's seat has no loop here yet: act in both directions within its scope, and ask which where the request does not show. Where a person asks you for one operation instead, do it as the seat's instance, and ask before you start the loop.

**Your seat is confirmed before each write.** Every command that writes as your instance first confirms your seat on the seat's state issue (DEC-059 point 6). So does `next-task`, before it takes a Task.

Where a command refuses because GitHub failed, run it once more. Where it still refuses, or your seat was released by force or is no longer yours, stop the loop and tell the person. Take a seat again only when they ask.

**The commit read.** Before a command confirms your seat, a note names the commit of the default branch that the run read (DEC-059 point 1). A run names it once, so the `start-work` that `next-task` runs names it no second time.

## 2. The planner's loop

A planner slices the work and files it, and builds none of it (DEC-059 point 2). From a planner's seat, `create-issue` files with no owner, so each Task enters the pool that every seat shares once it is scheduled.

1. **Take the round's work.** An EPIC whose slices wait for a second plan comes first, once the foundation's Feature its `## Outline of the slices` names has closed. The person tells you of one, or you find it in `pkit pm show-tree`: an open EPIC whose outline names no slice by number yet. Otherwise the round's work is the intent the person gives you, with its reference material.
2. **Plan it** with [batch-plan](batch-plan.md). It reads the seats and their scopes, and slices the work vertically. Where the planned Tasks would share a choice that nothing settles yet, its first plan files the foundation only, and the slices wait for a second plan ([project-management:DEC-060-foundation-before-slices]).
3. **Schedule only what the person approved.** A worker takes only a Task in Backlog. The plan's gate lists each Task the plan schedules there, and the person's approval of the plan is the authorisation that each such move needs ([project-management:DEC-006-state-machine-and-cascade]), which no role stands in for (DEC-059 point 8). Batch planning's filing step makes each move with `pkit pm promote-issue <N> --reason "<the person's approval of the plan>"`, with `--milestone <M>` where the plan names one.
4. **Report, and wait.** Say what you filed, what you scheduled, and what waits for what. The next round begins with the next intent, or with a foundation's Feature that closed.

A planner never takes a Task, and `next-task` refuses a planner's seat. It closes a container only on the person's authorisation (DEC-006), such as a foundation's Feature once its Tasks are done. An EPIC whose slices wait for a second plan is not done: say so, where the closure cascade reports it eligible to close.

## 3. The worker's loop

A worker takes ready work and builds it up to its merge (DEC-059 point 2). Each round builds one Task in this clone, and opens its pull request.

1. **Go on with what this clone has in flight,** each time the loop starts and each time it comes back here after `review-work`. Look at this clone's Task branches, named `<type>/<N>-<slug>`, and read each Task's state with `pkit pm show-issue <N>`. A Task In Progress that this clone was building goes on, on its branch. Read the pull request of each Task in Review by its branch, `pkit pm show-pr <branch>`, and go through these in order:
   - **It conflicts with the default branch,** where the `mergeable:` line reads `CONFLICTING`. On the Task's branch, fetch, merge the default branch in, resolve the conflicts, run the checks, and push. Never rebase and never force-push, since either rewrites the head the reviewers judged ([project-management:DEC-013-branch-and-pr-conventions]). Where the line reads `UNKNOWN`, GitHub has not worked out the answer yet, so read the pull request again before you take a Task.
   - **A verdict at its head asks for changes:** a `CHANGES_REQUESTED` on the `review:` line that is not marked stale. Run the fix round of [transition-state](transition-state.md)'s review step: read the findings with `pkit pm show-pr <branch> --field review`, fix only the blocking ones, and push. Answer each advisory finding in the pull request's body, with `pkit pm edit-pr <PR> --body-file <file>`, or file it as a follow-up. Leave each finding for a person to the person.
   - **Nothing left to mend:** take a new Task only once nothing is in flight, no pull request of yours waits on you, and the working tree is clean. No one needs to tell you of a conflict or a verdict, since each round looks. The person may also hand you back a pull request their landing stopped on.
2. **Take the next Task:** `pkit pm next-task --yes`. It takes this clone's own Task in Backlog, or the next ready Task in the seat's scope, and starts it through `start-work`. Starting a Task is the worker's own move, which no person authorises (`workflow.yaml`), so `--yes` is yours to pass.
   - **0:** its last line names the Task it started. Build it.
   - **5:** no Task is ready for this clone. Say so, and end the loop, keeping the seat.
   - **2:** this clone holds no seat that may take work: say what it printed, and end the loop. Where the listing reached its limit instead, run it again with a higher `--limit`.
   - **3:** the open issues could not be read. Run the command once more, then end the loop and report.
   - **1, or any other code:** a refusal, or a failure of `start-work`. Say what it printed, and end the loop.
3. **Read the Task:** `pkit pm show-issue <N>`, then its body, its acceptance criteria and its parent. Where its work rests on a foundation, read the records the foundation's Feature lists, and the walking skeleton's code (DEC-060 point 2).
   - **A Task taken over.** Where `next-task` named the Task "In Progress, its claim no longer counting", its work so far lies on its branch on the remote, with any pull request it opened. Fetch that branch, and while the fresh one `start-work` cut holds no commit, put it in its place: `git checkout -B <branch> origin/<branch>`, or delete the fresh branch where its name differs. Where the remote holds no such branch, keep the fresh one. Never force-push, and open no second pull request.
4. **Build it** in this clone, on the Task's branch, as the project builds any change: its conventions, its tests and its checks. Tick each acceptance criterion the work meets with `pkit pm check-criterion <N> <index>`, and each `## Doc impact` box with `--section doc-impact`. Write the answers the project's change check asks of the change, as the core rules say. Commit, and push the branch.
   - **A Task that holds a foundation's records.** The architect agent authors the records where the project deploys it, and you otherwise (DEC-060 point 2). The person accepts each record. Leave that criterion, and each record's status, to them.
5. **Open its pull request:** `pkit pm open-pr <N> --draft --body-file <file>`, then `pkit pm review-work <N>`. `review-work` checks the body, makes the pull request ready and moves the Task to Review. Never pass `--force` or `--bypass-owner` to either: each override is the person's.
   - **A refusal of the body:** mend the body with `pkit pm edit-pr <PR> --body-file <file>`, and run `review-work` again.
   - **A refusal by the clash guard, or of your seat:** stop the loop, and tell the person.
   - **Exit 3,** GitHub failed: run the command once more. Any other refusal, of either command, ends the loop with what it printed.
6. **Take the next Task.** Leave the clone clean, with everything committed and pushed, since the next `start-work` cuts its branch here. Then go back to 1, which reads your pull requests again before the next Task.

**The merge is the person's.** A role never authorises a merge ([project-management:DEC-059-topology-of-seats] point 8). Land a pull request only where the person asks you to, through [transition-state](transition-state.md)'s review step. Merge it only on their authorisation for that head.

**A pull request that a released seat left in Review.** A release frees every claim of the seat's clone, and the pool holds only Tasks in Backlog and In Progress ([project-management:DEC-059-topology-of-seats] points 5 and 7). So `next-task` never offers a Task in Review that a released seat left. Such a Task waits on its reviewers and the person (point 9). The person decides it: they land it as it stands, or hand it to a worker ([project-management:DEC-035-instance-ownership] point 4).

- **Take one up only where the person hands it to you.** Fetch its branch and put the branch in place, as for a Task taken over in step 3. From then on the branch is among your Task branches, and step 1 mends its pull request
- **Your own seat released by force:** the release freed your claims, so your Tasks in Review are the person's to hand back. Go on with one only where they do, once they have you take a seat again

**A foundation's choice that does not hold.** Make no other choice in its place. Say so on the Task with `pkit pm comment-issue <N> --body "<what does not hold, and why>"`, and tell the person, since the change goes through a Task of its own (DEC-060 point 5). No record decides yet how your Task waits for that change, so end the loop until the person says. The Task stays stopped, and later rounds pass over it, until they do.

**A Task you file while you work** names an open foundation's Feature among its dependencies, where it would make a choice that the Feature's `## Shared choices` lists (DEC-060 point 4).

## 4. When the seat's work ends

Keep the seat between rounds and between sessions, since a new session in this clone takes it up. Release it with `pkit pm release-seat` only when the person ends the seat's work. A release frees every claim this clone made, so a Task of yours still In Progress or in Review is left with no owner (DEC-059 point 5). `pkit pm seats` then names each such Task in Review, with its pull request, for the person to land or to hand over.

## Not in the loop yet

DEC-059 point 9 decides that the work renews a Task's claim, and that the procedure checks the claim before each push. A session whose claim passed to another clone then parks its work. No command carries these yet, and no claim lapses yet. A claim still passes to another clone after a release by force, though, and a push passes through no command. So before each push, check that `pkit pm seats` still marks your seat `← this clone`, and where it does not, push nothing and tell the person.

DEC-035 point 4 hands a Task to another clone with `handoff-issue --to-instance`, which is not built: `handoff-issue` does not move a claim between clones yet. So a pull request in Review that the person hands you keeps no owner, and no clash guard keeps another clone off it. No command lists a released seat's Tasks in Review yet either.
