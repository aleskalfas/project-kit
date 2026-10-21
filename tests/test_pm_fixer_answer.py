"""The answer a fixer writes for an artefact (#1792; project-management DEC-056 points 3 and 6).

project-management defines, under the fixers point's version, what a fixer run
passes a fixer and what the fixer hands back. The answer is one object a schema
holds, `schemas/fixer-answer.schema.json`. These tests hold:

- the schema itself, a valid JSON Schema whose fields the README's table lists;
- the answers both fixers document validate against it: software-analysis's
  `analysis-resolver` (#1745) and living-docs' `living-docs` agent (#1746), each
  for the outcomes its body says it proposes. Where a fixer's body or
  storyboard is on this tree, the fields it lists and the example it gives are
  read from it;
- answers off the contract are refused.

The line forms and the `none` reasons are data, `schemas/fixer-contract.yaml`:
`test_pm_fixer_contract.py` holds the record and the README to it.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parent.parent
PM = REPO / ".pkit" / "capabilities" / "project-management"
SCHEMA = PM / "schemas" / "fixer-answer.schema.json"
README = PM / "README.md"

#: The answer's fields, in the order the contract and both fixers list them.
FIELDS = ("artefact", "outcome", "justification", "sentence", "keep", "diff", "first")


def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))


def _errors(answer: Any) -> list[str]:
    return [error.message for error in _validator().iter_errors(answer)]


# --- the documented answers ------------------------------------------------------------

#: The analysis-resolver's answers, as its body ("When a command starts you") gives
#: their fields and its storyboard's Scenario 4 gives its example. `holds` is that
#: example word for word.
RESOLVER_ANSWERS: dict[str, dict[str, Any]] = {
    "holds": {
        "artefact": "tech-docs/analysis/use-case-model/use-cases/UC-003-run-suite.md",
        "outcome": "unchanged",
        "justification": (
            "The CSV export adds an output format. Running a suite is untouched: "
            "run_suite and --fast work as described."
        ),
        "sentence": None,
        "keep": [],
        "diff": None,
        "first": [],
    },
    # holds, the code moved: an anchor edit recorded as unchanged
    "holds-anchor-moved": {
        "artefact": "tech-docs/analysis/use-case-model/use-cases/UC-003-run-suite.md",
        "outcome": "unchanged",
        "justification": "src/cli/run.py moved to src/cli/suite.py; anchor re-pointed.",
        "sentence": None,
        "keep": ["path:src/cli/**"],
        "diff": "tech-docs/analysis/use-case-model/use-cases/UC-003-run-suite.md/UC-003.diff",
        "first": [],
    },
    # analysis-stale: the content edited, recorded as updated
    "analysis-stale": {
        "artefact": "tech-docs/analysis/use-case-model/use-cases/UC-005-export-report.md",
        "outcome": "updated",
        "justification": None,
        "sentence": "Step 3 names --output, the option the export writes the report to.",
        "keep": [],
        "diff": ("tech-docs/analysis/use-case-model/use-cases/UC-005-export-report.md/UC-005.diff"),
        "first": [],
    },
    # code-regressed: the person's placeholder stays, and the defect comes first
    "code-regressed": {
        "artefact": "tech-docs/analysis/use-case-model/use-cases/UC-005-export-report.md",
        "outcome": "unchanged",
        "justification": (
            "The description stands: the export still needs --out; 9c41e02 broke it "
            "— defect <the defect reference> reported."
        ),
        "sentence": None,
        "keep": [],
        "diff": None,
        "first": [
            "Report the defect 9c41e02 introduced, and write its reference in the reason.",
            "Write the revalidation's record with the analysis-author skill.",
        ],
    },
    # a glossary term's entry: its folder named by the term's artefact
    "term": {
        "artefact": "tech-docs/analysis/glossary.md#TERM-run",
        "outcome": "updated",
        "justification": None,
        "sentence": "The term says a run may be started by a command.",
        "keep": [],
        "diff": "tech-docs/analysis/glossary.md#TERM-run/TERM-run.diff",
        "first": [],
    },
}

#: The living-docs agent's answers, as its body ("A fixer run") gives their fields
#: and its storyboard's Scenario 5 the page it proposes.
LIVING_DOCS_ANSWERS: dict[str, dict[str, Any]] = {
    "rewritten": {
        "artefact": "docs/install.md",
        "outcome": "updated",
        "justification": None,
        "sentence": '"Running it" writes --output, which a3f9c1e renamed from --out.',
        "keep": [],
        "diff": "docs/install.md/install.md.diff",
        "first": [],
    },
    "still-holds": {
        "artefact": "docs/install.md",
        "outcome": "unchanged",
        "justification": "a3f9c1e renames a flag the page never mentions.",
        "sentence": None,
        "keep": ["source:keep-a-changelog"],
        "diff": None,
        "first": [],
    },
}


@pytest.mark.parametrize(
    ("fixer", "case", "answer"),
    [("analysis-resolver", case, a) for case, a in RESOLVER_ANSWERS.items()]
    + [("living-docs", case, a) for case, a in LIVING_DOCS_ANSWERS.items()],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_each_fixer_s_documented_answer_validates(
    fixer: str, case: str, answer: dict[str, Any]
) -> None:
    assert tuple(answer) == FIELDS
    assert _errors(answer) == [], (fixer, case)


# --- the fixers' own files, where this tree holds them ---------------------------------

#: Each fixer's body, the section that states its side of the contract, and the
#: pull request that brings it.
FIXERS = {
    "analysis-resolver": (
        REPO / ".pkit/capabilities/software-analysis/agents/analysis-resolver/analysis-resolver.md",
        "## When a command starts you",
        "#1789",
    ),
    "living-docs": (
        REPO / ".pkit/capabilities/living-docs/agents/living-docs/living-docs.md",
        "## A fixer run",
        "#1787",
    ),
}


def _section(fixer: str) -> str:
    """The fixer's run section. Skipped only while the body says nothing of a run's
    result lines: a body that does, under another heading, fails here."""
    path, heading, pull = FIXERS[fixer]
    text = path.read_text(encoding="utf-8")
    if "Fixer result (" not in text:
        pytest.skip(f"{fixer}'s run section lands with {pull}")
    assert heading in text, f"{fixer}'s run section is no longer headed {heading!r}"
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


@pytest.mark.parametrize("fixer", sorted(FIXERS))
def test_each_fixer_lists_the_schema_s_fields(fixer: str) -> None:
    listed = re.findall(r"^  - `([a-z]+)`: ", _section(fixer), flags=re.MULTILINE)
    assert tuple(listed) == FIELDS
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert tuple(schema["required"]) == FIELDS
    assert set(schema["properties"]) == set(FIELDS)


def test_the_resolver_s_storyboard_example_validates() -> None:
    _section("analysis-resolver")
    storyboard = FIXERS["analysis-resolver"][0].parent / "storyboard.md"
    scenario = storyboard.read_text(encoding="utf-8").split("## Scenario 4:", 1)[1]
    example = scenario.split("```json\n", 1)[1].split("```", 1)[0]
    answer = json.loads(example)
    assert answer == RESOLVER_ANSWERS["holds"]
    assert _errors(answer) == []


# --- answers off the contract ----------------------------------------------------------


def _changed(base: str, **fields: Any) -> dict[str, Any]:
    answers = {**RESOLVER_ANSWERS, **LIVING_DOCS_ANSWERS}
    answer = copy.deepcopy(answers[base])
    answer.update(fields)
    return answer


def _without(base: str, field: str) -> dict[str, Any]:
    answer = _changed(base)
    del answer[field]
    return answer


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(_without("holds", "first"), id="a-field-missing"),
        pytest.param(_changed("holds", command="pkit friction revalidate"), id="a-field-more"),
        pytest.param(_changed("holds", outcome="deferred"), id="an-outcome-off-the-list"),
        pytest.param(_changed("holds", outcome="holds"), id="a-capability-s-own-outcome"),
        pytest.param(_changed("holds", justification=None), id="unchanged-without-reason"),
        pytest.param(_changed("holds", justification="  "), id="unchanged-with-a-blank-reason"),
        pytest.param(_changed("holds", sentence="It changed."), id="unchanged-with-a-sentence"),
        pytest.param(_changed("rewritten", diff=None), id="updated-without-a-diff"),
        pytest.param(_changed("rewritten", sentence=None), id="updated-without-a-sentence"),
        pytest.param(_changed("rewritten", sentence="One.\nTwo."), id="a-sentence-of-two-lines"),
        pytest.param(_changed("rewritten", justification="Why."), id="updated-with-a-reason"),
        pytest.param(_changed("holds", keep=["src/cli/**"]), id="a-deferral-without-its-kind"),
        pytest.param(_changed("holds", keep=["path:a", "path:a"]), id="a-deferral-twice"),
        pytest.param(_changed("rewritten", diff="../install.md.diff"), id="a-diff-above"),
        pytest.param(_changed("rewritten", diff="/tmp/install.md.diff"), id="a-diff-absolute"),
        pytest.param(_changed("rewritten", diff="docs/../x.diff"), id="a-diff-through-dot-dot"),
        pytest.param(_changed("rewritten", diff="docs/install.md/x.sh"), id="a-diff-not-a-diff"),
        pytest.param(_changed("rewritten", artefact="docs/a`b.md"), id="a-name-with-a-backtick"),
        pytest.param(_changed("rewritten", artefact="docs/a\nb.md"), id="a-name-with-a-break"),
        pytest.param(_changed("rewritten", artefact="docs/a.md\n"), id="a-name-ending-a-line"),
        pytest.param(_changed("rewritten", artefact="docs/a\u0085b.md"), id="a-name-with-nel"),
        pytest.param(_changed("rewritten", artefact="docs/a\u2028b.md"), id="a-name-with-a-ls"),
        pytest.param(_changed("rewritten", artefact="/etc/passwd"), id="a-name-absolute"),
        pytest.param(_changed("rewritten", artefact="docs/../x.md"), id="a-name-through-dot-dot"),
        pytest.param(_changed("rewritten", artefact="./x.md"), id="a-name-through-dot"),
        pytest.param(_changed("rewritten", diff="docs/a.md/a.diff\n"), id="a-diff-ending-a-line"),
        pytest.param(_changed("holds", justification="Holds.\x1b[8m hidden"), id="an-escape"),
        pytest.param(_changed("holds", justification="Holds.\u202edlo"), id="a-bidi-override"),
        pytest.param(_changed("holds", justification="Holds.\u2067x\u2069"), id="a-bidi-isolate"),
        pytest.param(_changed("holds", justification="Holds.\u200b"), id="a-zero-width-space"),
        pytest.param(_changed("holds", justification="\ufeffHolds."), id="a-byte-order-mark"),
        pytest.param(_changed("holds", justification="Holds." + chr(0x061C)), id="a-letter-mark"),
        pytest.param(_changed("holds", justification="Holds." + chr(0x00AD)), id="a-soft-hyphen"),
        pytest.param(_changed("holds", justification="Holds." + chr(0xE0069)), id="a-tag"),
        pytest.param(_changed("holds", justification="Holds." + chr(0xE007F)), id="a-cancel-tag"),
        pytest.param(_changed("holds", justification="Holds." + chr(0xFFFB)), id="an-annotation"),
        pytest.param(_changed("rewritten", sentence="One.\n"), id="a-sentence-ending-a-line"),
        pytest.param(_changed("holds", keep=["path:a\n"]), id="a-deferral-ending-a-line"),
        pytest.param(_changed("holds", first=[""]), id="an-empty-step"),
        pytest.param(_changed("holds", first=["Do one.\nDo two."]), id="a-step-of-two-lines"),
        pytest.param(_changed("holds", keep="path:a"), id="keep-not-a-list"),
        pytest.param([RESOLVER_ANSWERS["holds"]], id="a-list-of-answers"),
    ],
)
def test_an_answer_off_the_contract_is_refused(answer: Any) -> None:
    assert _errors(answer) != []


# --- the schema and the documentation --------------------------------------------------


def test_the_schema_is_valid_and_its_fields_are_the_contract_s() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert tuple(schema["required"]) == FIELDS
    assert tuple(schema["properties"]) == FIELDS


def test_the_schema_s_version_is_the_fixers_point_s() -> None:
    """The point's version covers the run's contract (DEC-056 point 1), so the answer's
    schema names the version the point is accepted at."""
    package = YAML(typ="safe").load((PM / "package.yaml").read_text(encoding="utf-8"))
    point = package["connections"]["extension-points"]["accepts"]["pkit::work-tracking:fixers"]
    title = json.loads(SCHEMA.read_text(encoding="utf-8"))["title"]
    assert title.endswith(f"under pkit::work-tracking:fixers version {point['schema_version']}")


def _readme_contract() -> str:
    text = README.read_text(encoding="utf-8")
    return text.split("**The version covers what a fixer run passes and returns.**", 1)[1].split(
        "\n## ", 1
    )[0]


def test_the_readme_names_the_schema_s_fields() -> None:
    answer = _readme_contract().split("- **The answer,**", 1)[1].split("\n  - ", 1)[0]
    assert tuple(re.findall(r"`([a-z]+)`", answer)) == FIELDS
    assert "`schemas/fixer-answer.schema.json`" in answer
