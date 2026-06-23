"""Engine tests for the COR-037 cascade / cross-subject outcome-fold slot.

The single sanctioned cross-subject read: a parent process folds the outcomes of
ALL members of ONE named child process that belong to it into one yes/no a
`cascade-outcome` gate reads. This file builds a fixture capability with:

- a KEYED inner `poi-verification` process (`draft -> verified` per point-of-
  interest), the COR-036 single-inner resolution the fold reuses per member;
- an OUTER keyed `area-discovery` process declaring a `cascade` over its POIs:
  `members` (the parent-scoped candidate-set source), `membership` (the per-
  subject belongs test), and an `all` / `count` reducer over `verified`.

The fixture is file-backed:

- `_poi-<id>` markers hold each POI's verification state (draft|verified);
- `_area-<area>` lists the POI ids that belong to that area (one per line) —
  the candidate-set source; the `members` predicate reads ONLY the named area's
  file (parent-scoped — the engine never sees a global POI list);
- the membership predicate confirms a POI's listed area matches the parent.

Covers: `all` pass/fail; `count` pass/fail against threshold — including the
ALL-DETERMINATE branches (every member resolved terminal, a mix of `verified`
and `dismissed`, none still moving) that genuinely exercise the reducer's
`reached >= threshold` / `reached == total` comparison rather than
short-circuiting on an unresolved member; fail-closed on an unresolved member;
fail-closed on an INDETERMINATE membership test (C1); self-cascade acyclicity;
fail-closed on the empty set (NOT vacuously open); membership enumerated via
predicate (a POI outside the area is never folded, even verified); the
aggregate-wait auto-clear; read-only; behaviour-preserving for cascade-free
processes; and that a non-member's outcome is never read into the fold.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from project_kit.process import (
    ProcessEngine,
    load_definition,
    render_status_json,
    render_status_narrative,
)

# --- fixture process definitions ------------------------------------------

# INNER (keyed): a per-POI verification process. `draft -> verified` /
# `draft -> dismissed`. BOTH `verified` and `dismissed` are TERMINAL outcomes;
# `dismissed` is a terminal-but-NOT-`verified` outcome, so a member can resolve
# terminal without reaching the cascade's named outcome — this is what lets the
# determinate-below-threshold and determinate-`all`-false fold branches be
# exercised genuinely (a fully-resolved member set, none left moving), rather
# than every "fold fails" case short-circuiting on an unresolved member. Position
# resolved from the per-POI `_poi-<id>` marker.
_INNER_DEFINITION = """\
process:
  id: poi-verification
  version: 1
  subject:
    cardinality: keyed
    key: poi-id
  interface:
    outcomes:
      - name: verified
        meaning: The point checks out.
      - name: dismissed
        meaning: The point was dismissed (terminal, but not `verified`).
  states:
    - id: draft
      meaning: Drafted, not yet verified.
      detection:
        mode: inferred
        predicate:
          run: poi-detect-draft
    - id: verified
      meaning: Verified.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: poi-detect-verified
    - id: dismissed
      meaning: Dismissed.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: poi-detect-dismissed
  transitions:
    - from: draft
      to: verified
      trigger: verify
      authorisation: script
    - from: draft
      to: dismissed
      trigger: dismiss
      authorisation: script
"""

# OUTER (keyed): an area whose discovery closes once its POIs are all verified.
# `discovering` parks on the awaiting-cascade-outcome wait; the `close` move is
# gated `cascade-outcome` over the area's POIs. The reducer op/threshold is
# templated in per test.
_OUTER_TEMPLATE = """\
process:
  id: area-discovery
  version: 1
  subject:
    cardinality: keyed
    key: area-id
    blocked:
      blocked_on: awaiting-cascade-outcome
  cascade:
    runs: fixture:poi-verification
    members:
      run: area-pois
    membership:
      run: poi-in-area
    reducer:
{reducer}
  states:
    - id: discovering
      meaning: Discovering an area, verifying its points.
      detection:
        mode: inferred
        predicate:
          run: area-detect-discovering
    - id: discovered
      meaning: Area discovered (all points verified).
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: area-detect-discovered
  transitions:
    - from: discovering
      to: discovered
      trigger: close
      authorisation: agent-autonomous
      gate:
        kind: cascade-outcome
      why: Close once the area's points all reached `verified`.
"""

_ALL_REDUCER = "      op: all\n      outcome: verified\n"


def _count_reducer(threshold: int) -> str:
    return f"      op: count\n      outcome: verified\n      threshold: {threshold}\n"


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _install_defs(pkit: Path) -> None:
    defs_dst = pkit / "schemas" / "_defs"
    defs_dst.mkdir(parents=True, exist_ok=True)
    source_defs = (
        Path(__file__).resolve().parents[1] / ".pkit" / "schemas" / "_defs" / "process.schema.json"
    )
    defs_dst.joinpath("process.schema.json").write_text(
        source_defs.read_text(encoding="utf-8"), encoding="utf-8"
    )


# A POI marker detection: result True iff the subject's `_poi-<subject>` marker
# holds the asked state. The subject id is argv[1] (the engine threads it).
def _poi_detect(state_name: str) -> str:
    return (
        "import json, sys, pathlib\n"
        "subj = sys.argv[1]\n"
        "p = pathlib.Path(f'_poi-{subj}')\n"
        "cur = p.read_text().strip() if p.exists() else ''\n"
        f"print(json.dumps({{'result': cur == {state_name!r}, "
        "'reason': f'poi {subj} marker is {cur!r}'}))\n"
    )


# The area's own detection: result True iff `_area-state-<subject>` holds the
# asked state (the AREA's process position, distinct from its POI membership).
def _area_detect(state_name: str) -> str:
    return (
        "import json, sys, pathlib\n"
        "subj = sys.argv[1]\n"
        "p = pathlib.Path(f'_area-state-{subj}')\n"
        "cur = p.read_text().strip() if p.exists() else 'discovering'\n"
        f"print(json.dumps({{'result': cur == {state_name!r}, "
        "'reason': f'area {subj} state is {cur!r}'}))\n"
    )


# The candidate-set SOURCE: read ONLY the named area's POI-list file (parent-
# scoped). Returns { members: [...] }. The engine never sees a global list.
_AREA_POIS = (
    "import json, sys, pathlib\n"
    "subj = sys.argv[1]\n"
    "p = pathlib.Path(f'_area-{subj}')\n"
    "ids = [l.strip() for l in p.read_text().splitlines() if l.strip()] if p.exists() else []\n"
    "print(json.dumps({'members': ids, 'reason': f'{len(ids)} candidate poi(s)'}))\n"
)

# The per-subject membership test: does THIS poi (argv[1]) belong to the parent
# area? The poi's own `_poi-area-<id>` file names its area. The PARENT area id is
# passed as a static `with` arg (rendered by the engine into the JSON the script
# reads on stdin is not used here; instead we encode the parent in argv-free form
# by reading the `_membership-parent` file the test sets). To keep the predicate
# single-subject and content-free, the membership test reads the poi's declared
# area and compares it to the parent recorded in `_membership-parent`.
_POI_IN_AREA = (
    "import json, sys, pathlib\n"
    "subj = sys.argv[1]\n"
    "declared = pathlib.Path(f'_poi-area-{subj}')\n"
    "area = declared.read_text().strip() if declared.exists() else ''\n"
    "parent = pathlib.Path('_membership-parent').read_text().strip() "
    "if pathlib.Path('_membership-parent').exists() else ''\n"
    "print(json.dumps({'result': area == parent and area != '', "
    "'reason': f'poi {subj} area={area!r} parent={parent!r}'}))\n"
)


@pytest.fixture
def cascade_repo(tmp_path: Path):
    """A repo factory: build the fixture capability with a chosen reducer.

    Returns a callable `build(reducer_yaml) -> repo`. Markers are file-backed in
    the repo root.
    """

    def build(reducer: str) -> Path:
        repo = tmp_path
        pkit = repo / ".pkit"
        _install_defs(pkit)

        cap = pkit / "capabilities" / "fixture"
        scripts = cap / "scripts"
        cap.mkdir(parents=True, exist_ok=True)
        (cap / "package.yaml").write_text(
            """schema_version: 2
component:
  kind: capability
  name: fixture
  version: 0.1.0
description: Cascade fixture (COR-037).
commands:
  poi-detect-draft:
    script: scripts/poi_detect_draft.py
    help: poi draft
  poi-detect-verified:
    script: scripts/poi_detect_verified.py
    help: poi verified
  poi-detect-dismissed:
    script: scripts/poi_detect_dismissed.py
    help: poi dismissed
  area-detect-discovering:
    script: scripts/area_detect_discovering.py
    help: area discovering
  area-detect-discovered:
    script: scripts/area_detect_discovered.py
    help: area discovered
  area-pois:
    script: scripts/area_pois.py
    help: area candidate pois
  poi-in-area:
    script: scripts/poi_in_area.py
    help: poi membership
""",
            encoding="utf-8",
        )
        (cap / "schemas").mkdir(parents=True, exist_ok=True)
        (cap / "schemas" / "poi-verification.yaml").write_text(
            _INNER_DEFINITION, encoding="utf-8"
        )
        (cap / "schemas" / "area-discovery.yaml").write_text(
            _OUTER_TEMPLATE.format(reducer=reducer), encoding="utf-8"
        )

        _write_script(scripts / "poi_detect_draft.py", _poi_detect("draft"))
        _write_script(scripts / "poi_detect_verified.py", _poi_detect("verified"))
        _write_script(scripts / "poi_detect_dismissed.py", _poi_detect("dismissed"))
        _write_script(scripts / "area_detect_discovering.py", _area_detect("discovering"))
        _write_script(scripts / "area_detect_discovered.py", _area_detect("discovered"))
        _write_script(scripts / "area_pois.py", _AREA_POIS)
        _write_script(scripts / "poi_in_area.py", _POI_IN_AREA)
        return repo

    return build


def _outer(repo: Path, area: str = "a1") -> ProcessEngine:
    # The membership predicate compares each POI's declared area to this parent.
    (repo / "_membership-parent").write_text(area, encoding="utf-8")
    return ProcessEngine(load_definition(repo, "fixture:area-discovery"), repo, subject=area)


def _add_poi(repo: Path, poi: str, area: str, state: str = "draft") -> None:
    """Register a POI: list it under its area, declare its area, set its state."""
    list_file = repo / f"_area-{area}"
    existing = list_file.read_text().splitlines() if list_file.exists() else []
    if poi not in existing:
        existing.append(poi)
    list_file.write_text("\n".join(existing) + "\n", encoding="utf-8")
    (repo / f"_poi-area-{poi}").write_text(area, encoding="utf-8")
    (repo / f"_poi-{poi}").write_text(state, encoding="utf-8")


def _set_poi(repo: Path, poi: str, state: str) -> None:
    (repo / f"_poi-{poi}").write_text(state, encoding="utf-8")


def _close_check(engine: ProcessEngine, actor: str = "agent"):
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, actor)
    return next(c for c in checks if c.to == "discovered")


# --- the `all` reducer ----------------------------------------------------


def test_all_fold_closed_while_a_member_is_draft(cascade_repo) -> None:
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "draft")
    fold = _outer(repo).resolve_cascade_outcome()
    assert fold is not None
    assert fold.indeterminate is True  # p2 has no resolved outcome -> unresolved
    assert fold.opened is False
    assert _close_check(_outer(repo)).allowed is False


def test_all_fold_opens_when_every_member_verified(cascade_repo) -> None:
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "verified")
    fold = _outer(repo).resolve_cascade_outcome()
    assert fold is not None
    assert fold.opened is True
    assert fold.indeterminate is False
    assert fold.reached == 2 and fold.total == 2
    assert _close_check(_outer(repo)).allowed is True


def test_all_fold_determinate_false_when_a_member_dismissed(cascade_repo) -> None:
    # ALL-DETERMINATE branch: every member resolved to a TERMINAL outcome (a mix
    # of `verified` and `dismissed`, none still moving), but not all reached the
    # named `verified`. This must be a determinate "not all reached X" (opened
    # False, indeterminate False) — proving `all` distinguishes "reached a
    # DIFFERENT terminal" from "still moving" (which holds the fold unresolved).
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "verified")
    _add_poi(repo, "p3", "a1", "dismissed")
    fold = _outer(repo).resolve_cascade_outcome()
    assert fold is not None
    assert fold.opened is False
    assert fold.indeterminate is False  # genuinely determinate, NOT short-circuited
    assert fold.reached == 2 and fold.total == 3
    assert _close_check(_outer(repo)).allowed is False


def test_all_fold_empty_set_is_fail_closed_not_vacuously_open(cascade_repo) -> None:
    # An `all` over zero members does NOT vacuously open the gate.
    repo = cascade_repo(_ALL_REDUCER)  # no POIs added
    fold = _outer(repo).resolve_cascade_outcome()
    assert fold is not None
    assert fold.total == 0
    assert fold.opened is False
    assert fold.indeterminate is False  # determinate "not yet", not an eval failure
    assert _close_check(_outer(repo)).allowed is False


# --- the `count` reducer --------------------------------------------------


def test_count_fold_opens_when_threshold_met(cascade_repo) -> None:
    repo = cascade_repo(_count_reducer(2))
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "verified")
    _add_poi(repo, "p3", "a1", "verified")
    fold = _outer(repo).resolve_cascade_outcome()
    assert fold is not None
    assert fold.reached == 3 and fold.threshold == 2
    assert fold.opened is True
    assert _close_check(_outer(repo)).allowed is True


def test_count_fold_closed_below_threshold(cascade_repo) -> None:
    repo = cascade_repo(_count_reducer(3))
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "verified")
    _add_poi(repo, "p3", "a1", "verified")
    _set_poi(repo, "p3", "draft")  # only 2 verified, threshold 3
    fold = _outer(repo).resolve_cascade_outcome()
    assert fold is not None
    # p3 is draft (non-terminal) -> unresolved -> fail-closed.
    assert fold.opened is False
    assert _close_check(_outer(repo)).allowed is False


def test_count_fold_opens_when_threshold_met_all_determinate(cascade_repo) -> None:
    # ALL-DETERMINATE branch: 2 verified + 1 dismissed (every member terminal,
    # none moving), threshold 2. reached==2 meets the floor -> opens. This pins
    # the genuine `reached >= threshold` comparison, not the unresolved path.
    repo = cascade_repo(_count_reducer(2))
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "verified")
    _add_poi(repo, "p3", "a1", "dismissed")
    fold = _outer(repo).resolve_cascade_outcome()
    assert fold is not None
    assert fold.opened is True
    assert fold.indeterminate is False
    assert fold.reached == 2 and fold.total == 3
    assert _close_check(_outer(repo)).allowed is True


def test_count_fold_determinate_below_threshold(cascade_repo) -> None:
    # ALL-DETERMINATE below-floor: the SAME fully-resolved set (2 verified + 1
    # dismissed), threshold 3. reached==2 < 3 -> determinate not-met (opened
    # False, indeterminate False) — the genuine below-floor case, NOT the
    # unresolved-member short-circuit.
    repo = cascade_repo(_count_reducer(3))
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "verified")
    _add_poi(repo, "p3", "a1", "dismissed")
    fold = _outer(repo).resolve_cascade_outcome()
    assert fold is not None
    assert fold.opened is False
    assert fold.indeterminate is False  # determinate below floor, not short-circuited
    assert fold.reached == 2 and fold.total == 3
    assert _close_check(_outer(repo)).allowed is False


def test_count_fold_opens_exactly_at_floor(cascade_repo) -> None:
    # Pins `>=` vs `>`: reached == threshold must OPEN. 2 verified + 1 dismissed,
    # threshold exactly 2 -> reached==2==threshold -> opens.
    repo = cascade_repo(_count_reducer(2))
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "verified")
    _add_poi(repo, "p3", "a1", "dismissed")
    fold = _outer(repo).resolve_cascade_outcome()
    assert fold is not None
    assert fold.reached == fold.threshold == 2
    assert fold.opened is True
    assert fold.indeterminate is False


def test_count_fold_empty_set_is_fail_closed(cascade_repo) -> None:
    repo = cascade_repo(_count_reducer(1))  # threshold 1, zero members
    fold = _outer(repo).resolve_cascade_outcome()
    assert fold is not None
    assert fold.total == 0
    assert fold.opened is False
    assert fold.indeterminate is False


# --- fail-closed on an unresolved member ----------------------------------


def test_unresolved_member_holds_fold_unresolved(cascade_repo) -> None:
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "draft")
    # Break p2's detection entirely -> its inner position is indeterminate ->
    # the fold is fail-closed (indeterminate), the gate stays shut.
    scripts = repo / ".pkit" / "capabilities" / "fixture" / "scripts"
    _write_script(scripts / "poi_detect_draft.py", "import sys\nsys.exit(4)\n")
    _write_script(scripts / "poi_detect_verified.py", "import sys\nsys.exit(4)\n")
    fold = _outer(repo).resolve_cascade_outcome()
    assert fold is not None
    assert fold.indeterminate is True
    assert fold.opened is False


# --- membership enumerated via predicate (never a global list) ------------


def test_non_member_poi_is_never_folded(cascade_repo) -> None:
    # A verified POI that belongs to a DIFFERENT area must not count toward a1's
    # fold: membership is asked per subject, and the candidate-set source is
    # parent-scoped. Here p-other is verified but listed under area a2.
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "draft")
    _add_poi(repo, "p-other", "a2", "verified")  # different area, verified
    fold = _outer(repo, "a1").resolve_cascade_outcome()
    assert fold is not None
    # Only p1 is a member of a1; p-other is not enumerated into a1's fold.
    assert fold.total == 1
    # p1 is draft -> unresolved -> fold not open (and certainly not opened by the
    # unrelated verified POI).
    assert fold.opened is False


def test_membership_predicate_excludes_listed_but_unowned_candidate(cascade_repo) -> None:
    # Defence-in-depth: even if a candidate id is RETURNED by the members source,
    # the per-subject membership test gates it. Here p2 is listed under a1's
    # candidate file but its declared area is a2 -> membership says no -> excluded.
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "verified")
    # Force p2 into a1's candidate list but declare its real area as a2.
    list_file = repo / "_area-a1"
    list_file.write_text("p1\np2\n", encoding="utf-8")
    (repo / "_poi-area-p2").write_text("a2", encoding="utf-8")
    (repo / "_poi-p2").write_text("draft", encoding="utf-8")
    fold = _outer(repo, "a1").resolve_cascade_outcome()
    assert fold is not None
    # p2 is a candidate but not a member -> only p1 folded -> all-verified -> open.
    assert fold.total == 1 and fold.reached == 1
    assert fold.opened is True


def test_indeterminate_membership_holds_fold_unresolved(cascade_repo) -> None:
    # C1: an INDETERMINATE membership test (the predicate errors / times out for a
    # candidate) must hold the WHOLE fold unresolved (indeterminate, gate shut),
    # NOT silently drop the candidate (which would look like "fewer members" and
    # could let an `all` vacuously pass). A determinate non-member is still cleanly
    # excluded — here the membership predicate exits non-zero (indeterminate) for
    # every candidate, so the fold cannot resolve.
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "verified")
    scripts = repo / ".pkit" / "capabilities" / "fixture" / "scripts"
    _write_script(scripts / "poi_in_area.py", "import sys\nsys.exit(7)\n")
    fold = _outer(repo, "a1").resolve_cascade_outcome()
    assert fold is not None
    assert fold.indeterminate is True  # membership unresolved -> fold unresolved
    assert fold.opened is False
    assert _close_check(_outer(repo, "a1")).allowed is False


# --- self-cascade acyclicity ----------------------------------------------


def test_self_cascade_is_refused_as_cyclic(cascade_repo) -> None:
    # G2: a process whose `cascade.runs` is its OWN address must fail closed — the
    # inherited acyclicity guard (the parent's own address seeds its resolution
    # stack) refuses resolving a member as an embedding of the parent process
    # itself, exactly like a cyclic single-inner embedding. Proves the guard fires
    # on the cascade path, not just the COR-036 subprocess path.
    repo = cascade_repo(_ALL_REDUCER)
    # Point the cascade at the area-discovery process itself.
    outer_def = repo / ".pkit" / "capabilities" / "fixture" / "schemas" / "area-discovery.yaml"
    outer_def.write_text(
        outer_def.read_text(encoding="utf-8").replace(
            "runs: fixture:poi-verification", "runs: fixture:area-discovery"
        ),
        encoding="utf-8",
    )
    # Supply one candidate that membership confirms, so the fold actually reaches
    # the per-member resolution (where the cyclic guard fires).
    (repo / "_area-a1").write_text("a2\n", encoding="utf-8")
    (repo / "_poi-area-a2").write_text("a1", encoding="utf-8")
    fold = _outer(repo, "a1").resolve_cascade_outcome()
    assert fold is not None
    assert fold.indeterminate is True  # the self-embed is refused -> member unresolved
    assert fold.opened is False
    assert "cyclic" in fold.reason.lower() or "embedding" in fold.reason.lower()


# --- the awaiting-cascade-outcome aggregate wait (auto-clearing) -----------


def test_awaiting_cascade_outcome_blocked_while_fold_closed(cascade_repo) -> None:
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "draft")
    engine = _outer(repo)
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, "agent")
    blocked = engine.evaluate_blocked(pos, checks, "agent")
    assert blocked is not None
    assert blocked.blocked_on == "awaiting-cascade-outcome"
    assert blocked.at == "discovering"


def test_awaiting_cascade_outcome_auto_clears_when_fold_opens(cascade_repo) -> None:
    # The condition IS the live fold: when every member reaches `verified` the
    # gate opens, a legal move exists, and the wait clears -- no resume_when.
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "verified")
    engine = _outer(repo)
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, "agent")
    assert engine.evaluate_blocked(pos, checks, "agent") is None


def test_terminal_area_not_blocked(cascade_repo) -> None:
    # Once the area reaches `discovered` (terminal), no cascade wait applies.
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "verified")
    (repo / "_area-state-a1").write_text("discovered", encoding="utf-8")
    engine = _outer(repo)
    pos = engine.resolve_position()
    checks = engine.precheck_transitions(pos.state_id, "agent")
    assert engine.evaluate_blocked(pos, checks, "agent") is None


# --- status surfacing -----------------------------------------------------


def test_cascade_surfaces_on_json_status(cascade_repo) -> None:
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "draft")
    payload = json.loads(render_status_json(_outer(repo), actor="agent"))
    cascade = payload["position"]["cascade"]
    assert cascade is not None
    assert cascade["runs"] == "fixture:poi-verification"
    assert cascade["op"] == "all"
    assert cascade["total"] == 2
    assert cascade["opened"] is False
    assert payload["blocked"]["blocked_on"] == "awaiting-cascade-outcome"


def test_cascade_surfaces_on_narrative_status(cascade_repo) -> None:
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "verified")
    text = render_status_narrative(_outer(repo), actor="agent")
    assert "folds fixture:poi-verification" in text


# --- read-only ------------------------------------------------------------


def test_cascade_resolution_is_read_only(cascade_repo) -> None:
    repo = cascade_repo(_ALL_REDUCER)
    _add_poi(repo, "p1", "a1", "verified")
    _add_poi(repo, "p2", "a1", "draft")
    render_status_json(_outer(repo), actor="agent")
    render_status_narrative(_outer(repo), actor="agent")
    _outer(repo).resolve_cascade_outcome()
    # No journal written for the area or any folded POI.
    assert not _outer(repo).read_journal(), "resolving the fold must not write the journal"
    poi_journals = repo / ".pkit" / "capabilities" / "fixture" / "project" / "process"
    if poi_journals.exists():
        written = list(poi_journals.rglob("*.journal.jsonl"))
        assert not written, f"folding members must not write their journals: {written}"


# --- behaviour-preserving for cascade-free processes ----------------------


def test_cascade_free_process_unaffected(cascade_repo) -> None:
    # A process with NO cascade declaration resolves no fold and is unchanged:
    # the inner verification process itself declares no cascade.
    repo = cascade_repo(_ALL_REDUCER)
    inner = ProcessEngine(load_definition(repo, "fixture:poi-verification"), repo, subject="p1")
    assert inner.resolve_cascade_outcome() is None
    (repo / "_poi-p1").write_text("draft", encoding="utf-8")
    pos = inner.resolve_position()
    assert pos.state_id == "draft"
    # No cascade block in the JSON position for a cascade-free process.
    payload = json.loads(render_status_json(inner, actor="agent"))
    assert payload["position"]["cascade"] is None
