"""Claim and release of instance ownership — `_lib/instance_claims` (DEC-035).

The lifecycle side of DEC-035 points 3, 4 and 6, over the ADR-041 seam: who a
claim and a release write for, on which substrate, the same-instant back-off,
and the owner mirror in comment mode. Every `gh` call reaches an in-memory
GitHub (`tests/pm_ownership_support.FakeGitHub`), never GitHub itself.
"""

from __future__ import annotations

import importlib
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.pm_ownership_support import FakeGitHub

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
T0 = datetime(2026, 7, 7, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def ic():
    sys.path.insert(0, str(SCRIPTS))
    try:
        yield importlib.import_module("_lib.instance_claims")
    finally:
        sys.path.remove(str(SCRIPTS))


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A capability root of its own, deep enough for the provenance footer's
    version reading."""
    path = tmp_path / ".pkit" / "capabilities" / "project-management"
    path.mkdir(parents=True)
    return path


def _clone(ic, root: Path, instance: int = 2, substrate: str = "comment", login="me"):
    return ic.Clone(instance, substrate, login, root)


def _stamp(ic, event: str, instance: int, to: int | None = None) -> str:
    return ic.ownership.format_event_comment(event=event, instance=instance, ts=T0, to=to)


def _owners(ic, gh: FakeGitHub, n: int, account: str = "me", selector: str = "comment"):
    issue = gh.issues[n]
    return ic.ownership.resolve_owner(
        comments=issue.comments,
        labels=issue.labels,
        assignee_login=account,
        selector=selector,
    ).owners


def _events(gh: FakeGitHub, n: int) -> list[str]:
    """The ownership events posted on the issue, as `event=… instance=…`."""
    out = []
    for comment in gh.issues[n].comments:
        body = comment["body"]
        if "event=" in body:
            event = body.split("event=")[1].split()[0]
            instance = body.split("instance=")[1].split()[0]
            out.append(f"{event} {instance}")
    return out


# ---- activation ------------------------------------------------------------


def test_no_instance_id_means_no_clone(ic, root: Path) -> None:
    """The id is the sole activation gate: unset, there is no clone to act for."""
    assert ic.this_clone(root, "me") is None


def test_an_instance_id_activates_with_the_comment_default(ic, root: Path) -> None:
    importlib.import_module("_lib.instance_identity").write_instance_id(root, 2)
    clone = ic.this_clone(root, "me")
    assert clone == ic.Clone(2, "comment", "me", root)


def test_a_clone_id_outside_the_tests_own_folders_reads_as_unset(ic) -> None:
    """The suite runs as a clone with no id, whatever this checkout set
    (`tests/conftest.py`, `outside_any_clone`): a script run against this
    repository's capability must not claim on GitHub."""
    with tempfile.TemporaryDirectory() as outside:
        capability = Path(outside) / ".pkit" / "capabilities" / "project-management"
        identity = importlib.import_module("_lib.instance_identity")
        identity.write_instance_id(capability, 2)
        assert identity.identity_path(capability).exists()
        assert ic.this_clone(capability, "me") is None


def test_the_settings_file_selects_the_label_substrate(ic, root: Path) -> None:
    importlib.import_module("_lib.instance_identity").write_instance_id(root, 3)
    (root / "project" / "instance-ownership.yaml").write_text("substrate: label\n")
    assert ic.this_clone(root, "me").substrate == "label"


def test_an_unreadable_settings_file_falls_back_to_comment(ic, root: Path) -> None:
    importlib.import_module("_lib.instance_identity").write_instance_id(root, 3)
    (root / "project" / "instance-ownership.yaml").write_text("substrate: [unclosed\n")
    assert ic.this_clone(root, "me").substrate == "comment"


# ---- claim, comment substrate ------------------------------------------------


def test_claim_posts_an_event_and_mirrors_the_owner(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    result = ic.claim(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.CLAIMED
    assert result.winner == 2
    assert _events(gh, 7) == ["claim 2"]
    assert _owners(ic, gh, 7) == frozenset({2})
    body = gh.issues[7].body
    assert ic.ownership.MIRROR_BEGIN in body
    assert "**Owner:** instance 2" in body
    assert [argv[2] for argv in gh.writes()] == ["comment", "edit"]


def test_the_mirror_sits_above_the_provenance_footer(ic, root: Path) -> None:
    """A footer stamp strips everything from its first line on, so the mirror is
    kept above it, where re-stamping the body leaves it (ADR-037)."""
    gh = FakeGitHub()
    versions = ic.provenance.read_versions(root)
    gh.add(7, body=ic.provenance.stamp("## What\n\nx\n", versions))
    ic.claim(7, _clone(ic, root), {}, run=gh)
    body = gh.issues[7].body
    assert body.count(ic.provenance.MARKER_START) == 1
    assert body.index(ic.ownership.MIRROR_BEGIN) < body.index(ic.provenance.MARKER_START)
    assert ic.ownership.MIRROR_BEGIN in ic.provenance.strip_footer(body)


def test_a_second_claim_is_held_and_writes_nothing(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    ic.claim(7, _clone(ic, root), {}, run=gh)
    before = len(gh.writes())
    result = ic.claim(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.HELD
    assert len(gh.writes()) == before


def test_an_issue_another_instance_owns_is_not_claimed(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _stamp(ic, "claim", 3))
    result = ic.claim(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.ELSEWHERE
    assert result.winner == 3
    assert gh.writes() == []


def test_an_issue_assigned_to_another_account_is_not_claimed(ic, root: Path) -> None:
    """The owner is the assignee paired with an instance (DEC-035 point 5)."""
    gh = FakeGitHub()
    gh.add(7, assignees=("someone-else",))
    result = ic.claim(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.NOT_CLAIMED
    assert "@someone-else" in result.line
    assert gh.writes() == []


def test_a_clone_with_no_account_claims_nothing(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    result = ic.claim(7, _clone(ic, root, login=None), {}, run=gh)
    assert result.outcome == ic.NOT_CLAIMED
    assert gh.calls == []


def test_a_failed_claim_writes_no_mirror(ic, root: Path) -> None:
    gh = FakeGitHub(failing={"comment"})
    gh.add(7)
    result = ic.claim(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.FAILED
    assert result.warning
    assert "HTTP 502" in result.line
    assert ic.ownership.MIRROR_BEGIN not in gh.issues[7].body


def test_a_mirror_that_cannot_be_written_is_a_note_not_a_failure(ic, root: Path) -> None:
    gh = FakeGitHub(failing={"body"})
    gh.add(7)
    result = ic.claim(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.CLAIMED
    assert any("could not be updated" in note for note in result.notes)


def test_a_comment_claim_removes_a_residual_label(ic, root: Path) -> None:
    """Beside a comment marker, an `instance:N` label from a label-mode past is
    residual, and the next ownership write removes it (ADR-041 point 2)."""
    gh = FakeGitHub()
    gh.add(7, labels=("instance:5", "type:feature"))
    gh.post(7, _stamp(ic, "claim", 2))
    result = ic.claim(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.HELD
    assert gh.issues[7].labels == ["type:feature"]


def test_a_label_with_no_comment_marker_still_owns_the_issue(ic, root: Path) -> None:
    """With no comment marker, the label is the owner in comment mode too (the
    seam's fallback), so it is no commons issue to claim."""
    gh = FakeGitHub()
    gh.add(7, labels=("instance:5",))
    result = ic.claim(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.ELSEWHERE
    assert result.winner == 5
    assert gh.writes() == []


# ---- the same-instant clash (DEC-035 point 6) --------------------------------


def _rival_claims_before_the_reread(ic, gh: FakeGitHub, rival: int) -> None:
    """Another clone of the same account claims between this clone's write and its
    re-read: both markers are there when this clone reads again."""

    def on_view(number: int, seen: int) -> None:
        if seen == 1:
            gh.post(number, _stamp(ic, "claim", rival))

    gh.on_view = on_view


def test_the_higher_instance_backs_off(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    _rival_claims_before_the_reread(ic, gh, rival=1)
    result = ic.claim(7, _clone(ic, root, instance=2), {}, run=gh)
    assert result.outcome == ic.LOST
    assert result.winner == 1
    assert result.warning
    assert _events(gh, 7) == ["claim 2", "claim 1", "abandon 2"]
    assert _owners(ic, gh, 7) == frozenset({1})
    assert "**Owner:** instance 1 " in gh.issues[7].body


def test_the_lower_instance_keeps_its_claim(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    _rival_claims_before_the_reread(ic, gh, rival=3)
    result = ic.claim(7, _clone(ic, root, instance=2), {}, run=gh)
    assert result.outcome == ic.CLAIMED
    assert "same instant" in result.line
    assert _events(gh, 7) == ["claim 2", "claim 3"]
    assert "instance 2 wins" in gh.issues[7].body


# ---- claim, label substrate --------------------------------------------------


def test_a_label_claim_adds_the_label_and_writes_no_comment(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    result = ic.claim(7, _clone(ic, root, substrate="label"), {}, run=gh)
    assert result.outcome == ic.CLAIMED
    assert "instance:2" in gh.issues[7].labels
    assert _events(gh, 7) == []
    assert ic.ownership.MIRROR_BEGIN not in gh.issues[7].body


def test_a_missing_label_is_created_on_first_use(ic, root: Path) -> None:
    """DEC-035 point 2: the label is created lazily, then added."""
    gh = FakeGitHub(labels_must_exist=True)
    gh.add(7)
    result = ic.claim(7, _clone(ic, root, substrate="label"), {}, run=gh)
    assert result.outcome == ic.CLAIMED
    assert "instance:2" in gh.repo_labels
    assert "instance:2" in gh.issues[7].labels


def test_a_label_that_cannot_be_created_fails_the_claim(ic, root: Path) -> None:
    gh = FakeGitHub(labels_must_exist=True, failing={"label-create"})
    gh.add(7)
    result = ic.claim(7, _clone(ic, root, substrate="label"), {}, run=gh)
    assert result.outcome == ic.FAILED
    assert "not found" in result.line and "admin rights" in result.line


def test_a_label_claim_backs_off_by_removing_its_label(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)

    def on_view(number: int, seen: int) -> None:
        if seen == 1:
            gh.issues[number].labels.append("instance:1")

    gh.on_view = on_view
    result = ic.claim(7, _clone(ic, root, instance=2, substrate="label"), {}, run=gh)
    assert result.outcome == ic.LOST
    assert gh.issues[7].labels == ["instance:1"]


# ---- release (DEC-035 point 4) ------------------------------------------------


def test_release_posts_an_event_and_mirrors_no_owner(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    ic.claim(7, _clone(ic, root), {}, run=gh)
    result = ic.release(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.RELEASED
    assert _events(gh, 7) == ["claim 2", "release 2"]
    assert _owners(ic, gh, 7) == frozenset()
    assert "_Unclaimed_" in gh.issues[7].body
    assert gh.issues[7].body.count(ic.ownership.MIRROR_BEGIN) == 1


def test_release_clears_another_instance_of_the_same_account(ic, root: Path) -> None:
    """Whichever of the account's clones closes the issue, its owner is cleared."""
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _stamp(ic, "claim", 3))
    result = ic.release(7, _clone(ic, root, instance=2), {}, run=gh)
    assert result.outcome == ic.RELEASED
    assert _events(gh, 7) == ["claim 3", "release 3"]
    assert _owners(ic, gh, 7) == frozenset()


def test_release_removes_the_label(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7, labels=("instance:2", "type:feature"))
    result = ic.release(7, _clone(ic, root, substrate="label"), {}, run=gh)
    assert result.outcome == ic.RELEASED
    assert gh.issues[7].labels == ["type:feature"]
    assert _events(gh, 7) == []


def test_release_of_an_unowned_issue_writes_nothing(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    result = ic.release(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.NOTHING
    assert gh.writes() == []


def test_another_accounts_marker_is_left_to_its_clone(ic, root: Path) -> None:
    """A release from another account would not count (DEC-043 point 3), so none
    is posted."""
    gh = FakeGitHub()
    gh.add(7, assignees=("someone-else",))
    gh.post(7, _stamp(ic, "claim", 1), author="someone-else")
    result = ic.release(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.NOT_RELEASED
    assert "@someone-else" in result.line
    assert _events(gh, 7) == ["claim 1"]


def test_a_failed_release_is_a_warning(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _stamp(ic, "claim", 2))
    gh.failing.add("comment")
    result = ic.release(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.FAILED
    assert result.warning


# ---- the lines a caller prints -----------------------------------------------


def test_say_puts_a_warning_on_stderr(ic, capsys) -> None:
    ic.say(ic.Result(ic.LOST, "[warn] lost", notes=("[warn] note",)))
    ic.say(ic.Result(ic.CLAIMED, "[ok] claimed"))
    out, err = capsys.readouterr()
    assert out == "[ok] claimed\n"
    assert err == "[warn] lost\n[warn] note\n"


def test_plans_name_the_instance_and_the_substrate(ic, root: Path) -> None:
    clone = _clone(ic, root)
    assert ic.claim_plan(clone) == "claimed for instance 2 (comment substrate)"
    assert ic.claim_plan(clone, "someone-else").startswith("not claimed: assigned to @someone-else")
    assert "instance 2" in ic.release_plan(clone)
