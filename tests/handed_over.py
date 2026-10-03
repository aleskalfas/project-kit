"""The writer commands an agent's body or storyboard hands over for a person to run.

Shared by the tests of the agents that answer friction by handing commands over
— the living-docs agent and software-analysis' resolver — and by the test that
runs those commands (`test_handed_over_writers.py`, #1148). A command is handed
over either as a line of its own (in a fenced block, a quote or a list) or run
on in a sentence of a walkthrough.
"""

from __future__ import annotations

import re

#: A writer invoked: the friction writers, and the software-analysis record stamp.
WRITER = re.compile(
    r"pkit (?:friction (?:revalidate|defer|record-status)|analysis new revalidation)\b"
)

#: A flag that writes without asking, or shows without writing: never in a command
#: handed over, since running it is the person's.
CONSENT = re.compile(r"--yes\b|--dry-run\b")

#: The marks a line of a quote or a list opens with.
_LEAD = re.compile(r"^[ ]*(?:>[ ]?)?[ ]*")

#: A friction writer run on in a sentence: it ends at a backtick, at a full stop
#: before a space, or at the end of the line.
_INLINE = re.compile(r"pkit friction (?:revalidate|defer) [^`\n]*?(?=`|\.(?:\s|$)|$)")


def commands(text: str) -> list[str]:
    """Every writer command `text` hands over, in order and as written."""
    found: list[str] = []
    for line in text.splitlines():
        stripped = _LEAD.sub("", line).strip()
        if stripped.startswith("pkit "):
            if WRITER.match(stripped):
                found.append(stripped)
            continue
        found.extend(match.group(0) for match in _INLINE.finditer(line))
    return found
