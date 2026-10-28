"""Claim and release of instance ownership, and the clash guard —
`_lib/instance_claims` (DEC-035, DEC-059).

The lifecycle side of DEC-035 points 3, 4 and 6, over the ADR-041 seam: who a
claim and a release write for, on which substrate, the same-instant back-off,
the owner mirror in comment mode, and the guard that refuses an ordinary
command on another instance's issue. In a project with a topology of seats
(DEC-059 points 5, 7 and 9), a claim names its seat and counts only while its
clone holds that seat. Every `gh` call reaches an in-memory GitHub
(`tests/pm_ownership_support.FakeGitHub`), never GitHub itself.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.pm_ownership_support import (
    FakeGitHub,
    seat_issue,
    seat_snapshot,
    snapshot_with,
    topology_with,
)
from tests.pm_state_issue_fakes import FakeRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"


@pytest.fixture(scope="module")
def ic():
    sys.path.insert(0, str(SCRIPTS))
    try:
        yield importlib.import_module("_lib.instance_claims")
    finally:
        sys.path.remove(str(SCRIPTS))


@pytest.fixture
def no_topology(ic, monkeypatch) -> None:
    """The default branch declares no topology, as one run's snapshot reads it."""
    monkeypatch.setattr(ic, "_snapshot", lambda _root, _config, _login: None)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A capability root of its own, deep enough for the provenance footer's
    version reading."""
    path = tmp_path / ".pkit" / "capabilities" / "project-management"
    path.mkdir(parents=True)
    return path


def _clone(ic, root: Path, instance: int = 2, substrate: str = "comment", login: str | None = "me"):
    return ic.Clone(instance, substrate, login, root)


def _stamp(ic, event: str, instance: int, to: int | None = None) -> str:
    return ic.ownership.format_event_comment(event=event, instance=instance, to=to)


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


def test_an_instance_id_activates_with_the_comment_default(ic, root: Path, no_topology) -> None:
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


def test_the_settings_file_selects_the_label_substrate(ic, root: Path, no_topology) -> None:
    importlib.import_module("_lib.instance_identity").write_instance_id(root, 3)
    (root / "project" / "instance-ownership.yaml").write_text("substrate: label\n")
    assert ic.this_clone(root, "me").substrate == "label"


def test_an_unreadable_settings_file_falls_back_to_comment(ic, root: Path, no_topology) -> None:
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
    """The owner is the assignee paired with an instance (DEC-035 point 2)."""
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


def test_an_issue_owned_by_this_clones_label_alone_moves_to_the_comment_log(ic, root: Path) -> None:
    """In comment mode, an issue this clone owns by its label alone, as a
    label-mode past leaves it, is claimed on the comment log before the label is
    removed, so the issue keeps an owner (ADR-041 point 2)."""
    gh = FakeGitHub()
    gh.add(7, labels=("instance:2", "type:feature"))
    result = ic.claim(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.HELD
    assert _events(gh, 7) == ["claim 2"]
    assert gh.issues[7].labels == ["type:feature"]
    assert _owners(ic, gh, 7) == frozenset({2})
    assert "**Owner:** instance 2" in gh.issues[7].body


def test_a_label_owner_whose_comment_claim_fails_keeps_its_label(ic, root: Path) -> None:
    gh = FakeGitHub(failing={"comment"})
    gh.add(7, labels=("instance:2",))
    result = ic.claim(7, _clone(ic, root), {}, run=gh)
    assert result.outcome == ic.FAILED
    assert gh.issues[7].labels == ["instance:2"]
    assert _owners(ic, gh, 7) == frozenset({2})


def test_a_label_that_lost_a_label_clash_is_withdrawn_alone(ic, root: Path) -> None:
    """Two labels a label-mode clash left: in comment mode the higher instance
    removes its own label and leaves the lower one's, its only marker."""
    gh = FakeGitHub()
    gh.add(7, labels=("instance:1", "instance:2"))
    result = ic.claim(7, _clone(ic, root, instance=2), {}, run=gh)
    assert result.outcome == ic.LOST
    assert gh.issues[7].labels == ["instance:1"]
    assert _events(gh, 7) == []
    assert _owners(ic, gh, 7) == frozenset({1})


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
    assert "#7 closed, but its owner could not all be released" in result.line


def test_a_failed_release_says_what_happened_to_the_issue(ic, root: Path) -> None:
    """The move back releases through the same path a close does (DEC-006), and
    its warning says the issue moved back, not that it closed."""
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _stamp(ic, "claim", 2))
    gh.failing.add("comment")
    result = ic.release(7, _clone(ic, root), {}, run=gh, happened="moved back to backlog")
    assert result.outcome == ic.FAILED
    assert "#7 moved back to backlog, but its owner could not all be released" in result.line


# ---- an owner this clone cannot release (DEC-006, DEC-035 point 4) ---------------
#
# A command that must leave an issue with no owner, the move back from In
# Progress, asks before it writes. It writes nothing itself.


def _cannot(ic, gh: FakeGitHub, clone, root: Path):
    return ic.cannot_release(7, clone, {}, capability_root=root, login="me", run=gh)


def test_a_clone_can_release_every_owner_its_own_account_made(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7, labels=("instance:4",))
    gh.post(7, _stamp(ic, "claim", 3))
    assert _cannot(ic, gh, _clone(ic, root), root) is None
    assert gh.writes() == []


def test_a_claim_another_account_made_is_beyond_this_clone(ic, root: Path) -> None:
    """The fold trusts a claim on the comment log only from its account (DEC-043
    point 3), so only a clone of that account can release it."""
    gh = FakeGitHub()
    gh.add(7, assignees=("someone-else",))
    gh.post(7, _stamp(ic, "claim", 1), author="someone-else")
    kept = _cannot(ic, gh, _clone(ic, root), root)
    assert kept == ic.Unreleasable(
        "#7 is owned by instance 1 of @someone-else, a claim on the comment log that only a "
        "clone of @someone-else can release (DEC-043 point 3)",
        "run this from a clone of @someone-else, or once that account's clone released it",
    )
    assert gh.writes() == []


@pytest.mark.parametrize(
    ("claim", "labels", "owner"),
    [
        pytest.param(2, (), "instance 2", id="a-claim-on-the-comment-log"),
        pytest.param(None, ("instance:3",), "instance 3", id="an-instance-label"),
    ],
)
def test_a_clone_with_no_instance_releases_no_owner(
    ic, root: Path, no_topology, claim, labels, owner
) -> None:
    """DEC-035 point 1: a clone with no instance id touches no marker."""
    gh = FakeGitHub()
    gh.add(7, labels=labels)
    if claim is not None:
        gh.post(7, _stamp(ic, "claim", claim))
    kept = _cannot(ic, gh, None, root)
    assert kept is not None
    assert kept.why == (
        f"#7 is owned by {owner} of @me, and this clone takes no part in instance ownership, "
        "so it releases no claim (DEC-035 point 1)"
    )
    assert kept.remedy == "run this from the owner's clone, or once the owner released it"
    assert gh.writes() == []


def test_an_issue_no_instance_owns_needs_no_release_and_reads_no_topology(
    ic, root: Path, monkeypatch
) -> None:
    def no_read(*_args):
        raise AssertionError("an issue with no owner has no claim to judge")

    monkeypatch.setattr(ic, "_snapshot", no_read)
    gh = FakeGitHub()
    gh.add(7)
    assert _cannot(ic, gh, None, root) is None


def test_whose_an_issue_is_cannot_be_told_when_it_cannot_be_read(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    gh.failing.add("view")
    kept = _cannot(ic, gh, _clone(ic, root), root)
    assert kept is not None
    assert kept.why == "#7 could not be read, so whose it is cannot be told"


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
    assert ic.release_plan(clone).startswith("released on close (")
    assert ic.release_plan(clone, when="on the move back").startswith("released on the move back (")


# ---- the clash guard (DEC-035 point 6) ------------------------------------------

ME = SimpleNamespace(github_login="me", email="me@example.com")


def _guard(ic, gh: FakeGitHub, clone, bypass: str | None = None, dry_run: bool = False):
    return ic.guard(
        7,
        clone,
        {},
        verb="edit-issue",
        flag="--bypass-owner",
        bypass=bypass,
        invoker=ME,
        dry_run=dry_run,
        run=gh,
    )


def _audits(gh: FakeGitHub, n: int = 7) -> list[str]:
    return [c["body"] for c in gh.issues[n].comments if "pkit-audit-key" in c["body"]]


def test_the_guard_passes_an_unowned_issue(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    decision = _guard(ic, gh, _clone(ic, root))
    assert decision.outcome == ic.PASSED
    assert not decision.refused
    assert decision.line == ""
    assert gh.writes() == []


def test_the_guard_passes_this_clones_own_issue(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _stamp(ic, "claim", 2))
    assert _guard(ic, gh, _clone(ic, root)).outcome == ic.PASSED


def test_the_guard_refuses_another_instances_issue(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _stamp(ic, "claim", 3))
    decision = _guard(ic, gh, _clone(ic, root))
    assert decision.refused
    assert decision.line.startswith(
        "[refused] edit-issue #7: #7 is owned by instance 3, and this clone is instance 2."
    )
    assert 'pass --bypass-owner "<reason>"' in decision.line
    assert gh.writes() == []


def test_the_guard_refuses_an_instance_of_another_account(ic, root: Path) -> None:
    """The owner is the assignee paired with an instance (DEC-035 point 2)."""
    gh = FakeGitHub()
    gh.add(7, assignees=("someone-else",))
    gh.post(7, _stamp(ic, "claim", 2), author="someone-else")
    decision = _guard(ic, gh, _clone(ic, root))
    assert decision.refused
    assert "#7 is owned by instance 2 of @someone-else" in decision.line


def test_the_guard_names_no_account_on_an_unassigned_issue(ic, root: Path) -> None:
    """An unassigned issue that a label owns names its instance alone, never `@None`."""
    gh = FakeGitHub()
    gh.add(7, assignees=(), labels=("instance:3",))
    decision = _guard(ic, gh, _clone(ic, root, substrate="label"))
    assert decision.refused
    assert decision.line.startswith(
        "[refused] edit-issue #7: #7 is owned by instance 3, and this clone is instance 2."
    )
    assert "@None" not in decision.line


def test_in_a_same_instant_clash_the_guard_refuses_the_higher_instance(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _stamp(ic, "claim", 1))
    gh.post(7, _stamp(ic, "claim", 2))
    assert _guard(ic, gh, _clone(ic, root, instance=2)).refused
    assert _guard(ic, gh, _clone(ic, root, instance=1)).outcome == ic.PASSED


def test_an_issue_the_guard_cannot_read_is_refused(ic, root: Path) -> None:
    gh = FakeGitHub(failing={"view"})
    gh.add(7)
    decision = _guard(ic, gh, _clone(ic, root))
    assert decision.refused
    assert "#7 could not be read, so whose it is cannot be told" in decision.line


def test_a_bypass_posts_its_reason_once(ic, root: Path) -> None:
    """A command and the move it composes post one audit comment between them."""
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _stamp(ic, "claim", 3))
    first = _guard(ic, gh, _clone(ic, root), bypass="  its session is gone ")
    second = _guard(ic, gh, _clone(ic, root), bypass="its session is gone")
    assert first.bypassed and second.bypassed
    assert not first.refused
    (audit,) = _audits(gh)
    assert audit.startswith("<!-- pkit-audit -->\nBypassed by me <me@example.com>: its session")
    assert "The clash guard was bypassed: #7 is owned by instance 3, and this clone" in audit
    assert first.line.startswith("[warn] ownership: #7 is owned by instance 3, and --bypass-owner")


def test_a_bypass_whose_audit_cannot_be_posted_refuses(ic, root: Path) -> None:
    gh = FakeGitHub(failing={"comment"})
    gh.add(7)
    gh.post(7, _stamp(ic, "claim", 3))
    decision = _guard(ic, gh, _clone(ic, root), bypass="why")
    assert decision.outcome == ic.FAILED
    assert decision.refused
    assert "could not be written, so nothing was done" in decision.line


def test_a_dry_run_bypass_posts_nothing(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _stamp(ic, "claim", 3))
    decision = _guard(ic, gh, _clone(ic, root), bypass="why", dry_run=True)
    assert decision.bypassed
    assert decision.line.startswith("[dry-run] ownership:")
    assert gh.writes() == []


def test_say_guard_puts_a_refusal_on_stderr_and_a_pass_nowhere(ic, capsys) -> None:
    ic.say_guard(ic.Guard(ic.PASSED))
    ic.say_guard(ic.Guard(ic.REFUSED, "[refused] no"))
    ic.say_guard(ic.Guard(ic.BYPASSED, "[dry-run] would"))
    out, err = capsys.readouterr()
    assert out == "[dry-run] would\n"
    assert err == "[refused] no\n"


# ---- a project with a topology of seats (DEC-059) -------------------------------


def _held(ic, login: str = "me", key: str = "k2"):
    return ic.ownership.Holder(ic.ownership.SEAT_HELD, login, key)


def _seat_clone(ic, root: Path, *, role: str = "worker", holders: dict | None = None):
    """This clone holds seat `worker-2`, the topology's second, with the key `k2`."""
    seated = holders if holders is not None else {"worker-2": _held(ic)}
    return ic.Clone(2, "comment", "me", root, ic.Seat("worker-2", 2, role), "k2", seated)


def _seat_stamp(ic, seat: str, instance: int, key: str, event: str = "claim") -> str:
    return ic.ownership.format_event_comment(
        event=event, instance=instance, seat=seat, seat_number=instance, clone=key
    )


def test_a_clone_in_a_seat_takes_its_number_and_the_comment_log(ic, root, monkeypatch) -> None:
    """DEC-059 points 6 and 9: the seat's number, never a typed one, on the
    comment log whatever the selector names, with the key its runtime file keeps."""
    identity = importlib.import_module("_lib.instance_identity")
    identity.write_instance_id(root, 7)
    key = identity.ensure_clone_key(root)
    (root / "project" / "instance-ownership.yaml").write_text("substrate: label\n")
    holders = {"worker-2": _held(ic, key=key)}
    seat = ic.Seat("worker-2", 2, ic.WORKER)
    monkeypatch.setattr(
        ic, "read_topology", lambda _root, _config, **_kw: ic.Topology(seat, holders)
    )
    clone = ic.this_clone(root, "me")
    assert clone == ic.Clone(2, "comment", "me", root, seat, key, holders)
    assert clone.named() == "seat worker-2, instance 2"


def test_a_clone_that_holds_no_seat_takes_no_part(ic, root, monkeypatch) -> None:
    importlib.import_module("_lib.instance_identity").write_instance_id(root, 7)
    topology_with(ic, monkeypatch, ic.Topology(None, {}), key="k2")
    assert ic.this_clone(root, "me") is None


def test_a_clone_in_a_seat_with_no_key_takes_no_part(ic, root, monkeypatch) -> None:
    """A clone that holds a seat has a key, kept since its first claim on a
    state issue (DEC-058 point 5): with none, it cannot be the seat's holder."""
    seat = ic.Seat("worker-2", 2, ic.WORKER)
    topology_with(ic, monkeypatch, ic.Topology(seat, {"worker-2": _held(ic)}), key=None)
    assert ic.this_clone(root, "me") is None


def test_where_the_default_branch_declares_no_topology_dec_035_stands(
    ic, root: Path, no_topology
) -> None:
    """A project with no topology behaves as before: the typed number, the
    selected substrate, no seat and no holders."""
    importlib.import_module("_lib.instance_identity").write_instance_id(root, 2)
    assert ic.read_topology(root, {}, login="me") is None
    assert ic.this_clone(root, "me") == ic.Clone(2, "comment", "me", root)


@pytest.mark.parametrize(("role", "claims"), [("planner", False), ("worker", True), ("lead", True)])
def test_a_planner_files_with_no_owner(ic, root: Path, role: str, claims: bool) -> None:
    """DEC-059 point 7: a planner's work enters the shared pool, and a lead owns
    what it files."""
    clone = _seat_clone(ic, root, role=role)
    assert ic.claims_at_filing(clone, "me") is claims
    plan = ic.claim_plan(clone, "me", filing=True)
    assert plan.startswith("not claimed: seat worker-2") is not claims
    assert ic.claim_plan(clone) == "claimed for seat worker-2, instance 2 (comment substrate)"


def test_a_seats_claim_names_the_seat_its_number_and_the_key(ic, root: Path) -> None:
    """DEC-059 point 9, in the audit-log facility's stamp, with DEC-052's footer."""
    gh = FakeGitHub()
    gh.add(7)
    result = ic.claim(7, _seat_clone(ic, root), {}, run=gh)
    assert result.outcome == ic.CLAIMED
    assert result.line == (
        "[ok] ownership: #7 claimed for seat worker-2, instance 2 (comment substrate)."
    )
    claim = gh.issues[7].comments[0]["body"]
    assert "event=claim instance=2 seat=worker-2 seat_number=2 clone=k2 id=" in claim
    assert "<sub>🧰 pkit" in claim
    assert "**Owner:** instance 2 (worker-2)" in gh.issues[7].body


def test_with_no_topology_a_claim_names_no_seat(ic, root: Path) -> None:
    """An instance id's claim stays DEC-035's: the stamp holds the number alone."""
    gh = FakeGitHub()
    gh.add(7)
    ic.claim(7, _clone(ic, root), {}, run=gh)
    claim = gh.issues[7].comments[0]["body"]
    assert "event=claim instance=2 id=" in claim
    assert "seat=" not in claim and "clone=" not in claim


@pytest.mark.parametrize(
    "holder",
    [
        pytest.param(("free", None, None), id="its-seat-is-free"),
        pytest.param(("held", "me", "k3"), id="another-clone-took-its-seat"),
    ],
)
def test_a_claim_whose_clone_lost_its_seat_is_no_claim(ic, root, holder) -> None:
    """A seat's release frees its clone's claims with no write to the issue
    (DEC-059 point 5), so this clone claims."""
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _seat_stamp(ic, "worker-1", 1, "k1"))
    holders = {"worker-1": ic.ownership.Holder(*holder), "worker-2": _held(ic)}
    result = ic.claim(7, _seat_clone(ic, root, holders=holders), {}, run=gh)
    assert result.outcome == ic.CLAIMED
    assert result.winner == 2


def test_a_claim_made_under_a_typed_number_is_no_claim(ic, root) -> None:
    """DEC-059 point 9: it names no seat, so it stops counting with the topology."""
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _stamp(ic, "claim", 1))
    result = ic.claim(7, _seat_clone(ic, root), {}, run=gh)
    assert result.outcome == ic.CLAIMED


def test_a_claim_that_cannot_be_judged_keeps_the_issue(ic, root) -> None:
    """ADR-041 point 5: no consumer treats an unjudged claim as free."""
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _seat_stamp(ic, "worker-1", 1, "k1"))
    holders = {"worker-1": ic.ownership.Holder(ic.ownership.SEAT_UNREAD), "worker-2": _held(ic)}
    result = ic.claim(7, _seat_clone(ic, root, holders=holders), {}, run=gh)
    assert result.outcome == ic.ELSEWHERE
    assert "seat worker-1, instance 1, whose claim could not be judged since its seat's " in (
        result.line
    )
    assert gh.writes() == []


def test_two_seats_claiming_at_once_leave_it_to_the_lower(ic, root) -> None:
    gh = FakeGitHub()
    gh.add(7)

    def on_view(number: int, seen: int) -> None:
        if seen == 1:
            gh.post(number, _seat_stamp(ic, "worker-1", 1, "k1"))

    gh.on_view = on_view
    holders = {"worker-1": _held(ic, key="k1"), "worker-2": _held(ic)}
    result = ic.claim(7, _seat_clone(ic, root, holders=holders), {}, run=gh)
    assert result.outcome == ic.LOST
    assert result.line.startswith("[warn] ownership: seat worker-1, instance 1 claimed #7")
    assert "this clone, seat worker-2, instance 2, withdrew its claim" in result.line


def test_the_guard_refuses_another_seats_task_and_passes_a_void_claim(ic, root) -> None:
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _seat_stamp(ic, "worker-1", 1, "k1"))
    held = {"worker-1": _held(ic, key="k1"), "worker-2": _held(ic)}
    freed = {"worker-1": ic.ownership.Holder(ic.ownership.SEAT_FREE), "worker-2": _held(ic)}
    refused = _guard(ic, gh, _seat_clone(ic, root, holders=held))
    assert refused.refused
    assert "#7 is owned by seat worker-1, instance 1, and this clone is seat worker-2" in (
        refused.line
    )
    assert _guard(ic, gh, _seat_clone(ic, root, holders=freed)).outcome == ic.PASSED


def test_the_guard_refuses_a_claim_it_cannot_judge(ic, root) -> None:
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _seat_stamp(ic, "worker-1", 1, "k1"))
    decision = _guard(ic, gh, _seat_clone(ic, root))
    assert decision.refused
    assert "its seat is not among the seats read" in decision.line


def test_a_release_judges_claims_as_the_claim_and_the_guard_do(ic, root) -> None:
    """A claim that counts, and one that cannot be judged, are released. A claim
    whose clone no longer holds its seat is no owner, so none is posted for it."""
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _seat_stamp(ic, "worker-1", 1, "k1"))
    gh.post(7, _seat_stamp(ic, "worker-2", 2, "k2"))
    gh.post(7, _seat_stamp(ic, "worker-3", 3, "k3"))
    holders = {
        "worker-1": ic.ownership.Holder(ic.ownership.SEAT_FREE),
        "worker-2": _held(ic),
        "worker-3": ic.ownership.Holder(ic.ownership.SEAT_UNREAD),
    }
    result = ic.release(7, _seat_clone(ic, root, holders=holders), {}, run=gh)
    assert result.outcome == ic.RELEASED
    assert result.line == "[ok] ownership: #7 released (instance 2, instance 3)."
    assert _events(gh, 7) == ["claim 1", "claim 2", "claim 3", "release 2", "release 3"]


# ---- the topology read from the default branch, and the seat confirmed ---------
#
# One run's snapshot (`_lib/topology`) over seats whose state issues an in-memory
# GitHub holds (`tests/pm_state_issue_fakes.FakeRepo`). This clone is `me`, with
# the key `k2`, and took `worker-2`, the topology's third seat.


def _doc(*, retired: bool = False, scope: dict | None = None) -> dict:
    worker_2 = {"name": "worker-2", "role": "worker", "state_issue": 13, "retired": retired}
    if scope is not None:
        worker_2["scope"] = scope
    seats = [
        {"name": "planner", "role": "planner", "organizer": True, "state_issue": 11},
        {"name": "worker-1", "role": "worker", "state_issue": 12},
        worker_2,
    ]
    return {"schema_version": 1, "seats": seats}


def _seated(
    ic,
    holder: tuple[str, str] | None = ("me", "k2"),
    *,
    retired: bool = False,
    scope: dict | None = None,
):
    """The snapshot, and the GitHub that holds its seats: worker-1 held by
    `me`'s clone `k1`, and worker-2 by `holder`, with `scope` where given."""
    repo = FakeRepo()
    seat_issue(ic, repo, 11, "planner")
    seat_issue(ic, repo, 12, "worker-1", ("me", "k1"))
    seat_issue(ic, repo, 13, "worker-2", holder)
    return seat_snapshot(ic, _doc(retired=retired, scope=scope), repo), repo


def _views(repo: FakeRepo) -> list[int]:
    return [int(argv[3]) for argv in repo.calls if argv[1:3] == ["issue", "view"]]


def test_a_clone_that_took_no_seat_and_set_no_id_reads_nothing(ic, root, monkeypatch) -> None:
    def no_read(*_args):
        raise AssertionError("a clone that takes no part reads no topology")

    monkeypatch.setattr(ic, "_snapshot", no_read)
    assert ic.this_clone(root, "me") is None


def test_the_seat_is_confirmed_on_its_state_issue_and_numbered_by_its_place(
    ic, root, monkeypatch
) -> None:
    """DEC-059 point 6: the seat's name and number, from the topology, once its
    state issue shows this clone, by its account and key, as the holder."""
    snap, repo = _seated(ic)
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    clone = ic.this_clone(root, "me")
    assert clone is not None
    assert (clone.seat, clone.instance, clone.key) == (ic.Seat("worker-2", 3, "worker"), 3, "k2")
    assert clone.substrate == "comment" and clone.named() == "seat worker-2, instance 3"
    assert _views(repo) == [13]


def test_the_confirmed_seat_carries_the_scope_the_topology_gives_it(ic, root, monkeypatch) -> None:
    """DEC-059 point 7: the scope `next-task` narrows by is the topology seat's,
    and a seat the topology gives no scope has none."""
    snap, _repo = _seated(ic, scope={"workstreams": ["cli"], "types": ["bug"]})
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    scoped = ic.this_clone(root, "me")
    assert scoped is not None and scoped.seat is not None
    assert scoped.seat.scope == ic.topology.Scope(workstreams=("cli",), types=("bug",))
    snap, _repo = _seated(ic)
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    unscoped = ic.this_clone(root, "me")
    assert unscoped is not None and unscoped.seat is not None
    assert unscoped.seat.scope is None


def test_each_seats_holder_is_read_once_when_a_claim_names_it(ic, root, monkeypatch) -> None:
    """ADR-071 point 8: a seat's state issue is read when a claim names it, and
    the run judges every claim against what it read."""
    snap, repo = _seated(ic)
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    clone = ic.this_clone(root, "me")
    assert clone is not None and clone.holders is not None
    take = repo.issues[12].comments[-1]["id"]
    held = ic.ownership.Holder(ic.ownership.SEAT_HELD, "me", "k1", take)
    assert clone.holders["worker-1"] == held and clone.holders.get("worker-1") == held
    assert clone.holders["planner"] == ic.ownership.Holder(ic.ownership.SEAT_FREE)
    assert clone.holders.get("worker-9") is None
    assert _views(repo) == [13, 12, 11]


def test_the_guard_judges_claims_against_the_holders_it_reads(ic, root, monkeypatch) -> None:
    """A claim whose clone holds its seat refuses, and a claim of a clone that
    no longer holds it is no claim (DEC-059 points 5 and 9)."""
    snap, _repo = _seated(ic)
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    clone = ic.this_clone(root, "me")
    assert clone is not None
    held = FakeGitHub()
    held.add(7)
    held.post(7, _seat_stamp(ic, "worker-1", 2, "k1"))
    assert _guard(ic, held, clone).refused
    gone = FakeGitHub()
    gone.add(7)
    gone.post(7, _seat_stamp(ic, "worker-1", 2, "k0"))
    assert _guard(ic, gone, clone).outcome == ic.PASSED


def test_a_clone_with_no_seat_judges_claims_against_the_seats_it_reads(
    ic, root, monkeypatch
) -> None:
    """A clone that holds no seat releases no claim, so a claim that counts
    refuses the release. A void claim is no owner, and neither is a label,
    which names no seat (ADR-041 point 7)."""
    snap, _repo = _seated(ic)
    snapshot_with(ic, monkeypatch, snap, hint=None)
    held = FakeGitHub()
    held.add(7)
    held.post(7, _seat_stamp(ic, "worker-1", 2, "k1"))
    kept = _cannot(ic, held, None, root)
    assert kept is not None
    assert "#7 is owned by seat worker-1, instance 2 of @me" in kept.why
    gone = FakeGitHub()
    gone.add(7, labels=("instance:4",))
    gone.post(7, _seat_stamp(ic, "worker-1", 2, "k0"))
    assert _cannot(ic, gone, None, root) is None


# ---- a seat taken again after its release (#2182) --------------------------------
#
# A claim counts only where its clone made it after its current take of the seat
# (DEC-059 points 5 and 9). The seats' state issues and the Tasks are two fakes,
# which number their comments from one sequence, as GitHub does.


def _release_by_force(ic, repo: FakeRepo) -> None:
    """The organizer releases `worker-1` by force, on its state issue #12."""
    si, run = ic.state_issues, seat_snapshot(ic, _doc(), repo).run
    organizer = si.Clone("me", "k0", "host:/organizer")
    freed = si.force_release(
        12, ic.topology.SEAT_KIND, "worker-1", organizer, "its session stopped", run
    )
    assert freed.outcome == si.RELEASED


def _take_again(ic, repo: FakeRepo) -> None:
    """The clone that held `worker-1`, `me`'s `k1`, takes it again."""
    si, run = ic.state_issues, seat_snapshot(ic, _doc(), repo).run
    clone = si.Clone("me", "k1", "host:/clone")
    assert si.claim(12, ic.topology.SEAT_KIND, "worker-1", clone, run).outcome == si.CLAIMED


def _clone_in(ic, root, monkeypatch, repo: FakeRepo, seat: str = "worker-2", key: str = "k2"):
    """This clone in `seat`, with `key`, as a new run reads the seats from `repo`."""
    snap = seat_snapshot(ic, _doc(), repo, key=key)
    snapshot_with(ic, monkeypatch, snap, hint=seat, key=key)
    clone = ic.this_clone(root, "me")
    assert clone is not None
    return clone


def test_a_seat_taken_again_by_its_clone_revives_none_of_its_claims(ic, root, monkeypatch) -> None:
    """The same clone takes its seat again after a release by force, and the
    claim it made before the release stays void, so another seat may take its
    Task (DEC-059 point 5)."""
    _snap, repo = _seated(ic)
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _seat_stamp(ic, "worker-1", 2, "k1"))
    _release_by_force(ic, repo)
    _take_again(ic, repo)
    clone = _clone_in(ic, root, monkeypatch, repo)
    assert _guard(ic, gh, clone).outcome == ic.PASSED
    owner = ic.read_owner(7, clone, {}, run=gh)
    assert owner is not None and owner.owners == frozenset()
    judged = owner.judgement(2)
    assert judged is not None and judged.verdict == ic.ownership.VOID
    assert judged.reason == "its seat was released after it was made"


def test_a_task_taken_over_while_its_seat_was_free_stays_the_takers(ic, root, monkeypatch) -> None:
    """Another seat takes the Task over while the seat is free, and keeps it
    once the first clone takes its seat again: the guard passes the taker and
    refuses the first clone."""
    _snap, repo = _seated(ic)
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _seat_stamp(ic, "worker-1", 2, "k1"))
    _release_by_force(ic, repo)
    taker = _clone_in(ic, root, monkeypatch, repo)
    assert ic.claim(7, taker, {}, run=gh).outcome == ic.CLAIMED
    _take_again(ic, repo)
    taker = _clone_in(ic, root, monkeypatch, repo)
    assert _guard(ic, gh, taker).outcome == ic.PASSED
    owner = ic.read_owner(7, taker, {}, run=gh)
    assert owner is not None and owner.owners == frozenset({3})
    first = _clone_in(ic, root, monkeypatch, repo, seat="worker-1", key="k1")
    refused = _guard(ic, gh, first)
    assert refused.refused
    assert "#7 is owned by seat worker-2, instance 3" in refused.line


def test_a_claim_made_after_the_seat_was_taken_again_counts(ic, root, monkeypatch) -> None:
    """The clone that took its seat again owns what it claims from then on."""
    _snap, repo = _seated(ic)
    gh = FakeGitHub()
    gh.add(7)
    _release_by_force(ic, repo)
    _take_again(ic, repo)
    gh.post(7, _seat_stamp(ic, "worker-1", 2, "k1"))
    clone = _clone_in(ic, root, monkeypatch, repo)
    refused = _guard(ic, gh, clone)
    assert refused.refused
    assert "#7 is owned by seat worker-1, instance 2" in refused.line


@pytest.mark.parametrize(
    ("holder", "said"),
    [
        pytest.param(("me", "k9"), "held by @me, clone k9", id="another-clone"),
        pytest.param(("you", "k2"), "held by @you, clone k2", id="another-account"),
        pytest.param(None, "shows it free", id="free"),
    ],
)
def test_a_seat_this_clone_no_longer_holds_refuses(ic, root, monkeypatch, holder, said) -> None:
    """DEC-058 point 5: a command that acts as the holder refuses a clone that
    does not hold the seat, such as after a release by force."""
    snap, _repo = _seated(ic, holder)
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    with pytest.raises(ic.Unconfirmed, match="no longer holds the seat worker-2") as caught:
        ic.this_clone(root, "me")
    assert said in str(caught.value) and "#13" in str(caught.value)


def test_a_seat_whose_state_issue_cannot_be_read_refuses(ic, root, monkeypatch) -> None:
    snap, repo = _seated(ic)
    repo.failing.add("view")
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    with pytest.raises(ic.Unconfirmed, match="worker-2, could not be confirmed"):
        ic.this_clone(root, "me")


def test_a_seat_the_topology_does_not_hold_refuses(ic, root, monkeypatch) -> None:
    snap, _repo = _seated(ic)
    snapshot_with(ic, monkeypatch, snap, hint="worker-9")
    with pytest.raises(ic.Unconfirmed, match="the seat worker-9, which the topology at"):
        ic.this_clone(root, "me")


@pytest.mark.parametrize(
    ("login", "key", "said"),
    [("me", "", "keeps no key"), ("", "k2", "GitHub account could not be resolved")],
)
def test_a_clone_with_no_key_or_account_cannot_confirm_its_seat(
    ic, root, monkeypatch, login, key, said
) -> None:
    _snap, repo = _seated(ic)
    snap = seat_snapshot(ic, _doc(), repo, login=login, key=key)
    snapshot_with(ic, monkeypatch, snap, hint="worker-2", key=key or None)
    with pytest.raises(ic.Unconfirmed, match=said):
        ic.this_clone(root, login or None)


def test_a_retired_seat_is_released_at_its_clones_next_command(
    ic, root, monkeypatch, capsys
) -> None:
    """DEC-059 point 5: released as its clone would release it, and the clone
    then acts as no instance. A dry run releases nothing."""
    snap, repo = _seated(ic, retired=True)
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    assert ic.this_clone(root, "me", dry_run=True) is None
    assert repo.writes() == []
    assert ic.this_clone(root, "me") is None
    after = ic.state_issues.read(13, "seat", "worker-2", snap.run)
    assert after.fold is not None and after.fold.free
    assert [ev.type for ev in after.fold.events] == ["state-claim", "state-release"]
    err = capsys.readouterr().err
    assert "[dry-run] ownership: the seat worker-2 is retired" in err
    assert "the seat worker-2 is retired, so this clone released it on #13" in err


@pytest.mark.parametrize("failing", ["comment", "read-after"])
def test_a_retired_seat_whose_release_is_not_seen_to_land_is_not_forgotten(
    ic, root, monkeypatch, capsys, failing
) -> None:
    """A release that failed, or whose read after it failed, leaves the seat
    unread, which is no sign that the clone no longer holds it."""
    snap, repo = _seated(ic, retired=True)
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    forgotten: list[Path] = []
    monkeypatch.setattr(ic, "clear_seat_hint", lambda root: forgotten.append(root) or True)
    if failing == "comment":
        repo.failing.add("comment")
    else:
        repo.before_post = lambda _number: repo.failing.add("view")
    assert ic.this_clone(root, "me") is None
    assert forgotten == []
    assert "the seat worker-2 is retired, and its release on #13 failed" in (
        capsys.readouterr().err
    )


def test_a_typed_number_is_not_used_where_the_project_has_a_topology(
    ic, root, monkeypatch, capsys
) -> None:
    """DEC-059 point 6: a clone that took no seat takes no part, whatever number
    was typed into it."""
    importlib.import_module("_lib.instance_identity").write_instance_id(root, 5)
    snap, repo = _seated(ic)
    snapshot_with(ic, monkeypatch, snap, hint=None)
    assert ic.this_clone(root, "me") is None
    assert repo.calls == []
    err = capsys.readouterr().err
    assert "the number 5 typed into this clone is not used" in err
    assert err.count("c0ffee") == 1  # the commit is named once in the run


def test_without_the_default_branch_a_seat_cannot_be_confirmed(ic, root, monkeypatch) -> None:
    """DEC-059 point 1: no clone acts as a seat without the default branch."""

    def unresolved(*_args):
        raise ic.topology.Unresolved("origin/main is not fetched")

    monkeypatch.setattr(ic, "_snapshot", unresolved)
    monkeypatch.setattr(ic, "read_seat_hint", lambda _root: "worker-2")
    with pytest.raises(ic.Unconfirmed, match="origin/main is not fetched"):
        ic.this_clone(root, "me")


def test_without_the_default_branch_a_typed_number_stands(ic, root, monkeypatch, capsys) -> None:
    """A clone that took no seat keeps DEC-035's number, with a note, since no
    topology was read to refuse it."""

    def unresolved(*_args):
        raise ic.topology.Unresolved("origin/main is not fetched")

    importlib.import_module("_lib.instance_identity").write_instance_id(root, 2)
    monkeypatch.setattr(ic, "_snapshot", unresolved)
    assert ic.this_clone(root, "me") == ic.Clone(2, "comment", "me", root)
    assert "acts as the instance number typed into it" in capsys.readouterr().err


def test_an_unconfirmed_seat_is_refused_with_its_reason(ic, capsys) -> None:
    assert ic.say_unconfirmed("move-issue", 42, ic.Unconfirmed("why.")) == 1
    assert capsys.readouterr().err == "[refused] move-issue #42: why. Nothing was written.\n"


# ---- the commit the run read, named once (DEC-059 point 1) --------------------------

_READ = "[note] ownership: this clone read the topology of origin/main at c0ffee.\n"


def test_the_seat_confirmation_names_the_commit_it_read_once_a_run(ic, root, monkeypatch, capsys):
    """A clone says which commit of the default branch it read. A second reading
    in the run, such as the `move-issue` that `start-work` runs, says it no more."""
    snap, _repo = _seated(ic)
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    assert ic.this_clone(root, "me") is not None
    assert ic.this_clone(root, "me") is not None
    assert capsys.readouterr().err == _READ


def test_a_reading_of_a_commit_the_run_did_not_name_names_it(ic, root, monkeypatch, capsys):
    """The command that ran this one named another commit: the default branch
    moved between the two readings."""
    snap, _repo = _seated(ic)
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    monkeypatch.setenv(ic.topology.NAMED_ENV, "beef")
    assert ic.this_clone(root, "me") is not None
    assert capsys.readouterr().err == _READ


def test_the_commit_is_named_before_a_seat_is_refused(ic, root, monkeypatch, capsys) -> None:
    """A clone that has not fetched the default branch reads what it last
    fetched, so a refusal follows the commit it read."""
    snap, _repo = _seated(ic, ("me", "k9"))
    snapshot_with(ic, monkeypatch, snap, hint="worker-2")
    with pytest.raises(ic.Unconfirmed):
        ic.this_clone(root, "me")
    assert capsys.readouterr().err == _READ


def test_a_project_with_no_topology_names_no_commit(
    ic, root, monkeypatch, capsys, no_topology
) -> None:
    importlib.import_module("_lib.instance_identity").write_instance_id(root, 2)
    monkeypatch.setenv(ic.topology.NAMED_ENV, "")
    assert ic.this_clone(root, "me") == ic.Clone(2, "comment", "me", root)
    assert capsys.readouterr().err == ""
    assert os.environ[ic.topology.NAMED_ENV] == ""


# Every command that writes as an instance: the clash guard's six, the claim at
# filing and the release on close.
_WRITE_COMMANDS = (
    "create-issue.py",
    "start-work.py",
    "review-work.py",
    "done-work.py",
    "promote-issue.py",
    "edit-issue.py",
    "move-issue.py",
    "close-issue.py",
)
_OWNERSHIP_WRITES = ("instance_claims.guard(", "instance_claims.claim(", "instance_claims.release(")


def test_the_write_commands_are_every_script_that_writes_ownership() -> None:
    writers = {
        p.name
        for p in SCRIPTS.glob("*.py")
        if any(w in p.read_text(encoding="utf-8") for w in _OWNERSHIP_WRITES)
    }
    assert writers == set(_WRITE_COMMANDS)


@pytest.mark.parametrize("script", _WRITE_COMMANDS)
def test_every_write_command_confirms_the_seat_where_the_guard_runs(script: str) -> None:
    """DEC-059 point 6: one function confirms the clone's seat, and each write
    command asks it once, before its first ownership write, and handles its
    refusal."""
    source = (SCRIPTS / script).read_text(encoding="utf-8")
    assert source.count("instance_claims.this_clone(") == 1
    assert "except instance_claims.Unconfirmed" in source
    first = min(source.index(w) for w in _OWNERSHIP_WRITES if w in source)
    assert source.index("instance_claims.this_clone(") < first


# ---- the owner, as the shared pool reads it (DEC-059 point 7) ------------------


def test_read_owner_folds_as_the_guard_does_and_writes_nothing(ic, root: Path) -> None:
    gh = FakeGitHub()
    gh.add(7)
    gh.post(7, _seat_stamp(ic, "worker-1", 1, "k1"))
    held = {"worker-1": _held(ic, key="k1"), "worker-2": _held(ic)}
    resolution = ic.read_owner(7, _seat_clone(ic, root, holders=held), {}, run=gh)
    assert resolution is not None
    assert resolution.claimants == frozenset({1})
    assert ic.owner_named(resolution, 1) == "seat worker-1, instance 1"
    assert gh.writes() == []


def test_read_owner_reads_the_assignees_markers(ic, root: Path) -> None:
    """The markers of the first assignee where this clone's account is none."""
    gh = FakeGitHub()
    gh.add(7, assignees=("alice",))
    gh.post(7, _stamp(ic, "claim", 3), author="alice")
    resolution = ic.read_owner(7, _clone(ic, root), {}, run=gh)
    assert resolution is not None
    assert resolution.owners == frozenset({3})


def test_read_owner_of_an_issue_it_cannot_read_is_none(ic, root: Path) -> None:
    gh = FakeGitHub(failing={"view"})
    gh.add(7)
    assert ic.read_owner(7, _clone(ic, root), {}, run=gh) is None
