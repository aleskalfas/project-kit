# Overview of the analysis of core

<!-- pkit:overview reads=1 fingerprint=sha256:11c39f795e2eaaac1bfdccbf747ce5d3b0d69d59252472cc51e1027805d5711e -->

What the analysis of core holds, in the order it is built: its concepts, its actors, its requirements, its use cases area by area, and its journeys. The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).

## Concepts

The [glossary](../glossary.md) defines each term.

Each view of the domain model explains a group of related concepts:

- [VIEW-the-system-and-its-methodology — The system and its methodology](../domain-model/010-the-system-and-its-methodology.md): A way of working that only a few people know cannot be handed on, and one written as loose prose cannot be trusted (COR-007, COR-051). Each choice needs its reasons recorded, and each part that others cite needs a name that never moves (COR-025, COR-051, COR-058). Nothing should bind before a review accepts it (COR-051). The methodology also works inside sessions that another tool hosts, and relies on behaviour it cannot set (COR-047).
- [VIEW-parts-of-the-system — Parts of the system, and projects](../domain-model/020-parts-of-the-system.md): The system has parts that work only together, and parts that can move alone (COR-010). Whoever takes up a newer version of a part needs to know whether it breaks what works (COR-010). The methodology's content must reach more than one harness, with each kind of content in a home of its own (COR-006). It must also enter repositories that already hold files (COR-017).
- [VIEW-capabilities-areas-and-connection-points — Capabilities, areas and connection points](../domain-model/030-capabilities-areas-and-connection-points.md): Some disciplines suit only some projects, yet forcing them on every project is wrong, and copying them into each loses their reuse (COR-017). A component can also fail without a word when what it builds on changes incompatibly (COR-030). Other components must help each other without either depending on the other (COR-052, COR-053). Every project also needs fixed homes, with declared layouts, for its kinds of content (COR-011).
- [VIEW-versions-and-copies — Versions and copies](../domain-model/040-versions-and-copies.md): A project holds copies of the methodology's files so improvements reach it (COR-001). It also needs a routine repair that rebuilds those copies, and moves no version (COR-059). If its files move to a newer version without the migrations between, it holds content they never reached, and nothing says so (COR-059).
- [VIEW-a-projects-own-files — A project's own files](../domain-model/050-a-projects-own-files.md): A project adds content of its own, which the methodology must never take away (COR-001). Yet some of its files need entries the methodology ships (COR-002). Overwriting such a file destroys the project's entries, and writing it only once misses later ones (COR-002). Facts that no part owns, such as the project's name, must not be guessed either (COR-048).
- [VIEW-changes-review-and-releases — Changes, review and releases](../domain-model/060-changes-review-and-releases.md): Work reaches the shared history in logical units, each best judged before it lands, while a fix is still cheap (COR-009, COR-050). A check that compares such a unit with the wrong state of the shared history asks another question, and its result still looks right (COR-054). Whoever hits a problem with the system needs a way to raise it with the distribution it came from (PRJ-008). A version should move only for what someone could break against, so that the number stays a signal (PRJ-002).
- [VIEW-artefacts-and-friction — Artefacts and friction](../domain-model/070-artefacts-and-friction.md): A document is true only against something, such as the code it explains or a decision it applies (COR-050). When that changes and the document does not, it goes stale, and a review of the edit seldom sees it (COR-050). Rules need the same tracking, and must reach only the artefacts meant for them (COR-051, COR-056).

## Actors

- [ACT-adopter — Adopter](../use-case-model/actors/ACT-adopter.md)
- [ACT-ai-agent — AI agent](../use-case-model/actors/ACT-ai-agent.md)
- [ACT-ci-pipeline — CI pipeline](../use-case-model/actors/ACT-ci-pipeline.md)
- [ACT-component-author — Component author](../use-case-model/actors/ACT-component-author.md)
- [ACT-developer — Developer](../use-case-model/actors/ACT-developer.md)
- [ACT-merge-authoriser — Merge authoriser](../use-case-model/actors/ACT-merge-authoriser.md)
- [ACT-methodology-maintainer — Methodology maintainer](../use-case-model/actors/ACT-methodology-maintainer.md)
- [ACT-operator — Operator](../use-case-model/actors/ACT-operator.md)
- [ACT-planner — Planner](../use-case-model/actors/ACT-planner.md)

## Areas

### 010-develop

The methodology exists and can be extended, in its own source repository: capabilities, adapters, and a project's own skills and agent definitions.

- [UC-014 — Develop the methodology in its source repository](../use-case-model/use-cases/010-develop/UC-014-develop-methodology.md)
- [UC-015 — Package a recurring discipline as a capability](../use-case-model/use-cases/010-develop/UC-015-package-capability.md)
- [UC-016 — Keep a capability I wrote in my own repository](../use-case-model/use-cases/010-develop/UC-016-keep-capability.md)
- [UC-017 — Give my capability roles, data points and processes others connect to](../use-case-model/use-cases/010-develop/UC-017-connect-capability.md)
- [UC-018 — Know my capability is ready to share](../use-case-model/use-cases/010-develop/UC-018-check-shareable.md)
- [UC-019 — Adapt the system to another harness](../use-case-model/use-cases/010-develop/UC-019-adapt-harness.md)
- [UC-020 — Turn recurring work into my project's own skill or agent definition](../use-case-model/use-cases/010-develop/UC-020-own-skill-or-agent.md)

### 030-change

A change to a project is checked, answered and landed, so what the project states stays true as it changes.

- [UC-002 — Answer what my change made stale](../use-case-model/use-cases/030-change/UC-002-answer-stale.md)
- [UC-003 — Declare what my change means for the next release](../use-case-model/use-cases/030-change/UC-003-declare-changeset.md)
- [UC-004 — Know before I push that my change passes my project's checks](../use-case-model/use-cases/030-change/UC-004-check-before-push.md)
- [UC-005 — Say what my document rests on](../use-case-model/use-cases/030-change/UC-005-anchor-document.md)
- [UC-006 — Make my merges wait on the system's checks](../use-case-model/use-cases/030-change/UC-006-gate-merges.md)
- [UC-007 — Resolve what the default branch left out of date](../use-case-model/use-cases/030-change/UC-007-resolve-debt.md)
- [UC-010 — Never ship a backbone change that breaks installed projects without the migration that carries them across](../use-case-model/use-cases/030-change/UC-010-migrate-backbone-change.md)
- [UC-011 — Carry the projects that installed my component across a breaking change of it](../use-case-model/use-cases/030-change/UC-011-migrate-component-change.md)

### 040-release

The backbone and each component are released on their own versions, so projects can move to them and pin them.

- [UC-008 — Release the backbone so adopters can upgrade and pin to it](../use-case-model/use-cases/040-release/UC-008-release-backbone.md)
- [UC-009 — Release my component on its own version](../use-case-model/use-cases/040-release/UC-009-release-component.md)

### 050-adopt

Another project takes the system in, keeps it current, and reports what goes wrong with it.

- [UC-012 — Report a problem with the system, and follow the report](../use-case-model/use-cases/050-adopt/UC-012-report-problem.md)
- [UC-013 — Receive adopters' reports, and link each to its fix](../use-case-model/use-cases/050-adopt/UC-013-link-reports.md)

## Chain of use cases

```mermaid
flowchart LR
  accTitle: The chain of use cases
  accDescr: The chain of 19 use cases in force, grouped by area in the order of the areas' numbers. An arrow runs from each producer a use case names in `after` to that use case, the environment among them. A dotted arrow comes from a producer in a later area, an alternative its use case's area does not build on. 2 solid arrows that other solid arrows imply are left out.
  environment(("The environment"))
  subgraph area_010_develop["010-develop"]
    UC_014(["UC-014 — Develop the methodology in its source repository"])
    UC_015(["UC-015 — Package a recurring discipline as a capability"])
    UC_016(["UC-016 — Keep a capability I wrote in my own repository"])
    UC_017(["UC-017 — Give my capability roles, data points and processes others connect to"])
    UC_018(["UC-018 — Know my capability is ready to share"])
    UC_019(["UC-019 — Adapt the system to another harness"])
    UC_020(["UC-020 — Turn recurring work into my project's own skill or agent definition"])
  end
  subgraph area_030_change["030-change"]
    UC_002(["UC-002 — Answer what my change made stale"])
    UC_003(["UC-003 — Declare what my change means for the next release"])
    UC_004(["UC-004 — Know before I push that my change passes my project's checks"])
    UC_005(["UC-005 — Say what my document rests on"])
    UC_006(["UC-006 — Make my merges wait on the system's checks"])
    UC_007(["UC-007 — Resolve what the default branch left out of date"])
    UC_010(["UC-010 — Never ship a backbone change that breaks installed projects without the migration that carries them across"])
    UC_011(["UC-011 — Carry the projects that installed my component across a breaking change of it"])
  end
  subgraph area_040_release["040-release"]
    UC_008(["UC-008 — Release the backbone so adopters can upgrade and pin to it"])
    UC_009(["UC-009 — Release my component on its own version"])
  end
  subgraph area_050_adopt["050-adopt"]
    UC_012(["UC-012 — Report a problem with the system, and follow the report"])
    UC_013(["UC-013 — Receive adopters' reports, and link each to its fix"])
  end
  UC_008 --> UC_008
  UC_012 --> UC_013
  UC_014 --> UC_002
  UC_014 --> UC_003
  UC_014 --> UC_004
  UC_014 --> UC_005
  UC_014 --> UC_006
  UC_014 --> UC_008
  UC_014 --> UC_010
  UC_014 --> UC_015
  UC_014 --> UC_019
  UC_015 --> UC_011
  UC_015 --> UC_016
  UC_015 --> UC_018
  UC_016 --> UC_017
  UC_019 --> UC_011
  UC_019 --> UC_016
  UC_019 --> UC_020
  environment --> UC_008
```

## Use cases and their actors

```mermaid
flowchart LR
  accTitle: The use cases and their actors
  accDescr: The system's boundary holds 19 use cases, and 9 actors stand around it. An arrow joins each use case to the actor whose goal it is, and a line joins it to each other actor who takes part.
  ACT_adopter["ACT-adopter — Adopter"]
  ACT_ai_agent["ACT-ai-agent — AI agent"]
  ACT_ci_pipeline["ACT-ci-pipeline — CI pipeline"]
  ACT_component_author["ACT-component-author — Component author"]
  ACT_developer["ACT-developer — Developer"]
  ACT_merge_authoriser["ACT-merge-authoriser — Merge authoriser"]
  ACT_methodology_maintainer["ACT-methodology-maintainer — Methodology maintainer"]
  ACT_operator["ACT-operator — Operator"]
  ACT_planner["ACT-planner — Planner"]
  subgraph boundary["The system"]
    UC_002(["UC-002 — Answer what my change made stale"])
    UC_003(["UC-003 — Declare what my change means for the next release"])
    UC_004(["UC-004 — Know before I push that my change passes my project's checks"])
    UC_005(["UC-005 — Say what my document rests on"])
    UC_006(["UC-006 — Make my merges wait on the system's checks"])
    UC_007(["UC-007 — Resolve what the default branch left out of date"])
    UC_008(["UC-008 — Release the backbone so adopters can upgrade and pin to it"])
    UC_009(["UC-009 — Release my component on its own version"])
    UC_010(["UC-010 — Never ship a backbone change that breaks installed projects without the migration that carries them across"])
    UC_011(["UC-011 — Carry the projects that installed my component across a breaking change of it"])
    UC_012(["UC-012 — Report a problem with the system, and follow the report"])
    UC_013(["UC-013 — Receive adopters' reports, and link each to its fix"])
    UC_014(["UC-014 — Develop the methodology in its source repository"])
    UC_015(["UC-015 — Package a recurring discipline as a capability"])
    UC_016(["UC-016 — Keep a capability I wrote in my own repository"])
    UC_017(["UC-017 — Give my capability roles, data points and processes others connect to"])
    UC_018(["UC-018 — Know my capability is ready to share"])
    UC_019(["UC-019 — Adapt the system to another harness"])
    UC_020(["UC-020 — Turn recurring work into my project's own skill or agent definition"])
  end
  ACT_adopter --> UC_006
  ACT_adopter --> UC_012
  ACT_adopter --- UC_013
  ACT_ai_agent --- UC_002
  ACT_ai_agent --- UC_007
  ACT_ai_agent --- UC_010
  ACT_ai_agent --- UC_011
  ACT_ai_agent --- UC_012
  ACT_ai_agent --- UC_014
  ACT_ai_agent --- UC_015
  ACT_ai_agent --- UC_017
  ACT_ai_agent --- UC_019
  ACT_ai_agent --- UC_020
  ACT_ci_pipeline --- UC_002
  ACT_ci_pipeline --- UC_003
  ACT_ci_pipeline --- UC_004
  ACT_ci_pipeline --- UC_006
  ACT_ci_pipeline --- UC_007
  ACT_ci_pipeline --- UC_008
  ACT_ci_pipeline --- UC_009
  ACT_ci_pipeline --- UC_010
  ACT_ci_pipeline --- UC_011
  ACT_component_author --> UC_009
  ACT_component_author --> UC_011
  ACT_component_author --> UC_015
  ACT_component_author --> UC_016
  ACT_component_author --> UC_017
  ACT_component_author --> UC_018
  ACT_component_author --> UC_019
  ACT_developer --> UC_002
  ACT_developer --> UC_003
  ACT_developer --> UC_004
  ACT_developer --> UC_005
  ACT_developer --> UC_007
  ACT_developer --> UC_020
  ACT_merge_authoriser --- UC_002
  ACT_methodology_maintainer --> UC_008
  ACT_methodology_maintainer --> UC_010
  ACT_methodology_maintainer --- UC_012
  ACT_methodology_maintainer --> UC_013
  ACT_methodology_maintainer --> UC_014
```
