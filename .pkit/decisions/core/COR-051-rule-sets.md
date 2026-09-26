---
id: COR-051
title: Rules live in rule sets, each rule named, grounded and gated
status: proposed
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

When agents write and check a project's artefacts, they follow only what is written down. A project that wants its documentation, its analysis or its conventions kept to a standard therefore needs its rules written, and it needs more than prose to trust them:
- **a stable name**, so that a finding can say which rule it broke;
- **a record of who decided the rule and why**, so it can be questioned;
- **a visible way to change or retire it**, so that nothing silently keeps obeying a rule that was withdrawn.

Decision records provide all three, but at the weight of a four-section document per choice. A rule is usually one sentence, and a standard is a dozen of them. Written as full records, a set of small rules becomes a dozen files, which is the bureaucracy people route around. Written as loose prose, the rules lose their names, their reasons and their gate.

Rules are also layered. A component ships the rules its discipline needs, and each project adds its own on top. The project must be able to extend the shipped rules without editing them, and to notice when the shipped rules change under it.

## Decision

**Rules are kept in rule-set files. Each rule is a named, permanent, gated statement with a recorded origin, and each project extends the rule sets a component ships without editing them.**

1. **What a rule is.** A rule is a statement that every artefact in its scope must satisfy. It is caused by a decision, and a tool, an agent or a reviewer can check it. It differs from its neighbours:
   - a decision record chooses among alternatives and records why;
   - a template is a starting shape;
   - a schema checks the mechanically checkable part of some rules.

   Rules serve four needs: instructions for whoever writes an artefact, criteria for whoever checks it, a name that findings can cite, and extension across layers. The methodology's own operational rules for agents working in a repository are a different thing that shares the word, and are not governed by this record.

2. **A rule set is a collection of artefacts.** A rule set is one file. In the terms of the anchors-and-friction record (COR-050), it is a collection file whose entries are rules, and each rule is an artefact in its own right.
   - **Its front matter holds the data:**
     - the rule set's name and version;
     - what it inherits (point 7);
     - which artefacts its rules apply to (its *scope*, given as places; a consuming component may narrow it);
     - a map from each rule's id to that rule's machine fields: status, origin, the extension points it **offers**, the extension points it **fills**, its successor, and the anchor and recheck-marker fields every artefact carries (COR-050).
   - **Its body holds the prose:** one section per rule, headed by the rule's id and title, containing the statement.
   - A schema fixes the data's shape. Validation checks the schema, and also that every rule in the body has data and every data entry has a rule in the body.
   - **Discovery:** rule sets are found where artefacts are found, in the places a component or the project declares to hold them (COR-050).

   **Anchoring.** An artefact may anchor to an individual rule. A rule's content is its data entry together with its statement, and so includes its status. Editing a statement, or accepting, superseding or withdrawing a rule, is therefore a change that the rule's dependants see as friction. Nothing keeps silently obeying a rule that has changed.

3. **Identifiers.** A rule's id is `RS-<SET>-NNN`: the family prefix, the rule set's name, and a number. Ids are permanent. A rule is never renumbered, and a retired id is never reused. Rule-set names must be unique among rule sets. Because every rule id carries the `RS` family prefix, rule ids cannot collide with other identifier families. An **extension point** a rule offers is named with `#`, as in `RS-CMN-003#cause-location`, so that it never clashes with the colon that separates a namespace in a citation.

4. **Statuses and the gate.**
   - A rule without a status is **proposed**, and binds nothing.
   - **Accepted** rules bind: writers follow them and checks enforce them.
   - A **superseded** rule names its successor and binds nothing.
   - A **withdrawn** rule is retired without a successor and binds nothing.
   - Superseded and withdrawn rules stay in place with their ids.
   - Accepting a rule is a reviewed change, like accepting a decision record under the decision-record specification's acceptance gate. Where that path involves a person, an agent may draft rules and propose their acceptance, but it is the person's review that accepts them.
   - A successor sits in the same rule set, or in a set that inherits it.

5. **Origins, checked deterministically.** Every accepted rule carries an origin: when it was decided, by whom, and why, in the decider's words. Alternatively, the origin may cite a decision record for a rule whose reasoning outgrows a line. An origin may also cite a **source**: a captured record of where the quoted words were said, of a kind some capability resolves as an anchor kind. Validation fails unless all of the following hold:
   - every accepted rule has a complete origin;
   - a cited decision record exists, and is accepted whenever the rule is accepted;
   - a cited source resolves through the anchor kind a capability registered for it (COR-050). A source kind with no installed resolver is reported as unresolved-kind, never silently passed;
   - ids are unique and not reused;
   - every successor exists;
   - the join between data and prose holds.

   Whether a quoted reason truly supports its rule is judgment, left to agents and reviewers. A project may additionally require that every origin cite a source.

6. **Two kinds, two owners.**
   - **Method rule sets** ship with a component. They are owned and versioned with it and refreshed by sync.
   - **Project rule sets** are owned by the project. They live in places the project declares, by default under its internal documentation root (COR-049), and sync and uninstall never touch them.

   A project never edits a method rule set; it extends it. A method rule set is cited with its component's name; a project rule set is cited bare.

7. **Inheritance.**
   - A rule set may inherit one or more rule sets, and inherits all their rules unchanged. Because rule ids carry their set's name, rules from different inherited sets cannot collide. A capability's rule set may inherit another capability's rule set only if it declares a dependency on that capability, using the mechanism by which capabilities depend on one another (COR-030). Any capability may inherit a rule set the backbone ships.
   - It may add rules of its own, and may fill extension points that inherited rules offer. Each extension point is filled at most once along an inheritance chain. A filling rule anchors to the rule it fills, so a change to the inherited rule flags the fill.
   - It may not contradict or relax an inherited rule. Validation checks what can be checked mechanically: no redefined inherited id, no fill of an undeclared point, no second fill of the same point. Anything beyond that is left to reviewers. A project that disagrees with an inherited rule proposes a change to its owner, or does not inherit that set. It does not quietly override it.
   - Inheriting a rule set owned by someone else **pins that set's major version**, written as the set name followed by `@` and the major version. A rule set's version is its own, not its component's. A major version is required when an accepted rule is withdrawn, superseded or tightened, when an offered extension point is removed, or when a new accepted rule is added.
   - When a new major version of an inherited set arrives, the inheriting set is reported in status and fails validation wherever the check is enforced, until the project reviews it and updates the pin.
   - A fill whose inherited rule is superseded or withdrawn is reported as orphaned.

## Rationale

**Why several inherited sets are allowed.** A project may build on rules from more than one component. Family-prefixed ids cannot collide, and each extension point is filled at most once, so multiple inheritance needs no conflict resolution.

**Why data in front matter and prose in the body.** Every field a check depends on (status, origin, successor, extension points) is data. Reading data out of prose conventions is fragile: a misspelt marker becomes a missed rule instead of a schema error. The statements, and the reasons behind them, are what people and agents read, so they stay prose. A shape where front matter carries data and the body carries prose is already familiar from decision records. The id join between the two is itself a cheap deterministic check.

**Why proposed by default.** Everywhere else in the methodology, a new decision binds only after an explicit acceptance. If rules bound on being written, any draft, including one an agent wrote on its own, would take effect unreviewed.

**Why the family prefix.** Unprefixed rule-set names would compete with every other identifier family, and a project naming a rule set after one of them would make citations ambiguous. A family prefix makes collisions impossible by construction and makes a rule recognisable at a glance.

**Why pin the major version.** A project's rules are written against the shipped rules as they were. A breaking change to the shipped rules can silently invalidate them. Pinning turns that into a visible review, not a silent drift.

**Why a rule set is a collection of artefacts.** Discovery, anchoring and change detection already exist for artefacts (COR-050). Treating each rule as an artefact reuses them instead of building a second copy. It also makes a rule's change of status visible to everything that relies on it.

**Why core.** Two components need rules and must not depend on each other for the machinery: one that keeps analysis of what the system must do, and one that keeps documentation true. The rules about where artefacts come from govern both. Projects also write rules of their own on top of what components ship. Nothing here names a discipline. Project-owned rule sets need the machinery on their own. The component consumers are designed alongside, not guessed. On both counts, the usual wait for a pattern to recur before extracting it (COR-007) is not applied.

**Why rules cannot be relaxed by inheritors.** A project that could quietly loosen a shipped rule would make the rule meaningless for anyone reading the project's artefacts. Proposing the change upstream, or choosing not to inherit, keeps every binding rule honest about where it comes from.

### Alternatives considered

- **Every rule as a full decision record.** Rejected. A standard of a dozen one-line rules becomes a dozen documents, which is exactly the weight that makes people skip writing rules down.
- **Rules as loose prose.** Rejected. It loses names, origins, statuses and the gate.
- **Rules entirely as data, with the statement included, and a generated view for reading.** Rejected. It needs a generation step and generated files that can drift, and long statements and quotes are awkward to write and review as data.
- **Markers in the prose, parsed by pattern.** Rejected. It is fragile in exactly the fields that checks depend on.
- **Rules binding when written.** Rejected. It inverts the acceptance gate.
- **Rule-set names without a family prefix.** Rejected. Collisions with other identifier families would have to be policed by a reserved list.

## Implications

- **The backbone ships** the rule-set schema and the checks in points 2, 3, 5 and 7, run by validation, with rule ids as a new identifier family. Rules take part in friction like any other artefact.
- **Components** that ship rules put their method rule sets in their own subtrees and declare the extension points they offer.
- **Projects** keep their rule sets as project-owned files, and pin what they inherit.
- **Writers and checkers** (agents, reviewers, checks) follow accepted rules only, and cite rule ids in their findings.
- **The decision-record specification** describes rule sets as a separate identifier family with the same guarantees as decision records: permanent ids, recorded origins, statuses and the acceptance gate. It covers the `withdrawn` status, which only rules have, and the gate as it applies to rule sets living outside the decisions folder.
- **Rules rely on** the anchors-and-friction record's definition of a collection entry's content (its data entry together with its id-headed body section), so a rule's statement takes part in friction.
