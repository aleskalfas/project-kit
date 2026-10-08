---
id: DEC-001
title: Software analysis keeps actors, use cases, journeys and terms true as the software changes
status: accepted
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A project needs a written account of *what its software must do*: who uses it, what they are trying to achieve, how they get there, and what the words mean. Without one, every new person and every agent reconstructs it from code, and every design is judged against a picture that exists only in someone's head.

Such an account decays silently. Code changes, the account does not, and nobody notices until a reader is misled or a design is built on something no longer true. This capability's membership test follows from that: **an artefact belongs here if a change to the software can make it false, and we want to find out when it does.**

The core layer supplies the machinery this needs:
- where a project's technical documentation lives (COR-049);
- anchors and friction, which detect when what an artefact rests on has changed (COR-050);
- rule sets, which hold the rules a component ships, each binding at its status (COR-051);
- connection points, through which components exchange knowledge and signals without depending on each other: data slots (COR-052) as one kind, addressed by role (COR-053).

This record decides what the capability keeps, in what shape, where, and how it stays true.

## Decision

**The capability keeps four kinds of product knowledge (actors, use cases, journeys and glossary terms) as anchored artefacts, each carrying every part its kind ships, and keeps them true through revalidation: planned before code changes, and triggered by friction after.**

1. **What it keeps, and in what shape.** This point gives what each kind is for, and the distinctions behind its parts. Each kind's declared structure, below, holds the full list of its parts, their order, labels and forms.
   - **Actors:** named roles that use the system, not personas. An actor says what the role is and does with the system, when it comes to the system and with what, and carries in its front matter the needs it brings.
   - **Use cases:** one actor's goal and how the system fulfils it: the other actors who take part and what it must protect for each, what holds before it starts, what starts it, the main path and its variants, the state that shows the goal is met, and what the system still guarantees when it ends early or fails. What holds before it starts is split in two. A precondition is a state the system or an earlier use case made true, which no step checks. An assumption is what must also hold that nothing in the system secures, and it names the record that admits it.
   - **Journeys:** one actor's end-to-end path across several of its use cases, including the seams between them where the path can break. Each step carries its own seams: what it needs from an earlier step, or from a use case outside the journey, and how that can break. Like a use case, a journey states its goal, its own variants, the state that shows the whole path succeeded, and what still holds when it stops before its end. It is a summary-level path through the system, not a map of the actor's experience.
   - **Glossary terms:** the domain words, each with a stable id separate from its display name and a record of names it replaces, so that renaming a term does not break what cites it. A term's name is written as running text writes it, with no article, and in lower case unless it is a proper name. Its definition is a phrase that could stand in for the term, in the form terminology standards give a definition (ISO 1087 and the ISO/IEC Directives, Part 2): its broader kind, then what sets it apart. A term also gives an example, and the words it could be confused with and how each differs. The names it replaces are only those it carried in the analysis or in an accepted record; a working name that now means something else is one of the words it could be confused with.

   A user story, in the sense of a need stated in one sentence, is an actor's need and a use case's goal, not a separate artefact. The hints the capability ships ask for each need, and for the goal of a use case or a journey, in the actor's own voice: one sentence that starts with its verb, or with *Never* and the verb. A project that prefers another voice replaces those hints.

   **A kind's structure.** Every artefact and every record carries every part its kind ships, and a part with nothing to say reads `None.`. Which parts those are is the kind's *structure*, declared once as data. It binds once the capability's format rule is accepted, and a project may add to it but never relax it.
   - **Declared once, as data.** Each kind, the revalidation record (point 6) among them, declares its structure in data whose schema this capability ships. A structure lists the parts of the kind's body in their order, each with a permanent id, a label, a hint and an example. It also gives the forms a script checks in a part or a front-matter field, and the hint of each front-matter field a writer fills. For the glossary, a collection, it covers each term's section and the file's head. The body of the kind's template is rendered from the structure and shows exactly it; the template's front matter is written by hand and held to the kind's schema. Nothing reads a structure out of a template's text.
   - **Hints.** Where the stamp leaves a part or a field for a writer to fill, its hint is the placeholder, one marked line that says what goes there. A hint left in is refused whatever a rule's status, as any placeholder is, and the check's messages repeat the hint. A hint is advice: what binds is a part's presence, its order and its form. A tool takes data from an artefact's front matter only: a body's parts serve readers and the check, never another tool.
   - **The rule for every kind.** Every part a kind ships is present in every artefact or record of that kind, and wherever the structure binds, a missing part is an error. A part with nothing to say reads `None.`, where its structure allows it, so a script tells a part considered from a part forgotten. A project's own additions stay outside this rule: each is optional unless the project marks it required.
   - **When it binds.** The capability's method rule set (COR-051 point 6) holds a format rule: an analysis artefact or a revalidation record carries its kind's declared structure. The set has no scope, and binds through the capability's own check. The structure is that rule's checkable part, beside it as a schema is (COR-051 point 1), and no part of the rule's content. So changing a structure leaves the set's version alone, and a change that fails an artefact or a record the check passed before is a breaking change of the capability. The structure binds at the rule's status: under any status but accepted, the normal check reports nothing of it (COR-051 point 4). A kind's schema checks its front matter whatever the rule's status.
   - **A preview on request.** A check previews a proposed rule on request, as if it were accepted, and never fails on what it previews. A preview finding takes the severity that reports without judging, labelled `preview` (COR-055 point 4).
   - **What a project may change.** A project may relabel a shipped part, and replace the hint and example of a part or a field, with no rule, since a hint binds nothing. It may also tighten a structure, by adding parts or by requiring more of it, in data of its own in the capability's project tier. Each tightening names the project rule that asks for it, and binds at that rule's status and at the format rule's. It never relaxes a shipped structure: it does not drop or loosen a shipped part, or reorder the shipped parts. Nor may it invent a form, or add a kind, which needs a decision of its own (point 11). A part's id is permanent once shipped, retired and never renamed, as a rule's id is (COR-051 point 3). A project rule reaches only as far as the scope of the set that holds it (COR-051 point 2), so a tightening applies to an artefact only where that scope covers it. The stamp writes a revalidation record whole, so a writer adds a project's parts to a record by hand.
   - **Chosen at adoption.** Adopting the capability includes choosing each kind's parts. A project reviews each kind's shipped structure, and keeps it, relabels it or adds parts of its own; a shipped part it finds wrong is a change it proposes to the capability. The shipped structure is a starting point a project reviews, never a default it skips.
   - **When a structure changes.** Live artefacts, the actors, use cases, journeys and terms in force, describe the system as it is, so they are always migrated to the current structure. A revalidation record is the log of a revalidation that happened: it stays as written, and is checked against the structure in force when it was written. A withdrawn artefact is history too, and the check holds it to no part or form that came after its withdrawal.

2. **Where it keeps them.** Everything lives under the project's internal documentation root (COR-049), in an `analysis` area laid out after a use-case model:
   - the glossary is one collection file, serving everything;
   - the use-case model holds a folder of actors, one file each, a folder of use cases (optionally grouped by functional area), and a folder of journeys;
   - revalidation records are kept in a folder of their own.

   **A kind with many files gets its own folder; a kind with one file is a file.** Folders appear only when something goes into them.
   - **Location.** The `analysis` sub-path is declared in the capability's package metadata. Its location is recorded on first use in the capability's own project configuration, as the documentation-roots record requires (COR-049). A later change of root therefore never moves an existing analysis.
   - **Places.** The capability declares the glossary, actors, use cases and journeys as places holding anchored artefacts (COR-050). Revalidation records describe an act and are not anchored artefacts, so their folder is not a place: the capability declares it as a folder of held documents (COR-050 point 1), so the records are listed as this capability's and no place reads them as artefacts.
   - **Surface.** The capability declares no surface by default, since it cannot know a project's code. The project declares which paths its analysis ought to cover, in the friction key of its backbone configuration (COR-050).
   - **Ownership.** The artefacts live outside the capability's own subtree, so uninstalling the capability never removes them.

   The exact layout is in the capability's README, and each kind's parts are in its declared structure (point 1). The friction block — anchors and revalidation — follows the core schema, inside the methodology's container in each artefact (COR-050, COR-053).

3. **Identifiers.** Use cases and journeys are numbered within the project (`UC-NNN`, `JRN-NNN`), independent of any grouping. Moving a use case between areas never changes its id. Actors and terms are keyed by stable ids, an actor's naming its file and a term's its entry in the glossary, with distinct prefixes (`ACT-` for actors, `TERM-` for terms), so that no two artefacts in the analysis share an id.
   - **Append-only.** An artefact is withdrawn, never deleted, and its id is never reused: once settled, an id names one artefact for good. There is one exception, and only the project makes it; no tool infers it. Artefacts that nothing cites — a pilot abandoned before anything cited it, say — may be removed from the default branch, and the project may then name them; their ids are free again. Nothing else frees an id. Something cites an id when it names the artefact by that id and expects the analysis to answer for it; history fixed at a commit, such as a commit message, does not.

     Inside a use case, steps are numbered and variants are lettered after the step they branch from. Both are append-only too, because journeys and evidence cite them. A check compares each use case with the default branch's, and reports a step or a variant renumbered or removed.
   - **Parallel work.** When two lines of work number a new artefact the same, the first to reach the default branch keeps the number. A check that compares the branch with its base reports the collision, and the other renumbers before merging. A new number is given past what the default branch holds, and past any base the stamp is named, while a collision is judged at the merge at hand — against the base of that comparison, an integration branch included (refinement per COR-054, point 3).

4. **Every artefact says what makes it true.** Each carries anchors and a revalidation in the sense of the anchors-and-friction record (COR-050). Anchors run in one direction only, so they never form a cycle:
   - Actors and terms anchor to where the software or a decision embodies them. An actor with no such anchor is reported as unanchored, which is not an error.
   - Use cases anchor to their actor and to each other actor they involve, as artefact anchors, and to the code they exercise and the decisions they rely on. The other actors are listed in the use case's front matter, so a check resolves each to an actor.
   - Journeys anchor to their actor; to the use cases they pass through, and to each use case outside the journey that a step relies on; and to the code and decisions at the seams between them. A journey's ordered list of steps, and its list of the use cases it relies on, are the source. Its use-case anchors are written into its anchor field from the two by the capability's stamp and check, and validation requires them to match, so the friction check sees them and they cannot drift apart.

   A changed actor flags the use cases and journeys that anchor to it, and a changed use case flags the journeys that pass through it or rely on it. Friction is reported in that order. Revalidation is this capability's name for the act the core record calls by the same name; recording it on the artefact — its `at`, its outcome and any deferrals — is what clears friction (COR-050).

5. **Revalidation.** A **revalidation** is one review of some artefacts against one version of the system: a proposed design, or the actual code. It is an act, repeated whenever something triggers it:
   - **planned**: a change is proposed, before code;
   - **drift**: friction on a pull request;
   - **scheduled**: friction found by the whole-repository check;
   - **close**: a pull request that changes artefacts, or their anchors, lands;
   - **onboarding**.

   It ends, for each artefact, in one of these outcomes:
   - it **holds**;
   - **the analysis was stale**: the change was intended, so the artefact is updated;
   - **the code regressed**: the artefact still describes what is wanted, so a defect is reported rather than the analysis rewritten to match;
   - **a gap was found**: behaviour exists that nothing describes, or a description has no behaviour.

   These four outcomes map onto the core record's two (refinement per COR-050): *holds* and *the code regressed* are recorded as `unchanged`, with the justification saying why the description stands — for a regression, naming the defect reported; *the analysis was stale* ends in `updated`; *a gap was found* ends in `updated` where the artefact itself changed, and in `unchanged` — the justification naming the gap and the artefact that fills it — where the gap is closed by a new artefact. Friction an agent or person chooses not to resolve yet is a core deferral, with its reason, not an outcome. Whoever performs the revalidation (a person, or an agent) records it on the artefacts it covered. An agent proposes the outcomes. Where "stale" versus "regressed" is ambiguous, a person decides before any revalidation is recorded. The analysis is never silently rewritten to match broken code.

6. **Records only when there is something to say.** A revalidation that is planned, or that finds a gap or a regression, leaves a record in the revalidations folder. The record names the change that carried it (a tracked work item, a pull request, or a range of commits), the trigger, the artefacts covered with their outcomes, and the gaps. Each gap is labelled with the artefacts it affects, and says what resolved it or carries its fix. A check holds the gaps to the outcomes: every artefact whose outcome is a regression or a gap is named by a gap, and every gap names an artefact the record covers. Records cite artefacts by id, including withdrawn ones, and are named by date and subject rather than numbered, so parallel work cannot collide. A routine revalidation that finds everything still holds writes no record: the artefact's own revalidation block, with its outcome and justification, is the record.

   **What a planned record reviewed.** A planned record also names where the design it reviewed stood, in its front matter as `reviewed-against`. Each source of the design is named by what it is, its link where it lies outside this repository, and its version. The version is a pointer to the text reviewed, never a version number: the capability's artefacts and records carry no declared versions.
   - Text in a repository is pinned by a commit its default branch holds, or, in this repository, by the change the record lands in, whose commit is found from the history as a revalidation's is (COR-050 point 3).
   - Text in a tracker is pinned by its link and the time it was read.
   - A pull request's head is never a pointer, since a rebase loses a head reviewed mid-way. Nor is any other commit the default branch does not hold, since a squash leaves a branch's commits off it (COR-009 point 1).

   Validation checks the pointers' form. This record puts the check of where each commit sits outside validation (COR-055 point 1), because the pointers are provenance, not a gate. That check runs offline, and reports each commit of this repository that the default branch does not hold. A commit it cannot place, beyond a shallow clone's history say, it reports as unknown, never as a failure.

7. **Revalidation is not testing.** Revalidation asks whether *the description* is still true of the software, and usually fixes the description. Testing asks whether *the software* still does what the description says, and fixes the software. The capability owns revalidation. It does not run the software.

   The capability provides the **analysis role** and, under it, accepts a data point, `<methodology>::analysis:revalidation-evidence` (refinement per COR-053), for executed results that confirm or refute an artefact at a commit:
   - its schema is a companion schema the capability ships, named after the point (COR-052). At version 1 it has one entry per result, keyed by three parts — the artefact, the commit and the **check** — and holding the result and what was run. The check names one thing that was run against the artefact — a test, a scripted walk-through — and keeps that name from commit to commit; a filler gives each result it reports for one artefact at one commit a check of its own. A capability's checks open with the capability's own name, and a project file's with `project`. So two fillers' results for one artefact at one commit stand side by side, and only two that claim one check collide, which the project settles (COR-052 point 4). The opening name is a convention: where the capability's validation reads the point it warns on a capability's check that opens with another name, and never refuses, because the project replaces a capability's entry by writing one under that capability's check;
   - its policy is `union`;
   - no default takes part;
   - its inert policy is `fallback`, because the evidence advises and does not gate.

   The slots record (COR-052) allows three kinds of filler: a project file, a capability, and the provider's default. Here, a capability fills it (a later testing capability, or one that reads the test results the project already produces), or a project file records results, and no default takes part. Evidence **informs** a revalidation: a passing result is support for "holds", and a failing one is a regression with proof attached. It never replaces the revalidation. Only a revalidation or a deferral recorded on the artefact clears friction (COR-050). A revalidation record keeps a copy of each entry it drew on. A routine revalidation that writes no record (point 6) keeps none: its justification on the artefact says in its own words why the description holds, and naming a result is not a justification. Evidence kept on the artefact itself is not decided here (point 11).

8. **What it contributes to others.** The capability contributes to the documentation role's readers point, `<methodology>::documentation:readers`, by mapping its actors and their needs onto that point's shape (refinement per COR-053). It contributes to the work-tracking role's use-case point, `<methodology>::work-tracking:use-cases`, every use case the default branch holds, withdrawn ones included, each under its id. Once settled, an id names one use case for good; the only id that later names another is one the project freed, declaring that nothing cites it (point 3). Its filler reads settled state alone, and gives the whole set or no answer when a reading it relies on fails (refinement per COR-052 point 6 and COR-054). Each contribution addresses a role, not a capability, so any provider of that role receives it. A contribution is inert whenever no provider of its role is installed, and the capability never requires one.

9. **Brownfield onboarding.** A project with no analysis starts with nothing anchored, so friction reads zero. The signal is uncovered surface: the paths the project declares its analysis should cover (point 2), against what the artefacts anchor to (COR-050). An agent derives candidate actors, use cases and terms from the code, the existing documents and the project's decisions. On a brownfield project these are the ground truth, so the usual order is reversed. A person confirms the candidates. Onboarding needs a non-empty declared surface, and it is complete when that surface is covered. Every artefact must be either anchored, or explicitly accepted as unanchored with a reason recorded on the artefact, such as an actor that no code embodies. The reason is the core friction block's `unanchored-because` (COR-050 point 1), so an accepted actor or term is listed apart and never counted as unanchored work left to do (point 8).

10. **Independent.** The capability works with no work-tracking component and no testing component installed. When a work-tracking component is present, it may cite revalidation records from its work items, as an enrichment.

11. **Scope boundary.** Lifecycles on the process substrate (a planned revalidation; onboarding), further analysis artefacts (constraints and quality requirements, architecture views), executable use cases and evidence kept on the artefact itself are outside this record. Each needs its own decision when a real need arrives.

## Rationale

**Why product knowledge, not per-design documents.** A use case is true of the product for as long as the product supports it. What belongs to one design is the *revalidation* of the use cases it touches. Keeping the two apart means the knowledge persists after the design ships, and each design's validation is recorded where it happened.

**Why a use-case model layout.** Grouping actors with the use cases they take part in, and keeping the glossary apart because it serves everything, follows an established requirements practice that analysts and newcomers already recognise. Global ids with optional grouping get the benefit of functional areas without the cost of renumbering.

**Why roles, and paths through the system.** An artefact belongs here if a change to the software can make it false. A role's needs can go false when the software changes, so an actor is a role, covering everyone who plays it; a persona's imagined traits cannot. A journey's steps and seams are what a change can break, as in the critical user journeys of reliability engineering, so a journey is a path through the system; how the actor feels along it is not something a change to the software makes false.

**Why each kind's structure is data, with its template rendered from it.** A script checks only a structure it can read, and a template that writers copy drifts from any other statement of it. Declared once as data, the structure gives the check one home, and a template rendered from it cannot disagree with the check. The hint stands where the content goes, so the first writer, often an agent, meets what a part asks for rather than a bare label.

**Why every shipped part is present, and `None.` is an answer.** A part left out reads the same as a part forgotten. Asking for every part, with `None.` where there is nothing to say, makes the writer consider each one, and lets a script see that they did. A project's own additions serve that project alone, so the project decides whether each binds.

**Why a use case splits what holds before it starts, and names its guarantees.** A precondition is secured by the system, so a step may rely on it. An assumption is secured by nothing, so it is a risk to name, and a candidate for a check; requirements standards list assumptions apart for that reason (ISO/IEC/IEEE 29148). What the system still guarantees when a use case fails is what keeps a failure safe, so it gets a part of its own, and the other actors record whose interests the path must keep.

**Why a project reviews the shipped parts.** The shipped parts come from established practice, not from the project's own system. Only a project's own examples show whether they suit it, and a default nobody reviewed binds its artefacts to a choice nobody made. What a review finds goes into the project's own parts, or into a change proposed to the capability, as a project does with a rule it disagrees with (COR-051 point 7).

**Why live artefacts move to a new structure, and records do not.** An actor, a use case, a journey or a term describes the system as it is, so it is read in the current shape. A record says what one revalidation found on its day. Its words are the decision of whoever performed it, and rewriting them into a later shape would change what was decided.

**Why the actor's voice ships.** A need in the actor's first-person voice is how user stories state one, and a goal that starts with its verb is how use cases name one. Neither is one project's style, so the capability ships both in its hints, and a project that writes them otherwise replaces the hints.

**Why revalidation owns both planned and drift-triggered checks.** Checking before code and checking after an unplanned change are the same act with different triggers. One record shape, and one set of outcomes, serve both.

**Why records only with findings.** Most revalidations find that everything holds. Writing a file each time would bury the few that matter. Git already records the routine ones through the revalidation recorded on the artefact.

**Why a planned record names the design by pointer.** A pointer returns the exact text reviewed, which no version number does. A version an author declares on a document would tell a dependant one fact, whether the meaning changed: a minor and a major version would each ask the dependant to look again. So the capability's artefacts and records carry no declared versions, and a record points at the text itself.

**Why keep testing out.** Revalidation judges a description by reading; testing judges software by running it. Merging them would make this capability depend on executing arbitrary software, and would blur whose fix a failure demands. The evidence slot lets executed results inform revalidation without that coupling.

**Why a declared exception to never reusing an id.** An id is never reused so that whatever cites it keeps naming the artefact it meant. Artefacts nothing cites carry no such promise: a pilot abandoned before anything cited it leaves ids that name nothing anyone reads, and without the exception the analysis would count past them for good. The places that may cite an id, such as other repositories, trackers and code, are open-ended, so no tool can check them all. A person judges that nothing cites the ids, and answers for the judgement: the project declares the exception, naming each id it frees, and a reviewer sees the declaration as an act of its own.

**Why a person decides stale versus regressed.** The distinction is intent: was the change meant? An agent can propose it from the change's context, but when intent is unclear, only a person knows. Getting it wrong either rewrites the truth to match a bug, or reports a defect for an intended change.

### Alternatives considered

- **Use-case sets per design, validated once.** Rejected. The knowledge would be scattered across designs and would stop being maintained after each one shipped.
- **A flat analysis folder.** Rejected. Actors and terms get lost among many use cases, and there is no natural place for grouping or later modules.
- **Actors kept in one collection file.** Rejected. An actor's needs would sit far from its description, and keeping them beside it in the body would make a tool read data from a body, or keep one fact in two places.
- **Reading a kind's structure from its template.** Rejected. Required parts, a project's additions and its own content would need markup in the template, and a script would parse text a writer copies.
- **Keeping a structure in its rule's content.** Rejected. Every change to a structure would version the rule set and flag the rule's dependants, though what the rule says had not moved.
- **Hints only in the check's messages and the skill.** Rejected. The first writer, often an agent, would meet bare labels.
- **A project's templates beside the shipped ones.** Rejected. Two shapes of one kind would drift apart, which declaring the structure once exists to prevent.
- **A project's additions in the capability's configuration file.** Rejected. Settings and data would share a file, and a rule anchored to either would be flagged by every edit to both.
- **Optional shipped parts, left out where empty.** Rejected. A part left out reads the same as a part forgotten.
- **The actor's voice as each project's own rule.** Rejected. It is the common convention for needs and goals, not one project's style, and a project that writes otherwise replaces the hints.
- **Reporting a structure under a proposed rule.** Rejected. Everyone runs the normal check, and agents act on what it reports, so its findings would bind in practice what nobody accepted (COR-051 point 4). The preview shows them only to whoever asks.
- **A journey's seams in a part of their own.** Rejected. It gives an overview of every hand-over, but splits each step from what it needs, and a journey is read as a path.
- **The label reader in the backbone.** Not taken yet: this capability is the only component that reads declared labels (COR-007). The trigger to move it is a second component that must read them, such as a documentation component whose kinds of page declare labels, or let a project add to their structure. What would move is the reading of headings and labels, of where each part ends, and the forms any component could use. The forms only the analysis uses stay here.
- **A record for every revalidation.** Rejected. Routine records would bury the ones with findings.
- **Holding every record to today's structure.** Rejected. A part added later would fail every older record, and only rewriting the record would mend it.
- **Naming the design a planned record reviewed in one line of text.** Rejected. No script can check it, and each source of a design stands at a version of its own.
- **Copying the tracker text a planned record read into the record.** Rejected. The copy is exact and offline, but it doubles the design in every record that reads it.
- **A tag for each review, so a design reviewed on a branch keeps its commit.** Not taken: a commit on the default branch, or the change the record lands in, pins a design in the usual case. A tag per review is the fallback where a design must be reviewed before it lands.
- **Versions an author declares on each artefact or design, for a record to name.** Rejected. See Rationale. A pointer serves every source, and a number adds nothing a dependant reads.
- **Storing each artefact's current-or-stale state as truth.** Rejected. It would duplicate what anchors and git already answer; the core's tool-written status is a dated snapshot for visibility, never read for friction (COR-050).
- **Including executed testing in this capability.** Rejected. See Rationale; the evidence slot covers the useful part.
- **Requiring a documentation or work-tracking capability.** Rejected. The capability must be useful on its own.
- **Keeping the ids of artefacts nothing cites taken: counting past them, or restoring the artefacts as withdrawn.** Rejected. Both follow the rule, and the cost is cosmetic, but it lasts: ids that name nothing anyone reads, and withdrawn files describing work the software never had.
- **Freeing the ids of every artefact deleted before a given commit.** Rejected. It frees far more than the artefacts the project means, including any deleted while something cited them.
- **A marker in the history, such as a line in a commit message.** Rejected. It cannot be added to a commit already merged, and it is not reviewed as an act of its own.
- **Inferring which deletions free their ids.** Rejected. Deleting an artefact would become a legitimate way to free its id, the deletion the append-only rule exists to prevent.

## Implications

- **The capability ships** the layout for its artefacts, a declared structure per kind with the template rendered from it, its method rule set with the format rule, the declaration of its places and connections, commands to stamp artefacts and check their shape (friction itself is the core check), and an authoring skill that guides revalidation.
- **Projects** keep their analysis under their internal documentation root, choose each kind's parts when they adopt the capability, keep their own additions in its project tier, and wire the core friction check into their continuous integration if they want it enforced.
- **A change to a kind's structure** carries the migration of the live artefacts with it, and settles how a part it adds is answered and what friction the migration raises on their dependants.
- **History kept as it was written:** the way a record, or a withdrawn artefact, is checked against the structure in force when it was written or withdrawn comes with the first change to a kind's structure that needs it.
- **Documentation disciplines** can read actors and their needs through the readers point, without any dependency.
