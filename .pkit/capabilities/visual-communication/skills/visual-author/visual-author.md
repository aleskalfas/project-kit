---
name: visual-author
description: Draw a piece of visual work with the visual-communication capability. Start a figure or a presentation by bringing its libraries with `pkit visual add` and writing its `piece.yaml` and content by hand, choosing the top, the brand, the notation, the languages, the modes and the exports. Then work the build loop until the piece reads, through `pkit visual render`, `pkit visual check`, `pkit visual look` and `pkit visual pages`, mending the content first, then a local component, then a library. Composite skill per COR-020, with one sub-procedure for starting a piece and one for the build loop. Use when starting a piece, or when building, mending or reading one the project holds.
metadata:
  wraps_commands:
    - pkit visual add
    - pkit visual status
    - pkit visual render
    - pkit visual check
    - pkit visual look
    - pkit visual pages
    - pkit visual release
    - pkit validate
composes:
  - piece.md
  - build-loop.md
gates:
  - COR-020
  - COR-055
reads:
  paths:
    - .pkit/capabilities/visual-communication/decisions/DEC-001-visual-communication-discipline.md
    - .pkit/capabilities/visual-communication/decisions/DEC-002-files-and-validation.md
    - .pkit/capabilities/visual-communication/decisions/DEC-003-change-over-time.md
    - .pkit/capabilities/visual-communication/decisions/DEC-005-engine-and-plugins.md
    - .pkit/capabilities/visual-communication/decisions/DEC-015-viewing-step-and-reviewer.md
    - .pkit/capabilities/visual-communication/decisions/DEC-020-html-page-drawing.md
    - .pkit/capabilities/visual-communication/decisions/DEC-024-outside-programs-sandbox.md
    - .pkit/capabilities/visual-communication/README.md
    - .pkit/capabilities/visual-communication/files.md
    - .pkit/capabilities/visual-communication/components.md
    - .pkit/capabilities/visual-communication/outputs.md
    - .pkit/capabilities/visual-communication/checks.md
    - .pkit/capabilities/visual-communication/libraries/starter/README.md
---

# Drawing a piece

This is the **visual-communication** capability's skill for whoever draws a piece: a person, or an agent working for one. A *piece* is one finished item of visual work, such as a figure or a presentation.

- **The commands own what they write:** a copy of a library, the location, the lock, the findings record, the previews and the images.
- **This skill owns the choices:** which top, which brand, what the content says, what to read, what to mend, and when to stop.

No command writes a piece. You write its `piece.yaml` and its content by hand, and the commands read them.

The rule is [visual-communication:DEC-001-visual-communication-discipline]: content and look are data, and renderers only project them. How the files are kept and judged is [visual-communication:DEC-002-files-and-validation], how a lock moves is [visual-communication:DEC-003-change-over-time], and what a component may hold is [visual-communication:DEC-005-engine-and-plugins]. How drawn pages are seen is [visual-communication:DEC-015-viewing-step-and-reviewer]. Where a sandbox stops the browser that draws them, [visual-communication:DEC-024-outside-programs-sandbox] says how you go on.

Every command is under [Commands](../../README.md#commands) in the capability's README. Each file is in [The files of the visual work](../../files.md), each finding in [What the check reports](../../checks.md).

## Acceptance gate

Verify each record in `gates:` is `accepted`. Halt if any is `proposed` or `superseded`.

- **COR-020**: the composite folder form this skill follows.
- **COR-055**: validation is one check that installed components join. The capability's check is one of its members.

## Pick the operation

| You want to | Sub-procedure | Commands |
|---|---|---|
| Start a piece: bring its libraries, write its files, draw it once | `piece.md` | `pkit visual add <library>`, `pkit visual render <piece>` |
| Build a piece that holds a lock: draw it, judge it, read it and mend it, until it can stop | `build-loop.md` | `pkit visual render <piece>`, `pkit visual check <piece>`, `pkit visual pages <piece>`, `pkit visual look <piece>` |

Open the matching sub-procedure in this folder and follow it. The framing below applies to both.

## Shared framing

- **Where the work lies.** `pkit visual status` shows the location and each piece, with its state and its lock. It writes nothing. Run it first in a project you do not know.
- **Where to run a command.** Every command runs from anywhere in the project.
- **A refused command** prints `error: …` and exits 1, and it has written nothing. Mend what it names, and run it again.
- **What stays local.** The previews and the images lie in the clone's local folder, and no commit holds them ([The clone's local folder](../../files.md#the-clones-local-folder)).
- **What this skill leaves out.** A piece that is drawn and read goes on to `pkit visual export`, under [Commands](../../README.md#commands). A brand of the project's own is under [Brands](../../files.md#brands).
