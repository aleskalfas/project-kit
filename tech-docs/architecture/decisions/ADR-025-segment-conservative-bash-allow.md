---
id: ADR-025
title: Segment-conservative compound Bash auto-approve
status: accepted
date: 2026-06-24
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

A compound Bash command (`cd src && gh pr list`) reaches the permission
decision core as one string, and today the leading `cd src &&` prefix can keep
an otherwise-already-granted command (`gh pr list`) from auto-approving — a
*prompt over intent the model already grants*. This ADR makes the decision core
**conservatively** reduce that prompt: Phase 1 strips a single leading
`cd <path> &&` / `cd <path> ;` and decides on the remainder. It is a
prompt-reduction over already-granted intent, **never a new grant**, and it
inherits [ADR-004](ADR-004-autonomy-intent-confinement.md)'s
fail-closed-on-uncertainty stance wholesale: any segment the dumb splitter
cannot trust — a quote, `$()`, a backtick, a redirection (`<` / `>`), or an
unrecognized command — makes the core **abstain (prompt)**, never auto-allow.

**Decision in one line:** the core auto-approves a compound only by stripping a
leading `cd` and matching the remainder against existing grants; a general
"auto-approve any all-segments-safe compound" widening is **rejected as unsound**
and any broader widening is **deferred** under
[COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md) until a
demonstrated residual-prompt need earns it.

This is a **refinement child of [ADR-004](ADR-004-autonomy-intent-confinement.md)**,
not a supersession: the intent/confinement split, the fail-open hook + fail-closed
native double-lock, and the deny-side posture are all unchanged. Critically, the
deny side stays **porous** — this change does **not** promote the speed-bump to a
boundary. A future reader must not misread a tighter allow path as a hardened deny
path; the deny layer remains the speed-bump
[ADR-004](ADR-004-autonomy-intent-confinement.md) and
[ADR-019](ADR-019-enforcement-gate-mechanism-vs-boundary.md) describe.

## Context

The forcing question (issue #239, with a `critic` + `architect` review pass
behind it) is whether the permission decision core can stop prompting on a
compound Bash command whose *only* obstacle is a leading directory change. The
shared core (`.pkit/permissions/decide.py`) already segments a compound on
`&&` / `||` / `|` / `;` and strips a leading `export` / `VAR=` env prefix per
segment (the `segments()` helper fixed the `export GH_HOST=x && gh pr list`
false-prompt). It does **not** strip a leading `cd <path>`, so
`cd src && gh pr list` — where `gh pr list` is already granted — still prompts.

The decision core is harness-neutral, propagated, and imported by **both** the
claude-code PreToolUse hook (which runs in the adopter tree at decision time,
under bare `python3` inside the macOS Seatbelt box per
[ADR-014](ADR-014-macos-sandbox-platform-stance.md)) and the `pkit permissions`
CLI. [ADR-002](ADR-002-permission-realizer-ownership.md) /
[ADR-003](ADR-003-permission-core-code-home.md) pin the **same-code invariant**:
hook and CLI must decide identically from one `decide()`. So any change to how a
compound is classified lives in that one neutral core, never in the adapter hook
— otherwise the two callers diverge.

This sits squarely inside [ADR-004](ADR-004-autonomy-intent-confinement.md)'s
intent axis. The hook inspects a command string; it cannot confine a shell
(`cd` / absolute-path escapes defeat any cwd check — ADR-004's "directory-scoped
bash grant is security theater"). That is precisely why the deny side is a
speed-bump, not a boundary, and why this ADR must not let a tighter allow path
read as a hardened deny path. The operational rule the change supports is
core.md rule 15 — *issue the narrowest action the layer can vet*: a single
`cd && <granted-cmd>` is a narrow, vettable action, and reducing its false prompt
is the rule's intent applied to the hot path.

As project-kit's own architecture-decision record, harness and code-home
specifics are in scope here, unlike the harness-neutral COR. `status: proposed`
is the acceptance-gate gesture; because this is a child of foundational ADR-004,
accept it before any implementation cites it.

## Decision

**The decision core auto-approves a compound Bash command *conservatively*: it
strips a single leading `cd <path>` segment and decides on the remainder against
the existing grant model. It is a prompt-reduction over already-granted intent,
never a new grant. Every uncertainty fails closed (abstain / prompt), never to
auto-allow. A general all-segments-allowed widening is deferred, not taken.**

1. **Phase 1 — strip a leading `cd`, decide on the remainder.** When the first
   segment of a compound is a bare `cd <path>` (no quotes, no substitution, no
   redirection), the core drops it and evaluates the remaining command against the
   grant model exactly as if it had been issued alone. `cd src && gh pr list` with
   `gh pr list` granted auto-approves; `cd src && rm -rf /` does not (the remainder
   matches no allow and, for guardrail denies, the deny still binds). The strip is
   the *only* widening this ADR makes.

2. **Inherited fail-closed-on-uncertainty (ADR-004 decision point 4),
   non-negotiable.** Any segment the dumb splitter cannot trust — a quote, a `$()`
   command substitution, a backtick, a `<` / `>` / redirection, or an unrecognized
   command — makes the core **abstain (prompt)**. It NEVER auto-allows under
   uncertainty. The splitter stays dumb; the conservatism lives in the
   classification, not in smarter parsing.

3. **No shell parser.** The core keeps its dumb regex segmenter (`_SEP`). A real
   shell parser is **rejected on altitude grounds**: the hook runs bare `python3`
   in-sandbox ([ADR-014](ADR-014-macos-sandbox-platform-stance.md)), and importing
   an adversarial-input parser into a fail-open, security-adjacent component trades
   a bounded, auditable splitter for parsing fragility in the worst place to host
   it. Conservatism is achieved by abstaining on anything the dumb splitter cannot
   trust, not by parsing harder.

4. **Code home — the shared neutral core, not the adapter hook.** The change
   lands in `.pkit/permissions/decide.py` (`segments()` / classification), the
   single neutral core both the hook and `pkit permissions` import. This preserves
   the [ADR-002](ADR-002-permission-realizer-ownership.md) /
   [ADR-003](ADR-003-permission-core-code-home.md) same-code invariant — one
   `decide()`, identical decisions — and is covered by the existing conformance
   fixtures.

5. **The deny side is unchanged and remains porous.** This ADR touches only the
   *allow* path's prompt-reduction. The deny side — guardrail denies, the fail-open
   hook + fail-closed native double-lock — is untouched, and the merge layer / hook
   remains a **speed-bump, not a boundary**
   ([ADR-004](ADR-004-autonomy-intent-confinement.md),
   [ADR-019](ADR-019-enforcement-gate-mechanism-vs-boundary.md)). A reader must not
   read a tighter allow path as a hardened deny path. Real confinement is still the
   OS sandbox; real merge enforcement is still adopter-wired CI.

6. **The broader widening is deferred per COR-007.** A general
   "auto-approve any compound whose every segment is independently safe" is **not**
   taken (and is rejected outright as unsound — see Rationale). Any widening beyond
   the leading-`cd` strip is gated on a *demonstrated residual-prompt need* — the
   [COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md) recurrence
   test, not speculative generality.

## Rationale

**Why the leading-`cd` strip is safe and the only widening taken.** `cd <path>`
changes nothing about *what* the remainder may invoke — it changes only the cwd,
which the intent layer already does not confine (a granted `gh pr list` is
granted regardless of cwd). Stripping it therefore reveals the intent that was
always there; it grants nothing new. It is the minimal, surgical reduction of a
false prompt, and it composes with the existing env-prefix strip the same way.

**Why "auto-approve any all-segments-safe compound" is rejected as unsound.** A
per-segment matcher sees pieces, not the whole. Safe pieces compose into unsafe
wholes the matcher cannot see: a redirection target turns a benign `echo` into a
file write (`echo x > ~/.ssh/authorized_keys`); `$(...)` and backticks smuggle a
second command inside a "safe" one; `| sh` pipes arbitrary text into a shell;
`find -exec` and `bash -c` carry a payload the segment matcher never inspects.
An all-segments-allowed rule would auto-approve every one of these. The
per-segment view is structurally blind to composition, so the general widening
is not merely deferred for sequencing — it is *unsound* and must not be built as
stated. (Surfaced by the `critic` pass.)

**Why no shell parser (altitude).** The hook is fail-open and runs under bare
`python3` inside Seatbelt (ADR-014). A shell parser is an adversarial-input
parser; hosting one in a fail-open, security-adjacent, dependency-constrained
component imports parsing fragility exactly where a parse bug becomes a silent
auto-allow. The dumb splitter's failure mode is the *safe* one — it abstains on
anything it does not understand. Keeping it dumb and pushing all conservatism
into "abstain when unsure" is the honest stance at this altitude.

**Why this is a refinement of ADR-004, not a supersession.** ADR-004's model —
intent × confinement, the double-lock, the speed-bump-not-boundary posture, and
decision point 4's fail-closed-on-uncertainty — is unchanged and is *inherited*
here. This ADR only refines how the intent axis classifies one shape of compound
command, tightening a false prompt while obeying ADR-004's invariants. It adds no
new ownership tier and changes no prior decision.

### Alternatives considered

- **Auto-approve any compound whose every segment is independently safe.**
  Rejected as **unsound** (not merely deferred): a per-segment matcher is blind to
  composition. Redirection targets (`echo x > ~/.ssh/...`), `$(...)` / backticks,
  `| sh`, and `find -exec` / `bash -c` compose safe pieces into unsafe wholes the
  matcher cannot see, so the rule would auto-approve clear exfil/escalation. The
  leading-`cd` strip is the only widening that is sound at the per-segment view.

- **A real shell parser in the decision core.** Rejected on altitude grounds —
  the hook runs bare `python3` in-sandbox (ADR-014) and is fail-open; an
  adversarial-input parser there trades a bounded, abstain-on-doubt splitter for
  parsing fragility in a security-adjacent component. The dumb splitter stays;
  conservatism lives in the classification.

- **Coaching-reject: bounce a compound back to the agent to re-issue as a single
  granted command** (enforcing core.md rule 15's "narrowest action" directly).
  Considered and **deferred** as a Phase-2 alternative. It has merit — it teaches
  the agent the narrow-action habit rather than silently accommodating compounds —
  but it changes the interaction shape (a reject-with-guidance, not a silent
  allow) and is gated on the same demonstrated-need test as the broader widening.

- **Implement the change in the adapter hook rather than the shared core.**
  Rejected — it would break the ADR-002 / ADR-003 same-code invariant, letting the
  hook and `pkit permissions` diverge on identical compounds. The change lands in
  the one neutral `decide()` both callers import.

## Implications

- **The change lands in `.pkit/permissions/decide.py`** (the `segments()` /
  classification path), the shared neutral core, and is covered by the existing
  conformance fixtures proving hook and CLI decide identically. Implementation is
  the issue-#240 follow-on, not this ADR.

- **Deny side untouched; speed-bump posture preserved.** Guardrail denies, the
  fail-open hook + fail-closed native double-lock, and the
  speed-bump-not-boundary framing of ADR-004 / ADR-019 are unchanged. The deny
  side remains porous by design; this ADR narrows only the allow path's false
  prompts.

- **The broader widening is gated, not scheduled.** Any auto-approve beyond the
  leading-`cd` strip requires a demonstrated residual-prompt need (COR-007), and
  the all-segments-safe variant is recorded as unsound — a future author must not
  resurrect it as stated.

- **Supersedes nothing; child of ADR-004.** No prior decision changes. This ADR
  refines ADR-004's intent-axis classification and inherits its fail-closed,
  double-lock, and speed-bump invariants intact.

- **No migration.** No file/directory rename or removal in a kit-owned tree, no
  `schema_version` bump, no breaking CLI signature change, no capability-subtree
  restructure — `pkit migrations check-diff --include-working-tree --base main`
  is expected clean. This change authors the ADR file only; the eventual code
  change is behaviour-preserving-for-deny and additive-for-allow.

- **No version bump in this change-set.** Like the sibling permission ADRs, this
  authors the ADR file at `status: proposed`; the acceptance-gate flip and the
  eventual implementation's surface bump are separate lifecycle gestures.
