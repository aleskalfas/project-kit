"""The gate-coverage guard — every registered pm verb gates, or is exempt (#747).

The prerequisite gate is realised as an explicit call at the top of each gated
entry point rather than in the dispatcher (direct script invocation would bypass
that — the exact hole #747 closes) or in the shared config/`gh` seam (the
refusal would fire far from the command the user typed, and exempt scripts would
have to *opt out*: forget the opt-out and `bootstrap` itself breaks).

That placement buys three properties the alternatives lack — the refusal happens
where the command was typed, the exemption list is visible in code, and
completeness is **testable**. This file is the third one. Without it, verb #66
arrives next month with no gate and nobody notices, which is precisely how the
documentation-only gate came to be.

Same shape as the capability's sibling structural guards — the axis-label
sole-constructor guard (`test_pm_axis_label_seam_guard`) and the process-health
import-boundary pin: enumerate from the registry (here `package.yaml`'s
`commands:`), AST-scan the real files, and mutation-prove the detector so a
green result means something.

Enumerate-from-the-registry, not from a hand-listed set
------------------------------------------------------
The verb list comes from `package.yaml` — the same registry the dispatcher and
the process engine resolve commands through — so a newly registered verb is in
scope by construction. The exemption list comes from `_lib.bootstrap_gate`'s
`EXEMPT_VERBS`, not a copy: a second list here could be edited to excuse a verb
without anyone reading the reason, which is the drift this guard exists to stop.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"
PACKAGE = CAPABILITY / "package.yaml"
GATE_MODULE = SCRIPTS / "_lib" / "bootstrap_gate.py"

GATE_MODULE_NAME = "bootstrap_gate"
GATE_FUNCTION = "enforce"


def _registered_verbs() -> dict[str, Path]:
    """Every verb in `package.yaml`'s `commands:` → its script path."""
    data = YAML(typ="safe").load(PACKAGE.read_text(encoding="utf-8"))
    commands = data["commands"]
    return {verb: CAPABILITY / spec["script"] for verb, spec in commands.items()}


def _exempt_verbs() -> dict[str, str]:
    """`EXEMPT_VERBS` read from the gate module itself — never a local copy."""
    spec = importlib.util.spec_from_file_location(
        "pm_bootstrap_gate_under_test", GATE_MODULE
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return dict(module.EXEMPT_VERBS)


def _is_gate_call(func: ast.expr) -> bool:
    """Whether a call target is the gate's `enforce`.

    Matches both the `bootstrap_gate.enforce(...)` attribute form and a bare
    `enforce(...)` from a `from _lib.bootstrap_gate import enforce`.
    """
    return (
        isinstance(func, ast.Attribute)
        and func.attr == GATE_FUNCTION
        and isinstance(func.value, ast.Name)
        and func.value.id == GATE_MODULE_NAME
    ) or (isinstance(func, ast.Name) and func.id == GATE_FUNCTION)


def _gated_verbs_in(path: Path) -> set[str]:
    """The verb names this script passes to `bootstrap_gate.enforce(...)`.

    AST-based, so a mention of the call in a docstring, a comment, or a string
    does not count as coverage — only a real call node does. Matches both the
    `bootstrap_gate.enforce("verb")` attribute form and a bare
    `enforce("verb")` from a `from _lib.bootstrap_gate import enforce`.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_gate_call(node.func) or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            found.add(first.value)
    return found


VERBS = _registered_verbs()
EXEMPT = _exempt_verbs()


def test_the_registry_is_the_scope_and_every_script_exists() -> None:
    """Sanity: the guard is scanning the real, complete command surface."""
    assert len(VERBS) >= 65, f"expected the full command surface; got {len(VERBS)}"
    missing = sorted(verb for verb, path in VERBS.items() if not path.is_file())
    assert not missing, f"registered verbs with no script: {missing}"


def test_every_exempt_verb_is_registered() -> None:
    """An exemption for a verb that does not exist is dead weight that would
    quietly excuse a future verb of the same name."""
    unknown = sorted(set(EXEMPT) - set(VERBS))
    assert not unknown, f"exempt verbs not registered in package.yaml: {unknown}"


@pytest.mark.parametrize("verb", sorted(v for v in VERBS if v not in EXEMPT))
def test_every_gated_verb_calls_the_gate(verb: str) -> None:
    """The completeness half: each non-exempt verb calls the gate, naming ITSELF.

    The verb string matters, not just the call: it is what the refusal message
    prints, so a copy-paste that gates `move-issue` inside `close-issue` would
    hand the operator the wrong command to fix.
    """
    gated = _gated_verbs_in(VERBS[verb])
    assert gated, (
        f"`{verb}` does not call the prerequisite gate. Add, at the top of "
        f"main() after argument parsing:\n"
        f'    if not bootstrap_gate.enforce("{verb}", capability_root=capability_root):\n'
        f"        return 2\n"
        f"— or, if this verb genuinely must work on an un-bootstrapped project, "
        f"add it to EXEMPT_VERBS in _lib/bootstrap_gate.py WITH ITS REASON."
    )
    assert verb in gated, (
        f"`{verb}` calls the gate under the wrong verb name {sorted(gated)} — "
        f"the refusal would name a command the operator did not type."
    )


@pytest.mark.parametrize("verb", sorted(EXEMPT))
def test_no_exempt_verb_calls_the_gate(verb: str) -> None:
    """The other half, and the more dangerous one: `bootstrap` must never be
    gated (it is how a project BECOMES bootstrapped), and neither may the
    diagnosis verbs — a gated `pre-check` hides the answer the operator needs."""
    gated = _gated_verbs_in(VERBS[verb])
    assert not gated, (
        f"`{verb}` is exempt ({EXEMPT[verb]}) but calls the gate — that is a "
        f"deadlock: the project can never become bootstrapped."
    )


def test_the_exemption_list_records_a_reason_per_verb() -> None:
    """"The exemption list is decided and recorded, with the reason for each" —
    the acceptance criterion, pinned. A bare set would let a verb be excused
    without an argument."""
    for verb, reason in EXEMPT.items():
        assert len(reason.split()) >= 5, f"exemption for {verb} carries no reason"


def test_the_guard_detects_an_ungated_script(tmp_path: Path) -> None:
    """Mutation-proof: the detector fails a script that only *mentions* the gate
    and passes one that calls it. Without this, the guard above could be green
    because the detector is broken rather than because the verbs are covered."""
    mentions_only = tmp_path / "mentions.py"
    mentions_only.write_text(
        '"""This verb should call bootstrap_gate.enforce("show-tree") someday."""\n'
        "# if not bootstrap_gate.enforce('show-tree'): return 2\n"
        'HINT = "bootstrap_gate.enforce"\n',
        encoding="utf-8",
    )
    assert _gated_verbs_in(mentions_only) == set(), (
        "the detector counted a docstring / comment / string as coverage"
    )

    real_call = tmp_path / "real.py"
    real_call.write_text(
        "def main() -> int:\n"
        '    if not bootstrap_gate.enforce("show-tree", capability_root=root):\n'
        "        return 2\n"
        "    return 0\n",
        encoding="utf-8",
    )
    assert _gated_verbs_in(real_call) == {"show-tree"}


def test_the_guard_detects_a_wrong_verb_name(tmp_path: Path) -> None:
    """Mutation-proof for the verb-name half: a copy-pasted gate call naming
    another verb is visible to the detector, so the assertion above can catch
    it."""
    copy_paste = tmp_path / "copied.py"
    copy_paste.write_text(
        "def main() -> int:\n"
        '    if not bootstrap_gate.enforce("move-issue"):\n'
        "        return 2\n"
        "    return 0\n",
        encoding="utf-8",
    )
    assert _gated_verbs_in(copy_paste) == {"move-issue"}


def _has_capability_root_flag(path: Path) -> bool:
    """Whether the script exposes a `--capability-root` argument."""
    return '"--capability-root"' in path.read_text(encoding="utf-8")


def _gate_calls_pass_a_root(path: Path) -> bool:
    """Whether every `bootstrap_gate.enforce(...)` call passes `capability_root=`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_gate_call(node.func)
    ]
    return bool(calls) and all(
        any(kw.arg == "capability_root" for kw in call.keywords) for call in calls
    )


@pytest.mark.parametrize(
    "verb",
    sorted(
        v
        for v in VERBS
        if v not in EXEMPT and _has_capability_root_flag(VERBS[v])
    ),
)
def test_a_verb_that_takes_a_root_gates_that_root(verb: str) -> None:
    """A verb invoked with `--capability-root <elsewhere>` must be judged on
    THAT tree, not one walked up from the cwd.

    Otherwise the gate can pass on a bootstrapped project while the command
    operates on a different, un-bootstrapped one — a wrong-tree verdict, which
    is the same class of silent wrongness the gate exists to remove. (Verbs with
    no such flag resolve from the cwd by construction, and the gate's own
    fallback walk matches them; they are out of this parametrisation.)
    """
    assert _gate_calls_pass_a_root(VERBS[verb]), (
        f"`{verb}` accepts --capability-root but its gate call does not pass "
        f"`capability_root=`, so the gate would judge the cwd-resolved tree "
        f"instead of the one this invocation targets."
    )
