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
      at: 2026-09-29T22:22:51Z
      outcome: updated
---

# software-analysis capability

Keep a written, checkable account of **what your software must do**, and keep it true as the software changes. The account covers who uses it (actors), what they're trying to achieve and how (use cases), the end-to-end paths across several use cases (journeys), and what the words mean (glossary).

Install it when your project is past the point where one person holds the whole picture. That's when newcomers and agents need to learn the system from something more reliable than the code alone, and when you want to know if a change makes the description false. The rule is in [software-analysis:DEC-001-software-analysis-discipline].

## How it stays true

Each artefact declares what makes it true — its anchors — and when it was last revalidated, in the core friction block (COR-050). The core friction check flags it when an anchor changes. A **revalidation** then checks it, and ends as *holds*, *analysis was stale*, *code regressed* or *gap found*. A record is kept only when there's something to report. The full rule is in the decision.

- **Write** the analysis with the `analysis-author` skill, which walks each kind through its stamp, `pkit analysis new` ("Authoring" below).
- **Resolve** friction with the `analysis-resolver` agent: it proposes each flagged artefact's outcome with its evidence and the commands you run to record it, and asks you whenever it can't tell a stale analysis from regressed code ("The agent" below).

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
| `pkit analysis new actor <slug> [--name <text>] [--unanchored-because <text>]` | the entry `ACT-<slug>` of `use-case-model/actors.md`, with its section |
| `pkit analysis new term <slug> [--name <text>] [--unanchored-because <text>]` | the entry `TERM-<slug>` of `glossary.md`, with its section |
| `pkit analysis new use-case <slug> --actor <ACT-id> [--area <area>] [--title <text>]` | `use-case-model/use-cases/[<area>/]UC-NNN-<slug>.md`, its actor anchored |
| `pkit analysis new journey <slug> --actor <ACT-id> --step <UC-id> --step <UC-id> … [--title <text>]` | `use-case-model/journeys/JRN-NNN-<slug>.md`, its steps anchored |
| `pkit analysis new revalidation <slug> --change <ref> --trigger <trigger> --outcome <id>=<outcome> … --because <id>=<why> … [--gap "<gap> => <resolution>"]…` | a revalidation record, `revalidations/<date>-<slug>.md` — only one with something to say ("Revalidation records" below) |

Every artefact form also takes `--path <glob>` and `--record <id>`, each repeatable: the code that makes the artefact true and the decisions it relies on, written as its path and record anchors. Without them an actor or term is stamped unanchored — the core reports that, and never fails on it. An actor or term nothing embodies takes `--unanchored-because <why>` instead: the reason is written as its `unanchored-because`, and the stamp refuses it beside `--path` or `--record`.

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

**Revalidation record** (`schemas/revalidation-record.schema.json`) — no friction block; stamped by `pkit analysis new revalidation` from `templates/revalidation-record.md` as `revalidations/<date>-<subject>.md` ("Revalidation records" below):

```yaml
change: "#123"                  # the work item, pull request or commit range that carried it
trigger: drift                  # planned | drift | scheduled | close | onboarding
date: 2026-10-02                # the day in UTC, as a revalidation's `at` is
by: Alex                        # a person, or an agent
confirmed-by: Sam               # who confirmed an agent's outcomes, or decided stale
outcomes:                       # each artefact covered, withdrawn ones included
  UC-003: holds                 # holds | analysis-stale | code-regressed | gap-found
  JRN-001: analysis-stale
```

The body gives each artefact's outcome with its justification, then the gaps and what resolved each.

## Checking: `pkit analysis validate`

`pkit validate` runs the check as its `software-analysis:artefacts` member, so it runs wherever your check gate runs `pkit validate`; `pkit analysis validate` runs it alone, and `--json` prints the findings document it reads. It is a query: read-only, offline, and `pkit sync` provisions its dependencies. It reads the working tree alone, so the same tree always gets the same answer. It fails on:

- **a file in a place that is not its kind's shape** — a file without front matter, a glossary or actors file that is not a collection, a use-case or journey file holding entries;
- **missing required parts** — an artefact's own fields against its schema, and a collection entry whose key is not its kind's id;
- **a use case or journey whose heading is not its id and title** — `# UC-003 — <title>`, the `title` its front matter gives;
- **duplicate ids** — two artefacts holding one id;
- **a use case or journey naming what the stamp would refuse** — an actor, or a journey's step, that is not in the analysis, or that is withdrawn while the use case or journey is in force. A withdrawn artefact may name withdrawn ones: it is history;
- **a use case not anchored to its actor**, so a changed actor would not flag it;
- **a journey whose use-case anchors do not match its steps** — the message names the anchors to write;
- **a revalidation record** whose front matter does not fit its schema, or whose outcomes cite an id that is no artefact of the analysis (withdrawn ones are fine).

It says two more things, and never fails on them:

- **an open regression**, reported: a record's `code-regressed` artefact that has not been revalidated since the record — its `at` falls on no later day (UTC) than the record's date. The defect the record names is still open, or its fix was never revalidated against the artefact. It is worked out from the records and the artefacts each time, never kept in a ledger;
- **`unanchored-because` beside anchors**, a warning: the reason says why an actor or term has none, so one that has anchors says two things at once. The stamp refuses the pair; the warning catches a hand edit.

Friction itself, dead anchors and the friction block's own shape are the core's checks (`pkit validate`'s `friction` member and `pkit friction check`), and so is front matter that does not parse; an unanchored artefact is the core's measure, never an error.

## Numbers another branch took: `pkit analysis check-numbers`

`pkit analysis check-numbers [--base <ref>] [--json]` fails on **a number two branches took**: a use case or journey numbered in your working tree whose number the default branch gave to another file since your branch left it. The first to reach the default branch keeps the number; renumber yours before merging (`pkit analysis new` gives the next free one). A use case you moved into an area is not a collision, and once the default branch is merged in, a number both took is two files holding one id, which `pkit validate` reports as a duplicate.

It reads the default branch — its tip, and where your branch left it — so it answers about your change rather than the tree, and it is not a member of `pkit validate`: run it as a line of its own in your check gate, beside `pkit friction check`, with the same base. The base is `--base <ref>`, else `$PKIT_CHECK_BASE`, else `origin/main`. Like the friction change check:

- it **fails when the base names no commit** here, or shares no history with `HEAD` — fetch it, or name another — rather than passing without comparing. A working tree that numbers nothing has nothing to compare and needs no base;
- it **reports an outdated base** — one that moved on after your branch left it, which is when it can have taken a number since — and never fails on it.

`--json` prints `{schema_version, base, summary, findings}`: `base` is `{ref, tip, commit, outdated}` (`commit` is the merge-base), or `null` when nothing was compared. It is a query: read-only, offline, and `pkit sync` provisions its dependencies.

## Authoring: the `analysis-author` skill

The capability's skills, deployed by `pkit sync` with the others (in Claude Code, under `.claude/skills/`):

| Skill | Paired with | Use it to |
|---|---|---|
| `analysis-author` — composite: `actor`, `term`, `use-case`, `journey`, `revalidation-record` ([`skills/analysis-author/`](skills/analysis-author/analysis-author.md)) | `pkit analysis new` | write an actor, a term, a use case, a journey or a revalidation record: choose the slug, the area, the actor and the steps; decide what the artefact anchors to, or why an actor or term stays unanchored; fill the body; run the checks |

The command owns each file's correctness — its id, its place, the anchors the rule asks for — and the skill the choices behind it. One of those choices matters to revalidation later: **quote the code you describe** in backticks, since what an artefact quotes from its anchored code is the first thing the agent reads when that code changes ("The agent" below).

## Revalidation: four outcomes, two answers

A revalidation ends, for each artefact, in one of four outcomes, and each is recorded on the artefact as one of the core's two answers (DEC-001 point 5; COR-050 point 3). Only the answer on the artefact clears friction.

| Outcome | It means | The answer on the artefact |
|---|---|---|
| `holds` | the description still stands | `pkit friction revalidate <artefact> --outcome unchanged --because "<why it still holds against this change>"` |
| `analysis-stale` | the change was meant; the description is out of date | edit the artefact, then `pkit friction revalidate <artefact> --outcome updated` |
| `code-regressed` | the description is still what is wanted; the change broke it | report the defect, then `--outcome unchanged --because "<the description stands; defect <ref> reported>"` — the artefact is never rewritten to match |
| `gap-found` | behaviour nothing describes, or a description with no behaviour | `--outcome updated` where the artefact changed; `--outcome unchanged --because "<the gap, and the artefact that fills it>"` where a new artefact closes it |

Friction you choose not to resolve yet is not an outcome but a deferral: `pkit friction defer <artefact> --anchor <kind:value> --reason "<why it can wait>"`, which keeps it in the debt listing. Whether the analysis was stale or the code regressed is a question of intent — was the change meant? — and where the change's context doesn't say, a person decides before anything is recorded.

### Revalidation records

`pkit analysis new revalidation <slug> --change <ref> --trigger <trigger> --outcome <id>=<outcome> … --because <id>=<why> … [--gap "<gap> => <resolution>"]… [--by <who> | --by-agent <name>] [--confirmed-by <who>] [--title <text>]` writes `revalidations/<date>-<slug>.md` under the analysis location, **only when there is something to say**:

| The revalidation | A record? |
|---|---|
| was **planned** — a change proposed, checked before code | yes (DEC-001 point 6) |
| found a **regression** or a **gap** — `code-regressed` or `gap-found`, or a `--gap` | yes (point 6) |
| found an artefact **stale** where a person decided the change was meant — `analysis-stale`, with `--confirmed-by` naming them | yes: the decision point 5 leaves to a person is kept |
| found every artefact **holds**, or updated artefacts because the change was plainly meant | no: each artefact's own revalidation is its record (point 6) |

- **It writes** the front matter — the change that carried it, the trigger, the day in UTC (as a revalidation's `at` is), who performed it and who confirmed an agent's outcomes — and a body giving each outcome with its justification and each gap with what resolved it, or "None found." Who performed it is git's user name unless `--by` names another person; an agent that performed it is `--by-agent <name>`, which needs `--confirmed-by`: an agent proposes, a person decides.
- **Every word is the person's.** Each `--outcome` has its `--because`, and each gap is written as one pair with what resolved it, `--gap "<gap> => <resolution>"`, so no justification is left as the template's placeholder and no gap is matched with another's resolution. A text still holding a placeholder — words in angle brackets, as a command shown for you writes what you supply (`<the defect reference>`) — is refused, as the friction writers refuse one.
- **It refuses**, writing nothing: a record with nothing to say; a regression or gap that names no gap; a `--gap` that is not `<gap> => <resolution>`; an outcome without its `--because`, or with two; an agent without the person who confirmed it; a placeholder left unfilled; no outcome, an outcome that is not one of the four, or two for one artefact; an artefact that is not in the analysis (withdrawn ones are fine); a subject already recorded that day.

The record never clears friction itself: commit it in the same change as the answers on the artefacts it covers. `pkit analysis validate` holds it to its schema and to the artefacts it cites.

## The agent: `analysis-resolver`

The checks say *that* an artefact may no longer be true. Deciding what the change means for it is the judgment of a revalidation (DEC-001 point 5), and the capability's agent performs it; it is not a reviewer. `pkit sync` deploys it with the other agents; in Claude Code it is `.claude/agents/analysis-resolver.md`.

| Agent | Use it when | It hands you |
|---|---|---|
| `analysis-resolver` ([`agents/analysis-resolver/`](agents/analysis-resolver/analysis-resolver.md)) | the change check of a pull request, or the whole-repository report, flags analysis artefacts | a proposal in the agent workspace, `.agent-workspace/analysis-resolver/<change>/proposal.md`: each artefact's outcome with its evidence and the commands you run to record it, or the question it needs you to answer |

For each flagged artefact, upstream first, it reads `pkit friction explain`, the commits behind the changed anchor and the change's context — the commit messages, the pull request or work item — and proposes an outcome with its evidence, each quote it read beside its source and whether it was found there.

- **You run the commands; it runs none.** The proposal lists, per artefact, what you do first — an edit, a defect to report — and the writer commands word for word: `pkit friction revalidate` for the outcome, `pkit friction defer` for what you would rather postpone, and `pkit analysis new revalidation` for a record when there is something to say. None carries `--yes`, so each asks you once. Where the words are yours alone — the defect's reference, your name — a placeholder stands, and the writers refuse it until you fill it. Whether an agent may run the writers itself is for a project record to sanction; none does.
- **It never rewrites an artefact.** It has no edit tool and writes only in the agent workspace: an artefact's edit is a diff there, which you apply.
- **It asks where it can't tell stale from regressed.** That artefact, the artefacts downstream of it through the cascade and the record carry the question instead of commands — what disagrees, the commit, and the two readings; every other artefact gets its commands. Your answer is the quote it proposes from next.
- **Not for** another component's artefacts, writing new analysis (the skill's), reviewing a change, planned revalidations or onboarding, or running the software.

Its scripted flows — a drift resolved, the stop, and a regression recorded with its gap — are in [`agents/analysis-resolver/storyboard.md`](agents/analysis-resolver/storyboard.md).

### What the evidence decides: `pkit analysis propose`

`pkit analysis propose <artefact> [--contradicted <quote> --contradicted-from <source>] [--intended <quote> --intended-from <source>] [--unintended <quote> --unintended-from <source>] [--json]` is the part of the agent's judgment that needs no judgment, so what it leans on is a rule you can read. For one flagged artefact it reads `pkit friction explain`, and for each changed path anchor which code the artefact **quotes** — what it writes in backticks — the anchor's files held at its revalidation point, which of that is gone at HEAD, and where it went. A quote is matched as a whole word, so a quoted `--out` is gone once only `--output` is left.

**What the agent read goes in as quotes, each with its source**: a commit, a URL, or a person. A quote from a commit behind the changed anchors is checked against that commit's message (`git log --format=%B`, whitespace runs read as one space) and shown `verified` or not; any other source cannot be checked here and is shown unverified. The check is shown, never enforced: whether the change was meant is a person's decision, and the proposal puts the evidence beside it.

**Code that moved is not a disagreement.** When an anchored file was renamed, or the code the artefact quotes was carried into another file, the anchor is what went stale, not the description: one file outside the anchor, of the kind its files are (by extension), now holds every piece of lost quoted code and held none of it at the revalidation point — or, for an anchor the artefact quotes nothing from, git's rename detection says where its files went. The anchor is re-pointed (or the new file anchored beside it, where some quoted code stayed), and the revalidation is recorded `unchanged`, because an edit to the anchors alone changes no content — `updated` with no content change is a bump (COR-050 point 5). A quote found only in a file of another kind, or in more than one new file, is not a move.

The rules, in order (`scripts/_lib/resolve.py`):

| Rule | When | Comes to |
|---|---|---|
| `nothing-to-resolve` | the artefact is current or unanchored, and no anchor is dead | nothing |
| `ground-gone` | an anchored file is gone, code the artefact quotes is gone from it and went nowhere the reading can name, or the agent reads a contradiction (`--contradicted`, or evidence of one, `--unintended`) where code changed | `analysis-stale` with `--intended`; `code-regressed` with `--unintended`; **ambiguous** with neither, or both |
| `anchor-moved` | every changed anchor moved | `holds`, the anchor re-pointed, recorded `unchanged` |
| `deliberate-change` | a contradiction where only records or other artefacts changed | read, leaning to `analysis-stale` — a decision changes on purpose, but that alone does not say this artefact was meant to follow it; ambiguous against `--unintended` |
| `quoted-code-kept` | every changed anchor is a path whose files still hold everything the artefact quotes from them (or moved) | read, leaning to `holds` — that no quoted name vanished is all it shows: behaviour can change inside a name that stays, and a quote can survive in a call site, a comment or a test name |
| `nothing-decides` | otherwise — the artefact quotes nothing from the changed path, or a record or artefact changed with no contradiction read | read: the agent reads the change, and proposes `holds` or `gap-found`, or asks again with what contradicts |

It never proposes `gap-found`: behaviour nothing describes is found by reading. An ambiguous verdict carries the question for a person.

**The commands for the person.** For a verdict that comes to an outcome — a proposal, or a reading with its lean — it gives what the person does first (the edit, a defect to report) and the writer commands that record it, word for word and with no `--yes`: each writer asks once. Where the words are the agent's to draft (`<why it still holds against this change>`, `<why it is still wanted>`) or the person's alone (`<the defect reference>` — the defect is theirs to report and name), a placeholder stands, and the writers refuse it until it is filled. An ambiguous verdict has no commands, only its question.

**What it reads for itself.** The backbone does not yet expose three things this reading needs, so it works them out again, and each can disagree with the backbone: which files an anchor names (git's glob pathspec, which knows nothing of `friction.exclude` — a quote held only by an excluded file still counts), the commits behind a dead anchor (`git log` over it), and a collection entry's section (by its `## <id>` heading).

`--json` prints `{schema_version, artefact, location, state, head, revalidation_point, verdict, rule, reason, hint, question, anchors, read, answer}`: each changed anchor with its `shape` (`kept`, `moved`, `gone`, `deliberate`, `unread`), the commits behind it, what it `quoted`, what is `gone` and where it `moved_to`; each quote read with its `source`, `source_kind` (`commit` or `other`) and `verified` (`true`, `false`, or `null` when it cannot be checked); and the `answer`, `{outcome, first, commands}` or `null`. It reads HEAD, as the explanation does; exit `1` when the artefact cannot be explained (not committed, not found, or beyond a shallow clone), `2` on a usage error such as a quote without its source. A query: read-only, offline, and `pkit sync` provisions its dependencies.

## Connections (design-ahead)

Declared in the decision; the package metadata gains them in a later increment. The capability provides the `pkit::analysis` role (COR-053); `pkit::` and `pkit:` are this distribution's literals for the methodology's publisher qualifier and front-matter container ([the lifecycle README, "The methodology's literals"](../../lifecycle/README.md#the-methodologys-literals)).

- **Accepts** `pkit::analysis:revalidation-evidence`: executed results per artefact and commit, supplied by a capability or a [project file](../../lifecycle/README.md#where-a-project-filler-file-lives-the-address-to-path-mapping). Policy `union`, advisory. Evidence informs a revalidation; it doesn't replace one.
- **Contributes** to `pkit::documentation:readers` with actors and their needs. Inert when no documentation capability is installed.

## What's shipped now, what's next

Shipped: the decision; the analysis location and its places; a companion schema and a template for each artefact kind and for the revalidation record; the stamp, `pkit analysis new`, revalidation records included; the check, `pkit analysis validate`, a member of `pkit validate`; the number check, `pkit analysis check-numbers`, a check-gate line of its own; the `analysis-author` skill; and the `analysis-resolver` agent with `pkit analysis propose`. Next come: the connections above. Named for later: planned-revalidation and onboarding lifecycles, a supplementary specification (constraints and quality), architecture views, and executable use cases.

## Citing this capability's decisions

`[software-analysis:DEC-001-software-analysis-discipline]`.

## Dependencies

None. It works without any work-tracking, documentation or testing capability, and each of them can enrich it.
