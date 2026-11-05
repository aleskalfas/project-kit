"""Tests for `_lib/answers_told.py`, the one feed of what the person who authorises
the merge is told (project-management DEC-065 points 2 and 4).

`land-work` and `show-pr --field answers` print the same lines. They can differ
only if one of them feeds `friction_answers.told` for itself, so the last test here
holds that neither does. What each makes of a failure is tested with the command
(`tests/test_pm_land_work.py`, `tests/test_pm_show_pr.py`).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
from _lib import answers_told, fixers, friction_answers  # noqa: E402

HEAD = "a" * 40
LEFT_AT = "b" * 40
ROOT = Path("/capability")
SETTING = friction_answers.Setting(friction_answers.PLACES, ("docs",), ())
GRANT = fixers.GrantChange("fixer", "page", True, fixers.GRANTED)
BODY = "## What changed in each updated document\n\n- `docs/a.md`: Now says X.\n"
SAID = {"docs/a.md": "Now says X."}
DOCUMENT: dict[str, Any] = {
    "base": {"commit": LEFT_AT},
    "answers": [{"location": "docs/a.md", "answer": "updated"}],
}


class _Reads:
    """Stands in for each read `at_head` makes, and keeps their order."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *, derived=None, grants=()) -> None:
        self.order: list[str] = []
        self.derive_asked: list[tuple] = []
        self.grants_asked: list[tuple] = []
        self.derived = derived or friction_answers.Derivation(
            HEAD,
            document=DOCUMENT,
            answers=tuple(DOCUMENT["answers"]),
            settings=(SETTING,),
        )
        self.grants = grants
        monkeypatch.setattr(friction_answers, "derive", self._derive)
        monkeypatch.setattr(fixers, "change_between", self._change_between)

    def _derive(self, head: str, base: str, *, source=None) -> friction_answers.Derivation:
        self.order.append("answers")
        self.derive_asked.append((head, base, source))
        return self.derived

    def _change_between(self, merge_base: str, oid: str, capability_root: Path):
        self.order.append("grants")
        self.grants_asked.append((merge_base, oid, capability_root))
        return self.grants

    def read_body(self) -> str:
        self.order.append("description")
        return BODY


def test_what_is_told_is_fed_from_all_three_reads(monkeypatch) -> None:
    reads = _Reads(monkeypatch, grants=(GRANT,))
    fed = answers_told.at_head(HEAD, "main", ROOT, reads.read_body)
    assert fed.told == tuple(friction_answers.told(DOCUMENT, (SETTING,), SAID, [GRANT.said()]))
    assert fed.derived is reads.derived
    assert fed.grants == (GRANT,)
    assert fed.body == BODY
    assert fed.sentences == SAID


def test_the_answers_are_derived_at_the_head_against_the_base(monkeypatch) -> None:
    reads = _Reads(monkeypatch)
    source = friction_answers.Source("origin", "refs/heads/feat/42-thing")
    answers_told.at_head(HEAD, "integration", ROOT, reads.read_body, source=source)
    assert reads.derive_asked == [(HEAD, "integration", source)]


def test_the_grant_list_is_read_from_where_the_head_left_its_base(monkeypatch) -> None:
    reads = _Reads(monkeypatch)
    answers_told.at_head(HEAD, "main", ROOT, reads.read_body)
    assert reads.grants_asked == [(LEFT_AT, HEAD, ROOT)]


def test_the_description_is_read_last(monkeypatch) -> None:
    reads = _Reads(monkeypatch)
    answers_told.at_head(HEAD, "main", ROOT, reads.read_body)
    assert reads.order == ["answers", "grants", "description"]


def test_answers_that_cannot_be_derived_read_nothing_more(monkeypatch) -> None:
    derived = friction_answers.Derivation(HEAD, problem="the base could not be fetched")
    reads = _Reads(monkeypatch, derived=derived)
    fed = answers_told.at_head(HEAD, "main", ROOT, reads.read_body)
    assert reads.order == ["answers"]
    assert fed.derived is derived and fed.told == ()


def test_a_grant_list_that_cannot_be_read_tells_nothing(monkeypatch) -> None:
    unread = fixers.ChangeUnread("no such commit")
    reads = _Reads(monkeypatch, grants=unread)
    fed = answers_told.at_head(HEAD, "main", ROOT, reads.read_body)
    assert reads.order == ["answers", "grants"]
    assert fed.grants == unread and fed.told == ()


def test_only_the_one_feed_calls_told() -> None:
    """The two commands cannot differ by structure while neither derives the answers
    or calls `told` for what it prints."""
    readers = ("land-work.py", "show-pr.py")
    for name in readers:
        source = (SCRIPTS_DIR / name).read_text(encoding="utf-8")
        assert "answers_told.at_head(" in source
        assert "friction_answers.told(" not in source
        assert "friction_answers.derive(" not in source
    feeds = [
        path.name
        for path in sorted(SCRIPTS_DIR.rglob("*.py"))
        if "friction_answers.told(" in path.read_text(encoding="utf-8")
    ]
    assert feeds == ["answers_told.py"]
