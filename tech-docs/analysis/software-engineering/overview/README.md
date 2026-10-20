# Overview of the analysis of software-engineering

<!-- pkit:overview reads=1 fingerprint=sha256:dd22a8f5cdbb1a2543ac52487d70be85f927588e4fa4537b31332c03401acae6 -->

What the analysis of software-engineering holds, in the order it is built: its concepts, its actors, its requirements, its use cases area by area, and its journeys. The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).

## Concepts

The [glossary](../glossary.md) defines each term.

## Use cases

- [UC-001 — Build my change under my project's conventions](../use-case-model/use-cases/UC-001-build-under-conventions.md)

## Use cases and their actors

```mermaid
flowchart LR
  accTitle: The use cases and their actors
  accDescr: The system's boundary holds 1 use case, and 2 actors stand around it. An arrow joins each use case to the actor whose goal it is, and a line joins it to each other actor who takes part.
  core_ACT_ai_agent["core:ACT-ai-agent"]
  core_ACT_developer["core:ACT-developer"]
  subgraph boundary["The system"]
    UC_001(["UC-001 — Build my change under my project's conventions"])
  end
  core_ACT_ai_agent --- UC_001
  core_ACT_developer --> UC_001
```
