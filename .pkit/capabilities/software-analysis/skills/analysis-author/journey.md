# Adding a journey

A journey is an end-to-end path one actor takes across several use cases, including the seams between them where the path can break. It is a file, `JRN-NNN-<slug>.md`, numbered within the project.

## 1. Is it a journey?

Write one when an actor's real goal spans use cases — onboarding, a first release, a month-end close — and what carries over from one use case to the next can break. A single use case with variants is not a journey.

## 2. Name the actor and the steps

- **The actor** — the one who takes the whole path; in the analysis and in force.
- **The steps** — the use cases it passes through, in order, at least two, each in force. A use case may appear more than once. Stamp missing use cases first (`use-case.md`).

## 3. Choose the slug and the title

The path's goal, verb first — `first-run`, `month-end-close` — with `--title` as the heading reads it.

## 4. Decide what it rests on

The use-case anchors are written from the steps by the stamp. Add as `--path` the code at the **seams**: where state passes from one use case to the next — a file one writes and the next reads, a session, a hand-over.

## 5. Stamp it

```
pkit analysis new journey <slug> --actor <ACT-id> --step <UC-id> --step <UC-id> [...] [--title "<Title>"] [--path <glob>]...
```

## 6. Fill it

- **Starts** — where the actor begins, and what they want by the end.
- **Steps** — one line per step, what the actor achieves in that use case.
- **Seams to watch** — for each pair of steps, what must carry over and how it could break.
- **Done when** — the state that shows the whole path succeeded.

Then run the checks in the shared framing's "After stamping", including `pkit analysis check-numbers` before merging.

## Later

`steps` is the source. To change them, edit `steps` and the use-case artefact anchors together; the check names the anchors to write when the two differ, so the friction check always sees every use case the journey passes through.
