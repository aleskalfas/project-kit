---
id: COR-070
title: A capability's operational rules load in every session where it is installed
status: proposed
date: 2026-10-29
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a capability may ship operational rules of its own, as one loaded rule set. The file generated from that set travels with the capability. Wherever the capability is installed, the adapter puts that file where its harness loads files at the start of every session, as it deploys the capability's skills, and takes it away when the capability is uninstalled. Installing the capability is the project's consent to those rules. Rules add up across layers: a capability's never loosen core's, and a project's never loosen core's or a capability's. A rule that binds only where a capability is installed belongs to that capability, not to core. Validation fails where an installed capability's file is missing from the place its harness loads it. Whether every kind of session really loads it is a harness requirement, reported as indeterminate where it cannot be seen.

## Context

Operational rules are kept in loaded rule sets ([COR-068](COR-068-loaded-rule-sets.md)). A loaded set's accepted rules bind on the work of each session that loads the file generated from it. Core's set binds in every project, and a project's own in that project. COR-068 point 4 leaves a capability's loaded set to the first capability that ships one: how its loaded file reaches the sessions, and how a project's rules relate to a capability's. Until then, validation refuses one.

Some operational rules bind only where a capability is installed. A rule on which tests a session runs while it changes code binds where code is engineered. A branch-naming convention binds where the work tracker it names is in use. Such a rule sits today either in core's set, which binds in every project, or in each project's own rules, where every project writes it again. Or a core rule defers to the capability's documentation, which no session loads.

Core's loaded file reaches a session through an include in the project's instruction file, which the adapter merges in and the project owns ([COR-002](COR-002-merge-delivery.md)). A capability is installed and uninstalled ([COR-017](COR-017-capability-pattern.md)), so its file must arrive and leave with it.

Whether a session loads a file is the harness's behaviour, not the methodology's. A harness may load its start-up files in a session a person starts, and not in a helper it starts for another agent. A loaded rule binds only on the sessions that load its file (COR-068 point 2), so a session that loads none is bound by nothing, and nothing says so.

## Decision

**A capability may ship one loaded rule set. Its loaded file is generated where the capability is authored and travels with it. Each adapter deploys that file where its harness loads files into every session from its start, for as long as the capability is installed, and validation fails where it is missing. Installing the capability accepts its rules, and no layer's rules loosen another's.**

### 1. A capability ships at most one loaded set, and its loaded file travels with it

- **One set:** a capability may ship one loaded set, beside its ordinary rule sets (refinement of COR-068 point 4). It is a method set of the capability ([COR-051](COR-051-rule-sets.md) point 6), with one loaded set to a component, as COR-068 point 1 says.
- **Its file:** generated from the set where the capability is authored, as COR-068 point 3 says of every loaded set, and kept among the capability's own files. Sync, install and upgrade deliver it there with the set, and the deploy of point 2 brings it to the harness (refinement of COR-068 point 3). A project neither generates nor edits it.
- **What it holds:** the capability's rules about a session's work. Its rules about the files a project writes stay in its ordinary rule sets, which bind through a project's set that inherits them (COR-051 point 7; COR-068 point 1, "Which kind of set a rule belongs in").

### 2. The adapter deploys the loaded file where its harness loads files at every session's start

- **Where:** each adapter places an installed capability's loaded file where its harness loads files into every session from the session's start. The means is one the adapter owns, such as a file of its own in a folder the harness reads, never an edit to a file the project wrote. The deployed file points at the capability's file, or copies it, as the adapter deploys the capability's skills ([COR-005](COR-005-bundle-pattern.md)).
- **When:** whenever the adapter deploys again, as at install, sync and upgrade. Uninstalling the capability removes the deployed file, and so does unregistering it with its files kept.
- **What it never touches:** a file at that place that the adapter did not deploy. Such a file is the project's, and the capability's file stays undeployed there, which point 6 reports.
- **A harness that loads no such files:** its adapter says that it deploys no capability's rules. Its sessions then load none, which point 6 also reports.

### 3. Installing a capability accepts its loaded set

- **Consent:** the person who installs a capability consents to its loaded set's accepted rules. They bind in the project from the install to the uninstall. No rule is accepted a second time in the project, since a person accepted it where the capability is authored ([COR-066](COR-066-accepted-before-landing.md) point 1).
- **A later version:** a rule the capability accepts, edits or retires in a later version binds, or stops binding, once the upgrade or sync that brings it lands, as core's rules do (COR-068 point 5).
- **No opt-out while installed:** neither the capability's loaded file nor its deployed file is suspendable ([COR-001](COR-001-content-mechanisms.md)). A rule about a session's work has nowhere narrower to bind than the project, so a project chooses only to install the capability or not (COR-068, "Why core's set binds with no opt-in").

### 4. Rules add up across layers, and none loosens another

- **A session is bound by all of them:** every accepted rule of every loaded file the session loads binds it, core's, each installed capability's and the project's.
- **None loosens another:** a capability's rule never loosens a rule of core's, and a project's never loosens one of core's or of an installed capability's. A rule that reads as loosening one binds only in what it adds. A project that wants less changes the rule where it is kept, by proposing the change there, or uninstalls the capability.
- **A clash:** where a rule cannot be kept together with a rule of a layer above it, the upper layer's rule binds: core's above a capability's, and both above the project's. Where rules of two capabilities cannot both be kept, the session asks the person before it acts.
- **Judged, not checked:** whether a rule loosens another is read from prose, so no check decides it ([COR-055](COR-055-validation.md)). The person who accepts a rule judges it, in the change that proposes it.

### 5. A rule that binds only with a capability belongs to that capability

- **Where it goes:** a rule that binds a session's work only where a capability is installed belongs in that capability's loaded set. It does not belong in core's, whose rules bind in every project, nor in each project's own. This is the universal-applicability test ([COR-014](COR-014-universal-applicability.md)) between core and a capability.
- **What stays in core:** a core rule that loses such a part to a capability keeps its universal part. It is edited, keeping its id, where its claim stays, or withdrawn where none of it stays (COR-051 point 4).
- **No capability successor:** a core rule never names a capability's rule as its successor. A successor sits in the rule's own set or in one that inherits it, and no loaded set inherits another (COR-051 point 4; COR-068 point 1). A core rule must also read true in a project where the capability is absent (COR-014).
- **A project's plain rules:** a project whose rules are a plain file (COR-068 point 7) points from a moved rule to its new place as it chooses.

### 6. Validation fails where the file is not deployed, and whether a session loads it is a harness requirement

- **Deployed:** validation fails where an installed capability's loaded set has no deployed file at the place an adapter in use deploys it, or one whose content differs from the capability's loaded file. Where an adapter in use deploys no capability's rules (point 2), validation warns, naming the adapter.
- **In step:** where the capability is authored, the check COR-068 point 3 sets fails a loaded file out of step with its set.
- **Loaded:** a harness requirement ([COR-047](COR-047-harness-requirement-declaration.md)) states that every session the harness starts in a project holds the loaded files from its start. That covers a session a person starts, a delegated helper and an unattended run. Its truth is visible only inside a session, so a report run from outside one resolves it indeterminate, never satisfied (COR-047 point 4). The design dependency that admits it (COR-047 point 9) is COR-068 point 2: a loaded rule binds only on the sessions that load its file.

## Rationale

**Why the adapter deploys the file, rather than an include in the project's instruction file.** That file is the project's, merged by inserting what is absent (COR-002). An include for each capability would add a line to it at install and take one out of it at uninstall. A removal from a file the project writes can take the project's own text with it. A place the harness loads at every session's start lets the adapter add and remove a file it owns, as it does a capability's skills. An include is also one harness's mechanism, while a place loaded at every start is a behaviour any harness may offer.

**Why the file is generated where the capability is authored.** COR-068 point 3 decides that a project neither generates nor edits a loaded file it receives. A file generated at install would be the project's to keep in step with a set it does not edit. It could also read differently in two projects that install one version of the capability.

**Why installing accepts the set.** A capability is chosen by installing it, so its rules bind from that choice and end with it (COR-068, "Why core's set binds with no opt-in"). Accepting each rule again in each project would have every project review again what a person accepted where it is kept. A project that declined one rule would then be bound by a set that nobody authored.

**Why no layer loosens another.** Core's rules keep the methodology's invariants, and a capability's keep its discipline's. Other sessions, reviewers and the capability's own commands rely on both. A project's rule that waived one would take away a guarantee that others rely on, unseen. Adding to a rule never breaks it. Loosening one is a change to the rule itself, made where it is kept, where its author and its readers see it. The upper layer wins a clash for the same reason. Two capabilities stand side by side, so neither outranks the other, and the person decides.

**Why a core rule never names a capability's rule as its successor.** A capability may be absent from a project, and a successor there would name a rule that does not exist. COR-051 point 4 also keeps a successor in the rule's own set or an inheritor, so that where the old rule bound the successor binds. A core rule keeps what holds everywhere, and the capability's own set holds the rest.

**Why whether a session loads the file is a harness requirement, not a check.** Validation runs outside every session. It can see that the file is where the harness should load it, not that a session loaded it. A harness may start a helper with a context of its own. Reporting that indeterminate keeps "the file is in place" from reading as "every session follows the rules" (COR-047 point 3).

### Alternatives considered

- **An include for each capability in the project's instruction file.** Rejected: install and uninstall would edit a file the project owns.
- **One loaded file joining core's rules and every installed capability's.** Rejected: one file of several owners breaks the no-shared-files invariant, and it would be generated in the project at each install, which COR-068 point 3 rules out.
- **Generating a capability's loaded file at install or sync.** Rejected, as "Why the file is generated where the capability is authored" says.
- **Loading a capability's rules only in the sessions of its own agents, or only for the files a session touches.** Rejected: a loaded rule binds on any session's work where the capability is installed, and a person may do the capability's work with any agent. Binding on files only where a scope selects them is what ordinary rule sets do (COR-051 point 7).
- **A switch that keeps a capability's loaded set away while it is installed.** Rejected: a rule about a session's work leaves a project only installing the capability or not (COR-068).
- **Accepting each capability rule again in each project.** Rejected, as "Why installing accepts the set" says.
- **Retiring a core rule with a capability's rule as its successor.** Rejected, as "Why a core rule never names a capability's rule as its successor" says.

## Implications

- **COR-068 points 3 and 4** gain forward pointers to this record, and validation stops refusing a capability's set marked loaded.
- **The adapters' shared specification** counts the deploy of a capability's loaded file among the deploy primitives, and has the undeploy primitive remove it. The architecture record that realises this one decides each harness's place, the file's path among the capability's files and where the check runs.
- **The harness requirements** gain the requirement of point 6, and each adapter answers it in its support declaration.
- **The capabilities' reference** names a capability's loaded set and its loaded file among the files a capability may ship (COR-017).
- **Rules that bind only with a capability** move from core's set and from a project's own rules to that capability's loaded set, each leaving its old place as point 5 says.
- **Stands on these records, all accepted:** COR-001, COR-002, COR-005, COR-014, COR-017, COR-047, COR-051, COR-055, COR-066 and COR-068.
