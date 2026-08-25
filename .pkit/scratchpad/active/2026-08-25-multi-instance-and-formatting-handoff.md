---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-25
---

# Multi-instance ownership + comment-formatting — session handoff

**This is a continuity note, not a single-question exploration.** It bookmarks
two in-flight arcs so a future session can resume either without re-deriving the
context. It intentionally spans two topics (an exception to the scratchpad
one-question norm, matching the precedent of prior handoff notes like
`2026-05-28-session-handoff-cli-gap-follow-up.md`). Retirement: drop it once both
arcs have resumed and produced their own artifacts — it crystallises nothing
itself; the real design lives in the cited DECs and sibling notes.

Cross-arc link: the two arcs **overlap** at the audit/comment layer — the
comment house-style (arc B) governs how the shared audit-log facility (arc A,
DEC-044 / #511) renders. Reconcile them before either ships its comment renderer.

---

## Arc A — Multi-instance ownership & coordination (EPIC #508)

### Why it matters
Working multiple clones of the same project (as we do in project-kit itself)
causes interference: no clear signal for which instance owns which workstream.
The arc gives instances identity, ownership claims, and a shared audit log.

### Design basis (all `accepted`)
- **DEC-035** — instance ownership (claim / handoff / release + clash guard).
- **DEC-043** — ownership substrate selection (label-free: comment log +
  description mirror).
- **DEC-044** — shared audit-log facility. **Overlaps DEC-049** (audit/journal
  model, already shipped) **and #756** (comment house-style) — see "open
  questions" below; do not implement DEC-044's renderer until reconciled.
- **DEC-045** — named per-user instances (+ a `create-instance` script).

Predecessor EPIC **#232** (project-management: multi-clone instance ownership) is
still open — it is the earlier framing of the same problem. Close it as
superseded-by-#508 during the shape review (confirm nothing unique is stranded
there first).

### What is shipped vs. not
- **Shipped (#509, closed):** seam libraries `_lib/instance_identity.py` and
  `_lib/instance_ownership.py`. They exist but are **NOT wired into the
  lifecycle** (start-work / move-issue / etc. do not call them yet).
- **Not started:** the actual claim/release wiring, named instances, and
  `create-instance` provisioning.

### Open EPIC #508 subtree
- **#510** (Feature) — Instance identity + ownership lifecycle.
  - **#519** (Task, parent `Feature: #510`) — Claim/release wiring into the
    lifecycle. This is the first real implementation task.
- **#511** (Feature) — Shared audit-log facility (the DEC-044 ↔ DEC-049 ↔ #756
  overlap lives here).
- **#512** (Feature) — Named per-user instances.
- **#513** (Feature) — `create-instance` provisioning script.
- Closed: #509 (seam libs), #515.

### Shape review to do BEFORE implementing
The user's standing instruction: *review the EPIC + tasks for validity and good
shape before starting to implement.* Concretely:
1. **Reconcile the audit facility** across DEC-044 (this arc), DEC-049 (shipped
   audit/journal), and #756 (comment house-style). There is real overlap — decide
   whether #511 consumes DEC-049's journal + arc-B's renderer rather than
   introducing a parallel facility.
2. **Resolve the `handoff-issue` naming collision** — "handoff" means both a
   *member* handoff (reassign work) and an *instance* handoff (transfer
   ownership). Pick distinct verbs before either ships.
3. **Re-slice #510** — it is broad; split identity vs. ownership-lifecycle if the
   review confirms.
4. **Confirm #512 / #513 scope + priority.**
5. **Close predecessor #232** (superseded by #508).
6. Then implement, in order: **#519** (claim/release wiring) → the rest of
   **#510**.

### Delivery mechanism (user directive)
Do **all** #508 work **against one integration branch** —
`integration/508-multi-instance-ownership` — and do **not** merge to `main` until
the whole functionality is ready. This is the DEC-013 integration-branch
construct, which is now usable end-to-end:
- The read-side validator gap was fixed and merged (**#763 → PR #764 → `main`
  `92f0341`**). All parent-ref *read* recognizers now skip the
  `Integration: integration/<slug>` marker, and validate/edit-issue emit a
  precise `body.integration-marker` finding for a malformed one.
- **Known write-side gap (#765, open):** `set-field --parent` still inverts the
  marker/parent-ref order on a marked descendant. Fix #765 **before** relying on
  `set-field --parent` against marked #508 descendants (or avoid that path until
  then).

### Immediate next step for arc A
Run the shape review (list above) as a discussion — one decision at a time — then
designate `integration/508-multi-instance-ownership` (place the marker on #508,
propagate to #510/#511/#512/#513/#519) and start #519.

---

## Arc B — pkit comment house-style + aggregated review format (EPIC #756)

### State
- Branch **`feat/757-design-pkit-comment-house-style`**, draft **PR #759**
  ("Design pkit comment house-style + aggregated review format (scratchpad →
  DEC)"). Tip commit `87d4814`.
- Design work is captured in scratchpad notes committed on that branch:
  `2026-08-18-pkit-comment-house-style.md`,
  `2026-08-23-code-review-surface-template.md`, the rendered examples, and
  `2026-08-24-code-review-round-{1,2,3}.md` /
  `2026-08-24-code-review-agent-block-styles.md`.

### Settled design (ready to crystallise into a DEC)
- **One house style for every pkit-authored comment** — audit / verdict / filing
  / hooks all share it.
- Icons: **🧰 = pkit tool**, **🤖 = agent**.
- Per-agent block header: `### 🤖 \`agent\` → ⛔️/✅ VERDICT`, with nested
  `- *Blocking:*` / `- *Advisory:*` lists.
- Universal footer on every comment:
  `<sub>🧰 pkit · tree \`<v>\` · pm \`<v>\` · cli \`<v>\`</sub>`.
- **Aggregated code review = one review per round**, not one comment per agent.
- Drop the standalone filing comment (the footer is universal, so filing
  provenance rides the footer).

### Overlaps
- **DEC-049** (audit/journal, shipped) and **DEC-044 / #511** (arc A's audit-log
  facility) both render comments — they must adopt this house style. This is the
  cross-arc reconciliation point.

### Immediate next step for arc B
Crystallise the settled design into a **DEC** (comment house-style;
scratchpad → DEC per #757), take it through the reviewer gate, then implement the
shared renderer and migrate the audit / verdict / filing / hook call-sites onto
it. **This is the arc the user is switching to now.**

---

## Resume checklist
- **Arc A:** re-open this note + DEC-035/043/044/045 + EPIC #508 subtree; start
  with the shape-review discussion; mind #765 (write-side marker gap) before
  `set-field --parent` on marked issues.
- **Arc B:** `git checkout feat/757-design-pkit-comment-house-style`; the
  scratchpad notes on that branch are the source; next artifact is the DEC.
