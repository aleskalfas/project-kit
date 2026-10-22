# Overview of the analysis of software-engineering

<!-- pkit:overview reads=4 fingerprint=sha256:2265cc3ec7b93ec13f5ee3d331b4850e34d02b18b6c787cf50a6b5a65be663e5 -->

No record states what software-engineering is for yet. Write one with `pkit new decision`, and name it as `purpose` in the entry of software-engineering under `analyses` in `.pkit/capabilities/software-analysis/project/config.yaml`.

This analysis covers software-engineering, and builds on the analysis of core.

## Use cases

- [UC-001 — Build my change under my project's conventions](../use-case-model/use-cases/UC-001-build-under-conventions.md)

## Reference

### Who takes part

| Actor | Who they are | Areas they act in |
| --- | --- | --- |
| core:ACT-ai-agent — AI agent | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |
| core:ACT-developer — Developer | An actor of the analysis of core, which the head of the [glossary](../glossary.md) lists. | [the use cases](#use-cases) |

### Concepts

The [glossary](../glossary.md) defines each term.

### Use cases and their actors

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

---

The command `pkit analysis overview` writes this page from the analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).
