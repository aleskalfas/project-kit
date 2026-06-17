---
authors:
  - Ales Kalfas <ales.kalfas@ibm.com>
started: 2026-06-17
---

# PM capability: label-substrate adaptability

> **Hand-off to project-kit maintainers.** Written from an adopter
> (agentic-user-journey) that hit a wall adopting the project-management
> capability. Goal: make the capability adoptable by repos that **cannot own a
> label namespace**. Not a decision — a problem statement + candidate directions
> for a pkit-side record + schema/script changes.

## The question

How can the project-management capability be adopted by a repo that **can't
create the labels it expects** — because the operator lacks `labels:write`, or
the repo already runs an **established, differently-named label taxonomy** that
won't be replaced?

## Evidence (the adopter case)

agentic-user-journey, single-repo, label-fallback (no Projects v2 board):

- Existing labels are domain-specific and *not* the methodology's names:
  `P0`/`P1`/`P2` (priority-ish), `Synthetic Test Rig R&D` + 4 sibling
  workstream-ish labels, `Blocked`. **No `type:*` and no `state:*` labels.**
- The operator has **no permission to create labels**, so `bootstrap` (which
  creates them) is unavailable.
- `pre-check.py` consequently fails four axes (`type:*`, `priority:*`,
  `workstream:*`, `state:*` all "missing → run bootstrap") and **refuses every
  operation** — the capability is effectively unusable here.
- All four classification axes are `required_on_every_issue: true` with
  `missing/wrong_value_severity: hard-reject` (classification.yaml), so there's
  no soft-landing.

## What's already known (capability facts)

- **No alias / remap layer exists.** Label names are hard-coded conventions
  (`type:*`, `priority:*`, `workstream:*`, `state:*`) across `classification.yaml`,
  `pre-check.py`, `move-issue.py`, `bootstrap.py`. The only "mapping" in the code
  is `type:* → conventional-commit type` (unrelated). There's no config to point
  `priority:High` at an existing `P0`.
- **The board hatch is partial.** `move-issue.py` supports two substrates:
  Projects v2 board (`Status`/single-select fields carry priority/workstream/
  **state**) vs label-fallback (`state:*` labels). A board removes the *need* for
  priority/workstream/state labels — **but**:
  - **Type is always a label** (`classification.yaml`: "always a label regardless
    of board presence" — it drives PR-title alignment), so a board-only repo
    *still* needs the 6 `type:*` labels created.
  - Board-field **writes are deferred at v1** — `move-issue.py` reads state from
    the board but notes it does "not mutate the board field at v1", so state
    transitions aren't actually automated on a board yet.
- **Forking the schemas/scripts to remap is off-limits** — the no-shared-files
  invariant (COR-013 / COR-017) means adopters must not edit kit-shipped
  capability content, and it'd be clobbered on upgrade anyway.

Net: the smallest possible footprint today is *still* "create ≥6 `type:*`
labels", and full label-fallback adoption is "create ~24 labels". A repo with
zero label-create permission cannot adopt at all.

## Candidate directions (for pkit to weigh)

### A. Adopter-declared label alias / remap

Let the adopter map methodology values → existing label names in project config:

```yaml
label_aliases:
  type:      { feature: "Task", bug: "Bug", ... }     # or onto title-prefix only
  priority:  { High: "P0", Medium: "P1", Low: "P2" }
  workstream:{ cli: "Synthetic Test Rig R&D", ... }
  state:     { in-progress: "WIP", ... }               # if such labels exist
```

Scripts resolve through the alias when reading/writing labels; `pre-check.py`
validates that *aliases resolve to existing labels* instead of demanding
canonical names. Most general fix; reuses whatever the repo already has.
*Risks:* values without an existing label still can't be represented (e.g. no
`state:*` equivalents) — needs a fallback; alias drift; per-axis mutual-exclusion
enforcement against foreign labels.

### B. Lift "Type is always a label" → allow Type on the board / title-only

Type is *already* mirrored in the title prefix (`[Task]`, `[Bug]`, …) via
`title_prefix_by_value`. Could Type be validated from the **title prefix** (and/
or a board field) so a board-only or alias-only repo needs **zero** new labels?
Pairs with finishing board-field writes (the deferred v1 bit).

### C. Pluggable / minimal state substrate

Abstract the state substrate so state can live somewhere a permission-constrained
repo *can* write: an existing label, a board field, a milestone, or a structured
comment/marker — chosen by config. Removes the `state:*`-labels hard dependency.

### D. Advisory / degrade-gracefully mode

A capability mode where axes that can't be represented in the repo's substrate
**downgrade from hard-reject to warning** instead of refusing. The conventions
(titles, body format, branch/PR rules) still apply and validate; the
label-backed classification/state-machine becomes best-effort. Lets a repo get
*most* of the methodology's value with *no* label namespace.

## Forces

- **No-shared-files invariant** — the fix must live in config + kit-shipped
  scripts, never in adopter edits to schemas.
- **Upgrade-safety** — alias/remap config must survive capability upgrades.
- **Least-privilege repos** — many enterprise repos don't grant `labels:write`
  to contributors; adoption shouldn't require admin rights.
- **Established taxonomies** — orgs with a working label scheme won't adopt a
  parallel one; the methodology should *ride* theirs.
- **Hard-reject discipline** — the axes are hard-reject by design (classification
  integrity); any "degrade to warning" mode must be a deliberate, declared opt-in,
  not silent.

## Open questions

1. Where does the alias map live — `project/config.yaml`, a new
   `project/label-aliases.yaml`, or `workstreams.yaml`-style sidecars per axis?
2. How does `pre-check.py` validate aliases (resolve-to-existing-label) vs the
   current canonical-name check? Does it warn on values with no alias + no label?
3. Can Type be satisfied by title-prefix alone, or does PR-title alignment truly
   need a `type:*` label? (Direction B hinges on this.)
4. Should "degrade-to-warning" (D) be global, per-axis, or per-issue?
5. Migration: how do existing label-fallback adopters opt in without churn?
6. Is this one capability change or several (alias config, board-writes, Type
   relaxation, advisory mode are somewhat independent)?

## Crystallises into (when resolved)

- A project-kit decision (DEC) on capability adaptability, plus changes to
  `classification.yaml`, `pre-check.py`, `move-issue.py`, `bootstrap.py`, and the
  adopter `config.yaml` shape. Retire this note with `--produced <DEC-id> …` once
  those land upstream.
