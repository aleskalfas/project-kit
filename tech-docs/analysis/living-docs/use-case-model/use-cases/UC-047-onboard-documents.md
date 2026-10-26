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
---

# UC-047 — Bring my existing documents into documentation spaces

**Goal:** Bring my existing documents into documentation spaces, anchored and fit for their readers, through a proposed plan that I review before anything moves.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): the `living-docs` agent, which drafts the [onboarding plan](../../glossary.md#term-onboarding-plan--onboarding-plan) and the [proposals](../../glossary.md#term-proposal--proposal) it names, and applies none ([REQ-022](../../requirements/functional/REQ-022-agent-proposes-only.md)).

**Preconditions:** None.

**Assumptions:**

- The [project](../../../core/glossary.md#term-project--project) has living-docs installed, or registered in place where living-docs is developed, and the [adapter](../../../core/glossary.md#term-adapter--adapter) deploys its `living-docs` [agent definition](../../../core/glossary.md#term-agent-definition--agent-definition) (COR-013, COR-017 and COR-031).
- The [backbone configuration](../../../core/glossary.md#term-backbone-configuration--backbone-configuration) names the [documentation roots](../../../core/glossary.md#term-documentation-root--documentation-root), and declares the places that hold the project's documents, as `core:UC-021` describes (COR-050 point 1).
- The project declares the surface its documentation ought to cover, so the [whole-repository check](../../../core/glossary.md#term-whole-repository-check--whole-repository-check) measures what no [page](../../glossary.md#term-page--page) anchors (COR-050 points 8 and 14).
- Where a work-tracking [capability](../../../core/glossary.md#term-capability--capability) keeps a mapping from code to documents, it gives the mapping through its documentation-check [data point](../../../core/glossary.md#term-data-point--data-point) (project-management DEC-053). Without one, the agent has no mapping to read.
- A page new in a change counts as revalidated there. A change that alters the anchors of a document with front matter asks it for an [answer](../../../core/glossary.md#term-answer--answer) in the same change (COR-050 point 6).
- Nothing at run time confines the agent to the [agent workspace](../../../core/glossary.md#term-agent-workspace--agent-workspace). Its definition grants no tool that edits a file in place and owns no path, but its Write and its Bash reach any file (COR-013).

**Trigger:** The adopter installs living-docs on a [project](../../../core/glossary.md#term-project--project) that has documentation already.

**Main path:**

1. The adopter assigns each [place](../../../core/glossary.md#term-place--place) outside every [documentation root](../../../core/glossary.md#term-documentation-root--documentation-root) that holds documents to a space, under `places` in `.pkit/capabilities/living-docs/project/config.yaml` (DEC-001 point 1).
2. The adopter runs `pkit living-docs validate`.
3. The [system](../../../core/glossary.md#term-system--system) lists the [unclassified documents](../../glossary.md#term-unclassified-document--unclassified-document), and the pages left unanchored apart from those accepted with a reason (DEC-001 points 4 and 8). It exits 0.
4. The adopter asks the `living-docs` agent to onboard the documentation.
5. The agent gathers its evidence:
   - [validation](../../../core/glossary.md#term-validation--validation)'s [findings](../../../core/glossary.md#term-finding--finding)
   - the [whole-repository check](../../../core/glossary.md#term-whole-repository-check--whole-repository-check)'s measures
   - the mapping, where the [project](../../../core/glossary.md#term-project--project) keeps one
   - both configuration files, and the documents
6. The agent writes one [onboarding plan](../../glossary.md#term-onboarding-plan--onboarding-plan), `.agent-workspace/living-docs/onboarding/plan.md`, in four parts, each line citing its evidence (DEC-001 point 8):
   - **Spaces:** the space each unclassified document becomes a [page](../../glossary.md#term-page--page) of, with its `reader` and its `kind`, or why the spaces' rules do not govern it
   - **Splits and rewrites:** the pages that split, merge or are rewritten for their [readers](../../glossary.md#term-reader--reader)
   - **Anchors:** the anchors each page's statements need, each on the one part a statement rests on, and the statements nothing grounds, raised as questions
   - **Mapping:** the rules of the mapping that become page anchors, narrowed where an [anchor](../../../core/glossary.md#term-anchor--anchor) would match most of the repository
7. The agent shows the plan's summary, and waits at its one gate: approve, revise or reject.
8. The adopter approves the plan.
9. The agent drafts one [proposal](../../glossary.md#term-proposal--proposal) for each step the plan names, under `.agent-workspace/living-docs/onboarding/`, each a diff and a pull-request body that cites the plan's evidence. It applies none, and stops (DEC-001 point 8 and [REQ-022](../../requirements/functional/REQ-022-agent-proposes-only.md)).
10. The adopter reviews each proposal, applies it, and opens its [pull request](../../../core/glossary.md#term-pull-request--pull-request).
11. The adopter runs `pkit living-docs validate` again. The system counts no unclassified document, and no page left unanchored without an accepted reason (DEC-001 point 8).

**Variants:**

- **3a.** The two [documentation roots](../../../core/glossary.md#term-documentation-root--documentation-root) are one folder, as they are by default. [Validation](../../../core/glossary.md#term-validation--validation) reports that the spaces are not separate yet, and the plan proposes the roots apart, before anything else (DEC-001 point 1).
- **3b.** Validation fails on a fault in the declarations, such as a [place](../../../core/glossary.md#term-place--place) outside every root that holds a document and has no assignment. It exits 1, and the adopter mends the fault. The path rejoins at step 2.
- **6a.** A space has no [space definition](../../glossary.md#term-space-definition--space-definition) yet. The plan names `pkit living-docs new space`, which the adopter runs as `UC-043` describes. A definition that validation reports with no scope gets the scope the report names (DEC-001 point 2).
- **6b.** A document's title is not written as a level-one heading at the start of a line, such as one written in HTML. The plan says so beside the [page kind](../../glossary.md#term-page-kind--page-kind) it proposes, and proposes the title with the [page](../../glossary.md#term-page--page)'s change.
- **6c.** A page has nothing to [anchor](../../../core/glossary.md#term-anchor--anchor) to. The plan drafts its reason for having none, as `unanchored-because`, in place of anchors, for the adopter to accept at the gate (COR-050 point 1).
- **6d.** The [project](../../../core/glossary.md#term-project--project) keeps no mapping from code to documents. The plan's mapping part says so, and proposes nothing there.
- **6e.** A page kind the plan needs has no template yet. The plan names it as a question for the adopter.
- **7a.** The agent was dispatched as a subagent, so it cannot hear the adopter. The plan is its result, and the adopter's approval comes back as a new request that names the plan's file.
- **8a.** The adopter rejects the plan with feedback. The agent revises the plan, writes its file again and shows what changed, and the path rejoins at step 7.
- **8b.** The adopter rejects the plan outright. The agent drafts nothing, the plan stays in the [agent workspace](../../../core/glossary.md#term-agent-workspace--agent-workspace), and the use case ends.
- **9a.** The plan turns rules of a mapping into page anchors. Retiring the mapping is a separate change for whoever owns it, so the agent drafts no [proposal](../../glossary.md#term-proposal--proposal) for it (DEC-001 point 8).
- **10a.** A proposal adds anchors to a document that has front matter already. The adopter answers for it in the same [pull request](../../../core/glossary.md#term-pull-request--pull-request), as `core:UC-002` describes, and the path goes on at step 11.
- **11a.** [Unclassified documents](../../glossary.md#term-unclassified-document--unclassified-document) or pages left unanchored remain, or the [whole-repository check](../../../core/glossary.md#term-whole-repository-check--whole-repository-check) still measures surface that no page anchors. The path rejoins at step 4.

**Postconditions:** Each document in the spaces' places is a [page](../../glossary.md#term-page--page) of a space, or left out of the spaces' rules on purpose. Each page carries anchors, or a reason for none that a person accepted, and the declared surface is covered (DEC-001 point 8).

**Minimal guarantees:**

- Nothing is drafted before the adopter approves the plan, and nothing is applied ([REQ-022](../../requirements/functional/REQ-022-agent-proposes-only.md)).
- Every line of the plan, and every [proposal](../../glossary.md#term-proposal--proposal), cites its evidence (DEC-001 point 8).
- A [page](../../glossary.md#term-page--page) left unanchored stays counted until it carries anchors or an accepted reason. It is never hidden (DEC-001 point 8).
