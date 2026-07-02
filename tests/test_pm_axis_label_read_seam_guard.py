"""The read-side seam guard — the complement to the sole-constructor guard.

[ADR-026](../docs/architecture/decisions/ADR-026-substrate-map-read-path-contract.md)
makes ``_lib/axis_labels`` (and the classification-table readers layered on it)
the seam through which methodology axes are *read* as well as written. The
sole-constructor guard (`test_pm_axis_label_seam_guard`) polices the WRITE side —
no script may *construct* an ``<axis>:<value>`` label inline. But it deliberately
*exempts* a complete ``"type:feature"`` literal appearing as a **dict key**
(``TYPE_LABEL_TO_PREFIX``-style read-maps), because a key literal is not a label
coming into being.

That exemption left a hole on the READ side. A script could — and two did
(``start-work`` and ``review-work``, one a silent verbatim copy of the other) —
derive a branch's Conventional-Commits type by looking a raw ``type:*`` label up
in a private ``{"type:bug": "fix", ...}`` dict, bypassing the seam entirely. In a
brownfield substrate the kind lives in the ``[Bug]`` title prefix and NO
``type:*`` label exists, so every such lookup returns nothing and the verb breaks
for every brownfield adopter (Task #442).

This guard closes that hole structurally, so a third copy cannot silently
reappear: no script under the capability's ``scripts/`` tree may contain a **dict
literal keyed on ``type:*`` (or any ``<axis>:``) string literals**. That shape is
the signature of a raw-label read-map; the value must be read through the seam
(``axis_labels.read("type", labels)`` on the label arm,
``classification_rules.kind_from_title`` on the title-prefix arm) and mapped
through ``classification_rules.conv_type_for_kind`` (the single ``pr_type_mapping``
reader) instead.

Excluded from the scan:
  * ``_lib/axis_labels.py`` — the seam module itself (the sole legitimate place
    axis-prefix strings live).
  * ``_lib/classification_rules.py`` — the single reader of the classification
    tables; it names ``pr_type_mapping`` / ``title_prefix_by_value`` fields, not
    ``<axis>:`` label keys, so it does not match anyway, but it is excluded by
    name so the guard does not lean on that.

Mutation-proof: reintroduce a ``{"type:bug": "fix"}`` read-map in any script and
this test goes red; route the read through the seam + shared reader and it goes
green. `test_read_guard_detects_a_reintroduced_read_map` pins that discriminating
power in code.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

# Mirrors `_lib/axis_labels.AXES` — duplicated (not imported) so the guard does
# not depend on the module it polices being importable.
AXES = ("type", "priority", "workstream", "state")
PREFIXES = tuple(f"{axis}:" for axis in AXES)

# The two legitimate homes of the seam / its table readers. `axis_labels` builds
# labels with a dynamic axis (never a `<axis>:<value>` key); `classification_rules`
# reads `pr_type_mapping` / `title_prefix_by_value` by field name. Neither carries
# a raw-label read-map; both are excluded by name so the guard does not lean on
# their internal shape.
EXCLUDED = {
    SCRIPTS / "_lib" / "axis_labels.py",
    SCRIPTS / "_lib" / "classification_rules.py",
}


def _scanned_scripts() -> list[Path]:
    return [
        p
        for p in sorted(SCRIPTS.rglob("*.py"))
        if p not in EXCLUDED and "__pycache__" not in p.parts
    ]


def _axis_prefix_of(text: str) -> str | None:
    """The axis prefix ``text`` is a full ``<axis>:<value>`` label literal for,
    else None. Bare prefixes (``"type:"``), globs (``"type:*"``), and prose are
    NOT full labels and do not match — this hunts the *read-map key* shape."""
    for prefix in PREFIXES:
        if not text.startswith(prefix):
            continue
        value = text[len(prefix):]
        if value and not any(c.isspace() for c in value) and "*" not in value:
            return prefix
    return None


def _dict_keyed_on_axis_labels(node: ast.Dict) -> str | None:
    """The axis prefix a dict is keyed on when *every* string key is a full
    ``<axis>:<value>`` label literal on the same axis, else None.

    Requiring *all* string keys to be axis-label literals (not merely one) is
    what distinguishes a raw-label read-map (``{"type:bug": "fix", ...}``, the
    Task #442 bypass) from an ordinary dict that happens to carry one such string
    among unrelated keys."""
    string_keys = [
        k for k in node.keys
        if isinstance(k, ast.Constant) and isinstance(k.value, str)
    ]
    if not string_keys:
        return None
    prefixes = {_axis_prefix_of(k.value) for k in string_keys}
    if len(prefixes) == 1 and None not in prefixes:
        return next(iter(prefixes))
    return None


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            prefix = _dict_keyed_on_axis_labels(node)
            if prefix is not None:
                out.append(
                    f"{path.name}:{node.lineno}: dict keyed on `{prefix}` axis-label "
                    "literals is a raw-label read-map that bypasses the ADR-026 read "
                    "seam (read the value via axis_labels.read / "
                    "classification_rules.kind_from_title, then map it through "
                    "classification_rules.conv_type_for_kind)"
                )
    return out


@pytest.mark.parametrize(
    "path", _scanned_scripts(), ids=lambda p: str(p.relative_to(SCRIPTS))
)
def test_no_raw_axis_label_read_map(path: Path) -> None:
    """No pm script derives an axis value from a raw ``<axis>:*`` read-map dict —
    the read must go through the seam (ADR-026 read path). This is the guard that
    would have caught review-work's silent copy of start-work's bypass."""
    violations = _violations(path)
    assert not violations, (
        "raw-label read-map bypasses the ADR-026 read seam:\n  "
        + "\n  ".join(violations)
    )


def test_scan_covers_the_two_work_wrappers() -> None:
    """start-work / review-work — the scripts that carried the bypass — are in the
    scanned set, and the seam + table-reader modules are excluded."""
    scanned = {p.name for p in _scanned_scripts()}
    assert "start-work.py" in scanned
    assert "review-work.py" in scanned
    assert "axis_labels.py" not in scanned
    assert "classification_rules.py" not in scanned


def test_read_guard_detects_a_reintroduced_read_map(tmp_path: Path) -> None:
    """Mutation-proof: a script with a ``{"type:bug": "fix"}`` read-map is flagged;
    the seam-routed form (no such dict) is not."""
    bad = tmp_path / "bad.py"
    bad.write_text(
        'TYPE_LABEL_TO_PREFIX = {\n'
        '    "type:feature": "feat",\n'
        '    "type:bug": "fix",\n'
        '}\n',
        encoding="utf-8",
    )
    assert _violations(bad), "guard failed to flag a reintroduced raw-label read-map"

    good = tmp_path / "good.py"
    good.write_text(
        'kind = axis_labels.read("type", labels)\n'
        'prefix = classification_rules.conv_type_for_kind(kind, classification)\n',
        encoding="utf-8",
    )
    assert not _violations(good), "guard wrongly flagged the seam-routed read"


def test_read_guard_exempts_ordinary_and_pr_type_mapping_shapes(tmp_path: Path) -> None:
    """A dict that is NOT wholly keyed on axis-label literals is exempt: an
    ordinary config dict, and the seam-legitimate `pr_type_mapping` shape (a list
    of dicts keyed on plain field names like `issue_label_value`) — the very shape
    the fix routes through — must not trip the guard."""
    ordinary = tmp_path / "ordinary.py"
    ordinary.write_text(
        'cfg = {"base": "main", "draft": False, "type:bug": "fix"}\n',  # mixed keys
        encoding="utf-8",
    )
    assert not _violations(ordinary), (
        "guard wrongly flagged a dict with only one axis-label key among plain keys"
    )

    mapping = tmp_path / "mapping.py"
    mapping.write_text(
        'PR_TYPE_MAPPING = [\n'
        '    {"issue_label_value": "bug", "pr_conv_type": "fix"},\n'
        '    {"issue_label_value": "feature", "pr_conv_type": "feat"},\n'
        ']\n',
        encoding="utf-8",
    )
    assert not _violations(mapping), (
        "guard wrongly flagged the seam-legitimate pr_type_mapping shape"
    )
