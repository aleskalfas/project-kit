"""The kind of one account, read from a surface that gives it (DEC-079; ADR-094 point 3).

The backbone's one spelling of accounts, and its comparison of two, come with
its reading of the acting account ([pkit:ADR-094] points 1 and 3). A guard
that reads one account's kind alone, such as whether an approver or a claim's
author is a bot's, compares no two accounts, and ADR-094's order of changes
lets it be built before that function, in the change that moves its read to a
surface that gives the kind. It reads the kind from the sources ADR-094 point
3 names, the suffix first. This module is that test, in one place, so every
guard of [project-management:DEC-079-bots-are-no-person] reads a kind alike.

Two kinds are known, as ADR-094 point 3 knows them:

- **a bot's account,** wherever the login carries the service's ``[bot]``
  suffix, whatever type the surface gives, since no user's login can hold the
  brackets; and, by the form of a value that stands for an account, gh's
  ``app/<name>``;
- **a user's account,** where the surface gives the type GitHub's REST
  interface records for one, ``User``, on a login with no suffix; and, by the
  form of a value that stands for an account, a bare login.

Every other account is of a kind unknown, given here as None: a type other
than a user's on a login with no suffix, such as ``Bot``, ``Organization`` or
``Mannequin``; a login with no type; and a value of no form an account takes.
"""

from __future__ import annotations

import re

#: The kind of a user's account.
USER = "user"

#: The kind of a bot's account.
BOT = "bot"

#: The suffix GitHub's REST interface gives an app's account's login.
BOT_SUFFIX = "[bot]"

#: How gh writes an account the service does not record as a user's.
APP_PREFIX = "app/"

#: The type GitHub's REST interface records for a user's account.
USER_TYPE = "User"

# A user's login holds only letters, digits and dashes, and a managed user's
# adds an underscore and the enterprise's short code (ADR-094, Context). An
# app's name takes the same characters.
_NAME = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:_[A-Za-z0-9]+)?"
_BARE_RE = re.compile(_NAME)
_BOT_RE = re.compile(rf"{_NAME}\[bot\]", re.IGNORECASE)
_APP_RE = re.compile(rf"app/{_NAME}")


def of_record(login: object, service_type: object) -> str | None:
    """The kind of the account a record of the service names by ``login``,
    with the type ``service_type`` the record gives it, or None where it is a
    kind unknown."""
    if not isinstance(login, str) or not login.strip():
        return None
    if login.strip().lower().endswith(BOT_SUFFIX):
        return BOT
    if service_type == USER_TYPE:
        return USER
    return None


def of_form(value: object) -> str | None:
    """The kind a value that stands for an account names by its form: a bare
    login a user's, ``<name>[bot]`` and ``app/<name>`` a bot's, and None for
    a string with no spelling, such as ``@someone`` or one with a space in
    it. Surrounding whitespace is set aside."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if _BOT_RE.fullmatch(text) or _APP_RE.fullmatch(text):
        return BOT
    if _BARE_RE.fullmatch(text):
        return USER
    return None
