---
id: UC-011
title: Write a page for its reader, anchored to what makes it true
status: active
actor: ACT-developer
other-actors:
  - ACT-ai-agent
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/new.py
        - .pkit/capabilities/living-docs/scripts/_lib/stamp.py
        - .pkit/capabilities/living-docs/scripts/validate.py
        - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        - .pkit/capabilities/living-docs/scripts/_lib/doc_check.py
        - .pkit/capabilities/living-docs/skills/docs-author/page.md
        - .pkit/capabilities/software-engineering/agents/docs-reviewer.md
        - src/project_kit/friction_check.py
        - src/project_kit/friction_repository.py
      record:
        - living-docs:DEC-001#1
        - living-docs:DEC-001#2
        - living-docs:DEC-001#3
        - living-docs:DEC-001#4
        - living-docs:DEC-001#5
        - living-docs:DEC-001#7
        - project-management:DEC-015
        - project-management:DEC-053
        - COR-050#1
        - COR-050#3
        - COR-050#6
        - COR-050#7
        - COR-050#8
      artefact:
        - ACT-developer
        - ACT-ai-agent
---

# UC-011 — Write a page for its reader, anchored to what makes it true

**Goal:** Write a page for the reader it names, with anchors that ground each statement it makes.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): an agent with the `docs-author` skill drafts and stamps the page. `docs-reviewer` checks the change's documentation, and blocks a page that contradicts the code. The `living-docs` agent reads a page as its reader would.

**Preconditions:** The project has installed living-docs, which declares the project's documentation spaces.

**Assumptions:**

- Only what a page anchors grounds a statement (living-docs DEC-001 point 3). No check reads whether each statement is grounded. The reviewers and the reader-review judge it.
- The page says only what its reader needs, and keeps each fact in one home (living-docs DEC-001 point 3). Those rules bind where the space's definition selects the page, as project-kit's `TECH` and `USER` do (living-docs DEC-001 point 2).
- An agent writes the answers its own change owes, and no other answer (COR-050 point 3).

**Trigger:** The developer's change adds behaviour a page should describe, such as a new command, or the developer finds a fact that no page states.

**Main path:**

1. The developer chooses the page's space, its kind and its reader. The reader is one the readers point holds, such as `maintainer`, or an actor's id, such as `act-developer` (living-docs DEC-001 points 1 and 7).
2. The developer, or an agent with the `docs-author` skill, stamps the page: `pkit living-docs new page <file> --space <space> --kind <kind> --reader <reader> --title "<title>"`. Each `--path`, `--record`, `--artefact` and `--source` names an anchor.
3. The system writes the page, with its `reader`, its `kind` and its anchors in its front matter, and the kind's template as its body. It prints `stamped <file>: a <kind> page of space '<space>', for reader '<reader>'.`
4. The developer writes each statement for that reader, and grounds each one in an anchor. A statement nothing grounds gets its anchor, or goes (living-docs DEC-001 point 5).
5. Where the page sums up a fact whose home is another page, the summary links to that home. The page then anchors the home's section that states the fact, `<page>#<section>` (living-docs DEC-001 point 3).
6. The developer runs `pkit living-docs validate`, `pkit validate` and `pkit friction check`. A page new in the change counts as revalidated (COR-050 point 6).
7. The page lands in the same pull request as the code it describes, whose `## Doc impact` section names it (project-management DEC-015).
8. In each later change that modifies what one of its anchors names, the change check asks the page for an answer (UC-002).

**Variants:**

- **2a.** The space is not one of the project's. The stamp refuses with `space '<space>' is not a space of this project, …`, and names the command that creates one, `pkit living-docs new space <space>`. The path rejoins at step 2.
- **2b.** The space has no definition yet. The stamp writes the page, and warns that no rule binds on the space's pages, so validation checks neither the page's reader nor its structure.
- **3a.** The file would lie in no declared place, or in a place the space does not hold. The stamp refuses, says why the file would be no page of the space, and writes nothing. The path rejoins at step 2 with another file.
- **3b.** The page would bring a validation error the project did not have, such as a reader the readers point does not hold. The stamp refuses with `writing <file> would bring validation errors the project did not have — …`, and puts back every file it wrote.
- **4a.** A statement can neither be anchored nor cut. The developer raises it with a person as a question, and never leaves it standing as if it were true (living-docs DEC-001 point 5).
- **4b.** Nothing the repository holds makes the page true. A reason for having no anchors is written only once a person accepts it word for word (COR-050 points 1 and 3). The path goes on at step 6.
- **5a.** The fact is one a decision record decides, and the page anchors that record. The page states the fact with no link to another page (living-docs DEC-001 point 3).
- **6a.** An anchor the change added resolves to nothing. The change check reports a `dead-anchor`, which fails it in enforcing mode, and the path rejoins at step 4 (COR-050 point 7).
- **7a.** `docs-reviewer` finds that the page contradicts the code, and blocks the merge until the page is mended. The path rejoins at step 4.
- **7b.** The change adds code to the project's declared surface that no page anchors. In project-kit, `pkit pm check-doc-mapping` fails until a page anchors that code (project-management DEC-053). The path rejoins at step 2 for that page.

**Postconditions:** The page lies in its space for the reader it names, and an anchor grounds each statement it makes. So a change to what makes the page true asks it for an answer.

**Minimal guarantees:**

- A refused stamp writes nothing, and a write that would bring a new validation error is undone (`_lib/stamp.py`).
- The stamp writes no file that would be no page of the space it names (living-docs DEC-001 point 1, and `_lib/stamp.py`).
- Where the space's definition selects the page, a reader the readers point does not hold fails validation (living-docs DEC-001 points 4 and 7, and `validate.py`).
- A dead anchor is an error, never silence (COR-050 point 7).
