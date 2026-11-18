"""An assignee is never a bot's account (DEC-079 point 1).

Assignment names a person, someone responsible for the work
([project-management:DEC-019-mandatory-issue-state]), and a bot answers for
nothing it does. So no command makes a bot's account an assignee, at filing,
on an assignment or by handing a Task to it, whether or not a member's entry
names it ([project-management:DEC-079-bots-are-no-person] point 1). Every
command that makes an account an assignee confirms it here first:

- **By its form** (``_lib.account_kind``): ``<name>[bot]`` and ``app/<name>``
  name a bot's account, and a string with no spelling, such as ``@someone``,
  names none. Each is refused without a request.
- **A bare login, on the service's word.** A bare login names a user's
  account by its form, but the service lets some bots be assigned by a login
  with no suffix, such as its own coding agent. So a bare login is made an
  assignee only where the service answers that it names a user's account.
  Where it is the account the credential acts as, which the service answered
  as a user's, that answer stands. Otherwise it is looked up, as ``add-member``
  looks up an entry's login (``membership.look_up_account``), once for each
  assignee a command names.
- **Every lookup that confirms nothing refuses,** with the login and its cause:
  an account of another kind, no account with the login, or no answer. On a
  host other than the public one, a login mistyped and an account the host
  hides from the credential read alike, so the refusal says that a second run
  changes neither.

None of these refusals is a ``hard-reject`` finding of DEC-014's, so the
``--force`` DEC-046 gives such a finding does not reach them.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from _lib import account_kind
from _lib.gh import gh_env
from _lib.membership import FROM_SERVICE, Identity, LookedUp, look_up_account

#: The service's public host. A host other than it may hide an account from
#: the credential, and answer that it found none.
PUBLIC_HOST = "github.com"

LookUp = Callable[[str, "dict[str, Any] | None"], LookedUp]


def refusal(
    login: str,
    invoker: Identity | None,
    config: dict[str, Any] | None,
    *,
    look_up: LookUp | None = None,
) -> str | None:
    """Why ``login`` may not be made an assignee, or None where it may."""
    value = login.strip()
    kind = account_kind.of_form(value)
    if kind == account_kind.BOT:
        return (
            f"`{value}` names a bot's account, and an assignee names a person: no "
            "command makes a bot's account an assignee (DEC-079 point 1)."
        )
    if kind != account_kind.USER:
        return (
            f"`{value}` names no account: a login holds only letters, digits and "
            "dashes, with no `@` (DEC-079 point 1)."
        )
    if getattr(invoker, "login_source", None) == FROM_SERVICE:
        if value == getattr(invoker, "github_login", None):
            return None
    looked = (look_up or look_up_account)(value, config)
    if looked.cause:
        return (
            f"could not confirm that `{value}` names a user's account: {looked.cause}. "
            "An assignee is made only where GitHub answers that it names a user's "
            "account (DEC-079 point 1). Run the command again once GitHub answers."
        )
    if looked.missing:
        host = _host(config)
        if host == PUBLIC_HOST:
            return f"no account on GitHub has the login `{value}`: check the login."
        return (
            f"{host} knows no account `{value}` that this credential can see. A login "
            "mistyped and an account the host hides from the credential read alike, so "
            "running the command again changes neither: check the login, or run the "
            "command under a credential that sees the account."
        )
    if looked.account_type != account_kind.USER_TYPE:
        return (
            f"`{value}` names an account of type {looked.account_type}, not a user's, and "
            "an assignee names a person (DEC-079 point 1)."
        )
    return None


def first_refusal(
    logins: Iterable[str],
    invoker: Identity | None,
    config: dict[str, Any] | None,
    *,
    look_up: LookUp | None = None,
) -> str | None:
    """The refusal of the first of ``logins`` that may not be an assignee, or
    None where each may. Each is confirmed once, in order."""
    for login in dict.fromkeys(logins):
        refused = refusal(login, invoker, config, look_up=look_up)
        if refused:
            return refused
    return None


def _host(config: dict[str, Any] | None) -> str:
    """The host the commands' requests go to (DEC-023)."""
    return gh_env(config or {}).get("GH_HOST") or PUBLIC_HOST
