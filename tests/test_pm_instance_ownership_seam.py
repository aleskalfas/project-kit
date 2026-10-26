"""The instance-ownership marker seam — ADR-041, both halves.

[ADR-041](../tech-docs/architecture/decisions/ADR-041-instance-ownership-substrate-contract.md)
makes ownership resolution a single fold seam and each ownership write a single
construction point, over two selectable substrates (DEC-043). This file pins:

  * **the read fold** (:func:`resolve_owner`) — authenticity filtering, the
    append-only fold, lowest-wins on a same-instant clash, and comment-log-wins
    over a lingering label (ADR-041 §1-§2);
  * **the write constructors** — the ownership-event comment, the label backend,
    and the derived-mirror full-overwrite (ADR-041 §3-§4);
  * **the guard** (half b) — the ``pkit:instance-owner`` stamp is built ONLY in the
    seam module; no other script embeds it inline. The ownership marker's stamp is a
    distinctive literal signature, so the guard keys on it directly (unlike the
    multi-form ``gh`` argvs the ADR-031 guard must AST-resolve).
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.pm_ownership_support import stub_seat_stamps

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB = SCRIPTS / "_lib"
SEAM_MODULE = LIB / "instance_ownership.py"

# The distinctive stamp signature — the guard's key (half b).
STAMP_SIGNATURE = "pkit:instance-owner"

T0 = datetime(2026, 7, 7, 12, 0, 0, tzinfo=UTC)
T1 = datetime(2026, 7, 7, 12, 1, 0, tzinfo=UTC)  # T0 + 1 minute


@pytest.fixture(scope="module")
def io():
    """Load the seam via importlib (sibling _lib import path)."""
    if str(LIB) not in sys.path:
        sys.path.insert(0, str(LIB))
    spec = importlib.util.spec_from_file_location("pm_instance_ownership_under_test", SEAM_MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_instance_ownership_under_test"] = module
    spec.loader.exec_module(module)
    return module


def _comment(io, *, event, instance, author, ts, to=None, name=None):
    """A GitHub-comment dict carrying a real ownership stamp authored by `author`."""
    body = io.format_event_comment(event=event, instance=instance, ts=ts, to=to, name=name)
    return {"body": body, "author": {"login": author}}


# ---- stamp round-trip ----------------------------------------------------


def test_stamp_formats_and_parses_round_trip(io) -> None:
    comments = [_comment(io, event="claim", instance=2, author="alice", ts=T0)]
    events = io.parse_events(comments, "alice")
    assert len(events) == 1
    e = events[0]
    assert (e.event, e.instance, e.assignee) == ("claim", 2, "alice")


def test_stamp_carries_no_assignee_only_instance(io) -> None:
    """The stamp encodes instance (+ event + ts + optional `to`) but NOT the
    assignee — the owner's account is the comment's author.login (DEC-043 D3)."""
    stamp = io.format_stamp("claim", 2, T0)
    assert "instance=2" in stamp
    assert "assignee" not in stamp
    assert STAMP_SIGNATURE in stamp


# ---- the fold ------------------------------------------------------------


def test_claim_yields_owner(io) -> None:
    res = io.resolve_owner(
        comments=[_comment(io, event="claim", instance=2, author="alice", ts=T0)],
        labels=[],
        assignee_login="alice",
    )
    assert res.owners == frozenset({2})
    assert res.winner == 2
    assert res.substrate == "comment"
    assert res.claimed is True


def test_handoff_transfers_ownership(io) -> None:
    comments = [
        _comment(io, event="claim", instance=2, author="alice", ts=T0),
        _comment(io, event="handoff", instance=2, to=3, author="alice", ts=T1),
    ]
    res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice")
    assert res.owners == frozenset({3})


def test_abandon_and_release_return_to_commons(io) -> None:
    for terminal in ("abandon", "release"):
        comments = [
            _comment(io, event="claim", instance=2, author="alice", ts=T0),
            _comment(io, event=terminal, instance=2, author="alice", ts=T1),
        ]
        res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice")
        assert not res.claimed, f"{terminal} should return the issue to commons"
        assert res.winner is None


def test_same_instant_clash_lowest_wins(io) -> None:
    """Two clones claim at the same instant — both markers coexist (comment-create
    is atomic), and the winner is the lowest instance number (DEC-035 D6)."""
    comments = [
        _comment(io, event="claim", instance=3, author="alice", ts=T0),
        _comment(io, event="claim", instance=2, author="alice", ts=T0),
    ]
    res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice")
    assert res.owners == frozenset({2, 3})
    assert res.winner == 2  # lowest wins; instance 3 backs off


# ---- authenticity --------------------------------------------------------


def test_forged_marker_from_another_account_is_ignored(io) -> None:
    """A stamped comment authored by someone other than the issue assignee is a
    forgery and does not count (ADR-041 §1 / DEC-043 D3)."""
    comments = [_comment(io, event="claim", instance=9, author="mallory", ts=T0)]
    res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice")
    assert not res.claimed


def test_no_assignee_means_no_authentic_marker(io) -> None:
    comments = [_comment(io, event="claim", instance=2, author="alice", ts=T0)]
    res = io.resolve_owner(comments=comments, labels=[], assignee_login=None)
    assert not res.claimed


# ---- mixed-mode: comment-log-wins ---------------------------------------


def test_comment_log_wins_over_lingering_label(io) -> None:
    """A repo forward-switched label→comment may hold both; the comment-log owner
    is authoritative, the lingering `instance:N` label is residual (ADR-041 §2)."""
    comments = [_comment(io, event="claim", instance=2, author="alice", ts=T0)]
    res = io.resolve_owner(
        comments=comments,
        labels=[{"name": "instance:5"}],
        assignee_login="alice",
    )
    assert res.substrate == "comment"
    assert res.owners == frozenset({2})  # label:5 is residual, ignored


def test_label_resolves_when_no_comment_marker(io) -> None:
    res = io.resolve_owner(
        comments=[],
        labels=[{"name": "instance:4"}, {"name": "priority:High"}],
        assignee_login="alice",
    )
    assert res.substrate == "label"
    assert res.owners == frozenset({4})


def test_unclaimed_when_neither_substrate_marks(io) -> None:
    res = io.resolve_owner(comments=[], labels=[{"name": "type:feature"}], assignee_login="alice")
    assert not res.claimed
    assert res.substrate is None


# ---- write constructors --------------------------------------------------


def test_event_comment_constructor_shape(io) -> None:
    args = io.ownership_event_comment_args(issue_number=42, event="claim", instance=2, ts=T0)
    assert args[:4] == ["gh", "issue", "comment", "42"]
    assert args[4] == "--body"
    assert STAMP_SIGNATURE in args[5]
    assert "instance 2" in args[5]  # visible human text, so the comment isn't blank


def test_event_comment_refuses_unknown_event(io) -> None:
    with pytest.raises(ValueError):
        io.format_stamp("frobnicate", 2, T0)


def test_label_backend_constructor(io) -> None:
    assert io.instance_label_args(issue_number=7, instance=3) == [
        "gh",
        "issue",
        "edit",
        "7",
        "--add-label",
        "instance:3",
    ]
    assert io.instance_label_args(issue_number=7, instance=3, remove=True)[-2] == "--remove-label"


def test_label_create_constructor(io) -> None:
    """DEC-035 point 2 creates the label lazily; the seam builds that write too."""
    args = io.instance_label_create_args(instance=3)
    assert args[:4] == ["gh", "label", "create", "instance:3"]
    assert "--description" in args


# ---- derived mirror ------------------------------------------------------


def test_mirror_region_reflects_owner(io) -> None:
    res = io.resolve_owner(
        comments=[_comment(io, event="claim", instance=2, author="alice", ts=T0)],
        labels=[],
        assignee_login="alice",
    )
    region = io.render_mirror_region(res, names={2: "data"})
    assert io.MIRROR_BEGIN in region and io.MIRROR_END in region
    assert "instance 2 (data)" in region


def test_mirror_region_unclaimed(io) -> None:
    res = io.resolve_owner(comments=[], labels=[], assignee_login="alice")
    region = io.render_mirror_region(res)
    assert "Unclaimed" in region


def test_mirror_body_overwrites_not_appends(io) -> None:
    """Regeneration is a FULL OVERWRITE of the fenced region — a stray human edit
    is healed, and the region never accumulates (ADR-041 §4). Never an append."""
    res1 = io.resolve_owner(
        comments=[_comment(io, event="claim", instance=2, author="alice", ts=T0)],
        labels=[],
        assignee_login="alice",
    )
    body0 = "## What\n\nSome issue text.\n"
    body1 = io.render_mirror_body(body0, io.render_mirror_region(res1))
    assert body1.count(io.MIRROR_BEGIN) == 1
    assert "Some issue text." in body1  # existing content preserved

    # Re-render with a different owner — the region is replaced, not duplicated.
    res2 = io.resolve_owner(
        comments=[
            _comment(io, event="claim", instance=2, author="alice", ts=T0),
            _comment(io, event="handoff", instance=2, to=3, author="alice", ts=T1),
        ],
        labels=[],
        assignee_login="alice",
    )
    body2 = io.render_mirror_body(body1, io.render_mirror_region(res2))
    assert body2.count(io.MIRROR_BEGIN) == 1  # still one region
    assert "instance 3" in body2 and "instance 2" not in body2.split(io.MIRROR_BEGIN)[1]


# ---- selector ------------------------------------------------------------


def test_selector_defaults_to_comment(io) -> None:
    assert io.resolve_substrate(None) == "comment"
    assert io.resolve_substrate({}) == "comment"


def test_selector_reads_own_schema_home(io) -> None:
    # `settings` is the parsed instance-ownership.yaml (top-level `substrate`).
    assert io.resolve_substrate({"substrate": "label"}) == "label"
    # An unknown value falls back to the safe default.
    assert io.resolve_substrate({"substrate": "bogus"}) == "comment"


# ---- a project with a topology of seats (ADR-041 point 7) -----------------


@pytest.fixture
def seat_stamps(io, monkeypatch) -> None:
    """The stamp that names a seat, as the audit-log facility will build it (#2138)."""
    stub_seat_stamps(io, monkeypatch)


def _seat_comment(io, *, event, instance, seat, key, author="alice", to=None, created=None):
    body = io.format_event_comment(event=event, instance=instance, ts=T0, seat=seat, key=key, to=to)
    comment = {"body": body, "author": {"login": author}}
    if created is not None:
        comment["createdAt"] = created
    return comment


def _holders(io, **seats):
    """Each seat's holder: a key held by `alice`, `free` or `unread`."""
    out = {}
    for seat, value in seats.items():
        if value in ("free", "unread"):
            out[seat.replace("_", "-")] = io.Holder(value)
        else:
            out[seat.replace("_", "-")] = io.Holder(io.SEAT_HELD, "alice", value)
    return out


def test_with_no_builder_no_stamp_names_a_seat(io) -> None:
    """The builder and parser are #2138's: until they land, a claim that names a
    seat cannot be built, and no comment is read as one."""
    with pytest.raises(io.SeatStampUnavailable, match="#2138"):
        io.format_event_comment(event="claim", instance=1, ts=T0, seat="w-1", key="k1")
    assert io.read_seat_stamp("<!-- anything -->") is None


def test_a_seat_stamp_round_trips_with_its_seat_key_and_github_time(io, seat_stamps) -> None:
    comment = _seat_comment(
        io, event="claim", instance=2, seat="w-2", key="k2", created="2026-10-26T08:00:00Z"
    )
    (event,) = io.parse_events([comment], "alice")
    assert (event.event, event.instance, event.seat, event.key) == ("claim", 2, "w-2", "k2")
    assert event.ts == datetime(2026, 10, 26, 8, 0, tzinfo=UTC)
    assert "**🔖 Claimed** — instance 2 (w-2)" in comment["body"]


def test_a_claim_counts_while_its_clone_holds_its_seat(io, seat_stamps) -> None:
    comments = [_seat_comment(io, event="claim", instance=1, seat="w-1", key="k1")]
    res = io.resolve_owner(
        comments=comments, labels=[], assignee_login="alice", holders=_holders(io, w_1="k1")
    )
    assert res.owners == frozenset({1})
    assert res.claimants == frozenset({1})
    assert res.judgement(1) == io.ClaimJudgement(1, "w-1", "k1", io.COUNTS)


@pytest.mark.parametrize(
    ("holder", "verdict", "reason"),
    [
        ("free", "void", "its clone no longer holds its seat"),
        ("k9", "void", "its clone no longer holds its seat"),
        ("unread", "unjudged", "its seat's holder could not be read"),
        (None, "unjudged", "its seat is not among the seats read"),
    ],
)
def test_a_claim_is_judged_against_its_seats_holder(io, seat_stamps, holder, verdict, reason):
    """A seat's release frees its clone's claims when they are read (DEC-059 point
    5), and a seat that was not read leaves the claim unjudged (ADR-041 point 7)."""
    comments = [_seat_comment(io, event="claim", instance=1, seat="w-1", key="k1")]
    holders = _holders(io, w_1=holder) if holder is not None else {}
    res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice", holders=holders)
    assert res.owners == frozenset()
    assert res.judgement(1).verdict == verdict
    assert res.judgement(1).reason == reason
    assert res.claimants == (frozenset({1}) if verdict == "unjudged" else frozenset())


def test_a_holder_under_another_account_does_not_hold_the_claim(io, seat_stamps) -> None:
    comments = [_seat_comment(io, event="claim", instance=1, seat="w-1", key="k1")]
    holders = {"w-1": io.Holder(io.SEAT_HELD, "bob", "k1")}
    res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice", holders=holders)
    assert res.judgement(1).verdict == io.VOID


def test_under_a_topology_a_typed_number_claim_and_a_label_are_void(io) -> None:
    """DEC-059 point 9: neither names a seat."""
    comments = [_comment(io, event="claim", instance=2, author="alice", ts=T0)]
    res = io.resolve_owner(
        comments=comments, labels=["instance:3"], assignee_login="alice", holders={}
    )
    assert res.owners == frozenset()
    assert [(j.instance, j.verdict, j.reason) for j in res.judgements] == [
        (2, "void", "it names no seat"),
        (3, "void", "it names no seat"),
    ]


def test_under_a_topology_the_log_folds_in_githubs_order(io, seat_stamps) -> None:
    """The stamps' times are a clone's and decide nothing (ADR-041 point 7): a
    claim listed after an abandon holds, whatever time its stamp carries."""
    abandon = _comment(io, event="abandon", instance=1, author="alice", ts=T1)
    claim = _seat_comment(io, event="claim", instance=1, seat="w-1", key="k1")
    holders = _holders(io, w_1="k1")
    res = io.resolve_owner(
        comments=[abandon, claim], labels=[], assignee_login="alice", holders=holders
    )
    assert res.owners == frozenset({1})
    # With no topology a log listed in the same order folds by the stamps'
    # times: the abandon, stamped later, comes last there.
    plain = io.resolve_owner(
        comments=[abandon, _comment(io, event="claim", instance=1, author="alice", ts=T0)],
        labels=[],
        assignee_login="alice",
    )
    assert plain.owners == frozenset()


def test_a_handoff_to_a_seat_counts_for_the_target(io, seat_stamps) -> None:
    comments = [
        _seat_comment(io, event="claim", instance=1, seat="w-1", key="k1"),
        _seat_comment(io, event="handoff", instance=1, seat="w-2", key="k2", to=2),
    ]
    holders = _holders(io, w_1="k1", w_2="k2")
    res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice", holders=holders)
    assert res.owners == frozenset({2})
    assert res.judgement(2).seat == "w-2"


# ========================================================================
# Half (b) — the guard: the stamp is built ONLY in the seam
# ========================================================================


def _scanned_scripts() -> list[Path]:
    return [
        p
        for p in sorted(SCRIPTS.rglob("*.py"))
        if p != SEAM_MODULE and "__pycache__" not in p.parts
    ]


@pytest.mark.parametrize("path", _scanned_scripts(), ids=lambda p: str(p.relative_to(SCRIPTS)))
def test_no_script_embeds_the_ownership_stamp_inline(path: Path) -> None:
    """No pm script embeds the `pkit:instance-owner` stamp literal except the seam
    (ADR-041 §3 part b). Every ownership-event / mirror write is constructed by the
    seam; a script that hard-codes the stamp is bypassing the sole constructor."""
    src = path.read_text(encoding="utf-8")
    assert STAMP_SIGNATURE not in src, (
        f"{path.name} embeds the ownership stamp `{STAMP_SIGNATURE}` inline — "
        "construct ownership writes only via _lib.instance_ownership "
        "(ownership_event_comment_args / render_mirror_region)."
    )


def test_seam_is_the_one_place_the_stamp_lives() -> None:
    """The seam module is the sole constructor of the stamp — pins that the
    construction actually lives there (the guard above excludes it by name)."""
    assert STAMP_SIGNATURE in SEAM_MODULE.read_text(encoding="utf-8")
