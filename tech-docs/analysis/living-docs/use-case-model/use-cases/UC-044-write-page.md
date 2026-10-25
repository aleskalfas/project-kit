---
id: UC-044
title: Write a page for the reader it names
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-operator
  - core:ACT-ai-agent
requirements:
  - REQ-023
  - REQ-024
  - REQ-025
shortfalls:
  - at: 5
    issue: "#1765"
    record: ADR-034#1
  - at: "10a"
    issue: "#1803"
    record: living-docs:DEC-002
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/new.py
        - .pkit/capabilities/living-docs/scripts/_lib/stamp.py
        - .pkit/capabilities/living-docs/scripts/validate.py
        - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        - .pkit/capabilities/living-docs/scripts/_lib/formats.py
        - .pkit/capabilities/living-docs/scripts/_lib/sources.py
        - .pkit/capabilities/living-docs/scripts/resolve-source.py
        - .pkit/capabilities/living-docs/schemas/page.schema.json
        - .pkit/capabilities/living-docs/schemas/page-kinds.yaml
        - .pkit/capabilities/living-docs/schemas/source.schema.json
        - .pkit/capabilities/living-docs/templates/reference.md
        - .pkit/capabilities/living-docs/templates/signpost.md
        - .pkit/capabilities/living-docs/skills/docs-author/page.md
        - .pkit/capabilities/living-docs/rule-sets/ldoc.md
      record:
        - living-docs:DEC-001#1
        - living-docs:DEC-001#2
        - living-docs:DEC-001#3
        - living-docs:DEC-001#4
        - living-docs:DEC-001#6
        - living-docs:DEC-001#7
        - living-docs:DEC-001#8
        - living-docs:DEC-002
        - ADR-034#1
        - COR-005
        - COR-013
        - COR-017
        - COR-021
        - COR-031
        - COR-039#2
        - COR-050#1
        - COR-050#2
        - COR-050#6
        - COR-050#7
        - COR-051#7
        - COR-052
      artefact:
        - REQ-023
        - REQ-024
        - REQ-025
    revalidated:
      at: 2026-10-25T04:40:37Z
      outcome: unchanged
      unchanged-because: DEC-001 point 7 changed only on who reads the reading-evidence entries. The use case relies on point 7 for the readers point alone, which is as it was.
---

# UC-044 — Write a page for the reader it names

**Goal:** Write a page for the reader it names, with anchors that ground each statement it makes.

**Other actors:**

- **Operator** (`core:ACT-operator`): is asked before `pkit living-docs new page` writes in a repository other than the session's own, so no such write happens silently (core:REQ-012).
- **AI agent** (`core:ACT-ai-agent`): writes the [page](../../glossary.md#term-page--page) for the developer through the `docs-author` [skill](../../../core/glossary.md#term-skill--skill)'s page operation, and may run steps 4 and 11.

**Preconditions:** None.

**Assumptions:**

- The [project](../../../core/glossary.md#term-project--project) has living-docs installed, or registered in place where living-docs is developed (COR-017 and COR-031). The CLI registers `pkit living-docs new` and `validate` from its [package metadata](../../../core/glossary.md#term-package-metadata--package-metadata) (COR-021). The [adapter](../../../core/glossary.md#term-adapter--adapter) deploys the `docs-author` [skill](../../../core/glossary.md#term-skill--skill) (COR-005 and COR-013).
- The [backbone](../../../core/glossary.md#term-backbone--backbone) reads the [page](../../glossary.md#term-page--page)'s anchors, and its [change check](../../../core/glossary.md#term-change-check--change-check) asks the page for an [answer](../../../core/glossary.md#term-answer--answer) whenever what an [anchor](../../../core/glossary.md#term-anchor--anchor) names changes (COR-050 point 6). It resolves a `source` anchor through living-docs' resolver, `pkit living-docs resolve-source` (COR-050 point 2).
- A `source` anchor that no captured file answers is a dead anchor. The core's checks report it, and fail it where a change adds it (COR-050 point 7 and core:REQ-020).
- The backbone resolves the [readers](../../glossary.md#term-reader--reader) [data point](../../../core/glossary.md#term-data-point--data-point) from its default, the project's file and each [capability](../../../core/glossary.md#term-capability--capability) that fills it (COR-052). It answers where each [rule](../../../core/glossary.md#term-rule--rule) binds (COR-051 point 7).
- Nothing checks, as the page is written, that its anchors ground each statement it makes. A [reader-review](../../glossary.md#term-reader-review--reader-review) judges it, as `UC-046` describes (DEC-001 points 3 and 6).

**Trigger:** The developer has something to explain to one [reader](../../glossary.md#term-reader--reader) of a space, such as a new command its users run.

**Main path:**

1. The developer chooses the [page](../../glossary.md#term-page--page)'s [documentation space](../../glossary.md#term-documentation-space--documentation-space), its [page kind](../../glossary.md#term-page-kind--page-kind), `signpost` or `reference`, and its [reader](../../glossary.md#term-reader--reader) (the `docs-author` [skill](../../../core/glossary.md#term-skill--skill)'s page operation).
2. The developer chooses where the file goes: under the space's root by default, or in a [place](../../../core/glossary.md#term-place--place) assigned to the space (DEC-001 point 1).
3. The developer chooses what the page rests on, each by its option (DEC-001 point 4):
   - code by `--path`
   - decisions, or their points, by `--record`
   - rules, analysis [artefacts](../../../core/glossary.md#term-artefact--artefact), or the section of a fact's home, by `--artefact`
   - [captured sources](../../glossary.md#term-captured-source--captured-source) by `--source`
4. The developer runs `pkit living-docs new page` with the page's file, its `--space`, `--kind`, `--reader` and `--title`, and an option for each [anchor](../../../core/glossary.md#term-anchor--anchor).
5. At its entry, before it writes, the [system](../../../core/glossary.md#term-system--system) checks that the repository it would change is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (core:REQ-012).

> [!WARNING]
> **Not built yet:** `pkit living-docs new` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

6. The system runs the check that `pkit living-docs validate` runs, over the [project](../../../core/glossary.md#term-project--project) as it stands.
7. The system writes the page from its page kind's template. Its front matter names the reader and the page kind, and its [friction](../../../core/glossary.md#term-friction--friction) block lists the anchors given. The title fills its level-one heading (DEC-001 point 4).
8. The system runs the check again. It finds the file a page of the space named, and no [validation](../../../core/glossary.md#term-validation--validation) error the project did not have before.
9. The system lists the lines that still hold one of the template's placeholders.
10. The developer writes in each placeholder's place what the reader needs. Each statement rests on what the page anchors, and each fact has one home (DEC-001 point 3).
11. The developer runs `pkit living-docs validate`.
12. The system checks the page's `kind`. Where `RS-LDOC-003` binds on the page, it checks that the page names its reader, and that the readers [data point](../../../core/glossary.md#term-data-point--data-point) holds it. Where `RS-LDOC-004` binds, it checks the page's body against the structure its page kind declares. It checks neither part where its [rule](../../../core/glossary.md#term-rule--rule) does not bind (REQ-024).
13. The system prints its summary, with the readers it checked against and the pages it checked against their page kind's structure, and exits 0.

**Variants:**

- **1a.** The [page kind](../../glossary.md#term-page-kind--page-kind) is one the [project](../../../core/glossary.md#term-project--project) adds, with a template of its own. The [stamp](../../../core/glossary.md#term-stamp--stamp) takes only a page kind living-docs declares, so the developer writes the [page](../../glossary.md#term-page--page) by hand from that template (`stamp.py`). The path goes on at step 10.
- **2a.** The developer puts the page in a [place](../../../core/glossary.md#term-place--place) assigned to the space outside every root, as DEC-001 point 1 allows. The `docs-author` [skill](../../../core/glossary.md#term-skill--skill)'s page operation offers that place. The stamp writes the page there, as it writes one under the root.
- **3a.** The page rests on a text outside the repository, such as a standard. The developer captures it in `.pkit/capabilities/living-docs/project/sources/<name>.yaml`, holding its `title`, its `version` and, where it has one, its `url`. The page anchors it with `--source <name>`, and nothing fetches the text (DEC-001 point 4 and REQ-025).
- **3b.** The page has nothing to [anchor](../../../core/glossary.md#term-anchor--anchor) yet. The stamp writes an empty [friction](../../../core/glossary.md#term-friction--friction) block, and [validation](../../../core/glossary.md#term-validation--validation) counts the page as unanchored for onboarding, never failing it (DEC-001 point 8). A reason for having no anchors is a person's decision, accepted word for word before it is written (COR-050 point 1).
- **4a.** The developer passes `--dry-run`. The [system](../../../core/glossary.md#term-system--system) makes the checks before the write, prints the page it would write, and writes nothing. Whether the file would be a page of the space shows only once it is written, and the use case ends.
- **6a.** The request does not hold, in one of these ways, and the system refuses and writes nothing:
  - a space that is no space of the project, or a page kind living-docs does not declare
  - a file that exists, a path that is no Markdown file of the repository, or one reached through a link
  - a [reader](../../glossary.md#term-reader--reader) that is not a word, or a title that is empty or a placeholder

  The use case ends.
- **6b.** The check cannot read what it judges, such as where the rules bind or the readers [data point](../../../core/glossary.md#term-data-point--data-point). The system refuses, quoting what it could not read, and writes nothing. The use case ends.
- **6c.** The space has no [space definition](../../glossary.md#term-space-definition--space-definition) yet. The system warns that no [rule](../../../core/glossary.md#term-rule--rule) binds on the page, so validation checks neither its reader nor its structure. The path goes on at step 7 (DEC-001 point 2).
- **8a.** The check does not read the file as a page of the space named, such as a file in a place assigned to another space. The system puts the file back, refuses and says why (REQ-023). The use case ends.
- **8b.** The page brings a validation error the project did not have, such as a reader the readers data point does not hold where `RS-LDOC-003` binds. The system puts the file back, refuses and quotes the error (REQ-023). The use case ends.
- **8c.** The check after the write cannot read what it judges, such as the readers data point once the page names a reader where `RS-LDOC-003` binds. The system puts the file back, and refuses (REQ-023). The use case ends.
- **10a.** The page shows a diagram, an image, console output or a callout. The developer writes each as neutral content, with no styling, in the form living-docs gives it (DEC-002). A diagram, for one, is a `mermaid` fence with an `accTitle` and an `accDescr`. The `docs-author` skill gives the developer each form, and examples of a documentation site.

> [!WARNING]
> **Not built yet:** the `docs-author` skill gives none of these forms, and no example of a site. DEC-002 decides that the authoring skill gives writers the forms of its points 1, 2 and 5 to 9, and #1803 tracks it.

- **10b.** The page states a fact whose home is another page. The developer states it as a summary that links to that page, and anchors the section that states it in full (DEC-001 point 3).
- **12a.** Validation finds a fault in the page, names it, and exits 1. The developer mends the page, and the path rejoins at step 11. The faults are these:
  - a `kind` that is not a word
  - where `RS-LDOC-003` binds, a reader the page lacks, one that is not a word, or one the readers data point does not hold
  - where `RS-LDOC-004` binds, a section the structure declares that the body lacks or carries out of order
- **12b.** The readers data point does not resolve. Validation reports one error, "readers unresolved", and checks no page's reader until the data point resolves. It never reads the missing result as one that holds no reader (DEC-001 point 7 and core:REQ-004).
- **12c.** The page's kind declares no structure, such as a kind the project adds. Validation reports the page with its kind, and never fails it (DEC-001 point 3).
- **12d.** `RS-LDOC-008` is proposed, so it binds on no page, and the summary says so. Where it binds, validation fails a `mermaid` fence of the page that lacks an `accTitle` or an `accDescr` (DEC-002 points 8 and 10).
- **12e.** A `source` anchor of the page names no captured file. Validation reports it, and never fails it (DEC-001 point 4).

**Postconditions:** The [page](../../glossary.md#term-page--page) lies in its space. It names its [reader](../../glossary.md#term-reader--reader) and its [page kind](../../glossary.md#term-page-kind--page-kind), and its anchors name what its statements rest on. Where the space's rules bind on it, [validation](../../../core/glossary.md#term-validation--validation) holds its reader and its structure.

**Minimal guarantees:**

- A refused [stamp](../../../core/glossary.md#term-stamp--stamp) puts back every file it wrote, or names each it could not (REQ-023).
- The stamp never writes over a file that exists (`stamp.py`).
- [Validation](../../../core/glossary.md#term-validation--validation) and the resolver of a `source` [anchor](../../../core/glossary.md#term-anchor--anchor) change no file, need no network and give the same result for the same state. So they meet core:REQ-005 and core:REQ-007 (`validate.py` and `resolve-source.py`).
- A [readers](../../glossary.md#term-reader--reader) [data point](../../../core/glossary.md#term-data-point--data-point) that does not resolve fails validation, and never passes a [page](../../glossary.md#term-page--page) on fewer readers (DEC-001 point 7).
