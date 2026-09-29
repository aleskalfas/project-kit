"""Tests for the backbone configuration pass of `pkit validate` (COR-048 point 4,
COR-049 points 1 and 7, COR-050 points 12 and 14, COR-053 point 7, ADR-056).

Every test stands up an adopter repository with the shared fixture, so the
schema is the one the installed tree ships and the repository checks run
against a real root.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit import backbone_schemas as bs
from project_kit import config_validate as cv
from project_kit import report_context
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO = Path(__file__).resolve().parents[1]


def _write_config(repo: AdopterRepo, text: str) -> Path:
    path = report_context.project_config_path(repo.root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _run(repo: AdopterRepo) -> cv.ConfigReport:
    return cv.run_configuration_pass(repo.root)


def _messages(report: cv.ConfigReport, severity: cv.Severity | None = None) -> list[str]:
    findings = report.findings if severity is None else report.by_severity(severity)
    return [f.message for f in findings]


def _paths(report: cv.ConfigReport, severity: cv.Severity | None = None) -> list[str]:
    findings = report.findings if severity is None else report.by_severity(severity)
    return [f.path for f in findings]


# --- the shipped schema ------------------------------------------------------


def test_shipped_config_schema_is_draft_2020_12_without_a_version_key() -> None:
    path = bs.backbone_schema_path(REPO, cv.CONFIG_SCHEMA_KIND)
    assert path.is_file()
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    # No version key in the file (ADR-056 point 3); the backbone owns the shape.
    assert "schema_version" not in schema["properties"]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {
        "name", "docs", "friction", "connections", "process", "project",
    }


def test_installed_tree_ships_the_config_schema(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    assert bs.backbone_schema_path(repo.root, cv.CONFIG_SCHEMA_KIND).is_file()


# --- presence ----------------------------------------------------------------


def test_absent_file_is_clean_and_defaults_apply(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    assert not report_context.project_config_path(repo.root).exists()
    report = _run(repo)
    assert report.schema_present
    assert not report.present
    assert report.findings == ()
    assert report.is_clean


def test_empty_file_is_clean(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "# nothing declared yet\n")
    report = _run(repo)
    assert not report.present
    assert report.findings == ()


def test_valid_file_with_every_key_is_clean(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo(capabilities=("project-management",))
    # The connection entries are checked for real (#983): the named capability
    # must provide the role, and the selected point must be `single` with the
    # named capability among its contributors. project-management provides
    # `pkit::work-tracking` (#1000); a `single` point and a contribution to it
    # are added beside its own.
    package = repo.pkit / "capabilities" / "project-management" / "package.yaml"
    yaml = YAML()
    data = yaml.load(package.read_text(encoding="utf-8"))
    connections = data["connections"]
    connections["extension-points"]["accepts"]["pkit::work-tracking:issue-kinds"] = {
        "schema_version": 1,
        "schema": "issue-kinds.schema.json",
        "description": "The kinds.",
        "combination": "single",
    }
    connections["extensions"]["contributes"].append(
        {"point": "pkit::work-tracking:issue-kinds", "schema_version": 1}
    )
    with package.open("w", encoding="utf-8") as handle:
        yaml.dump(data, handle)
    (package.parent / "schemas" / "issue-kinds.schema.json").write_text("{}", encoding="utf-8")
    (repo.root / "docs").mkdir()
    (repo.root / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    _write_config(
        repo,
        """
name: example
docs:
  user: docs/
  internal: docs
friction:
  mode: enforcing
  status-job: after-merge
  places: [docs/**/*.md]
  surface: [docs/**]
  exclude: [docs/guide.md]
connections:
  providers:
    pkit::work-tracking: project-management
  selections:
    pkit::work-tracking:issue-kinds: project-management
project:
  anything: [goes, here]
  nested: {deeply: true}
""",
    )
    report = _run(repo)
    assert report.findings == ()  # the connection entries are verified, and hold


def test_name_only_file_is_clean(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    report_context.write_project_name(repo.root, "example")
    assert _run(repo).findings == ()


# --- shape -------------------------------------------------------------------


def test_unknown_top_level_key_names_the_nearest_known_key(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "doc:\n  user: docs\n")
    report = _run(repo)
    assert [(f.path, f.severity) for f in report.findings] == [("/doc", cv.Severity.ERROR)]
    assert report.findings[0].message == bs.render_unknown_key("doc", ["docs"])
    assert "did you mean 'docs'" in report.findings[0].message


def test_unknown_nested_key_names_the_nearest_known_key(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "friction:\n  mod: warning\n  places: []\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/friction/mod"]
    assert "did you mean 'mode'" in report.errors[0].message


def test_wrong_type_is_an_error_at_its_position(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "name: [not, a, string]\nfriction:\n  mode: loud\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/friction/mode", "/name"]
    assert "is not one of ['warning', 'enforcing']" in report.errors[0].message
    assert "is not of type 'string'" in report.errors[1].message


def test_connection_key_not_an_address_is_an_error(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "connections:\n  providers:\n    work-tracking: project-management\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/connections/providers/work-tracking"]
    assert "<publisher>::<role>" in report.errors[0].message


def test_project_block_is_accepted_without_inspection(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "project:\n  doc: [1, 2]\n  frictoin: {mode: loud}\n  2026: x\n")
    assert _run(repo).findings == ()


def test_project_block_must_be_a_mapping(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "project: [a, list]\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/project"]


def test_unparsable_file_is_an_error_on_the_file(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "name: [unclosed\n")
    report = _run(repo)
    assert [(f.path, f.severity) for f in report.findings] == [("", cv.Severity.ERROR)]
    assert "does not parse as YAML" in report.findings[0].message


def test_non_mapping_file_is_an_error_on_the_file(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "- just\n- a list\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == [""]
    assert "must be a mapping" in report.errors[0].message


# --- documentation roots (COR-049) ------------------------------------------


def test_missing_root_is_a_warning(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "docs:\n  internal: handbook\n")
    report = _run(repo)
    assert report.errors == ()
    assert _paths(report, cv.Severity.WARNING) == ["/docs/internal"]
    assert "does not exist yet" in report.findings[0].message


def test_root_outside_repository_is_an_error(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "docs:\n  user: ../elsewhere\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/docs/user"]
    assert "outside the repository" in report.errors[0].message


def test_absolute_root_is_refused_by_the_schema(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "docs:\n  user: /tmp/docs\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/docs/user"]
    assert "does not match" in report.errors[0].message


def test_root_inside_methodology_tree_is_an_error(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "docs:\n  internal: .pkit/decisions\n  user: .pkit\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/docs/internal", "/docs/user"]
    assert all("methodology's own tree" in m for m in _messages(report))


def test_root_symlink_is_followed(make_adopter_repo: MakeAdopterRepo, tmp_path: Path) -> None:
    repo = make_adopter_repo(root=tmp_path / "repo")
    outside = tmp_path / "outside-docs"
    outside.mkdir()
    (repo.root / "docs").symlink_to(outside, target_is_directory=True)
    (repo.root / "local").mkdir()
    (repo.root / "linked").symlink_to(repo.root / "local", target_is_directory=True)
    _write_config(repo, "docs:\n  user: docs\n  internal: linked\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/docs/user"]
    assert "outside the repository" in report.errors[0].message
    assert _paths(report, cv.Severity.WARNING) == []


# --- friction paths (COR-050) -----------------------------------------------


def test_friction_pattern_outside_repository_is_an_error(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "friction:\n  places: ['../sibling/**']\n  exclude: ['docs/../../x']\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/friction/places/0", "/friction/exclude/0"]
    assert all("leaves the repository" in m for m in _messages(report))


def test_friction_pattern_resolving_outside_through_a_link_is_an_error(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    outside = repo.root.parent / f"{repo.root.name}-outside"  # beside the repository, not in it
    outside.mkdir()
    (repo.root / "docs").mkdir()
    (repo.root / "docs" / "linked").symlink_to(outside, target_is_directory=True)
    _write_config(repo, "friction:\n  places: ['docs/linked/**', 'docs/linked/sub/**']\n")
    report = cv.run_configuration_pass(repo.root)
    assert _paths(report, cv.Severity.ERROR) == ["/friction/places/0", "/friction/places/1"]
    assert all("through a link" in m for m in _messages(report))


def test_friction_pattern_matching_nothing_is_a_warning(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    (repo.root / "notes").mkdir()
    (repo.root / "notes" / "a.md").write_text("x\n", encoding="utf-8")
    _write_config(
        repo,
        "friction:\n  places: ['notes/**/*.md', 'nowhere/**/*.md']\n  surface: [notes]\n",
    )
    report = _run(repo)
    assert report.errors == ()
    assert _paths(report, cv.Severity.WARNING) == ["/friction/places/1"]
    assert "matches nothing" in report.findings[0].message


def test_friction_mode_value_is_checked(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "friction:\n  mode: off\n  status-job: weekly\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/friction/mode", "/friction/status-job"]


# --- process journal logging (COR-033 point 7) -----------------------------


def test_process_journal_settings_validate(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "process:\n  journal:\n    enabled: true\n    committed: false\n")
    assert _run(repo).findings == ()


def test_process_journal_values_must_be_booleans(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "process:\n  journal:\n    enabled: 'yes'\n    committed: 1\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == [
        "/process/journal/committed", "/process/journal/enabled",
    ]


def test_unknown_process_journal_key_names_the_nearest_known_key(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "process:\n  journal:\n    enable: true\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/process/journal/enable"]
    assert "did you mean 'enabled'" in report.errors[0].message


def test_config_set_turns_journal_logging_on_and_the_ignore_line_follows(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    gitignore = repo.root / ".pkit" / ".gitignore"
    assert "journal.jsonl" in gitignore.read_text(encoding="utf-8")
    runner = CliRunner()

    enabled = runner.invoke(main, ["config", "set", "process.journal.enabled", "true", "--yes"])
    committed = runner.invoke(
        main, ["config", "set", "process.journal.committed", "true", "--yes"]
    )

    assert enabled.exit_code == 0, enabled.output
    assert committed.exit_code == 0, committed.output
    assert "rendered      .pkit/.gitignore" in committed.output
    assert "journal.jsonl" not in gitignore.read_text(encoding="utf-8")
    config = YAML(typ="safe").load(report_context.project_config_path(repo.root).read_text())
    assert config["process"] == {"journal": {"enabled": True, "committed": True}}


def test_friction_findings_on_a_valid_configuration_are_pinned(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Every pattern form the settings allow — a folder, a file, `*`, `**`, the whole
    repository — judged on a valid configuration. The findings are pinned: reading the
    patterns and matching them through discovery (ADR-057 point 2) must not move them."""
    repo = make_adopter_repo()
    repo.write(
        {
            "docs/guide.md": "# Guide\n",
            "docs/sub/deep.md": "# Deep\n",
            "notes/a.md": "# A\n",
            "src/cli/main.py": "print('x')\n",
        }
    )
    _write_config(
        repo,
        "name: example\n"
        "docs:\n  user: docs/\n  internal: tech-docs\n"
        "friction:\n"
        "  mode: warning\n"
        "  places: [docs, 'docs/**/*.md', 'notes/*.md', notes/a.md, 'nowhere/**']\n"
        "  surface: ['src/**', ., src]\n"
        "  exclude: [docs/sub, missing.md]\n",
    )
    report = _run(repo)
    assert [(f.path, f.severity, f.message) for f in report.findings] == [
        (
            "/docs/internal",
            cv.Severity.WARNING,
            "documentation root 'tech-docs' does not exist yet; the default applies to "
            "readers until it is created (COR-049 point 7).",
        ),
        (
            "/friction/places/4",
            cv.Severity.WARNING,
            "friction pattern 'nowhere/**' matches nothing in the repository; a dead pattern "
            "keeps silence looking like health (COR-050 point 12).",
        ),
        (
            "/friction/exclude/1",
            cv.Severity.WARNING,
            "friction pattern 'missing.md' matches nothing in the repository; a dead pattern "
            "keeps silence looking like health (COR-050 point 12).",
        ),
    ]


def test_a_pattern_is_live_only_when_it_covers_a_file_the_checks_see(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Matching is discovery's: over the working tree's one listing, by the reading the
    checks apply. A glob that reaches only a folder, a folder holding only files git
    ignores, and an empty folder cover no file the checks ever see — dead patterns."""
    repo = make_adopter_repo()
    repo.write(
        {
            ".gitignore": "build/\n",
            "build/out.md": "# generated\n",
            "docs/sub/page.md": "# Page\n",
        }
    )
    (repo.root / "empty").mkdir()
    _write_config(repo, "friction:\n  exclude: ['docs/*', build, empty, 'docs/**']\n")
    report = _run(repo)
    assert report.errors == ()
    assert _paths(report, cv.Severity.WARNING) == [
        "/friction/exclude/0",
        "/friction/exclude/1",
        "/friction/exclude/2",
    ]


def test_a_pattern_is_judged_as_discovery_reads_it(make_adopter_repo: MakeAdopterRepo) -> None:
    """Discovery walks a pattern without its surrounding spaces, so that is the pattern
    judged; the finding still points at the entry as written."""
    repo = make_adopter_repo()
    repo.write({"docs/page.md": "# Page\n"})
    _write_config(repo, "friction:\n  places: [' docs ', ' nowhere']\n")
    report = _run(repo)
    assert [(f.path, f.severity) for f in report.findings] == [
        ("/friction/places/1", cv.Severity.WARNING)
    ]
    assert report.findings[0].message.startswith("friction pattern 'nowhere' matches nothing")


# --- connections (COR-053, COR-052) ------------------------------------------


def test_provider_naming_uninstalled_capability_is_an_error(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_config(
        repo,
        "connections:\n"
        "  providers:\n"
        "    pkit::work-tracking: project-management\n"
        "  selections:\n"
        "    pkit::documentation:pages: living-docs\n",
    )
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == [
        "/connections/providers/pkit::work-tracking",
        "/connections/selections/pkit::documentation:pages",
    ]
    assert "not an installed capability" in report.errors[0].message
    assert "pkit capabilities install project-management" in report.errors[0].message
    assert report.by_severity(cv.Severity.INFO) == ()


def test_provider_naming_installed_capability_that_does_not_provide_the_role_is_an_error(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The check is real now (#983): the shipped capability provides
    `pkit::work-tracking` (#1000), not `pkit::documentation`."""
    repo = make_adopter_repo(capabilities=("project-management",))
    _write_config(repo, "connections:\n  providers:\n    pkit::documentation: project-management\n")
    report = _run(repo)
    assert _paths(report, cv.Severity.ERROR) == ["/connections/providers/pkit::documentation"]
    assert "does not provide role 'pkit::documentation'" in report.errors[0].message
    assert "no installed capability provides the role" in report.errors[0].message
    assert report.by_severity(cv.Severity.INFO) == ()


# --- determinism and the tree's schema ---------------------------------------


def test_same_input_yields_identical_output(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(
        repo,
        "doc: {}\nfriction:\n  mod: warning\n  places: ['zzz/**', 'aaa/**']\n"
        "docs:\n  user: ../out\n  internal: nowhere\n"
        "connections:\n  providers: {pkit::b: gone, pkit::a: gone}\n",
    )
    first = _run(repo)
    second = _run(repo)
    assert first == second
    # Shape findings first, by position; then the repository checks in the
    # file's key order (fixed: docs, friction, connections), each in written order.
    assert _paths(first) == [
        "/doc",
        "/friction/mod",
        "/docs/user",
        "/docs/internal",
        "/friction/places/0",
        "/friction/places/1",
        "/connections/providers/pkit::b",
        "/connections/providers/pkit::a",
    ]


def test_missing_schema_in_tree_skips_the_pass(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    bs.backbone_schema_path(repo.root, cv.CONFIG_SCHEMA_KIND).unlink()
    _write_config(repo, "totally: wrong\n")
    report = _run(repo)
    assert not report.schema_present
    assert report.findings == ()


# --- the writer stamps the editor directive ----------------------------------


def test_write_project_name_stamps_editor_directive_on_a_fresh_file(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    path = report_context.write_project_name(repo.root, "example")
    text = path.read_text(encoding="utf-8")
    assert text.startswith(report_context.EDITOR_DIRECTIVE + "\n")
    assert report_context.read_project_name(repo.root) == "example"
    assert _run(repo).findings == ()
    # The directive is a comment: the shipped schema resolves relative to the file.
    directive_target = path.parent / report_context.EDITOR_DIRECTIVE.split("$schema=", 1)[1]
    assert (
        directive_target.resolve()
        == bs.backbone_schema_path(repo.root, cv.CONFIG_SCHEMA_KIND).resolve()
    )


def test_write_project_name_keeps_an_existing_file_as_is(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "# my header\ndocs:\n  user: docs\n")
    path = report_context.write_project_name(repo.root, "example")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# my header\n")
    assert report_context.EDITOR_DIRECTIVE not in text
    assert "user: docs" in text
    assert report_context.read_project_name(repo.root) == "example"


# --- the command --------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_pkit_validate_fails_on_configuration_errors_only(
    make_adopter_repo: MakeAdopterRepo, runner: CliRunner
) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "docs:\n  internal: nowhere\n")
    result = runner.invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert "configuration" in result.output
    assert "warning" in result.output
    assert "does not exist yet" in result.output

    _write_config(repo, "doc: {}\n")
    result = runner.invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 1, result.output
    assert ".pkit/project/config.yaml" in result.output
    assert "did you mean 'docs'" in result.output


def test_pkit_validate_reports_absent_configuration(
    make_adopter_repo: MakeAdopterRepo, runner: CliRunner
) -> None:
    make_adopter_repo()
    result = runner.invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert "absent or empty: defaults apply" in result.output
