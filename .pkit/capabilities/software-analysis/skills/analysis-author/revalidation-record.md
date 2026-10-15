# Recording a revalidation

A **revalidation** is one check of some artefacts against one version of the system — a proposed design, or the code. Its answer for each artefact is written on the artefact itself, and that answer is what clears friction. A **record** is written beside it only when the revalidation has something to say: it is a file, `revalidations/<date>-<slug>.md`, citing artefacts by id.

## 1. Does it need a record?

Only when it has something to say: the one table of when is the capability README's [Revalidation records](../../README.md#revalidation-records). The stamp refuses a record with nothing to say, so that the few records that matter are never buried among routine ones.

## 2. Give each artefact its answer

Each artefact covered ends in one of four outcomes, and each is recorded on the artefact as one of the core's two answers: the one table of that mapping is the capability README's [Revalidation: four outcomes, two answers](../../README.md#revalidation-four-outcomes-two-answers). Record each artefact's answer as it says, before or with the record.

**A regression is never answered by rewriting the artefact to match the code.** When you cannot tell whether the change was meant — stale, or regressed — a person who knows the intent decides before anything is recorded.

Friction you choose not to resolve yet is not an outcome: it is a deferral of the anchor with its reason, as the same section says. It stays in the debt listing until someone revalidates.

## 3. Choose the slug

The subject of the change, as a word: `export-dropped`, `report-redesign`. The file is named by the day and the subject, never numbered, so two lines of work cannot collide; the stamp refuses a subject already recorded that day.

## 4. Stamp the record

```
pkit analysis new revalidation <slug> --change <ref> --trigger <planned|drift|scheduled|close|onboarding>
    --outcome <id>=<outcome>... --because <id>=<why>...
    [--reviewed-against "<title> @ <version> [@ <link>]"]...
    [--gap "<ids>: <what was found> => <the defect reported, or the artefact written>"]...
    [--by <who> | --by-agent <name>] [--confirmed-by <who>] [--title "<Subject>"]
```

- **`--change`** — what carried it: a work item (`#123`), a pull request, or a range of commits on the default branch.
- **`--trigger`** — `planned` before code; `drift` on a pull request's friction; `scheduled` for friction the whole-repository check found; `close` when a pull request changing artefacts lands; `onboarding`.
- **`--reviewed-against`** — a planned record's only, once for each source of the design it reviewed: its title, then its version, then its link where it lies outside this repository. The stamp refuses a planned record without it, and a record of any other trigger with it. The capability README's [Revalidation records](../../README.md#revalidation-records) gives the form.
  - **A source in this repository** is `"<title> @ <version>"`, its version a commit the default branch holds: the commit where the design landed. Name `this change` when the design lands with the record. A branch's commit is no pointer, since a squash merge leaves it off the default branch.
  - **A source outside it** is `"<title> @ <version> @ <link>"`, its version the time its text was read, in UTC, such as `2026-01-05T10:00:00Z`.
  - **A commit the default branch does not hold:** the stamp writes the record, and warns that `pkit analysis check-pointers` will fail the change until the source names one it holds, or `this change`. That command fails a change that adds such a record, naming the record and the source. The README's [Commits off the default branch](../../README.md#commits-off-the-default-branch-pkit-analysis-check-pointers) says how it places a commit.
- **`--outcome`** — each artefact covered, withdrawn ones included, and how it ended.
- **`--because`** — each outcome's justification, one per `--outcome`: the stamp refuses an outcome without one.
- **`--gap`** — each gap, as one with the artefacts it affects and what resolved it: `"<ids>: <gap> => <resolution>"`, the ids separated by commas, each one an `--outcome` gives. A regression or a gap found must name at least one, and each regression and each gap found is named among a gap's ids.
- **`--by`** — the person who performed it (git's user name by default); **`--by-agent`** — the agent that did, which needs **`--confirmed-by`**: the person who confirmed its outcomes, and decided stale against regressed where the two were ambiguous.
- **No placeholder left.** A command an agent proposes for you writes what only you can supply in angle brackets — `<the defect reference>`, `<your name>`; the stamp refuses to write one still holding it.

## 5. Land it with the answers

Commit the record in the same change as the answers on the artefacts it covers. The record never clears friction itself — only the artefacts' revalidations and deferrals do — and `pkit analysis validate` holds it to its schema and to the artefacts it cites.
