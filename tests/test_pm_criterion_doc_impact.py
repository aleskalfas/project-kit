"""check-criterion / uncheck-criterion address `## Doc impact` boxes (#1015).

`--section doc-impact` points the same index + expected-text grammar at the
Doc impact section, numbered as `show-issue --field doc-impact` numbers it, so
closing a Task whose Doc impact section uses checkboxes no longer needs a
whole-body rewrite. The address helpers behind done-work's refusal hints are
pinned here too. Every `gh` call is faked.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAP_ROOT / "scripts"

TASK_BODY = (
    "Milestone: [#5](../milestone/5)\n\n"
    "## What\n\nwork\n\n"
    "## Acceptance criteria\n\n"
    "- [x] the verb ticks it\n"
    "- [ ] a test covers it\n\n"
    "## Doc impact\n\n"
    "- [ ] The pm README documents it\n"
    "- [ ] The skill mentions it\n"
)


@pytest.fixture(scope="module")
def lib():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from _lib import criteria, criterion_ops

    return SimpleNamespace(criteria=criteria, ops=criterion_ops)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        f"pm_{name.replace('-', '_')}_doc_impact_under_test", SCRIPTS / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --- the engine, pointed at the Doc impact section ------------------------


def test_doc_impact_boxes_are_numbered_within_their_section(lib) -> None:
    items = lib.criteria.extract_criteria(TASK_BODY, lib.criteria.DOC_IMPACT_HEADINGS)
    assert [(i.index, i.text) for i in items] == [
        (1, "The pm README documents it"),
        (2, "The skill mentions it"),
    ]


def test_the_engine_ticks_a_doc_impact_box_with_a_guard(lib) -> None:
    plan = lib.ops.plan_batch(
        TASK_BODY,
        [lib.ops.Target(2, "The skill mentions it")],
        target_checked=True,
        headings=lib.criteria.DOC_IMPACT_HEADINGS,
        noun="doc-impact box",
        plural="doc-impact boxes",
    )
    assert plan.accepted and plan.changed
    assert "- [x] The skill mentions it" in plan.new_body
    assert "- [ ] a test covers it" in plan.new_body  # the criteria are untouched
    assert plan.results[0].message == "doc-impact box 2: ticked"


def test_an_out_of_range_doc_impact_index_names_the_section(lib) -> None:
    plan = lib.ops.plan_batch(
        TASK_BODY,
        [lib.ops.Target(3)],
        target_checked=True,
        headings=lib.criteria.DOC_IMPACT_HEADINGS,
        noun="doc-impact box",
        plural="doc-impact boxes",
    )
    assert not plan.accepted
    assert (
        plan.results[0].message == "doc-impact box 3: out of range (issue has 2 doc-impact boxes)"
    )


# --- addresses and the tick hints done-work shows -------------------------


def test_checkbox_addresses_cover_both_sections(lib) -> None:
    lines = TASK_BODY.splitlines()
    addresses = lib.criteria.checkbox_addresses(TASK_BODY)
    by_text = {lines[n].strip(): where for n, where in addresses.items()}
    assert by_text == {
        "- [x] the verb ticks it": ("criteria", 1),
        "- [ ] a test covers it": ("criteria", 2),
        "- [ ] The pm README documents it": ("doc-impact", 1),
        "- [ ] The skill mentions it": ("doc-impact", 2),
    }


def test_tick_hints_name_check_criterion_or_the_body_edit(lib) -> None:
    body = TASK_BODY + "\n## Notes\n\n- [ ] elsewhere\n"
    lines = body.splitlines()
    wanted = [
        lines.index("- [ ] a test covers it"),
        lines.index("- [ ] The skill mentions it"),
        lines.index("- [ ] elsewhere"),
    ]
    hints = lib.criteria.tick_hints(7, body, wanted)
    assert hints[0] == "pkit pm check-criterion 7 2"
    assert hints[1] == "pkit pm check-criterion 7 --section doc-impact 2"
    assert "pkit pm edit-issue 7 --body-file" in hints[2]


# --- the verb, end to end -------------------------------------------------


def _run_verb(monkeypatch, script: str, argv: list[str], body: str = TASK_BODY) -> SimpleNamespace:
    module = _load(script)
    from _lib import criterion_cli

    monkeypatch.setattr(sys, "argv", [script, *argv])
    monkeypatch.setattr(module.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(criterion_cli, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(criterion_cli, "load_adopter_config", lambda _root: {})
    monkeypatch.setattr(criterion_cli, "_read_members", lambda *a: [])
    monkeypatch.setattr(
        criterion_cli, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(criterion_cli, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(criterion_cli.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(
        criterion_cli, "gh_get_issue", lambda n, config, fields: {"title": "[Task] t", "body": body}
    )
    written: list[str] = []
    monkeypatch.setattr(
        criterion_cli,
        "_gh_write_body",
        lambda n, new_body, config: written.append(new_body) or True,
    )
    return SimpleNamespace(rc=module.main(), written=written)


def test_check_criterion_ticks_a_doc_impact_box(monkeypatch, capsys) -> None:
    rec = _run_verb(monkeypatch, "check-criterion", ["42", "--section", "doc-impact", "1", "--yes"])
    assert rec.rc == 0
    assert len(rec.written) == 1
    assert "- [x] The pm README documents it" in rec.written[0]
    assert "- [ ] The skill mentions it" in rec.written[0]
    assert "- [ ] a test covers it" in rec.written[0]
    assert "doc-impact box 1: ticked" in capsys.readouterr().out


def test_uncheck_criterion_unticks_a_doc_impact_box(monkeypatch) -> None:
    body = TASK_BODY.replace("- [ ] The skill mentions it", "- [x] The skill mentions it")
    rec = _run_verb(
        monkeypatch, "uncheck-criterion", ["42", "--section", "doc-impact", "2", "--yes"], body=body
    )
    assert rec.rc == 0
    assert "- [ ] The skill mentions it" in rec.written[0]


def test_without_section_the_criteria_are_addressed_as_before(monkeypatch) -> None:
    rec = _run_verb(monkeypatch, "check-criterion", ["42", "2", "--yes"])
    assert rec.rc == 0
    assert "- [x] a test covers it" in rec.written[0]
    assert "- [ ] The pm README documents it" in rec.written[0]


def test_show_issue_numbers_the_doc_impact_items() -> None:
    """The index check-criterion takes is the line show-issue prints."""
    si = _load("show-issue")
    doc_impact = si._extract_criteria(TASK_BODY, si.DOC_IMPACT_HEADINGS)
    assert doc_impact == ["The pm README documents it", "The skill mentions it"]
    assert "doc-impact" in si.ISSUE_FIELD_NAMES
