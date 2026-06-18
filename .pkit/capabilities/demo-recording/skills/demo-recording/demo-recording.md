---
name: demo-recording
description: Work with the demo-recording capability — record a screen-captured CLI demo, validate a storyboard, open just the recording windows, stop an in-flight recording, or author a new bundle, storyboard, or post-record hook. Composite skill per COR-020; dispatches to per-operation sub-procedures. macOS/iTerm2 for the recording operations; validate and the authoring operations are platform-neutral.
composes:
  - start.md
  - stop.md
  - validate.md
  - windows.md
  - new-bundle.md
  - storyboard-author.md
  - hook-author.md
gates:
  - COR-017
  - COR-020
reads:
  paths:
    - .pkit/capabilities/demo-recording/README.md
    - .pkit/capabilities/demo-recording/decisions/DEC-001-storyboard-as-executable-format.md
    - .pkit/capabilities/demo-recording/decisions/DEC-002-three-layer-plugin-architecture.md
    - .pkit/capabilities/demo-recording/decisions/DEC-004-platform-coupling-and-gate-placement.md
    - .pkit/capabilities/demo-recording/schemas/record-config.yaml
---

# Working with the demo-recording capability

This is the **demo-recording capability** engine skill. It composes the operations that drive the recording engine over a demo bundle and author the bundle's content: they share the `record.yaml` configuration, the executable storyboard document format, and the macOS/iTerm2 recording machinery.

Pick the operation that fits the request:

## Drive the engine

| Operation | When to use it | Sub-procedure |
|---|---|---|
| **Record a demo** | Capture a screen-recorded run of a storyboard — open the windows, start capture, drive the storyboard, stop and post-process. | `start.md` |
| **Validate a storyboard** | Before recording, or as a CI / pre-commit check — confirm the storyboard's syntax and print the resolved step plan. Platform-neutral. | `validate.md` |
| **Open the windows only** | Set up the RECORDING + CONTROL windows without recording (manual rehearsal, geometry tuning). | `windows.md` |
| **Stop a recording** | Stop an in-flight recording started in another terminal. | `stop.md` |

## Author bundle content

| Operation | When to use it | Sub-procedure |
|---|---|---|
| **Author a new bundle** | Scaffold a new adopter-side demo bundle — its directory, `record.yaml`, storyboards skeleton, and hooks. | `new-bundle.md` |
| **Author a storyboard** | Write or extend an executable storyboard against the document format + the recording directive vocabulary. | `storyboard-author.md` |
| **Author a post-record hook** | Write an `after_record` hook against the `DCR_*` env-var contract. | `hook-author.md` |

Engine operations operate on an existing bundle; authoring operations produce the bundle content the engine consumes.

## Shared framing (applies to every operation)

### Acceptance gate

Verify the records in `gates:` are `accepted`:

- **COR-017** — capability pattern. demo-recording is a capability; its installed state is what surfaces the `pkit demo-recording <command>` dispatch.
- **COR-020** — composite-skill folder form. The convention this skill follows: this dispatcher carries the shared framing; each sub-procedure carries the per-operation walkthrough.

Halt if any is `proposed` or `superseded`.

### Conventions every operation respects

- **The storyboard IS the executable form** (per [demo-recording:DEC-001-storyboard-as-executable-format]). The markdown file an author reads is the file the engine runs; there is no separate generated artifact.
- **The format is generic; recording is one plugin** (per [demo-recording:DEC-002-three-layer-plugin-architecture]). The parser knows only steps + fenced blocks; the recording plugin owns the `boot`/`panes`/`narrate`/`shell`/… directive vocabulary. New backends register as additional plugins without touching the format.
- **Surface via the CLI dispatch, not direct paths.** Prefer `pkit demo-recording record|run|validate …` over invoking `scripts/*.sh` by path. The dispatcher execs the bash leaves; the scripts self-resolve their siblings via `dirname "${BASH_SOURCE[0]}"`.
- **Platform boundary** (per [demo-recording:DEC-004-platform-coupling-and-gate-placement]). The recording operations (record / windows / stop) require macOS + iTerm2 and refuse cleanly elsewhere; **validate and the authoring operations are platform-neutral** and run anywhere. The platform gate lives at the recording-plugin boundary, not the capability entry.
- **`record.yaml`, storyboards, and hooks are adopter content.** The engine reads a bundle's `record.yaml` (modelled by the `record-config` schema); the bundle, its storyboards, and its hooks live in the adopter's tree, not the capability. See the README's adopter-vs-capability boundary.

### Routing to the sub-procedure

After confirming the gates and identifying the operation, read the matching sub-procedure file in this folder (`start.md`, `validate.md`, `windows.md`, `stop.md`, `new-bundle.md`, `storyboard-author.md`, or `hook-author.md`) and follow its walkthrough. The shared framing above applies; the sub-procedure adds the operation-specific steps.
