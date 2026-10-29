"""The carriage accessor's truth table, purity, and layering.

`_lib/axis_carriage` is the single composition answering *which substrate carries
this axis* — "ask the map" ([project-management:DEC-062-axes-chosen-in-the-map]
point 1, over [project-management:DEC-051-axis-carriage-activation] decision
points 1 and 4). It exists because the answer used to be derivable from two files
that could not see each other, so a writer and a reader could each be locally
correct and still disagree: the filing verb honoured the board flag and wrote no
label, nothing wrote the board field, and the reviewer resolved through the map
and found nothing (#708).

Three properties are pinned here, and each has a distinct failure mode.

**The truth table**, because a wrong cell is a silent mis-write rather than a
crash. The board flag carries no axis: an axis is on the board only where the
map binds it there, an axis absent from a present map degrades board or no
board, and a `kit-label` axis reads as it does with no map.

**Purity**, because the whole carriage rewiring across the verb family is only
safe if asking "where does this live?" cannot fail. Every verb asks it; only a
few ever need a board value. If this module could perform I/O, a board outage
would become a filing outage on paths that never touch a board
([pkit:ADR-053], decision point 1).

**The one-way layering** — carriage calls the label seam, and the seam never
calls carriage. An import cycle here would invert the composition ordering
[pkit:ADR-026] pins, which is the shape of the original failure.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB_DIR = SCRIPTS_DIR / "_lib"


@pytest.fixture(scope="module")
def mod():
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        from _lib import axis_carriage, axis_labels

        yield axis_carriage, axis_labels
    finally:
        sys.path.remove(str(SCRIPTS_DIR))


BOARD = {"has_projects_v2_board": True, "projects_v2_board_id": 2}
NO_BOARD = {"has_projects_v2_board": False}


def _map(axes, axis_labels):
    return axis_labels.SubstrateMap(axes=axes)


# --- the truth table --------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "axis", "config", "axes", "expected"),
    [
        # No map at all: the kit's own labels carry every axis, board or no
        # board. The flag says only that a board exists (DEC-062 point 1).
        ("no map, no board", "priority", NO_BOARD, None, "kit-label"),
        ("no map, a board carries nothing", "priority", BOARD, None, "kit-label"),
        ("no map, workstream under a board", "workstream", BOARD, None, "kit-label"),
        ("no map, state under a board", "state", BOARD, None, "kit-label"),
        ("type with no map", "type", BOARD, None, "kit-label"),
        # A binding governs. This row IS the reported failure: board
        # configured, priority label-bound.
        (
            "label binding under a board",
            "priority",
            BOARD,
            {"priority": {"label": {"remap": {"High": "P0"}}}},
            "adopter-label",
        ),
        (
            "board binding under a board",
            "priority",
            BOARD,
            {"priority": {"board": True}},
            "board",
        ),
        (
            "board binding on state",
            "state",
            BOARD,
            {"state": {"board": True}},
            "board",
        ),
        # The map alone answers: a `board: true` binding under a config with no
        # board is still `board`. The prerequisite check refuses the pair, and
        # a consumer reading the board fails on it ([pkit:ADR-053] point 2).
        (
            "board binding with no board configured",
            "workstream",
            NO_BOARD,
            {"workstream": {"board": True}},
            "board",
        ),
        (
            "kit-label binding",
            "workstream",
            BOARD,
            {"workstream": {"kit-label": True}},
            "kit-label",
        ),
        (
            "title-prefix binding",
            "type",
            BOARD,
            {"type": {"title-prefix": {"remap": {"task": "[Task]"}}}},
            "title",
        ),
        (
            "derive binding",
            "state",
            BOARD,
            {"state": {"derive": {"states": {"open": "issue is open"}}}},
            "derived",
        ),
        # `unsupported` names NO substrate: it degrades, as an omitted axis
        # does, board or no board (DEC-062 point 2).
        (
            "unsupported degrades under a board",
            "priority",
            BOARD,
            {"priority": {"unsupported": True}},
            "degrade",
        ),
        (
            "unsupported with no board degrades",
            "priority",
            NO_BOARD,
            {"priority": {"unsupported": True}},
            "degrade",
        ),
        (
            "unsupported on a non-board axis degrades",
            "type",
            BOARD,
            {"type": {"unsupported": True}},
            "degrade",
        ),
        # Absent from a PRESENT map: degrade, board or no board. A board's
        # existence carries no axis.
        (
            "absent from present map under a board degrades",
            "workstream",
            BOARD,
            {"priority": {"board": True}},
            "degrade",
        ),
        (
            "absent from present map, no board, degrades",
            "workstream",
            NO_BOARD,
            {"priority": {"label": {"remap": {"High": "P0"}}}},
            "degrade",
        ),
        (
            "type absent from present map degrades",
            "type",
            BOARD,
            {"priority": {"board": True}},
            "degrade",
        ),
        # A binding matching no known arm is malformed and fails closed rather
        # than falling back to a label the adopter may not have.
        (
            "malformed binding fails closed",
            "priority",
            BOARD,
            {"priority": {"nonsense": True}},
            "degrade",
        ),
    ],
)
def test_carriage_truth_table(mod, case, axis, config, axes, expected):
    axis_carriage, axis_labels = mod
    smap = _map(axes, axis_labels) if axes is not None else None
    assert axis_carriage.carriage(axis, config, smap) == expected, case


def test_carriage_returns_a_closed_set(mod):
    """Never a bare boolean.

    A board/not-board boolean would re-create the ordering inversion in a form a
    flag-read guard cannot see: a consumer with a `False` arm still has to ask
    the seam to be correct. `False` is also ambiguous between "the kit's own
    label" and "nothing carries it", which are opposite instructions to a
    presence gate.
    """
    axis_carriage, axis_labels = mod
    allowed = {"kit-label", "adopter-label", "title", "derived", "board", "degrade"}
    for axis in ("type", "priority", "workstream", "state"):
        for config in (BOARD, NO_BOARD, None):
            for smap in (
                None,
                _map({}, axis_labels),
                _map({axis: {"board": True}}, axis_labels),
                _map({axis: {"unsupported": True}}, axis_labels),
            ):
                got = axis_carriage.carriage(axis, config, smap)
                assert got in allowed
                assert not isinstance(got, bool)


# --- the scoping predicate --------------------------------------------------


def test_is_board_carried_scopes_the_raise(mod):
    """The predicate that scopes "an unreadable board raises".

    It must be answerable WITHOUT performing a board read, or the scoping rule
    is circular — you would have to read the board to learn whether reading the
    board was expected ([pkit:ADR-053], decision point 3).
    """
    axis_carriage, axis_labels = mod
    on_board = _map({"priority": {"board": True}}, axis_labels)
    assert axis_carriage.is_board_carried("priority", BOARD, on_board) is True
    # The flag alone puts no axis on the board (DEC-062 point 1).
    assert axis_carriage.is_board_carried("priority", BOARD, None) is False
    assert axis_carriage.is_board_carried("type", BOARD, None) is False
    label_bound = _map({"priority": {"label": {"remap": {"High": "P0"}}}}, axis_labels)
    assert axis_carriage.is_board_carried("priority", BOARD, label_bound) is False


def test_expects_kit_labels_with_no_map_or_a_kit_label_binding(mod):
    """A presence gate may demand `priority:High` only where the kit's labels
    carry the axis: no map, or `kit-label: true` (DEC-062 points 3 and 4)."""
    axis_carriage, axis_labels = mod
    assert axis_carriage.expects_kit_labels("priority", NO_BOARD, None) is True
    assert axis_carriage.expects_kit_labels("priority", BOARD, None) is True
    kit = _map({"priority": {"kit-label": True}}, axis_labels)
    assert axis_carriage.expects_kit_labels("priority", BOARD, kit) is True
    # The map's other axes are absent, and degrade: a map carries nothing beyond
    # its bindings.
    assert axis_carriage.expects_kit_labels("workstream", BOARD, kit) is False
    present = _map({"priority": {"label": {"remap": {"High": "P0"}}}}, axis_labels)
    assert axis_carriage.expects_kit_labels("priority", NO_BOARD, present) is False


def test_a_map_binding_every_axis_to_the_kit_labels_behaves_as_no_map(mod):
    """DEC-062 point 4: a map whose every binding is `kit-label` answers as no
    map, for every axis and every config."""
    axis_carriage, axis_labels = mod
    all_kit = _map(
        {axis: {"kit-label": True} for axis in ("type", "priority", "workstream", "state")},
        axis_labels,
    )
    for axis in ("type", "priority", "workstream", "state"):
        for config in (BOARD, NO_BOARD, None):
            assert axis_carriage.carriage(axis, config, all_kit) == axis_carriage.carriage(
                axis, config, None
            )


# --- purity and layering ----------------------------------------------------


def test_carriage_module_performs_no_io():
    """Structural, not behavioural: the module may not import an I/O surface.

    Asserted by AST rather than by mocking, because the property must hold for
    code paths no test exercises. If this ever needs relaxing, the carriage
    rewiring across the verb family stops being safe — see the module docstring.
    """
    tree = ast.parse((LIB_DIR / "axis_carriage.py").read_text(encoding="utf-8"))
    forbidden = {"subprocess", "requests", "urllib", "http", "socket", "shutil"}
    forbidden_local = {"board_fields", "gh"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in forbidden, f"carriage imports I/O module {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root not in forbidden, f"carriage imports I/O module {node.module}"
            for alias in node.names:
                assert alias.name not in forbidden_local, (
                    f"carriage imports the board read seam ({alias.name}) — "
                    "carriage must answer where an axis lives without reading it"
                )


def test_seam_never_imports_carriage():
    """One-way layering: carriage calls the seam, never the reverse.

    A cycle here would invert the composition ordering ADR-026 pins — the
    adopter-binding question resolving first — which is the shape of the failure
    this work exists to end.
    """
    tree = ast.parse((LIB_DIR / "axis_labels.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""] + [a.name for a in node.names]
        for name in names:
            assert "axis_carriage" not in name, (
                "the label seam imports the carriage accessor — layering inverted"
            )


def test_unsupported_is_equivalent_to_omission(mod):
    """The schema's stated equivalence, pinned as a property rather than a row.

    `unsupported: true` is defined as "equivalent to omitting the axis from a
    present map". Carriage must honour that for every axis and every config, or
    the map means two different things depending on whether the adopter wrote
    the key.
    """
    axis_carriage, axis_labels = mod
    other = {"type": {"title-prefix": {"remap": {"task": "[Task]"}}}}
    for axis in ("priority", "workstream", "state"):
        for config in (BOARD, NO_BOARD, None):
            explicit = _map({**other, axis: {"unsupported": True}}, axis_labels)
            omitted = _map(dict(other), axis_labels)
            assert axis_carriage.carriage(axis, config, explicit) == axis_carriage.carriage(
                axis, config, omitted
            ), f"{axis} under {config}: explicit-unsupported diverged from omitted"
