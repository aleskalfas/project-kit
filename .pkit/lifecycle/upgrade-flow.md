---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/upgrade.py
        - src/project_kit/sync.py
        - src/project_kit/install.py
        - src/project_kit/capabilities.py
        - src/project_kit/manifest.py
        - src/project_kit/migrations.py
        - src/project_kit/loaded_rules.py
        - src/project_kit/connections.py
        - src/project_kit/router.py
        - src/project_kit/versioning.py
        - src/project_kit/provisioning.py
        - src/project_kit/visibility.py
        - src/project_kit/workspace.py
        - src/project_kit/agents_overlay.py
        - src/project_kit/settings_consolidate.py
        - .pkit/lifecycle/ownership.py
        - .pkit/migrations/backbone/2.0.0/002-move-answers-to-files.sh
        - hatch_build.py
        - tests/test_area_name_clash.py
      record: [COR-001, COR-010, COR-011, COR-015, COR-017, COR-030, COR-031, COR-041, "COR-053#6", "COR-059#5", "COR-059#6", "COR-059#7", "COR-059#8", "COR-059#9", "COR-062#11", "COR-070#3", ADR-033, ADR-039, ADR-049, ADR-059, ADR-064, ADR-065, ADR-076, "ADR-089#4", "ADR-089#5"]
      artefact:
        - .pkit/lifecycle/manifest.md#backbone-manifest-projectpkitmanifestyaml
        - .pkit/lifecycle/manifest.md#where-a-capabilitys-manifest-lives
        - .pkit/lifecycle/manifest.md#an-adapters-manifest
        - .pkit/lifecycle/manifest.md#a-data-points-question
        - .pkit/lifecycle/manifest.md#how-the-wiring-is-resolved
        - .pkit/lifecycle/manifest.md#the-connection-documentation-and-friction-blocks
        - .pkit/lifecycle/migrations.md#three-scopes-per-tier
        - .pkit/lifecycle/migrations.md#script-contract
        - .pkit/lifecycle/component-registry.md#install-pre-flight-checks
---

# The upgrade flow

How a version transition moves a project to a release, what guards it, and how one capability moves on its own ([COR-059](../decisions/core/COR-059-version-transition.md)).

## Contents

<!-- pkit:contents -->
- [The steps of a transition](#the-steps-of-a-transition)
- [Seed paths](#seed-paths)
- [A new collision](#a-new-collision)
- [The capabilities' rules index](#the-capabilities-rules-index)
- [What a step newly binds](#what-a-step-newly-binds)
- [A clash of area names](#a-clash-of-area-names)
- [The dependency gates](#the-dependency-gates)
- [What the settings merge widens](#what-the-settings-merge-widens)
- [Two recorded states, and an interrupted upgrade](#two-recorded-states-and-an-interrupted-upgrade)
- [Rolling back an upgrade](#rolling-back-an-upgrade)
- [The replay: a missing completion](#the-replay-a-missing-completion)
- [Sync's guard: no path down, and no migration passed over](#syncs-guard-no-path-down-and-no-migration-passed-over)
- [Per-component upgrade](#per-component-upgrade)
<!-- /pkit:contents -->

## The steps of a transition

The upgrade command transitions an adopter project to a target backbone version. It runs inside the backbone's two recorded states: it records its target first and its completion last (below). Every migration runs inside it, in COR-010's order:

1. **Compatibility and collisions.** Each check may refuse, and none writes.
   - **A component its bundle ships older:** an adapter or a capability the running pkit's bundle ships older than the version the project records refuses the transition. The refusal names the component, both versions, and a pkit whose bundle ships that version or newer. No flag overrides it.
   - **A clash of area names:** a project's own area at `.pkit/lifecycle/` refuses the transition ("A clash of area names", below). No flag overrides it.
   - **A file that is not the capabilities' rules index:** a file at `.pkit/rules/capabilities.md` <!-- unanchored: names the file the step reads or writes, not its content --> whose first line is not the backbone's marker refuses the transition ("The capabilities' rules index", below). No flag overrides it.
   - **Compatibility resolution:** each installed component's post-upgrade `requires_backbone` must admit the target. It is read from the bundle where the bundle ships the component, and from the installed copy where it does not. Conflicts are surfaced so the adopter can address them: upgrade specific components, pin the backbone, or remove an incompatible component.
   - **The dependency gates** run over the set the transition would leave ("The dependency gates", below).
   - **The collision flow** asks about each new naming collision, or refuses ("A new collision", below).
2. **The target is recorded.** `backbone_version` becomes the target, by an edit of its own line, before anything else is written ([`manifest.md`, "Backbone manifest"](manifest.md#backbone-manifest-projectpkitmanifestyaml)). `completed_version` keeps its value or stays missing. Each capability manifest still at its root then moves under its `project/` ([`manifest.md`, "Where a capability's manifest lives"](manifest.md#where-a-capabilitys-manifest-lives)). Each skip chosen in step 1 is recorded there, and each project artefact an override chose to replace is removed.
3. **Propagation at the target.** The propagation step `pkit sync` runs copies the target's content (per COR-001). It copies the backbone's trees, adapters included, and every installed kit-shipped capability the target ships, with its skips. The upgrade calls the step, never the sync command, so sync's guard never stops it. After the copy, in this order:
   - an adapter the copy placed that the registry lacks is registered, and recorded at the version it ships
   - `.pkit/.gitignore` <!-- unanchored: names the file the step reads or writes, not its content --> is rendered, so a migration reads the render of the target's declarations
   - the upgrade says what the copy newly binds of each loaded set it delivered ("What a step newly binds", below)
4. **Backbone migrations** run in order ([`migrations.md`, "Three scopes (per tier)"](migrations.md#three-scopes-per-tier)): manifest-schema → structural → resource-scoped. They run each folder in the window from the recorded completion, `completed_version`, to the target ("The migration window", below). With no completion recorded, every backbone migration up to the target runs (the replay, below).
5. **Adapter migrations** run for each adapter, from the version its manifest records, in version order with the same scope ordering within each `<major>.<minor>.0/` directory. Their scripts are read from the running pkit's bundle, as a capability's are. Each registered adapter is then recorded at the version the target ships. One with no manifest runs no migration ([`manifest.md`, "An adapter's manifest"](manifest.md#an-adapters-manifest)).
6. **Capability migrations** run for each copied capability, dependencies first by their `requires_capabilities` (COR-030), each from the version it records. Each capability is then restamped at the version it ships. One with no readable version runs none and is recorded at that version.
7. **Seed paths.** Each one that is missing is created, never over one that exists ("Seed paths", below). They follow the migrations, so a migration that moves a project's file to a seed path finds no fresh seed there.
8. **Derivable state.** Each component's setup primitive re-applies the kit-side spec at its current version and the adopter's config, idempotently:
   - the capabilities' rules index rendered again
   - merge delivery in its tier that asks nothing
   - deploy
   - `.pkit/.gitignore` <!-- unanchored: names the file the step reads or writes, not its content --> rendered again
   - pkit's private region of the local exclude file where the project is private
   - the agent workspace
   - provisioning

   The report lists each widening the settings merge brings ("What the settings merge widens", below).
9. **The completion is recorded.** `completed_version` becomes the target, by an edit of its own line.
10. **The pin,** the last of the upgrade's writes.

**After the transition, the questions.** Once the pin is written, the upgrade runs every question a data point declares, where a person can answer. Otherwise it prints the command for each ([`manifest.md`, "A data point's question"](manifest.md#a-data-points-question)). They are no step of the transition (COR-059 point 5).

Every write of the upgrade is made before the first question starts. So a question that fails or is stopped leaves nothing of the upgrade to finish.

**Already current:** upgrade returns early, before step 1, writing or raising only its pin, when all of these hold:

- `backbone_version` and `completed_version` both name the target
- every registered adapter and shipped capability records the version the target ships, each capability under its `project/`

Otherwise upgrade runs, to finish what is not, even at the same backbone version.

**The migration window.** Steps 4 to 6 each run the folders above a lower bound and at or below the target by minor. The lower bound is the completion for the backbone, and the version its manifest records for each component. It is read in PEP 440 order, where a release candidate sorts below its final release.

- **A move to a candidate,** such as `0.55.0rc1`, runs the folder of its final release, `0.55.0/`.
- **For a release version,** the window holds the minors above the one recorded.
- **Public versions:** every comparison of a recorded version with the version the target ships, the early return's among them, reads both as public versions. The pre-release is kept and a local segment dropped, so `0.55.0rc1` reads below `0.55.0`, and `0.6.0+x` reads as `0.6.0`.

**The report and the dry run** name the target, each component's move, and the replay where no completion is recorded. They list each component's migrations, each collision the upgrade asks about, and each question it would ask. `--dry-run` asks nothing and writes nothing.

## Seed paths

One seeding step creates the paths a project is seeded with:

- each area's `project/` folder
- the scratchpad's state folders
- the agents overlay (`.pkit/agents/project/overlay.yaml` <!-- unanchored: names the file the step reads or writes, not its content -->)
- each adapter's `settings/project/settings.json`
- each shipped capability's `project/` folder

Each seed path that is a folder holds an empty `.gitkeep`. First install and a version transition run the seeding step, and create each one that is missing, never over one that exists. Sync runs none (COR-059 point 8), so a seed the project deleted on purpose does not come back on a sync. The next transition creates it again.

## A new collision

A new collision is a skill or agent name that meets both of these:

- a shipped capability's target version ships it, in either of its forms (COR-015)
- another installed artefact already uses it: the project's own, or an incubated or no-longer-shipped capability's

A name the capability's installed copy holds, or its manifest records as skipped, is not new.

- **The flow is COR-017's install-time flow.** Where a person can answer, with standard input and standard output both terminals, the upgrade asks for each collision:
  - **skip:** the copy leaves the capability's artefact out. Its manifest records the skip in step 2, before the copy, so an interrupted upgrade does not ask again.
  - **override:** the capability's artefact replaces the project's, which git keeps. The project's is removed in step 2, before the copy. So an interrupted upgrade finds the name in the capability's installed copy, and does not ask again. Nothing is recorded.
  - **override of another capability's agent:** it removes nothing. Step 2 records the capability being moved as the project's choice for the agent's name, in place of any earlier choice (COR-017). The backbone manifest keeps it, under `agent_choices`.
  - **inspect:** shows the diff and asks again.
- **With nobody to answer,** the upgrade refuses before it writes anything. It names two ways on: run it again at a terminal, or rename the project's artefact.
- **No capability is held back,** so the project stays at one release (COR-059 point 7).
- **What the flow leaves out:**
  - a core skill or agent a release adds, which a project artefact of the same name suspends by deploy's name precedence
  - a clash between two artefacts one release ships, core's or a shipped capability's, which is the release's to prevent
  - a collision with externally-sourced content, which surfaces as COR-041 sets
  - a core area whose name a project's own area takes, which stops the upgrade instead ("A clash of area names", below)

## The capabilities' rules index

The backbone renders the capabilities' rules index, `.pkit/rules/capabilities.md` <!-- unanchored: names the file the step reads or writes, not its content -->, at each step below, and refuses a file at that path that is not the index. What the index is, and how a session reaches it, is [the rules reference's](../rules/README.md#the-capabilities-rules-index) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->.

- **Rendered whole,** each time after the manifest is written:
  - at first install, sync, the self-host branch and a transition's step 8
  - at a capability's install, register, upgrade and uninstall

  No migration reads it, so step 3 does not render it.
- **Never a synced copy.** The ownership predicate answers it as it answers `.pkit/.gitignore`. So sync never copies the methodology's source's own index, and the packaging leaves it out of the bundle.
- **A file that is not the index:** a file at its path whose first line is not the marker is someone else's. The transition's step 1 and sync, before they write, refuse, naming the file. Nothing overrides it. An empty file is no clash.
  - Move the file elsewhere, or remove it, and run the command again.
- **Adapters that differ:** while registered adapters declare different `entry:` forms, the render writes nothing and says so, and validation fails.

## What a step newly binds

Install, sync and upgrade, and a capability's install, register and upgrade, print what they newly bind of each loaded set they deliver ([COR-070](../decisions/core/COR-070-capability-loaded-rules.md) point 3).

- **Which sets:** core's `OPS` and each capability's alike.
- **What they print:** for each set, its name and version, and each rule it newly binds, changes or retires since the copy it replaces. A first install lists every accepted rule.
- **An upgrade from a version before core's rule set:** it cannot tell which of `OPS`'s rules bound before. Until then, the project's sessions loaded `.pkit/rules/core.md` <!-- unanchored: names the file the step reads or writes, not its content --> as a plain file, whose rules carry no ids to compare by. So the upgrade says so, and lists each rule the set holds after `holds`, none as newly bound.
- **The comparison:** one comparison, for every step, of two readings of a set's accepted rules, by id, status and statement. The readings are the set the project holds, read before the copy, and the set the step copies.
- **Rules that bind no session:** where no adapter in use declares `loaded_rules:`, a capability's set says that its rules bind no session in the project. It does not list them as bound.
- **The lines inform, and stop nothing:** installing the capability is the consent to its rules.

## A clash of area names

A project may create its own area at `.pkit/<name>/` (COR-011). A release that later ships a core area of the same name would copy over it, so the upgrade stops first.

- **The one clash among published releases:** a project's own area at `.pkit/lifecycle/`, made at a release before v1.149.0, which first shipped the core `lifecycle` area.
- **How it is told apart:** the core area holds `ownership.py`, and a project's own area does not. So anything else at `.pkit/lifecycle` is a clash: a folder without that file, a file, or a link. An empty folder is not.
- **Where it stops:** the upgrade, in step 1, and the propagation step, before it writes the methodology's trees. So `pkit sync` stops on it too. The stop writes nothing, stops under `--dry-run` too, and takes no override, `--force` included.
- **The message** names the path, and the running release, which ships the core area. It names the ways on:
  - move the project's area to another name, with what refers to it, and run the command again
  - after the upgrade's stop, to stay at the release the project records: `pkit pin` in an unpinned project. A project pinned at that release needs nothing, since its pin did not move.
  - where the methodology's own area has lost `ownership.py`: restore it from git, or remove the folder where git holds no copy of it
- **The copy writes `ownership.py` first** in that area. So an interrupted copy leaves the folder empty or holding the file, never a clash.
- **What the test cannot tell apart,** and the upgrade's copy writes over until the full check:
  - a project's own `lifecycle` area that holds a file named `ownership.py`
  - a project's own area under a name core shipped before v1.134.0, in a project still at a release before core shipped that name
  - a project's own area at `.pkit/rule-sets/`, made at a release before the one that first ships the core `rule-sets` area
- **No release adds a core area or a core adapter** until the full check, but `rule-sets`, where the backbone keeps its method rule sets. Every Markdown file there but its `README.md` is read as a rule set the backbone ships. So a project has no use for an area of that name.
  - The exception is no precedent. A test holds the areas a release propagates, `rule-sets` among them, the adapters it ships, and the core area's `ownership.py` to what they are today.

## The dependency gates

The gates run as `pkit capabilities upgrade` runs them (COR-030, COR-053 point 6), over the set the transition would leave. That set holds every shipped capability the bundle ships at its bundled version, and every other capability at its installed version. Within one release the moving capabilities agree, so a conflict involves a capability that does not move: an incubated, externally-sourced or no-longer-shipped one.

- **A moving capability** refuses, with a hint, when a dependency its new version requires is not installed, or is out of the range it declares. So does one whose new version carries a mandatory process connection the set leaves unmet. No flag overrides the refusal. An optional dependency that is not installed passes.
- **A moving dependency** warns when its new version falls outside the range a capability that does not move declares for it, naming each such dependent. So does one that leaves such a capability's mandatory connection unmet. The upgrade proceeds only under `pkit upgrade --force`, so neither is a hard block.
- **`--force` overrides those two warnings and nothing else.** It overrides no guard, no compatibility refusal, no refusal of a component bundled older, no collision, and no clash of area names.
- **Not the upgrade's to judge:** a pair in which neither side moves, and a mandatory connection of a capability that does not move, already unmet before the upgrade.
- **How a range is read:** with its pre-releases admitted, by every check of a range, compatibility resolution and validation among them. So a range admits a release candidate within its bounds, and `>=2.0.0` and `<2.0.0` both refuse `2.0.0rc1`.

## What the settings merge widens

The merge delivery in step 8 may add to the settings file the adapter's merge writes, `.claude/settings.json` <!-- unanchored: names the file the step reads or writes, not its content --> for Claude Code.

- **The report:** the upgrade reads the file before and after the merge. Its report lists each allow entry and each top-level key the merge adds, such as `hooks`, `env` or `sandbox`.
- **The question back:** an `ask` rule for an entry, in the project's additions to the adapter's settings, brings the question back.
- **The changelog:** a release's changelog names each widening too. A change that adds an allow entry or a top-level key to an adapter's baseline settings says so in its changeset.

## Two recorded states, and an interrupted upgrade

A transition is complete when its two recorded states are equal (COR-059 point 6, [`manifest.md`, "Backbone manifest"](manifest.md#backbone-manifest-projectpkitmanifestyaml)). The target is written first, so an interrupted transition never reads as finished. An older pkit that refuses a project ahead of it reads only `backbone_version`, finds a version newer than its own, and refuses.

- **An interrupted upgrade is finished by the next one.** A migration that exits non-zero stops the upgrade: the completion is not recorded, and no pin is written. The next upgrade finds the two keys apart, propagates again, and runs the backbone migrations from `completed_version`, the stopped one included. So a migration may fail loudly.
- **A migration that fails every time** is fixed at its cause, and the upgrade is run again. Or the upgrade is undone with git, which restores both keys ("Rolling back an upgrade", below).
- **A sync between the two** stops: its guard finds them apart and names `pkit upgrade` ("Sync's guard", below). Sync moves no recorded version.
- **First install records the same two states:**
  - the target, before it copies anything
  - each adapter, registered and recorded after the copy
  - the completion, last

  The next upgrade finishes an interrupted install.

## Rolling back an upgrade

A project goes back to an earlier release with git, by reverting the commit of each upgrade since that release. It never goes back with pkit, since pkit's migrations run forward only (COR-010). Each revert restores every file its upgrade changed, in `.pkit/` and outside it.

- **What an upgrade writes outside `.pkit/`:**
  - the derivable state and merge delivery of step 8 (the lifecycle README, "What sync writes"). Among them are the deployed skills and agents, and the settings file the adapter merges.
  - each file a migration edits, which may be one of the project's own artefacts. The 2.0.0 move of answers, `2.0.0/002-move-answers-to-files.sh`, rewrites the front matter of each of the project's own artefacts whose block holds an answer (COR-062 point 11).
- **Not `.pkit/` alone:** `git checkout <ref> -- .pkit/` restores only what lies in `.pkit/`. After the 2.0.0 move, the checkout leaves the blocks of the artefacts outside `.pkit/` without their answers, so an older backbone reads none there. Nor does it remove a file the upgrade added in `.pkit/` that `<ref>` does not hold.
- **A revert moves no installed pkit.** Where pkit then runs a release other than the project's, sync's guard stops `pkit sync` and names the remedy ("Sync's guard", below).

## The replay: a missing completion

With no `completed_version`, the project's backbone migration history is unknown (COR-059 point 6). Its next upgrade runs every backbone migration up to its target, once. Each component's migrations still run from the version its manifest records.

- **When:**
  - a manifest written before the release that added the key
  - a missing manifest, which upgrade writes at its target as first install does
  - a `backbone_version` that is no version
- **What it may restore:** a migration that adds a missing default can add one the project removed after the migration first ran. The release's notes say so ([`migrations.md`, "Script contract"](migrations.md#script-contract)).
- **What the operator sees:** the report says that no completion is recorded, so every backbone migration runs once, and lists them. `--dry-run` says the same before anything runs, listing the scripts of the running pkit's bundle.

## Sync's guard: no path down, and no migration passed over

One guard keeps a pkit at another version than the project's from writing its release over the project's (COR-059 point 9). It reads the backbone manifest's two recorded states and the pin (`.pkit/version-pin`), and compares them with the running pkit's version. It compares public versions, as the migration window does ("The steps of a transition", above).

The content a sync writes, and the target of a backbone upgrade, is the running pkit's own version. A release's content is tied to its code. That version can be another than the project's:

- a pin raise leaves the installed tool where it was
- an installed tool moves on its own
- when the entry-point router cannot fetch a project's pin, it runs the installed tool instead

The comparison vouches for content only under a tagged install, the one the CLI README recommends ("Installing pkit on PATH"). The development install, from main, carries the last release's version over files that may be newer. So no version vouches for its content.

- **`sync` calls it in both directions,** at its entry, before anything is written. Sync runs no migration, so stopping is what keeps a migration from being passed over. It stops when any of these holds:
  - the manifest is missing, or its `backbone_version` is no version
  - the running pkit is not `backbone_version`
  - `completed_version` differs from `backbone_version`, or is missing
  - the pin is newer than the running pkit
- **`capabilities install` and `capabilities upgrade` call it in both directions too,** at their entry, before they read or write anything ([`component-registry.md`, "Install pre-flight checks"](component-registry.md#install-pre-flight-checks)). Each copies the capability the running pkit's bundle ships. So each stops in sync's states, with sync's remedies, the command named as the operator would run it again.
  - **So every shipped file a project holds comes from the release its backbone records,** wherever a version names one content. A version names one content under a tagged install, the one the CLI README recommends ("Installing pkit on PATH").
  - **`capabilities register`** copies nothing and does not call the guard.
- **`upgrade` calls it in the older direction only,** before it writes anything. It refuses a running pkit older than the newest of `backbone_version`, `completed_version` and the pin. It calls the propagation step, never the sync command, so the sync command's guard never stops it.
- **How it stops:** exit non-zero, name the state found and its remedy, and write nothing: no content, no manifest, no pin. No flag overrides it, `sync --force` and the capability commands' `--force` included, and a dry run stops too.

  The CLI README's `sync` entry carries the wording, and the router's notice when it runs a pkit other than the pin.
- **No path down:** migrations are forward-only (COR-010), and a pin is never moved down. So a project is rolled back with git, by reverting the commit of each upgrade since that release ("Rolling back an upgrade", above). The reverts restore kit-owned and project-owned state, both recorded versions included, together.
- **`upgrade` refuses under the router's fallback, in both directions.** When the router cannot fetch a project's pin, it runs the installed pkit and marks the run. Upgrade refuses that pkit when it is older than the pin or the content, and when it is newer. It refuses before its tool step and before it writes anything, and names the fallback's remedies. A run with routing bypassed on purpose (`PKIT_NO_ROUTE`) is no fallback.

Only an unambiguous order is compared:

- a pin that is not a version blocks nothing
- a `backbone_version` that is no version stops sync, and is one `pkit upgrade` records its target over

Read-only commands are unaffected.

A pinned project's `upgrade` under its pin's code checks first for a newer release, and hands over to it. That release's upgrade finishes content left ahead of the pin by an interrupted raise. With no newer release, the check refuses such content before the run's own transition to the pin, which would take it down.

The methodology's source repository is exempt: its sync runs the self-host branch, and moves no version.

## Per-component upgrade

`pkit capabilities upgrade <name>` is a transition of one capability (COR-010). It runs in the transition's order for that capability alone, at the recorded backbone, and writes neither of the backbone's two recorded versions:

1. **Its checks,** each of which may refuse and none of which writes:
   - sync's guard, first, which stops the command wherever `pkit sync` stops ("Sync's guard", above)
   - the refusal of a capability the running pkit's bundle ships older than the project records, with no override. The message names both versions. It names `pkit upgrade` too, run by a pkit whose bundle ships the recorded version or newer, since the running pkit ships the project's own release.
   - its new version's `requires_backbone` against the recorded backbone
   - the dependency check in both directions (below), and its mandatory process connections
   - the collision flow. A new collision is asked about only under `--interactive`. Without the flag the command refuses and names it.
2. **Its manifest,** still at the capability's root, moves under its `project/` before the copy ([`manifest.md`, "Where a capability's manifest lives"](manifest.md#where-a-capabilitys-manifest-lives)). Before the copy too, each skip chosen in step 1 is recorded there, and each project artefact an override chose to replace is removed.
3. **Its copy,** with its skips, then `.pkit/.gitignore` <!-- unanchored: names the file the step reads or writes, not its content --> rendered, so a migration reads the new version's render. It creates no seed path.
4. **Its migrations,** after the copy, from the version it records, then its restamp at the version it ships. One with no readable version runs none.
5. **Its derivable state:** the capabilities' rules index rendered again, merge delivery and deploy, its query commands' provisioning, and `.pkit/.gitignore` <!-- unanchored: names the file the step reads or writes, not its content --> rendered again. The upgrade says what its copy newly binds of the capability's loaded set ("What a step newly binds", above).

**After it, the questions** of the points the capability defines and of the points its contributions reach. They are asked where a person can answer, and printed otherwise ([`manifest.md`, "A data point's question"](manifest.md#a-data-points-question)). They are no step of the transition. An incubated capability's upgrade, and one in the methodology's source, end with them too.

`pkit capabilities upgrade` finishes a capability that an interrupted transition of that capability, or an untagged install, left behind. Over an interrupted transition of the backbone, sync's guard stops it and names `pkit upgrade`, which finishes that transition.

The command moves the capability to the version the running pkit's bundle ships. Sync's guard stops it under any pkit but the project's version. So that is the version the project's recorded release ships (COR-010), wherever a version names one content. A version names one content under a tagged install, the one the CLI README recommends ("Installing pkit on PATH").

### Upgrading an incubated capability (COR-031 D1/D4)

`pkit capabilities upgrade <name>` is **origin-aware**. For an `incubated-in-repo` capability there is no kit source to resolve against: the working tree *is* the source. So the command **must not** route through the kit-source resolution path.

Instead, "upgrade" for an incubated capability **re-applies deploy from the in-repo tree**, mirroring sync's skip-branch (the lifecycle README, "The incubated-origin skip-branch (COR-031 D1)"). Any newly-authored skills/agents re-materialise in the harness, and source-reconciliation stays suppressed. If the in-repo subtree has gone missing, the command reports that plainly — never as a kit-source orphan, and never suggesting uninstall.

Sync's guard runs at the command's entry, before the origin is read. So this re-deploy stops under another pkit too, as `pkit sync`'s re-deploy of it does. A `kit-shipped` capability's upgrade path is the transition of one capability above.

In the methodology's source repository, run by its own code, a `kit-shipped` capability's kit source *is* its subtree. So its upgrade re-applies deploy in place the same way: the deploy primitives re-run and its query commands are provisioned. Nothing is copied, no receipt is restamped and no migration is run. It is sync's self-host path for one capability.

For capabilities, a **direction-split dependency check (COR-030)** runs before collision detection:

- *Upgrading a dependent* — the new source version's `requires_capabilities` is checked against the installed dependency versions. If a required dependency is absent, or any installed one is out of range, the upgrade **refuses with an actionable hint**. An optional dependency that is not installed passes.
- *Upgrading a dependency* — installed capabilities that declare this capability in their `requires_capabilities`, required or optional, are checked against the new version. If the new version falls outside a dependent's declared range, the upgrade **warns loudly and requires `--force` to proceed** — it is not a hard block. Use `--force` as the by-hand analogue of cascade-upgrade, then upgrade the now-desynced dependents to restore consistency.

Both entry points run the same direction split, and compare a range through one relation. The backbone-wide `pkit upgrade` runs it over the set it would leave, every shipped capability at its bundled version ("The dependency gates", above). The single-capability `pkit capabilities upgrade <name>` runs it over the installed set with that one capability at its new version. The warn+force direction also applies at install and register ([`component-registry.md`, "Install pre-flight checks"](component-registry.md#install-pre-flight-checks)).

### Mandatory process connections (COR-053 point 6)

A capability's generated `depends-on` entries may carry a mandatory mark (the process area's connections page, "depends_on"). The mark means the upstream process definition must exist, offered at an equal interface version when the entry names one. The lifecycle is the mark's **one reader**, and it reads the mark from package metadata only, never by parsing process definitions. Validation keeps the list fresh against them ([`manifest.md`, "The connection, documentation and friction blocks"](manifest.md#the-connection-documentation-and-friction-blocks)).

It judges through the wiring resolver ([`manifest.md`, "How the wiring is resolved"](manifest.md#how-the-wiring-is-resolved)), over the wiring the operation would leave. That wiring is the installed set with the capability in place of any installed copy, or without it. So a mark refuses exactly when `pkit validate` would then report it unmet.

The disposition is COR-030's direction split:

- **The side carrying the mark is refused.** `install`, `register` and `capabilities upgrade` refuse a capability whose mandatory upstream would be missing, or offered at another interface version. There is no override.
  - **Missing upstream:** its capability not installed, no installed capability providing its role, or no such process offered or defined.
  - **The refusal:** one line per unmet mark with the mark's reason, and the hint to install or upgrade the upstream first.
- **The side the mark targets is warned.** `capabilities upgrade` and `uninstall` of a capability name every other capability whose mandatory mark the operation would leave unmet. Each such mark was met, or at least not already unmet, before the operation. A mark that was unmet before is not the operation's to report.
  - **Without `--force`:** they refuse.
  - **Under `--force`:** the warning is still printed and the operation proceeds. Never a hard block.

Two marks facing each other, each capability's mandatory connection needing the other installed first, are a cycle no install order satisfies. Validation rejects it, and the install plan reports it (COR-053 point 6).

The backbone-wide `pkit upgrade` runs the same split over the set it would leave, every capability it moves at its bundled version ("The dependency gates", above). It refuses a moving capability that carries a mark the set leaves unmet. For a capability that does not move, it warns, proceeding only under `--force`.
