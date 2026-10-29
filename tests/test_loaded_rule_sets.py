"""Loaded rule sets (COR-068; ADR-073, #2260).

A loaded set (`loaded: true`) keeps operational rules. Its accepted rules bind on
the work of the sessions that load a file generated from it, never on an artefact.
These tests hold:

- **the backbone's set**, `OPS`: core's 22 rules, each accepted with an origin,
  each keeping its number, and `.pkit/rules/core.md` generated from it;
- **the projection** (`loaded_rule_sets.project`): accepted rules only, under
  `N. Title (RS-<SET>-NNN)`, the prose and the groups kept, no front matter, no
  retired or proposed rule, nothing added;
- **the generator** (`pkit rule-sets generate`) and its refusals;
- **the staleness check**, where the set is authored, and not where it arrives by
  sync;
- **the schema's and the pass's refusals** on a loaded set;
- **the reach walk**, which routes through no loaded set;
- **the citation check** of the `refs` member: the forms it reads, what it never
  reads, and the files it leaves out.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import friction_discovery as fd
from project_kit import loaded_rule_sets as lr
from project_kit import refs
from project_kit import rule_sets as rs
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO = Path(__file__).resolve().parents[1]
OPS_FILE = REPO / ".pkit" / "rule-sets" / "ops.md"
CORE_RULES = REPO / ".pkit" / "rules" / "core.md"
PROJECT_SETS = "docs/rule-sets"
PROJECT_LOADED = ".pkit/rules/project.md"
CORE_LOADED = ".pkit/rules/core.md"

Kind = rs.RuleSetFindingKind

QUOTE = {"date": "2026-10-28", "by": "A. Person", "why": "Sessions keep it."}


def loaded_text(
    name: str,
    rules: Mapping[str, Mapping[str, Any]],
    *,
    body: str | None = None,
    **front: Any,
) -> str:
    """A loaded set's file: `name`, `loaded: true`, `rules`, and either `body` or a
    preface with one `### <id> — Rule <n>` section per rule."""
    yaml = YAML()
    yaml.default_flow_style = False
    buffer = io.StringIO()
    yaml.dump(
        {"rule-set": name, "loaded": True, "version": "1.0.0", **front, "rules": dict(rules)},
        buffer,
    )
    if body is None:
        sections = "\n".join(
            f"### {rule_id} — Rule {int(rule_id.rsplit('-', 1)[1])}\n\n"
            f"**Rule {int(rule_id.rsplit('-', 1)[1])}.** The statement.\n"
            for rule_id in rules
        )
        body = f"*The preface.*\n\n## Group\n\nThe group's prose.\n\n{sections}"
    return f"---\n{buffer.getvalue()}---\n\n{body}"


def accepted(*ids: str) -> dict[str, dict[str, Any]]:
    return {rule_id: {"status": "accepted", "origin": dict(QUOTE)} for rule_id in ids}


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def project_set(adopter: AdopterRepo, text: str, name: str = "own.md") -> None:
    adopter.write({f"{PROJECT_SETS}/{name}": text})


def the_set(root: Path, name: str) -> rs.RuleSet:
    (found,) = [s for s in rs.discover_rule_sets(root).rule_sets if s.name == name]
    return found


def findings(adopter: AdopterRepo, kind: Kind) -> list[rs.RuleSetFinding]:
    return [f for f in rs.validate_rule_sets(adopter.root).findings if f.kind is kind]


# --- the backbone's set, `OPS` -------------------------------------------------------


def test_ops_holds_core_s_22_rules_each_accepted_with_an_origin() -> None:
    ops = the_set(REPO, "OPS")
    assert ops.path == ".pkit/rule-sets/ops.md"
    assert (ops.component, ops.citation, ops.loaded) == ("backbone", "backbone:OPS", True)
    assert [rule.id for rule in ops.rules] == [f"RS-OPS-{n:03d}" for n in range(1, 23)]
    for rule in ops.rules:
        assert rule.status == "accepted", rule.id
        origin = rule.origin or {}
        assert "decision" in origin or {"date", "by", "why"} <= set(origin), rule.id
        # COR-068 point 6: a core record, or the decider's words; never an ADR or a PRJ.
        assert not str(origin.get("decision", "")).startswith(("ADR-", "PRJ-")), rule.id


def test_each_ops_rule_is_anchored_to_core_records_or_says_why_it_is_not() -> None:
    """So an adopter's measures count no rule of the set as forgotten: each rule anchors
    the core records it rests on, or gives the reason it has none (COR-050 point 1). An
    anchor names a core record only, since a set every project receives would resolve an
    `ADR-` or `PRJ-` anchor against that project's own records."""
    artefacts = {
        a.id: a for a in fd.discover_artefacts(REPO).artefacts if a.path == ".pkit/rule-sets/ops.md"
    }
    assert sorted(artefacts) == [f"RS-OPS-{n:03d}" for n in range(1, 23)]
    origins = {rule.id: rule.origin or {} for rule in the_set(REPO, "OPS").rules}
    for rule_id, artefact in artefacts.items():
        anchors, reason = dict(artefact.anchors), artefact.unanchored_because
        assert bool(anchors) != bool(reason), rule_id
        assert set(anchors) <= {"record"}, rule_id
        records = anchors.get("record", ())
        assert all(record.startswith("COR-") for record in records), rule_id
        decided = origins[rule_id].get("decision")
        assert decided is None or decided in records, rule_id


def test_ops_and_core_md_are_clean_in_the_methodology_s_source() -> None:
    result = rs.validate_rule_sets(REPO)
    ops = [f for f in result.findings if f.location.startswith((".pkit/rule-sets/", CORE_LOADED))]
    assert ops == []


def test_core_md_is_the_projection_of_ops() -> None:
    assert CORE_RULES.read_text(encoding="utf-8") == lr.project(the_set(REPO, "OPS"))


def test_each_rule_of_core_md_names_its_number_title_and_id() -> None:
    headings = re.findall(r"^### (\d+)\. (.+) \((RS-OPS-\d{3})\)$", CORE_RULES.read_text(), re.M)
    assert [int(n) for n, _title, _id in headings] == list(range(1, 23))
    assert all(rule_id == f"RS-OPS-{int(n):03d}" for n, _title, rule_id in headings)
    assert ("19", "A session changes only its own repository", "RS-OPS-019") in headings


def test_core_md_carries_no_data_and_no_h1() -> None:
    text = CORE_RULES.read_text(encoding="utf-8")
    assert not text.startswith("---")
    assert "origin:" not in text and "status: accepted" not in text
    assert not re.search(r"^# ", text, re.M)
    assert text.startswith("*Operational rules and tool hygiene")
    assert "`pkit rule-sets generate`; edit the set, not the loaded file." in text


# --- the projection ----------------------------------------------------------------


def test_the_projection_keeps_accepted_rules_and_leaves_out_the_rest(
    adopter: AdopterRepo,
) -> None:
    rules = {
        **accepted("RS-OWN-001"),
        "RS-OWN-002": {},
        "RS-OWN-003": {"status": "superseded", "successor": "RS-OWN-004", "origin": dict(QUOTE)},
        **accepted("RS-OWN-004"),
        "RS-OWN-005": {"status": "withdrawn", "origin": dict(QUOTE)},
    }
    project_set(adopter, loaded_text("OWN", rules))
    text = lr.project(the_set(adopter.root, "OWN"))
    assert text == (
        "*The preface.*\n\n## Group\n\nThe group's prose.\n\n"
        "### 1. Rule 1 (RS-OWN-001)\n\n**Rule 1.** The statement.\n\n"
        "### 4. Rule 4 (RS-OWN-004)\n\n**Rule 4.** The statement.\n"
    )


def test_the_projection_keeps_the_level_and_the_groups_as_written(
    adopter: AdopterRepo,
) -> None:
    body = (
        "Opening prose.\n\n## First\n\n#### RS-OWN-001 - One\n\nStatement one.\n\n"
        "## Second\n\nUnder the second.\n\n#### RS-OWN-002: Two\n\nStatement two.\n\n"
        "## Closing\n\n- a list that carries over\n"
    )
    project_set(adopter, loaded_text("OWN", accepted("RS-OWN-001", "RS-OWN-002"), body=body))
    assert lr.project(the_set(adopter.root, "OWN")) == (
        "Opening prose.\n\n## First\n\n#### 1. One (RS-OWN-001)\n\nStatement one.\n\n"
        "## Second\n\nUnder the second.\n\n#### 2. Two (RS-OWN-002)\n\nStatement two.\n\n"
        "## Closing\n\n- a list that carries over\n"
    )


def test_a_rule_section_runs_to_the_next_heading_of_its_level(adopter: AdopterRepo) -> None:
    body = (
        "## Group\n\n### RS-OWN-001 — Gone\n\nIts text.\n\n#### Inside it\n\nStill its text.\n\n"
        "### RS-OWN-002 — Kept\n\nKept text.\n"
    )
    rules = {"RS-OWN-001": {"status": "withdrawn", "origin": dict(QUOTE)}, **accepted("RS-OWN-002")}
    project_set(adopter, loaded_text("OWN", rules, body=body))
    assert lr.project(the_set(adopter.root, "OWN")) == (
        "## Group\n\n### 2. Kept (RS-OWN-002)\n\nKept text.\n"
    )


def test_headings_in_fenced_code_open_no_section(adopter: AdopterRepo) -> None:
    body = "### RS-OWN-001 — One\n\n```\n### RS-OWN-001 — not a heading\n```\n"
    project_set(adopter, loaded_text("OWN", accepted("RS-OWN-001"), body=body))
    assert lr.project(the_set(adopter.root, "OWN")) == (
        "### 1. One (RS-OWN-001)\n\n```\n### RS-OWN-001 — not a heading\n```\n"
    )


# --- the generator ------------------------------------------------------------------


def test_generate_writes_a_project_s_loaded_file_and_says_so(adopter: AdopterRepo) -> None:
    project_set(adopter, loaded_text("OWN", accepted("RS-OWN-001")))
    result = CliRunner().invoke(main, ["rule-sets", "generate"])
    assert result.exit_code == 0, result.output
    assert f"wrote      {PROJECT_LOADED}  (from OWN, {PROJECT_SETS}/own.md)" in result.output
    assert f"left       {CORE_LOADED}  (backbone:OPS arrives by sync)" in result.output
    written = (adopter.root / PROJECT_LOADED).read_text(encoding="utf-8")
    assert written == lr.project(the_set(adopter.root, "OWN"))

    again = CliRunner().invoke(main, ["rule-sets", "generate"])
    assert again.exit_code == 0, again.output
    assert f"unchanged  {PROJECT_LOADED}" in again.output


def test_generate_refuses_where_every_loaded_set_arrives_by_sync(adopter: AdopterRepo) -> None:
    before = (adopter.root / CORE_LOADED).read_bytes()
    result = CliRunner().invoke(main, ["rule-sets", "generate"])
    assert result.exit_code == 1
    assert "every loaded rule set here arrives by sync: backbone:OPS" in result.output
    assert "the next sync brings it" in result.output
    assert (adopter.root / CORE_LOADED).read_bytes() == before


def test_generate_refuses_a_set_whose_rules_and_sections_do_not_join(
    adopter: AdopterRepo,
) -> None:
    project_set(adopter, loaded_text("OWN", accepted("RS-OWN-001"), body="No sections.\n"))
    result = CliRunner().invoke(main, ["rule-sets", "generate"])
    assert result.exit_code == 1
    assert "its rules and its sections do not join" in result.output
    assert "`pkit validate`" in result.output
    assert not (adopter.root / PROJECT_LOADED).exists()


def test_generate_refuses_an_unreadable_rule_set_file(adopter: AdopterRepo) -> None:
    adopter.write({f"{PROJECT_SETS}/broken.md": "no front matter\n"})
    result = CliRunner().invoke(main, ["rule-sets", "generate"])
    assert result.exit_code == 1
    assert f"the rule-set file {PROJECT_SETS}/broken.md has no front matter" in result.output


def test_generate_writes_core_md_where_the_set_is_authored(tmp_path: Path) -> None:
    """In the methodology's source — the predicate's own test — core's loaded file is
    written from `OPS`, and a second run writes nothing."""
    root = tmp_path
    for marker in ("src/project_kit/__init__.py", ".pkit/lifecycle/ownership.py"):
        source = REPO / marker
        (root / marker).parent.mkdir(parents=True, exist_ok=True)
        (root / marker).write_bytes(source.read_bytes())
    (root / ".pkit/rule-sets").mkdir(parents=True)
    (root / ".pkit/rule-sets/ops.md").write_bytes(OPS_FILE.read_bytes())
    generation = lr.generate(root)
    assert [(g.path, g.changed) for g in generation.written] == [(CORE_LOADED, True)]
    assert (root / CORE_LOADED).read_bytes() == CORE_RULES.read_bytes()
    assert [(g.path, g.changed) for g in lr.generate(root).written] == [(CORE_LOADED, False)]


# --- the staleness check -------------------------------------------------------------


def test_a_loaded_file_out_of_step_with_its_set_fails_validation(adopter: AdopterRepo) -> None:
    project_set(adopter, loaded_text("OWN", accepted("RS-OWN-001")))
    adopter.write({PROJECT_LOADED: "a hand edit\n"})
    (finding,) = findings(adopter, Kind.LOADED_FILE_STALE)
    assert finding.severity is rs.Severity.ERROR
    assert finding.location == PROJECT_LOADED
    assert "the file differs from the loaded file of OWN" in finding.message
    assert "`pkit rule-sets generate`" in finding.message


def test_a_missing_loaded_file_fails_validation(adopter: AdopterRepo) -> None:
    project_set(adopter, loaded_text("OWN", accepted("RS-OWN-001")))
    adopter.write({PROJECT_LOADED: None})
    (finding,) = findings(adopter, Kind.LOADED_FILE_STALE)
    assert "the file is missing" in finding.message


def test_line_endings_alone_are_no_difference(adopter: AdopterRepo) -> None:
    project_set(adopter, loaded_text("OWN", accepted("RS-OWN-001")))
    text = lr.project(the_set(adopter.root, "OWN"))
    (adopter.root / PROJECT_LOADED).write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    assert findings(adopter, Kind.LOADED_FILE_STALE) == []


def test_a_set_that_arrives_by_sync_is_not_compared(adopter: AdopterRepo) -> None:
    adopter.write({CORE_LOADED: "the project edited the file it receives\n"})
    assert findings(adopter, Kind.LOADED_FILE_STALE) == []


def test_a_tree_without_the_ownership_module_skips_the_check_and_says_so(
    adopter: AdopterRepo,
) -> None:
    (adopter.root / ".pkit/lifecycle/ownership.py").unlink()
    reported = findings(adopter, Kind.LOADED_FILE_UNCHECKED)
    assert reported and all(f.severity is rs.Severity.REPORT for f in reported)
    assert findings(adopter, Kind.LOADED_FILE_STALE) == []


# --- the refusals ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("front", "rule", "key"),
    [
        ({"scope": ["docs/**"]}, {}, "scope"),
        ({"inherits": ["CMN@1"]}, {}, "inherits"),
        ({"checks": {"RS-OWN-001": [{"check": "lint", "part": "words"}]}}, {}, "checks"),
        ({}, {"offers": ["point"]}, "offers"),
        ({}, {"fills": ["RS-CMN-001#point"]}, "fills"),
    ],
)
def test_the_schema_refuses_what_says_where_rules_bind(
    adopter: AdopterRepo, front: dict[str, Any], rule: dict[str, Any], key: str
) -> None:
    rules = {"RS-OWN-001": {"status": "accepted", "origin": dict(QUOTE), **rule}}
    project_set(adopter, loaded_text("OWN", rules, **front))
    shaped = [f for f in findings(adopter, Kind.SHAPE) if f.pointer.endswith(f"/{key}")]
    assert len(shaped) == 1, findings(adopter, Kind.SHAPE)
    assert f"a loaded rule set takes no `{key}`" in shaped[0].message


def test_a_set_marked_loaded_false_is_an_ordinary_one(adopter: AdopterRepo) -> None:
    text = loaded_text("OWN", accepted("RS-OWN-001"), scope=["docs/**"]).replace(
        "loaded: true", "loaded: false"
    )
    project_set(adopter, text)
    assert findings(adopter, Kind.SHAPE) == []
    assert not the_set(adopter.root, "OWN").loaded


def test_no_set_inherits_a_loaded_set(adopter: AdopterRepo) -> None:
    project_set(adopter, loaded_text("OWN", accepted("RS-OWN-001")))
    adopter.write(
        {
            f"{PROJECT_SETS}/doc.md": (
                "---\nrule-set: DOC\nversion: 1.0.0\ninherits: [OWN@1]\nscope: [docs/**]\n"
                "rules: {}\n---\n"
            )
        }
    )
    (finding,) = findings(adopter, Kind.INHERITS_LOADED)
    assert (finding.location, finding.pointer) == (f"{PROJECT_SETS}/doc.md", "/inherits/0")


def test_one_loaded_set_to_an_owner(adopter: AdopterRepo) -> None:
    project_set(adopter, loaded_text("ONE", accepted("RS-ONE-001")), "a.md")
    project_set(adopter, loaded_text("TWO", accepted("RS-TWO-001")), "b.md")
    (finding,) = findings(adopter, Kind.SECOND_LOADED)
    assert finding.location == f"{PROJECT_SETS}/b.md"
    assert "ONE" in finding.message


def test_a_capability_s_loaded_set_is_refused(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    adopter.write(
        {".pkit/capabilities/evidence/rule-sets/ev.md": loaded_text("EV", accepted("RS-EV-001"))}
    )
    (finding,) = findings(adopter, Kind.CAPABILITY_LOADED)
    assert "COR-068 point 4" in finding.message


def test_an_h1_in_a_loaded_set_s_body_is_refused(adopter: AdopterRepo) -> None:
    body = "# A title\n\n### RS-OWN-001 — One\n\nText.\n"
    project_set(adopter, loaded_text("OWN", accepted("RS-OWN-001"), body=body))
    (finding,) = findings(adopter, Kind.LOADED_HEADING)
    assert "'A title'" in finding.message


# --- the reach walk -------------------------------------------------------------------


def test_the_reach_walk_routes_through_no_loaded_set(adopter: AdopterRepo) -> None:
    """Even a loaded set validation refuses for a scope, and a set validation refuses
    for inheriting one, bind nothing of it on an artefact (ADR-073 point 7)."""
    project_set(adopter, loaded_text("OWN", accepted("RS-OWN-001"), scope=["docs/**"]))
    adopter.write(
        {
            "docs/guide.md": "---\nreader: user\n---\n\n# Guide\n",
            f"{PROJECT_SETS}/doc.md": (
                "---\nrule-set: DOC\nversion: 1.0.0\ninherits: [OWN@1]\nscope: [docs/**]\n"
                "rules:\n  RS-DOC-001:\n    status: accepted\n"
                "    origin: {date: 2026-10-28, by: A. Person, why: Kept.}\n---\n\n"
                "## RS-DOC-001 — Own\n\nText.\n"
            ),
        }
    )
    _discovery, _sets, answer = rs.reach_at(adopter.root)
    bound = {binding.rule.id for found in answer.by_location.values() for binding in found.bindings}
    assert "RS-DOC-001" in bound
    assert not any(rule_id.startswith(("RS-OWN-", "RS-OPS-")) for rule_id in bound)


# --- the citation check ----------------------------------------------------------------


def cited(text: str, *, markdown: bool = True, loaded: Iterable[str] = ("OPS",)) -> list[tuple]:
    return [
        (c.layer, c.number, c.rule, c.component)
        for c in refs.operational_rule_citations(text, loaded_sets=set(loaded), markdown=markdown)
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("see core rule 19.", [("core", 19)]),
        ("Core rule 5 says", [("core", 5)]),
        ("per core.md rule 13", [("core", 13)]),
        ("per `.pkit/rules/core.md` rule 7", [("core", 7)]),
        ("(COR-010 / rules/core.md #7)", [("core", 7)]),
        ("(rules/core.md 14-15)", [("core", 14), ("core", 15)]),
        ("core rules 3, 5 and 13", [("core", 3), ("core", 5), ("core", 13)]),
        ("core rules 14-15", [("core", 14), ("core", 15)]),
        ("the core rule\n  2 says", [("core", 2)]),
        ("project rule 4", [("project", 4)]),
        ("Project rules 1 to 3", [("project", 1), ("project", 2), ("project", 3)]),
    ],
)
def test_the_forms_by_layer_and_number(text: str, expected: list[tuple[str, int]]) -> None:
    assert [(layer, number) for layer, number, _r, _c in cited(text)] == expected


def test_the_forms_by_id() -> None:
    assert cited("`backbone:RS-OPS-019`, [backbone:RS-OPS-003] and RS-OPS-008") == [
        (None, None, "RS-OPS-019", "backbone"),
        (None, None, "RS-OPS-003", "backbone"),
        (None, None, "RS-OPS-008", None),
    ]
    assert cited("RS-WRITE-005") == []  # a rule of no loaded set


@pytest.mark.parametrize(
    "text",
    ["see rule 5 above", "rule 19", "COR-058 point 10", "the rule-18 gate", "score rule 4"],
)
def test_what_is_never_read(text: str) -> None:
    assert cited(text) == []


def test_fenced_code_is_skipped_in_markdown_only() -> None:
    text = "```\ncore rule 99\n```\n"
    assert cited(text, markdown=True) == []
    assert cited(text, markdown=False) == [("core", 99, None, None)]


def test_a_missing_or_retired_rule_is_a_warning_naming_it(adopter: AdopterRepo) -> None:
    rules = {
        **accepted("RS-OWN-001"),
        "RS-OWN-002": {"status": "superseded", "successor": "RS-OWN-001", "origin": dict(QUOTE)},
    }
    project_set(adopter, loaded_text("OWN", rules))
    adopter.write(
        {
            "docs/guide.md": (
                "Core rule 19 holds. Core rule 99 is not one. Project rule 1 holds.\n"
                "Project rule 2 is retired, and so is RS-OWN-002.\n"
            )
        }
    )
    found = [
        (u.path, u.citation.line, u.message) for u in refs.unheld_operational_rules(adopter.root)
    ]
    assert [(path, line) for path, line, _m in found] == [
        ("docs/guide.md", 1),
        ("docs/guide.md", 2),
        ("docs/guide.md", 2),
    ]
    assert "which backbone:OPS (.pkit/rule-sets/ops.md) does not hold" in found[0][2]
    assert "which is superseded; its successor is RS-OWN-001" in found[1][2]
    assert "RS-OWN-002" in found[2][2]

    result = CliRunner().invoke(main, ["validate", "--only", "refs"])
    assert result.exit_code == 0, result.output
    assert "warning  docs/guide.md:1" in result.output


def test_a_layer_with_no_loaded_set_is_not_judged(adopter: AdopterRepo) -> None:
    adopter.write({"docs/guide.md": "project rule 99 of a plain project.md\n"})
    assert refs.unheld_operational_rules(adopter.root) == []


def test_the_files_left_out(adopter: AdopterRepo) -> None:
    unheld = "Core rule 99.\n"
    adopter.write(
        {
            ".pkit/project/config.yaml": "name: adopter\nfriction:\n  exclude: [notes/]\n",
            "tests/test_x.py": f"# {unheld}",
            "src/test_y.py": f"# {unheld}",
            "notes/draft.md": unheld,
            ".pkit/project/friction/answers/20261028T000000Z-0000aaaa.yaml": f"# {unheld}",
            ".pkit/decisions/project/PRJ-001-old.md": (
                f"---\nid: PRJ-001\ntitle: Old\nstatus: superseded\n---\n\n{unheld}"
            ),
            ".pkit/decisions/project/PRJ-002-new.md": (
                f"---\nid: PRJ-002\ntitle: New\nstatus: accepted\n---\n\n{unheld}"
            ),
        }
    )
    # The synced copies (`.pkit/rules/core.md`, the backbone's records) are read nowhere.
    assert [u.path for u in refs.unheld_operational_rules(adopter.root)] == [
        ".pkit/decisions/project/PRJ-002-new.md"
    ]


def test_a_loaded_set_s_rule_cited_in_an_agent_is_reported_once(adopter: AdopterRepo) -> None:
    agent = adopter.root / ".pkit/agents/project/helper.md"
    agent.parent.mkdir(parents=True, exist_ok=True)
    agent.write_text(
        "---\nname: helper\ndescription: helps\n---\n\nKeep backbone:RS-OPS-099.\n",
        encoding="utf-8",
    )
    issues = refs.validate_corpus(adopter.root)
    about = [i for i in issues if "RS-OPS-099" in i.diagnosis]
    assert [i.kind for i in about] == [refs.OPERATIONAL_CITATION]


def test_the_source_s_citations_all_name_rules_in_force() -> None:
    assert refs.unheld_operational_rules(REPO) == []


def test_backbone_component_is_the_ops_owner() -> None:
    assert the_set(REPO, "OPS").component == fd.BACKBONE_COMPONENT
