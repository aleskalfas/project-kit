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
      record: ["software-analysis:DEC-001", COR-049, COR-050, COR-052, COR-053]
    revalidated:
      at: 2026-09-29T22:00:25Z
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
| `pkit analysis new actor <slug> [--name <text>]` | the entry `ACT-<slug>` of `use-case-model/actors.md`, with its section |
| `pkit analysis new term <slug> [--name <text>]` | the entry `TERM-<slug>` of `glossary.md`, with its section |
| `pkit analysis new use-case <slug> --actor <ACT-id> [--area <area>] [--title <text>]` | `use-case-model/use-cases/[<area>/]UC-NNN-<slug>.md`, its actor anchored |
| `pkit analysis new journey <slug> --actor <ACT-id> --step <UC-id> --step <UC-id> … [--title <text>]` | `use-case-model/journeys/JRN-NNN-<slug>.md`, its steps anchored |

Every form also takes `--path <glob>` and `--record <id>`, each repeatable: the code that makes the artefact true and the decisions it relies on, written as its path and record anchors. Without them an actor or term is stamped unanchored — the core reports that, and never fails on it.

- **Ids.** A slug is a word: a lowercase letter, then lowercase letters, digits and hyphens. An actor is `ACT-<slug>` and a term `TERM-<slug>`; the stamp refuses an id already held, withdrawn or not, since an id is never used again. A use case or journey takes the **next free number**: one past the highest the working tree and the default branch hold. A number has one spelling — three digits below 1000 (`UC-007`), no leading zero from 1000 on (`UC-1000`); the check refuses another (`UC-0007`), and both the stamp and the duplicate check read it as the number it spells, so it is never a second id. The default branch is `--base <ref>`, else `$PKIT_CHECK_BASE`, else `origin/main`; when it names no commit, the stamp numbers from the working tree alone and says so. A number another branch takes after yours is `pkit analysis check-numbers`' to report (below).
- **What it writes.** The artefact's own fields from its template, its title or name (the slug, capitalised, by default) — a use case's or journey's title in its front matter and in its heading after the id — and the friction block with the anchors the decision asks for: a use case anchors to its actor, and a journey to the use cases of its steps. The body keeps the template's placeholders, `<…>`, for you to fill.
- **Collection files.** A new actor or term is added to the file's front matter, and its section to the body, each where its id sorts among those already there; every other byte stays as it was, and the stamp checks the result reads back as the file plus the new entry before writing. Kept sorted, two branches adding different entries touch different places of the file and merge without a conflict unless their ids are neighbours. The file is created from the template the first time.
- **What it refuses**, writing nothing: an actor, or a step, that is not in the analysis or is withdrawn — the check holds every use case and journey in force to the same; a journey with fewer than two steps; a slug or area that is not a word; an id already held.

The stamp reads the analysis through the core's reading command, `pkit friction artefacts` — the working tree's, and with `--at` the default branch's — and records the location through `pkit docs record-location --yes` (running the stamp is your consent to that write); it never walks the folders itself.

## The artefacts

Each anchored artefact's own fields sit beside the core friction block, which lives inside the `pkit:` container of its front matter (COR-050, COR-053) — the container of a document, or of each entry of a collection. Each kind's own fields have a companion schema in `schemas/`; unknown fields are refused, so a misspelt one is caught. The templates in `templates/` show the full shape.

**Use case** (`schemas/use-case.schema.json`) — one actor's goal and how the system fulfils it:

```markdown
---
id: UC-003
title: Run a test suite against a sandbox
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

The heading is the id and the `title`, `# <id> — <title>`, and the check requires the two to agree: whoever reads only the front matter sees the title the page shows. The title may change; the id does not. Steps are numbered and variants lettered after the step they branch from; both are only ever added, since journeys and evidence cite them.

**Journey** (`schemas/journey.schema.json`) — the same fields, `title` and heading included, plus `steps`: the use cases it passes through, in order, at least two. `steps` is the source; the stamp writes its use cases into the artefact anchors, and the check requires the two to match. Add the code at the seams as path anchors. The body gives where it starts, the ordered steps, the **seams to watch** between them, and when it is done.

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
evidence:                       # optional: the executed results drawn on, each copied whole from the evidence point
  - id: UC-003@78981922613b2afb6025042ff6bd878ac1994e85   # <artefact>@<commit>: its own two fields
    artefact: UC-003
    commit: "78981922613b2afb6025042ff6bd878ac1994e85"
    result: passed              # supports UC-003's `holds`
    ran: tests/test_run.py::test_sandbox
```

The body gives each artefact's outcome with its justification, then the gaps and what resolved each. Evidence supports an outcome and never stands in for one: each artefact the record draws evidence for has its outcome. The record **copies** each entry of the evidence point it draws on, whole and in the point's shape (Connections, below), rather than naming it by id: a record is permanent history, while the point holds what its fillers report now, so an id alone would point at nothing once a filler stops reporting that commit. The copy is the evidence the record shows.

## Checking: `pkit analysis validate`

`pkit validate` runs the check as its `software-analysis:artefacts` member, so it runs wherever your check gate runs `pkit validate`; `pkit analysis validate` runs it alone, and `--json` prints the findings document it reads. It is a query: read-only, offline, and `pkit sync` provisions its dependencies. It reads the working tree — and the evidence point, when a record copies evidence — so the same tree gets the same answer as long as the evidence fillers read the tree alone. It fails on:

- **a file in a place that is not its kind's shape** — a file without front matter, a glossary or actors file that is not a collection, a use-case or journey file holding entries;
- **missing required parts** — an artefact's own fields against its schema, and a collection entry whose key is not its kind's id;
- **a use case or journey whose heading is not its id and title** — `# UC-003 — <title>`, the `title` its front matter gives;
- **duplicate ids** — two artefacts holding one id;
- **a use case or journey naming what the stamp would refuse** — an actor, or a journey's step, that is not in the analysis, or that is withdrawn while the use case or journey is in force. A withdrawn artefact may name withdrawn ones: it is history;
- **a use case not anchored to its actor**, so a changed actor would not flag it;
- **a journey whose use-case anchors do not match its steps** — the message names the anchors to write;
- **a revalidation record** whose front matter does not fit its schema, or whose outcomes cite an id that is no artefact of the analysis (withdrawn ones are fine);
- **a revalidation record copying evidence for an artefact it gives no outcome**: evidence supports an outcome and never replaces it, so the record is incomplete whatever the evidence says;
- **an evidence entry whose `id` is not its own `<artefact>@<commit>`** — the entry's `artefact` and `commit` joined by `@`: the id is the pair the result is for, and which of the two is meant cannot be told, so nothing else is read from that entry.

It warns, and never fails, on:

- **a result at odds with its outcome** — a `failed` result copied for an artefact whose outcome is `holds`, or a `passed` one for `code-regressed`: a passing result supports *holds* and a failing one is a regression's proof, so the outcome or the evidence is likely wrong;
- **a copy that differs from what the evidence point now holds under its id**: the copy strayed from its source, or the result at that commit was reported again otherwise.

It says nothing of an id the point no longer holds, or of a point that does not resolve: the record's copy is the evidence, and a filler that stops reporting an old commit is ordinary. It reads the point, through `pkit connections resolve`, only when some record copies evidence.

Friction itself, dead anchors and the friction block's own shape are the core's checks (`pkit validate`'s `friction` member and `pkit friction check`), and so is front matter that does not parse; an unanchored artefact is the core's measure, never an error.

## Numbers another branch took: `pkit analysis check-numbers`

`pkit analysis check-numbers [--base <ref>] [--json]` fails on **a number two branches took**: a use case or journey numbered in your working tree whose number the default branch gave to another file since your branch left it. The first to reach the default branch keeps the number; renumber yours before merging (`pkit analysis new` gives the next free one). A use case you moved into an area is not a collision, and once the default branch is merged in, a number both took is two files holding one id, which `pkit validate` reports as a duplicate.

It reads the default branch — its tip, and where your branch left it — so it answers about your change rather than the tree, and it is not a member of `pkit validate`: run it as a line of its own in your check gate, beside `pkit friction check`, with the same base. The base is `--base <ref>`, else `$PKIT_CHECK_BASE`, else `origin/main`. Like the friction change check:

- it **fails when the base names no commit** here, or shares no history with `HEAD` — fetch it, or name another — rather than passing without comparing. A working tree that numbers nothing has nothing to compare and needs no base;
- it **reports an outdated base** — one that moved on after your branch left it, which is when it can have taken a number since — and never fails on it.

`--json` prints `{schema_version, base, summary, findings}`: `base` is `{ref, tip, commit, outdated}` (`commit` is the merge-base), or `null` when nothing was compared. It is a query: read-only, offline, and `pkit sync` provisions its dependencies.

## Connections

Declared in the package metadata's `connections` block (COR-053), as the decision's points 7 and 8 ask. `pkit capabilities show software-analysis` prints them and what they connect to in your project; `pkit connections graph` draws them among the rest. `pkit::` is this distribution's publisher qualifier for the methodology's roles ([the lifecycle README, "The methodology's literals"](../../lifecycle/README.md#the-methodologys-literals)).

**Provides the `pkit::analysis` role.** Anything that connects to the analysis addresses the role, never this capability, so another provider of the role could take its place.

**Accepts `pkit::analysis:revalidation-evidence`** (version 1): executed results that confirm or refute an artefact at a commit — a test run against a use case, a trace through a journey. This capability runs nothing: a capability that runs such checks fills the point, or you do, in the point's [project file](../../lifecycle/README.md#where-a-project-filler-file-lives-the-address-to-path-mapping) — `docs/pkit/fillers/pkit/analysis/revalidation-evidence.yaml` with the default internal root:

```yaml
schema_version: 1
value:
  - id: UC-003@78981922613b2afb6025042ff6bd878ac1994e85   # <artefact>@<commit>: the pair the entry is for
    artefact: UC-003
    commit: "78981922613b2afb6025042ff6bd878ac1994e85"    # the version the result is true of, by its full name; quoted, as digits alone read as a number
    result: passed                # passed | failed
    ran: tests/test_run.py::test_sandbox    # what was run, so it can be found and run again
    steps: ["1", "2", "2a"]       # optional: the steps and variants it went through
    where: https://ci.example/runs/42       # optional: where the result can be read
    by: the pipeline              # optional: who or what ran it
```

The entry's shape is `schemas/revalidation-evidence.schema.json`. It reads alone, since two providers of one point are compared by that file alone (COR-053 point 5), so it carries a copy of the id shapes whose one home is `schemas/analysis.schema.json`; a test holds the copy equal to its source. A commit is written by its **full name** — 40 hexadecimal digits, or 64 under SHA-256 — and a short name such as `7898192` is refused, so a pair has one spelling and a record's copy is compared with the entry it came from exactly. The point is `union`: entries from every filler merge by id, and yours replaces a capability's with the same id, or drops one with `remove` and a reason. The id is the artefact and the commit alone, so two results for the same artefact at the same commit share one id. From two capabilities — one running the tests and another tracing the journeys, say — that is a collision under `union`: the point does not resolve, its reason naming both, until your filler gives the id itself (COR-052 point 4); and a result your filler gives replaces a capability's for the same pair. That stands until the key is refined to tell such results apart. No default takes part, so while nothing fills it the point is unresolved — `pkit connections resolve pkit::analysis:revalidation-evidence --json` says `unfilled`, and nothing fails on it. Its inert policy is `fallback`: evidence advises, so a filler that cannot answer is warned, and the rest still count.

**Evidence informs a revalidation and never replaces it.** A revalidation record copies the entries it drew on under `evidence` (The artefacts, above): a passing result as support for *holds*, a failing one as a regression's proof. The record still gives each artefact its outcome — the check fails a record that copies evidence for an artefact without one — and only a revalidation or a deferral recorded on the artefact clears friction (COR-050).

**Contributes to `pkit::documentation:readers`** (version 1), the documentation role's point for who reads the documentation: one reader per actor in force, through the `fill-readers` command.

| Actor | Reader |
|---|---|
| its id, `ACT-tester` | `act-tester` — the id in lower case: a word, as the point asks, and never one of the point's default readers, so actors are added beside `user` and `maintainer` rather than replacing them |
| its name and needs | the description: `Test author, the analysis' actor ACT-tester. Needs: Run the suite against a clean sandbox; Read a failure's cause.` |
| withdrawn | no reader: it is history |

A page names an actor as its reader by that id (`reader: act-tester`). `pkit analysis fill-readers` prints the readers for you, `--json` the envelope the backbone reads. The filler reads the analysis through the core's reading command, `pkit friction artefacts`, and never walks the folders. The readers point fails closed, so an actors file that does not parse, or is not a collection, is no answer rather than no readers: the point is unresolved, its reason naming the file, until you fix it. **Inert when no capability provides the documentation role**: the contribution is reported as having no active provider, its command never runs, and this capability never requires one.

## What's shipped now, what's next

Shipped: the decision; the analysis location and its places; a companion schema and a template for each artefact kind and for the revalidation record; the stamp, `pkit analysis new`; the check, `pkit analysis validate`, a member of `pkit validate`; the number check, `pkit analysis check-numbers`, a check-gate line of its own; and the connections above — the analysis role, the evidence point with its companion schema, and the readers contribution with its filler, `pkit analysis fill-readers`. Next comes an authoring skill that guides revalidation. Named for later: planned-revalidation and onboarding lifecycles, a supplementary specification (constraints and quality), architecture views, and executable use cases.

## Citing this capability's decisions

`[software-analysis:DEC-001-software-analysis-discipline]`.

## Dependencies

None. It works without any work-tracking, documentation or testing capability, and each of them can enrich it.
