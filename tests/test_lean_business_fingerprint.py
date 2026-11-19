"""lean-business's canonical form and the fingerprints taken over it (DEC-002 point 13):
form 1's text, what each kind covers, and how a kept fingerprint is checked."""

from __future__ import annotations

import hashlib
import math
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load

(fingerprint, reading) = load("lean-business", "fingerprint", "reading")

SCHEMAS = Path(__file__).resolve().parent.parent / ".pkit/capabilities/lean-business/schemas"
IDEA = Path(__file__).resolve().parent / "fixtures/lean-business/repo/lean-business/meal-plan"

GOAL = {"revenue": {"amount": 1000000, "per": "year"}, "years": 3, "by": "A. Founder"}


def canvas(**boxes: Any) -> dict[str, Any]:
    return {
        "id": "idea.direct",
        "archetype": "direct",
        "boxes": {
            name: [{"id": f"idea.direct.{name}", "text": text}] for name, text in boxes.items()
        },
        "viability": [{"price": {"amount": 8, "per": "month"}, "conversion": 0.05}],
        "traction": {"multiplier": 10, "first-stage": {"metric": "revenue", "target": 50}},
    }


# --- the text -----------------------------------------------------------------------------------


def test_the_text_sorts_keys_and_leaves_no_space() -> None:
    assert fingerprint.canonical_text({"b": 1, "a": [1, "x"]}) == '{"a":[1,"x"],"b":1}'


def test_a_whole_number_is_an_integer_and_another_its_shortest_form() -> None:
    assert fingerprint.canonical_text([2.0, 0.1, 3]) == "[2,0.1,3]"


def test_a_key_whose_value_is_empty_counts_as_no_key() -> None:
    sparse = {"a": 1, "b": None, "c": [], "d": {}, "e": {"f": None}}
    assert fingerprint.canonical_text(sparse) == fingerprint.canonical_text({"a": 1})


def test_a_string_keeps_its_characters_and_a_day_its_iso_text() -> None:
    assert fingerprint.canonical_text({"t": 'Kč "x"'}) == '{"t":"Kč \\"x\\""}'
    assert fingerprint.canonical_text({"d": date(2026, 11, 19)}) == '{"d":"2026-11-19"}'


@pytest.mark.parametrize("number", [math.inf, -math.inf, math.nan])
def test_a_number_that_is_not_finite_has_no_text(number: float) -> None:
    with pytest.raises(fingerprint.FingerprintError):
        fingerprint.canonical_text({"x": number})


def test_the_digest_is_the_sha256_of_the_text_as_utf_8() -> None:
    taken = fingerprint.take({"b": "č", "a": 1})
    text = '{"a":1,"b":"č"}'
    assert taken == fingerprint.Fingerprint(1, hashlib.sha256(text.encode("utf-8")).hexdigest())
    assert taken.as_data() == {"form": 1, "sha256": taken.sha256}


def test_layout_order_and_quoting_make_nothing_stale() -> None:
    one = reading.load_yaml('b: "x"\na:\n  - 1\n')
    other = reading.load_yaml("# a comment\na: [1]\nb: x\n")
    assert fingerprint.take(one) == fingerprint.take(other)


def test_a_form_this_version_does_not_know_is_refused() -> None:
    with pytest.raises(fingerprint.FingerprintError):
        fingerprint.take({}, form=2)


# --- what each kind covers ----------------------------------------------------------------------


def test_desirability_covers_its_boxes_and_not_the_goal_or_pricing() -> None:
    base = canvas(problem="Too long")
    taken = fingerprint.of_verdict("desirability", base, GOAL)
    priced = canvas(problem="Too long", **{"revenue-streams": "A subscription"})
    assert fingerprint.of_verdict("desirability", priced, {"years": 9}) == taken
    assert fingerprint.of_verdict("desirability", canvas(problem="Too dear"), GOAL) != taken


def test_viability_covers_the_revenue_streams_the_inputs_and_the_goal() -> None:
    base = canvas(**{"revenue-streams": "A subscription"})
    taken = fingerprint.of_verdict("viability", base, GOAL)
    assert fingerprint.of_verdict("viability", canvas(**{"revenue-streams": "Ads"}), GOAL) != taken
    assert fingerprint.of_verdict("viability", base, {**GOAL, "years": 5}) != taken
    cheaper = {**base, "viability": [{"price": {"amount": 4, "per": "month"}}]}
    assert fingerprint.of_verdict("viability", cheaper, GOAL) != taken
    worded = {**base, "boxes": {**base["boxes"], "problem": [{"id": "idea.direct.p", "text": "x"}]}}
    assert fingerprint.of_verdict("viability", worded, GOAL) == taken


def test_feasibility_covers_the_traction_target_and_the_goal() -> None:
    base = canvas(problem="Too long")
    taken = fingerprint.of_verdict("feasibility", base, GOAL)
    assert fingerprint.of_verdict("feasibility", canvas(problem="Other"), GOAL) == taken
    nearer = {**base, "traction": {"first-stage": {"metric": "revenue", "target": 20}}}
    assert fingerprint.of_verdict("feasibility", nearer, GOAL) != taken
    assert fingerprint.of_verdict("feasibility", base, {**GOAL, "years": 5}) != taken


def test_the_goal_counts_by_its_content_never_who_set_it_or_when() -> None:
    base = canvas()
    taken = fingerprint.of_verdict("viability", base, GOAL)
    reset = {**GOAL, "by": "B. Partner", "when": "2027-01-01"}
    assert fingerprint.of_verdict("viability", base, reset) == taken


def test_a_kind_names_what_it_covers_so_one_never_stands_for_another() -> None:
    empty: dict[str, Any] = {}
    taken = {fingerprint.of_verdict(step, empty, None) for step in fingerprint.STEPS}
    taken |= {fingerprint.of_shortlisting(empty, None), fingerprint.of_plan(empty)}
    taken.add(fingerprint.of_declaration(empty))
    assert len(taken) == 6


def test_a_shortlisting_covers_every_box_and_not_the_verdicts_kept_beside_it() -> None:
    base = canvas(**{"cost-structure": "Hosting"})
    taken = fingerprint.of_shortlisting(base, GOAL)
    judged = {**base, "verdicts": {"desirability": {"answer": "yes"}}, "outcome": {"kind": "x"}}
    assert fingerprint.of_shortlisting(judged, GOAL) == taken
    assert fingerprint.of_shortlisting(canvas(**{"cost-structure": "None"}), GOAL) != taken


def test_a_declaration_covers_its_fields_but_its_binding_and_what_comes_after() -> None:
    declared = {"id": "idea.one", "kind": "generative", "learn": "Whether", "start": "2026-12-01"}
    taken = fingerprint.of_declaration(declared)
    recorded = {
        **declared,
        "pkit_schema": "lean-business:experiment",
        "schema_version": 1,
        "stopped": {"by": "A"},
        "result": {"measured": 3},
        "decision": {"next": "stop"},
    }
    assert fingerprint.of_declaration(recorded) == taken
    assert fingerprint.of_declaration({**declared, "start": "2026-12-02"}) != taken


def test_a_declaration_covers_its_record_but_its_own_fingerprint() -> None:
    rested = {"fingerprint": {"form": 1, "sha256": "a" * 64}, "when": "2026-11-20"}
    record = {"by": "A", "when": "2026-11-30", "rested-on": rested}
    declared = {"id": "idea.one", "kind": "generative", "declared": record}
    taken = fingerprint.of_declaration(declared)
    kept = {**record, "fingerprint": taken.as_data()}
    assert fingerprint.of_declaration({**declared, "declared": kept}) == taken
    for changed in (
        {**record, "when": "2026-11-29"},
        {**record, "by": "B"},
        {**record, "rested-on": {**rested, "when": "2026-11-21"}},
    ):
        assert fingerprint.of_declaration({**declared, "declared": changed}) != taken


def test_a_traction_target_that_leaves_its_multiplier_out_counts_ten() -> None:
    stage = {"first-stage": {"metric": "revenue", "target": 50}}
    left_out = {**canvas(), "traction": stage}
    written = {**canvas(), "traction": {**stage, "multiplier": 10}}
    assert fingerprint.of_verdict("feasibility", left_out, GOAL) == fingerprint.of_verdict(
        "feasibility", written, GOAL
    )
    assert fingerprint.of_shortlisting(left_out, GOAL) == fingerprint.of_shortlisting(written, GOAL)
    other = {**canvas(), "traction": {**stage, "multiplier": 5}}
    assert fingerprint.of_shortlisting(other, GOAL) != fingerprint.of_shortlisting(written, GOAL)


def test_a_plan_never_covers_its_suspensions_or_its_review() -> None:
    plan = {"window": {"start": "2026-12-01", "days": 90}, "variants": ["[canvas:idea.direct]"]}
    taken = fingerprint.of_plan(plan)
    lived = {**plan, "suspensions": [{"first-day": "2026-12-10"}], "review": {"decision": "pause"}}
    assert fingerprint.of_plan({**lived, "planned": {"by": "A"}}) == taken
    assert fingerprint.of_plan({**plan, "window": {"start": "2026-12-01", "days": 60}}) != taken


def test_a_step_the_method_does_not_judge_is_refused() -> None:
    with pytest.raises(fingerprint.FingerprintError):
        fingerprint.of_verdict("fun", {}, None)


# --- checking a fingerprint kept ----------------------------------------------------------------


def test_compare_finds_a_match_a_difference_an_unknown_form_and_no_fingerprint() -> None:
    data = {"a": 1}
    kept = fingerprint.take(data).as_data()
    assert fingerprint.compare(kept, lambda form: fingerprint.take(data, form)) == "matches"
    assert fingerprint.compare(kept, lambda form: fingerprint.take({"a": 2}, form)) == "differs"
    later = {**kept, "form": 2}
    assert fingerprint.compare(later, lambda form: fingerprint.take(data, form)) == "unknown-form"
    for stored in (
        None,
        {"form": 1},
        {"form": True, "sha256": kept["sha256"]},
        {"form": 1, "sha256": "x"},
    ):
        assert (
            fingerprint.compare(stored, lambda form: fingerprint.take(data, form)) == "unreadable"
        )


def test_a_check_tells_fresh_from_stale_and_names_what_has_no_text() -> None:
    plan = {"window": {"start": "2026-12-01", "days": 90}}
    kept = {**plan, "planned": {"fingerprint": fingerprint.of_plan(plan).as_data()}}
    assert fingerprint.check_plan(kept).fresh
    changed = {**kept, "window": {"start": "2026-12-01", "days": 60}}
    assert fingerprint.check_plan(changed).stale
    later = {**kept, "planned": {"fingerprint": {"form": 2, "sha256": "a" * 64}}}
    checked = fingerprint.check_plan(later)
    assert (checked.outcome, checked.form, checked.fresh, checked.stale) == (
        "unknown-form",
        2,
        False,
        False,
    )
    endless = fingerprint.check_plan({**kept, "window": {"days": math.inf}})
    assert endless.outcome == fingerprint.NO_TEXT and endless.why


def test_each_kind_is_checked_against_what_it_covers() -> None:
    base = canvas(**{"revenue-streams": "A subscription"})
    judged = {
        **base,
        "verdicts": {
            step: {"fingerprint": fingerprint.of_verdict(step, base, GOAL).as_data()}
            for step in fingerprint.STEPS
        },
        "outcome": {"fingerprint": fingerprint.of_shortlisting(base, GOAL).as_data()},
    }
    assert all(fingerprint.check_verdict(s, judged, GOAL).fresh for s in fingerprint.STEPS)
    assert fingerprint.check_shortlisting(judged, GOAL).fresh
    assert fingerprint.check_shortlisting(judged, {**GOAL, "years": 4}).stale
    record: dict[str, Any] = {"by": "A"}
    declared: dict[str, Any] = {"id": "idea.one", "kind": "generative", "declared": record}
    record["fingerprint"] = fingerprint.of_declaration(declared).as_data()
    assert fingerprint.check_declaration(declared).fresh
    assert fingerprint.check_declaration({**declared, "kind": "evaluative"}).stale


def test_a_shortlisting_is_read_with_the_day_it_was_recorded() -> None:
    taken = fingerprint.take({"a": 1})
    outcome = {"kind": "shortlisted", "fingerprint": taken.as_data(), "when": "2026-10-08"}
    standing = fingerprint.shortlisting({"outcome": outcome})
    assert standing == fingerprint.Shortlisting(taken, date(2026, 10, 8))
    assert standing.as_data() == {"fingerprint": taken.as_data(), "when": "2026-10-08"}
    assert fingerprint.rested_on(standing.as_data()) == standing
    # Given again on an unchanged canvas, it keeps its fingerprint and is another.
    again = fingerprint.shortlisting({"outcome": {**outcome, "when": "2026-11-15"}})
    assert again is not None and again.fingerprint == standing.fingerprint and again != standing


@pytest.mark.parametrize(
    "outcome",
    [
        {"kind": "shelved", "when": "2026-10-08"},
        {"kind": "shortlisted", "when": "2026-10-08"},
        {"kind": "shortlisted", "fingerprint": {"form": 1, "sha256": "a" * 64}, "when": "soon"},
    ],
    ids=["not-shortlisted", "no-fingerprint", "no-day"],
)
def test_no_shortlisting_is_read_where_none_reads_whole(outcome: dict[str, Any]) -> None:
    assert fingerprint.shortlisting({"outcome": outcome}) is None
    assert fingerprint.rested_on(outcome) is None


def test_the_reference_cycle_keeps_the_fingerprint_its_plan_takes() -> None:
    cycle = reading.read_yaml(SCHEMAS / "cycle.yaml")
    kept = cycle["planned"]["fingerprint"]
    assert fingerprint.compare(kept, lambda form: fingerprint.of_plan(cycle, form)) == "matches"


def test_the_fixture_keeps_the_fingerprints_its_judgements_take() -> None:
    goal = reading.read_yaml(IDEA / "goal.yaml")
    direct = reading.read_yaml(IDEA / "variants/direct/canvas.yaml")
    for step in fingerprint.STEPS:
        kept = direct["verdicts"][step]["fingerprint"]
        assert fingerprint.read(kept) == fingerprint.of_verdict(step, direct, goal)
    assert fingerprint.read(direct["outcome"]["fingerprint"]) == fingerprint.of_shortlisting(
        direct, goal
    )
    standing = fingerprint.shortlisting(direct)
    for path in sorted(IDEA.glob("experiments/*.yaml")):
        experiment = reading.read_yaml(path)
        assert fingerprint.check_declaration(experiment).fresh
        assert fingerprint.rested_on(experiment["declared"]["rested-on"]) == standing
    assert fingerprint.check_plan(reading.read_yaml(IDEA / "cycles/first.yaml")).fresh
