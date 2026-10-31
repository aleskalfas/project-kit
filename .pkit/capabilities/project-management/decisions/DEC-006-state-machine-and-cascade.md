---
id: DEC-006
title: Gated lifecycle state machine with upward-only cascade
status: accepted
date: 2026-05-21
author: Ales Kalfas
source:
  upstream: pm-workflow
  upstream_id: MET-005
  commit: 9d1f0237f5d5778ed9811c72f22ae8268e5faff3
  captured_at: 2026-05-21
---

> **Partially superseded by [DEC-062](DEC-062-axes-chosen-in-the-map.md).** Where a project's substrate map puts state on its board, the board's Status is the source of an open issue's position, and a closed issue stays Done by its native close. Overturned there: the State machine's "the native primitives the canonical state is inferred from", and its sentences that a board's Status field is a projection the agent maintains and that native wins. Where a present map omits state or marks it `unsupported`, the agent maintains no projection on the board, so two sentences are overturned there too: the one that it does, and the Implications' "Where a board exists and the state is native, the card's Status follows the move back". Each stands as the default, for every other project.
>
> **Partially superseded by [DEC-064](DEC-064-forward-cascade-unplaced-ancestor.md).** Where the board carries the state, the forward cascade writes nothing to an ancestor the board does not place, and the move that started it stands. So the promise that a container is never behind its work gives way at that ancestor. DEC-064's "What this overturns, and what stands" lists each passage, and each stands for every ancestor the read places.

## Context

Every issue moves through some sequence of states from filing to closure. The capability needs to fix what those states are, who authorises each transition (since the agent runs most state changes, but the commitments at either end — scheduling the work, and ending it — need explicit human gates), and how parent issues respond when their children's states change. Without this, agent behaviour around state changes is non-deterministic and the cascade across the hierarchy in [project-management:DEC-004-six-level-hierarchy] has no defined propagation rule.

## Decision

### State machine

Five states in linear order: **Todo → Backlog → In Progress → Review → Done**. Encoded in [`schemas/workflow.yaml`](../schemas/workflow.yaml). Each state carries a display name, prose meaning, the issue types it `applies_to` (Review is task-only; the other four apply to every type), and the native primitives the canonical state is inferred from (issue open/closed, Milestone assignment, branch existence, PR state).

When a Projects v2 board exists, its Status field is a projection the agent maintains. When the board and native primitives disagree, **native wins**.

### Authorisation gates

The schema's `transitions` list fixes who authorises each transition and what the agent does on violation:

| Transition | Authorisation | Severity (on violation) |
|---|---|---|
| Todo → Backlog | User (assigns a Milestone, or gives an audited reason) | bypassable-with-audit |
| Backlog → In Progress | Agent autonomous | warning |
| In Progress → Review | Agent autonomous (Task only) | warning |
| Review → Done | User (per-PR approval) | hard-reject |
| Backlog/Todo → Done (won't-do) | User | hard-reject |
| In Progress → Done (parent cascade-eligibility close) | User | hard-reject |
| Todo, Backlog or In Progress → Done (a Task completed without a pull request) | User (naming where the work's result lives) | hard-reject |
| In Progress → Backlog or Todo (move back) | User (with the reason the work stopped) | hard-reject |

The user holds the scheduling of the work, its end, and the move back from In Progress, which settles what becomes of the scheduling. The agent starts the work and puts a Task up for review on its own. Authorisations govern a move asked for directly, and are per-issue and in-session — no standing "go ahead with everything" applies in a later turn. The agent records the bypass with an audit-trail comment per [project-management:DEC-014-validation-severity-model] when a bypassable transition is overridden.

The Todo → Backlog gate means the **user-held scheduling commitment** ("this is real work we intend to do"). A Milestone assignment is one way to give it, not a precondition: a project that runs no Milestone *instances*, such as one that declares a Milestone category but has created none, still makes that commitment. So the gate is satisfied by **either** a Milestone assignment **or** an audited verbal reason, the bypassable-with-audit verbal-authorisation path [project-management:DEC-014-validation-severity-model] enumerates.

The wrapper that carries it is `promote-issue`, whose `--milestone` is optional ([project-management:DEC-026-work-ownership-lifecycle], "The seven commands"). The gate's severity is **bypassable-with-audit** in every project, whether it runs Milestones or not.

Where the project's topology declares pools of workers, a seat that builds, a worker or a lead, takes of its own choosing only a Task in an open Milestone of a pool it serves. So a Task scheduled with an audited reason and no Milestone is taken only where the user directs a seat to it (refinement per [project-management:DEC-061-pools-of-workers] point 5). Putting a Task into a Milestone in a pool, or moving it from one pool to another, is then the user's act, held like the transitions the user authorises at hard-reject severity and never bypassed with an audit (DEC-061 point 6). That hold sits on the write of the Task's Milestone, beside the scheduling gate, whose severity stays bypassable-with-audit.

**Moving back from In Progress.** The user moves back an issue In Progress that nobody is working on, so that In Progress means work is moving. The move lands in Backlog where the issue is in a Milestone, and in Todo where it is in none, so an issue scheduled with an audited reason and no Milestone returns to Todo. A move to Backlog keeps the scheduling the user gave, and a move to Todo withdraws it. A container in no Milestone lands in Backlog where one of its children is in Backlog, since a container is never behind the work under it. The user authorises the move, as the other moves the user holds, and gives the reason the work stopped.

The move posts that reason on the issue before the state changes, as the audit comment of a user-authorised move carrying a reason, which every audit setting but `off` posts ([project-management:DEC-049-audit-journal-model] point 2). It releases every owner of the issue, so the work is free for whoever takes it next. Where the clone making the move cannot release an owner, the move is refused, naming that owner ([project-management:DEC-035-instance-ownership] point 4). The owner's clone then moves the issue back, or the owner releases the claim first, so an issue never waits in Backlog or Todo still claimed.

A Task's branch and draft pull request stay as they are, for the next taker to continue or to replace. A container takes the move only where none of its children is In Progress or in Review. The move back moves no other issue: a container may stand ahead of the work under it, never behind it. The move has no wrapper of its own among the seven commands ([project-management:DEC-026-work-ownership-lifecycle]): it is rare and always a person's act, so `move-issue`, with the reason it requires, is its path.

### Cascade rule

Three behaviours, encoded in the schema's `cascade` block:

- **Forward cascade (Todo → Backlog → In Progress).** Direction `upward`. Automatic. A container is never behind the work under it: when an issue moves forward, the agent checks each ancestor — its parent, that parent's parent, and so on to the top — and brings any that is behind up to the moved issue's state, capped at In Progress. An ancestor moves only through transitions the schema declares: one in Todo under a started issue goes to Backlog and then to In Progress. Where a journal is kept ([project-management:DEC-049-audit-journal-model]), each step is recorded with the move that caused it as its reason. The cascade is not an authorisation and asks for none: the authorisation gates on a transition govern a move asked for directly, on that issue. So an ancestor can stand in Backlog with no Milestone and no audited promotion of its own — under a descendant scheduled or started, the scheduling commitment the user holds was given on that descendant when it was scheduled, and the ancestor's state reports it. A won't-do close from Todo or Backlog moves no ancestor forward. A Task's completed close (`manual-completed`) does, from those states as from In Progress: each ancestor behind is brought up to In Progress before the closure cascade runs. What grounds those moves is the user's authorisation of the close itself, which every completed close carries, since a Task closed from Todo was never scheduled. Idempotent — repeated firings on already-cascaded ancestors are no-ops.
- **Closure cascade (→ Done).** Direction `upward`. Semi-automatic. When the *last open* child of a parent closes, the parent becomes **eligible to close** but never auto-closes. The agent validates the parent's close criteria (Feature acceptance criteria ticked, EPIC success criteria met, Umbrella purpose served) and prompts the user to authorise closure at each level.
- **Downward cascade.** Direction `none`. Disallowed. Parent state changes do not change children. The wrong direction of causation.

**Review is a Task's state alone.** A child entering Review moves no container past In Progress. A container reaches Done only through the closure cascade (In Progress → Done, cascade-eligibility per the authorisation table), once every child is done and its close criteria are met.

### Closure triggers

Five paths reach Done, encoded as schema entries:

- **`pr-merge-into-main`** — Task's normal path. PR opens → user authorises merge → agent squash-merges (head branch deleted on merge) → the tracker's `Closes #N` auto-closes the Task → cascade runs.
- **`pr-merge-into-integration`** — same mechanics but PR base is `integration/<slug>` (per [project-management:DEC-013-branch-and-pr-conventions]).
- **`manual-completed`** — a Task's completed close, for work that was not a pull request, such as an audit, an investigation or a decision walked with the user. The user authorises the close once every checkbox is ticked, per [project-management:DEC-007-checkbox-validation], and the close comment names where the work's result lives, such as an issue, a record or a comment. The tracker records the Task as completed. The forward cascade then brings each ancestor behind up to In Progress, and the closure cascade runs as for a PR-merge closure. It closes a Task in Todo, Backlog or In Progress, since a Task in Review has a pull request open and closes through its merge.
- **`manual-wont-do`** — user authorises with a reason; agent verifies all checkboxes are ticked or removed per [project-management:DEC-007-checkbox-validation], records the reason in a close comment.
- **`cascade-eligibility-close`** — triggered by closure cascade; agent validates parent's close criteria and prompts user per-level.

## Rationale

Gated state machines work well for agent-mediated workflows because the gates — the places where humans must explicitly authorise — can be enforced as tool refusals encoded in schema severities. Asked directly for a user-gated transition, the agent literally cannot make it without an authorisation signal. This converts the methodology's authority discipline into mechanical enforcement.

Upward-only cascade matches the natural direction of causation in planning: a parent's progress is a function of its children's progress, not the other way around. Allowing downward cascade would force the agent to override individual children's states based on parent moves, the wrong direction. For the same reason a forward-cascaded move is not a move asked for directly and claims no authorisation: a container's progress follows the work under it, so a container behind its descendants is brought level, not moved on anyone's say-so.

Review models a PR open for a leaf, and a container has no PR of its own. A container in Review would be stuck: Review's only forward exit is Done, while children remain to build. So no `Review → In Progress` back-edge is needed, since a container never enters Review.

The "eligible to close but never auto-close" asymmetry makes the cascade safe. Closing a Feature is a commitment ("this capability shipped"); closing an EPIC is a bigger one. Auto-closing on the last child closing would produce a chain reaction with no human pause point. Stopping at each parent for explicit authorisation preserves the deliberate quality of those commitments.

**Why a Task closes as completed without a pull request.** Some work ends with nothing to merge: an audit whose findings are filed as issues, an investigation, a decision walked with the user. Without a close of its own, such a Task can only stay open, stating work not yet done, or close as won't-do, stating work dropped, and both are false. The close names where the result lives, so a later reader finds the work, as a merged pull request's reference leads to code. The user authorises it as the user authorises every end of work, and every checkbox ticked is what says the work is done.

**Why a completed close brings its ancestors level.** A won't-do close moves no ancestor forward, since dropped work is no progress, and a container it moved would report work that never started. That reason does not cover a completed close: completed work is progress, wherever the Task stood when it closed. A container left behind it would state something false, as one behind started work does. So the forward cascade runs on a completed close from Todo or Backlog, and the closure cascade then offers each parent for closing, as after any close. A Task closed from Todo was never scheduled, so no scheduling grounds its ancestors' moves: the user's authorisation of the close does, since it says the work under them is done.

**Why a move back, and why it is the user's.** People planning the work, and agents choosing what to take next, read In Progress as work that is moving. An issue left In Progress after its work stopped states something false, and without a move back the only way to make it true is to close live work. The user's commitment is the scheduling, not the start of work, which the agent takes on its own. A move back settles what becomes of the scheduling: a move to Todo withdraws it, and a move to Backlog keeps it. So the user holds the move back, as the user holds the scheduling and the end. Releasing the claim frees the work for whoever takes it next, and the reason on the issue tells a later reader why the work stopped.

A claim left on an issue moved back would tell every other clone that someone works on it, which is the falsehood the move back exists to end. So the move is refused where the claim cannot go with it, and is left to the owner, who can release the claim.

A container moved back over a child In Progress or in Review would stand behind that child, which is the state the forward cascade exists to prevent. Refusing that move keeps the cascade's guarantee without making the cascade run in both directions.

### Alternatives considered

- **Open/closed only (no intermediate states).** Rejected — loses planning visibility from Backlog/In Progress/Review.
- **Auto-close parents when last child closes.** Rejected — removes the deliberate-act quality of closure.
- **Bidirectional cascade.** Rejected — wrong direction of causation.
- **No cascade.** Rejected — parents drift out of sync with their children's reality.
- **Declare Todo → In Progress for containers, so the forward cascade moves one in a single step.** Rejected — the container's history would lose the scheduling step: it would read as started without ever having been scheduled, while the work under it was scheduled first, or closed as completed on the user's authorisation.
- **Refuse to start a child whose ancestor is unscheduled, or leave the ancestor behind and report it.** Rejected — a container behind a started child states something false.
- **Lower the Todo → Backlog severity to `warning` in a project that runs no Milestone.** Rejected — it would hand the agent the scheduling commitment, which the user holds. The audited reason already serves such a project at bypassable-with-audit. A severity that varies with a project's configuration would also break [project-management:DEC-014-validation-severity-model]'s dispatch on the severity token without per-rule logic.
- **Let the agent move back an issue it finds idle.** Rejected — whether work has stopped is a judgement on a commitment the user made, and an agent reading inactivity alone could stop live work.
- **Move a container back together with its children.** Rejected — a container's move would change its children's states, the downward cascade this record disallows.
- **Close a Task whose work was not a pull request as won't-do, with a reason naming the result.** Rejected — the tracker records it as not planned, so every reader of the close reason takes the work as dropped.
- **Give such a Task a pull request, such as a note committed only to close it.** Rejected — the commit adds a file nobody needs, and the result still lives elsewhere.
- **Let a completed close from Todo or Backlog move no ancestor, as a won't-do close moves none.** Rejected — each container above the Task would stand behind finished work, which the forward cascade exists to prevent.

## Implications

- The transition-state skill walks the schema's `transitions` list to dispatch every requested state change — refuses the move (per the listed severity) if the requested transition isn't in the schema or if the user-gated transition lacks authorisation.
- The project-manager runs the cascade check after every state-changing operation: forward cascade walks ancestors and bumps any behind; closure cascade surfaces a parent-close prompt when eligibility is reached.
- PR-merge of a Task requires the checkbox-completeness check from [project-management:DEC-007-checkbox-validation] to pass before the agent authorises the merge — the tracker's auto-close on PR merge would otherwise bypass the close-gate.
- Won't-do closures and a Task's completed close trigger the same closure cascade as PR-merge closures.
- Date-based Milestone close interacts with this cascade via the rollforward rule in [project-management:DEC-016-time-bound-containers]; open children roll forward rather than closing, and the closure cascade only counts actually-closed children for eligibility.
- Integration-scope closures run the same closure cascade — the change is only the PR base branch (integration vs `main`) plus the final integration → main PR closing the owning root. See [project-management:DEC-013-branch-and-pr-conventions].
- A move back from In Progress is refused, and writes nothing, where a condition of "Moving back from In Progress" does not hold or cannot be checked. The conditions are a reason, a target that is the state the issue lands in, and, for a container, no child In Progress or in Review. So a container is refused too where its children cannot all be listed, or where the state of one of them cannot be read. The capability's [README](../README.md), "Moving an issue back from In Progress", lists each refusal and what it names.
- A move back releases the owner's claim through the one release path a close uses, so the two never disagree on what a release writes. Where that path cannot release an owner, the move back refuses before it writes anything, naming the owner ([project-management:DEC-035-instance-ownership] point 4).
- Where the board carries the state, the move back is refused and writes nothing, so it releases no claim and journals no move. Where a board exists and the state is native, the card's Status follows the move back, as it follows every move.
- Where the substrate map puts state on the board, a move writes the board's Status as the state's source, and so does the forward cascade. That write lands with the read of a board-carried state ([project-management:DEC-051-axis-carriage-activation] point 6), or after it, since a writer with no reader would put the state where nothing reads it.
- Open where the board carries the state: what a card a person drags by hand means, such as whether a card dragged back from In Progress makes a move back, owing a reason and releasing the owner, and whether a cascade reconciles such a move on its own.
