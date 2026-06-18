---
name: new-bundle
description: Scaffold a new adopter-side demo bundle — a directory with a record.yaml (per the record-config schema), a storyboards/ folder, and an optional hooks/ folder — for recording one CLI demo. Use when an adopter starts a new screen-recorded demo for their project.
gates:
  - COR-017
reads:
  paths:
    - .pkit/capabilities/demo-recording/README.md
    - .pkit/capabilities/demo-recording/schemas/record-config.yaml
    - .pkit/capabilities/demo-recording/schemas/record-config.schema.json
    - .pkit/capabilities/demo-recording/decisions/DEC-001-storyboard-as-executable-format.md
---

# Scaffold a new demo bundle

A **demo bundle** is adopter-side content: a directory holding everything specific to one recorded CLI demo. The capability ships the recording engine; the bundle holds the demo's configuration, its storyboards, and its hooks. This skill walks through laying one out.

## When this skill applies

Reach for it when an adopter wants to record a new CLI demo of their project — a fresh `record.yaml` + storyboard(s) + (optionally) post-record hooks. It does not author the recording engine (that is the capability) and it does not record (that is the `record` skill).

## Acceptance gate

Verify **COR-017** (capability pattern) is `accepted` — the adopter-vs-capability boundary this skill respects is fixed there and in the capability README. Halt if not.

## The bundle layout

Lay the bundle out under the adopter's own demo area (conventionally `demo/<name>/`):

```
demo/<name>/
├── record.yaml        # per-bundle config (record-config schema)
├── record.sh          # OPTIONAL thin wrapper: exec the engine with --config record.yaml
├── storyboards/       # the executable storyboard .md files (author with the storyboard-author operation)
│   └── <demo>.md
├── hooks/             # OPTIONAL post-record hooks (author with hook-author)
│   └── <hook>.sh
└── recordings/        # output dir (.mov + .mp4); created on first take
```

The bundle is **adopter content** and stays in the adopter's tree — the capability never takes it over (per [demo-recording:DEC-001-storyboard-as-executable-format] and the README's boundary).

## Procedure

### 1. Create the bundle directory

Pick a kebab-case name describing the demo (e.g. `quickstart`, `replay`, `ai-operator`). Create `demo/<name>/storyboards/`.

### 2. Author `record.yaml`

Start from the `record-config` schema's worked example (the example record.yaml carried in the schema YAML, declared in this skill's reads). The shape:

```yaml
pkit_schema: demo-recording:record-config
schema_version: 1
cwd: /abs/path/the/demo/drives          # REQUIRED — windows cd here
windows:                                # REQUIRED — iTerm bounds [left, top, right, bottom]
  recording: [50, 50, 1330, 850]
  control:   [50, 880, 750, 1150]
recordings_dir: ./recordings            # optional (default ./recordings)
font_size: 18                           # optional
font_name: Menlo-Regular                # optional
hooks:                                  # optional
  after_record:
    - ./hooks/<hook>.sh
```

The `pkit_schema:` line binds the file to the schema so `pkit data validate <path>` can check it; the `binds_to:` fallback in the schema also matches `**/record.yaml`. Validate the config:

```
pkit data validate demo/<name>/record.yaml
```

### 3. (Optional) Add a thin wrapper `record.sh`

A one-line wrapper keeps invocation terse and pins the config:

```bash
#!/usr/bin/env bash
exec pkit demo-recording record --config "$(dirname "$0")/record.yaml" "$@"
```

This is optional sugar — adopters can also invoke `pkit demo-recording record … --config demo/<name>/record.yaml` directly.

### 4. Author the first storyboard

Use the `demo-recording` skill's `storyboard-author` operation to write `storyboards/<demo>.md`. Validate it:

```
pkit demo-recording validate demo/<name>/storyboards/<demo>.md
```

### 5. (Optional) Author hooks

If the demo needs post-record bookkeeping (link the video to an issue, upload it, etc.), use the `hook-author` skill and list each hook under `record.yaml`'s `hooks.after_record`.

### 6. Record

Drive a take with the `record` skill. The video lands in `recordings/`.

## Notes

- Multiple bundles can coexist under `demo/` — one directory per demo. A short README under the demo area indexing them is a useful adopter convention.
- Keep `recordings/` out of version control if the videos are large; commit only what the project wants to keep.
