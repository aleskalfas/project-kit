"""The kind of one account, from a surface that gives it (DEC-079; ADR-094 point 3).

A guard that reads one account's kind alone reads it here: the `[bot]` suffix
first, then the type GitHub's REST interface records, and a kind unknown in
every other case.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / ".pkit/capabilities/project-management/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import account_kind  # noqa: E402


@pytest.mark.parametrize(
    ("login", "service_type", "kind"),
    [
        ("alice", "User", account_kind.USER),
        ("robot[bot]", "Bot", account_kind.BOT),
        ("robot[bot]", "User", account_kind.BOT),
        ("robot[bot]", None, account_kind.BOT),
        ("Copilot", "Bot", None),
        ("acme", "Organization", None),
        ("ghost-import", "Mannequin", None),
        ("alice", None, None),
        ("alice", "Robot", None),
        (None, "User", None),
        ("", "User", None),
    ],
)
def test_a_records_kind_reads_the_suffix_first_then_the_type(login, service_type, kind) -> None:
    assert account_kind.of_record(login, service_type) == kind


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        ("alice", account_kind.USER),
        ("  alice  ", account_kind.USER),
        ("a-b-c", account_kind.USER),
        ("jdoe_acme", account_kind.USER),
        ("robot[bot]", account_kind.BOT),
        ("Robot[BOT]", account_kind.BOT),
        ("app/robot", account_kind.BOT),
        ("@alice", None),
        ("alice smith", None),
        ("-alice", None),
        ("app/", None),
        ("[bot]", None),
        ("", None),
        (None, None),
    ],
)
def test_a_values_form_names_its_kind(value, kind) -> None:
    assert account_kind.of_form(value) == kind
