"""Whether a host file holds a line: one table of cases that both tests of it are held to
(ADR-076 point 2) — the Claude Code merge primitive's, in the shell
(`merge-claude-md.sh`), and the backbone's check (`loaded_rules.holds_line`).

"Holds the line" means a line of the file that is exactly the line once the spaces and
tabs around it are trimmed and a CRLF ending is read as `\\n`, outside fenced code. A line
opening with three backticks or three tildes, indented at most three spaces, opens or
closes fenced code, and lies inside it. A mention in a code span, in a fence, or as part
of a longer token does not hold it.

Each case is the text that follows a host's held include of core's rules, and whether it
holds the index's line. The values are written out here, not taken from either test, so
the table is an oracle of its own.
"""

from __future__ import annotations

#: The line the cases ask about: the index's, as the Claude Code adapter renders it.
LINE = "@.pkit/rules/capabilities.md"

#: (name, text, held)
CASES: tuple[tuple[str, str, bool], ...] = (
    ("a line of its own", f"{LINE}\n", True),
    ("spaces around it", f"   {LINE}  \n", True),
    ("a tab before it", f"\t{LINE}\n", True),
    ("a CRLF ending", f"{LINE}\r\n", True),
    ("after a closed fence", f"```\ncode\n```\n{LINE}\n", True),
    ("after a fence indented three spaces, closed", f"   ```\ncode\n   ```\n{LINE}\n", True),
    ("a marker indented four spaces opens no fence", f"    ```\n{LINE}\n", True),
    ("the last line, with no line break", f"prose\n{LINE}", True),
    ("inside a backtick fence", f"```\n{LINE}\n```\n", False),
    ("inside a tilde fence with an info string", f"~~~md\n{LINE}\n~~~\n", False),
    ("inside a fence never closed", f"```\n{LINE}\n", False),
    ("a tilde line does not close a backtick fence", f"```\n~~~\n{LINE}\n```\n", False),
    ("inside a fence with CRLF endings", f"```\r\n{LINE}\r\n```\r\n", False),
    ("in a code span", f"`{LINE}`\n", False),
    ("part of a longer token", f"{LINE}.bak\n", False),
    ("in a sentence", f"See {LINE} for the capabilities' rules.\n", False),
    ("absent", "Nothing here.\n", False),
)
