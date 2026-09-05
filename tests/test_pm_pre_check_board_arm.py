"""pre-check's checks for the `board:` binding arm (project-management:DEC-051).

The substrate map gained a `board: true` arm so a brownfield adopter can declare
that an axis is carried by a field on their Projects-v2 board. Until it existed,
pre-check's own remediation told adopters to spell that `unsupported: true` — a
declaration the schema defines as the axis having NO encoding, with every rule
needing it degrading. These pin the three checks the arm brings with it, plus the
corrected guidance:

  * **hard** — `board: true` with no configured board is UNSATISFIABLE and fails.
    Explicitly a `fail`, and explicitly NOT covered by the softening DEC-051
    decision point 5 applies to the neighbouring double-claim refusal.
  * **advisory** — a board-declarable axis ABSENT from a PRESENT map under a
    configured board is reported, never failed: decision point 3 keeps that
    axis's carriage exactly as today and buys the cleanliness with a diagnostic
    instead of a semantics change.
  * **warning** — a `default:` on a `board:` arm with no `set-board-field` hook
    behind it is a value nothing writes. The claim is bounded by what a hook
    actually declares (an opaque `field_id`, never an axis), so an existing hook
    yields "unverified", not a false all-clear.

Pure: no `gh`, no network. Every check reads only the already-loaded config
mapping, the parsed substrate-map, and (for the `default:` check) hooks.yaml off
a tmp_path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
SCRIPT = SCRIPTS_DIR / "pre-check.py"


@pytest.fixture(scope="module")
def pc():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_pre_check_board_arm", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_pre_check_board_arm"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def axis_labels():
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _lib import axis_labels as mod

    yield mod


BOARD_CONFIG = {
    "schema_version": 1,
    "default_branch": "main",
    "workstreams": ["cli"],
    "has_projects_v2_board": True,
    "projects_v2_board_id": 2,
}

NO_BOARD_CONFIG = {
    "schema_version": 1,
    "default_branch": "main",
    "workstreams": ["cli"],
    "has_projects_v2_board": False,
}


def _map(axis_labels, axes):
    return axis_labels.SubstrateMap(axes=axes)


def _write_hooks(cap_root: Path, body: str) -> Path:
    (cap_root / "project").mkdir(parents=True, exist_ok=True)
    (cap_root / "project" / "hooks.yaml").write_text(body, encoding="utf-8")
    return cap_root


# =========================================================================
# The admissibility sets
# =========================================================================


def test_board_declarable_axes_match_the_schema(pc) -> None:
    """The arm is admissible on `priority` and `workstream` ONLY — `type` and
    `state` carry a `not: {required: [board]}` in the schema. pre-check's tuple
    has to agree with the schema, or it recommends a map `pkit schemas validate`
    rejects."""
    schema = json.loads(
        (
            REPO_ROOT
            / ".pkit"
            / "capabilities"
            / "project-management"
            / "schemas"
            / "substrate-map.schema.json"
        ).read_text(encoding="utf-8")
    )
    axis_props = schema["properties"]["axes"]["properties"]
    refused = {
        axis for axis, spec in axis_props.items()
        if spec.get("not", {}).get("required") == ["board"]
    }
    admitted = set(axis_props) - refused
    assert set(pc.BOARD_DECLARABLE_AXES) == admitted == {"priority", "workstream"}


def test_board_declarable_is_a_strict_subset_of_board_claimed(pc) -> None:
    """`state` is board-CLAIMED by the flag today but not board-DECLARABLE in the
    map. Collapsing the two tuples would produce a remediation telling a `state`
    adopter to write a binding the schema refuses."""
    assert set(pc.BOARD_DECLARABLE_AXES) < set(pc.BOARD_CLAIMED_AXES)
    assert "state" in pc.BOARD_CLAIMED_AXES
    assert "state" not in pc.BOARD_DECLARABLE_AXES


# =========================================================================
# HARD: `board: true` with no configured board
# =========================================================================


def test_board_arm_without_a_board_fails(pc, axis_labels) -> None:
    """The pair is unsatisfiable: the map says the value lives on a board field,
    the config says there is no board. Nothing carries the axis."""
    sm = _map(axis_labels, {"priority": {"board": True}})
    results = pc._check_substrate_board_arm_satisfiable(NO_BOARD_CONFIG, sm)
    fails = [r for r in results if r.status == "fail"]
    assert len(fails) == 1
    assert "priority" in fails[0].label
    assert "UNSATISFIABLE" in fails[0].detail


def test_board_arm_failure_is_a_fail_not_a_warn(pc, axis_labels) -> None:
    """DEC-051 decision point 2 makes this refusal NEW and hard, and decision
    point 2 says in as many words that it must not inherit decision point 5's
    softening of the neighbouring double-claim refusal. A later softening pass
    over this file must leave it alone — hence this test, which fails loudly if
    the status is relaxed."""
    sm = _map(axis_labels, {"workstream": {"board": True}})
    results = pc._check_substrate_board_arm_satisfiable(NO_BOARD_CONFIG, sm)
    assert any(r.status == "fail" for r in results)
    assert not any(r.status == "warn" for r in results)


def test_board_arm_failure_is_per_axis(pc, axis_labels) -> None:
    sm = _map(
        axis_labels, {"priority": {"board": True}, "workstream": {"board": True}}
    )
    fails = [
        r
        for r in pc._check_substrate_board_arm_satisfiable(NO_BOARD_CONFIG, sm)
        if r.status == "fail"
    ]
    assert len(fails) == 2
    assert {"priority", "workstream"} == {
        axis for axis in ("priority", "workstream")
        for r in fails if axis in r.label
    }


def test_board_arm_failure_remediation_offers_both_exits(pc, axis_labels) -> None:
    """Actionable on its own: configure the board, or bind the axis to what
    actually carries it. And it must NOT sell `unsupported: true` as the way to
    spell board carriage — that is the withdrawn instruction."""
    sm = _map(axis_labels, {"priority": {"board": True}})
    fail = next(
        r
        for r in pc._check_substrate_board_arm_satisfiable(NO_BOARD_CONFIG, sm)
        if r.status == "fail"
    )
    assert fail.remediation is not None
    assert "has_projects_v2_board: true" in fail.remediation
    assert "set-board-field" in fail.remediation
    assert "label:" in fail.remediation
    # `unsupported` is named, but as what it MEANS, not as a board spelling.
    assert "no encoding" in fail.remediation.lower()


def test_board_arm_with_a_board_is_ok(pc, axis_labels) -> None:
    """The satisfiable pair: the map declares the board and the config configures
    one. No finding beyond the confirmation."""
    sm = _map(axis_labels, {"priority": {"board": True}})
    results = pc._check_substrate_board_arm_satisfiable(BOARD_CONFIG, sm)
    assert all(r.status != "fail" for r in results)
    assert any(r.status == "ok" for r in results)


def test_no_board_arm_declared_is_a_skip(pc, axis_labels) -> None:
    """A map with no `board:` arm anywhere cannot trip the check — including a
    board-less project, which is the common case and must stay clean."""
    sm = _map(
        axis_labels,
        {
            "priority": {"label": {"remap": {"High": "P0"}}},
            "workstream": {"unsupported": True},
        },
    )
    for config in (NO_BOARD_CONFIG, BOARD_CONFIG):
        results = pc._check_substrate_board_arm_satisfiable(config, sm)
        assert all(r.status != "fail" for r in results)
        assert all(r.status == "skip" for r in results)


def test_unreadable_config_does_not_manufacture_a_failure(pc, axis_labels) -> None:
    """A config that failed to load says nothing about whether a board exists —
    the config check already reported the read failure. Guessing `fail` here would
    report a second, invented problem."""
    sm = _map(axis_labels, {"priority": {"board": True}})
    results = pc._check_substrate_board_arm_satisfiable(None, sm)
    assert all(r.status != "fail" for r in results)


def test_board_arm_on_state_is_not_read_as_declared(pc, axis_labels) -> None:
    """`state` cannot carry the arm (the schema refuses it), so a hand-written
    `state: {board: true}` is a map `pkit schemas validate` rejects. pre-check
    must not treat it as a declaration and must not fail on it either — the
    schema validator owns that refusal, and duplicating it here would double-
    report one error."""
    sm = _map(axis_labels, {"state": {"board": True}})
    results = pc._check_substrate_board_arm_satisfiable(NO_BOARD_CONFIG, sm)
    assert all(r.status != "fail" for r in results)


# =========================================================================
# ADVISORY: the absent-axis nudge
# =========================================================================


def test_absent_board_claimable_axis_is_reported_under_a_board(pc, axis_labels) -> None:
    """DEC-051 decision point 3: an axis the map does not name keeps today's
    carriage — under a configured board, the board carries it. That is reported,
    with the one-line edit that makes it explicit."""
    sm = _map(axis_labels, {"type": {"title-prefix": {"remap": {"task": "[Task]"}}}})
    results = pc._check_board_axis_absent_from_map(BOARD_CONFIG, sm)
    labels = [r.label for r in results]
    assert len(results) == 2
    assert any("priority" in lbl for lbl in labels)
    assert any("workstream" in lbl for lbl in labels)
    assert all("board: true" in r.detail for r in results)


def test_absent_axis_nudge_never_fails(pc, axis_labels) -> None:
    """Informational, deliberately. Making a present map authoritative was
    REJECTED as a silent behaviour change by upgrade; the cleanliness is bought
    with this diagnostic INSTEAD of semantics, so it must not gate."""
    sm = _map(axis_labels, {"type": {"title-prefix": {"remap": {"task": "[Task]"}}}})
    results = pc._check_board_axis_absent_from_map(BOARD_CONFIG, sm)
    assert results
    assert all(r.status == "skip" for r in results)
    assert not any(r.status in ("fail", "warn") for r in results)


def test_absent_axis_nudge_silent_without_a_board(pc, axis_labels) -> None:
    """With no board configured, an absent axis is degrading rather than
    board-carried — nudging toward `board: true` would point at the very pair the
    hard check refuses."""
    sm = _map(axis_labels, {"type": {"title-prefix": {"remap": {"task": "[Task]"}}}})
    assert pc._check_board_axis_absent_from_map(NO_BOARD_CONFIG, sm) == []


def test_absent_axis_nudge_silent_for_a_declared_axis(pc, axis_labels) -> None:
    """An axis the map DOES name — bound, or explicitly `unsupported` — is a
    declaration, not an oversight. Re-reading it as one is the overreach decision
    point 3 rejects."""
    sm = _map(
        axis_labels,
        {
            "priority": {"label": {"remap": {"High": "P0"}}},
            "workstream": {"unsupported": True},
        },
    )
    assert pc._check_board_axis_absent_from_map(BOARD_CONFIG, sm) == []


def test_absent_axis_nudge_silent_for_an_already_declared_board_arm(
    pc, axis_labels
) -> None:
    """The destination state: both axes declared `board: true`. Nothing left to
    nudge."""
    sm = _map(
        axis_labels, {"priority": {"board": True}, "workstream": {"board": True}}
    )
    assert pc._check_board_axis_absent_from_map(BOARD_CONFIG, sm) == []


def test_absent_axis_nudge_needs_a_present_map(pc, axis_labels, tmp_path) -> None:
    """A project with NO substrate-map gets nothing. Greenfield has nothing to
    declare, and the check is wired inside pre-check's present-map block — this
    pins that wiring, not just the function."""
    cap_root = tmp_path / "cap"
    (cap_root / "project").mkdir(parents=True)
    assert axis_labels.load_substrate_map(cap_root) is None
    source = SCRIPT.read_text(encoding="utf-8")
    block = source.split("substrate_map = axis_labels.load_substrate_map", 1)[1]
    guarded = block.split("if substrate_map is not None:", 1)[1]
    guarded = guarded.split("\n    # 3b.", 1)[0]
    assert "_check_board_axis_absent_from_map" in guarded


def test_state_is_never_nudged(pc, axis_labels) -> None:
    """`state` is board-claimed by the flag but not board-declarable, so nudging
    it would recommend a binding the schema refuses."""
    sm = _map(axis_labels, {"priority": {"board": True}, "workstream": {"board": True}})
    results = pc._check_board_axis_absent_from_map(BOARD_CONFIG, sm)
    assert not any("state" in r.label for r in results)


# =========================================================================
# WARNING: a `board:` arm's `default:` with no hook behind it
# =========================================================================

_BOARD_DEFAULT_MAP_AXES = {"priority": {"board": True, "default": "P1"}}

_HOOKS_WITH_CREATE_BOARD_FIELD = """\
schema_version: 1
hooks:
  after_create_issue:
    - kind: set-board-field
      field_id: PVTSSF_x
      single_select_option_id: opt-1
"""

_HOOKS_WITH_OTHER_EVENT_ONLY = """\
schema_version: 1
hooks:
  after_move_issue:
    - kind: set-board-field
      field_id: PVTSSF_x
      single_select_option_id: opt-1
"""

_HOOKS_WITHOUT_BOARD_FIELD = """\
schema_version: 1
hooks:
  after_create_issue:
    - kind: post-comment
      template_path: project/templates/welcome.md
"""


def test_default_with_no_hook_at_all_warns(pc, axis_labels, tmp_path) -> None:
    """The exact claim: no `set-board-field` hook exists, so nothing writes the
    board field the `default:` describes."""
    cap_root = _write_hooks(tmp_path / "cap", _HOOKS_WITHOUT_BOARD_FIELD)
    results = pc._check_board_arm_default_has_hook(
        cap_root, _map(axis_labels, _BOARD_DEFAULT_MAP_AXES)
    )
    assert len(results) == 1
    assert results[0].status == "warn"
    assert "NO `set-board-field` hook at all" in results[0].detail
    assert results[0].remediation is not None
    assert "after_create_issue" in results[0].remediation


def test_default_with_no_hooks_file_warns(pc, axis_labels, tmp_path) -> None:
    """An absent hooks.yaml is a legitimate no-hooks state, not a read failure —
    and it means the same thing: nothing writes the field."""
    cap_root = tmp_path / "cap"
    (cap_root / "project").mkdir(parents=True)
    results = pc._check_board_arm_default_has_hook(
        cap_root, _map(axis_labels, _BOARD_DEFAULT_MAP_AXES)
    )
    assert len(results) == 1
    assert results[0].status == "warn"


def test_default_with_hook_on_another_event_warns_narrowly(
    pc, axis_labels, tmp_path
) -> None:
    """A `set-board-field` hook exists, but not at filing time — so a NEW issue
    still gets no value. The message narrows the claim rather than repeating the
    stronger one."""
    cap_root = _write_hooks(tmp_path / "cap", _HOOKS_WITH_OTHER_EVENT_ONLY)
    results = pc._check_board_arm_default_has_hook(
        cap_root, _map(axis_labels, _BOARD_DEFAULT_MAP_AXES)
    )
    assert len(results) == 1
    assert results[0].status == "warn"
    assert "other events" in results[0].detail
    assert "NO `set-board-field` hook at all" not in results[0].detail


def test_default_with_a_create_hook_is_unverified_not_asserted(
    pc, axis_labels, tmp_path
) -> None:
    """A hook declares an opaque `field_id`, never an axis — nothing readable
    offline says WHICH axis a hook serves. So this degrades to "unverified"
    rather than claiming the `default:` is backed (a false all-clear) or claiming
    it is not (a false alarm)."""
    cap_root = _write_hooks(tmp_path / "cap", _HOOKS_WITH_CREATE_BOARD_FIELD)
    results = pc._check_board_arm_default_has_hook(
        cap_root, _map(axis_labels, _BOARD_DEFAULT_MAP_AXES)
    )
    assert len(results) == 1
    assert results[0].status == "skip"
    assert "UNVERIFIED" in results[0].detail
    assert "field_id" in results[0].detail


def test_no_default_on_the_board_arm_is_silent(pc, axis_labels, tmp_path) -> None:
    """The arm without a `default:` claims no seeded value, so there is nothing to
    corroborate."""
    cap_root = _write_hooks(tmp_path / "cap", _HOOKS_WITHOUT_BOARD_FIELD)
    results = pc._check_board_arm_default_has_hook(
        cap_root, _map(axis_labels, {"priority": {"board": True}})
    )
    assert results == []


def test_default_on_a_label_arm_is_not_this_checks_business(
    pc, axis_labels, tmp_path
) -> None:
    """A `default:` on a `label:` binding IS written by the label writer — only
    the `board:` arm delegates the write to a hook."""
    cap_root = _write_hooks(tmp_path / "cap", _HOOKS_WITHOUT_BOARD_FIELD)
    results = pc._check_board_arm_default_has_hook(
        cap_root,
        _map(axis_labels, {"priority": {"label": {"remap": {"High": "P0"}}, "default": "P1"}}),
    )
    assert results == []


def test_default_check_stays_quiet_on_an_unreadable_hooks_file(
    pc, axis_labels, tmp_path
) -> None:
    """`_check_hooks_file` is the check that validates and reports hooks.yaml. A
    second voice reporting the same parse failure would double-count it, so this
    one degrades to a skip that says the correspondence is unknown."""
    cap_root = _write_hooks(tmp_path / "cap", "hooks: [this is not a mapping\n")
    results = pc._check_board_arm_default_has_hook(
        cap_root, _map(axis_labels, _BOARD_DEFAULT_MAP_AXES)
    )
    assert len(results) == 1
    assert results[0].status == "skip"
    assert "could not be read" in results[0].detail


def test_default_check_never_fails(pc, axis_labels, tmp_path) -> None:
    """A missing seed degrades a convenience; it does not make the axis
    unsatisfiable (the value is still settable per-issue). Same posture as the
    DEC-042 contributed-label warn."""
    for body in (
        _HOOKS_WITHOUT_BOARD_FIELD,
        _HOOKS_WITH_OTHER_EVENT_ONLY,
        _HOOKS_WITH_CREATE_BOARD_FIELD,
    ):
        cap_root = _write_hooks(tmp_path / f"cap-{hash(body)}", body)
        results = pc._check_board_arm_default_has_hook(
            cap_root, _map(axis_labels, _BOARD_DEFAULT_MAP_AXES)
        )
        assert all(r.status != "fail" for r in results)


# =========================================================================
# The corrected guidance (the withdrawn `unsupported`-means-board instruction)
# =========================================================================


def test_conflict_remediation_names_the_board_arm(pc, axis_labels) -> None:
    """The one place the withdrawn instruction was actually SHOWN to an adopter.
    It now names `board: true`."""
    sm = _map(axis_labels, {"priority": {"label": {"remap": {"High": "P0"}}}})
    fail = next(
        r
        for r in pc._check_substrate_board_conflict(BOARD_CONFIG, sm)
        if r.status == "fail"
    )
    assert fail.remediation is not None
    assert "board: true" in fail.remediation
    assert "unsupported: true" not in fail.remediation


def test_conflict_remediation_does_not_recommend_board_for_state(pc, axis_labels) -> None:
    """`state` is board-claimed but NOT board-declarable. Telling a `state`
    adopter to write `board: true` would hand them a map `pkit schemas validate`
    rejects, so that arm gets the only honest instruction available: drop the
    binding and let the flag govern (decision point 3)."""
    sm = _map(axis_labels, {"state": {"label": {"remap": {"open": "Open"}}}})
    fail = next(
        r
        for r in pc._check_substrate_board_conflict(BOARD_CONFIG, sm)
        if r.status == "fail"
    )
    assert fail.remediation is not None
    assert "state: { board: true }" not in fail.remediation
    assert "cannot yet declare board carriage" in fail.remediation
    assert "Remove the `label:` binding" in fail.remediation


def test_conflict_docstring_no_longer_calls_unsupported_the_board_shape(pc) -> None:
    """The docstring is read by every future author of this check; leaving the
    withdrawn framing there would reintroduce it. It must not describe an
    `unsupported` axis as agreeing with the writer about board carriage."""
    doc = pc._check_substrate_board_conflict.__doc__
    assert doc is not None
    assert "board: true" in doc
    assert "it agrees with the\n    writer" not in doc
    assert "the shape a board-backed axis uses" not in doc


def test_board_arm_is_not_a_conflict(pc, axis_labels) -> None:
    """`board: true` NAMES the board as the substrate — the same answer the flag
    gives — so it is agreement, not a competing claim."""
    sm = _map(
        axis_labels, {"priority": {"board": True}, "workstream": {"board": True}}
    )
    results = pc._check_substrate_board_conflict(BOARD_CONFIG, sm)
    assert all(r.status != "fail" for r in results)


# =========================================================================
# The capability matrix renders the arm honestly
# =========================================================================


def test_matrix_does_not_call_a_board_armed_axis_unsupported(pc, axis_labels) -> None:
    """Where the read seam has not been taught the arm, `axis_disposition`
    fail-closes to `unsupported` for it. Rendering that verbatim would print
    "explicitly `unsupported`" over an axis whose map says exactly the opposite —
    the mis-description this change exists to remove, reappearing at the one place
    an adopter reads it. The dedicated branch keeps the line true either way."""
    sm = _map(axis_labels, {"priority": {"board": True}})
    results = pc._check_substrate_capability_matrix(sm)
    line = next(r for r in results if "priority" in r.label)
    assert "degraded" not in line.label
    assert "unsupported" not in line.detail.split("contrast")[0]
    assert "board: true" in line.detail


def test_matrix_names_the_binding_kind_rather_than_a_question_mark(
    pc, axis_labels
) -> None:
    """The served arm names its kind from a fixed tuple that does not include
    `board`, so without its own branch a board-armed axis renders `bound via ?`."""
    sm = _map(axis_labels, {"priority": {"board": True}})
    line = next(
        r for r in pc._check_substrate_capability_matrix(sm) if "priority" in r.label
    )
    assert "`?`" not in line.detail
    assert "SERVED" in line.detail
    assert line.status == "ok"


def test_matrix_still_never_fails_with_a_board_arm(pc, axis_labels) -> None:
    sm = _map(
        axis_labels,
        {
            "priority": {"board": True},
            "workstream": {"board": True},
            "type": {"title-prefix": {"remap": {"task": "[Task]"}}},
        },
    )
    assert all(r.status != "fail" for r in pc._check_substrate_capability_matrix(sm))


# =========================================================================
# Serialisation + this repo's own config
# =========================================================================


def test_every_new_result_is_json_serialisable(pc, axis_labels, tmp_path) -> None:
    """pre-check's `--json` path dumps `CheckResult.__dict__`; a finding that
    cannot round-trip breaks the machine-readable surface."""
    cap_root = _write_hooks(tmp_path / "cap", _HOOKS_WITHOUT_BOARD_FIELD)
    sm = _map(axis_labels, {"priority": {"board": True, "default": "P1"}})
    results = [
        *pc._check_substrate_board_arm_satisfiable(NO_BOARD_CONFIG, sm),
        *pc._check_board_axis_absent_from_map(BOARD_CONFIG, sm),
        *pc._check_board_arm_default_has_hook(cap_root, sm),
    ]
    assert results
    json.dumps([r.__dict__ for r in results])


def test_this_repos_own_config_trips_none_of_the_new_checks(pc, axis_labels) -> None:
    """Self-hosting sanity: project-kit's own pm config is board-less with no
    substrate-map, so none of the three can fire."""
    from ruamel.yaml import YAML

    cap_root = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    config = YAML(typ="safe").load(
        (cap_root / "project" / "config.yaml").read_text(encoding="utf-8")
    )
    assert axis_labels.load_substrate_map(cap_root) is None
    empty = _map(axis_labels, {})
    assert pc._check_board_axis_absent_from_map(config, empty) == []
    assert pc._check_board_arm_default_has_hook(cap_root, empty) == []
    assert all(
        r.status != "fail"
        for r in pc._check_substrate_board_arm_satisfiable(config, empty)
    )
