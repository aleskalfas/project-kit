# Stop a recording

Stop an in-flight recording — useful when the take was started in another terminal (autonomous mode), or when you want to end a recording early from any shell.

## Preconditions

- macOS (this is a recording operation, gated to darwin per [demo-recording:DEC-004-platform-coupling-and-gate-placement]).
- An active recording — i.e. a state file exists (written when a take started). If none exists, stop is a clean no-op with a message.

## Procedure

1. **Stop the recording:**

   ```
   pkit demo-recording record stop --config <bundle>/record.yaml
   ```

   (Or the bundle wrapper's `stop` subcommand.)

2. **What happens.** The engine sends SIGINT to the screen-capture process, waits for the `.mov` to flush, runs ffmpeg post-processing (`.mov` → smaller `.mp4` with corrected colour) when ffmpeg is available, runs any `after_record` hooks, and closes the RECORDING + CONTROL windows.

## Notes

- There are three ways to stop a take: this `stop` command (from any terminal), Ctrl-C in CONTROL (the session's SIGINT trap), or — in `--interactive` mode — the post-demo Enter prompt. They converge on the same teardown.
- Hook failures log a warning but do **not** fail the stop: by the time hooks run, the video is already on disk (per the after_record contract in the README).
