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
  - [UC-043]
shortfalls:
  - at: 3
    issue: "#1921"
    record: living-docs:DEC-001#7
  - at: "4a"
    issue: "#1812"
    record: living-docs:DEC-002
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
        - living-docs:DEC-002
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

- **AI agent** (`core:ACT-ai-agent`): the `living-docs` agent, which performs the reader-review. It changes nothing it judges, so it meets core:REQ-021 (REQ-022).

**Preconditions:**

- **From UC-044 or UC-047:** The page names its reader and its page kind.
- **From UC-043:** The page's documentation space has its space definition, whose scope selects the page.

**Assumptions:**

- The project has living-docs installed, or registered in place where living-docs is developed, and the adapter deploys its `living-docs` agent definition (COR-013, COR-017 and COR-031).
- The backbone resolves the readers point from its default, the project's file and each capability that fills it (COR-052). It answers where each rule binds (COR-051 point 7).

**Trigger:** The developer wants to know whether a page serves the reader it names, such as before the page is published.

**Main path:**

1. The developer asks the `living-docs` agent to review a page as its reader.
2. The agent reads the rules that bind on the page, `LDOC`'s and its space's own, with `pkit rule-sets reach --json` (DEC-001 point 3).
3. The agent resolves the page's reader against the readers point, with `pkit connections resolve pkit::documentation:readers --json`. It takes that reader's needs, and the paths the reader takes through the pages (DEC-001 points 6 and 7).

> [!WARNING]
> **Not built yet:** an entry of the readers point holds only an id and a description of its reader's needs. Its schema refuses any other field. DEC-001 point 7 decides that each entry carries the paths its reader takes too, and #1921 tracks it.

4. The agent reads the page as that reader. It asks whether the page answers that reader's questions, only those, and in a way the reader can follow (DEC-001 point 6).
5. The agent judges the page against each rule that binds on it, such as whether its anchors ground each statement. It leaves to validation the parts of `LDOC`'s rules that validation enforces (DEC-001 point 6).
6. The agent follows the page's links where its space's own rules ask it. The user space's rule that reader paths stay unbroken is one (DEC-001 point 3).
7. The agent finds nothing. It says so in one line, and writes no file (DEC-001 point 6).

**Variants:**

- **1a.** The developer asks the agent to review a change for documentation it left missing or contradicted. That is change review, which belongs to code review, and the agent says so (DEC-001 point 6). The use case ends.
- **2a.** No rule binds on the page. No space definition's scope selects it, or it is reached only through a pin behind `LDOC`'s major. The agent says so, names what validation reports of it, and judges it against no rule.
- **3a.** The readers point is not available yet. The agent says so, and reads the page as its space's audience: users for the user space, maintainers for the technical one (DEC-001 point 1).
- **3b.** `RS-LDOC-003` binds on the page, and the readers point holds no reader of the page's id. That is validation's finding, so the agent names `pkit living-docs validate`, and stops.
- **4a.** The page shows a diagram, an image, console output or a callout. The agent judges each against the form living-docs gives it, neutral and with no styling, and with a text alternative where it carries meaning (DEC-002). An image's alt text is judged here, since no check tells a decorative image from one that carries meaning.

> [!WARNING]
> **Not built yet:** the agent reads none of these forms, and judges a page's visual elements as any other text. DEC-002 decides that the agent reads them when it reviews a page as its reader, and #1812 tracks it.

- **7a.** The agent finds something. It writes one record, `.agent-workspace/living-docs/reader-review/<page-slug>.md`, naming the page, the commit it reviewed and the reader. Each finding cites the rule it breaks and quotes the passage. It says what the reader misses or does not need, with a direction, never a rewritten page (DEC-001 point 6).
- **7b.** A passage is one a rule leaves to a person's judgement, such as a fact the page states twice in agreement. The agent lists it in the record as a question for the developer, not as a break (DEC-001 point 3).
- **7c.** The developer asks for the findings as a pull-request comment, and names the pull request. The agent posts the record with `gh pr comment`, its one write outside the agent workspace (REQ-022). Where it found nothing, it posts no comment.

**Postconditions:** The developer knows whether the page serves its reader. The agent said in one line that it found nothing, or wrote a record of findings, each citing the rule the page breaks.

**Minimal guarantees:**

- The agent changes nothing it judges (REQ-022 and core:REQ-021).
- A review that finds nothing leaves no file and no comment (DEC-001 point 6).
- The agent judges no part of a rule a second time that validation already enforces (DEC-001 point 6).
