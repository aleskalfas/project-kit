"""The carriage-flag guard — exactly one site derives CARRIAGE from the board flag.

[project-management:DEC-051-axis-carriage-activation] settles which substrate
carries a classification axis: the adopter's substrate-map governs the axes it
binds, and ``has_projects_v2_board`` governs only where the map is silent. Decision
point 4 makes that ONE composition — ``_lib/axis_carriage`` — "asked by every
writer, reader, prerequisite check and mutator, so no two consumers can form
different beliefs about where an axis lives". The record is explicit that without a
guard "point 4 is an assertion, not an invariant": the failure it exists to end is
DRIFT, and drift returns the moment a second consumer reads the flag and decides
for itself.

Why this is an allow-list and not a prohibition
-----------------------------------------------
A blanket "no script may read the flag" would be wrong twice over, and the record
says so. The flag keeps THREE legitimate jobs that have nothing to do with
carriage:

  * **Identity** — is a board configured, and what is its node id
    (``_lib/board_fields.board_number``, bootstrap's node-id cache).
  * **Membership** — every issue belongs on the configured board (DEC-019).
    Routing THAT through carriage "would silently drop the membership requirement
    for any board adopter who wrote a single label binding".
  * **Carriage where the map is silent** — retained deliberately to avoid a silent
    behaviour change, which is why the accessor itself reads the flag. A blanket
    prohibition would either fail on the accessor or be weakened to uselessness.

So the invariant is countable rather than absolute: **exactly one carriage site**,
and every other read named with the job it does. A new read of the flag fails this
test until its author adds it here with a reason — which is the point. If that
reason is "to decide which substrate carries an axis", the answer is no: call
``axis_carriage.carriage(axis, config, substrate_map)``.

The two halves
--------------
1. **Structural** (this file's first half) — the AST scan and the allow-list, so a
   new flag read cannot appear unnoticed.
2. **Behavioural** (second half) — the writers actually AGREE with the accessor on
   the reported configuration (board flag on, map binds the axis to labels). The
   structural half alone would pass on a verb that read the accessor and then
   ignored it.

Mutation-proof: reintroduce ``config.get("has_projects_v2_board")`` in any script
and the scan reports it; `test_guard_detects_a_reintroduced_flag_read` pins that
discriminating power in code.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

# The adopter config key. Duplicated (not imported) so the guard does not depend
# on the module it polices being importable.
FLAG = "has_projects_v2_board"

# The one site that may read the flag to answer WHERE AN AXIS LIVES.
CARRIAGE_ACCESSOR = "_lib/axis_carriage.py"

# Every file permitted to read the flag, with the count of reads and the job each
# does. A file absent from here fails; a count that no longer matches fails. Both
# failures mean the same thing: someone added a read of the board flag, and it has
# to be named before it can stay.
ALLOWED_READS: dict[str, tuple[int, str]] = {
    CARRIAGE_ACCESSOR: (
        1,
        "CARRIAGE — the single composition (DEC-051 decision point 4). The flag "
        "still governs where the map is silent, which is why the accessor reads "
        "it. This is the one entry that may say 'carriage'.",
    ),
    "_lib/board_fields.py": (
        1,
        "IDENTITY — `board_number` answers 'is a board configured, and which one', "
        "the read seam's own job. Routing it through carriage would make the board "
        "unreachable for an adopter with one label binding.",
    ),
    "bootstrap.py": (
        1,
        "IDENTITY — whether to resolve and cache `projects_v2_node_id` (#310). The "
        "label-palette decision beside it asks the accessor per axis.",
    ),
    "create-issue.py": (
        1,
        "MEMBERSHIP — the DEC-019 auto-add to the configured board, plus its "
        "pre-flight display line. Explicitly NOT carriage (DEC-051: 'board "
        "membership stays with the flag').",
    ),
    "pre-check.py": (
        4,
        "MIXED, and two of them are the deferred rewiring: board-id resolution "
        "(identity) and the `board:` arm's satisfiability + the absent-axis nudge "
        "(both statements ABOUT the flag, which is their subject). The carriage "
        "branches it threads into `_check_labels` / `_check_state_labels` are a "
        "READ-PATH gate, deliberately left for the commit that lands the repair "
        "path — rewiring them now would hard-reject every pre-existing issue with "
        "no tool to fix it.",
    ),
    "validate-issue.py": (
        1,
        "MIXED — one read serving the board-membership drift finding (DEC-019, "
        "must stay with the flag) and the classification presence gate. The gate "
        "half is the deferred read-path rewiring, for the same repair-path reason "
        "as pre-check.",
    ),
}


def _scanned_scripts() -> list[Path]:
    """Every `.py` under scripts/ (and `_lib/`). Scan-all: no file is exempt."""
    return [
        p
        for p in sorted(SCRIPTS.rglob("*.py"))
        if "__pycache__" not in p.parts
    ]


def _flag_read_lines(source: str) -> list[int]:
    """Line numbers where ``source`` READS the board flag out of a mapping.

    Two shapes, which is every way the tree reads adopter config: a
    ``.get("has_projects_v2_board"...)`` call and a ``[...]`` subscript. Prose is
    not matched — a docstring or comment naming the key is a reference, not a read,
    and the capability's records and remediations name it constantly.
    """
    tree = ast.parse(source)
    lines: list[int] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
        ):
            lines.extend(
                node.lineno
                for arg in node.args
                if isinstance(arg, ast.Constant) and arg.value == FLAG
            )
        elif isinstance(node, ast.Subscript):
            index = node.slice
            if isinstance(index, ast.Constant) and index.value == FLAG:
                lines.append(node.lineno)
    return sorted(lines)


@pytest.mark.parametrize(
    "path", _scanned_scripts(), ids=lambda p: str(p.relative_to(SCRIPTS))
)
def test_board_flag_reads_are_allow_listed(path: Path) -> None:
    """No pm script reads the board flag without a named, counted justification."""
    rel = str(path.relative_to(SCRIPTS))
    found = _flag_read_lines(path.read_text(encoding="utf-8"))
    expected, reason = ALLOWED_READS.get(rel, (0, ""))

    if not found and not expected:
        return
    assert found, (
        f"{rel}: allow-listed for {expected} read(s) of `{FLAG}` but has none. "
        f"If the read was removed (good), remove its entry from ALLOWED_READS."
    )
    assert rel in ALLOWED_READS, (
        f"{rel}:{found[0]}: reads `{FLAG}`, which is not allow-listed. If this "
        f"read decides WHICH SUBSTRATE CARRIES AN AXIS, it must not exist — call "
        f"`axis_carriage.carriage(axis, config, substrate_map)` instead "
        f"([project-management:DEC-051-axis-carriage-activation] decision point "
        f"4). If it is board IDENTITY or MEMBERSHIP, add it to ALLOWED_READS with "
        f"the job it does."
    )
    assert len(found) == expected, (
        f"{rel}: {len(found)} read(s) of `{FLAG}` at lines {found}, "
        f"allow-listed for {expected} ({reason}). A NEW read here needs the same "
        f"scrutiny as a new file: if it derives carriage, use "
        f"`axis_carriage.carriage(...)`; if not, raise the count and say why."
    )


def test_exactly_one_site_derives_carriage_from_the_flag() -> None:
    """The countable form of DEC-051 decision point 4, as a single assertion."""
    carriage_entries = [
        rel for rel, (_n, reason) in ALLOWED_READS.items() if "CARRIAGE" in reason
    ]
    assert carriage_entries == [CARRIAGE_ACCESSOR]
    assert ALLOWED_READS[CARRIAGE_ACCESSOR][0] == 1


def test_guard_detects_a_reintroduced_flag_read() -> None:
    """Mutation proof: the scan sees a reintroduced read, in either shape."""
    assert _flag_read_lines('x = config.get("has_projects_v2_board", False)\n') == [1]
    assert _flag_read_lines('if config["has_projects_v2_board"]:\n    pass\n') == [1]
    # Prose naming the key is not a read.
    assert _flag_read_lines('"""Set has_projects_v2_board: true."""\n') == []


def test_the_seam_never_calls_the_carriage_accessor() -> None:
    """The one-way layering [pkit:ADR-026] pins and [pkit:ADR-053] restates:
    carriage calls the seams, and no seam calls carriage. An edge the other way
    would invert the composition ordering — the shape of the original failure."""
    for module in ("_lib/axis_labels.py", "_lib/board_fields.py"):
        source = (SCRIPTS / module).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert "axis_carriage" not in imported, (
            f"{module} imports the carriage accessor — the layering runs one way "
            f"only (carriage → seam)."
        )


# --- behavioural: the writers agree with the accessor ------------------------
#
# The reported configuration (#708): `has_projects_v2_board: true` while the map
# binds `priority` (and here `state`) to the adopter's own labels. Each writer used
# to resolve board-versus-label FIRST and reach the seam only in its no-board
# branch, so the binding was never consulted and the value landed nowhere. These
# assert the one answer reaches all three verbs — the property the structural half
# cannot see.


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def scripts():
    return {
        "create_issue": _load("pm_carriage_create_issue", "create-issue.py"),
        "set_field": _load("pm_carriage_set_field", "set-field.py"),
        "move_issue": _load("pm_carriage_move_issue", "move-issue.py"),
        "self_test": _load("pm_carriage_self_test", "self-test.py"),
    }


@pytest.fixture(scope="module")
def axis_labels(scripts):
    return scripts["create_issue"].axis_labels


BOARD_CONFIG = {"has_projects_v2_board": True, "projects_v2_board_id": 7}


@pytest.fixture
def label_bound_map(axis_labels):
    """The reported adopter's shape: a board configured, and the map binding the
    axes to the repo's own labels."""
    return axis_labels.SubstrateMap(
        axes={
            "priority": {"label": {"remap": {"High": "P0"}}},
            "state": {"label": {"remap": {"backlog": "Ready", "todo": "Inbox"}}},
        }
    )


def test_create_issue_writes_the_bound_label_under_a_board(
    scripts, label_bound_map
) -> None:
    labels, _advisories, resolved = scripts["create_issue"]._build_labels(
        kind="feature",
        priority="High",
        workstream=None,
        config=BOARD_CONFIG,
        substrate_map=label_bound_map,
    )
    assert resolved["priority"] == "P0"
    assert "P0" in labels


def test_set_field_routes_the_bound_axis_to_labels_under_a_board(
    scripts, label_bound_map
) -> None:
    label_axes, board_axes, results = scripts["set_field"]._route_axes(
        priority="High",
        workstream=None,
        config=BOARD_CONFIG,
        substrate_map=label_bound_map,
    )
    assert label_axes == {"priority": "High"}
    assert board_axes == {} and results == []


def test_move_issue_writes_the_bound_state_label_under_a_board(
    scripts, label_bound_map
) -> None:
    """And it strips the adopter's OWN stale label — a prefix-only search would
    leave `Inbox` behind beside the new `Ready`."""
    mi = scripts["move_issue"]
    plan = mi._compute_plan(
        issue_number=42,
        current_state="todo",
        target_state="backlog",
        state_on_board=mi.axis_carriage.is_board_carried(
            "state", BOARD_CONFIG, label_bound_map
        ),
        labels=["Inbox", "type:bug"],
        substrate_map=label_bound_map,
    )
    assert plan.add_label == "Ready"
    assert plan.remove_label == "Inbox"


def test_self_test_seeds_no_label_for_a_board_carried_axis(scripts, tmp_path) -> None:
    """The live bug: `priority` was resolved unconditionally, outside the guard
    that wrapped `state`. On a greenfield board adopter that produced the kit's
    `priority:Low` — a label bootstrap deliberately did not create — so
    `gh issue create` failed on a label that does not exist."""
    assert scripts["self_test"]._seed_labels(tmp_path, BOARD_CONFIG) == []


def test_self_test_seeds_the_kit_labels_in_greenfield(scripts, tmp_path) -> None:
    """Greenfield is unchanged: both axes are kit-label-carried and both seed."""
    assert scripts["self_test"]._seed_labels(tmp_path, {}) == [
        "priority:Low",
        "state:todo",
    ]
