# software-analysis capability

Keep a written, checkable account of **what your software must do**, and keep it true as the software changes. The account covers who uses it (actors), what they're trying to achieve and how (use cases), the end-to-end paths across several use cases (journeys), and what the words mean (glossary).

Install it when your project is past the point where one person holds the whole picture. That's when newcomers and agents need to learn the system from something more reliable than the code alone, and when you want to know if a change makes the description false. The rule is in [software-analysis:DEC-001-software-analysis-discipline].

## How it stays true

Each artefact declares what makes it true and when it was last rechecked. The core friction check (COR-050) flags it when that changes. A **revalidation** then checks it, and ends as *holds*, *analysis was stale*, *code regressed* or *gap found*. A record is kept only when there's something to report. The full rule is in the decision.

## Where things live

Under your project's internal documentation root (COR-049; `docs/` by default):

```
analysis/
├── glossary.md                      collection: one entry per term
├── use-case-model/
│   ├── actors.md                    collection: one entry per actor
│   ├── use-cases/
│   │   ├── UC-001-<slug>.md
│   │   └── <area>/UC-014-<slug>.md  optional grouping by functional area
│   └── journeys/
│       └── JRN-001-<slug>.md
└── revalidations/
    └── <date>-<subject>.md
```

A kind with many files gets a folder, and a kind with one file is a file. Folders appear only when something goes into them. These files belong to your project: uninstalling the capability leaves them in place.

## Templates

**Use case** (`UC-NNN-<slug>.md`):

```markdown
---
id: UC-003
status: active                  # or: withdrawn (file kept, id never reused)
actor: ACT-test-author
anchors:
  artefact: [ACT-test-author]
  path: [src/cli/run.py, src/sandbox/**]
  record: [ADR-006]
revalidated: 2026-10-02T09:40:12Z
---

# UC-003 — Run a test suite against a sandbox

**Goal:** …   **Starts when:** …
**Main path:** 1. … 2. … 3. …
**Variants:** 2a. … 3a. …
**Done when:** …
```

**Journey** (`JRN-NNN-<slug>.md`): the same front matter, with an ordered `steps: [UC-001, UC-002, …]`. Its use-case anchors are written into `anchors` from `steps` by the stamp and check commands; you add the code at the seams. The body gives *Starts*, *Done when*, the ordered steps, and the *seams to watch*.

**Actors / glossary** (collection files): front matter maps each id to its data, and the body has one `## <id>` section per entry. Actor ids start `ACT-` and actors carry `needs`. An artefact deliberately left unanchored carries `unanchored_reason:`. Term ids start `TERM-`; a term carries a display name, `replaces:` for former names, and a definition.

**Revalidation record** (`<date>-<subject>.md`): front matter with `change` (a work item, a pull request, or commits), `trigger` (`planned` | `drift` | `scheduled` | `close` | `onboarding`), the date performed, who did it (and who confirmed), and the ids of the artefacts covered. The body has one outcome per artefact, then the gaps and what resolved each.

Anchor and marker field names follow the core anchors-and-friction schema. The examples above are illustrative until that schema ships.

## Slots

- **Declares** `software-analysis:revalidation-evidence`: executed results per artefact and commit, supplied by a capability or a project file. Policy `union`, advisory. Evidence informs a revalidation; it doesn't replace one.
- **Will fill** `living-docs:readers` with actors and their needs, once that slot's record is accepted. It is inert when living-docs is not installed.

## What's shipped now, what's next

This increment ships the decision and this README. Next come: commands to stamp and check artefacts, an authoring skill that guides revalidation, and the declarations of places, surface and slots. Named for later: planned-revalidation and onboarding lifecycles, a supplementary specification (constraints and quality), architecture views, and executable use cases.

## Citing this capability's decisions

`[software-analysis:DEC-001-software-analysis-discipline]`.

## Dependencies

None. It works without any work-tracking, documentation or testing capability, and each of them can enrich it.
