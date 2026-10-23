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
  - [UC-014]
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
---

# UC-038 — Author and extend my project's own rule sets

**Goal:** Author and extend my project's rule sets without editing the ones that ship with the system.

**Other actors:** None.

**Preconditions:**

- **From UC-014:** The project runs the system: it is the methodology's source repository, or the system is installed in it.
- **From UC-014, UC-023 or UC-016:** The method rule sets the project may inherit lie in it. They are those the backbone ships, and those of each capability the manifest records (COR-051 point 6).

**Assumptions:**

- A rule set of the project's own neither contradicts nor relaxes a rule it inherits. Validation checks only what it can read, and a reviewer judges the rest (COR-051 point 7).

**Trigger:** The project needs a rule of its own on its artefacts, or needs a method rule set's rules to bind on them.

**Main path:**

1. The developer writes a rule set of the project's own, a Markdown file in `rule-sets/` under the internal documentation root, such as `docs/rule-sets/`. No stamp writes one, and the folder alone makes the file a rule set (ADR-056 point 2).
2. In its front matter, the developer gives the set's name and its own version. Its scope selects the artefacts for its rules, by their paths or their types (COR-051 point 2).
3. The developer writes each rule as a section headed by its id, `RS-<SET>-NNN`, and its title, holding the statement. Each rule has an entry in `rules` too (COR-051 points 2 and 3).
4. A new rule takes no status, so it is proposed and binds nothing (COR-051 point 4).
5. To extend a method rule set, the developer names it in `inherits`, pinned to its major, as `<component>:<SET>@<major>` writes it. The developer never edits the method rule set itself, which sync refreshes (COR-051 points 6 and 7).
6. Where an inherited rule offers an extension point, a rule of the set may fill it. It names the point in `fills`, and anchors the rule it fills, so a change there flags the fill (COR-051 point 7).
7. The developer runs `pkit validate`. Its `rule-sets` pass checks each set's schema and the join between its data and its sections. It checks the ids, the origins, the successors and what each set inherits too (COR-051 points 2, 3, 5 and 7).
8. The developer runs `pkit rule-sets reach`. The system answers which accepted rules bind on each artefact, and through which sets. It names each rule that a pin behind its set holds back (COR-051 point 7).
9. The developer runs `pkit rule-sets reach --preview`, which answers as if every proposed rule were accepted. It marks what holds only under the preview, and validation never reads that answer.
10. The developer commits the rule set. Its rules stay proposed until the merge authoriser accepts them (UC-040).

**Variants:**

- **1a.** A capability's install created the set, inheriting the capability's method rule set (UC-023). The developer runs `pkit capabilities project-rule-set <name>`, which shows that set and each set of the project's own that inherits the method set. It writes nothing (REQ-005). The developer edits that set, and the path goes on at step 3.
- **1b.** The project keeps rule sets in a place of its own whose path has a `rule-sets` segment, declared in `friction.places`. The developer writes the set there, and the path goes on at step 2.
- **1c.** The developer would change a rule a method rule set ships. The developer proposes the change to that set's owner, or does not inherit the set (COR-051 point 7). An edit of the set would not survive sync. The use case ends.
- **2a.** A scope holds an empty list, names neither paths nor types, or names a type that no owner declares. Validation fails on it, and the path rejoins at step 2.
- **5a.** The set would inherit a set that does not exist under the address written, or the inheriting would close a cycle. Validation fails, naming the set, and the path rejoins at step 5.
- **7a.** A rule's id carries another set's name, or redefines an inherited id. Or a rule and its section do not match, or two rule sets share a name. Validation fails, naming each, and the path rejoins at step 3.
- **7b.** An accepted rule has no complete origin, or its origin cites a decision record that is not accepted. Validation fails, naming the rule (COR-051 point 5).
- **7c.** A rule's origin cites a source of a kind a capability registers. Validation resolves it through that kind's command, offline and within thirty seconds (REQ-006 and REQ-007). A command that gives no answer fails validation as `unanswered-source`, and is never passed (REQ-004).
- **7d.** A fill names a point that no inherited rule offers, fills a point a second time along the chain, or anchors no rule it fills. Validation fails at the fill, and the path rejoins at step 6.
- **7e.** One artefact is reached through two routes that pin one set at different majors, or through sets that bring different fills for one point. Validation fails on the artefact, naming both routes, and never chooses between them (COR-051 point 7).
- **7f.** A pin names a major that its inherited set has passed. Validation fails on the inheriting set, naming the new major, and `pkit status` shows the pin with its fix. No rule binds through the pin until the project reviews the new major and updates it.
- **7g.** A file in a `rule-sets` folder reads as a set that no location rule finds, such as one a root changed by hand left behind. Validation fails on it as `unfound-rule-set`, naming how to mend it (COR-051 point 6).
- **7h.** A part of a rule that the set declares under `checks` names a check that is not there. Validation reports it without failing, and that part goes back to whoever judges the rest of the rule (COR-051 point 2).
- **8a.** The developer passes `--at <rev>`. The system answers for that commit's state, read from the commit's objects, and checks nothing out.

**Postconditions:** The project holds a rule set of its own that validation passes. It inherits each method rule set it extends at a major the project reviewed, and leaves each one unedited. Its accepted rules bind on the artefacts its scope selects.

**Minimal guarantees:**

- Sync never reads or writes a rule set of the project's own, and uninstall never writes one (COR-051 point 6 and REQ-002).
- No rule of a method rule set binds until a set of the project's own with a scope inherits it (COR-051 point 7).
- A proposed rule binds nothing, wherever it is inherited (COR-051 point 4).
- `pkit rule-sets reach` and `pkit capabilities project-rule-set` write nothing (REQ-005).
