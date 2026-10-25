---
id: UC-038
title: Author and extend my project's own rule sets
status: active
actor: ACT-developer
other-actors: []
requirements:
  - REQ-002
  - REQ-004
  - REQ-005
  - REQ-006
  - REQ-007
after:
  - [UC-014, UC-049]
  - [UC-014, UC-023, UC-016]
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/rule_sets.py
        - src/project_kit/rule_set_reading.py
        - src/project_kit/declared_rule_sets.py
        - src/project_kit/cli.py
        - .pkit/schemas/README.md
      record:
        - COR-051#2
        - COR-051#3
        - COR-051#4
        - COR-051#5
        - COR-051#6
        - COR-051#7
        - COR-017
        - ADR-056#2
        - ADR-057#2
      artefact:
        - ACT-developer
        - REQ-002
        - REQ-004
        - REQ-005
        - REQ-006
        - REQ-007
    revalidated:
      at: 2026-10-25T04:19:19Z
      outcome: unchanged
      unchanged-because: The change edits cli.py only in pkit refs lookup, which answers several ids under --json and now also resolves a point of a record to its heading's anchor. No step of this use case looks a record up, so it holds.
---

# UC-038 — Author and extend my project's own rule sets

**Goal:** Author and extend my project's rule sets without editing the ones that ship with the system.

**Other actors:** None.

**Preconditions:**

- **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.
- **From UC-014, UC-023 or UC-016:** The method [rule sets](../../../glossary.md#term-rule-set--rule-set) the project may inherit lie in it. They are those the [backbone](../../../glossary.md#term-backbone--backbone) ships, and those of each [capability](../../../glossary.md#term-capability--capability) the [manifest](../../../glossary.md#term-manifest--manifest) records (COR-051 [point](../../../glossary.md#term-point--point) 6).

**Assumptions:**

- A [rule set](../../../glossary.md#term-rule-set--rule-set) of the [project](../../../glossary.md#term-project--project)'s own neither contradicts nor relaxes a [rule](../../../glossary.md#term-rule--rule) it inherits. [Validation](../../../glossary.md#term-validation--validation) checks only what it can read, and a [reviewer](../../../glossary.md#term-reviewer--reviewer) judges the rest (COR-051 [point](../../../glossary.md#term-point--point) 7).

**Trigger:** The [project](../../../glossary.md#term-project--project) needs a [rule](../../../glossary.md#term-rule--rule) of its own on its [artefacts](../../../glossary.md#term-artefact--artefact), or needs a method [rule set](../../../glossary.md#term-rule-set--rule-set)'s rules to bind on them.

**Main path:**

1. The developer writes a [rule set](../../../glossary.md#term-rule-set--rule-set) of the [project](../../../glossary.md#term-project--project)'s own, a Markdown file in `rule-sets/` under the internal [documentation root](../../../glossary.md#term-documentation-root--documentation-root), such as `docs/rule-sets/`. No [stamp](../../../glossary.md#term-stamp--stamp) writes one, and the folder alone makes the file a rule set (ADR-056 [point](../../../glossary.md#term-point--point) 2).
2. In its front matter, the developer gives the set's name and its own `version`. Its scope selects the [artefacts](../../../glossary.md#term-artefact--artefact) for its rules, by their paths or their types (COR-051 point 2).
3. The developer writes each [rule](../../../glossary.md#term-rule--rule) as a section headed by its id, `RS-<SET>-NNN`, and its title, holding the statement. Each rule has an entry in `rules` too (COR-051 points 2 and 3).
4. A new rule takes no status, so it is proposed and binds nothing (COR-051 point 4).
5. The developer names in `inherits` each method rule set the set extends, pinned to its major, as `<component>:<SET>@<major>` writes it. The developer never edits the method rule set to extend it, since its [component](../../../glossary.md#term-component--component) owns it (COR-051 points 6 and 7).
6. The developer runs `pkit validate`. Its `rule-sets` pass checks each set's schema and the join between its data and its sections. It checks the ids, the origins, the successors and what each set inherits too (COR-051 points 2, 3, 5 and 7).
7. The developer runs `pkit rule-sets reach`. The [system](../../../glossary.md#term-system--system) answers which accepted rules bind on each artefact, and through which sets. It names each rule that a pin behind its set holds back (COR-051 point 7).
8. The developer runs `pkit rule-sets reach --preview`, which answers as if every proposed rule were accepted. It marks what holds only under the preview, and [validation](../../../glossary.md#term-validation--validation) never reads that output.
9. The developer commits the rule set. Its rules stay proposed until the merge authoriser accepts them (UC-040).

**Variants:**

- **1a.** A [capability](../../../glossary.md#term-capability--capability)'s [install](../../../glossary.md#term-install--install) created the set, inheriting the capability's method [rule set](../../../glossary.md#term-rule-set--rule-set) (UC-023). The developer runs `pkit capabilities project-rule-set <name>`, which shows that set and each set of the [project](../../../glossary.md#term-project--project)'s own that inherits the method set. It writes nothing (REQ-005). The developer edits that set, and the path goes on at step 3.
- **1b.** The project keeps rule sets in a [place](../../../glossary.md#term-place--place) of its own whose path has a `rule-sets` segment, declared in `friction.places`. The developer writes the set there, and the path goes on at step 2.
- **1c.** The developer would edit a [rule](../../../glossary.md#term-rule--rule) a method rule set ships. That edit belongs to the [component](../../../glossary.md#term-component--component) that ships the set, so the developer proposes it there, or does not inherit the set (COR-051 [point](../../../glossary.md#term-point--point) 7). The use case ends.
- **2a.** A scope holds an empty list, names neither paths nor types, or names a type that no owner declares. [Validation](../../../glossary.md#term-validation--validation) fails on it, and the path rejoins at step 2.
- **5a.** The set would inherit a set that does not exist under the address written, or the inheriting would close a cycle. Validation fails, naming the set, and the path rejoins at step 5.
- **5b.** An inherited rule offers an extension point, and a rule of the set fills it. The filling rule names the extension point in `fills`, and anchors the rule it fills, so an edit there flags the fill (COR-051 point 7).
- **6a.** Validation fails on a rule or a set's name, naming each, and the path rejoins at step 3. It fails on each of these:
  - a rule's id that carries another set's name, or redefines an inherited id
  - a rule and a section that do not match
  - two rule sets that share a name
- **6b.** An accepted rule has no complete origin, or its origin cites a [decision record](../../../glossary.md#term-decision-record--decision-record) that is not accepted. Validation fails, naming the rule (COR-051 point 5).
- **6c.** A rule's origin cites a source of a kind a capability registers. Validation resolves it through that kind's command, offline as REQ-007 asks, and stops the command after thirty seconds (REQ-006). A command that gives no result fails validation as `unanswered-source`, and is never passed (REQ-004). A kind no installed component resolves is reported, without failing (COR-051 point 5).
- **6d.** Validation fails at a fill, and the path rejoins at step 5. It fails on each of these:
  - a fill of an extension point that no inherited rule offers
  - a second fill of one extension point along the chain
  - a filling rule that anchors no rule it fills
- **6e.** One [artefact](../../../glossary.md#term-artefact--artefact) is reached through two routes that pin one set at different majors, or through sets that bring different fills for one extension point. Validation fails on the artefact, naming both routes, and never chooses between them (COR-051 point 7).
- **6f.** A pin names a major that its inherited set has passed. Validation's `versions` member fails on the inheriting set, naming the new major, and `pkit status` shows the pin with its fix. No rule binds through the pin until the project reviews the new major and updates it.
- **6g.** A file in a `rule-sets` folder reads as a set that no location rule finds, such as one a root changed by hand left behind. Validation fails on it as `unfound-rule-set`, naming how to mend it (COR-051 point 6).
- **6h.** A part of a rule that the set declares under `checks` names a check that is not there. Validation reports it without failing, and that part goes back to whoever judges the rest of the rule (COR-051 point 2).
- **7a.** The developer passes `--at <rev>`. The [system](../../../glossary.md#term-system--system) answers for that commit's state, read from the commit's objects, and checks nothing out.

**Postconditions:** The [project](../../../glossary.md#term-project--project) holds a [rule set](../../../glossary.md#term-rule-set--rule-set) of its own that [validation](../../../glossary.md#term-validation--validation) passes. It inherits each method rule set it extends at a major the project reviewed, and leaves each one unedited. The accepted rules it inherits bind on the [artefacts](../../../glossary.md#term-artefact--artefact) its scope selects. Each new [rule](../../../glossary.md#term-rule--rule) of its own is proposed, and binds nothing until the merge authoriser accepts it.

**Minimal guarantees:**

- [Sync](../../../glossary.md#term-sync--sync) never reads or writes a [rule set](../../../glossary.md#term-rule-set--rule-set) of the [project](../../../glossary.md#term-project--project)'s own, and uninstall never writes one (COR-051 [point](../../../glossary.md#term-point--point) 6 and REQ-002).
- No [rule](../../../glossary.md#term-rule--rule) of a method rule set binds until a set of the project's own with a scope inherits it (COR-051 point 7).
- A proposed rule binds nothing, wherever it is inherited (COR-051 point 4).
- `pkit rule-sets reach` and `pkit capabilities project-rule-set` write nothing (REQ-005).
