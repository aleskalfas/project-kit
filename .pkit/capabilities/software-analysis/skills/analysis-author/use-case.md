# Adding a use case

A use case is one actor's goal and how the system fulfils it: when it starts, the main path, the variants, and when it is done. It is a file, `UC-NNN-<slug>.md`, numbered within the project whatever area it sits in.

## 1. One actor, one goal

Two actors with the same goal are two use cases, or the goal belongs to a third actor they both are. A goal that takes the actor through several use cases, with seams between them, is a journey over those use cases — write the use cases first.

## 2. Name the actor

The actor must be in the analysis and in force; stamp it first (`actor.md`) if it is not. The stamp refuses an actor that is missing or withdrawn.

## 3. Choose the slug, the title and the area

- **Slug** — the goal, verb first: `run-suite`, `export-report`. It names the file only.
- **`--title`** — the goal as the heading reads it: `Export the report as a file`. The heading is `# UC-NNN — <title>`, and the check keeps the two in step.
- **`--area <word>`** — a folder per functional area, when the project groups use cases. Moving a use case to another area later never changes its id; a move renames the file, so revalidate it in the same change (COR-050 point 3).

## 4. Decide what it rests on

- **`--path`** — the code the use case exercises: the entry point and the files doing the behaviour its steps describe.
- **`--record`** — the decisions its steps rely on.

The actor anchor is written by the stamp.

## 5. Stamp it

```
pkit analysis new use-case <slug> --actor <ACT-id> [--title "<Title>"] [--area <area>] [--path <glob>]... [--record <id>]...
```

It takes the next free number on the default branch and in the working tree.

## 6. Fill it

- **Goal** — what the actor wants, in one sentence.
- **Starts when** — what triggers it.
- **Main path** — numbered steps, each what the actor or the system does. Quote in backticks the commands, flags, functions and messages a step names.
- **Variants** — each lettered after the step it branches from (`2a`, `2b`): the condition, what happens instead, and where the path rejoins or ends.
- **Done when** — the state that shows the goal is met.

Then run the checks in the shared framing's "After stamping", including `pkit analysis check-numbers` before merging.

## Later

Steps and variants are **only ever added**, never renumbered: journeys and evidence cite them. A step that no longer happens stays in place, its number kept, marked withdrawn. A use case no actor pursues any more is withdrawn, never deleted.
