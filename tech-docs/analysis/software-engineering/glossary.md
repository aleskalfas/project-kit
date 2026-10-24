---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-adapter, name: adapter}
      - {id: TERM-agent-definition, name: agent definition}
      - {id: TERM-anchor, name: anchor}
      - {id: TERM-answer, name: answer}
      - {id: TERM-artefact, name: artefact}
      - {id: TERM-base, name: base}
      - {id: TERM-capability, name: capability}
      - {id: TERM-change, name: change}
      - {id: TERM-change-check, name: change check}
      - {id: TERM-debt, name: debt}
      - {id: TERM-decision-record, name: decision record}
      - {id: TERM-default-branch, name: default branch}
      - {id: TERM-finding, name: finding}
      - {id: TERM-head, name: head}
      - {id: TERM-methodology, name: methodology}
      - {id: TERM-project, name: project}
      - {id: TERM-pull-request, name: pull request}
      - {id: TERM-reviewer, name: reviewer}
      - {id: TERM-whole-repository-check, name: whole-repository check}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Build my change with an agent that writes the change's code to my project's own conventions, read from wherever I keep them.
          - Decide each answer the change check did not ask of my change, from its words in the agent's hand-off, before it is written.
      - id: ACT-ai-agent
        name: AI agent
      - id: ACT-merge-authoriser
        name: Merge authoriser
        needs:
          - Have a reviewer other than their writer check a change's answers, so no merge I authorise rests on an answer that does not hold.
  - analysis: project-management
    version: 2.0.0
    terms:
      - {id: TERM-merge-gate, name: merge gate}
      - {id: TERM-required-reviewer, name: required reviewer}
      - {id: TERM-verdict, name: verdict}
TERM-code-review-panel:
  name: code-review panel
  status: active
  definition: "set of three reviewer agents software-engineering ships to judge a pull request's correctness, security and documentation, each a required reviewer of every change that meets its condition"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-engineering/review-contributions.yaml
          - .pkit/capabilities/software-engineering/agents/code-reviewer.md
          - .pkit/capabilities/software-engineering/agents/security-reviewer.md
          - .pkit/capabilities/software-engineering/agents/docs-reviewer.md
        record:
          - software-engineering:DEC-002#1
          - software-engineering:DEC-002#3
          - project-management:DEC-032#D1
TERM-conventions-corpus:
  name: conventions corpus
  status: active
  definition: set of a project's own coding standards, kept where the project names it, which the agents that write and review its code read
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-engineering/agents/software-engineer.md
        record:
          - software-engineering:DEC-001#2
          - software-engineering:DEC-001#4
          - software-engineering:DEC-002#4
          - ADR-013
          - COR-001
          - COR-010
      revalidated:
        at: 2026-10-20T01:37:23Z
        outcome: unchanged
        unchanged-because: It moved into software-engineering's analysis, whose use case UC-001 alone uses it, with its definition, example and distinctions as they were. It gains COR-001 and COR-010, the records behind the core's term project, which its definition names.
TERM-hand-off:
  name: hand-off
  status: active
  definition: "report an AI agent gives the person it works for as it passes a change on, saying what it did and what it leaves that person to decide"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-engineering/agents/software-engineer.md
        record:
          - software-engineering:DEC-001#4
          - COR-050#3
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than software-engineering's floor, 1.0.0.
  - **Term:** [adapter](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-adapter--adapter)
  - **Term:** [agent definition](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-agent-definition--agent-definition)
  - **Term:** [anchor](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-anchor--anchor)
  - **Term:** [answer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-answer--answer)
  - **Term:** [artefact](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-artefact--artefact)
  - **Term:** [base](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-base--base)
  - **Term:** [capability](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-capability--capability)
  - **Term:** [change](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change--change)
  - **Term:** [change check](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change-check--change-check)
  - **Term:** [debt](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-debt--debt)
  - **Term:** [decision record](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-decision-record--decision-record)
  - **Term:** [default branch](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-default-branch--default-branch)
  - **Term:** [finding](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-finding--finding)
  - **Term:** [head](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-head--head)
  - **Term:** [methodology](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-methodology--methodology)
  - **Term:** [project](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project--project)
  - **Term:** [pull request](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-pull-request--pull-request)
  - **Term:** [reviewer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-reviewer--reviewer)
  - **Term:** [whole-repository check](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-whole-repository-check--whole-repository-check)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Build my change with an agent that writes the change's code to my project's own conventions, read from wherever I keep them.
    - Decide each answer the change check did not ask of my change, from its words in the agent's hand-off, before it is written.
  - **Actor:** [AI agent](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-ai-agent.md)
  - **Actor:** [Merge authoriser](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-merge-authoriser.md)
    - Have a reviewer other than their writer check a change's answers, so no merge I authorise rests on an answer that does not hold.
- **From project-management at 2.0.0:** its terms of reviewing a pull request and merging it. No release holds project-management's analysis yet, so the links name the next release, 2.0.0, rather than software-engineering's floor of project-management, 0.54.0.
  - **Term:** [merge gate](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/project-management/glossary.md#term-merge-gate--merge-gate)
  - **Term:** [required reviewer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/project-management/glossary.md#term-required-reviewer--required-reviewer)
  - **Term:** [verdict](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/project-management/glossary.md#term-verdict--verdict)

## TERM-code-review-panel — code-review panel

**Example:** a pull request whose diff changes a script needs the approval of the whole code-review panel. One that changes only documents, and closes an issue with a `type`, needs the `docs-reviewer` alone.

**Distinctions:**

- **The core's reviewers:** the `critic`, the `architect` and the other reviewer agents the core ships. They judge a draft or a diff against the methodology's disciplines and rules, and none judges a change's correctness or its security (COR-024).
- **The `pm-reviewer`:** project-management's reviewer, which judges a pull request against project-management's conventions, never its code (software-engineering DEC-002).
- **The `software-engineer` agent:** it writes the code the panel judges, and posts no verdict (software-engineering DEC-001 point 1).

## TERM-conventions-corpus — conventions corpus

**Example:** the `software-engineer` agent reads the conventions corpus before it writes a change's code, and checks its own diff against it.

**Distinctions:**

- **The methodology's conventions:** conventional commits, branch names and the no-shared-files invariant, which bind every project. The `convention-compliance-reviewer` checks them, and never reads the corpus (software-engineering DEC-001 point 4).
- **The reviewers' knowledge:** what each code-review agent knows of any project. The project's own rules come from the corpus alone (software-engineering DEC-002 point 4).

## TERM-hand-off — hand-off

**Example:** the `software-engineer` agent's hand-off says that the change wrote answers. It also names a revalidation of a document the change check did not flag, with its words, for the developer to decide.

**Distinctions:**

- **A process's hand-off:** the point where one process's subject passes to another process, which a connection may declare checkable (COR-042). It is no report to a person.
- **The pull request's description:** what the change's author writes for its reviewers and for the person who authorises the merge. A hand-off goes to the person the agent works for.
