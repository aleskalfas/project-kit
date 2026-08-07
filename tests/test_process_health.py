"""The `pkit process health` missed-hand-off check (COR-042 / ADR-048).

These tests pin the load-bearing facts:

- the grounding case reproduces: N upstream subjects at the trigger with no
  downstream pickup report N misses, exit non-zero (the trip-planner
  seven-unpicked-screens shape);
- a pickup makes its line disappear (missed = absent, nothing else);
- fan-out (one upstream -> several downstream ids) satisfies; fan-in (several
  upstreams -> one downstream) checks each upstream independently;
- fail-closed indeterminacy is DISTINCT from a miss: a phantom trigger, an
  unresolvable upstream address, an erroring/unregistered candidate source, an
  erroring `resolve`, and an unreadable upstream position each report
  indeterminate and hold the exit code non-zero;
- determinate-empty is clean (an explicit empty candidate set exits 0);
- entries WITHOUT a `handoff` contract are never evaluated by anything;
- singleton endpoints participate (a singleton upstream's one subject);
- `--process` filters to contracts touching one address; `--json` is the
  byte-stable machine form; couplings order topologically (sources first, name
  tie-breaks, name-order fallback on declared cycles);
- the ADR-048 module boundary: the runtime engine module never imports the
  health module (the mirror of the render's never-invokes-engine pin), and
  health itself never moves a subject or writes anything (report-only).

Built on a fixture pair of capabilities: `design` (upstream `screen` keyed
process + `catalog` singleton) whose detection reads per-subject marker files,
and `delivery` (downstream `unit` process) declaring the contract and supplying
the `candidates` / `resolve` seam scripts, file-backed at the repo root.
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import cli_render
from project_kit import process_health as ph
from project_kit.cli import main
from project_kit.process import ProcessEngine

# --- fixture process definitions ------------------------------------------

# UPSTREAM (design:screen, keyed): a screen design ladder. The stable
# `implementation-ready` state is the hand-off trigger (COR-042's stable-trigger
# authoring rule); `built` is past-trigger (a picked-up-and-done screen must
# leave the report). Position is file-backed per subject (`_screen-<id>`); the
# marker value BOOM makes detection error (an unreadable position).
_SCREEN_DEF = """\
process:
  id: screen
  version: 1
  subject:
    cardinality: keyed
    key: screen-id
  states:
    - id: drafting
      meaning: Drafting the screen design.
      entry: true
      detection:
        mode: inferred
        predicate:
          run: screen-drafting
    - id: implementation-ready
      meaning: Design approved, ready to hand off to delivery.
      detection:
        mode: inferred
        predicate:
          run: screen-ready
    - id: built
      meaning: Built downstream.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: screen-built
  transitions: []
"""

# UPSTREAM (design:catalog, singleton): the singleton-endpoint case. Its one
# subject's position is the `_catalog` marker; `ready` is the trigger.
_CATALOG_DEF = """\
process:
  id: catalog
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: filling
      meaning: Collecting entries.
      entry: true
      detection:
        mode: inferred
        predicate:
          run: catalog-filling
    - id: ready
      meaning: Catalog ready to hand off.
      detection:
        mode: inferred
        predicate:
          run: catalog-ready
    - id: done
      meaning: Published.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: catalog-done
  transitions: []
"""

# DOWNSTREAM (delivery:unit, keyed): declares the contract on a push-mode
# triggered-by edge (COR-042: the contract is orthogonal to relation/mode).
# The upstream address and trigger are templated so the phantom-trigger and
# unresolvable-upstream cases reuse the same definition.
_UNIT_DEF_TEMPLATE = """\
process:
  id: unit
  version: 1
  subject:
    cardinality: keyed
    key: unit-id
  states:
    - id: building
      meaning: Building a unit for a readied screen.
      entry: true
      detection:
        mode: inferred
        predicate:
          run: unit-detect
      depends_on:
        - upstream: {upstream}
          relation: triggered-by
          mode: push
          why: A unit builds the screen the design process readied.
          handoff:
            trigger: {trigger}
            candidates:
              run: list-candidates
            resolve:
              run: resolve-pickup
    - id: done
      meaning: Done.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: unit-detect
  transitions: []
"""

# The same coupling WITHOUT a contract: fully inert (COR-038 preserved) — the
# check must not evaluate it even when every seam script would error.
_UNIT_INERT_DEF = """\
process:
  id: unit
  version: 1
  subject:
    cardinality: keyed
    key: unit-id
  states:
    - id: building
      meaning: Building a unit for a readied screen.
      entry: true
      detection:
        mode: inferred
        predicate:
          run: unit-detect
      depends_on:
        - upstream: design:screen
          relation: triggered-by
          mode: push
          why: A unit builds the screen the design process readied.
    - id: done
      meaning: Done.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: unit-detect
  transitions: []
"""

# DOWNSTREAM (delivery:pipeline, singleton): the singleton-downstream side of
# the singleton-endpoint case — couples to the singleton catalog.
_PIPELINE_DEF = """\
process:
  id: pipeline
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: assembling
      meaning: Assembling the pipeline from the catalog.
      entry: true
      detection:
        mode: inferred
        predicate:
          run: unit-detect
      depends_on:
        - upstream: design:catalog
          relation: constrained-with
          mode: pull
          why: The pipeline consumes the readied catalog.
          handoff:
            trigger: ready
            candidates:
              run: list-candidates
            resolve:
              run: resolve-pickup
  transitions: []
"""


# --- fixture scripts -------------------------------------------------------


def _screen_detect(state_name: str) -> str:
    """Detection for one screen state: result True iff `_screen-<subject>` holds
    that state. A BOOM marker errors the predicate (unreadable position)."""
    return (
        "import json, sys, pathlib\n"
        "subj = sys.argv[1]\n"
        "p = pathlib.Path(f'_screen-{subj}')\n"
        "cur = p.read_text().strip() if p.exists() else ''\n"
        "if cur == 'BOOM':\n"
        "    sys.exit(1)\n"
        f"print(json.dumps({{'result': cur == {state_name!r}, "
        "'reason': f'screen {subj} marker is {cur!r}'}))\n"
    )


def _catalog_detect(state_name: str) -> str:
    """Detection for the singleton catalog: reads the one `_catalog` marker
    (the engine threads the singleton sentinel; the marker is subject-free)."""
    return (
        "import json, pathlib\n"
        "cur = pathlib.Path('_catalog').read_text().strip() "
        "if pathlib.Path('_catalog').exists() else 'filling'\n"
        f"print(json.dumps({{'result': cur == {state_name!r}, "
        "'reason': f'catalog marker is {cur!r}'}))\n"
    )


# The candidate SOURCE (ADR-048): the subject slot carries the contract's
# UPSTREAM ADDRESS, and the script picks its root by that scope — which is what
# pins the address threading. A sentinel file records every invocation (the
# no-contract-never-evaluated proof). A missing root file errors (broken-empty,
# indeterminate); a present-but-empty root is a determinate empty answer.
_LIST_CANDIDATES = (
    "import json, sys, pathlib\n"
    "pathlib.Path('_candidates-ran').write_text('1')\n"
    "scope = sys.argv[1]\n"
    "name = '_catalog-candidates' if scope == 'design:catalog' else '_screens'\n"
    "p = pathlib.Path(name)\n"
    "if not p.exists():\n"
    "    sys.exit(1)\n"
    "ids = [l.strip() for l in p.read_text().splitlines() if l.strip()]\n"
    "print(json.dumps({'candidates': ids, 'reason': f'{len(ids)} candidate(s) for {scope}'}))\n"
)

# The point-to-point RESOLVE (ADR-048): the subject slot carries ONE upstream
# subject id; `_pickups.json` maps it to downstream unit ids. Missing file =
# erroring resolve (indeterminate); mapped ERROR = per-subject error; mapped
# MALFORMED = a payload with no explicit `downstream` list (indeterminate);
# missing key = explicit absence (a determinate MISS); a list = the pickup(s).
_RESOLVE_PICKUP = (
    "import json, sys, pathlib\n"
    "subj = sys.argv[1]\n"
    "p = pathlib.Path('_pickups.json')\n"
    "if not p.exists():\n"
    "    sys.exit(1)\n"
    "data = json.loads(p.read_text())\n"
    "val = data.get(subj)\n"
    "if val == 'ERROR':\n"
    "    sys.exit(1)\n"
    "if val == 'MALFORMED':\n"
    "    print(json.dumps({'reason': 'no explicit answer'}))\n"
    "    sys.exit(0)\n"
    "ids = val if isinstance(val, list) else []\n"
    "print(json.dumps({'downstream': ids, 'reason': f'unit(s) for {subj}: {ids}'}))\n"
)

_NOOP = "import json\nprint(json.dumps({'result': False, 'reason': 'noop'}))\n"


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_package_yaml(cap: Path, name: str, commands: dict[str, str]) -> None:
    lines = [
        "schema_version: 2",
        "component:",
        "  kind: capability",
        f"  name: {name}",
        "  version: 0.1.0",
        f"description: Health fixture capability ({name}).",
        "commands:",
    ]
    for command, script in commands.items():
        lines.append(f"  {command}:")
        lines.append(f"    script: {script}")
        lines.append(f"    help: {command}")
    cap.joinpath("package.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def health_repo(tmp_path: Path):
    """A repo factory: build the design/delivery fixture pair.

    `build(unit_yaml, include_pipeline=False)` writes both capabilities and
    seeds the clean baseline (empty `_screens`, empty pickups). Markers are
    file-backed at the repo root (predicates run with cwd = repo root).
    """

    def build(
        unit_yaml: str | None = None, *, include_pipeline: bool = False
    ) -> Path:
        repo = tmp_path
        caps = repo / ".pkit" / "capabilities"

        design = caps / "design"
        design.mkdir(parents=True, exist_ok=True)
        _write_package_yaml(
            design,
            "design",
            {
                "screen-drafting": "scripts/screen_drafting.py",
                "screen-ready": "scripts/screen_ready.py",
                "screen-built": "scripts/screen_built.py",
                "catalog-filling": "scripts/catalog_filling.py",
                "catalog-ready": "scripts/catalog_ready.py",
                "catalog-done": "scripts/catalog_done.py",
            },
        )
        (design / "schemas").mkdir(parents=True, exist_ok=True)
        (design / "schemas" / "screen.yaml").write_text(_SCREEN_DEF, encoding="utf-8")
        (design / "schemas" / "catalog.yaml").write_text(_CATALOG_DEF, encoding="utf-8")
        scripts = design / "scripts"
        _write_script(scripts / "screen_drafting.py", _screen_detect("drafting"))
        _write_script(scripts / "screen_ready.py", _screen_detect("implementation-ready"))
        _write_script(scripts / "screen_built.py", _screen_detect("built"))
        _write_script(scripts / "catalog_filling.py", _catalog_detect("filling"))
        _write_script(scripts / "catalog_ready.py", _catalog_detect("ready"))
        _write_script(scripts / "catalog_done.py", _catalog_detect("done"))

        delivery = caps / "delivery"
        delivery.mkdir(parents=True, exist_ok=True)
        _write_package_yaml(
            delivery,
            "delivery",
            {
                "unit-detect": "scripts/unit_detect.py",
                "list-candidates": "scripts/list_candidates.py",
                "resolve-pickup": "scripts/resolve_pickup.py",
            },
        )
        (delivery / "schemas").mkdir(parents=True, exist_ok=True)
        if unit_yaml is None:
            unit_yaml = _UNIT_DEF_TEMPLATE.format(
                upstream="design:screen", trigger="implementation-ready"
            )
        (delivery / "schemas" / "unit.yaml").write_text(unit_yaml, encoding="utf-8")
        if include_pipeline:
            (delivery / "schemas" / "pipeline.yaml").write_text(
                _PIPELINE_DEF, encoding="utf-8"
            )
        scripts = delivery / "scripts"
        _write_script(scripts / "unit_detect.py", _NOOP)
        _write_script(scripts / "list_candidates.py", _LIST_CANDIDATES)
        _write_script(scripts / "resolve_pickup.py", _RESOLVE_PICKUP)

        # Clean baseline: a determinate-empty candidate set, no pickups.
        (repo / "_screens").write_text("", encoding="utf-8")
        _set_pickups(repo, {})
        return repo

    return build


def _add_screen(repo: Path, screen_id: str, state: str = "implementation-ready") -> None:
    (repo / f"_screen-{screen_id}").write_text(state, encoding="utf-8")
    screens = repo / "_screens"
    existing = screens.read_text(encoding="utf-8") if screens.exists() else ""
    screens.write_text(existing + screen_id + "\n", encoding="utf-8")


def _set_pickups(repo: Path, mapping: dict) -> None:
    (repo / "_pickups.json").write_text(json.dumps(mapping), encoding="utf-8")


def _the_contract(report: ph.HealthReport) -> ph.ContractReport:
    assert len(report.contracts) == 1
    return report.contracts[0]


# --- the grounding case: N unpicked upstreams = N misses -------------------


def test_seven_unpicked_upstreams_report_seven_misses(health_repo) -> None:
    # The trip-planner grounding shape (COR-042 context): seven screens at
    # implementation-ready, no units — seven reported missed hand-offs.
    repo = health_repo()
    for i in range(1, 8):
        _add_screen(repo, f"screen-{i}")
    report = ph.build_report(repo)
    cr = _the_contract(report)
    assert cr.contract.upstream == "design:screen"
    assert cr.contract.downstream == "delivery:unit"
    assert cr.contract.trigger == "implementation-ready"
    assert [f.subject for f in cr.misses] == [f"screen-{i}" for i in range(1, 8)]
    assert cr.indeterminate == ()
    assert cr.at_trigger == 7 and cr.satisfied == 0
    assert report.missed_total == 7
    assert report.indeterminate_total == 0
    assert not report.ok


def test_pickup_satisfies_and_its_line_disappears(health_repo) -> None:
    repo = health_repo()
    for i in range(1, 8):
        _add_screen(repo, f"screen-{i}")
    _set_pickups(repo, {"screen-3": ["unit-9"]})
    report = ph.build_report(repo)
    cr = _the_contract(report)
    assert "screen-3" not in [f.subject for f in cr.misses]
    assert len(cr.misses) == 6
    assert cr.satisfied == 1
    # Every screen picked up: the report goes fully clean.
    _set_pickups(repo, {f"screen-{i}": [f"unit-{i}"] for i in range(1, 8)})
    clean = ph.build_report(repo)
    assert _the_contract(clean).findings == ()
    assert clean.ok


# --- cardinality degrades cleanly (COR-042 point 2) ------------------------


def test_fan_out_one_upstream_to_several_downstream_satisfies(health_repo) -> None:
    repo = health_repo()
    _add_screen(repo, "wide")
    _set_pickups(repo, {"wide": ["unit-a", "unit-b", "unit-c"]})
    report = ph.build_report(repo)
    cr = _the_contract(report)
    assert cr.findings == () and cr.satisfied == 1
    assert report.ok


def test_fan_in_each_upstream_checked_independently(health_repo) -> None:
    # Two screens resolve to the SAME downstream unit: each satisfied on its
    # own; a third with no pickup still reports its own miss.
    repo = health_repo()
    _add_screen(repo, "s-1")
    _add_screen(repo, "s-2")
    _add_screen(repo, "s-3")
    _set_pickups(repo, {"s-1": ["unit-shared"], "s-2": ["unit-shared"]})
    report = ph.build_report(repo)
    cr = _the_contract(report)
    assert cr.satisfied == 2
    assert [f.subject for f in cr.misses] == ["s-3"]


# --- only subjects AT the trigger count (live snapshot) --------------------


def test_subjects_not_at_the_trigger_produce_no_line(health_repo) -> None:
    # A drafting screen (before the trigger) and a built one (past it) both
    # leave the report — the check reads the live at-trigger snapshot only.
    repo = health_repo()
    _add_screen(repo, "early", state="drafting")
    _add_screen(repo, "late", state="built")
    report = ph.build_report(repo)
    cr = _the_contract(report)
    assert cr.findings == () and cr.at_trigger == 0
    assert report.ok


# --- indeterminate is distinct from a miss (fail-closed) -------------------


def test_unreadable_upstream_position_is_indeterminate(health_repo) -> None:
    repo = health_repo()
    _add_screen(repo, "ok-1")
    _add_screen(repo, "broken")
    (repo / "_screen-broken").write_text("BOOM", encoding="utf-8")
    report = ph.build_report(repo)
    cr = _the_contract(report)
    assert [f.subject for f in cr.misses] == ["ok-1"]
    assert [f.subject for f in cr.indeterminate] == ["broken"]
    assert not report.ok


def test_erroring_resolve_is_indeterminate_not_a_miss(health_repo) -> None:
    repo = health_repo()
    _add_screen(repo, "s-err")
    _add_screen(repo, "s-missed")
    _set_pickups(repo, {"s-err": "ERROR"})
    report = ph.build_report(repo)
    cr = _the_contract(report)
    assert [f.subject for f in cr.misses] == ["s-missed"]
    assert [f.subject for f in cr.indeterminate] == ["s-err"]
    assert report.missed_total == 1 and report.indeterminate_total == 1


def test_resolve_without_explicit_answer_is_indeterminate(health_repo) -> None:
    # A payload with no explicit `downstream` list is NOT absence — an answer
    # that fails to say either way must never be read as "no miss" (or as one).
    repo = health_repo()
    _add_screen(repo, "s-vague")
    _set_pickups(repo, {"s-vague": "MALFORMED"})
    cr = _the_contract(ph.build_report(repo))
    assert cr.misses == ()
    assert [f.subject for f in cr.indeterminate] == ["s-vague"]


def test_malformed_resolve_member_is_indeterminate_not_a_miss(health_repo) -> None:
    # {'downstream': [42]} must NOT silently filter to [] — that would read a
    # broken answer as a determinate MISS. A malformed member makes the whole
    # payload uninterpretable (indeterminate), per COR-042's
    # broken-is-never-determinate rule.
    repo = health_repo()
    _add_screen(repo, "s-int")
    _set_pickups(repo, {"s-int": [42]})
    cr = _the_contract(ph.build_report(repo))
    assert cr.misses == ()
    assert [f.subject for f in cr.indeterminate] == ["s-int"]


def test_malformed_candidates_member_is_contract_indeterminate(
    health_repo, monkeypatch
) -> None:
    # {'candidates': ['ok', 42]} must NOT filter to just ['ok'] (or to clean):
    # a malformed member is an uninterpretable payload -> contract-level
    # indeterminate, exit non-zero.
    repo = health_repo()
    monkeypatch.setattr(
        ph.PredicateRunner,
        "run_raw",
        lambda self, predicate: {"candidates": ["ok", 42]},
    )
    report = ph.build_report(repo)
    cr = _the_contract(report)
    assert cr.misses == ()
    assert len(cr.indeterminate) == 1
    assert cr.indeterminate[0].subject is None  # contract-level, distinctly
    assert not report.ok


def test_erroring_candidates_source_is_contract_indeterminate(health_repo) -> None:
    # Broken-empty vs determinate-empty (COR-042): a candidate source that
    # ERRORS is indeterminate for the whole contract, never "nothing missed".
    repo = health_repo()
    (repo / "_screens").unlink()
    report = ph.build_report(repo)
    cr = _the_contract(report)
    assert cr.misses == ()
    assert len(cr.indeterminate) == 1
    assert cr.indeterminate[0].subject is None  # contract-level, distinctly
    assert not report.ok


def test_determinate_empty_candidate_set_is_clean(health_repo) -> None:
    # The baseline `_screens` file exists and is empty: evaluated without
    # error, zero candidates — a clean, determinate answer, exit 0.
    repo = health_repo()
    report = ph.build_report(repo)
    assert _the_contract(report).findings == ()
    assert report.ok


def test_phantom_trigger_is_indeterminate_never_green(health_repo) -> None:
    repo = health_repo(
        _UNIT_DEF_TEMPLATE.format(upstream="design:screen", trigger="aproved-typo")
    )
    report = ph.build_report(repo)
    cr = _the_contract(report)
    assert cr.misses == ()
    assert cr.indeterminate[0].subject is None
    assert "aproved-typo" in cr.indeterminate[0].reason
    assert not report.ok


def test_unresolvable_upstream_address_is_indeterminate(health_repo) -> None:
    repo = health_repo(
        _UNIT_DEF_TEMPLATE.format(upstream="ghost:nowhere", trigger="implementation-ready")
    )
    report = ph.build_report(repo)
    cr = _the_contract(report)
    assert cr.indeterminate[0].subject is None
    assert "ghost:nowhere" in cr.indeterminate[0].reason
    assert not report.ok


# --- opt-in: entries without a contract are never evaluated ----------------


def test_entries_without_handoff_are_never_evaluated(health_repo) -> None:
    # The same coupling with NO handoff block, in a repo where every seam read
    # would error (no `_screens`, a BOOM screen): the check evaluates nothing,
    # runs nothing (the sentinel proves the candidates script never ran), and
    # exits clean — COR-038's inert contract preserved.
    repo = health_repo(_UNIT_INERT_DEF)
    (repo / "_screens").unlink()
    _add_screen(repo, "any")
    (repo / "_screen-any").write_text("BOOM", encoding="utf-8")
    (repo / "_screens").unlink()  # _add_screen recreated it; remove again
    report = ph.build_report(repo)
    assert report.contracts == ()
    assert report.ok
    assert not (repo / "_candidates-ran").exists()


# --- singleton endpoints participate (COR-042 point 2) ---------------------


def test_singleton_endpoints_participate(health_repo) -> None:
    repo = health_repo(include_pipeline=True)
    (repo / "_catalog").write_text("ready", encoding="utf-8")
    (repo / "_catalog-candidates").write_text("catalog\n", encoding="utf-8")
    report = ph.build_report(repo, focus="design:catalog")
    cr = _the_contract(report)
    assert (cr.contract.upstream, cr.contract.downstream) == (
        "design:catalog",
        "delivery:pipeline",
    )
    # The singleton's one subject at the trigger, unpicked: one miss.
    assert [f.subject for f in cr.misses] == ["catalog"]
    # Picked up: clean.
    _set_pickups(repo, {"catalog": ["pipeline"]})
    clean = ph.build_report(repo, focus="design:catalog")
    assert _the_contract(clean).findings == ()
    assert clean.ok


# --- the --process filter --------------------------------------------------


def test_focus_filters_to_contracts_touching_the_address(health_repo) -> None:
    repo = health_repo(include_pipeline=True)
    (repo / "_catalog-candidates").write_text("", encoding="utf-8")
    everything = ph.build_report(repo)
    assert len(everything.contracts) == 2
    upstream_focus = ph.build_report(repo, focus="design:screen")
    assert [c.contract.upstream for c in upstream_focus.contracts] == ["design:screen"]
    downstream_focus = ph.build_report(repo, focus="delivery:pipeline")
    assert [c.contract.downstream for c in downstream_focus.contracts] == [
        "delivery:pipeline"
    ]
    untouched = ph.build_report(repo, focus="no:such")
    assert untouched.contracts == ()


# --- --json: the byte-stable machine form ----------------------------------


def test_json_shape_and_totals(health_repo) -> None:
    repo = health_repo()
    _add_screen(repo, "s-1")
    _add_screen(repo, "s-2")
    _set_pickups(repo, {"s-2": ["unit-2"]})
    payload = json.loads(ph.render_json(ph.build_report(repo)))
    assert set(payload) == {"contracts", "skipped", "totals"}
    assert payload["totals"] == {"missed": 1, "indeterminate": 0}
    assert payload["skipped"] == []
    (contract,) = payload["contracts"]
    assert set(contract) == {
        "upstream",
        "downstream",
        "trigger",
        "state",
        "misses",
        "indeterminate",
        "counts",
    }
    assert contract["upstream"] == "design:screen"
    assert contract["downstream"] == "delivery:unit"
    assert contract["trigger"] == "implementation-ready"
    assert contract["state"] == "building"
    assert [m["subject"] for m in contract["misses"]] == ["s-1"]
    assert contract["counts"] == {
        "at_trigger": 2,
        "satisfied": 1,
        "missed": 1,
        "indeterminate": 0,
    }


def test_json_byte_stable_across_environment_and_runs(health_repo, monkeypatch) -> None:
    repo = health_repo()
    _add_screen(repo, "s-1")
    cli_render.set_color(False)
    cli_render.set_wrap_width(cli_render.NO_WRAP)
    baseline = ph.render_json(ph.build_report(repo))

    cli_render.set_color(True)
    cli_render.set_wrap_width(40)
    monkeypatch.setenv("COLUMNS", "40")
    styled = ph.render_json(ph.build_report(repo))

    assert styled == baseline
    assert "\033[" not in baseline
    assert ph.render_json(ph.build_report(repo)) == baseline


# --- ordering: topological over the wiring, deterministic ------------------

_CHAIN_PLAIN = """\
process:
  id: {pid}
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: only
      meaning: Only state.
      entry: true
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: chain-noop
  transitions: []
"""

_CHAIN_WITH_CONTRACT = """\
process:
  id: {pid}
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: only
      meaning: Only state.
      entry: true
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: chain-noop
      depends_on:
        - upstream: {upstream}
          relation: constrained-with
          mode: pull
          why: Chain coupling for the ordering pin.
          handoff:
            trigger: only
            candidates:
              run: chain-empty-candidates
            resolve:
              run: chain-noop
  transitions: []
"""

_CHAIN_EMPTY_CANDIDATES = (
    "import json\nprint(json.dumps({'candidates': [], 'reason': 'none'}))\n"
)


def _write_chain_repo(root: Path, processes: dict[str, str | None]) -> Path:
    """A `chain` capability whose processes optionally declare a contract on an
    upstream address. Candidate sets are determinate-empty (clean) — these
    fixtures pin ORDERING, not findings."""
    cap = root / ".pkit" / "capabilities" / "chain"
    cap.mkdir(parents=True, exist_ok=True)
    _write_package_yaml(
        cap,
        "chain",
        {
            "chain-noop": "scripts/chain_noop.py",
            "chain-empty-candidates": "scripts/chain_empty_candidates.py",
        },
    )
    (cap / "schemas").mkdir(parents=True, exist_ok=True)
    for pid, upstream in processes.items():
        body = (
            _CHAIN_PLAIN.format(pid=pid)
            if upstream is None
            else _CHAIN_WITH_CONTRACT.format(pid=pid, upstream=upstream)
        )
        (cap / "schemas" / f"{pid}.yaml").write_text(body, encoding="utf-8")
    _write_script(cap / "scripts" / "chain_noop.py", _NOOP)
    _write_script(cap / "scripts" / "chain_empty_candidates.py", _CHAIN_EMPTY_CANDIDATES)
    return root


def test_couplings_order_topologically_sources_first(tmp_path: Path) -> None:
    # a -> b (declared in b) and b -> c (declared in c): the upstream-most
    # coupling group renders first regardless of address sort order.
    repo = _write_chain_repo(
        tmp_path, {"alpha": "chain:beta", "beta": "chain:gamma", "gamma": None}
    )
    # Wiring: gamma -> beta (declared in beta), beta -> alpha (declared in
    # alpha). Sources first: the gamma-headed coupling precedes the beta one —
    # NOT plain address order (which would put alpha's declaration first).
    report = ph.build_report(repo)
    assert [
        (c.contract.upstream, c.contract.downstream) for c in report.contracts
    ] == [("chain:gamma", "chain:beta"), ("chain:beta", "chain:alpha")]
    assert report.ok


def test_declared_cycle_falls_back_to_name_order_deterministically(
    tmp_path: Path,
) -> None:
    # a depends on b AND b depends on a: no topological order exists; the
    # name-order fallback pins a deterministic report (and terminates).
    repo = _write_chain_repo(tmp_path, {"pong": "chain:ping", "ping": "chain:pong"})
    report = ph.build_report(repo)
    assert [
        (c.contract.upstream, c.contract.downstream) for c in report.contracts
    ] == [("chain:ping", "chain:pong"), ("chain:pong", "chain:ping")]
    assert ph.render_json(report) == ph.render_json(ph.build_report(repo))


# --- unreadable definitions are surfaced, fail-closed ----------------------


def test_unloadable_definition_counts_indeterminate(health_repo) -> None:
    # Two schema files claiming one process id: the definition cannot load, so
    # its contract set is UNKNOWN — surfaced and counted indeterminate (a green
    # report over it would lie), never silently dropped.
    repo = health_repo()
    dup = repo / ".pkit" / "capabilities" / "design" / "schemas"
    body = _CHAIN_PLAIN.format(pid="dup")
    (dup / "dup_a.yaml").write_text(body, encoding="utf-8")
    (dup / "dup_b.yaml").write_text(body, encoding="utf-8")
    report = ph.build_report(repo)
    assert [s.address for s in report.skipped] == ["design:dup"]
    assert report.indeterminate_total == 1
    assert not report.ok


# --- the CLI surface -------------------------------------------------------


def _invoke_health(repo: Path, monkeypatch, *args: str):
    monkeypatch.setattr("project_kit.process.resolve_repo_root", lambda: repo)
    return CliRunner().invoke(main, ["process", "health", *args])


def test_cli_exits_zero_when_clean(health_repo, monkeypatch) -> None:
    repo = health_repo()
    result = _invoke_health(repo, monkeypatch)
    assert result.exit_code == 0, result.output
    assert "0 missed, 0 indeterminate" in result.output


def test_cli_exits_non_zero_on_misses_with_flow_direction_header(
    health_repo, monkeypatch
) -> None:
    repo = health_repo()
    for i in range(1, 8):
        _add_screen(repo, f"screen-{i}")
    result = _invoke_health(repo, monkeypatch)
    assert result.exit_code == 1
    # Flow-direction header: upstream → downstream @trigger.
    assert "design:screen → delivery:unit" in result.output
    assert "@implementation-ready" in result.output
    assert result.output.count("✗") == 7
    assert "7 missed, 0 indeterminate" in result.output


def test_cli_exits_non_zero_on_indeterminate_alone(health_repo, monkeypatch) -> None:
    repo = health_repo(
        _UNIT_DEF_TEMPLATE.format(upstream="design:screen", trigger="phantom")
    )
    result = _invoke_health(repo, monkeypatch)
    assert result.exit_code == 1
    assert "contract indeterminate" in result.output
    assert "0 missed, 1 indeterminate" in result.output


def test_cli_json_flag_emits_machine_form(health_repo, monkeypatch) -> None:
    repo = health_repo()
    _add_screen(repo, "s-1")
    result = _invoke_health(repo, monkeypatch, "--json")
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["totals"] == {"missed": 1, "indeterminate": 0}


def test_cli_process_filter(health_repo, monkeypatch) -> None:
    repo = health_repo(include_pipeline=True)
    (repo / "_catalog-candidates").write_text("", encoding="utf-8")
    result = _invoke_health(repo, monkeypatch, "--process", "design:catalog", "--json")
    payload = json.loads(result.output)
    assert [c["upstream"] for c in payload["contracts"]] == ["design:catalog"]


def test_cli_reports_no_contracts_declared(health_repo, monkeypatch) -> None:
    repo = health_repo(_UNIT_INERT_DEF)
    result = _invoke_health(repo, monkeypatch)
    assert result.exit_code == 0
    assert "no hand-off contracts declared" in result.output


# --- the ADR-048 module boundary, pinned -----------------------------------


def test_runtime_engine_module_never_imports_health() -> None:
    """The mirror of the render's never-invokes-engine pin: the runtime engine
    module (`process.py` — status/can-move/move/validate live here) must import
    NOTHING from the health module, so 'the runtime position operations never
    read depends_on' stays structurally true by module boundary (ADR-048)."""
    src = Path(__file__).resolve().parents[1] / "src" / "project_kit" / "process.py"
    assert "process_health" not in src.read_text(encoding="utf-8")


def test_importing_runtime_surfaces_does_not_load_health_module() -> None:
    # In a FRESH interpreter, importing the engine and the full CLI module must
    # not pull the health module in — the CLI's health verb imports it lazily,
    # inside the command only.
    code = (
        "import sys\n"
        "import project_kit.process\n"
        "import project_kit.cli\n"
        "assert 'project_kit.process_health' not in sys.modules, "
        "'runtime surfaces must not import the health module'\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def test_health_is_report_only_never_moves_never_writes(
    health_repo, monkeypatch
) -> None:
    """Report-only (COR-042 point 3): the walk resolves positions and runs the
    two seam predicates but never validates/executes a move and writes nothing.
    Poison the engine's mutating/gating surfaces; snapshot the repo tree."""

    def _boom(*_args, **_kwargs):
        raise AssertionError("the health walk must not gate or move anything")

    monkeypatch.setattr(ProcessEngine, "move", _boom)
    monkeypatch.setattr(ProcessEngine, "can_move", _boom)
    monkeypatch.setattr(ProcessEngine, "precheck_transitions", _boom)

    repo = health_repo()
    for i in range(1, 4):
        _add_screen(repo, f"screen-{i}")
    before = {p for p in repo.rglob("*") if p.is_file()}
    report = ph.build_report(repo)
    after = {p for p in repo.rglob("*") if p.is_file()}
    assert report.missed_total == 3
    # The fixture's candidates sentinel is the one expected new file — written
    # by the BINDING's script, not by the health surface itself.
    assert after - before == {repo / "_candidates-ran"}
