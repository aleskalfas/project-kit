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
  UC-007: gap-found
  UC-008: gap-found
  UC-009: gap-found
  UC-010: gap-found
  JRN-001: gap-found
  JRN-002: gap-found
---

# 2026-09-29 — Multi-clone coordination against EPIC #943

A planned revalidation (software-analysis DEC-001 point 5): the coordination use cases and journeys, walked against one version of the design, before EPIC #943's Features are sliced.

**The version walked.** Two sources, taken together:

- the design the coordination scratchpad note settled, `2026-09-24-multi-clone-coordination-arc`, retired with this change — its "Settled in discussion" and "Coordination EPIC — slicing" sections as committed on the default branch at `681e819`, which the retirement left unchanged;
- EPIC #943 as it stood on 2026-09-30 (body last edited 2026-09-29 22:36 UTC), which carries the outcome and success criteria the use cases serve, and lists the proposed fixes below as pending.

**Three rounds of finding.** The situations were first walked while that design was made, from 2026-09-21 to 24, with `critic` and `architect` reviews; that walk found gaps A to D, whose fixes are part of the version walked. This walk checked the written use cases against that version on 2026-09-29 and found gaps E to J. The `critic` and `architect` review of this walk, on 2026-09-30, checked against the same version, found K1 to K3, and refined several of the others. None of E to K3 is resolved: each has a proposed fix, pending authorisation, which a Feature or Task of EPIC #943's slicing carries — or, for J, #1140 under EPIC #508. Where a fix has alternatives the review raised, they are listed and not decided. No code was walked — the design is not built — so no outcome is analysis-stale or code-regressed.

## Outcomes

- **UC-001 — gap-found.** A restarted clone needs its position in seconds on whichever substrate carries ownership; the design read it with label queries (gap E).
- **UC-002 — holds.** The first note from `start-work --next`, the pause note from `pause-issue`, and resuming from the latest note give the path and every variant; a pause is neither a handoff nor a block. That notes are never merged still needs authorisation (below), which is not a gap in the description.
- **UC-003 — gap-found.** Finding work while another clone owns the filed tree needed the reclaimable items (gap A), and then workstream routing must not filter them out again (gap F); under a stabilisation, release-scope work it lists as free was refused by the start guard (gap K1).
- **UC-004 — gap-found.** The cross-clone overview was missing (gap B), and it shares UC-001's substrate gap (gap E).
- **UC-005 — gap-found.** The release needed release scope derived from what landed (gap C) and a deferral (gap D); the deferral then had to narrow the scope the guards hold (gap G), and to reach pull requests whose status was already green (gap K2); and the release pull request, closing no issue, falls outside scope as defined (gap K3).
- **UC-006 — gap-found.** The renumber command's refusal, as the design stated it, refused the very collision it exists to resolve (gap H).
- **UC-007 — gap-found.** The start guard refused release-scope work its own step 2 offers as free to pick (gap K1), and the required status that holds out-of-date clones and raw merges does not see a stabilisation that came after a pull request's last commit (gap K2). Its restart path otherwise holds: the stabilisation lives on the tracker, so restarted sessions meet it without remembering it.
- **UC-008 — gap-found.** Pull requests into an integration branch were exempt from the landing guard, but the start guard read "landed" on the default branch only (gap I).
- **UC-009 — gap-found.** A developer subagent in a worktree does not see its clone's instance id (gap J).
- **UC-010 — gap-found.** Stabilising computes release scope, and the deferral must reach that computation (gap G); the start guard refused release-scope fronts (gap K1); the required status misses tracker events (gap K2); and pull requests that close no issue have no rule (gap K3).
- **JRN-001 — gap-found.** Its seam from the overview to the idle clone breaks where routing filters reclaimable items out (gap F), and the overview and each clone must read ownership the same way (gap E).
- **JRN-002 — gap-found.** Its seam from stabilising to the release needs one release scope for the guards, the readiness and the gate (gap G), a status that sees tracker events (gap K2), and a rule for the release pull request (gap K3). Its middle step, the overview (UC-004), was dropped in review: it was no seam of this path, whose real hand-over is UC-005's readiness.

## Gaps

### Found while the design was made (2026-09-21 to 24)

These are the earlier walk's findings. Their fixes were folded into the design before this walk, so they are part of the version walked — designed, not built.

- **A — UC-003: nothing free to pick while another clone owns the filed tree.** A clone owns every issue it files, the whole tree (project-management DEC-035 point 3), so an idle clone's free list — issues no instance owns — was empty while the other clone's Backlog was full. Fix, in the version walked: the position also lists other instances' unstarted Backlog as reclaimable, with the command that claims it (`handoff-issue --to-instance self`, #521).
- **B — UC-004: the position was per clone.** The operator had to visit every clone to see the whole picture. Fix, in the version walked: `brief --all-instances`, from any clone.
- **C — UC-005: a partly landed parent fell out of release scope.** Scope was the Milestone's tagged children, so the remaining Tasks of a Feature with some Tasks already on the default branch lay outside it; and tagging landed work with the release Milestone collided with an issue's one Milestone, already taken by Housekeeping buckets. Fix, in the version walked: what landed is derived from the default branch's history since the last release — its commits, their pull requests, the issues those close, and those issues' open parents — and release scope widens to the open parents of landed work, with their subtrees.
- **D — UC-005: no way to release without a parent that will not finish in time.** Fix, in the version walked: the operator defers it through the gate's bypass (`gate-milestone-closable --bypass "<reason>"`), which stamps an audit comment on the parent naming the Milestone; the gate sees the stamp and passes, in CI too.

### Found in this walk (2026-09-29)

- **E — UC-001, UC-004, JRN-001: the position's speed rested on the label substrate.** The design made `brief` fast by answering from label, assignee and state queries. But the default ownership substrate is the comment log (DEC-043; project-kit selects none, so it has the default), and a label query cannot see its owners. Proposed fix (pending authorisation; carried by F1 T1.2 of EPIC #943): `brief` folds ownership through the one read seam (ADR-041) from a single batched read of the operator's open assigned issues with their comments, so it answers in seconds on either substrate, and every clone and the overview agree on who owns what. Open: unowned and unassigned issues — the free-to-pick list — are not among the operator's assigned issues, so they need a second query; and which governs the read, DEC-043's "the comment log is read only to reconcile or show history", with the owner read from the description's mirror, or ADR-041's fold of the log.
- **F — UC-003, JRN-001: workstream routing filtered the reclaimable items out again.** The design intersected the free and reclaimable items with the workstreams this instance handles (DEC-045). Where the operator routes each workstream to one instance, another clone's filed tree lies in that clone's workstreams, so the intersection removed exactly what gap A's fix added. Proposed fix (pending authorisation; carried by F1 T1.2 of EPIC #943): reclaimable items form a group of their own, not filtered by routing and marked when outside this instance's workstreams — routing is a hint, and the clash guard warns on such a claim; and an empty position names the filter that emptied it. Open: whether free items stay filtered while reclaimable ones are not, or both are left unfiltered and marked, or both filtered; and what settles two clones reclaiming the same item at once, which DEC-035 point 6's tie-break, written for claiming an unowned issue, does not cover (UC-003 5a claimed it did).
- **G — UC-005, UC-010, JRN-002: a deferral satisfied the gate but not the guards.** The deferral stamp let the release gate pass, but release scope as the stabilisation guards hold it still contained the deferred parent's subtree, so its remaining Tasks could land on the default branch during the freeze. Proposed fix (pending authorisation; carried by F2 T2.1 and T2.2 of EPIC #943): release scope is one computation, read by the gate, the guards and `brief`, and it drops a deferred parent with its subtree. Open: how a deferral is recorded — the gate's bypass, as gap D's fix had it, or a revocable audit event of its own; and which wins when a Task lies in a deferred subtree and is also a child of the Milestone.
- **H — UC-006: the renumber refusal was inverted.** The design had `decisions renumber <old> <new>` refuse "if `<old>` is on the default branch under another slug" — which is exactly the collision it exists to resolve. Proposed fix (pending authorisation; carried by F3 T3.2 of EPIC #943): it refuses when the record being renumbered has already landed on the default branch, or when `<new>` is held there. Open: how "already landed" is recognised — by this branch's slug on the default branch, or by the record having existed at the merge-base, which a changed or coinciding slug cannot mislead.
- **I — UC-008: continuing an integration arc looked like a new front.** Pull requests into an integration branch were exempt from the stabilisation's landing guard, but the start guard's new-front test read "landed" on the default branch only, so a Task continuing an arc whose earlier Tasks had landed on its integration branch was refused. Proposed fix (pending authorisation; carried by F2 T2.2 of EPIC #943): "landed" is read on the branch the work lands on — the integration branch, for work under an integration marker; starting an arc that has landed nothing is still a new front. Alternative: leave integration-marked work out of the start guard altogether. Refusing its start sits ill with UC-008's goal, that integration work goes on during a stabilisation, and its one way to the default branch, the promotion, is guarded already.
- **J — UC-009: a developer subagent's worktree does not know its clone.** The instance id is read from a git-ignored file under the working tree's own root (`_lib/instance_identity.py`), and an isolated worktree has none. Tracker commands a subagent runs there act as a clone that never opted in: no claim, no clash guard, and work it starts missing from its clone's position. Proposed fix (pending authorisation; carried by #1140, under EPIC #508): a worktree inherits its clone's instance id through git's common directory. Open: whether a worktree's own id file wins, so that a worktree may act as an instance of its own; #1140 proposes it does.

### Found in review of this walk (2026-09-30)

- **K1 — UC-003, UC-007, UC-010: the start guard refused release-scope work.** As written, the guard refuses every new front — including an untouched Feature under the release Milestone, and every Task filed directly under it through the shortcut hierarchy (project-management DEC-004) — while UC-003 2a and UC-007 step 2 offer exactly those as free to pick. Proposed fix (pending authorisation; carried by F2 T2.2 of EPIC #943): refuse a start only when it is a new front **and** outside release scope.
- **K2 — UC-005, UC-007, UC-010, JRN-002: the required status does not see tracker events.** A required CI status is computed per head commit. `stabilize-milestone` and a deferral are tracker events that push no commit, so a pull request that went green before the freeze stays green, and a raw merge crosses it — the case UC-007 4a and TERM-stabilisation say the status holds. It also bears on gap G: a deferral narrows scope without re-running anything. Proposed fix (pending authorisation; carried by F2 T2.3 and T2.5 of EPIC #943; the design must choose): re-run open pull requests' status on Milestone edits and deferral events; evaluate at merge time, through a merge queue (#1011); or declare the residual gap, as ADR-019 point 3 requires of a gate that does not hold its whole boundary.
- **K3 — UC-005, UC-010, JRN-002: a pull request that closes no issue has no place in release scope.** Release scope is defined over issues. The release pull request closes no issue, and neither do changeset-only, documentation and dependency pull requests, so the landing guard and the required status either refuse the release pull request — a deadlock, the freeze holding back the release it exists for — or leave it undefined. Proposed fix (pending authorisation; carried by F2 T2.3 and T2.5 of EPIC #943): state the rule in UC-005 and UC-010 — either a pull request closing no issue is in scope, or release pull requests are exempt, by the project's configuration.
- **K4 — refines C and G, for UC-005, UC-010 and TERM-release-scope.** Not a gap of its own; open questions the release-scope computation must answer: whether "open parent" means the nearest parent or every ancestor; that a parent may be a Milestone — the shortcut hierarchy files Tasks directly under it — and a Milestone takes no comments, so a deferral cannot be stamped on it; and that a catch-all Umbrella, which never closes, would as an open parent of landed work hold every release.

## Needs explicit human authorisation

Nothing above is settled until a person authorises it.

- **From the design walked** (the retired note's list): a core record for provisional decision numbering (F3 T3.0); the reciprocal note on project-management DEC-049, content against projection; the PRJ-002 amendment for the release gate; the refinement of DEC-016 for a `release` Milestone category.
- **J refines DEC-035 point 1.** The instance id is "clone-local" there; a clone would include its worktrees, and perhaps let a worktree set its own id.
- **Intent notes that are never merged refine DEC-044 point 2**, whose stamp lets a re-run command find an earlier stamp and skip or update it rather than post again.
- **E may set aside DEC-043's read cost**, if every listing reads the comment log rather than the description's mirror.
- **Every proposed fix here is agent-made and unconfirmed.** This record carries no `confirmed-by`: the outcomes and the fixes stand as the agent's proposal until the operator confirms or amends them.
