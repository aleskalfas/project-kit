"""GitHub's answer to the lookup of a bare assignee, in tests (DEC-079 point 1).

Every command that makes an account an assignee confirms a bare login with
GitHub first, unless it is the account GitHub answered the credential acts as
(`_lib/assignees.py`). A test of such a command that is about something else
has every lookup answer a user's account, through :func:`answer`. A test of
the lookup gives the answers it means, login by login.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / ".pkit/capabilities/project-management/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import assignees, membership  # noqa: E402


def users_account(login: str) -> membership.LookedUp:
    """GitHub's answer for a user's account with ``login``."""
    return membership.LookedUp(login=login, account_type="User")


def answer(
    monkeypatch: pytest.MonkeyPatch,
    answers: Mapping[str, membership.LookedUp] | None = None,
) -> list[str]:
    """Answer each lookup from ``answers``, and every other login as a user's
    account. Returns the logins looked up, in order."""
    asked: list[str] = []
    given = dict(answers or {})

    def look_up(login: str, _config: Any = None) -> membership.LookedUp:
        asked.append(login)
        return given.get(login) or users_account(login)

    monkeypatch.setattr(assignees, "look_up_account", look_up)
    return asked
