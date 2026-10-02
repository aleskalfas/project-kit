---
name: capability-author
description: Author a new capability — an opt-in installable methodology discipline at .pkit/capabilities/<name>/ — with proper layout, package metadata, and the COR-017 contract. Use when packaging a coherent body of decisions, skills, agents, and scripts that some adopters need and others don't.
metadata:
  wraps_command: pkit new capability
gates:
  - COR-005
  - COR-006
  - COR-007
  - COR-008
  - COR-017
reads:
  records:
    - COR-011
    - PRJ-002
  paths:
    - .pkit/cli/README.md
    - .pkit/lifecycle/README.md
    - .pkit/permissions/README.md
    - .pkit/decisions/README.md
    - .pkit/decisions/core/COR-017-capability-pattern.md
    - .pkit/decisions/core/COR-005-bundle-pattern.md
    - .pkit/decisions/core/COR-007-pattern-extraction.md
    - CONTRIBUTING.md
---

# Authoring a capability

This skill walks through adding a new **capability** at `.pkit/capabilities/<name>/` (per COR-017). A capability is an opt-in installable discipline — a coherent bundle of decisions, skills, agents, scripts, and schemas that some adopters install per project and others don't. Capabilities slot in alongside areas, bundles, and adapters as a sibling concept, not a fourth area variant.

## When this skill applies

Reach for a capability when:

- The discipline is **useful but not universal** — most adopters won't need it, but those who do need the whole bundle (decisions + skills + maybe an agent + maybe a script).
- A clean opt-in/opt-out boundary exists. If you can describe "install this and it appears, uninstall and it disappears, no shared files" you have a capability.
- The pattern has earned its keep per COR-007 — at minimum, a concrete adopter motivated it; ideally, two or more adopters or use cases would benefit. Inventing capabilities speculatively is the failure mode this skill is designed to prevent.

Do **not** use this skill for:

- Universal disciplines every adopter must follow — those belong in `core/` (areas) and ship via propagation, not opt-in install.
- Single-adopter customisation — that belongs in the adopter's `project/` namespaces (per COR-011's universal variant).
- Harness translations — those are adapters (per COR-005).
- Alternative implementations of the same area's contract — those are bundles (per COR-005).

## Acceptance gate (run first)

Per `.pkit/decisions/README.md`'s acceptance gate: verify every record in `gates:` is `accepted` before authoring. Halt if any is `proposed` or `superseded`.

The current dependencies:

- **COR-005** — the bundle/adapter pattern; capabilities share their package-yaml shape and skill/command-pairing discipline.
- **COR-006** — artifact roles; what belongs in a decision vs a skill vs an agent vs a script.
- **COR-007** — pattern extraction; capabilities should formalise a recurring discipline, not anticipate one.
- **COR-008** — git workflow conventions; the commit step.
- **COR-017** — the capability pattern; the canonical record fixing layout, lifecycle, citation form, and install/sync/uninstall semantics.

## Procedure

### 1. Pick the capability name

Use a kebab-case noun that names the *discipline*, not the implementation. Examples:

- `evidence` — citation discipline (not `citations` or `evidence-yaml`)
- `product-management` — product-management discipline (not `pm-agent` or `scrum`)
- `storyboard-authoring` — storyboard discipline (not `storyboards`, which would conflict with the universal area)

The name becomes the directory name, the value of `component.name` in `package.yaml`, and the prefix in citations: `[<capability-name>:DEC-NNN-<slug>]`.

**Reserved names: `core`, `project`, `adr` and `backbone`.** `pkit new capability`, `pkit capabilities install`, and `pkit capabilities register` all refuse each, giving the reason:

- `core` is the name core's own entries carry where a capability's carry the capability's name — the namespace of the core decision records and agents (`pkit new decision core …`, `pkit new agent core …`), and the core schemas area (`.pkit/schemas/`) wherever a schemas verb takes an owner — so a capability named `core` could have no decision records or agents stamped, and its `schemas/` would be silently unreachable.
- `project` is the name the project's own entries carry where a capability's carry the capability's name — the namespace of the project's decision records and agents (`pkit new decision project …`, `pkit new agent project …`), and the opening name of the project's checks in an evidence point (the software-analysis and living-docs capabilities' DEC-001, point 7) — so a capability named `project` would be indistinguishable from the project itself.
- `adr` is the namespace of the project's architecture decision records, which `pkit new decision adr …` stamps before any capability name is tried, so a capability named `adr` could have no decision records stamped.
- `backbone` is the name the backbone carries where a component's carry the component's name — the component of the backbone's changesets (`component: backbone` under `.changes/unreleased/`), the owner of its validators (beside a capability's `<capability>:<name>`), the component its rule sets are cited with (`backbone:<SET>`), and the component its documentation locations are recorded under — so a capability named `backbone` would have its changesets, validators, rule sets and documentation locations read as the backbone's.

A capability registered under any of these names before it was reserved stays registered; `pkit validate` reports it as an error naming the rename.

**Not a backbone command's name either.** The dispatcher reads an installed capability's name as a top-level command, and a backbone command (`validate`, `status`, `sync`, `capabilities`, … — `pkit --help` lists them) holds its name first, so a capability named after one could never surface its commands as `pkit <name> …`. `pkit new capability` refuses such a name, reading the commands from the dispatcher when it runs. `pkit capabilities install` and `register` do not: the backbone gains commands with its releases, so an upgrade can take a name that was free when a capability shipped, and refusing it then would break the installation of something that worked. Instead `pkit validate` reports an installed capability that ships a `commands:` block under a backbone command's name as an error naming the rename; one with no `commands:` block surfaces no namespace and is not reported.

### 2. Read the contract

Read `.pkit/decisions/core/COR-017-capability-pattern.md`. Every capability ships:

- `package.yaml` — component metadata (`schema_version`, `kind: capability`, `name`, `version`, `description`, `requires_backbone`, all required; the package schema refuses a key it does not know — see `.pkit/lifecycle/README.md`, "Package metadata").
- `README.md` — adopter-facing intro: the discipline, the commands, the conventions.
- Some non-empty subset of `decisions/`, `skills/`, `agents/`, `scripts/`, `schemas/`. A capability with no decisions and no skills is suspicious — at minimum, you'd expect one decision establishing the discipline's invariant plus one skill or script operationalising it.

### 3. Stamp the scaffold

Use the authoring command (per `.pkit/cli/README.md`):

```
pkit new capability <name>
```

The command:

- Creates `.pkit/capabilities/<name>/`.
- Stamps `package.yaml` with `kind: capability`, `version: 0.1.0`, a placeholder `description` to replace with the one-line summary, and `requires_backbone` pinned to a range matching the project's current backbone.
- Stamps `README.md` with placeholder prose explaining the discipline, install command, and citation form.
- Creates empty `decisions/`, `skills/`, `agents/`, `scripts/`, and `schemas/` subdirectories with `.gitkeep`.

Unlike bundles and adapters, the capability is **not** registered in the backbone manifest by the scaffolding step. Capabilities are kit-shipped from the source-of-edit's perspective; adopters register them per-project via `pkit capabilities install <name>`.

The command refuses if a capability with that name already exists, if the slug isn't kebab-case, if the name is reserved (`core`, `project`, `adr` or `backbone`), or if it is a backbone command's (see step 1).

### 4. Fill in the README

Open `.pkit/capabilities/<name>/README.md` and replace the placeholders with:

- **One-paragraph summary** — what discipline the capability formalises, when an adopter would install it.
- **What this capability ships** — the kit-shipped artifacts an adopter receives.
- **Adopter setup** — the install command and any per-project configuration the adopter must fill in.
- **Citing this capability's decisions** — keep the stamped paragraph; it documents the `[<capability-name>:DEC-NNN-<slug>]` citation form.
- **Dependencies** — what the adopter needs in place: external tooling, other capabilities, accounts.

### 5. Author the decisions

Capability decisions live in `decisions/` with filenames `DEC-NNN-<slug>.md`. The numbering is scoped to *this* capability — every capability has its own `DEC-001`. Author by hand for now: there is no `pkit new decision` extension for capability namespaces yet (per COR-007, that pattern lands when capability authoring recurs enough to justify the tooling).

Each decision has the same shape as a PRJ decision (axiom + principles-not-inventory disciplines apply; project-neutrality does not — capabilities are explicitly discipline-specific):

```markdown
---
id: DEC-001
title: <imperative short title>
status: accepted
date: YYYY-MM-DD
author: <name>
---

## Context

## Decision

## Rationale

## Implications
```

Cite other capability decisions in the same capability using the form `[<this-capability>:DEC-NNN-<slug>]`. Cite COR / PRJ records as `COR-NNN` / `PRJ-NNN` (the kit's existing forms).

### 6. Author the skills, agents, scripts, and schemas

Skills, agents, scripts, and schemas in a capability follow the same shapes as their area-shipped counterparts (per COR-006). Two notes specific to capabilities:

- Skills and agents may cite *this capability's* decisions in body prose via the `[<name>:DEC-NNN-slug]` form. The validator (`pkit refs validate`) walks capability subtrees and resolves these citations.
- Scripts can be Python with PEP 723 inline metadata (so adopters can run them via `uv run` without a host project) or shell. If a script needs Python dependencies, declare them inline so the script is self-installing.

### 6b. (Optional) Ship a permission fragment

If the capability needs to **shape its own agents' tool reach** — define a privilege the backbone catalog should not carry, and deny it to one of the capability's agents — it ships a `permissions/` fragment (the capability-contributed privilege-definition + grant mechanism; see `.pkit/permissions/README.md`). Stamp the skeleton:

```
pkit permissions scaffold <name>
```

This stamps `.pkit/capabilities/<name>/permissions/privilege-catalog.yaml` (the privilege *definition*) and `grants.yaml` (the deny *policy*), with inline guidance. It refuses an unknown capability and refuses to clobber an existing fragment file. Skip this step entirely if the capability shapes no permissions.

Two footguns the stamped comments call out — and that you must respect when editing the fragment:

- **Fragment privilege keys are authored BARE.** Write `ad-hoc-scraping:`, not `<name>:ad-hoc-scraping:`. The loader rewrites each key to the capability-scoped id `<name>:ad-hoc-scraping`. Writing the scope yourself double-scopes it.
- **A grant references a fragment privilege with the SCOPED token.** In `grants.yaml`, reference it as `[privilege-catalog:<name>:ad-hoc-scraping]` — the `<name>:` scope is **required**. A bare `[privilege-catalog:ad-hoc-scraping]` resolves to no merged privilege, so the deny silently does **not** bind (a fail-open hazard). A *backbone* privilege is still referenced bare (e.g. `[privilege-catalog:issue-tracker-write]`).
- **`guardrail: true` is forbidden in a fragment.** A capability may extend the recognised vocabulary but may never install a deny on every adopter by default; the loader rejects such an entry.

`pkit schemas validate` runs a fragment-token-resolution lint over every installed capability's `grants.yaml`: a token resolving to no privilege in the merged catalog fails the gate (catching the bare-vs-scoped mistake even in a hand-authored fragment). Run it after editing the fragment.

### 7. Self-check

Walk the capability against COR-017's universal-element checklist:

- *Is the capability genuinely opt-in?* If every adopter would install it, it's not a capability — it belongs in core areas.
- *Does the capability stand on its own?* Could an adopter install it and use it without inheriting hidden expectations from the rest of the kit?
- *Are the decisions principle-shaped?* No inventory dressed up as decisions. The COR-017 disciplines apply to capability decisions too.
- *Is there a citation form that an author can use?* `[<name>:DEC-NNN-<slug>]` should round-trip through `pkit refs validate`.
- *Is the README adopter-facing?* It explains the discipline, not the implementation; an adopter reading it cold should understand what they're opting into.

If any check fails, revise.

### 8. Smoke install + uninstall

Before committing, validate the capability mechanically:

```
pkit refs validate                              # capability subtree is parsed cleanly
```

If the capability ships a `permissions/` fragment, also run `pkit schemas validate` — its fragment-token-resolution lint confirms each grant token resolves to a real privilege in the merged catalog (catches a bare-vs-scoped token).

Then in a scratch adopter:

```
cd /tmp/scratch-adopter && pkit init --here     # --here installs into this fresh non-git dir (bypasses the off-CWD confirm)
pkit capabilities install <name>               # subtree copies in, manifest registers
pkit status                                     # capability appears under installed
pkit capabilities uninstall <name>             # tree removed, manifest unregisters
```

Catch any layout or schema mistakes here, not at adopter time.

### 9. Commit

Per COR-008, conventional-commits format. Type is `feat`; scope is `capabilities` or the capability name:

```
feat(capabilities): add <name> capability

<body — 1–3 paragraphs naming the discipline this capability
formalises, what it ships, and what motivated bundling it as an opt-in
capability rather than core content>
```

The capability lands at `version: 0.1.0`. Subsequent bumps follow the same surface-change rule the methodology uses for its own backbone (per PRJ-002 in project-kit's own repo; adopter-shipped capabilities use whatever bump policy that project adopts).

## Variations

- **Adding decisions/skills/agents to an existing capability** — edit the capability's subtree directly. Refusing to use the scaffolding command for follow-up work is fine; the scaffold is just for the first instance.
- **Adopters authoring their own capability** — same procedure, same command. An adopter who develops a discipline worth sharing creates it under their own copy of the methodology and contributes upstream if generally useful.
- **Bumping a capability's version** — bump `version:` in `package.yaml` whenever the capability lands a surface change visible to adopters: new decision, new skill, new agent, new script, removed file, schema change. Adopters pick up the new version on the next `pkit sync` or `pkit capabilities upgrade <name>`.
- **Swappable implementations of the same capability** — defer until two implementations exist. COR-017's variants note (Implications section) captures this: if the same discipline ships in multiple flavours (e.g., evidence-yaml-python vs evidence-sqlite), pattern-extract a sub-structure when the second flavour lands per COR-007.
