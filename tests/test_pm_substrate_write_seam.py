"""The non-label substrate-write sole-constructor seam — ADR-031, both halves.

[ADR-031](../docs/architecture/decisions/ADR-031-substrate-write-path-contract.md)
makes "no script string-builds a covered non-label substrate write inline"
structural by requiring that ``_lib/substrate_writes`` be the **sole
constructor** of each covered write: the Projects-v2 single-select/text
field-value write (``gh project item-edit … --field-id`` AND its GraphQL twin
``gh api graphql … updateProjectV2ItemFieldValue``) and the milestone write
(``gh issue edit --milestone`` post-hoc AND ``gh issue create --milestone`` at
create time). This is the non-label, write-side twin of ADR-026's label
sole-constructor and its guard (`test_pm_axis_label_seam_guard`).

The invariant is a tested property with two halves (ADR-031 point 4) — only both
together make it structural:

  * **Half (a) — the construction test** (this file's first section): the
    primitive constructs and executes the covered writes, and the converged call
    sites (DEC-024's ``set-board-field`` / ``assign-milestone`` handlers,
    ``create-issue``'s milestone write) obtain their write *from* it.
  * **Half (b) — the grep/AST guard** (this file's second section): no script
    string-builds a covered write's argv inline except the sole-constructor
    module. Without half (b), half (a) passes while a stray inline write in some
    future handler bypasses the primitive — exactly the four-site scatter ADR-031
    converges, re-growing unnoticed.

The guard recognises the *operation*, not bare tokens (resolves the airtightness
gap the critic found in the first cut)
---------------------------------------------------------------------------------
The first cut of half (b) inspected only the literal string elements of a single
``ast.List``/``ast.Tuple`` and flagged any list carrying both ``"issue"`` and
``"--milestone"`` (or both ``"item-edit"`` and ``"--field-id"``) anywhere. That
was defeated by every argv-assembly idiom the scripts actually use — ``.extend`` /
``.append`` accumulation (the create-issue idiom!), variable-built flags
(``FID = "--field-id"``), list concatenation (``[...] + ["--field-id", fid]``),
f-string / ``.format`` / ``%`` elements, and string-form commands
(``shlex.split("gh issue edit … --milestone …")``) — and it over-fired on any
coincidental token list (a future allowlist ``["issue", "pr", …, "--milestone",
"--label"]`` would false-positive).

This guard ports the proven multi-shape value resolution from
`test_pm_axis_label_seam_guard` and makes recognition **operation-shaped**:

  * It resolves each argv expression into the ordered sequence of its *literal*
    string elements — following ``.extend`` / ``.append`` accumulation on a list
    variable across statements, list concatenation (``BinOp`` ``+``),
    ``shlex.split`` of a literal command, and variable-bound flag literals
    (``FID = "--field-id"``), and resolving f-string / ``.format`` / ``%`` /
    ``str.join`` element forms back to the literal text they place.
  * Over the resolved literals it recognises the actual ``gh`` operation — the
    subcommand AND its value flag in the right structural relationship — not bare
    token membership. ``gh project item-edit`` carrying ``--field-id`` is a
    field-value write; ``gh issue {edit,create}`` carrying ``--milestone`` is a
    milestone write; ``gh api graphql`` carrying ``updateProjectV2ItemFieldValue``
    is the GraphQL field-value write. A coincidental list that merely contains the
    flag token without the operation around it does NOT match.

Board-membership is NAMED OUT (ADR-031 point 3)
-----------------------------------------------
``_gh_add_to_board``'s ``gh project item-add`` (membership, DEC-019) is a distinct
operation and is NOT a covered write. The guard recognises ``item-edit`` (carrying
``--field-id``), not the ``gh project`` prefix, so the legitimate ``item-add``
membership site is left alone even under the stricter operation matcher.

The seam-routed splice is NOT flagged
-------------------------------------
``create-issue`` assembles its ``gh issue create`` argv and then
``cmd.extend(milestone_create_args(title))`` — the ``--milestone`` argv comes from
the seam *call*, not an inline literal, so the resolver never sees a literal
``--milestone`` and the operation does not match. Splice a literal
``cmd.extend(["--milestone", title])`` instead and the resolver sees the literal,
the operation matches, and the guard fires. That discriminating power is what the
mutation-proofs below pin.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB = SCRIPTS / "_lib"

# The one allow-listed constructor — the seam itself legitimately builds the
# covered `gh` argv; everything else must ask it. Excluded by name from the guard
# scan (half b) so the guard does not lean on the seam keeping any internal shape.
SEAM_MODULE = LIB / "substrate_writes.py"


# =========================================================================
# Half (a) — the construction test
# =========================================================================


@pytest.fixture(scope="module")
def substrate_writes():
    """Load the substrate-writes primitive via importlib (sibling _lib import)."""
    if str(LIB) not in sys.path:
        sys.path.insert(0, str(LIB))
    spec = importlib.util.spec_from_file_location(
        "pm_substrate_writes_under_test", SEAM_MODULE
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_substrate_writes_under_test"] = module
    spec.loader.exec_module(module)
    return module


# --- the primitive constructs the covered writes -------------------------


def test_field_value_args_constructs_the_single_select_write(substrate_writes) -> None:
    args = substrate_writes.field_value_args(
        item_id="ITEM_1",
        field_id="FIELD_1",
        project_id="PROJ_1",
        single_select_option_id="OPT_1",
    )
    assert args == [
        "gh", "project", "item-edit",
        "--id", "ITEM_1",
        "--field-id", "FIELD_1",
        "--project-id", "PROJ_1",
        "--single-select-option-id", "OPT_1",
    ]


def test_field_value_args_constructs_the_text_write(substrate_writes) -> None:
    args = substrate_writes.field_value_args(
        item_id="ITEM_1",
        field_id="FIELD_1",
        project_id="PROJ_1",
        text_value="Spyre",
    )
    assert args[-2:] == ["--text", "Spyre"]
    assert "--single-select-option-id" not in args


def test_field_value_args_refuses_a_valueless_write(substrate_writes) -> None:
    """A field-value write with neither value form is incoherent — fail loud
    rather than emit a valueless `item-edit`."""
    with pytest.raises(ValueError):
        substrate_writes.field_value_args(
            item_id="ITEM_1", field_id="FIELD_1", project_id="PROJ_1"
        )


def test_milestone_edit_args_constructs_the_post_hoc_write(substrate_writes) -> None:
    assert substrate_writes.milestone_edit_args(issue_number=42, title="M1") == [
        "gh", "issue", "edit", "42", "--milestone", "M1",
    ]


def test_milestone_create_args_constructs_the_at_create_fragment(substrate_writes) -> None:
    """The at-create form yields only the `--milestone` argv fragment — the create
    call (title/body/labels/assignee) is assembled and run by the caller; the
    fragment still ORIGINATES in the sole constructor (ADR-031 point 1)."""
    assert substrate_writes.milestone_create_args("M1") == ["--milestone", "M1"]


# --- the primitive executes, and is failure-posture-neutral --------------


def test_write_field_value_returns_neutral_success(substrate_writes, monkeypatch) -> None:
    """On success the result carries ok + the constructed argv; no exception, no
    posture imposed (ADR-031 point 6)."""
    captured: dict = {}

    def fake_gh(args, config):
        captured["args"] = args
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(substrate_writes, "_gh_call", fake_gh)
    result = substrate_writes.write_field_value(
        {},
        item_id="ITEM_1",
        field_id="FIELD_1",
        project_id="PROJ_1",
        single_select_option_id="OPT_1",
    )
    assert result.ok is True
    assert result.executed is True
    assert result.error is None
    # argv is an immutable tuple; it carries the same sequence as the executed argv.
    assert result.argv == tuple(captured["args"])
    assert result.argv[:3] == ("gh", "project", "item-edit")


def test_result_argv_is_an_immutable_tuple(substrate_writes, monkeypatch) -> None:
    """`SubstrateWriteResult.argv` is a tuple, not a list — a caller / T2's
    `--emit-script` renderer cannot mutate state the result shares with whatever
    ran the write (the result is `frozen=True`, but a `list` field would still be
    mutable in place)."""
    def fake_gh(args, config):
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(substrate_writes, "_gh_call", fake_gh)
    result = substrate_writes.write_milestone({}, issue_number=7, title="M1")
    assert isinstance(result.argv, tuple)
    with pytest.raises((AttributeError, TypeError)):
        result.argv.append("--mutated")  # type: ignore[attr-defined]


def test_write_milestone_failure_is_carried_not_raised(substrate_writes, monkeypatch) -> None:
    """A failed write returns ok=False with the stderr in `error` — it does NOT
    raise. Posture-neutrality: the caller decides what the failure means."""
    def fake_gh(args, config):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="boom")

    monkeypatch.setattr(substrate_writes, "_gh_call", fake_gh)
    result = substrate_writes.write_milestone({}, issue_number=7, title="M1")
    assert result.ok is False
    assert result.executed is True
    assert result.error == "boom"
    assert "boom" in result.detail


def test_write_missing_gh_binary_is_carried_not_raised(substrate_writes, monkeypatch) -> None:
    def fake_gh(args, config):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(substrate_writes, "_gh_call", fake_gh)
    result = substrate_writes.write_milestone({}, issue_number=7, title="M1")
    assert result.ok is False
    assert result.executed is False
    assert result.error is not None


# --- the converged sites obtain their write FROM the primitive -----------


def _imports_substrate_writes(path: Path) -> bool:
    """True when `path` imports the substrate-writes primitive (any import form)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.endswith("substrate_writes") for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.endswith("substrate_writes"):
                return True
            if any(a.name == "substrate_writes" for a in node.names):
                return True
    return False


def test_hooks_handlers_route_through_the_primitive(substrate_writes) -> None:
    """The two DEC-024 handlers call the primitive's write functions, not an
    inline `gh` build (half a for the hook sites)."""
    hooks_src = (LIB / "hooks.py").read_text(encoding="utf-8")
    assert _imports_substrate_writes(LIB / "hooks.py")
    assert "substrate_writes.write_field_value" in hooks_src
    assert "substrate_writes.write_milestone" in hooks_src


def test_create_issue_milestone_routes_through_the_primitive() -> None:
    """create-issue's at-create milestone write obtains its `--milestone` argv
    from the primitive (half a for the create site)."""
    create_src = (SCRIPTS / "create-issue.py").read_text(encoding="utf-8")
    assert _imports_substrate_writes(SCRIPTS / "create-issue.py")
    assert "milestone_create_args" in create_src


# =========================================================================
# Half (b) — the grep/AST guard
# =========================================================================
#
# The guard flags a covered substrate write whose argv is string-built inline
# anywhere but the seam. It resolves each argv expression to its ordered LITERAL
# string elements (following the assembly idioms the scripts use — see the
# resolver below) and then recognises the OPERATION over those literals:
#
#   * field-value (item-edit):  `gh project item-edit` carrying a `--field-id`
#                               flag — the `gh project item-edit … --field-id`
#                               write. `item-add` (membership) carries no
#                               `--field-id` and is left alone — ADR-031 point 3.
#   * field-value (GraphQL):    `gh api graphql` carrying the
#                               `updateProjectV2ItemFieldValue` mutation — the
#                               GraphQL twin of the item-edit write (same
#                               substrate, ADR-031). None exists in the tree
#                               today; the detector covers a future #122 reach.
#   * milestone:                `gh issue {edit,create}` carrying a `--milestone`
#                               flag — the `gh issue …--milestone` write.
#
# Recognising the OPERATION (subcommand + value flag in the right structural
# relationship), not bare token membership, is what (a) leaves `item-add`
# untouched and (b) does not over-fire on a coincidental token list.


# The literal markers the operation matcher keys on. Duplicated here (not
# imported) so the guard does not depend on the very module it polices being
# importable — mirrors the axis-label guard's `AXES` duplication.
GH = "gh"
FIELD_VALUE_SUBCOMMAND = ("project", "item-edit")
FIELD_ID_FLAG = "--field-id"
GRAPHQL_SUBCOMMAND = ("api", "graphql")
GRAPHQL_FIELD_MUTATION = "updateProjectV2ItemFieldValue"
MILESTONE_VERB = "issue"
MILESTONE_SUBCOMMANDS = ("edit", "create")
MILESTONE_FLAG = "--milestone"


def _all_scanned_scripts() -> list[Path]:
    """Every `.py` under scripts/ (and _lib/) except the seam module."""
    return [
        p
        for p in sorted(SCRIPTS.rglob("*.py"))
        if p != SEAM_MODULE and "__pycache__" not in p.parts
    ]


# --- value resolution: argv expression -> ordered literal elements -------
#
# Ported from `test_pm_axis_label_seam_guard`'s multi-shape value resolution and
# extended for THIS guard's needs: `.extend` / `.append` accumulation tracking and
# variable-bound flag literals. Each element of an argv resolves either to its
# literal string (when statically known) or to None (a runtime value / a
# seam-sourced fragment — opaque to the guard, and crucially NOT a literal flag).


# Sentinel for an element whose literal value is not statically known.
_OPAQUE = None


def _const_str(node: ast.AST) -> str | None:
    """The string value of a bare string constant, else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _resolve_element(node: ast.AST, names: dict[str, str]) -> str | None:
    """Resolve one argv *element* expression to its literal text, or None.

    Handles the element forms the scripts (and plausible evasions) use:
      * bare string constant                     -> its text;
      * a name bound earlier to a string literal -> that literal (variable-built
        flags, e.g. `FID = "--field-id"; args = [..., FID, fid]`);
      * f-string / `.format` / `%` / `str.join`  -> the literal text they place
        (so a flag interpolated/formatted into a string is still recognised);
      * anything else (a call, an attribute, a runtime name) -> None (opaque).
    """
    text = _const_str(node)
    if text is not None:
        return text
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    if isinstance(node, ast.JoinedStr):
        return _joinedstr_literal_text(node)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        # `"%s" % v` / `"--milestone %s" % v` — the template's literal text.
        return _const_str(node.left)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        # `"--milestone" + v` / `"--mile" + "stone"` — concatenated literal text.
        left = _resolve_element(node.left, names)
        right = _resolve_element(node.right, names)
        return (left or "") + (right or "") if (left or right) else None
    if isinstance(node, ast.Call):
        text = _format_call_literal_text(node, names)
        if text is not None:
            return text
        return _join_call_literal_text(node, names)
    return None


def _joinedstr_literal_text(node: ast.JoinedStr) -> str:
    """The concatenated literal (non-interpolated) text of an f-string.

    `f"--milestone {x}"` -> `"--milestone "`. Interpolations contribute nothing
    statically, but the literal text around them is enough to recognise a flag.
    """
    parts: list[str] = []
    for part in node.values:
        text = _const_str(part)
        if text is not None:
            parts.append(text)
    return "".join(parts)


def _format_call_literal_text(node: ast.Call, names: dict[str, str]) -> str | None:
    """`"...".format(...)` -> the template's literal text, else None."""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "format":
        return _resolve_element(func.value, names)
    return None


def _join_call_literal_text(node: ast.Call, names: dict[str, str]) -> str | None:
    """`sep.join([...])` -> the joined literal text, else None.

    Covers a string-form command assembled via join (`" ".join(["gh", "issue",
    "edit", n, "--milestone", t])`); the joined literal pieces are recognised.
    """
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr == "join"):
        return None
    sep = _resolve_element(func.value, names) or ""
    if not node.args or not isinstance(node.args[0], (ast.List, ast.Tuple)):
        return None
    pieces = [_resolve_element(e, names) or "" for e in node.args[0].elts]
    return sep.join(pieces)


def _resolve_sequence(node: ast.AST, names: dict[str, str]) -> list[str | None] | None:
    """Resolve a list/tuple-shaped argv expression to its ordered elements.

    Returns a list whose entries are literal strings (statically known) or None
    (opaque). Returns None when `node` is not a sequence-shaped expression at all.
    Handles list/tuple literals and `[...] + [...]` concatenation (`BinOp` Add of
    two sequences — the `[...] + ["--field-id", fid]` evasion).
    """
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_resolve_element(e, names) for e in node.elts]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _resolve_sequence(node.left, names)
        right = _resolve_sequence(node.right, names)
        if left is not None or right is not None:
            return (left or [_OPAQUE]) + (right or [_OPAQUE])
    return None


def _shlex_split_command(node: ast.AST) -> list[str | None] | None:
    """`shlex.split("gh issue edit … --milestone …")` -> the split literal tokens.

    A string-form command is still a covered write if its tokens spell the
    operation. Only a literal-string argument is resolvable; a runtime string is
    opaque (returns None).
    """
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    is_shlex_split = (
        isinstance(func, ast.Attribute)
        and func.attr == "split"
        and isinstance(func.value, ast.Name)
        and func.value.id == "shlex"
    )
    if not is_shlex_split or not node.args:
        return None
    text = _const_str(node.args[0])
    if text is None:
        return None
    return list(text.split())


def _collect_string_bindings(tree: ast.AST) -> dict[str, str]:
    """Map every name bound to a *string literal* anywhere in the module.

    Powers variable-built-flag tracking: `FID = "--field-id"` lets a later
    `[..., FID, fid]` resolve `FID` back to `"--field-id"`. Module-wide (not
    scope-aware) by design — a guard errs toward catching evasions, and a flag
    constant rebinding the same name to two different literals is not a real idiom
    here. Last binding wins on collision.
    """
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            text = _const_str(node.value)
            if text is None:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings[target.id] = text
    return bindings


def _collect_accumulated_argvs(
    tree: ast.AST, names: dict[str, str]
) -> list[tuple[int, list[str | None]]]:
    """Resolve list variables assembled across statements via `.extend`/`.append`.

    The create-issue idiom: `cmd = ["gh", "issue", "create", ...]` then
    `cmd.extend([...])` / `cmd.append(...)` on later lines. Walks each scope's
    statements in order, seeding each name from its initial sequence assignment and
    folding in every literal `.extend(seq)` / `.append(elt)` on that name. A
    `.extend` whose argument is a *call* (e.g. `cmd.extend(milestone_create_args(t))`)
    contributes an opaque element — the seam-routed splice is therefore NOT seen as
    a literal `--milestone`, while `cmd.extend(["--milestone", t])` IS.

    Folding is **per scope** (the module body, and each function body separately):
    two functions that both build a local `cmd` must not clobber each other's
    accumulation through a shared name (create-issue has both a `gh issue create`
    `cmd` and a `gh project item-add` `cmd`). Each fully-folded argv is returned as
    a `(seed-lineno, sequence)` pair so the violation can be reported at the line
    the argv was seeded. Names whose initial value is not a sequence are skipped.
    """
    out: list[tuple[int, list[str | None]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        accumulated: dict[str, list[str | None]] = {}
        seed_lines: dict[str, int] = {}
        _fold_block(node.body, names, accumulated, seed_lines)
        for name, seq in accumulated.items():
            out.append((seed_lines.get(name, 0), seq))
    return out


# Statement attributes that carry nested statement blocks — accumulation can
# happen inside a `for`/`if`/`with`/`try`/loop body (the create-issue idiom puts
# `cmd.extend(...)` inside a `for` and an `if`), so the fold must descend into
# them in source order rather than only inspecting a function's top-level body.
_NESTED_BLOCK_ATTRS = ("body", "orelse", "finalbody", "handlers")


def _fold_block(
    body: list[ast.stmt],
    names: dict[str, str],
    accumulated: dict[str, list[str | None]],
    seed_lines: dict[str, int],
) -> None:
    """Fold `.extend`/`.append` accumulation over a statement block, in order.

    Descends into nested blocks (`for` / `if` / `with` / `try`) so an argv
    assembled across control flow — `cmd.extend([...])` inside a loop or guard, as
    create-issue does — is folded into the same accumulated sequence. A nested
    function definition is NOT descended into here (it is reached on its own as a
    `FunctionDef` walk root, with its own seeds). `seed_lines` records the line of
    each name's seeding assignment so the violation is reported there.
    """
    for stmt in body:
        # seed: `name = <sequence>`
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    seq = _resolve_sequence(stmt.value, names)
                    if seq is not None:
                        accumulated[target.id] = list(seq)
                        seed_lines[target.id] = stmt.lineno
            continue
        # accumulate: `name.extend(<seq>)` / `name.append(<elt>)`
        call = _expr_call(stmt)
        if call is not None:
            _fold_accumulation_call(call, names, accumulated)
            continue
        # descend into nested control-flow blocks (but not nested functions).
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for attr in _NESTED_BLOCK_ATTRS:
            nested = getattr(stmt, attr, None)
            if not nested:
                continue
            for item in nested:
                if isinstance(item, ast.ExceptHandler):
                    _fold_block(item.body, names, accumulated, seed_lines)
                elif isinstance(item, ast.stmt):
                    _fold_block([item], names, accumulated, seed_lines)


def _fold_accumulation_call(
    call: ast.Call,
    names: dict[str, str],
    accumulated: dict[str, list[str | None]],
) -> None:
    """Fold one `name.extend(<seq>)` / `name.append(<elt>)` call into `accumulated`."""
    func = call.func
    if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)):
        return
    name = func.value.id
    if name not in accumulated or not call.args:
        return
    if func.attr == "extend":
        seq = _resolve_sequence(call.args[0], names)
        accumulated[name].extend(seq if seq is not None else [_OPAQUE])
    elif func.attr == "append":
        accumulated[name].append(_resolve_element(call.args[0], names))


def _expr_call(stmt: ast.stmt) -> ast.Call | None:
    """The `ast.Call` of an expression statement, else None."""
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        return stmt.value
    return None


# --- operation recognition over resolved literal elements ----------------
#
# Bare token membership is replaced by structural operation recognition: the
# subcommand AND its value flag must both be present as literals. (The flag and
# subcommand need not be adjacent — `gh issue edit <n> --milestone <t>` separates
# them — but both must be literal tokens of the same resolved argv, so a
# coincidental list that merely contains `--milestone` without `gh issue` around
# it does not match, and an allowlist `["issue", "pr", …, "--milestone"]` that
# lacks the `gh`/`edit|create` operation structure does not match either.)


def _literals(elements: list[str | None]) -> list[str]:
    """The statically-known literal elements (drop opaque/runtime entries)."""
    return [e for e in elements if e is not None]


def _has_subsequence(literals: list[str], sub: tuple[str, ...]) -> bool:
    """True when `sub` appears as a contiguous subsequence of `literals`.

    Used to recognise a multi-token subcommand (`gh project item-edit`,
    `gh issue edit`) in order, so a list that merely contains the tokens scattered
    does not satisfy it.
    """
    if not sub:
        return True
    n = len(sub)
    windows = range(len(literals) - n + 1)
    return any(tuple(literals[i:i + n]) == sub for i in windows)


def _is_field_value_write(elements: list[str | None]) -> bool:
    """`gh project item-edit … --field-id` recognised as an operation.

    Requires the `gh project item-edit` subcommand as a contiguous run AND a
    `--field-id` flag literal. `item-add` (membership) lacks both `item-edit` and
    `--field-id`, so it does not match — ADR-031 point 3.
    """
    literals = _literals(elements)
    return (
        _has_subsequence(literals, (GH, *FIELD_VALUE_SUBCOMMAND))
        and FIELD_ID_FLAG in literals
    )


def _is_graphql_field_value_write(elements: list[str | None]) -> bool:
    """`gh api graphql … updateProjectV2ItemFieldValue` recognised as an operation.

    The GraphQL twin of the item-edit field-value write (same substrate). Requires
    the `gh api graphql` subcommand run AND the `updateProjectV2ItemFieldValue`
    mutation name appearing in some literal token (it usually rides inside the
    query string, so substring-match a literal rather than require an exact token).
    """
    literals = _literals(elements)
    if not _has_subsequence(literals, (GH, *GRAPHQL_SUBCOMMAND)):
        return False
    return any(GRAPHQL_FIELD_MUTATION in lit for lit in literals)


def _is_milestone_write(elements: list[str | None]) -> bool:
    """`gh issue {edit,create} … --milestone` recognised as an operation.

    Requires the `gh issue edit` or `gh issue create` subcommand run AND a
    `--milestone` flag literal. A coincidental list that contains `issue` and
    `--milestone` scattered without the `gh issue edit|create` operation does NOT
    match (resolves the over-broad first cut).
    """
    literals = _literals(elements)
    if MILESTONE_FLAG not in literals:
        return False
    return any(
        _has_subsequence(literals, (GH, MILESTONE_VERB, sub))
        for sub in MILESTONE_SUBCOMMANDS
    )


# --- the scan ------------------------------------------------------------


def _candidate_argvs(
    tree: ast.AST,
    names: dict[str, str],
    accumulated: list[tuple[int, list[str | None]]],
) -> list[tuple[int, list[str | None]]]:
    """Every (lineno, resolved-elements) argv candidate in the module.

    Pulls argvs from each shape the resolver understands: inline list/tuple
    literals and list-concatenations, `shlex.split` string-commands, and the
    per-scope fully-folded `.extend`/`.append` accumulations (already carrying
    their seed lineno). Each is checked against the operation matchers by the
    caller.
    """
    out: list[tuple[int, list[str | None]]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple, ast.BinOp)):
            seq = _resolve_sequence(node, names)
            if seq is not None:
                out.append((node.lineno, seq))
        elif isinstance(node, ast.Call):
            tokens = _shlex_split_command(node)
            if tokens is not None:
                out.append((node.lineno, tokens))
    out.extend(accumulated)
    return out


def _violations(path: Path) -> list[str]:
    """Lines in `path` that string-build a covered substrate write outside the seam."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = _collect_string_bindings(tree)
    accumulated = _collect_accumulated_argvs(tree, names)

    out: list[str] = []
    seen: set[tuple[int, str]] = set()
    for lineno, elements in _candidate_argvs(tree, names, accumulated):
        if _is_field_value_write(elements) or _is_graphql_field_value_write(elements):
            key = (lineno, "field")
            if key not in seen:
                seen.add(key)
                out.append(
                    f"{path.name}:{lineno}: inline field-value write "
                    f"(`gh project item-edit … --field-id` or `gh api graphql … "
                    f"updateProjectV2ItemFieldValue`) — route through "
                    f"_lib.substrate_writes.field_value_args / write_field_value"
                )
        if _is_milestone_write(elements):
            key = (lineno, "milestone")
            if key not in seen:
                seen.add(key)
                out.append(
                    f"{path.name}:{lineno}: inline `gh issue …--milestone` write "
                    f"(route through _lib.substrate_writes.milestone_* / write_milestone)"
                )
    return out


@pytest.mark.parametrize(
    "path", _all_scanned_scripts(), ids=lambda p: str(p.relative_to(SCRIPTS))
)
def test_no_inline_substrate_write_construction(path: Path) -> None:
    """No pm script string-builds a covered substrate write outside the seam
    (ADR-031 part (b)). Scan-all over scripts/ and _lib/ except the seam module."""
    violations = _violations(path)
    assert not violations, (
        "covered substrate write constructed outside the sole-constructor seam "
        "(ADR-031 part (b)):\n  " + "\n  ".join(violations)
    )


def test_seam_module_is_the_one_allow_listed_constructor() -> None:
    """The seam itself builds the covered argv — it is excluded from the scan by
    name; this pins that it is the one place the construction lives."""
    assert SEAM_MODULE.exists()
    seam_violations = _violations(SEAM_MODULE)
    assert seam_violations, (
        "the seam must be the constructor of the covered writes — if this is "
        "empty, the construction has moved out of the seam"
    )


def test_guard_leaves_board_membership_alone() -> None:
    """`_gh_add_to_board`'s `gh project item-add` membership write is NOT flagged —
    the guard recognises `item-edit` (carrying `--field-id`), not the `gh project`
    prefix (ADR-031 point 3). This pins the named-out boundary on the live tree."""
    create_violations = _violations(SCRIPTS / "create-issue.py")
    assert not create_violations, (
        "the guard must not flag the named-out board-membership (`item-add`) "
        f"write or the seam-routed milestone splice: {create_violations}"
    )


# --- mutation-proofs: one per evasion shape ------------------------------
#
# The first cut's mutation-proofs only covered the clean-list-literal case, so a
# green run proved nothing about the holes the critic found. Each test below
# reintroduces ONE evasion shape and asserts the guard catches it, plus asserts
# the legitimate seam-routed form is NOT flagged.


def _violations_for_source(tmp_path: Path, name: str, src: str) -> list[str]:
    """Write `src` to a temp module and run the guard's `_violations` over it."""
    p = tmp_path / name
    p.write_text(src, encoding="utf-8")
    return _violations(p)


def test_guard_detects_a_clean_list_literal_field_value_write(tmp_path: Path) -> None:
    """Baseline: an inline `gh project item-edit … --field-id` list is flagged;
    the seam-routed form is not."""
    bad = _violations_for_source(
        tmp_path, "bad_field.py",
        'args = ["gh", "project", "item-edit", "--id", iid, "--field-id", fid]\n',
    )
    assert bad, "guard failed to flag a clean-list inline field-value write"

    good = _violations_for_source(
        tmp_path, "good_field.py",
        'args = substrate_writes.field_value_args(item_id=iid, field_id=fid, project_id=pid)\n',
    )
    assert not good, "guard wrongly flagged the seam-routed field-value form"


def test_guard_detects_a_clean_list_literal_milestone_write(tmp_path: Path) -> None:
    """Baseline: an inline `gh issue edit … --milestone` list is flagged; the
    seam-routed form is not."""
    bad = _violations_for_source(
        tmp_path, "bad_ms.py",
        'args = ["gh", "issue", "edit", str(n), "--milestone", title]\n',
    )
    assert bad, "guard failed to flag a clean-list inline milestone write"

    good = _violations_for_source(
        tmp_path, "good_ms.py",
        'args = substrate_writes.milestone_edit_args(issue_number=n, title=title)\n',
    )
    assert not good, "guard wrongly flagged the seam-routed milestone form"


def test_guard_detects_extend_accumulation_milestone_write(tmp_path: Path) -> None:
    """EVASION: `.extend` argv-accumulation (the create-issue idiom). A milestone
    write assembled across statements via a literal `.extend(["--milestone", t])`
    is caught — AND the seam-routed `cmd.extend(milestone_create_args(t))` splice
    on the SAME base argv is NOT flagged (the splice's `--milestone` comes from a
    call, not a literal)."""
    bad = _violations_for_source(
        tmp_path, "bad_extend.py",
        "cmd = ['gh', 'issue', 'create', '--title', title]\n"
        "for label in labels:\n"
        "    cmd.extend(['--label', label])\n"
        "if milestone is not None:\n"
        "    cmd.extend(['--milestone', milestone])\n",
    )
    assert bad, "guard failed to flag a `.extend`-accumulated milestone write"

    good = _violations_for_source(
        tmp_path, "good_extend.py",
        "cmd = ['gh', 'issue', 'create', '--title', title]\n"
        "for label in labels:\n"
        "    cmd.extend(['--label', label])\n"
        "if milestone is not None:\n"
        "    cmd.extend(milestone_create_args(milestone))\n",
    )
    assert not good, (
        "guard wrongly flagged the seam-routed `.extend(milestone_create_args(...))` "
        "splice — the create-issue idiom must stay clean"
    )


def test_guard_detects_append_accumulation_field_value_write(tmp_path: Path) -> None:
    """EVASION: `.append` argv-accumulation. A field-value write assembled by
    appending the `--field-id` flag literal is caught."""
    bad = _violations_for_source(
        tmp_path, "bad_append.py",
        "cmd = ['gh', 'project', 'item-edit', '--id', iid]\n"
        "cmd.append('--field-id')\n"
        "cmd.append(fid)\n",
    )
    assert bad, "guard failed to flag an `.append`-accumulated field-value write"


def test_guard_detects_variable_built_flag(tmp_path: Path) -> None:
    """EVASION: a flag string bound to a name then used in the argv. The resolver
    binds `FID = '--field-id'` and resolves it back when it appears in the list."""
    bad = _violations_for_source(
        tmp_path, "bad_var_flag.py",
        "FID = '--field-id'\n"
        "args = ['gh', 'project', 'item-edit', '--id', iid, FID, fid]\n",
    )
    assert bad, "guard failed to flag a variable-built `--field-id` flag"

    bad_ms = _violations_for_source(
        tmp_path, "bad_var_flag_ms.py",
        "MS = '--milestone'\n"
        "args = ['gh', 'issue', 'edit', n, MS, title]\n",
    )
    assert bad_ms, "guard failed to flag a variable-built `--milestone` flag"


def test_guard_detects_list_concatenation(tmp_path: Path) -> None:
    """EVASION: `[...] + ["--field-id", fid]` list concatenation (an `ast.BinOp`).
    The base and the concatenated fragment together spell the operation."""
    bad = _violations_for_source(
        tmp_path, "bad_concat.py",
        "args = ['gh', 'project', 'item-edit', '--id', iid] + ['--field-id', fid]\n",
    )
    assert bad, "guard failed to flag a `[...] + [...]` field-value concatenation"

    bad_ms = _violations_for_source(
        tmp_path, "bad_concat_ms.py",
        "args = ['gh', 'issue', 'edit'] + [str(n), '--milestone', title]\n",
    )
    assert bad_ms, "guard failed to flag a `[...] + [...]` milestone concatenation"


def test_guard_detects_fstring_format_and_percent_flag_elements(tmp_path: Path) -> None:
    """EVASION: a flag carried by an f-string / `.format` / `%` element. The
    resolver recovers the literal text these forms place around their
    interpolations, so a flag whose token sits in the literal part is seen. (The
    flag token must appear intact in the literal — a template that *splits* a flag
    across a substitution, e.g. `'--field-{}'.format('id')`, is a contrived shape
    a value-resolver cannot soundly recover and is out of scope; the realistic
    evasion carries the flag token whole, which this catches.)"""
    bad_fstring = _violations_for_source(
        tmp_path, "bad_fstring.py",
        "args = ['gh', 'issue', 'edit', f'{n}', f'--milestone', title]\n",
    )
    assert bad_fstring, "guard failed to flag an f-string `--milestone` element"

    bad_format = _violations_for_source(
        tmp_path, "bad_format.py",
        "args = ['gh', 'project', 'item-edit', '--id', iid, '--field-id', '{}'.format(fid)]\n",
    )
    assert bad_format, "guard failed to flag a field-value write with a `.format` value"

    bad_percent = _violations_for_source(
        tmp_path, "bad_percent.py",
        "args = ['gh', 'issue', 'edit', '%s' % n, '--milestone', title]\n",
    )
    assert bad_percent, "guard failed to flag a milestone write with a `%`-formatted element"


def test_guard_detects_shlex_split_string_command(tmp_path: Path) -> None:
    """EVASION: a string-form command split with `shlex.split`. The literal tokens
    of the command string spell the operation and are caught."""
    bad = _violations_for_source(
        tmp_path, "bad_shlex.py",
        "import shlex\n"
        "args = shlex.split('gh issue edit 42 --milestone M1')\n",
    )
    assert bad, "guard failed to flag a `shlex.split` string-form milestone write"

    bad_field = _violations_for_source(
        tmp_path, "bad_shlex_field.py",
        "import shlex\n"
        "args = shlex.split('gh project item-edit --id X --field-id F --text V')\n",
    )
    assert bad_field, "guard failed to flag a `shlex.split` string-form field-value write"


def test_guard_detects_graphql_field_value_write(tmp_path: Path) -> None:
    """EVASION / new form: the GraphQL twin `gh api graphql … with the
    `updateProjectV2ItemFieldValue` mutation. Same substrate as item-edit; the
    sole-constructor invariant must cover it (a future #122 reach)."""
    bad = _violations_for_source(
        tmp_path, "bad_graphql.py",
        "args = ['gh', 'api', 'graphql', '-f',\n"
        "        'mutation { updateProjectV2ItemFieldValue"
        "(input: {...}) { clientMutationId } }']\n",
    )
    assert bad, "guard failed to flag a GraphQL `updateProjectV2ItemFieldValue` write"


def test_guard_does_not_overfire_on_coincidental_token_lists(tmp_path: Path) -> None:
    """Operation-recognition, not bare token membership: a coincidental list that
    merely CONTAINS `issue`/`--milestone` (or `item-edit`/`--field-id`) tokens
    without the `gh <subcommand>` operation structure is NOT flagged. This is the
    over-broad-matcher regression the critic named (a future allowlist)."""
    # An allowlist of issue-type/flag tokens — no `gh issue edit|create` operation.
    allowlist = _violations_for_source(
        tmp_path, "allowlist.py",
        "ALLOWED = ['issue', 'pr', 'discussion', '--milestone', '--label', '--field-id']\n",
    )
    assert not allowlist, (
        "guard over-fired on a coincidental token allowlist (must recognise the "
        "operation, not bare token membership)"
    )

    # A help/usage string mentioning the flags — prose, not an argv.
    prose = _violations_for_source(
        tmp_path, "prose.py",
        "HELP = ['pass --milestone to set it', 'item-edit needs --field-id']\n",
    )
    assert not prose, "guard over-fired on a prose list mentioning the flags"


def test_guard_fires_on_the_live_create_issue_idiom_if_splice_goes_literal(
    tmp_path: Path,
) -> None:
    """End-to-end mutation-proof on the REAL create-issue source: the live file's
    seam-routed `cmd.extend(milestone_create_args(...))` splice is clean, but
    replacing that single call with a literal `cmd.extend(["--milestone", ...])`
    on the same accumulated `cmd` makes the guard fire. This pins the create-issue
    `.extend`-accumulation idiom against the exact regression — proving the clean
    state is load-bearing, not coincidental."""
    live = (SCRIPTS / "create-issue.py").read_text(encoding="utf-8")
    assert "cmd.extend(milestone_create_args(milestone_title))" in live, (
        "the create-issue seam splice changed shape — update this mutation-proof"
    )
    assert not _violations(SCRIPTS / "create-issue.py"), (
        "precondition: the live create-issue file must be clean"
    )

    mutated = live.replace(
        "cmd.extend(milestone_create_args(milestone_title))",
        'cmd.extend(["--milestone", milestone_title])',
    )
    violations = _violations_for_source(tmp_path, "create_issue_mutated.py", mutated)
    assert any("milestone" in v for v in violations), (
        "guard failed to fire when create-issue's seam splice was swapped for a "
        "literal inline `.extend(['--milestone', ...])` — the accumulation tracker "
        "is not airtight against the create-issue idiom"
    )


def test_guard_exempts_board_membership_item_add(tmp_path: Path) -> None:
    """The named-out `gh project item-add` membership write (no `--field-id`) is
    NOT a covered write and must not be flagged (ADR-031 point 3) — verified under
    the stricter operation matcher, including the `.extend` accumulation form
    create-issue actually uses for the board write."""
    membership = _violations_for_source(
        tmp_path, "membership.py",
        "cmd = ['gh', 'project', 'item-add', str(bid), '--owner', owner, '--url', url]\n",
    )
    assert not membership, (
        "guard wrongly flagged the named-out board-membership (item-add) write"
    )

    membership_accum = _violations_for_source(
        tmp_path, "membership_accum.py",
        "cmd = ['gh', 'project', 'item-add', str(bid)]\n"
        "cmd.extend(['--owner', owner])\n"
        "cmd.extend(['--url', url])\n",
    )
    assert not membership_accum, (
        "guard wrongly flagged an `.extend`-assembled board-membership write"
    )
