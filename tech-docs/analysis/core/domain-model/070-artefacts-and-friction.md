---
id: VIEW-artefacts-and-friction
title: Artefacts and friction
status: active
explains:
  - TERM-anchor
  - TERM-dead-anchor
  - TERM-place
  - TERM-artefact
  - TERM-declared-surface
  - TERM-answer
  - TERM-revalidation-answer
  - TERM-deferral
  - TERM-revisit-entry
  - TERM-answer-file
  - TERM-friction
  - TERM-change-check
  - TERM-whole-repository-check
  - TERM-revalidation-point
  - TERM-debt
  - TERM-revisit-link
  - TERM-link-target
  - TERM-trigger-field
  - TERM-revisit
  - TERM-rule-set
  - TERM-method-rule-set
  - TERM-loaded-rule-set
  - TERM-rules-index
  - TERM-inheritance-pin
  - TERM-artefact-type
  - TERM-package-metadata
  - TERM-query-command
pkit:
  friction:
    anchors:
      record:
        - COR-014
        - COR-017
        - COR-021
        - COR-030
        - COR-050
        - COR-051
        - COR-053#3
        - COR-053#8
        - COR-054#3
        - COR-056
        - COR-062
        - COR-068
        - COR-070
        - COR-070#1
        - COR-070#2
        - COR-070#3
        - COR-070#4
        - COR-070#5
        - ADR-057
        - ADR-076#2
      artefact:
        - TERM-anchor
        - TERM-dead-anchor
        - TERM-place
        - TERM-artefact
        - TERM-declared-surface
        - TERM-answer
        - TERM-revalidation-answer
        - TERM-deferral
        - TERM-revisit-entry
        - TERM-answer-file
        - TERM-friction
        - TERM-change-check
        - TERM-whole-repository-check
        - TERM-revalidation-point
        - TERM-debt
        - TERM-revisit-link
        - TERM-link-target
        - TERM-trigger-field
        - TERM-revisit
        - TERM-rule-set
        - TERM-method-rule-set
        - TERM-loaded-rule-set
        - TERM-rules-index
        - TERM-inheritance-pin
        - TERM-artefact-type
        - TERM-package-metadata
        - TERM-query-command
---

# VIEW-artefacts-and-friction — Artefacts and friction

A document is true only against something, such as the code it explains or a decision it applies ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). When that changes and the document does not, it goes stale, and a review of the edit seldom sees it (COR-050). Rules need the same tracking, and must reach only the [artefacts](../glossary.md#term-artefact--artefact) meant for them ([COR-051](../../../../.pkit/decisions/core/COR-051-rule-sets.md), [COR-056](../../../../.pkit/decisions/core/COR-056-artefact-types.md)).

An artefact in a [place](../glossary.md#term-place--place) declares its anchors, the things that make it true. When one of them changes, the artefact has [friction](../glossary.md#term-friction--friction) until an [answer](../glossary.md#term-answer--answer) stands for the edit. A [change](../glossary.md#term-change--change) writes its answers in [answer files](../glossary.md#term-answer-file--answer-file) of its own, outside the artefacts, so they never conflict with another change's answers ([COR-062](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md)). The [change check](../glossary.md#term-change-check--change-check) finds the friction a change brings, and the [whole-repository check](../glossary.md#term-whole-repository-check--whole-repository-check) reports the [debt](../glossary.md#term-debt--debt) left on the [default branch](../glossary.md#term-default-branch--default-branch).

What an [anchor](../glossary.md#term-anchor--anchor) names is a path, a record or an artefact, or a part of one. What it stands on is what the checks compare between two states to tell whether the anchor changed ([COR-050 point 5](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#5-when-an-anchor-has-changed-and-what-answers-it)). An anchor on a record's [point](../glossary.md#term-point--point) names the point, but stands on the point's section and on what says whether and how the record binds.

Some anchors matter the other way too. A requirement anchors the test that verifies it, and a changed threshold can leave the test checking the old value, unflagged (COR-050). So a [component](../glossary.md#term-component--component) may declare a [revisit link](../glossary.md#term-revisit-link--revisit-link) on a place. An edit to an artefact's [trigger fields](../glossary.md#term-trigger-field--trigger-field) there then asks the change for a [revisit](../glossary.md#term-revisit--revisit) of each [link target](../glossary.md#term-link-target--link-target).

[Rule sets](../glossary.md#term-rule-set--rule-set) hold the rules artefacts must satisfy, and select the artefacts their rules bind on, by path or by [artefact type](../glossary.md#term-artefact-type--artefact-type). A component's [package metadata](../glossary.md#term-package-metadata--package-metadata) declares its places and its artefact types.

```mermaid
classDiagram
  accTitle: Artefacts and friction
  accDescr: A place holds artefacts, and gives most of them their artefact type. An artefact carries its anchors, and a dead anchor is one that resolves to nothing. An answer is on an artefact, and lives apart from it, in an answer file of the change that wrote it. A revalidation answer, a deferral and a revisit entry are answers. Friction is a finding on an artefact, and a revalidation answer or a deferral settles it. A revalidation answer sets its artefact's revalidation point, which the whole-repository check measures from. The change check finds friction. The whole-repository check reports debt, which is a finding too. Package metadata declares revisit links on places. A revisit link names trigger fields and takes link targets, which are anchors. The change check asks for a revisit of each link target, and a revisit entry may record it. A rule set holds rules, selects artefacts by artefact type, and names an inheritance pin for each set it inherits. A loaded rule set holds operational rules, and the rules index lists the loaded file of each installed capability's. A component ships package metadata and method rule sets. Its package metadata declares its places, its artefact types and its declared surface, and registers its query commands.
  class Place["Place"]
  class Artefact["Artefact"]
  class Anchor["Anchor"]
  Anchor : kind
  Anchor : value
  class DeadAnchor["Dead anchor"]
  class DeclaredSurface["Declared surface"]
  class Answer["Answer"]
  class RevalidationAnswer["Revalidation answer"]
  RevalidationAnswer : at
  RevalidationAnswer : outcome
  class Deferral["Deferral"]
  class RevisitEntry["Revisit entry"]
  class AnswerFile["Answer file"]
  class RevalidationPoint["Revalidation point"]
  class Friction["Friction"]
  class Finding["Finding"]
  class ChangeCheck["Change check"]
  ChangeCheck : mode
  class WholeRepositoryCheck["Whole-repository check"]
  class Debt["Debt"]
  Debt : kind
  class RevisitLink["Revisit link"]
  class LinkTarget["Link target"]
  class TriggerField["Trigger field"]
  class Revisit["Revisit"]
  class RuleSet["Rule set"]
  RuleSet : version
  RuleSet : scope
  class Rule["Rule"]
  class InheritancePin["Inheritance pin"]
  class MethodRuleSet["Method rule set"]
  class LoadedRuleSet["Loaded rule set"]
  class OperationalRule["Operational rule"]
  class RulesIndex["Rules index"]
  class ArtefactType["Artefact type"]
  class PackageMetadata["Package metadata"]
  class QueryCommand["Query command"]
  class Component["Component"]
  Place o-- Artefact : holds
  Place --> ArtefactType : gives
  Artefact "1" *-- "*" Anchor : carries
  DeadAnchor --|> Anchor
  Answer "*" ..> "1" Artefact : is on
  AnswerFile "1" *-- "*" Answer : holds
  RevalidationAnswer --|> Answer
  Deferral --|> Answer
  RevisitEntry --|> Answer
  Friction --|> Finding
  Friction ..> Artefact : is on
  RevalidationAnswer ..> Friction : settles
  Deferral ..> Friction : settles
  RevalidationAnswer --> RevalidationPoint : sets
  ChangeCheck --> Friction : finds
  WholeRepositoryCheck --> Debt : reports
  WholeRepositoryCheck ..> RevalidationPoint : measures from
  Debt --|> Finding
  PackageMetadata --> RevisitLink : declares on a place
  RevisitLink --> TriggerField : names
  RevisitLink --> LinkTarget : takes
  LinkTarget --|> Anchor
  ChangeCheck --> Revisit : asks for
  Revisit ..> LinkTarget : is owed for
  RevisitEntry ..> Revisit : records
  RuleSet *-- Rule : holds
  RuleSet ..> ArtefactType : may select by
  RuleSet "1" *-- "*" InheritancePin : names one for each set it inherits
  LoadedRuleSet *-- OperationalRule : holds
  RulesIndex --> LoadedRuleSet : lists the loaded file of each installed capability's
  Component --> PackageMetadata : ships
  Component --> MethodRuleSet : ships
  PackageMetadata --> Place : declares
  PackageMetadata --> ArtefactType : declares
  PackageMetadata --> DeclaredSurface : declares
  PackageMetadata --> QueryCommand : registers
```

```mermaid
flowchart LR
  accTitle: How an edit leaves an artefact or a link target behind, and how each is answered
  accDescr: A change edits what an anchor names, or an artefact's list of anchors, and the artefact has friction. The change check finds it. A revalidation answer in the change, updated or unchanged, clears the friction. A deferral clears it too, and leaves deferred debt on the default branch. Friction nobody answered stays on the default branch as stale debt. Two revalidation answers on one artefact made apart, neither reading the other, leave answered-apart debt until a revalidation answer reads both. The whole-repository check reports each kind of debt, and never fails. A change that edits a trigger field owes a revisit of each link target, which the change check asks for. A change to what the link target stands on, or a revisit entry, unchanged or deferred, meets the revisit. Otherwise the revisit stays unmet, and the link target is a finding of the change check.
  E([A change edits what an anchor names, or the list of anchors]) --> F[Friction on the artefact]
  F -->|the change check finds it| A{Answer in the change?}
  A -->|revalidation answer, updated or unchanged| CL[Friction cleared]
  A -->|deferral| DF["Friction cleared, deferred debt on the default branch"]
  A -->|none, and the change lands| SD[Stale debt on the default branch]
  CL -->|another change revalidated it apart, neither reading the other| AA["Answered-apart debt on the default branch"]
  DF -->|reported by| W["Whole-repository check, which never fails"]
  SD -->|reported by| W
  AA -->|reported by| W
  T([A change edits a trigger field of a revisit link]) --> RO[Revisit owed for each link target]
  RO -->|the change check asks for it| M{Met in the change?}
  M -->|what the link target stands on changed| RM[Revisit met]
  M -->|revisit entry, unchanged or deferred| RM
  M -->|neither| RF[Revisit unmet, the link target a finding of the change check]
```

## Anchor

Defined in [TERM-anchor](../glossary.md#term-anchor--anchor).

**Why:** A document goes stale when what it rests on changes, and only a recorded link to that ground lets a check notice ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). Declared, the link is a claim someone made, which a check can test, where an inferred one is guesswork (COR-050).

An anchor is a declared link from a document, or a collection entry, to what makes it true. That may be a path, a record, or another document or entry. It says: if this changes, check me. A page that anchors `src/project_kit/changesets.py` is asked whether it still holds when that file is edited.

**Attributes:**

- its kind ([COR-050 point 2](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#2-anchors)):
  - a path
  - a record, or one of its points
  - another [artefact](../glossary.md#term-artefact--artefact), or one of its sections, or its lead
  - a kind a [capability](../glossary.md#term-capability--capability) registers
- its value, written as its kind writes it, such as `COR-058#4` (COR-050 point 2)

**Relations:**

- An artefact carries it, in its `friction` block ([COR-050 point 1](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#1-artefacts)).
- A capability may register a kind of its own, with a command that resolves it (COR-050 point 2).

**States:** None.

**Always true:**

- An anchor that resolves to nothing is a [dead anchor](../glossary.md#term-dead-anchor--dead-anchor) ([COR-050 point 7](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#7-dead-anchors-excluded-paths-and-over-broad-anchors)).
- An anchor on its own artefact, or on a section of it, is a cycle, and an error ([COR-050 point 5](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#5-when-an-anchor-has-changed-and-what-answers-it)).

## Dead anchor

Defined in [TERM-dead-anchor](../glossary.md#term-dead-anchor--dead-anchor).

**Why:** A glob that matches nothing brings no [friction](../glossary.md#term-friction--friction), ever, and that silence would look like health ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)).

A dead anchor is an [anchor](../glossary.md#term-anchor--anchor) of an [artefact](../glossary.md#term-artefact--artefact) that resolves to nothing. A path whose glob matches no file is one, and so is a path that matches only excluded paths or [answer files](../glossary.md#term-answer-file--answer-file). A record anchor on a [point](../glossary.md#term-point--point) its record does not hold is one too.

**Attributes:**

- what resolves to nothing: a path matching no file, an id that does not resolve, or a missing point or section ([COR-050 point 7](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#7-dead-anchors-excluded-paths-and-over-broad-anchors))

**Relations:**

- It is an anchor of the artefact that carries it ([COR-050 point 2](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#2-anchors)).
- Both the [change check](../glossary.md#term-change-check--change-check) and the [whole-repository check](../glossary.md#term-whole-repository-check--whole-repository-check) find it (COR-050 point 7). The change check fails on one it can lay at the [change](../glossary.md#term-change--change), in enforcing mode ([COR-050 point 12](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#12-warning-or-enforcing-and-who-owns-which-finding)).
- A path anchor stands on no answer file, so one that matches only answer files is a dead anchor ([COR-062 point 2](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#2-the-answer-folder)).

**States:** None.

**Always true:**

- A dead anchor is an error, never silence (COR-050 point 7).
- An anchor on a retired point stands on nothing, and is no dead anchor, since the record says where the point went (COR-050 point 7).
- An anchor whose kind nothing installed resolves, or whose command gave no result, is reported apart from a dead anchor (COR-050 point 7).

## Place

Defined in [TERM-place](../glossary.md#term-place--place).

**Why:** Many files carry front matter that has nothing to do with anchors ([COR-050 point 1](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#1-artefacts)). The [backbone](../glossary.md#term-backbone--backbone) looks only in declared places, so it never misreads such a file (COR-050 point 1). The owner of a place also knows what its files are, and can declare that there ([COR-056](../../../../.pkit/decisions/core/COR-056-artefact-types.md)).

A place is a path or glob that the [project](../glossary.md#term-project--project) or a [component](../glossary.md#term-component--component) declares, within which the backbone looks for [artefacts](../glossary.md#term-artefact--artefact) that carry anchors. project-kit lists `.pkit/cli/README.md` among its places, so the backbone reads that page's anchors.

**Attributes:**

- its path or glob
- optionally an [artefact type](../glossary.md#term-artefact-type--artefact-type), which it gives to what it holds (COR-050 point 1, [COR-056 point 2](../../../../.pkit/decisions/core/COR-056-artefact-types.md#2-who-declares-it))

**Relations:**

- A component declares its places in its [package metadata](../glossary.md#term-package-metadata--package-metadata), and the project declares its places in its [backbone configuration](../glossary.md#term-backbone-configuration--backbone-configuration) (COR-050 point 1).
- It may lie inside a [documentation root](../glossary.md#term-documentation-root--documentation-root), and a root may hold files no place reads.

**States:** None.

**Always true:**

- The backbone looks for artefacts only in places (COR-050 point 1).
- A folder of [synced copies](../glossary.md#term-synced-copy--synced-copy) is never a place, or each [sync](../glossary.md#term-sync--sync) would read as [friction](../glossary.md#term-friction--friction) ([COR-050 point 14](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#14-project-settings)).

## Artefact

Defined in [TERM-artefact](../glossary.md#term-artefact--artefact).

**Why:** Descriptions of what the [system](../glossary.md#term-system--system) must do and documentation both go stale when what they rest on changes ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). [Components](../glossary.md#term-component--component) that must not depend on each other keep them, so the mechanism that finds staleness is shared (COR-050). An artefact is the unit it works on, and carries its own anchors ([COR-050 point 1](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#1-artefacts)).

An artefact is a document with front matter, or a keyed entry of a collection file, in a declared [place](../glossary.md#term-place--place). It carries its own anchors. Each entry of this analysis's glossary is one.

**Attributes:**

- its own fields, such as its id and its status, which belong to the component that defines it (COR-050 point 1)
- its `friction` block, which holds its anchors (COR-050 point 1)
- one [artefact type](../glossary.md#term-artefact-type--artefact-type), or none ([COR-056 point 1](../../../../.pkit/decisions/core/COR-056-artefact-types.md#1-what-a-type-is))

**Relations:**

- A place holds it (COR-050 point 1).
- It carries anchors (COR-050 point 1). Its answers, for edits to what the anchors name, lie in [answer files](../glossary.md#term-answer-file--answer-file) apart from it ([COR-050 point 3](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation), [COR-062 point 1](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#1-answers-live-in-answer-files)).
- A [decision record](../glossary.md#term-decision-record--decision-record) is an artefact only where a place holds it (COR-050 point 1).

**States:** None.

**Always true:**

- The [change check](../glossary.md#term-change-check--change-check) asks a [revalidation answer](../glossary.md#term-revalidation-answer--revalidation-answer) of a [change](../glossary.md#term-change--change) that moves it, by renaming its file or moving its entry (COR-050 point 3). It asks one too of a change to its own list of anchors ([COR-050 point 6](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#6-friction-in-two-checks)).
- An artefact with no anchors is unanchored: the [backbone](../glossary.md#term-backbone--backbone) reports it, and never fails on it ([COR-050 point 2](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#2-anchors)).

## Declared surface

Defined in [TERM-declared-surface](../glossary.md#term-declared-surface--declared-surface).

**Why:** Counting every file of the repository as needing a description would make the measure noise from the first day ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). It means something only against what someone said ought to be described (COR-050).

The declared surface is the paths that a [component](../glossary.md#term-component--component)'s [package metadata](../glossary.md#term-package-metadata--package-metadata), or the [project](../glossary.md#term-project--project)'s [backbone configuration](../glossary.md#term-backbone-configuration--backbone-configuration), names as what descriptions ought to cover. Each of its paths that no [artefact](../glossary.md#term-artefact--artefact) anchors is reported as uncovered. project-kit's backbone configuration lists `src/**` in it, under `friction.surface`.

**Attributes:**

- its paths, which the excluded paths narrow (COR-050 points [7](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#7-dead-anchors-excluded-paths-and-over-broad-anchors) and [8](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#8-two-measures-not-failures))

**Relations:**

- A component declares its surface in its package metadata, and the project declares it in its backbone configuration (COR-050 point 8).
- It leaves out the folder the [backbone](../glossary.md#term-backbone--backbone) keeps for answers ([COR-062 point 2](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#2-the-answer-folder)).

**States:** None.

**Always true:**

- Uncovered surface is a measure, which no check fails on (COR-050 point 8).

## Answer

Defined in [TERM-answer](../glossary.md#term-answer--answer).

**Why:** Whether an [artefact](../glossary.md#term-artefact--artefact) still holds after what it rests on changed is a judgement no tool can make ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). Kept in the repository, not in one tool's pull-request description, that judgement needs nothing else (COR-050). Kept in an [answer file](../glossary.md#term-answer-file--answer-file) only its own [change](../glossary.md#term-change--change) writes, it never conflicts with another change's answer on the same artefact ([COR-062](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md)).

An answer is a statement in an answer file, which one change adds to the folder the [backbone](../glossary.md#term-backbone--backbone) keeps for answers ([COR-062 point 1](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#1-answers-live-in-answer-files)). It settles an edit to what an artefact rests on, or a [revisit](../glossary.md#term-revisit--revisit) its [revisit links](../glossary.md#term-revisit-link--revisit-link) ask for. It is a [revalidation answer](../glossary.md#term-revalidation-answer--revalidation-answer), a [deferral](../glossary.md#term-deferral--deferral) or a [revisit entry](../glossary.md#term-revisit-entry--revisit-entry).

**Attributes:**

- its kind: a revalidation answer, a deferral or a revisit entry (COR-062 point 1)
- the artefact it is on, by its location, and the other answer files on that artefact that it read (COR-062 points 1 and [4](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#4-each-answer-names-what-it-read))

**Relations:**

- It lives in an answer file apart from its artefact, never in a [pull request](../glossary.md#term-pull-request--pull-request)'s description ([COR-050 point 6](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#6-friction-in-two-checks), COR-062 point 1).
- It replaces the answers of its kind on its artefact that it read ([COR-062 point 5](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#5-what-an-answer-replaces)).
- A revalidation answer or a deferral clears [friction](../glossary.md#term-friction--friction) ([COR-050 point 5](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#5-when-an-anchor-has-changed-and-what-answers-it)).
- A revisit entry answers for one [link target](../glossary.md#term-link-target--link-target) ([COR-050 point 16](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#16-a-link-may-ask-for-a-revisit-of-its-targets-when-its-source-changes)).
- The [change check](../glossary.md#term-change-check--change-check) lists every answer a change wrote, word for word, and a [reviewer](../glossary.md#term-reviewer--reviewer) works from that list ([COR-050 point 3](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).

**States:** None.

**Always true:**

- A change never rewrites an answer file its [base](../glossary.md#term-base--base) holds, so an answer that landed stays as it was written ([COR-062 point 3](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#3-a-change-adds-answer-files-and-rewrites-none-its-base-holds)).

## Revalidation answer

Defined in [TERM-revalidation-answer](../glossary.md#term-revalidation-answer--revalidation-answer).

**Why:** Why an [artefact](../glossary.md#term-artefact--artefact) still holds after a [change](../glossary.md#term-change--change) is the one part of the judgement that no tool can supply ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)).

A revalidation answer is a statement, in an [answer file](../glossary.md#term-answer-file--answer-file) of a change's own, that records an artefact's review against what changed under its anchors. Its outcome is `updated`, where the artefact's content changed with it, or `unchanged`, with why the artefact still holds. `pkit friction revalidate` writes one.

**Attributes:**

- its timestamp, `at`, which is new in every revalidation answer ([COR-050 point 3](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation))
- its outcome, `updated` or `unchanged`, and with `unchanged`, its `unchanged-because`: why the artefact still holds against this change (COR-050 point 3)
- the [deferrals](../glossary.md#term-deferral--deferral) it keeps, each with its deferral point ([COR-050 point 4](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#4-deferrals))

**Relations:**

- It is an [answer](../glossary.md#term-answer--answer), beside a deferral and a [revisit entry](../glossary.md#term-revisit-entry--revisit-entry) ([COR-062 point 1](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#1-answers-live-in-answer-files)).
- It clears the [friction](../glossary.md#term-friction--friction) on its artefact ([COR-050 point 5](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#5-when-an-anchor-has-changed-and-what-answers-it)).
- Its `at` sets its artefact's [revalidation point](../glossary.md#term-revalidation-point--revalidation-point) (COR-050 point 3).
- It replaces each revalidation answer on its artefact that it read, and each deferral it read that it does not keep ([COR-062 point 5](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#5-what-an-answer-replaces)).

**States:** None.

**Always true:**

- An `unchanged` revalidation answer says why the artefact still holds, in words that differ from each it read (COR-050 point 3, COR-062 point 5).
- Its outcome is a record of what happened, and is never read to work out friction (COR-050 point 3).
- Writing back an `at` the artefact carried before is no revalidation answer, and answers nothing (COR-050 point 3).
- A change that moves an artefact writes a revalidation answer on it (COR-050 point 3).
- Two revalidation answers on one artefact, neither of which read the other, were made apart. They are [debt](../glossary.md#term-debt--debt) until a revalidation answer that reads both judges their combined state ([COR-062 point 7](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#7-answers-made-apart-are-debt-not-a-conflict)).

## Deferral

Defined in [TERM-deferral](../glossary.md#term-deferral--deferral).

**Why:** A deferral is a judgement about one edit to what an [anchor](../glossary.md#term-anchor--anchor) stands on, and a later edit there is a new question ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)).

A deferral is an [answer](../glossary.md#term-answer--answer) that puts off one anchor's [friction](../glossary.md#term-friction--friction), as the anchor stood when the deferral was written. Its reason names the follow-up that will answer that friction. `pkit friction defer` writes one.

**Attributes:**

- the anchor it puts off, written as its kind and value, and its reason ([COR-050 point 4](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#4-deferrals))
- its deferral point, the commit that first introduced it, which rewording its reason does not move (COR-050 point 4)

**Relations:**

- It clears its anchor's friction, while what the anchor stands on is as it stood at the deferral point (COR-050 point 4).
- It leaves deferred [debt](../glossary.md#term-debt--debt) on the [default branch](../glossary.md#term-default-branch--default-branch), dated from its deferral point ([COR-050 point 9](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#9-debt-is-derived-from-git-never-kept-in-a-ledger)).
- A [revalidation answer](../glossary.md#term-revalidation-answer--revalidation-answer) may keep it, and it keeps its deferral point. Kept so, it answers no friction, since that revalidation answer answered what it put off (COR-050 point 4).
- It replaces only the deferral of its own anchor that it read, and keeps that one's deferral point (COR-062 points [5](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#5-what-an-answer-replaces) and [6](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#6-each-value-keeps-its-point-across-homes)).

**States:** None.

**Always true:**

- It holds only where its reason names an open follow-up, which a [reviewer](../glossary.md#term-reviewer--reviewer) checks ([COR-050 point 3](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).
- Writing one changes no `at`, so it is no revalidation answer (COR-050 point 4).
- Two deferrals of one anchor made apart each cover the anchor only as it stood at its own deferral point ([COR-062 point 7](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#7-answers-made-apart-are-debt-not-a-conflict)).

## Revisit entry

Defined in [TERM-revisit-entry](../glossary.md#term-revisit-entry--revisit-entry).

**Why:** What a [link target](../glossary.md#term-link-target--link-target) names may be no [artefact](../glossary.md#term-artefact--artefact), such as a test file, or a record the [project](../glossary.md#term-project--project) receives and cannot edit ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). So the reason is recorded among the answers on the [revisit link](../glossary.md#term-revisit-link--revisit-link)'s source, which is always an artefact (COR-050).

A revisit entry is an [answer](../glossary.md#term-answer--answer) that records, for one link target a [change](../glossary.md#term-change--change) was asked about, how the link target stands. Its outcome is `unchanged`, with why the link target still stands, or `deferred`, naming an open follow-up that will [revisit](../glossary.md#term-revisit--revisit) it. `pkit friction revisit` writes one.

**Attributes:**

- its link target, by the [anchor](../glossary.md#term-anchor--anchor)'s kind and value ([COR-050 point 16](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#16-a-link-may-ask-for-a-revisit-of-its-targets-when-its-source-changes))
- its outcome, `unchanged` or `deferred`, and its reason (COR-050 point 16)

**Relations:**

- It records a revisit among the source's answers, and meets that revisit (COR-050 point 16).
- It replaces only the entry for its own link target that it read ([COR-062 point 5](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#5-what-an-answer-replaces)).
- Only the [change check](../glossary.md#term-change-check--change-check) reads it. The [whole-repository check](../glossary.md#term-whole-repository-check--whole-repository-check), the [debt](../glossary.md#term-debt--debt) listing and the tool-written status never do (COR-050 point 16).

**States:** None.

**Always true:**

- It answers only where the change wrote its reason, one that differs from each entry it replaces (COR-050 point 16, COR-062 point 5).
- It changes no content, moves no [revalidation point](../glossary.md#term-revalidation-point--revalidation-point) and flags no dependant (COR-050 point 16).
- One revisit entry answers for a link target, whatever revisit links take it (COR-050 point 16).
- [Validation](../glossary.md#term-validation--validation) fails an entry that names no link target of the source's revisit links, and a second entry for one link target (COR-050 point 16).

## Answer file

Defined in [TERM-answer-file](../glossary.md#term-answer-file--answer-file).

**Why:** Two changes that answered on one [artefact](../glossary.md#term-artefact--artefact) rewrote the same lines of its block, so whichever landed second was in conflict ([COR-062](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md)). Git merges two changes cleanly where each adds a file that no other [change](../glossary.md#term-change--change) writes (COR-062).

An answer file is a document that one change adds to the folder the [backbone](../glossary.md#term-backbone--backbone) keeps for answers, and that no other change writes. It holds what the change settled on each artefact. A change that revalidates two pages names both in its answer file.

**Attributes:**

- its name, which no other change uses ([COR-062 point 1](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#1-answers-live-in-answer-files))
- for each artefact it answers, its location and the answers on it (COR-062 point 1). A document is named by its path, and an entry by its file's path, `#` and its id.

**Relations:**

- One change adds it, and may rewrite or remove it, since the change's [base](../glossary.md#term-base--base) does not hold it ([COR-062 point 3](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#3-a-change-adds-answer-files-and-rewrites-none-its-base-holds)).
- Both checks, the [debt](../glossary.md#term-debt--debt) listing and `pkit friction explain` read an artefact's answers from the answer files (COR-062 point 1).
- The folder that holds it is never a [place](../glossary.md#term-place--place), so no place reads an answer file as an artefact ([COR-062 point 2](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#2-the-answer-folder)).

**States:** None.

**Always true:**

- A change rewrites no answer file its base holds, and removes one only to prune or to revert (COR-062 point 3).
- No [anchor](../glossary.md#term-anchor--anchor) stands on an answer file (COR-062 point 2).
- No [sync](../glossary.md#term-sync--sync) reads or writes the folder that holds it (COR-062 point 2).

## Friction

Defined in [TERM-friction](../glossary.md#term-friction--friction).

**Why:** People forget to update what depends on what they changed, and nobody notices until a reader is misled ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). Friction marks each such [artefact](../glossary.md#term-artefact--artefact) at the edit that left it behind, while the fix is still cheap (COR-050).

Friction is a [finding](../glossary.md#term-finding--finding) that something an artefact rests on changed, with no [answer](../glossary.md#term-answer--answer) standing for it. What changed may be what an [anchor](../glossary.md#term-anchor--anchor) names, or the list of anchors. A [change](../glossary.md#term-change--change) that edits `src/project_kit/release.py` brings friction to `.pkit/release/README.md` until the change gives the page an answer.

**Attributes:**

- the artefact it is on, and what changed: an anchor's target, or the list of anchors (COR-050 points [5](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#5-when-an-anchor-has-changed-and-what-answers-it) and [6](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#6-friction-in-two-checks))

**Relations:**

- The [change check](../glossary.md#term-change-check--change-check) and the [whole-repository check](../glossary.md#term-whole-repository-check--whole-repository-check) each find it (COR-050 point 6).
- A [revalidation answer](../glossary.md#term-revalidation-answer--revalidation-answer) or a [deferral](../glossary.md#term-deferral--deferral) clears it (COR-050 point 5).
- Friction nobody answered stays on the [default branch](../glossary.md#term-default-branch--default-branch) as [debt](../glossary.md#term-debt--debt) ([COR-050 point 9](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#9-debt-is-derived-from-git-never-kept-in-a-ledger)).

**States:** None.

**Always true:**

- It is worked out from git on each run. A status a job writes back after a merge is never read for it (COR-050 points [3](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation) and [10](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#10-a-tool-written-status-on-separate-lines)).
- An edit undone before the later state brings none (COR-050 point 5).
- It never reads an [artefact type](../glossary.md#term-artefact-type--artefact-type) ([COR-056 point 5](../../../../.pkit/decisions/core/COR-056-artefact-types.md#5-limits)).

## Change check

Defined in [TERM-change-check](../glossary.md#term-change-check--change-check).

**Why:** The cheapest moment to fix a stale [artefact](../glossary.md#term-artefact--artefact) is the [change](../glossary.md#term-change--change) that made it stale, while its author is still at work ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)).

The change check compares a [head](../glossary.md#term-head--head) with its [base](../glossary.md#term-base--base). It finds the [friction](../glossary.md#term-friction--friction) and [dead anchors](../glossary.md#term-dead-anchor--dead-anchor) the diff brings, and lists every [answer](../glossary.md#term-answer--answer) the diff wrote. `pkit friction check` runs it.

**Attributes:**

- its mode: warning, where it reports and passes, or enforcing, where it fails ([COR-050 point 12](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#12-warning-or-enforcing-and-who-owns-which-finding))
- its base, the [default branch](../glossary.md#term-default-branch--default-branch) unless the run names another ([COR-054 point 3](../../../../.pkit/decisions/core/COR-054-default-branch.md#3-the-override-is-a-base-not-a-declaration))

**Relations:**

- It finds friction ([COR-050 point 6](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#6-friction-in-two-checks)).
- A [reviewer](../glossary.md#term-reviewer--reviewer) works from its list of answers ([COR-050 point 3](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).

**States:** None.

**Always true:**

- It reports each artefact that has an [anchor](../glossary.md#term-anchor--anchor) the change altered, and no answer in the same change (COR-050 point 6).
- An artefact new in the change counts as revalidated (COR-050 point 6).
- It reads the artefacts, never a [pull request](../glossary.md#term-pull-request--pull-request)'s description, so it runs the same anywhere (COR-050 point 6).

## Whole-repository check

Defined in [TERM-whole-repository-check](../glossary.md#term-whole-repository-check--whole-repository-check).

**Why:** What a [change](../glossary.md#term-change--change) leaves unanswered stays on the [default branch](../glossary.md#term-default-branch--default-branch) once it lands ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). The whole-repository check asks the [change check](../glossary.md#term-change-check--change-check)'s question of every [artefact](../glossary.md#term-artefact--artefact), so that state stays visible (COR-050).

The whole-repository check compares every artefact, at the latest commit, with its [revalidation point](../glossary.md#term-revalidation-point--revalidation-point) ([COR-050 point 6](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#6-friction-in-two-checks)). It reports, and never fails. `pkit friction check --all` runs it.

**Attributes:** None.

**Relations:**

- What it reports on the default branch is [debt](../glossary.md#term-debt--debt) ([COR-050 point 9](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#9-debt-is-derived-from-git-never-kept-in-a-ledger)).

**States:** None.

**Always true:**

- It never fails, since [friction](../glossary.md#term-friction--friction) already there holds no other work back ([COR-050 point 12](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#12-warning-or-enforcing-and-who-owns-which-finding)).

## Revalidation point

Defined in [TERM-revalidation-point](../glossary.md#term-revalidation-point--revalidation-point).

**Why:** If formatting or a moved file could advance an [artefact](../glossary.md#term-artefact--artefact)'s revalidation point, [friction](../glossary.md#term-friction--friction) could be cleared without anyone revalidating ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). So it moves only when someone writes a [revalidation answer](../glossary.md#term-revalidation-answer--revalidation-answer) on purpose (COR-050).

A revalidation point is the commit where an artefact's answers first carried the timestamp `at` they carry now. The checks measure from it what the artefact's anchors stand on. A page last revalidated in one commit has that commit as its revalidation point.

**Attributes:** None.

**Relations:**

- The latest revalidation answer on its artefact sets it, by that [answer](../glossary.md#term-answer--answer)'s `at` ([COR-050 point 3](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).
- The [whole-repository check](../glossary.md#term-whole-repository-check--whole-repository-check) compares each artefact, at the latest commit, with its revalidation point ([COR-050 point 6](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#6-friction-in-two-checks)).
- A value of `at` keeps its revalidation point when it moves to another home: an [answer file](../glossary.md#term-answer-file--answer-file), or an artefact's block ([COR-062 point 6](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#6-each-value-keeps-its-point-across-homes)).

**States:** None.

**Always true:**

- It is read from its artefact's file history, renames followed, back to where the file or the entry was last added (COR-050 point 3).
- Commits that do not descend from one another may each first carry the value. Each is then a revalidation point, and an [anchor](../glossary.md#term-anchor--anchor) has changed only where what it stands on differs at every one (COR-050 point 3).
- Which came first is read from the history, never from the timestamps (COR-050 point 3).
- An artefact with no `at` has as its revalidation point the commit that first introduced its block (COR-050 point 3).

## Debt

Defined in [TERM-debt](../glossary.md#term-debt--debt).

**Why:** An [artefact](../glossary.md#term-artefact--artefact) left out of date on the [default branch](../glossary.md#term-default-branch--default-branch), by [friction](../glossary.md#term-friction--friction) nobody answered or by a [deferral](../glossary.md#term-deferral--deferral), must stay in view ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). Derived from git on each run, debt never drifts the way a separate ledger would (COR-050).

Debt is a [finding](../glossary.md#term-finding--finding) of the [whole-repository check](../glossary.md#term-whole-repository-check--whole-repository-check), dated from the commit it originates in. It is stale, where a [change](../glossary.md#term-change--change) nobody answered left an artefact behind, or deferred, where a deferral put an [answer](../glossary.md#term-answer--answer) off. It is answered apart where two [revalidation answers](../glossary.md#term-revalidation-answer--revalidation-answer) on one artefact, neither of which read the other, left their combined state unjudged ([COR-062 point 7](../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#7-answers-made-apart-are-debt-not-a-conflict)).

**Attributes:**

- its kind, stale, deferred or answered apart ([COR-050 point 9](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#9-debt-is-derived-from-git-never-kept-in-a-ledger), COR-062 point 7)
- the commit it originates in, with its author and its date (COR-050 point 9)

**Relations:**

- The whole-repository check reports it (COR-050 point 9).
- Friction nobody answered becomes stale debt on the default branch (COR-050 point 9).

**States:** None.

**Always true:**

- No ledger keeps it: each run derives it from git again (COR-050 point 9).
- A deferral never expires on its own, and its age is shown ([COR-050 point 4](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#4-deferrals)).
- Answered-apart debt is never stale and fails nothing. The next revalidation answer that reads both clears it (COR-062 point 7).

## Revisit link

Defined in [TERM-revisit-link](../glossary.md#term-revisit-link--revisit-link).

**Why:** An [anchor](../glossary.md#term-anchor--anchor) flags only the [artefact](../glossary.md#term-artefact--artefact) that carries it ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). So a relaxed requirement leaves the test that verifies it, and the [decision record](../glossary.md#term-decision-record--decision-record) made to meet it, unvisited (COR-050). Asked at every edit of an artefact, each anchor would draw a reason written blindly (COR-050). So the [component](../glossary.md#term-component--component) that defines a kind of artefact declares which anchors of those artefacts bind both ways (COR-050).

A revisit link is a declaration a component makes on a [place](../glossary.md#term-place--place), in its [package metadata](../glossary.md#term-package-metadata--package-metadata). Editing chosen fields of an artefact there asks whether what chosen anchors of the artefact name still stands. software-analysis declares one on each of its requirement places, under `revisits`.

**Attributes:**

- the own fields that choose its [link targets](../glossary.md#term-link-target--link-target): one that lists them, or fields that list the anchors that stay out ([COR-050 point 16](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#16-a-link-may-ask-for-a-revisit-of-its-targets-when-its-source-changes))
- its [trigger fields](../glossary.md#term-trigger-field--trigger-field) (COR-050 point 16)

**Relations:**

- A component declares it on a place, in its package metadata (COR-050 point 16).
- Each artefact the place holds is its source. A source takes the revisit links of every place a component declares that matches its file at the [head](../glossary.md#term-head--head) (COR-050 point 16).
- It names trigger fields of its source, and takes link targets from its source's anchors (COR-050 point 16).

**States:** None.

**Always true:**

- No place asks for a [revisit](../glossary.md#term-revisit--revisit) unless a component declares a revisit link on it, so none does by default (COR-050 point 16).
- A [project](../glossary.md#term-project--project) declares no revisit link on its own places (COR-050 point 16).

## Link target

Defined in [TERM-link-target](../glossary.md#term-link-target--link-target).

**Why:** A field says which anchors a [revisit link](../glossary.md#term-revisit-link--revisit-link) takes ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). Taking every [anchor](../glossary.md#term-anchor--anchor) of one kind could not tell those anchors apart from the rest (COR-050). A requirement's record anchors may hold both the decisions it rests on and those made to meet it (COR-050).

A link target is an anchor of an [artefact](../glossary.md#term-artefact--artefact) that a revisit link takes. A requirement's anchor on the test that verifies it is a link target of the revisit link on its [place](../glossary.md#term-place--place).

**Attributes:**

- its anchor's kind and value, by which a [revisit entry](../glossary.md#term-revisit-entry--revisit-entry) names it ([COR-050 point 16](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#16-a-link-may-ask-for-a-revisit-of-its-targets-when-its-source-changes))

**Relations:**

- It is an anchor of the revisit link's source (COR-050 point 16).
- A value in a field that lists link targets names every anchor of the source that has it (COR-050 point 16).
- A [revisit](../glossary.md#term-revisit--revisit) is owed for it when an edit triggers its revisit link (COR-050 point 16). The revisit link must take it at the [base](../glossary.md#term-base--base) and at the [head](../glossary.md#term-head--head), and the link target must resolve at the head.

**States:** None.

**Always true:**

- A link target the [change](../glossary.md#term-change--change) adds to its revisit link owes nothing, since it was linked against the new state (COR-050 point 16).
- A link target that is a [dead anchor](../glossary.md#term-dead-anchor--dead-anchor) owes no revisit, since it is a [finding](../glossary.md#term-finding--finding) of its own already (COR-050 points [7](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#7-dead-anchors-excluded-paths-and-over-broad-anchors) and 16).
- [Validation](../glossary.md#term-validation--validation) fails a value that no anchor of the source has, in a field that lists link targets (COR-050 point 16).

## Trigger field

Defined in [TERM-trigger-field](../glossary.md#term-trigger-field--trigger-field).

**Why:** Only what matters should ask for a [revisit](../glossary.md#term-revisit--revisit), such as a requirement's statement and its threshold, never the wording of its rationale ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). A field keeps its name, while a [project](../glossary.md#term-project--project) may reword the labels and headings of a body (COR-050).

A trigger field is one of an [artefact](../glossary.md#term-artefact--artefact)'s own keys, an own field that a [revisit link](../glossary.md#term-revisit-link--revisit-link) names. Where it differs between the [base](../glossary.md#term-base--base) and the [head](../glossary.md#term-head--head), compared parsed, the revisit link is triggered. A requirement's `statement`, `measure` and `applies-to` are its trigger fields.

**Attributes:** None.

**Relations:**

- A revisit link names it, among its source's own fields ([COR-050 point 16](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#16-a-link-may-ask-for-a-revisit-of-its-targets-when-its-source-changes)).
- Its edit asks for a revisit of every [link target](../glossary.md#term-link-target--link-target) of that revisit link (COR-050 point 16).

**States:** None.

**Always true:**

- A field absent at one state and present at the other differs (COR-050 point 16).
- These sources trigger nothing (COR-050 point 16):
  - a source new in the [change](../glossary.md#term-change--change)
  - a source the change removes
  - a source under an excluded path at the head
- A move alone triggers nothing either (COR-050 point 16).

## Revisit

Defined in [TERM-revisit](../glossary.md#term-revisit--revisit).

**Why:** The question belongs to the [change](../glossary.md#term-change--change) that alters the source, so the [change check](../glossary.md#term-change-check--change-check) asks it ([COR-050](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md)). What a [link target](../glossary.md#term-link-target--link-target) names may be no [artefact](../glossary.md#term-artefact--artefact), such as a test file, so the reason is recorded among the source's answers (COR-050).

A revisit is the judgement a change owes, once it edits a [trigger field](../glossary.md#term-trigger-field--trigger-field), of whether one link target still stands. The change meets it by changing what the link target stands on, or by a [revisit entry](../glossary.md#term-revisit-entry--revisit-entry) among the source's answers. `pkit friction revisit` writes the entry.

**Attributes:**

- the link target it is owed for ([COR-050 point 16](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#16-a-link-may-ask-for-a-revisit-of-its-targets-when-its-source-changes))
- how the change met it: by changing what the link target stands on, or by a revisit entry, `unchanged` or `deferred` (COR-050 point 16)

**Relations:**

- A change that edits a trigger field owes it, for each link target of that [revisit link](../glossary.md#term-revisit-link--revisit-link) (COR-050 point 16).
- A revisit entry, an [answer](../glossary.md#term-answer--answer), records it among the source's answers (COR-050 point 16).
- The change check lists each link target the change revisited by changing what it stands on. A [reviewer](../glossary.md#term-reviewer--reviewer) checks that this edit meets the edit to the source (COR-050 points [3](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation) and 16).

**States:** A revisit is owed once the change edits a trigger field. It is met where what the link target stands on differs between the [base](../glossary.md#term-base--base) and the [head](../glossary.md#term-head--head). It is met too where a revisit entry the change wrote names the link target. Otherwise the revisit stays unmet, and the change check reports the link target as a [finding](../glossary.md#term-finding--finding) (COR-050 points [12](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#12-warning-or-enforcing-and-who-owns-which-finding) and 16).

```mermaid
stateDiagram-v2
  accTitle: The states of a revisit
  accDescr: A change that edits a trigger field owes a revisit of a link target. A change to what the link target stands on, or a revisit entry the change wrote, meets the revisit. With neither, the revisit stays unmet, and the change check reports the link target as a finding.
  [*] --> owed : the change edits a trigger field
  owed --> met : what the link target stands on changes, or a revisit entry names the link target
  owed --> unmet : the change check finds neither
```

**Always true:**

- Only the change check asks for a revisit (COR-050 point 16).

## Rule set

Defined in [TERM-rule-set](../glossary.md#term-rule-set--rule-set).

**Why:** Rules need the discovery, anchoring and drift detection that [artefacts](../glossary.md#term-artefact--artefact) already have ([COR-051](../../../../.pkit/decisions/core/COR-051-rule-sets.md)). Kept as a collection of artefacts, a rule set reuses that machinery, with no second copy of it (COR-051). A shared set says what to require, and each set that inherits it says where (COR-051).

A rule set is a collection file of rules that artefacts must satisfy. It has its own `version`, the rule sets it inherits, and any scope that selects the artefacts its rules bind on. `ANA` is project-kit's rule set for its analysis.

**Attributes:**

- its name and its `version` ([COR-051 point 2](../../../../.pkit/decisions/core/COR-051-rule-sets.md#2-a-rule-set-is-a-collection-of-artefacts))
- the rule sets it inherits, each at an [inheritance pin](../glossary.md#term-inheritance-pin--inheritance-pin), as in `WRITE@2` ([COR-051 point 7](../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind))
- a scope, by path or by [artefact type](../glossary.md#term-artefact-type--artefact-type), on a set of the [project](../glossary.md#term-project--project)'s own (COR-051 points 2 and [6](../../../../.pkit/decisions/core/COR-051-rule-sets.md#6-two-kinds-two-owners))

**Relations:**

- Each of its rules is an artefact of its own, whose answers to [friction](../glossary.md#term-friction--friction) lie in [answer files](../glossary.md#term-answer-file--answer-file) apart from the set (COR-051 point 2).
- Its scope selects artefacts by path or by artefact type (COR-051 point 2).
- A rule set the [backbone](../glossary.md#term-backbone--backbone) or a [component](../glossary.md#term-component--component) ships is a [method rule set](../glossary.md#term-method-rule-set--method-rule-set), which takes no scope (COR-051 point 6).

**States:** None.

**Always true:**

- A set takes every [rule](../glossary.md#term-rule--rule) of the sets it inherits unchanged (COR-051 point 7).

## Method rule set

Defined in [TERM-method-rule-set](../glossary.md#term-method-rule-set--method-rule-set).

**Why:** A scope on a shipped [rule set](../glossary.md#term-rule-set--rule-set) would bind every adopting [project](../glossary.md#term-project--project)'s [artefacts](../glossary.md#term-artefact--artefact), whether or not a set of the project's own inherits it ([COR-051](../../../../.pkit/decisions/core/COR-051-rule-sets.md)). That would take away a project's choice not to inherit the set (COR-051).

A method rule set is a collection file of rules that the [backbone](../glossary.md#term-backbone--backbone) or a [component](../glossary.md#term-component--component) ships and owns with itself. It takes no scope, and a project never edits it. `software-analysis:SAN` is one, which binds on project-kit's analysis through `ANA`.

**Attributes:**

- its component's name, with which it is cited, as in `software-analysis:SAN` ([COR-051 point 6](../../../../.pkit/decisions/core/COR-051-rule-sets.md#6-two-kinds-two-owners))

**Relations:**

- The backbone or a component ships it, owned and versioned with it, and [sync](../glossary.md#term-sync--sync) refreshes it (COR-051 point 6).
- Unless it is a [loaded rule set](../glossary.md#term-loaded-rule-set--loaded-rule-set), its rules bind only through a scoped set of the project's own that inherits it ([COR-051 point 7](../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind)).

**States:** None.

**Always true:**

- A project never edits a method rule set. Unless it is a loaded rule set, the project extends it by inheriting it (COR-051 point 6, [COR-068 point 1](../../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md#1-a-loaded-rule-set)).

## Loaded rule set

Defined in [TERM-loaded-rule-set](../glossary.md#term-loaded-rule-set--loaded-rule-set).

**Why:** [Operational rules](../glossary.md#term-operational-rule--operational-rule) were numbered, so a [rule](../glossary.md#term-rule--rule) inserted or removed renumbered those after it ([COR-068](../../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md)). Each citation of a moved rule then named another rule, and nothing said so (COR-068). [Rule sets](../glossary.md#term-rule-set--rule-set) already give permanent ids, statuses and origins, so operational rules are kept in sets of their own (COR-068).

A loaded rule set is a collection file of rules that bind on the work of sessions, never on an [artefact](../glossary.md#term-artefact--artefact). They bind on each session that loads a file generated from the set. It has no scope, inherits no set, and no set inherits it. The [backbone](../glossary.md#term-backbone--backbone)'s `OPS` is one, and `.pkit/rules/core.md` is generated from it.

**Attributes:**

- its name, such as `OPS`, and its `version`, which no [inheritance pin](../glossary.md#term-inheritance-pin--inheritance-pin) holds (COR-068 points [5](../../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md#5-a-version-that-no-pin-holds) and [6](../../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md#6-ids-origins-and-citations))
- its layer, the backbone's, an installed [capability](../glossary.md#term-capability--capability)'s or the [project](../glossary.md#term-project--project)'s ([COR-068 point 4](../../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md#4-which-sets-bind-where), [COR-070 point 4](../../../../.pkit/decisions/core/COR-070-capability-loaded-rules.md#4-rules-add-up-across-layers-and-none-loosens-another)):
  - **The backbone's:** the set `OPS`, whose rules are cited by their ids, such as [RS-OPS-008](../../../../.pkit/rule-sets/ops.md#rs-ops-008--pause-and-confirm-before-destructive-operations), or with their [component](../glossary.md#term-component--component), as `backbone:RS-OPS-008` (COR-068 point 6).
  - **A capability's:** the one loaded rule set an installed capability may ship. Its rules bind only where the capability is installed. In the backbone's set they would bind everywhere, and each project would have to write them again in its own ([COR-070](../../../../.pkit/decisions/core/COR-070-capability-loaded-rules.md)). They are cited by their ids with the capability's name, as in `software-engineering:RS-SWE-001` ([COR-070 point 1](../../../../.pkit/decisions/core/COR-070-capability-loaded-rules.md#1-a-capability-ships-at-most-one-loaded-set-and-its-loaded-file-travels-with-it)).
  - **The project's:** a set the project keeps of its own operational rules. Until it keeps one, they are a plain file, loaded as it stands and cited by number, as in project rule 4 ([COR-068 point 7](../../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md#7-a-projects-rules-not-yet-in-a-set)).

**Relations:**

- Its rules are operational rules. Each has a rule's permanent id, origin and status, and its number in the generated file is its id's number (COR-068 point 6).
- The file a session loads is generated from it where it is authored, and holds only its accepted rules ([COR-068 point 3](../../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md#3-the-loaded-file-is-generated-from-the-set-where-the-set-is-authored)).
- The backbone's binds in every project. A capability's binds in each project that installs the capability, and a project's binds in that project (COR-068 point 4).

**States:** None.

**Always true:**

- Its accepted rules bind wherever its file is loaded, with no rule set inheriting it ([COR-068 point 2](../../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md#2-where-its-accepted-rules-bind)).
- An operational rule that fits any project is in the backbone's loaded rule set ([COR-014](../../../../.pkit/decisions/core/COR-014-universal-applicability.md)). One that binds only where a capability is installed is in that capability's ([COR-070 point 5](../../../../.pkit/decisions/core/COR-070-capability-loaded-rules.md#5-a-rule-that-binds-only-with-a-capability-belongs-to-that-capability)).
- A capability's operational rule never loosens one of the backbone's, and a project's never loosens one of the backbone's or of a capability's. The backbone's layer is above a capability's, which is above the project's. Where two operational rules of different layers cannot both be kept, the upper layer's rule binds. Where two capabilities' operational rules clash, the session stops the step and reports the clash (COR-070 point 4).
- A citation by layer and number, such as "core rule 19", names the same rule while its loaded rule set stands (COR-068 point 6).

## Rules index

Defined in [TERM-rules-index](../glossary.md#term-rules-index--rules-index).

**Why:** The [backbone](../glossary.md#term-backbone--backbone)'s loaded file reaches a session through one include in the [project](../glossary.md#term-project--project)'s [instruction file](../glossary.md#term-instruction-file--instruction-file) ([COR-070](../../../../.pkit/decisions/core/COR-070-capability-loaded-rules.md)). A [capability](../glossary.md#term-capability--capability) is installed and uninstalled, so its loaded file must arrive and leave with it (COR-070).

A rules index is a generated file that lists the loaded file of each installed capability. The [harness](../glossary.md#term-harness--harness)'s instruction file includes it, beside the backbone's loaded file. project-kit's is `.pkit/rules/capabilities.md`, which its `CLAUDE.md` includes after `.pkit/rules/core.md`.

**Attributes:**

- a marker line, saying that the backbone renders it ([ADR-076 point 2](../../../architecture/decisions/ADR-076-capability-rules-index.md#2-the-backbone-renders-an-index-and-claudemd-includes-it))
- a line for each installed capability that ships a [loaded rule set](../glossary.md#term-loaded-rule-set--loaded-rule-set), in the order of their names (ADR-076 point 2)

**Relations:**

- A capability's [operational rules](../glossary.md#term-operational-rule--operational-rule) reach the sessions that load the instruction file through it, from each session's start ([COR-070 point 2](../../../../.pkit/decisions/core/COR-070-capability-loaded-rules.md#2-the-adapter-delivers-the-loaded-file-by-the-route-that-carries-cores-rules)).
- The backbone renders it whole wherever the lifecycle regenerates derivable state, a capability's [install](../glossary.md#term-install--install), upgrade and uninstall among them (ADR-076 point 2).
- The [adapter](../glossary.md#term-adapter--adapter) keeps the one line that includes it present in the instruction file, and inserts that line wherever it is absent (COR-070 point 2).

**States:** None.

**Always true:**

- It holds no [rule](../glossary.md#term-rule--rule) of its own (ADR-076 point 2).
- A project never edits it (ADR-076 point 2).
- Deleting its line opts no project out, since the adapter inserts the line wherever it is absent (ADR-076 point 2, [COR-070 point 3](../../../../.pkit/decisions/core/COR-070-capability-loaded-rules.md#3-installing-a-capability-accepts-its-loaded-set)).

## Inheritance pin

Defined in [TERM-inheritance-pin](../glossary.md#term-inheritance-pin--inheritance-pin).

**Why:** A set's rules are written against the rules it inherits as they were, and a breaking edit to those can silently invalidate them ([COR-051](../../../../.pkit/decisions/core/COR-051-rule-sets.md)). Pinning their major turns that into a visible review, not a silent drift (COR-051).

An inheritance pin is the major [version](../glossary.md#term-version--version) a [rule set](../glossary.md#term-rule-set--rule-set) names for each set it inherits, after the set's name and `@`, as in `WRITE@2`. While it is behind the set's current major, no inherited [rule](../glossary.md#term-rule--rule) binds through it.

**Attributes:** None.

**Relations:**

- A rule set names one in its `inherits` for each set it inherits ([COR-051 point 7](../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind)).
- A [loaded rule set](../glossary.md#term-loaded-rule-set--loaded-rule-set) has none, since no rule set inherits it ([COR-068 point 1](../../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md#1-a-loaded-rule-set)).

**States:** An inheritance pin is current while it names its set's current major. A new major of that set leaves it behind, until the [project](../glossary.md#term-project--project) reviews the new major and moves the pin (COR-051 point 7).

```mermaid
stateDiagram-v2
  accTitle: The states of an inheritance pin
  accDescr: An inheritance pin is current while it names its set's current major. A new major of that set leaves it behind. Once the project reviews the new major and moves the pin, it is current again.
  [*] --> current : a rule set inherits a set at its current major
  current --> behind : the inherited set reaches a new major
  behind --> current : the project reviews the new major and moves the pin
```

**Always true:**

- While an inheritance pin is behind its set, no rule binds through it, and [validation](../glossary.md#term-validation--validation) fails on the inheriting set (COR-051 point 7).
- One [artefact](../glossary.md#term-artefact--artefact) reached through two lines of inheritance that pin one set at different majors is a validation error (COR-051 point 7).
- A rule set that moves an inheritance pin to another major takes a new major of its own (COR-051 point 7).
- Only the project moves an inheritance pin, once it has reviewed the new major (COR-051 point 7).

## Artefact type

Defined in [TERM-artefact-type](../glossary.md#term-artefact-type--artefact-type).

**Why:** Selecting [artefacts](../glossary.md#term-artefact--artefact) by path alone cannot tell apart the different sorts one folder holds ([COR-056](../../../../.pkit/decisions/core/COR-056-artefact-types.md)). Inferring a sort from fields fails without a word, so the owner of a [place](../glossary.md#term-place--place) declares it there (COR-056).

An artefact type is the declared name of what a document or a collection entry is. The place holding the document's or the entry's file gives the type. The exceptions are a [rule](../glossary.md#term-rule--rule), which always takes `backbone:rule`, and a type that a kind field gates.

A [rule set](../glossary.md#term-rule-set--rule-set)'s scope may select by artefact type. The glossary's place gives each entry the type `software-analysis:term`.

**Attributes:**

- its name: a [component](../glossary.md#term-component--component)'s is qualified, such as `software-analysis:term`, and a [project](../glossary.md#term-project--project)'s is bare ([COR-056 point 1](../../../../.pkit/decisions/core/COR-056-artefact-types.md#1-what-a-type-is))

**Relations:**

- A place gives it to the artefacts it holds (COR-056 point 1). Where the type names a kind field, an artefact takes it only when it declares that kind ([COR-056 point 4](../../../../.pkit/decisions/core/COR-056-artefact-types.md#4-how-a-kind-field-gates-the-type)).
- A component declares its types in its [package metadata](../glossary.md#term-package-metadata--package-metadata) ([COR-056 point 2](../../../../.pkit/decisions/core/COR-056-artefact-types.md#2-who-declares-it)).
- A rule set's scope may select by it ([COR-051 point 2](../../../../.pkit/decisions/core/COR-051-rule-sets.md#2-a-rule-set-is-a-collection-of-artefacts)).

**States:** None.

**Always true:**

- An artefact has one type, or none (COR-056 point 1).
- [Friction](../glossary.md#term-friction--friction) never reads a type, so giving a place a type flags nothing ([COR-056 point 5](../../../../.pkit/decisions/core/COR-056-artefact-types.md#5-limits)).
- Every rule takes the type `backbone:rule`, whatever place holds it ([COR-056 point 3](../../../../.pkit/decisions/core/COR-056-artefact-types.md#3-how-the-backbone-resolves-it)).

## Package metadata

Defined in [TERM-package-metadata](../glossary.md#term-package-metadata--package-metadata).

**Why:** What a [component](../glossary.md#term-component--component) adds to the [backbone](../glossary.md#term-backbone--backbone) must be declared on purpose, not found by scanning its files ([COR-021](../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)). A scan would let a renamed file reshape the commands others rely on, without a word (COR-021).

Package metadata is the file a component ships that declares its [version](../glossary.md#term-version--version), its ranges and what it adds to the backbone. It may add places, types, [roles](../glossary.md#term-role--role), commands and [validators](../glossary.md#term-validator--validator). The `package.yaml` of `software-analysis` declares the glossary as a [place](../glossary.md#term-place--place).

**Attributes:**

- the component's name, kind and version, and its ranges: on the backbone, and on other [capabilities](../glossary.md#term-capability--capability) ([COR-017](../../../../.pkit/decisions/core/COR-017-capability-pattern.md), [COR-030](../../../../.pkit/decisions/core/COR-030-capability-dependencies.md))
- its commands (COR-021)
- its connections: the [connection points](../glossary.md#term-connection-point--connection-point) it defines and those it plugs into ([COR-053 point 3](../../../../.pkit/decisions/core/COR-053-connection-points.md#3-declared-in-package-metadata-in-one-block-named-for-the-functionality))
- its places, and its [artefact types](../glossary.md#term-artefact-type--artefact-type) ([COR-050 point 1](../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#1-artefacts), [COR-056 point 2](../../../../.pkit/decisions/core/COR-056-artefact-types.md#2-who-declares-it))

**Relations:**

- A component ships it (COR-017).
- It is no [manifest](../glossary.md#term-manifest--manifest): a manifest is what the [project](../glossary.md#term-project--project) recorded when it installed the component.

**States:** None.

**Always true:**

- A capability's connections can be read from it before the capability is installed ([COR-053 point 8](../../../../.pkit/decisions/core/COR-053-connection-points.md#8-discovery-a-plan-predicts-the-wiring-exactly)).
- It is the only source of a capability's commands (COR-021).

**Note:** COR-017 calls it the capability's manifest, a word the analysis keeps for the project's record.

## Query command

Defined in [TERM-query-command](../glossary.md#term-query-command--query-command).

**Why:** [Capabilities](../glossary.md#term-capability--capability) supply commands that the [backbone](../glossary.md#term-backbone--backbone)'s engines run, such as one that resolves a kind of [anchor](../glossary.md#term-anchor--anchor) ([ADR-057](../../../architecture/decisions/ADR-057-backbone-engines-and-command-limits.md)). The core sets the contract each keeps (ADR-057).

A query command is a script a [component](../glossary.md#term-component--component) registers for the backbone to run and read. A command that resolves a kind of anchor is one, and so are a command that fills a [data point](../glossary.md#term-data-point--data-point) and a [validator](../glossary.md#term-validator--validator). Its component declares it offline, read-only and deterministic, and the backbone bounds its time.

**Attributes:**

- its declaration, on its own entry among its component's commands ([ADR-057 point 3](../../../architecture/decisions/ADR-057-backbone-engines-and-command-limits.md#3-query-commands-declare-the-query-contract-the-engine-that-runs-one-enforces-the-bound-and-reads-the-answer-failing-closed)). It says that the command:
  - needs no network
  - changes nothing in the [project](../glossary.md#term-project--project)
  - gives the same output for the same inputs

**Relations:**

- Its component registers it in its [package metadata](../glossary.md#term-package-metadata--package-metadata) (ADR-057 point 3).
- The backbone runs it within a time bound of thirty seconds, and stops the whole of what it started past that bound (ADR-057 point 3).
- An abnormal exit, a timeout or a result the backbone cannot read gives no result, which is never read as an empty one. Each caller then does what its own [decision record](../glossary.md#term-decision-record--decision-record) decides for that case (ADR-057 point 3).

**States:** None.

**Always true:**

- The backbone runs no query command that lacks its declaration, and [validation](../glossary.md#term-validation--validation) of package metadata reports one (ADR-057 point 3).
- Its obligations are declared and trusted, never enforced. A project that needs a boundary confines the command where it runs it ([ADR-057 point 4](../../../architecture/decisions/ADR-057-backbone-engines-and-command-limits.md#4-what-nothing-here-confines-stated)).

## What is built on these concepts

Each concept below lists the use cases, journeys and requirements whose text links its term.

**Anchor:**

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-005 — Say what my document rests on](../use-case-model/use-cases/030-change/UC-005-anchor-document.md)
- [UC-006 — Make my merges wait on the system's checks](../use-case-model/use-cases/020-set-up/UC-006-gate-merges.md)
- [UC-007 — Resolve what the default branch left out of date](../use-case-model/use-cases/030-change/UC-007-resolve-debt.md)
- [REQ-006 · Quality · The backbone stops a command it runs for an anchor, a data point, validation or a process after thirty seconds](../requirements/quality/REQ-006-command-time-bound.md)
- [REQ-007 · Constraint · A command that resolves an anchor, fills a data point or joins validation is offline, read-only and deterministic](../requirements/constraints/REQ-007-offline-same-answer.md)
- [REQ-020 · Functional · A dead anchor is an error, never silence](../requirements/functional/030-change/REQ-020-dead-anchor-error.md)

**Dead anchor:**

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-005 — Say what my document rests on](../use-case-model/use-cases/030-change/UC-005-anchor-document.md)
- [UC-006 — Make my merges wait on the system's checks](../use-case-model/use-cases/020-set-up/UC-006-gate-merges.md)
- [UC-007 — Resolve what the default branch left out of date](../use-case-model/use-cases/030-change/UC-007-resolve-debt.md)
- [REQ-020 · Functional · A dead anchor is an error, never silence](../requirements/functional/030-change/REQ-020-dead-anchor-error.md)

**Place:**

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-005 — Say what my document rests on](../use-case-model/use-cases/030-change/UC-005-anchor-document.md)
- [UC-006 — Make my merges wait on the system's checks](../use-case-model/use-cases/020-set-up/UC-006-gate-merges.md)
- [UC-021 — Declare my project's backbone configuration once, and have it validated](../use-case-model/use-cases/020-set-up/UC-021-declare-backbone-configuration.md)
- [UC-038 — Author and extend my project's own rule sets](../use-case-model/use-cases/030-change/UC-038-author-rule-sets.md)
- [JRN-001 — Adopt the system](../use-case-model/journeys/JRN-001-adopt-system.md)
- [JRN-003 — Deliver a change](../use-case-model/journeys/JRN-003-deliver-change.md)

**Artefact:**

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-005 — Say what my document rests on](../use-case-model/use-cases/030-change/UC-005-anchor-document.md)
- [UC-006 — Make my merges wait on the system's checks](../use-case-model/use-cases/020-set-up/UC-006-gate-merges.md)
- [UC-007 — Resolve what the default branch left out of date](../use-case-model/use-cases/030-change/UC-007-resolve-debt.md)
- [UC-034 — Land my change on the default branch](../use-case-model/use-cases/030-change/UC-034-land-change.md)
- [UC-038 — Author and extend my project's own rule sets](../use-case-model/use-cases/030-change/UC-038-author-rule-sets.md)
- [UC-039 — Think a question through in a scratchpad note, and retire it](../use-case-model/use-cases/030-change/UC-039-think-in-scratchpad.md)
- [UC-040 — Have a drafted record or rule become binding only through my own review](../use-case-model/use-cases/030-change/UC-040-accept-through-review.md)
- [UC-041 — Keep each core record true for any project that adopts it](../use-case-model/use-cases/030-change/UC-041-keep-core-records-true.md)
- [UC-042 — Have my draft challenged and my diff checked against the conventions](../use-case-model/use-cases/030-change/UC-042-challenge-and-check.md)
- [UC-051 — Upgrade the system like a dependency](../use-case-model/use-cases/050-adopt/UC-051-upgrade-system.md)
- [UC-053 — Re-pin an inherited rule set once I have reviewed its new major](../use-case-model/use-cases/050-adopt/UC-053-repin-rule-set.md)
- [JRN-001 — Adopt the system](../use-case-model/journeys/JRN-001-adopt-system.md)
- [JRN-003 — Deliver a change](../use-case-model/journeys/JRN-003-deliver-change.md)
- [REQ-004 · Quality · A check never reads a missing result as one that found nothing](../requirements/quality/REQ-004-missing-answer-never-clean.md)
- [REQ-018 · Quality · A reading command of `pkit friction` prints the same document for the same state](../requirements/quality/030-change/REQ-018-same-json-same-state.md)
- [REQ-020 · Functional · A dead anchor is an error, never silence](../requirements/functional/030-change/REQ-020-dead-anchor-error.md)
- [REQ-030 · Functional · A choice in a version transition that needs a person is never taken silently](../requirements/functional/050-adopt/REQ-030-person-choice-never-silent.md)

**Declared surface:**

- [UC-021 — Declare my project's backbone configuration once, and have it validated](../use-case-model/use-cases/020-set-up/UC-021-declare-backbone-configuration.md)

**Answer:**

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-005 — Say what my document rests on](../use-case-model/use-cases/030-change/UC-005-anchor-document.md)
- [UC-006 — Make my merges wait on the system's checks](../use-case-model/use-cases/020-set-up/UC-006-gate-merges.md)
- [UC-007 — Resolve what the default branch left out of date](../use-case-model/use-cases/030-change/UC-007-resolve-debt.md)
- [UC-034 — Land my change on the default branch](../use-case-model/use-cases/030-change/UC-034-land-change.md)
- [JRN-003 — Deliver a change](../use-case-model/journeys/JRN-003-deliver-change.md)

**Revalidation answer:**

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-005 — Say what my document rests on](../use-case-model/use-cases/030-change/UC-005-anchor-document.md)
- [UC-007 — Resolve what the default branch left out of date](../use-case-model/use-cases/030-change/UC-007-resolve-debt.md)

**Deferral:**

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-034 — Land my change on the default branch](../use-case-model/use-cases/030-change/UC-034-land-change.md)
- [JRN-003 — Deliver a change](../use-case-model/journeys/JRN-003-deliver-change.md)

**Revisit entry:** None.

**Answer file:**

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-003 — Declare what my change means for the next release](../use-case-model/use-cases/030-change/UC-003-declare-changeset.md)
- [UC-006 — Make my merges wait on the system's checks](../use-case-model/use-cases/020-set-up/UC-006-gate-merges.md)
- [UC-007 — Resolve what the default branch left out of date](../use-case-model/use-cases/030-change/UC-007-resolve-debt.md)

**Friction:**

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-005 — Say what my document rests on](../use-case-model/use-cases/030-change/UC-005-anchor-document.md)
- [UC-006 — Make my merges wait on the system's checks](../use-case-model/use-cases/020-set-up/UC-006-gate-merges.md)
- [JRN-003 — Deliver a change](../use-case-model/journeys/JRN-003-deliver-change.md)

**Change check:**

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-004 — Know before I push that my change passes my project's checks](../use-case-model/use-cases/030-change/UC-004-check-before-push.md)
- [UC-005 — Say what my document rests on](../use-case-model/use-cases/030-change/UC-005-anchor-document.md)
- [UC-006 — Make my merges wait on the system's checks](../use-case-model/use-cases/020-set-up/UC-006-gate-merges.md)
- [UC-007 — Resolve what the default branch left out of date](../use-case-model/use-cases/030-change/UC-007-resolve-debt.md)
- [UC-034 — Land my change on the default branch](../use-case-model/use-cases/030-change/UC-034-land-change.md)
- [JRN-001 — Adopt the system](../use-case-model/journeys/JRN-001-adopt-system.md)
- [JRN-003 — Deliver a change](../use-case-model/journeys/JRN-003-deliver-change.md)
- [REQ-004 · Quality · A check never reads a missing result as one that found nothing](../requirements/quality/REQ-004-missing-answer-never-clean.md)
- [REQ-005 · Quality · A command that only reads or validates changes nothing in the project](../requirements/quality/REQ-005-reading-writes-nothing.md)
- [REQ-018 · Quality · A reading command of `pkit friction` prints the same document for the same state](../requirements/quality/030-change/REQ-018-same-json-same-state.md)
- [REQ-020 · Functional · A dead anchor is an error, never silence](../requirements/functional/030-change/REQ-020-dead-anchor-error.md)

**Whole-repository check:**

- [UC-007 — Resolve what the default branch left out of date](../use-case-model/use-cases/030-change/UC-007-resolve-debt.md)
- [JRN-003 — Deliver a change](../use-case-model/journeys/JRN-003-deliver-change.md)
- [REQ-004 · Quality · A check never reads a missing result as one that found nothing](../requirements/quality/REQ-004-missing-answer-never-clean.md)
- [REQ-018 · Quality · A reading command of `pkit friction` prints the same document for the same state](../requirements/quality/030-change/REQ-018-same-json-same-state.md)
- [REQ-019 · Functional · Each reading document of `pkit friction` carries its version, and a reader refuses one it does not know](../requirements/functional/030-change/REQ-019-reading-document-versioned.md)
- [REQ-020 · Functional · A dead anchor is an error, never silence](../requirements/functional/030-change/REQ-020-dead-anchor-error.md)

**Revalidation point:**

- [UC-007 — Resolve what the default branch left out of date](../use-case-model/use-cases/030-change/UC-007-resolve-debt.md)

**Debt:**

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-007 — Resolve what the default branch left out of date](../use-case-model/use-cases/030-change/UC-007-resolve-debt.md)
- [UC-034 — Land my change on the default branch](../use-case-model/use-cases/030-change/UC-034-land-change.md)
- [JRN-003 — Deliver a change](../use-case-model/journeys/JRN-003-deliver-change.md)
- [REQ-018 · Quality · A reading command of `pkit friction` prints the same document for the same state](../requirements/quality/030-change/REQ-018-same-json-same-state.md)

**Revisit link:** None.

**Link target:** None.

**Trigger field:** None.

**Revisit:** None.

**Rule set:**

- [UC-021 — Declare my project's backbone configuration once, and have it validated](../use-case-model/use-cases/020-set-up/UC-021-declare-backbone-configuration.md)
- [UC-023 — Add or remove a capability, and be told of a name collision](../use-case-model/use-cases/020-set-up/UC-023-add-or-remove-capability.md)
- [UC-038 — Author and extend my project's own rule sets](../use-case-model/use-cases/030-change/UC-038-author-rule-sets.md)
- [UC-049 — Install the system into my project with one command](../use-case-model/use-cases/050-adopt/UC-049-install-system.md)
- [UC-053 — Re-pin an inherited rule set once I have reviewed its new major](../use-case-model/use-cases/050-adopt/UC-053-repin-rule-set.md)
- [JRN-001 — Adopt the system](../use-case-model/journeys/JRN-001-adopt-system.md)
- [JRN-002 — Upgrade the system](../use-case-model/journeys/JRN-002-upgrade-system.md)
- [JRN-007 — Upgrade one capability, and re-pin its rule set](../use-case-model/journeys/JRN-007-upgrade-one-capability.md)
- [REQ-008 · Constraint · Until #1600 is done, the only area or adapter a change may add is `rule-sets`, and none may be removed](../requirements/constraints/010-develop/REQ-008-areas-held.md)

**Method rule set:**

- [UC-023 — Add or remove a capability, and be told of a name collision](../use-case-model/use-cases/020-set-up/UC-023-add-or-remove-capability.md)
- [UC-038 — Author and extend my project's own rule sets](../use-case-model/use-cases/030-change/UC-038-author-rule-sets.md)
- [UC-053 — Re-pin an inherited rule set once I have reviewed its new major](../use-case-model/use-cases/050-adopt/UC-053-repin-rule-set.md)
- [JRN-001 — Adopt the system](../use-case-model/journeys/JRN-001-adopt-system.md)
- [JRN-002 — Upgrade the system](../use-case-model/journeys/JRN-002-upgrade-system.md)
- [JRN-007 — Upgrade one capability, and re-pin its rule set](../use-case-model/journeys/JRN-007-upgrade-one-capability.md)
- [REQ-008 · Constraint · Until #1600 is done, the only area or adapter a change may add is `rule-sets`, and none may be removed](../requirements/constraints/010-develop/REQ-008-areas-held.md)

**Loaded rule set:**

- [UC-023 — Add or remove a capability, and be told of a name collision](../use-case-model/use-cases/020-set-up/UC-023-add-or-remove-capability.md)
- [UC-038 — Author and extend my project's own rule sets](../use-case-model/use-cases/030-change/UC-038-author-rule-sets.md)

**Rules index:**

- [UC-023 — Add or remove a capability, and be told of a name collision](../use-case-model/use-cases/020-set-up/UC-023-add-or-remove-capability.md)
- [UC-026 — Start every session with the project's rules loaded](../use-case-model/use-cases/020-set-up/UC-026-start-with-rules.md)
- [UC-049 — Install the system into my project with one command](../use-case-model/use-cases/050-adopt/UC-049-install-system.md)
- [JRN-001 — Adopt the system](../use-case-model/journeys/JRN-001-adopt-system.md)

**Inheritance pin:**

- [UC-038 — Author and extend my project's own rule sets](../use-case-model/use-cases/030-change/UC-038-author-rule-sets.md)
- [UC-040 — Have a drafted record or rule become binding only through my own review](../use-case-model/use-cases/030-change/UC-040-accept-through-review.md)
- [UC-042 — Have my draft challenged and my diff checked against the conventions](../use-case-model/use-cases/030-change/UC-042-challenge-and-check.md)
- [UC-053 — Re-pin an inherited rule set once I have reviewed its new major](../use-case-model/use-cases/050-adopt/UC-053-repin-rule-set.md)
- [JRN-002 — Upgrade the system](../use-case-model/journeys/JRN-002-upgrade-system.md)
- [JRN-007 — Upgrade one capability, and re-pin its rule set](../use-case-model/journeys/JRN-007-upgrade-one-capability.md)

**Artefact type:** None.

**Package metadata:**

- [UC-015 — Package a recurring discipline as a capability](../use-case-model/use-cases/010-develop/UC-015-package-capability.md)
- [UC-016 — Keep a capability I wrote in my own repository](../use-case-model/use-cases/010-develop/UC-016-keep-capability.md)
- [UC-017 — Give my capability roles, data points and processes others connect to](../use-case-model/use-cases/010-develop/UC-017-connect-capability.md)
- [UC-018 — Know my capability is ready to share](../use-case-model/use-cases/010-develop/UC-018-check-shareable.md)
- [UC-019 — Adapt the system to another harness](../use-case-model/use-cases/010-develop/UC-019-adapt-harness.md)
- [UC-024 — See what a capability would connect to before I install it](../use-case-model/use-cases/020-set-up/UC-024-see-capability-connections.md)
- [JRN-005 — Package a discipline as a capability, and make it ready to share](../use-case-model/journeys/JRN-005-package-and-share-capability.md)
- [JRN-009 — Release a breaking change of my component with its migration](../use-case-model/journeys/JRN-009-release-breaking-component-change.md)

**Query command:**

- [UC-049 — Install the system into my project with one command](../use-case-model/use-cases/050-adopt/UC-049-install-system.md)
- [UC-050 — Get a fresh clone ready to work with one sync](../use-case-model/use-cases/050-adopt/UC-050-ready-fresh-clone.md)
- [UC-054 — Upgrade one capability on its own](../use-case-model/use-cases/050-adopt/UC-054-upgrade-capability.md)
- [JRN-006 — Start working on a project on a new machine](../use-case-model/journeys/JRN-006-start-on-new-machine.md)
