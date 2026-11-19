"""Team membership predicate library (per DEC-021 and DEC-076).

Resolves the invoker's identity from the backbone's reading of the acting
account, reads the adopter's `members.yaml`, and returns whether the invoker is
allowed to mutate methodology state.

**Who acts** ([project-management:DEC-076-app-credentials] point 1). The account
the credential acts as, and of which kind, comes from the backbone's one reading
(`pkit account read`, through `_lib.accounts`), which names an account only from
GitHub's answer ([pkit:ADR-094]). Nothing else names it: not git's email, and not
`PM_INVOKER_LOGIN`.

**The person the agent works for** (DEC-076 point 3). Where GitHub does not
answer that the credential acts as a user's account, `PM_INVOKER_LOGIN` names
the person whose work the session or the run does, read here and nowhere else.
That person serves only where naming a person grants nothing: the default
assignee, `--me`, and whose Task `start-work` compares with. Beside a user's
account GitHub answered, the variable is no identity.

Two modes:
  * Open mode  — `members.yaml` is absent OR `members:` is empty list.
                 Any invoker passes.
  * Closed mode — `members.yaml` has ≥1 member. Only an entry whose
                  `github_login` is one account with the acting account passes,
                  as the backbone compares accounts (ADR-094 point 3): a user's by
                  its login, a bot's by its own `<name>[bot]`. Where the commands
                  know no acting account, nothing passes. Git's email and the
                  variable pass nothing.

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
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

try:
    from _lib import accounts
except ImportError:  # pragma: no cover - `scripts/_lib/` itself on sys.path
    import accounts  # type: ignore[no-redef]

CAPABILITY_NAME = "project-management"
MEMBERS_RELATIVE = "project/members.yaml"
#: The seconds a lookup of an account by its login is given.
GH_USER_TIMEOUT = 10
#: The variable that names the person the agent works for, read only where
#: GitHub does not answer that the credential acts as a user's account
#: (DEC-076 point 3).
INVOKER_VARIABLE = "PM_INVOKER_LOGIN"
#: What GitHub is asked of an account: its login and its type, tab-separated.
ACCOUNT_FIELDS = "[.login, .type] | @tsv"
#: The type GitHub gives a user's account, as against an app's or an organization's.
USER_TYPE = "User"
#: The kinds of account the backbone's reading names.
KIND_USER = accounts.KIND_USER
KIND_BOT = accounts.KIND_BOT

#: A function that gives the backbone's reading, for a test that stands in for it.
ReadingProvider = Callable[[], accounts.Reading]


@dataclass(frozen=True)
class Identity:
    """Resolved identity for the user invoking a pm script.

    ``github_login`` is the account the credential acts as, in the backbone's
    one spelling, a user's or a bot's, and ``kind`` its kind. It is None where
    the commands know no acting account, and ``unresolved_cause`` then says
    why, for people, and ``cause`` gives the reading's cause. A command that
    acts on an account it cannot tell words its message from it, through
    :func:`format_unresolved`.

    ``works_for`` is the person the agent works for, `PM_INVOKER_LOGIN`'s
    value, read only where the credential names no user's account (DEC-076
    point 3). ``email`` is git's configured email, which no gate matches."""

    github_login: str | None
    email: str | None
    unresolved_cause: str | None = None
    kind: str | None = None
    cause: str | None = None
    works_for: str | None = None

    def label(self) -> str:
        """A single human-readable label for refusal / log lines."""
        return self.github_login or "<unresolved>"

    @property
    def names_user(self) -> bool:
        """Whether GitHub answered that the credential acts as a user's account.
        A stand-in that names an account and no kind is read by its form."""
        if self.github_login is None:
            return False
        if self.kind is not None:
            return self.kind == KIND_USER
        return not self.github_login.strip().endswith("[bot]")

    @property
    def unnamed(self) -> bool:
        """Whether GitHub answered that the credential's account is no user's,
        and the reading names none, such as for an App installation's token."""
        return self.github_login is None and self.cause in accounts.UNNAMED_CAUSES

    @property
    def unresolved(self) -> bool:
        """Whether GitHub gave no answer about who the credential is: an
        unresolved identity, under a person's own credential too (DEC-076)."""
        return self.github_login is None and not self.unnamed

    @property
    def person(self) -> str | None:
        """The person whose work this is: the user's account GitHub answered,
        or, under a credential that names no user's account, the person the
        agent works for, where `PM_INVOKER_LOGIN` names one (DEC-076 point 3)."""
        if self.names_user:
            return self.github_login
        return self.works_for

    def acts_as(self) -> str:
        """What the reading says the credential acts as, where it names no user's
        account, as a clause: a bot's account; no user's account and nothing
        naming who runs it, where GitHub answered so; or that pkit cannot tell,
        and why, where GitHub gave no answer (DEC-073 point 2's two outcomes)."""
        if self.github_login is not None:
            return (
                f"GitHub answers that the credential acts as {self.github_login}, a bot's "
                "account, which stands for no person"
            )
        if self.unnamed:
            because = f" ({self.unresolved_cause})" if self.unresolved_cause else ""
            return (
                f"GitHub answers that the credential names no user's account{because}, and "
                "nothing names who runs it"
            )
        return format_unresolved(self.unresolved_cause)

    def no_person(self) -> str:
        """Why no person stands for this run, and how a session names one, as a
        clause a refusal carries (DEC-076 point 3)."""
        return (
            f"{self.acts_as()}, and {INVOKER_VARIABLE} is not set, so no person is named for "
            f"whom this work is done. Set {INVOKER_VARIABLE} to the login of the person the agent "
            "works for, or run under a credential that names that person's account "
            "(DEC-076 point 3)"
        )


@dataclass(frozen=True)
class MembershipResult:
    """Outcome of a membership predicate check."""

    allowed: bool
    mode: str  # "open" | "closed"
    invoker: Identity
    refusal_message: str | None = None


def resolve_invoker_identity(
    config: dict | None = None,
    reading_provider: ReadingProvider | None = None,
    email_provider=None,
) -> Identity:
    """Resolve the invoker's identity (DEC-021, "Identity resolution", as
    DEC-076 refines it).

    The account comes from the backbone's reading of the acting account, once
    in a run for the host `config['gh']['host']` names (`_lib.accounts.read`):

      1. Where it names a user's account, that login alone is the identity,
         whatever the variable names. A variable that is set is ignored, with
         a warning once per process.
      2. Where it names a bot's account, that account is the identity, and
         `PM_INVOKER_LOGIN`, where it is set, names the person the agent works
         for (``works_for``), who is no identity.
      3. Where it names none, the commands know no acting account: the login
         is None, with the reading's cause, and the variable names the person
         the agent works for as in 2. Nothing falls back to git's email or the
         variable (DEC-076 point 1).

    The email comes from `git config user.email` when available. No gate
    matches it; `add-member --me` records it.

    `reading_provider` and `email_provider` are testing seams: the first
    returns an `accounts.Reading`, the second a string or None.
    """
    reading = reading_provider() if reading_provider is not None else accounts.read(config or {})
    if email_provider is None:
        email_provider = _email_via_subprocess
    email = email_provider() or None
    variable = (os.environ.get(INVOKER_VARIABLE) or "").strip() or None
    if reading.account is not None and reading.kind == KIND_USER:
        _warn_if_ignored(variable, reading.account)
        return Identity(github_login=reading.account, email=email, kind=KIND_USER)
    if reading.account is not None:
        return Identity(
            github_login=reading.account, email=email, kind=reading.kind, works_for=variable
        )
    return Identity(
        github_login=None,
        email=email,
        unresolved_cause=reading.because(),
        cause=reading.cause,
        works_for=variable,
    )


def check_membership(
    members: list[dict],
    invoker: Identity,
    *,
    run: accounts.Runner | None = None,
) -> MembershipResult:
    """Apply the membership predicate to a parsed members list.

    `members` is the `members:` field of the parsed `members.yaml`.
    An empty list (or absent / unparseable file represented as `[]`
    by the caller) means open mode.

    In closed mode the acting account passes only where the backbone's
    function answers that it is one account with an entry's `github_login`
    (ADR-094 point 3), case and surrounding whitespace set aside. Where the
    commands know no acting account, nothing passes (DEC-076 point 2). Git's
    email and `PM_INVOKER_LOGIN` pass nothing.

    Returns a `MembershipResult`. When `allowed=False`, the
    `refusal_message` field carries the standard structured refusal.
    """
    if not members:
        return MembershipResult(allowed=True, mode="open", invoker=invoker)
    logins = [
        entry["github_login"]
        for entry in members
        if isinstance(entry, dict) and isinstance(entry.get("github_login"), str)
    ]
    found = None
    if invoker.github_login is not None:
        found = accounts.fold(
            accounts.entry(invoker.github_login), [accounts.entry(x) for x in logins], run=run
        )
        if found.answer == accounts.ONE:
            return MembershipResult(allowed=True, mode="closed", invoker=invoker)
    return MembershipResult(
        allowed=False,
        mode="closed",
        invoker=invoker,
        refusal_message=format_refusal(invoker, members, found),
    )


def format_refusal(
    invoker: Identity, members: Sequence[object] = (), found: accounts.Fold | None = None
) -> str:
    """Standard refusal message per DEC-021's structured refusal. Where the
    commands know no acting account, it says so, and why. It names each entry
    or value that explains the refusal (ADR-094 point 3), and what did not
    count beside the acting account: a `PM_INVOKER_LOGIN` set, and git's email."""
    lines = []
    if invoker.github_login is None:
        lines.append(
            f"{format_unresolved(invoker.unresolved_cause)}, and a closed gate passes no "
            "account it cannot name (DEC-076 point 2)."
        )
    lines.extend(_explained(invoker, found))
    lines.extend(_not_counted(invoker, members))
    said = "".join(f"          → {line}\n" for line in lines)
    return (
        "[refused] Membership required for this operation\n"
        f"          → This repository is in closed mode "
        f"(.pkit/capabilities/{CAPABILITY_NAME}/{MEMBERS_RELATIVE} "
        "has ≥1 entry).\n"
        f"          → Your identity ({invoker.label()}) is not in the "
        "member list.\n"
        f"{said}"
        "          → Remediation: ask an existing member to add you via "
        f"`pkit {CAPABILITY_NAME} add-member`, under their own credential."
    )


def _explained(invoker: Identity, found: accounts.Fold | None) -> list[str]:
    """The entries that explain why the acting account matched none (ADR-094
    point 3, "The refusal names it instead"): one with no spelling, with why,
    and a bare one whose login agrees with the bot's account acting, with the
    spelling that would name it. Where the backbone could not be asked, why."""
    if found is None:
        return []
    if found.cause:
        return [f"whether the acting account is a member cannot be told: {found.cause}."]
    lines = []
    acting = found.account
    for _answer, entry in found.among:
        if entry.account is None:
            why = entry.reason or "it names no account"
            lines.append(f"the entry {entry.login!r} names no account the gate can match: {why}.")
        elif (
            acting is not None
            and acting.kind == KIND_BOT
            and entry.kind == KIND_USER
            and acting.account is not None
            and entry.account.lower() == acting.account.removesuffix("[bot]").lower()
        ):
            lines.append(
                f"the entry {entry.login!r} names a user's account; the bot's account acting "
                f"is spelled {acting.account} (ADR-094 point 3)."
            )
    return lines


def _not_counted(invoker: Identity, members: Sequence[object]) -> list[str]:
    """What the gate does not count beside the acting account (DEC-076 point
    2): one line for each of `PM_INVOKER_LOGIN` set, and git's email where an
    entry carries it."""
    entries = [entry for entry in members if isinstance(entry, dict)]
    lines = []
    variable = (os.environ.get(INVOKER_VARIABLE) or "").strip()
    if variable:
        lines.append(
            f"{INVOKER_VARIABLE} ({variable}) names the person the agent works for, and "
            "passes no gate (DEC-076 point 2)."
        )
    if invoker.email and any(entry.get("email") == invoker.email for entry in entries):
        lines.append(
            f"git's email ({invoker.email}) matches an entry, and passes no gate: an entry "
            "matches by its login alone."
        )
    return lines


def member_list_refusal(invoker: Identity, verb: str) -> str | None:
    """Why ``verb`` changes no member list under this credential, or None where
    it may (DEC-076 point 2). Membership grants authority, so the list changes
    only under a credential that names a user's account, a person standing
    behind each change, in open mode too, where a bot's first entry would close
    the gate with no person in it."""
    if invoker.names_user:
        return None
    return (
        f"[refused] {verb}: {invoker.acts_as()}, and the member list changes only under a "
        "credential that names a user's account, since membership grants authority and a person "
        "stands behind each change to it (DEC-076 point 2). Change the list under your "
        f"own credential. {INVOKER_VARIABLE} names no member here. Nothing was written."
    )


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


# ---- the variable beside a user's account ---------------------------

#: Whether the warning on an ignored `PM_INVOKER_LOGIN` was given.
_warned = False


def forget_service_answers() -> None:
    """Forget the warning given, as a new process holds none. For a test that
    loads this module once and runs many cases. The reading's own answers are
    `_lib.accounts`'s."""
    global _warned
    _warned = False
    accounts.forget_service_answers()


def _warn_if_ignored(variable: str | None, answered: str) -> None:
    """Say once per process, on stderr, that `PM_INVOKER_LOGIN` is set beside
    the user's account GitHub answered, and is no identity (DEC-076 point 3)."""
    global _warned
    if _warned or not variable or variable == answered:
        return
    _warned = True
    print(
        f"[warn] {INVOKER_VARIABLE} names {variable}, but GitHub answers that the "
        f"credential acts as the user's account {answered}. pkit takes {answered} "
        "as the account acting, and reads the variable for nothing (DEC-076 point 3).",
        file=sys.stderr,
    )


# ---- subprocess helpers (testing seams) ----------------------------


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
