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

Externally-sourced content already draws the line this record needs (COR-041). Sync brings the consumer's copy to its pin and moves nothing. Only an upgrade moves it, by repointing the pin.

## Decision

**A project stays at the versions it records. Reconciliation keeps the project in line with those versions, and moves none of them. A version transition is the one operation that moves a recorded version, and every migration runs inside it, under the one consent of choosing its target. It records its target before it writes anything and its completion last, so an interrupted transition is never mistaken for a finished one.**

The points that follow:

- **Points 1 to 3** say what a project records, what reconciliation does, and what a version transition is.
- **Points 4 and 5** say why a transition is one operation under COR-004.
- **Points 6 to 8** say how a transition records its progress, which components it moves, and which seed paths it creates.
- **Point 9** stops a command that would copy content under another version than the project records.
- **Point 10** keeps a rewrite of the project's own content out of the transition.

### 1. A project records a version for its backbone and for each component it installs

- **What a recorded version names:** the release whose content the project holds, for the backbone and for each component (COR-010).
- **Where it sits:** out of propagation's reach, in the backbone manifest and in each component's project-side directory (COR-010, "Implications"). Copying the methodology's content never writes or removes a recorded version.
- **By origin** (COR-031):
  - a component the methodology ships records the version it shipped with
  - an externally-sourced component records its pin (COR-041)
  - a component authored in the project is the project's own, and its version moves when the project edits it. No operation of the core layer moves it.

### 2. Reconciliation runs at the recorded versions, and moves none

Reconciliation is the sync operation (COR-001), COR-010's Update: it brings the installed state in line with the spec at the versions the project records.

- **It moves no recorded version, and runs no migration.**
- **It writes three kinds of thing, and no other:**
  - methodology content at the recorded versions, by propagation (COR-001)
  - derivable state, regenerated from the project's own declarations (COR-010)
  - project-owned paths, through merge delivery only, in its auto-add tier (COR-002). That tier only appends, and adds only what the project already decided: its own additions and the baseline of the release it records.
- **A merge tier that prompts** runs only where a person can answer. With nobody to answer, it writes nothing.
- **It creates no seed path** (point 8).
- **A component the running CLI ships at another version than the project records** is not copied, and reconciliation reports it.

### 3. A version transition is the only operation that moves a recorded version

- **What it is:** an operation that moves a project's recorded versions to a target. An upgrade is one.
- **It is one operation on COR-004's list,** beside propagation, seeding and merge.
- **Every migration runs inside it,** in COR-010's order. No other operation runs a migration.
- **What it writes:** the target's content, every pending migration with the writes their owning records allow, merge delivery, the seed paths point 8 names, and the recorded versions.
- **An externally-sourced component moves on its own,** when its pin is repointed (COR-041). That repointing is its transition.

### 4. One consent covers a transition's parts

- **Choosing the target is the consent.** Every part of a transition follows from the target the person chose, so one consent covers them all.
- **What each part does depends on what it finds,** as propagation's copy does. What COR-004 still rejects is a verb whose consent depends on what it finds: silent in one case, asking in another.
- **Two choices do not follow from the target,** and keep the consent their own records set:
  - which of two colliding artefacts the project keeps (point 7, COR-017)
  - merge delivery's prompt-once tier (COR-002)
- **Each is asked only where a person can answer.** With nobody to answer, a collision refuses the transition before it writes anything (point 7), and the prompt-once tier writes nothing.

### 5. The one-operation rule governs operations on a project

- **COR-004's rule,** one operation for each command, governs what a command does to a project.
- **Updating the CLI installed on the machine acts on no project.** So a command may first update the CLI that runs it, and then perform its one operation.

### 6. A transition records its target first and its completion last

- **Two recorded states:**
  - **the target,** written as the backbone's recorded version before the transition writes anything else
  - **the completion,** written last, once every migration has run and the derivable state is regenerated
- **A transition is complete when the two are equal.** Each component's record moves to the target when that component's migrations finish.
- **The next transition finishes an incomplete one.** It runs the backbone migrations from the recorded completion, and each component's from that component's own record.
- **A missing completion reads as incomplete, with no lower bound.** The project's migration history is unknown, so its next transition runs every backbone migration up to its target, once. So a backbone migration must be safe to run over any state, which COR-010's migration rule requires.
- **A migration that fails stops the transition,** which stays incomplete. The next transition runs it again.
- **Reconciliation never runs over an incomplete transition** (point 9).

### 7. A transition moves every component the methodology ships together

- **One release for each project.** A transition moves the backbone and every component the methodology ships with it to the target's versions. No such component is held back at its old version.
- **A new collision is resolved inside the transition.** A shipped artefact whose name an artefact of the project already uses goes through the install-time flow of COR-017: override, skip or inspect, for each artefact. The skips are recorded in the component's record.
- **With nobody to answer,** the transition refuses before it writes anything. It names two ways on: run it again where a person can answer, or rename the project's artefact.
- **Components outside the release keep their own movement:** an externally-sourced one by its pin (COR-041), and one authored in the project by the project (COR-031). Dependency checks that involve them keep the dispositions COR-030 sets.

### 8. A transition creates a missing seed path, and reconciliation creates none

- **A transition creates each declared seed path that is missing,** from the target's seed. It never writes over a seed path that exists.
- **Reconciliation creates no seed path.**
- **A seed the project deleted on purpose returns** at the next transition.

### 9. A command that copies content under another version than the project records stops

- **The commands it binds:** every command that copies methodology content into a project at the backbone version the project records. Reconciliation, a component's install and a transition of one component are among them.
- **When it stops:** when the running CLI's version is not the backbone version the project records, or when the last transition is incomplete.
- **How it stops:** it writes nothing, a preview included, and takes no override.
- **Its message names the remedy for the state it finds,** such as a transition to move the project on, or the project's own version of the CLI to stay.
- **A transition of the backbone moves forward only.** It refuses to run under a CLI older than the version the project records.

### 10. A rewrite of the project's own content stays out of the transition

- **An operation that rewrites content the project wrote,** to follow a format change, is not part of a transition.
- **Their consents differ.** A transition's consent is choosing a target. A rewrite of the project's content is consented to by reviewing its diff. One command holding both would be the two-consent verb COR-004 rejects.

### What this overturns, and what stands

This record partially supersedes COR-001, COR-004 and COR-017. Each overturned passage stays in its record as it stood.

- **COR-004,** "Each command anchors to one mechanism or operation":
  - **Overturned:** the sentence "Compound verbs (e.g., an "update" that does sync + merge + migrations) hide which contract is being invoked, conflate consent profiles, and resist the manifest-level reasoning the install/sync runtime needs", and the rejected alternative "One smart `update` verb that picks sync / merge / migration as needed". A version transition is one operation (points 3 and 4).
  - **Stands:** one operation for each command, and the rejection of a verb whose consent depends on what it finds.
- **COR-004,** "`sync` and `merge` stay separate":
  - **Overturned:** "They are different verbs because they encode different consent", as far as it keeps merge out of sync. Reconciliation carries merge delivery's auto-add tier, which only appends, and a tier that prompts runs only where a person can answer (point 2).
  - **Stands:** merge stays a command of its own, and reconciliation never overwrites a project-owned path.
- **COR-001,** "Install-time seeding":
  - **Overturned:** the cadence "written exactly once, at first install", the Implications' "Seeded extension artifacts are project-owned after first install. Core makes no further claim on them", and the Rationale's reading of seeding as one event. A transition creates a declared seed path that is missing (point 8).
  - **With it:** COR-004's reason for a one-shot first install, that a re-run would "resurface seeded content (violating COR-001's seed contract)". A transition resurfaces a seed path that is missing. First install stays one-shot.
  - **Stands:** that sync never seeds, seeding as a delivery operation and no fourth mechanism, and the seeded path's ownership by the project. Nothing writes over a seed path that exists.
- **COR-017,** "Lifecycle: install, sync, uninstall":
  - **Overturned:** the sentence that sync "auto-upgrades installed capabilities", and the paragraph's refusal on a new collision, which names an interactive capability upgrade. A transition moves the capabilities, and resolves a new collision inside it or refuses (point 7). Reconciliation keeps a capability at its recorded version (point 2).
  - **With it:** the section's "install / sync / uninstall lifecycle", which gains the transition, and the Implications' "**Sync extension** — refreshes installed capabilities; surfaces no-longer-shipped capabilities; refuses upgrade on new collisions". The Rationale's skipped-artifact records persist in the component's record, and both reconciliation and the next transition respect them.
  - **Stands:** install and its collision flow, the warning for a capability the methodology no longer ships, and uninstall.

## Rationale

**Why only one operation moves a version.** A migration bridges two recorded versions. Whatever moves the version must run the migrations between them, or they are stranded. If two operations may move a version and only one runs migrations, the other strands them, and the one that runs them later finds nothing to do. One operation that moves versions and runs every migration leaves no path that skips them.

**Why reconciliation stays.** A project needs a routine repair that never moves it: a fresh clone, a deleted file, a new skill of the project's own whose grant merge adds. Reconciliation at the recorded versions does that and can run at any time, since it changes no version.

**Why merge delivery stays in reconciliation.** Merge reads the project's own inputs: its additions, its own skills and its components' contributions. A project edits its additions and expects the next routine run to apply them. Taking merge out of reconciliation would turn every such edit into a separate command. Its auto-add tier only appends what the project already decided, so carrying it in a routine run asks no new consent. A tier that prompts still waits for a person.

**Why one consent.** COR-004 rejects a compound verb because it hides which contract runs and asks for consent unevenly. A transition's parts all follow from one choice, the target. The person who chooses the target already runs that release's code, its migrations included. Asking again for each part would ask about consequences of a choice already made. The two choices that do not follow from the target, a collision and a prompting merge tier, keep their own consent.

**Why the target is recorded first.** An older CLI meeting a project mid-transition reads only the state it already knows: the recorded version. Recorded first, the target shows the older CLI a newer version, and it refuses (point 9). Recorded last, the record would show the older CLI its own version, and it would copy its older content over a half-migrated tree. A separate "in progress" marker would not help, since the older CLI cannot read it. So the transition records two states, and the completion comes last.

**Why every shipped component moves together.** A project that mixes two releases needs gates for every pair that might not agree, and no release was tested in that mix. Moving every shipped component together keeps the project at one release. A collision, the one thing that could hold a component back, is resolved inside the transition or stops it before it writes.

**Why the transition creates missing seed paths.** New seed paths arrive only with a new release, and reconciliation runs at the recorded release. So creating seeds in reconciliation would only ever repair a seed the project deleted, against the project's choice. The transition is where a release's new seed paths appear. Writing only what is missing keeps every seed the project already holds.

**Why a rewrite of the project's content stays out.** A transition's parts follow from the target, and the methodology owns what they replace or add. A rewrite of content the project wrote changes the project's own words. The person consents to it by reading the diff, which the choice of a target does not give.

**Why COR-041 is the precedent.** Externally-sourced content already separates the two operations: sync brings the copy to its pin and moves nothing, and an upgrade moves it by repointing the pin. This record applies the same split to the backbone and every shipped component.

### Alternatives considered

- **Keep COR-004 as it stands, and record the upgrade as a named exception elsewhere.** Rejected: a core rule with an exception that only one project's own records know of. An adopter reading the core records would find a rule the tool breaks.
- **Reconciliation moves content but records no version.** Rejected: content would move without the migrations that bridge it, and the recorded version would no longer name the content held.
- **Reconciliation fetches the recorded version's content when another CLI runs it.** Rejected: it adds a fetch to a routine repair, and offline it still has to stop.
- **An "in progress" marker in place of two recorded states.** Rejected: an older CLI cannot read a marker it does not know, so the marker would not stop it.
- **A ledger of the migrations that ran.** Rejected: it drifts from the files, conflicts across branches, and COR-010 keys migrations on versions.
- **Hold a colliding component back at its old version.** Rejected: the project would mix two releases, and every dependency check would need a disposition for the mix.
- **Merge leaves reconciliation, and runs only at install, in a transition and on its own command.** Rejected: every edit to a project's additions, and every new skill of its own, would need a separate command.
- **Reconciliation and the transition both create missing seed paths.** Rejected: a seed the project deleted on purpose would return on every routine run.
- **The transition rewrites the project's own content too.** Rejected: one command would hold two consents.

## Implications

- **COR-004's list of operations** names the version transition. Its forward-only failure and its recovery after a failed first install name the transition as the way to finish an interrupted move.
- **COR-001** states that the core layer writes a project-owned path only through an operation a record names as that content's writer. Reconciliation's merge delivery, and the transition's migrations and seed creation, are such writers.
- **COR-002's merge** runs on every sync too, in its auto-add tier.
- **COR-010:** Update runs at the recorded versions. Its upgrade order records the target first and the completion last. A backbone migration acts only on a positive sign that its change is needed, so a transition may run it over any state. Selective movement remains for externally-sourced content.
- **COR-048 point 1:** no lifecycle command removes the configuration file, and an upgrade writes it only through the migrations point 5 names.
- **A command that moves one shipped component alone** is a transition too. It moves that component to the version the project's recorded backbone ships with, under the CLI at that version (point 9). So it finishes a component an earlier transition left behind.
- **The realisation** is the implementing project's: the commands, where the completion is recorded, and the remedies each stop names. A realising decision records it (COR-025).
