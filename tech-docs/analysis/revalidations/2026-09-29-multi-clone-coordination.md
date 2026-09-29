---
change: "#943"
trigger: planned
date: "2026-09-29"
by: "software-engineer agent, for #890"
outcomes:
  UC-001: gap-found
  UC-002: holds
  UC-003: gap-found
  UC-004: gap-found
  UC-005: gap-found
  UC-006: gap-found
  UC-007: holds
  UC-008: gap-found
  UC-009: gap-found
  UC-010: gap-found
  JRN-001: gap-found
  JRN-002: gap-found
---

# 2026-09-29 — Multi-clone coordination against EPIC #943

A planned revalidation (software-analysis DEC-001 point 5): the coordination use cases and journeys, walked against the design EPIC #943 carries, before its Features are sliced. The design is the one the coordination scratchpad note settled (`2026-09-24-multi-clone-coordination-arc`, retired with this change), in its "Settled in discussion" and "Coordination EPIC — slicing" sections.

The situations were first walked while that design was made (2026-09-21 to 24, with `critic` and `architect` reviews), and that walk found gaps A to D. This walk, over the written use cases, found gaps E to J. Every gap is resolved in the design; the fixes for E to J are carried into EPIC #943's Features when they are sliced. No code was walked — the design is not built yet — so no outcome is analysis-stale or code-regressed.

## Outcomes

- **UC-001 — gap-found.** A restarted clone needs its position in seconds on whichever substrate carries ownership; the design read it with label queries (gap E).
- **UC-002 — holds.** The first note from `start-work --next`, the pause note from `pause-issue`, and resuming from the latest note give the path and every variant; a pause is neither a handoff nor a block.
- **UC-003 — gap-found.** Finding work while another clone owns the filed tree needed the reclaimable items (gap A), and then workstream routing must not filter them out again (gap F).
- **UC-004 — gap-found.** The cross-clone overview was missing (gap B), and it shares UC-001's substrate gap (gap E).
- **UC-005 — gap-found.** The release needed release scope derived from what landed (gap C) and a deferral gesture (gap D); the deferral then had to narrow the scope the guards hold (gap G).
- **UC-006 — gap-found.** The renumber command's refusal, as the design stated it, refused the very collision it exists to resolve (gap H).
- **UC-007 — holds.** The stabilisation lives on the tracker, in the Milestone's description, and the guards run in every clone and again as a required CI status, so restarted sessions and out-of-date clones meet it without remembering it.
- **UC-008 — gap-found.** Pull requests into an integration branch were exempt from the landing guard, but the start guard read "landed" on the default branch only (gap I).
- **UC-009 — gap-found.** A developer subagent in a worktree does not see its clone's instance id (gap J).
- **UC-010 — gap-found.** Stabilising computes release scope, and the deferral must reach that computation (gap G).
- **JRN-001 — gap-found.** Its seam from the overview to the idle clone breaks where routing filters reclaimable items out (gap F), and the overview and each clone must read ownership through the one fold (gap E).
- **JRN-002 — gap-found.** Its seam from the overview to the release needs one release-scope computation for the overview, the guards and the gate (gap G).

## Gaps

### Found while the design was made (2026-09-21 to 24)

- **A — UC-003: nothing free to pick while another clone owns the filed tree.** A clone owns every issue it files, the whole tree (project-management DEC-035 point 3), so an idle clone's free list — issues no instance owns — was empty while the other clone's Backlog was full. Resolved: the position also lists other instances' unstarted Backlog as reclaimable, with the command that claims it (`handoff-issue --to-instance self`, #521).
- **B — UC-004: the position was per clone.** The operator had to visit every clone to see the whole picture. Resolved: `brief --all-instances`, from any clone.
- **C — UC-005: a partly landed parent fell out of release scope.** Scope was the Milestone's tagged children, so the remaining Tasks of a Feature with some Tasks already on the default branch lay outside it; and tagging landed work with the release Milestone collided with an issue's one Milestone, already taken by Housekeeping buckets. Resolved: what landed is derived from the default branch's history since the last release — its commits, their pull requests, the issues those close, and those issues' open parents — and release scope widens to the open parents of landed work, with their subtrees.
- **D — UC-005: no way to release without a parent that will not finish in time.** Resolved: the operator defers it through the gate's bypass (`gate-milestone-closable --bypass "<reason>"`), which stamps an audit comment on the parent naming the Milestone; the gate sees the stamp and passes, in CI too.

### Found in this walk

- **E — UC-001, UC-004, JRN-001: the position's speed rested on the label substrate.** The design made `brief` fast by answering from label, assignee and state queries. But the default ownership substrate is the comment log (DEC-043; project-kit selects none, so it has the default), and a label query cannot see its owners. Resolved: `brief` folds ownership through the one read seam (ADR-041) from a single batched read of the operator's open assigned issues with their comments, so it answers in seconds on either substrate, and every clone and the overview agree on who owns what.
- **F — UC-003, JRN-001: workstream routing filtered the reclaimable items out again.** The design intersected the free and reclaimable items with the workstreams this instance handles (DEC-045). Where the operator routes each workstream to one instance, another clone's filed tree lies in that clone's workstreams, so the intersection removed exactly what gap A's fix added. Resolved: reclaimable items form a group of their own, not filtered by routing and marked when outside this instance's workstreams — routing is a hint, and the clash guard warns on such a claim; and an empty position names the filter that emptied it.
- **G — UC-005, UC-010, JRN-002: a deferral satisfied the gate but not the guards.** The deferral stamp let the release gate pass, but release scope as the stabilisation guards hold it still contained the deferred parent's subtree, so its remaining Tasks could land on the default branch during the freeze. Resolved: release scope is one computation, read by the gate, the guards and `brief`, and it drops a deferred parent with its subtree.
- **H — UC-006: the renumber refusal was inverted.** The design had `decisions renumber <old> <new>` refuse "if `<old>` is on the default branch under another slug" — which is exactly the collision it exists to resolve. Resolved: it refuses when the record being renumbered has already landed on the default branch under this branch's slug, or when `<new>` is held there.
- **I — UC-008: continuing an integration arc looked like a new front.** Pull requests into an integration branch were exempt from the stabilisation's landing guard, but the start guard's new-front test read "landed" on the default branch only, so a Task continuing an arc whose earlier Tasks had landed on its integration branch was refused. Resolved: "landed" is read on the branch the work lands on — the integration branch, for work under an integration marker. Starting an arc that has landed nothing is still a new front.
- **J — UC-009: a developer subagent's worktree does not know its clone.** The instance id is read from a git-ignored file under the working tree's own root (`_lib/instance_identity.py`), and an isolated worktree has none. Tracker commands a subagent runs there act as a clone that never opted in: no claim, no clash guard, and work it starts missing from its clone's position. Resolved: the instance id is resolved from the clone's main working tree, through git's common directory, so every worktree of a clone shares it.
