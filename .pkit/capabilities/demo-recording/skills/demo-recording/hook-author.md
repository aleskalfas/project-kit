---
name: hook-author
description: Author an after_record hook — an adopter-side script the recording engine runs after a successful take, with the DCR_* environment contract (scenario, video path, config, repo root, front-matter meta). Use when a recorded demo needs post-record bookkeeping (link the video to an issue, upload it, update a session id).
gates:
  - COR-017
reads:
  paths:
    - .pkit/capabilities/demo-recording/README.md
    - .pkit/capabilities/demo-recording/schemas/record-config.yaml
---

# Authoring an after_record hook

An **after_record hook** is an adopter-side script the recording engine runs **after** a successful take — after the storyboard exits, screen capture stops, and ffmpeg post-processing completes. A `--no-recording` run captures no video, so it runs no hook. Hooks are where post-record bookkeeping lives: link the video to a work-tracker issue, upload it to a CDN, stamp a replay session id. They are adopter content; the capability ships only the contract and the runner.

## Acceptance gate

Verify **COR-017** (capability pattern) is `accepted`. Halt if not.

## Declaring hooks

List hook scripts under the bundle's `record.yaml`, in run order:

```yaml
hooks:
  after_record:
    - ./hooks/update-replay-session-id.sh
    - ./hooks/upload-to-cdn.sh
```

- Scripts run **sequentially in array order**.
- Relative paths resolve against `record.yaml`'s directory.
- Each script must be **executable** (`chmod +x`).

## The hook environment contract

Every hook runs with these environment variables set, and with its **working directory** at `DCR_REPO_ROOT` (the directory containing `record.yaml`), so relative paths in the hook resolve against the adopter project:

| Var | Value |
|---|---|
| `DCR_SCENARIO` | basename of the storyboard (e.g. `ai`, `human`, `replay`) |
| `DCR_STORYBOARD` | absolute path to the storyboard `.md` |
| `DCR_VIDEO_PATH` | absolute path to the final video — `.mp4` when ffmpeg ran, `.mov` otherwise |
| `DCR_CONFIG` | absolute path to `record.yaml` |
| `DCR_REPO_ROOT` | directory containing `record.yaml`; also the hook's working directory |
| `DCR_META_<KEY>` | one entry per scalar key in the storyboard's front-matter, key upcased (e.g. `mode: ai` → `DCR_META_MODE=ai`) |

## Failure policy

A hook's non-zero exit **logs a warning to stderr but does not fail the recording** — by the time hooks run, the video is already on disk. Hooks are sugar on top of a take that already succeeded, not part of its success criteria. Write hooks defensively, but a hook crash will not lose the video.

## Procedure

### 1. Decide what the hook does

Name the post-record action: link to an issue, upload, notify, rename. If it needs to branch on which storyboard ran, plan to read a `DCR_META_*` var (and add the corresponding front-matter key to the storyboards that need it).

### 2. Write the script

Start from the contract. A skeleton that branches on front-matter mode:

```bash
#!/usr/bin/env bash
set -euo pipefail

case "${DCR_META_MODE:-}" in
    ai|human)
        echo "post-record: ${DCR_META_MODE} recording landed at ${DCR_VIDEO_PATH}"
        # ... project-specific bookkeeping, run from DCR_REPO_ROOT
        ;;
    *)
        # nothing to do
        ;;
esac
```

Hooks run only after a recorded take, so `DCR_VIDEO_PATH` always names the saved video.

### 3. Make it executable + wire it in

```
chmod +x demo/<bundle>/hooks/<hook>.sh
```

Add its path to `record.yaml`'s `hooks.after_record`. Re-validate the config (`pkit data validate demo/<bundle>/record.yaml`).

### 4. Test

Run a recorded take: `--no-recording` runs no hook, so it cannot exercise one. To try the hook without a take, run it by hand from `DCR_REPO_ROOT` with the `DCR_*` variables set. Confirm the hook fires and its bookkeeping lands. Because failures are non-fatal, check the engine's stderr for any hook warning.

## Notes

- The cross-capability seam (e.g. linking a recording to a work-tracker issue) lives **in the hook**, not as a capability dependency — the engine stays unaware of what the hook does. This keeps `demo-recording` free of a `requires_capabilities` edge on the work tracker.
- Keep hooks idempotent where they mutate external state, so a re-run of a take doesn't double-apply.
