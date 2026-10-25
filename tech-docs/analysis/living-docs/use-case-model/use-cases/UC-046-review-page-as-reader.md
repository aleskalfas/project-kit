---
id: UC-046
title: Have a page read as its declared reader would read it
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements:
  - REQ-022
after:
  - [UC-044, UC-047]
shortfalls:
  - at: "4a"
    issue: "#1812"
    record: living-docs:DEC-002#8
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        - .pkit/capabilities/living-docs/agents/living-docs/storyboard.md
        - .pkit/capabilities/living-docs/schemas/readers.schema.json
        - .pkit/capabilities/living-docs/rule-sets/ldoc.md
      record:
        - living-docs:DEC-001#1
        - living-docs:DEC-001#3
        - living-docs:DEC-001#6
        - living-docs:DEC-001#7
        - living-docs:DEC-002#8
        - COR-013
        - COR-017
        - COR-031
        - COR-051#7
        - COR-052
      artefact:
        - REQ-022
---

# UC-046 — Have a page read as its declared reader would read it

**Goal:** Have a page read as its declared reader would read it, each finding citing the rule the page breaks.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): the `living-docs` agent, which performs the [reader-review](../../glossary.md#term-reader-review--reader-review). It changes nothing it judges (REQ-022).

**Preconditions:**

- **From UC-044 or UC-047:** The [page](../../glossary.md#term-page--page) names its [reader](../../glossary.md#term-reader--reader) and its [page kind](../../glossary.md#term-page-kind--page-kind).

**Assumptions:**

- The [project](../../../core/glossary.md#term-project--project) has living-docs installed, or registered in place where living-docs is developed, and the [adapter](../../../core/glossary.md#term-adapter--adapter) deploys its `living-docs` [agent definition](../../../core/glossary.md#term-agent-definition--agent-definition) (COR-013, COR-017 and COR-031).
- The [backbone](../../../core/glossary.md#term-backbone--backbone) resolves the [readers](../../glossary.md#term-reader--reader) [data point](../../../core/glossary.md#term-data-point--data-point) from its default, the project's file and each [capability](../../../core/glossary.md#term-capability--capability) that fills it (COR-052). It answers where each [rule](../../../core/glossary.md#term-rule--rule) binds (COR-051 point 7).
- Nothing at run time confines the agent to the [agent workspace](../../../core/glossary.md#term-agent-workspace--agent-workspace). Its definition grants no tool that edits a file in place and owns no path, but its Write and its Bash reach any file (COR-013).

**Trigger:** The developer wants to know whether a [page](../../glossary.md#term-page--page) serves the [reader](../../glossary.md#term-reader--reader) it names, such as before the page is published.

**Main path:**

1. The developer asks the `living-docs` agent to review a [page](../../glossary.md#term-page--page) as its [reader](../../glossary.md#term-reader--reader).
2. The agent reads the rules that bind on the page, `LDOC`'s and its space's own, with `pkit rule-sets reach --json` (DEC-001 point 3).
3. The agent resolves the page's reader against the readers [data point](../../../core/glossary.md#term-data-point--data-point), with `pkit connections resolve pkit::documentation:readers --json`. It takes that reader's needs. Where the reader's entry carries paths, the agent takes them too, each path the pages the reader reads in order (DEC-001 points 6 and 7).
4. The agent reads the page as that reader. It asks whether the page answers that reader's questions, only those, and in a way the reader can follow (DEC-001 point 6).
5. The agent judges the page against each [rule](../../../core/glossary.md#term-rule--rule) that binds on it, such as whether its anchors ground each statement. It leaves to [validation](../../../core/glossary.md#term-validation--validation) the parts of `LDOC`'s rules that validation enforces (DEC-001 point 6).
6. Where a rule of the page's space asks the agent to, the agent follows each of the reader's paths that passes through the page. The user space's rule that reader paths stay unbroken is one (DEC-001 point 3). With no paths, the agent follows the page's own links.
7. The agent finds what the reader misses or does not need. It writes one record, `.agent-workspace/living-docs/reader-review/<page-slug>.md`, naming the page, the commit it reviewed and the reader (DEC-001 point 6).
8. Each [finding](../../../core/glossary.md#term-finding--finding) of the record cites the rule the page breaks, and quotes the passage. It says what the reader misses or does not need, with a direction, never a rewritten page (DEC-001 point 6).
9. The agent tells the developer where the record lies, and how many findings it holds.

**Variants:**

- **1a.** The developer asks the agent to review a change for documentation it left missing or contradicted. That is change review, which belongs to code review, and the agent says so (DEC-001 point 6). The use case ends.
- **2a.** No [rule](../../../core/glossary.md#term-rule--rule) binds on the [page](../../glossary.md#term-page--page). No [space definition](../../glossary.md#term-space-definition--space-definition)'s scope selects it, or it is reached only through a pin behind `LDOC`'s major. The agent says so, names what [validation](../../../core/glossary.md#term-validation--validation) reports of it, and judges it against no rule.
- **3a.** The [readers](../../glossary.md#term-reader--reader) [data point](../../../core/glossary.md#term-data-point--data-point) is not available yet. The agent says so, and reads the page as its space's audience, `spaces.<space>.audience` in the [capability](../../../core/glossary.md#term-capability--capability)'s configuration (DEC-001 point 1). Where the space's entry names none, the agent reads a user page as users, and reads a technical page as maintainers. For a space the [project](../../../core/glossary.md#term-project--project) adds whose entry names none, the agent names that entry, and stops.
- **3b.** `RS-LDOC-003` binds on the page, and the readers data point holds no reader of the page's id. That is validation's [finding](../../../core/glossary.md#term-finding--finding), so the agent names `pkit living-docs validate`, and stops.
- **4a.** The page shows a diagram, an image or a recording. The agent judges whether each that carries meaning has a text alternative, and a decorative image an empty one (DEC-002 point 8). An image's alt text is judged here alone, since no check tells a decorative image from one that carries meaning.

> [!WARNING]
> **Not built yet:** the agent reads none of DEC-002's forms, and judges a page's visual elements as any other text. DEC-002 point 8 leaves an image's text alternative to [reader-review](../../glossary.md#term-reader-review--reader-review), and #1812 tracks it.

- **4b.** The reading-evidence data point holds results of executed checks that followed the page, such as a simulated reader running a guide. Before step 4, the agent resolves the point with `pkit connections resolve pkit::documentation:reading-evidence --json`. The agent reads each result for the page as advice, which never replaces its own reading (DEC-001 points 6 and 7). The record of step 7, or the line of variant 7a, names each result the agent read, by its id.
- **7a.** The agent finds nothing. It says so in one line, writes no file, and the use case ends (DEC-001 point 6).
- **8a.** A passage is one a rule leaves to a person's judgement, such as a fact the page states twice in agreement. The agent lists it in the record as a question for the developer, not as a break (DEC-001 point 3).
- **9a.** The developer asks for the findings as a pull-request comment, and names the [pull request](../../../core/glossary.md#term-pull-request--pull-request). The agent posts the record with `gh pr comment`, its one write outside the [agent workspace](../../../core/glossary.md#term-agent-workspace--agent-workspace) (REQ-022). Where it found nothing, it posts no comment.

**Postconditions:** The developer knows whether the [page](../../glossary.md#term-page--page) serves its [reader](../../glossary.md#term-reader--reader). The agent wrote a record of [findings](../../../core/glossary.md#term-finding--finding), each citing the [rule](../../../core/glossary.md#term-rule--rule) the page breaks, or said in one line that it found nothing.

**Minimal guarantees:**

- The agent changes nothing it judges (REQ-022).
- A review that finds nothing leaves no file and no comment (DEC-001 point 6).
- The agent judges no part of a [rule](../../../core/glossary.md#term-rule--rule) a second time that [validation](../../../core/glossary.md#term-validation--validation) already enforces (DEC-001 point 6).
