---
id: PRJ-008
title: "`pkit report` — a built-in adopter→project-kit feedback channel"
status: accepted
date: 2026-08-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** adopter feedback about pkit-the-tool has no home today — it
gets pasted into a chat and lost. This adds a built-in `pkit report` command so an
adopter files a **bug** or freeform **feedback** to **project-kit's own tracker**,
agent-assisted, with pkit + capability versions auto-attached and home paths
stripped, and can then **watch their reports move** (states, maintainer comments,
and the issues that will fix them) from the CLI. Maintainers (working *in* the
project-kit repo) get the receiving side — an inbox and a link verb. The point is
adoption: a reporter who sees their feedback acted on trusts the tool and keeps
using it.

## Context

Mike (an adopter, pkit 1.105 / pm 0.24) hit real friction and had no first-class
way to report it — the feedback was pasted into an assistant chat. An adopter *can*
open a GitHub issue by hand, but must know to, lands on a template that fits their
mixed feedback awkwardly, gives the maintainer a report with **no version/environment
context** (the single most useful thing for triage), and then has no easy way to see
whether it went anywhere. A built-in report channel is the well-worn tool pattern
(`gh`/`rustc`-style bug-report) that closes all three, and — because pkit is
self-hosted and solo-maintained — the *tracking* half is the adoption flywheel, not
a nicety.

This is the **adopter→tool-repo** direction, and must not be conflated with the pm
capability's existing **"Feedback to the spec"** channel, which flows
*maintainer→upstream-spec* (`pm-workflow`) via scratchpad notes. Different source,
different sink.

## Decision

**Ship a `pkit report` command family. The backbone provides a *target-agnostic*
report mechanism; project-kit-the-distribution configures its target to project-kit's
own repo.** The command surface is universal (every adopter gets it); the *fixed
target* is project-kit-specific, which is why this is a PRJ, not a COR (below).

### Surface — the split

The command family has two sides, and *the split is the decision* (the per-command
surface is spec'd once in `.pkit/cli/README.md`, not re-enumerated here):

- **Reporter side — universal**, available in any adopting repo: compose+file a
  **bug** (structured) or **feedback** (freeform), and read back the invoker's own
  reports and their progress. Representative verbs: `report bug|feedback`,
  `report` (list), `report show`.
- **Maintainer side — target-repo-gated**, enabled *only when the current repo is
  the report target* (the structural "just for project-kit developers" gate; inert
  elsewhere — a fork's maintainer side follows its own configured target). It
  triages incoming reports and maintains the fix-linkage. Representative verbs:
  `report inbox`, `report link|unlink`.
- A `--on-behalf-of @login` modifier files under the invoker's identity with an
  attribution (see below).

### Target

The target is set by **distribution-level project config** — a `report.target`
`owner/repo` key the distribution carries in its project config (project-kit sets it
to project-kit's own repo; the exact config path is pinned at build) — **not** a
neutral-core constant and **not** an adopter-facing `--repo` flag. This keeps the neutral backbone free of any hard-wired phone-home
(COR-014), keeps it a single contained target (never a general foreign-issue-filer),
and lets a fork retarget by editing its own config. Report is inert / degrades to a
draft when no target is configured. (Same shape as [pkit:PRJ-004]'s
project-kit-specific install source carried by universal surface.)

### Tracking model

- `list` **renders one line per report** (number, state, title, last activity) —
  **flat by default**, not a bare count. Its scope is the issues **authored by *or*
  attributed to** the invoker, so an on-behalf report still shows up for its
  beneficiary. A **`--tree`** mode expands each feedback with its `## Tracked by`
  fixes and their states inline (and `show <N>` always gives that per-report
  detail) — flat stays the default so the overview is a quick scan.
- `show <feedback-N>` renders a **`## Tracked by`** section — a GitHub task-list of
  `#N` references (many-to-many, non-owning: derived *or* pre-existing) — resolving
  each linked issue's state. Chosen over native sub-issues (single-parent ownership
  can't express "one fix addresses several feedbacks") and over a bespoke
  `derived-from:` label. Maintainer-derived issues are maintainer-authored, so they
  never clutter the reporter's `list`; they surface under their parent feedback.

### On-behalf = attribution, not authorship

GitHub stamps the authenticated user as author; one cannot file *as* another person.
`--on-behalf-of @mike` files under the invoker's identity with a "Reported for
@mike" credit + marker; the marker restores @mike's tracking. The flow nudges a
consent check (public repo + their name).

### Safety obligations (detailed in [pkit:ADR-045])

The reporter side is a **cross-repo write** to the fixed upstream — the first
realization of [COR-039](../core/COR-039-session-repo-mutation-boundary.md)'s
reserved cross-repo exception. It is bound by: a per-invocation **target-naming
confirm**; **URL-first, `gh`-file opt-in**; **`--yes`/autonomy degrades to a draft**,
never auto-posts; and **redaction by construction** of the environment block. The
maintainer side is a same-repo edit (the dev's cwd *is* the target) and carries none
of this.

## Rationale

**Why build it, and why tracking is v1 not v2.** The auto-context block
(version-stamped, redacted) is the concrete value — it's what turns "something broke"
into a triageable report. Tracking is the *adoption* argument: a solo-maintained tool
grows by adopters who report, watch it move, and trust the loop. There *is* a first
trackable item (Mike's), so the "one instance, defer it" (COR-007) objection is
weaker than it looks; and the only tracked-half piece with a missing producer — the
derived-issue rollup — is made real here by the `report link` verb + the
`## Tracked by` convention, rather than left hostage to an unwritten one.

**Why PRJ, not COR.** The command *surface* is universal, but the *decision content*
— "the fixed upstream is project-kit's own repo" — is product-specific and fails
universal applicability (a neutral principle would not name project-kit's repo). A
COR here would be speculative generality (COR-007 — no second methodology-tool
consumer of "ships an upstream channel"). [pkit:PRJ-004] already pins a
project-kit-specific fact (the install source) into universal backbone surface; this
is the same shape.

### Alternatives considered

- **A capability adopters install.** Rejected — a channel that must *always* be
  present cannot sit behind an install gate; that re-creates the "feedback had no
  home" gap for every adopter who didn't install it.
- **A pm-capability feature.** Rejected — pm's target is the adopter's *own* repo;
  this target is project-kit's repo. Categorically different; conflating them
  confuses "which repo am I filing to."
- **`pkit report --context` only** (print a redacted block to paste, no write).
  Genuinely simpler and dissolves the cross-repo + target questions — but it drops
  the tracking/adoption loop the maintainer wants. Kept as the degrade path (the
  no-`gh` / `--yes` draft *is* a paste-able block), not the whole feature.
- **Hardcode the target in neutral core** (the install-source shape). Rejected for
  the *target* specifically — it bakes one product's support desk into the neutral
  methodology (COR-014); the distribution-config split keeps the core neutral while
  the target stays fixed-per-distribution.
- **Native sub-issues for the fix-linkage.** Rejected — single-parent ownership
  can't express many-to-many "one fix addresses several feedbacks / a pre-existing
  issue addresses this one."

## Implications

- **New records:** this PRJ + [pkit:ADR-045] (the cross-repo realization) + a
  `report` entry in the CLI spec (`.pkit/cli/README.md`). No COR.
- **Backbone command + a shared accessor.** The command lives in the backbone CLI.
  Its environment block reuses an **extracted `collect_environment()`** accessor
  (shared with `status`, reading the *installed* manifest side) rather than a
  hand-rolled version walk (COR-007).
- **Distribution config** carries the target; project-kit sets it to its own repo.
  Absent target ⇒ inert/degrade, never a silent no-op.
- **A `report-author` skill** carries the agent-assisted formulation (structuring,
  not bloating).
- **Maintainer discipline:** on triage, the maintainer adds fixing issues to a
  feedback's `## Tracked by` via `report link` — the cheap producer that makes
  `show`'s rollup real.
- **Surface change / versioning** per [pkit:PRJ-002] (new CLI command family).
- **Neutrality check owed:** run `methodology-reviewer` on this record set — the
  hard-wired-target-in-neutral-core smell is the specific thing to confirm is
  resolved by the distribution-config split.
- Because this refines nothing already accepted and introduces a new surface,
  promotion `proposed → accepted` is a maintainer gesture after review.
