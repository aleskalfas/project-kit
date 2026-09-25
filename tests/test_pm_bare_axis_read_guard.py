"""The bare-axis-read guard — every ``axis_labels.read(`` outside the seam is reviewed.

``axis_labels.read(axis, labels)`` is the greenfield arm of the read seam: a scan
for the kit's own ``<axis>:`` label prefix. It knows nothing of the adopter's
substrate map, so a caller that reaches for it directly reads an axis the map
remaps to the adopter's own labels as ABSENT (#910 — ``context-workstream``
printed nothing for a plainly-set remapped workstream).

``_lib/axis_carriage`` states that it is "consulted by every writer, reader,
prerequisite check and mutator"
([project-management:DEC-051-axis-carriage-activation] decision point 4). A new
bare read makes that statement silently false again, and nothing downstream
notices — the read degrades to "absent", which every caller already tolerates.

Why an allow-list and not a prohibition
---------------------------------------
A bare read is CORRECT where the caller has already established that the kit's
own labels are the substrate — inside a ``carriage(...) == "kit-label"`` branch,
behind a ``substrate_map is None`` short-circuit, or over labels already
normalised to the kit vocabulary. Forbidding those would force a redundant
map lookup on paths that have already asked. So the invariant is countable: each
file's bare reads are named, counted, and justified. A new one fails until its
author either routes it through the map — ``axis_labels.resolve_read(axis,
labels, substrate_map)``, or ``axis_carriage.carriage(...)`` where the caller
needs more than the label arm — or adds it here with the reason it is safe.

``_lib/axis_labels.py`` is excluded by name: it defines ``read`` and its own
``resolve_read`` calls it as the no-map arm, which is the seam working.

Mutation-proof: ``test_guard_detects_a_bare_read`` pins that the scan sees the
call shape and ignores prose and the map-aware reader.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

# The seam module itself — the definition of `read` and its no-map caller.
EXCLUDED = {SCRIPTS / "_lib" / "axis_labels.py"}

# Every file permitted a bare `axis_labels.read(` call, with the count and the
# reason the kit's own prefix is the right thing to read there. Keep this small:
# an entry is a claim that the caller already knows the kit labels carry the axis.
ALLOWED_BARE_READS: dict[str, tuple[int, str]] = {
    "validate-issue.py": (
        1,
        "the kind read for the DEC-011 kind/structural cross-check sits inside "
        "the `axis_carriage.carriage('type', ...) == 'kit-label'` branch, so the "
        "kit's `type:*` label is established as the substrate before it is read.",
    ),
    "_lib/structural_type.py": (
        1,
        "`structural_type_from_kind_label` is reached only from "
        "`infer_structural_type`'s last fallback, AFTER its `substrate_map is not "
        "None` short-circuit returns — i.e. greenfield only.",
    ),
    "_lib/pr_validation.py": (
        1,
        "`_expected_conv_types` parses labels its caller has ALREADY resolved "
        "through carriage and expressed in the kit vocabulary (validate-pr's "
        "`_gather_closing_type_labels`); open-pr and review-work pass `[]`.",
    ),
}


def _scanned_scripts() -> list[Path]:
    return [
        p
        for p in sorted(SCRIPTS.rglob("*.py"))
        if p not in EXCLUDED and "__pycache__" not in p.parts
    ]


def _bare_read_lines(source: str) -> list[int]:
    """Line numbers of every ``axis_labels.read(...)`` CALL in ``source``.

    Matches the call node, so a docstring or comment naming the function (the
    tree does so often, to explain the arms) is not counted, and
    ``axis_labels.resolve_read`` / ``read_all`` are different attributes.
    """
    lines: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "read"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "axis_labels"
        ):
            lines.append(node.lineno)
    return sorted(lines)


@pytest.mark.parametrize(
    "path", _scanned_scripts(), ids=lambda p: str(p.relative_to(SCRIPTS))
)
def test_bare_axis_reads_are_allow_listed(path: Path) -> None:
    """No pm script reads an axis by the bare kit prefix without a named reason."""
    rel = str(path.relative_to(SCRIPTS))
    found = _bare_read_lines(path.read_text(encoding="utf-8"))
    expected, reason = ALLOWED_BARE_READS.get(rel, (0, ""))

    if not found and not expected:
        return
    assert found, (
        f"{rel}: allow-listed for {expected} bare `axis_labels.read(` call(s) but "
        "has none. If the read was removed or routed through the map (good), "
        "remove its entry from ALLOWED_BARE_READS."
    )
    assert rel in ALLOWED_BARE_READS, (
        f"{rel}:{found[0]}: bare `axis_labels.read(` reads the axis by the kit's "
        "own prefix and misses a label the adopter's substrate map remaps (#910). "
        "Read through the map with `axis_labels.resolve_read(axis, labels, "
        "substrate_map)` (or branch on `axis_carriage.carriage(...)`). If the "
        "caller has already established the kit labels as the substrate, add it "
        "to ALLOWED_BARE_READS with that reason."
    )
    assert len(found) == expected, (
        f"{rel}: {len(found)} bare `axis_labels.read(` call(s) at lines {found}, "
        f"allow-listed for {expected} ({reason}). A new one needs the same "
        "scrutiny as a new file."
    )


def test_allow_list_names_only_existing_files() -> None:
    """A stale entry (file renamed or deleted) is caught rather than lingering."""
    for rel in ALLOWED_BARE_READS:
        assert (SCRIPTS / rel).is_file(), f"ALLOWED_BARE_READS names missing {rel}"


def test_guard_detects_a_bare_read() -> None:
    """Mutation proof: the call is seen; prose and the map-aware readers are not."""
    assert _bare_read_lines('v = axis_labels.read("workstream", labels)\n') == [1]
    assert _bare_read_lines(
        'v = axis_labels.resolve_read("workstream", labels, substrate_map)\n'
    ) == []
    assert _bare_read_lines('vs = axis_labels.read_all("type", labels)\n') == []
    assert _bare_read_lines('"""Greenfield uses `axis_labels.read("type", x)`."""\n') == []
