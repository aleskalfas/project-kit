"""The use-case point and the use cases an issue body cites (project-management DEC-054, #889).

project-management defines `pkit::work-tracking:use-cases` — `single`, no
default, inert `fallback` — and reads it through `pkit connections resolve`:
a body's `## Use cases` section is checked against the point, and a cited use
case the point does not hold is a warning. Whatever keeps the use cases fills
the point; here a test capability of the test's own, or the project's filler
file, stands in for it.

Three layers:

- the pieces — the package declaration, the companion schema, the matcher
  derived from its id pattern, the section a citation is read from, the state
  each resolve document puts the point in, and the rule over each state;
- the point end to end, read through the real `pkit connections resolve` in an
  adopter repository: off (`undefined`, `unfilled`), could not check (a
  default branch the clone cannot read; no document, or one this reading
  does not know), partly checked, empty, has entries;
- the rule on the three verbs that apply it — `validate-issue`, `edit-issue`
  and `create-issue --body-file` — with `gh` mocked: a report that never
  changes a verb's exit, at the severity the body-format schema gives the
  rule, and no resolution for a body that cites nothing or is no Feature's
  or Task's.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS_DIR = CAPABILITY_ROOT / "scripts"

POINT = "pkit::work-tracking:use-cases"
PM = "project-management"
KEEPER = "keeper"
FILLER_FILE = "docs/pkit/fillers/pkit/work-tracking/use-cases.yaml"
SHA = "1a2b3c4d5e6f" + "0" * 28

_yaml: Any = YAML(typ="safe")

#: The shipped body-format schema, and the labels the rule reports under: a cited
#: use case the point does not hold, and the notice that citations were not checked.
BODY_FORMAT: Any = _yaml.load(
    (CAPABILITY_ROOT / "schemas" / "body-format.yaml").read_text(encoding="utf-8")
)
RULE = "body.use-case-citation"
UNCHECKED = "body.use-cases-unchecked"


def _load(module_name: str, path: Path) -> ModuleType:
    inserted = str(SCRIPTS_DIR) not in sys.path
    if inserted:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and str(SCRIPTS_DIR) in sys.path:
            sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def vi() -> ModuleType:
    return _load("pm_validate_issue_for_use_cases", SCRIPTS_DIR / "validate-issue.py")


@pytest.fixture(scope="module")
def ei() -> ModuleType:
    return _load("pm_edit_issue_for_use_cases", SCRIPTS_DIR / "edit-issue.py")


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return _load("pm_create_issue_for_use_cases", SCRIPTS_DIR / "create-issue.py")


@pytest.fixture(scope="module")
def uc(vi: ModuleType, ei: ModuleType, ci: ModuleType) -> ModuleType:
    """The module the three verbs read the point through — one module, so a test
    that replaces its reading replaces it for every verb."""
    module: ModuleType = vi.use_case_citations
    assert ei.use_case_citations is module and ci.use_case_citations is module
    return module


# --- resolve documents ----------------------------------------------------------------

ACTIVE = {
    "id": "UC-001",
    "title": "Run a suite",
    "status": "active",
    "path": "docs/analysis/UC-001-run-a-suite.md",
}
WITHDRAWN = {"id": "UC-002", "title": "An old flow", "status": "withdrawn"}

#: A keeper's command filler that read the default branch at a commit, and answered.
SETTLED_FILLER = {
    "source": "contribution",
    "name": KEEPER,
    "supplies": "command 'fill'",
    "state": "taken",
    "reason": "",
    "query_contract": True,
    "reads": [{"state": "settled", "ref": "origin/main", "commit": SHA}],
}


def _document(
    outcome: str,
    *,
    value: Any = None,
    fillers: tuple[Mapping[str, Any], ...] = (),
    origin: str = "",
    why: str = "",
) -> dict[str, Any]:
    """A `pkit connections resolve --json` document for the point."""
    return {
        "schema_version": 1,
        "address": POINT,
        "defined": outcome != "undefined",
        "from": "resolution",
        "provider": PM,
        "policy": "single",
        "inert_policy": "fallback",
        "participation": None,
        "resolved": outcome == "resolved",
        "outcome": outcome,
        "why": why,
        "value": value,
        "origin": origin,
        "entries": [],
        "removals": [],
        "fillers": list(fillers),
    }


HAS_ENTRIES = _document(
    "resolved", value=[ACTIVE, WITHDRAWN], fillers=(SETTLED_FILLER,), origin=KEEPER
)


def _body(*lines: str, outside: str = "") -> str:
    """A Task body whose `## Use cases` section lists `lines`; none — no section."""
    body = (
        "Feature: #10\n\n## What\n\nThe work.\n\n## Acceptance criteria\n\n- [ ] done\n\n"
        f"## Doc impact\n\nNo doc impact — internal.{outside}\n"
    )
    if lines:
        body += "\n## Use cases\n\n" + "".join(f"- {line}\n" for line in lines)
    return body


# --- the pieces ---------------------------------------------------------------------------


def test_the_package_accepts_the_point_as_the_record_describes_it() -> None:
    package = _yaml.load((CAPABILITY_ROOT / "package.yaml").read_text("utf-8"))
    point = package["connections"]["extension-points"]["accepts"][POINT]
    assert point == {
        "schema_version": 1,
        "schema": "use-cases.schema.json",
        "description": point["description"],
        "combination": "single",
        "inert": "fallback",
    }  # no default: this capability holds no use cases of its own
    for promise in ("withdrawn ones", "names the same use case for good", "complete or none"):
        assert promise in " ".join(point["description"].split())
    assert "reads settled state" in point["description"]
    assert (CAPABILITY_ROOT / "schemas" / point["schema"]).is_file()


def _schema() -> Draft202012Validator:
    schema = json.loads((CAPABILITY_ROOT / "schemas" / "use-cases.schema.json").read_text("utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_the_companion_schema_holds_id_title_status_and_an_optional_path() -> None:
    schema = _schema()
    assert schema.is_valid([ACTIVE, WITHDRAWN])
    assert schema.is_valid([{**ACTIVE, "id": "UC-1000"}])
    assert schema.is_valid([])
    for broken in (
        {**ACTIVE, "id": "UC-12"},
        {**ACTIVE, "id": "uc-001"},
        {**ACTIVE, "id": "JRN-001"},
        {**ACTIVE, "status": "draft"},
        {**ACTIVE, "title": ""},
        {**ACTIVE, "path": ""},
        {k: v for k, v in ACTIVE.items() if k != "title"},
        {k: v for k, v in ACTIVE.items() if k != "status"},
        {**ACTIVE, "actor": "ACT-tester"},
    ):
        assert not schema.is_valid([broken]), broken


@pytest.mark.parametrize(
    ("text", "ids"),
    [
        ("UC-001", ["UC-001"]),
        ("UC-1000 and UC-014", ["UC-1000", "UC-014"]),
        ("`UC-003` — export (UC-003)", ["UC-003"]),
        ("UC-12", []),
        ("UC-NNN", []),
        ("JRN-001", []),
        ("XUC-001", []),
        ("UC-001a", []),
        ("uc-001", []),
    ],
)
def test_a_citation_is_an_id_the_point_s_pattern_matches(
    uc: ModuleType, text: str, ids: list[str]
) -> None:
    assert uc.cited(_body(text)) == ids


def test_the_matcher_follows_the_point_s_id_pattern(
    uc: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The matcher is derived from the companion schema, so a different pattern
    there is a different matcher here — the two never disagree."""
    schema = json.loads(uc.SCHEMA.read_text(encoding="utf-8"))
    schema["$defs"]["use-case"]["properties"]["id"]["pattern"] = "^REQ-[0-9]{2}$"
    other = tmp_path / "use-cases.schema.json"
    other.write_text(json.dumps(schema), encoding="utf-8")
    monkeypatch.setattr(uc, "SCHEMA", other)
    uc.citation.cache_clear()
    try:
        assert uc.cited(_body("REQ-07 and UC-001")) == ["REQ-07"]
    finally:
        uc.citation.cache_clear()


def test_citations_are_read_from_the_use_cases_section_only(uc: ModuleType) -> None:
    body = _body("UC-001 — Run a suite", "UC-001 again", outside=" Unlike UC-099.")
    assert uc.cited(body) == ["UC-001"]
    assert uc.cited(_body(outside=" Serves UC-099.")) == []
    assert uc.section(_body()) is None


def test_the_section_ends_at_the_next_heading_and_before_the_footer(uc: ModuleType) -> None:
    body = (
        "Feature: #10\n\n## use cases\n\n- UC-001\n\n```sh\n# UC-002 in a fence\n```\n\n"
        "### By area\n\n- UC-003\n\n## Related\n\n- UC-004\n\n## Use cases\n\n- UC-005\n"
        "\n<!-- pkit-provenance:start -->\nfiled with UC-006\n<!-- pkit-provenance:end -->\n"
    )
    assert uc.cited(body) == ["UC-001", "UC-002", "UC-003", "UC-005"]


@pytest.mark.parametrize(
    ("document", "state"),
    [
        (_document("undefined"), "Off"),
        (_document("unfilled"), "Off"),
        (_document("no-answer", why="no filler answered"), "NotChecked"),
        (_document("inert-fail"), "NotChecked"),
        (_document("collision"), "NotChecked"),
        (_document("selection-needed"), "NotChecked"),
        (_document("selection-unmatched"), "NotChecked"),
        (_document("definer-defect"), "NotChecked"),
        (_document("a-later-ending"), "NotChecked"),
        ({k: v for k, v in HAS_ENTRIES.items() if k != "outcome"}, "NotChecked"),
        ({**HAS_ENTRIES, "schema_version": 2}, "NotChecked"),
        ({**HAS_ENTRIES, "value": {"UC-001": "x"}}, "NotChecked"),
        (HAS_ENTRIES, "Held"),
        (_document("resolved", value=[], fillers=(SETTLED_FILLER,), origin=KEEPER), "Held"),
    ],
)
def test_the_state_comes_from_the_outcome_and_the_fillers_state(
    uc: ModuleType, document: dict[str, Any], state: str
) -> None:
    assert type(uc.reading_of(document)).__name__ == state


def test_the_state_never_comes_from_why(uc: ModuleType) -> None:
    """A sentence that reads like another ending changes nothing: `why` is for people."""
    assert uc.reading_of({**HAS_ENTRIES, "why": "unfilled: no filler is declared"}) == (
        uc.reading_of(HAS_ENTRIES)
    )
    assert isinstance(uc.reading_of(_document("unfilled", why="resolved")), uc.Off)


def test_a_resolved_point_with_an_inert_filler_is_partly_checked(uc: ModuleType) -> None:
    inert = {
        "source": "project filler",
        "name": FILLER_FILE,
        "supplies": "file",
        "state": "inert",
        "reason": "its value does not fit the point",
    }
    reading = uc.reading_of(
        _document("resolved", value=[ACTIVE], fillers=(inert, SETTLED_FILLER), origin=KEEPER)
    )
    assert reading == uc.Held(
        ids=frozenset({"UC-001"}),
        source=f"settled on the default branch (read at origin/main {SHA[:12]})",
        fetch=True,
        missing=(f"{FILLER_FILE} (its value does not fit the point)",),
    )


def test_what_the_set_was_read_against(uc: ModuleType) -> None:
    project = {
        "source": "project filler",
        "name": FILLER_FILE,
        "supplies": "file",
        "state": "taken",
        "reason": "",
        "reads": [],
    }
    held = uc.reading_of(
        _document("resolved", value=[ACTIVE], fillers=(project,), origin="project filler")
    )
    assert (held.source, held.fetch) == (f"in the project's filler file {FILLER_FILE}", False)
    unborn = {**SETTLED_FILLER, "reads": [{"state": "settled", "ref": "main", "commit": None}]}
    held = uc.reading_of(_document("resolved", value=[], fillers=(unborn,), origin=KEEPER))
    assert (held.source, held.fetch) == (
        "settled on the default branch (main, which has no commit yet)",
        False,
    )
    working_tree = {**SETTLED_FILLER, "reads": []}
    held = uc.reading_of(_document("resolved", value=[], fillers=(working_tree,), origin=KEEPER))
    assert (held.source, held.fetch) == (f"that {KEEPER} gave", False)


def _answering(document: Any, code: int = 0, stderr: str = "") -> Callable[..., Any]:
    def run(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        assert argv == ["pkit", "connections", "resolve", POINT, "--json"]
        stdout = document if isinstance(document, str) else json.dumps(document)
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    return run


def test_reading_the_point_takes_the_document_whatever_the_exit_code(uc: ModuleType) -> None:
    assert isinstance(uc.read_point(_answering(_document("unfilled"), code=1)), uc.Off)
    held = uc.read_point(_answering(HAS_ENTRIES))
    assert held.ids == frozenset({"UC-001", "UC-002"})
    old = uc.read_point(_answering("", code=2, stderr="Error: No such command 'connections'.\n"))
    assert old == uc.NotChecked(
        f"`pkit connections resolve {POINT} --json` exited 2 without its document: "
        "Error: No such command 'connections'."
    )

    def absent(argv: list[str], **_kw: Any) -> Any:
        raise FileNotFoundError(argv[0])

    assert uc.read_point(absent) == uc.NotChecked("`pkit` is not on PATH")

    def slow(argv: list[str], **kw: Any) -> Any:
        raise subprocess.TimeoutExpired(argv, kw["timeout"])

    assert isinstance(uc.read_point(slow), uc.NotChecked)


def _raising(error: Callable[[list[str], Mapping[str, Any]], Exception]) -> Callable[..., Any]:
    def run(argv: list[str], **kw: Any) -> Any:
        raise error(argv, kw)

    return run


@pytest.mark.parametrize(
    "run",
    [
        pytest.param(_answering("", code=1), id="no-document"),
        pytest.param(_answering("Traceback (most recent call last):", code=1), id="no-json"),
        pytest.param(_answering("[]"), id="no-mapping"),
        pytest.param(_raising(lambda argv, _kw: FileNotFoundError(argv[0])), id="no-pkit"),
        pytest.param(
            _raising(lambda argv, kw: subprocess.TimeoutExpired(argv, kw["timeout"])),
            id="timed-out",
        ),
        pytest.param(
            _answering({**_document("unfilled"), "schema_version": 2}, code=1),
            id="unknown-version",
        ),
        pytest.param(
            _answering({"address": POINT, "defined": True, "resolved": False, "fillers": []}),
            id="predates-outcome",
        ),
    ],
)
def test_no_document_or_one_it_does_not_know_is_could_not_check_never_off(
    uc: ModuleType, run: Callable[..., Any]
) -> None:
    """The rule goes quiet only on a document that says `undefined` or `unfilled`:
    anything less is one notice that the citations were not checked."""
    reading = uc.read_point(run)
    assert isinstance(reading, uc.NotChecked) and reading.why
    [(severity, label, _detail)] = uc.findings(
        _body("UC-042"), "task", BODY_FORMAT, lambda: reading
    )
    assert (severity, label) == ("warning", UNCHECKED)


def _reader(uc: ModuleType, document: Mapping[str, Any]) -> Callable[[], Any]:
    return lambda: uc.reading_of(document)


def _never() -> Any:
    raise AssertionError("the point was read for a body the rule does not read")


def test_a_body_citing_nothing_resolves_nothing(uc: ModuleType) -> None:
    assert uc.findings(_body(), "task", BODY_FORMAT, _never) == []
    assert uc.findings(_body(outside=" See UC-001."), "task", BODY_FORMAT, _never) == []
    assert uc.findings(_body("UC-042"), "task", BODY_FORMAT, _reader(uc, HAS_ENTRIES)) != []
    assert uc.findings(_body("UC-042"), "task", BODY_FORMAT, None) == []


@pytest.mark.parametrize("issue_type", ["epic", "umbrella", "milestone", None])
def test_a_body_of_another_type_is_not_read(uc: ModuleType, issue_type: str | None) -> None:
    """On an EPIC, Umbrella or Milestone body a `## Use cases` heading is ordinary
    content: nothing is read, checked or reported."""
    assert uc.findings(_body("UC-042"), issue_type, BODY_FORMAT, _never) == []


@pytest.mark.parametrize("issue_type", ["feature", "task"])
def test_a_feature_or_task_body_is_read(uc: ModuleType, issue_type: str) -> None:
    [(severity, label, _detail)] = uc.findings(
        _body("UC-042"), issue_type, BODY_FORMAT, _reader(uc, HAS_ENTRIES)
    )
    assert (severity, label) == ("warning", RULE)


# --- the rule as the schema carries it --------------------------------------------------------


def test_the_schema_carries_the_rule_under_its_id_at_the_record_s_severity(
    uc: ModuleType,
) -> None:
    [rule] = [r for r in BODY_FORMAT["universal_body_rules"] if r.get("id") == uc.LABEL]
    assert uc.LABEL == RULE and uc.UNCHECKED == UNCHECKED
    assert rule["severity"] == "[validation-severity:warning]"
    assert "existence only" in " ".join(rule["rule"].split())
    assert uc.rule_of(BODY_FORMAT) == uc.Rule("warning", frozenset({"feature", "task"}))
    for kind in ("feature", "task"):
        assert "## Use cases" in BODY_FORMAT["bodies"][kind]["optional_section_recommendations"]
    for kind in ("epic", "umbrella"):
        assert "## Use cases" not in BODY_FORMAT["bodies"][kind].get(
            "optional_section_recommendations", []
        )


def _with_rule(**changes: Any) -> dict[str, Any]:
    """The body-format schema with the use-case rule's entry changed."""
    rules = [
        {**r, **changes} if r.get("id") == RULE else r for r in BODY_FORMAT["universal_body_rules"]
    ]
    return {**BODY_FORMAT, "universal_body_rules": rules}


def test_the_severity_is_the_rule_s_token_in_the_schema(uc: ModuleType) -> None:
    """Never a constant of the script's: another token there is another severity here,
    for the finding and for the notice alike."""
    raised = _with_rule(severity="[validation-severity:bypassable-with-audit]")
    [(severity, _label, _detail)] = uc.findings(
        _body("UC-042"), "task", raised, _reader(uc, HAS_ENTRIES)
    )
    assert severity == "bypassable-with-audit"
    [(severity, label, _detail)] = uc.findings(
        _body("UC-042"), "task", raised, _reader(uc, _document("no-answer"))
    )
    assert (severity, label) == ("bypassable-with-audit", UNCHECKED)


def test_a_schema_without_the_rule_applies_none(uc: ModuleType) -> None:
    without = {
        **BODY_FORMAT,
        "universal_body_rules": [
            r for r in BODY_FORMAT["universal_body_rules"] if r.get("id") != RULE
        ],
    }
    assert uc.rule_of(without) is None
    assert uc.rule_of(_with_rule(severity="loud")) is None
    assert uc.findings(_body("UC-042"), "task", without, _never) == []


def test_no_template_carries_the_section() -> None:
    for template in sorted((CAPABILITY_ROOT / "templates").rglob("*")):
        if template.is_file():
            assert "use cases" not in template.read_text(encoding="utf-8").lower(), template


#: The capability that keeps the use cases in this repository, however it is spelt.
KEEPER_SPELLINGS = ("software-analysis", "software_analysis", "software analysis")


def test_nothing_the_capability_ships_names_a_keeper() -> None:
    """project-management reads the point and knows no keeper (DEC-054 point 2): no
    file it ships — code, schema, record, skill, agent, storyboard, README — names
    the capability that fills the point here. `project/` is this repository's own
    configuration of the capability, not what it ships."""
    for path in sorted(CAPABILITY_ROOT.rglob("*")):
        inside = path.relative_to(CAPABILITY_ROOT).parts
        if not path.is_file() or "__pycache__" in inside or inside[0] == "project":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for name in KEEPER_SPELLINGS:
            assert name not in text, f"{path.relative_to(REPO_ROOT)} names {name!r}"


# --- the rule over each state ----------------------------------------------------------------


def _judged(uc: ModuleType, body: str, document: Mapping[str, Any]) -> list[Any]:
    return uc.judge(uc.cited(body), uc.reading_of(document), "warning")


def test_a_known_or_withdrawn_citation_passes(uc: ModuleType) -> None:
    assert _judged(uc, _body("UC-001", "UC-002"), HAS_ENTRIES) == []


def test_an_unknown_citation_is_a_warning_naming_the_commit_read(uc: ModuleType) -> None:
    assert _judged(uc, _body("UC-001", "UC-042", "UC-043"), HAS_ENTRIES) == [
        (
            "warning",
            RULE,
            "cites UC-042 and UC-043, not among the use cases settled on the default branch "
            f"(read at origin/main {SHA[:12]}). The check is of existence only. If the use "
            "case has landed since, fetch the default branch and validate again.",
        )
    ]


def test_an_empty_set_holds_no_citation(uc: ModuleType) -> None:
    empty = _document("resolved", value=[], fillers=(SETTLED_FILLER,), origin=KEEPER)
    [(_severity, label, detail)] = _judged(uc, _body("UC-001"), empty)
    assert label == RULE
    assert detail.startswith("cites UC-001, not among the use cases settled")


def test_could_not_check_is_one_notice_and_no_unknown_citation(uc: ModuleType) -> None:
    inert = {
        **SETTLED_FILLER,
        "state": "inert",
        "reason": "its command 'fill' reads the default branch, and it resolves to no commit",
        "reads": [{"state": "settled", "ref": None, "commit": None}],
    }
    unread = _document("no-answer", fillers=(inert,), why="no filler answered")
    assert _judged(uc, _body("UC-001", "UC-042"), unread) == [
        (
            "warning",
            UNCHECKED,
            "use-case citations not checked (UC-001 and UC-042): the use cases could not be "
            f"read — no filler answered; {KEEPER} (its command 'fill' reads the default "
            "branch, and it resolves to no commit). None is reported as unknown on that "
            "ground.",
        )
    ]
    [(_severity, label, detail)] = _judged(
        uc, _body("UC-001"), _document("a-later-ending", why="w")
    )
    assert label == UNCHECKED
    assert "'a-later-ending', which this reading does not know" in detail


def test_partly_checked_names_what_it_lacks_in_one_notice(uc: ModuleType) -> None:
    inert = {**SETTLED_FILLER, "name": "other", "state": "inert", "reason": "it exited 1"}
    partly = _document("resolved", value=[ACTIVE], fillers=(inert, SETTLED_FILLER), origin=KEEPER)
    assert _judged(uc, _body("UC-001"), partly) == []
    assert _judged(uc, _body("UC-001", "UC-042", "UC-043"), partly) == [
        (
            "warning",
            UNCHECKED,
            "UC-042 and UC-043 not checked: the use-case point answered without other (it "
            "exited 1), so the set it holds may be incomplete.",
        )
    ]


def test_an_off_point_says_nothing(uc: ModuleType) -> None:
    for outcome in ("undefined", "unfilled"):
        assert _judged(uc, _body("UC-042"), _document(outcome)) == []


# --- the point end to end, through the real backbone -------------------------------------------


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path) -> AdopterRepo:
    """An adopter with project-management installed, its point read through a `pkit`
    that is the real CLI."""
    return make_adopter_repo(capabilities=(PM,))


def _keeper(repo: AdopterRepo, body: str) -> None:
    """A capability of the test's own filling the point through a command that reads
    settled state and runs `body` — standing in for whatever keeps the use cases."""
    root = repo.pkit / "capabilities" / KEEPER
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    script = root / "scripts" / "fill.py"
    script.write_text(f"#!{sys.executable}\nimport json, sys\n{body}", encoding="utf-8")
    script.chmod(0o755)
    package = {
        "schema_version": 2,
        "component": {"kind": "capability", "name": KEEPER, "version": "0.1.0"},
        "description": "Keeps use cases, for the test.",
        "requires_backbone": ">=0.0.0",
        "commands": {
            "fill": {
                "script": "scripts/fill.py",
                "help": "Print the use cases.",
                "query-contract": True,
                "reads": ["settled"],
            }
        },
        "connections": {
            "extensions": {
                "contributes": [{"point": POINT, "schema_version": 1, "command": "fill"}]
            }
        },
    }
    (root / "package.yaml").write_text(json.dumps(package, indent=2), encoding="utf-8")
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    if not any(e.name == KEEPER for e in backbone.components):
        backbone.components.append(
            ComponentRegistryEntry(
                kind="capability",
                name=KEEPER,
                manifest=f".pkit/capabilities/{KEEPER}/project/manifest.yaml",
                origin="incubated-in-repo",
            )
        )
        write_backbone_manifest(repo.root, backbone)


def _printing(*entries: Mapping[str, Any]) -> str:
    return f"print(json.dumps({{'schema_version': 1, 'value': {list(entries)!r}}}))\n"


def _filler_file(repo: AdopterRepo, value: Any) -> None:
    repo.write({FILLER_FILE: json.dumps({"schema_version": 1, "value": value}) + "\n"})


def test_off_when_nothing_defines_the_point(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, uc: ModuleType
) -> None:
    make_adopter_repo()
    assert isinstance(uc.read_point(), uc.Off)


def test_off_when_nothing_fills_the_point(project: AdopterRepo, uc: ModuleType) -> None:
    assert isinstance(uc.read_point(), uc.Off)


def test_has_entries_read_at_the_default_branch_s_commit(
    project: AdopterRepo, uc: ModuleType
) -> None:
    _keeper(project, _printing(ACTIVE, WITHDRAWN))
    head = project.commit("initial")
    assert uc.read_point() == uc.Held(
        ids=frozenset({"UC-001", "UC-002"}),
        source=f"settled on the default branch (read at main {head[:12]})",
        fetch=True,
    )


def test_empty_is_a_set_that_holds_nothing(project: AdopterRepo, uc: ModuleType) -> None:
    _keeper(project, _printing())
    project.commit("initial")
    reading = uc.read_point()
    assert isinstance(reading, uc.Held) and reading.ids == frozenset() and not reading.missing


def test_could_not_check_when_the_default_branch_cannot_be_read(
    project: AdopterRepo, uc: ModuleType
) -> None:
    """A remote holds the default branch and this clone has not fetched it: the
    backbone does not start the keeper's filler, and the point has no answer."""
    _keeper(project, _printing(ACTIVE))
    project.commit("initial")
    project.git("remote", "add", "origin", "https://example.invalid/project.git")
    reading = uc.read_point()
    assert isinstance(reading, uc.NotChecked)
    assert reading.why.startswith(f"no filler answered; {KEEPER} (its command 'fill' reads")
    assert "git fetch origin main" in reading.why
    [(_severity, label, _detail)] = uc.judge(["UC-001"], reading, "warning")
    assert label == UNCHECKED


def test_partly_checked_when_a_filler_meant_to_answer_did_not(
    project: AdopterRepo, uc: ModuleType
) -> None:
    """The project's filler file is asked first and cannot answer; the keeper answers."""
    _keeper(project, _printing(ACTIVE))
    _filler_file(project, [{**ACTIVE, "status": "draft"}])
    project.commit("initial")
    reading = uc.read_point()
    assert isinstance(reading, uc.Held) and reading.ids == frozenset({"UC-001"})
    (missing,) = reading.missing
    assert missing.startswith(f"{FILLER_FILE} (")


def test_the_project_s_filler_file_replaces_the_keeper_s_answer_whole(
    project: AdopterRepo, uc: ModuleType
) -> None:
    _keeper(project, _printing(ACTIVE, WITHDRAWN))
    _filler_file(project, [{"id": "UC-007", "title": "Ours", "status": "active"}])
    project.commit("initial")
    assert uc.read_point() == uc.Held(
        ids=frozenset({"UC-007"}), source=f"in the project's filler file {FILLER_FILE}"
    )


# --- the rule on the three verbs ------------------------------------------------------------

TITLES = {
    "task": "[Task] Do a thing with a long enough title",
    "epic": "[EPIC] Hold a thesis with a long enough title",
}
EPIC_BODY = (
    "Milestone: v1\n\n## Outcome\n\nThe thesis.\n\n## Success criteria\n\n- [ ] proven\n\n"
    "## Use cases\n\n- UC-042\n"
)


class _Resolver:
    """Stands in for `pkit connections resolve`: answers `document`, counts the asking."""

    def __init__(self, uc: ModuleType, document: Mapping[str, Any]) -> None:
        self.uc, self.document, self.calls = uc, document, 0

    def __call__(self) -> Any:
        self.calls += 1
        return self.uc.reading_of(self.document)


def _allow(*_args: object, **_kwargs: object) -> bool:
    return True


def _staged(root: Path) -> Path:
    """project-management's schemas and templates under `root`, bootstrapped and
    configured; returns the capability root."""
    capability_root = root / ".pkit" / "capabilities" / PM
    for folder in ("schemas", "templates"):
        shutil.copytree(CAPABILITY_ROOT / folder, capability_root / folder)
    (capability_root / "project").mkdir(parents=True)
    (capability_root / "project" / "config.yaml").write_text(
        "schema_version: 1\nworkstreams: [core]\n", encoding="utf-8"
    )
    (capability_root / "project" / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\nbootstrap:\n  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.0.0-test\n  by: bootstrap\n  repo:\n",
        encoding="utf-8",
    )
    return capability_root


Verb = Callable[..., tuple[int, str]]


@pytest.fixture
def verbs(
    vi: ModuleType,
    ei: ModuleType,
    ci: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> dict[str, Verb]:
    """Each verb run on a body of an issue of `kind` (a Task unless named), `gh`
    mocked: `(exit code, what it printed)`."""
    capability_root = _staged(tmp_path)
    monkeypatch.setenv("PM_INVOKER_LOGIN", "someone")
    for module in (vi, ei, ci):
        monkeypatch.setattr(module.bootstrap_gate, "enforce", _allow)
    monkeypatch.setattr(ei.session_guard, "enforce", _allow)
    monkeypatch.setattr(ci.session_guard, "enforce", _allow)
    root = ["--capability-root", str(capability_root)]

    def run(module: ModuleType, argv: list[str]) -> tuple[int, str]:
        monkeypatch.setattr(sys, "argv", argv)
        code = module.main()
        out = capsys.readouterr()
        return code, out.out + out.err

    def validate(body: str, kind: str = "task") -> tuple[int, str]:
        issue = {"number": 7, "title": TITLES[kind], "body": body, "labels": []}
        monkeypatch.setattr(vi, "_gh_get_issue", lambda *_a: issue)
        return run(vi, ["validate-issue", "7", *root])

    def edit(body: str, kind: str = "task") -> tuple[int, str]:
        issue = {"number": 7, "title": TITLES[kind], "body": "", "labels": []}
        monkeypatch.setattr(ei, "_gh_get_issue", lambda *_a: issue)
        body_file = tmp_path / "edit.md"
        body_file.write_text(body, encoding="utf-8")
        return run(ei, ["edit-issue", "7", *root, "--body-file", str(body_file), "--dry-run"])

    def create(body: str, kind: str = "task") -> tuple[int, str]:
        def gh(cmd: list[str], *_a: Any, **_kw: Any) -> Any:
            stdout = json.dumps({"title": "[Feature] A capability"}) if "view" in cmd else ""
            return subprocess.CompletedProcess(cmd, 0, stdout, "")

        monkeypatch.setattr(ci.subprocess, "run", gh)
        body_file = tmp_path / "create.md"
        body_file.write_text(body, encoding="utf-8")
        argv = ["create-issue", "--type", kind, "--title", TITLES[kind].split("] ", 1)[1]]
        argv += ["--workstream", "core", "--body-file", str(body_file)]
        argv += ["--parent", "10"] if kind == "task" else []
        return run(ci, [*argv, *root, "--dry-run"])

    return {"validate-issue": validate, "edit-issue": edit, "create-issue": create}


VERBS = ("validate-issue", "edit-issue", "create-issue")


@pytest.mark.parametrize("verb", VERBS)
def test_a_known_or_withdrawn_citation_passes_silently(
    verbs: dict[str, Verb], uc: ModuleType, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    resolver = _Resolver(uc, HAS_ENTRIES)
    monkeypatch.setattr(uc, "read_point", resolver)
    _code, out = verbs[verb](_body("UC-001 — Run a suite", "UC-002"))
    assert resolver.calls == 1
    assert "use-case" not in out


@pytest.mark.parametrize("verb", VERBS)
def test_an_unknown_citation_warns_and_leaves_the_exit_alone(
    verbs: dict[str, Verb], uc: ModuleType, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    monkeypatch.setattr(uc, "read_point", _Resolver(uc, HAS_ENTRIES))
    clean, _ = verbs[verb](_body("UC-001"))
    code, out = verbs[verb](_body("UC-001", "UC-042"))
    assert code == clean
    assert "[warning]" in out and f"{RULE}: cites UC-042, not among" in out
    assert f"read at origin/main {SHA[:12]}" in out and "fetch the default branch" in out


@pytest.mark.parametrize("verb", VERBS)
def test_could_not_check_is_a_notice_with_no_unknown_citation(
    verbs: dict[str, Verb], uc: ModuleType, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    unread = _document("no-answer", why="no filler answered")
    monkeypatch.setattr(uc, "read_point", _Resolver(uc, unread))
    clean, _ = verbs[verb](_body())
    code, out = verbs[verb](_body("UC-042"))
    assert code == clean
    assert "[warning]" in out
    assert f"{UNCHECKED}: use-case citations not checked (UC-042)" in out
    assert RULE not in out


@pytest.mark.parametrize("verb", VERBS)
def test_partly_checked_names_the_ids_not_checked(
    verbs: dict[str, Verb], uc: ModuleType, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    inert = {**SETTLED_FILLER, "name": "other", "state": "inert", "reason": "it exited 1"}
    partly = _document("resolved", value=[ACTIVE], fillers=(inert, SETTLED_FILLER), origin=KEEPER)
    monkeypatch.setattr(uc, "read_point", _Resolver(uc, partly))
    clean, _ = verbs[verb](_body("UC-001"))
    code, out = verbs[verb](_body("UC-001", "UC-042"))
    assert code == clean
    assert "[warning]" in out
    assert f"{UNCHECKED}: UC-042 not checked: the use-case point answered" in out
    assert RULE not in out


@pytest.mark.parametrize("verb", VERBS)
def test_an_off_point_mentions_no_use_case(
    verbs: dict[str, Verb], uc: ModuleType, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    monkeypatch.setattr(uc, "read_point", _Resolver(uc, _document("unfilled")))
    clean, _ = verbs[verb](_body())
    code, out = verbs[verb](_body("UC-042"))
    assert code == clean and "use-case" not in out


@pytest.mark.parametrize("verb", VERBS)
def test_a_body_without_a_use_cases_section_resolves_nothing(
    verbs: dict[str, Verb], uc: ModuleType, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    """An id outside the section is no citation, so nothing is resolved either."""
    resolver = _Resolver(uc, HAS_ENTRIES)
    monkeypatch.setattr(uc, "read_point", resolver)
    _code, out = verbs[verb](_body(outside=" Related: UC-042."))
    assert resolver.calls == 0
    assert "use-case" not in out


@pytest.mark.parametrize("verb", VERBS)
def test_an_epic_body_is_not_read(
    verbs: dict[str, Verb], uc: ModuleType, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    """A `## Use cases` heading on an EPIC body is ordinary content: the verb ends as
    it does without it, resolves nothing and reports nothing about use cases."""
    resolver = _Resolver(uc, HAS_ENTRIES)
    monkeypatch.setattr(uc, "read_point", resolver)
    clean, _ = verbs[verb](EPIC_BODY.split("## Use cases")[0], "epic")
    code, out = verbs[verb](EPIC_BODY, "epic")
    assert code == clean
    assert resolver.calls == 0
    assert "use-case" not in out


def test_validate_issue_json_carries_the_notice_among_the_findings(
    vi: ModuleType,
    uc: ModuleType,
    verbs: dict[str, Verb],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """One channel: the notice that citations were not checked is a warning-level
    finding under its own label, and the document has no other place for it."""
    monkeypatch.setattr(uc, "read_point", _Resolver(uc, _document("collision", why="w")))
    issue = {"number": 7, "title": TITLES["task"], "body": _body("UC-042"), "labels": []}
    monkeypatch.setattr(vi, "_gh_get_issue", lambda *_a: issue)
    capability_root = tmp_path / ".pkit" / "capabilities" / PM
    monkeypatch.setattr(
        sys, "argv", ["validate-issue", "7", "--capability-root", str(capability_root), "--json"]
    )
    vi.main()
    document = json.loads(capsys.readouterr().out)
    assert sorted(document) == ["findings", "issue_number", "issue_title"]
    assert [f for f in document["findings"] if "use-case" in f["label"]] == [
        {
            "severity": "warning",
            "label": UNCHECKED,
            "detail": "use-case citations not checked (UC-042): the use cases could not be "
            "read — w. None is reported as unknown on that ground.",
        }
    ]


def test_validate_issue_reads_the_point_through_the_real_backbone(
    project: AdopterRepo,
    vi: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """End to end: the project's filler file answers, and the verb reads it through
    the real `pkit connections resolve`."""
    _filler_file(project, [ACTIVE])
    capability_root = project.root / ".pkit" / "capabilities" / PM
    (capability_root / "project").mkdir(parents=True, exist_ok=True)
    (capability_root / "project" / "config.yaml").write_text(
        "schema_version: 1\nworkstreams: [core]\n", encoding="utf-8"
    )
    monkeypatch.setenv("PM_INVOKER_LOGIN", "someone")
    monkeypatch.setattr(vi.bootstrap_gate, "enforce", _allow)
    issue = {
        "number": 7,
        "title": TITLES["task"],
        "body": _body("UC-001", "UC-042"),
        "labels": [],
    }
    monkeypatch.setattr(vi, "_gh_get_issue", lambda *_a: issue)
    monkeypatch.setattr(
        sys, "argv", ["validate-issue", "7", "--capability-root", str(capability_root), "--json"]
    )
    vi.main()
    findings = json.loads(capsys.readouterr().out)["findings"]
    [finding] = [f for f in findings if f["label"] == "body.use-case-citation"]
    assert finding == {
        "severity": "warning",
        "label": "body.use-case-citation",
        "detail": f"cites UC-042, not among the use cases in the project's filler file "
        f"{FILLER_FILE}. The check is of existence only.",
    }
