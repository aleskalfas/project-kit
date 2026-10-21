---
name: adapter-author
description: Author a new adapter (harness translation layer at .pkit/adapters/<name>/) with proper layout, package metadata, and the COR-005 contract. Use when supporting a new AI harness (Claude Code, Codex, Cursor, etc.).
metadata:
  wraps_command: pkit new adapter
gates:
  - COR-005
  - COR-006
  - COR-008
  - COR-010
  - COR-047
reads:
  records:
    - COR-002
  paths:
    - .pkit/cli/README.md
    - .pkit/lifecycle/README.md
    - .pkit/adapters/README.md
    - .pkit/decisions/README.md
    - .pkit/decisions/core/COR-005-bundle-pattern.md
    - .pkit/adapters/claude-code/README.md
    - .pkit/schemas/harness-requirements.yaml
    - .pkit/schemas/harness-support.schema.json
---

# Authoring an adapter

This skill walks through adding a new **adapter** at `.pkit/adapters/<name>/` (per COR-005). An adapter is a harness translation layer — it ports core-shipped content (skills, agents, settings, hooks) into whatever the target harness (Claude Code, Codex, Cursor, …) expects. Adapters sit at the methodology's top level, not inside an area, because they cut across multiple areas' content.

## Acceptance gate (run first)

Per `.pkit/decisions/README.md`'s acceptance gate: verify every record in `gates:` is `accepted` before authoring. Halt if any is `proposed` or `superseded`.

The current dependencies:

- **COR-005** — the bundle/adapter pattern; fixes the directory shape, universal elements, and install model.
- **COR-006** — artifact roles; harness-agnostic vs. harness-flavoured content split.
- **COR-008** — git workflow conventions; the commit step.
- **COR-010** — resource lifecycle; fixes the `package.yaml` schema, `requires_backbone` semantics, and migration directory layout.
- **COR-047** — harness requirements; the adapter answers each one the core declares, in its support declaration.

## Procedure

### 1. Pick the adapter name

Use the harness's canonical kebab-case name: `claude-code`, `codex`, `cursor`, etc. The name becomes the directory name and the value of the `component.name` field in `package.yaml`.

**Reserved name: `backbone`.** `pkit new adapter` refuses it, giving the reason, and `pkit init` refuses a methodology source that ships an adapter under it. `backbone` is the name the backbone carries where a component's carry the component's name, and two of those places read adapters as well as capabilities — the component of the backbone's changesets (`component: backbone` under `.changes/unreleased/`; every `package.yaml` under `.pkit/` is a component there) and the owner of its validators (every registered component's validators are owned by its name) — so an adapter named `backbone` would have its changesets and validators read as the backbone's. An adapter registered under it before it was reserved stays registered; `pkit validate` reports it as an error naming the rename. The other names reserved for capabilities (`core`, `project`, `adr`) collide only where a capability's name is read — decision, agent and schema namespaces, an evidence point's checks — so an adapter may take them.

**Not a capability's name either.** An adapter and a capability cannot share a name: the backbone reads a component by its name alone where it reads both kinds — a changeset names its component and the release keys every `package.yaml` under `.pkit/` by name, so a release would move only one of the two; every registered component's validators are owned by its name, so the two would share one owner; and the wiring resolver reads the component registry by name, so one of the two would be read under the other's kind. `pkit new adapter` refuses a name a capability holds in the project — registered in the backbone manifest, or present at `.pkit/capabilities/<name>/` — giving the reason, as `pkit new capability`, `pkit capabilities install` and `register` refuse a name an adapter holds, and `pkit init` refuses a methodology source that ships an adapter and a capability of one name. A pair registered before the refusal stays registered; `pkit validate` reports it as an error at each of the two, naming its rename.

### 2. Read the contract

Read `.pkit/decisions/core/COR-005-bundle-pattern.md` ("Adapter structure", "Universal elements" and "Authoring surface"). Every adapter must ship:

- `package.yaml` — component metadata per COR-010 (`schema_version`, `kind: adapter`, `name`, `version`, `description`, `requires_backbone`, all required; the package schema refuses a key it does not know — see `.pkit/lifecycle/README.md`, "Package metadata").
- `README.md` — what the adapter handles, what content it ships, how to deploy it.
- `migrations/` — the adapter's version migrations per COR-010, empty until its first one.

Beyond these, an adapter's content is heterogeneous — settings files in the harness's expected format, the scripts the lifecycle calls, runtime artifacts. Read `.pkit/adapters/README.md`, "Primitives the lifecycle calls", for the scripts and when each runs, and `.pkit/adapters/claude-code/` as the worked example; your harness may need a different mix.

### 3. Stamp the scaffold

Use the authoring command (per `.pkit/cli/README.md`):

```
pkit new adapter <name>
```

The command:

- Creates `.pkit/adapters/<name>/`.
- Stamps `package.yaml` with `kind: adapter`, `version: 0.1.0`, a placeholder `description` to replace with the one-line summary, and `requires_backbone` pinned to a range matching the project's current backbone.
- Stamps `README.md` with a placeholder body.
- Creates an empty `migrations/` directory.
- Registers the adapter in the backbone manifest's `components` registry (so `pkit status` sees it immediately).

It stamps no script and no settings template: which of them an adapter needs depends on its harness, so you write them in step 5 (COR-005, "Authoring surface").

The command refuses if an adapter with that name already exists, if the slug isn't kebab-case, if the name is reserved (`backbone`, see step 1), or if a capability holds it (see step 1).

### 4. Fill in the README

Open `.pkit/adapters/<name>/README.md` and replace the placeholders with:

- A one-paragraph summary of which harness the adapter translates for and what core content it carries across.
- A "What this adapter ships" section listing the artifacts the adapter provides — settings file(s), deploy scripts, runtime artifacts.
- A "How adopters use this adapter" section walking through deployment: what happens at `pkit init` (or sync), what the adopter does once, what runs automatically.

Look at `.pkit/adapters/claude-code/README.md` as a reference.

### 5. Author the harness-specific content

Add the artifacts the harness needs. The lifecycle finds an adapter's scripts **by name** in its folder and runs each one present; that is the contract the core relies on, set out in full in the adapters README, "Primitives the lifecycle calls", with `.pkit/adapters/claude-code/` as the worked example:

- **Deploy primitives** — `merge-settings.sh`, `merge-claude-md.sh`, `deploy-skills.sh`, `deploy-agents.sh`, run in that order, with no arguments, at init, sync, upgrade and a capability's install, register, upgrade and uninstall. Each is optional: one the adapter does not ship is skipped silently, so write only those your harness needs.
  - `merge-settings.sh` combines a settings baseline and the project's additions into the harness's fixed-path file (per COR-002), typically from a `core/` + `project/` split inside a `settings/` directory (the universal area pattern applied internally).
  - `merge-claude-md.sh` makes the harness's instructions file load the methodology's rules. The lifecycle calls it by this name whatever that file is called in your harness.
  - `deploy-skills.sh` and `deploy-agents.sh` put the skills and agents where the harness looks for them, and drop what they deployed from a source that is gone.
- **Undeploy primitive** — `undeploy-capability.sh <capability-name>`, removing what the deploy scripts put in the harness for that one capability, recognised by their deploy mark. The lifecycle runs it when it unregisters a capability whose files stay. Unlike the deploy primitives, its absence is reported: the lifecycle names an adapter that ships none in a `warning` line, since its harness keeps the capability active. An adapter that deploys nothing per capability ships one that does nothing.
- **What every script owes** — it is executable, with an interpreter line, since the lifecycle starts it from the project root; it is idempotent; and it exits non-zero only when it fails, which stops the lifecycle command with an error naming it.
- **Hook configuration** — if the harness supports hooks.

Skills, agents, and decisions live in their own harness-agnostic areas (per COR-006); the adapter only translates them at deploy time.

### 6. Declare the harness's support

Write `.pkit/adapters/<name>/harness-support.yaml`, shaped by `.pkit/schemas/harness-support.schema.json` (COR-047 point 2). Give one answer to each requirement in `.pkit/schemas/harness-requirements.yaml`: its `grade` (`supported`, `at-cost` or `not-achievable`), the `cost` of an `at-cost` answer, its `harness_versions` (`unbounded`, the `[lowest, highest]` you tested, or `[]`) and its `evidence`. The adapters README, "Harness requirements", says what each means. Answer only what you have evidence for. A requirement you leave out reports `indeterminate`, which is honest; a guessed grade is not. Then run `pkit validate` and `pkit harness report --adapter <name>`, and say the answers in prose in the adapter's README.

### 7. Self-check

Walk the adapter against the COR-005 universal-element checklist:

- *Does the adapter have a `README.md`, a `package.yaml` and a `migrations/` folder?*
- *Does the `README.md` cover what the adapter handles, what's shipped, and how to deploy it?*
- *Is each script named as the lifecycle calls it, executable, and idempotent? Re-running it should be a no-op.*
- *Does the adapter ship `undeploy-capability.sh`? Without it, a capability uninstalled with its files kept stays active in the harness, and the lifecycle warns.*
- *Does the adapter respect COR-006's harness-agnostic discipline — core content lives at canonical paths, and the adapter only translates at deploy time?*
- *Does every answer in `harness-support.yaml` rest on evidence, with its versions bounded to what was tested?*

If any check fails, revise.

### 8. Commit

Per COR-008, conventional-commits format. Type is `feat`; scope is `adapters` (or the adapter name if more specific):

```
feat(adapters): add <name> adapter

<body — 1–3 paragraphs naming the harness, what content the adapter
translates for, and any harness-specific deployment notes>
```

The adapter lands at `version: 0.1.0`. Subsequent bumps follow the same surface-change rule the methodology uses for its own backbone.

## Variations

- **Adopters authoring their own adapter** — same procedure, same command. An adopter using an in-house AI harness creates the adapter under their own copy of the methodology and contributes it back upstream if generally useful.
- **Adding an adapter for a harness already shipped** — refuses by design. To extend an existing adapter, edit its files (core-side if you're a methodology maintainer; via the methodology's extension mechanisms otherwise).
