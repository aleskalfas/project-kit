"""An in-memory GitHub for the state-issue seam and the reader of comment logs.

`FakeRepo` answers the `gh` calls `_lib/state_issues` and `_lib/comment_log`
make: a page of an issue's comments, an author's access and who opened an issue
(`gh api`), a read of an issue, a listing of issues, a comment, a description
written from a file, a new issue, a lock, and a reopen or a close. Every comment
and issue it is handed is authored by `author`, as GitHub authors one by the
account `gh` runs as. An issue a test adds is opened by `author` too, unless the
test names its `opener`. No test reaches GitHub.

`access` maps a login to the level GitHub would answer; a login it lacks
answers 404. `failing` holds the verbs whose next call fails once (`"comment"`,
`"edit"`, `"create"`, `"view"`, `"list"`, `"page"`, `"access"`, `"issue"`,
`"lock"`, `"reopen"`), and `"comment-landed"` for a comment that lands though
its call fails. `before_post` runs before each comment lands, with the issue's
number, so a test can post another clone's comment there to stand for one made
in the same instant.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_PAGE = re.compile(r"repos/\{owner\}/\{repo\}/issues/(\d+)/comments\?per_page=(\d+)&page=(\d+)")
_ACCESS = re.compile(r"repos/\{owner\}/\{repo\}/collaborators/([^/]+)/permission")
_ISSUE = re.compile(r"repos/\{owner\}/\{repo\}/issues/(\d+)")


@dataclass
class FakeIssue:
    """One issue. ``opener`` is the login that opened it, and ``""`` stands for
    an account GitHub no longer has."""

    title: str
    body: str
    state: str = "OPEN"
    comments: list[dict[str, Any]] = field(default_factory=list)
    args: list[str] = field(default_factory=list)
    opener: str = "me"
    locked: bool = False


@dataclass
class FakeRepo:
    author: str = "me"
    issues: dict[int, FakeIssue] = field(default_factory=dict)
    access: dict[str, str] = field(default_factory=dict)
    failing: set[str] = field(default_factory=set)
    calls: list[list[str]] = field(default_factory=list)
    before_post: Callable[[int], None] | None = None
    next_issue: int = 100
    next_comment: int = 1000

    def add(
        self,
        number: int,
        body: str = "",
        *,
        title: str = "t",
        state: str = "OPEN",
        opener: str | None = None,
    ):
        self.issues[number] = FakeIssue(
            title, body, state, opener=self.author if opener is None else opener
        )
        return self.issues[number]

    def post(self, number: int, body: str, author: str | None = None) -> dict[str, Any]:
        """A comment on the issue, by `author` (the fake's own by default); an
        author of `""` stands for an account GitHub no longer has."""
        self.next_comment += 1
        user = None if author == "" else {"login": author or self.author}
        comment = {
            "id": self.next_comment,
            "user": user,
            "created_at": f"2026-10-26T00:00:{self.next_comment % 60:02d}Z",
            "body": body,
        }
        self.issues[number].comments.append(comment)
        return comment

    def writes(self) -> list[list[str]]:
        """Every call that changed something."""
        return [
            argv
            for argv in self.calls
            if argv[1] == "issue"
            and argv[2] in ("comment", "edit", "create", "lock", "reopen", "close")
        ]

    def bodies(self, number: int) -> list[str]:
        return [c["body"] for c in self.issues[number].comments]

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        argv = [str(a) for a in argv]
        self.calls.append(argv)
        if argv[1] == "api":
            return self._api(argv)
        assert argv[1] == "issue", f"unexpected gh call: {argv}"
        verb = argv[2]
        if verb == "create":
            if self._fails("create"):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            title = argv[argv.index("--title") + 1]
            body = Path(argv[argv.index("--body-file") + 1]).read_text(encoding="utf-8")
            self.next_issue += 1
            issue = self.add(self.next_issue, body, title=title)
            issue.args = argv
            url = f"https://github.com/o/r/issues/{self.next_issue}\n"
            return _done(argv, stdout=url)
        if verb == "list":
            return self._list(argv)
        number = int(argv[3])
        issue = self.issues[number]
        if verb == "view":
            if self._fails("view"):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            record = {"number": number, "state": issue.state, "title": issue.title}
            record["body"] = issue.body
            fields = argv[argv.index("--json") + 1].split(",")
            return _done(argv, stdout=json.dumps({f: record[f] for f in fields}))
        if verb == "comment":
            if self.before_post is not None:
                self.before_post(number)
            if self._fails("comment"):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            self.post(number, argv[argv.index("--body") + 1])
            if self._fails("comment-landed"):
                return _done(argv, 1, stderr="HTTP 504: Gateway Timeout")
            return _done(argv)
        if verb == "edit":
            if self._fails("edit"):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            issue.body = Path(argv[argv.index("--body-file") + 1]).read_text(encoding="utf-8")
            return _done(argv)
        if verb == "lock":
            if self._fails("lock"):
                return _done(argv, 1, stderr="HTTP 403: Resource not accessible by integration")
            issue.locked = True
            return _done(argv)
        if verb in ("reopen", "close"):
            if self._fails(verb):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            issue.state = "OPEN" if verb == "reopen" else "CLOSED"
            return _done(argv)
        raise AssertionError(f"unexpected gh call: {argv}")

    def _list(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        """`gh issue list --state <s> --limit <n> --json <fields>`: the newest first,
        as GitHub lists them."""
        if self._fails("list"):
            return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
        state = argv[argv.index("--state") + 1] if "--state" in argv else "open"
        limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 30
        fields = argv[argv.index("--json") + 1].split(",")
        rows = []
        for number in sorted(self.issues, reverse=True):
            issue = self.issues[number]
            if state != "all" and issue.state != state.upper():
                continue
            record = {"number": number, "state": issue.state, "title": issue.title}
            record["body"] = issue.body
            rows.append({f: record[f] for f in fields})
        return _done(argv, stdout=json.dumps(rows[:limit]))

    def _api(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        path = argv[2]
        page = _PAGE.fullmatch(path)
        if page:
            if self._fails("page"):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            number, size, index = (int(g) for g in page.groups())
            comments = self.issues[number].comments
            chunk = comments[(index - 1) * size : index * size]
            return _done(argv, stdout=json.dumps(chunk))
        access = _ACCESS.fullmatch(path)
        if access:
            if self._fails("access"):
                return _done(argv, 1, stderr="HTTP 403: Resource not accessible by integration")
            login = access.group(1)
            if login not in self.access:
                return _done(argv, 1, stderr="gh: Not Found (HTTP 404)")
            level = self.access[login]
            return _done(argv, stdout=json.dumps({"permission": level, "role_name": level}))
        opened = _ISSUE.fullmatch(path)
        if opened:
            if self._fails("issue"):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            number = int(opened.group(1))
            issue = self.issues[number]
            user = {"login": issue.opener} if issue.opener else None
            record = {"number": number, "state": issue.state.lower(), "user": user}
            record["locked"] = issue.locked
            return _done(argv, stdout=json.dumps(record))
        raise AssertionError(f"unexpected gh api call: {argv}")

    def _fails(self, verb: str) -> bool:
        if verb in self.failing:
            self.failing.discard(verb)
            return True
        return False


def _done(argv: list[str], rc: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(argv, rc, stdout, stderr)
