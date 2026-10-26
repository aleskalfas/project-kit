"""The audit-log facility's builder and parser (DEC-044, ADR-041 point 3, ADR-071 point 5).

`_lib/audit_log` builds every event comment of the ownership seam and of the
state-issue seam, and parses a comment back into its event. These tests pin the
stamp's grammar, that no value can end the stamp, the id each act carries, the
frame of DEC-052, and that the stamps written before the facility still read.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import audit_log  # noqa: E402
from _lib.provenance import Versions  # noqa: E402

VERSIONS = Versions(tree="1.2.3", capability="0.9.0", cli="1.2.3")


def test_an_event_round_trips_through_its_comment() -> None:
    ev = audit_log.event("state-claim", key="planner", clone="k1", place="mac:/work/repo")
    parsed = audit_log.parse(audit_log.build(ev, versions=VERSIONS))
    assert parsed is not None and parsed == ev
    assert parsed.family == audit_log.STATE_ISSUE


@pytest.mark.parametrize(
    "value",
    ["a b", "x>y", "end -->", "a--b", "a---b", "100%", "tab\there", "naïve", "", "-"],
)
def test_no_value_can_end_the_stamp(value: str) -> None:
    ev = audit_log.event(
        "state-force-release", key="planner", clone="k", place="p", reason=value or "r"
    )
    stamp = audit_log.stamp(ev)
    inner = stamp[len("<!--") : -len("-->")]
    assert "-->" not in inner and "--" not in inner and ">" not in inner
    assert audit_log.parse(stamp) == ev


def test_every_act_carries_an_id_of_its_own() -> None:
    first = audit_log.event("state-release", key="k", clone="c", place="p")
    second = audit_log.event("state-release", key="k", clone="c", place="p")
    assert first.act and second.act and first.act != second.act
    kept = audit_log.event("state-release", key="k", clone="c", place="p", id=first.act)
    assert kept.act == first.act


def test_a_retry_finds_its_own_act_and_a_second_act_does_not() -> None:
    ev = audit_log.event("state-claim", key="k", clone="c", place="p")
    again = audit_log.event("state-claim", key="k", clone="c", place="p")
    assert ev.act is not None and again.act is not None
    bodies = ["hello", audit_log.build(ev)]
    assert audit_log.posted(bodies, ev.act)
    assert not audit_log.posted(bodies, again.act)


def test_the_comment_wears_the_frame_of_its_kind() -> None:
    ev = audit_log.event("claim", instance=2, seat="worker", seat_number=3, clone="abc")
    body = audit_log.build(ev, versions=VERSIONS)
    lines = body.splitlines()
    assert lines[0].startswith("🔖 claim — instance 2")
    assert "<!-- pkit-claim -->" in lines
    assert lines[-1] == "<sub>🧰 pkit · tree `1.2.3` · pm `0.9.0` · cli `1.2.3`</sub>"


def test_a_reason_stands_on_its_own_paragraph() -> None:
    ev = audit_log.event(
        "state-force-release", key="planner", clone="k", place="p", reason="the clone died"
    )
    assert audit_log.render(ev).split("\n\n")[1] == "Reason: the clone died"


def test_an_event_refuses_an_unknown_type_or_field_or_a_missing_one() -> None:
    with pytest.raises(ValueError):
        audit_log.event("frobnicate")
    with pytest.raises(ValueError):
        audit_log.event("claim", instance=1, colour="red")
    with pytest.raises(ValueError):
        audit_log.event("state-claim", key="k", clone="c")
    with pytest.raises(ValueError):
        audit_log.event("state-force-release", key="k", clone="c", place="p")


def test_the_old_ownership_stamp_still_reads() -> None:
    old = (
        "**🔖 Claimed** — instance 2\n"
        "<!-- pkit:instance-owner v=1 event=handoff instance=2 to=3 "
        "ts=2026-07-07T12:00:00+00:00 -->"
    )
    ev = audit_log.parse(old)
    assert ev is not None and ev.legacy
    assert (ev.type, ev.get("instance"), ev.get("to")) == ("handoff", "2", "3")


def test_a_stamp_quoted_in_a_code_block_records_nothing() -> None:
    stamp = audit_log.stamp(audit_log.event("state-claim", key="k", clone="c", place="p"))
    assert audit_log.parse(f"```\n{stamp}\n```\n") is None
    assert audit_log.parse(f"see {stamp} here") is None


@pytest.mark.parametrize("version", ["²", "٣", "9" * 5000])
def test_no_version_a_comment_writes_makes_the_parser_fail(version: str) -> None:
    assert audit_log.parse(f"<!-- pkit:audit v={version} event=claim instance=1 -->") is None
    legacy = f"<!-- pkit:instance-owner v=1 event=claim instance={version} ts=x -->"
    assert audit_log.parse(legacy) is None


def test_a_field_cannot_put_a_stamp_ahead_of_the_comments_own() -> None:
    planted = audit_log.stamp(audit_log.event("state-claim", key="k", clone="evil", place="p"))
    for reason in (f"r\n{planted}", planted):
        ev = audit_log.event(
            "state-force-release", key="k", clone="c", place=f"x\n{planted}", reason=reason
        )
        assert audit_log.parse(audit_log.build(ev)) == ev


def test_a_later_version_of_the_stamp_reads_as_nothing() -> None:
    assert audit_log.parse("<!-- pkit:audit v=2 event=claim instance=1 id=x -->") is None


def test_the_families_name_each_seams_types() -> None:
    assert audit_log.OWNERSHIP_EVENTS == ("claim", "handoff", "abandon", "release")
    assert audit_log.STATE_EVENTS == ("state-claim", "state-release", "state-force-release")


def test_the_facility_agrees_with_its_schema() -> None:
    """`audit-log.yaml` declares the stamp and the event types; the builder
    and the parser hold to it."""
    from ruamel.yaml import YAML

    schema = YAML(typ="safe").load(
        (SCRIPTS.parent / "schemas" / "audit-log.yaml").read_text(encoding="utf-8")
    )
    assert schema["stamp"]["prefix"] == audit_log.STAMP_PREFIX
    assert schema["stamp"]["version"] == audit_log.STAMP_VERSION
    assert schema["stamp"]["act_field"] == "id"
    assert [x["prefix"] for x in schema["stamp"]["legacy"]] == [audit_log.LEGACY_OWNERSHIP_PREFIX]
    declared = {
        name: (entry["family"], tuple(entry["fields"]), tuple(entry["required"]))
        for name, entry in schema["events"].items()
    }
    built = {name: (t.family, t.fields, t.required) for name, t in audit_log.EVENT_TYPES.items()}
    assert declared == built
