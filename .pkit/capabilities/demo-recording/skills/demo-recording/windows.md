# Open the windows only

Open the RECORDING + CONTROL iTerm2 windows at the bundle's configured bounds, without starting a recording or driving a storyboard. Use for rehearsal, geometry tuning, or manually inspecting the layout a take will use.

## Preconditions

- macOS + iTerm2 (this is a recording operation, so it is gated to darwin per [demo-recording:DEC-004-platform-coupling-and-gate-placement]).
- A `record.yaml` with `cwd` and both window-bounds entries (the `recording` and `control` bounds under `windows`).

## Procedure

1. **Open the windows:**

   ```
   pkit demo-recording record windows --config <bundle>/record.yaml
   ```

2. **What happens.** The engine writes a dynamic iTerm profile (so the demo font size doesn't disturb your everyday iTerm), opens:
   - **RECORDING** at `windows.recording` bounds (visible in the video — defaults give a 1280×800 inner window).
   - **CONTROL** at `windows.control` bounds (off the recording region — drives the take).

   Both `cd` to the bundle's `cwd` and clear their screen, and the engine persists their window IDs so a later recording can raise RECORDING automatically.

3. **Use them.** Rehearse the demo by hand, tune `windows.*` bounds in `record.yaml` and re-run until the framing is right, or start a recorder cropped to the RECORDING bounds manually.

## Notes

- Font size/family come from `record.yaml`'s optional `font_size` / `font_name` (defaults: 18pt Menlo-Regular).
- The windows persist until closed manually or until a `record … stop` / a full take's teardown closes them. Set `DCR_KEEP_WINDOWS=1` to keep them across a stop.
