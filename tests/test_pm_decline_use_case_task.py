"""A declined use-case Task, kept in this checkout until the next day (DEC-054 point 5, #889).

Over an empty use-case set, batch planning offers a Task to author the use cases;
when the user revises it out of an approved plan, `decline-use-case-task` keeps the
UTC time of the approval in a git-ignored file under the capability's
`project/instance/`. The answer counts as declined while the machine's local
calendar day is the day it was given, and has expired from local midnight on.

Pinned here, through `_lib.use_case_task` with the current time and the time zone
passed in:

- the calendar day — the same local day is declined, the next is expired, also
  across both daylight-saving changes and at a decline one second before midnight;
- the time kept is truncated to the second, so a read at the recorded moment is
  declined;
- every file that cannot be read offers the Task, and reading never raises;
- the write is whole or nothing, and clearing is safe to repeat;
- the file is git-ignored, and the clone's instance identity (DEC-035) ignores it;
- what `--show` and `--show --json` print.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS_DIR = CAPABILITY_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
from _lib import instance_identity  # noqa: E402
from _lib import use_case_task as uct  # noqa: E402

PRAGUE = ZoneInfo("Europe/Prague")
ONE_SECOND = timedelta(seconds=1)


def at(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> datetime:
    """A moment on Prague's clock."""
    return datetime(year, month, day, hour, minute, second, tzinfo=PRAGUE)


def utc(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


def _write(root: Path, content: str) -> None:
    path = uct.path_of(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# --- the calendar day --------------------------------------------------------------------------


def test_nothing_kept_is_none(tmp_path: Path) -> None:
    assert uct.read(tmp_path, at(2026, 10, 3, 9, 12), PRAGUE) == uct.Kept(uct.NONE)


def test_a_second_later_it_is_declined_until_local_midnight(tmp_path: Path) -> None:
    uct.record(tmp_path, at(2026, 10, 3, 9, 12))
    kept = uct.read(tmp_path, at(2026, 10, 3, 9, 12, 1), PRAGUE)
    assert kept == uct.Kept(uct.DECLINED, utc(2026, 10, 3, 7, 12), at(2026, 10, 4, 0, 0))


def test_the_same_local_day_is_declined_and_the_next_is_expired(tmp_path: Path) -> None:
    uct.record(tmp_path, at(2026, 10, 3, 9, 12))
    assert uct.read(tmp_path, at(2026, 10, 3, 23, 59, 59), PRAGUE).state == uct.DECLINED
    assert uct.read(tmp_path, at(2026, 10, 4, 0, 0), PRAGUE).state == uct.EXPIRED
    assert uct.read(tmp_path, at(2026, 10, 4, 9, 30), PRAGUE).state == uct.EXPIRED


def test_a_decline_one_second_before_midnight_expires_at_midnight(tmp_path: Path) -> None:
    """The late-evening case the calendar day accepts: one revision the next plan."""
    uct.record(tmp_path, at(2026, 10, 3, 23, 59, 59))
    assert uct.read(tmp_path, at(2026, 10, 3, 23, 59, 59), PRAGUE).state == uct.DECLINED
    assert uct.read(tmp_path, at(2026, 10, 4, 0, 0, 0), PRAGUE).state == uct.EXPIRED


def test_a_read_at_the_recorded_moment_is_declined(tmp_path: Path) -> None:
    """The time is truncated to the second, never rounded up into the future."""
    uct.record(tmp_path, at(2026, 10, 3, 9, 12, 30).replace(microsecond=999_999))
    assert json.loads(uct.path_of(tmp_path).read_text(encoding="utf-8")) == {
        "declined_at": "2026-10-03T07:12:30Z"
    }
    assert uct.read(tmp_path, at(2026, 10, 3, 9, 12, 30), PRAGUE).state == uct.DECLINED


def test_a_day_with_an_extra_hour_lasts_to_its_own_midnight(tmp_path: Path) -> None:
    """25 October 2026 in Prague is 25 hours long: summer time ends at 03:00."""
    uct.record(tmp_path, at(2026, 10, 25, 0, 30))  # 22:30 UTC the day before
    kept = uct.read(tmp_path, utc(2026, 10, 25, 22, 59, 59), PRAGUE)  # 23:59:59 CET
    assert kept.state == uct.DECLINED
    assert kept.offered_again_at == utc(2026, 10, 25, 23, 0)  # midnight CET
    assert uct.read(tmp_path, utc(2026, 10, 25, 23, 0), PRAGUE).state == uct.EXPIRED


def test_a_day_with_an_hour_missing_ends_at_its_own_midnight(tmp_path: Path) -> None:
    """28 March 2027 in Prague is 23 hours long: summer time starts at 02:00."""
    uct.record(tmp_path, at(2027, 3, 28, 0, 30))  # 23:30 UTC the day before
    kept = uct.read(tmp_path, utc(2027, 3, 28, 21, 59, 59), PRAGUE)  # 23:59:59 CEST
    assert kept.state == uct.DECLINED
    assert kept.offered_again_at == utc(2027, 3, 28, 22, 0)  # midnight CEST
    assert uct.read(tmp_path, utc(2027, 3, 28, 22, 0), PRAGUE).state == uct.EXPIRED


def test_the_zone_is_the_one_in_force_when_the_answer_is_read(tmp_path: Path) -> None:
    """Only the UTC time is kept; the day it belongs to is decided at each read."""
    uct.record(tmp_path, utc(2026, 10, 3, 23, 30))  # 4 October in Prague, 3rd in UTC
    assert uct.read(tmp_path, utc(2026, 10, 4, 0, 30), UTC).state == uct.EXPIRED
    assert uct.read(tmp_path, utc(2026, 10, 4, 0, 30), PRAGUE).state == uct.DECLINED


@pytest.fixture
def machine_in_prague(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The machine's own time zone set to Prague, and set back afterwards."""
    if not hasattr(time, "tzset"):
        pytest.skip("the machine's time zone is set through time.tzset, which is Unix-only")
    monkeypatch.setenv("TZ", "Europe/Prague")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


@pytest.mark.usefixtures("machine_in_prague")
def test_without_a_zone_the_machine_local_day_counts(tmp_path: Path) -> None:
    uct.record(tmp_path, at(2026, 10, 25, 0, 30))
    kept = uct.read(tmp_path, utc(2026, 10, 25, 22, 59, 59))
    assert kept.state == uct.DECLINED
    assert kept.offered_again_at == utc(2026, 10, 25, 23, 0)
    assert uct.read(tmp_path, utc(2026, 10, 25, 23, 0)).state == uct.EXPIRED
    assert uct.local_text(utc(2026, 10, 25, 23, 0)) == "2026-10-26 00:00 CET"


def test_a_time_without_a_zone_is_refused_by_the_caller_contract(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        uct.record(tmp_path, datetime(2026, 10, 3, 9, 12))


# --- a file that cannot be read offers the Task ------------------------------------------------


def test_a_time_later_than_now_is_unreadable(tmp_path: Path) -> None:
    uct.record(tmp_path, at(2026, 10, 3, 9, 12))
    kept = uct.read(tmp_path, at(2026, 10, 3, 9, 11, 59), PRAGUE)
    assert kept.state == uct.UNREADABLE
    assert kept.declined_at is None
    assert kept.why is not None and "later than now" in kept.why


@pytest.mark.parametrize(
    ("content", "why"),
    [
        ("{ not json", "not JSON"),
        ('["2026-10-03T07:12:00Z"]', "no object"),
        ("{}", "no `declined_at` time"),
        ('{"declined_at": 1791011520}', "no `declined_at` time"),
        ('{"declined_at": "2026-10-03T07:12:00"}', "not a UTC time"),
        ('{"declined_at": "2026-10-03T09:12:00+02:00"}', "not a UTC time"),
        ('{"declined_at": "yesterday"}', "not a UTC time"),
    ],
)
def test_a_file_that_cannot_be_read_is_unreadable(tmp_path: Path, content: str, why: str) -> None:
    _write(tmp_path, content)
    kept = uct.read(tmp_path, at(2026, 10, 3, 12, 0), PRAGUE)
    assert kept.state == uct.UNREADABLE
    assert kept.why is not None and why in kept.why


def test_a_folder_in_the_file_s_place_is_unreadable(tmp_path: Path) -> None:
    uct.path_of(tmp_path).mkdir(parents=True)
    assert uct.read(tmp_path, at(2026, 10, 3, 12, 0), PRAGUE).state == uct.UNREADABLE


# --- writing and clearing ----------------------------------------------------------------------


def test_a_new_answer_replaces_the_old_one(tmp_path: Path) -> None:
    uct.record(tmp_path, at(2026, 10, 2, 9, 12))
    uct.record(tmp_path, at(2026, 10, 3, 14, 0))
    kept = uct.read(tmp_path, at(2026, 10, 3, 15, 0), PRAGUE)
    assert kept.declined_at == at(2026, 10, 3, 14, 0)
    assert [p.name for p in uct.path_of(tmp_path).parent.iterdir()] == ["use-case-task.json"]


def test_a_write_cut_short_leaves_the_kept_answer_as_it_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uct.record(tmp_path, at(2026, 10, 3, 9, 12))
    before = uct.path_of(tmp_path).read_text(encoding="utf-8")

    def cut_short(source: str, target: str) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(uct.os, "replace", cut_short)
    with pytest.raises(OSError):
        uct.record(tmp_path, at(2026, 10, 3, 14, 0))
    assert uct.path_of(tmp_path).read_text(encoding="utf-8") == before
    assert [p.name for p in uct.path_of(tmp_path).parent.iterdir()] == ["use-case-task.json"]


def test_clearing_removes_the_answer_and_is_safe_to_repeat(tmp_path: Path) -> None:
    uct.record(tmp_path, at(2026, 10, 3, 9, 12))
    assert uct.clear(tmp_path) is True
    assert uct.read(tmp_path, at(2026, 10, 3, 9, 13), PRAGUE).state == uct.NONE
    assert uct.clear(tmp_path) is False


# --- where the file lives ----------------------------------------------------------------------


@pytest.mark.parametrize("name", [Path(uct.RELATIVE).name, ".use-case-task.k3x9q1ab.json"])
def test_the_file_and_its_temporary_twin_are_git_ignored(name: str) -> None:
    """Asked of git against the committed `.pkit/.gitignore`, which the capability's
    `runtime_ignore:` glob renders — so a file that left the glob's folder fails."""
    relative = (CAPABILITY_ROOT / Path(uct.RELATIVE).parent / name).relative_to(REPO_ROOT)
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", relative.as_posix()],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    assert ignored.returncode == 0, f"{relative} is not git-ignored"


def test_the_instance_identity_does_not_read_the_kept_answer(tmp_path: Path) -> None:
    """DEC-035's activation switch is `clone.json` alone; this file switches nothing on."""
    uct.record(tmp_path, at(2026, 10, 3, 9, 12))
    assert uct.path_of(tmp_path).parent == instance_identity.identity_path(tmp_path).parent
    assert instance_identity.read_instance_id(tmp_path) is None


# --- what --show prints ------------------------------------------------------------------------


def test_the_json_document_gives_utc_and_local_times(tmp_path: Path) -> None:
    uct.record(tmp_path, at(2026, 10, 3, 9, 12))
    kept = uct.read(tmp_path, at(2026, 10, 3, 10, 0), PRAGUE)
    assert uct.document(kept, PRAGUE) == {
        "state": "declined",
        "declined_at": "2026-10-03T07:12:00Z",
        "offered_again_at": "2026-10-03T22:00:00Z",
        "declined_at_local": "2026-10-03 09:12 CEST",
        "offered_again_at_local": "2026-10-04 00:00 CEST",
        "why": None,
    }


def test_the_json_document_of_no_answer_carries_no_times() -> None:
    assert uct.document(uct.Kept(uct.NONE), PRAGUE) == {
        "state": "none",
        "declined_at": None,
        "offered_again_at": None,
        "declined_at_local": None,
        "offered_again_at_local": None,
        "why": None,
    }


def test_the_line_names_the_local_times_to_quote(tmp_path: Path) -> None:
    uct.record(tmp_path, at(2026, 10, 3, 9, 12))
    declined = uct.read(tmp_path, at(2026, 10, 3, 10, 0), PRAGUE)
    assert uct.describe(declined, PRAGUE) == (
        "declined: at 09:12 today (2026-10-03 09:12 CEST); "
        "the Task is offered again from tomorrow (2026-10-04 00:00 CEST)."
    )
    expired = uct.read(tmp_path, at(2026, 10, 4, 9, 30), PRAGUE)
    assert uct.describe(expired, PRAGUE) == (
        "expired: declined at 2026-10-03 09:12 CEST; "
        "the Task is offered again since 2026-10-04 00:00 CEST."
    )
    assert uct.describe(uct.Kept(uct.NONE), PRAGUE).startswith("none: ")
    unreadable = uct.Kept(uct.UNREADABLE, why="use-case-task.json is not JSON")
    assert uct.describe(unreadable, PRAGUE) == (
        "unreadable: use-case-task.json is not JSON; the Task is offered."
    )


@pytest.mark.parametrize("arguments", [["--show", "--clear"], ["--json"], ["--clear", "--json"]])
def test_the_command_refuses_arguments_that_do_not_go_together(arguments: list[str]) -> None:
    """Refused before the capability is looked for, so nothing is read or written."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "decline-use-case-task.py"), *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 3, result.stderr
    assert result.stdout == ""
