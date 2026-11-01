---
variant: specialized
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/scratchpads.py
      record: [COR-004, COR-005, COR-006, COR-007, COR-012, COR-043]
      artefact:
        - .pkit/cli/README.md#new-scratchpad-slug
        - .pkit/cli/README.md#scratchpad-commands
        - .pkit/cli/README.md#scratchpad-done-slug---produced-ref
        - .pkit/cli/README.md#scratchpad-drop-slug
        - .pkit/cli/README.md#scratchpad-reported-slug-ref
        - .pkit/cli/README.md#scratchpad-list
        - .pkit/cli/README.md#report-bug--report-feedback--report-change-request
        - .pkit/cli/README.md#report-submit-id
        - .pkit/lifecycle/README.md#seed-paths
---

# Scratchpad notes

<a id="authoring-workflow"></a><a id="why-scratchpad-and-not-draft-or-notes"></a>

A scratchpad note is a working draft that explores a question too large for a decision record yet ([COR-012](../decisions/core/COR-012-scratchpad-notes.md)). It binds nothing, and it retires once other documents hold what it found, or once its line of thought fails. Why notes exist, and how people start, send upstream and retire one, is in [the scratchpad guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/scratchpad/README.md).

## Contents

<!-- pkit:contents -->
- [Layout](#layout)
- [States](#states)
- [File name](#file-name)
- [Body](#body)
- [Front matter](#front-matter)
- [Commands](#commands)
<!-- /pkit:contents -->

## Layout

The area holds this README and a folder for each state of a note:

```
.pkit/scratchpad/
├── README.md         # this page, which sync updates
├── active/           # open notes
├── reported/         # open notes sent upstream as a report, while one lies here
├── done/             # notes whose content other documents hold
├── dropped/          # notes whose line of thought failed
└── .report-drafts/   # reports staged for `pkit report submit`, never a note
```

Each note is the file `<state>/<YYYY-MM-DD>-<slug>.md` ("File name" below).

- <a id="adopter-relevance"></a>**The notes are the project's.** Sync updates this README, and never reads or writes a note (COR-012).
- **Only `.md` files are notes.** A command moves a note's own file and nothing beside it, and `pkit scratchpad list` lists `.md` files only.
- **`active/`, `done/` and `dropped/`** are seed paths. The first install and each transition of the backbone create each one that is missing, with an empty `.gitkeep` ([the lifecycle README, "Seed paths"](../lifecycle/README.md#seed-paths)).
- **`reported/` is lazy.** It is created when the first note enters it, and removed when a retirement empties it (COR-043 point 2).
- **`.report-drafts/`** holds each report that `pkit report feedback --yes`, or the `bug` or `change-request` verb, stages until `pkit report submit` posts it. It keeps itself out of git ([the CLI reference, "report submit"](../cli/README.md#report-submit-id)).

<a id="lifecycle"></a>

## States

The folder a note lies in is its state, and no field of its front matter holds one (COR-012). `reported` refines `active`, and is no fourth stage (COR-043 point 1).

| State (folder) | Meaning |
|---|---|
| **`active/`** | The question is open, and the note is being filled or referenced. |
| **`reported/`** | The note is still open, and was sent upstream as a report. Only a send enters this state: a successful post, or the manual stamp of a send made outside the tooling (COR-043 point 3). |
| **`done/`** | Other documents, such as records, guides, skills or agents, hold the note's content. The note is kept. |
| **`dropped/`** | The line of thought failed. The note is kept, ending with why it stopped. |

- **A move between states** is a move of the file, which a command makes ("Commands" below). The command writes the file in its new folder and deletes the old one, and stages nothing in git. Once both paths are staged, git shows the move as a rename where the note changed little.
- **A reported note is frozen by convention.** Do not edit it, since the issue holds the text as sent. Put further thinking in a new note that links it (COR-043 point 4).
- **An edit to it is detected, never prevented.** `pkit scratchpad list` marks a reported note `[modified since reported]` when it differs from the hash stamped at the send. Composing a report warns of such a note too ([the CLI reference, "report"](../cli/README.md#report-bug--report-feedback--report-change-request)).
- **Its issues' states are read live.** `pkit scratchpad list` reads each through `gh` at each run, and stores none. A state it cannot read shows as `state unknown` (COR-043 point 5).
- **Retiring a note is a person's decision.** Once every issue of a reported note is closed, the listing prints the `pkit scratchpad done` command that retires it, and never runs it (COR-043 point 5).

<a id="filename"></a>

## File name

A note's file is `<YYYY-MM-DD>-<slug>.md` (COR-012):

- **`<YYYY-MM-DD>`** is the day the note was stamped. It never changes when the note moves.
- **`<slug>`** names the question in two to four words of kebab-case: lower-case letters and digits, joined by single hyphens.
- **A slug finds every note whose file name ends in `-<slug>.md`,** so `layer` finds `2026-06-03-cache-layer.md`. `pkit new scratchpad` refuses a slug that a note in any state folder ends with ("Commands" below).

Examples: `2026-05-12-agent-architecture.md`, `2026-06-03-cache-layer.md`.

## Body

The body opens with a level-1 heading, the note's title. The title is in the body, never a field of the front matter (COR-012):

```markdown
# Agent architecture — meta-agents vs role-shaped specialists

…body content…
```

- **The stamp's title** is the slug, with its hyphens turned into spaces and its first letter capital, such as `# Cache layer`. Edit it to the question.
- **The rest of the body** takes any shape.
- **A dropped note** ends with a paragraph or a section that says why its line of thought stopped, written before the drop.

<a id="frontmatter"></a>

## Front matter

The front matter holds who writes in a note and when it moved, and its fields depend on the note's state (COR-012).

### `active/`

```yaml
---
authors:
  - Name <email>
started: 2026-05-12
---
```

- **`authors`:** each person who writes in the note, as `Name <email>`. The stamp writes git's `user.name` and `user.email`, the name alone where git has no e-mail, or `<unknown>` where it has no name. Add each later writer.
- **`started`:** the day the note was stamped, the date its file name holds.

<a id="reported-side-state-of-active-cor-043"></a>

### `reported/`

The stamp adds these fields to the note's own (COR-043 point 3):

```yaml
---
authors:
  - Name <email>
started: 2026-05-12
reported: 2026-08-10
reported_to:
  - owner/repo#631
reported_hash: sha256:<hex>
---
```

- **`reported`:** the day the note was first sent.
- **`reported_to`:** each issue the note became, as `owner/repo#N`. A GitHub issue's web address given in its place is written in that form. One note may become several issues.
- **`reported_hash`:** `sha256:` and the SHA-256 of the note as sent, without the fields the stamp writes. The listing compares it with the note as it is now.
- **`project` and `workstream`:** the report's context, where the report named it. Only a report's post writes them.
- **Who writes these fields:** the successful post of a report composed with `--scratchpad <slug>`, or `pkit scratchpad reported <slug> <ref>...`. A report staged or filed in a browser writes nothing until one of the two runs.
- **A later send** of a reported note adds each new issue to `reported_to`, and stamps the hash again. So the listing no longer marks an edit made before that send. Where every issue given is recorded already, nothing changes.

### `done/`

```yaml
---
authors:
  - Name <email>
started: 2026-05-12
retired: 2026-05-15
produced:
  - PRJ-012
  - docs/cache.md
---
```

- **`retired`:** the day the note was retired.
- **`produced`:** each document the note's content went into: a record's id, a file's path or a web address. A reported note names its issues among them (COR-043 point 1).
- **What `pkit scratchpad done` writes:** its `--produced` values, in place of any `produced` the note holds. Given none, it leaves `produced` as it is, or absent. Add a later value by hand.
- **A reported note retired** keeps its reported fields.

### `dropped/`

```yaml
---
authors:
  - Name <email>
started: 2026-05-12
retired: 2026-05-15
---
```

- **`retired`:** the day the note was dropped.
- **No `produced`.**

<a id="cli-commands"></a>

## Commands

Each command has its full entry in the CLI reference, which each name below links. `pkit new scratchpad`, `pkit scratchpad done`, `drop` and `reported` take `--dry-run`, which prints what the command would do and writes nothing.

| Command | What it does |
|---|---|
| [`pkit new scratchpad <slug>`](../cli/README.md#new-scratchpad-slug) | Stamps `active/<today>-<slug>.md` with `authors`, `started` and a title drawn from the slug. Run it through the `scratchpad-author` skill, which it is paired with (COR-005). |
| [`pkit scratchpad done <slug> [--produced <ref>...]`](../cli/README.md#scratchpad-done-slug---produced-ref) | Moves the note from `active/` or `reported/` to `done/`, and adds `retired` and any `produced`. |
| [`pkit scratchpad drop <slug>`](../cli/README.md#scratchpad-drop-slug) | Moves the note from `active/` or `reported/` to `dropped/`, and adds `retired`. |
| [`pkit scratchpad reported <slug> <ref>...`](../cli/README.md#scratchpad-reported-slug-ref) | Records a send made outside the tooling. Moves the note from `active/` to `reported/` and adds the reported fields, or adds new issues to a reported note. |
| [`pkit scratchpad list`](../cli/README.md#scratchpad-list) | Lists the notes by folder, each reported note with its issues' live states. Marks an edited reported note, and names the retiring command once all its issues are closed. Writes nothing. |
| [`pkit report feedback … --scratchpad <slug>`](../cli/README.md#report-bug--report-feedback--report-change-request), and the `bug` and `change-request` verbs alike | Attaches the whole note, front matter included, to a public issue. Stamps the note reported on a successful post only. |

- **No skill pairs `done`, `drop` or `reported`,** since each is mechanical (COR-006).
- **A report run by an agent** goes through the `report-author` skill. Run with `--yes`, the verb only stages the report. A person posts it at a terminal with `pkit report submit <id>`, and only that post stamps the note.
- **Before a note is sent,** tell the person that its authors' names and e-mail addresses go into the public issue with it.
- **`<slug>`** of `done`, `drop` and `reported`, and of `--scratchpad`, is a slug or a whole file name. A slug finds every note whose file name ends in `-<slug>.md` ("File name" above). Give the whole file name where a short slug could find another note.
- **The refusals** write nothing:
  - `new scratchpad`: a slug that is not kebab-case, or that a note in any state folder ends with, or a project with no `active/`
  - `done` and `drop`:
    - no `active/`
    - a slug that finds no note in `active/` or `reported/`, or that finds two in one folder
    - a note with no front matter, or with front matter that is no mapping
    - a file of the same name in the target folder already
  - `reported`:
    - a ref that is neither `owner/repo#N` nor a GitHub issue's web address
    - a note that lies in neither `active/` nor `reported/`
    - a note with no front matter
    - a file of the same name in `reported/` already
- **Not built yet:** a command that reopens a note (COR-007). Move its file from `done/` or `dropped/` back to `active/` by hand, with `git mv`. Then remove each front-matter field `active/` does not hold, and a dropped note's closing paragraph on why it stopped.
