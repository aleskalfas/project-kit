---
name: storyboard-author
description: Author an executable demo storyboard — a markdown document with step headings and fenced recording directives that the engine both reads and runs. Distinct from the core storyboard-author skill (COR-016 scripted-scenario storyboards), which is a different sense of "storyboard". Use when writing or revising a screen-recorded CLI demo's script.
gates:
  - COR-017
reads:
  paths:
    - .pkit/capabilities/demo-recording/README.md
    - .pkit/capabilities/demo-recording/decisions/DEC-001-storyboard-as-executable-format.md
    - .pkit/capabilities/demo-recording/decisions/DEC-002-three-layer-plugin-architecture.md
  records:
    - COR-016
---

# Authoring an executable demo storyboard

A **demo storyboard** is a plain markdown document that is **also the executable form** of a screen-recorded CLI demo (per [demo-recording:DEC-001-storyboard-as-executable-format]). The same file a colleague reads to understand the demo is the file the engine drives — there is no separate driver script and no generation step. It reads like a script for a play; fenced code blocks carry the directives the recording engine executes.

## Naming — two senses of "storyboard"

This is **not** the methodology's COR-016 *scripted-scenario* storyboard (a narrative behaviour spec an agent reads). This skill authors an *executable demo* storyboard. The two senses are deliberately kept distinct: this is the `storyboard-author` operation of the `demo-recording` capability — namespaced under that composite skill, so it doesn't collide with the methodology's top-level core `storyboard-author` skill. If the task is a behaviour-narrative spec, use the core `storyboard-author` skill instead.

## Acceptance gate

Verify **COR-017** (capability pattern) is `accepted`. Halt if not.

## The document format

```markdown
---                                  # optional YAML front-matter (scalars only)
mode: ai
---

# Title of the demo                  # required H1

Optional intro prose. Read by colleagues; ignored by the engine.

## Step 1 — short title              # steps delimited by `## Step N — <title>`

Optional prose describing the step.

```<directive>
<directive content>
```

## Step 2 — next thing
...
```

Rules:
- The **H1 title is required**.
- Steps are `## Step N — <title>`. `N` is a unique integer (need not be contiguous).
- A step body is any prose plus zero or more fenced directive blocks.
- **Unknown directive tags are warnings, not errors** — a storyboard stays readable without the plugin loaded (per [demo-recording:DEC-002-three-layer-plugin-architecture]).

### Front-matter (optional)

A leading `---`-delimited block of **scalar `key: value` pairs only** (no nesting, lists, or quoted values). Each scalar is projected to an `after_record` hook as `DCR_META_<KEY>` (key upcased) — see the README's hook contract. Use it only when hooks need to differentiate behaviour per storyboard; omit it otherwise.

## The recording directive vocabulary

Each fenced block's language tag names a directive the recording plugin owns:

| Tag | Purpose | Content |
|---|---|---|
| `boot` | Pre-tmux startup: narrate into the bare shell, wipe the line, run the command | `narration:` (scalar or `|` block) + `command:` |
| `panes` | Bind logical roles to tmux pane numbers (state-mutating; re-issue if topology changes) | `<role>: <int>` lines |
| `narrate` | Type into the pane bound to the `narrate` role (the thoughts pane) | plain text |
| `chat` | Type into the pane bound to the `chat` role (the AI TUI) | plain text |
| `shell` | Type a bash command into the pane bound to the `shell` role and run it | plain text |
| `wait` | Pause until the operator presses Enter in CONTROL | operator hint text |
| `ready` | Poll the RECORDING window's text; advance when a *new* occurrence of a pattern appears | terse pattern, or `pattern:` + optional `timeout:` |
| `keys` | Send modifier-key chords (e.g. `ctrl+b`, `Enter`) to the focused pane | one chord per line; modifiers chain with `+` |
| `sleep` | Fixed wall-clock pause (auto-advance, with a countdown) | a positive integer of seconds |

The full per-directive spec — including `boot`'s block-scalar form, `ready`'s "wait for new occurrence" semantics and sentinel pattern, and the `panes` → automatic `C-b q <N>` pane selection — is in the capability README. Read it before writing non-trivial storyboards.

## Procedure

### 1. Frame the demo as ordered beats

A CLI demo is a linear script (this is why the executable-prose medium fits, per [demo-recording:DEC-001-storyboard-as-executable-format]). Sketch the beats: what does the audience see first, what gets typed, what does the demo wait on, how does it end. Each beat becomes a `## Step N`.

### 2. Write the title + intro

An H1 that names the demo, and a sentence or two of intro prose so a reader understands the demo without running it.

### 3. Write each step

For each beat: a `## Step N — <title>`, a line of prose explaining it, and the directive(s) that drive it. Bind panes once with a `panes` block before the first `narrate`/`chat`/`shell`; re-issue if the topology changes.

### 4. Choose the right wait directive

When a step depends on something completing, pick deliberately:
- **`ready`** — there is a programmatic completion signal (a tmux mode marker, or an assistant sentinel like `STATS-READY` appended to the chat request). Preferred when a signal exists.
- **`sleep`** — the duration is known up front ("let the replay play 20s").
- **`wait`** — the time is genuinely unknown and an operator will judge it. Note: `wait` requires a human at the keyboard, so avoid it in autonomous/CI storyboards.

### 5. Validate

```
pkit demo-recording validate <storyboard.md>
```

Fix every error; resolve unknown-directive warnings (usually a typo'd tag). Re-run until clean. A clean validate is a strong signal the take will dispatch.

### 6. (Optional) Rehearse without recording

`pkit demo-recording record <demo> --config … --no-recording` drives the choreography without capturing video — a fast way to feel the pacing before a real take.

## Notes

- Keep narration short and readable; the audience reads it on screen at typing pace.
- Use distinctive all-caps-hyphenated sentinels (`STATS-READY`, `WORK-COMPLETE`) with `ready` so the poll can't false-match.
- Tunables (typing cadence, review pauses) are env vars at record time, not storyboard content — keep timing concerns out of the document.
