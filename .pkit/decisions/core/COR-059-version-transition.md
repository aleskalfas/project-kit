---
id: COR-059
title: A project stays at its version until a version transition moves it
status: proposed
date: 2026-10-13
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A project records which release of the methodology it holds: a version for its backbone and one for each component it installs (COR-010). Migrations bridge a project's state from one recorded version to the next, and COR-010 orders them inside an upgrade: compatibility, propagation, backbone migrations, component migrations, derivable state, and the recorded versions last.

No record says which operations may move a recorded version. When an operation other than the upgrade moves one, the migrations between the two versions are stranded:

- **A sync under a newer CLI** copies the newer content over the project's and records the newer version, but runs no backbone migration. The next upgrade finds the project at its target and runs none either.
- **An upgrade that records its version before its migrations,** and is interrupted during them, leaves the project at its target. Re-running it finds nothing to do.

Either way the project holds content its migrations never reached, and nothing says so.

The command surface stands in the way of the obvious fix. Moving a project to a new release takes the release's content, its migrations, a merge of its baselines and the new recorded versions together. COR-004 rejects exactly that compound: an "update" that does sync, merge and migrations. So the operation that moves a version anchors to nothing on COR-004's list of operations.

Externally-sourced content already keeps the routine operation from moving a version (COR-041). Sync brings the consumer's copy to its pin and moves nothing. Only an upgrade moves it, by repointing the pin.

## Decision

**A project stays at the versions it records. Reconciliation keeps the project in line with those versions, and moves none of them. A version transition is the one operation of the core layer that moves a recorded version, and every migration of what it moves runs inside it, under the one consent of choosing its target. It records its target before it writes anything and its completion only when every migration has run, so an interrupted transition is never mistaken for a finished one.**

The points that follow:

- **Points 1 to 3** say what a project records, what reconciliation does, and what a version transition is.
- **Points 4 and 5** say why a transition is one operation under COR-004.
- **Points 6 to 8** say how a transition records its progress, which components it moves, and which seed paths it creates.
- **Point 9** stops a command that would propagate content under another version than the project records.
- **Point 10** keeps a rewrite of the project's own content out of the transition.

### 1. A project records a version for its backbone and for each component it installs

- **What a recorded version names:** the release whose content the project holds, for the backbone and for each component (COR-010). While a transition is incomplete, the backbone's recorded version names the transition's target instead (point 6).
- **Where it sits:** out of propagation's reach, in the backbone manifest and in each component's project-side directory (COR-010, "Implications"). Copying the methodology's content never writes or removes a recorded version.
- **By origin** (COR-031):
  - a component the methodology ships records the version it shipped with
  - an externally-sourced component records its pin (COR-041)
  - a component authored in the project is the project's own, and its version moves when the project edits it. No operation of the core layer moves it.

### 2. Reconciliation runs at the recorded versions, and moves none

Reconciliation is the sync operation (COR-001), COR-010's Update. It is one operation: it regenerates the installed state from the spec at the versions the project records. The order COR-010 calls its reconciliation order is a transition's (point 6).

- **It moves no recorded version, and runs no migration.**
- **It writes three kinds of thing, and no other:**
  - methodology content at the recorded versions, by propagation (COR-001)
  - derivable state, regenerated from the project's own declarations (COR-010)
  - project-owned paths, through merge delivery only, in its auto-add tier (COR-002)
- **Its merge is regeneration.** COR-010 counts merged-config entries as derivable state, so the auto-add tier is part of the one operation. It never removes an entry. It adds nothing beyond the project's own additions, the grants of what the project has deployed, and the baseline of the release the project records, safety entries included (COR-002).
- **A merge tier that prompts never runs in reconciliation.** It runs only in merge's own command, at first install and in a transition, and only where a person can answer. With nobody to answer, it writes nothing.
- **It creates no seed path** (point 8). Merge delivery may create its own target file where that file is missing, as merge, not as seeding.
- **A component the running CLI ships at another version than the project records** is not copied, and reconciliation reports it.
- **An authoritative region** that a realizer manages in a project-owned file (COR-002, COR-028) is outside this record.

### 3. A version transition is the only operation of the core layer that moves a recorded version

- **What it is:** an operation that moves a project's recorded versions to a target. An upgrade is one.
- **It is one operation on COR-004's list,** beside propagation, seeding and merge.
- **Every migration of what it moves runs inside it,** backbone migrations first and then each component's. No other operation runs a migration of the backbone or of a shipped component.
- **What it writes:**
  - the target's content
  - every pending migration, with the writes that the records owning the written content allow, as COR-048 point 5 does for the configuration file
  - derivable state, merge delivery included
  - the seed paths point 8 names
  - the recorded versions
- **A transition may move one shipped component alone.** It moves that component to the version the project's recorded backbone ships with, and runs only under the CLI at that version (point 9).
- **An externally-sourced component** records its pin, and an upgrade moves it by repointing the pin (COR-041). Its content follows when reconciliation brings the copy to the pin. Whether and where its own migrations run is outside this record.

### 4. One consent covers a transition's parts

- **Choosing the target is the consent.** Every part of a transition follows from the target the person chose, so one consent covers them all.
- **What each part does depends on what it finds,** as propagation's copy does. What stays rejected under COR-004 is a verb that takes one and the same choice silently in one case and asks for it in another.
- **Some choices keep the consent their own records set:**
  - which of two colliding artefacts the project keeps (point 7, COR-017)
  - merge delivery's prompt-once tier (COR-002)
  - the explicit override that lets a dependency move outside a dependent's range (COR-030, COR-053 point 6)
- **Each is asked only where a person can answer, and none is ever taken silently.** With nobody to answer, a collision refuses the transition before it writes anything (point 7), the prompt-once tier writes nothing, and a dependency gate refuses without its override.

### 5. The one-operation rule governs operations on a project

- **COR-004's rule,** one operation for each command, governs what a command does to a project.
- **Updating the CLI installed on the machine acts on no project.** So a command may first update the CLI that runs it, and then perform its one operation.

### 6. A transition records its target first and its completion last

- **Two recorded states:**
  - **the target,** written as the backbone's recorded version before the transition writes anything else
  - **the completion,** the last of the recorded states, written once every migration has run and the derivable state is regenerated
- **A transition is complete when the two are equal.** Each component's record moves to the target when that component's migrations finish.
- **First install records both,** at the version it installs.
- **The next transition finishes an incomplete one.** It runs the backbone migrations from the recorded completion, and each component's from that component's own record.
- **A missing completion reads as incomplete, with no lower bound.** The project's backbone migration history is unknown, so its next transition runs every backbone migration up to its target, once. So every backbone migration must be safe to run over any state, a contract COR-010's migration rule takes (Implications).
- **The replay is the backbone's alone.** A component's migrations run from its own record.
- **A migration that fails stops the transition,** which stays incomplete. The next transition runs it again.
- **Reconciliation never runs over an incomplete transition** (point 9).

### 7. A transition moves every component the methodology ships together

- **One release for each project.** A transition moves the backbone, and every component the project installed from what the methodology ships, to the target's versions. No such component is held back at its old version.
- **A new collision is resolved inside the transition.** A shipped artefact whose name an artefact of the project already uses goes through the install-time flow of COR-017: override, skip or inspect, for each artefact. The skips are recorded in the component's record.
- **With nobody to answer,** the transition refuses before it writes anything. It names two ways on: run it again where a person can answer, or rename the project's artefact.
- **A collision with externally-sourced content** surfaces, as COR-041 sets.
- **Components outside the release keep their own course:**
  - an externally-sourced one moves by its pin (COR-041)
  - one authored in the project moves by the project (COR-031)
  - one the target no longer ships stays installed, with COR-017's warning
- **Dependency checks that involve them** keep the dispositions COR-030 and COR-053 point 6 set.

### 8. A transition creates a missing seed path, and reconciliation creates none

- **A transition creates each declared seed path that is missing,** from the target's seed. It never writes over a seed path that exists.
- **Reconciliation creates no seed path.**
- **A seed the project deleted on purpose returns** at the next transition.

### 9. A command that propagates content under another version than the project records stops

- **The commands it binds:** every command that propagates methodology content into a project at the backbone version the project records. Reconciliation, a component's install and a transition of one component are among them.
- **When it stops:** when the running CLI's version is not the backbone version the project records, or when the last transition is incomplete.
- **How it stops:** it writes nothing, stops in a preview too, and takes no override.
- **Its message names the remedy for the state it finds,** such as a transition to move the project on, or the project's own version of the CLI to stay.
- **A transition of the backbone moves forward only.** It refuses to run under a CLI older than the version the project records.

### 10. A rewrite of the project's own content stays out of the transition

- **What stays out:** an operation that rewrites content the project wrote, to follow a format change, beyond the writes that point 3 lets a migration make.
- **It is another operation, with another consent.** A transition's consent is given before it runs, by choosing a target. A rewrite of the project's content is consented to after it runs, by reviewing its diff.

### What this overturns, and what stands

This record partially supersedes COR-001, COR-004 and COR-017. Each overturned passage stays in its record as it stood. Passages the change leaves true but incomplete are refined in place in their records.

- **COR-004:**
  - **Overturned:**
    - in "Each command anchors to one mechanism or operation", the sentence "Compound verbs (e.g., an "update" that does sync + merge + migrations) hide which contract is being invoked, conflate consent profiles, and resist the manifest-level reasoning the install/sync runtime needs"
    - the Rationale's sentence that compound verbs "would create a parallel vocabulary that drifts from the mechanism vocabulary and re-encodes consent contracts in opaque names", as it reads on a version transition, which is on the list
    - the rejected alternative "One smart `update` verb that picks sync / merge / migration as needed". A version transition is one operation (points 3 and 4).
    - in "`sync` and `merge` stay separate", "They are different verbs because they encode different consent", as far as it keeps merge out of sync, and the Implications' example "a sub-verb that combined sync + merge would hit the anchoring rule". Reconciliation carries merge delivery's auto-add tier, and a tier that prompts never runs in it (point 2).
    - in "`init` is one-shot", the reason that a re-run would "resurface seeded content (violating COR-001's seed contract)". A transition creates a seed path that is missing (point 8). First install stays one-shot.
  - **Stands:** one operation for each command, merge as a command of its own, a routine refresh that never asks, and first install as one-shot.
- **COR-001:**
  - **Overturned:** in "Install-time seeding", the cadence "written exactly once, at first install", the Implications' "Subsequent syncs run propagation only." and "Seeded extension artifacts are project-owned after first install. Core makes no further claim on them.", and the Rationale's reading of seeding as one event. Reconciliation runs propagation and merge delivery's auto-add tier (point 2), and a transition creates a declared seed path that is missing (point 8).
  - **Stands:** that sync never seeds, seeding as a delivery operation and no fourth mechanism, and the seeded path's ownership by the project. Seeding never writes over a seed path that exists.
- **COR-017,** "Lifecycle: install, sync, uninstall":
  - **Overturned:** the sentence that sync "auto-upgrades installed capabilities", and the paragraph's refusal on a new collision, which names an interactive capability upgrade. Also the Implications' "**Sync extension** — refreshes installed capabilities; surfaces no-longer-shipped capabilities; refuses upgrade on new collisions", and the interactive single-capability upgrade the Implications list as the way to resolve a collision. A transition moves the capabilities, and resolves a new collision inside it or refuses (point 7). Reconciliation keeps a capability at its recorded version (point 2).
  - **Stands:** install and its collision flow, the install / sync / uninstall lifecycle, which the transition joins, the warning for a capability the methodology no longer ships, the skipped-artifact records, which reconciliation and the next transition both respect, and uninstall.

## Rationale

**Why only one operation moves a version.** A migration bridges two recorded versions. Whatever moves the version must run the migrations between them, or they are stranded. If two operations may move a version and only one runs migrations, the other strands them, and the one that runs them later finds nothing to do. One operation that moves versions and runs every migration of what it moves leaves no path that skips them.

**Why reconciliation stays.** A project needs a routine repair that never moves it: a fresh clone, a deleted file, a new skill of the project's own whose grant merge adds. Reconciliation at the recorded versions does that and can run at any time, since it changes no version.

**Why merge delivery stays in reconciliation.** Merge reads the project's own inputs: its additions, its own skills and its components' contributions. A project edits its additions and expects the next routine run to apply them. Taking merge out of reconciliation would turn every such edit into a separate command. COR-010 already counts merged-config entries as derivable state, which its Update regenerates, so the auto-add tier is part of reconciliation's one operation and not a second one beside it. That tier asks nothing, so carrying it in a routine run keeps a routine refresh from asking. A tier that prompts stays out.

**Why one consent.** COR-004 rejects a compound verb because it hides which contract runs and asks for consent unevenly. A transition's parts all follow from one choice, the target. The person who chooses the target already runs that release's code, its migrations included. Asking again for each part would ask about consequences of a choice already made. The choices that do not follow from the target keep the consent their own records set. Each is asked wherever it arises, and never taken silently, so no choice is silent in one case and asked in another.

**Why the target is recorded first.** An older CLI meeting a project mid-transition reads only the state it already knows: the recorded version. Recorded first, the target shows the older CLI a newer version, and an older CLI that applies point 9 refuses. Recorded last, the record would show the older CLI its own version, and it would copy its older content over a half-migrated tree. A separate "in progress" marker would not help, since the older CLI cannot read it. So the transition records two states, and the completion comes last. The protection holds against every CLI that applies point 9, and not against one released before it.

**Why every shipped component moves together.** A project that mixes two releases needs gates for every pair that might not agree, and no release was tested in that mix. Moving every shipped component together keeps the project at one release. A collision, the one thing that could hold a component back, is resolved inside the transition or stops it before it writes.

**Why the transition creates missing seed paths.** New seed paths arrive only with a new release, and reconciliation runs at the recorded release. So all reconciliation could add is to bring back, on every routine run, a seed the project deleted. A transition comes once for each release, and it is where a release's new seed paths appear. Writing only what is missing keeps every seed the project already holds.

**Why a rewrite of the project's content stays out.** A transition's parts follow from the target, and the methodology owns what they replace or add. A rewrite of content the project wrote changes the project's own words. The person consents to it by reading the diff after it runs, which the choice of a target before the run does not give.

**Why COR-041 is the precedent.** Externally-sourced content already keeps the routine operation from moving a recorded version: sync brings the copy to its pin, and only an upgrade repoints the pin. This record applies the same rule to the backbone and every shipped component, and adds that the operation that moves a version runs the migrations of what it moves.

### Alternatives considered

- **Keep COR-004 as it stands, and record the upgrade as a named exception elsewhere.** Rejected: a core rule with an exception that only one project's own records know of. An adopter reading the core records would find a rule the tool breaks.
- **Reconciliation moves content but records no version.** Rejected: content would move without the migrations that bridge it, and the recorded version would no longer name the content held.
- **Reconciliation fetches the recorded version's content when another CLI runs it.** Rejected: it adds a fetch to a routine repair, and offline it still has to stop.
- **An "in progress" marker in place of two recorded states.** Rejected: an older CLI cannot read a marker it does not know, so the marker would not stop it.
- **The completion written right after the backbone migrations.** Rejected: reconciliation could then run over a component whose content moved and whose migrations had not run. Running the backbone migrations again after a late interruption is cheap.
- **A missing completion means complete, and a stranded project runs the backbone migrations from a version its operator names.** Rejected: a project stays stranded unless its operator learns it is. Each migration can tell its own state from the files, but nothing tells the operator which to run.
- **A ledger of the migrations that ran.** Rejected: it drifts from the files, conflicts across branches, and COR-010 keys migrations on versions.
- **Hold a colliding component back at its old version.** Rejected: the project would mix two releases, and every dependency check would need a disposition for the mix.
- **Merge leaves reconciliation, and runs only at install, in a transition and on its own command.** Rejected: every edit to a project's additions, and every new skill of its own, would need a separate command.
- **Reconciliation and the transition both create missing seed paths.** Rejected: a seed the project deleted on purpose would return on every routine run.
- **The transition rewrites the project's own content too.** Rejected: the rewrite's consent comes from reviewing a diff after the run, which choosing a target cannot give.

## Implications

- **COR-004's list of operations** names the version transition. Its forward-only failure and its recovery after a failed first install name the transition as the way to finish an interrupted move.
- **COR-001** states that the core layer writes a project-owned path only through an operation a record names as that content's writer, with the consent that record sets. Merge delivery, including reconciliation's, and the transition's migrations and seed creation are such writers.
- **COR-002's merge** runs on every sync too, in its auto-add tier.
- **COR-010:**
  - its Update runs at the recorded versions
  - its upgrade order is a version transition's: the target recorded first, derivable state a migration reads regenerated after propagation, and the completion recorded last
  - a backbone migration acts only on a positive sign that its change is needed, and never deletes by a path's name or position alone, so a transition may run it over any state
  - selective movement remains for externally-sourced content
- **COR-048 point 1:** no lifecycle command removes the configuration file, and a transition writes it only through the migrations point 5 names.
- **The decisions specification's no-shared-files invariant** says that sync writes a project-owned path only through merge delivery, that it reads the backbone manifest, and that it stops under a CLI at another version than the project's.
- **The realisation** is the implementing project's: the commands, where the completion is recorded, how a component with no record is read, and the remedies each stop names. A realising decision records it (COR-025).
