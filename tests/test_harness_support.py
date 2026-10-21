"""Harness support (COR-047 points 2 to 5; #1853): each adapter's support declaration,
and the report of what the project's harness leaves unmet.

- every shipped adapter answers every core harness requirement, and its declaration
  passes its schema; the Claude Code adapter's version bound on the confined run is the
  runner's tested range;
- each requirement resolves to exactly one of satisfied, unsatisfied or indeterminate.
  The pass reads files only, so it confirms nothing: silence, an answer for no version or
  for versions it cannot check, and a `supported` or `at-cost` answer are indeterminate,
  never satisfied; a `not-achievable` answer for every version is unsatisfied, its grade
  kept and its provenance `computed`;
- `pkit harness report` reports for each registered adapter, offline, in words and in
  JSON; it exits 1 when anything is unmet and 3 on a declaration its schema refuses;
- `pkit validate`'s schemas member checks each declaration's shape, and warns on an
  answer to a requirement the core does not declare.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import harness_support, schemas_validate
from project_kit.cli import main
from project_kit.harness_support import (
    AT_COST,
    COMPUTED,
    INDETERMINATE,
    NOT_ACHIEVABLE,
    SUPPORTED,
    UNBOUNDED,
    UNSATISFIED,
    Requirement,
)
from project_kit.validators import Severity

REPO = Path(__file__).resolve().parent.parent
ADAPTERS = REPO / ".pkit" / "adapters"
SCHEMAS = REPO / ".pkit" / "schemas"

OUTSIDE = Requirement("outside", "Seen from outside", "out-of-session")
INSIDE = Requirement("inside", "Seen from inside", "in-session")
HOOKED = Requirement("hooked", "Seen at the hooks", "interposed-runtime")


def _shipped_adapters() -> list[str]:
    return sorted(p.name for p in ADAPTERS.iterdir() if (p / "package.yaml").is_file())


def _answer(grade: str, versions: Any = UNBOUNDED) -> dict[str, Any]:
    answer: dict[str, Any] = {"grade": grade, "harness_versions": versions, "evidence": "e"}
    if grade == AT_COST:
        answer["cost"] = "  a  setting  "
    return answer


# --- the shipped declarations -----------------------------------------------------------


@pytest.mark.parametrize("adapter", _shipped_adapters())
def test_every_shipped_adapter_answers_every_core_requirement(adapter: str) -> None:
    known = harness_support.requirements(REPO)
    assert known, "the core declares no harness requirement"
    assert harness_support.shape_problems(REPO, adapter) == []
    document = harness_support.load_declaration(REPO, adapter)
    assert document is not None, f"{adapter} ships no {harness_support.DECLARATION}"
    assert list(document["requirements"]) == [r.id for r in known]


def test_the_shipped_schema_pair_validates() -> None:
    report = schemas_validate.validate_path(SCHEMAS / "harness-support.yaml", REPO)
    assert report.is_clean, report.issues
    assert report.pairs_checked == 1


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_confined_runs_version_bound_is_the_runners_tested_range() -> None:
    """Only the author who ran the probe widens either (COR-047 point 2, ADR-066
    point 12): the declaration claims the versions the runner admits, no more."""
    runner = _load(ADAPTERS / "claude-code" / "run-agent.py", "claude_code_runner_for_support")
    document = harness_support.load_declaration(REPO, "claude-code")
    assert document is not None
    answer = document["requirements"]["unattended-confined-run"]
    assert answer["harness_versions"] == list(runner.TESTED_RANGE)


# --- resolution -------------------------------------------------------------------------


def test_silence_is_indeterminate_with_no_grade() -> None:
    result = harness_support.resolve(OUTSIDE, None)
    assert (result.result, result.grade, result.provenance) == (INDETERMINATE, None, None)
    assert "no declaration" in result.reason
    assert not result.met


@pytest.mark.parametrize("requirement", [OUTSIDE, INSIDE, HOOKED])
@pytest.mark.parametrize("grade", [SUPPORTED, AT_COST])
def test_a_grade_nothing_was_read_to_confirm_is_indeterminate(
    requirement: Requirement, grade: str
) -> None:
    """The pass reaches no observation point, the configuration outside a session
    included, so a declared grade is reported, never taken as satisfied."""
    result = harness_support.resolve(requirement, _answer(grade))
    assert (result.result, result.grade, result.provenance) == (INDETERMINATE, grade, None)
    assert requirement.observation_point in result.reason
    assert "nothing was read to confirm" in result.reason


def test_an_at_cost_answer_names_its_cost() -> None:
    assert harness_support.resolve(OUTSIDE, _answer(AT_COST)).cost == "a setting"


@pytest.mark.parametrize("requirement", [OUTSIDE, INSIDE])
def test_not_achievable_is_unsatisfied_and_keeps_its_grade(requirement: Requirement) -> None:
    result = harness_support.resolve(requirement, _answer(NOT_ACHIEVABLE))
    assert (result.result, result.grade, result.provenance) == (
        UNSATISFIED,
        NOT_ACHIEVABLE,
        COMPUTED,
    )


@pytest.mark.parametrize("grade", [SUPPORTED, AT_COST, NOT_ACHIEVABLE])
def test_an_answer_tested_on_no_version_is_no_grade_of_the_harness(grade: str) -> None:
    result = harness_support.resolve(OUTSIDE, _answer(grade, []))
    assert (result.result, result.grade) == (INDETERMINATE, None)
    assert "covers no harness version" in result.reason


@pytest.mark.parametrize("grade", [SUPPORTED, NOT_ACHIEVABLE])
def test_an_answer_bounded_to_tested_versions_is_indeterminate(grade: str) -> None:
    result = harness_support.resolve(OUTSIDE, _answer(grade, ["2.1.300", "2.1.310"]))
    assert (result.result, result.grade) == (INDETERMINATE, grade)
    assert "2.1.300 to 2.1.310" in result.reason
    assert result.harness_versions == ("2.1.300", "2.1.310")


# --- the command and the validate check -------------------------------------------------

REQUIREMENTS = """\
schema_version: 1
requirements:
  outside:
    title: Seen from outside
    behaviour: b
    observation_point: out-of-session
    evidence: e
  inside:
    title: Seen from inside
    behaviour: b
    observation_point: in-session
    evidence: e
"""

ANSWERED = """\
schema_version: 1
requirements:
  outside:
    grade: not-achievable
    harness_versions: unbounded
    evidence: tested
  inside:
    grade: supported
    harness_versions: unbounded
    evidence: tested
"""


def _project(tmp_path: Path, declarations: dict[str, str | None]) -> Path:
    root = tmp_path / "proj"
    schemas = root / ".pkit" / "schemas"
    schemas.mkdir(parents=True)
    (schemas / "harness-requirements.yaml").write_text(REQUIREMENTS, encoding="utf-8")
    shutil.copy(SCHEMAS / "harness-support.schema.json", schemas / "harness-support.schema.json")
    components = "".join(
        f"  - kind: adapter\n    name: {name}\n"
        f"    manifest: .pkit/adapters/{name}/project/manifest.yaml\n"
        for name in declarations
    )
    registry = components or "  []\n"
    (root / ".pkit" / "manifest.yaml").write_text(
        f"backbone_version: 0.0.0\ncomponents:\n{registry}", encoding="utf-8"
    )
    for name, text in declarations.items():
        folder = root / ".pkit" / "adapters" / name
        folder.mkdir(parents=True)
        if text is not None:
            (folder / harness_support.DECLARATION).write_text(text, encoding="utf-8")
    return root


def _run(root: Path, monkeypatch: pytest.MonkeyPatch, *args: str) -> Any:
    monkeypatch.chdir(root)
    return CliRunner().invoke(main, ["harness", "report", *args])


def test_the_command_reports_each_registered_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path, {"one": ANSWERED, "two": None})
    done = _run(root, monkeypatch)
    assert done.exit_code == 1, done.output
    out = done.stdout
    assert out.startswith("Harness requirements — 4 unmet of 4")
    assert "ONE — .pkit/adapters/one/harness-support.yaml" in out
    assert "TWO — no support declaration" in out
    rows = [line.split() for line in out.splitlines() if line.startswith("  ")]
    assert [row[:4] for row in rows if row[1] in ("outside", "inside")] == [
        ["unsatisfied", "outside", "not-achievable", "computed"],
        ["indeterminate", "inside", "supported", "its"],
        ["indeterminate", "outside", "—", "no"],
        ["indeterminate", "inside", "—", "no"],
    ]
    legend = {line.split()[0] for line in out.split("Legend\n")[1].split("\n\n")[0].splitlines()}
    assert legend == {"unsatisfied", "indeterminate", "supported", "not-achievable", "computed"}


def test_the_command_emits_one_json_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path, {"one": ANSWERED})
    done = _run(root, monkeypatch, "--json")
    assert done.exit_code == 1, done.output
    document = json.loads(done.stdout)
    assert document["schema_version"] == 1
    assert document["requirements"] == ["outside", "inside"]
    assert document["unmet"] == 2
    [adapter] = document["adapters"]
    assert adapter["adapter"] == "one"
    assert adapter["declaration"] == ".pkit/adapters/one/harness-support.yaml"
    assert [
        (r["id"], r["result"], r["grade"], r["provenance"], r["harness_versions"])
        for r in adapter["requirements"]
    ] == [
        ("outside", UNSATISFIED, NOT_ACHIEVABLE, COMPUTED, UNBOUNDED),
        ("inside", INDETERMINATE, SUPPORTED, None, UNBOUNDED),
    ]


def test_with_no_adapter_registered_every_requirement_is_indeterminate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path, {})
    done = _run(root, monkeypatch)
    assert done.exit_code == 1, done.output
    assert "Harness requirements — 2 unmet of 2" in done.stdout
    assert "NO ADAPTER — none is registered" in done.stdout


def test_nothing_unmet_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _project(tmp_path, {"one": ANSWERED})
    (root / ".pkit" / "schemas" / "harness-requirements.yaml").write_text(
        "schema_version: 1\nrequirements: {}\n", encoding="utf-8"
    )
    done = _run(root, monkeypatch)
    assert done.exit_code == 0, done.output
    assert "Harness requirements — 0 unmet of 0" in done.stdout
    assert "the core declares no harness requirement" in done.stdout


def test_the_command_refuses_a_declaration_its_schema_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(
        tmp_path,
        {
            "one": "schema_version: 1\nrequirements:\n  outside:\n    grade: at-cost\n"
            "    harness_versions: unbounded\n    evidence: e\n"
        },
    )
    done = _run(root, monkeypatch)
    assert done.exit_code == 3, done.output
    assert ".pkit/adapters/one/harness-support.yaml/requirements/outside" in done.stderr
    assert "cost" in done.stderr


def test_the_command_refuses_an_unknown_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path, {"one": ANSWERED})
    assert _run(root, monkeypatch, "--adapter", "../one").exit_code == 2
    assert _run(root, monkeypatch, "--adapter", "nowhere").exit_code == 2
    done = _run(root, monkeypatch, "--adapter", "one")
    assert done.exit_code == 1 and "ONE — " in done.stdout


def test_validate_reports_a_shape_the_schema_refuses_and_passes_silence(tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        {
            "one": "schema_version: 1\nrequirements:\n  outside:\n    grade: maybe\n"
            "    harness_versions: unbounded\n    evidence: e\n",
            "two": "schema_version: 1\nrequirements: {}\n",
            "three": None,
        },
    )
    issues = schemas_validate._check_adapter_support_declarations(root)
    assert [i.location for i in issues] == [
        ".pkit/adapters/one/harness-support.yaml/requirements/outside/grade"
    ]


def test_validate_refuses_an_answer_that_drops_its_version_bound(tmp_path: Path) -> None:
    """Required, so an edit that drops `[]` never widens an answer to every version."""
    root = _project(
        tmp_path,
        {
            "one": "schema_version: 1\nrequirements:\n  outside:\n"
            "    grade: supported\n    evidence: e\n"
        },
    )
    issues = schemas_validate._check_adapter_support_declarations(root)
    assert [i.location for i in issues] == [
        ".pkit/adapters/one/harness-support.yaml/requirements/outside"
    ]
    assert "harness_versions" in issues[0].message


def test_validate_warns_on_an_answer_to_a_requirement_the_core_does_not_declare(
    tmp_path: Path,
) -> None:
    root = _project(
        tmp_path,
        {
            "one": ANSWERED + "  invented:\n    grade: supported\n    harness_versions: unbounded\n"
            "    evidence: e\n"
        },
    )
    assert schemas_validate._check_adapter_support_declarations(root) == []
    [warning] = schemas_validate.adapter_support_warnings(root)
    assert warning.location == ".pkit/adapters/one/harness-support.yaml/requirements/invented"
    assert warning.severity is Severity.WARNING
    assert "retired, or newer than this backbone" in warning.message
