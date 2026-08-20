"""Tests for `_lib/checkbox_gate.py` — DEC-007's unticked-checkbox rule.

Two jobs. First, pin the rule itself: what counts as an unticked box, the
"no boxes at all is complete" carve-out, and the refusal's shape.

Second — and the reason this module exists rather than more per-script tests —
pin that the rule is *genuinely shared* (#734). It used to be written out
separately in `close-issue`, `merge-pr`, and `_lib/lifecycle_inference` (the
engine predicate's path), which is exactly how three copies drift. The
identity assertions below fail the moment any call site forks its own copy
back out, which no behavioural test on a single script would catch.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)

sys.path.insert(0, str(SCRIPTS))
from _lib import checkbox_gate  # noqa: E402
from _lib import lifecycle_inference  # noqa: E402


def _load_script(name: str):
    module_name = f"pm_{name.replace('-', '_')}_checkbox_gate_under_test"
    spec = importlib.util.spec_from_file_location(
        module_name, SCRIPTS / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- the rule ---------------------------------------------------------


def test_unticked_boxes_finds_dash_and_asterisk_styles() -> None:
    body = "- [ ] first\n* [ ] second\n"
    assert checkbox_gate.unticked_boxes(body) == ["- [ ] first", "* [ ] second"]


def test_unticked_boxes_handles_indentation() -> None:
    body = "  - [ ] nested\n\t- [ ] tabbed\n"
    assert len(checkbox_gate.unticked_boxes(body)) == 2


def test_unticked_boxes_ignores_ticked_boxes() -> None:
    assert checkbox_gate.unticked_boxes("- [x] done\n- [X] also done\n") == []


def test_unticked_boxes_ignores_plain_list_items() -> None:
    body = "- a bullet, not a box\n- [ ] a box\n"
    assert checkbox_gate.unticked_boxes(body) == ["- [ ] a box"]


def test_unticked_boxes_ignores_a_bare_box() -> None:
    """A contentless `- [ ]` is an unauthored skeleton, not an open claim.

    Reporting it belongs to `placeholder_detection`, which distinguishes "the
    author never filled this section in" from "this criterion is not yet met".
    """
    assert checkbox_gate.unticked_boxes("## Test plan\n\n- [ ]\n") == []


@pytest.mark.parametrize("body", ["", None, "no boxes here at all\n"])
def test_all_boxes_ticked_true_without_boxes(body) -> None:
    """DEC-007 applies only when boxes exist; an absent set is complete."""
    assert checkbox_gate.all_boxes_ticked(body) is True


def test_all_boxes_ticked_false_when_any_unticked() -> None:
    assert checkbox_gate.all_boxes_ticked("- [x] one\n- [ ] two\n") is False


# --- the refusal shape ------------------------------------------------


def test_refusal_message_lists_each_box_then_the_remedy() -> None:
    message = checkbox_gate.refusal_message(
        ["- [ ] first", "- [ ] second"], remedy="tick them.",
    )
    lines = message.splitlines()
    assert lines[0] == "[refused] DEC-007 checkbox close-gate:"
    assert lines[1] == "  - - [ ] first"
    assert lines[2] == "  - - [ ] second"
    assert lines[-1] == "  → tick them."


def test_refusal_message_scope_qualifies_the_header() -> None:
    message = checkbox_gate.refusal_message(
        ["- [ ] x"], remedy="tick it.", scope="cascade-eligibility",
    )
    assert message.startswith(
        "[refused] DEC-007 checkbox close-gate (cascade-eligibility):"
    )


# --- one implementation, every call site (#734) -----------------------


def test_engine_predicate_path_reads_the_shared_rule() -> None:
    """`lifecycle_inference` re-exports the rule; it does not restate it.

    This is the engine predicate's path: `gate-checkboxes-ticked` →
    `lifecycle_predicates.gate_checkboxes_ticked` → `infer.unticked_boxes`.
    """
    assert lifecycle_inference.unticked_boxes is checkbox_gate.unticked_boxes


@pytest.mark.parametrize("script", ["close-issue", "done-work", "merge-pr"])
def test_command_call_sites_read_the_shared_rule(script: str) -> None:
    """Every command that refuses on checkboxes resolves to the one rule.

    A script that reintroduces a local `_unticked_boxes` body — however
    faithful a copy — fails here, which is the drift #734 closes.
    """
    module = _load_script(script)
    resolved = getattr(module, "_unticked_boxes", None) or getattr(
        module, "unticked_boxes", None
    )
    assert resolved is checkbox_gate.unticked_boxes, (
        f"{script} does not use `_lib.checkbox_gate.unticked_boxes`"
    )


def test_predicate_and_done_work_agree_on_a_body() -> None:
    """The engine's gate and done-work's pre-flight give the same verdict.

    Same rule, so the same answer — asserted on a body that exercises the
    ticked / unticked / bare-box / plain-bullet cases together.
    """
    body = (
        "## Acceptance criteria\n\n"
        "- [x] shipped\n"
        "- [ ] tested\n"
        "- [ ]\n"
        "- not a box\n"
    )
    done_work = _load_script("done-work")
    result = done_work._check_checkbox_gate(
        7, {"labels": [], "body": body}, skip=False,
    )
    assert result.passed is False
    assert lifecycle_inference.unticked_boxes(body) == ["- [ ] tested"]
