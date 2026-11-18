"""Which approvals count as a person's, in human mode (DEC-079 point 3).

``done-work``'s gate in human mode passes on an approving review or an
`Approved` comment from another account than the pull request's author, or on
a bypass ([project-management:DEC-026-work-ownership-lifecycle],
[project-management:DEC-027-review-modes]). Human mode asks for a person's
approval, so [project-management:DEC-079-bots-are-no-person] point 3 counts
one only from an account read as a user's, and never as an approving review
whose body carries a reviewer agent's verdict marker, in any of its forms.

The approvals are read here, each with its author's kind:

- **the reviews,** from GitHub's REST interface, which gives each reviewer's
  login and type, where gh's JSON gives a reviewer by its login alone;
- **the comments,** through the one reader of an issue's comment log
  (``_lib.comment_log``), which keeps each author's type.

**The order of reviews.** The latest review that approves, requests changes or
was dismissed decides, and passes only where it approves. An approval that
does not count is left out of that order, and a request for changes stays in
it whoever made it, a bot's and a reviewer agent's delivered as a native
review among them, so no approving review passes until a person approves after
it.

**Not read here yet:** whether an approver is an account the project registers
as a reviewer agent's, and the comparison of an approver with the author that
sets case aside. Each compares two accounts, which waits on the backbone's
comparison of accounts ([pkit:ADR-094] point 3). Until it comes, the author is
told apart by the login each surface gives, exactly.

The ``gh`` runner is the caller's (``gh(argv)``), as for the comment log, so a
test fakes it and this module imports no ``gh`` helper.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from _lib import account_kind, comment_log
from _lib.agent_verdicts import read_marker

#: A ``gh`` runner: takes the argv, returns what ``subprocess.run`` returns.
Gh = Callable[[list[str]], Any]

APPROVED = "APPROVED"
CHANGES_REQUESTED = "CHANGES_REQUESTED"
DISMISSED = "DISMISSED"

#: The review states that take a place in the order of reviews.
DECIDING_STATES = (APPROVED, CHANGES_REQUESTED, DISMISSED)

#: The prefix an approving comment opens with, case-sensitive.
APPROVED_PREFIX = "Approved"

# One review per line, its reviewer's login and type with its state and body.
_REVIEWS_JQ = ".[] | {login: .user.login, type: .user.type, state: .state, body: .body}"


@dataclass(frozen=True)
class Review:
    """One review of the pull request, with its reviewer's kind."""

    author: str | None
    kind: str | None
    state: str
    body: str


@dataclass(frozen=True)
class Reviews:
    """The pull request's reviews in the order GitHub records them, or why
    they could not be read."""

    complete: bool
    reviews: tuple[Review, ...] = ()
    cause: str | None = None


@dataclass(frozen=True)
class Approval:
    """An approval read, and why it does not count where it does not
    (``left_out`` empty where it counts). ``no_person`` marks an approval left
    out as no person's (DEC-079 point 3), as against the author's own or one
    whose author could not be told from the PR's."""

    author: str | None
    left_out: str = ""
    no_person: bool = False


def reviews_args(pr_number: int) -> list[str]:
    """The ``gh api`` call that reads every review of the pull request."""
    return [
        "gh",
        "api",
        "--paginate",
        f"repos/{{owner}}/{{repo}}/pulls/{int(pr_number)}/reviews?per_page=100",
        "--jq",
        _REVIEWS_JQ,
    ]


def read_reviews(pr_number: int, gh: Gh) -> Reviews:
    """Read every review of ``pr_number`` with its reviewer's kind."""
    try:
        proc = gh(reviews_args(pr_number))
    except FileNotFoundError:
        return Reviews(False, cause="`gh` is not on PATH")
    if getattr(proc, "returncode", 1) != 0:
        return Reviews(False, cause=comment_log.said(proc))
    read: list[Review] = []
    for line in str(getattr(proc, "stdout", "") or "").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            entry = None
        if not isinstance(entry, dict) or not isinstance(entry.get("state"), str):
            return Reviews(False, cause=f"a review of PR #{pr_number} could not be read")
        login = entry.get("login")
        author = login if isinstance(login, str) and login else None
        read.append(
            Review(
                author=author,
                kind=account_kind.of_record(author, entry.get("type")),
                state=entry["state"],
                body=str(entry.get("body") or ""),
            )
        )
    return Reviews(True, tuple(read))


def judge_review(review: Review, pr_author: str) -> Approval:
    """Whether an approving review counts as a person's approval.

    GitHub keeps a PR's author from approving it, so a review needs no author
    read (#1485): an unread author leaves no review out, and only an author
    read that names the reviewer does.
    """
    if read_marker(review.body)[0]:
        return Approval(review.author, "it carries a reviewer agent's verdict marker", True)
    judged = _judge_kind(review.author, review.kind)
    if not judged.left_out and pr_author and review.author == pr_author:
        return Approval(review.author, "it is the PR's author's own")
    return judged


def judge_comment(comment: comment_log.LogComment, pr_author: str) -> Approval:
    """Whether an `Approved` comment counts as a person's approval. With the
    PR's author unread, no commenter is known to be another account (#1485)."""
    judged = _judge_kind(
        comment.author, account_kind.of_record(comment.author, comment.author_type)
    )
    if judged.left_out:
        return judged
    if not pr_author:
        return Approval(comment.author, "the PR's author could not be read")
    if comment.author == pr_author:
        return Approval(comment.author, "it is the PR's author's own")
    return judged


def _judge_kind(author: str | None, kind: str | None) -> Approval:
    """Only an account read as a user's approves as a person."""
    if kind == account_kind.BOT:
        return Approval(author, "a bot's account approves nothing as a person", True)
    if kind != account_kind.USER:
        return Approval(author, "its account is of a kind unknown, so it approves nothing", True)
    return Approval(author)


def deciding_review(
    reviews: Iterable[Review], pr_author: str
) -> tuple[Review | None, tuple[Approval, ...]]:
    """The review that decides, and the approvals left out of the order as no
    person's.

    The latest review that approves, requests changes or was dismissed
    decides, an approval that does not count left out.
    """
    order: list[Review] = []
    left_out: list[Approval] = []
    for review in reviews:
        if review.state not in DECIDING_STATES:
            continue
        if review.state == APPROVED:
            judged = judge_review(review, pr_author)
            if judged.left_out:
                if judged.no_person:
                    left_out.append(judged)
                continue
        order.append(review)
    return (order[-1] if order else None), tuple(left_out)


def approving_comment(
    comments: Iterable[comment_log.LogComment], pr_author: str
) -> tuple[comment_log.LogComment | None, tuple[Approval, ...]]:
    """The latest `Approved` comment that counts as a person's approval, and
    the `Approved` comments after it left out as no person's."""
    left_out: list[Approval] = []
    for comment in reversed(list(comments)):
        if not comment.body.strip().startswith(APPROVED_PREFIX):
            continue
        judged = judge_comment(comment, pr_author)
        if not judged.left_out:
            return comment, tuple(left_out)
        if judged.no_person:
            left_out.append(judged)
    return None, tuple(left_out)
