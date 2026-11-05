"""A capability's loaded rules and how they reach a session (COR-070; ADR-076, #2269).

These tests hold:

- **a capability's loaded set**: its generated `rules.md`, the staleness check and the
  preface that names it where it is authored, a second loaded set refused, and a
  `rules.md` with no set behind it;
- **`pkit rule-sets loaded`**: every layer's loaded file with its owner, registered
  capabilities only;
- **the index** `.pkit/rules/capabilities.md`: its render, its order, the empty case,
  the forms that differ, and a file at its path that is no index;
- **the check** `loaded-rules-undelivered`: an index out of step, an entry whose file is
  missing, an entry for no registered capability, a host without the line, the index
  absent, an adapter with no key, and entry forms that differ;
- **an import token** in a loaded set, refused outside code;
- **the citation form** `<capability>:RS-<SET>-NNN`;
- **what a step newly binds**, for core's set and a capability's;
- **`pkit status`**, which reports the index.
"""

from __future__ import annotations

import json
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import capabilities as caps
from project_kit import install as install_mod
from project_kit import loaded_rule_sets as lrs
from project_kit import loaded_rules as lr
from project_kit import refs, sync
from project_kit import rule_sets as rs
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    adapter_manifest_rel,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO = Path(__file__).resolve().parents[1]
Kind = rs.RuleSetFindingKind
INDEX = ".pkit/rules/capabilities.md"
UNDELIVERED = lr.DeliveryKind.UNDELIVERED.value

PACKAGE = """schema_version: 1
component:
  kind: capability
  name: {name}
  version: 0.1.0
description: A capability of the tests.
requires_backbone: ">=0.1.0"
"""


def loaded_set(name: str, set_name: str, *, status: str = "accepted", preface: str = "") -> str:
    """A capability's loaded set with one rule, its preface naming the capability."""
    preface = preface or f"*The rules of the {name} capability, which add to core's.*"
    return (
        f"---\nrule-set: {set_name}\nloaded: true\nversion: 1.0.0\nrules:\n"
        f"  RS-{set_name}-001:\n    status: {status}\n"
        f'    origin: {{date: 2026-10-30, by: "A. Person", why: "Sessions keep it."}}\n'
        f"---\n\n## Rules of {set_name}\n\n{preface}\n\n"
        f"### RS-{set_name}-001 — One rule\n\n**Keep it.** The statement.\n"
    )


def incubated(adopter: AdopterRepo, name: str, set_text: str | None = None) -> Path:
    """Author capability `name` in the project and register it in place: a capability
    authored here, whose loaded set is generated and checked here."""
    folder = adopter.root / ".pkit" / "capabilities" / name
    (folder / "rule-sets").mkdir(parents=True)
    (folder / "package.yaml").write_text(PACKAGE.format(name=name), encoding="utf-8")
    if set_text is not None:
        (folder / "rule-sets" / "set.md").write_text(set_text, encoding="utf-8")
    source = caps.find_capability_in_repo(adopter.root, name)
    assert source is not None
    caps.register_incubated_capability(adopter.root, source)
    return folder


def generate_and_render(adopter: AdopterRepo) -> None:
    lrs.generate(adopter.root)
    lr.write_index(adopter.root)


def host_with_line(adopter: AdopterRepo) -> None:
    adopter.write({"CLAUDE.md": "# Host\n\n@.pkit/rules/core.md\n@.pkit/rules/capabilities.md\n"})


def delivery_findings(adopter: AdopterRepo) -> list[tuple[str, str, str]]:
    return [
        (f.location, f.severity.value, f.message) for f in lr.check_delivery(adopter.root).findings
    ]


def kinds(adopter: AdopterRepo, kind: rs.RuleSetFindingKind) -> list[rs.RuleSetFinding]:
    return [f for f in rs.validate_rule_sets(adopter.root).findings if f.kind is kind]


def register_adapter(adopter: AdopterRepo, name: str, package: str) -> None:
    folder = adopter.root / ".pkit" / "adapters" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "package.yaml").write_text(package, encoding="utf-8")
    manifest = read_backbone_manifest(adopter.root)
    assert manifest is not None
    manifest.components.append(
        ComponentRegistryEntry(kind="adapter", name=name, manifest=adapter_manifest_rel(name))
    )
    write_backbone_manifest(adopter.root, manifest)


ADAPTER = """schema_version: 1
component:
  kind: adapter
  name: {name}
  version: 0.1.0
description: An adapter of the tests.
requires_backbone: ">=0.1.0"
{key}"""


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


# --- a capability's loaded set (ADR-076 point 1) ----------------------------------------


def test_generate_writes_a_capability_s_rules_md_where_it_is_authored(
    adopter: AdopterRepo,
) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    generation = lrs.generate(adopter.root)
    written = {g.path: g.changed for g in generation.written}
    assert written[".pkit/capabilities/alpha/rules.md"] is True
    text = (adopter.root / ".pkit/capabilities/alpha/rules.md").read_text(encoding="utf-8")
    assert text.startswith("## Rules of ALPHA\n\n*The rules of the alpha capability")
    assert "### 1. One rule (RS-ALPHA-001)" in text
    assert kinds(adopter, Kind.LOADED_FILE_STALE) == []


def test_a_capability_s_proposed_rules_leave_only_its_preface(adopter: AdopterRepo) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA", status="proposed"))
    lrs.generate(adopter.root)
    text = (adopter.root / ".pkit/capabilities/alpha/rules.md").read_text(encoding="utf-8")
    assert "RS-ALPHA-001" not in text and "alpha capability" in text


def test_a_capability_s_rules_md_out_of_step_fails(adopter: AdopterRepo) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    adopter.write({".pkit/capabilities/alpha/rules.md": "a hand edit\n"})
    (finding,) = kinds(adopter, Kind.LOADED_FILE_STALE)
    assert finding.location == ".pkit/capabilities/alpha/rules.md"
    assert "alpha:ALPHA" in finding.message


def test_a_preface_that_does_not_name_its_capability_fails(adopter: AdopterRepo) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA", preface="*Some rules.*"))
    (finding,) = kinds(adopter, Kind.LOADED_PREFACE)
    assert finding.location == ".pkit/capabilities/alpha/rule-sets/set.md"
    assert "does not name its capability, alpha" in finding.message


def test_a_capability_s_set_that_arrives_by_sync_is_not_judged_here(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    adopter.write(
        {
            ".pkit/capabilities/evidence/rule-sets/ev.md": loaded_set(
                "evidence", "EV", preface="*Some rules.*"
            ),
            ".pkit/capabilities/evidence/rules.md": "whatever arrived\n",
        }
    )
    assert kinds(adopter, Kind.LOADED_PREFACE) == []
    assert kinds(adopter, Kind.LOADED_FILE_STALE) == []


def test_a_second_loaded_set_of_a_capability_is_refused(adopter: AdopterRepo) -> None:
    folder = incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    (folder / "rule-sets" / "two.md").write_text(loaded_set("alpha", "BETA"), encoding="utf-8")
    (finding,) = kinds(adopter, Kind.SECOND_LOADED)
    assert finding.location.endswith("two.md")


def test_a_rules_md_with_no_loaded_set_behind_it_fails(adopter: AdopterRepo) -> None:
    folder = incubated(adopter, "alpha")
    (folder / "rules.md").write_text("left behind\n", encoding="utf-8")
    (finding,) = kinds(adopter, Kind.LOADED_FILE_ORPHANED)
    assert finding.location == ".pkit/capabilities/alpha/rules.md"
    assert "ships no loaded rule set" in finding.message


def test_a_left_behind_rules_md_of_a_capability_that_arrives_by_sync_is_not_judged(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    adopter.write({".pkit/capabilities/evidence/rules.md": "arrived\n"})
    assert kinds(adopter, Kind.LOADED_FILE_ORPHANED) == []


def test_the_shipped_capability_sets_name_their_capability_and_are_in_step() -> None:
    """project-management's `PM` and software-engineering's `SWE`, the first capability
    loaded sets, validate in the methodology's source, their files generated."""
    result = rs.validate_rule_sets(REPO)
    for path in (
        ".pkit/capabilities/project-management/rule-sets/pm.md",
        ".pkit/capabilities/software-engineering/rule-sets/swe.md",
    ):
        assert [f for f in result.findings if f.location.startswith(path)] == [], path
    for name, set_name in (("project-management", "PM"), ("software-engineering", "SWE")):
        (found,) = [s for s in result.discovery.rule_sets if s.name == set_name]
        assert found.loaded and found.component == name
        text = (REPO / lrs.capability_loaded_file(name)).read_text(encoding="utf-8")
        assert text == lrs.project(found)


# --- `pkit rule-sets loaded` (ADR-076 point 1) -------------------------------------------


def test_loaded_answers_every_layer_with_its_owner(adopter: AdopterRepo) -> None:
    incubated(adopter, "zeta", loaded_set("zeta", "ZETA"))
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    incubated(adopter, "plain")
    adopter.write({".pkit/rules/project.md": "*The project's own.*\n"})
    lrs.generate(adopter.root)
    answer = [(f.layer, f.owner, f.path, f.rule_set) for f in lr.loaded_files(adopter.root)]
    assert answer == [
        ("backbone", "backbone", ".pkit/rules/core.md", "backbone:OPS"),
        ("capability", "alpha", ".pkit/capabilities/alpha/rules.md", "alpha:ALPHA"),
        ("capability", "zeta", ".pkit/capabilities/zeta/rules.md", "zeta:ZETA"),
        ("project", "project", ".pkit/rules/project.md", None),
    ]


def test_loaded_gives_a_project_s_own_loaded_set(adopter: AdopterRepo) -> None:
    adopter.write(
        {
            "docs/rule-sets/own.md": loaded_set("project", "OWN").replace(
                "*The rules of the project capability", "*The project's rules"
            )
        }
    )
    (project,) = [f for f in lr.loaded_files(adopter.root) if f.layer == "project"]
    assert (project.path, project.rule_set) == (".pkit/rules/project.md", "OWN")


def test_an_unregistered_capability_s_set_is_left_out(adopter: AdopterRepo) -> None:
    folder = incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    lrs.generate(adopter.root)
    manifest = read_backbone_manifest(adopter.root)
    assert manifest is not None
    manifest.components = [c for c in manifest.components if c.name != "alpha"]
    write_backbone_manifest(adopter.root, manifest)
    assert (folder / "rules.md").is_file()
    assert [f.owner for f in lr.loaded_files(adopter.root)] == ["backbone"] + (
        ["project"] if (adopter.root / ".pkit/rules/project.md").is_file() else []
    )


def test_the_command_prints_the_list_the_json_and_the_index(adopter: AdopterRepo) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    lrs.generate(adopter.root)
    runner = CliRunner()
    human = runner.invoke(main, ["rule-sets", "loaded"])
    assert human.exit_code == 0, human.output
    assert ".pkit/capabilities/alpha/rules.md" in human.output
    as_json = runner.invoke(main, ["rule-sets", "loaded", "--json"])
    document = json.loads(as_json.output)
    assert [entry["owner"] for entry in document["loaded"]][:2] == ["backbone", "alpha"]
    index = runner.invoke(main, ["rule-sets", "loaded", "--index", "claude-code"])
    assert index.output == f"{lr.INDEX_MARKER}\n@../capabilities/alpha/rules.md\n"
    unknown = runner.invoke(main, ["rule-sets", "loaded", "--index", "nobody"])
    assert unknown.exit_code == 1


# --- the index (ADR-076 points 2 and 4) --------------------------------------------------


def test_the_index_lists_each_registered_capability_by_name(adopter: AdopterRepo) -> None:
    incubated(adopter, "zeta", loaded_set("zeta", "ZETA"))
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    generate_and_render(adopter)
    assert (adopter.root / INDEX).read_text(encoding="utf-8") == (
        f"{lr.INDEX_MARKER}\n@../capabilities/alpha/rules.md\n@../capabilities/zeta/rules.md\n"
    )


def test_install_renders_the_index_with_the_marker_alone(adopter: AdopterRepo) -> None:
    """First install renders the index; with no capability shipping a loaded set, it holds
    its marker alone, a comment the harness drops."""
    assert (adopter.root / INDEX).read_text(encoding="utf-8") == f"{lr.INDEX_MARKER}\n"
    assert lr.INDEX_MARKER.startswith("<!--") and lr.INDEX_MARKER.endswith("-->")


def test_with_no_declaring_adapter_the_index_holds_the_marker_alone() -> None:
    loaded = (
        lr.LoadedFile("capability", "alpha", ".pkit/capabilities/alpha/rules.md", "A", "s", True),
    )
    assert lr.render_index(loaded, lr.Deliveries((), ("other",))) == f"{lr.INDEX_MARKER}\n"


def test_differing_entry_forms_refuse_the_render() -> None:
    forms = (
        lr.DeliveryForm("one", "@{file}", "CLAUDE.md", "@{index}"),
        lr.DeliveryForm("two", "include {file}", "AGENTS.md", "include {index}"),
    )
    with pytest.raises(lr.DifferingForms) as raised:
        lr.render_index((), lr.Deliveries(forms, ()))
    assert "one (`@{file}`), two (`include {file}`)" in raised.value.message


def test_the_render_writes_only_where_the_index_differs(adopter: AdopterRepo) -> None:
    assert lr.write_index(adopter.root).split()[0] == "unchanged"
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    assert lr.write_index(adopter.root, dry_run=True).split()[:2] == ["would", "render"]
    assert lr.write_index(adopter.root).split()[0] == "rendered"


def test_uninstall_s_render_leaves_the_capability_out(adopter: AdopterRepo) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    generate_and_render(adopter)
    caps.uninstall_capability(adopter.root, "alpha", source_kit=adopter.source_kit)
    lr.write_index(adopter.root)
    assert (adopter.root / INDEX).read_text(encoding="utf-8") == f"{lr.INDEX_MARKER}\n"


def test_the_source_s_index_is_never_copied_into_a_project(adopter: AdopterRepo) -> None:
    """The ownership predicate answers the index as no synced copy, so the rules area's
    copy leaves the source's own out (ADR-076 point 2)."""
    ctx = install_mod.InstallContext(adopter.root, REPO / ".pkit", dry_run=False)
    install_mod._install_area(
        REPO / ".pkit" / "rules", adopter.root / ".pkit" / "rules", ctx, overwrite=True
    )
    assert (adopter.root / INDEX).read_text(encoding="utf-8") == f"{lr.INDEX_MARKER}\n"


# --- a file at the index's path that is no index -----------------------------------------


def test_a_file_without_the_marker_is_a_clash_and_never_written_over(
    adopter: AdopterRepo,
) -> None:
    adopter.write({INDEX: "# My own notes\n"})
    assert lr.index_clash(adopter.root) == adopter.root / INDEX
    assert lr.write_index(adopter.root).split()[0] == "refused"
    assert (adopter.root / INDEX).read_text(encoding="utf-8") == "# My own notes\n"
    with pytest.raises(click.ClickException) as raised:
        lr.refuse_index_clash(adopter.root, command="upgrade")
    assert "refusing to run `pkit upgrade`" in raised.value.message


def test_sync_stops_on_the_clash_before_it_writes(adopter: AdopterRepo) -> None:
    adopter.write({INDEX: "# My own notes\n"})
    (adopter.root / ".pkit/rules/core.md").write_text("an old copy\n", encoding="utf-8")
    with pytest.raises(click.ClickException) as raised:
        sync.run_sync(adopter.root)
    assert ".pkit/rules/capabilities.md" in raised.value.message
    assert (adopter.root / ".pkit/rules/core.md").read_text(encoding="utf-8") == "an old copy\n"


def test_an_empty_file_is_no_clash(adopter: AdopterRepo) -> None:
    adopter.write({INDEX: ""})
    assert lr.index_clash(adopter.root) is None


# --- the check (ADR-076 point 5) ---------------------------------------------------------


def test_a_delivery_in_step_passes_and_says_what_it_holds(adopter: AdopterRepo) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    generate_and_render(adopter)
    host_with_line(adopter)
    delivery = lr.check_delivery(adopter.root)
    assert delivery.findings == ()
    assert delivery.summary == (
        f"capabilities' rules index {INDEX}: 1 capability file(s) (alpha), reached from "
        "CLAUDE.md (claude-code).",
    )


def test_an_index_out_of_step_fails(adopter: AdopterRepo) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    lrs.generate(adopter.root)
    host_with_line(adopter)
    ((location, severity, message),) = delivery_findings(adopter)
    assert (location, severity) == (INDEX, "error")
    assert "it lacks '@../capabilities/alpha/rules.md'" in message
    assert "`pkit sync`" in message
    (finding,) = lr.check_delivery(adopter.root).findings
    assert finding.label == UNDELIVERED


def test_an_entry_for_no_registered_capability_fails(adopter: AdopterRepo) -> None:
    host_with_line(adopter)
    adopter.write({INDEX: f"{lr.INDEX_MARKER}\n@../capabilities/gone/rules.md\n"})
    ((_location, _severity, message),) = delivery_findings(adopter)
    assert "for no registered capability's loaded set" in message


def test_an_entry_whose_file_is_missing_fails(adopter: AdopterRepo) -> None:
    folder = incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    generate_and_render(adopter)
    host_with_line(adopter)
    (folder / "rules.md").unlink()
    messages = [message for _l, _s, message in delivery_findings(adopter)]
    assert any(
        "names .pkit/capabilities/alpha/rules.md, which this checkout" in m for m in messages
    )


def test_line_endings_alone_are_no_difference(adopter: AdopterRepo) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    generate_and_render(adopter)
    host_with_line(adopter)
    path = adopter.root / INDEX
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert delivery_findings(adopter) == []


def test_a_host_without_the_line_fails(adopter: AdopterRepo) -> None:
    adopter.write({"CLAUDE.md": "# Host\n\n@.pkit/rules/core.md\n"})
    ((location, severity, message),) = delivery_findings(adopter)
    assert (location, severity) == ("CLAUDE.md", "error")
    assert "does not hold the line `@.pkit/rules/capabilities.md`" in message
    assert "The next `pkit sync` inserts it." in message


def test_a_host_whose_core_include_sits_in_code_says_the_project_mends_it(
    adopter: AdopterRepo,
) -> None:
    adopter.write({"CLAUDE.md": "# Host\n\n```\n@.pkit/rules/core.md\n```\n"})
    ((_location, _severity, message),) = delivery_findings(adopter)
    assert "move the include out of the code" in message


def test_a_host_the_checkout_does_not_hold_is_a_summary_line(adopter: AdopterRepo) -> None:
    delivery = lr.check_delivery(adopter.root)
    assert delivery.findings == ()
    assert delivery.summary[1].startswith("CLAUDE.md is not in this checkout")


def test_an_index_the_checkout_does_not_hold_is_a_summary_line(adopter: AdopterRepo) -> None:
    (adopter.root / INDEX).unlink()
    adopter.write({"CLAUDE.md": "# Host\n"})
    delivery = lr.check_delivery(adopter.root)
    assert delivery.findings == ()
    assert delivery.summary[0].startswith("no capabilities' rules index here")


def test_an_adapter_without_the_key_is_one_warning(adopter: AdopterRepo) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    register_adapter(adopter, "other", ADAPTER.format(name="other", key=""))
    generate_and_render(adopter)
    host_with_line(adopter)
    ((location, severity, message),) = delivery_findings(adopter)
    assert (location, severity) == (".pkit/adapters/other/package.yaml", "warning")
    assert "declares no `loaded_rules:`" in message and "alpha" in message


def test_with_no_declaring_adapter_the_index_is_compared_with_the_marker(
    adopter: AdopterRepo,
) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    package = adopter.root / ".pkit/adapters/claude-code/package.yaml"
    text = package.read_text(encoding="utf-8")
    start = text.index("loaded_rules:")
    end = text.index("\n# The agent runner")
    package.write_text(text[:start] + text[end + 1 :], encoding="utf-8")
    generate_and_render(adopter)
    assert (adopter.root / INDEX).read_text(encoding="utf-8") == f"{lr.INDEX_MARKER}\n"
    assert [severity for _l, severity, _m in delivery_findings(adopter)] == ["warning"]


def test_differing_entry_forms_fail(adopter: AdopterRepo) -> None:
    key = 'loaded_rules:\n  entry: "include {file}"\n  host: AGENTS.md\n  line: "include {index}"\n'
    register_adapter(adopter, "other", ADAPTER.format(name="other", key=key))
    host_with_line(adopter)
    ((_location, severity, message),) = delivery_findings(adopter)
    assert severity == "error"
    assert "claude-code (`@{file}`), other (`include {file}`)" in message


def test_validate_s_rule_sets_member_carries_the_delivery(adopter: AdopterRepo) -> None:
    adopter.write({"CLAUDE.md": "# Host\n\n@.pkit/rules/core.md\n"})
    outcome = rs.outcome(adopter.root)
    assert any(line.startswith("capabilities' rules index") for line in outcome.summary)
    assert [f.label for f in outcome.errors] == [UNDELIVERED]


# --- an import token in a loaded set (ADR-076 point 1) -----------------------------------


def test_an_import_token_outside_code_is_refused(adopter: AdopterRepo) -> None:
    text = loaded_set("alpha", "ALPHA").replace("The statement.", "Ask @someone first.")
    incubated(adopter, "alpha", text)
    (finding,) = kinds(adopter, Kind.LOADED_IMPORT_TOKEN)
    assert "'@someone'" in finding.message


@pytest.mark.parametrize(
    "written",
    ["Read `@.pkit/rules/core.md` first.", "Write to name@example.com.", "<!-- @hidden -->"],
)
def test_code_an_address_and_a_comment_are_no_import_token(
    adopter: AdopterRepo, written: str
) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA").replace("The statement.", written))
    assert kinds(adopter, Kind.LOADED_IMPORT_TOKEN) == []


def test_with_no_declared_prefix_nothing_is_refused(adopter: AdopterRepo) -> None:
    text = loaded_set("alpha", "ALPHA").replace("The statement.", "Ask @someone first.")
    incubated(adopter, "alpha", text)
    package = adopter.root / ".pkit/adapters/claude-code/package.yaml"
    package.write_text(
        package.read_text(encoding="utf-8").replace("loaded_rules:", "unrelated_rules:"),
        encoding="utf-8",
    )
    assert kinds(adopter, Kind.LOADED_IMPORT_TOKEN) == []


def test_core_s_set_holds_no_import_token() -> None:
    assert [
        f for f in rs.validate_rule_sets(REPO).findings if f.kind is Kind.LOADED_IMPORT_TOKEN
    ] == []


# --- the citation form (COR-070 point 1; ADR-076 point 1) --------------------------------


def test_a_capability_s_rule_is_cited_with_its_capability(adopter: AdopterRepo) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    adopter.write(
        {"notes.md": "Keep alpha:RS-ALPHA-001, and mind alpha:RS-ALPHA-009 and RS-ALPHA-001.\n"}
    )
    unheld = [u for u in refs.unheld_operational_rules(adopter.root) if u.path == "notes.md"]
    assert [u.citation.text for u in unheld] == ["alpha:RS-ALPHA-009"]
    assert "does not resolve" in unheld[0].message


def test_a_capability_s_retired_rule_cited_is_a_warning(adopter: AdopterRepo) -> None:
    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA", status="withdrawn"))
    adopter.write({"notes.md": "Keep alpha:RS-ALPHA-001.\n"})
    (unheld,) = [u for u in refs.unheld_operational_rules(adopter.root) if u.path == "notes.md"]
    assert "withdrawn" in unheld.message


# --- what a step newly binds (ADR-076 point 6) -------------------------------------------


def test_compare_names_what_binds_changes_and_retires() -> None:
    before = lr.SetReading("x:X", "x", "1.0.0", {"A": ("a", "one"), "B": ("b", "two")})
    after = lr.SetReading("x:X", "x", "1.1.0", {"A": ("a", "one, edited"), "C": ("c", "three")})
    bound = lr.compare(before, after)
    assert (bound.binds, bound.changes, bound.retires) == (
        (("C", "c"),),
        (("A", "a"),),
        (("B", "b"),),
    )
    assert (bound.before, bound.after, bound.first) == ("1.0.0", "1.1.0", False)


def test_a_first_install_lists_every_accepted_ops_rule() -> None:
    (bound,) = lr.bound_by({}, [("backbone", REPO / ".pkit")])
    (ops,) = [s for s in rs.discover_rule_sets(REPO).rule_sets if s.name == "OPS"]
    accepted = [rule.id for rule in ops.rules if rule.binds]
    assert bound.first and [rule_id for rule_id, _t in bound.binds] == accepted
    rendered = lr.render_bound([bound], capabilities_delivered=True)
    assert "backbone:OPS" in rendered and "(first delivered)" in rendered
    assert "binds    RS-OPS-001  The no-shared-files invariant" in rendered


def test_sync_says_what_it_newly_binds_of_core_s_set(
    adopter: AdopterRepo, capsys: pytest.CaptureFixture[str]
) -> None:
    ops = adopter.root / ".pkit/rule-sets/ops.md"
    ops.write_text(
        ops.read_text(encoding="utf-8").replace(
            "  RS-OPS-002:\n    status: accepted", "  RS-OPS-002:\n    status: proposed"
        ),
        encoding="utf-8",
    )
    sync.run_sync(adopter.root)
    out = capsys.readouterr().out
    assert "Loaded rules — what this step newly binds" in out
    assert "binds    RS-OPS-002  The acceptance gate" in out


def test_a_capability_s_set_newly_bound_and_where_no_adapter_delivers(
    adopter: AdopterRepo,
) -> None:
    folder = incubated(adopter, "alpha", loaded_set("alpha", "ALPHA", status="proposed"))
    before = lr.read_component("alpha", folder)
    (folder / "rule-sets" / "set.md").write_text(loaded_set("alpha", "ALPHA"), encoding="utf-8")
    (bound,) = lr.bound_by({"alpha": before}, [("alpha", folder)])
    assert [rule_id for rule_id, _t in bound.binds] == ["RS-ALPHA-001"]
    delivered = lr.render_bound([bound], capabilities_delivered=True)
    assert "binds    RS-ALPHA-001  One rule" in delivered
    nowhere = lr.render_bound([bound], capabilities_delivered=False)
    assert "its rules bind no session in this project" in nowhere
    assert "RS-ALPHA-001" not in nowhere


def test_a_step_that_changes_no_rule_says_so() -> None:
    reading = lr.SetReading("x:X", "x", "1.0.0", {"A": ("a", "one")})
    rendered = lr.render_bound([lr.compare(reading, reading)], capabilities_delivered=True)
    assert "no rule newly binds, changes or retires" in rendered


# --- `pkit status` ------------------------------------------------------------------------


def test_status_reports_the_index_and_its_capabilities(
    adopter: AdopterRepo, capsys: pytest.CaptureFixture[str]
) -> None:
    from project_kit import status

    incubated(adopter, "alpha", loaded_set("alpha", "ALPHA"))
    generate_and_render(adopter)
    status._report_claude_adapter(adopter.root)
    out = capsys.readouterr().out
    assert "rules index        .pkit/rules/capabilities.md, including 1 capability file(s):" in out
    assert "alpha" in out
