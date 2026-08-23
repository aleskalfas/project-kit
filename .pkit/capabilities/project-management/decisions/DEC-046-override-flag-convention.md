---
id: DEC-046
title: Override-flag convention — `--bypass` for bypassable gates, `--force` for firm stops
status: accepted
date: 2026-08-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the capability's mutating commands offer two families of
override flag, and which one a command exposes — and why — was never written down,
so it looked like drift and a new command had no rule to follow. This record states
the rule and, as the load-bearing part, **amends
[project-management:DEC-014-validation-severity-model] to say out loud what the code
already does: a `hard-reject` can be overridden by the operator with `--force`.**
The rule, one question — *is the stop a `bypassable-with-audit` gate?*:

- **`--bypass[-<gate>]`** overrides a gate the severity model *designed* to be
  bypassable (DEC-014's `bypassable-with-audit`): a required, audited reason, using
  the gate's own escape valve.
- **`--force`** overrides a **`hard-reject` finding** *or* a **hard script
  precondition** — a stop the methodology treats as firm. Boolean; audited where the
  substrate can carry the audit.

The per-command roster of which flag lives where is a table in the capability
README, not this record; this record fixes the *rule* that populates it.

## Context

Two override families run across the capability's mutating commands, and the split
between them was never stated, so three things looked wrong at once:

- **It read as drift.** The help text had genuinely drifted — `edit-issue`'s
  `--force` called itself "the DEC-014 bypassable-with-audit pattern" (the mechanism
  it is *not* using), and `remove-workstream`'s `--force` help used the *bypass* verb
  on the *force* flag. A new command adding an override had no rule to pick by.
- **A hard-reject can already be `--force`d, but DEC-014 says it can't.** `--force`
  on the body-validation commands overrides a `hard-reject` and *proceeds*, while
  DEC-014's schema sets `bypassable: false` and says the operation "never proceeds" —
  a **machine-consumed field an agent dispatches on that is factually untrue** for
  those findings.
- **Not every `--force` stop is a DEC-014 finding.** Some `--force` sites guard a
  *script-level precondition* (a milestone with open children; a workstream label
  still carrying issues) that appears nowhere in the severity model — so "read the
  gate's severity" has nothing to read there.

Issue #570 chose to **document the rule** rather than unify the two names into one
(a breaking rename across the command surface plus a COR-010 migration, flattening a
real distinction). Documenting it honestly requires amending DEC-014, not narrating
around it.

## Decision

**A mutating command's override flag is chosen by the stop it overrides, per the
rule below; and DEC-014's `hard-reject` is amended to carry an operator-`--force`
override.**

**1. `--bypass[-<gate>]` — the sanctioned override of a `bypassable-with-audit`
gate.** Where a gate is `bypassable-with-audit`, the override is a **`--bypass`
family** flag carrying a **required reason** (inline or a paired `--bypass-reason`)
and the DEC-014 audit comment, posted *before* the mutation. A command with one
bypassable gate spells it `--bypass`; a command with **several** (the CI-status gate
alongside an approval gate is the live case) **qualifies each** — `--bypass` for the
primary, `--bypass-<gate>` for the rest — so overriding one gate never silently
clears another.

**2. `--force` — the operator's override of a `hard-reject` finding or a hard
precondition.** Boolean. It covers **two** firm stops: a DEC-014 `hard-reject`
*finding*, and a **script-level precondition** the methodology treats as firm but
which is *not* a DEC-014 finding. It leaves a durable audit trail **where the
substrate can carry one** — an issue or PR comment, a milestone's description — and,
where the substrate has no annotation surface (a bare label), surfaces the override
in the command output instead. Audit is **substrate-conditional**, not universal.

**3. The discriminator, and where it is mechanical vs a judgement.** *Is the stop a
`bypassable-with-audit` gate?* → `--bypass[-<gate>]`. *A `hard-reject` finding or a
hard precondition?* → `--force`. For a **DEC-014 finding** this is mechanical —
resolve the finding's severity, read off the flag. For a **script precondition**
there is no severity token; it is a firm-stop-by-construction and takes `--force` by
this rule. The record does not pretend the precondition branch is a severity read —
it is the one place the choice is by construction, not by a checkable field.

**4. Amend DEC-014 — a `hard-reject` is operator-`--force`-overridable (out of
band).** DEC-014's `hard-reject` keeps **`bypassable: false`** — there is no in-band,
reason-based `--bypass` for it, and that is correct. What is added, openly, is that a
hard-reject additionally carries an **out-of-band operator `--force` override**,
audited where the substrate allows. This lands two ways in the same change-set: a
reciprocal note on the DEC-014 *record*, and a **`force_overridable: true`** field on
the `hard-reject` entry in `validation-severity.yaml`, so an agent dispatching on the
severity token sees an override *does* exist (the prior state — `bypassable: false`
with no other signal — mislead it into "no override"). Behaviour is unchanged; only
the model is made honest. This **refines** DEC-014 (its hard-reject definition gains a
second override layer); it does not supersede it — `bypassable`, `aborts_operation`,
and the `--bypass` semantics all stand.

## Rationale

**Why document rather than unify the two names.** The split tracks a real
distinction — *use a gate's designed escape valve* (`--bypass`) versus *force past a
firm stop* (`--force`). Two names for two acts beats one name that erases the
difference; unifying is a breaking rename across the command surface plus a COR-010
migration that flattens the signal, for negative information value. **Honest
caveat:** the split was *not* clean-all-along-merely-undocumented — the precondition
sites never had a severity and the help text had drifted. So this record *imposes*
the rule and *corrects* those sites; it does not transcribe a pre-existing clean one.

**Why amend DEC-014 openly instead of narrating around it.** `--force` over a
hard-reject is real and shipping; DEC-014's machine-consumed `bypassable: false`,
with no other signal, tells an agent no override exists while the CLI offers one. A
"nothing changed" note would preserve that falsehood. Adding `force_overridable:
true` and saying so is the honest fix, and it costs no behaviour change (the `--force`
overrides already exist).

**Why `--force`'s audit is substrate-conditional.** A hard-reject or precondition is
a *firmer* stop than a bypassable gate, so `--force` carries at least as strong an
audit obligation — but the obligation is "leave a durable trace on the substrate that
has one," not "always post a comment." A bare label has no comment thread; demanding
a universal comment would force inventing an annotation surface where none exists.

### Alternatives considered

- **Unify to one flag with a rename migration.** Rejected — a breaking rename across
  the command surface plus a migration, flattening a real distinction.
- **Re-tag the body-validation findings as `bypassable-with-audit`** (so their
  override becomes `--bypass`). Rejected — it *reverses* DEC-014's deliberate call
  that those findings are hard-reject ("violation would corrupt downstream logic") and
  is a behaviour change (rename the flag, now require a reason). The chosen path keeps
  behaviour and DEC-014's severity call intact.
- **Introduce a distinct "operator-precondition / firm-stop" severity class.**
  Rejected — the hard-reject-finding-vs-script-precondition distinction (point 2)
  captures the two `--force` domains without a new token; a fourth class is model
  weight for little gain, and DEC-014 already declined a different fourth class.
- **Name the rule "authorisation vs conformance".** Kept as the *mnemonic*, not the
  normative discriminator — for findings the DEC-014 severity is the checkable ground
  truth; the authorisation/conformance reading is the intuition, not the rule.

## Implications

- **DEC-014 is amended in the same change-set** — a reciprocal note on the record and
  a `force_overridable: true` field on the `hard-reject` entry in
  `validation-severity.yaml` (+ its companion, additively — an optional field, no
  `schema_version` bump, so no COR-010 migration). **Because this refines DEC-014's
  severity model, its acceptance carries maintainer sign-off.**
- **Help text on every override flag must name the stop it overrides and the
  mechanism it uses** — a `--force` flag must not describe itself as the
  bypassable-with-audit pattern, and a `--bypass` flag names the bypassable gate it
  clears. (The drifted `edit-issue` / `remove-workstream` strings are corrected in
  this change-set.)
- **The per-command roster lives in the capability README**, not this record — the
  DEC holds the discriminator, the README holds the table of which command exposes
  which flag (including the out-of-scope note that a `gh`-passthrough like
  `--admin` is not a methodology override). A new command picks its flag by the
  discriminator and is added to the README table, not here.
- **No behaviour change / no migration.** No flag is renamed, no gate changes
  severity; the schema field is additive. Version impact is the adopter's
  docs/wording bump policy.

## Amendment (2026-08-21) — parameterised bypass member (DEC-050)

[project-management:DEC-050] extends this family with a **parameterised, repeatable** member: `done-work --bypass-reviewer <name> --bypass-reason "<r>"`, a per-reviewer override of the approval gate. This is the one shape this record did not contemplate — its `--bypass[-<gate>]` suffix was a *fixed* gate name, whereas `--bypass-reviewer`'s target is a reviewer-name *parameter*. It remains a member of the `--bypass` family (audited, reason-required, bypassable-with-audit), not a new `--override-*` verb — the convention holds; only the suffix gains a parameterised form.
