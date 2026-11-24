"""The acting account: which account on the hosting service the credential acts as.

ADR-094 decides it. This module is the one home of the reading (point 1): it
asks the hosting service, through `gh`, which account the credential acts as,
and names an account, a user's or a bot's, only from the service's answer
(point 2). Beside it is the one function that spells accounts named by any
surface and compares them (point 3).

- **The reading** (:func:`read`) has three outcomes. *Resolved*: the service
  answered with the account and its kind. *An unnamed account*: the service
  refused the request because the credential is an integration's, or answered
  with an account of a kind unknown. *An unresolved identity*: every other
  outcome. Each comes with its cause, a value of :data:`CAUSES`, and a reason
  for people. It asks at most once in a run (point 4), never under the offline
  marker, and within :data:`READ_SECONDS`.
- **The spelling** (:func:`spell`). A user's account is spelled by its login, a
  bot's by its login with the service's `[bot]` suffix. Every other account is
  of a kind unknown and has no spelling, and so is a string no login can be.
  The kind comes only from the form the caller names (:data:`FORMS`).
- **The comparison** (:func:`compare`, :func:`fold`) answers that two accounts
  are one, that they are two, or that it cannot tell (:data:`ANSWERS`). It
  sets aside the case of ASCII letters and surrounding whitespace, and asks
  the service nothing.

The request is REST's `GET /user`. It holds under a user's credential, and an
installation's token is refused it as an integration's, so such a credential
reads as an unnamed account: the first request of point 1 asked alone, until a
measurement finds a second that names an installation's own account.

GitHub only, through `gh`, and provisional (point 7). The process engine never
calls this module: it takes the actor its caller names (ADR-098).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from project_kit import command_runner

#: The version of every document the reading command prints (ADR-097).
SCHEMA_VERSION = 1

#: How long the reading waits for the service before it reads no answer.
READ_SECONDS = 15.0

KIND_USER = "user"
KIND_BOT = "bot"
#: The kinds the function knows (point 3). Every other account is of a kind unknown.
KINDS = (KIND_USER, KIND_BOT)

#: The suffix the service's REST interface gives a bot's login, an app's among them.
BOT_SUFFIX = "[bot]"
#: The prefix gh's JSON gives every author the service does not record as a user's.
GH_PREFIX = "app/"

# The causes where the reading names no account (point 1). The first two are an
# unnamed account: the service answered that the credential's account is no
# user's. The rest are an unresolved identity: the service said nothing of who
# the credential is.
CAUSE_INTEGRATION_REFUSED = "integration-refused"
CAUSE_KIND_UNKNOWN = "kind-unknown"
CAUSE_REFUSED = "refused"
CAUSE_NO_ANSWER = "no-answer"
CAUSE_GH_MISSING = "gh-missing"
CAUSE_OFFLINE = "offline"
CAUSE_TIMEOUT = "timeout"
CAUSE_NO_ACCOUNT = "no-account"
CAUSES = (
    CAUSE_INTEGRATION_REFUSED,
    CAUSE_KIND_UNKNOWN,
    CAUSE_REFUSED,
    CAUSE_NO_ANSWER,
    CAUSE_GH_MISSING,
    CAUSE_OFFLINE,
    CAUSE_TIMEOUT,
    CAUSE_NO_ACCOUNT,
)
#: The causes of an unnamed account, the service's answer that no user acts.
UNNAMED_CAUSES = frozenset({CAUSE_INTEGRATION_REFUSED, CAUSE_KIND_UNKNOWN})

# The forms a caller names each account in, which say where its kind comes from
# (point 3, "The forms a caller gives").
FORM_ENTRY = "entry"
FORM_TYPED = "typed"
FORM_GH = "gh"
FORM_USERS_FIELD = "users-field"
FORM_LOGIN = "login"
FORMS = (FORM_ENTRY, FORM_TYPED, FORM_GH, FORM_USERS_FIELD, FORM_LOGIN)

ANSWER_ONE = "one"
ANSWER_TWO = "two"
ANSWER_CANNOT_TELL = "cannot-tell"
#: What a comparison answers (point 3, "What a comparison answers").
ANSWERS = (ANSWER_ONE, ANSWER_TWO, ANSWER_CANNOT_TELL)

#: The type the service's REST interface records for a user's account.
USER_TYPE = "User"
#: The status and the service's stated reason of the integration's refusal, the
#: one refusal whose words the reading reads (point 2; project-management DEC-073
#: point 2).
_INTEGRATION_STATUS = 403
_INTEGRATION_REASON = "Resource not accessible by integration"
#: The variable the offline marker sets (ADR-057 point 3).
OFFLINE_VARIABLE = "PKIT_OFFLINE"
#: What the reading asks `gh` to print of the signed-in account: its login, type
#: and id, tab-separated. A refusal prints the service's body as it stands.
ACCOUNT_FIELDS = "[.login, .type, .id] | @tsv"

_LOGIN_LETTERS = re.compile(r"[A-Za-z0-9_-]+")
_HTTP_STATUS = re.compile(r"\(HTTP (\d{3})\)")


class FormError(ValueError):
    """A request to spell or compare that the function refuses: a form it does
    not know, or an account given with no login. Its caller reads the refusal
    as no document (point 1)."""


# ---- the spelling ----------------------------------------------------------


@dataclass(frozen=True)
class Account:
    """One account as the function reads it.

    `login` is the string the caller gave, or the service answered. `kind` is
    :data:`KIND_USER`, :data:`KIND_BOT` or None, a kind unknown. `account` is
    the one spelling, None wherever the kind is unknown or the string names no
    account the function can tell. `reason` says, for people, why an account
    has no spelling, None where it has one."""

    login: str
    kind: str | None
    account: str | None
    reason: str | None = None
    #: The login with the suffix and the prefix set aside, in ASCII lower case:
    #: what two accounts are compared by. None for a string with no spelling.
    name: str | None = None

    def document(self) -> dict[str, Any]:
        """The account as the reading command gives it, asked to spell or to
        compare: its `id` is null, since the function asks the service nothing
        (point 1, "When its keys are null")."""
        return {
            "account": self.account,
            "kind": self.kind,
            "id": None,
            "login": self.login,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class _Letters:
    """A string read as a login: its name with the suffix and the prefix set
    aside, and which of the two it carried. `name` is None where the string
    can be no login, and `why` then says why."""

    name: str | None
    suffixed: bool = False
    prefixed: bool = False
    why: str | None = None


def _letters(given: str) -> _Letters:
    """Read `given` as a login, its surrounding whitespace set aside (point 3,
    "A string with no spelling")."""
    text = given.strip()
    prefixed = text.startswith(GH_PREFIX)
    if prefixed:
        text = text[len(GH_PREFIX) :]
    suffixed = text.endswith(BOT_SUFFIX)
    if suffixed:
        text = text[: -len(BOT_SUFFIX)]
    if prefixed and suffixed:
        return _Letters(None, why=f"it holds gh's {GH_PREFIX!r} and {BOT_SUFFIX!r} together")
    if not text:
        return _Letters(None, why="it holds no login")
    if _LOGIN_LETTERS.fullmatch(text) is None:
        return _Letters(
            None, why="it holds a character no login holds, such as '@' or a space inside"
        )
    return _Letters(text, suffixed=suffixed, prefixed=prefixed)


def _ascii_lower(text: str) -> str:
    """`text` with its ASCII letters in lower case, and no other folding."""
    return text.translate(_ASCII_LOWER)


_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def spell(
    login: str,
    form: str,
    *,
    account_type: str | None = None,
    account_id: int | str | None = None,
    is_bot: bool | None = None,
) -> Account:
    """Read `login`, given in `form`, as an account in the one spelling.

    The kind comes from the form alone (point 3, "Where a kind comes from"):

    - :data:`FORM_ENTRY`, an entry or a value pkit holds: a login with the
      suffix is a bot's, and so is gh's form `app/<name>`, read as
      `<name>[bot]`; a bare one is a user's;
    - :data:`FORM_TYPED`, a login with the type the service records for it:
      `User` is a user's; any other type on a login with no suffix is a kind
      unknown;
    - :data:`FORM_GH`, a login with gh's id and bot flag: an id, gh's node
      id or a number, and no bot flag is a user's; anything else is a kind
      unknown, since gh writes an app's account, a mannequin and an
      organization alike;
    - :data:`FORM_USERS_FIELD`, a login from a field the service declares to
      hold users' accounts only: a user's;
    - :data:`FORM_LOGIN`, a login and nothing more: a kind unknown.

    In every form, a login with the suffix names a bot's account, whatever
    type a surface gives, and outside an entry a login with gh's prefix is of
    a kind unknown. Raises :class:`FormError` for a form the function does
    not know."""
    if form not in FORMS:
        raise FormError(f"unknown form {form!r}; the forms are {', '.join(FORMS)}")
    letters = _letters(login)
    if letters.name is None:
        why = f"{login!r} names no account: {letters.why}"
        return Account(login=login, kind=None, account=None, reason=why)
    name = _ascii_lower(letters.name)
    kind = _kind(letters, form, account_type=account_type, account_id=account_id, is_bot=is_bot)
    if kind is None:
        return Account(
            login=login,
            kind=None,
            account=None,
            reason=_unknown_reason(login, form, account_type),
            name=name,
        )
    spelled = letters.name + BOT_SUFFIX if kind == KIND_BOT else letters.name
    return Account(login=login, kind=kind, account=spelled, name=name)


def _kind(
    letters: _Letters,
    form: str,
    *,
    account_type: str | None,
    account_id: int | str | None,
    is_bot: bool | None,
) -> str | None:
    """The kind `form` gives a login read as `letters`, or None, a kind unknown."""
    if letters.suffixed:
        return KIND_BOT
    if form == FORM_ENTRY:
        return KIND_BOT if letters.prefixed else KIND_USER
    if letters.prefixed:
        return None
    if form == FORM_TYPED:
        return KIND_USER if account_type == USER_TYPE else None
    if form == FORM_GH:
        return KIND_USER if account_id not in (None, "") and is_bot is False else None
    if form == FORM_USERS_FIELD:
        return KIND_USER
    return None


def _unknown_reason(login: str, form: str, account_type: str | None) -> str:
    """Why an account of a kind unknown has no spelling, for people."""
    if form == FORM_TYPED and account_type:
        return (
            f"{login!r} is an account of type {account_type!r} with no {BOT_SUFFIX!r} "
            "suffix, a kind pkit does not spell"
        )
    return f"nothing given with {login!r} says whether it is a user's account or a bot's"


def compare(left: Account, right: Account) -> str:
    """Whether `left` and `right` are one account, two, or the function cannot
    tell (point 3, "What a comparison answers"):

    - *one* where both kinds are known and the spellings are equal;
    - *two* where both kinds are known and the spellings differ, or where one is
      a user's account and the other's login, the suffix and the prefix set
      aside, is another;
    - *cannot tell* in every other case, a string with no spelling among it.

    Case of ASCII letters and surrounding whitespace are set aside."""
    if left.name is None or right.name is None:
        return ANSWER_CANNOT_TELL
    if left.account is not None and right.account is not None:
        same = _ascii_lower(left.account) == _ascii_lower(right.account)
        return ANSWER_ONE if same else ANSWER_TWO
    if KIND_USER in (left.kind, right.kind) and left.name != right.name:
        return ANSWER_TWO
    return ANSWER_CANNOT_TELL


def fold(answers: Sequence[str]) -> str:
    """One account's answers against many, folded (point 3, "One against
    many"): *one* where it is one with some entry, *two* where it is two with
    every entry, *cannot tell* otherwise. An answer the fold does not know
    reads as *cannot tell*."""
    if ANSWER_ONE in answers:
        return ANSWER_ONE
    if all(answer == ANSWER_TWO for answer in answers):
        return ANSWER_TWO
    return ANSWER_CANNOT_TELL


# ---- the reading -----------------------------------------------------------


@dataclass(frozen=True)
class Reading:
    """What the reading found. Where it names an account, `account` is that
    account in the one spelling, with its `kind`, `id` and `login` as the
    service answered, and `cause` is None. Where it names none, each of those
    is None and `cause` says why, a value of :data:`CAUSES`, with `reason`
    giving the service's words or the reading's own, for people."""

    account: str | None = None
    kind: str | None = None
    id: int | None = None
    login: str | None = None
    cause: str | None = None
    reason: str | None = None

    @property
    def named(self) -> bool:
        """Whether the reading names an account."""
        return self.account is not None

    @property
    def unnamed(self) -> bool:
        """Whether the service answered that the credential's account is no
        user's, and the reading can name none."""
        return self.cause in UNNAMED_CAUSES

    def document(self) -> dict[str, Any]:
        """The reading command's document (point 1, "When its keys are null")."""
        return {
            "schema_version": SCHEMA_VERSION,
            "account": self.account,
            "kind": self.kind,
            "id": self.id,
            "login": self.login,
            "cause": self.cause,
            "reason": self.reason,
        }

    def because(self) -> str:
        """Why the reading names no account, as a clause for people: the reason
        where there is one, else the cause."""
        return self.reason or self.cause or "the reading names no account"


#: The reading's answer in this run, asked at most once (point 4).
_answered: Reading | None = None


def read() -> Reading:
    """Which account the credential acts as, asked of the service at most once
    in this process: the answer of the first call is the answer of every
    later one (point 4)."""
    global _answered
    if _answered is None:
        _answered = _ask()
    return _answered


def forget_service_answers() -> None:
    """Forget this process's answer, as a new run holds none. For tests, whose
    shared fixture forgets every module's answers by this name."""
    global _answered
    _answered = None


def _ask() -> Reading:
    """Ask the service, through `gh api user`, which account the credential
    acts as, and read its answer (point 2). The service's host is `gh`'s,
    from the caller's environment (point 1)."""
    if os.environ.get(OFFLINE_VARIABLE):
        return Reading(
            cause=CAUSE_OFFLINE,
            reason=f"the offline marker ({OFFLINE_VARIABLE}) is set, so the service was not asked",
        )
    asked = "`gh api user`"
    try:
        proc = command_runner.run_bounded(
            ["gh", "api", "user", "--jq", ACCOUNT_FIELDS], cwd=None, seconds=READ_SECONDS
        )
    except FileNotFoundError:
        return Reading(cause=CAUSE_GH_MISSING, reason="`gh` is not on PATH")
    except subprocess.TimeoutExpired:
        return Reading(
            cause=CAUSE_TIMEOUT,
            reason=f"{asked} did not answer within {READ_SECONDS:g} seconds, and was ended",
        )
    except OSError as exc:
        return Reading(cause=CAUSE_NO_ANSWER, reason=f"{asked} could not be run: {exc}")
    if proc.returncode < 0:
        return Reading(
            cause=CAUSE_NO_ANSWER, reason=f"{asked} was ended by signal {-proc.returncode}"
        )
    if proc.returncode != 0:
        return _refusal(proc, asked)
    return _answer(proc.stdout, asked)


def _refusal(proc: subprocess.CompletedProcess[str], asked: str) -> Reading:
    """Read a run of `gh` that failed: the integration's refusal, another
    refusal, or no answer where the service gave no status."""
    said = (proc.stderr or "").strip()
    found = _HTTP_STATUS.findall(said)
    status = int(found[-1]) if found else None
    stated = _stated_reason(proc.stdout)
    words = stated or said or f"{asked} exited {proc.returncode}"
    if status is None:
        return Reading(cause=CAUSE_NO_ANSWER, reason=f"{asked} failed: {words}")
    if status == _INTEGRATION_STATUS and stated == _INTEGRATION_REASON:
        return Reading(
            cause=CAUSE_INTEGRATION_REFUSED,
            reason=(
                f"the service refused {asked} because the credential is an "
                f"integration's: {stated} (HTTP {status})"
            ),
        )
    if status >= 500:
        return Reading(cause=CAUSE_NO_ANSWER, reason=f"the service failed: {words} (HTTP {status})")
    return Reading(cause=CAUSE_REFUSED, reason=f"the service refused {asked}: {words}")


def _stated_reason(stdout: str | None) -> str | None:
    """The service's stated reason, the `message` of the body `gh` prints for
    a refusal, or None where it printed none."""
    body = _json_object(stdout)
    message = body.get("message") if body is not None else None
    return message.strip() if isinstance(message, str) and message.strip() else None


def _answer(stdout: str | None, asked: str) -> Reading:
    """Read the service's answer for the signed-in account: its login, type and
    id, tab-separated (:data:`ACCOUNT_FIELDS`). A type or an id left out is
    none given."""
    fields = [field.strip() for field in (stdout or "").strip("\r\n").split("\t")]
    login = fields[0]
    if not login:
        return Reading(cause=CAUSE_NO_ACCOUNT, reason=f"{asked} answered no account")
    account_type = fields[1] if len(fields) > 1 and fields[1] else None
    account_id = int(fields[2]) if len(fields) > 2 and fields[2].isdigit() else None
    found = spell(login, FORM_TYPED, account_type=account_type)
    if found.name is None:
        return Reading(cause=CAUSE_NO_ACCOUNT, reason=f"{asked} answered {login!r}, no login")
    if found.account is None:
        return Reading(
            cause=CAUSE_KIND_UNKNOWN,
            reason=(
                f"the service answered that the credential acts as {login}, an account of "
                f"type {account_type or 'unknown'} that is no user's and that pkit cannot spell"
            ),
        )
    return Reading(account=found.account, kind=found.kind, id=account_id, login=login)


def _json_object(text: str | None) -> Mapping[str, Any] | None:
    """`text` parsed as a JSON object, or None where it is no object."""
    try:
        parsed: object = json.loads(text or "")
    except (json.JSONDecodeError, ValueError):
        return None
    return cast("Mapping[str, Any]", parsed) if isinstance(parsed, dict) else None


# ---- the documents a caller asks to spell or compare -------------------------


def account_from_request(given: object) -> Account:
    """An account given in a request to spell or compare: an object with its
    `form` and `login`, and `type`, `id` or `is_bot` where the form reads them.
    Raises :class:`FormError` for anything else."""
    if not isinstance(given, dict):
        raise FormError("each account is an object with its `form` and its `login`")
    fields = cast("dict[str, Any]", given)
    form = fields.get("form")
    login = fields.get("login")
    if not isinstance(form, str):
        raise FormError("an account names no `form`")
    if not isinstance(login, str):
        raise FormError("an account names no `login`")
    account_type = fields.get("type")
    account_id = fields.get("id")
    is_bot = fields.get("is_bot")
    return spell(
        login,
        form,
        account_type=account_type if isinstance(account_type, str) else None,
        account_id=_given_id(account_id),
        is_bot=is_bot if isinstance(is_bot, bool) else None,
    )


def _given_id(value: object) -> int | str | None:
    """An id a request gives: a number, or a string such as gh's node id with
    something in it. Anything else is no id."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return value
    return None


def spell_document(request: object) -> dict[str, Any]:
    """The document the reading command prints, asked to spell `request`'s
    `accounts`, in their order. Raises :class:`FormError` on a malformed
    request."""
    accounts = _list_of(request, "accounts")
    return {
        "schema_version": SCHEMA_VERSION,
        "accounts": [account_from_request(given).document() for given in accounts],
    }


def compare_document(request: object) -> dict[str, Any]:
    """The document the reading command prints, asked to compare `request`'s
    `pairs`, each two accounts, and its `folds`, each one `account` against the
    accounts `among`, all in their order. Raises :class:`FormError` on a
    malformed request."""
    pairs: list[dict[str, Any]] = []
    for given in _list_of(request, "pairs", required=False):
        if not isinstance(given, list) or len(cast("list[object]", given)) != 2:
            raise FormError("each of `pairs` is a list of two accounts")
        left, right = (account_from_request(one) for one in cast("list[object]", given))
        pairs.append(
            {"answer": compare(left, right), "accounts": [left.document(), right.document()]}
        )
    folds: list[dict[str, Any]] = []
    for given in _list_of(request, "folds", required=False):
        if not isinstance(given, dict):
            raise FormError("each of `folds` is an object with an `account` and `among`")
        question = cast("dict[str, Any]", given)
        account = account_from_request(question.get("account"))
        among = [account_from_request(one) for one in _list_of(question, "among")]
        answers = [compare(account, entry) for entry in among]
        folds.append(
            {
                "answer": fold(answers),
                "account": account.document(),
                "among": [
                    {"answer": answer, "account": entry.document()}
                    for answer, entry in zip(answers, among, strict=True)
                ],
            }
        )
    return {"schema_version": SCHEMA_VERSION, "pairs": pairs, "folds": folds}


def _list_of(request: object, key: str, *, required: bool = True) -> list[object]:
    """`request[key]` where it is a list. A missing key is an empty list where
    it is not `required`; anything else raises :class:`FormError`."""
    if not isinstance(request, dict):
        raise FormError("the request is a JSON object")
    value = cast("dict[str, Any]", request).get(key)
    if value is None and not required:
        return []
    if not isinstance(value, list):
        raise FormError(f"the request's `{key}` is a list")
    return cast("list[object]", value)


def search_name(account: str) -> str:
    """The name the service's search gives `account`, an account in the one
    spelling: a bot's as `app/<name>`, a user's by its login (point 3,
    "Requests"). It is the form a request takes, never a respelling, so nothing
    is stored or compared in it."""
    if account.endswith(BOT_SUFFIX):
        return GH_PREFIX + account.removesuffix(BOT_SUFFIX)
    return account


def kind_phrase(reading: Reading) -> str:
    """The account a reading names, said for people, with its kind where it is
    a bot's: `@alice`, or `@robot[bot], a bot's account`."""
    if reading.account is None:
        return "no account"
    if reading.kind == KIND_BOT:
        return f"@{reading.account}, a bot's account"
    return f"@{reading.account}"
