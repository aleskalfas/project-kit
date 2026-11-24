"""The acting account and the comparison of accounts, as the backbone gives them
(ADR-094; [project-management:DEC-076-app-credentials] point 1).

Which account the credential acts as, and of which kind, is read once, in the
backbone, from GitHub's answer alone. Every command of this capability takes it
from there, through the backbone's reading command, and asks GitHub no way of
its own ([pkit:ADR-094] point 1):

- :func:`read` runs ``pkit account read --json`` once in a run, for each host,
  and gives the account in the one spelling, its kind, or why it names none.
  The host the capability's requests go to (DEC-023) is passed on through the
  environment, as ``GH_HOST``.
- :func:`compare` and :func:`fold` run ``pkit account compare --json``, which
  asks GitHub nothing, so that every comparison of two accounts goes through the
  backbone's one function (point 3). A reader that compares many accounts
  compares them in one call.

**What this module never does.** It names an account only from the document's
``account``, never from ``login``, and decides on ``cause``, never on
``reason``. A document it cannot read, a version it does not know, a kind it
does not know and a cause it does not know are each read as an unresolved
identity; an answer it does not know, and no document, as *cannot tell* (ADR-094
point 1, "Its sets may grow"). It keeps no copy of the spelling or of the
comparison (ADR-057 point 2).

The forms an account is given in say where its kind comes from (ADR-094 point
3, "The forms a caller gives"): :func:`entry` for an entry or a value pkit
holds, the acting account the reading spelled among them; :func:`typed` for a
login with the type GitHub's REST interface records; :func:`users_field` for a
login from a field GitHub declares to hold users' accounts, such as an issue's
assignees; and :func:`login` for a login and nothing more.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

try:
    from _lib import backbone
    from _lib import document_keys as keys
except ImportError:  # pragma: no cover - `scripts/_lib/` itself on sys.path
    import backbone  # type: ignore[no-redef]
    import document_keys as keys  # type: ignore[no-redef]

#: The backbone's reading command, and its command that compares accounts.
READ_ARGV = ("pkit", "account", "read", "--json")
SPELL_ARGV = ("pkit", "account", "spell", "--json")
COMPARE_ARGV = ("pkit", "account", "compare", "--json")
#: The version of the documents this module reads; another is no answer.
VERSION = 1
#: How long a call waits for the backbone. The reading bounds its own ask of
#: GitHub at 15 seconds, and `pkit` starts on top of it.
TIMEOUT = 45

KIND_USER = "user"
KIND_BOT = "bot"
#: The kinds this module knows. A kind it does not know is a kind unknown.
KINDS = frozenset({KIND_USER, KIND_BOT})

#: The causes of an unnamed account: GitHub answered that the credential's
#: account is no user's, and the reading can name none (ADR-094 point 2).
CAUSE_INTEGRATION_REFUSED = "integration-refused"
CAUSE_KIND_UNKNOWN = "kind-unknown"
UNNAMED_CAUSES = frozenset({CAUSE_INTEGRATION_REFUSED, CAUSE_KIND_UNKNOWN})
#: The causes of an unresolved identity this module knows. A cause it does not
#: know reads as an unresolved identity too.
UNRESOLVED_CAUSES = frozenset(
    {"refused", "no-answer", "gh-missing", "offline", "timeout", "no-account"}
)
#: The cause this module gives where the backbone gave no document it can read.
CAUSE_NO_DOCUMENT = "no-document"

ONE = "one"
TWO = "two"
CANNOT_TELL = "cannot-tell"
ANSWERS = frozenset({ONE, TWO, CANNOT_TELL})

FORM_ENTRY = "entry"
FORM_TYPED = "typed"
FORM_GH = "gh"
FORM_USERS_FIELD = "users-field"
FORM_LOGIN = "login"

Runner = Callable[..., subprocess.CompletedProcess[str]]


# ---- the reading ---------------------------------------------------------------


@dataclass(frozen=True)
class Reading:
    """Which account the credential acts as, as the backbone read it.

    Where it names one, ``account`` is that account in the one spelling and
    ``kind`` is ``user`` or ``bot``, and ``cause`` is None. Where it names none,
    both are None, ``cause`` says why, and ``reason`` says it for people."""

    account: str | None = None
    kind: str | None = None
    cause: str | None = None
    reason: str | None = None

    @property
    def names_user(self) -> bool:
        """Whether GitHub answered that the credential acts as a user's account."""
        return self.account is not None and self.kind == KIND_USER

    @property
    def unnamed(self) -> bool:
        """Whether GitHub answered that the credential's account is no user's,
        and the reading can name none: an integration's refusal, or an account
        of a kind unknown."""
        return self.account is None and self.cause in UNNAMED_CAUSES

    @property
    def unresolved(self) -> bool:
        """Whether GitHub gave no answer about who the credential is, for any
        cause: an unresolved identity (DEC-076, "The terms")."""
        return self.account is None and not self.unnamed

    def because(self) -> str:
        """Why the reading names no account, as a clause for people."""
        return self.reason or self.cause or "the backbone's reading named no account"


#: The reading in this run, by the host asked, so a command and the commands it
#: loads in its own process ask once (ADR-094 point 4).
_readings: dict[str | None, Reading] = {}


def read(config: Mapping[str, Any] | None = None, *, run: Runner | None = None) -> Reading:
    """Which account the credential acts as, read by the backbone, once in a run
    for the host the capability's requests go to (DEC-023)."""
    host = _host(config)
    if host not in _readings:
        _readings[host] = _ask(host, run or backbone.run)
    return _readings[host]


def forget_service_answers() -> None:
    """Forget the readings of this run, as a new run holds none. For tests,
    whose shared fixture forgets every module's answers by this name."""
    _readings.clear()


def _ask(host: str | None, run: Runner) -> Reading:
    """Run the backbone's reading command and read its document."""
    try:
        proc = run(list(READ_ARGV), **_options(host))
    except FileNotFoundError:
        return Reading(cause=CAUSE_NO_DOCUMENT, reason="`pkit` is not on PATH")
    except subprocess.TimeoutExpired:
        return Reading(
            cause=CAUSE_NO_DOCUMENT,
            reason=f"`pkit account read` did not answer within {TIMEOUT} seconds",
        )
    except OSError as exc:
        return Reading(cause=CAUSE_NO_DOCUMENT, reason=f"`pkit account read` failed: {exc}")
    if proc.returncode != 0:
        said = (proc.stderr or proc.stdout or "").strip().splitlines()
        tail = said[-1] if said else f"it exited {proc.returncode}"
        return Reading(
            cause=CAUSE_NO_DOCUMENT,
            reason=(
                f"the backbone's `pkit account read` gave no document ({tail}); the backbone "
                "may predate it"
            ),
        )
    try:
        return reading_of(json.loads(proc.stdout or ""))
    except (ValueError, keys.Untold) as exc:
        return Reading(
            cause=CAUSE_NO_DOCUMENT,
            reason=f"the document of `pkit account read` could not be read: {exc}",
        )


def reading_of(document: object) -> Reading:
    """The reading a document of ``pkit account read`` gives. Raises
    :class:`keys.Untold` where it cannot be read, or holds a version this module
    does not know."""
    if not isinstance(document, dict):
        raise keys.Untold("the document is no object")
    version = keys.value(document, "schema_version", "")
    if version != VERSION:
        raise keys.Untold(f"`schema_version` is {version!r}, not {VERSION}")
    account = keys.text_or_null(document, "account", "")
    kind = keys.text_or_null(document, "kind", "")
    cause = keys.text_or_null(document, "cause", "")
    reason = keys.text_or_null(document, "reason", "")
    if account is not None:
        if kind not in KINDS:
            return Reading(
                cause=CAUSE_NO_DOCUMENT,
                reason=f"the backbone named {account} as of a kind this code does not know",
            )
        return Reading(account=account, kind=kind)
    if cause in UNNAMED_CAUSES or cause in UNRESOLVED_CAUSES:
        return Reading(cause=cause, reason=reason)
    # A cause this code does not know is an unresolved identity, whose cause it
    # cannot tell (ADR-094 point 1).
    return Reading(cause=CAUSE_NO_DOCUMENT, reason=reason or f"the cause {cause!r}")


# ---- the comparison -------------------------------------------------------------


def entry(value: str) -> dict[str, Any]:
    """An entry or a value pkit holds, in the one spelling: a member's login, a
    registered reviewer's, a variable that names an account, or the acting
    account the reading spelled."""
    return {"form": FORM_ENTRY, "login": value}


def typed(value: str, account_type: str | None) -> dict[str, Any]:
    """A login with the type GitHub's REST interface records for the account."""
    given: dict[str, Any] = {"form": FORM_TYPED, "login": value}
    if account_type:
        given["type"] = account_type
    return given


def users_field(value: str) -> dict[str, Any]:
    """A login from a field GitHub declares to hold users' accounts, such as an
    issue's assignees."""
    return {"form": FORM_USERS_FIELD, "login": value}


def login(value: str) -> dict[str, Any]:
    """A login and nothing more, such as gh's JSON gives a comment's author."""
    return {"form": FORM_LOGIN, "login": value}


def gh_author(author: Mapping[str, Any]) -> dict[str, Any]:
    """An author as gh's JSON gives one, with its id and its bot flag, such as
    a pull request's `mergedBy`."""
    given: dict[str, Any] = {"form": FORM_GH, "login": str(author.get("login") or "")}
    if author.get("id") not in (None, ""):
        given["id"] = author.get("id")
    if isinstance(author.get("is_bot"), bool):
        given["is_bot"] = author.get("is_bot")
    return given


@dataclass(frozen=True)
class Spelled:
    """One account as the backbone's function read it: ``account`` in the one
    spelling, None where it has none, and ``reason`` why not, for people."""

    login: str
    account: str | None
    kind: str | None
    reason: str | None = None


@dataclass(frozen=True)
class Fold:
    """One account against many: ``answer`` folded, and each entry's own answer,
    in the order given (ADR-094 point 3, "One against many")."""

    answer: str
    account: Spelled | None = None
    among: tuple[tuple[str, Spelled], ...] = ()
    #: Why the backbone could not be asked, where it could not.
    cause: str | None = None


@dataclass(frozen=True)
class Compared:
    """The backbone's answers to one request: each pair's answer, and each fold,
    in the order asked. Where it gave no document it can read, every answer is
    *cannot tell*, and ``cause`` says why."""

    pairs: tuple[str, ...] = ()
    folds: tuple[Fold, ...] = ()
    cause: str | None = None


def ask(
    pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]] = (),
    folds: Sequence[tuple[Mapping[str, Any], Sequence[Mapping[str, Any]]]] = (),
    *,
    run: Runner | None = None,
) -> Compared:
    """Ask the backbone's function, in one call, whether each pair is one account,
    and whether each folded account is one of its entries. Nothing is asked where
    nothing is given."""
    if not pairs and not folds:
        return Compared()
    request = {
        "pairs": [[dict(left), dict(right)] for left, right in pairs],
        "folds": [
            {"account": dict(account), "among": [dict(one) for one in among]}
            for account, among in folds
        ],
    }
    cause: str | None
    try:
        proc = (run or backbone.run)(
            list(COMPARE_ARGV), input=json.dumps(request), **_options(None)
        )
    except FileNotFoundError:
        cause = "`pkit` is not on PATH"
    except subprocess.TimeoutExpired:
        cause = f"`pkit account compare` did not answer within {TIMEOUT} seconds"
    except OSError as exc:
        cause = f"`pkit account compare` failed: {exc}"
    else:
        if proc.returncode == 0:
            try:
                return _compared(json.loads(proc.stdout or ""), len(pairs), folds)
            except (ValueError, keys.Untold) as exc:
                cause = f"the document of `pkit account compare` could not be read: {exc}"
        else:
            said = (proc.stderr or proc.stdout or "").strip().splitlines()
            tail = said[-1] if said else f"it exited {proc.returncode}"
            cause = f"`pkit account compare` gave no document ({tail})"
    return Compared(
        pairs=tuple(CANNOT_TELL for _ in pairs),
        folds=tuple(
            Fold(
                CANNOT_TELL, among=tuple((CANNOT_TELL, _unread(one)) for one in among), cause=cause
            )
            for _, among in folds
        ),
        cause=cause,
    )


def spell(given: Sequence[Mapping[str, Any]], *, run: Runner | None = None) -> list[Spelled]:
    """Each account of ``given`` in the one spelling, in one call of the
    backbone's function. Where the backbone gave no document it can read, none
    has a spelling, and each reason says why."""
    if not given:
        return []
    request = {"accounts": [dict(one) for one in given]}
    cause: str
    try:
        proc = (run or backbone.run)(list(SPELL_ARGV), input=json.dumps(request), **_options(None))
    except FileNotFoundError:
        cause = "`pkit` is not on PATH"
    except subprocess.TimeoutExpired:
        cause = f"`pkit account spell` did not answer within {TIMEOUT} seconds"
    except OSError as exc:
        cause = f"`pkit account spell` failed: {exc}"
    else:
        if proc.returncode == 0:
            try:
                document = json.loads(proc.stdout or "")
                spelled = _spelled_list(document)
                if len(spelled) == len(given):
                    return spelled
                cause = "`pkit account spell` answered another number of accounts"
            except (ValueError, keys.Untold) as exc:
                cause = f"the document of `pkit account spell` could not be read: {exc}"
        else:
            said = (proc.stderr or proc.stdout or "").strip().splitlines()
            tail = said[-1] if said else f"it exited {proc.returncode}"
            cause = f"`pkit account spell` gave no document ({tail})"
    return [
        Spelled(login=str(one.get("login") or ""), account=None, kind=None, reason=cause)
        for one in given
    ]


def _spelled_list(document: object) -> list[Spelled]:
    """The accounts of a document of ``pkit account spell``."""
    if not isinstance(document, dict):
        raise keys.Untold("the document is no object")
    version = keys.value(document, "schema_version", "")
    if version != VERSION:
        raise keys.Untold(f"`schema_version` is {version!r}, not {VERSION}")
    return [_spelled(one, where) for where, one in keys.objects(document, "accounts", "")]


def compare(left: Mapping[str, Any], right: Mapping[str, Any], *, run: Runner | None = None) -> str:
    """Whether ``left`` and ``right`` are one account, two, or the backbone's
    function cannot tell."""
    return ask(pairs=[(left, right)], run=run).pairs[0]


def fold(
    account: Mapping[str, Any], among: Sequence[Mapping[str, Any]], *, run: Runner | None = None
) -> Fold:
    """Whether ``account`` is one of ``among``: *one* where it is one with some
    entry, *two* where it is two with every entry, *cannot tell* otherwise. An
    empty ``among`` folds to *two*, since no entry names it."""
    if not among:
        return Fold(TWO)
    return ask(folds=[(account, among)], run=run).folds[0]


def _compared(
    document: object,
    asked: int,
    folds: Sequence[tuple[Mapping[str, Any], Sequence[Mapping[str, Any]]]],
) -> Compared:
    """The answers of a document of ``pkit account compare``."""
    if not isinstance(document, dict):
        raise keys.Untold("the document is no object")
    version = keys.value(document, "schema_version", "")
    if version != VERSION:
        raise keys.Untold(f"`schema_version` is {version!r}, not {VERSION}")
    pairs = [_answer(pair, where) for where, pair in keys.objects(document, "pairs", "")]
    read_folds: list[Fold] = []
    for where, question in keys.objects(document, "folds", ""):
        among = tuple(
            (_answer(one, inner), _spelled(keys.mapping(one, "account", inner), inner))
            for inner, one in keys.objects(question, "among", where)
        )
        account = _spelled(keys.mapping(question, "account", where), where)
        read_folds.append(Fold(_answer(question, where), account=account, among=among))
    if len(pairs) != asked or len(read_folds) != len(folds):
        raise keys.Untold("it answers another number of questions than were asked")
    return Compared(pairs=tuple(pairs), folds=tuple(read_folds))


def _answer(entry_: Mapping[str, Any], where: str) -> str:
    """An answer, *cannot tell* where it is one this module does not know."""
    found = keys.text(entry_, "answer", where)
    return found if found in ANSWERS else CANNOT_TELL


def _spelled(document: Mapping[str, Any], where: str) -> Spelled:
    """One account of a document of ``pkit account compare``."""
    kind = keys.text_or_null(document, "kind", where)
    account = keys.text_or_null(document, "account", where)
    if kind not in KINDS:
        account, kind = None, None
    return Spelled(
        login=keys.text(document, "login", where),
        account=account,
        kind=kind,
        reason=keys.text_or_null(document, "reason", where),
    )


def _unread(given: Mapping[str, Any]) -> Spelled:
    """An account the backbone could not be asked about."""
    return Spelled(login=str(given.get("login") or ""), account=None, kind=None)


# ---- shared steps ---------------------------------------------------------------


def _host(config: Mapping[str, Any] | None) -> str | None:
    """The host the capability's requests go to, where its configuration pins
    one (DEC-023), or None for `gh`'s own."""
    block = (config or {}).get("gh") if isinstance(config, Mapping) else None
    host = block.get("host") if isinstance(block, Mapping) else None
    return host if isinstance(host, str) and host else None


def _options(host: str | None) -> dict[str, Any]:
    """The keywords of a call of the backbone: its output captured as text, and
    the capability's host passed on as ``GH_HOST`` where it pins one."""
    options: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "check": False,
        "timeout": TIMEOUT,
    }
    if host is not None:
        options["env"] = {**os.environ, "GH_HOST": host}
    return options
