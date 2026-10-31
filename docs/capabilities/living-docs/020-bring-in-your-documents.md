---
reader: act-adopter
kind: guide
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        - .pkit/capabilities/living-docs/agents/living-docs/storyboard.md
        - .pkit/capabilities/living-docs/scripts/validate.py
      record: ["living-docs:DEC-001", "COR-050#1", "COR-050#6", "COR-050#8"]
      artefact:
        - UC-047
        - ACT-adopter
        - REQ-022
        - .pkit/capabilities/living-docs/agent.md#onboarding
        - .pkit/capabilities/living-docs/spaces.md#each-definitions-scope
        - .pkit/cli/README.md#friction-check---base-ref---head-rev---json
        - docs/capabilities/living-docs/010-set-up-your-spaces.md#declare-the-pages-outside-the-documentation-roots
        - docs/capabilities/living-docs/010-set-up-your-spaces.md#declare-the-code-your-pages-should-cover
        - docs/capabilities/living-docs/010-set-up-your-spaces.md#name-the-page-your-readers-start-from
---

# Bring in your documents

A project that has documentation already brings it into its spaces through one plan, which the `living-docs` agent drafts and you review. Here you take the documents you have to pages that name their reader and anchor what they rest on. What the agent's plan holds, and where it writes, are in [the reference on the agent](../../../.pkit/capabilities/living-docs/agent.md#onboarding).

## Contents

<!-- pkit:contents -->
- [Why a plan comes first](#why-a-plan-comes-first)
- [Declare where your documents lie](#declare-where-your-documents-lie)
- [Ask the agent for a plan](#ask-the-agent-for-a-plan)
- [Review the changes it drafts](#review-the-changes-it-drafts)
- [Repeat until no document is left](#repeat-until-no-document-is-left)
<!-- /pkit:contents -->

## Why a plan comes first

Documents written before living-docs name no reader and anchor nothing, so nobody can say which still hold. Moving them one file at a time misses the facts that several of them repeat. An agent that moves them alone can misjudge which audience a file serves. So the agent proposes the whole change as one plan, and drafts nothing until you approve it.

Here is a request and the agent's answers, as its storyboard, the script it follows, gives them. The project in it had not set up its spaces yet, so the plan sets them up too. The person rejects the first plan, and approves the revision:

```text
User: We just installed living-docs. Can you onboard our existing docs?

living-docs: Running pkit living-docs validate… 14 unclassified documents, both spaces still rooted in docs/, and no definition yet for either space. Running pkit friction check --all and resolving the doc-check point… 5 code-to-doc mapping rules, and 212 paths of declared surface that nothing anchors. Drafting one plan.

living-docs: Plan: (1) spaces — 9 documents become user pages, 4 technical, and the changelog is left ungoverned by excluding it; the technical space gets its own root, tech-docs/, with a definition each from the template. (2) Splits — docs/architecture.md serves both readers: its overview stays a user page, its internals move to the technical space. (3) Anchors — the ground of each page's statements, with 3 statements nothing grounds raised as questions. (4) Mapping — 4 rules become path anchors on the pages they name; src/** would be over-broad and is narrowed per page. The whole plan, with its evidence, is in .agent-workspace/living-docs/onboarding/plan.md. Approve, revise, or reject?

User: Reject. Don't split architecture.md — only maintainers read it.

living-docs: Revised: docs/architecture.md moves whole to the technical space as a maintainer page, and the two user pages that link to it lose those links, since user navigation never leads into technical material. The rest is unchanged. Approve, revise, or reject?

User: Approve.

living-docs: Drafting the changes the plan names… Four reviewable changes are in .agent-workspace/living-docs/onboarding/: roots and definitions, user pages, technical pages with the architecture split, and mapping anchors — each a diff and a pull-request body citing its evidence. Nothing was applied; they are yours to review and open.
```

## Declare where your documents lie

Validation counts the documents in your spaces' places that are not pages yet, and that count is the plan's input. Below, a project holds one such document, `docs/install.md`, with no front matter:

```console
$ pkit capabilities install living-docs >/dev/null
$ pkit living-docs new space user --yes >/dev/null 2>&1
$ mkdir -p docs && printf '# Install\n\nRun the installer.\n' > docs/install.md
$ pkit living-docs validate | grep -A1 "for onboarding to classify"
unclassified document(s), for onboarding to classify (1):
  docs/install.md
```

- **Documents outside the documentation roots,** such as a `wiki/` folder, are declared as places of their space first ([Set up your spaces](010-set-up-your-spaces.md#declare-the-pages-outside-the-documentation-roots)).
- **A place declared after its space was created** must be added to the paths of the space definition's scope as well. Otherwise validation fails each of its pages, since the pages lie outside the scope ([the reference, "Each definition's scope"](../../../.pkit/capabilities/living-docs/spaces.md#each-definitions-scope)).
- **The surface.** Declare the code your documentation should cover, so that the plan can anchor it ([Set up your spaces, "Declare the code your pages should cover"](010-set-up-your-spaces.md#declare-the-code-your-pages-should-cover)).

Run `pkit living-docs validate` until it reports no error.

## Ask the agent for a plan

In Claude Code, ask your session to use the `living-docs` agent, such as "Use the living-docs agent to onboard our existing docs". It reads validation's findings, the friction checks' measures and your documents, and drafts one plan in four parts:

- **Spaces:** the space each document becomes a page of, with its reader and its kind, or why your spaces' rules leave it out.
- **Splits and rewrites:** each page that serves two readers, or states another page's fact with no link to it or no anchor on it, split, merged or rewritten.
- **Anchors:** the anchors each page's statements need. A statement that nothing grounds is raised as a question, never kept as if it were true.
- **Mapping:** where your work tracker keeps a mapping from code to documents, which of its rules become page anchors.

Each line of the plan cites its evidence, and the plan is in `.agent-workspace/living-docs/onboarding/plan.md`. Approve it, ask for a revision, or reject it. The agent drafts nothing before you approve.

Where your session runs the agent as a subagent, the agent cannot hear your answer, and stops once the plan is written ([the reference, "Onboarding"](../../../.pkit/capabilities/living-docs/agent.md#onboarding)). Approve the plan in a new request that names its file, such as "Use the living-docs agent to draft the approved plan in .agent-workspace/living-docs/onboarding/plan.md".

## Review the changes it drafts

Once you approve, the agent writes one reviewable change for each step of the plan, under `.agent-workspace/living-docs/onboarding/`, and stops. Each change is a diff and a pull-request body. Apply each one you accept, and open its pull request:

```sh
git apply .agent-workspace/living-docs/onboarding/<step>/<file>.diff
```

- **A document with no front matter before the change** is new to the friction checks there, and owes no answer.
- **A document that had front matter already** owes an answer for its new anchors, in the same pull request. "Fix a stale page" shows how to give one.

## Repeat until no document is left

Run `pkit living-docs validate` after each change lands, and ask the agent again while it counts documents that are not pages yet. Bringing in your documents is done once these hold:

- **No document is left** that is not a page yet, or left out of your spaces' rules on purpose.
- **Every page has anchors,** or a reason for having none that you accepted. A page with nothing to anchor carries that reason in its friction block, as `unanchored-because`.
- **The surface is covered.** `pkit friction check --all` counts the surface files that no page anchors.

Once the page your readers start from is a page of its space, name it as the space's entry point ([Set up your spaces](010-set-up-your-spaces.md#name-the-page-your-readers-start-from)).
