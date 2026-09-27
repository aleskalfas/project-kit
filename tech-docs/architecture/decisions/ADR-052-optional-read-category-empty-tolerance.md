---
id: ADR-052
title: An optional overlay read category tolerates absence structurally — patterns-only reference deploys the agent without it
status: accepted
date: 2026-08-25
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

An agent that only *reads* an adopter overlay category — where the corpus being
absent is a normal early state — must still deploy when that category is
undefined, and must receive the resolved path when it *is* defined. The overlay
resolver did neither: it failed the whole deploy on any undefined
angle-bracket placeholder, so the `software-engineering` agents dodged the
failure by writing the category as a **bare literal** (`project-conventions`,
no brackets) — which silently dodged substitution and discovery too. The corpus
path never reached the deployed agent even when the adopter configured it, and
`pkit agents reconcile` reported "complete" for a category it could not see.

This record fixes the seam by making tolerance **structural**: a category an
agent references **only** through `reads.patterns` (never `owns` / `needs` /
`answers` / `reads.paths` / `reads.records`) is an **optional read** — undefined
resolves to *dropped item, agent deploys*; defined resolves to *the path,
substituted in*. `reads.patterns` becomes the designated optional read channel;
`reads.paths` and `reads.records` stay hard reads. The agents return to the
angle-bracket form ADR-013 D1 always specified. Nothing names
`project-conventions` in backbone code — the property is inferred from the
reference site, so any capability's read-only category inherits it for free.
This composes ADR-013 and ADR-051; it is not a new principle, so an ADR, not a
COR.

## Context

ADR-013 fixed the conventions-discovery seam: an agent reads a project's
conventions through the overlay-resolved `<project-conventions>` category, and
an empty or absent corpus is a **normal early state, not an error** (ADR-013 D1,
Implications). ADR-051 fixed the *write* twin: a core agent's `owns:` carries an
overlay category placeholder, and a category tolerant of absence ships as an
explicit `[]` so the agent deploys **inert** rather than being skipped.

Between them sat an unhandled case the `software-engineering` capability walked
straight into. Its four agents (`software-engineer` and the three-agent
code-review panel) *read* `<project-conventions>` and nothing else through it —
no `owns:` entry, because they do not write the corpus (ADR-013 D2: no capability
owns it). At the time they were authored, the deploy resolver had exactly one
behaviour for an undefined angle-bracket placeholder: fail the deploy loudly and
skip the agent. That is correct for a *hard* reference and correct for a
*write-carrying* one under ADR-051's explicit-`[]` opt-in — but wrong for an
*optional read*, where undefined is the expected early state and skipping the
agent is the opposite of what ADR-013 D1 promised.

The authoring-time workaround was to drop the angle brackets: declare
`reads.patterns: [project-conventions]` as a **bare literal**. That sidestepped
the deploy failure — and, because the resolver and the backbone scanner both
substitute and detect *only* angle-bracket items, it sidestepped three things at
once:

1. **Delivery.** The bare literal falls through the resolver's pass-through
   branch untouched, so the deployed frontmatter carries the inert token
   `project-conventions`, never the adopter's resolved path — even when the
   overlay defines it. The agent has no machine-delivered corpus location; it
   runs the generalist fallback unconditionally.
2. **Discovery.** The scanner never sees the category, so `pkit agents
   reconcile` reports "overlay is complete" and cannot stub it — contradicting
   ADR-013 Implications and the capability's own README.
3. **Its own contract.** ADR-013 D1 specifies the consumer declares
   `<project-conventions>` — angle-bracket — in `reads.patterns`. The shipped
   agents violate the ADR they stand on.

The scanner and resolver are mirror-guarded (a parity test), so both stayed
consistently wrong. This record supplies the missing behaviour so the agents can
return to the form ADR-013 D1 always specified.

## Decision

**A category an agent references *only* through `reads.patterns` — and never
through `owns`, `needs`, `answers`, `reads.paths`, or `reads.records` — is an
*optional read*. At deploy time an undefined optional read resolves to a dropped
list item and the agent deploys; a defined one resolves to its path, substituted
into the deployed frontmatter as for any placeholder. `reads.patterns` is
therefore the designated *optional* read channel; `reads.paths` and
`reads.records` remain *hard* reads. Tolerance is inferred structurally from the
reference site — no backbone constant names the tolerant category.**

1. **`reads.patterns` is the optional read channel; `reads.paths` /
   `reads.records` are hard.** An undefined `<cat>` in `reads.paths` or
   `reads.records`, or in any list key (`owns` / `needs` / `answers`), still
   fails the deploy loudly and skips the agent — unchanged. Only `reads.patterns`
   gains the tolerant behaviour. Authors get a clean lever: a required read goes
   in `reads.paths`, an optional/corpus read goes in `reads.patterns`.

2. **"Optional" is per-agent and structural: patterns-only, absent-from-hard.**
   A category is optional *for an agent* iff it appears as an angle-bracket
   placeholder under that agent's `reads.patterns` and as a placeholder under
   *none* of its hard keys. A category that appears in both `reads.patterns` and,
   say, `owns:` is *hard* — the hard reference wins. This keeps the ADR-051
   write-carrying categories (`process-authoring-targets`, carried in `owns:`)
   hard, even where an agent also lists the bare name in `reads.patterns` as a
   label.

3. **Undefined optional resolves to a dropped item; the agent deploys.** Where a
   hard undefined placeholder makes the resolver exit non-zero, an optional
   undefined placeholder is simply omitted from the resolved list — the deployed
   `reads.patterns` may shrink to `[]`. This restores ADR-013 D1's zero-config
   empty-is-normal without an overlay entry of any kind. It is deliberately
   *unlike* ADR-051's inert-deploy, which requires an explicit `[]` in the
   overlay as its auditable opt-in gesture: an optional read needs no gesture,
   because tolerating a missing read is the safe default, not a granted
   authority.

4. **No backbone constant names the tolerant category.** Unlike ADR-051's
   `WRITE_CARRYING_CATEGORIES` allowlist — legitimate because it names a
   *core-introduced* write category with deliberate, auditable opt-in — read
   optionality is derived from the reference site alone. The backbone never
   learns `project-conventions` (or any capability's read category). This is the
   maximal expression of ADR-013 D2 ("owned by no single capability") and of
   COR-014 universal applicability: any capability's read-only category inherits
   the behaviour with zero backbone edits.

5. **The scanner mirrors the resolver's channel split.** The backbone's
   reference-detection and deploy-readiness view classify a patterns-only
   category as optional exactly as the resolver treats it: an agent whose *only*
   undefined categories are optional is **deployable**, not skipped;
   `pkit agents reconcile` still *surfaces* the optional category (so an adopter
   can define it to enrich the agent) but frames it as optional — "the agent
   already deploys without this" — never as a blocker. The existing parity guard
   is extended to pin the channel split across the two implementations.

6. **The agents return to the angle-bracket form.** `software-engineer`,
   `code-reviewer`, `security-reviewer`, and `docs-reviewer` declare
   `reads.patterns: [<project-conventions>]` — the form ADR-013 D1 specified —
   and now receive the resolved path when the adopter defines it, and deploy
   cleanly (as generalists) when they do not.

## Rationale

**Why structural, not an allowlist.** The write and read cases share a surface
shape — "a referenced category tolerant of absence" — but their safe-default
directions are opposite. A granted *write* must be a deliberate, auditable opt-in
(ADR-051's explicit `[]`), so a positive allowlist keyed on the category name is
right: silence means *not* granted. A missing *read* must be tolerated by
default (ADR-013: empty-is-normal), so an allowlist is exactly wrong: it would
make the next capability's read category skip the agent until someone remembered
to register it — the failure a structural rule cannot have. Inferring tolerance
from the reference site (`reads.patterns`) makes the safe behaviour automatic and
capability-independent.

**Why a new class beside `WRITE_CARRYING_CATEGORIES`, not a generalization of
it (COR-007).** Folding the two into one "tolerant category" concept would force
a regression on one side: either optional reads would require an overlay `[]` to
deploy (breaking ADR-013's zero-config empty-is-normal), or write categories
would deploy without their explicit grant (breaking ADR-051's auditable opt-in).
The recurrence COR-007 rewards extracting is the reconcile *plumbing*
(bucket-partition, block-append writer, the shared `.pkit/lifecycle/ownership.py`
home) — which this reuses. The *policy* is genuinely two concerns; unifying them
would be a false abstraction.

**Why `reads.patterns` is the right channel.** The `paths` / `records` /
`patterns` split already exists; this assigns `patterns` a load-bearing meaning
that matches its natural connotation — a pattern is matched *if present*, a path
names a *required* file. It costs no new frontmatter surface and no new marker
syntax in the placeholder regex the scanner and resolver both mirror (a
`<cat?>`-style marker would add exactly that drift surface). It is also
backward-safe: the installed `architect` / `process-author` agents carry their
categories in `owns:` (hard) and merely *label* them in `reads.patterns`, so they
stay hard and unchanged.

**Why this is an ADR, not a COR.** It composes only existing principles —
ADR-013's discovery seam and empty-is-normal, ADR-051's referenced-category
absence-tolerance and its single-consumer/structural-inference discipline,
COR-013 rule 5's deploy-time resolution, COR-007's don't-duplicate — into the
architectural realization of an *optional* overlay read. It introduces no new
universal principle; it repairs the seam so ADR-013 D1's already-decided contract
actually holds. It matches the ADR-013/ADR-051 family.

### Alternatives considered

- **Keep the bare literal.** Rejected — it is the bug: no delivery, no
  discovery, and a standing violation of ADR-013 D1.
- **A new `optional_reads:` frontmatter key.** Rejected — a second declaration
  surface for what the `paths`/`patterns` split already expresses; new parsing in
  both mirror-guarded implementations for no capability the existing channel
  can't carry.
- **A per-item marker (`<project-conventions?>`).** Rejected — complicates the
  angle-bracket regex mirrored across scanner and resolver, the exact drift the
  parity guard exists to prevent.
- **Add `project-conventions` to a read-side allowlist mirroring
  `WRITE_CARRYING_CATEGORIES`.** Rejected — names a capability's category in
  backbone code (against ADR-013 D2), and runs safe-default the wrong way for a
  read (a new capability's category would skip until registered).
- **Generalize `WRITE_CARRYING_CATEGORIES` to cover both.** Rejected — collapses
  two opposite safe-defaults; regresses one of ADR-013 or ADR-051 whichever way
  the merged semantics fall (see Rationale).

## Implications

- **The deploy resolver and the backbone scanner gain a channel split** —
  `reads.patterns` optional, `reads.paths` / `reads.records` hard — shipped with
  the implementing change-set and pinned by the extended parity guard. Additive;
  hard-reference behaviour is unchanged.
- **`pkit agents` deploy-readiness changes for optional-only agents.** An agent
  whose only undefined categories are optional now reports **deployable**, not
  SKIPPED, matching what the resolver does. `reconcile` surfaces the optional
  category with optional framing and can stub it; it never blocks.
- **ADR-013 D1 is realized, not amended.** The four agents move from bare literal
  to `<project-conventions>`. This makes the corpus path actually reach the agent
  and makes `reconcile` see the category — the two behaviours ADR-013 promised.
- **ADR-051 is untouched.** `process-authoring-targets` stays write-carrying and
  hard (carried in `owns:`); its explicit-`[]` inert-deploy path is unchanged.
- **Adopter-observable surface change → changeset, no migration.** The resolver
  rule (adapter component) and the agent frontmatter (capability component) are
  adopter-observable when they ship, so they ride changesets per PRJ-002. No
  COR-010 migration is owed: `pkit sync` re-resolves and re-deploys every agent
  on each run, so the fix reaches installed adopters by re-deploy with no
  persisted state to migrate, and no file rename / removal / schema_version bump
  is involved. `pkit migrations check-diff` gates the implementing diff
  regardless.
- **Acceptance precedes citation (COR-025).** This record is accepted before any
  agent frontmatter or the `software-engineering` README cites it, per the
  ADR-051 companion-record sequencing.
- **The universal property is recorded, not just coded.** "A patterns-only
  overlay read tolerates absence; the backbone infers this from the reference
  site and names no category" is pinned here so a future capability's read
  category inherits the behaviour without re-deciding the mechanism, and so a
  later author cannot regress it into a per-category allowlist.
