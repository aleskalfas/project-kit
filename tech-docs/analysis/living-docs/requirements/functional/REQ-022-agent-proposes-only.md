---
id: REQ-022
title: The living-docs agent proposes each change, and applies none
status: active
statement: The living-docs agent changes no tracked file and runs no friction writer, so each change it drafts waits for a person to apply it.
measure: Every file the agent writes lies in the agent workspace, or in the workspace a fixer run's brief names. Its one other write is a reader-review posted as a pull-request comment, where the person asks for one and names the pull request.
applies-to: "The living-docs agent in each of its intents: a fix, a reader-review, an onboarding plan, and a run a command starts, in which nobody can answer it."
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
        - living-docs:DEC-001#5
        - living-docs:DEC-001#6
        - living-docs:DEC-001#8
        - COR-050#3
---

# REQ-022 · Functional · The living-docs agent proposes each change, and applies none

**Verified by:** A test finds that the [agent definition](../../../core/glossary.md#term-agent-definition--agent-definition) grants Read, Glob, Grep, Bash and Write alone, and owns no path. So it has no tool that edits a file in place, and none that asks the person. Tests of its text find that it names each [friction](../../../core/glossary.md#term-friction--friction) writer and runs none, and that its storyboard hands over no consent. Nothing confines its Write or its Bash to the workspace at run time, and no test runs the agent.

**Rationale:** An agent that rewrites pages directly will eventually rewrite them wrongly. It will misjudge an ambiguous file's audience, or fix a [page](../../glossary.md#term-page--page) to match a regression. [Proposals](../../glossary.md#term-proposal--proposal) that cite their evidence, reviewed by a person, keep speed without giving up judgement ([living-docs DEC-001](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md)). The [answer](../../../core/glossary.md#term-answer--answer) a page carries is a person's decision too ([COR-050 point 3](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).
