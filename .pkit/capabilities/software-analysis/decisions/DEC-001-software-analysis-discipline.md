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
- connection points, through which components exchange knowledge and signals without depending on each other: data slots (COR-052) as one kind, addressed by role (COR-053).

This record decides what the capability keeps, where, and how it stays true.

## Decision

**The capability keeps four kinds of product knowledge (actors, use cases, journeys and glossary terms) as anchored artefacts, and keeps them true through revalidation: planned before code changes, and triggered by friction after.**

1. **What it keeps.**
   - **Actors:** named roles that use the system, each with the needs it brings.
   - **Use cases:** one actor's goal and how the system fulfils it: when it starts, the main path, variants, and when it is done.
   - **Journeys:** an end-to-end path an actor takes across several use cases, including the seams between them where the path can break.
   - **Glossary terms:** the domain words, each with a stable id separate from its display name and a record of names it replaces, so that renaming a term does not break what cites it.

   A user story, in the sense of a need stated in one sentence, is an actor's need and a use case's goal, not a separate artefact.

2. **Where it keeps them.** Everything lives under the project's internal documentation root (COR-049), in an `analysis` area laid out after a use-case model:
   - the glossary is one collection file, serving everything;
   - the use-case model holds a collection file of actors, a folder of use cases (optionally grouped by functional area), and a folder of journeys;
   - revalidation records are kept in a folder of their own.

   **A kind with many files gets its own folder; a kind with one file is a file.** Folders appear only when something goes into them.
   - **Location.** The `analysis` sub-path is declared in the capability's package metadata. Its location is recorded on first use in the capability's own project configuration, as the documentation-roots record requires (COR-049). A later change of root therefore never moves an existing analysis.
   - **Places.** The capability declares the glossary, actors, use cases and journeys as places holding anchored artefacts (COR-050). Revalidation records describe an act and are not anchored artefacts, so their folder is not a place: the capability declares it as a folder of held documents (COR-050 point 1), so the records are listed as this capability's and no place reads them as artefacts.
   - **Surface.** The capability declares no surface by default, since it cannot know a project's code. The project declares which paths its analysis ought to cover, in the friction key of its backbone configuration (COR-050).
   - **Ownership.** The artefacts live outside the capability's own subtree, so uninstalling the capability never removes them.

   The exact layout and templates are in the capability's README. The friction block — anchors and revalidation — follows the core schema, inside the methodology's container in each artefact (COR-050, COR-053).

3. **Identifiers.** Use cases and journeys are numbered within the project (`UC-NNN`, `JRN-NNN`), independent of any grouping. Moving a use case between areas never changes its id. Actors and terms are keyed by stable ids inside their collection files, with distinct prefixes (`ACT-` for actors, `TERM-` for terms), so that no two artefacts in the analysis share an id.
   - **Append-only.** An artefact is withdrawn, never deleted, and its id is never reused. Inside a use case, steps are numbered and variants are lettered after the step they branch from. Both are append-only too, because journeys and evidence cite them.
   - **Parallel work.** When two lines of work number a new artefact the same, the first to reach the default branch keeps the number. Validation reports the collision, and the other renumbers before merging. A new number is given past what the default branch holds, and past any base the stamp is named, while a collision is judged at the merge at hand — against the base of that comparison, an integration branch included (refinement per COR-054, point 3).

4. **Every artefact says what makes it true.** Each carries anchors and a revalidation in the sense of the anchors-and-friction record (COR-050). Anchors run in one direction only, so they never form a cycle:
   - Actors and terms anchor to where the software or a decision embodies them. An actor with no such anchor is reported as unanchored, which is not an error.
   - Use cases anchor to their actor, as an artefact anchor, and to the code they exercise and the decisions they rely on.
   - Journeys anchor to the use cases they pass through, and to the code at the seams between them. A journey's ordered list of steps is the source. Its use-case anchors are written into its anchor field from that list by the capability's stamp and check, and validation requires the two to match, so the friction check sees them and the two cannot drift apart.

   A changed actor flags its use cases, and a changed use case flags the journeys through it. Friction is reported in that order. Revalidation is this capability's name for the act the core record calls by the same name; recording it on the artefact — its `at`, its outcome and any deferrals — is what clears friction (COR-050).

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

6. **Records only when there is something to say.** A revalidation that is planned, or that finds a gap or a regression, leaves a record in the revalidations folder. The record names the change that carried it (a tracked work item, a pull request, or a range of commits), the trigger, the artefacts covered with their outcomes, and the gaps with what resolved each. Records cite artefacts by id, including withdrawn ones, and are named by date and subject rather than numbered, so parallel work cannot collide. A routine revalidation that finds everything still holds writes no record: the artefact's own revalidation block, with its outcome and justification, is the record.

7. **Revalidation is not testing.** Revalidation asks whether *the description* is still true of the software, and usually fixes the description. Testing asks whether *the software* still does what the description says, and fixes the software. The capability owns revalidation. It does not run the software.

   The capability provides the **analysis role** and, under it, accepts a data point, `<methodology>::analysis:revalidation-evidence` (refinement per COR-053), for executed results that confirm or refute an artefact at a commit:
   - its schema is a companion schema the capability ships, named after the point (COR-052). At version 1 it has one entry per result, keyed by three parts — the artefact, the commit and the **check** — and holding the result and what was run. The check names one thing that was run against the artefact — a test, a scripted walk-through — and keeps that name from commit to commit; a filler gives each result it reports for one artefact at one commit a check of its own. A capability's checks open with the capability's own name, and a project file's with `project`. So two fillers' results for one artefact at one commit stand side by side, and only two that claim one check collide, which the project settles (COR-052 point 4). The opening name is a convention: where the capability's validation reads the point it warns on a capability's check that opens with another name, and never refuses, because the project replaces a capability's entry by writing one under that capability's check;
   - its policy is `union`;
   - no default takes part;
   - its inert policy is `fallback`, because the evidence advises and does not gate.

   The slots record (COR-052) allows three kinds of filler: a project file, a capability, and the provider's default. Here, a capability fills it (a later testing capability, or one that reads the test results the project already produces), or a project file records results, and no default takes part. Evidence **informs** a revalidation: a passing result is support for "holds", and a failing one is a regression with proof attached. It never replaces the revalidation. Only a revalidation or a deferral recorded on the artefact clears friction (COR-050). A revalidation record keeps a copy of each entry it drew on. A routine revalidation that writes no record (point 6) keeps none: its justification on the artefact says in its own words why the description holds, and naming a result is not a justification. Evidence kept on the artefact itself is not decided here (point 11).

8. **What it contributes to others.** The capability contributes to the documentation role's readers point, `<methodology>::documentation:readers`, by mapping its actors and their needs onto that point's shape (refinement per COR-053). It addresses the role, not a capability, so any provider of the documentation role receives it. The contribution is inert whenever no provider is installed, and the capability never requires one.

9. **Brownfield onboarding.** A project with no analysis starts with nothing anchored, so friction reads zero. The signal is uncovered surface: the paths the project declares its analysis should cover (point 2), against what the artefacts anchor to (COR-050). An agent derives candidate actors, use cases and terms from the code, the existing documents and the project's decisions. On a brownfield project these are the ground truth, so the usual order is reversed. A person confirms the candidates. Onboarding needs a non-empty declared surface, and it is complete when that surface is covered. Every artefact must be either anchored, or explicitly accepted as unanchored with a reason recorded on the artefact, such as an actor that no code embodies. The reason is the core friction block's `unanchored-because` (COR-050 point 1), so an accepted actor or term is listed apart and never counted as unanchored work left to do (point 8).

10. **Independent.** The capability works with no work-tracking component and no testing component installed. When a work-tracking component is present, it may cite revalidation records from its work items, as an enrichment.

11. **Scope boundary.** Lifecycles on the process substrate (a planned revalidation; onboarding), further analysis artefacts (constraints and quality requirements, architecture views), executable use cases and evidence kept on the artefact itself are outside this record. Each needs its own decision when a real need arrives.

## Rationale

**Why product knowledge, not per-design documents.** A use case is true of the product for as long as the product supports it. What belongs to one design is the *revalidation* of the use cases it touches. Keeping the two apart means the knowledge persists after the design ships, and each design's validation is recorded where it happened.

**Why a use-case model layout.** Grouping actors with the use cases they take part in, and keeping the glossary apart because it serves everything, follows an established requirements practice that analysts and newcomers already recognise. Global ids with optional grouping get the benefit of functional areas without the cost of renumbering.

**Why revalidation owns both planned and drift-triggered checks.** Checking before code and checking after an unplanned change are the same act with different triggers. One record shape, and one set of outcomes, serve both.

**Why records only with findings.** Most revalidations find that everything holds. Writing a file each time would bury the few that matter. Git already records the routine ones through the revalidation recorded on the artefact.

**Why keep testing out.** Revalidation judges a description by reading; testing judges software by running it. Merging them would make this capability depend on executing arbitrary software, and would blur whose fix a failure demands. The evidence slot lets executed results inform revalidation without that coupling.

**Why a person decides stale versus regressed.** The distinction is intent: was the change meant? An agent can propose it from the change's context, but when intent is unclear, only a person knows. Getting it wrong either rewrites the truth to match a bug, or reports a defect for an intended change.

### Alternatives considered

- **Use-case sets per design, validated once.** Rejected. The knowledge would be scattered across designs and would stop being maintained after each one shipped.
- **A flat analysis folder.** Rejected. Actors and terms get lost among many use cases, and there is no natural place for grouping or later modules.
- **A record for every revalidation.** Rejected. Routine records would bury the ones with findings.
- **Storing each artefact's current-or-stale state as truth.** Rejected. It would duplicate what anchors and git already answer; the core's tool-written status is a dated snapshot for visibility, never read for friction (COR-050).
- **Including executed testing in this capability.** Rejected. See Rationale; the evidence slot covers the useful part.
- **Requiring a documentation or work-tracking capability.** Rejected. The capability must be useful on its own.

## Implications

- **The capability ships** the templates and layout for its artefacts, the declaration of its places and connections, commands to stamp artefacts and check their shape (friction itself is the core check), and an authoring skill that guides revalidation.
- **Projects** keep their analysis under their internal documentation root and wire the core friction check into their continuous integration if they want it enforced.
- **Documentation disciplines** can read actors and their needs through the readers point, without any dependency.
