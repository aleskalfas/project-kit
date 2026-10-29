---
id: COR-070
title: A capability's operational rules load in every session where it is installed
status: proposed
date: 2026-10-29
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a capability may ship operational rules of its own, as one loaded rule set. The file generated from that set travels with the capability, and names the capability and how its rules stand to core's. Wherever the capability is installed, the adapter puts that file, in a place of its own, where its harness loads files into every session, and takes it away when the capability is uninstalled. Installing the capability is the project's consent to those rules, and install, sync and upgrade say which rules they newly bind, core's among them. Rules add up across layers: a capability's never loosen core's, and a project's never loosen core's or a capability's. A rule that binds only where a capability is installed belongs to that capability, not to core. Validation fails where the adapter's place for these files is in a checkout and an installed capability's file is missing from it or differs. Whether every kind of session really loads it is a harness requirement, reported as indeterminate where it cannot be seen.

## Context

Operational rules are kept in loaded rule sets ([COR-068](COR-068-loaded-rule-sets.md)). A loaded set's accepted rules bind on the work of each session that loads the file generated from it. Core's set binds in every project, and a project's own in that project. COR-068 point 4 leaves a capability's loaded set to the first capability that ships one: how its loaded file reaches the sessions, and how a project's rules relate to a capability's. Until then, validation refuses one.

Some operational rules bind only where a capability is installed. A rule on which tests a session runs while it changes code binds where code is engineered. A rule on how work is linked to the issues that track it binds where that work tracker is in use. Such a rule sits today either in core's set, which binds in every project, or in each project's own rules, where every project writes it again. Or a core rule defers to the capability's documentation, which no session loads.

Core's loaded file reaches a session through one include in the project's instruction file, which the adapter inserts once and the project owns ([COR-002](COR-002-merge-delivery.md)). A capability is installed and uninstalled ([COR-017](COR-017-capability-pattern.md)), so its file must arrive and leave with it.

A session reads the files it loads, not the records behind them ([COR-065](COR-065-records-and-projection.md) point 7). So what a session needs to know of how a capability's rules stand to core's and to a project's must be in the file it loads.

Whether a session loads a file is the harness's behaviour, not the methodology's. A harness may load its start-up files in a session a person starts, and not in some helpers it starts for another agent, or in a run started without the project's settings. A loaded rule binds only on the sessions that load its file (COR-068 point 2), so a session that loads none is bound by nothing, and nothing says so.

## Decision

**A capability may ship one loaded rule set. Its loaded file is generated where the capability is authored, travels with it, and names the capability's layer. Each adapter deploys that file, through a place of its own, where its harness loads files into every session, for as long as the capability is installed, and validation fails where that place is in a checkout without the file, or with it changed. Installing the capability accepts its rules, and no layer's rules loosen another's.**

### 1. A capability ships at most one loaded set, and its loaded file travels with it

- **One set:** a capability may ship one loaded set, beside its ordinary rule sets (refinement of COR-068 point 4). It is a method set of the capability ([COR-051](COR-051-rule-sets.md) point 6), with one loaded set to a component, as COR-068 point 1 says. Its name is its own, and no other set a project holds takes it (COR-051 point 3).
- **Its file:** generated from the set where the capability is authored, as COR-068 point 3 says of every loaded set, and kept among the capability's own files. Sync, install and upgrade deliver it there with the set, and the deploy of point 2 brings it to the harness (refinement of COR-068 point 3). A project neither generates nor edits it.
- **It names its layer:** the set's prose before its first rule, which carries into the loaded file, names the capability and says how its rules stand to core's and to a project's, as point 4 decides. A session reading the file then knows its layer.
- **Which rules it holds:** COR-068 point 1's test, read for a capability's layer. A rule that must bind on a session's work wherever the capability is installed, with no opt-in, goes in its loaded set, a rule about files among them. A rule a project chooses to bind on its own artefacts goes in an ordinary set, and binds through the project set the capability's install declares (COR-017, "Running install is the consent") or one the project writes.
- **Its citations and origins:** its rules are cited by their ids with the capability's name, as a method set's rules are (COR-051 point 6). Each rule's origin cites a record that travels with the capability or with the backbone, or gives the decider's words, since the set is validated in every project that installs it.

### 2. The adapter deploys the loaded file where its harness loads files into every session

- **Where:** each adapter places an installed capability's loaded file where its harness loads files into every session, from the session's start and for its whole length.
- **Through a place of its own:** the adapter deploys into a file or folder of its own, which no file of the project's shares a name with. That place is one the harness reads at every session's start, or one the project's instruction file reaches through a single line the adapter inserts once, as it inserts what is absent there (COR-002). Nothing the adapter does at install, sync or uninstall removes or rewrites the project's own text.
- **What it deploys:** the content of the capability's loaded file, as the adapter deploys the capability's skills and agents ([COR-005](COR-005-bundle-pattern.md)).
- **When:** whenever the adapter deploys again, as at install, sync and upgrade. Uninstalling the capability removes the deployed file, and so does unregistering it with its files kept.
- **A harness that loads no such files:** its adapter says that it deploys no capability's rules. Its sessions then load none, which point 6 reports.

### 3. Installing a capability accepts its loaded set

- **Consent:** the person who installs a capability consents to its loaded set's accepted rules: running install is the consent, as it is for the project rule set the capability declares (COR-017). The rules bind in the project from the install to the uninstall. No rule is accepted a second time in the project, since a rule a project receives from elsewhere is judged where it is kept ([COR-066](COR-066-accepted-before-landing.md) point 2), and a person accepted it there (COR-066 point 1).
- **Told what binds:** install, sync and upgrade name each loaded set they deliver, core's among them, and list the rules it newly binds, changes or retires since the version it replaces (refinement of COR-068 point 5). That is information, not a gate. Where the harness's adapter deploys no capability's rules (point 2), they say that a capability's rules bind no session there, rather than list them as bound.
- **A later version:** a rule the capability accepts, edits or retires in a later version binds, or stops binding, once the upgrade or sync that brings it lands, as core's rules do (COR-068 point 5).
- **No opt-out while installed:** neither the capability's loaded file nor its deployed file is suspendable ([COR-001](COR-001-content-mechanisms.md)). A rule about a session's work has nowhere narrower to bind than the project, so a project chooses only to install the capability or not (COR-068, "Why core's set binds with no opt-in").

### 4. Rules add up across layers, and none loosens another

- **A session is bound by all of them:** every accepted rule of every loaded file the session loads binds it, core's, each installed capability's and the project's.
- **None loosens another:** a capability's rule never loosens a rule of core's, and a project's never loosens one of core's or of an installed capability's. A capability's rule that loosens core's is a defect of the capability, judged where its rule is accepted. A project's rule that reads as loosening one binds only in what it adds. A project that wants less proposes the change where the rule is kept, or uninstalls the capability.
- **A clash met in a session:** where a rule cannot be kept together with a rule of a layer above it, the upper layer's rule binds: core's above a capability's, and both above the project's. Where rules of two capabilities cannot both be kept, the session stops the step and reports the clash, as it stops a step that keeps failing, rather than choose between them. The capability's loaded file says so (point 1), since a session does not read this record.
- **Judged, not checked:** whether a rule loosens another, or clashes with it, is read from prose, so no check decides it ([COR-055](COR-055-validation.md)). The person who accepts a rule judges it, in the change that proposes it.

### 5. A rule that binds only with a capability belongs to that capability

- **Where it goes:** a rule that binds a session's work only where a capability is installed belongs in that capability's loaded set, rather than in core's, whose rules bind in every project, or written again in each project. This is the universal-applicability test ([COR-014](COR-014-universal-applicability.md)) between core and a capability.
- **Written for its layer:** a rule that moves from a project's rules to a capability's is written again for every project that installs the capability, with an origin of its own. Its part that holds only in the project stays the project's.
- **What stays in core:** a core rule that loses such a part to a capability keeps its universal part. It is edited, keeping its id, where its claim stays, or withdrawn where none of it stays (COR-051 point 4).
- **No capability successor:** a core rule never names a capability's rule as its successor. A successor sits in the rule's own set or in one that inherits it, and no loaded set inherits another (COR-051 point 4; COR-068 point 1). A core rule must also read true in a project where the capability is absent (COR-014).
- **A project's plain rules:** a project whose rules are a plain file (COR-068 point 7) points from a moved rule to its new place as it chooses.

### 6. Validation fails where a deploy left the file missing, and whether a session loads it is a harness requirement

- **Deployed:** where the adapter's place for capabilities' rules is in a checkout, validation fails an installed capability's loaded set with no deployed file there, or one whose content differs from the capability's loaded file. Where that place is not in the checkout, validation reports, without failing, that these files are not deployed there. Where an adapter in use deploys no capability's rules (point 2), validation warns, once, naming the adapter and the capabilities whose rules its sessions then miss.
- **In step:** where the capability is authored, the check COR-068 point 3 sets fails a loaded file out of step with its set.
- **Loaded:** a harness requirement ([COR-047](COR-047-harness-requirement-declaration.md)) states that every session the harness starts in a project holds the loaded files from its start and for its whole length, after the harness shortens the session's context too. That covers a session a person starts, a delegated helper and an unattended run. Its truth is visible only inside a session, so a report run from outside one resolves it indeterminate, never satisfied (COR-047 point 4). The design dependency that admits it (COR-047 point 9) is COR-068 point 2: a loaded rule binds only on the sessions that load its file.

## Rationale

**Why the adapter deploys through a place of its own.** The project's instruction file is the project's, merged by inserting what is absent (COR-002). A line added for each capability at install would have to be taken out at uninstall, and a removal from a file the project writes can take the project's own text with it. A place the adapter owns lets it add and remove what it deployed, as it does a capability's skills, and never meet a file of the project's under the same name. A harness that reads no such place at each start can still reach one, through a single line inserted once and never removed. An insertion of what is absent is what COR-002 already allows.

**Why the file names its layer.** A session loads files, not records (COR-065 point 7), so how a capability's rules stand to core's and to a project's binds a session only where its loaded file says it. Three files with numbered rules read alike otherwise.

**Why the file is generated where the capability is authored.** COR-068 point 3 decides that a project neither generates nor edits a loaded file it receives. A file generated at install would be the project's to keep in step with a set it does not edit. It could also read differently in two projects that install one version of the capability.

**Why installing accepts the set.** A capability is chosen by installing it, so its rules bind from that choice and end with it (COR-068, "Why core's set binds with no opt-in"). Its declared project rule set is consented to the same way (COR-017). Accepting each rule again in each project would have every project review again what a person accepted where it is kept (COR-066 point 2). A project that declined one rule would then be bound by a set that nobody authored.

**Why install, sync and upgrade say which rules they bind.** Consent given once at install covers rules a later version adds. Without a word at the upgrade, a project's own rule could stop binding in part, because a new rule now sits above it, and nobody would judge it. Core's set sits above the project too (point 4), so a sync that brings a new core rule does the same, and is named the same way. Naming what newly binds lets the project see it, without a gate that would hold back rules that must reach every session (COR-068, "Why a version that holds nothing back").

**Why no layer loosens another.** Core's rules keep the methodology's invariants, and a capability's keep its discipline's. Other sessions, reviewers and the capability's own commands rely on both. A project's rule that waived one would take away a guarantee that others rely on, unseen. Adding to a rule never breaks it. Loosening one is a change to the rule itself, made where it is kept, where its author and its readers see it. The upper layer wins a clash for the same reason.

**Why rules rank the other way from agents and skills.** Where two layers ship an agent or a skill of one name, the project's takes the place of a capability's, and a capability's the place of core's. That order is deliberate, and so is its reverse here. An agent or a skill is a whole that a layer replaces, to specialise it for its work, and only one of two can run. Rules compose: every layer's bind at once, and a lower layer only adds to an upper one. A project that could replace core's rule would take away what the methodology guarantees, unseen. Core's loaded file says how the layers stand, as a capability's does, so a session in a project with no capability's rules reads it too.

**Why a clash between two capabilities stops the step.** Two capabilities stand side by side, so neither outranks the other. A session that chose between them would decide what no author decided. Asking the person each time would ask the same question in every session, with no answer it could keep, since a project's rule that picks one would loosen the other, and an unattended run has no one to ask. Stopping the step and reporting the clash makes it a defect for the capabilities' authors to settle where their rules are kept.

**Why a core rule never names a capability's rule as its successor.** A capability may be absent from a project, and a successor there would name a rule that does not exist. COR-051 point 4 also keeps a successor in the rule's own set or an inheritor, so that where the old rule bound the successor binds. A core rule keeps what holds everywhere, and the capability's own set holds the rest.

**Why a moved rule is written again.** A project's rule was written for that project's tools and checks. Moved as it stands into a capability, it would be false in a project that has neither, against COR-014. So the capability states what holds wherever it is installed, under an origin of its own, and the project keeps what is its own.

**Why validation reports, rather than fails, where the place is absent.** A checkout without the adapter's place for these files is one where the deploy never ran, or one whose project keeps that place out of version control, such as a continuous-integration checkout. Its sessions load none of these files, and only a deploy, or a choice of what the project keeps in version control, could change that. Failing there would fail a healthy project for that choice. Where the place is there, a missing or differing file is a deploy left incomplete or a file edited by hand, which the next deploy mends, so it fails. The check keys on that place itself, not on whether the adapter deployed something else, since a project may keep one of the adapter's folders in version control and not another.

**Why whether a session loads the file is a harness requirement, not a check.** Validation runs outside every session. It can see that the file is where the harness should load it, not that a session loaded it. A harness may start a helper with a context of its own, or a run that skips the project's settings. Reporting that indeterminate keeps "the file is in place" from reading as "every session follows the rules" (COR-047 point 3).

### Alternatives considered

- **A line for each capability in the project's instruction file.** Rejected: uninstall would remove text from a file the project owns.
- **A region of the adapter's own inside the project's instruction file.** Rejected: its content would change at each install and uninstall, inside a file the project writes. COR-002 inserts what is absent and defines no region of the adapter's inside a project's file.
- **The harness's start hook, adding the file to a session's context.** Rejected as the means: a project's own hook may take its place, and what a hook adds may not last the session.
- **One loaded file joining core's rules and every installed capability's.** Rejected: one file of several owners breaks the no-shared-files invariant, and it would be generated in the project at each install, which COR-068 point 3 rules out.
- **Generating a capability's loaded file at install or sync.** Rejected, as "Why the file is generated where the capability is authored" says.
- **Loading a capability's rules only in the sessions of its own agents, or only for the files a session touches.** Rejected: a loaded rule binds on any session's work where the capability is installed, and a person may do the capability's work with any agent. Binding on files only where a scope selects them is what ordinary rule sets do (COR-051 point 7).
- **A switch that keeps a capability's loaded set away while it is installed.** Rejected: a rule about a session's work leaves a project only installing the capability or not (COR-068).
- **Accepting each capability rule again in each project.** Rejected, as "Why installing accepts the set" says.
- **Asking the person at each clash between two capabilities.** Rejected, as "Why a clash between two capabilities stops the step" says.
- **Retiring a core rule with a capability's rule as its successor.** Rejected, as "Why a core rule never names a capability's rule as its successor" says.

## Implications

- **COR-068 points 3, 4 and 5** gain forward pointers to this record, and validation stops refusing a capability's set marked loaded.
- **The adapters' shared specification** counts the deploy of a capability's loaded file among the deploy primitives, and has the undeploy primitive remove it. The architecture record that realises this one decides each harness's place, the file's path among the capability's files, the form of the prose that names the layer, the form of a citation and where the check runs.
- **The harness requirements** gain the requirement of point 6, and each adapter answers it in its support declaration.
- **The capabilities' reference** names a capability's loaded set and its loaded file among the files a capability may ship (COR-017).
- **Rules that bind only with a capability** move from core's set and from a project's own rules to that capability's loaded set, each leaving its old place as point 5 says. The architecture record that realises this one names which.
- **Git conventions** stay core's where [COR-008](COR-008-git-conventions.md) and [COR-009](COR-009-pr-workflow.md) decide them for every project, branch naming and the pull-request workflow among them. Only what binds where a work tracker is in use moves, as point 5 says.
- **Core's loaded file says how the layers stand:** its preface gains a short statement that every layer's rules bind at once, that a capability's and a project's add to core's and never loosen them, and that the upper layer's rule binds where two cannot both be kept (point 4). It closes by naming each installed capability's loaded file as where that capability's rules are kept, in place of its documentation. The change that realises this record makes both edits, and a person accepts them in it (COR-066).
- **Stands on these records, all accepted:** COR-001, COR-002, COR-005, COR-008, COR-009, COR-014, COR-017, COR-047, COR-051, COR-055, COR-065, COR-066 and COR-068.
