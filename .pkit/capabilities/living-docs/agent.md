---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/agents/**
        - .pkit/capabilities/living-docs/review-contributions.yaml
        - .pkit/capabilities/living-docs/scripts/new.py
      record: ["living-docs:DEC-001", "living-docs:DEC-002", "COR-050", COR-057, "COR-062#1", "COR-062#7", "software-analysis:DEC-001#10", "project-management:DEC-032", "project-management:DEC-056"]
      artefact:
        - .pkit/cli/README.md#sync
        - .pkit/cli/README.md#friction-explain-artefact---json
        - .pkit/cli/README.md#friction-check---all---json
        - .pkit/cli/README.md#friction-checks
        - .pkit/cli/README.md#rule-sets-reach-path---at-rev---preview---json
        - .pkit/adapters/claude-code/README.md#deploy-agentssh
        - .pkit/capabilities/project-management/README.md#starting-the-fixers--fix-drift
        - .pkit/capabilities/living-docs/spaces.md#declaring-the-spaces
        - .pkit/capabilities/living-docs/pages.md#a-pages-fields
        - .pkit/capabilities/living-docs/spaces.md#each-definitions-scope
        - .pkit/capabilities/living-docs/validation.md#what-it-reports
        - RS-LDOC-002
        - RS-LDOC-003
        - .pkit/cli/README.md#validate
        - .pkit/cli/README.md#friction-check---base-ref---head-rev---json
        - .pkit/cli/README.md#friction-revalidate-artefact---outcome-updatedunchanged---because-text---keep-anchor---yes----dry-run
---

# The living-docs agent

The capability's agent, `living-docs`, and the review contribution the capability makes to a merge gate ([living-docs:DEC-001-living-docs-discipline] points 5, 6, 8 and 9).

## Contents

<!-- pkit:contents -->
- [What it does](#what-it-does)
- [What it never does](#what-it-never-does)
- [As the fixer of pages](#as-the-fixer-of-pages)
- [Onboarding](#onboarding)
- [The review contribution](#the-review-contribution)
<!-- /pkit:contents -->

## What it does

The checks say *that* a page drifted, and *which* documents are not pages yet. Deciding what that means for a page is judgment, and the capability's agent, `living-docs`, does it. Each result is a proposal a person reviews, never an edit (DEC-001 points 5, 6 and 8).

- **Its deployment.** `pkit sync` deploys it with the other agents. In Claude Code it is `.claude/agents/living-docs.md` <!-- unanchored: named so a reader finds the deployed agent, which the sync section the page anchors deploys -->, which the adapter's `deploy-agents.sh` writes.
- **How it is asked.** In plain words. It picks one of three intents from the request, each below.
- **What each intent writes,** under `.agent-workspace/living-docs/`:
  - a fix: its diff and pull-request body, in `fix/<page>/`
  - a reader-review: its record, in `reader-review/<page>.md`, only when something was found
  - onboarding: its plan, in `onboarding/plan.md`, and a folder for each step it drafts once the plan is approved

**Asked to fix a stale or deferred page:**

- **It reads** `pkit friction explain <page>`: the anchors that changed and the commits behind them. Then it reads those commits and the page.
- **It gives** a diff of the page and a pull-request body. They cite each commit and the anchor it changed, and name the answer given once the diff is applied (`pkit friction revalidate … --outcome updated`).
- **An anchor it re-points or adds** names the one part a statement rests on, where it rests on one.
- **Nothing to change.** When nothing in the page needs to change, it proposes the `unchanged` answer, with a draft reason for the person to confirm.
- **A page `explain` reports `unresolved`.** It says why from the anchor's finding, and proposes nothing for the prose:
  - for `no-answer`: run again, then `pkit sync`, or mend the resolver
  - for `unresolved-kind`, where the kind misspells a registered one: a one-line anchor correction, with the revalidation a changed anchor list needs. `pkit validate` names the nearest kind.
  - otherwise: the capability to install, or the registration to mend

**Asked to review a page as its reader:**

- **It reads** the page's `reader`, resolved through `pkit::documentation:readers`, with that reader's description and paths.
- **It reads the rules** that bind on the page, `LDOC`'s and its space's own, from `pkit rule-sets reach`.
- **It reads the evidence** of executed checks that followed the page, from `pkit::documentation:reading-evidence`, as advice where there is any.
- **Something found:** a findings record, naming each reading-evidence entry it read. Each finding cites the rule the page breaks (`RS-LDOC-003`, or the space's own rule), and quotes the passage. Each passage a rule leaves to a person's judgement, such as a fact the page repeats, is listed as a question.
- **Nothing found:** one line, naming any reading-evidence entry it read, and no file.
- **On request,** it posts the record as a pull-request comment.

**Asked to onboard existing documentation,** it reads validation's unclassified documents and findings, the friction check's measures, and the project's code-to-doc mapping where it keeps one. It gives one plan behind one approval gate ("Onboarding" below).

**Its readers before the readers point resolves.** Until then, the agent reads a page as its space's `audience` ([the page on spaces, "Declaring the spaces"](spaces.md#declaring-the-spaces)), and says so. Where the space's entry names none, it reads a user page as users and a technical page as maintainers, as DEC-001 gives them. For a space the project added whose entry names none, it reads no page, and names that entry.

**Answers kept apart from the page.** A change writes its answers in answer files of its own, never in the page (COR-062 point 1). Two branches that revalidate one page apart leave it reported as debt, never stale. It stays so until a revalidation that reads both judges the merged page (COR-062 point 7).

**Its definition and its script.** The agent itself is [`agents/living-docs/living-docs.md`](agents/living-docs/living-docs.md). Its scripted flows are in [`agents/living-docs/storyboard.md`](agents/living-docs/storyboard.md):

- a fix proposed
- a reader-review that finds nothing
- an onboarding plan rejected and revised
- a page stale on a source
- a fixer run a command started

## What it never does

- **Apply anything.** Its definition keeps it read-only on the repository. It never edits, moves or deletes a tracked file, never changes configuration, and never runs a friction writer (`revalidate`, `defer`, `record-status`).
  - **What holds it:** its definition alone. Nothing at run time confines its Write tool or its shell to the agent workspace, outside a fixer run that a work-tracking command confines. So never ask it to apply a change.
  - **Why:** for what this agent proposes, the answer a page carries is a person's decision (COR-050 point 3). This agent has no tool for asking the person, and judges pages besides. Who may run a writer is in the agents README, "Friction writers".
  - **Where its proposals land:** in the agent workspace, under `.agent-workspace/living-docs/`, as diffs applied with `git apply` and pull-request bodies.
  - **Its one write outside the workspace:** a reader-review posted as a pull-request comment, on request.
- **Repeat validation.** What `pkit living-docs validate` and `pkit validate` already judge, it names rather than judges again.
- **Review a change for missing docs.** That is change review, the code-review panel's documentation reviewer where one is installed. Reader-review looks at the page, not the diff.
- **Test the docs by running the product.** Such results arrive through the reading-evidence point, and the agent reads them as advice when it reviews a page as its reader.
- **Revalidate what is not a page,** such as a decision record, a rule or another capability's artefact. Its own component does that.
- **Fetch a source.** For a page stale on a `source` anchor, it reads the versions recorded and the address from the source file's history (`git show <commit> -- <file>`). It names the source, both versions and the link, and asks the person what changed in the source that bears on the page's statements. It never rewrites a page from a version change alone.
- **Read a friction document of a version it does not read.** The `explain`, `debt` and `check --all` documents carry a `schema_version` ([the CLI reference, "Friction checks"](../../cli/README.md#friction-checks)). One other than 1 it refuses, naming the command and the version, and proposes nothing from it. One without the key, from a backbone before it, reads as 1.

## As the fixer of pages

Where the project granted it, a work-tracking command may start the agent with nobody watching. project-management ships one, `pkit pm fix-drift` ([its README, "Starting the fixers"](../project-management/README.md#starting-the-fixers--fix-drift)). In such a run the agent only proposes friction fixes, on the pages the command names, and writes in the workspace the command gives it:

- **For each page it proposes,** it writes the evidence and the answer as fields. For an `updated` answer, it writes a diff of the page's text and anchors too. The command builds the answer's command from those fields, and never runs a command the agent wrote.
- **A page whose fix needs what only the person knows,** such as what changed in a source, is held with one question. The person's answer goes with the page's next run.
- **It ends with one line for each page,** in the forms of project-management's run contract. A line says proposed, held with its question, or none with one of the contract's reasons. One reason is `not-mine`, for a location that is no page.

Nothing is applied until the person accepts it.

## Onboarding

On a project that already has documentation, nothing is anchored yet. So onboarding is not moving files: it is friction work on that starting point (DEC-001 point 8).

**Its input.** Validation's summary counts the **unclassified documents**, the documents in the spaces' places that are not pages yet ([the page on pages, "A page's fields"](pages.md#a-pages-fields)). Before asking for a plan, declare the places, each place outside the roots assigned to a space ([the page on spaces, "Declaring the spaces"](spaces.md#declaring-the-spaces)). Run `pkit living-docs validate` until it reports no error.

**Its plan.** Asked to onboard, the agent drafts **one plan**, each line citing its evidence, in four parts:

- **Spaces:** which space each unclassified document becomes a page of, with its `reader` and `kind`, or why the spaces' rules do not govern it. Roots still shared are separated. A space with no definition gets one from `pkit living-docs new space`, which the person runs, with the scope that selects its pages.
- **Splits and rewrites:** pages that serve two readers, split, merged or rewritten for their reader. So are pages that state another page's fact with no link to its home, or no anchor on the home's section (`RS-LDOC-002`).
- **Anchors:** the anchors each page's statements need, each on the one part a statement rests on where it rests on one. The statements nothing grounds are raised as questions, rather than kept.
- **Mapping:** where the project keeps a code-to-doc mapping, which of its rules become path anchors on the pages they name. The mapping is project-management's, read through the work-tracking role's documentation-check point. An anchor that would match most of the repository is narrowed. Retiring the mapping is a separate change, for whoever owns it.

**Its single gate.** The person approves, revises or rejects the plan. Dispatched as a subagent, the agent cannot hear the person. The plan is then its result, and approval arrives as a new request that names the plan's file. Then:

- Nothing is drafted before approval.
- A revision comes back to the gate.
- A rejection drafts nothing.

**Its drafts.** On approval, it writes one reviewable change per step into `.agent-workspace/living-docs/onboarding/`, as diffs and pull-request bodies, and stops. The person applies them and opens the pull requests.

- **A document with no front matter before the change** is new there, and owes no answer.
- **A document that had front matter already** owes an answer for its new anchors, in the same pull request (COR-050 point 6).

**When it is done.** Onboarding is complete when the declared surface is covered, and no page is left unanchored without a reason a person accepted.

- **A page with nothing to anchor** carries that reason in its friction block, `unanchored-because: <why>`, instead of anchors. That is the core's key (COR-050 point 1), which the core refuses beside anchors.
- **The measures.** `pkit friction check --all` shows both, listing the pages accepted with a reason apart and counting only those without one. `pkit living-docs validate` counts the pages of the spaces each way in its summary, and lists them ([the page on validation, "What it reports"](validation.md#what-it-reports)).

From then on, the friction checks flag pages as their anchors change, and the agent proposes each fix.

## The review contribution

Where the project-management capability is installed, this capability contributes the core `rule-set-reviewer` to its merge gate (DEC-001 point 9). The reviewer judges a change against the accepted rules that bind on what it alters or brings under a rule (COR-057). The contribution is `review-contributions.yaml`, with one rule:

```yaml
contributions:
  - floor: touches-ruled-artefact
    reviewer: rule-set-reviewer
```

When that floor requires the reviewer, and what it reads locally, is in [project-management's README](../project-management/README.md), "Documents the rules govern" ([project-management:DEC-032-conditional-reviewer-requirements] D1).

- **What it covers.** Every artefact on which an accepted rule binds, a page or not, such as an analysis artefact. software-analysis contributes the same rule. With both installed, the reviewer is required once.
- **Opting out.** An opt-out under `review.agents.contributed_opt_out` in project-management's configuration withdraws one capability's contribution. The reviewer stays required through any other, so an opt-out lists each capability that contributes it.
- **The reviewer.** Core ships it, and `pkit sync` deploys it with the other agents. While it is not deployed, project-management refuses to resolve any pull request's reviewers.
- **Not a connection.** The contribution names project-management's gate, not a role, so it is none of the capability's connections.
