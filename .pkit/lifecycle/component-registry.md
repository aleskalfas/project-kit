---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/capabilities.py
        - src/project_kit/install.py
        - src/project_kit/sync.py
        - src/project_kit/treecopy.py
        - src/project_kit/manifest.py
        - src/project_kit/declared_rule_sets.py
        - src/project_kit/package_validate.py
        - src/project_kit/capability_plans.py
        - src/project_kit/point_questions.py
        - src/project_kit/connections.py
      record: [COR-001, COR-005, COR-007, COR-010, COR-017, COR-030, COR-031, "COR-051#3", "COR-053#6", COR-061, "ADR-059", "ADR-065#7", "ADR-065#11"]
      artefact:
        - .pkit/lifecycle/manifest.md#discovery-what-a-capability-would-connect-to
        - .pkit/lifecycle/manifest.md#a-data-points-question
        - .pkit/lifecycle/manifest.md#how-a-registered-command-is-run
        - .pkit/lifecycle/manifest.md#validation-the-package-schema
        - .pkit/lifecycle/manifest.md#strict-on-unknown-keys
---

# The component registry

The backbone manifest's `components` list is the canonical install record. Each operation below reads or writes it, after the checks it runs first.

**Install** a component → run the pre-flight checks (below), create its per-component manifest at the designated path, then append a `{kind, name, manifest}` entry to `components`.

**Register an in-repo (incubated) capability** (COR-031) → a no-copy variant of install, for a capability the adopter authored in its own repository.

- **Its checks:** install's pre-flight checks, but those it skips ("Register pre-flight checks" below). It skips "exists in kit source", since the tree in the repository *is* the source. It skips "Rule-set names", which only install runs.
- **Its entry:** it appends a `{kind, name, origin: incubated-in-repo, manifest}` entry.
- **No copy:** it copies no subtree, and writes no per-component manifest, since the tree is the adopter's (COR-031 D2 and D3).
- **The same as install otherwise:** deploy primitives and dependency gating run as for install (COR-031 D1). Only source reconciliation differs (the lifecycle README, "The incubated-origin skip-branch (COR-031 D1)").

**Remove** a component → run refusal checks (see below), delete the registry entry, then delete the per-component manifest file. Adopter-owned content authored on top of the component (project-side records, customisations) is left untouched per COR-005 and the no-shared-files invariant. For a **capability**, whether the capability's *subtree* is also deleted is origin-dependent. A kit-shipped copy is deleted, an incubated (adopter-authored) subtree is kept unless explicitly purged (COR-031 D4, see "Uninstall: origin-aware removal" below).

**Status, validate and upgrade** walk the registry to find each component's manifest, then work per component.

**What a copy leaves out.** Every copy of a source tree into a project leaves out Python's caches. They are any `__pycache__` folder and any compiled `.pyc` or `.pyo` file in the source, which importing its scripts in place writes there.

- **The copies it covers:** the backbone's on `pkit init` and in the propagation step that `pkit sync` and `pkit upgrade` run. A capability's on install, in that step and in the refresh of `pkit capabilities upgrade`.
- **What it gives:** what a project receives does not depend on what ran in the source before the copy. One rule decides it for every copy path.

## Install pre-flight checks

`pkit capabilities install` runs sync's guard, then six checks in order, before it places any file.

**The version check comes first: sync's guard.** The install copies the capability that the running pkit's bundle ships. So it runs only where that pkit is the release the project records, over a finished upgrade. It stops in each state that stops `pkit sync` ([`upgrade-flow.md`, "Sync's guard"](upgrade-flow.md#syncs-guard-no-path-down-and-no-migration-passed-over)).

- **When it stops:** before anything is read or written, under `--dry-run` and `--plan` too. Under another pkit, both would preview another release's capability.
- **No override:** nothing overrides it. Its message names sync's remedies for the state it finds.
- **The methodology's source** is exempt, as it is for sync.

**The six checks.** `--plan` runs after the first, since an installed capability has no install plan. It stops there, and writes nothing.

- **What the plan covers instead:** what the backbone, dependency and mandatory-connection checks would refuse on is among what the plan says the capability needs ([`manifest.md`, "Discovery"](manifest.md#discovery-what-a-capability-would-connect-to)). A range that an installed capability declares on it is among the findings the plan adds.

1. **Already installed?** Refuse with a hint to use `upgrade`.
2. **Backbone compatibility.** The capability's `requires_backbone` range must include the current backbone version. Install and register run this one shared gate, the copy from the kit source and the incubated capability in place (COR-007). So neither can activate a capability that the current backbone cannot support.
3. **Capability dependencies (COR-030), in both directions.**
   - **The ranges the capability declares.** Each required dependency in its `requires_capabilities` must be installed. Each installed dependency's recorded version must fall within the declared semver range. An optional dependency that is not installed passes. Refuse with an actionable hint that names what to install or upgrade first, and never install anything automatically.
   - **The ranges declared on it.** Its version must fall within each range an installed capability declares for it, whether that entry is required or optional. Outside one, warn, naming each such dependent and its range, and refuse unless `--force` is given. Under `--force` the warning is still printed and the install proceeds, as an upgrade of a dependency does ([`upgrade-flow.md`, "Per-component upgrade"](upgrade-flow.md#per-component-upgrade)). The check is the upgrade's own, with the same range comparison.
4. **Mandatory process connections (COR-053 point 6).** Every `depends-on` entry the capability marks mandatory must find its upstream, at an equal interface version where it names one. Refuse, one line per unmet mark with its reason ([`upgrade-flow.md`, "Mandatory process connections"](upgrade-flow.md#mandatory-process-connections-cor-053-point-6)). Never install anything automatically.
5. **Rule-set names (COR-051 point 3).** No rule set the capability ships may take a name that a project rule set already declares. A set's name is in each of its rule ids, so the clash could not be undone once installed. Refuse, one line per clash, naming the set, the capability's file and the project's.
6. **Naming collision detection.** The new capability's skills and agents must not collide with names already installed. Interactive resolution is available.

**The declared project rule set.** After the copy and the registration, install creates the one project rule set the capability declares ([COR-017](../decisions/core/COR-017-capability-pattern.md)), once for this install. Running install is the consent. One computation decides it, which the reading command `pkit capabilities project-rule-set` gives too ([`manifest.md`, "How a registered command is run"](manifest.md#how-a-registered-command-is-run), "The seams back").

- **The file:** `rule-sets/<name in lower case>.md` under the internal documentation root. That is the project's own rule-set place, so the backbone finds it with no configuration. It holds the declared name and scope, version `1.0.0`, no rules, and `inherits: [<capability>:<SET>@<major>]`. The major is the method set's, in the copy being installed.
- **Where none inherits.** No set of the project's own may inherit the method set, directly or through other sets, as the rule-set reader judges it. Where one does, install creates none and names it.
- **Never over the project's content.** Install creates none where any of these holds. It then says why in a `warning` line, and goes on:
  - a project rule-set file cannot be read
  - any rule set takes the name
  - a file lies at the path, or where its folder would be
  - the path runs through a link
  - the write itself fails
- **Never again.** Sync, a transition and a later install of an installed capability never create or change it. It is no seed path. `--dry-run` says what it would create, and register creates none.
- **Earlier installs.** A capability's migration creates the set for a project that installed the capability before it declared one.
  - It reads the plan through `pkit capabilities project-rule-set <name> --json`.
  - It writes the `text` given, where `creates` is `true` and the file is still missing.
  - It never fails the upgrade when the answer cannot be read. It warns, and names the command.

**The questions its points declare.** Install ends, after the deploy, with the questions of the points the capability defines and of the points its contributions reach ([COR-061](../decisions/core/COR-061-point-questions.md)). They are asked where a person can answer, and printed otherwise ([`manifest.md`, "A data point's question"](manifest.md#a-data-points-question)).

- `--dry-run` names them.
- Register ends with them too, where it registers the capability.
- A capability already registered, or adopted in place, is asked nothing.

**In the methodology's source repository, run by its own code,** the capability's subtree lies in the tree that the running code installs from. The source is the destination, so install places none of the capability's files.

- **What it does instead:** after the first five checks, it registers the capability in place with origin `kit-shipped`, and deploys it. It makes no copy, no per-component receipt and no `project/` stub.
- **The declared project rule set:** install creates it as anywhere, since that set is the project's file.
- **Collisions:** its collision check is register's, since the capability's own artefacts are no collisions against themselves. A collision with other content is refused, since nothing is copied that could be skipped.
- **Any caller:** beneath the verbs, a capability copy whose source and destination are one tree is refused.

## Register pre-flight checks (incubated; COR-031)

`pkit capabilities register` runs the install checks that still apply, and adds one of its own.

- **The checks it shares:**
  - backbone satisfaction
  - capability dependencies in both directions, with the same `--force`
  - mandatory process connections
  - collision detection against *other* installed content
- **The checks it skips:**
  - "exists in kit source", since the tree in the repository *is* the source
  - "Rule-set names", which only install runs
  - sync's guard, since it copies nothing, so it runs under any pkit
  - the check of the ranges declared on it, where it adopts a capability already registered in place, since that moves no version

**Self-consistency validation (COR-031 D1).** Register adds this one check. The adopter wrote the capability by hand, and nothing upstream validated it. So before activation, register checks these against the working tree, which is the capability's spec:

- its own `package.yaml`, through the package validator that `pkit validate` uses ([`manifest.md`, "Validation: the package schema"](manifest.md#validation-the-package-schema)). Only its errors refuse, an unknown key among them ([`manifest.md`, "Strict on unknown keys"](manifest.md#strict-on-unknown-keys)).
- the required layout, `README.md`
- its own schema pairs, through the validator that `pkit schemas validate` runs

It refuses with the structural problems listed. This is self-validation, not source reconciliation. Origin suppresses the latter, never the former (the lifecycle README, "The incubated-origin skip-branch (COR-031 D1)").

## Uninstall: origin-aware removal (COR-031 D4)

`pkit capabilities uninstall` first runs three refusal checks, and `--force` defeats each. `--plan` runs before them and stops there, writing nothing ([`manifest.md`, "Discovery"](manifest.md#discovery-what-a-capability-would-connect-to)).

1. **Declared dependents (COR-030).** If any installed capability lists this one as a required dependency in its `requires_capabilities`, refuse and name the dependents. The operator must uninstall or upgrade the dependents first. An optional dependency never blocks the uninstall. The dependent works without the capability it names, and its own runtime guard covers the absence.
2. **Mandatory process connections (COR-053 point 6).** If the removal would leave another capability's mandatory `depends-on` mark unmet, warn and refuse. The warning names each counterpart with its mark's reason. Under `--force` the warning is still printed and the removal proceeds ([`upgrade-flow.md`, "Mandatory process connections"](upgrade-flow.md#mandatory-process-connections-cor-053-point-6)).
3. **References.** Refuse, and list the references, where either of these holds:
   - an adopter-authored file cites the capability, by a citation token or a path reference
   - a project rule set's `inherits` names one of its method sets, read as data whatever the list's form (COR-017). The project rule set that install created is one.

Once those pass, **what gets deleted depends on origin** — origin-blind deletion would destroy adopter-authored work, the exact hazard COR-031 exists to prevent:

- **`kit-shipped`** — the subtree is a disposable copy of kit source. Uninstall deletes the subtree, removes the registry entry, and re-runs deploy (deploy's stale-removal pass then drops the harness symlinks, since the source is gone). Unchanged from before.
- **`incubated-in-repo`:** the subtree is the adopter's *only* copy of authored work. So uninstall unregisters in place. It removes the registry entry and drops the capability's deployed harness skills and agents. It leaves the authored subtree on disk, and the CLI reports "unregistered in place; your authored files are kept at `<path>`".
  - **The undeploy primitive:** a re-run of deploy would not drop the agents. The agents deploy keys its stale-removal on whether the *source file* still exists, and here it does. The skills deploy reads the registry, and would drop the skills. So the lifecycle runs each installed adapter's undeploy primitive, `undeploy-capability.sh <name>`, found by name as the deploy primitives are.
  - **What each side does:** the adapter removes what it deployed for that capability (the adapters README, "Primitives the lifecycle calls"). The lifecycle names the capability and carries no harness path.
  - **An adapter with no undeploy primitive** is named in a `warning` line, since its harness still carries the capability. It is never skipped silently.
  - **The order:** the undeploy runs before the registry entry is removed. So a failing adapter leaves the capability registered, and the uninstall can run again.
  - **`--purge`:** deleting an incubated capability's files is a separate, explicit opt-in. `--purge` confirms first, honouring the pause-before-destructive-ops discipline, and `--yes` skips the prompt for non-interactive use. The default never deletes incubated files.
- **The methodology's source repository, run by its own code:** whatever the origin, the subtree is never deleted. It is unregistered in place as an incubated one is, the adapters' undeploy primitives included.
  - **Its source, never a copy:** a kit-shipped or incubated capability's subtree is its source there. Uninstall keeps an externally-sourced one too, since it reads every subtree in the source as authored.
  - **A `kit-shipped` registration,** whose uninstall would otherwise delete the subtree: the CLI first says which subtree it would have deleted, and that it unregisters instead. It then asks: `--yes` answers, and `--dry-run` asks nothing.
  - **`--purge`** is refused there. A capability leaves the source through git.
  - **No caller deletes the source:** the guard resolves the running code's tree itself.
  - **Run by other code,** uninstall refuses there before anything else, as install, upgrade and register do.
