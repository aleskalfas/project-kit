"""Tests for `pkit decisions validate`: the decision-id collision check (Feature #162)
and the revision-narration report (#862)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import decisions_validate
from project_kit.cli import main
from project_kit.validators import Severity
from tests.adopter_repo import MakeAdopterRepo


def _write_record(
    path: Path, record_id: str, body: str = "## Context\n", status: str = "proposed"
) -> None:
    """Stamp a minimal decision record with the given frontmatter id at `path`.

    The front matter is seven lines and a blank line follows it, so the body's
    first line is line 9 of the file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {record_id}\ntitle: x\nstatus: {status}\n"
        f"date: 2026-06-21\nauthor: t\n---\n\n{body}",
        encoding="utf-8",
    )


def _make_capability(target_root: Path, name: str) -> Path:
    """Create a minimal valid capability directory; return its decisions/ path."""
    cap_dir = target_root / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True)
    (cap_dir / "package.yaml").write_text(
        f"component:\n  kind: capability\n  name: {name}\n  version: 0.1.0\n",
        encoding="utf-8",
    )
    decisions_dir = cap_dir / "decisions"
    decisions_dir.mkdir()
    return decisions_dir


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project tree with the fixed decision namespaces present."""
    (tmp_path / ".pkit" / "decisions" / "core").mkdir(parents=True)
    (tmp_path / ".pkit" / "decisions" / "project").mkdir(parents=True)
    return tmp_path


# --- clean repo --------------------------------------------------------


def test_clean_repo_passes(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-001-a.md", "COR-001")
    _write_record(core / "COR-002-b.md", "COR-002")
    _write_record(project / ".pkit" / "decisions" / "project" / "PRJ-001-c.md", "PRJ-001")

    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean
    assert report.records_checked == 3


def test_empty_repo_is_clean(project: Path) -> None:
    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean
    assert report.records_checked == 0


# --- duplicate detection -----------------------------------------------


def test_duplicate_id_in_same_space_fails(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-001-a.md", "COR-001")
    _write_record(core / "COR-001-b.md", "COR-001")

    report = decisions_validate.validate_decision_ids(project)
    assert not report.is_clean
    dupes = [i for i in report.issues if "COR-001" in i.location]
    assert len(dupes) == 1
    assert "COR-001-a.md" in dupes[0].message
    assert "COR-001-b.md" in dupes[0].message


def test_duplicate_dec_in_same_capability_fails(project: Path) -> None:
    cap = _make_capability(project, "alpha")
    _write_record(cap / "DEC-001-one.md", "DEC-001")
    _write_record(cap / "DEC-001-two.md", "DEC-001")

    report = decisions_validate.validate_decision_ids(project)
    assert not report.is_clean
    assert any(i.location == "capability:alpha :: DEC-001" for i in report.issues)


# --- cross-space is NOT a collision ------------------------------------


def test_same_dec_number_in_two_capabilities_is_not_a_collision(project: Path) -> None:
    alpha = _make_capability(project, "alpha")
    beta = _make_capability(project, "beta")
    _write_record(alpha / "DEC-001-a.md", "DEC-001")
    _write_record(beta / "DEC-001-b.md", "DEC-001")

    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean, [i.message for i in report.issues]
    assert report.records_checked == 2


def test_cor_and_prj_with_same_number_is_not_a_collision(project: Path) -> None:
    _write_record(project / ".pkit" / "decisions" / "core" / "COR-001-a.md", "COR-001")
    _write_record(project / ".pkit" / "decisions" / "project" / "PRJ-001-b.md", "PRJ-001")

    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean


# --- id / filename consistency -----------------------------------------


def test_id_filename_mismatch_is_flagged(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-005-mismatch.md", "COR-003")

    report = decisions_validate.validate_decision_ids(project)
    assert not report.is_clean
    assert any("disagrees with the filename" in i.message for i in report.issues)


def test_zero_padding_difference_is_not_a_mismatch(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    # filename uses unpadded number; frontmatter is padded — same number.
    _write_record(core / "COR-7-x.md", "COR-007")
    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean


def test_unparseable_id_is_flagged(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    (core / "COR-001-bad.md").write_text("no frontmatter here\n", encoding="utf-8")
    report = decisions_validate.validate_decision_ids(project)
    assert not report.is_clean
    assert any("could not parse" in i.message for i in report.issues)


def test_readme_in_decisions_dir_is_skipped(project: Path) -> None:
    proj = project / ".pkit" / "decisions" / "project"
    (proj / "README.md").write_text("# index\n", encoding="utf-8")
    _write_record(proj / "PRJ-001-a.md", "PRJ-001")
    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean
    assert report.records_checked == 1


# --- ADR id-space ------------------------------------------------------


def test_adr_duplicates_detected_via_overlay(project: Path) -> None:
    overlay = project / ".pkit" / "agents" / "project" / "overlay.yaml"
    overlay.parent.mkdir(parents=True)
    overlay.write_text("adr-records:\n  - docs/architecture/decisions/\n", encoding="utf-8")
    adr_dir = project / "docs" / "architecture" / "decisions"
    adr_dir.mkdir(parents=True)
    _write_record(adr_dir / "ADR-001-a.md", "ADR-001")
    _write_record(adr_dir / "ADR-001-b.md", "ADR-001")

    report = decisions_validate.validate_decision_ids(project)
    assert not report.is_clean
    assert any(i.location == "adr :: ADR-001" for i in report.issues)


def test_missing_overlay_does_not_error(project: Path) -> None:
    # No overlay configured: ADRs simply aren't scanned, no crash.
    _write_record(project / ".pkit" / "decisions" / "core" / "COR-001-a.md", "COR-001")
    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean


# --- CLI ---------------------------------------------------------------


def test_cli_clean_exits_zero(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    _write_record(project / ".pkit" / "decisions" / "core" / "COR-001-a.md", "COR-001")
    monkeypatch.chdir(project)
    result = CliRunner().invoke(main, ["decisions", "validate"])
    assert result.exit_code == 0
    assert "No id collisions found" in result.output


def test_cli_duplicate_exits_nonzero(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-001-a.md", "COR-001")
    _write_record(core / "COR-001-b.md", "COR-001")
    monkeypatch.chdir(project)
    result = CliRunner().invoke(main, ["decisions", "validate"])
    assert result.exit_code != 0
    assert "COR-001" in result.output


# --- revision narration (#862) -----------------------------------------
#
# A record states what is true and is refined in place; git history is its
# change log (`.pkit/decisions/README.md`, "Refining an accepted record").
# Narration is reported — never an error.

_CLEAN_BODY = """\
## Context

The engine now reads the manifest; rules no longer in the model do not reappear.

## Decision

1. **Update** — re-running the setup primitive reconciles installed state.
2. **Closed area taxonomy.** Four areas, fixed here.

## Rationale

DEC-028's step 7 must be corrected in place when this record is accepted.

## Implications

The forcing question (issue #255) is answered.
"""


@pytest.mark.parametrize(
    ("line", "shape"),
    [
        ("## Amendment (2026-08-09)", "amendment heading"),
        ("### Amendments", "amendment heading"),
        ("## Erratum", "amendment heading"),
        ("**Amendment 1** — the reader set is re-scoped.", "amendment marker"),
        ("> **Amendment (#20, under EPIC #18) — the stance splits.**", "amendment marker"),
        ("**Amended 2026-08-25 (#755):** the flag first shipped bare.", "amendment marker"),
        ("- A floor. **(Amended 2026-08-20: a floor is exempt.)**", "amendment marker"),
        ("> **Amended by [DEC-052](DEC-052-x.md).** The footer moves.", "amendment marker"),
        ("**Amended in place, not superseded — and here is the line.**", "amendment marker"),
        ("the empty set *(amended — see note below)*.", "amendment marker"),
        ("**Update (#252) — what the region contains.**", "revision stamp"),
        ("> **Correction (2026-06-25, issue #304).** The sidecar moves.", "revision stamp"),
        ("**Closed (#823 / PR #844) — the divergence is gone.**", "revision stamp"),
        ("**Source means the owned tier** (clarified, #813).", "revision stamp"),
        ("This record originally claimed a definition could declare it.", "change-log phrasing"),
        ("Previously we believed the region was narrow.", "change-log phrasing"),
        ("An earlier draft of this record rejected stamping.", "change-log phrasing"),
    ],
)
def test_each_narration_shape_is_found(line: str, shape: str) -> None:
    found = decisions_validate.find_revision_narration(f"## Decision\n\n{line}\n")
    assert [(number, found_shape) for number, found_shape, _ in found] == [(3, shape)]


def test_a_clean_record_reports_nothing() -> None:
    assert decisions_validate.find_revision_narration(_CLEAN_BODY) == []


@pytest.mark.parametrize(
    "line",
    [
        "*Superseded by [COR-023]. The field convention stands; only the location changes.*",
        "> **Superseded by [DEC-036](DEC-036-x.md).**",
        "> **Partially superseded by [DEC-036](DEC-036-x.md).** One leg is retired.",
        "### Capabilities as a sibling concept (refinement per COR-017)",
        "1. **The slot belongs to its consumer** (refinement per [COR-053](COR-053-x.md)).",
    ],
)
def test_the_permitted_markers_are_not_narration(line: str) -> None:
    """A superseded-by line and a forward refinement pointer name another record."""
    assert decisions_validate.find_revision_narration(f"{line}\n") == []


def test_code_is_quoted_material_not_narration() -> None:
    text = (
        "The note reads `> **Amended by [DEC-052]**` once accepted.\n"
        "\n"
        "```markdown\n"
        "## Amendment (2026-08-09)\n"
        "```\n"
        "~~~\n"
        "**Update (#252)**\n"
        "~~~\n"
        "- A list item:\n"
        "    ```\n"
        "    **Amendment 1**\n"
        "    ```\n"
        "> ```\n"
        "> **Correction (2026-06-25)**\n"
        "> ```\n"
    )
    assert decisions_validate.find_revision_narration(text) == []


def test_front_matter_is_not_read_and_lines_count_over_the_file() -> None:
    text = "---\nid: ADR-001\ntitle: Amendment (#1) policy\n---\n\n## Amendment (2026-08-09)\n"
    found = decisions_validate.find_revision_narration(text)
    assert found == [(6, "amendment heading", '"## Amendment (2026-08-09)"')]


def test_the_excerpt_quotes_the_line_as_written() -> None:
    text = "**Update (#252) — what the managed `permissions` region contains.**\n"
    [(_, _, excerpt)] = decisions_validate.find_revision_narration(text)
    assert excerpt == '"**Update (#252) — what the managed `permissions` region cont…"'


def test_narration_names_the_record_and_line_in_every_id_space(project: Path) -> None:
    body = "## Decision\n\n## Amendment (2026-08-09)\n"
    _write_record(project / ".pkit" / "decisions" / "core" / "COR-001-a.md", "COR-001", body)
    overlay = project / ".pkit" / "agents" / "project" / "overlay.yaml"
    overlay.parent.mkdir(parents=True)
    overlay.write_text("adr-records:\n  - docs/architecture/decisions/\n", encoding="utf-8")
    adr_dir = project / "docs" / "architecture" / "decisions"
    adr_dir.mkdir(parents=True)
    _write_record(adr_dir / "ADR-001-a.md", "ADR-001", body)
    cap = _make_capability(project, "alpha")
    _write_record(cap / "DEC-001-a.md", "DEC-001", body)

    narration = decisions_validate.revision_narration(project)

    assert sorted(issue.location for issue in narration) == [
        ".pkit/capabilities/alpha/decisions/DEC-001-a.md:11",
        ".pkit/decisions/core/COR-001-a.md:11",
        "docs/architecture/decisions/ADR-001-a.md:11",
    ]
    assert all(issue.message.startswith("amendment heading") for issue in narration)


def test_a_superseded_record_is_not_read(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    body = "*Superseded by [COR-002].*\n\n## Amendment (2026-08-09)\n"
    _write_record(core / "COR-001-a.md", "COR-001", body, status="superseded")
    assert decisions_validate.revision_narration(project) == ()


_NARRATING_BODY = "## Decision\n\n## Amendment (2026-08-09)\n"


def test_a_synced_copy_is_not_read_and_the_projects_own_record_is(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """In an adopter, a core record and a kit-shipped capability's arrive as synced
    copies: refined where they are authored, so an edit here would be overwritten."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    decisions = repo.root / ".pkit" / "decisions"
    _write_record(decisions / "core" / "COR-900-a.md", "COR-900", _NARRATING_BODY)
    capability = repo.root / ".pkit" / "capabilities" / "living-docs" / "decisions"
    _write_record(capability / "DEC-900-a.md", "DEC-900", _NARRATING_BODY)
    _write_record(decisions / "project" / "PRJ-900-a.md", "PRJ-900", _NARRATING_BODY)

    narration = decisions_validate.revision_narration(repo.root)

    assert [issue.location for issue in narration] == [".pkit/decisions/project/PRJ-900-a.md:11"]


def test_the_methodology_source_reads_its_own_core_records(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Where the methodology is authored nothing is a copy, so a core record is read."""
    repo = make_adopter_repo()
    package = repo.root / "src" / "project_kit" / "__init__.py"
    package.parent.mkdir(parents=True)
    package.write_text("", encoding="utf-8")
    core = repo.root / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-900-a.md", "COR-900", _NARRATING_BODY)

    narration = decisions_validate.revision_narration(repo.root)

    assert ".pkit/decisions/core/COR-900-a.md:11" in [issue.location for issue in narration]


def test_narration_is_not_an_id_issue(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-001-a.md", "COR-001", "## Amendment (2026-08-09)\n")
    assert decisions_validate.validate_decision_ids(project).is_clean


def test_the_validate_member_reports_narration_without_failing(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    body = "## Decision\n\n> **Amendment (#20) — the stance splits.**\n"
    _write_record(core / "COR-001-a.md", "COR-001", body, status="accepted")

    outcome = decisions_validate.outcome(project)

    assert outcome.errors == ()
    assert [(f.location, f.severity) for f in outcome.findings] == [
        (".pkit/decisions/core/COR-001-a.md:11", Severity.REPORT)
    ]
    assert "0 error(s), 1 report(s)." in outcome.summary[0]


def test_cli_reports_narration_and_exits_zero(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    body = "## Decision\n\n**Update (#252) — what the region contains.**\n"
    _write_record(project / ".pkit" / "decisions" / "core" / "COR-001-a.md", "COR-001", body)
    monkeypatch.chdir(project)
    result = CliRunner().invoke(main, ["decisions", "validate"])
    assert result.exit_code == 0, result.output
    assert "No id collisions found" in result.output
    assert "1 report(s) of revision narration" in result.output
    assert ".pkit/decisions/core/COR-001-a.md:11" in result.output
    assert "revision stamp" in result.output


def test_cli_says_nothing_of_narration_on_a_clean_corpus(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-001-a.md", "COR-001", _CLEAN_BODY)
    monkeypatch.chdir(project)
    result = CliRunner().invoke(main, ["decisions", "validate"])
    assert result.exit_code == 0, result.output
    assert "narration" not in result.output
