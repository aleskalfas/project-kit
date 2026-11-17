"""Team membership predicate library (per DEC-021).

Resolves the invoker's identity from `gh` / `git` / env, reads the
adopter's `members.yaml`, and returns whether the invoker is allowed
to mutate methodology state.

Two modes:
  * Open mode  — `members.yaml` is absent OR `members:` is empty list.
                 Any invoker passes.
  * Closed mode — `members.yaml` has ≥1 member entry. Only listed
                  members pass. Where GitHub answers that the credential
                  acts as a user's account, only an entry naming that
                  login passes. Otherwise identity matches by
                  `github_login` or `email`; either surface is sufficient.

The library is dependency-free at import time so it can be imported
from any PEP 723 script regardless of what `dependencies:` block the
script declares. YAML parsing is the caller's responsibility — scripts
read `members.yaml` themselves and pass the parsed `members` list to
`check_membership()`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

CAPABILITY_NAME = "project-management"
MEMBERS_RELATIVE = "project/members.yaml"
#: The seconds `gh api user` is given to name the account acting.
GH_USER_TIMEOUT = 10
#: The variable a CI or agent context sets to name the invoker, read only where
#: GitHub names no user's account for the credential (DEC-021, "Identity resolution").
INVOKER_VARIABLE = "PM_INVOKER_LOGIN"
#: What GitHub is asked of an account: its login and its type, tab-separated.
ACCOUNT_FIELDS = "[.login, .type] | @tsv"
#: The type GitHub gives a user's account, as against an app's or an organization's.
USER_TYPE = "User"
#: Where an identity's login came from: GitHub's answer for the credential, or
#: `PM_INVOKER_LOGIN` where GitHub named no user's account.
FROM_SERVICE = "service"
FROM_VARIABLE = "variable"


@dataclass(frozen=True)
class Identity:
    """Resolved identity for the user invoking a pm script.

    ``unresolved_cause`` says why ``github_login`` could not be resolved, such
    as `gh api user`'s refusal, where it could not. A command that acts on an
    account it cannot tell words its message from it, through
    :func:`format_unresolved`.

    ``login_source`` says where ``github_login`` came from: ``FROM_SERVICE``,
    a user's account GitHub answers for the credential, or ``FROM_VARIABLE``,
    `PM_INVOKER_LOGIN` where GitHub named none. ``service_cause`` says why
    GitHub named none, where the login is the variable's."""

    github_login: str | None
    email: str | None
    unresolved_cause: str | None = None
    login_source: str | None = None
    service_cause: str | None = None

    def label(self) -> str:
        """A single human-readable label for refusal / log lines."""
        return self.github_login or self.email or "<unresolved>"


@dataclass(frozen=True)
class MembershipResult:
    """Outcome of a membership predicate check."""

    allowed: bool
    mode: str  # "open" | "closed"
    invoker: Identity
    refusal_message: str | None = None


def resolve_invoker_identity(
    config: dict | None = None,
    gh_login_provider=None,
    email_provider=None,
) -> Identity:
    """Resolve the invoker's identity from gh / git / env (DEC-021,
    "Identity resolution").

    GitHub is asked first, whether or not `PM_INVOKER_LOGIN` is set:
    `gh api user`, routed through the gh helper per
    [project-management:DEC-023-gh-host-and-owner], so the call lands on
    the host declared in `config['gh']['host']` when set. It is asked once
    per process and host (:func:`service_answer`).

      1. Where GitHub answers that the credential acts as a user's
         account, that login alone is the identity, whatever the variable
         names. A variable that names another account is ignored, with a
         warning once per process.
      2. Otherwise `PM_INVOKER_LOGIN`, where it is set, names the invoker.
      3. Otherwise the login is unresolved, with GitHub's cause.

    The email comes from `git config user.email` when available, in every
    case: the gate matches it only where GitHub named no user's account
    (:func:`check_membership`), and the audit comment carries it (DEC-014).

    A login that cannot be resolved is reported here, with its cause, as the
    identity's `unresolved_cause` (#3162).

    `config` is the adopter's parsed `project/config.yaml`. When omitted,
    the gh call uses ambient state (equivalent to single-org github.com).
    `gh_login_provider` and `email_provider` are testing seams; a
    `gh_login_provider` passed is asked on every call, with no memo.
    `gh_login_provider` returns `(login, None)` where GitHub answers with
    a user's account, or `(None, cause)` where it names none;
    `email_provider` returns a string-or-None. Production uses subprocess.
    """
    if gh_login_provider is None:
        answered, cause = service_answer(config or {})
    else:
        answered, cause = gh_login_provider()
    if email_provider is None:
        email_provider = _email_via_subprocess
    email = email_provider() or None

    variable = os.environ.get(INVOKER_VARIABLE)
    if answered:
        _warn_if_ignored(variable, answered)
        return Identity(github_login=answered, email=email, login_source=FROM_SERVICE)
    if not variable:
        return Identity(github_login=None, email=email, unresolved_cause=cause)
    login = variable.strip()
    if login:
        return Identity(
            github_login=login,
            email=email,
            login_source=FROM_VARIABLE,
            service_cause=cause,
        )
    blank = f"{INVOKER_VARIABLE} holds only blanks"
    return Identity(
        github_login=None,
        email=email,
        unresolved_cause=f"{cause}, and {blank}" if cause else blank,
    )


def check_membership(
    members: list[dict],
    invoker: Identity,
) -> MembershipResult:
    """Apply the membership predicate to a parsed members list.

    `members` is the `members:` field of the parsed `members.yaml`.
    An empty list (or absent / unparseable file represented as `[]`
    by the caller) means open mode.

    Where GitHub answered the login (`login_source` is `FROM_SERVICE`),
    only an entry whose `github_login` names that account passes, without
    regard to case, since GitHub looks an account's name up so; git's email
    and `PM_INVOKER_LOGIN` count for nothing (DEC-021). Otherwise the match
    is positive if the login or the email matches an entry's field. An
    identity with no `login_source`, such as a stand-in, is matched the
    second way.

    Returns a `MembershipResult`. When `allowed=False`, the
    `refusal_message` field carries the standard structured refusal.
    """
    if not members:
        return MembershipResult(allowed=True, mode="open", invoker=invoker)

    answered = getattr(invoker, "login_source", None) == FROM_SERVICE
    for entry in members:
        if not isinstance(entry, dict):
            continue
        if answered:
            if same_account(entry.get("github_login"), invoker.github_login):
                return MembershipResult(allowed=True, mode="closed", invoker=invoker)
            continue
        if invoker.github_login and entry.get("github_login") == invoker.github_login:
            return MembershipResult(allowed=True, mode="closed", invoker=invoker)
        if invoker.email and entry.get("email") == invoker.email:
            return MembershipResult(allowed=True, mode="closed", invoker=invoker)

    return MembershipResult(
        allowed=False,
        mode="closed",
        invoker=invoker,
        refusal_message=format_refusal(invoker, members),
    )


def same_account(one: object, other: object) -> bool:
    """Whether two logins name one GitHub account: both are logins, equal
    without regard to case, as GitHub looks an account's name up."""
    return (
        isinstance(one, str)
        and isinstance(other, str)
        and bool(one)
        and one.casefold() == other.casefold()
    )


def format_refusal(invoker: Identity, members: Sequence[object] = ()) -> str:
    """Standard refusal message per DEC-021's structured refusal. Where the
    invoker's login could not be resolved, it says so, and why. Where GitHub
    answered the login, it names what the gate did not count beside it: a
    `PM_INVOKER_LOGIN` that names a member, and an entry git's email matches."""
    unresolved = ""
    if not invoker.github_login:
        unresolved = f"          → {format_unresolved(invoker.unresolved_cause)}.\n"
    not_counted = "".join(f"          → {line}\n" for line in _not_counted(invoker, members))
    return (
        "[refused] Membership required for this operation\n"
        f"          → This repository is in closed mode "
        f"(.pkit/capabilities/{CAPABILITY_NAME}/{MEMBERS_RELATIVE} "
        "has ≥1 entry).\n"
        f"          → Your identity ({invoker.label()}) is not in the "
        "member list.\n"
        f"{unresolved}"
        f"{not_counted}"
        "          → Remediation: ask an existing member to add you via "
        f"`pkit {CAPABILITY_NAME} add-member`."
    )


def _not_counted(invoker: Identity, members: Sequence[object]) -> list[str]:
    """What names a member beside a login GitHub answered, which the gate
    does not count (DEC-021): one line for each."""
    if getattr(invoker, "login_source", None) != FROM_SERVICE:
        return []
    entries = [entry for entry in members if isinstance(entry, dict)]
    lines = []
    variable = (os.environ.get(INVOKER_VARIABLE) or "").strip()
    if not same_account(variable, invoker.github_login) and any(
        same_account(entry.get("github_login"), variable) for entry in entries
    ):
        lines.append(
            f"{INVOKER_VARIABLE} names the member {variable}, and is no identity "
            f"where GitHub answers that the credential acts as a user's account "
            f"({invoker.github_login})."
        )
    if invoker.email:
        matched = [entry for entry in entries if entry.get("email") == invoker.email]
        if matched:
            lines.append(
                f"git's email ({invoker.email}) matches the entry of "
                f"{matched[0].get('github_login')}, and counts only where GitHub "
                "answers with no user's account."
            )
    return lines


def format_unresolved(cause: str | None) -> str:
    """The report of an account pkit cannot tell: that it cannot tell which
    account is acting, and why, where the cause is known (#3162). A command
    that acts on such an account words its message from this one sentence,
    whose cause is an identity's `unresolved_cause`."""
    because = f", since {cause}" if cause else ""
    return f"pkit cannot tell which account is acting{because}"


def members_path(capability_root: Path) -> Path:
    """The canonical path to `members.yaml` for this capability."""
    return capability_root / MEMBERS_RELATIVE


def resolve_capability_root(explicit: Path | None) -> Path | None:
    """Walk up from CWD until `.pkit/capabilities/<CAPABILITY_NAME>/` is found.

    Returns None when the capability is not installed at the expected
    path. Used by every pm script for adopter-root discovery.
    """
    if explicit is not None:
        return explicit if explicit.is_dir() else None
    cur = Path.cwd()
    while cur != cur.parent:
        candidate = cur / ".pkit" / "capabilities" / CAPABILITY_NAME
        if candidate.is_dir():
            return candidate
        cur = cur.parent
    return None


# ---- GitHub's answer for the credential ----------------------------

#: GitHub's answer for the credential, by the host asked, kept for the life of
#: the process, so a command and the commands it loads in-process ask once. A
#: child process asks again.
_service_answers: dict[str | None, tuple[str | None, str | None]] = {}
#: Whether the warning on an ignored `PM_INVOKER_LOGIN` was given.
_warned = False


def service_answer(config: dict | None = None) -> tuple[str | None, str | None]:
    """GitHub's answer for the credential, asked once per process and host:
    `(login, None)` where it acts as a user's account, or `(None, cause)`."""
    from _lib.gh import gh_env  # deferred to avoid circular import at module load

    host = gh_env(config or {}).get("GH_HOST")
    if host not in _service_answers:
        _service_answers[host] = _gh_login_via_subprocess(config or {})
    return _service_answers[host]


def forget_service_answers() -> None:
    """Forget GitHub's answers and the warning given, as a new process holds
    neither. For a test that loads this module once and runs many cases."""
    global _warned
    _service_answers.clear()
    _warned = False


def _warn_if_ignored(variable: str | None, answered: str) -> None:
    """Say once per process, on stderr, that `PM_INVOKER_LOGIN` names another
    account than the one GitHub answered, and is ignored."""
    global _warned
    named = (variable or "").strip()
    if _warned or not named or same_account(named, answered):
        return
    _warned = True
    print(
        f"[warn] {INVOKER_VARIABLE} names {named}, but GitHub answers that the "
        f"credential acts as the user's account {answered}. pkit takes {answered} "
        "as the account acting and ignores the variable (DEC-021).",
        file=sys.stderr,
    )


# ---- subprocess helpers (testing seams) ----------------------------


def _gh_login_via_subprocess(config: dict | None = None) -> tuple[str | None, str | None]:
    """Ask `gh api user` which account the credential acts as, through the gh
    helper: `(login, None)` where it answers with a user's account, or
    `(None, cause)` where it does not, the cause in words.

    The answer is a login and a type, tab-separated (`ACCOUNT_FIELDS`). An
    answer with fewer fields, an empty one included, is no answer, and a type
    other than `User`, such as an app's `Bot`, names no user's account.
    GitHub refuses `/user` to an app installation's token and to a
    workflow's, so such a credential takes the no-answer path here.

    Routes the call through `_lib.gh.gh_run` so the adopter's pinned host
    (per DEC-023) determines which GitHub instance answers. Without
    config (or with no `gh.host` set), the call uses ambient `gh` state.

    Uses `from _lib.gh import gh_run` matching the convention used by
    parent scripts (e.g. move-issue.py, start-work.py). This requires
    that the caller has `scripts/` on sys.path, which every pm script
    ensures via `sys.path.insert(0, str(_HERE))` before importing.
    """
    from _lib.comment_log import said  # deferred, as gh_run is
    from _lib.gh import gh_run  # deferred to avoid circular import at module load

    try:
        proc = gh_run(
            ["gh", "api", "user", "--jq", ACCOUNT_FIELDS],
            config or {},
            check=False,
            timeout=GH_USER_TIMEOUT,
        )
    except FileNotFoundError:
        return None, "`gh` is not on PATH"
    except subprocess.TimeoutExpired:
        return None, f"`gh api user` did not answer within {GH_USER_TIMEOUT} seconds"
    if proc.returncode != 0:
        return None, f"`gh api user` failed: {said(proc)}"
    answer = proc.stdout.strip()
    if not answer:
        return None, "`gh api user` answered no login"
    account = _account(answer)
    if account is None:
        return None, f"`gh api user` answered {answer!r}, not a login and an account type"
    login, account_type = account
    if account_type != USER_TYPE:
        return None, (
            f"`gh api user` answered {login}, an account of type {account_type}, not a user's"
        )
    return login, None


@dataclass(frozen=True)
class LookedUp:
    """What GitHub answers for a login. Where it names an account, `login` is
    the login as GitHub spells it and `account_type` the account's type.
    `missing` is True where it knows no account by the login. Where it gave
    no answer, `cause` says why."""

    login: str | None = None
    account_type: str | None = None
    missing: bool = False
    cause: str | None = None


def look_up_account(login: str, config: dict | None = None) -> LookedUp:
    """Ask GitHub for the account a login names, `gh api users/<login>`, so
    an entry can name a user's login as GitHub spells it (DEC-021, "File
    location and shape")."""
    from _lib.comment_log import said  # deferred, as gh_run is
    from _lib.gh import gh_run  # deferred to avoid circular import at module load

    asked = f"`gh api users/{login}`"
    try:
        proc = gh_run(
            ["gh", "api", f"users/{quote(login, safe='[]')}", "--jq", ACCOUNT_FIELDS],
            config or {},
            check=False,
            timeout=GH_USER_TIMEOUT,
        )
    except FileNotFoundError:
        return LookedUp(cause="`gh` is not on PATH")
    except subprocess.TimeoutExpired:
        return LookedUp(cause=f"{asked} did not answer within {GH_USER_TIMEOUT} seconds")
    if proc.returncode != 0:
        if "HTTP 404" in (proc.stderr or ""):
            return LookedUp(missing=True)
        return LookedUp(cause=f"{asked} failed: {said(proc)}")
    account = _account(proc.stdout.strip())
    if account is None:
        return LookedUp(cause=f"{asked} answered no login and account type")
    return LookedUp(login=account[0], account_type=account[1])


def _account(answer: str) -> tuple[str, str] | None:
    """A login and an account type, from GitHub's tab-separated answer, or
    None where it holds anything else."""
    fields = answer.split("\t")
    if len(fields) != 2 or not all(field.strip() for field in fields):
        return None
    return fields[0].strip(), fields[1].strip()


def _email_via_subprocess() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None
