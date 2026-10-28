---
id: COR-068
title: Operational rules are a loaded rule set
status: accepted
date: 2026-10-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the operational rules that every agent session loads are kept as a rule set, so each rule gets what a rule set gives: a permanent id, a status, an origin, and a successor when it retires. The set is a *loaded* one. It binds on the work of the sessions that load it, not on a project's files, so it has no scope, no inheritance and no pins. The file a session loads is generated from the set where the set is authored. It holds the set's accepted rules under the set's sections, and none of the set's data. Core's set binds in every project that adopts the methodology, and a project's own in that project. A citation such as "core rule 19" keeps naming the same rule.

## Context

Every agent session loads the methodology's operational rules through the harness's include, beside the rules of the project's own (COR-014). They are numbered, and they are cited by core or project and their number across records, documents and code. The numbers are not permanent: a rule inserted or removed renumbers the rules after it, and each citation of a moved rule then names another rule, with nothing to say so. A retired rule leaves no trace of where its content went. A rule cites the record that decided it only by convention (COR-065 point 7), and nothing checks it.

Rule sets have these guarantees already (COR-051 points 3 to 5): permanent ids, statuses with the acceptance gate, origins checked by validation, and retirement with a successor. COR-051 point 1 leaves operational rules out of rule sets. They do not fit a rule set's binding, which this record reads as the reason. A rule set binds on artefacts that a scope selects, through routes and pinned inheritance (COR-051 point 7). An operational rule binds on what an agent does in a session, from the session's start, and core's must bind in every project the methodology runs in, with no opt-in. A pin would hold back exactly the rules that must reach every session.

A rule set does two jobs, then. One is a rule's identity and history: its id, status, origin and successor. The other is where its rules bind: scope, routes, pins, inheritance and extension points. Operational rules need the first job and not the second. Giving them a second mechanism for the first would build again what rule sets have.

## Decision

**Operational rules are kept in loaded rule sets. A loaded set has no scope, inheritance or pins. Its accepted rules bind on the work of each session that loads the file generated from it. Core's set binds in every project, and a project's own in that project.**

### 1. A loaded rule set

A *loaded* rule set is a rule set whose rules bind on the work of the agent sessions that load it, not on artefacts (refinement of COR-051 point 1).
- **It has no scope,** inherits no set and is inherited by none, so no route reaches it (refinement of COR-051 point 2). Without inheritance, it offers and fills no extension point. It declares no part a check enforces, since a check enforces a part only where a rule binds on an artefact.
- **One loaded set to a component,** and one to a project, so a citation by core or project and a number names one rule.
- **What else of COR-051 holds:** the file's shape of data in front matter and prose in the body, ids (point 3), statuses and the gate (point 4), origins and their validation (point 5), method and project sets and how each is cited (point 6).
- **Each rule is an artefact** in its own right, as every rule of a set is (COR-051 point 2), so a change to it is friction for what anchors to it (COR-050).
- **Which kind of set a rule belongs in:** a rule that must bind on a session's work in every project of its layer, with no opt-in, goes in a loaded set. A rule a project chooses to bind on its own artefacts goes in an ordinary set.

### 2. Where its accepted rules bind

A loaded set's accepted rules bind on the work of each session that loads its loaded file (point 3). A proposed, superseded or withdrawn rule binds nothing, and is not in the loaded file.
- **Not on artefacts.** The one answer to which accepted rules bind on an artefact (COR-051 point 7) holds no rule of a loaded set, even one about files. Such a rule is kept by the sessions that load it, not judged against an artefact (refinement of COR-051 points 4 and 7).
- **A method set binds with no inheritor.** COR-051 point 7 lets a method set bind only through a project's set that inherits it. A loaded method set binds where its loaded file is loaded instead (refinement of COR-051 point 7).

### 3. The loaded file is generated from the set where the set is authored

The file a session loads is a projection of the set (COR-065 point 1), generated where the set is authored.
- **Its content:** the set's accepted rules in the set's order, under the set's sections, each rule under a heading that names its id and title, followed by its statement. The prose between sections carries over. It holds no front matter, no origin and no retired rule, and takes the form the harness's include requires. Each statement keeps its pointer to the record it rests on (COR-065 point 7). The origin is the validated data behind that pointer.
- **Kept in step:** a change that accepts, edits, supersedes or withdraws a rule regenerates the loaded file in the same change. Validation fails where the set is authored when the loaded file does not match its set.
- **Delivered with its set:** a project that receives the set by sync receives its loaded file with it, at the place the harness's include reads, by the same mechanism as before (COR-001). The project neither generates it nor edits it. Core's loaded file is not suspendable (COR-001), since core's set binds in every project.

### 4. Which sets bind where

- **Core's loaded set** is a method set the backbone ships. It binds in every project that adopts the methodology, from its first session.
- **A project's own loaded set** is a project set. It binds in that project.
- **A capability's loaded set** binds in each project that installs the capability, while it is installed. How its loaded file reaches the sessions, and how a project's rules relate to a capability's, are decided with the first capability that ships one. Until then, validation refuses a capability's set marked loaded, so no accepted rule binds nowhere unseen.

### 5. A version that no pin holds

A loaded set keeps its version, as every rule-set file does (COR-051 point 2), and COR-051 point 7's rules say which number a change moves. Nothing pins it, so a new version holds nothing back. Its accepted rules bind once their acceptance lands, and in a project once the sync that brings them runs.

### 6. Ids, origins and citations

- **A rule's id is its set's** (COR-051 point 3), so it is never renumbered and never reused. A rule that leaves is superseded or withdrawn, and stays in the set (COR-051 point 4).
- **Core's set is named `OPS`,** for operational. Its rules keep the numbers they held before the set existed, so the rule that was core rule 19 is `backbone:RS-OPS-019`, cited with its component as a method set's rule is (COR-051 point 6).
- **Each rule's origin** cites the record that decides it, or gives the decider's words, which may name the issue where the rule was decided (COR-051 point 5).
- **A citation by core or project and a number,** such as "core rule 19", names that layer's rule of that number, and stays a valid citation of it (refinement of COR-051 point 6).
- **Validation reports** a citation, in either form, of a rule that is missing, superseded or withdrawn, as a warning, since it is read from prose (COR-055). Where a set is authored it reads every citation of the set's rules. In a project that receives a set, it reads the project's own citations of that set's rules. It reads neither synced copies nor history: superseded records and recorded answers stay as they were written.

### 7. A project's rules not yet in a set

A project's operational rules kept as a plain file, not as a loaded set, are loaded as they stand. Nothing checks their numbers or their origins. The project converts the file into a loaded set of its own when it chooses, and gives each rule an origin then. Until it does, a citation of one of its rules by project and number is not checked.

## Rationale

**Why rule sets, not an id scheme of their own.** Rule sets already give permanent ids, statuses, origins, successors and their validation. A second scheme for operational rules would build all of it again, and leave two families of ids for one need. The parts of a rule set that do not fit operational rules are those that say where a rule binds, so a loaded set leaves exactly those out.

**Why no scope, inheritance or pins.** A rule set's scope and routes answer which artefacts a rule binds on, and an operational rule binds on a session's work. A pin exists so that a new rule reaches an inheritor only after the inheritor reviews it (COR-051, "Why pin the major version"). Operational rules keep the methodology's invariants, such as which files a project may edit, and must reach every session at once. A pin would hold back exactly those.

**Why core's set binds with no opt-in, and a capability's by installing.** A project chooses the methodology by adopting it, and the methodology's invariants hold only if every session keeps them. So core's rules bind from the first session. COR-051 gives a method set no scope so that a project chooses whether its artefacts are bound. That choice is about a project's artefacts, not about the methodology it adopted. A capability is chosen by installing it, so its rules bind from that choice and end with it. An ordinary capability set leaves a project the choice of where it binds. A loaded one leaves only installing or not, since a rule about a session's work has nowhere narrower to bind.

**Why a rule about files may sit in a loaded set.** Some rules about files must bind in every project with no opt-in, such as one on what a migration script must do. An ordinary method set binds nothing until a project's set inherits it, so such a rule would bind nowhere by default. The cost is that no per-artefact check or review judges a file against it. The sessions that load it keep it.

**Why the loaded file is generated.** A session reads the whole file at every start. Front matter, origins, anchors and retired rules would fill every session's context with data an agent does not act on. COR-051 rejected a generated view for reading on two grounds: generated files can drift, and statements are awkward to write and review as data. Validation where the set is authored fails a loaded file that drifts from its set, and the statements stay prose in the set. A file kept by hand beside the set would drift, and a sidecar is not open to a rule-set file (COR-063 point 5).

**Why accepting a rule regenerates the loaded file.** A rule binds from its acceptance (COR-051 point 4). A loaded file still holding the earlier text would have sessions follow what is no longer accepted, or miss what is. Regenerating it in the same change keeps acceptance and what sessions load together.

**Why a version that holds nothing back.** One shape for every rule-set file keeps one schema and one validation. Without pins a version gates nothing, but it still tells a reader what a change did. A new accepted rule moves the major, and for a loaded set that is honest: it changes what every session must do.

**Why a citation by layer and number stays valid.** Records, documents, code and decided answers cite operational rules by core or project and number. Keeping each rule's number as its id leaves every such citation correct, with nothing rewritten, a decided answer among them.

**Why a project's plain file is left as it is.** Converting it needs an origin for each of its rules, and only the project knows who decided each and why. A conversion run for it would leave the rules proposed, binding nothing, or invent their origins. Loading the file as it stands keeps every project's rules in force, and leaves the conversion to the project.

### Alternatives considered

- **Permanent numbers in the form of a record's points** (COR-058). Rejected. It gives a rule no status, its retired points sit in front matter that every session would load, its stub sentence names a point of the same record, and its points need a Decision heading that a rules file has none of. It would also build retirement and origins a second time.
- **An id family of its own,** with retirements in a list outside the loaded file. Rejected. It builds again what rule sets have, and leaves two families of ids.
- **Operational rules as ordinary rule sets,** reached through a project's own set. Rejected. Core's rules would bind in a project only once the project's set inherited them, and pins would hold back every new rule.
- **Sorting rules by what they apply to,** rules about files into ordinary rule sets and rules about a session's work into a form of their own. Rejected, for the reason under "Why a rule about files may sit in a loaded set".
- **Loading the rule-set file as it stands.** Rejected. Every session would load its front matter and its retired rules.
- **Converting a project's plain file by a migration.** Rejected. A migration cannot supply an origin for a project's own rule.

## Implications

- **The backbone ships core's loaded set,** its loaded file where the harness's include reads it, the generation, and validation of the loaded file against its set. The rules area's reference says where the set and its file live, and how a project converts its own file. The backbone's sets live where the places rule sets are found put them. The architecture record that realises this one decides where the generation and its check live.
- **The rule-set schema** marks a set as loaded, and refuses a scope, an inheritance, an extension point, a fill and a part a check enforces on one.
- **COR-051 points 1, 2, 4, 6 and 7** gain forward pointers to this record. **COR-058 point 10** says that operational rules in a loaded set have permanent ids under this record.
- **The rule-set reviewer and per-artefact checks** judge no rule of a loaded set, since none binds on an artefact.
- **Agents,** reviewers and skills cite operational rules by id or by layer and number. Either names the same rule.
