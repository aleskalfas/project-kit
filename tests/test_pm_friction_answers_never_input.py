"""The friction answers' section is never input (project-management DEC-055 point 4).

A pull request's `## Friction answers` section carries the artefacts' words, as the
change check lists them. No reader of the description treats it as input: a
reason saying "fixes #77" closes nothing and meets no closing requirement, a
`## Doc impact` in a reason is no Doc impact section, and a path in it overrides no
mapping (`test_pm_check_doc_mapping`). Each reader here is the capability's own:
`pr_validation` (behind done-work, merge-pr, validate-pr, open-pr and edit-pr),
show-pr, show-tree and `lifecycle_inference`. done-work's close of the issues a PR
closes is tested through land-work (`test_pm_land_work`).
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAP_ROOT / "scripts"


@pytest.fixture(scope="module")
def scripts() -> Iterator[None]:
    sys.path.insert(0, str(SCRIPTS))
    yield
    sys.path.remove(str(SCRIPTS))


def _script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"pm_never_input_{name}", SCRIPTS / name)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _body(scripts: None) -> str:
    """A PR body closing #42, with a Doc impact section and a list whose reason
    reads as a closing reference and names a Doc impact heading."""
    from _lib import friction_answers

    entry = {
        "artefact": "guide",
        "location": "docs/guide.md",
        "answer": "unchanged",
        "anchor": None,
        "reason": "fixes #77 — the ## Doc impact of the guide holds",
        "kept": [],
        "asked": True,
        "status": "stands",
        "new": False,
    }
    section = friction_answers.render({"base": {"commit": "b" * 40}, "answers": [entry]}, "a" * 40)
    assert section is not None
    return f"Closes #42\n\n## Summary\n\nWork.\n\n## Doc impact\n\nThe README.\n\n{section}\n"


def test_pr_validation_reads_no_closing_reference_in_the_section(scripts: None) -> None:
    from _lib import pr_validation

    body = _body(scripts)
    assert pr_validation.extract_closing_issues(body) == [42]
    # A closing reference only in the section meets no closing requirement, and a
    # Doc impact heading only in it is no Doc impact section.
    without = body.replace("Closes #42\n\n", "").replace("## Doc impact\n\nThe README.\n\n", "")
    findings = pr_validation.validate_pr(
        pr_title="feat(pm): x",
        pr_body=without,
        titles={},
        classification={},
        git_conv={},
        closing_type_labels=[],
    )
    assert {f.label for f in findings} == {"body.closes", "body.doc-impact"}
    # A closing reference added for #77 is added: the section does not close it.
    assert "Closes #77" in pr_validation.with_closing_references(body, [77])


def test_show_pr_reads_no_closing_reference_or_doc_impact_in_the_section(scripts: None) -> None:
    show_pr = _script("show-pr.py")
    body = _body(scripts)
    assert show_pr._extract_closing_issues(body) == [42]
    bare = body.replace("## Doc impact\n\nThe README.\n\n", "")
    summary = show_pr._summarise({"title": "feat(pm): x", "body": bare})
    assert summary["closes"] == [42] and summary["has_doc_impact_section"] is False
    assert summary["body"] == bare  # shown as it is: only its reading leaves the section out


def test_show_tree_links_no_issue_the_section_names(scripts: None) -> None:
    show_tree = _script("show-tree.py")
    prs = show_tree._parse_prs(
        [{"number": 9, "title": "t", "state": "OPEN", "body": _body(scripts)}]
    )
    assert prs[9].closes == [42]


def test_lifecycle_inference_reads_no_closing_reference_in_the_section(scripts: None) -> None:
    from _lib import lifecycle_inference

    assert lifecycle_inference.closing_issue_numbers(_body(scripts)) == [42]
