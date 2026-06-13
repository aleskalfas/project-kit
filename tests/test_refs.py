"""Tests for the reference-graph and hook-registry surface (per COR-013 / #74)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import refs
from project_kit.cli import main


# --- fixtures -------------------------------------------------------


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimal tree: `.pkit/agents/{core,project}/`, `.pkit/skills/{core,project}/`, `.pkit/decisions/{core,project}/`."""
    for area in ("agents", "skills", "decisions"):
        for ns in ("core", "project"):
            (tmp_path / ".pkit" / area / ns).mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write_agent(root: Path, namespace: str, name: str, body: str) -> Path:
    target = root / ".pkit" / "agents" / namespace / f"{name}.md"
    target.write_text(body, encoding="utf-8")
    return target


def _write_skill(root: Path, namespace: str, name: str, body: str) -> Path:
    target = root / ".pkit" / "skills" / namespace / f"{name}.md"
    target.write_text(body, encoding="utf-8")
    return target


def _write_decision(root: Path, namespace: str, prefix: str, num: str, slug: str) -> Path:
    target = root / ".pkit" / "decisions" / namespace / f"{prefix}-{num}-{slug}.md"
    target.write_text(
        f"---\nid: {prefix}-{num}\ntitle: Test\nstatus: accepted\ndate: 2026-01-01\nauthor: t\n---\n",
        encoding="utf-8",
    )
    return target


# --- body parser ----------------------------------------------------


def test_parser_extracts_backticked_paths() -> None:
    body = "See `.pkit/decisions/README.md` for details."
    refs_ = refs.extract_body_refs(body)
    assert ".pkit/decisions/README.md" in refs_.paths


def test_parser_extracts_markdown_link_targets() -> None:
    body = "Read [the spec](.pkit/agents/README.md) first."
    refs_ = refs.extract_body_refs(body)
    assert ".pkit/agents/README.md" in refs_.paths


def test_parser_skips_url_link_targets() -> None:
    body = "Visit [docs](https://example.com/docs) and [internal](.pkit/foo.md)."
    refs_ = refs.extract_body_refs(body)
    assert "https://example.com/docs" not in refs_.paths
    assert ".pkit/foo.md" in refs_.paths


def test_parser_extracts_record_ids_as_bare_tokens() -> None:
    body = "Per COR-005 and PRJ-002, this rule applies."
    refs_ = refs.extract_body_refs(body)
    assert "COR-005" in refs_.records
    assert "PRJ-002" in refs_.records


def test_parser_extracts_hook_names() -> None:
    body = "This agent calls `workflow.promote-issue` and `workflow.github.create-pr`."
    refs_ = refs.extract_body_refs(body)
    assert "workflow.promote-issue" in refs_.hooks
    assert "workflow.github.create-pr" in refs_.hooks


def test_parser_skips_fenced_code_blocks() -> None:
    body = "Outside text references COR-005.\n\n```yaml\nreads:\n  records: [COR-999]\n```\n\nMore text."
    refs_ = refs.extract_body_refs(body)
    assert "COR-005" in refs_.records
    assert "COR-999" not in refs_.records, "fenced code block leaked through"


def test_parser_skips_html_comments() -> None:
    body = "Real text refs COR-005. <!-- ignored COR-999 mentioned here --> end."
    refs_ = refs.extract_body_refs(body)
    assert "COR-005" in refs_.records
    assert "COR-999" not in refs_.records


def test_parser_skips_strikethrough() -> None:
    body = "Keep COR-005. ~~Old reference to COR-999 dropped.~~"
    refs_ = refs.extract_body_refs(body)
    assert "COR-005" in refs_.records
    assert "COR-999" not in refs_.records


def test_parser_skips_template_placeholders_in_paths() -> None:
    """Illustrative paths like `.pkit/agents/<name>.md` must not be flagged as literal refs."""
    body = "Stamp at `.pkit/agents/<name>.md` and walk `.pkit/skills/...`."
    refs_ = refs.extract_body_refs(body)
    assert all("<" not in p and "..." not in p for p in refs_.paths)


def test_parser_does_not_flag_yaml_field_paths_as_hooks() -> None:
    """`reads.records` looks hook-shaped but is a YAML schema field path."""
    body = "Declare references under the `reads.records` field of the frontmatter."
    refs_ = refs.extract_body_refs(body)
    assert "reads.records" not in refs_.hooks


def test_parser_does_not_flag_command_examples_as_paths() -> None:
    """Backticked command examples like `pkit init` aren't paths."""
    body = "Run `pkit init` first, then `pkit sync`."
    refs_ = refs.extract_body_refs(body)
    assert "pkit init" not in refs_.paths
    assert "pkit sync" not in refs_.paths


# --- declared (frontmatter) loader ----------------------------------


def test_declared_reads_typed_buckets() -> None:
    fm = {
        "reads": {
            "paths": [".pkit/foo.md"],
            "records": ["COR-001"],
            "patterns": ["code-paths"],
        },
        "owns": ["src/foo/"],
        "needs": ["workflow.do-thing"],
        "answers": ["workflow.answer-that"],
        "gates": ["COR-002"],
    }
    declared = refs.extract_declared(fm)
    assert declared.reads_paths == frozenset({".pkit/foo.md"})
    assert declared.reads_records == frozenset({"COR-001"})
    assert declared.reads_patterns == frozenset({"code-paths"})
    assert declared.owns == frozenset({"src/foo/"})
    assert declared.needs == frozenset({"workflow.do-thing"})
    assert declared.answers == frozenset({"workflow.answer-that"})
    assert declared.gates == frozenset({"COR-002"})


def test_declared_handles_missing_buckets() -> None:
    declared = refs.extract_declared({})
    assert declared.reads_paths == frozenset()
    assert declared.gates == frozenset()


# --- corpus loader --------------------------------------------------


def test_load_artifacts_discovers_agents_and_skills(kit_target: Path) -> None:
    _write_agent(kit_target, "core", "agent-a", "---\nname: agent-a\n---\n# A\n")
    _write_skill(kit_target, "project", "skill-b", "---\nname: skill-b\n---\n# B\n")

    artifacts = refs.load_artifacts(kit_target)
    kinds = {(a.kind, a.namespace, a.name) for a in artifacts}
    assert ("agent", "core", "agent-a") in kinds
    assert ("skill", "project", "skill-b") in kinds


def test_load_artifacts_handles_both_flat_and_folder_layouts(kit_target: Path) -> None:
    # Flat
    _write_agent(kit_target, "core", "flat-agent", "---\nname: flat-agent\n---\n# F\n")
    # Folder form
    folder = kit_target / ".pkit" / "agents" / "core" / "folder-agent"
    folder.mkdir()
    (folder / "folder-agent.md").write_text("---\nname: folder-agent\n---\n# F\n", encoding="utf-8")

    artifacts = refs.load_artifacts(kit_target)
    names = {a.name for a in artifacts}
    assert "flat-agent" in names
    assert "folder-agent" in names


# --- capabilities (per COR-017) -------------------------------------


def test_load_artifacts_discovers_capability_skills_and_agents(kit_target: Path) -> None:
    """Skills + agents under an installed capability subtree are loaded and tagged."""
    cap_skills = kit_target / ".pkit" / "capabilities" / "evidence" / "skills"
    cap_skills.mkdir(parents=True)
    (cap_skills / "evidence-citer.md").write_text(
        "---\nname: evidence-citer\n---\n# Evidence citer\n", encoding="utf-8"
    )
    cap_agents = kit_target / ".pkit" / "capabilities" / "evidence" / "agents"
    cap_agents.mkdir(parents=True)
    (cap_agents / "evidence-reviewer.md").write_text(
        "---\nname: evidence-reviewer\n---\n# Reviewer\n", encoding="utf-8"
    )

    artifacts = refs.load_artifacts(kit_target)
    by_name = {a.name: a for a in artifacts}
    assert "evidence-citer" in by_name
    assert by_name["evidence-citer"].capability == "evidence"
    assert "evidence-reviewer" in by_name
    assert by_name["evidence-reviewer"].capability == "evidence"


def test_composes_field_parsed_from_frontmatter(kit_target: Path) -> None:
    """A composite skill's `composes:` list is extracted into declared.composes."""
    family = kit_target / ".pkit" / "skills" / "core" / "composite"
    family.mkdir(parents=True)
    (family / "composite.md").write_text(
        "---\nname: composite\ncomposes:\n  - op-a.md\n  - op-b.md\n---\n# Composite\n",
        encoding="utf-8",
    )
    (family / "op-a.md").write_text("# A\n", encoding="utf-8")
    (family / "op-b.md").write_text("# B\n", encoding="utf-8")
    artifacts = refs.load_artifacts(kit_target)
    c = next((a for a in artifacts if a.name == "composite"), None)
    assert c is not None
    assert c.declared.composes == frozenset({"op-a.md", "op-b.md"})


def test_validate_corpus_clean_when_composes_paths_exist(kit_target: Path) -> None:
    family = kit_target / ".pkit" / "skills" / "core" / "composite"
    family.mkdir(parents=True)
    (family / "composite.md").write_text(
        "---\nname: composite\ncomposes:\n  - op-a.md\n  - scripts/helper.py\n---\n# Composite\n",
        encoding="utf-8",
    )
    (family / "op-a.md").write_text("# A\n", encoding="utf-8")
    (family / "scripts").mkdir()
    (family / "scripts" / "helper.py").write_text("# script\n", encoding="utf-8")
    issues = refs.validate_corpus(kit_target)
    composes_issues = [i for i in issues if "composes" in i.diagnosis]
    assert composes_issues == []


def test_validate_corpus_flags_missing_composes_entry(kit_target: Path) -> None:
    family = kit_target / ".pkit" / "skills" / "core" / "composite"
    family.mkdir(parents=True)
    (family / "composite.md").write_text(
        "---\nname: composite\ncomposes:\n  - op-a.md\n  - op-missing.md\n---\n# Composite\n",
        encoding="utf-8",
    )
    (family / "op-a.md").write_text("# A\n", encoding="utf-8")
    issues = refs.validate_corpus(kit_target)
    msgs = [i.diagnosis for i in issues]
    assert any("op-missing.md" in m and "not found" in m for m in msgs), msgs
    assert not any("op-a.md" in m and "not found" in m for m in msgs), msgs


def test_validate_corpus_flags_composes_on_flat_skill(kit_target: Path) -> None:
    """A flat skill can't declare composes — only folder-form composites can."""
    _write_skill(
        kit_target,
        "core",
        "flat-with-composes",
        "---\nname: flat-with-composes\ncomposes:\n  - op-a.md\n---\n# Flat\n",
    )
    issues = refs.validate_corpus(kit_target)
    msgs = [i.diagnosis for i in issues]
    assert any("flat-form" in m and "composes" in m for m in msgs), msgs


def test_load_artifacts_composite_skill_unions_sibling_body_refs(kit_target: Path) -> None:
    """For composite skills (COR-020), sub-procedure file bodies contribute to body_refs."""
    family_dir = kit_target / ".pkit" / "skills" / "core" / "schema"
    family_dir.mkdir(parents=True)
    # Dispatcher cites COR-018 in body.
    (family_dir / "schema.md").write_text(
        "---\nname: schema\n---\n# Working with schemas\n\nPer COR-018, schemas...\n",
        encoding="utf-8",
    )
    # Sub-procedure author.md cites COR-019.
    (family_dir / "author.md").write_text(
        "# Author\n\nPer COR-019, references use typed tokens.\n",
        encoding="utf-8",
    )
    # Sub-procedure extend.md cites a path.
    (family_dir / "extend.md").write_text(
        "# Extend\n\nSee `.pkit/schemas/README.md` for the mechanism.\n",
        encoding="utf-8",
    )

    artifacts = refs.load_artifacts(kit_target)
    schema = next((a for a in artifacts if a.name == "schema"), None)
    assert schema is not None
    # Records from BOTH the dispatcher and sub-procedure files appear.
    assert "COR-018" in schema.body_refs.records
    assert "COR-019" in schema.body_refs.records
    # Paths from sub-procedure files also appear.
    assert ".pkit/schemas/README.md" in schema.body_refs.paths


def test_load_artifacts_capability_supports_folder_form(kit_target: Path) -> None:
    """Folder-form artifacts under a capability are picked up just like area folder-form."""
    folder = kit_target / ".pkit" / "capabilities" / "product" / "agents" / "pm-agent"
    folder.mkdir(parents=True)
    (folder / "pm-agent.md").write_text("---\nname: pm-agent\n---\n# PM\n", encoding="utf-8")

    artifacts = refs.load_artifacts(kit_target)
    pm = next((a for a in artifacts if a.name == "pm-agent"), None)
    assert pm is not None
    assert pm.capability == "product"


def test_load_artifacts_no_capabilities_dir_is_fine(kit_target: Path) -> None:
    """Absence of `.pkit/capabilities/` is not an error — just yields no capability artifacts."""
    _write_agent(kit_target, "core", "lone", "---\nname: lone\n---\n# X\n")
    artifacts = refs.load_artifacts(kit_target)
    assert all(a.capability is None for a in artifacts)


def test_parser_extracts_capability_citation() -> None:
    body = "Per [evidence:DEC-001-citation-discipline] every claim must cite a source."
    body_refs = refs.extract_body_refs(body)
    assert ("evidence", "DEC-001-citation-discipline") in body_refs.capability_citations


def test_parser_extracts_multiple_capability_citations() -> None:
    body = "See [evidence:DEC-001] and [product:DEC-002-prioritisation] for context."
    body_refs = refs.extract_body_refs(body)
    assert ("evidence", "DEC-001") in body_refs.capability_citations
    assert ("product", "DEC-002-prioritisation") in body_refs.capability_citations


def test_parser_skips_capability_citations_in_fenced_blocks() -> None:
    body = "Outside [real:DEC-001-foo].\n\n```\n[fake:DEC-999-bar]\n```\n"
    body_refs = refs.extract_body_refs(body)
    assert ("real", "DEC-001-foo") in body_refs.capability_citations
    assert ("fake", "DEC-999-bar") not in body_refs.capability_citations


def test_validate_capability_citation_resolves_to_installed_decision(kit_target: Path) -> None:
    """A cited capability decision that exists on disk produces no issue."""
    # Stage the capability with a decision file.
    cap_decisions = kit_target / ".pkit" / "capabilities" / "evidence" / "decisions"
    cap_decisions.mkdir(parents=True)
    (cap_decisions / "DEC-001-citation-discipline.md").write_text(
        "---\nid: DEC-001\nstatus: accepted\n---\n# Cite\n", encoding="utf-8"
    )
    body = """---
name: skill-a
description: t
---
# Skill
See [evidence:DEC-001-citation-discipline] for the rule.
"""
    _write_skill(kit_target, "core", "skill-a", body)

    issues = refs.validate_corpus(kit_target)
    citation_issues = [
        i for i in issues if "evidence:DEC-001-citation-discipline" in i.diagnosis
    ]
    assert citation_issues == []


def test_validate_capability_citation_to_missing_decision_fires_issue(
    kit_target: Path,
) -> None:
    """A capability citation that doesn't resolve to a file is flagged."""
    body = """---
name: skill-a
description: t
---
# Skill
We rely on [evidence:DEC-001-citation-discipline] here.
"""
    _write_skill(kit_target, "core", "skill-a", body)

    issues = refs.validate_corpus(kit_target)
    diagnostics = [i.diagnosis for i in issues]
    assert any(
        "evidence:DEC-001-citation-discipline" in d
        and "no file at .pkit/capabilities/evidence/decisions/" in d
        for d in diagnostics
    ), f"expected unresolved capability citation issue; got: {diagnostics}"


# --- validation -----------------------------------------------------


def test_validate_passes_when_declared_matches_body(kit_target: Path) -> None:
    _write_decision(kit_target, "core", "COR", "001", "a-thing")
    body = """---
name: skill-a
description: test
gates: [COR-001]
reads:
  records: [COR-001]
---
# Skill
Per COR-001 this is fine.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    issues = refs.validate_corpus(kit_target)
    assert issues == [], f"clean corpus produced issues: {issues}"


def test_validate_flags_forward_drift_record_in_frontmatter_not_in_body(kit_target: Path) -> None:
    body = """---
name: skill-a
description: test
reads:
  records: [COR-005]
---
# Skill
Body never mentions the record.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    issues = refs.validate_corpus(kit_target)
    assert any("frontmatter declares record 'COR-005'" in i.diagnosis for i in issues)


def test_validate_flags_backward_drift_record_in_body_not_declared(kit_target: Path) -> None:
    body = """---
name: skill-a
description: test
---
# Skill
Mentions COR-999 without declaring it.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    issues = refs.validate_corpus(kit_target)
    assert any("body cites record 'COR-999'" in i.diagnosis for i in issues)


def test_validate_flags_hook_closure_violation(kit_target: Path) -> None:
    """Agent needs a hook no provider answers/provides."""
    body = """---
name: agent-a
description: test
needs: [workflow.unknown]
---
# A
Calls workflow.unknown to do things.
"""
    _write_agent(kit_target, "project", "agent-a", body)
    issues = refs.validate_corpus(kit_target)
    assert any("no provider exists" in i.diagnosis for i in issues)


def test_validate_passes_when_hook_provider_exists(kit_target: Path) -> None:
    skill_body = """---
name: provider-skill
description: provides
answers: [workflow.do-thing]
---
# Provider
Implements workflow.do-thing.
"""
    agent_body = """---
name: consumer-agent
description: consumes
needs: [workflow.do-thing]
---
# Consumer
Calls workflow.do-thing.
"""
    _write_skill(kit_target, "core", "provider-skill", skill_body)
    _write_agent(kit_target, "project", "consumer-agent", agent_body)
    issues = refs.validate_corpus(kit_target)
    # Should have no hook-closure issue; only forward/backward bidirectional
    # which are clean here.
    assert not any("no provider exists" in i.diagnosis for i in issues)


# --- lookups --------------------------------------------------------


def test_resolve_record_returns_file_path(kit_target: Path) -> None:
    target = _write_decision(kit_target, "core", "COR", "005", "bundle-pattern")
    found = refs.resolve_record(kit_target, "COR-005")
    assert found == target


def test_resolve_record_returns_none_for_missing(kit_target: Path) -> None:
    assert refs.resolve_record(kit_target, "COR-999") is None


def test_resolve_record_rejects_malformed_id(kit_target: Path) -> None:
    assert refs.resolve_record(kit_target, "not-a-record") is None


def test_resolve_hook_picks_project_over_core(kit_target: Path) -> None:
    providers = [
        refs.Provider(hook="x.y", tier="core", source="core-skill", implementation="/core-skill"),
        refs.Provider(hook="x.y", tier="project", source="proj-skill", implementation="/proj-skill"),
    ]
    winner = refs.resolve_hook(providers, "x.y")
    assert winner is not None
    assert winner.tier == "project"


def test_who_references_finds_declared_and_body_mentions(kit_target: Path) -> None:
    _write_decision(kit_target, "core", "COR", "005", "test")
    body = """---
name: skill-a
description: test
gates: [COR-005]
reads:
  records: [COR-005]
---
# A
Per COR-005 this matters.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    artifacts = refs.load_artifacts(kit_target)
    matches = refs.who_references(artifacts, "COR-005")
    assert len(matches) == 1
    assert matches[0].name == "skill-a"


# --- CLI wiring -----------------------------------------------------


def test_cli_refs_validate_reports_clean_on_empty_corpus(kit_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["refs", "validate"])
    assert result.exit_code == 0
    assert "All checks passed." in result.output


def test_cli_refs_lookup_returns_record_path(kit_target: Path) -> None:
    _write_decision(kit_target, "core", "COR", "001", "thing")
    runner = CliRunner()
    result = runner.invoke(main, ["refs", "lookup", "COR-001"])
    assert result.exit_code == 0
    assert ".pkit/decisions/core/COR-001-thing.md" in result.output


def test_cli_refs_lookup_errors_on_missing_record(kit_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["refs", "lookup", "COR-999"])
    assert result.exit_code != 0
    assert "no record matches" in result.output


def test_cli_hooks_list_shows_winning_provider(kit_target: Path) -> None:
    skill_body = """---
name: provider
description: provides
answers: [workflow.do-thing]
---
# P
Implements workflow.do-thing.
"""
    _write_skill(kit_target, "core", "provider", skill_body)
    runner = CliRunner()
    result = runner.invoke(main, ["hooks", "list"])
    assert result.exit_code == 0
    assert "workflow.do-thing" in result.output
    assert "core:provider" in result.output


def test_cli_hooks_resolve_returns_provider(kit_target: Path) -> None:
    skill_body = """---
name: provider
description: provides
answers: [workflow.do-thing]
---
# P
Implements workflow.do-thing.
"""
    _write_skill(kit_target, "core", "provider", skill_body)
    runner = CliRunner()
    result = runner.invoke(main, ["hooks", "resolve", "workflow.do-thing"])
    assert result.exit_code == 0
    assert "core:provider" in result.output


# --- storyboard queries (show / who-references / graph) -------------


def _agent_with_storyboard(root: Path, name: str, sb_path: str) -> Path:
    sb_file = root / sb_path
    sb_file.parent.mkdir(parents=True, exist_ok=True)
    sb_file.write_text("# Storyboard\n", encoding="utf-8")
    agent_path = root / ".pkit" / "agents" / "project" / f"{name}.md"
    agent_path.parent.mkdir(parents=True, exist_ok=True)
    agent_path.write_text(
        f"---\nname: {name}\ndescription: test\ntools: [Read]\nstoryboards:\n  - {sb_path}\n---\n# A\nLoad `{sb_path}` at session start.\n",
        encoding="utf-8",
    )
    return agent_path


def test_outgoing_refs_includes_storyboards_bucket(kit_target: Path) -> None:
    """`pkit refs show` displays a `storyboards` bucket when declared."""
    _agent_with_storyboard(kit_target, "a", ".pkit/agents/project/a-storyboards/storyboard.md")
    artifacts = refs.load_artifacts(kit_target)
    art = next(a for a in artifacts if a.name == "a")
    buckets = refs.outgoing_refs(art)
    assert "storyboards" in buckets
    assert ".pkit/agents/project/a-storyboards/storyboard.md" in buckets["storyboards"]


def test_who_references_finds_storyboard_path(kit_target: Path) -> None:
    """`pkit refs who-references <storyboard>` finds the owning agent."""
    sb_path = ".pkit/agents/project/r-storyboards/storyboard.md"
    _agent_with_storyboard(kit_target, "r", sb_path)
    artifacts = refs.load_artifacts(kit_target)
    matches = refs.who_references(artifacts, sb_path)
    assert len(matches) == 1
    assert matches[0].name == "r"


def test_graph_dot_emits_storyboard_edges(kit_target: Path) -> None:
    """The DOT graph carries a labeled edge for each `storyboards:` entry."""
    sb_path = ".pkit/agents/project/g-storyboards/storyboard.md"
    _agent_with_storyboard(kit_target, "g", sb_path)
    artifacts = refs.load_artifacts(kit_target)
    dot = refs.emit_graph_dot(artifacts)
    assert "storyboards" in dot
    assert f'-> "{sb_path}"' in dot


# --- storyboard validation (COR-016) --------------------------------


def test_validate_storyboards_passes_when_declared_path_exists_and_body_cites(
    kit_target: Path,
) -> None:
    """Happy path: storyboard declared, file exists, body cites it, Read in tools."""
    storyboard = kit_target / ".pkit" / "agents" / "project" / "a" / "storyboard.md"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(
        "---\nconsumers:\n  - kind: agent\n    name: a\n    namespace: project\n---\n\n# Storyboard\n",
        encoding="utf-8",
    )

    agent_body = """---
name: a
description: test
tools: [Read, Edit]
storyboards:
  - .pkit/agents/project/a/storyboard.md
---
# A
Load `.pkit/agents/project/a/storyboard.md` at session start.
"""
    agent_path = kit_target / ".pkit" / "agents" / "project" / "a" / "a.md"
    agent_path.write_text(agent_body, encoding="utf-8")

    issues = refs.validate_corpus(kit_target)
    assert all("storyboard" not in i.diagnosis for i in issues), (
        f"unexpected storyboard issues on clean fixture: {issues}"
    )


def test_validate_storyboards_flags_missing_file(kit_target: Path) -> None:
    """Declared storyboard path that doesn't resolve on disk gets flagged."""
    agent_path = kit_target / ".pkit" / "agents" / "project" / "a.md"
    agent_path.write_text(
        """---
name: a
description: test
tools: [Read]
storyboards:
  - .pkit/agents/project/a/missing.md
---
# A
Body cites `.pkit/agents/project/a/missing.md`.
""",
        encoding="utf-8",
    )

    issues = refs.validate_corpus(kit_target)
    assert any("file does not exist" in i.diagnosis for i in issues)


def test_validate_storyboards_flags_body_not_citing(kit_target: Path) -> None:
    """A declared storyboard whose path doesn't appear in body is a load-bearing-ref violation."""
    storyboard = kit_target / ".pkit" / "agents" / "project" / "a" / "storyboard.md"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text("# Storyboard\n", encoding="utf-8")

    agent_path = kit_target / ".pkit" / "agents" / "project" / "a" / "a.md"
    agent_path.write_text(
        """---
name: a
description: test
tools: [Read]
storyboards:
  - .pkit/agents/project/a/storyboard.md
---
# A
Body never mentions the storyboard path.
""",
        encoding="utf-8",
    )

    issues = refs.validate_corpus(kit_target)
    assert any("body does not cite" in i.diagnosis for i in issues)


def test_validate_storyboards_flags_missing_read_tool(kit_target: Path) -> None:
    """Declaring storyboards without Read in tools is a violation — runtime can't load them."""
    storyboard = kit_target / ".pkit" / "agents" / "project" / "a" / "storyboard.md"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text("# Storyboard\n", encoding="utf-8")

    agent_path = kit_target / ".pkit" / "agents" / "project" / "a" / "a.md"
    agent_path.write_text(
        """---
name: a
description: test
tools: [Edit, Bash]
storyboards:
  - .pkit/agents/project/a/storyboard.md
---
# A
Body cites `.pkit/agents/project/a/storyboard.md`.
""",
        encoding="utf-8",
    )

    issues = refs.validate_corpus(kit_target)
    assert any("Read" in i.diagnosis and "tools" in i.diagnosis for i in issues)


def _make_storyboarded_agent(
    root: Path, name: str, sb_filename: str = "storyboard.md"
) -> tuple[Path, Path]:
    """Stamp a folder-form agent with a properly-declared storyboard sibling."""
    folder = root / ".pkit" / "agents" / "project" / name
    folder.mkdir(parents=True, exist_ok=True)
    agent_file = folder / f"{name}.md"
    sb_path_rel = f".pkit/agents/project/{name}/{sb_filename}"
    agent_file.write_text(
        f"---\nname: {name}\ndescription: t\ntools: [Read]\nstoryboards:\n  - {sb_path_rel}\n---\n# A\nLoad `{sb_path_rel}` at session start.\n",
        encoding="utf-8",
    )
    sb_file = folder / sb_filename
    sb_file.write_text(
        f"---\nconsumers:\n  - kind: agent\n    name: {name}\n    namespace: project\n---\n\n# Storyboard\n",
        encoding="utf-8",
    )
    return agent_file, sb_file


def test_validate_storyboard_missing_consumers_frontmatter(kit_target: Path) -> None:
    """A storyboard file without `consumers:` frontmatter is flagged."""
    agent_file, sb_file = _make_storyboarded_agent(kit_target, "a")
    sb_file.write_text("# Storyboard\n\nNo frontmatter.\n", encoding="utf-8")

    issues = refs.validate_corpus(kit_target)
    assert any("missing a non-empty `consumers:`" in i.diagnosis for i in issues)


def test_validate_storyboard_consumer_back_reference(kit_target: Path) -> None:
    """If a storyboard declares an agent consumer, that agent must declare this storyboard back."""
    agent_file, sb_file = _make_storyboarded_agent(kit_target, "a")
    # Strip the storyboards: declaration from the agent — now back-reference fails.
    agent_file.write_text(
        "---\nname: a\ndescription: t\ntools: [Read]\n---\n# A\n",
        encoding="utf-8",
    )

    issues = refs.validate_corpus(kit_target)
    assert any(
        "consumer agent project/a" in i.diagnosis
        and "does not include this path" in i.diagnosis
        for i in issues
    )


def test_validate_storyboard_consumer_must_exist(kit_target: Path) -> None:
    """If a storyboard names a consumer that doesn't exist, the validator flags it."""
    folder = kit_target / ".pkit" / "agents" / "project" / "orphan-folder"
    folder.mkdir(parents=True)
    sb_file = folder / "storyboard.md"
    sb_file.write_text(
        "---\nconsumers:\n  - kind: agent\n    name: nonexistent\n    namespace: project\n---\n\n# Orphan\n",
        encoding="utf-8",
    )

    issues = refs.validate_corpus(kit_target)
    assert any("no such agent exists" in i.diagnosis for i in issues)


def test_validate_storyboard_unsupported_kind(kit_target: Path) -> None:
    """A consumer of an unsupported kind (e.g. `cli`) is flagged until kinds are added."""
    folder = kit_target / ".pkit" / "agents" / "project" / "future-cli"
    folder.mkdir(parents=True)
    sb_file = folder / "storyboard.md"
    sb_file.write_text(
        "---\nconsumers:\n  - kind: cli\n    name: pkit-upgrade\n    namespace: core\n---\n\n# Future\n",
        encoding="utf-8",
    )

    issues = refs.validate_corpus(kit_target)
    assert any("only `agent` is supported" in i.diagnosis for i in issues)


def test_validate_storyboard_orphan_file_flagged(kit_target: Path) -> None:
    """A storyboard file in an agent folder that no agent declares is flagged as orphan."""
    folder = kit_target / ".pkit" / "agents" / "project" / "a"
    folder.mkdir(parents=True)
    (folder / "a.md").write_text(
        "---\nname: a\ndescription: t\n---\n# A\n", encoding="utf-8"
    )
    # Drop a storyboard alongside that the agent doesn't declare.
    orphan = folder / "orphan.storyboard.md"
    orphan.write_text(
        "---\nconsumers:\n  - kind: agent\n    name: a\n    namespace: project\n---\n# Orphan\n",
        encoding="utf-8",
    )

    issues = refs.validate_corpus(kit_target)
    assert any("orphan" in i.diagnosis.lower() for i in issues)


def test_validate_storyboard_quiet_on_clean_two_sided_pair(kit_target: Path) -> None:
    """A properly-declared two-sided pair produces no storyboard-related findings."""
    _make_storyboarded_agent(kit_target, "clean-agent")
    issues = refs.validate_corpus(kit_target)
    assert all(
        "storyboard" not in i.diagnosis.lower() for i in issues
    ), f"unexpected storyboard findings on clean pair: {issues}"


def test_validate_storyboards_quiet_when_no_storyboards_declared(kit_target: Path) -> None:
    """Agents without `storyboards:` get no storyboard-related findings."""
    _write_agent(kit_target, "project", "judgement-agent", "---\nname: judgement-agent\n---\n# A\n")
    issues = refs.validate_corpus(kit_target)
    assert all(
        "storyboard" not in i.diagnosis.lower() for i in issues
    ), f"unexpected storyboard findings on storyboardless agent: {issues}"


# --- rot detection --------------------------------------------------


def test_rot_flags_superseded_record_reference(kit_target: Path) -> None:
    """Citing a record whose status is `superseded` is rotten."""
    super_path = _write_decision(kit_target, "core", "COR", "010", "old-thing")
    super_path.write_text(
        "---\nid: COR-010\ntitle: t\nstatus: superseded\ndate: 2026-01-01\nauthor: a\n---\n",
        encoding="utf-8",
    )
    body = """---
name: skill-a
description: t
reads:
  records: [COR-010]
---
# A
Per COR-010 this matters.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    artifacts = refs.load_artifacts(kit_target)
    issues = refs.find_rot(kit_target, artifacts)
    assert any("superseded" in i.diagnosis and "COR-010" in i.diagnosis for i in issues)


def test_rot_flags_dropped_scratchpad_reference(kit_target: Path) -> None:
    dropped = kit_target / ".pkit" / "scratchpad" / "dropped"
    dropped.mkdir(parents=True)
    (dropped / "2026-05-01-old-idea.md").write_text("---\nretired: 2026-05-10\n---\n# old\n", encoding="utf-8")
    body = """---
name: skill-a
description: t
reads:
  paths: [.pkit/scratchpad/dropped/2026-05-01-old-idea.md]
---
# A
Cites `.pkit/scratchpad/dropped/2026-05-01-old-idea.md`.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    artifacts = refs.load_artifacts(kit_target)
    issues = refs.find_rot(kit_target, artifacts)
    assert any("dropped scratchpad" in i.diagnosis for i in issues)


def test_rot_flags_missing_path(kit_target: Path) -> None:
    body = """---
name: skill-a
description: t
reads:
  paths: [.pkit/does-not-exist.md]
---
# A
Cites `.pkit/does-not-exist.md`.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    artifacts = refs.load_artifacts(kit_target)
    issues = refs.find_rot(kit_target, artifacts)
    assert any("missing path" in i.diagnosis and "does-not-exist" in i.diagnosis for i in issues)


def test_rot_clean_corpus_returns_no_issues(kit_target: Path) -> None:
    """Accepted records + existing files + no superseded refs = no rot."""
    _write_decision(kit_target, "core", "COR", "001", "thing")
    body = """---
name: skill-a
description: t
reads:
  records: [COR-001]
---
# A
Per COR-001 it works.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    artifacts = refs.load_artifacts(kit_target)
    issues = refs.find_rot(kit_target, artifacts)
    assert issues == []


# --- rename ---------------------------------------------------------


def test_rename_updates_frontmatter_record(kit_target: Path) -> None:
    body = """---
name: skill-a
description: t
reads:
  records: [COR-001]
gates: [COR-001]
---
# A
Per COR-001 yes.
"""
    skill = _write_skill(kit_target, "core", "skill-a", body)
    modified = refs.rename_reference(kit_target, "COR-001", "COR-099")
    assert skill in modified
    new_text = skill.read_text()
    assert "COR-099" in new_text
    assert "COR-001" not in new_text


def test_rename_updates_body_record(kit_target: Path) -> None:
    body = """---
name: skill-a
description: t
---
# A
Bare body mention of COR-005 here.
"""
    skill = _write_skill(kit_target, "core", "skill-a", body)
    refs.rename_reference(kit_target, "COR-005", "COR-099")
    new_text = skill.read_text()
    assert "COR-099" in new_text
    assert "COR-005" not in new_text


def test_rename_updates_path_in_backticks_and_links(kit_target: Path) -> None:
    body = """---
name: skill-a
description: t
reads:
  paths: [.pkit/old.md]
---
# A
See `.pkit/old.md` and also [the doc](.pkit/old.md).
"""
    skill = _write_skill(kit_target, "core", "skill-a", body)
    refs.rename_reference(kit_target, ".pkit/old.md", ".pkit/new.md")
    new_text = skill.read_text()
    assert ".pkit/new.md" in new_text
    assert ".pkit/old.md" not in new_text


def test_rename_updates_hook_token(kit_target: Path) -> None:
    body = """---
name: agent-a
description: t
needs: [workflow.old-name]
---
# A
Calls workflow.old-name now.
"""
    agent = _write_agent(kit_target, "project", "agent-a", body)
    refs.rename_reference(kit_target, "workflow.old-name", "workflow.new-name")
    new_text = agent.read_text()
    assert "workflow.new-name" in new_text
    assert "workflow.old-name" not in new_text


def test_rename_dry_run_writes_nothing(kit_target: Path) -> None:
    body = """---
name: skill-a
description: t
reads:
  records: [COR-001]
---
# A
Per COR-001.
"""
    skill = _write_skill(kit_target, "core", "skill-a", body)
    before = skill.read_text()
    modified = refs.rename_reference(kit_target, "COR-001", "COR-099", dry_run=True)
    assert skill in modified  # reported as would-modify
    assert skill.read_text() == before  # but file unchanged


def test_rename_noop_returns_empty(kit_target: Path) -> None:
    """Renaming a value that doesn't appear anywhere returns no modifications."""
    body = "---\nname: skill-a\ndescription: t\n---\n# A\n"
    _write_skill(kit_target, "core", "skill-a", body)
    modified = refs.rename_reference(kit_target, "COR-999", "COR-998")
    assert modified == []


# --- graph emission -------------------------------------------------


def test_emit_graph_dot_includes_nodes_and_edges(kit_target: Path) -> None:
    _write_decision(kit_target, "core", "COR", "001", "thing")
    body = """---
name: skill-a
description: t
reads:
  records: [COR-001]
---
# A
Per COR-001.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    artifacts = refs.load_artifacts(kit_target)
    dot = refs.emit_graph_dot(artifacts)
    assert dot.startswith("digraph refs")
    assert "skill-a" in dot
    assert "COR-001" in dot
    assert "reads.records" in dot


def test_emit_graph_ascii_uses_tree_style_layout(kit_target: Path) -> None:
    """The ASCII format renders each artifact as a tree with box-drawing characters."""
    _write_decision(kit_target, "core", "COR", "001", "thing")
    body = """---
name: skill-a
description: test
gates: [COR-001]
reads:
  records: [COR-001]
---
# A
Per COR-001 this matters.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    artifacts = refs.load_artifacts(kit_target)
    ascii_out = refs.emit_graph_ascii(artifacts)
    # Header line for the artifact
    assert "skill core/skill-a" in ascii_out
    # Tree branch characters
    assert "├──" in ascii_out or "└──" in ascii_out
    # Branch labels match bucket names from outgoing_refs
    assert "reads.records" in ascii_out
    assert "gates" in ascii_out
    # The actual ref values appear as tree leaves
    assert "COR-001" in ascii_out


def test_emit_graph_ascii_separates_artifacts_with_blank_line(kit_target: Path) -> None:
    """Multiple artifacts are separated by a blank line so trees are visually distinct."""
    body_a = "---\nname: a\ndescription: t\ngates: [COR-001]\n---\n# A\nPer COR-001.\n"
    body_b = "---\nname: b\ndescription: t\ngates: [COR-002]\n---\n# B\nPer COR-002.\n"
    _write_decision(kit_target, "core", "COR", "001", "thing")
    _write_decision(kit_target, "core", "COR", "002", "other")
    _write_skill(kit_target, "core", "a", body_a)
    _write_skill(kit_target, "core", "b", body_b)
    artifacts = refs.load_artifacts(kit_target)
    ascii_out = refs.emit_graph_ascii(artifacts)
    # Two artifact headers, separated by exactly one blank line
    assert "skill core/a" in ascii_out
    assert "skill core/b" in ascii_out
    assert "\n\nskill core/b" in ascii_out


def test_cli_refs_graph_ascii_format(kit_target: Path) -> None:
    """`pkit refs graph --format ascii` returns the tree-style output."""
    body = "---\nname: skill-a\ndescription: t\ngates: [COR-001]\n---\n# A\nPer COR-001.\n"
    _write_decision(kit_target, "core", "COR", "001", "thing")
    _write_skill(kit_target, "core", "skill-a", body)
    runner = CliRunner()
    result = runner.invoke(main, ["refs", "graph", "--format", "ascii"])
    assert result.exit_code == 0
    assert "skill core/skill-a" in result.output
    assert "├──" in result.output or "└──" in result.output


def test_cli_refs_graph_defaults_to_ascii(kit_target: Path) -> None:
    """No `--format` flag uses the ascii tree-style output (the new default)."""
    body = "---\nname: skill-a\ndescription: t\ngates: [COR-001]\n---\n# A\nPer COR-001.\n"
    _write_decision(kit_target, "core", "COR", "001", "thing")
    _write_skill(kit_target, "core", "skill-a", body)
    runner = CliRunner()
    result = runner.invoke(main, ["refs", "graph"])
    assert result.exit_code == 0
    # Box-drawing characters confirm ascii (tree) format, not text (plain) or dot.
    assert "├──" in result.output or "└──" in result.output
    assert "digraph" not in result.output


def test_emit_graph_text_lists_artifacts_and_refs(kit_target: Path) -> None:
    body = """---
name: skill-a
description: t
gates: [COR-001]
---
# A
Per COR-001 yes.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    artifacts = refs.load_artifacts(kit_target)
    text = refs.emit_graph_text(artifacts)
    assert "skill core/skill-a" in text
    assert "gates:" in text
    assert "COR-001" in text


# --- CLI wiring for new subcommands ---------------------------------


def test_cli_refs_rot_clean(kit_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["refs", "rot"])
    assert result.exit_code == 0
    assert "no rotten references" in result.output


def test_cli_refs_rename_modifies_files(kit_target: Path) -> None:
    body = """---
name: skill-a
description: t
reads:
  records: [COR-001]
---
# A
Per COR-001.
"""
    _write_skill(kit_target, "core", "skill-a", body)
    runner = CliRunner()
    result = runner.invoke(main, ["refs", "rename", "COR-001", "COR-099"])
    assert result.exit_code == 0
    assert "modified 1 file" in result.output


def test_cli_refs_rename_dry_run(kit_target: Path) -> None:
    body = "---\nname: skill-a\ndescription: t\nreads:\n  records: [COR-001]\n---\n# A\nPer COR-001.\n"
    skill = _write_skill(kit_target, "core", "skill-a", body)
    before = skill.read_text()
    runner = CliRunner()
    result = runner.invoke(main, ["refs", "rename", "COR-001", "COR-099", "--dry-run"])
    assert result.exit_code == 0
    assert "would modify" in result.output
    assert skill.read_text() == before


def test_cli_refs_graph_dot_format(kit_target: Path) -> None:
    body = "---\nname: skill-a\ndescription: t\n---\n# A\n"
    _write_skill(kit_target, "core", "skill-a", body)
    runner = CliRunner()
    result = runner.invoke(main, ["refs", "graph", "--format", "dot"])
    assert result.exit_code == 0
    assert result.output.startswith("digraph refs") or "digraph refs" in result.output


def test_cli_hooks_who_needs_lists_agents(kit_target: Path) -> None:
    agent_body = """---
name: consumer
description: consumes
needs: [workflow.do-thing]
answers: []
---
# C
Calls workflow.do-thing.
"""
    _write_agent(kit_target, "project", "consumer", agent_body)
    runner = CliRunner()
    result = runner.invoke(main, ["hooks", "who-needs", "workflow.do-thing"])
    assert result.exit_code == 0
    assert "consumer" in result.output
