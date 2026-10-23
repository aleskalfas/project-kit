---
id: UC-045
title: Have the fix for a stale page proposed, and review it before it is applied
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements:
  - REQ-022
after:
  - [UC-044, UC-047]
shortfalls:
  - at: "4c"
    issue: "#1812"
    record: living-docs:DEC-002
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        - .pkit/capabilities/living-docs/agents/living-docs/storyboard.md
        - .pkit/capabilities/living-docs/package.yaml
      record:
        - living-docs:DEC-001#4
        - living-docs:DEC-001#5
        - living-docs:DEC-002
        - project-management:DEC-056#3
        - project-management:DEC-056#6
        - COR-013
        - COR-017
        - COR-031
        - COR-050#3
        - COR-050#5
        - COR-050#13
      artefact:
        - REQ-022
---

# UC-045 — Have the fix for a stale page proposed, and review it before it is applied

**Goal:** Have the fix for a stale page proposed with its evidence, and review the fix before it is applied.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): the `living-docs` agent, which drafts each proposal and applies none, so the developer reviews every fix before it lands (REQ-022).

**Preconditions:**

- **From UC-044 or UC-047:** The page is a page of a documentation space, with anchors.

**Assumptions:**

- The project has living-docs installed, or registered in place where living-docs is developed, and the adapter deploys its `living-docs` agent definition (COR-013, COR-017 and COR-031).
- A change modified what one of the page's anchors names, and the core's friction checks name the page stale or deferred. That is the change check, the whole-repository check or its debt listing (COR-050 point 5).
- The history at hand reaches the page's last answer, as the friction checks need it (COR-050 point 5).
- The answer a page carries is a person's decision. The developer gives it once the diff is applied, as `core:UC-002` describes (COR-050 point 3).
- Where the project grants the agent the page type, a work-tracking capability's command may start it with nobody watching. What the run passes the agent, and what it reads back, are that capability's (project-management DEC-056 points 3 and 6).
- Nothing at run time stops the agent writing outside the agent workspace. Its definition grants it no tool for editing a file, and owns no path (COR-013).

**Trigger:** A friction check names a page stale or deferred, and the developer wants its fix.

**Main path:**

1. The developer asks the `living-docs` agent to propose the fix for a page that is stale or deferred.
2. The agent runs `pkit friction explain <page> --json`. It takes the page's state, its anchors, and the commits behind each changed anchor, with the paths the check read as that anchor's change.
3. The agent reads each commit with `git show <commit> -- <paths>`. For a stale anchor on one part, it first reads the diff of what that part stands on, which `explain` gives (COR-050 point 13).
4. The agent judges each statement the changed anchor grounds. One still true stays as it is, and one no longer true is rewritten to match. Where its ground moved, the anchor is re-pointed, to the one part the statement rests on where it rests on one (DEC-001 point 5).
5. A statement that nothing grounds any more is given a new anchor, taken out, or raised with the developer as a question. It is never left standing as if it were true (DEC-001 point 5).
6. The agent writes the proposal under `.agent-workspace/living-docs/fix/<page-slug>/`: a diff of the page, labelled with the page's own path, and a pull-request body (DEC-001 point 5).
7. The pull-request body cites each commit and each anchor, and each hunk with the statement it changes. It names the answer the developer gives once the diff is applied.
8. The agent checks the diff with `git apply --check`, which writes nothing, and tells the developer where the proposal lies. It applies nothing (REQ-022).
9. The developer reviews the proposal, and accepts it.
10. The developer applies the diff with `git apply`, and gives the page's answer, as `core:UC-002` describes.

**Variants:**

- **1a.** The developer asks for every stale page the debt listing shows. The agent takes them in the check's order, upstream first, and writes one proposal for each.
- **1b.** A work-tracking capability's command starts the agent as the fixer of pages, on the pages the default branch left stale, with nobody to ask. The agent takes only those pages, in the order its brief gives, and writes only in the workspace the brief names (DEC-001 point 5). The path goes on at step 2, and variants 6a and 8a apply.
- **2a.** `explain` reports the page current, or unanchored. The agent says that there is nothing to fix, or that the page needs anchors first, and offers onboarding or a reader-review. The use case ends.
- **2b.** The artefact is no page, such as a decision record, a rule, or another component's artefact. The agent says that its owner revalidates it, and stops (DEC-001 point 5).
- **2c.** `explain` reports the page `unresolved`, so it was not judged. The agent proposes nothing for its text, and says why from the anchor's finding. Where the anchor's kind misspells a registered one, it proposes the one-line correction of the anchor.
- **2d.** A friction document carries a `schema_version` other than 1. The agent refuses it, naming the command and the version, and proposes nothing from it (core:REQ-019). The use case ends.
- **2e.** The page is stale on a `source` anchor. The agent reads the versions recorded, and the address, from the captured source's history, and never fetches the text. It names the text, both versions and the link, and asks the developer what changed that bears on the page (DEC-001 point 4). The path goes on at step 4, judged from the developer's answer.
- **2f.** The developer cannot say yet what changed in the text. The agent proposes nothing for the page's text. It names the two answers that are the developer's: read the text and come back, or defer the anchor with a reason. The use case ends.
- **4a.** The change looks wrong, rather than the page, such as code that now contradicts a decision the page applies. The agent says so, and leaves the call to the developer. It never rewrites the page to match a regression (DEC-001 point 5).
- **4b.** No statement needs to change. The agent proposes the `unchanged` answer, with its evidence and a draft reason the developer confirms or rewrites, and writes no diff.
- **4c.** A statement rests on a capture script or on console output, which only a new capture or a new run can tell. The agent runs neither, and holds the page with one question for the developer (DEC-002).

> [!WARNING]
> **Not built yet:** the agent knows nothing of capture scripts or console output, and judges such a page as any other. DEC-002 decides that the fixer of pages holds a page whose fix needs a new capture or a new run, and #1812 tracks it.

- **4d.** The page is deferred. The proposal answers the change the deferral put off, and the answer it names keeps no deferral.
- **6a.** In a run nobody watches, the agent writes each page's evidence, its diff where the answer is `updated`, and the answer as fields. The diff changes only the page's text and its anchors. A page whose fix needs what only a person knows, or a file other than the page, is held with one question (DEC-001 point 5).
- **8a.** In a run nobody watches, the agent ends with one result line for each page: proposed, held with its question, or none with its reason. The command that started it hands the developer each proposal, and the path goes on at step 9.
- **9a.** The developer asks for a change to the proposal. The agent revises it, and the path rejoins at step 8.
- **9b.** The developer refuses the proposal. Nothing is applied, and the page stays stale until someone answers it. The use case ends.

**Postconditions:** The proposal lies in the agent workspace, citing the commits and the anchors behind each statement it changes. Once the developer applies it, each statement the changed anchors ground holds again.

**Minimal guarantees:**

- The agent changes no file the repository tracks and runs no friction writer, so nothing is applied that the developer did not review (REQ-022).
- The agent never fetches a captured source's text, and never rewrites a page from a version change alone (DEC-001 point 4).
- The agent never rewrites a page to match a change that looks wrong (DEC-001 point 5).
- A friction document of a version the agent does not read is never read as version 1 (core:REQ-019).
