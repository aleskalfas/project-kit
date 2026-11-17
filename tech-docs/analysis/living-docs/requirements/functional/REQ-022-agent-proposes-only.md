---
id: REQ-022
title: The living-docs agent proposes each edit, and applies none
status: active
statement: The living-docs agent changes no tracked file and runs no command that writes an answer, so each edit it drafts waits for a person.
measure: Every file the agent writes lies in the agent workspace, or in the workspace the brief of a run a command starts names. Its one other write is a reader-review posted as a pull-request comment, where the person asks for one and names the pull request.
applies-to: "The living-docs agent in each of its intents: a fix, a reader-review, an onboarding plan, and a run a command starts."
obligation: v1:sha256:eff3622e466716adcc571dc871f66afb20c92552c6de282b34ace12e2cfb575a
actors:
  - core:ACT-developer
  - core:ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        - tests/test_living_docs_agent.py
      record:
        - living-docs:DEC-001
        - living-docs:DEC-001#5
        - living-docs:DEC-001#6
        - living-docs:DEC-001#8
        - COR-050#3
        - COR-062#1
        - ADR-060#6
        - COR-009
        - ADR-061#3
        - PRJ-002#D1
        - PRJ-002#D2
        - COR-050#6
        - COR-050#9
        - COR-051#4
        - COR-066#1
        - COR-066#2
        - COR-001
        - COR-010
        - COR-053#8
        - COR-059#3
---

# REQ-022 · Functional · The living-docs agent proposes each edit, and applies none

**Verified by:** A test finds that the [agent definition](../../../core/glossary.md#term-agent-definition--agent-definition) grants Read, Glob, Grep, Bash and Write alone, and owns no path. So it has no tool that edits a file in place, and none that asks the person. Tests of its text find that it names each command that writes an [answer](../../../core/glossary.md#term-answer--answer) and runs none, and that its [storyboard](../../../core/glossary.md#term-storyboard--storyboard) hands over no consent. In a session, nothing at run time confines the agent's Write to the [agent workspace](../../../core/glossary.md#term-agent-workspace--agent-workspace) ([ADR-060 point 6](../../../../architecture/decisions/ADR-060-path-scoped-workspace-allow.md#6-realised-by-the-hook-never-as-a-settings-rule)), and no test runs the agent.

**Rationale:** An agent that rewrites pages directly will eventually rewrite them wrongly. It will misjudge an ambiguous file's audience, or fix a [page](../../glossary.md#term-page--page) to match a regression. [Proposals](../../glossary.md#term-proposal--proposal) that cite their evidence, reviewed by a person, keep speed without giving up judgement ([living-docs DEC-001](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md)). An [answer](../../../core/glossary.md#term-answer--answer) on a page is a person's decision too ([COR-050 point 3](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation) and [COR-062 point 1](../../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#1-answers-live-in-answer-files)).
