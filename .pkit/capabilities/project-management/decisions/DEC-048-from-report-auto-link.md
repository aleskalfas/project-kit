---
id: DEC-048
title: --from-report auto-links filed fixes into a report's Tracked by via the backbone's one linker
status: accepted
date: 2026-08-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a maintainer turning feedback/change-request #N into fix
issues should not have to remember the `## Tracked by` link-back. `create-issue`
(and the batch-plan filing loop, which is create-issue in a loop) gains
`--from-report <N>`: after a successful create, the new issue is linked into
#N's `## Tracked by` — by **invoking** the backbone's `pkit report link` verb,
never by re-editing the body itself. That is the load-bearing one-linker rule.

## Context

The report channel (pkit PRJ-008) tracks a feedback's fixes in its
`## Tracked by` task-list, edited by exactly one implementation — the backbone's
report link editor, exposed as `pkit report link <N> <fix>` (maintainer-side,
gated to run only inside the report-target repo). Filing the fix, though,
belongs to this capability: `create-issue` owns classification, titles, body
composition, and batch-plan owns the planned-arc filing loop. Without a bridge,
the maintainer files through pm and must then remember a separate `report link`
call per issue — the forgettable manual step the #634 arc set out to close. A
`report derive <N>` verb wrapping issue-creation was explored and
**operator-ruled out as too ambiguous** (does it classify? does it plan? whose
flags does it carry?) — the ruling is recorded in the design carrier scratchpad
`.pkit/scratchpad/active/2026-08-09-report-scratchpad-handoff.md` ("The `derive`
fork").

## Decision

**`create-issue` gains `--from-report <N>`; batch-plan's filing loop passes it
through when the plan originated from a report. The link-back is performed by
invoking `pkit report link <N> <new>` as a subprocess — capability→backbone,
the one-linker rule.**

1. **Flag shape.** `--from-report <N>` names the feedback/change-request issue.
   After a successful create, the script invokes `pkit report link <N> <new>`
   with the new issue's number. The flag composes with every other create-issue
   flag; batch-plan is prose (a skill), so its coverage is the filing loop
   passing the flag per filed issue.
2. **One-linker rule.** The `## Tracked by` edit is implemented **once**, in the
   backbone's report link editor; pm **invokes** the canonical verb (a
   subprocess, matching how pm scripts already shell to `pkit process …`) and
   never imports backbone Python or reimplements the body edit. `--from-report`
   and a manual `report link` therefore share one editor — the reporter's
   tracking loop cannot fork. `report link` stays unchanged as the universal
   fallback (pre-existing issues, non-pm repos).
3. **Maintainer-side, same-repo posture.** The link runs where the fix is filed
   — the report-target repo. The backbone verb owns that gate (it refuses
   outside the target repo); pm does not duplicate the check and surfaces the
   refusal verbatim. Nothing new versus pkit ADR-047's report-write posture.
4. **Failure posture: warn loudly, never roll back.** A link failure after a
   successful create prints the backbone's message verbatim plus the exact
   remediation command (`pkit report link <N> <new>`) and exits non-zero
   (exit 4) — the created issue is never deleted or closed to "undo" the
   partial state.

## Rationale

The one-linker rule is the whole point: two `## Tracked by` implementations
would drift (section creation, idempotency, ordering), and the reporter-side
read (`report list --tree`, `inbox --resolved`) parses that section — a forked
writer silently breaks the close-prompt loop. Invoking the CLI verb rather than
importing backbone code keeps the dependency direction honest
(capability→backbone through the public surface) and inherits the verb's gate
and idempotency for free. The rejected `derive` verb would have put filing
authority on the report side, duplicating pm's classification/planning surface
behind an ambiguous name; the flag keeps filing where filing lives.
Warn-don't-rollback follows the capability's standing posture (native-link and
hook failures never fail the create): the issue is real work correctly filed;
only the link-back is missing, and the remediation is one printed command.

## Implications

- `create-issue.py` gains the flag + a `_link_from_report` helper (subprocess
  to `pkit report link`); exit code 4 = created-but-unlinked. Pure addition —
  no rename/removal, no schema bump, no breaking CLI change ⇒ no COR-010
  migration.
- The pm skill docs (`skills/pm/create-issue.md`, `skills/pm/batch-plan.md`)
  document the flag as what the batch-plan filing loop passes when the plan
  originated from a report.
- `requires_backbone` floor rises to the backbone version shipping
  `pkit report link` (v1.144.0) — an older backbone would fail the subprocess
  on every `--from-report` use.
- New verb flag = a capability surface change ⇒ minor changeset. Status
  `accepted` at authoring: pre-authorised in the #634 plan gate.
