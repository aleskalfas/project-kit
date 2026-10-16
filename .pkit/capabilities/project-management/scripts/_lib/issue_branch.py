"""Which local branch is an issue's: the one reading every verb that finds an
issue's branch by name shares (#1608).

A branch is an issue's by its name, `<type>/<N>-<slug>`
([project-management:DEC-013-branch-and-pr-conventions]). `start-work`,
`create-draft`, `review-work`, `back-to-draft`, `review-pr`, `done-work` and
`land-work` find it among the clone's local branches. More than one can match.
An earlier attempt may leave a branch behind, for example an empty one from a
run that was stopped. Each verb used to take the first in git's order, so a
stale branch could stand in for the one carrying the issue's pull request.

The reading:

- **None match.** There is no branch. Each verb says what that means for it.
- **One matches.** It is the issue's branch. Nothing more is read.
- **Several match.** The one with an open pull request is the issue's. The
  open pull requests of all of them are read in one `gh` call. When none has
  one, when more than one has, or when `gh` does not answer, no branch is
  chosen, and :attr:`Reading.refusal` names each branch and why. A reading
  `gh` did not answer is never taken for "no open pull request".

A verb that composes others (`land-work`) hands its reading on, so the open
pull requests are read once per run.

A branch that names the issue in another shape (`feat/42`, `feat/42-Foo`) is
never the issue's branch. Such branches are kept in :attr:`Reading.misshapen`
for `start-work`, which refuses to cut a branch beside one.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from _lib.gh import gh_run

#: The open pull requests from one branch, under a GraphQL alias that also
#: names the variable carrying the branch's name. A branch has at most one
#: open pull request per base, so ten says whether it has one.
_OPEN_PRS = (
    "{alias}: pullRequests(headRefName: ${alias}, states: OPEN, first: 10) {{ nodes {{ number }} }}"
)


@dataclass(frozen=True)
class Reading:
    """The clone's local branches that name issue `issue`, and which of them
    is its branch."""

    issue: int
    #: Every local branch of the shape `<type>/<N>-<slug>`, in git's order.
    matching: tuple[str, ...] = ()
    #: Local branches that name the issue in another shape.
    misshapen: tuple[str, ...] = ()
    #: The open pull requests from each matching branch, by number. Read only
    #: when several match, and empty otherwise.
    open_prs: Mapping[str, tuple[int, ...]] = field(default_factory=dict)
    #: Why `gh` did not say which of several branches has an open pull
    #: request. Empty when it did, or was not asked.
    unread: str = ""

    @property
    def branch(self) -> str | None:
        """The issue's branch. None when no branch matches, and when several
        do and :attr:`refusal` says why none was chosen."""
        if len(self.matching) == 1:
            return self.matching[0]
        if self.unread:
            return None
        with_pr = self._with_open_pr()
        return with_pr[0] if len(with_pr) == 1 else None

    @property
    def none_open(self) -> bool:
        """Several branches match, and `gh` said none has an open pull request.
        A verb that completes a merged pull request found from the issue
        itself (`done-work`) still can."""
        return len(self.matching) > 1 and not self.unread and not self._with_open_pr()

    @property
    def refusal(self) -> str:
        """Why none of several matching branches is the issue's, naming each.
        Empty when one is chosen, or none matches."""
        if len(self.matching) < 2 or self.branch is not None:
            return ""
        count = f"{len(self.matching)} local branches match `*/{self.issue}-*`"
        if self.unread:
            return (
                f"{count} ({', '.join(self.matching)}), and whether any of them has an open "
                f"pull request could not be read: {self.unread}. Which is #{self.issue}'s "
                "branch cannot be told. Run it again once gh answers."
            )
        several = len(self._with_open_pr()) > 1
        why = (
            "more than one has an open pull request" if several else "none has an open pull request"
        )
        lines = [f"{count}, and {why}, so which is #{self.issue}'s branch cannot be told:"]
        for name in self.matching:
            numbers = self.open_prs.get(name) or ()
            prs = ", ".join(f"#{n}" for n in numbers)
            lines.append(
                f"  - {name}: " + (f"open pull request {prs}" if prs else "no open pull request")
            )
        if several:
            lines.append(
                f"Close the pull requests that are not #{self.issue}'s, then run it again."
            )
        else:
            lines.append(
                f"Delete or rename the branches that are not #{self.issue}'s, then run it again."
            )
        return "\n".join(lines)

    def _with_open_pr(self) -> list[str]:
        return [name for name in self.matching if self.open_prs.get(name)]


def read(issue_number: int, config: dict[str, Any]) -> Reading:
    """The local branches that name `issue_number`, and which is its branch.
    `gh` is asked only when several match, once for all of them."""
    names = _local_branches()
    shaped = re.compile(rf"^[a-z]+/{issue_number}-[a-z0-9-]+$")
    naming = re.compile(rf"^[a-z]+/{issue_number}(-|$)")
    matching = tuple(name for name in names if shaped.match(name))
    misshapen = tuple(name for name in names if naming.match(name) and not shaped.match(name))
    if len(matching) < 2:
        return Reading(issue_number, matching, misshapen)
    open_prs, unread = _open_prs(matching, config)
    return Reading(issue_number, matching, misshapen, open_prs, unread)


def _local_branches() -> tuple[str, ...]:
    """The clone's local branches, in git's order. Empty when git cannot list
    them, which reads as no branch matching, as it did for each verb before."""
    try:
        proc = subprocess.run(
            ["git", "branch", "--list", "--format=%(refname:short)"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ()
    if proc.returncode != 0:
        return ()
    return tuple(line.strip() for line in proc.stdout.splitlines() if line.strip())


def _open_prs(
    branches: tuple[str, ...], config: dict[str, Any]
) -> tuple[dict[str, tuple[int, ...]], str]:
    """The open pull requests from each of `branches`, by number, read in one
    `gh` call. Second, why `gh` did not answer, and then the first is empty."""
    aliases = [f"b{i}" for i in range(len(branches))]
    variables = "".join(f", ${alias}: String!" for alias in aliases)
    fields = " ".join(_OPEN_PRS.format(alias=alias) for alias in aliases)
    query = (
        f"query($owner: String!, $repo: String!{variables}) "
        f"{{ repository(owner: $owner, name: $repo) {{ {fields} }} }}"
    )
    argv = ["gh", "api", "graphql", "-f", f"query={query}", "-F", "owner={owner}"]
    argv += ["-F", "repo={repo}"]
    for alias, name in zip(aliases, branches, strict=True):
        argv += ["-f", f"{alias}={name}"]
    try:
        proc = gh_run(argv, config, check=False)
    except FileNotFoundError:
        return {}, "`gh` not on PATH"
    if proc.returncode != 0:
        return {}, (proc.stderr or "").strip() or f"gh exited {proc.returncode}"
    try:
        payload = json.loads(proc.stdout or "null")
    except ValueError:
        return {}, "gh's answer is not JSON"
    repository = _dig(payload, "data", "repository")
    if not isinstance(repository, dict):
        return {}, "gh's answer names no repository"
    open_prs: dict[str, tuple[int, ...]] = {}
    for alias, name in zip(aliases, branches, strict=True):
        nodes = _dig(repository, alias, "nodes")
        if not isinstance(nodes, list):
            return {}, f"gh's answer says nothing of {name}"
        numbers = (_dig(node, "number") for node in nodes)
        open_prs[name] = tuple(n for n in numbers if isinstance(n, int))
    return open_prs, ""


def _dig(value: object, *keys: str) -> object:
    """`value[k1][k2]...`, or None where a step is not a mapping holding the key."""
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value
