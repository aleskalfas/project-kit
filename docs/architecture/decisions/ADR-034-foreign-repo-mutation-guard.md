---
id: ADR-034
title: Foreign-repo mutation guard — pkit self-checks the session anchor against the cwd target
status: accepted
date: 2026-06-30
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

A session rooted in repo A can `cd` into a different project's repo B and file
an issue, author a record, or commit there — landing mechanically-correct
artifacts under the wrong project's governance. [COR-039](../../../.pkit/decisions/core/COR-039-session-repo-mutation-boundary.md)
fixed the universal principle (a session mutates only the repo it is rooted in;
cross-repo mutation is operator-gated, never silent). This ADR records the
**harness-specific *how*** for the Claude Code adapter — and is honest about
which layer can actually carry the check and which cannot.

The lever is a **pkit self-guard**: the program that owns a mutation (the
project-management capability scripts and `pkit`) compares the **cwd-derived
mutation target** against the **session anchor** — the `CLAUDE_PROJECT_DIR`
environment variable, which the harness sets at session launch and which **does
not move with `cd`**. On divergence it **refuses-or-prompts** (operator-gated),
never a silent mutation and never a hard deny. The self-guard is feasible
precisely *because* the anchor is cd-invariant: `cd /B && create-issue` leaves
the anchor pointing at A, so the comparison sees the mismatch — and the
cd-defeat that breaks command-string inspection does **not** recur one layer
down, because the anchor is the env var, not a second cwd-walk.

**Decision in one line:** the mutating program self-checks anchor-vs-target and
operator-gates on divergence; the intent-layer hook adds one honest catch (an
Edit/Write to an absolute foreign path may prompt); and session-root
write-scoping is **explicitly not** introduced as a foreign-repo boundary,
because on macOS the mutating tools (`uv`/`pkit`, `gh`) run *outside* the box by
necessity ([ADR-014](ADR-014-macos-sandbox-platform-stance.md) /
[ADR-027](ADR-027-required-sandbox-exclusion-auto-apply.md) /
[ADR-030](ADR-030-gh-exclusion-required-subclass-generalises.md)), so a
filesystem fence would be partial for exactly the incident's command class — the
believed-but-absent-boundary trap ([ADR-004](ADR-004-autonomy-intent-confinement.md)
decision point 4).

This is a **discipline-grade interlock, not a security boundary.** It catches the
*accidental-handoff* shape (the methodology's own validated path used while the
session is `cd`'d into the wrong repo) reliably for that path. It does **not**
stop a determined bypass (raw `gh -R`, raw `git -C`, `unset CLAUDE_PROJECT_DIR`).
That residual gap is declared honestly per [COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md),
not papered over. Because the ADR makes a load-bearing claim about a boundary's
**absence** (the interlock is not a wall), it carried an explicit
foundational-re-authorisation flag and landed `proposed` pending operator
sign-off — the same class of flag [ADR-030](ADR-030-gh-exclusion-required-subclass-generalises.md)
carried; that sign-off has since been given and the record is `accepted`.

## Context

[COR-039](../../../.pkit/decisions/core/COR-039-session-repo-mutation-boundary.md)
(accepted) establishes the principle: an agent session is rooted in one repo and
carries that repo's governance (its rules, conventions, deployed agents,
permission model); a session must mutate only the repo it is rooted in; a
genuine cross-repo mutation is a legitimate but operator-gated exception,
surfaced and confirmed per change, never silent. COR-039 deliberately leaves the
*how* — the session-anchor signal, the detection point, the per-platform
confinement story — to a realization ADR. This is that ADR for the Claude Code
adapter.

The incident COR-039 closes occurred concretely: a session rooted in one repo
filed issues, authored decisions, and committed into a **separate** adopter repo
by changing directory into it. The mechanics succeeded — `gh` and `git` operate
on whatever they are pointed at — but the second repo's governance never loaded.

**The decisive code fact this ADR's lever rests on.** The mutating program
already reads two *different* roots from two *different* sources, and they
diverge under exactly the incident's `cd`:

- The **pkit tree** is resolved from the **session anchor**. The Claude Code
  permission hook's `_target_root()` (`.pkit/adapters/claude-code/permission-hook.py`)
  reads `CLAUDE_PROJECT_DIR` — the harness's session-launch contract — and the
  capability scripts resolve their capability root the same way
  (`resolve_capability_root` in `.pkit/capabilities/project-management/scripts/`).
  `CLAUDE_PROJECT_DIR` is set once at session launch and **does not move with
  `cd`**: `cd /B && create-issue` still resolves the pkit tree at A.
- The **mutation target** is resolved from **cwd's remote**. `create-issue.py`
  posts via `gh issue create`, and `gh` derives the repo from the cwd's git
  remote (`_resolve_repo_name_with_owner_safe()` calls `gh repo view`); a `cd`
  redirects it to B.

That asymmetry — a cd-invariant anchor and a cd-redirected target read by the
same program — is the guard's hook. The program can compare the two and detect
the mismatch the moment it is about to mutate B while rooted at A.

Two prior structures bound the shape of any realization and must be honoured:

- **The intent/permission layer cannot carry this as a wall.**
  [ADR-004](ADR-004-autonomy-intent-confinement.md) and
  [ADR-025](ADR-025-segment-conservative-bash-allow.md) establish that command
  inspection cannot confine a shell: `cd` and absolute paths defeat any cwd
  check, and the dumb segmenter abstains rather than parses harder. A bash
  command pointed at B is exactly the shape the hook cannot reliably catch —
  [ADR-025](ADR-025-segment-conservative-bash-allow.md) strips a leading `cd` for
  *prompt-reduction* and explicitly does **not** parse the rest. So the hook is
  not the lever.
- **Confinement is partial for the mutating tools on macOS.** On macOS,
  `uv`/`pkit` ([ADR-014](ADR-014-macos-sandbox-platform-stance.md) /
  [ADR-027](ADR-027-required-sandbox-exclusion-auto-apply.md)) and `gh`
  ([ADR-030](ADR-030-gh-exclusion-required-subclass-generalises.md)) are
  **required exclusions** that run *outside* the Seatbelt box by necessity (fixed
  mach-service denials, accommodation-proof). A `filesystem.allowWrite` fence
  scoped to the session root therefore would not bound exactly the commands at
  issue — the pm scripts (via `uv`) and `gh`. Advertising such a fence as a
  foreign-repo boundary is the believed-but-absent-boundary trap
  ([ADR-004](ADR-004-autonomy-intent-confinement.md) decision point 4 forbids it;
  [COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md)'s
  honesty discipline forbids it).

The existing cross-repo coordination stance also bounds the framing.
[DEC-022 (methodology-mesh)](../../../.pkit/capabilities/project-management/decisions/DEC-022-methodology-mesh.md)
already establishes that cross-repo work is *detect-don't-enforce* with a
per-change human gate — never a blanket block. A guard that *blocked* cross-repo
mutation would forbid that sanctioned pattern by construction; the right shape is
operator-gated, mesh-compatible.

As project-kit's own architecture-decision record, harness and code-home
specifics are in scope here, unlike the harness-neutral COR-039. Acceptance is
the operator-sign-off gesture per
[PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md); because this
ADR makes a load-bearing claim about a boundary's *absence*, that sign-off was
the foundational-re-authorisation gesture, given before any implementation cites it.

## Decision

**The Claude Code realization of COR-039 is a pkit self-guard: the mutating
program compares the cd-invariant session anchor against the cd-derived mutation
target and operator-gates on divergence. The intent-layer hook adds one honest
Edit/Write catch. Session-root write-scoping is not introduced as a foreign-repo
boundary. The mechanism is an interlock against accidental handoff, not a
security boundary, and its residual gap is declared.** Each point below is
load-bearing.

1. **The pkit self-guard is the honest, reliable lever.** The mutating program —
   the project-management capability scripts and `pkit` — computes the mutation
   target from cwd (the repo `gh`/`git` would act on) and compares it against the
   **session anchor** (`CLAUDE_PROJECT_DIR`). On divergence it **refuses (under
   autonomy) or prompts (interactively)**. This is feasible *because the anchor
   does not move with `cd`*: `cd /B && create-issue` leaves the anchor at A, so
   the comparison sees A-vs-B and gates. The cd-defeat that breaks command-string
   inspection **does not recur one layer down**, because the comparison's anchor
   is the environment variable the harness froze at launch, **not** a second
   cwd-walk that `cd` would redirect. This does **not** contradict
   [ADR-001](ADR-001-project-root-resolution.md)'s cwd-only root resolution:
   ADR-001 governs *ordinary single-repo* root resolution (no `--root`, no env
   side channel) for commands operating within their own tree; a *foreign-repo
   guard* reading the harness session anchor to detect a cross-repo mismatch is a
   distinct concern, layered on top, not a violation of the resolver's contract.
   The purpose-asymmetry is decisive: ADR-001 bars an env var as a root *input*
   precisely because a stale/forgotten variable makes resolution confusing — so
   the anchor here is **never** a root input (the resolver still finds the root
   from cwd, untouched); it is only a **comparand**, and its very stickiness — the
   property ADR-001 distrusted for resolution — is exactly what lets it catch the
   divergence a pure-cwd resolver follows blind. (ADR-001's own Implications even
   contemplate an override layered *ahead of* the resolver as a non-breaking
   extension; this guard is less invasive still — it sits beside the resolver, not
   in it.)

2. **One detectable corner at the intent layer — a small honest catch, not the
   lever.** The PreToolUse hook MAY **prompt** on an `Edit`/`Write` whose
   `tool_input` carries an absolute path under a foreign repo. Edit/Write carry
   the literal target path in their tool input (unlike a bash command, whose
   target is buried in argv the dumb segmenter does not parse —
   [ADR-025](ADR-025-segment-conservative-bash-allow.md)), so this one surface is
   honestly inspectable. It is a small catch covering only the Edit/Write
   surface; it does **not** cover bash / `uv` / `gh`, so it is explicitly **not**
   the lever — the self-guard (point 1) is. Naming it as a corner, not a wall,
   keeps the honesty discipline intact.

3. **Session-root write-scoping is NOT introduced as a foreign-repo boundary.** A
   `filesystem.allowWrite` fence at the session root is **rejected as the
   foreign-repo lever** on macOS: `uv`/`pkit` and `gh` are required exclusions
   running unconfined ([ADR-014](ADR-014-macos-sandbox-platform-stance.md) /
   [ADR-027](ADR-027-required-sandbox-exclusion-auto-apply.md) /
   [ADR-030](ADR-030-gh-exclusion-required-subclass-generalises.md)), so the
   fence would be partial for *exactly* the incident's command class (pm scripts
   via `uv`, and `gh`). Advertising a partial fence as a foreign-repo boundary is
   the believed-but-absent-boundary trap
   ([ADR-004](ADR-004-autonomy-intent-confinement.md) decision point 4). The
   existing confinement is kept for its **existing** purpose (the
   filesystem-confinement dimension of ADR-004); it is **not** repurposed or
   re-advertised here. *(Where a platform genuinely confines the mutating tools —
   e.g. Linux/WSL2 bubblewrap, where `uv`/`gh` run inside the box — write-scoping
   is a legitimate per-platform **reinforcement** of the self-guard: optional,
   additive, never the principle.)*

4. **Operator-gated, not blocked.** On divergence the default is
   **refuse-with-explanation under autonomy / prompt interactively** — never a
   hard deny. An operator who genuinely intends the cross-repo mutation confirms
   and proceeds. This is mesh-compatible: it is the same per-change human gate
   [DEC-022 (methodology-mesh)](../../../.pkit/capabilities/project-management/decisions/DEC-022-methodology-mesh.md)
   already calls for, applied at mutation time, so the sanctioned
   coordinated-cross-repo pattern stays reachable as the confirmed exception.

5. **A discipline-grade interlock, not a security boundary.** The self-guard
   catches the *accidental-handoff* shape — the incident: the methodology's own
   validated path (`create-issue`, `pkit`, the capability scripts) invoked while
   the session is `cd`'d into the wrong repo — reliably, for that path. It does
   **not** stop a determined bypass that routes *around* the methodology: a raw
   `gh -R owner/B ...`, a raw `git -C /B ...`, or `unset CLAUDE_PROJECT_DIR`
   followed by a cwd-walk. Per
   [COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md),
   that residual gap is **declared, not hidden**: the mechanism is reported as an
   interlock against accidental handoff, never as a wall, and the discipline rule
   (COR-039's operational carrier) teaches the boundary on the paths no
   methodology code interposes on.

6. **`decide.py`'s bash-path core is untouched.** The shared decision core
   (`.pkit/permissions/decide.py`) and its bash classification are unchanged; the
   [ADR-002](ADR-002-permission-realizer-ownership.md) /
   [ADR-003](ADR-003-permission-core-code-home.md) same-code invariant (hook and
   `pkit permissions` decide identically from one `decide()`) stands. The only
   hook change is the additive Edit/Write foreign-path prompt (point 2); the
   self-guard (point 1) lives in the mutating program, not the decision core.

## Rationale

**Why the self-guard is the lever and the hook is not.** The honest place to
detect a cross-repo mismatch is the layer that *performs* the mutation and runs
as itself — it holds both facts (the session anchor and the cwd target) and can
compare them. The intent layer holds only a defeasible command string; on a bash
command the target is in argv the dumb segmenter does not parse
([ADR-025](ADR-025-segment-conservative-bash-allow.md)). Putting the check where
both facts are in hand avoids relying on a layer the platform has already shown
cannot carry it.

**Why the cd-invariance is the whole feasibility argument.** A naive guard that
re-derived "the repo this session belongs to" with a second cwd-walk would be
defeated by the same `cd` that caused the incident — the walk would resolve B
just as `gh` does, and the comparison would be B-vs-B (no mismatch seen). The
self-guard escapes this *only* because `CLAUDE_PROJECT_DIR` is frozen at session
launch and is immune to `cd`. The anchor is the one signal in the system that
still points at A after `cd /B`. That is why the lever is the env var, not a
filesystem resolution — and why the cd-defeat does not recur one layer down.

**Why write-scoping is not the foreign-repo boundary.** A fence that does not
bound the very commands that performed the incident (pm scripts via `uv`, `gh`)
is partial for the case it would be advertised to cover. A partial boundary sold
as whole is worse than none: the operator stops watching, trusting a wall that
leaks for exactly the command class at issue. The platform genuinely cannot
supply this fence on macOS for these tools (they are forced exclusions —
[ADR-030](ADR-030-gh-exclusion-required-subclass-generalises.md)), so the honest
artifact is the program-level self-guard, not a fence claim. Where the platform
*does* confine these tools, write-scoping is a fine reinforcement — but it
reinforces; it is not the principle.

**Why operator-gated, not blocked.** A blanket block would make legitimate
coordinated cross-repo work illegal by construction, contradicting
[DEC-022](../../../.pkit/capabilities/project-management/decisions/DEC-022-methodology-mesh.md)'s
detect-don't-enforce stance. The blast-radius-aware response to a cross-repo
write is a per-change human decision; an operator-gated exception *is* that gate,
applied at mutation time. Surfacing-and-confirming kills the silent path while
preserving the deliberate one.

**Why honest-about-reach, not a claimed wall.** The mechanism reliably catches
the realistic mistake — the accidental handoff through the methodology's own
path — and that is a real, recurring failure worth an interlock. But a guard sold
as stopping *any* cross-repo mutation would be a lie: raw tool invocations and
`unset CLAUDE_PROJECT_DIR` route around it. Declaring the interlock as an
interlock and naming the residual gap is the only stance
[COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md)
permits, and it is why this ADR carries an operator sign-off gate — it makes a
load-bearing claim about what is *not* protected.

### Alternatives considered

- **Enforce in the intent/permission hook (deny a foreign-target command).**
  Rejected as the lever — command inspection is defeated by `cd` and
  absolute/relative path redirection, and on bash the target lives in argv the
  dumb segmenter does not parse ([ADR-025](ADR-025-segment-conservative-bash-allow.md)).
  The hook keeps only the one honestly-inspectable corner (Edit/Write absolute
  foreign path, point 2), as a prompt, not a deny.

- **Session-root `filesystem.allowWrite` fence as the foreign-repo boundary.**
  Rejected on macOS — `uv`/`pkit` and `gh` run unconfined as required exclusions
  ([ADR-014](ADR-014-macos-sandbox-platform-stance.md) /
  [ADR-030](ADR-030-gh-exclusion-required-subclass-generalises.md)), so the fence
  is partial for exactly the incident's command class; advertising it as the
  boundary is the believed-but-absent-boundary trap
  ([ADR-004](ADR-004-autonomy-intent-confinement.md) decision point 4). Retained
  as an optional per-platform reinforcement where the box *does* confine those
  tools.

- **Re-derive the session's home repo with a second cwd-walk and compare.**
  Rejected — defeated by the same `cd` that caused the incident: the walk
  resolves B, the comparison is B-vs-B, no mismatch is seen. The cd-invariant
  anchor (`CLAUDE_PROJECT_DIR`) is the only signal that survives `cd`, so it must
  be the comparison's anchor.

- **Block cross-repo mutation outright (hard deny on divergence).** Rejected —
  forbids the sanctioned coordinated-cross-repo pattern
  ([DEC-022](../../../.pkit/capabilities/project-management/decisions/DEC-022-methodology-mesh.md))
  by construction. The right shape is the per-change operator gate, not a wall.

- **Modify `decide.py`'s bash classification to detect foreign targets.**
  Rejected — it would import target-parsing into the fail-open, dumb-segmenter
  decision core, the exact altitude
  [ADR-025](ADR-025-segment-conservative-bash-allow.md) refused a shell parser
  at, and would break nothing useful (the cd-escape still defeats it). The
  self-guard at the mutating program is where both facts are in hand.

## Implications

- **Foundational re-authorisation flag (escalation).** This ADR makes a
  load-bearing claim about a boundary's **absence** — the interlock is *not* a
  security boundary, and session-root write-scoping is *not* advertised as a
  foreign-repo wall. Because a future reader could mistake the interlock for a
  wall and stop watching, the absence-claim is itself the load-bearing decision
  and requires **operator sign-off**: the sign-off gesture is what flips this
  record from `proposed` to `accepted` per the
  [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md) acceptance
  gate. This is the same class of flag
  [ADR-030](ADR-030-gh-exclusion-required-subclass-generalises.md) carried.

- **The self-guard is a single extracted check, not a per-script
  reimplementation** ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)):
  "is the repo I am about to mutate the one this session is anchored to?" is
  computed once at the mutation seam (the capability scripts' shared lib /
  `pkit`), not re-derived in every mutating script. The anchor read
  (`CLAUDE_PROJECT_DIR`, with the script-position fallback already in
  `_target_root()`) and the target read (cwd's git remote) are the two inputs;
  the comparison and the gate are the extracted unit.

- **`decide.py` untouched; same-code invariant stands.** The shared decision core
  and its bash path are unchanged
  ([ADR-002](ADR-002-permission-realizer-ownership.md) /
  [ADR-003](ADR-003-permission-core-code-home.md)). The only hook-side change is
  the additive Edit/Write foreign-path prompt; the self-guard lives in the
  mutating program. The fail-open hook + fail-closed native double-lock and the
  speed-bump-not-boundary posture of
  [ADR-004](ADR-004-autonomy-intent-confinement.md) /
  [ADR-019](ADR-019-enforcement-gate-mechanism-vs-boundary.md) are unaffected.

- **Honesty discipline governs the realization**
  ([COR-028](../../../.pkit/decisions/core/COR-028-permission-model-realization.md)):
  the mechanism is reported as an interlock against accidental handoff, never as
  a wall; the residual gap (a determined bypass routing around the methodology —
  raw `gh -R`, raw `git -C`, `unset CLAUDE_PROJECT_DIR`) is stated in the apply /
  status surfaces and in the operational discipline rule (COR-039's rule
  carrier), not hidden.

- **Mesh-compatible by construction.** The operator-gated framing is the same
  per-change human gate
  [DEC-022](../../../.pkit/capabilities/project-management/decisions/DEC-022-methodology-mesh.md)
  already calls for; a genuine cross-repo mutation is the confirmed exception, so
  the cross-repo-write generalisation stays reachable rather than forbidden.

- **Cross-platform / cross-harness.** The self-guard is the portable core — any
  harness that supplies a cd-invariant session anchor (Claude Code's
  `CLAUDE_PROJECT_DIR` here; another adapter names its own) can carry it. The
  Edit/Write hook corner is Claude-Code-specific (it depends on the harness's
  tool-input shape). The write-scoping reinforcement is per-platform (it applies
  only where the box confines the mutating tools — e.g. Linux/WSL2 bubblewrap,
  not macOS). Each future adapter declares its own anchor signal and its own
  residual gap.

- **Forward-pointers, not amendments.** This ADR cites but does **not** amend:
  [ADR-004](ADR-004-autonomy-intent-confinement.md) decision point 4 (the
  believed-but-absent-boundary trap — forward-pointed, not re-litigated),
  [ADR-025](ADR-025-segment-conservative-bash-allow.md) (why the hook cannot
  carry the bash case), [ADR-014](ADR-014-macos-sandbox-platform-stance.md) /
  [ADR-027](ADR-027-required-sandbox-exclusion-auto-apply.md) /
  [ADR-030](ADR-030-gh-exclusion-required-subclass-generalises.md) (the macOS
  required exclusions that make write-scoping partial),
  [ADR-001](ADR-001-project-root-resolution.md) (ordinary cwd root resolution —
  distinct concern, not contradicted),
  [DEC-022](../../../.pkit/capabilities/project-management/decisions/DEC-022-methodology-mesh.md)
  (operator-gated cross-repo), and
  [COR-039](../../../.pkit/decisions/core/COR-039-session-repo-mutation-boundary.md)
  (the principle this realizes).

- **Implementation is separate follow-on work, not this ADR.** This record
  specifies the *contract* — the self-guard's anchor-vs-target comparison, the
  operator-gate behaviour, the Edit/Write hook corner, the not-a-boundary
  declaration. The self-guard code (the extracted check in the capability lib /
  `pkit`, the hook's Edit/Write prompt, the status/apply surfacing of the
  residual gap) lands in the implementing issue. This ADR sanctions building it
  on acceptance.

- **Versioning + migration.** This change-set authors the ADR record only (no
  behaviour); no version bump here. The eventual implementation is a
  behaviour-observable surface change (a new operator-gate on cross-repo
  mutation) → it bumps `.pkit/VERSION` per
  [PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md) when
  it lands. Whether the self-guard's introduction warrants a migration is a
  [COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md) judgement
  for the implementing change (it is additive — a new gate, not a rename/removal
  — so likely migration-clean); `pkit migrations check-diff
  --include-working-tree --base main` gates it. The ADR file itself is
  migration-clean.
