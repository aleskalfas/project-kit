#!/usr/bin/env python3
"""storyboards/runner.py — parse + plugin dispatch for storyboard execution.

Reads a storyboard .md file, parses it via parser.py, validates each fence
with the loaded plugin(s), and either:

  --validate   pretty-print the resolved step plan (with plugin names and
               directive summaries) then exit 0 (clean) / 1 (errors).

  (default)    emit tab-separated dispatch lines for the bash runner to
               consume.  One tuple per line, fields tab-separated.

This script is what run-storyboard.sh and record.sh call.  It loads the
recording plugin by default (the only plugin shipped in v1).

Dispatch format (one action per line, fields tab-separated)::

    select_pane  <pane_number>
    narrate      <text>
    narrate_wipe_run  <text>  <command>
    shell_run    <command>
    wait_only    <message>
    wait_for_focus  <hint>  <verb>

Usage::

    runner.py <storyboard.md>             # emit dispatch lines
    runner.py <storyboard.md> --validate  # pretty-print step plan
"""

import os
import sys

# Allow running directly from the demo-cli-recorder tree without installing.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from storyboards.parser import parse  # noqa: E402
from storyboards.plugin import PluginRegistry  # noqa: E402

# Load the built-in recording plugin.
from plugins.recording import directives as _recording_directives  # noqa: E402


def _build_registry() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register(_recording_directives.RecordingPlugin())
    return registry


def _emit_dispatch(tree: dict, registry: PluginRegistry) -> int:
    """Walk the storyboard tree and emit tab-separated bash action tuples."""

    def _qt(s: str) -> str:
        """Quote a field: collapse tabs + newlines (field separator safety)."""
        return str(s).replace("\t", "    ").replace("\n", " ").strip()

    context: dict = {}

    for step in tree["steps"]:
        for fence in step["fences"]:
            lang = fence["lang"]
            content = fence["content"]
            actions = registry.actions_for_fence(lang, content, context)
            for action in actions:
                print("\t".join(_qt(str(a)) for a in action))

    return 0


def _emit_validate(
    tree: dict,
    errors: list[str],
    plugin_errors: list[str],
    registry: PluginRegistry,
    path: str,
) -> int:
    """Pretty-print the resolved step plan.  Returns exit code."""

    print(f"Storyboard: {path}")
    print()

    for step in tree["steps"]:
        suffix = f" — {step['title']}" if step["title"] else ""
        print(f"Step {step['number']}{suffix}")
        if step["fences"]:
            for fence in step["fences"]:
                desc = registry.describe_fence(
                    fence["lang"],
                    fence["content"],
                    step["number"],
                    fence["line"],
                )
                print(desc)
        else:
            print("  (no directives)")
        print()

    all_errors = errors + plugin_errors
    if all_errors:
        print(f"✗ {len(all_errors)} error(s):", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    n = len(tree["steps"])
    print(f"✓ {n} step(s) parsed.  No errors.")
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__, file=sys.stderr)
        return 0 if len(sys.argv) > 1 else 2

    path = sys.argv[1]
    validate = "--validate" in sys.argv[2:]

    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        print(f"runner.py: cannot read {path}: {exc}", file=sys.stderr)
        return 1

    tree, struct_errors = parse(text)
    registry = _build_registry()

    # Run plugin validation on every fence.
    plugin_errors: list[str] = []
    for step in tree["steps"]:
        for fence in step["fences"]:
            errs = registry.validate_fence(
                fence["lang"],
                fence["content"],
                step["number"],
                fence["line"],
            )
            plugin_errors.extend(errs)

    if validate:
        return _emit_validate(tree, struct_errors, plugin_errors, registry, path)

    # Dispatch mode: fail fast if there are errors.
    all_errors = struct_errors + plugin_errors
    if all_errors:
        for e in all_errors:
            print(f"runner.py: {e}", file=sys.stderr)
        return 1

    return _emit_dispatch(tree, registry)


if __name__ == "__main__":
    sys.exit(main())
