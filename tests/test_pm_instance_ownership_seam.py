"""The instance-ownership marker seam — ADR-041, both halves.

[ADR-041](../tech-docs/architecture/decisions/ADR-041-instance-ownership-substrate-contract.md)
makes ownership resolution a single fold seam and each ownership write a single
construction point, over two selectable substrates (DEC-043). This file pins:

  * **the read fold** (:func:`resolve_owner`) — authenticity filtering, the
    append-only fold, lowest-wins on a same-instant clash, and comment-log-wins
    over a lingering label (ADR-041 §1-§2);
  * **the write constructors** — the ownership-event comment, the label backend,
    and the derived-mirror full-overwrite (ADR-041 §3-§4);
  * **the guard** (half b) — the ``pkit:instance-owner`` signature, of the old
    stamp the facility still reads and of the mirror region, lives ONLY in the seam
    module and the audit-log facility; no other script embeds it inline. The
    ownership marker's stamp is a distinctive literal signature, so the guard keys
    on it directly (unlike the multi-form ``gh`` argvs the ADR-031 guard must
    AST-resolve).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB = SCRIPTS / "_lib"
SEAM_MODULE = LIB / "instance_ownership.py"
BUILDER_MODULE = LIB / "audit_log.py"

# The distinctive stamp signature — the guard's key (half b).
STAMP_SIGNATURE = "pkit:instance-owner"

#: An ownership stamp as the seam wrote it before the audit-log facility.
OLD_STAMP = "<!-- pkit:instance-owner v=1 event={event} instance={instance}{to} ts={ts} -->"


@pytest.fixture(scope="module")
def io():
    """Load the seam via importlib (sibling _lib import path)."""
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("pm_instance_ownership_under_test", SEAM_MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_instance_ownership_under_test"] = module
    spec.loader.exec_module(module)
    return module


def _comment(io, *, event, instance, author, to=None, name=None, **topology):
    """A GitHub-comment dict carrying a real ownership stamp authored by `author`."""
    body = io.format_event_comment(event=event, instance=instance, to=to, name=name, **topology)
    return {"body": body, "author": {"login": author}}


def _old_comment(*, event, instance, author, to=None, ts="2026-07-07T12:00:00+00:00"):
    stamp = OLD_STAMP.format(
        event=event, instance=instance, to=f" to={to}" if to is not None else "", ts=ts
    )
    return {"body": f"**Old** — instance {instance}\n{stamp}", "author": {"login": author}}


# ---- stamp round-trip ----------------------------------------------------


def test_stamp_formats_and_parses_round_trip(io) -> None:
    comments = [_comment(io, event="claim", instance=2, author="alice")]
    events = io.parse_events(comments, "alice")
    assert len(events) == 1
    e = events[0]
    assert (e.event, e.instance, e.assignee) == ("claim", 2, "alice")
    assert e.act and not e.legacy


def test_stamp_carries_no_assignee_only_instance(io) -> None:
    """The stamp encodes instance (+ event + optional `to`) but NOT the assignee —
    the owner's account is the comment's author.login (DEC-043 D3) — and no time:
    the fold takes the comment's time from GitHub (ADR-041 point 7)."""
    body = io.format_event_comment(event="claim", instance=2)
    assert "instance=2" in body
    assert "assignee" not in body and " ts=" not in body
    assert "<!-- pkit-claim -->" in body  # DEC-052's kind marker


def test_the_new_stamp_names_the_seat_its_number_and_the_clones_key(io) -> None:
    comments = [
        _comment(
            io, event="claim", instance=3, author="alice", seat="worker", seat_number=3, clone="k9"
        )
    ]
    (e,) = io.parse_events(comments, "alice")
    assert (e.seat, e.seat_number, e.clone) == ("worker", 3, "k9")


def test_the_old_stamps_still_read(io) -> None:
    """A claim made before the facility keeps its owner (DEC-059 Implications)."""
    comments = [
        _old_comment(event="claim", instance=2, author="alice"),
        _old_comment(event="handoff", instance=2, to=4, author="alice"),
    ]
    res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice")
    assert res.owners == frozenset({4})
    assert all(e.legacy for e in res.events)
    assert res.events[0].ts is not None


def test_old_and_new_stamps_fold_in_the_order_of_their_comments(io) -> None:
    comments = [
        _old_comment(event="claim", instance=2, author="alice", ts="2030-01-01T00:00:00+00:00"),
        _comment(io, event="release", instance=2, author="alice"),
    ]
    res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice")
    assert not res.claimed  # the release follows the claim, whatever its stamp's time


def test_the_event_carries_the_id_its_caller_made_for_the_act(io) -> None:
    args = io.ownership_event_comment_args(issue_number=4, event="abandon", instance=2, act="a1")
    (e,) = io.parse_events([{"body": args[5], "author": {"login": "x"}}], "x")
    assert e.act == "a1"


# ---- the fold ------------------------------------------------------------


def test_claim_yields_owner(io) -> None:
    res = io.resolve_owner(
        comments=[_comment(io, event="claim", instance=2, author="alice")],
        labels=[],
        assignee_login="alice",
    )
    assert res.owners == frozenset({2})
    assert res.winner == 2
    assert res.substrate == "comment"
    assert res.claimed is True


def test_handoff_transfers_ownership(io) -> None:
    comments = [
        _comment(io, event="claim", instance=2, author="alice"),
        _comment(io, event="handoff", instance=2, to=3, author="alice"),
    ]
    res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice")
    assert res.owners == frozenset({3})


def test_abandon_and_release_return_to_commons(io) -> None:
    for terminal in ("abandon", "release"):
        comments = [
            _comment(io, event="claim", instance=2, author="alice"),
            _comment(io, event=terminal, instance=2, author="alice"),
        ]
        res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice")
        assert not res.claimed, f"{terminal} should return the issue to commons"
        assert res.winner is None


def test_same_instant_clash_lowest_wins(io) -> None:
    """Two clones claim at the same instant — both markers coexist (comment-create
    is atomic), and the winner is the lowest instance number (DEC-035 D6)."""
    comments = [
        _comment(io, event="claim", instance=3, author="alice"),
        _comment(io, event="claim", instance=2, author="alice"),
    ]
    res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice")
    assert res.owners == frozenset({2, 3})
    assert res.winner == 2  # lowest wins; instance 3 backs off


# ---- authenticity --------------------------------------------------------


def test_forged_marker_from_another_account_is_ignored(io) -> None:
    """A stamped comment authored by someone other than the issue assignee is a
    forgery and does not count (ADR-041 §1 / DEC-043 D3)."""
    comments = [_comment(io, event="claim", instance=9, author="mallory")]
    res = io.resolve_owner(comments=comments, labels=[], assignee_login="alice")
    assert not res.claimed


def test_no_assignee_means_no_authentic_marker(io) -> None:
    comments = [_comment(io, event="claim", instance=2, author="alice")]
    res = io.resolve_owner(comments=comments, labels=[], assignee_login=None)
    assert not res.claimed


# ---- mixed-mode: comment-log-wins ---------------------------------------


def test_comment_log_wins_over_lingering_label(io) -> None:
    """A repo forward-switched label→comment may hold both; the comment-log owner
    is authoritative, the lingering `instance:N` label is residual (ADR-041 §2)."""
    comments = [_comment(io, event="claim", instance=2, author="alice")]
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
    args = io.ownership_event_comment_args(issue_number=42, event="claim", instance=2)
    assert args[:4] == ["gh", "issue", "comment", "42"]
    assert args[4] == "--body"
    assert "<!-- pkit:audit v=1 event=claim instance=2 " in args[5]
    assert "instance 2" in args[5]  # visible human text, so the comment isn't blank


def test_event_comment_refuses_unknown_event(io) -> None:
    with pytest.raises(ValueError):
        io.format_event_comment(event="frobnicate", instance=2)


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


# ---- derived mirror ------------------------------------------------------


def test_mirror_region_reflects_owner(io) -> None:
    res = io.resolve_owner(
        comments=[_comment(io, event="claim", instance=2, author="alice")],
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
        comments=[_comment(io, event="claim", instance=2, author="alice")],
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
            _comment(io, event="claim", instance=2, author="alice"),
            _comment(io, event="handoff", instance=2, to=3, author="alice"),
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


# ========================================================================
# Half (b) — the guard: the stamp is built ONLY in the seam
# ========================================================================


def _scanned_scripts() -> list[Path]:
    return [
        p
        for p in sorted(SCRIPTS.rglob("*.py"))
        if p not in (SEAM_MODULE, BUILDER_MODULE) and "__pycache__" not in p.parts
    ]


@pytest.mark.parametrize("path", _scanned_scripts(), ids=lambda p: str(p.relative_to(SCRIPTS)))
def test_no_script_embeds_the_ownership_stamp_inline(path: Path) -> None:
    """No pm script embeds the `pkit:instance-owner` literal except the seam,
    whose mirror region carries it, and the audit-log facility, which reads the
    old stamps (ADR-041 §3 part b). Every ownership-event / mirror write is
    constructed there; a script that hard-codes the stamp bypasses them."""
    src = path.read_text(encoding="utf-8")
    assert STAMP_SIGNATURE not in src, (
        f"{path.name} embeds the ownership stamp `{STAMP_SIGNATURE}` inline — "
        "construct ownership writes only via _lib.instance_ownership "
        "(ownership_event_comment_args / render_mirror_region)."
    )


def test_seam_and_builder_are_where_the_signature_lives() -> None:
    """The seam's mirror and the facility's reader of the old stamp hold the
    signature — pins that they live there (the guard above excludes them by name)."""
    assert STAMP_SIGNATURE in SEAM_MODULE.read_text(encoding="utf-8")
    assert STAMP_SIGNATURE in BUILDER_MODULE.read_text(encoding="utf-8")
