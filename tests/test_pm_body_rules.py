"""Unit tests for the _lib/body_rules reader (DEC-010).

The one reader of `body-format.yaml`'s body rules that `create-issue`,
`edit-issue` and `validate-issue` share: each section an issue type requires,
and the universal rules a body is checked against, at the severity the schema
gives each.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"

sys.path.insert(0, str(CAPABILITY_ROOT / "scripts"))

from _lib import body_rules  # noqa: E402

TASK_BODY = (
    "Feature: #1\n\n"
    "## What\nthe change\n\n"
    "## Acceptance criteria\n\n- [ ] it holds\n\n"
    "## Doc impact\n\nNo doc impact: internal only.\n"
)


@pytest.fixture(scope="module")
def shipped() -> dict:
    """The shipped body-format.yaml, as every command reads it."""
    path = CAPABILITY_ROOT / "schemas" / "body-format.yaml"
    return YAML(typ="safe").load(path.read_text(encoding="utf-8"))


def _labels(findings) -> list[str]:
    return [label for _severity, label, _detail in findings]


# ---- required sections ----------------------------------------------


@pytest.mark.parametrize("issue_type", ["epic", "feature", "umbrella", "task"])
def test_each_type_requires_the_sections_the_schema_lists(shipped, issue_type) -> None:
    """For each issue type, a body without a section its entry lists is refused,
    naming that section, at the entry's severity."""
    headings = [s["heading"] for s in shipped["bodies"][issue_type]["required_sections"]]
    for missing in headings:
        body = "\n\n".join(f"{h}\n\ntext" for h in headings if h != missing)
        findings = body_rules.required_sections(body, issue_type, shipped)
        assert [(s, label) for s, label, _ in findings] == [
            ("hard-reject", "body.required-section")
        ]
        assert repr(missing) in findings[0][2]


def test_a_body_with_every_required_section_passes(shipped) -> None:
    assert body_rules.check(TASK_BODY, "task", shipped) == []


def test_no_type_requires_no_section(shipped) -> None:
    assert body_rules.required_sections("no sections", None, shipped) == []


def test_a_schema_without_bodies_requires_nothing() -> None:
    assert body_rules.required_sections("no sections", "task", {"sections": {}}) == []


# ---- universal rules ------------------------------------------------


def test_a_heading_of_the_first_level_is_refused(shipped) -> None:
    findings = body_rules.check(TASK_BODY + "\n# A title again\n", "task", shipped)
    assert [(s, label) for s, label, _ in findings] == [("hard-reject", "body.h1")]


def test_a_hash_line_in_a_fenced_block_is_no_heading(shipped) -> None:
    """A shell comment in a fenced code block is not a heading of the first level."""
    body = TASK_BODY + "\n```sh\n# run it\npkit pm show-issue 1\n```\n\n~~~\n# also\n~~~\n"
    assert body_rules.check(body, "task", shipped) == []


def test_a_heading_after_a_closed_fence_is_still_read(shipped) -> None:
    body = TASK_BODY + "\n```\ncode\n```\n# A title again\n"
    assert _labels(body_rules.check(body, "task", shipped)) == ["body.h1"]


def test_a_file_line_reference_warns(shipped) -> None:
    findings = body_rules.check(TASK_BODY + "\nSee foo/bar.py:42.\n", "task", shipped)
    assert [(s, label) for s, label, _ in findings] == [("warning", "body.file-line-refs")]


@pytest.mark.parametrize("heading", ["## Implementation", "## How"])
def test_an_implementation_recipe_warns(shipped, heading) -> None:
    findings = body_rules.check(TASK_BODY + f"\n{heading}\n\nstep one\n", "task", shipped)
    assert [(s, label) for s, label, _ in findings] == [("warning", "body.implementation-recipe")]
    assert repr(heading) in findings[0][2]


@pytest.mark.parametrize("heading", ["## Implementation notes", "## How to reproduce"])
def test_a_longer_heading_is_no_recipe(shipped, heading) -> None:
    """`## Implementation notes` is a section the templates recommend, and a
    heading that only starts with `How` names no recipe."""
    assert body_rules.check(TASK_BODY + f"\n{heading}\n\ntext\n", "task", shipped) == []


def test_each_rule_that_only_warns_is_reported_and_nothing_refuses(shipped) -> None:
    body = TASK_BODY + "\nSee foo/bar.py:42.\n\n## How\n\nstep one\n"
    findings = body_rules.check(body, "task", shipped)
    assert sorted(_labels(findings)) == ["body.file-line-refs", "body.implementation-recipe"]
    assert not body_rules.blocking(findings)


# ---- severities read from the schema --------------------------------


def test_the_shipped_schema_names_each_universal_rule_it_checks(shipped) -> None:
    """The universal rules this reader checks carry their label as `id`, with the
    severity DEC-010 gives each, so the reader takes it from the schema."""
    by_id = {r.get("id"): r["severity"] for r in shipped["universal_body_rules"]}
    assert by_id["body.h1"] == "[validation-severity:hard-reject]"
    assert by_id["body.file-line-refs"] == "[validation-severity:warning]"
    assert by_id["body.implementation-recipe"] == "[validation-severity:warning]"


def test_a_universal_rule_takes_its_severity_from_the_schema() -> None:
    schema = {
        "universal_body_rules": [
            {
                "id": "body.file-line-refs",
                "rule": "x",
                "severity": "[validation-severity:hard-reject]",
            }
        ]
    }
    findings = body_rules.universal("See foo/bar.py:42.", schema)
    assert findings[0][:2] == ("hard-reject", "body.file-line-refs")
    assert body_rules.blocking(findings) == findings


def test_a_schema_without_the_rule_gives_its_default() -> None:
    findings = body_rules.universal("# Title\n\nSee foo/bar.py:42.\n\n## How\n", {})
    assert [(s, label) for s, label, _ in findings] == [
        ("hard-reject", "body.h1"),
        ("warning", "body.file-line-refs"),
        ("warning", "body.implementation-recipe"),
    ]


# ---- what the fence reader leaves to be read ------------------------


@pytest.mark.parametrize(
    "body",
    [
        "```x`\n# Heading\n",  # a backtick in a backtick fence's info string: no fence
        "- item\n  ```\n# Heading\n",  # a fence never closed hides nothing
    ],
)
def test_a_line_no_closed_fence_holds_is_still_read(shipped, body) -> None:
    assert _labels(body_rules.universal(body, shipped)) == ["body.h1"]


def test_the_file_line_check_stays_linear_on_a_long_body(shipped) -> None:
    """A long run with no `:digits` after it is read in linear time: a body file
    has no length limit before `create-issue` checks it."""
    import time

    started = time.monotonic()
    assert body_rules.universal("a." * 500_000, shipped) == []
    assert time.monotonic() - started < 2
    assert _labels(body_rules.universal("x see foo/bar.py:42 y", shipped)) == [
        "body.file-line-refs"
    ]
