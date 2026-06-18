# Validate a storyboard

Parse a storyboard markdown file, run structural + per-directive validation, and print the resolved step plan. Read-only; opens no windows and starts no recording. **Platform-neutral** — runs anywhere Python 3 runs (per [demo-recording:DEC-004-platform-coupling-and-gate-placement]).

## When to use

- Before every recording take (the cheapest way to catch a storyboard typo).
- As a pre-commit or CI gate on a bundle's storyboards.
- While authoring a storyboard, to confirm each directive's content parses.

## Procedure

1. **Run validate** on the storyboard:

   ```
   pkit demo-recording validate <storyboard.md>
   ```

   Equivalently, `pkit demo-recording record <demo> --config <bundle>/record.yaml --validate`, or the bundle wrapper's `--validate`.

2. **Read the output.** The validator prints, per step, the resolved directive plan — the plugin that owns each fence and a one-line summary of its content. Example:

   ```
   Step 1 — boot into the shell
     [recording/boot] narrate: "We'll start the stack…"  command: './run.sh restart demo'
   Step 2 — bind the tmux panes
     [recording/panes] chat=2  narrate=3  shell=1
   ...
   ✓ 9 step(s) parsed.  No errors.
   ```

3. **Resolve any errors.** A non-zero exit means structural or directive errors. Common ones:
   - Missing H1 title, or a `## Step N` with a duplicate number.
   - A `boot` block missing `narration:` or `command:`.
   - A `panes` value that isn't an integer.
   - An unclosed fenced block.
   - An unknown directive tag — printed as a **warning** (`[UNKNOWN 'xyz']`), not an error: a storyboard stays readable when a providing plugin is absent (per [demo-recording:DEC-001-storyboard-as-executable-format]).

   Fix the storyboard and re-run until clean.

## Notes

- Validation never touches macOS APIs, so it is the right surface for Linux/CI checks of storyboard syntax even though recording itself is macOS-only.
- The validator is the parser + the recording plugin's per-directive `validate` methods — the same code the engine runs before a take, so a clean validate is a strong signal the take will dispatch.
