"""GitHub's answer to the one reading of several branches' open pull requests (#1608).

When several local branches match an issue, `_lib/issue_branch` reads which of
them has an open pull request in one `gh api graphql` call, each branch passed
as a variable `-f b<i>=<name>`. These helpers recognise that call and answer it
from a mapping of branch name to open pull request numbers.
"""

from __future__ import annotations

import itertools
import json
import subprocess
from collections.abc import Mapping, Sequence


def is_open_prs_reading(argv: Sequence[str]) -> bool:
    """Whether `argv` is `_lib/issue_branch`'s reading of open pull requests."""
    args = list(argv[1:]) if argv[:1] == ["gh"] else list(argv)
    return args[:2] == ["api", "graphql"] and any("pullRequests(headRefName" in a for a in args)


def asked(argv: Sequence[str]) -> dict[str, str]:
    """The branches the reading asks about, by GraphQL alias."""
    branches: dict[str, str] = {}
    for option, value in itertools.pairwise(argv):
        alias, _, name = value.partition("=")
        if option == "-f" and alias[:1] == "b" and alias[1:].isdigit():
            branches[alias] = name
    return branches


def answer(argv: Sequence[str], open_on: Mapping[str, Sequence[int]]) -> str:
    """GitHub's answer: each branch asked about, with its open pull requests."""
    repository = {
        alias: {"nodes": [{"number": n} for n in open_on.get(name, ())]}
        for alias, name in asked(argv).items()
    }
    return json.dumps({"data": {"repository": repository}})


def fake_gh(
    open_on: Mapping[str, Sequence[int]] | None,
    calls: list[list[str]] | None = None,
):
    """A `gh_run` that answers the reading from `open_on`, or, when it is
    None, fails as an unanswered `gh` does. Each call is kept in `calls`."""

    def gh_run(argv: list[str], config: object, **_kwargs: object) -> subprocess.CompletedProcess:
        if calls is not None:
            calls.append(list(argv))
        if not is_open_prs_reading(argv):
            return subprocess.CompletedProcess(argv, 1, "", f"unexpected gh call: {argv}")
        if open_on is None:
            return subprocess.CompletedProcess(argv, 1, "", "HTTP 502: Bad Gateway")
        return subprocess.CompletedProcess(argv, 0, answer(argv, open_on), "")

    return gh_run
