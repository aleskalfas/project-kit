---
id: UC-043
title: Set up a documentation space for one audience
status: active
actor: core:ACT-adopter
other-actors:
  - core:ACT-operator
  - core:ACT-ai-agent
requirements:
  - REQ-023
  - REQ-024
shortfalls:
  - at: "1b"
    issue: "#1986"
    record: living-docs:DEC-001#1
  - at: 6
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/new.py
        - .pkit/capabilities/living-docs/scripts/_lib/stamp.py
        - .pkit/capabilities/living-docs/scripts/validate.py
        - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        - .pkit/capabilities/living-docs/schemas/config.schema.json
        - .pkit/capabilities/living-docs/templates/space-definition.md
        - .pkit/capabilities/living-docs/skills/docs-author/space.md
        - .pkit/capabilities/living-docs/package.yaml
      record:
        - living-docs:DEC-001#1
        - living-docs:DEC-001#2
        - living-docs:DEC-001#3
        - ADR-034#1
        - COR-005
        - COR-013
        - COR-017
        - COR-021
        - COR-031
        - COR-039#2
        - COR-049#5
        - COR-050#1
        - COR-051#4
        - COR-051#7
        - COR-056#2
        - COR-056#6
      artefact:
        - REQ-023
        - REQ-024
---

# UC-043 — Set up a documentation space for one audience

**Goal:** Set up a documentation space for one audience, with its own location and a definition whose scope selects its pages.

**Other actors:**

- **Operator** (`core:ACT-operator`): is asked before `pkit living-docs new space` writes in a repository other than the session's own, so no such write happens silently ([core:REQ-012](../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).
- **AI agent** (`core:ACT-ai-agent`): carries out the steps for the adopter through the `docs-author` [skill](../../../core/glossary.md#term-skill--skill)'s space operation. It asks the adopter before it edits a configuration file.

**Preconditions:** None.

**Assumptions:**

- The [project](../../../core/glossary.md#term-project--project) has living-docs installed, or registered in place where living-docs is developed ([COR-017](../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-031](../../../../../.pkit/decisions/core/COR-031-capability-origin.md)). The CLI registers `pkit living-docs new` and `validate` from its [package metadata](../../../core/glossary.md#term-package-metadata--package-metadata) ([COR-021](../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)). The [adapter](../../../core/glossary.md#term-adapter--adapter) deploys the `docs-author` [skill](../../../core/glossary.md#term-skill--skill) ([COR-005](../../../../../.pkit/decisions/core/COR-005-bundle-pattern.md) and [COR-013](../../../../../.pkit/decisions/core/COR-013-agent-architecture.md)).
- The [backbone configuration](../../../core/glossary.md#term-backbone-configuration--backbone-configuration) names the two [documentation roots](../../../core/glossary.md#term-documentation-root--documentation-root), and declares in `friction.places` each [place](../../../core/glossary.md#term-place--place) outside them that holds the space's pages ([COR-050 point 1](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#1-artefacts)). Such a place gives the [page](../../glossary.md#term-page--page) type where a [space definition](../../glossary.md#term-space-definition--space-definition) selects by type ([COR-056 point 2](../../../../../.pkit/decisions/core/COR-056-artefact-types.md#2-who-declares-it)).
- The [backbone](../../../core/glossary.md#term-backbone--backbone) answers which documents each place holds, with their types and the scopes over them ([COR-056 point 6](../../../../../.pkit/decisions/core/COR-056-artefact-types.md#6-one-answer)). It answers where each [rule](../../../core/glossary.md#term-rule--rule) binds ([COR-051 point 7](../../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind)). living-docs reads those answers, and ranks no place itself.
- The backbone records a documentation location when a [component](../../../core/glossary.md#term-component--component) first uses it, and a later change of root moves nothing it recorded ([COR-049 point 5](../../../../../.pkit/decisions/core/COR-049-documentation-roots.md#5-a-derived-location-is-recorded-when-it-is-first-used)).
- The review of the change that carries a space definition accepts each rule the definition writes as accepted ([COR-051 point 4](../../../../../.pkit/decisions/core/COR-051-rule-sets.md#4-statuses-and-the-gate)).

**Trigger:** The adopter adopts living-docs, which asks for a user and a technical space. Or the adopter needs a space for an audience neither serves, such as an interface reference's [readers](../../glossary.md#term-reader--reader).

**Main path:**

1. The adopter assigns each [place](../../../core/glossary.md#term-place--place) outside every [documentation root](../../../core/glossary.md#term-documentation-root--documentation-root) that holds the space's pages to the space, under `places` in `.pkit/capabilities/living-docs/project/config.yaml` ([DEC-001 point 1](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#1-spaces)).
2. The adopter names the space's audience in words, as `spaces.<space>.audience` in that file (DEC-001 point 1).
3. The adopter runs `pkit living-docs new space <space> --dry-run`.
4. The [system](../../../core/glossary.md#term-system--system) makes the checks it makes before the write, prints the [space definition](../../glossary.md#term-space-definition--space-definition) and the configuration as it would write them, and writes nothing. So the adopter previews each edit, as [core:REQ-009](../../../core/requirements/quality/REQ-009-preview-before-change.md) asks.
5. The adopter reads the scope it would write, and runs `pkit living-docs new space <space>`.
6. At its entry, before it writes, the system checks that the repository it would change is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses ([core:REQ-012](../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).

> [!WARNING]
> **Not built yet:** `pkit living-docs new` runs no such check, and writes in whatever repository holds its working directory. [ADR-034 point 1](../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

7. The system runs the check that `pkit living-docs validate` runs, over the [project](../../../core/glossary.md#term-project--project) as it stands.
8. The system writes the space definition to `<definitions>/rule-sets/<space>.md`, under the location living-docs declares in the technical space. It inherits `living-docs:LDOC` at its current major. Its scope selects the space's root and the places assigned to it, by the [page](../../glossary.md#term-page--page) type ([DEC-001 point 2](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#2-definitions-kept-apart-from-content)).
9. The system names the definition as the space's `definition` in the [capability](../../../core/glossary.md#term-capability--capability)'s configuration, and keeps every other byte of the file. For a space the project adds, that entry declares the space (DEC-001 point 2).
10. The system runs the check again, and judges the write against where the rules bound before it.
11. The first time a space definition is placed, the system records the definitions location through the [backbone](../../../core/glossary.md#term-backbone--backbone)'s `pkit docs record-location` (DEC-001 point 2).
12. The system says what it wrote, and lists as a warning each page of the space that the space's rules now fail. The definition stands (DEC-001 point 2).
13. The adopter names the page its [readers](../../glossary.md#term-reader--reader) start from as the space's `entry-point` in the configuration (DEC-001 point 1).
14. The adopter runs `pkit living-docs validate`.
15. The system checks the space's places and their assignment, its definition's scope against them, its entry point and its definition (DEC-001 points 1 and 2). It checks a part of an `LDOC` [rule](../../../core/glossary.md#term-rule--rule) only on the pages where that rule binds ([REQ-024](../../requirements/functional/REQ-024-checks-where-rule-binds.md)). It prints a summary that names the spaces whose definitions carry a scope, and exits 0.

**Variants:**

- **1a.** Every [page](../../glossary.md#term-page--page) of the space lies under its [documentation root](../../../core/glossary.md#term-documentation-root--documentation-root), so no [place](../../../core/glossary.md#term-place--place) needs assigning. The path goes on at step 2.
- **1b.** The space is one the [project](../../../core/glossary.md#term-project--project) adds, and records its own location, one that serves its audience ([DEC-001 point 1](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#1-spaces)). The configuration gives it no root of its own, so each of its places is assigned to it. Its new pages go into those places.

> [!WARNING]
> **Not built yet:** the configuration holds no root for a space the project adds. DEC-001 point 1 decides that such a space may record a root as its location, and #1986 tracks it.

- **1c.** A place outside every root that the adopter assigns gives no type in `friction.places`, and the [space definition](../../glossary.md#term-space-definition--space-definition) selects by type. The write then fails [validation](../../../core/glossary.md#term-validation--validation), as variant 10a says ([DEC-001 point 1](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#1-spaces)).
- **3a.** The adopter has an AI agent run steps 3 and 5 through the `docs-author` [skill](../../../core/glossary.md#term-skill--skill)'s space operation. The agent asks the adopter first, where the space needs a configuration file edited (the skill's space operation).
- **5a.** The adopter writes the space definition by hand instead, from the template `templates/space-definition.md` ([DEC-001 point 2](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#2-definitions-kept-apart-from-content)). They record the definitions location with `pkit docs record-location living-docs definitions`, and the path goes on at step 13.
- **5b.** The two documentation roots are one folder, as they are by default. Before its checks, the [system](../../../core/glossary.md#term-system--system) offers to set the internal root apart, at `tech-docs` or a folder the adopter names ([DEC-001 point 2](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#2-definitions-kept-apart-from-content)). `pkit config set docs.internal` writes the new internal root, asking once, or off a terminal with the [stamp](../../../core/glossary.md#term-stamp--stamp)'s `--yes`. Declined, nothing is written and the use case ends, and accepted, the path goes on at step 6.
- **7a.** No scope can select the space's pages yet, since the space is one the project adds with no place assigned. The system refuses, naming the fix, and writes nothing. The use case ends ([DEC-001 point 1](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#1-spaces)).
- **7b.** The space has a definition already, or a definition lies at its path that the configuration does not name. Or another [rule set](../../../core/glossary.md#term-rule-set--rule-set) holds the set's name. The system refuses, saying why, and writes nothing ([DEC-001 point 2](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#2-definitions-kept-apart-from-content)). Where the name is taken, the adopter names another with `--set`, and the path rejoins at step 5.
- **7c.** The check cannot read what it judges, such as the places or where the rules bind. The system refuses, quoting what it could not read, and writes nothing. The use case ends.
- **8a.** The space is the user space. Its definition carries the space's own [rule](../../../core/glossary.md#term-rule--rule), that [reader](../../glossary.md#term-reader--reader) paths stay unbroken, written as accepted ([DEC-001 point 3](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#3-what-the-shared-rules-require)). The system says that the review of the change that carries the definition accepts it.
- **9a.** The [capability](../../../core/glossary.md#term-capability--capability)'s configuration does not exist yet. The system creates it, holding the space's entry.
- **9b.** The configuration's `spaces` is not written as a block mapping, or its lines end in more than one way. The system refuses before it writes anything, and names the line to add by hand. The use case ends.
- **10a.** The write brings a validation error the project did not have, such as an assigned place outside every root that gives no page type. The system puts back every file it wrote, refuses and quotes the error ([REQ-023](../../requirements/quality/REQ-023-refused-stamp-writes-nothing.md)). The use case ends.
- **10b.** The check after the write cannot read what it judges once the rules bind. An example is a readers [data point](../../../core/glossary.md#term-data-point--data-point) that does not resolve, where the space's pages name readers. The system puts back every file it wrote, and refuses (REQ-023). The use case ends.
- **11a.** The definitions location cannot be recorded. The system puts back every file it wrote, and refuses (REQ-023). The use case ends.
- **12a.** The space's rules fail some of its pages once they bind. The adopter mends those pages next, as `UC-044` describes, and the path goes on at step 13.
- **13a.** The page the space's readers start from does not exist yet. The adopter writes it first, as `UC-044` describes, and the path rejoins at step 13.
- **15a.** Validation finds a fault in the space, names it, and exits 1. The adopter mends it, and the path rejoins at step 14. The faults it fails on are these:
  - a place outside every root that holds a document nothing else claims, with no assignment
  - an assignment of a place `friction.places` does not declare, to a space nobody declares, or of one place twice
  - a page an assigned place gives the space, outside the definition's scope or inside another space definition's scope
  - an entry point that is not a document of its space
  - a space definition outside `<definitions>/rule-sets/`, or one that does not inherit `living-docs:LDOC`
- **15b.** Validation reports, without failing, what onboarding or the adopter still owes. That is a space with no definition, a definition whose scope is missing or holds a placeholder, and the pages a scope leaves out. It names the scope to give such a definition ([DEC-001 point 2](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#2-definitions-kept-apart-from-content)).

**Postconditions:** The space has a [space definition](../../glossary.md#term-space-definition--space-definition) in the technical space, named in the [capability](../../../core/glossary.md#term-capability--capability)'s configuration, whose scope selects the space's pages. `LDOC`'s rules and the space's own bind on those pages, and [validation](../../../core/glossary.md#term-validation--validation) holds the places' assignment to that scope.

**Minimal guarantees:**

- A refused [stamp](../../../core/glossary.md#term-stamp--stamp) puts back every file it wrote, or names each it could not ([REQ-023](../../requirements/quality/REQ-023-refused-stamp-writes-nothing.md)).
- The stamp writes no [space definition](../../glossary.md#term-space-definition--space-definition) that exists, and no other space's definition. It writes nothing of the [backbone configuration](../../../core/glossary.md#term-backbone-configuration--backbone-configuration) itself, which only `pkit config set` writes, under its own consent ([DEC-001 point 2](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#2-definitions-kept-apart-from-content)).
- The stamp writes only what living-docs DEC-001 point 2 names it the writer of, so it meets [core:REQ-002](../../../core/requirements/functional/REQ-002-project-owned-writers.md).
- [Validation](../../../core/glossary.md#term-validation--validation) changes no file, needs no network and answers the same for the same state, meeting [core:REQ-005](../../../core/requirements/quality/REQ-005-reading-writes-nothing.md) and [core:REQ-007](../../../core/requirements/constraints/REQ-007-offline-same-answer.md) (`validate.py`).
- A later change of root moves no space definition, since the definitions location is recorded on first use ([COR-049 point 5](../../../../../.pkit/decisions/core/COR-049-documentation-roots.md#5-a-derived-location-is-recorded-when-it-is-first-used) and [core:REQ-014](../../../core/requirements/functional/020-set-up/REQ-014-root-change-moves-nothing.md)).
