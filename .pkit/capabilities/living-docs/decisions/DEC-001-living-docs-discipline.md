---
id: DEC-001
title: Living documentation keeps each documentation space true for its readers
status: accepted
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A project that lets an agent write and maintain its documentation gets fluent text quickly. Without rules, it also gets fluent text that is wrong, repeated, aimed at nobody in particular, and quietly out of date after the next change. Documentation earns trust only if a reader can rely on it. That means it is true against something checkable. It says each fact once. It is written for a reader it actually serves. And it keeps the paths that reader takes unbroken.

Documentation serves two audiences who should not meet each other's material:
- **Users** need to know *what* the system does and *how* to use it.
- **Maintainers**, and the agents that write and check the documentation, need to know *why*, *from where*, and *by which rules*.

Mixing the two either buries users in internals or leaves maintainers without the grounds for what the user-facing pages say.

The core layer supplies the machinery:
- documentation roots by audience (COR-049);
- anchors and friction, which detect when what a page rests on has changed (COR-050);
- rule sets (COR-051);
- connection points, through which components exchange knowledge and signals without depending on each other: data slots (COR-052) as one kind, addressed by role (COR-053).

This record decides how this capability uses them.

## Decision

**Documentation is kept in spaces, each serving one audience. Every page is anchored to what makes it true and written for a declared reader. Drift is detected as friction and fixed by proposals a person reviews, never applied blind.**

1. **Spaces.** A *documentation space* is a body of documentation with its own audience, its own entry point, and its own definition.
   - Every project has at least a **user space** and a **technical space**, and may add others, such as an interface reference.
   - **Where new pages go.** New pages of the user space go under the user documentation root, and new pages of the technical space under the internal root (COR-049). A space the project adds declares its own location, under whichever root serves its audience.
   - **What belongs to a space.** A space's pages are found in the places declared for it (COR-050), which may include files outside its root, such as a repository's top-level README. The capability declares the roots as default places. The project declares any other places, and its surface, in the friction key of its backbone configuration, which the anchors-and-friction record owns (COR-050). The capability's own project configuration holds only what the backbone does not need: each space's audience, entry point and definition path. Trees that arrive as a synced copy are never places, so a sync never shows up as friction in the project's own history; the capability's validation keys on the manifest's origin (COR-031) *and* on whether the repository is the methodology's own source — the lifecycle's ownership predicate answers both — not on the path, so a repository in which those trees are authored source may declare them (origin alone would refuse them: the backbone's own areas carry no origin, and a kit-shipped capability's origin reads as a copy there).
   - **Which space a place belongs to.** A root is a default place of the space it serves, and a place the project declares inside a root — a *project place*, declared in the friction key of the backbone configuration (COR-050) — belongs to that root's space unless the project assigns it otherwise. A project place **outside every root** is assigned to exactly one space in this capability's project configuration, which is also where a project-added space records its location: a root, or project places with their assignment. Assignment lives here and not in the friction key because a capability adds no key to the backbone configuration (COR-048) and "space" is this capability's term; the join between the two files is a path, normalised and validated: an out-of-root project place that holds a document nothing else claims and has no assignment is a finding, and so is an assignment naming a place the friction key does not declare.
   - **What another component claims is never a page.** A place or a folder of held documents (COR-050 point 1) that another component declares in its package metadata belongs to that component — an analysis capability's artefacts or its review log, say — and so does any document another component's schema recognises. The space's page rules do not reach them, whatever root they sit under. The capability's own templates in a definition sub-path are its artefacts, not pages, on the same principle.
   - **Precedence between places.** Where places nest, the **most specific one wins**: an exact file beats a directory, a directory beats a glob; between directories the longer prefix wins, between globs the longer literal prefix before the first wildcard; a project place beats a root; between nested roots the nested one wins. A file claimed by two project places of equal specificity is a validation error, resolved by narrowing one declaration; a project place equal to or enclosing a root is refused when declared. A collection file is one file, so its entries never split across places.
   - **Separation.** This capability's rule is that the two spaces are **separate**: user-facing navigation and search never lead into technical material, and neither root lies inside the other. When a project adopts the capability with both roots still the same folder, as they are by default, that is reported as a finding for onboarding (point 8) to clear, not as a validation failure.

2. **Definitions, kept apart from content.** Each space has a *definition*: the rules its pages follow, and how its pages are made. Definitions are written down so that people and agents follow the same method.
   - Rules live in rule sets (COR-051). The capability ships a **shared method rule set**, and each space's definition inherits it and adds its own.
   - A space's definition, including the user space's, lives in the technical space, under a sub-path the capability declares and records on first use (COR-049). Templates and rules are the writers' tools, not reading material, so a space's readers never meet its definition.
   - The capability's method names nothing project-specific, so the same method serves every project that adopts it.

3. **What the shared rules require.** The shared rule set turns these properties into checkable rules:
   - a page's **anchors ground every statement** it makes: code, decisions and rules, captured sources, analysis artefacts. Inline citations are optional where a page mixes sources;
   - each fact is **stated once**, and other pages link to it;
   - each page **names its reader** and says only what that reader needs;
   - pages of a kind follow **one format**, with a template per kind;
   - an index-like file is a **signpost** to what a folder holds, never a summary of its contents;
   - nothing is created ahead of the need for it.

   The user space adds one more: the **reader paths stay unbroken**.

   The shared set is named `LDOC`, and its origins record this capability's own reasons. The rules about how rules themselves are named, grounded and inherited are not in it, because the rule-set record (COR-051) provides them. The rules about where artefacts come from are carried by anchors: each page names what it rests on, and the anchor graph is the index of why each page exists. A project that already has documentation rules of its own keeps them as a project rule set that inherits `LDOC`. It withdraws any that duplicate what the core provides.

   **A kind's structure.** A kind's template is the starting shape a writer fills in. The part of a kind's format that a tool checks is its *structure*: the sections every page of the kind carries, in order where order matters. A structure is declared once, with the kind, in data whose schema this capability ships, and is never read out of the template's text; it names only what every page of the kind must carry, so a template may show more, and each template satisfies its kind's structure. The capability declares the structure of each kind it ships. Validation checks a page's body against the structure its kind declares: while the rule that pages of a kind follow one format is accepted, a section a page lacks or carries out of order is a validation error, and under any other status the rule binds nothing and no body is checked (COR-051 point 4). A page whose kind declares no structure — a kind the project adds, say — is reported with its kind and never failed. A structure is the checkable part of that rule, beside it as a schema is (COR-051 point 1), and no part of the rule's content: changing a structure leaves the rule set's version alone, and a change that fails a page it passed before is a breaking change of the component that owns the kind.

4. **Pages are anchored and revalidated.** Every page is an artefact in the sense of the anchors-and-friction record (COR-050), in the places declared for its space. A page anchors to the code it describes, the decisions and rules it applies, the sources it quotes, and the analysis artefacts it builds on. Its front matter also names its **reader** and its **page kind**, in fields whose schema this capability ships. Sources need an anchor kind that some capability registers. Without one, a source anchor is reported as an unresolved kind, never silently accepted. Because core anchors and registered kinds cover every kind of ground a page rests on, the capability needs no separate slot for anchors. Not every document in a place is a page. A document is a page only if it carries the reader and page-kind fields; decision records and rule-set files are anchor targets, not pages (COR-050, COR-051), recognised by their own schemas; what another component claims is that component's (point 1). The residue — a document in a space's place that nothing claims and that carries neither field — is reported as an **unclassified document** for onboarding (point 8) to classify as a page of some space or as something the space's rules do not govern. Friction flags a page when any of those changed and the page was not revalidated. A page's reader and kind fields are the page's own; its friction block is the core's, in the methodology's container (COR-050, COR-053). Deciding what the change means for the page is judgment, which is what the capability's agent does next.

5. **Fixes are proposed, never applied blind.** The capability's agent resolves friction by *proposing* the change to the page, citing the change that caused it and the anchors it rests on. A person reviews the proposal through the project's approval path. The same holds for any rewrite the agent suggests. A statement the page's anchors do not ground is either grounded by a new anchor, taken out, or raised with a person as a question. It is never left standing as if it were true.

6. **Reader-review.** A *reader-review* reads a page as its declared reader, taken from the readers point (point 7). It asks whether the page answers that reader's questions, only those, and in a way they can follow. Findings cite the rule a page breaks. A reader-review leaves a record only when it finds something.

   Reader-review judges whether the documentation serves its reader. It is distinct from reviewing a change for missing or contradicted documentation, which belongs to code review: a change review looks at the diff, and reader-review looks at the page. Executed checks, in which a simulated reader follows the documentation and runs the system, are not performed here. Their results arrive through the reading-evidence point.

7. **Connections.** The capability provides the **documentation role** and, under it, accepts two data points (refinement per COR-053) — slots in the sense of COR-052, addressed by role so that another provider of the role is interchangeable:
   - **`<methodology>::documentation:readers`**: who reads the documentation and what they need.
     - **Schema:** a companion schema named after the point, at version 1. Each entry carries an id, the reader's needs and the paths they take.
     - **Policy:** `union`.
     - **Default:** always included, with one entry per mandatory space, a `user` and a `maintainer`. A fresh project therefore has readers on day one. A project file can add or override them, and a capability that keeps knowledge about the software's users may fill it too.
     - **Inert policy:** `fail`, because validation checks that each page's declared reader resolves. The consequence is intended: if a capability filler falls out of version step, the whole point is unresolved and page reader checks fail until it catches up.
     - Reader ids are distinct from the ids an analysis capability gives its actors, so a capability's readers are added alongside the defaults. The project file can override or suppress the defaults by their ids.
   - **`<methodology>::documentation:reading-evidence`**: results of executed checks that follow the documentation. Its companion schema, at version 1, has one entry per result, keyed by three parts: the page or path, the commit and the **check**. The check names one executed check and keeps that name from commit to commit; a filler gives each result it reports for one page or path at one commit a check of its own. By convention a capability's checks open with the capability's own name and a project file's with `project`. Nothing in this capability reads the entries: the schema's patterns hold the shape of the id and the check, and nothing warns on the opening name. Two fillers' results for one page or path at one commit stand side by side, and only two that claim one check collide (COR-052 point 4). Policy `union`, no default takes part, inert policy `fallback`, because the evidence advises.

   The capability contributes to the work-tracking role's documentation-check point, `<methodology>::work-tracking:doc-check`, with friction on anchored pages and uncovered surface — new code that nothing describes (refinement per COR-053). The contribution is inert when no provider of that role is installed, and never required. It answers only for what the friction check could judge. When the check could not do its work on a page — an anchor's resolver gave no answer, or the page's friction lies beyond the history at hand — the contribution gives no answer, and the documentation check reports itself unresolved rather than pass on fewer obligations ([project-management:DEC-053-doc-check-slot] point 1). A page the check left unjudged only because nothing installed resolves one of its anchors' kinds owes what its other anchors owe: such an anchor is a declaration for the project to mend, which the change check fails where a change is why and otherwise reports (COR-050 point 12), never a failure of every later change.

8. **Brownfield onboarding is transformation.** On a project that adopts the capability with existing documentation, nothing is anchored yet. Onboarding is friction work on that starting point. The capability's agent proposes:
   - which space each existing page belongs to;
   - how pages should be split, merged or rewritten for their readers;
   - which anchors each statement should carry;
   - which existing mappings from code to documentation, if the project keeps any, become page anchors. Retiring such mappings is a separate change for whoever owns them.

   Every proposal cites its evidence and passes a person's review, and moves land as ordinary reviewable changes. Onboarding is complete when the declared surface is covered and no page is left unanchored without an accepted reason. An accepted reason is the core's `unanchored-because` in the page's friction block, written on a person's decision (COR-050 point 1); the unanchored measure lists such a page apart and does not count it (point 8).

9. **Independent.** The capability works without any analysis, work-tracking or testing component, and each of them can enrich it through its connection points.

## Rationale

**Why spaces by audience.** A user who meets maintainers' material in navigation is lost. A maintainer who cannot find the grounds for a user page cannot keep it true. Separating by audience, and keeping each space's method in the technical space, gives both readers what they need. It also gives the writing agent a checkable boundary in place of a judgment call.

**Why the method is kept apart from content.** A method written once, and inherited, can be reused across projects and changed in one place. A method mixed into content cannot be separated again.

**Why every statement must be grounded by the page's anchors.** A statement nothing grounds cannot be judged true or false, and that is what makes fluent, unfounded text look reliable. Anchoring the page, not each sentence, keeps the cost bearable. The agent's and the reviewer's judgment connects each statement to the anchors. Anchors turn "is this still true?" into a question a tool can raise and a reviewer can answer.

**Why propose and never apply.** An agent that rewrites pages directly will eventually rewrite them wrongly: it will misjudge an ambiguous file's audience, or "fix" a page to match a regression. Proposals that cite their evidence, reviewed by a person, keep speed without giving up judgment.

**Why reader-review is separate from change review.** Change review asks whether a change left documentation missing or contradicted. Reader-review asks whether the documentation serves its reader at all. They catch different failures, and merging them would blur both.

### Alternatives considered

- **One documentation tree, with an internal section.** Rejected. Readers meet internal material in navigation and search, and the writing agent loses a checkable boundary.
- **An audience attribute on each friction-key entry.** Rejected: it would put this capability's term into a key the core owns, which a capability may not extend (COR-048).
- **Declaring the capability's places from its own configuration rather than the friction key.** Rejected: component places are static package metadata and project places are the friction key's, by the anchors-and-friction record (COR-050); a third channel would split discovery.
- **Every place assigned explicitly, including in-root ones.** Rejected: a place inside a root already says which audience it serves; asking twice invites drift, and the finding it enables is covered by the out-of-root case.
- **Each space written without a shared method.** Rejected. Rules would be re-derived per space and per project, and would drift.
- **Agents applying fixes directly.** Rejected. See Rationale.
- **A documentation registry maintained by hand.** Rejected. A registry needs maintaining as much as the pages do. Anchors and friction give the same currency signal from the pages themselves.
- **Running the product inside this capability to test the docs.** Rejected. That is testing; its results arrive as reading evidence instead.

## Implications

- **The capability ships** its shared method rule set, a template and a declared structure per page kind, the declaration of its places, surface and connections, an agent that proposes friction fixes and performs reader-review, and an onboarding guide.
- **Projects** declare their spaces' locations through the documentation roots — and any further places through the friction key, assigning out-of-root ones to a space in the capability's configuration — keep each space's definition in the technical space, and wire the core friction check into their continuous integration if they want it enforced.
- **Analysis components** can supply readers through the readers point. The capability keeps no glossary of its own; if it needs one, it takes it through a point from whatever component keeps one. **Work-tracking components** receive the capability's contribution to their documentation checks through their own point.

