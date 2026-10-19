# Adding a journey

A journey is an end-to-end path one actor takes across several use cases, including the seams between them where the path can break. It is a file, `JRN-NNN-<slug>.md`, numbered within the project.

## 1. Is it a journey?

Write one when an actor's real goal spans use cases — onboarding, a first release, a month-end close — and what carries over from one use case to the next can break. A single use case with variants is not a journey.

## 2. Name the actor and the steps

- **The actor** — the one who takes the whole path; in the analysis and in force.
- **The steps** — the use cases it passes through, in order, at least two, each in force and each the actor's own: its `actor` is the journey's. A use case the actor only takes part in is another actor's, and the stamp and the check refuse it as a step. A use case may appear more than once. Stamp missing use cases first (`use-case.md`).
- **What it relies on outside it** — each use case outside the journey that a step needs something from, of any actor, with `--relies-on <UC-id>`: one that set something up the path takes over, say. None of the steps is one. Each is written in `relies-on` and anchored, and each needs a hand-over under the step that relies on it.

## 3. Choose the slug and the title

The path's goal, verb first — `first-run`, `month-end-close` — with `--title` as the heading reads it.

## 4. Decide what it rests on

The stamp writes the anchor to the actor, and the use-case anchors from the steps and `relies-on`. Add as `--path` the code at the **seams**: where state passes from one use case to the next — a file one writes and the next reads, a session, a hand-over.

**`--requirement`** names a requirement that binds the journey's **whole path**, once for each, such as how long the whole path may take, end to end. Each must be in the analysis and in force. The stamp writes each in `requirements`, and anchors it (DEC-002 point 7).

- **A requirement that binds one step** is that step's use case's to list (`use-case.md`), not the journey's. Listed by both, one change would flag both for one obligation.
- **No check can tell the two apart.** Ask whether the requirement holds of the path as a whole, or of one use case on it. List it on the journey only for the whole path.

## 5. Stamp it

```
pkit analysis new journey <slug> --actor <ACT-id> --step <UC-id> --step <UC-id> [...] [--relies-on <UC-id>]... [--requirement <REQ-id>]... [--title "<Title>"] [--path <glob>]...
```

## 6. Fill it

Each part holds its hint, which says what goes there and gives an example. Fill each part as its hint says, and delete the hint. The stamp writes the step lines under **Steps**, one for each use case of `steps`. Keep them as written. The goal and each minimal guarantee name their source (the shared framing's "Name the source of what the system must do"). Write each concept by its term (the shared framing's "Use the glossary's terms").

Then run the checks in the shared framing's "After stamping": `pkit analysis validate --preview` first, and `pkit analysis check-numbers` before merging. A hand-over the check refuses is named in its message, with the label it expects.

## Later

`steps` and `relies-on` are the source. To change either, edit it and the use-case artefact anchors together; the check names the anchors to write when they differ, so the friction check always sees every use case the journey passes through or relies on. `requirements` is the source of its requirement anchors in the same way, and the change that withdraws a requirement takes it off the list, with its anchor.
