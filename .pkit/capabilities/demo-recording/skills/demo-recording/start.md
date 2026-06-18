# Record a demo

Capture a screen-recorded run of a storyboard: open the two iTerm2 windows at the bundle's configured bounds, start screen capture, drive the storyboard step-by-step, then stop and post-process.

## Preconditions

- macOS + iTerm2 (the recording machinery is macOS-only per [demo-recording:DEC-004-platform-coupling-and-gate-placement]).
- Accessibility + Screen Recording permission granted to the controlling terminal app (System Settings → Privacy & Security).
- A demo bundle exists with a `record.yaml` (per the `record-config` schema) and at least one storyboard `.md`. If not, scaffold one with the `new-bundle` skill.
- The storyboard validates clean. Run `validate.md` first if unsure — it is cheap and platform-neutral.

## Procedure

1. **Validate first.** Always run `pkit demo-recording validate <storyboard.md>` (or the bundle wrapper's `--validate`) before a take. A typo that the parser would reject is far cheaper to catch before the windows open.

2. **Start the recording.** From the bundle, run its wrapper (which passes `--config <bundle>/record.yaml`), or invoke the engine directly:

   ```
   pkit demo-recording record <demo> --config <bundle>/record.yaml
   ```

   `<demo>` is either a path to a storyboard `.md` or a bare name resolved against the config directory (`<name>.md`, then `storyboards/<name>.md`).

3. **Pick the interaction mode.**
   - **Autonomous (default).** Recording starts on dispatch and stops automatically when the storyboard finishes. This is the right default for AI/replay storyboards and CI — no operator keystrokes needed.
   - **`--interactive`.** Adds Enter gates: the operator presses Enter in CONTROL to start, and again to stop, so they can read the dispatch summary and abort with Ctrl-C. Use when rehearsing or inspecting.
   - **`--no-recording`.** Drives the storyboard without screen capture (dry rehearsal of the choreography).

4. **Drive the take.** The engine opens RECORDING (visible in the video) and CONTROL (off-region, drives the take). It dispatches the session into CONTROL, brings RECORDING frontmost once, and types each directive into the bound pane. A `wait` directive pauses for the operator's Enter in CONTROL; otherwise the run is hands-off.

5. **Finish.** On completion (autonomous) or on the operator's Enter (`--interactive`), the recording stops, the `.mov` is saved, optional ffmpeg post-processing produces a smaller `.mp4` with corrected colour, and any `after_record` hooks run. The video lands in the bundle's `recordings_dir`.

## Notes

- **Diagnostics.** A per-take log lands at `<recordings_dir>/.logs/<timestamp>-<demo>.log`. Tail it in another terminal (`tail -f <path>`) if a take goes sideways. Override with `DCR_LOG`.
- **Abort anytime.** Ctrl-C in CONTROL stops the recording cleanly via the session's SIGINT trap.
- **Tunables** (env vars, per invocation): `FOCUS_DELAY`, `MIN_MS`/`MAX_MS`, `CHUNK_SIZE`, `REVIEW_PAUSE`, `PRE_RUN_PAUSE` control typing cadence; `DCR_CRF`, `DCR_NO_REENCODE`, `DCR_KEEP_MOV` control post-processing. See the README's tunables table.
