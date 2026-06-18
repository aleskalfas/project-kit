# demo-recording capability

Screen-recorded CLI demos, driven by an **executable markdown storyboard**. An author writes a plain markdown file — a title, step headings, and fenced directive blocks — and the engine both *reads* it (it renders as a coherent narrative in any markdown viewer) and *runs* it (typing narration and commands into a recording window on macOS). The same document is the script a colleague reads and the program the recorder executes. Install this when your project wants repeatable, consistently-framed recorded terminal demos without hand-writing keystroke-injection plumbing per demo.

The capability owns the generic storyboard format (parser + plugin interface + runner + validator) and the one macOS CLI-recording plugin as an internal module. It does **not** own your demos: storyboards, `record.yaml`, and hook scripts are adopter content (see [Adopter vs capability boundary](#adopter-vs-capability-boundary)).

## What this capability ships

When an adopter runs `pkit capabilities install demo-recording`, they receive:

- **Decisions** (`decisions/DEC-NNN-*.md`) — the four design choices the capability rests on:
  - `DEC-001-storyboard-as-executable-format` — the markdown document IS the executable form (vs a data-file + generator).
  - `DEC-002-three-layer-plugin-architecture` — parser / plugin interface / recording plugin, with the core knowing nothing domain-specific.
  - `DEC-003-single-capability-deferred-split` — ship one capability now; split the format from recording only when a second non-recording backend recurs (COR-007).
  - `DEC-004-platform-coupling-and-gate-placement` — assume macOS for v1; gate at the recording-plugin boundary; defer the portability abstraction.
- **Schema** (`schemas/record-config.{yaml,schema.json}`) — the `record.yaml` shape (per-bundle recording configuration). Adopter `record.yaml` files bind to it (per COR-023).
- **Scripts** (`scripts/`) — the recording engine:
  - `record.sh` — entry point (config parse + windows + recording lifecycle).
  - `run-storyboard.sh` — the step walker (drives a storyboard without/with recording).
  - `validate.sh` — platform-neutral storyboard validation.
  - `storyboards/` — Layer 1+2: `parser.py` (markdown → tree), `plugin.py` (Plugin ABC + registry), `runner.py` (CLI entry).
  - `plugins/recording/` — Layer 3: `directives.py` (the recording vocabulary), `lib.sh` (keystroke + pane primitives), `setup-windows.sh`, `_session.sh`, `post-demo.sh`, `ffmpeg_post.sh`, and `platform-guard.sh` (the single macOS gate).
- **Skills** (`skills/`):
  - `record/` — composite skill (per COR-020): `start` / `validate` / `windows` / `stop`.
  - `new-bundle` — scaffold an adopter demo bundle (`record.yaml` + `storyboards/` + `hooks/`).
  - `demo-storyboard-author` — author an executable demo storyboard (named distinctly from the core COR-016 scripted-scenario `storyboard-author`).
  - `hook-author` — author an `after_record` hook against the `DCR_*` contract.

## CLI surface

The capability declares three commands via the CLI dispatch (per COR-021); once installed they surface under `pkit demo-recording`:

| Command | Does |
|---|---|
| `pkit demo-recording record <demo> --config <bundle>/record.yaml` | Open the windows, start screen capture, drive the storyboard, stop + post-process. Sub-actions: `windows`, `stop`; flags `--validate`, `--no-recording`, `--interactive`. |
| `pkit demo-recording run <storyboard.md>` | Drive a storyboard step-by-step **without** screen recording. `--validate` to parse-and-print only. |
| `pkit demo-recording validate <storyboard.md>` | Validate a storyboard's syntax + print the resolved step plan. Read-only, **platform-neutral**. |

The dispatcher execs the bash leaves directly; the scripts self-resolve their siblings via `dirname "${BASH_SOURCE[0]}"`, which survives the dispatch proxy.

## Adopter setup

Install:

```
pkit capabilities install demo-recording
```

Then, per demo, scaffold a **bundle** (use the `new-bundle` skill). A bundle is a directory the adopter owns, conventionally under `demo/<name>/`:

```
demo/<name>/
├── record.yaml        # per-bundle config (record-config schema)
├── record.sh          # OPTIONAL thin wrapper: exec the engine with --config record.yaml
├── storyboards/       # the executable storyboard .md files
│   └── <demo>.md
├── hooks/             # OPTIONAL post-record hooks
└── recordings/        # output (.mov + .mp4); created on first take
```

Write storyboards with the `demo-storyboard-author` skill, hooks with `hook-author`, then record with the `record` skill.

## The storyboard format

A storyboard is a plain markdown document that reads like a script for a play; fenced code blocks carry the executable directives. The format is **intentionally general** — the core knows document structure (titles, steps, fenced blocks) but nothing about what any directive means; execution semantics live in the recording plugin (per `DEC-002`).

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
- Steps are `## Step N — <title>`; `N` is a unique integer (need not be contiguous).
- A step body is any prose plus zero or more fenced directive blocks.
- **Unknown directive tags are warnings, not errors** — a storyboard stays readable without the plugin present (the read-without-execute property, per `DEC-001`).

### Front-matter (optional)

If the file starts with `---` on line 1, the engine parses a YAML front-matter block of **scalar `key: value` pairs only** (no nesting, lists, or quoted values) until the next `---`. Each scalar is projected to `after_record` hooks as `DCR_META_<KEY>` (key upcased):

| Front-matter | Hook env var |
|---|---|
| `mode: ai` | `DCR_META_MODE=ai` |
| `target: production` | `DCR_META_TARGET=production` |

Front-matter is optional — omit it when you have no hooks that need to differentiate behaviour per storyboard.

## The recording directive vocabulary

The recording plugin owns these fence tags:

| Tag | Purpose | Required content |
|---|---|---|
| `boot` | Pre-tmux startup: narrate into the bare shell, wipe the line, run the command | `narration:` (scalar or `\|` block) + `command:` |
| `panes` | Bind logical roles to tmux pane numbers (state-mutating; re-issue on topology change) | `<role>: <int>` lines |
| `narrate` | Type into the pane bound to the `narrate` role (the thoughts pane) | plain text |
| `chat` | Type into the pane bound to the `chat` role (the AI TUI) | plain text |
| `shell` | Type a bash command into the pane bound to the `shell` role and run it | plain text |
| `wait` | Pause until the operator presses Enter in CONTROL | operator hint text |
| `ready` | Poll the RECORDING window's text; advance when a *new* occurrence of a pattern appears | terse pattern, or `pattern:` + optional `timeout:` (default 30s) |
| `keys` | Send modifier-key chords (e.g. `ctrl+b`, `Enter`) to the focused pane | one chord per line; modifiers chain with `+` |
| `sleep` | Fixed wall-clock pause (auto-advance, with a countdown) | a positive integer of seconds |

Notes on the subtler directives:

- **`boot`** narrates into the bare recording shell (the only surface before tmux panes exist), pauses so the audience reads it, wipes the line with Ctrl-U, then types and submits the command. `narration:` accepts a single line or a YAML `|` block scalar.
- **`panes`** is state-mutating: subsequent `narrate`/`chat`/`shell` directives use the most recent binding. Before typing into any of those targets, the engine sends `C-b q <N>` (tmux select-pane by number) automatically — no manual pane clicking.
- **`ready`** polls the RECORDING session's visible text every 0.5s and advances when the pattern's occurrence count strictly **increases** beyond what was visible when polling started. This "wait for a new occurrence" rule handles the common cases uniformly — a tmux status marker appearing (0 → 1), or an assistant emitting a sentinel the chat request already contained (1 → 2). Recommended: append `"…say <SENTINEL> when done"` to a `chat` request and poll for a distinctive token like `STATS-READY`.
- **`wait` vs `sleep` vs `ready`** — `wait` is operator-driven (Enter to advance; needs a human, so avoid in autonomous/CI takes); `sleep` is a known fixed duration; `ready` is a programmatic completion signal.

A storyboard runs **autonomously by default** (recording starts on dispatch, stops when the storyboard finishes) — the right default for AI/replay storyboards and CI. Pass `--interactive` for start/stop Enter gates when rehearsing.

## Hooks (`after_record`)

Optional scripts the engine runs **after** a successful recording — after the storyboard exits, capture stops, and ffmpeg post-processing completes. Declared in `record.yaml`:

```yaml
hooks:
  after_record:
    - ./hooks/update-replay-session-id.sh
    - ./hooks/upload-to-cdn.sh
```

Scripts run sequentially in array order; relative paths resolve against `record.yaml`'s directory; each must be executable.

### Hook environment contract

Every hook runs with its working directory at `DCR_REPO_ROOT` and these variables set:

| Var | Value |
|---|---|
| `DCR_SCENARIO` | basename of the storyboard (e.g. `ai`, `human`, `replay`) |
| `DCR_STORYBOARD` | absolute path to the storyboard `.md` |
| `DCR_VIDEO_PATH` | absolute path to the final video — `.mp4` when ffmpeg ran, `.mov` otherwise; **empty string** when `--no-recording` was passed |
| `DCR_CONFIG` | absolute path to `record.yaml` |
| `DCR_REPO_ROOT` | directory containing `record.yaml`; also the hook's working directory |
| `DCR_META_<KEY>` | one entry per scalar key in the storyboard's front-matter, key upcased |

### Failure policy

A hook's non-zero exit **logs a warning but does not fail the recording** — by the time hooks run, the video is already on disk. Hooks are sugar on top of a take that already succeeded.

The recording → work-tracker-issue linkage (e.g. an `update-replay-session-id.sh` that stamps an issue) lives **in the hook**, as adopter-bundle content — not as a capability dependency. The engine stays unaware of what hooks do, which keeps `demo-recording` free of a `requires_capabilities` edge.

## Tunables (env vars)

Typing cadence and post-processing are tuned via environment variables at record time, not via `record.yaml` (their migration into config is deferred — see the `record-config` schema):

| Var | Default | Effect |
|---|---|---|
| `FOCUS_DELAY` | `3` | Seconds between the operator's Enter and typing starting. |
| `MIN_MS` / `MAX_MS` | `15` / `40` | Per-chunk inter-keystroke jitter range. |
| `CHUNK_SIZE` | `4` | Characters per osascript call (higher = faster typing). |
| `REVIEW_PAUSE` | `0.6` | Seconds narration sits before the Ctrl-U wipe in `boot`. |
| `PRE_RUN_PAUSE` | `0.2` | Seconds between Ctrl-U and command typing. |
| `DCR_CRF` | `23` | H.264 quality for the `.mp4` re-encode (higher = smaller). |
| `DCR_NO_REENCODE` / `DCR_KEEP_MOV` / `DCR_NO_POSTPROCESS` | unset | Skip re-encode / keep the source `.mov` / skip post-processing entirely. |
| `DCR_LOG` / `DCR_DEBUG` | unset | Per-take diagnostic log path / enable debug logging. |

## Adopter vs capability boundary

The split is clean and load-bearing (per `DEC-001`):

- **The capability ships** the recording engine, the storyboard format, the one `record-config` schema, and the skills. This is reusable, project-neutral tooling.
- **The adopter owns** the bundles: each `record.yaml`, the storyboard `.md` files, the `hooks/*.sh`, and the `recordings/` output. These stay in the adopter's tree — the capability never takes them over. This mirrors how the project-management capability ships the issue-body *schema* while issue *bodies* are adopter content.

## Dependencies

- **macOS** (per `DEC-004`). The recording machinery uses `osascript` + System Events (keystroke injection), iTerm2 AppleScript (window control), and `screencapture`. Recording refuses cleanly off darwin; **storyboard validation is platform-neutral** and runs anywhere Python 3 runs.
- **iTerm2** — the window control is iTerm-specific.
- **Python 3.8+** — stdlib only, no pip dependencies.
- **ffmpeg** (optional) — for `.mov` → smaller `.mp4` re-encode with corrected colour. Recording works without it (the `.mov` is kept).
- **Accessibility + Screen Recording permission** for the controlling terminal app.

A Linux port would be a second recording backend behind the plugin seam — deferred until a Linux consumer recurs (per `DEC-004`).

## When the single capability splits

Today this is one capability: the generic format and the recording plugin ship together, with the internal three-layer seam (`DEC-002`) preserved but the package unified (`DEC-003`). The split into a standalone `executable-storyboards` format capability plus a `recording` capability is **deferred** until a second, independent, *non-recording* execution backend actually recurs — a discipline that wants the same step-plus-fenced-directive document with its own directive vocabulary, ships its own plugin against the Layer-2 interface, and would depend on the format. Absent that consumer, splitting would be the speculative extraction COR-007 forbids. The clean layering keeps the split cheap to do later, along the seam that already exists.

## Citing this capability's decisions

Inside this capability's content, cite decisions by their filename stem: `[demo-recording:DEC-001-storyboard-as-executable-format]`. Other capabilities and adopter content use the same form.
