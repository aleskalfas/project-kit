---
id: COR-051
title: Rules live in rule sets, each rule named, grounded and gated
status: accepted
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

When agents write and check a project's artefacts, they follow only what is written down. A project that wants its documentation, its analysis or its conventions kept to a standard therefore needs its rules written, and it needs more than prose to trust them:
- **a stable name**, so that a finding can say which rule it broke;
- **a record of who decided the rule and why**, so it can be questioned;
- **a visible way to change or retire it**, so that nothing silently keeps obeying a rule that was withdrawn.

Decision records provide all three, but at the weight of a four-section document per choice. A rule is usually one sentence, and a standard is a dozen of them. Written as full records, a set of small rules becomes a dozen files, which is the bureaucracy people route around. Written as loose prose, the rules lose their names, their reasons and their gate.

Rules are also layered. A component ships the rules its discipline needs, and each project adds its own on top. The project must be able to extend the shipped rules without editing them, to say where they bind, and to notice when the shipped rules change under it.

## Decision

**Rules are kept in rule-set files. Each rule is a named, permanent, gated statement with a recorded origin. Each project extends the rule sets a component ships without editing them, and its own sets say where the rules bind.**

1. **What a rule is.** A rule is a statement that every artefact it binds on must satisfy (point 7). It is caused by a decision, and a tool, an agent or a reviewer can check it. It differs from its neighbours:
   - a decision record chooses among alternatives and records why;
   - a template is a starting shape;
   - a schema checks the mechanically checkable part of some rules.

   Rules serve four needs: instructions for whoever writes an artefact, criteria for whoever checks it, a name that findings can cite, and extension across layers. The methodology's own operational rules for agents working in a repository are a different thing that shares the word, and are not governed by this record.

2. **A rule set is a collection of artefacts.** A rule set is one file. In the terms of the anchors-and-friction record (COR-050), it is a collection file whose entries are rules, and each rule is an artefact in its own right.
   - **Its front matter holds the data:**
     - the rule set's name and version;
     - what it inherits (point 7);
     - which artefacts it selects for its rules (its *scope*, below);
     - a map from each rule's id to that rule's machine fields: status, origin, the extension points it **offers**, the extension points it **fills**, its successor, and, inside the entry's methodology container, the friction block — anchors and revalidation — every artefact carries (COR-050);
     - the parts of its rules that checks enforce, which are not among any rule's own fields (below).
   - **Its body holds the prose:** one section per rule, headed by the rule's id and title, containing the statement.
   - A schema fixes the data's shape. Validation checks the schema, and also that every rule in the body has data and every data entry has a rule in the body.
   - **Discovery:** rule sets are found where artefacts are found, in the places a component or the project declares to hold them (COR-050).

   **Scope.** A set's scope selects artefacts by the paths of their files and by their types (refinement per COR-056). It has three keys, each a list. A path is relative to the repository root. It names a file, a folder with everything beneath it, or a glob in which `**` matches across folders.
   - `paths`: an artefact is selected when one of these paths matches its file. Without `paths`, every file matches.
   - `exclude`: a selected artefact is left out when one of these paths matches its file. Without `exclude`, nothing is left out.
   - `types`: an artefact is selected when its type, or a type in contention for it (COR-056 point 3), is one of these. Without `types`, every artefact matches, with a type or with none.

   An artefact is in the scope when `paths` and `types` both select it and `exclude` does not leave it out. An empty list is refused, since it could mean nothing or everything. A scope with neither `paths` nor `types` is refused too. A type in `types` must be one its owner declares (COR-056 point 2), and any other is a validation error. A scope written as a plain list of paths is its `paths`. An artefact under the excluded paths of the anchors-and-friction record (COR-050 point 7) stays in any scope that selects it. A set with no scope selects no artefact itself, and its rules bind only through the sets that inherit it (point 7). A method rule set (point 6), whether the backbone or a component ships it, takes no scope, and a scope on one is a validation error.

   **Anchoring.** An artefact may anchor to an individual rule. A rule's content is its data entry together with its statement, and so includes its status. Editing a statement, or accepting, superseding or withdrawing a rule, is therefore a change that the rule's dependants see as friction. Nothing keeps silently obeying a rule that has changed.

   **What a check enforces.** A check can enforce part of a rule, such as a validator that reads a field, or a tool that counts the words in a sentence. The rule's owner declares that part in the set's front matter, beside the rule but not among its own fields. The declaration names the check and whose it is. A check may be the backbone's, a command a component registers in its package metadata, or the project's own tool. A check enforces its part only where the rule binds (point 7), and whoever judges the rest of the rule leaves that part to it.
   - **Outside the content.** The declaration is none of the rule's own fields and no part of its statement, so it is no part of the rule's content (COR-050). Declaring a check, or changing one, changes no rule and flags nothing anchored to it.
   - **A check that is not there.** A declaration may name a backbone check that does not exist, or a component command that no installed component registers. Validation reports it without failing, and that part goes back to whoever judges the rest of the rule.
   - **A check nobody runs.** A project's own tool is trusted by its name, and validation cannot see whether a named check is run at all. A tool that stops running, or a check that nothing runs, leaves its part unjudged until the declaration is removed.

3. **Identifiers.** A rule's id is `RS-<SET>-NNN`: the family prefix, the rule set's name, and a number. Ids are permanent. A rule is never renumbered, and a retired id is never reused. Rule-set names must be unique among rule sets. Because every rule id carries the `RS` family prefix, rule ids cannot collide with other identifier families. An **extension point** a rule offers is named with `#`, as in `RS-CMN-003#cause-location`, so that it never clashes with the colon that separates a namespace in a citation.

4. **Statuses and the gate.**
   - A rule without a status is **proposed**, and binds nothing.
   - **Accepted** rules bind, on the artefacts point 7 says: writers follow them and checks enforce them.
   - A **superseded** rule names its successor and binds nothing.
   - A **withdrawn** rule is retired without a successor and binds nothing.
   - Superseded and withdrawn rules stay in place with their ids.
   - Accepting a rule is a reviewed change, like accepting a decision record under the decision-record specification's acceptance gate. Where that path involves a person, an agent may draft rules and propose their acceptance, but it is the person's review that accepts them.
   - A successor sits in the same rule set, or in a set that inherits it. It binds wherever its own set's rules bind (point 7), which may be less than where the rule it replaces bound. A set that inherits the replaced rule's set, but not the successor's, loses the rule. A supersession requires a new major, so that set's pin falls behind, and the loss is reviewed before the pin is updated (point 7).

5. **Origins, checked deterministically.** Every accepted rule carries an origin: when it was decided, by whom, and why, in the decider's words. Alternatively, the origin may cite a decision record for a rule whose reasoning outgrows a line. An origin may also cite a **source**: a captured record of where the quoted words were said, of a kind some capability resolves as an anchor kind. Validation fails unless all of the following hold:
   - every accepted rule has a complete origin;
   - a cited decision record exists, and is accepted whenever the rule is accepted;
   - a cited source resolves through the anchor kind a capability registered for it (COR-050). A source kind with no installed resolver is reported as unresolved-kind, never silently passed;
   - ids are unique and not reused;
   - every successor exists;
   - the join between data and prose holds.

   Whether a quoted reason truly supports its rule is judgment, left to agents and reviewers. A project may additionally require that every origin cite a source.

6. **Two kinds, two owners.**
   - **Method rule sets** ship with the backbone or with a component. They are owned and versioned with it and refreshed by sync.
   - **Project rule sets** are owned by the project. They live in places the project declares, by default under its internal documentation root (COR-049). Sync never reads or writes them, and uninstall never writes them.

   A project never edits a method rule set; it extends it. A method rule set is cited with its component's name; a project rule set is cited bare.

7. **Inheritance, and where rules bind.**
   - **Inheriting.** A rule set may inherit one or more rule sets, and inherits all their rules unchanged. Because rule ids carry their set's name, rules from different inherited sets cannot collide. A capability's rule set may inherit another capability's rule set only if it declares a required dependency on that capability, using the mechanism by which capabilities depend on one another (COR-030). Any capability may inherit a rule set the backbone ships. A set's inheritance *chain* is the set and every set it inherits, directly or not.
   - **Pins.** Inheriting a rule set **pins that set's major version**, written as the set name followed by `@` and the major version. A rule set's version is its own, not its component's. A new major version is required when:
     - an accepted rule is withdrawn, superseded or tightened
     - an offered extension point is removed
     - a new accepted rule is added
     - what the set inherits changes: a set added or dropped, or a pin moved to another major
   - **Routes.** A *route* leads from an artefact to a rule set. It starts at a set whose scope selects the artefact, and follows what that set inherits, pin by pin. It passes only through sets whose own scope, where they have one, also selects the artefact. A set *reaches* every artefact from which a route leads to it. One artefact may have several routes to one set: from two sets whose scopes both select it, or along two lines of inheritance from one set.
   - **Where a rule binds.** An inherited rule binds within the scope of the set that inherits it. Exactly: an accepted rule binds on an artefact when a route leads from the artefact to the rule's set, and no pin on that route is behind its set (below). A *shared set*, one with no scope of its own, therefore reaches wherever the sets that inherit it reach, and nowhere else. A set that declares a scope keeps it. Its rules bind only on artefacts its own scope selects, whoever inherits it, so inheriting a set never widens its scope.
   - **Method rule sets.** A method rule set takes no scope (point 2), so every route starts at a set of the project's own. No rule of a method rule set binds, even on the artefacts of the backbone or component that ships it, until a set of the project's own with a scope inherits it, directly or not.
   - **One answer.** The backbone answers, for each artefact, which accepted rules bind on it. Writers, checks and reviewers all read that one answer.
   - **A pin behind its set.** When a new major version of an inherited set arrives, the inheriting set is reported in status and fails validation wherever the check is enforced, until the project reviews it and updates the pin. Until then, the pin is behind its set, and no rule binds through it, whether the new major changed the rule or not. The repository holds only the newer major, and nobody has reviewed it for the inheriting set. So each inheritor's pin decides when a shared set's new rules start binding within its reach.
   - **Pins that disagree.** One artefact reached through two routes that pin the same set at different majors is a validation error, never a silent choice between them.
   - **Adding and filling.** An inheriting set may add rules of its own, and may fill extension points that inherited rules offer. Each extension point is filled at most once along an inheritance chain. A filling rule anchors to the rule it fills, so a change to the inherited rule flags the fill. A fill binds only where the rule it fills binds through the filling set, and only while both are accepted.
   - **Fills through several sets.** An offering rule may bind on one artefact through several sets whose scopes select it. Where one of those sets inherits another, directly or not, it is the *more specific* of the two. The most specific sets, those that none of the others inherits, decide the extension point. Each brings the accepted fill its chain holds for that extension point, or none. Where they agree, that fill binds, or none does. Where they differ, by two different rules or by a rule against none, that is a validation error, never a silent choice between them. Until it is mended, the backbone's answer for that artefact names the conflict and takes no side.
   - **No relaxing.** An inheriting set may not contradict or relax an inherited rule. Validation checks what can be checked mechanically: no redefined inherited id, no fill of an undeclared point, no second fill of the same point. Anything beyond that is left to reviewers. A project that disagrees with an inherited rule proposes a change to its owner, or does not inherit that set. It does not quietly override it.
   - **Orphaned fills.** A fill whose inherited rule is superseded or withdrawn is reported as orphaned.

## Rationale

**Why several inherited sets are allowed.** A project may build on rules from more than one component. Family-prefixed ids cannot collide, and each extension point is filled at most once along a chain. Where two routes to one artefact would still disagree, on a set's major or on a fill, validation fails. So multiple inheritance needs no silent choice.

**Why an inherited rule binds within the inheriting set's scope.** A shared set says what to require, and each set that inherits it says where. So one shared set, with no scope of its own, serves several sets, each over its own artefacts. Its new rules bind through an inheritor only once that inheritor has reviewed them and updated its pin. A shared set that bound only within its own scope would bind nothing without one. Given one, its new rules would bind there at once, past every pin.

**Why a parent keeps its own scope.** A set that names its own artefacts means its rules for those artefacts. An inheritor that carried them further would widen a rule its owner had limited. The cost is that a scoped set's new rules bind at once, past its inheritors' pins, and so does any widening of its scope. That stays within one project, since only a project's own sets have scopes.

**Why a method rule set takes no scope.** A scope on a method rule set would bind every adopting project's artefacts with no project set inheriting it. That would take away a project's choice not to inherit the set. The cost is that no shipped rule binds in a project until a scoped set of the project's own inherits it.

**Why a pin behind its set binds nothing.** A tightened rule keeps its id, and the repository holds only the newer text. Binding that text through a pin behind it would bind what nobody reviewed for the inheriting set. The cost is a gap: every new major, a new rule included, stops the set binding through each inheritor until that inheritor updates its pin. Validation fails meanwhile, so the gap is never silent.

**Why pins that disagree are an error.** Two pins of one set at different majors mean the sets that share an artefact were reviewed against different texts. An error names the artefact and both routes, so the project updates the pins together. An artefact's rules then never depend on which inheritor reviewed the set.

**Why the more specific set's fill binds, and differing fills are otherwise an error.** Where two sets select an artefact and one inherits the other, the inheriting set is the more specific. A fill is how it narrows what it inherits. Its chain also holds its parent's fill, since an extension point is filled at most once along a chain. Between sets that do not inherit one another, neither is more specific. An unfilled extension point is not empty, since the offering rule still binds without a fill. So two such sets that leave one extension point filled differently require different things of one artefact. Any choice between them would be silent.

**Why a new major is due when what a set inherits changes.** A set that gains a parent, or moves a pin to a newer major, passes new rules to every set that inherits it. A set that drops a parent, or moves a pin to an older major, takes rules away, as withdrawing them does. Without a new major, either change would reach every inheritor past its pin.

**Why the rule's owner declares what a check enforces.** One declaration serves every kind of check: the backbone's, a component's command and a project's own tool alike. A check's own registration could not serve them all, since a project's tool registers nothing. The owner knows what the rule means, so the owner says which part a check settles. Kept outside the rule's content, a new check flags nothing that depends on the rule. The cost is a gap that nothing reports. Validation sees whether a named check exists, never whether anything runs it. So a declared part that no running check enforces goes unjudged until the declaration is removed.

**Why data in front matter and prose in the body.** Every field a check depends on (status, origin, successor, extension points) is data. Reading data out of prose conventions is fragile: a misspelt marker becomes a missed rule instead of a schema error. The statements, and the reasons behind them, are what people and agents read, so they stay prose. A shape where front matter carries data and the body carries prose is already familiar from decision records. The id join between the two is itself a cheap deterministic check.

**Why proposed by default.** Everywhere else in the methodology, a new decision binds only after an explicit acceptance. If rules bound on being written, any draft, including one an agent wrote on its own, would take effect unreviewed.

**Why the family prefix.** Unprefixed rule-set names would compete with every other identifier family, and a project naming a rule set after one of them would make citations ambiguous. A family prefix makes collisions impossible by construction and makes a rule recognisable at a glance.

**Why pin the major version.** A set's rules are written against the rules it inherits as they were, whether a component ships those rules or the project keeps them. A breaking change to the inherited rules can silently invalidate them. Pinning turns that into a visible review, not a silent drift.

**Why a rule set is a collection of artefacts.** Discovery, anchoring and change detection already exist for artefacts (COR-050). Treating each rule as an artefact reuses them instead of building a second copy. It also makes a rule's change of status visible to everything that relies on it.

**Why core.** Two components need rules and must not depend on each other for the machinery: one that keeps analysis of what the system must do, and one that keeps documentation true. The rules about where artefacts come from govern both. Projects also write rules of their own on top of what components ship. Nothing here names a discipline. Project-owned rule sets need the machinery on their own. The component consumers are designed alongside, not guessed. On both counts, the usual wait for a pattern to recur before extracting it (COR-007) is not applied.

**Why rules cannot be relaxed by inheritors.** A project that could quietly loosen a shipped rule would make the rule meaningless for anyone reading the project's artefacts. Proposing the change upstream, or choosing not to inherit, keeps every binding rule honest about where it comes from.

### Alternatives considered

- **Every rule as a full decision record.** Rejected. A standard of a dozen one-line rules becomes a dozen documents, which is exactly the weight that makes people skip writing rules down.
- **Rules as loose prose.** Rejected. It loses names, origins, statuses and the gate.
- **Rules entirely as data, with the statement included, and a generated view for reading.** Rejected. It needs a generation step and generated files that can drift, and long statements and quotes are awkward to write and review as data.
- **Markers in the prose, parsed by pattern.** Rejected. It is fragile in exactly the fields that checks depend on. A decision record's points are an exception: a live point's id is read from its heading (refinement per COR-058).
- **Rules binding when written.** Rejected. It inverts the acceptance gate.
- **Rule-set names without a family prefix.** Rejected. Collisions with other identifier families would have to be policed by a reserved list.
- **An inherited rule binding only within its own set's scope.** Rejected. A shared set with no scope would bind nothing, and one given a scope would bind its new rules past every inheritor's pin.
- **A consuming component narrowing a set's scope.** Rejected. Nothing in the set would name who narrows it, and a second list of places would drift from the first. Each set narrows itself with `exclude` and `types`.
- **A method rule set also binding on the artefacts of whoever ships it, with no project set inheriting it.** Rejected. A shipped set would bind every adopting project's artefacts, and no pin would hold back its new rules.
- **The checked part of a method rule set's rule kept as its component's own invariant, checked everywhere apart from the rule.** Rejected. One requirement would be enforced two ways: by the check everywhere, and by judgement only where the rule binds. The rule's status would no longer decide when its check applies.
- **Rules the pinned major held keep binding while the pin is behind.** Rejected. The repository holds only the newer text, and a tightened rule keeps its id, so what bound would not be what was reviewed.
- **A silent choice between routes that disagree, such as the newest major.** Rejected. It hides which rules bind, and the newest major binds rules nobody reviewed for that artefact.
- **A fill always binding over a set that leaves its extension point unfilled.** Rejected. Between sets that do not inherit one another, it overrides what the offering rule requires without a fill, and nothing reports it.
- **Each check declaring the rules it covers, in its own registration.** Rejected. A project's own tool registers nothing, and a second place for the same fact drifts.

## Implications

- **The backbone ships** the rule-set schema and the checks in points 2, 3, 5 and 7, run by validation, with rule ids as a new identifier family. Rules take part in friction like any other artefact. The backbone also gives the one answer of point 7, which accepted rules bind on an artefact.
- **Components** that ship rules put their method rule sets in their own subtrees, and give them no scope. They declare the extension points they offer, and the parts their own checks enforce. A component's own check reads from the backbone where each rule binds.
- **Projects** keep their rule sets as project-owned files, pin what they inherit, and give their sets the scopes that say where shared rules bind.
- **Writers and checkers** (agents, reviewers, checks) follow only the accepted rules that bind on an artefact, and cite rule ids in their findings.
- **The decision-record specification** describes rule sets as a separate identifier family with the same guarantees as decision records: permanent ids, recorded origins, statuses and the acceptance gate. It covers the `withdrawn` status, which only rules have, and the gate as it applies to rule sets living outside the decisions folder.
- **Rules rely on** the anchors-and-friction record's definition of a collection entry's content (its data entry together with its id-headed body section), so a rule's statement takes part in friction.
