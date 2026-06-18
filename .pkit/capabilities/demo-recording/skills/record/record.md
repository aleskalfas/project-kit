---
name: record
description: Drive the demo-recording engine — record a screen-captured CLI demo, validate a storyboard, open just the recording windows, or stop an in-flight recording. Composite skill per COR-020; dispatches to per-operation sub-procedures. macOS/iTerm2 for the recording operations; validate is platform-neutral.
composes:
  - start.md
  - stop.md
  - validate.md
  - windows.md
gates:
  - COR-017
  - COR-020
reads:
  paths:
    - .pkit/capabilities/demo-recording/README.md
    - .pkit/capabilities/demo-recording/decisions/DEC-001-storyboard-as-executable-format.md
    - .pkit/capabilities/demo-recording/decisions/DEC-004-platform-coupling-and-gate-placement.md
    - .pkit/capabilities/demo-recording/schemas/record-config.yaml
---

# Driving the demo-recording engine

This is the **demo-recording capability** operating skill. It composes the operations that drive the recording engine over a demo bundle: they share the `record.yaml` configuration, the storyboard document format, and the macOS/iTerm2 recording machinery.

Pick the operation that fits the request:

| Operation | When to use it | Sub-procedure |
|---|---|---|
| **Record a demo** | Capture a screen-recorded run of a storyboard — open the windows, start capture, drive the storyboard, stop and post-process. | `start.md` |
| **Validate a storyboard** | Before recording, or as a CI/pre-commit check — confirm the storyboard's syntax and print the resolved step plan. Platform-neutral. | `validate.md` |
| **Open the windows only** | Set up the RECORDING + CONTROL windows without recording (manual rehearsal, geometry tuning). | `windows.md` |
| **Stop a recording** | Stop an in-flight recording started in another terminal. | `stop.md` |

If the request is to *author* a storyboard, a bundle, or a hook — not to drive the engine — use `demo-storyboard-author`, `new-bundle`, or `hook-author` instead.

## Shared framing (applies to every operation)

### Acceptance gate

Verify the records in `gates:` are `accepted`:

- **COR-017** — capability pattern. demo-recording is a capability; its installed state is what surfaces the `pkit demo-recording <command>` dispatch.
- **COR-020** — skill family folder form. The convention this composite skill follows.

Halt if any is `proposed` or `superseded`.

### Conventions every operation respects

- **The storyboard IS the executable form** (per [demo-recording:DEC-001-storyboard-as-executable-format]). The markdown file an author reads is the file the engine runs; there is no separate generated artifact.
- **Surface via the CLI dispatch, not direct paths.** Prefer `pkit demo-recording record|run|validate …` over invoking `scripts/*.sh` by path. The dispatcher execs the bash leaves; the scripts self-resolve their siblings via `dirname "${BASH_SOURCE[0]}"`.
- **Platform boundary** (per [demo-recording:DEC-004-platform-coupling-and-gate-placement]). The recording operations (start / windows / stop) require macOS + iTerm2 and refuse cleanly elsewhere; **validate is platform-neutral** and runs anywhere.
- **`record.yaml` is adopter content.** The engine reads a bundle's `record.yaml` (modelled by the `record-config` schema); the bundle, its storyboards, and its hooks live in the adopter's tree, not the capability. See the README's adopter-vs-capability boundary.

### Routing to the sub-procedure

After confirming the gates and identifying the operation, read the matching sub-procedure file (`start.md`, `validate.md`, `windows.md`, or `stop.md`) and follow its walkthrough. The shared framing above applies; the sub-procedure adds the operation-specific steps.
