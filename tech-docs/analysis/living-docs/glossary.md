---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-adapter, name: adapter}
      - {id: TERM-agent-definition, name: agent definition}
      - {id: TERM-agent-workspace, name: agent workspace}
      - {id: TERM-anchor, name: anchor}
      - {id: TERM-answer, name: answer}
      - {id: TERM-artefact, name: artefact}
      - {id: TERM-artefact-type, name: artefact type}
      - {id: TERM-backbone, name: backbone}
      - {id: TERM-backbone-configuration, name: backbone configuration}
      - {id: TERM-capability, name: capability}
      - {id: TERM-change-check, name: change check}
      - {id: TERM-component, name: component}
      - {id: TERM-data-point, name: data point}
      - {id: TERM-debt, name: debt}
      - {id: TERM-decision-record, name: decision record}
      - {id: TERM-default-branch, name: default branch}
      - {id: TERM-documentation-root, name: documentation root}
      - {id: TERM-finding, name: finding}
      - {id: TERM-friction, name: friction}
      - {id: TERM-install, name: install}
      - {id: TERM-package-metadata, name: package metadata}
      - {id: TERM-place, name: place}
      - {id: TERM-project, name: project}
      - {id: TERM-pull-request, name: pull request}
      - {id: TERM-rule, name: rule}
      - {id: TERM-rule-set, name: rule set}
      - {id: TERM-skill, name: skill}
      - {id: TERM-source-repository, name: source repository}
      - {id: TERM-stamp, name: stamp}
      - {id: TERM-system, name: system}
      - {id: TERM-validation, name: validation}
      - {id: TERM-whole-repository-check, name: whole-repository check}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Write a page for the reader it names, with anchors that ground each statement it makes.
          - Have the fix for a stale page proposed with its evidence, and review the fix before it is applied.
          - Have a page read as its declared reader would read it, each finding citing the rule the page breaks.
      - id: ACT-adopter
        name: Adopter
        needs:
          - Set up a documentation space for one audience, with its own location and a definition whose scope selects its pages.
          - Bring my existing documents into documentation spaces, anchored and fit for their readers, through a proposed plan that I review before anything moves.
      - id: ACT-ai-agent
        name: AI agent
      - id: ACT-operator
        name: Operator
TERM-captured-source:
  name: captured source
  noun-forms: [captured sources]
  status: active
  definition: "file naming a text outside the repository that pages rest on, where it is found, and which version of it was last checked"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/schemas/source.schema.json
          - .pkit/capabilities/living-docs/scripts/_lib/source_layout.py
        record:
          - living-docs:DEC-001#4
TERM-documentation-space:
  name: documentation space
  noun-forms: [documentation spaces]
  status: active
  definition: "collection of pages for one audience, in the places declared for it, with the page its readers start from and the rules its pages follow"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/schemas/config.schema.json
          - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        record:
          - living-docs:DEC-001#1
TERM-onboarding-plan:
  name: onboarding plan
  noun-forms: [onboarding plans]
  status: active
  definition: "outline of how a project's existing documents come into its documentation spaces, with its evidence, which a person approves before any proposal is drafted"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
          - .pkit/capabilities/living-docs/agents/living-docs/storyboard.md
        record:
          - living-docs:DEC-001#8
TERM-page:
  name: page
  status: active
  definition: "document in the places of a documentation space that names, in its front matter, the template it follows"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/schemas/page.schema.json
        record:
          - living-docs:DEC-001#1
          - living-docs:DEC-001#4
      revalidated:
        at: 2026-10-23T21:35:27Z
        outcome: updated
TERM-page-kind:
  name: page kind
  noun-forms: [page kinds]
  status: active
  definition: "category of documents, named by one word in each one's front matter, whose members follow one template"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/schemas/page-kinds.yaml
          - .pkit/capabilities/living-docs/templates/reference.md
          - .pkit/capabilities/living-docs/templates/signpost.md
        record:
          - living-docs:DEC-001#3
          - living-docs:DEC-001#4
TERM-proposal:
  name: proposal
  noun-forms: [proposals]
  status: active
  definition: "edit the living-docs agent drafts with the evidence it rests on, which nothing applies until a person accepts it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        record:
          - living-docs:DEC-001#5
TERM-reader:
  name: reader
  noun-forms: [readers]
  status: active
  definition: "class of people or agents who read a project's documentation, declared under an id that a page names, with what they need from it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/schemas/readers.schema.json
          - .pkit/capabilities/living-docs/scripts/_lib/readers.py
        record:
          - living-docs:DEC-001#7
TERM-reader-review:
  name: reader-review
  noun-forms: [reader-reviews]
  status: active
  definition: "judgement of one page as those it is written for would read it, against the rules that bind on it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        record:
          - living-docs:DEC-001#6
TERM-space-definition:
  name: space definition
  noun-forms: [space definitions]
  status: active
  definition: "rule set of the project's own that inherits `LDOC`, holding the rules for the pages of one audience, which bind where its scope selects them"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/templates/space-definition.md
          - .pkit/capabilities/living-docs/scripts/_lib/stamp.py
        record:
          - living-docs:DEC-001#2
TERM-unclassified-document:
  name: unclassified document
  noun-forms: [unclassified documents]
  status: active
  definition: "file in the places of a documentation space that is no page, no decision record and no rule-set file, and that no other owner claims"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        record:
          - living-docs:DEC-001#4
          - living-docs:DEC-001#8
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than living-docs's floor, 1.149.0.
  - **Term:** [adapter](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-adapter--adapter)
  - **Term:** [agent definition](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-agent-definition--agent-definition)
  - **Term:** [agent workspace](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-agent-workspace--agent-workspace)
  - **Term:** [anchor](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-anchor--anchor)
  - **Term:** [answer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-answer--answer)
  - **Term:** [artefact](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-artefact--artefact)
  - **Term:** [artefact type](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-artefact-type--artefact-type)
  - **Term:** [backbone](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-backbone--backbone)
  - **Term:** [backbone configuration](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-backbone-configuration--backbone-configuration)
  - **Term:** [capability](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-capability--capability)
  - **Term:** [change check](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change-check--change-check)
  - **Term:** [component](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-component--component)
  - **Term:** [data point](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-data-point--data-point)
  - **Term:** [debt](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-debt--debt)
  - **Term:** [decision record](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-decision-record--decision-record)
  - **Term:** [default branch](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-default-branch--default-branch)
  - **Term:** [documentation root](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-documentation-root--documentation-root)
  - **Term:** [finding](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-finding--finding)
  - **Term:** [friction](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-friction--friction)
  - **Term:** [install](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-install--install)
  - **Term:** [package metadata](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-package-metadata--package-metadata)
  - **Term:** [place](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-place--place)
  - **Term:** [project](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project--project)
  - **Term:** [pull request](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-pull-request--pull-request)
  - **Term:** [rule](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-rule--rule)
  - **Term:** [rule set](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-rule-set--rule-set)
  - **Term:** [skill](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-skill--skill)
  - **Term:** [source repository](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-source-repository--source-repository)
  - **Term:** [stamp](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-stamp--stamp)
  - **Term:** [system](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-system--system)
  - **Term:** [validation](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-validation--validation)
  - **Term:** [whole-repository check](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-whole-repository-check--whole-repository-check)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Write a page for the reader it names, with anchors that ground each statement it makes.
    - Have the fix for a stale page proposed with its evidence, and review the fix before it is applied.
    - Have a page read as its declared reader would read it, each finding citing the rule the page breaks.
  - **Actor:** [Adopter](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-adopter.md)
    - Set up a documentation space for one audience, with its own location and a definition whose scope selects its pages.
    - Bring my existing documents into documentation spaces, anchored and fit for their readers, through a proposed plan that I review before anything moves.
  - **Actor:** [AI agent](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-ai-agent.md)
  - **Actor:** [Operator](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-operator.md)

## TERM-captured-source — captured source

Explained in [VIEW-spaces-and-pages](domain-model/010-spaces-and-pages.md#captured-source).

**Example:** `.pkit/capabilities/living-docs/project/sources/keep-a-changelog.yaml` captures Keep a Changelog at version `1.1.0`. A [page](#term-page--page) that rests on it anchors it as `source: [keep-a-changelog]`.

**Distinctions:**

- **The text it names:** the standard, specification or other text outside the repository. Nothing fetches it, so a change to it is seen only once a person records the version they read (DEC-001 point 4).
- **Source repository:** where the [backbone](../core/glossary.md#term-backbone--backbone) or a [component](../core/glossary.md#term-component--component) is authored. A captured source names a text outside the repository, never a repository the [project](../core/glossary.md#term-project--project) syncs from.

## TERM-documentation-space — documentation space

Explained in [VIEW-spaces-and-pages](domain-model/010-spaces-and-pages.md#documentation-space).

**Example:** project-kit's user space starts its [readers](#term-reader--reader) at `README.md`. Its pages lie under `docs/`, and in places outside it assigned to the space, such as `.pkit/cli/README.md`.

**Distinctions:**

- **Documentation root:** a folder the [backbone configuration](../core/glossary.md#term-backbone-configuration--backbone-configuration) names for internal or for user-facing readers. It is a default [place](../core/glossary.md#term-place--place) of the space it serves, and a space's pages may lie outside it too (DEC-001 point 1).
- **Place:** a path or glob where the [backbone](../core/glossary.md#term-backbone--backbone) looks for documents. A place outside every root belongs to the space the [project](../core/glossary.md#term-project--project) assigns it to (DEC-001 point 1).

## TERM-onboarding-plan — onboarding plan

Explained in [VIEW-proposals-and-reviews](domain-model/020-proposals-and-reviews.md#onboarding-plan).

**Example:** on a [project](../core/glossary.md#term-project--project) with 14 [unclassified documents](#term-unclassified-document--unclassified-document), the plan makes nine of them user pages and four technical pages. It leaves `CHANGELOG.md` out of the spaces. The adopter approves it, and the agent drafts four [proposals](#term-proposal--proposal).

**Distinctions:**

- **Proposal:** a drafted edit with its evidence. The agent writes proposals only once the plan is approved, and the plan itself changes nothing (DEC-001 point 8).
- **A mapping from code to documents:** a work-tracking [capability](../core/glossary.md#term-capability--capability)'s list of which documents a change of code obliges. The plan turns its rules into [page](#term-page--page) anchors, and retiring the mapping is a separate change for its owner (DEC-001 point 8).

## TERM-page — page

Explained in [VIEW-spaces-and-pages](domain-model/010-spaces-and-pages.md#page).

**Example:** `.pkit/permissions/README.md` declares the kind `reference` and the [reader](#term-reader--reader) `user`, and anchors `.pkit/permissions/decide.py`, so a change to that code asks it whether it still holds.

**Distinctions:**

- **Unclassified document:** a document in a space's places that declares no [page kind](#term-page-kind--page-kind). It is no page, and onboarding classifies it (DEC-001 point 4).
- **Decision record:** a document a page anchors. It is never a page, whatever [place](../core/glossary.md#term-place--place) it lies in (DEC-001 point 4).
- **Page kind:** what a page declares in `kind`, such as `reference`. Declaring it is what makes a document a page (DEC-001 point 4).

## TERM-page-kind — page kind

Explained in [VIEW-spaces-and-pages](domain-model/010-spaces-and-pages.md#page-kind).

**Example:** `.pkit/cli/README.md` names the page kind `reference` in its `kind` field. So it starts from the template `templates/reference.md`, and its body carries a title at level one, as the kind's structure declares.

**Distinctions:**

- **Artefact type:** what the [backbone](../core/glossary.md#term-backbone--backbone) gives a document from its [place](../core/glossary.md#term-place--place), such as `living-docs:page`. A document of a root takes the [page](#term-page--page) type only where it names a page kind (DEC-001 point 4).
- **Template:** the starting shape a writer fills in. What a tool checks is the kind's structure, declared apart in `schemas/page-kinds.yaml`, and a template may show more than it (DEC-001 point 3).

## TERM-proposal — proposal

Explained in [VIEW-proposals-and-reviews](domain-model/020-proposals-and-reviews.md#proposal).

**Example:** `docs/install.md` is stale since `--out` became `--output`. The agent writes `fix/install/install.md.diff` and a pull-request body that names the commit and the [anchor](../core/glossary.md#term-anchor--anchor), and the developer applies the diff with `git apply`.

**Distinctions:**

- **Answer:** the statement in a [page](#term-page--page)'s `friction` block that settles its [friction](../core/glossary.md#term-friction--friction). A proposal names the [answer](../core/glossary.md#term-answer--answer) to give once it is applied, and a person gives that answer (COR-050 point 3).
- **Onboarding plan:** the outline of a whole onboarding. The agent drafts proposals only once a person approves it (DEC-001 point 8).
- **A proposed decision record or rule:** one whose status is `proposed`, which binds nothing yet. A proposal is no record, and never binds.

## TERM-reader — reader

Explained in [VIEW-spaces-and-pages](domain-model/010-spaces-and-pages.md#reader).

**Example:** a [page](#term-page--page) for `user` says what the [system](../core/glossary.md#term-system--system) does and how to use it, never its internals. A [project](../core/glossary.md#term-project--project) adds `operator` in its file for the readers [data point](../core/glossary.md#term-data-point--data-point), for whoever runs its service in production.

**Distinctions:**

- **Actor:** a role an analysis names. A reader's id is distinct from an actor's, so the readers an analysis [capability](../core/glossary.md#term-capability--capability) gives stand beside the defaults (DEC-001 point 7).
- **A documentation space's audience:** users, or maintainers, whom the whole space serves. Each page of the space names one reader (DEC-001 point 1).

## TERM-reader-review — reader-review

Explained in [VIEW-proposals-and-reviews](domain-model/020-proposals-and-reviews.md#reader-review).

**Example:** the agent reads `docs/quick-start.md` as `user`, against `LDOC` and the user space's definition, and finds nothing. It says so in one line, and writes no file.

**Distinctions:**

- **Change review:** a review of a diff for documentation it left missing or contradicted, which belongs to code review. A reader-review looks at the [page](#term-page--page), not the diff (DEC-001 point 6).
- **Validation:** it checks the parts of `LDOC`'s rules that living-docs enforces, such as a page's [reader](#term-reader--reader). A reader-review leaves those parts to it, and judges the rest of each [rule](../core/glossary.md#term-rule--rule) (DEC-001 point 6).
- **An executed check:** a run that follows the documentation, such as a simulated reader running a guide. living-docs runs none (DEC-001 point 6).

## TERM-space-definition — space definition

Explained in [VIEW-spaces-and-pages](domain-model/010-spaces-and-pages.md#space-definition).

**Example:** project-kit's user space has its definition in `tech-docs/living-docs/rule-sets/user.md`, the [rule set](../core/glossary.md#term-rule-set--rule-set) `USER`. It inherits `living-docs:LDOC@1`, selects the user space's pages, and adds the [rule](../core/glossary.md#term-rule--rule) that [reader](#term-reader--reader) paths stay unbroken.

**Distinctions:**

- **`LDOC`:** the rule set living-docs ships, which every space definition inherits. It takes no scope, so its rules bind on a [page](#term-page--page) only through a set of the [project](../core/glossary.md#term-project--project)'s own that selects it (DEC-001 point 2).
- **Template:** a writer's tool in the definitions location, such as a page template copied there. It is never a page, and holds no rule (DEC-001 point 2).

## TERM-unclassified-document — unclassified document

Explained in [VIEW-spaces-and-pages](domain-model/010-spaces-and-pages.md#unclassified-document).

**Example:** a [project](../core/glossary.md#term-project--project) adopts living-docs with `docs/guide.md`, whose front matter names no [page kind](#term-page-kind--page-kind). [Validation](../core/glossary.md#term-validation--validation) counts that file as an unclassified document, for onboarding to classify.

**Distinctions:**

- **Page:** a document of the [page](#term-page--page) type, or one that names its page kind in an untyped [place](../core/glossary.md#term-place--place) of the project's outside every root. An unclassified document is neither (DEC-001 point 4).
- **A document another owner claims:** such as an analysis [artefact](../core/glossary.md#term-artefact--artefact), a [decision record](../core/glossary.md#term-decision-record--decision-record) or a rule-set file. It is its owner's, and never counts as unclassified (DEC-001 points 1 and 4).
- **A document passed over:** one that lies only in an unassigned place of [rule sets](../core/glossary.md#term-rule-set--rule-set) outside every root, such as that place's `README.md`. It is neither a page nor unclassified (DEC-001 point 1).
