#!/usr/bin/env python3
"""Claude Code start hook: the context every session and every subagent starts with.

A propagated adapter script, registered in the adapter's baseline settings
(`settings/core/settings.json`) under two events, so every session runs it:

- `SessionStart`, when a session starts, resumes, clears or compacts
- `SubagentStart`, when the harness starts a subagent

It answers each with `hookSpecificOutput.additionalContext`, which the harness
adds to that conversation's context before its first prompt.

The context opens with one sentence (#2026). The harness's environment note
tells every session and subagent to keep temporary files in a session scratch
directory outside the repository. The methodology keeps them in the agent workspace
(core rule 16), and the permission hook asks on a write outside the repository,
in every mode (ADR-034 point 2). The sentence names the harness's note by what
it says, at the moment that note arrives. `_resolve_agent.py` ends every agent
body the deploy writes with the same sentence, and a test holds the two equal.

Where no `pkit` command is on the `PATH` the hook runs with, the context gains
one line (#3005). It names the install script the CLI area ships,
`.pkit/cli/install-pkit.sh`, which installs the project's version (ADR-090
points 3 and 4). The hook only names the script, and never runs it.

Runtime: bare system `python3`, standard library only, as the permission hook
runs, so it starts inside the sandbox and needs nothing to provision. It never
blocks: an unreadable payload, or an event it does not serve, gets no output
and exit 0.
"""

from __future__ import annotations

import json
import shutil
import sys

#: The sentence, worded against the harness's environment note.
WORKSPACE_NOTE = (
    "The session scratch directory your environment names is replaced by "
    "`.agent-workspace/` at the repository root: keep every intermediate file there, "
    "never in that directory."
)

#: The line added where no `pkit` command is on the `PATH`: the install script
#: that installs the project's version.
NO_PKIT_NOTE = (
    "No `pkit` command is on the `PATH`: run `sh .pkit/cli/install-pkit.sh` at the "
    "project's root to install this project's version."
)

#: The events the hook answers. The harness takes `additionalContext` from both.
EVENTS = ("SessionStart", "SubagentStart")


def start_context(payload: object) -> dict | None:
    """The hook's answer to *payload*, or None where it gives none."""
    if not isinstance(payload, dict):
        return None
    event = payload.get("hook_event_name")
    if event not in EVENTS:
        return None
    context = WORKSPACE_NOTE
    if shutil.which("pkit") is None:
        context += "\n" + NO_PKIT_NOTE
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
    except (OSError, UnicodeDecodeError, ValueError):
        return 0
    answer = start_context(payload)
    if answer is not None:
        sys.stdout.write(json.dumps(answer))
    return 0


if __name__ == "__main__":
    sys.exit(main())
