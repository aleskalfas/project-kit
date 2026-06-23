---
authors:
  - Ales Kalfas <ales.kalfas@ibm.com>
started: 2026-06-23
retired: 2026-06-24
produced:
  - DEC-036
---

# project-management on brownfield repos — adapting to an immutable substrate

Design exploration, to be relayed upstream to project-kit / pm-workflow. The
operational-friction companion is
[`2026-06-19-pm-capability-dogfooding-findings`](./2026-06-19-pm-capability-dogfooding-findings.md)
— that note lists bugs/gaps hit while *running* the capability; this note asks a
deeper design question the AUJ case surfaced.

## The question

The project-management capability today assumes it can **create its own
substrate** — it bootstraps `type:*`, `priority:*`, `workstream:*`, and
`state:*` labels (and optionally a Projects v2 board), and `pre-check`
**hard-refuses to proceed** when they're absent. That is a *greenfield*
assumption.

Many real repos are **brownfield**: the team cannot change repo settings —
labels, fields, board columns are fixed by org policy or permissions, and a
large body of issues already follows a native convention. In `agentic-user-journey`
(AUJ) we *cannot create labels at all*. The capability is vendored there but
unusable end-to-end: `pre-check` fails, `create-issue` refuses tasks without a
parent the repo's flat tracker doesn't have, and so on.

**How should the capability adapt to an existing, immutable substrate —
remapping its conceptual needs onto what already exists, degrading gracefully
when something is missing, and tolerating attributes it doesn't manage — so a
brownfield adopter keeps as much of the methodology as the substrate allows
instead of being blocked wholesale?**

The goal: preserve as much of the capability as possible under a fixed setting.
Greenfield should stay the easy path; brownfield should be a supported mode, not
a wall.

## Forces

- **Immutable substrate.** No `bootstrap` (can't create labels/state/board). The
  capability must consume what exists, read-only on settings.
- **Graceful degradation over refusal.** `pre-check` currently fails hard on
  missing labels and *refuses to proceed*. A brownfield adopter needs the
  opposite default: run with what's available, disable (with a clear notice)
  only the features whose substrate is truly absent.
- **A native convention already in use.** Brownfield repos have existing labels,
  title prefixes, and hundreds of issues. The capability must coexist — map onto
  the native scheme, never clobber it, and not require re-tagging history.
- **Conceptual axes vs. their substrate.** The methodology's *concepts* (type,
  priority, workstream, lifecycle state, hierarchy) are separable from the
  *substrate* that encodes them (labels, prefixes, board columns, body refs).
  Greenfield binds each concept to a kit-created label; brownfield needs each
  concept independently bindable — to an existing label, to a title prefix, to
  "derive it", or to "unsupported → disable that feature".
- **Tolerate extras.** The repo will have labels/attributes the methodology
  doesn't model (e.g. AUJ's `Leadership Requests`, `Blocked`). These must pass
  through untouched, not trip validation.

## How AUJ actually works (the concrete substrate)

Documenting the worked example, since a remap has to target something real.

- **No `type:*` / `workstream:*` / `state:*` labels exist**, and they cannot be
  created. `pre-check` reports all three sets missing.
- **Priority**: native `P0` / `P1` / `P2` labels (not `priority:High/Medium/Low`).
- **Type / structure**: conveyed by **title prefix** — `[Task]`, `[Epic]`
  (note: lowercase-`pic`, off from the kit's `[EPIC]`), occasionally none. No
  `type:*` label, no parent-ref labels.
- **Workstream / theme**: native thematic labels — `Synthetic Test Rig R&D`,
  `Roles & User Journeys`, `Human & Observational Testing`, `Eval & Insight`,
  `Leadership Requests`. These are the closest thing to a workstream axis, but
  the vocabulary is the team's, not the kit's.
- **Lifecycle state**: **no `state:*` labels** — state is implicit (issue
  open/closed; `Blocked` label for blocked). No board columns the capability can
  read (no Projects v2; `has_projects_v2_board: false`).
- **Hierarchy**: **flat**. Issues are not arranged as EPIC → Feature → Task with
  enforced parent-refs; `[Epic]`-prefixed issues exist but children don't carry a
  machine-checkable parent link. `create-issue --type task` *requires* a parent
  type the repo doesn't model.
- **Vendored config is un-tailored**: `workstreams.yaml` still holds project-kit's
  *own* workstreams (`capabilities, schemas, decisions, …`) — boilerplate that
  doesn't describe AUJ. (Even if we could bootstrap, it'd create the wrong
  labels.)

Net: of the methodology's axes, AUJ can serve **priority** (remapped to P0/P1/P2)
and a rough **workstream/type** (via thematic labels + title prefix); it cannot
serve **state labels** or **enforced hierarchy** at all.

## What the capability assumes today (the greenfield bias)

- `pre-check` treats missing `type/priority/workstream/state` labels as **hard
  fails** and refuses to proceed — no "run degraded" path.
- `bootstrap` is the only blessed way to get a working substrate; there's no
  "adopt-existing" inventory-and-map alternative.
- `create-issue` enforces the **containment graph** (a `task` must have a
  `feature/umbrella/epic/milestone` parent) — unconditionally, even where the
  adopter runs flat.
- The `move-issue` state machine assumes `state:*` labels (in label-fallback
  mode) as its substrate.
- Classification labels are **fixed vocabulary** (`priority:High`, etc.) rather
  than a binding the adopter can point at an existing label.

## Design space (candidate approaches)

Rough enumeration; sharpens with discussion.

1. **A substrate-mapping file.** New adopter config (e.g.
   `project/substrate-map.yaml`) that binds each methodology axis to the
   existing substrate. Per axis, one of: `label: <existing-label-set>` (with a
   value→value remap, e.g. `priority: {High: P0, Medium: P1, Low: P2}`),
   `title-prefix`, `derive` (e.g. state from open/closed + `Blocked`),
   or `unsupported` (feature that needs it is disabled). The engine reads the
   map instead of assuming its own vocabulary.

2. **Graceful-degradation pre-check.** A `mode: brownfield` (or
   `substrate: existing`) switch that turns substrate hard-fails into warnings,
   prints a capability matrix ("priority: ✓ via P0/P1/P2; state machine: ✗
   disabled — no state substrate; hierarchy: advisory-only"), and lets the rest
   run.

3. **`adopt-existing` bootstrap variant.** Instead of *creating* labels,
   inventory the repo's existing labels/prefixes and **scaffold a draft
   substrate-map** for the adopter to confirm — the brownfield analogue of
   `bootstrap`.

4. **Per-axis required/optional/derived/disabled matrix.** Make explicit which
   features are load-bearing vs. nice-to-have, so degradation is principled:
   e.g. classification can be partial; the state machine can fall back to
   open/closed; hierarchy can be advisory (parent-ref in body text, not gated).

5. **Tolerate-extras by default.** Unknown labels/attributes are preserved and
   ignored; the methodology operates over its mapped subset and never clobbers
   or fails on what it doesn't manage.

6. **Hierarchy without parent-ref labels.** Allow a flat mode where parent-refs
   are body-text only (recorded, not enforced), so `create-issue` doesn't
   require a parent the repo can't express.

## A worked remap for AUJ (illustrative)

| Methodology axis | AUJ substrate | Binding |
|---|---|---|
| priority | `P0` / `P1` / `P2` | `label` remap: High→P0, Medium→P1, Low→P2 |
| type (structural) | `[Task]` / `[Epic]` title prefix | `title-prefix`; tolerate `[Epic]` casing |
| workstream / theme | thematic labels (`Synthetic Test Rig R&D`, …) | `label` (adopter vocabulary) or `unsupported` |
| lifecycle state | open/closed + `Blocked` | `derive` (no state machine labels) |
| hierarchy | flat | advisory (body-text parent-ref, ungated) |
| extras | `Leadership Requests`, etc. | pass-through, ignored |

Under this, AUJ could file/classify/validate issues and open/edit PRs through the
capability without ever needing a label it can't create; only the state-machine
and gated-hierarchy features degrade to advisory.

## A second axis of rigidity: PRs that must close a numbered issue

The same greenfield assumption shows up in the **PR flow**, not just the label
substrate. `open-pr` requires the branch to match `<type>/<issue#>-<slug>` and
derives a mandatory `Closes #N` — *every* PR must close a numbered issue. But
legitimate PRs routinely close none:

- **Scratchpad / exploratory notes** (COR-012) — a design note isn't "task work"
  with acceptance criteria.
- **Decision-acceptance PRs** — flipping a record `proposed → accepted` is a
  one-line status change that closes no issue.
- **Docs-only touch-ups** with no corresponding ticket.

Observed concretely this session: merging *this very note* required manufacturing
a tracking issue (#134) + a numbered branch + ticking acceptance boxes solely to
satisfy `open-pr` and the close-gate; and the PRJ-003 acceptance PR had no honest
closing issue at all (tying it to an unrelated issue would wrongly auto-close
that issue). On a branch-protected `main` — where the only way onto the branch is
a PR — "no natural closing issue" becomes a hard wall: the agent can stage
everything but can't open the PR through the validated path, and is forced either
into ceremony (a throwaway issue) or out of the validated path entirely (raw
`gh`, which a confined agent may not be permitted).

So "a PR must close a numbered issue" is the same class of greenfield rigidity as
"the substrate must be the kit's own labels": both assume the project is shaped
exactly as the methodology bootstraps it. A substrate-pluggable design should
also treat **issue-less PRs** (scratchpad / decision-acceptance / docs-only) as a
first-class, validated mode — `open-pr` accepting a non-numbered branch with no
`Closes`, and the close-gate simply not applying — rather than forcing ceremony
or pushing the work outside the validated path.

## Open questions

- Which features are genuinely **load-bearing** vs. degradable? (The `move-issue`
  state machine without `state:*` labels — derive from open/closed, or just
  disable?)
- Gating semantics in degraded mode: which `hard-reject`s soften to `warning`
  when their substrate is absent, and which stay hard (e.g. title-prefix is
  cheap, keep it)?
- Is brownfield a **single `mode` flag**, or does it emerge implicitly from the
  presence of a `substrate-map.yaml`?
- How does the **remap interact with the schemas** (classification.yaml,
  issue-types.yaml, git-conventions.yaml) — an overlay/indirection layer, or
  per-schema `binds_to`-style fields?
- Coexistence: how to avoid the capability ever *writing* a label the adopter
  can't manage (e.g. `open-pr`/`create-issue` must not try to apply `type:*` when
  the binding is `title-prefix`).
- Does this also fix the `open-pr` "every PR must close a numbered issue"
  assumption (decision-acceptance PRs close none) — i.e., is "no closing issue"
  another form of substrate flexibility?

## Retiring this note

Relay to project-kit / pm-workflow as a design input: **the capability should be
substrate-pluggable, defaulting to greenfield bootstrap but supporting a
brownfield/adopt-existing mode that remaps its axes onto an immutable substrate
and degrades feature-by-feature.** When it produces a decision/spec upstream (or
is folded into a consolidated pm-workflow report),
`pkit scratchpad done pm-brownfield-adoption --produced <ref>`. Cross-reference
the dogfooding-findings note, whose Findings 2 (parent-ref rigidity) and the
`pre-check` hard-fail behaviour are symptoms of the same greenfield bias.
