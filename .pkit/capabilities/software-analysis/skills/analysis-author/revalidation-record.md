# Recording a revalidation

A **revalidation** is one check of some artefacts against one version of the system — a proposed design, or the code. Its answer for each artefact is written on the artefact itself, and that answer is what clears friction. A **record** is written beside it only when the revalidation has something to say: it is a file, `revalidations/<date>-<slug>.md`, citing artefacts by id.

## 1. Does it need a record?

Only when it has something to say: the one table of when is the capability README's [Revalidation records](../../README.md#revalidation-records). The stamp refuses a record with nothing to say, so that the few records that matter are never buried among routine ones.

## 2. Give each artefact its answer

Each artefact covered ends in one of four outcomes, and each maps onto the answer the core records on the artefact (DEC-001 point 5):

| Outcome | It means | The answer on the artefact |
|---|---|---|
| `holds` | the description still stands | `pkit friction revalidate <artefact> --outcome unchanged --because "<why it still holds against this change>"` |
| `analysis-stale` | the change was meant; the description is out of date | edit the artefact, then `pkit friction revalidate <artefact> --outcome updated` |
| `code-regressed` | the description is still what is wanted; the change broke it | report the defect, then `pkit friction revalidate <artefact> --outcome unchanged --because "<the description stands; defect <ref> reported>"` |
| `gap-found` | behaviour nothing describes, or a description with no behaviour | `--outcome updated` where the artefact itself changed; `--outcome unchanged --because "<the gap, and the artefact that fills it>"` where a new artefact closes it |

**A regression is never answered by rewriting the artefact to match the code.** When you cannot tell whether the change was meant — stale, or regressed — a person who knows the intent decides before anything is recorded.

Friction you choose not to resolve yet is not an outcome: defer the anchor with its reason, `pkit friction defer <artefact> --anchor <kind:value> --reason "<why it can wait>"`. It stays in the debt listing until someone revalidates.

## 3. Choose the slug

The subject of the change, as a word: `export-dropped`, `report-redesign`. The file is named by the day and the subject, never numbered, so two lines of work cannot collide; the stamp refuses a subject already recorded that day.

## 4. Stamp the record

```
pkit analysis new revalidation <slug> --change <ref> --trigger <planned|drift|scheduled|close|onboarding>
    --outcome <id>=<outcome>... --because <id>=<why>...
    [--gap "<what was found> => <the defect reported, or the artefact written>"]...
    [--by <who> | --by-agent <name>] [--confirmed-by <who>] [--title "<Subject>"]
```

- **`--change`** — what carried it: a work item (`#123`), a pull request, or a range of commits.
- **`--trigger`** — `planned` before code; `drift` on a pull request's friction; `scheduled` for friction the whole-repository check found; `close` when a pull request changing artefacts lands; `onboarding`.
- **`--outcome`** — each artefact covered, withdrawn ones included, and how it ended.
- **`--because`** — each outcome's justification, one per `--outcome`: the stamp refuses an outcome without one.
- **`--gap`** — each gap and what resolved it, as one pair: `"<gap> => <resolution>"`. A regression or a gap found must name at least one.
- **`--by`** — the person who performed it (git's user name by default); **`--by-agent`** — the agent that did, which needs **`--confirmed-by`**: the person who confirmed its outcomes, and decided stale against regressed where the two were ambiguous.
- **No placeholder left.** A command an agent proposes for you writes what only you can supply in angle brackets — `<the defect reference>`, `<your name>`; the stamp refuses to write one still holding it.

## 5. Land it with the answers

Commit the record in the same change as the answers on the artefacts it covers. The record never clears friction itself — only the artefacts' revalidations and deferrals do — and `pkit analysis validate` holds it to its schema and to the artefacts it cites.
