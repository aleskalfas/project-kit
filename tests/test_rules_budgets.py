"""Each rules file a session loads stays within a word budget (COR-069; ADR-077, #2262).

A loaded set gives its loaded file's budget as `budget` in its front matter; a
project's plain `.pkit/rules/project.md` takes `rule-sets.plain-file-budget` from the
configuration. These tests hold:

- **the count** (`loaded_rule_sets.word_count`): runs of characters none of which has
  Unicode's White_Space property, named rather than left to Python's split;
- **the first budgets**: `OPS` and project-kit's own `project.md`, each within its
  budget in the methodology's source;
- **the check**: a file within its budget and past it, where its owner can correct it
  and where it is received; a component's set without a budget; an ordinary set with
  one; the key that bounds nothing;
- **the report**: a summary line for each rules file, in a project that receives `OPS`;
- **the generator**, which prints each file's count against its budget;
- **`pkit rule-sets altered`**, which lists a raise, a lowering, an addition and a
  removal of a budget.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import loaded_rule_sets as lr
from project_kit import rule_set_reading as reading
from project_kit import rule_sets as rs
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.test_loaded_rule_sets import accepted, loaded_text

REPO = Path(__file__).resolve().parents[1]
OPS_FILE = ".pkit/rule-sets/ops.md"
CORE_LOADED = ".pkit/rules/core.md"
PROJECT_LOADED = ".pkit/rules/project.md"
CONFIG = ".pkit/project/config.yaml"
OWN_SET = "docs/rule-sets/own.md"

Kind = rs.RuleSetFindingKind

# Characters a count must read by Unicode's White_Space property, by code point.
NBSP, IDEOGRAPHIC, LINE_SEPARATOR, THIN_SPACE, ZERO_WIDTH = (
    chr(code) for code in (0xA0, 0x3000, 0x2028, 0x2009, 0x200B)
)


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def findings(root: Path, kind: Kind) -> list[rs.RuleSetFinding]:
    return [f for f in rs.validate_rule_sets(root).findings if f.kind is kind]


def with_budget(text: str, budget: int | None) -> str:
    """A loaded set's file with its `budget` set to `budget`, or removed for None."""
    text = re.sub(r"^budget: .*\n", "", text, count=1, flags=re.M)
    if budget is None:
        return text
    return text.replace("loaded: true\n", f"loaded: true\nbudget: {budget}\n", 1)


def set_key(root: Path, budget: int | None) -> None:
    """The adopter's configuration with `rule-sets.plain-file-budget` set, or left out."""
    path = root / CONFIG
    written = path.read_text(encoding="utf-8") if path.is_file() else ""
    text = re.sub(r"(?m)^rule-sets:\n  plain-file-budget: .*\n", "", written)
    if budget is not None:
        text += f"\nrule-sets:\n  plain-file-budget: {budget}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def own_set(adopter: AdopterRepo, budget: int | None) -> str:
    """A project's own loaded set with one rule and `budget`, its loaded file generated
    from it; returns that file's text."""
    adopter.write({OWN_SET: with_budget(loaded_text("OWN", accepted("RS-OWN-001")), budget)})
    (own,) = [s for s in rs.discover_rule_sets(adopter.root).rule_sets if s.name == "OWN"]
    text = lr.project(own)
    adopter.write({PROJECT_LOADED: text})
    return text


def authored_tree(root: Path, ops: str) -> Path:
    """A tree where the backbone's set is authored, as in the methodology's source — the
    ownership predicate's own test — holding `ops` and the file it generates."""
    for marker in ("src/project_kit/__init__.py", ".pkit/lifecycle/ownership.py"):
        (root / marker).parent.mkdir(parents=True, exist_ok=True)
        (root / marker).write_bytes((REPO / marker).read_bytes())
    (root / OPS_FILE).parent.mkdir(parents=True)
    (root / OPS_FILE).write_text(ops, encoding="utf-8")
    lr.generate(root)
    return root


def budget_check(root: Path) -> lr.BudgetCheck:
    return lr.check_budgets(root, rs.discover_rule_sets(root))


# --- the count -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "words"),
    [
        ("", 0),
        (" \n\t ", 0),
        ("one two  three\n", 3),
        ("`a/path` [link](x.md#y) RS-OPS-019", 3),  # a link, a path or an id is one word
        (f"no{NBSP}break ideographic{IDEOGRAPHIC}space", 4),
        (f"line{LINE_SEPARATOR}separator next\x85line thin{THIN_SPACE}space", 6),
        ("unit\x1fseparator", 1),  # Python's split takes it as space; White_Space does not
        (f"zero{ZERO_WIDTH}width", 1),  # no White_Space property either
    ],
)
def test_a_word_is_a_run_of_characters_none_of_them_white_space(text: str, words: int) -> None:
    assert lr.word_count(text) == words


def test_the_white_space_named_is_unicode_s_property() -> None:
    """The 25 characters PropList.txt gives White_Space: none of the information
    separators Python's `str.isspace` admits."""
    assert len(lr.WHITE_SPACE) == 25
    assert {"\x1c", "\x1d", "\x1e", "\x1f"}.isdisjoint(lr.WHITE_SPACE)
    assert {chr(code) for code in (0xA0, 0x1680, 0x202F, 0x205F, 0x3000, 0x85)} <= lr.WHITE_SPACE


# --- the first budgets ----------------------------------------------------------------


CAPABILITY_LOADED = {
    ".pkit/capabilities/project-management/rules.md": "project-management:PM",
    ".pkit/capabilities/software-engineering/rules.md": "software-engineering:SWE",
}


def test_ops_and_project_kit_s_project_md_are_within_their_budgets() -> None:
    """Core's set gives its budget, each capability set that ships one gives its own,
    and project-kit sets its own file's (ADR-077 point 7), so the check holds here.
    The files are counted in the order a session reads them: core's, each registered
    capability's, then the project's (COR-070 point 1)."""
    budgets = budget_check(REPO)
    paths = [str(file.path) for file in budgets.files]
    assert paths == [CORE_LOADED, *CAPABILITY_LOADED, PROJECT_LOADED]
    by_path = {str(file.path): file for file in budgets.files}
    core, project = by_path[CORE_LOADED], by_path[PROJECT_LOADED]
    assert core.rule_set is not None and core.rule_set.citation == "backbone:OPS"
    assert core.checked and project.checked and project.rule_set is None
    for path, citation in CAPABILITY_LOADED.items():
        capability = by_path[path]
        assert capability.rule_set is not None and capability.rule_set.citation == citation
        assert capability.checked, path
    for file in budgets.files:
        assert file.budget is not None and file.words is not None
        assert file.words <= file.budget, file.path
    assert core.words == lr.word_count((REPO / CORE_LOADED).read_text(encoding="utf-8"))
    assert budgets.findings == ()


# --- the check: a loaded set's file ---------------------------------------------------


def test_a_project_s_loaded_file_within_its_budget_passes(adopter: AdopterRepo) -> None:
    text = own_set(adopter, budget=1000)
    result = rs.validate_rule_sets(adopter.root)
    assert [f for f in result.findings if f.kind is Kind.RULES_FILE_OVER_BUDGET] == []
    own = [f for f in result.rules_files if str(f.path) == PROJECT_LOADED]
    assert [(f.words, f.budget, f.checked) for f in own] == [(lr.word_count(text), 1000, True)]


def test_a_project_s_loaded_file_past_its_budget_fails(adopter: AdopterRepo) -> None:
    text = own_set(adopter, budget=1000)
    words = lr.word_count(text)
    adopter.write({OWN_SET: with_budget(adopter.root.joinpath(OWN_SET).read_text(), words - 1)})
    (finding,) = findings(adopter.root, Kind.RULES_FILE_OVER_BUDGET)
    assert finding.severity is rs.Severity.ERROR
    assert finding.location == PROJECT_LOADED
    assert f"holds {words} words, 1 past its budget of {words - 1}" in finding.message
    assert f"`budget` in OWN ({OWN_SET})" in finding.message
    assert "raising a budget is a person's decision (COR-069 point 4)" in finding.message
    assert "`pkit rule-sets generate`" in finding.message
    result = CliRunner().invoke(main, ["validate", "--only", "rule-sets"])
    assert result.exit_code == 1, result.output
    assert f"error    {PROJECT_LOADED}" in result.output


def test_a_project_s_own_loaded_set_may_give_no_budget(adopter: AdopterRepo) -> None:
    own_set(adopter, budget=None)
    assert findings(adopter.root, Kind.LOADED_SET_WITHOUT_BUDGET) == []
    lines = rs.summary_lines(rs.validate_rule_sets(adopter.root))
    assert any(line.startswith(f"rules file {PROJECT_LOADED}: ") for line in lines)
    assert next(line for line in lines if PROJECT_LOADED in line).endswith("word(s), no budget.")


def test_a_component_s_file_past_its_budget_fails_where_its_set_is_authored(
    tmp_path: Path,
) -> None:
    ops = (REPO / OPS_FILE).read_text(encoding="utf-8")
    words = lr.word_count((REPO / CORE_LOADED).read_text(encoding="utf-8"))
    root = authored_tree(tmp_path, with_budget(ops, words - 5))
    (finding,) = budget_check(root).findings
    assert finding.kind is Kind.RULES_FILE_OVER_BUDGET
    assert (finding.location, finding.severity) == (CORE_LOADED, rs.Severity.ERROR)
    assert f"5 past its budget of {words - 5}" in finding.message
    assert f"`budget` in backbone:OPS ({OPS_FILE})" in finding.message


def test_a_project_is_never_failed_for_a_file_it_receives(adopter: AdopterRepo) -> None:
    """The project cannot correct the backbone's file (COR-055 point 1): past its budget,
    it is reported and fails nothing."""
    ops = adopter.root / OPS_FILE
    ops.write_text(with_budget(ops.read_text(encoding="utf-8"), 10), encoding="utf-8")
    assert findings(adopter.root, Kind.RULES_FILE_OVER_BUDGET) == []
    (line,) = [
        line
        for line in rs.summary_lines(rs.validate_rule_sets(adopter.root))
        if line.startswith(f"rules file {CORE_LOADED}")
    ]
    assert re.fullmatch(rf"rules file {CORE_LOADED}: \d+ word\(s\), budget 10, \d+ over\.", line)


def test_an_installed_capability_s_file_is_counted_and_never_failed_where_received(
    adopter: AdopterRepo,
) -> None:
    """A registered capability's loaded file is a rules file, counted between core's and
    the project's (COR-069 point 1; COR-070 point 1). The project receives it by install,
    so past its budget it is reported and fails nothing (COR-055 point 1)."""
    adopter.install_capabilities("project-management", "software-engineering")
    loaded = ".pkit/capabilities/software-engineering/rules.md"
    swe = adopter.root / ".pkit/capabilities/software-engineering/rule-sets/swe.md"
    swe.write_text(with_budget(swe.read_text(encoding="utf-8"), 10), encoding="utf-8")
    assert findings(adopter.root, Kind.RULES_FILE_OVER_BUDGET) == []
    lines = rs.summary_lines(rs.validate_rule_sets(adopter.root))
    files = [line.split(":")[0] for line in lines if line.startswith("rules file ")]
    assert files.index(f"rules file {CORE_LOADED}") < files.index(f"rules file {loaded}")
    (line,) = [line for line in lines if line.startswith(f"rules file {loaded}")]
    assert re.fullmatch(rf"rules file {loaded}: \d+ word\(s\), budget 10, \d+ over\.", line)


def test_a_component_s_loaded_set_without_a_budget_fails_where_authored(
    tmp_path: Path,
) -> None:
    root = authored_tree(tmp_path, with_budget((REPO / OPS_FILE).read_text("utf-8"), None))
    (finding,) = budget_check(root).findings
    assert finding.kind is Kind.LOADED_SET_WITHOUT_BUDGET
    assert (finding.location, finding.severity) == (OPS_FILE, rs.Severity.ERROR)
    assert "the backbone's loaded set backbone:OPS gives no `budget`" in finding.message
    assert "COR-069 point 2" in finding.message


def test_a_component_s_set_without_a_budget_is_not_failed_where_received(
    adopter: AdopterRepo,
) -> None:
    ops = adopter.root / OPS_FILE
    ops.write_text(with_budget(ops.read_text(encoding="utf-8"), None), encoding="utf-8")
    assert findings(adopter.root, Kind.LOADED_SET_WITHOUT_BUDGET) == []
    lines = rs.summary_lines(rs.validate_rule_sets(adopter.root))
    assert next(line for line in lines if CORE_LOADED in line).endswith("word(s), no budget.")


def test_the_schema_refuses_a_budget_on_an_ordinary_set(adopter: AdopterRepo) -> None:
    adopter.write(
        {
            "docs/rule-sets/doc.md": (
                "---\nrule-set: DOC\nbudget: 100\nversion: 1.0.0\nscope: [docs/**]\nrules:\n"
                "  RS-DOC-001:\n    status: accepted\n"
                "    origin: {date: 2026-10-29, by: A. Person, why: Kept.}\n---\n\n"
                "## RS-DOC-001 — One\n\nText.\n"
            )
        }
    )
    (finding,) = [f for f in findings(adopter.root, Kind.SHAPE) if f.pointer == "/budget"]
    assert finding.location == "docs/rule-sets/doc.md"
    assert "an ordinary rule set takes no `budget`" in finding.message


@pytest.mark.parametrize("written", ["0", '"500"', "true"])
def test_the_schema_refuses_a_budget_that_is_no_count(adopter: AdopterRepo, written: str) -> None:
    text = with_budget(loaded_text("OWN", accepted("RS-OWN-001")), 1)
    adopter.write({OWN_SET: text.replace("budget: 1\n", f"budget: {written}\n")})
    shaped = [f for f in findings(adopter.root, Kind.SHAPE) if f.pointer == "/budget"]
    assert len(shaped) == 1, findings(adopter.root, Kind.SHAPE)
    (own,) = [s for s in rs.discover_rule_sets(adopter.root).rule_sets if s.name == "OWN"]
    assert own.budget is None


# --- the check: a plain project file -------------------------------------------------


def test_a_plain_project_file_within_its_key_passes(adopter: AdopterRepo) -> None:
    adopter.write({PROJECT_LOADED: "## Rules\n\n1. **Keep it short.** Four words here.\n"})
    set_key(adopter.root, 9)
    result = rs.validate_rule_sets(adopter.root)
    assert [f for f in result.findings if f.kind.value.startswith(("rules-", "plain-"))] == []
    assert f"rules file {PROJECT_LOADED}: 9 word(s), budget 9, 0 to spare." in rs.summary_lines(
        result
    )


def test_a_plain_project_file_past_its_key_fails(adopter: AdopterRepo) -> None:
    adopter.write({PROJECT_LOADED: "## Rules\n\n1. **Keep it short.** Four words here.\n"})
    set_key(adopter.root, 8)
    (finding,) = findings(adopter.root, Kind.RULES_FILE_OVER_BUDGET)
    assert finding.location == PROJECT_LOADED
    assert "holds 9 words, 1 past its budget of 8" in finding.message
    assert f"set as `rule-sets.plain-file-budget` in {CONFIG}" in finding.message
    assert "`pkit rule-sets generate`" not in finding.message


def test_a_plain_project_file_with_no_key_has_no_budget(adopter: AdopterRepo) -> None:
    adopter.write({PROJECT_LOADED: "One two three.\n"})
    result = rs.validate_rule_sets(adopter.root)
    assert f"rules file {PROJECT_LOADED}: 3 word(s), no budget." in rs.summary_lines(result)
    assert result.errors == () and result.warnings == ()


def test_the_key_bounds_nothing_without_a_plain_file(adopter: AdopterRepo) -> None:
    adopter.write({PROJECT_LOADED: None})
    set_key(adopter.root, 100)
    (finding,) = findings(adopter.root, Kind.PLAIN_FILE_BUDGET_UNUSED)
    assert finding.severity is rs.Severity.WARNING
    assert (finding.location, finding.pointer) == (CONFIG, "/rule-sets/plain-file-budget")
    assert f"keeps no rules file at {PROJECT_LOADED}" in finding.message
    result = CliRunner().invoke(main, ["validate", "--only", "rule-sets"])
    assert result.exit_code == 0, result.output
    assert "0 error(s), 1 warning(s), 0 report(s)." in result.output
    assert f"warning  {CONFIG}:/rule-sets/plain-file-budget" in result.output


def test_the_key_bounds_nothing_beside_the_project_s_own_loaded_set(
    adopter: AdopterRepo,
) -> None:
    """Converting the plain file moves its budget into the set, and the key then holds
    nothing, which validation says (COR-069 point 3)."""
    own_set(adopter, budget=1000)
    set_key(adopter.root, 1000)
    (finding,) = findings(adopter.root, Kind.PLAIN_FILE_BUDGET_UNUSED)
    assert f"the loaded set OWN ({OWN_SET})" in finding.message
    assert "Move the budget into the set's `budget`" in finding.message


# --- the report, in a project that receives `OPS` -------------------------------------


def test_validate_reports_each_rules_file_in_a_project_that_receives_ops(
    adopter: AdopterRepo,
) -> None:
    adopter.write({PROJECT_LOADED: "One two three.\n"})
    (ops,) = [s for s in rs.discover_rule_sets(adopter.root).rule_sets if s.name == "OPS"]
    assert ops.budget is not None  # it arrives with the backbone's set
    words = lr.word_count((adopter.root / CORE_LOADED).read_text(encoding="utf-8"))
    result = CliRunner().invoke(main, ["validate", "--only", "rule-sets"])
    assert result.exit_code == 0, result.output
    assert f"    rules file {CORE_LOADED}: {lr.measure(words, ops.budget)}.\n" in result.output
    assert f"    rules file {PROJECT_LOADED}: 3 word(s), no budget.\n" in result.output


def test_the_member_s_help_names_the_rules_files_and_their_budgets() -> None:
    from project_kit import validators

    (member,) = [v for v in validators.BACKBONE_VALIDATORS if v.name == "rule-sets"]
    assert "every rules file" in member.help and "budgets" in member.help


# --- the generator --------------------------------------------------------------------


def test_generate_prints_each_file_s_count_against_its_budget(adopter: AdopterRepo) -> None:
    adopter.write({OWN_SET: with_budget(loaded_text("OWN", accepted("RS-OWN-001")), 1000)})
    result = CliRunner().invoke(main, ["rule-sets", "generate"])
    assert result.exit_code == 0, result.output
    words = lr.word_count((adopter.root / PROJECT_LOADED).read_text(encoding="utf-8"))
    assert f"wrote      {PROJECT_LOADED}  (from OWN, {OWN_SET})\n" in result.output
    assert f"\n             {words} word(s), budget 1000, {1000 - words} to spare\n" in (
        result.output
    )


def test_generate_writes_a_file_past_its_budget_and_says_to_trim(adopter: AdopterRepo) -> None:
    adopter.write({OWN_SET: with_budget(loaded_text("OWN", accepted("RS-OWN-001")), 2)})
    result = CliRunner().invoke(main, ["rule-sets", "generate"])
    assert result.exit_code == 0, result.output
    assert (adopter.root / PROJECT_LOADED).is_file()
    assert "budget 2, " in result.output and " over; raising a budget is a person's" in (
        result.output
    )


def test_generate_says_a_file_has_no_budget(adopter: AdopterRepo) -> None:
    adopter.write({OWN_SET: loaded_text("OWN", accepted("RS-OWN-001"))})
    result = CliRunner().invoke(main, ["rule-sets", "generate"])
    assert re.search(r"\n {13}\d+ word\(s\), no budget\n", result.output), result.output


# --- `pkit rule-sets altered` ---------------------------------------------------------


@pytest.fixture
def changed(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """A base on `main` with `OPS` as shipped, a project's own loaded set `OWN` at budget
    50, and `rule-sets.plain-file-budget` at 100; then branch `feature`."""
    from tests.friction_documents import commit_install

    repo = make_adopter_repo(prepare=commit_install)
    repo.write({OWN_SET: with_budget(loaded_text("OWN", accepted("RS-OWN-001")), 50)})
    set_key(repo.root, 100)
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    return repo


def budgets_of(repo: AdopterRepo) -> list[tuple[str, int | None, int | None, str]]:
    document = reading.altered_document(repo.root, "main")
    return [(b["set_by"], b["base"], b["head"], b["change"]) for b in document["budgets"]]


def test_altered_lists_a_raise_and_a_lowering(changed: AdopterRepo) -> None:
    ops = changed.root / OPS_FILE
    (shipped,) = [s for s in rs.discover_rule_sets(changed.root).rule_sets if s.name == "OPS"]
    assert shipped.budget is not None
    ops.write_text(with_budget(ops.read_text(encoding="utf-8"), shipped.budget + 40), "utf-8")
    changed.write({OWN_SET: with_budget(changed.root.joinpath(OWN_SET).read_text(), 40)})
    assert budgets_of(changed) == [
        ("backbone:OPS", shipped.budget, shipped.budget + 40, "raised"),
        ("OWN", 50, 40, "lowered"),
    ]
    (entry, _lowered) = reading.altered_document(changed.root, "main")["budgets"]
    assert (entry["path"], entry["file"]) == (OPS_FILE, CORE_LOADED)

    human = CliRunner().invoke(main, ["rule-sets", "altered", "--base", "main"]).output
    raises = human.index("Budgets the change raises, each a person's to authorise")
    assert raises < human.index("backbone:OPS") < human.index("Budgets otherwise changed:")
    assert f"raised    backbone:OPS  {shipped.budget} → {shipped.budget + 40} word(s)" in human
    assert f"lowered   OWN  50 → 40 word(s)  ({OWN_SET}, bounding {PROJECT_LOADED})" in human


def test_altered_lists_an_addition_and_a_removal(changed: AdopterRepo) -> None:
    """The project converts nothing here: it drops the set's budget and the key's, and a
    second set gains one. Each is listed, and the JSON says how."""
    changed.write(
        {
            OWN_SET: with_budget(changed.root.joinpath(OWN_SET).read_text(), None),
            "docs/rule-sets/two.md": with_budget(loaded_text("TWO", accepted("RS-TWO-001")), 70),
        }
    )
    set_key(changed.root, None)
    assert budgets_of(changed) == [
        ("OWN", 50, None, "removed"),
        ("TWO", None, 70, "added"),
        ("rule-sets.plain-file-budget", 100, None, "removed"),
    ]
    result = CliRunner().invoke(main, ["rule-sets", "altered", "--base", "main", "--json"])
    document = json.loads(result.stdout)
    assert document["schema_version"] == 1  # a key added
    assert document["budgets"][-1] == {
        "set_by": "rule-sets.plain-file-budget",
        "path": CONFIG,
        "file": PROJECT_LOADED,
        "base": 100,
        "head": None,
        "change": "removed",
    }
    human = CliRunner().invoke(main, ["rule-sets", "altered", "--base", "main"]).output
    assert "Budgets the change raises" not in human
    assert "added     TWO  none → 70 word(s)" in human


def test_altered_lists_no_budget_a_change_leaves_as_it_was(changed: AdopterRepo) -> None:
    changed.write({OWN_SET: changed.root.joinpath(OWN_SET).read_text() + "\nMore prose.\n"})
    assert budgets_of(changed) == []
