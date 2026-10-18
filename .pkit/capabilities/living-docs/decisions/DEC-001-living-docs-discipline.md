---
id: DEC-001
title: Living documentation keeps each documentation space true for its readers
status: accepted
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A project that lets an agent write and maintain its documentation gets fluent text quickly. Without rules, it also gets fluent text that is wrong, repeated, aimed at nobody in particular, and quietly out of date after the next change. Documentation earns trust only if a reader can rely on it. That means it is true against something checkable. It gives each fact one home. It is written for a reader it actually serves. And it keeps the paths that reader takes unbroken.

Documentation serves two audiences who should not meet each other's material:
- **Users** need to know *what* the system does and *how* to use it.
- **Maintainers**, and the agents that write and check the documentation, need to know *why*, *from where*, and *by which rules*.

Mixing the two either buries users in internals or leaves maintainers without the grounds for what the user-facing pages say.

The core layer supplies the machinery:
- documentation roots by audience (COR-049);
- anchors and friction, which detect when what a page rests on has changed (COR-050);
- rule sets (COR-051);
- the rule-set reviewer, a core agent that judges a change against the rules that bind on it (COR-057);
- versioned dependencies between capabilities, required or optional (COR-030);
- artefact types, which name what an artefact is, so a rule set can select it (COR-056);
- connection points, through which components exchange knowledge and signals without depending on each other: data slots (COR-052) as one kind, addressed by role (COR-053).

This record decides how this capability uses them.

## Decision

**Documentation is kept in spaces, each serving one audience. Every page is anchored to what makes it true and written for a declared reader. Drift is detected as friction and fixed by proposals a person reviews, never applied blind.**

### 1. Spaces

A *documentation space* is a body of documentation with its own audience, its own entry point, and its own definition.
- Every project has at least a **user space** and a **technical space**, and may add others, such as an interface reference.
- **Where new pages go.** New pages of the user space go under the user documentation root, and new pages of the technical space under the internal root (COR-049). A space the project adds declares its own location, under whichever root serves its audience.
- **What belongs to a space.** A space's pages are found in the places declared for it (COR-050), which may include files outside its root, such as a repository's top-level README. The capability declares the roots as default places, each giving the page type (point 4). The project declares any other places, and its surface, in the friction key of its backbone configuration, which the anchors-and-friction record owns (COR-050). The capability's own project configuration holds only what the backbone does not need: each space's audience, entry point and definition path. Trees that arrive as a synced copy are never places, so a sync never shows up as friction in the project's own history. The backbone's friction validation refuses a synced tree declared as a place, whoever declares it (COR-050 point 14). It keys on the manifest's origin (COR-031) *and* on whether the repository is the methodology's own source — the lifecycle's ownership predicate answers both — not on the path, so a repository in which those trees are authored source may declare them (origin alone would refuse them: the backbone's own areas carry no origin, and a kit-shipped capability's origin reads as a copy there).
- **Which space a place belongs to.** A root is a default place of the space it serves, and a place the project declares inside a root — a *project place*, declared in the friction key of the backbone configuration (COR-050) — belongs to that root's space unless the project assigns it otherwise. A project place **outside every root** takes its space from its assignment in this capability's project configuration, to exactly one space. That configuration is also where a project-added space records its location: a root, or project places with their assignment. Assignment lives here and not in the friction key because a capability adds no key to the backbone configuration (COR-048) and "space" is this capability's term; the join between the two files is a path, normalised and validated. An out-of-root project place that holds a document nothing else claims and has no assignment is a finding, unless it is an untyped place of rule sets (below). So is an assignment naming a place the friction key does not declare.
- **An untyped place of rule sets outside every root owes no assignment, and is passed over until it has one.** A *place of rule sets* is a project place the backbone reads as declared to hold rule sets (COR-051 point 2). Its rule-set files are never pages (point 4). Its only other documents are its *signposts*: what the backbone reads there as describing the folder, not as a rule set. A configuration command may declare such a place when a change of root would leave rule sets behind (COR-051 point 6).
  - Outside every root, a place of rule sets that gives no type gives no space until the project assigns it one. It owes no assignment. Where places nest, it is passed over (precedence, below).
  - A document that lies in it and in no place of a space, such as its signpost, is then neither a page nor an unclassified document. One that declares a page kind is reported, never failed. The report names the assignment that would make it a page.
  - A type on a place names what its documents are (COR-056 points 1 and 2), whoever writes it. So a place of rule sets that gives a type is held to an assignment as any other project place is.
- **The assignment agrees with the definitions' scopes.** Where a space's definition carries a scope, which selects artefacts by path and by type (COR-051 point 2), the scope and the assignment both say where the space's pages lie. Validation holds them to each other:
  - A place assigned to a space lies in that space definition's scope, and in no other space definition's scope. Validation checks this on each page the place gives a space to, reading the scopes that cover the page from the backbone's answer. A page outside its own definition's scope, or inside another's, fails.
  - Where a space's definition selects by type, an assigned place outside every root must give the page type (point 4). Otherwise the scope misses the place's pages. Validation fails the place itself, which names the fix and holds before the place has pages.

  A definition with no scope selects no artefact itself (COR-051 point 2), so nothing is held to it. The places assigned to its space are checked only against the scopes of the other spaces' definitions. A space with no definition yet is checked the same way.
- **What another owner claims is never a page.** Each document in a space's places takes the type the backbone gives it (COR-056), and the type says whose the document is. What another owner claims:
  - A document of another component's type, such as an analysis capability's artefact, is that component's. So is a document another component holds in a folder it declares (COR-050 point 1). So is a document of no type in a place another component declares, which keeps its files whether it types them or not (COR-056 point 3).
  - A document of a type of the project's own is the project's.
  - The capability's own templates, in its definitions location, are of its template type (point 2).

  The space's page rules reach none of them, whatever root they sit under. The capability never reads a `reader` or a `kind` of theirs. A place another component declares without a type shadows no other place (COR-056 point 3). So a document there that declares a page kind takes the page type from the root around it, and is a page. The backbone reports that the root typed another component's file, and the component keeps such documents by typing its place.
- **Precedence between places.** Where places nest, the backbone's order of places decides (COR-056 point 3), and the capability ranks none itself. It reads each document's matching places in that order from the backbone's one answer (COR-056 point 6). The first of them that is a root or a project place gives the document its space. In short:
  - A place that equals or encloses a root comes after every place that does not, so a project place beats a root.
  - Otherwise the longer literal part wins: the path up to its first wildcard. So between nested roots the nested one wins.
  - At equal length, an exact file beats a glob, and a glob beats a folder.
  - A project place that yields to a component's own place (COR-056 point 3) comes after every other.

  Two roots that are one folder give no space until onboarding separates them (Separation, below). A project place equal to or enclosing a root is refused when declared, and gives no space. An untyped place of rule sets outside every root with no assignment is passed over (above). The next of a document's places in the backbone's order then gives its space, if one does. A file that two project places claim at equal rank, ahead of every other, is a validation error, resolved by narrowing one declaration. A collection file is one file, so its entries never split across places.
- **Separation.** This capability's rule is that the two spaces are **separate**: user-facing navigation and search never lead into technical material, and neither root lies inside the other. When a project adopts the capability with both roots still the same folder, as they are by default, that is reported as a finding for onboarding (point 8) to clear, not as a validation failure.

### 2. Definitions, kept apart from content

Each space has a *definition*: the rules its pages follow, and how its pages are made. Definitions are written down so that people and agents follow the same method.
- Rules live in rule sets (COR-051). The capability ships a **shared method rule set**, and each space's definition inherits it and adds its own.
- **A definition is scoped to its space's pages.** A space's definition is a project rule set whose scope selects the space's pages (COR-051 point 2). The shared set takes no scope, so sets of the project's own, the definitions among them, say where its rules bind (point 3). Each definition's pin on the shared set decides when a new major of that set starts binding through it.
- **Writing a space's definition gives it its scope.** Whoever writes a space's definition writes its scope with it, and the capability's template for a definition carries one. So the shared rules bind on the space's pages as soon as the definition exists. Validation reports a definition with no scope, which selects no page itself (COR-051 point 2), and names the scope to give it.
- **The capability's authoring command writes a space's definition when the project creates the space.** The project creates the user and technical spaces as it adopts the capability, and any other space when it adds one. The command makes three writes:
  - the definition, with the scope that selects the space's pages;
  - the definition's path, in the space's entry of the capability's project configuration, which it adds for a space the project adds;
  - the definitions location, recorded on first use (COR-049 point 5).

  The record names the command as the writer of these (COR-001), and running the command is the consent for them. It reports each page of the space that then fails validation. It writes no definition that exists, and nothing of the backbone configuration or of another space's definition. A project may still write a definition by hand.
- A space's definition, including the user space's, lives in the technical space, under a sub-path the capability declares and records on first use (COR-049). Templates and rules are the writers' tools, not reading material, so a space's readers never meet its definition.
- That sub-path is a place the capability declares, which gives its documents the capability's *template* type, `living-docs:template` (COR-056). The type registry declares it beside the page type, and admits no project place for it. The place ranks ahead of the root around it (point 1). So a page template copied there is a template, never a page, though it carries a page's fields. A rule there is a rule, of the backbone's type for rules (COR-056 point 3).
- The capability's method names nothing project-specific, so the same method serves every project that adopts it.

### 3. What the shared rules require

The shared rule set turns these properties into checkable rules:
- a page's **anchors ground every statement** it makes: code, decisions and rules, captured sources, analysis artefacts, and the home of each fact it summarises. Inline citations are optional where a page mixes sources;
- each fact has **one home**: the decision record that decides it, for a page that anchors what decides it, and otherwise one page. A page states a fact whose home is another page only as a summary that links to the home and anchors to the home's section;
- each page **names its reader** and says only what that reader needs;
- pages of a kind follow **one format**, with a template per kind;
- an index-like file is a **signpost** to what a folder holds, never a summary of its contents;
- nothing is created ahead of the need for it.

The user space adds one more: the **reader paths stay unbroken**.

The shared set is named `LDOC`, and its origins record this capability's own reasons. The rules about how rules themselves are named, grounded and inherited are not in it, because the rule-set record (COR-051) provides them. The rules about where artefacts come from are carried by anchors: each page names what it rests on, and the anchor graph is the index of why each page exists. A project that already has documentation rules of its own keeps them as a project rule set that inherits `LDOC`. It withdraws any that duplicate what the core provides.

**What grounds a statement.** Only what a page anchors grounds a statement. A change to anything else flags no page (COR-050 point 5).
- **A record the page mentions or cites** but does not anchor grounds nothing. An inline citation tells the reader where a sentence's ground lies, and grounds the sentence only where the page anchors what it cites.
- **Code reached only through a call** from a file the page anchors grounds nothing either.
- **An anchor on one part** of a record or a document grounds only what that part stands on (COR-050 point 5).

So a statement that rests on anything else breaks the rule on grounding until the page anchors what it rests on.

**A fact's home.** Each fact a page states has one home for that page. A change to a fact is made at the record that decides it, or else at its home among the pages.
- **A fact a decision record decides** has the record as its home for a page that anchors the record. The anchor may be on the whole record, or on a part that stands on what decides the fact (COR-050 point 5). The page may state the fact. It needs no link to another page that states it, and no anchor on one.
- **Every other fact a page states** has its home among the pages: the one page that states it in full, or for a decided fact, a page that states it in full. A fact that only one page states has that page as its home.
- **A summary of a fact whose home is a page,** on another page, is allowed, so that each page stays useful on its own. It links to the home. Its page anchors to the home's section that states the fact (COR-050 point 2). A change to that section then flags the summary, and the change check asks it for an answer. An anchor on the whole home is not that anchor, since it would flag the summary on every edit of the home.
- **A statement of such a fact on another page** that lacks the link or the anchor breaks the rule on a fact's home, however short it is. Words that give the fact state it, a phrase as much as a clause. Whether one with both summarises the home, or states the fact in full again, is a passage for a person to judge.
- **A name,** such as a command's, a page's or a record's, needs no link to a home and no anchor on one. That holds where the name gives none of the named thing's facts.
- **A fact stated more than once on one page,** each time in agreement, is a passage for a person to judge, not a settled break (COR-057 point 3). The rule leaves to that person whether the repeat serves the page's reader, as an opening summary or a recap may.
- **Two statements of one fact that disagree** break the rule on a fact's home on each page that holds one of them, on one page or on two. Two statements disagree where one says what the other rules out. A statement that leaves out detail the other gives does not disagree with it.

Two consequences follow from other rules. Anchors between artefacts form no cycle (COR-050 point 5), so two pages never summarise each other, directly or through other pages. And user-facing navigation never leads into technical material (point 1), so a page of the user space never has a fact's home on a page of the technical space.

**Where `LDOC` binds.** `LDOC`'s rules bind on a page only through a set of the project's own whose scope selects it, such as a space's definition (point 2). They do not bind through a pin that is behind its set (COR-051 point 7). A check enforces its part of an `LDOC` rule (point 6) only where the rule binds, as the backbone's one answer gives it. So validation checks a page's structure (RS-LDOC-004) and its reader (RS-LDOC-003) each only where its rule binds.

**A kind's structure.** A kind's template is the starting shape a writer fills in. The part of a kind's format that a tool checks is its *structure*: the sections every page of the kind carries, in order where order matters. A structure is declared once, with the kind, in data whose schema this capability ships, and is never read out of the template's text; it names only what every page of the kind must carry, so a template may show more, and each template satisfies its kind's structure. The capability declares the structure of each kind it ships. Where the one-format rule binds on a page (above), a section the page lacks or carries out of order is a validation error. A page whose kind declares no structure — a kind the project adds, say — is reported with its kind and never failed. A structure is the checkable part of that rule, beside it as a schema is (COR-051 point 1), and no part of the rule's content: changing a structure leaves the rule set's version alone, and a change that fails a page it passed before is a breaking change of the component that owns the kind.

### 4. Pages are anchored and revalidated

Every page is an artefact in the sense of the anchors-and-friction record (COR-050), in the places declared for its space. A page anchors to the code it describes, the decisions and rules it applies, the sources it quotes, the analysis artefacts it builds on, and the home of each fact it summarises (point 3). Its front matter has a field for its **page kind** and one for its **reader**, in a schema this capability ships. A source is anchored through the `source` kind this capability registers (below). Because core anchors and registered kinds cover every kind of ground a page rests on, the capability needs no separate slot for anchors. Friction flags a page when any of those changed and the page was not revalidated. A page's reader and kind fields are the page's own; its friction block is the core's, in the methodology's container (COR-050, COR-053). Deciding what the change means for the page is judgment, which is what the capability's agent does next.

**What a page is.** Not every document in a place is a page. A document is a page when it is of the capability's *page* type, `living-docs:page` (COR-056). It is also a page when it declares its page kind in a project place that lies outside every root and gives no type. An unassigned place of rule sets is not such a place (point 1).
- **The type.** The capability's type registry declares `page`, with `kind` as its kind field, and admits project places (COR-056 point 2). Each root gives the type, and a project may give it on its own places.
- **The page kind decides.** A document takes the type where the place that wins for it gives the type and the document declares its page kind in `kind` (COR-056 point 4). A document that counts as the page type in a tie is a page until the tie is mended, whatever other type it counts as. A document that declares no page kind takes no type and is no page, even where it names a reader.
- **A project place that gives no type.** The core promises that an untyped place keeps its meaning (COR-056, Implications), and this capability keeps that promise for its pages. A project place that lies outside every root and names no type holds pages. A document of no type there is a page when it declares its page kind in `kind` and no other owner claims it (point 1). It has no type, so a scope that selects by type misses it. Point 1 guards the spaces' definitions against that. A document that lies only in an untyped place of rule sets outside every root, with no assignment, is no page. That place is declared to hold rule sets (point 1 and COR-051 point 2).
- **Never a page.** Decision records and rule-set files are anchor targets (COR-050, COR-051). Every rule in a rule-set file takes the backbone's type for rules. The capability reads a document's own `id` only to tell a decision record. A decision record that would otherwise be a page fails validation: one of the page type, or one of no type that declares its page kind in a project place giving none. What another owner claims is that owner's (point 1).
- **Unclassified documents.** Any other document in a space's places is an **unclassified document**. It is no page, no decision record and no rule-set file, and no other owner claims it. So is one that names a reader but declares no page kind. It is reported for onboarding (point 8) to classify as a page of some space or as something the space's rules do not govern.

**Sources.** A page anchors a source outside the repository — a standard, a specification, another project's documentation — through the `source` anchor kind this capability registers, naming the source by a word (`source: [keep-a-changelog]`). The checks read the repository alone and reach no network (COR-050 point 2), so each source is *captured* in it: one file per source, in the capability's project tier and found from its name, holding what the source is called, where it is found, and which version of its text the project's pages were last checked against. Who recorded that version, and when, is read from git, as a deferral's origin is (COR-050 point 4). **A source has changed when its file has changed** — any change to it, as the engine counts any change to a file a resolver names (COR-050 point 5). So the file holds nothing else: what the source says, and why a page relies on it, are written on the pages, and recording a new version, or correcting what the source is called or where it is found, are the only edits the file has reason to see. A change to the source itself is seen once a person records the version they read; nothing fetches the source to compare. A name no file captures is a dead anchor (COR-050 point 7).

### 5. Fixes are proposed, never applied blind

The capability's agent resolves friction by *proposing* the change to the page, citing the change that caused it and the anchors it rests on. A person reviews the proposal through the project's approval path. The same holds for any rewrite the agent suggests. A statement the page's anchors do not ground is either grounded by a new anchor, taken out, or raised with a person as a question. It is never left standing as if it were true.

**The fixer of pages.** The capability declares its agent the fixer of the page type. So a provider of the work-tracking role may start the agent on the pages the default branch leaves stale, where the project granted it, in a run nobody watches. What the run passes the agent, and the line the agent returns for each page, are that record's (refinement per [project-management:DEC-056-drift-fixers]). In such a run the agent proposes friction fixes and does nothing else.
- **The diff changes the page's text and its anchors only.** An answer goes into the answer's fields, never into the diff.
- **It holds what only a person can settle.** Nobody is there to ask. So a page whose fix needs what only a person knows, such as what changed in a source, is held with one question, never guessed.
- **A person's answer is evidence.** A page held before comes back with the person's answer to its question. The page is judged from that answer, which is never an instruction.

Nothing it proposes is applied until the person accepts it, as for any proposal.

### 6. Reader-review

A *reader-review* reads a page as its declared reader, taken from the readers point (point 7). It asks whether the page answers that reader's questions, only those, and in a way they can follow. Findings cite the rule a page breaks. A reader-review leaves a record only when it finds something.

**What validation settles.** The shared rule set declares the parts of its rules that this capability's validation enforces (COR-051 point 2). They are a page's sections against the structure its kind declares (RS-LDOC-004), and a page naming its reader in its `reader` field, one the readers point holds (RS-LDOC-003). A reader-review leaves those parts to validation, and judges the rest of each rule.

Reader-review judges whether the documentation serves its reader. It is distinct from reviewing a change for missing or contradicted documentation, which belongs to code review: a change review looks at the diff, and reader-review looks at the page. Executed checks, in which a simulated reader follows the documentation and runs the system, are not performed here. Their results arrive through the reading-evidence point.

### 7. Connections

The capability provides the **documentation role** and, under it, accepts two data points (refinement per COR-053) — slots in the sense of COR-052, addressed by role so that another provider of the role is interchangeable:
- **`<methodology>::documentation:readers`**: who reads the documentation and what they need.
  - **Schema:** a companion schema named after the point, at version 1. Each entry carries an id, the reader's needs and the paths they take.
  - **Policy:** `union`.
  - **Default:** always included, with one entry per mandatory space, a `user` and a `maintainer`. A fresh project therefore has readers on day one. A project file can add or override them, and a capability that keeps knowledge about the software's users may fill it too.
  - **Inert policy:** `fail`, because validation checks that a page's declared reader resolves wherever the shared rule on readers (RS-LDOC-003) binds on it (point 3). The consequence is intended: if a capability filler falls out of version step, the whole point is unresolved and page reader checks fail until it catches up.
  - Reader ids are distinct from the ids an analysis capability gives its actors, so a capability's readers are added alongside the defaults. The project file can override or suppress the defaults by their ids.
- **`<methodology>::documentation:reading-evidence`**: results of executed checks that follow the documentation. Its companion schema, at version 1, has one entry per result, keyed by three parts: the page or path, the commit and the **check**. The check names one executed check and keeps that name from commit to commit; a filler gives each result it reports for one page or path at one commit a check of its own. By convention a capability's checks open with the capability's own name and a project file's with `project`. Nothing in this capability reads the entries: the schema's patterns hold the shape of the id and the check, and nothing warns on the opening name. Two fillers' results for one page or path at one commit stand side by side, and only two that claim one check collide (COR-052 point 4). Policy `union`, no default takes part, inert policy `fallback`, because the evidence advises.

The capability contributes to the work-tracking role's documentation-check point, `<methodology>::work-tracking:doc-check`, with friction on anchored pages and uncovered surface — new code that nothing describes (refinement per COR-053). The contribution is inert when no provider of that role is installed, and never required. It answers only for what the friction check could judge. When the check could not do its work on a page — an anchor's resolver gave no answer, or the page's friction lies beyond the history at hand — the contribution gives no answer, and the documentation check reports itself unresolved rather than pass on fewer obligations ([project-management:DEC-053-doc-check-slot] point 1). A page the check left unjudged only because nothing installed resolves one of its anchors' kinds owes what its other anchors owe: such an anchor is a declaration for the project to mend, which the change check fails where a change is why and otherwise reports (COR-050 point 12), never a failure of every later change.

The capability also contributes to the work-tracking role's fixers point, `<methodology>::work-tracking:fixers`, naming its agent as the fixer of the page type (point 5). The contribution is a static value, so it reads in the capability's package metadata and resolving it runs nothing. It is inert when no provider of that role is installed, and it starts no agent until the project grants the fixer (refinement per [project-management:DEC-056-drift-fixers]).

### 8. Brownfield onboarding is transformation

On a project that adopts the capability with existing documentation, nothing is anchored yet. Onboarding is friction work on that starting point. The capability's agent proposes:
- which space each existing page belongs to;
- how pages should be split, merged or rewritten for their readers;
- which anchors each statement should carry;
- which existing mappings from code to documentation, if the project keeps any, become page anchors. Retiring such mappings is a separate change for whoever owns them.

Every proposal cites its evidence and passes a person's review, and moves land as ordinary reviewable changes. Onboarding is complete when the declared surface is covered and no page is left unanchored without an accepted reason. An accepted reason is the core's `unanchored-because` in the page's friction block, written on a person's decision (COR-050 point 1); the unanchored measure lists such a page apart and does not count it (point 8).

### 9. Independent

The capability works without any analysis, work-tracking or testing component, and each of them can enrich it through its connection points.

**Its review contribution.** The project-management capability is one such work-tracking component. Where it is installed, this capability contributes the core rule-set reviewer to its merge gate. It does so under the gate's floor on ruled artefacts ([project-management:DEC-032-conditional-reviewer-requirements] D1).
- **What it covers:** every artefact a change alters on which an accepted rule binds, a page or not. It also covers every artefact the change brings under such a rule (COR-057 point 6).
- **Its evidence:** the reviewer was run by hand on eleven changes, and the maintainer judged one of its sixteen settled breaks wrong. That meets the bar of at most one, which COR-057 point 8 leaves to the contributor ([project-kit#1599](https://github.com/aleskalfas/project-kit/issues/1599)).
- **Apart from its contributions to roles (point 7):** the contribution is addressed to project-management's gate, not to a role.
- **The dependency:** the capability declares project-management as an optional dependency, since it works without it (COR-030). In each release of the capability, the range admits no release of project-management without the gate's floor on ruled artefacts. A change cannot name a version before that version is released. So the change that adds the contribution declares that it needs the project-management release with that floor. The range's start is raised to that release when it is made ([project-kit#1640](https://github.com/aleskalfas/project-kit/issues/1640)). Without project-management, nothing reads the contribution.

## Rationale

**Why spaces by audience.** A user who meets maintainers' material in navigation is lost. A maintainer who cannot find the grounds for a user page cannot keep it true. Separating by audience, and keeping each space's method in the technical space, gives both readers what they need. It also gives the writing agent a checkable boundary in place of a judgment call.

**Why the method is kept apart from content.** A method written once, and inherited, can be reused across projects and changed in one place. A method mixed into content cannot be separated again.

**Why the shared rules bind through the spaces' definitions.** A method rule set takes no scope, so the project's own sets say where a shipped rule binds (COR-051 point 7). A space's definition already names the rules its pages follow, so its scope says where they bind. Its pin says when a new major of `LDOC` starts binding there. Its scope also keeps a space's own rules off another space's pages.

The cost falls on a page that no scoped set of the project's own reaches. No rule of `LDOC` binds on it, so validation enforces no part of one there (point 6). Validation reports a space with no definition yet, and a definition with no scope, so the gap is not silent.

**Why running the command is the consent for a definition.** The command writes only what creating the space needs: the definition, its path in the space's entry, and the location the definitions lie in. A definition makes the space's rules bind on the space's pages, including those already there. That is its purpose (point 2), and it is what the project chooses by creating the space. The command reports each page that then fails validation, so the choice is never made blind.

**Why the backbone's types and order decide.** A rule set that selects pages by type reaches what the backbone types (COR-056). A page the capability told apart by claims of its own could be a page to its checks and not to a scope, or the reverse. So types decide, and the capability takes the backbone's order of places, not one of its own. A document's type and its space then come from places ranked one way. The cost is that a change to the backbone's order of places moves pages between spaces as well as types.

**Why a project place that gives no type holds pages.** A project's pages outside its roots stay pages until it types their places. The core puts typing places before relying on types on the project (COR-056, Implications). So the capability does not take pages away from a project that has not typed its places yet, save in an unassigned place of rule sets (below). The spaces' definitions are the rule sets it knows, so it guards them: once a definition selects by type, an assigned place that gives no type fails. That scope then never misses the space's pages without a word.

**Why an untyped place of rule sets outside every root owes no assignment.** A configuration command of the backbone declares such a place under one consent, so that a change of root leaves no rule set unfound (COR-051 point 6). It cannot write the assignment, which is this capability's, in this capability's configuration (point 1). Asking one would make that consented write fail this capability's validation on the next run. The steps the finding would then ask serve the finding alone:
- The assignment would put a place of rule sets into a space, for the sake of its signpost.
- Where the space's definition selects by type, the place would then have to give the page type.
- When the project moves the sets and removes the place, the assignment would name a place no longer declared.

A type names what a place's documents are, so a typed place of rule sets is held to an assignment as any other place is. A signpost under a root stays in that root's space, so a signpost page there is kept.

The cost falls on a signpost page in the default folder of project rule sets (COR-051 point 6). A change of the internal root can take it out of every space, and it is then no page, whatever kind it declares. It is reported with the assignment that would make it a page, so that is never silent.

**Why every statement must be grounded by the page's anchors.** A statement nothing grounds cannot be judged true or false, and that is what makes fluent, unfounded text look reliable. Anchoring the page, not each sentence, keeps the cost bearable. The agent's and the reviewer's judgment connects each statement to the anchors. Anchors turn "is this still true?" into a question a tool can raise and a reviewer can answer.

**Why only what a page anchors grounds it.** A change flags a page only through the page's anchors. A record the page only mentions or cites can change, and so can code an anchored file calls, and no tool asks whether the page still holds. A statement resting on either would look grounded and could turn false unseen.

**Why each fact has one home, and a summary anchors to it.** A reader needs a fact on the page where they look, so another page may summarise it. The anchor keeps the statements together: a change to the home's section flags each summary of it, so the change check asks each one for an answer. An anchor on the home's section, not the whole home, asks only when that part changes. A statement on another page with no anchor drifts unseen. Within one page, both statements sit in one file, where whoever edits one has the other in front of them, and an opening summary or a recap may serve the reader. So whether a repeat earns its place is a person's call. Two statements that disagree never serve the reader, since one of them is false.

**Why a decision record a page anchors is the home of the facts it decides.** A change to what decides the fact flags every page that anchors it, and each page's statement is held to what it anchors. So a decided fact stays true on each such page with no link between pages. The page anchors the record to ground the statement anyway, so the record as home adds no flag. A page that does not anchor the record needs a home among the pages, since nothing else flags that page when the fact changes.

**Why a name needs nothing and a short statement needs both.** A name that gives none of a thing's facts turns false only when the thing is renamed or removed. An anchor on every name would flag a page on each edit of everything it names. A phrase that gives a fact drifts with the fact as a sentence does, and only the anchor on the home's section flags it.

**Why propose and never apply.** An agent that rewrites pages directly will eventually rewrite them wrongly: it will misjudge an ambiguous file's audience, or "fix" a page to match a regression. Proposals that cite their evidence, reviewed by a person, keep speed without giving up judgment.

**Why a run nobody watches holds rather than guesses.** In a session the agent asks the person what only they know. A run a command starts has nobody to ask. A guess there would be fluent text that nothing grounds, which is what point 5 exists to prevent. Holding the page with one question costs one run, and the person's answer comes with the page's next run.

**Why reader-review is separate from change review.** Change review asks whether a change left documentation missing or contradicted. Reader-review asks whether the documentation serves its reader at all. They catch different failures, and merging them would blur both.

**Why a source is captured as the version read.** A check that gives the same answer wherever it runs cannot ask a source whether it changed (COR-050 point 2). It can read the project's own record of the source, and that record changes exactly when someone reads a new version — which is when the pages resting on it should be read again. A fingerprint kept in each page would conflict on every parallel change and tell a reader nothing (COR-050, Rationale). The engine counts any change to the record's file (COR-050 point 5), so the file is kept to what should count: one source per file, so a new version of one asks only its own pages; and nothing in it but what identifies the source and the version read, so no edit has reason to happen there except one the pages should answer. The price is coarseness: a new version asks every page resting on any part of the source, and an edit that changes nothing a page relies on — a reformat, a comment added later — asks them too. The file is data the check reads, not documentation, so it lives in the capability's project tier, beside its configuration, where it is neither a page nor an artefact; uninstalling the capability removes the tier, captured sources with it, as it leaves their anchors with no resolver.

### Alternatives considered

- **One documentation tree, with an internal section.** Rejected. Readers meet internal material in navigation and search, and the writing agent loses a checkable boundary.
- **An audience attribute on each friction-key entry.** Rejected: it would put this capability's term into a key the core owns, which a capability may not extend (COR-048). A type on a place differs: a core record defines that field (COR-056).
- **Declaring the capability's places from its own configuration rather than the friction key.** Rejected: component places are static package metadata and project places are the friction key's, by the anchors-and-friction record (COR-050); a third channel would split discovery.
- **Every place assigned explicitly, including in-root ones.** Rejected: a place inside a root already says which audience it serves; asking twice invites drift, and the finding it enables is covered by the out-of-root case.
- **A project place that gives no type holding no pages.** Not taken. Pages would then be exactly what the type selects. But every project with pages outside its roots would lose them until it typed its places, and an untyped place keeps its meaning (COR-056).
- **Asking an assignment of an untyped place of rule sets as of any other place.** Rejected. A consented write of the backbone would fail this capability's validation, and each step the finding asks serves the finding alone (Rationale).
- **Failing only a document there that declares a page kind, and leaving the others silent.** Not taken. The kind does signal a page the project wants. But the failure would still follow a consented write of the backbone, for a page that write left behind. The report names the same assignment without failing.
- **Passing over a place of rule sets that gives a type too.** Rejected. A type names what the place's documents are, and a document of the page type there is a page by its type (point 4).
- **Treating the signpost of a place of rule sets as never a page, as a rule-set file is.** Rejected. A rule-set file is no page because it holds rules. A signpost is a document like any other, often a signpost page (point 3). Under a root, the rule would take such a page out of that root's space.
- **The backbone leaving the signpost of a place of rule sets out of the places' files.** Rejected. The places alone decide which files hold artefacts (COR-056 point 5). Friction would change for a judgment of this capability, and the signpost's own anchors would go unchecked.
- **An order of places of the capability's own for spaces, pinned to the backbone's by a test.** Rejected. Two orders would need keeping in step, and a document's type and its space could come from places ranked two ways.
- **Each fact on one page only, other pages linking to it.** Rejected. A reader would follow a link for each fact, so a page would not serve on its own.
- **A repeat within one page as a break.** Rejected. Both statements sit in one file, and an opening summary or a recap may be there on purpose.
- **A link and an anchor to a page, for a decided fact on a page that anchors its record.** Rejected. The record already flags the page. The anchor would add a second flag on one fact, and the link would send the reader away for it.
- **A short statement of another page's fact left to a person.** Rejected. No length marks where words start to state a fact. So one passage could be judged a break one time and left to a person the next.
- **Any other artefact a page anchors as the home of what it says, such as a rule, an analysis artefact or code.** Not taken yet. It waits for a page that needs it. Until then, a fact no record decides, such as what a command does, has its home among the pages.
- **A record a page mentions or cites, or code reached through an anchored file, grounding a statement.** Rejected. A change to either flags no page.
- **Each space written without a shared method.** Rejected. Rules would be re-derived per space and per project, and would drift.
- **The checks enforcing `LDOC`'s parts on every page of the spaces.** Rejected, as COR-051 rejects it for every method rule set (COR-051 point 2). One requirement would be enforced two ways, and the rule's status and scope would no longer decide where its check applies.
- **Agents applying fixes directly.** Rejected. See Rationale.
- **A documentation registry maintained by hand.** Rejected. A registry needs maintaining as much as the pages do. Anchors and friction give the same currency signal from the pages themselves.
- **Running the product inside this capability to test the docs.** Rejected. That is testing; its results arrive as reading evidence instead.
- **Counting only some fields of a source's file as its change.** Rejected: the engine compares a file's content (COR-050 point 5); teaching it fields for one kind would grow the backbone for one consumer, when keeping only those fields in the file gives the same answer.
- **One file listing every source.** Rejected: a change to any source would ask every page resting on any of them.
- **A source captured as a page, or as an artefact with a friction block of its own.** Rejected: its prose, or its bookkeeping, would be part of the file whose every change asks the pages resting on it.
- **Captured sources in a documentation space, beside the space definitions.** Not taken. They would survive uninstalling the capability and sit where maintainers read, but the resolver would have to learn where that location lies from the backbone — a full discovery for every name it is asked — and the file that records the location would join every answer, so recording or moving it would ask every page resting on a source.
- **Fetching each source and comparing it in the check.** Rejected: the check reaches no network, and a fetched page changes with every timestamp on it. A command that fetches sources and reports, outside the check, can come when a project needs one.
- **A capability of its own for the `source` kind.** Not taken yet: pages are the kind's only consumer today (COR-007). The cost is that an artefact outside documentation — a decision record, say — can anchor a source only where this capability is installed. A consumer that needs the kind without it is the trigger to move the kind and its captured sources to a capability of their own.
- **A narrower name for the kind.** Not taken: "source" is the word the core records and this decision use for what a page quotes (COR-050, COR-051 point 5), and a kind is one word for the whole project with one registrant. Other captured records — a transcript, an excerpt — name their kinds for what they hold.

## Implications

- **The capability ships** its shared method rule set with the parts of it that validation enforces, a template and a declared structure per page kind, the declaration of its places, surface and connections, a type registry naming `page` and `template` with the type each of its places gives, the `source` anchor kind with its resolver and the shape of a captured source, an agent that proposes friction fixes and performs reader-review and that it declares the fixer of its pages, and an onboarding guide. Its template for a space's definition carries a scope. It also ships an authoring command for a page and a space, paired with a skill (COR-005). It ships its contribution of the rule-set reviewer too, with an optional dependency on project-management (point 9).
- **Projects** declare their spaces' locations through the documentation roots — and any further places through the friction key, assigning out-of-root ones to a space in the capability's configuration, an untyped place of rule sets only where they want its signpost in a space — keep each space's definition in the technical space, and wire the core friction check into their continuous integration if they want it enforced; they capture each source their pages rest on and record a new version of it when they read one, and uninstalling the capability removes the captured sources with its project tier. A project gives its assigned out-of-root places the page type before a space's definition selects pages by type. Each space's definition carries a scope that selects the space's pages.
- **Analysis components** can supply readers through the readers point. The capability keeps no glossary of its own; if it needs one, it takes it through a point from whatever component keeps one. **Work-tracking components** receive the capability's contributions through their own points: friction to their documentation checks, and its agent as the fixer of pages.

