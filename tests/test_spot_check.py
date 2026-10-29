"""The planted-bug spot-check (`scripts/spot_check.py`, #2315): what it plants, how it
reads a run, and when it says the new tests lost a check. Its runs of pytest are the
script's own, so these tests hold the parts around them."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts import spot_check as sc


def _bugs(tmp_path: Path, find: str) -> list[sc.Bug]:
    (tmp_path / "code.py").write_text("x = 1\ny = 1\n", encoding="utf-8")
    text = json.dumps([{"id": "b", "file": "code.py", "find": find, "replace": "x = 2"}])
    return sc.read_bugs(text, root=tmp_path)


def test_a_bug_is_planted_where_its_text_appears_once(tmp_path: Path) -> None:
    (bug,) = _bugs(tmp_path, "x = 1")
    assert bug == sc.Bug("b", "code.py", "x = 1", "x = 2")
    for find, said in (("= 1", r"appears 2 time\(s\)"), ("z = 1", r"appears 0 time\(s\)")):
        with pytest.raises(sc.Refused, match=said):
            _bugs(tmp_path, find)
    with pytest.raises(sc.Refused, match="lists no bug"):
        sc.read_bugs("[]", root=tmp_path)


def test_the_planted_file_is_put_back_whatever_happens(tmp_path: Path) -> None:
    (bug,) = _bugs(tmp_path, "x = 1")
    path = tmp_path / "code.py"
    with pytest.raises(RuntimeError), sc.planted(bug, root=tmp_path):
        assert path.read_text(encoding="utf-8") == "x = 2\ny = 1\n"
        raise RuntimeError("the run broke")
    assert path.read_text(encoding="utf-8") == "x = 1\ny = 1\n"


def test_an_old_test_is_read_beside_the_new_one() -> None:
    assert sc.old_name("tests/test_a.py") == "tests/_spot_old_test_a.py"
    assert sc.old_name("tests/test_a.py::test_b") == "tests/_spot_old_test_a.py::test_b"


def test_a_test_catches_a_bug_by_failing_never_by_an_error_around_it() -> None:
    """The guard's error at a test's tearing-down is no catch: the old tests start
    processes the guard counts."""
    junit = (
        "<testsuites><testsuite>"
        '<testcase classname="tests.test_a" name="test_fails"><failure message="no"/></testcase>'
        '<testcase classname="tests.test_a" name="test_errs"><error message="teardown"/></testcase>'
        '<testcase classname="tests.test_a" name="test_passes"/>'
        "</testsuite></testsuites>"
    )
    assert sc.failures(junit) == {"tests.test_a::test_fails"}


def test_a_bug_is_lost_only_where_the_old_tests_caught_it_and_the_new_ones_did_not() -> None:
    assert sc.Verdict("b", old=2, new=0).lost
    assert not sc.Verdict("b", old=2, new=1).lost
    assert not sc.Verdict("b", old=0, new=0).lost
