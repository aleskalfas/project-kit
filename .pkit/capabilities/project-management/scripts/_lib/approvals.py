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

**Who approves** (:func:`compare_approvers`). An approval counts only from an
account that is another than the pull request's author, and that the project
does not register as a reviewer agent's (``review.agents.remote_registered``).
Each approver is compared with the author and with every registered entry as
the backbone compares accounts ([pkit:ADR-094] point 3), in one call for the
gate: the approver with the kind GitHub's REST interface records, the author as
gh gives it, with its id and bot flag, and each entry as the project writes it.
Only *two accounts* lets an approval count: *one account* is the author's own
or a reviewer agent's, and *cannot tell* counts for nothing. A registered entry
with no spelling, such as ``@bot``, leaves every approver untold from it, so no
approval counts until a person mends it, and the refusal names the entry.

**Who is asked** (:func:`askable_reviewers`). Human mode asks no member whose
entry names a bot's account, or a reviewer agent's, for a review, nor the
author, nor a member the comparison cannot tell from the author. A registered
entry with no spelling leaves every member untold from a reviewer agent's, so
no member is asked until a person mends it.

The ``gh`` runner is the caller's (``gh(argv)``), as for the comment log, so a
test fakes it and this module imports no ``gh`` helper.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from _lib import account_kind, accounts, comment_log
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

#: Where the project registers its reviewer agents' accounts (DEC-028).
REGISTERED_KEY = "review.agents.remote_registered"

# One review per line, its reviewer's login and type with its state and body.
_REVIEWS_JQ = ".[] | {login: .user.login, type: .user.type, state: .state, body: .body}"


@dataclass(frozen=True)
class Review:
    """One review of the pull request, with its reviewer's kind."""

    author: str | None
    kind: str | None
    state: str
    body: str
    #: The type GitHub's REST interface records for the reviewer's account.
    account_type: str | None = None


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


@dataclass(frozen=True)
class Standing:
    """What the backbone's comparison found of each approver: why its approval
    counts for nothing, keyed by its login and type, where it counts for nothing
    by the comparison (:func:`compare_approvers`). ``unspelled`` are the
    registered entries with no spelling, each with why it names no account."""

    left_out: dict[tuple[str | None, str | None], Approval]
    unspelled: tuple[tuple[str, str], ...] = ()

    def of(self, author: str | None, account_type: str | None) -> Approval | None:
        """Why the approval of ``author`` counts for nothing, or None where it may."""
        return self.left_out.get((author, account_type))


#: A standing that leaves nothing out: no approver of a user's kind to compare.
NO_STANDING = Standing({})


def compare_approvers(
    approvers: Iterable[tuple[str | None, str | None]],
    author: Any,
    registered: Iterable[str],
    *,
    run: accounts.Runner | None = None,
) -> Standing:
    """Compare each approver, a login with the type GitHub records for it, with
    the PR's ``author``, gh's author object, where it was read, and with each
    ``registered`` entry, in one call of the backbone's function (ADR-094 point
    3). Approvers of a kind other than a user's are left to :func:`_judge_kind`."""
    asked = sorted(
        {
            (login, kind)
            for login, kind in approvers
            if login and account_kind.of_record(login, kind) == account_kind.USER
        }
    )
    entries = [entry for entry in registered if isinstance(entry, str) and entry]
    if not asked:
        return NO_STANDING
    author_form = accounts.gh_author(author) if isinstance(author, dict) else None
    pairs = (
        [(accounts.typed(login, kind), author_form) for login, kind in asked]
        if author_form is not None and author_form.get("login")
        else []
    )
    folds = (
        [
            (accounts.typed(login, kind), [accounts.entry(e) for e in entries])
            for login, kind in asked
        ]
        if entries
        else []
    )
    compared = accounts.ask(pairs=pairs, folds=folds, run=run)
    left_out: dict[tuple[str | None, str | None], Approval] = {}
    unspelled: dict[str, str] = {}
    for index, (login, kind) in enumerate(asked):
        if folds:
            judged = _registered(login, compared.folds[index], entries, compared.cause, unspelled)
            if judged is not None:
                left_out[(login, kind)] = judged
                continue
        if pairs:
            answer = compared.pairs[index]
            if answer == accounts.ONE:
                left_out[(login, kind)] = Approval(login, "it is the PR's author's own")
            elif answer != accounts.TWO:
                why = compared.cause or "the backbone's comparison cannot tell the two apart"
                left_out[(login, kind)] = Approval(
                    login, f"it cannot be told from the PR's author's own: {why}", True
                )
    return Standing(left_out, tuple(sorted(unspelled.items())))


def _registered(
    login: str,
    fold: accounts.Fold,
    entries: list[str],
    cause: str | None,
    unspelled: dict[str, str],
) -> Approval | None:
    """Why ``login``'s approval counts for nothing against the registered
    reviewer agents, by its ``fold``, or None where it is none of them."""
    if fold.answer == accounts.TWO:
        return None
    if fold.answer == accounts.ONE:
        return Approval(
            login,
            f"it is an account the project registers as a reviewer agent's ({REGISTERED_KEY})",
            True,
        )
    for entry, (_answer, spelled) in zip(entries, fold.among, strict=False):
        if spelled.account is None and cause is None:
            unspelled[entry] = spelled.reason or "it names no account"
    if unspelled:
        named = ", ".join(f"`{entry}`" for entry in sorted(unspelled))
        return Approval(
            login,
            f"the entry {named} of {REGISTERED_KEY} names no account, so no approval can be "
            "told from a reviewer agent's until it is mended",
            True,
        )
    why = cause or "the backbone's comparison cannot tell it from a registered entry"
    return Approval(
        login, f"it cannot be told from an account registered as a reviewer agent's: {why}", True
    )


def approvers_of(
    reviews: Iterable[Review], comments: Iterable[comment_log.LogComment]
) -> list[tuple[str | None, str | None]]:
    """Each account that approves, by a review or an `Approved` comment, with
    the type GitHub records for it, for :func:`compare_approvers`."""
    out = [(r.author, r.account_type) for r in reviews if r.state == APPROVED]
    out += [
        (c.author, c.author_type) for c in comments if c.body.strip().startswith(APPROVED_PREFIX)
    ]
    return out


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
        account_type = entry.get("type") if isinstance(entry.get("type"), str) else None
        read.append(
            Review(
                author=author,
                kind=account_kind.of_record(author, account_type),
                state=entry["state"],
                body=str(entry.get("body") or ""),
                account_type=account_type,
            )
        )
    return Reviews(True, tuple(read))


def judge_review(review: Review, pr_author: str, standing: Standing) -> Approval:
    """Whether an approving review counts as a person's approval.

    GitHub keeps a PR's author from approving it, so a review needs no author
    read (#1485): an unread author leaves no review out, and only an author
    the comparison finds one account with the reviewer, or cannot tell from
    it, does (``standing``, :func:`compare_approvers`).
    """
    if read_marker(review.body)[0]:
        return Approval(review.author, "it carries a reviewer agent's verdict marker", True)
    judged = _judge_kind(review.author, review.kind)
    if judged.left_out:
        return judged
    return standing.of(review.author, review.account_type) or judged


def judge_comment(comment: comment_log.LogComment, pr_author: str, standing: Standing) -> Approval:
    """Whether an `Approved` comment counts as a person's approval. With the
    PR's author unread, no commenter is known to be another account (#1485)."""
    judged = _judge_kind(
        comment.author, account_kind.of_record(comment.author, comment.author_type)
    )
    if judged.left_out:
        return judged
    compared = standing.of(comment.author, comment.author_type)
    if compared is not None and compared.no_person:
        return compared
    if not pr_author:
        return Approval(comment.author, "the PR's author could not be read")
    return compared or judged


def _judge_kind(author: str | None, kind: str | None) -> Approval:
    """Only an account read as a user's approves as a person."""
    if kind == account_kind.BOT:
        return Approval(author, "a bot's account approves nothing as a person", True)
    if kind != account_kind.USER:
        return Approval(author, "its account is of a kind unknown, so it approves nothing", True)
    return Approval(author)


def deciding_review(
    reviews: Iterable[Review], pr_author: str, standing: Standing
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
            judged = judge_review(review, pr_author, standing)
            if judged.left_out:
                if judged.no_person:
                    left_out.append(judged)
                continue
        order.append(review)
    return (order[-1] if order else None), tuple(left_out)


def approving_comment(
    comments: Iterable[comment_log.LogComment], pr_author: str, standing: Standing
) -> tuple[comment_log.LogComment | None, tuple[Approval, ...]]:
    """The latest `Approved` comment that counts as a person's approval, and
    the `Approved` comments after it left out as no person's."""
    left_out: list[Approval] = []
    for comment in reversed(list(comments)):
        if not comment.body.strip().startswith(APPROVED_PREFIX):
            continue
        judged = judge_comment(comment, pr_author, standing)
        if not judged.left_out:
            return comment, tuple(left_out)
        if judged.no_person:
            left_out.append(judged)
    return None, tuple(left_out)


def askable_reviewers(
    candidates: Iterable[str],
    author: Mapping[str, Any] | None,
    registered: Iterable[str],
    *,
    run: accounts.Runner | None = None,
) -> tuple[list[str], list[str]]:
    """The members of ``candidates``, each a member's entry, that human mode
    asks for a review, and a line for each it passes over, saying why (DEC-079
    point 3, "Who is asked").

    ``author`` is the PR's author in a form the backbone's function takes, such
    as gh's (:func:`accounts.gh_author`), or None where it is not known, and
    then no member can be told from it. Each member is compared with the author
    and with each ``registered`` entry in one call of the backbone's function
    (ADR-094 point 3)."""
    members = [c for c in candidates if isinstance(c, str) and c]
    entries = [e for e in registered if isinstance(e, str) and e]
    passed: list[str] = []
    asked: list[str] = []
    for member in members:
        if account_kind.of_form(member) == account_kind.BOT:
            passed.append(f"@{member}: the entry names a bot's account, which reviews as no person")
        else:
            asked.append(member)
    if not asked:
        return [], passed
    if author is None:
        passed += [
            f"@{member}: the PR's author is not known, so the member cannot be told from it"
            for member in asked
        ]
        return [], passed
    compared = accounts.ask(
        pairs=[(accounts.entry(member), author) for member in asked],
        folds=(
            [(accounts.entry(member), [accounts.entry(e) for e in entries]) for member in asked]
            if entries
            else []
        ),
        run=run,
    )
    out: list[str] = []
    for index, member in enumerate(asked):
        why = _passed_over(index, compared, entries)
        if why is None:
            out.append(member)
        else:
            passed.append(f"@{member}: {why}")
    return out, passed


def _passed_over(index: int, compared: accounts.Compared, entries: list[str]) -> str | None:
    """Why the member asked at ``index`` is passed over, or None where it is asked."""
    if entries:
        fold = compared.folds[index]
        if fold.answer == accounts.ONE:
            return f"the entry names an account registered as a reviewer agent's ({REGISTERED_KEY})"
        if fold.answer != accounts.TWO:
            unspelled = [
                entry
                for entry, (_answer, spelled) in zip(entries, fold.among, strict=False)
                if spelled.account is None
            ]
            if unspelled and compared.cause is None:
                named = ", ".join(f"`{entry}`" for entry in unspelled)
                return (
                    f"the entry {named} of {REGISTERED_KEY} names no account, so no member can "
                    "be told from a reviewer agent's until it is mended"
                )
            cause = compared.cause or "the comparison cannot tell it from a registered entry"
            return f"it cannot be told from an account registered as a reviewer agent's: {cause}"
    answer = compared.pairs[index]
    if answer == accounts.ONE:
        return "it is the PR's author"
    if answer != accounts.TWO:
        cause = compared.cause or "the comparison cannot tell it from the author"
        return f"it cannot be told from the PR's author: {cause}"
    return None
