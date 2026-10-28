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

## Context

Every issue moves through some sequence of states from filing to closure. The capability needs to fix what those states are, who authorises each transition (since the agent runs most state changes but irreversible ones — start of work, end of work — need explicit human gates), and how parent issues respond when their children's states change. Without this, agent behaviour around state changes is non-deterministic and the cascade across the hierarchy in [project-management:DEC-004-six-level-hierarchy] has no defined propagation rule.

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

User holds both ends of the gate (start and end of work); the agent owns the middle. Authorisations govern a move asked for directly, and are per-issue and in-session — no standing "go ahead with everything" applies in a later turn. The agent records the bypass with an audit-trail comment per [project-management:DEC-014-validation-severity-model] when a bypassable transition is overridden.

The Todo → Backlog gate means the **user-held scheduling commitment** ("this is real work we intend to do"). A Milestone assignment is one way to give it, not a precondition: a project that runs no Milestone *instances*, such as one that declares a Milestone category but has created none, still makes that commitment. So the gate is satisfied by **either** a Milestone assignment **or** an audited verbal reason, the bypassable-with-audit verbal-authorisation path [project-management:DEC-014-validation-severity-model] enumerates.

The wrapper that carries it is `promote-issue`, whose `--milestone` is optional ([project-management:DEC-026-work-ownership-lifecycle], "The seven commands"). The gate's severity is **bypassable-with-audit** in every project, whether it runs Milestones or not.

Where the project's topology declares pools of workers, a Task reaches a worker only through a Milestone in a pool, so a Task scheduled with an audited reason and no Milestone reaches no worker. Putting a Task into a Milestone in a pool, or moving it from one pool to another, is then the user's act. It is held like the transitions the user authorises at hard-reject severity, never bypassed with an audit (refinement per [project-management:DEC-061-pools-of-workers] point 6).

### Cascade rule

Three behaviours, encoded in the schema's `cascade` block:

- **Forward cascade (Todo → Backlog → In Progress).** Direction `upward`. Automatic. A container is never behind the work under it: when an issue moves forward, the agent checks each ancestor — its parent, that parent's parent, and so on to the top — and brings any that is behind up to the moved issue's state, capped at In Progress. An ancestor moves only through transitions the schema declares: one in Todo under a started issue goes to Backlog and then to In Progress. Where a journal is kept ([project-management:DEC-049-audit-journal-model]), each step is recorded with the move that caused it as its reason. The cascade is not an authorisation and asks for none: the authorisation gates on a transition govern a move asked for directly, on that issue. So an ancestor can stand in Backlog with no Milestone and no audited promotion of its own — the start commitment the user holds was given on the descendant when it was scheduled, and the ancestor's state reports it. A move to Done from Todo or Backlog — a won't-do close — moves no ancestor forward. Idempotent — repeated firings on already-cascaded ancestors are no-ops.
- **Closure cascade (→ Done).** Direction `upward`. Semi-automatic. When the *last open* child of a parent closes, the parent becomes **eligible to close** but never auto-closes. The agent validates the parent's close criteria (Feature acceptance criteria ticked, EPIC success criteria met, Umbrella purpose served) and prompts the user to authorise closure at each level.
- **Downward cascade.** Direction `none`. Disallowed. Parent state changes do not change children. The wrong direction of causation.

**Review is a Task's state alone.** A child entering Review moves no container past In Progress. A container reaches Done only through the closure cascade (In Progress → Done, cascade-eligibility per the authorisation table), once every child is done and its close criteria are met.

### Closure triggers

Four paths reach Done, encoded as schema entries:

- **`pr-merge-into-main`** — Task's normal path. PR opens → user authorises merge → agent squash-merges (head branch deleted on merge) → GitHub's `Closes #N` auto-closes the Task → cascade runs.
- **`pr-merge-into-integration`** — same mechanics but PR base is `integration/<slug>` (per [project-management:DEC-013-branch-and-pr-conventions]).
- **`manual-wont-do`** — user authorises with a reason; agent verifies all checkboxes are ticked or removed per [project-management:DEC-007-checkbox-validation], records the reason in a close comment.
- **`cascade-eligibility-close`** — triggered by closure cascade; agent validates parent's close criteria and prompts user per-level.

## Rationale

Gated state machines work well for agent-mediated workflows because the gates — the places where humans must explicitly authorise — can be enforced as tool refusals encoded in schema severities. Asked directly for a user-gated transition, the agent literally cannot make it without an authorisation signal. This converts the methodology's authority discipline into mechanical enforcement.

Upward-only cascade matches the natural direction of causation in planning: a parent's progress is a function of its children's progress, not the other way around. Allowing downward cascade would force the agent to override individual children's states based on parent moves, the wrong direction. For the same reason a forward-cascaded move is not a move asked for directly and claims no authorisation: a container's progress follows the work under it, so a container behind its descendants is brought level, not moved on anyone's say-so.

Review models a PR open for a leaf, and a container has no PR of its own. A container in Review would be stuck: Review's only forward exit is Done, while children remain to build. So no `Review → In Progress` back-edge is needed, since a container never enters Review.

The "eligible to close but never auto-close" asymmetry makes the cascade safe. Closing a Feature is a commitment ("this capability shipped"); closing an EPIC is a bigger one. Auto-closing on the last child closing would produce a chain reaction with no human pause point. Stopping at each parent for explicit authorisation preserves the deliberate quality of those commitments.

### Alternatives considered

- **Open/closed only (no intermediate states).** Rejected — loses planning visibility from Backlog/In Progress/Review.
- **Auto-close parents when last child closes.** Rejected — removes the deliberate-act quality of closure.
- **Bidirectional cascade.** Rejected — wrong direction of causation.
- **No cascade.** Rejected — parents drift out of sync with their children's reality.
- **Declare Todo → In Progress for containers, so the forward cascade moves one in a single step.** Rejected — the container's history would lose the scheduling step: it would read as started without ever having been scheduled, while the work under it was scheduled first.
- **Refuse to start a child whose ancestor is unscheduled, or leave the ancestor behind and report it.** Rejected — a container behind a started child states something false.
- **Lower the Todo → Backlog severity to `warning` in a project that runs no Milestone.** Rejected — it would hand the agent the start commitment, one of the two ends the user holds. The audited reason already serves such a project at bypassable-with-audit. A severity that varies with a project's configuration would also break [project-management:DEC-014-validation-severity-model]'s dispatch on the severity token without per-rule logic.

## Implications

- The transition-state skill walks the schema's `transitions` list to dispatch every requested state change — refuses the move (per the listed severity) if the requested transition isn't in the schema or if the user-gated transition lacks authorisation.
- The project-manager runs the cascade check after every state-changing operation: forward cascade walks ancestors and bumps any behind; closure cascade surfaces a parent-close prompt when eligibility is reached.
- PR-merge of a Task requires the checkbox-completeness check from [project-management:DEC-007-checkbox-validation] to pass before the agent authorises the merge — GitHub's auto-close on PR merge would otherwise bypass the close-gate.
- Won't-do closures trigger the same closure cascade as PR-merge closures.
- Date-based Milestone close interacts with this cascade via the rollforward rule in [project-management:DEC-016-time-bound-containers]; open children roll forward rather than closing, and the closure cascade only counts actually-closed children for eligibility.
- Integration-scope closures run the same closure cascade — the change is only the PR base branch (integration vs `main`) plus the final integration → main PR closing the owning root. See [project-management:DEC-013-branch-and-pr-conventions].
