"""The sole-constructor guard — ADR-026 part (b), the structural half.

[ADR-026](../docs/architecture/decisions/ADR-026-substrate-map-read-path-contract.md)
makes "never write an unmanaged label" structural by requiring that the
``_lib/axis_labels`` seam be the **sole constructor** of any methodology
axis-label (``type:`` / ``priority:`` / ``workstream:`` / ``state:``). A script
that string-formats ``<axis>:<value>`` itself routes *around* the seam, so the
seam's fail-closed posture (and, in Task B, its substrate-map resolution) cannot
constrain it (ADR-026 part (i)).

This guard is the regression net for that invariant — the direct analogue of
ADR-024's "``render_status_json`` never calls ``wrap()``" byte-stability test
(`test_cli_render_wrap` references it): there, the byte-test only holds *because*
a structural check forbids the unsafe call from reaching the protected surface;
here, the parity test (`test_pm_axis_label_seam_parity`) only stays meaningful
*because* this guard forbids inline axis-label construction from reappearing.
Without this half, parity would pass while an inline-construction site quietly
bypassed the seam.

Scan-all, not an allow-list
---------------------------
The guard AST-scans **every** ``.py`` under the capability's ``scripts/`` tree
(and ``_lib/``) except the seam module itself — there is no hand-maintained
``MUTATING_SCRIPTS`` list to drift out of date. Any newly added script, and
every currently-omitted write path (``pre-check``, ``promote-issue``,
``close-issue``, ``reopen-issue``, …), is covered by construction. The only
exclusion is the seam module ``_lib/axis_labels.py``: it is the one legitimate
constructor and *must* format ``<axis>:<value>``. It is excluded by name (rather
than relying on the dynamic-axis shape carve-out) so the guard does not depend on
the seam keeping a particular internal shape.

The shape-vs-intent discriminator (resolves WR-1)
-------------------------------------------------
Scan-all forces an explicit ruling on which *shapes* are constructions. The rule
this guard enforces, uniformly across display and write sites:

  An **axis prefix combined with a value** is a construction → it must go through
  the seam → flag it ANYWHERE it appears outside the seam. A displayed
  ``f"state:{x}"`` is as much a construction as a written one — and in Task B the
  displayed label must reflect the seam's substrate-map mapping, not the raw
  value, so display sites route through the seam too.

  A shape that does **not** combine a prefix with a value is **not** a
  construction and is exempt:
    * a **glob** — ``"state:*"`` (prose / filter pattern, no value);
    * a **bare prefix** — ``"type:"`` (a read key, ``startswith`` / ``removeprefix``);
    * a **complete static read-key literal used for lookup** — a full
      ``"type:feature"`` literal appearing as a *dict key* (the
      ``TYPE_LABEL_TO_PREFIX`` maps in start-work / review-work, G-2). These are
      reads against the greenfield encoding, carry their own Task-B markers, and
      are not new labels coming into being. A full literal used as a *value*
      (assigned, appended, passed) is still flagged — it is a construction.

The construction shapes the guard detects:
  * **f-string interpolation** — literal text ending in ``<axis>:`` immediately
    before a ``{...}`` (the ``f"type:{x}"`` shape);
  * **concatenation** — ``BinOp``/``Add`` whose left operand is a ``Constant``
    ending in ``<axis>:`` (the ``"type:" + v`` shape, RF-1);
  * **``str.join``** — ``sep.join([...])`` where ``sep`` ends in / is an axis
    prefix, or an element ends in one (a ``":".join(["type", v])`` shape);
  * **``str.format``** — a format template whose literal text places a ``{}``
    field immediately after ``<axis>:`` (the ``"type:{}".format(v)`` shape);
  * **bare full literal used as a value** — ``"type:maintenance"`` outside a
    dict-key position.

Mutation-proof: reintroduce ``labels = [f"type:{args.kind}"]`` in ``create-issue``
or ``f"missing: {'type:' + v}"`` in ``pre-check`` and this test goes red; route it
back through ``axis_labels.label`` and it goes green. The concatenation detector
is mutation-proved in code by `test_guard_detects_a_reintroduced_concatenation`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

# The four methodology axes encoded as `<axis>:<value>` labels. Mirrors
# `_lib/axis_labels.AXES`; duplicated here (not imported) so the guard does not
# depend on the very module it polices being importable.
AXES = ("type", "priority", "workstream", "state")
PREFIXES = tuple(f"{axis}:" for axis in AXES)

# The one allow-listed constructor — the seam itself legitimately formats
# `<axis>:<value>`; everything else must ask it. Excluded by name so the guard
# does not lean on the seam keeping any particular internal shape.
SEAM_MODULE = SCRIPTS / "_lib" / "axis_labels.py"


def _all_scanned_scripts() -> list[Path]:
    """Every `.py` under scripts/ (and _lib/) except the seam module.

    Scan-all (RF-2 / CA-1): the guard's scope is the whole script tree, not a
    hand-maintained allow-list. The seam is the sole legitimate constructor and
    is the only exclusion.
    """
    paths = sorted(SCRIPTS.rglob("*.py"))
    return [
        p
        for p in paths
        if p != SEAM_MODULE and "__pycache__" not in p.parts
    ]


def _text_ends_in_axis_prefix(text: str) -> str | None:
    """The axis prefix ``text`` ends in (``"...type:"``), else None."""
    for prefix in PREFIXES:
        if text.endswith(prefix):
            return prefix
    return None


def _dict_key_lines(tree: ast.AST) -> set[int]:
    """Line numbers of string constants appearing as dict keys.

    A complete static ``"type:feature"`` literal used as a *dict key* is a
    read-key for lookup against the greenfield encoding, not a label coming into
    being (the G-2 ``TYPE_LABEL_TO_PREFIX`` maps). Exempt those positions; a full
    literal used as a value stays flagged.
    """
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    lines.add(key.lineno)
    return lines


def _fstring_constructs_axis_label(node: ast.JoinedStr) -> list[str]:
    """Axis prefixes this f-string constructs (literal `<axis>:` then a value).

    Catches the ``f"type:{x}"`` shape: a literal part ending in an axis prefix
    immediately followed by an interpolation (`FormattedValue`). This is the
    structural signature of dynamic axis-label construction. Prose like
    ``f"... state:* labels ..."`` does not match — the char after ``state:`` is
    ``*``/space, not an interpolation; a display column header
    ``f"  priority:   {x}"`` does not match — whitespace separates the prefix
    from the field.
    """
    hits: list[str] = []
    parts = node.values
    for i, part in enumerate(parts):
        if not (isinstance(part, ast.Constant) and isinstance(part.value, str)):
            continue
        prefix = _text_ends_in_axis_prefix(part.value)
        if prefix is None:
            continue
        nxt = parts[i + 1] if i + 1 < len(parts) else None
        if isinstance(nxt, ast.FormattedValue):
            hits.append(prefix)
    return hits


def _concat_constructs_axis_label(node: ast.BinOp) -> str | None:
    """Axis prefix of a ``"<axis>:" + value`` concatenation, else None.

    Catches the RF-1 shape: a ``BinOp`` with ``Add`` whose left operand is a
    string constant ending in an axis prefix. The right operand is whatever value
    is being concatenated on — by combining a prefix with a value, this is a
    construction regardless of what the right side is.
    """
    if not isinstance(node.op, ast.Add):
        return None
    left = node.left
    if isinstance(left, ast.Constant) and isinstance(left.value, str):
        return _text_ends_in_axis_prefix(left.value)
    return None


def _join_constructs_axis_label(node: ast.Call) -> str | None:
    """Axis prefix of a ``sep.join([...])`` that builds an axis label, else None.

    Catches the ``":".join(["type", v])`` / ``"type:".join([...])`` shapes: a
    ``str.join`` whose separator constant ends in an axis prefix, or any element
    constant that ends in one. A combination of a prefix with the joined values
    is a construction.
    """
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr == "join"):
        return None
    # separator ends in an axis prefix: `"type:".join(...)`
    if isinstance(func.value, ast.Constant) and isinstance(func.value.value, str):
        prefix = _text_ends_in_axis_prefix(func.value.value)
        if prefix is not None:
            return prefix
    # an element constant ends in an axis prefix: `":".join(["type:", v])`
    if node.args and isinstance(node.args[0], (ast.List, ast.Tuple)):
        for elt in node.args[0].elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                prefix = _text_ends_in_axis_prefix(elt.value)
                if prefix is not None:
                    return prefix
    return None


def _format_constructs_axis_label(node: ast.Call) -> str | None:
    """Axis prefix of a ``"<axis>:{}".format(v)`` call, else None.

    Catches ``str.format`` where the template literal places a ``{`` field marker
    immediately after an axis prefix (``"type:{}"`` / ``"type:{0}"`` /
    ``"type:{kind}"``). Mirrors the f-string detector for the ``.format`` spelling.
    """
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr == "format"):
        return None
    tmpl = func.value
    if not (isinstance(tmpl, ast.Constant) and isinstance(tmpl.value, str)):
        return None
    text = tmpl.value
    for prefix in PREFIXES:
        idx = text.find(prefix)
        if idx != -1 and text[idx + len(prefix):idx + len(prefix) + 1] == "{":
            return prefix
    return None


def _bare_axis_label_constant(node: ast.Constant) -> str | None:
    """The axis prefix of a bare ``"<axis>:<value>"`` literal, else None.

    A full static label literal (e.g. ``"type:maintenance"``, ``"state:todo"``)
    used as a *value*. Prefix-only constants (``"type:"`` for a read), label
    *globs* (``"state:*"`` in prose), and substrings inside a longer sentence are
    not flagged — the literal must be exactly ``<axis>:<non-empty-value>`` with no
    whitespace or ``*``. Dict-key positions (G-2 read-maps) are filtered out by
    the caller before this runs.
    """
    if not isinstance(node.value, str):
        return None
    text = node.value
    for prefix in PREFIXES:
        if not text.startswith(prefix):
            continue
        value = text[len(prefix):]
        if value and not any(c.isspace() for c in value) and "*" not in value:
            return prefix
    return None


def _docstring_lines(tree: ast.AST) -> set[int]:
    """Line span of every docstring's text — prose mentioning labels lives there
    (e.g. a module docstring listing ``state:todo`` … ``state:done``) and must
    not trip the bare-constant check."""
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is None:
                continue
            body0 = node.body[0]
            if isinstance(body0, ast.Expr) and isinstance(body0.value, ast.Constant):
                start = body0.value.lineno
                end = getattr(body0.value, "end_lineno", start)
                lines.update(range(start, end + 1))
    return lines


def _violations(path: Path) -> list[str]:
    """Lines in ``path`` that construct an axis-label outside the seam."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    docstring_lines = _docstring_lines(tree)
    dict_key_lines = _dict_key_lines(tree)

    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            for prefix in _fstring_constructs_axis_label(node):
                out.append(
                    f"{path.name}:{node.lineno}: f-string constructs "
                    f"`{prefix}` axis-label inline (route through "
                    f"_lib.axis_labels.label)"
                )
        elif isinstance(node, ast.BinOp):
            prefix = _concat_constructs_axis_label(node)
            if prefix is not None:
                out.append(
                    f"{path.name}:{node.lineno}: concatenation constructs "
                    f"`{prefix}` axis-label inline (route through "
                    f"_lib.axis_labels.label)"
                )
        elif isinstance(node, ast.Call):
            prefix = _join_constructs_axis_label(node)
            if prefix is not None:
                out.append(
                    f"{path.name}:{node.lineno}: `.join` constructs "
                    f"`{prefix}` axis-label inline (route through "
                    f"_lib.axis_labels.label)"
                )
            prefix = _format_constructs_axis_label(node)
            if prefix is not None:
                out.append(
                    f"{path.name}:{node.lineno}: `.format` constructs "
                    f"`{prefix}` axis-label inline (route through "
                    f"_lib.axis_labels.label)"
                )
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.lineno in docstring_lines or node.lineno in dict_key_lines:
                continue
            prefix = _bare_axis_label_constant(node)
            if prefix is not None:
                out.append(
                    f"{path.name}:{node.lineno}: bare `{node.value}` axis-label "
                    f"literal used as a value (route through _lib.axis_labels.label)"
                )
    return out


@pytest.mark.parametrize(
    "path", _all_scanned_scripts(), ids=lambda p: str(p.relative_to(SCRIPTS))
)
def test_no_inline_axis_label_construction(path: Path) -> None:
    """No pm script constructs an axis-label outside the seam (ADR-026 part (i)).

    Scan-all: every `.py` under scripts/ and _lib/ except the seam module.
    """
    violations = _violations(path)
    assert not violations, (
        "axis-label constructed outside the sole-constructor seam "
        "(ADR-026 part (i)):\n  " + "\n  ".join(violations)
    )


def test_scan_covers_the_previously_omitted_write_paths() -> None:
    """The scan-all set includes the write paths the old allow-list omitted —
    pinning RF-2 / CA-1 so a regression to a hand-maintained list is caught."""
    scanned = {p.name for p in _all_scanned_scripts()}
    for required in (
        "pre-check.py",
        "promote-issue.py",
        "close-issue.py",
        "reopen-issue.py",
        "create-issue.py",
        "bootstrap.py",
    ):
        assert required in scanned, f"scan-all must cover {required}"
    assert SEAM_MODULE.name not in scanned, "the seam module must be excluded"


def test_seam_module_builds_labels_with_a_fully_dynamic_axis() -> None:
    """The seam builds labels as ``f"{axis}:{value}"`` / ``f"{axis}:"`` — the axis
    itself is interpolated, so the literal text never ends in a *fixed* ``<axis>:``
    prefix before a value. The seam is excluded from the scan by name, but this
    pins *why* it is structurally distinct: even if it were scanned, the
    dynamic-axis shape would not match the inline-construction shapes the guard
    hunts, while every call site that hard-codes the axis does."""
    assert SEAM_MODULE.exists()
    assert not _violations(SEAM_MODULE), (
        "the seam should build labels with a dynamic axis (`f\"{axis}:{value}\"`), "
        "which the guard does not flag — if this fires, the seam has started "
        "hard-coding an axis and now looks like the inline sites it replaces"
    )


def test_guard_detects_a_reintroduced_inline_fstring(tmp_path: Path) -> None:
    """Mutation-proof: a script with an inline `f\"type:{x}\"` is flagged, and the
    seam-routed form is not. Pins the f-string detector's discriminating power."""
    bad = tmp_path / "bad.py"
    bad.write_text('labels = [f"type:{kind}"]\n', encoding="utf-8")
    assert _violations(bad), "guard failed to flag a reintroduced inline f-string"

    good = tmp_path / "good.py"
    good.write_text('labels = [axis_labels.label("type", kind)]\n', encoding="utf-8")
    assert not _violations(good), "guard wrongly flagged the seam-routed form"


def test_guard_detects_a_reintroduced_concatenation(tmp_path: Path) -> None:
    """Mutation-proof for the concatenation detector (RF-1 shape). A script with
    `'type:' + v` is flagged; the seam-routed form is not. This is the exact
    shape pre-check.py used in its error messages before the fix."""
    bad = tmp_path / "concat.py"
    bad.write_text(
        "msg = ', '.join('type:' + v for v in missing)\n", encoding="utf-8"
    )
    assert _violations(bad), "guard failed to flag a `'type:' + v` concatenation"

    good = tmp_path / "concat_ok.py"
    good.write_text(
        "msg = ', '.join(axis_labels.label('type', v) for v in missing)\n",
        encoding="utf-8",
    )
    assert not _violations(good), "guard wrongly flagged the seam-routed form"


def test_guard_detects_join_and_format_shapes(tmp_path: Path) -> None:
    """The sibling dynamic shapes WR-1 names — `.join` and `.format` that combine
    an axis prefix with a value — are flagged."""
    joined = tmp_path / "joined.py"
    joined.write_text('x = "type:".join([a, b])\n', encoding="utf-8")
    assert _violations(joined), "guard failed to flag a `.join` axis construction"

    formatted = tmp_path / "formatted.py"
    formatted.write_text('x = "state:{}".format(s)\n', encoding="utf-8")
    assert _violations(formatted), "guard failed to flag a `.format` axis construction"


def test_guard_exempts_non_construction_shapes(tmp_path: Path) -> None:
    """The shape-vs-intent rule: globs, bare prefixes, and complete static
    read-key literals used as dict keys are NOT constructions and are not flagged.
    A full literal used as a *value* still is."""
    exempt = tmp_path / "exempt.py"
    exempt.write_text(
        'msg = "state:* labels missing"\n'          # glob
        'pfx = "type:"\n'                            # bare prefix (read key)
        'if name.startswith("workstream:"):\n'       # bare prefix (read key)
        '    pass\n'
        'TYPE_LABEL_TO_PREFIX = {\n'                 # dict-key read-map (G-2)
        '    "type:feature": "feat",\n'
        '    "type:bug": "fix",\n'
        '}\n',
        encoding="utf-8",
    )
    assert not _violations(exempt), (
        "guard wrongly flagged a glob / bare-prefix / dict-key read literal"
    )

    # A full literal used as a *value* (not a dict key) is still a construction.
    bare_value = tmp_path / "bare_value.py"
    bare_value.write_text('SENTINEL = "state:todo"\n', encoding="utf-8")
    assert _violations(bare_value), (
        "guard failed to flag a bare full-literal label used as a value"
    )
