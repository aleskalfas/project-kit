---
id: UC-047
title: Bring my existing documents into documentation spaces
status: active
actor: core:ACT-adopter
other-actors:
  - core:ACT-ai-agent
requirements:
  - REQ-022
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        - .pkit/capabilities/living-docs/agents/living-docs/storyboard.md
        - .pkit/capabilities/living-docs/scripts/validate.py
        - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
      record:
        - living-docs:DEC-001#1
        - living-docs:DEC-001#2
        - living-docs:DEC-001#4
        - living-docs:DEC-001#8
        - project-management:DEC-053
        - COR-013
        - COR-017
        - COR-031
        - COR-050#1
        - COR-050#6
        - COR-050#8
        - COR-050#14
      artefact:
        - REQ-022
    revalidated:
      at: 2026-10-24T00:22:01Z
      outcome: unchanged
      unchanged-because: The agent and its storyboard changed only where a reader-review takes the reader's paths. Onboarding is as it was.
---

# UC-047 — Bring my existing documents into documentation spaces

**Goal:** Bring my existing documents into documentation spaces, anchored and fit for their readers, through a proposed plan that I review before anything moves.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): the `living-docs` agent, which drafts the onboarding plan and the proposals it names, and applies none (REQ-022).

**Preconditions:** None.

**Assumptions:**

- The project has living-docs installed, or registered in place where living-docs is developed, and the adapter deploys its `living-docs` agent definition (COR-013, COR-017 and COR-031).
- The backbone configuration names the documentation roots, and declares the places that hold the project's documents, as `core:UC-021` describes (COR-050 point 1).
- The project declares the surface its documentation ought to cover, so the whole-repository check measures what no page anchors (COR-050 points 8 and 14).
- Where a work-tracking capability keeps a mapping from code to documents, it gives the mapping through its documentation-check data point (project-management DEC-053). Without one, the agent has no mapping to read.
- A page new in a change counts as revalidated there. A change that alters the anchors of a document with front matter asks it for an answer in the same change (COR-050 point 6).
- Nothing at run time confines the agent to the agent workspace. Its definition grants no tool that edits a file in place and owns no path, but its Write and its Bash reach any file (COR-013).

**Trigger:** The adopter installs living-docs on a project that has documentation already.

**Main path:**

1. The adopter assigns each place outside every documentation root that holds documents to a space, under `places` in `.pkit/capabilities/living-docs/project/config.yaml` (DEC-001 point 1).
2. The adopter runs `pkit living-docs validate`.
3. The system lists the unclassified documents, and the pages left unanchored apart from those accepted with a reason (DEC-001 points 4 and 8). It exits 0.
4. The adopter asks the `living-docs` agent to onboard the documentation.
5. The agent gathers its evidence:
   - validation's findings
   - the whole-repository check's measures
   - the mapping, where the project keeps one
   - both configuration files, and the documents
6. The agent writes one onboarding plan, `.agent-workspace/living-docs/onboarding/plan.md`, in four parts, each line citing its evidence (DEC-001 point 8):
   - **Spaces:** the space each unclassified document becomes a page of, with its `reader` and its `kind`, or why the spaces' rules do not govern it
   - **Splits and rewrites:** the pages that split, merge or are rewritten for their readers
   - **Anchors:** the anchors each page's statements need, each on the one part a statement rests on, and the statements nothing grounds, raised as questions
   - **Mapping:** the rules of the mapping that become page anchors, narrowed where an anchor would match most of the repository
7. The agent shows the plan's summary, and waits at its one gate: approve, revise or reject.
8. The adopter approves the plan.
9. The agent drafts one proposal for each step the plan names, under `.agent-workspace/living-docs/onboarding/`, each a diff and a pull-request body that cites the plan's evidence. It applies none, and stops (DEC-001 point 8 and REQ-022).
10. The adopter reviews each proposal, applies it, and opens its pull request.
11. The adopter runs `pkit living-docs validate` again. The system counts no unclassified document, and no page left unanchored without an accepted reason (DEC-001 point 8).

**Variants:**

- **3a.** The two documentation roots are one folder, as they are by default. Validation reports that the spaces are not separate yet, and the plan proposes the roots apart, before anything else (DEC-001 point 1).
- **3b.** Validation fails on a fault in the declarations, such as a place outside every root that holds a document and has no assignment. It exits 1, and the adopter mends the fault. The path rejoins at step 2.
- **6a.** A space has no space definition yet. The plan names `pkit living-docs new space`, which the adopter runs as `UC-043` describes. A definition that validation reports with no scope gets the scope the report names (DEC-001 point 2).
- **6b.** A document's title is not written as a level-one heading at the start of a line, such as one written in HTML. The plan says so beside the page kind it proposes, and proposes the title with the page's change.
- **6c.** A page has nothing to anchor to. The plan drafts its reason for having none, as `unanchored-because`, in place of anchors, for the adopter to accept at the gate (COR-050 point 1).
- **6d.** The project keeps no mapping from code to documents. The plan's mapping part says so, and proposes nothing there.
- **6e.** A page kind the plan needs has no template yet. The plan names it as a question for the adopter.
- **7a.** The agent was dispatched as a subagent, so it cannot hear the adopter. The plan is its result, and the adopter's approval comes back as a new request that names the plan's file.
- **8a.** The adopter rejects the plan with feedback. The agent revises the plan, writes its file again and shows what changed, and the path rejoins at step 7.
- **8b.** The adopter rejects the plan outright. The agent drafts nothing, the plan stays in the agent workspace, and the use case ends.
- **9a.** The plan turns rules of a mapping into page anchors. Retiring the mapping is a separate change for whoever owns it, so the agent drafts no proposal for it (DEC-001 point 8).
- **10a.** A proposal adds anchors to a document that has front matter already. The adopter answers for it in the same pull request, as `core:UC-002` describes, and the path goes on at step 11.
- **11a.** Unclassified documents or pages left unanchored remain, or the whole-repository check still measures surface that no page anchors. The path rejoins at step 4.

**Postconditions:** Each document in the spaces' places is a page of a space, or left out of the spaces' rules on purpose. Each page carries anchors, or a reason for none that a person accepted, and the declared surface is covered (DEC-001 point 8).

**Minimal guarantees:**

- Nothing is drafted before the adopter approves the plan, and nothing is applied (REQ-022).
- Every line of the plan, and every proposal, cites its evidence (DEC-001 point 8).
- A page left unanchored stays counted until it carries anchors or an accepted reason. It is never hidden (DEC-001 point 8).
