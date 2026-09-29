---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/scripts/**
        - .pkit/capabilities/software-analysis/schemas/**
        - .pkit/capabilities/software-analysis/templates/**
        - .pkit/capabilities/software-analysis/skills/**
        - .pkit/capabilities/software-analysis/agents/**
      record: ["software-analysis:DEC-001", COR-049, COR-050, COR-053]
    revalidated:
      at: 2026-09-29T19:25:30Z
      outcome: updated
---

# software-analysis capability

Keep a written, checkable account of **what your software must do**, and keep it true as the software changes. The account covers who uses it (actors), what they're trying to achieve and how (use cases), the end-to-end paths across several use cases (journeys), and what the words mean (glossary).

Install it when your project is past the point where one person holds the whole picture. That's when newcomers and agents need to learn the system from something more reliable than the code alone, and when you want to know if a change makes the description false. The rule is in [software-analysis:DEC-001-software-analysis-discipline].

## How it stays true

Each artefact declares what makes it true — its anchors — and when it was last revalidated, in the core friction block (COR-050). The core friction check flags it when an anchor changes. A **revalidation** then checks it, and ends as *holds*, *analysis was stale*, *code regressed* or *gap found*. A record is kept only when there's something to report. The full rule is in the decision.

## Where things live

Under the `analysis/` folder of your internal documentation root (COR-049) — `docs/analysis/` with the default root:

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

**What the capability declares for you**, in its package metadata: the location `analysis`, a sub-path of the internal root, and the four places inside it that hold anchored artefacts — the glossary, the actors, the use cases and the journeys. The revalidation records describe an act rather than an anchored artefact, so their folder is not a place. The location is **recorded the first time you stamp an artefact**, in `.pkit/capabilities/software-analysis/project/docs-locations.yaml`, so changing the root later moves nothing already written. The capability declares no surface: the code your analysis ought to cover is yours to declare, in the `friction.surface` key of `.pkit/project/config.yaml`.

## Stamping artefacts: `pkit analysis new`

Create artefacts with the stamp, never by copying a template by hand: it gives each one its id, puts it in its place and writes the anchors it must carry. `analysis` is this capability's alias; `pkit software-analysis new` is the same command.

| Command | Writes |
|---|---|
| `pkit analysis new actor <slug> [--name <text>]` | the entry `ACT-<slug>` of `use-case-model/actors.md`, with its section at the end of the body |
| `pkit analysis new term <slug> [--name <text>]` | the entry `TERM-<slug>` of `glossary.md`, with its section |
| `pkit analysis new use-case <slug> --actor <ACT-id> [--area <area>] [--title <text>]` | `use-case-model/use-cases/[<area>/]UC-NNN-<slug>.md`, its actor anchored |
| `pkit analysis new journey <slug> --actor <ACT-id> --step <UC-id> --step <UC-id> … [--title <text>]` | `use-case-model/journeys/JRN-NNN-<slug>.md`, its steps anchored |

Every form also takes `--path <glob>` and `--record <id>`, each repeatable: the code that makes the artefact true and the decisions it relies on, written as its path and record anchors. Without them an actor or term is stamped unanchored — the core reports that, and never fails on it.

- **Ids.** A slug is a word: a lowercase letter, then lowercase letters, digits and hyphens. An actor is `ACT-<slug>` and a term `TERM-<slug>`; the stamp refuses an id already held, withdrawn or not, since an id is never used again. A use case or journey takes the **next free number**: one past the highest the working tree and the default branch hold. The default branch is `--base <ref>`, else `$PKIT_CHECK_BASE`, else `origin/main`; when it names no commit, the stamp numbers from the working tree alone and says so.
- **What it writes.** The artefact's own fields from its template, its title or name (the slug, capitalised, by default), and the friction block with the anchors the decision asks for: a use case anchors to its actor, and a journey to the use cases of its steps. The body keeps the template's placeholders, `<…>`, for you to fill.
- **Collection files.** A new actor or term is added to the end of the file's front matter and its section to the end of the body; every other byte stays as it was, and the stamp checks the result reads back as the file plus the new entry before writing. The file is created from the template the first time.
- **What it refuses**, writing nothing: an actor, or a step, that is not in the analysis or is withdrawn; a journey with fewer than two steps; a slug or area that is not a word; an id already held.

The stamp reads the analysis through the core's reading command, `pkit friction artefacts` — the working tree's, and with `--at` the default branch's — and records the location through `pkit docs record`; it never walks the folders itself.

## The artefacts

Each anchored artefact's own fields sit beside the core friction block, which lives inside the `pkit:` container of its front matter (COR-050, COR-053) — the container of a document, or of each entry of a collection. Each kind's own fields have a companion schema in `schemas/`; unknown fields are refused, so a misspelt one is caught. The templates in `templates/` show the full shape.

**Use case** (`schemas/use-case.schema.json`) — one actor's goal and how the system fulfils it:

```markdown
---
id: UC-003
status: active                  # or: withdrawn (file kept, id never reused)
actor: ACT-tester
pkit:
  friction:
    anchors:
      path:
        - src/cli/run.py
      record:
        - ADR-006
      artefact:
        - ACT-tester
---

# UC-003 — Run a test suite against a sandbox

**Goal:** …
**Starts when:** …
**Main path:** 1. … 2. …
**Variants:** 1a. …
**Done when:** …
```

Steps are numbered and variants lettered after the step they branch from; both are only ever added, since journeys and evidence cite them.

**Journey** (`schemas/journey.schema.json`) — the same fields, plus `steps`: the use cases it passes through, in order, at least two. `steps` is the source; the stamp writes its use cases into the artefact anchors, and the check requires the two to match. Add the code at the seams as path anchors. The body gives where it starts, the ordered steps, the **seams to watch** between them, and when it is done.

**Actors** (`schemas/actor.schema.json`) — a collection file: the front matter maps each id to its entry, and the body has one `## <id> — <name>` section per entry.

```yaml
ACT-tester:
  name: Test author             # may change; the id does not
  status: active
  needs:
    - Run the suite against a clean sandbox
  pkit:
    friction:
      anchors:
        path:
          - src/cli/**
```

**Glossary** (`schemas/term.schema.json`) — the same collection shape, each entry a `name`, a `status`, a one-sentence `definition`, and on a rename the former names, newest first, in `replaces`. The id never changes.

An actor or a term nothing embodies carries `unanchored-because:` — the reason onboarding accepts it unanchored.

**Revalidation record** (`schemas/revalidation-record.schema.json`) — no friction block; copy `templates/revalidation-record.md` to `revalidations/<date>-<subject>.md`:

```yaml
change: "#123"                  # the work item, pull request or commit range that carried it
trigger: drift                  # planned | drift | scheduled | close | onboarding
date: 2026-10-02
by: Alex                        # a person, or an agent
confirmed-by: Sam               # optional: who confirmed an agent's outcomes
outcomes:                       # each artefact covered, withdrawn ones included
  UC-003: holds                 # holds | analysis-stale | code-regressed | gap-found
  JRN-001: analysis-stale
```

The body gives each artefact's outcome with its justification, then the gaps and what resolved each.

## Checking: `pkit analysis validate`

`pkit validate` runs the check as its `software-analysis:artefacts` member, so it runs wherever your check gate runs `pkit validate`; `pkit analysis validate` runs it alone, and `--json` prints the findings document it reads. It is a query: read-only, offline, and `pkit sync` provisions its dependencies. It fails on:

- **a file in a place that is not its kind's shape** — a file without front matter, a glossary or actors file that is not a collection, a use-case or journey file holding entries;
- **missing required parts** — an artefact's own fields against its schema, and a collection entry whose key is not its kind's id;
- **duplicate ids** — two artefacts holding one id;
- **a use case not anchored to its actor**, so a changed actor would not flag it;
- **a journey whose use-case anchors do not match its steps** — the message names the anchors to write;
- **a number two branches took**: a use case or journey whose number the default branch gave to another file since your branch left it. The first to reach the default branch keeps the number; renumber yours before merging. The default branch is read as the stamp reads it (`--base`, `$PKIT_CHECK_BASE`, `origin/main`); when it names no commit here, the numbers are not compared, and the check says so without failing;
- **a revalidation record** whose front matter does not fit its schema.

Friction itself, dead anchors and the friction block's own shape are the core's checks (`pkit validate`'s `friction` member and `pkit friction check`), and so is front matter that does not parse; an unanchored artefact is the core's measure, never an error.

## Connections (design-ahead)

Declared in the decision; the package metadata gains them in a later increment. The capability provides the `pkit::analysis` role (COR-053); `pkit::` and `pkit:` are this distribution's literals for the methodology's publisher qualifier and front-matter container ([the lifecycle README, "The methodology's literals"](../../lifecycle/README.md#the-methodologys-literals)).

- **Accepts** `pkit::analysis:revalidation-evidence`: executed results per artefact and commit, supplied by a capability or a [project file](../../lifecycle/README.md#where-a-project-filler-file-lives-the-address-to-path-mapping). Policy `union`, advisory. Evidence informs a revalidation; it doesn't replace one.
- **Contributes** to `pkit::documentation:readers` with actors and their needs. Inert when no documentation capability is installed.

## What's shipped now, what's next

Shipped: the decision; the analysis location and its places; a companion schema and a template for each artefact kind and for the revalidation record; the stamp, `pkit analysis new`; and the check, `pkit analysis validate`, a member of `pkit validate`. Next come: the connections above, and an authoring skill that guides revalidation. Named for later: planned-revalidation and onboarding lifecycles, a supplementary specification (constraints and quality), architecture views, and executable use cases.

## Citing this capability's decisions

`[software-analysis:DEC-001-software-analysis-discipline]`.

## Dependencies

None. It works without any work-tracking, documentation or testing capability, and each of them can enrich it.
