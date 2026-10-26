"""The state of one GitHub issue, read live: the backbone's one reader of it.

Two commands ask what has become of an issue, and both read it here:
`pkit scratchpad list`, for the issues a reported note became
(`scratchpads.resolve_ref`), and `pkit decisions proposed`, for the issue a
proposed record waits on (`decisions_proposed`). So the read behaves one way,
as COR-043 point 5 has it:

- **pull only:** the issue is read each time it is asked about, and its state
  is stored nowhere, so nothing drifts
- **never guessing:** a read that fails gives the state `unknown`, with its
  reason, never `open` or `closed`
- **never blocking:** a read that fails, or that `gh` does not answer within
  `GH_TIMEOUT_SECONDS`, ends there, and the caller goes on

It reads GitHub only, through `gh`, and its name says so. It sits in the backbone
under that label provisionally, as ADR-061 point 3 places the backbone's landing
of a pull request. Whether core content may act on one hosting service is raised
for a core decision in #1222.

`issue` names an issue of the repository `gh` finds from the git remote of `cwd`
by its number alone, `795`, or an issue of any repository as `owner/repo#795`.
Reading another repository's issue is a cross-repository read, which COR-039
leaves unrestricted. A value of any other shape is never passed to `gh`.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import cast

# The states a reading gives.
OPEN = "open"
CLOSED = "closed"
UNKNOWN = "unknown"

# How long one read may take before it is given up as unknown.
GH_TIMEOUT_SECONDS = 30

# An issue of a named repository, `owner/repo#795`. A repository's name cannot open
# with `-`, so no value reads to `gh` as an option.
ELSEWHERE = re.compile(r"^(?P<repo>[A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]*)#(?P<number>[1-9]\d*)$")

# An issue of the repository `gh` finds from the remote, by its number alone.
_HERE = re.compile(r"^(?P<number>[1-9]\d*)$")


@dataclass(frozen=True)
class IssueReading:
    """What GitHub said of one issue at the moment of asking."""

    state: str  # OPEN, CLOSED or UNKNOWN
    reason: str = ""  # why the state is UNKNOWN, and empty otherwise
    title: str = ""
    url: str = ""


def read_issue(issue: str, *, cwd: Path | None = None) -> IssueReading:
    """One issue's state, title and URL, in one read through `gh` (see the module docstring)."""
    named = ELSEWHERE.match(issue) or _HERE.match(issue)
    if named is None:
        return _unknown(f"{issue!r} names no issue: write `795` or `owner/repo#795`")
    args = ["gh", "issue", "view", named["number"], "--json", "state,title,url"]
    repo = named.groupdict().get("repo")
    if repo:
        args += ["--repo", repo]
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=GH_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return _unknown("`gh`, the GitHub client, is not installed")
    except subprocess.TimeoutExpired:
        return _unknown(f"`gh` gave no answer in {GH_TIMEOUT_SECONDS} seconds")
    except OSError as exc:
        return _unknown(f"`gh` could not run: {exc}")
    if proc.returncode != 0:
        said = next((line.strip() for line in (proc.stderr or "").splitlines() if line.strip()), "")
        return _unknown(f"`gh` exited {proc.returncode}" + (f": {said}" if said else ""))
    try:
        data: object = json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        data = None
    fields = cast("dict[str, object]", data) if isinstance(data, dict) else {}
    state = fields.get("state")
    if isinstance(state, str) and state.lower() in (OPEN, CLOSED):
        return IssueReading(
            state.lower(),
            title=str(fields.get("title") or ""),
            url=str(fields.get("url") or ""),
        )
    return _unknown("`gh` gave no state for it")


def _unknown(reason: str) -> IssueReading:
    return IssueReading(UNKNOWN, reason)
