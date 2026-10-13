"""Tests for `pkit decisions validate`: the decision-id collision check (Feature #162)
and the revision-narration warning (#862)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from project_kit import decisions_validate, lifecycle_ownership
from project_kit.cli import main
from project_kit.validators import Finding, Severity
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


# --- synced copies (COR-055 point 1) -----------------------------------


def test_a_synced_copy_is_not_checked_for_its_id_and_the_projects_own_record_is(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """In an adopter, a core record and a kit-shipped capability's arrive as synced
    copies. The project cannot mend them, so no id issue is reported on one."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    decisions = repo.root / ".pkit" / "decisions"
    capability = repo.root / ".pkit" / "capabilities" / "living-docs" / "decisions"
    for folder, prefix in ((decisions / "core", "COR"), (capability, "DEC")):
        _write_record(folder / f"{prefix}-900-a.md", f"{prefix}-900")
        _write_record(folder / f"{prefix}-900-b.md", f"{prefix}-900")
        _write_record(folder / f"{prefix}-901-c.md", f"{prefix}-902")
        (folder / f"{prefix}-903-d.md").write_text("no front matter\n", encoding="utf-8")
    own = decisions / "project"
    _write_record(own / "PRJ-900-a.md", "PRJ-900")
    _write_record(own / "PRJ-900-b.md", "PRJ-900")
    _write_record(own / "PRJ-901-c.md", "PRJ-902")

    report = decisions_validate.validate_decision_ids(repo.root)

    assert [issue.location for issue in report.issues] == [
        ".pkit/decisions/project/PRJ-901-c.md",
        "project :: PRJ-900",
    ]
    assert report.records_checked == len(list(own.glob("*-*.md")))


def test_the_methodology_source_checks_its_own_core_records_for_ids(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Where the methodology is authored nothing is a copy, so a core record's id is
    checked."""
    repo = make_adopter_repo()
    package = repo.root / "src" / "project_kit" / "__init__.py"
    package.parent.mkdir(parents=True)
    package.write_text("", encoding="utf-8")
    core = repo.root / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-900-a.md", "COR-900")
    _write_record(core / "COR-900-b.md", "COR-900")

    report = decisions_validate.validate_decision_ids(repo.root)

    assert "core :: COR-900" in [issue.location for issue in report.issues]


@pytest.mark.parametrize(
    ("synced", "own"),
    [
        (["a"], ["b"]),
        (["a", "b"], ["c"]),
        (["a"], ["b", "c"]),
    ],
)
def test_a_projects_record_that_takes_a_synced_copys_id_is_reported_on_the_projects_record(
    project: Path, monkeypatch: pytest.MonkeyPatch, synced: list[str], own: list[str]
) -> None:
    """A synced copy keeps its id, so the project's record that shares it is the one
    reported. No tree's id-space mixes the two today, since a space's folder is synced
    whole or not at all, so the tree's predicate is stood in for here."""
    core = project / ".pkit" / "decisions" / "core"
    for name in [*synced, *own]:
        _write_record(core / f"COR-001-{name}.md", "COR-001")
    copies = {f".pkit/decisions/core/COR-001-{name}.md" for name in synced}
    ownership = SimpleNamespace(is_synced_copy=lambda _root, rel: rel in copies)
    monkeypatch.setattr(lifecycle_ownership, "load_ownership", lambda _root: ownership)

    report = decisions_validate.validate_decision_ids(project)

    assert [issue.location for issue in report.issues] == [
        f".pkit/decisions/core/COR-001-{name}.md" for name in own
    ]
    kept = (
        "arrives as a synced copy, which keeps its id"
        if len(synced) == 1
        else "arrive as synced copies, which keep their ids"
    )
    for issue in report.issues:
        assert issue.message.startswith(f"id 'COR-001' is claimed by {len(synced) + len(own)}")
        assert f"{kept}, since the next sync overwrites an edit here." in issue.message
        assert issue.message.endswith("This record takes another id.")
        assert all(f"COR-001-{name}.md" in issue.message for name in [*synced, *own])
    assert report.records_checked == len(own)


def test_the_validate_member_reports_nothing_on_a_synced_copy(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The member answers for the project's own records: a synced copy with a bad
    front matter, a duplicate id and an id its filename disagrees with yields no
    finding, while the project's record with a bad front matter does."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    decisions = repo.root / ".pkit" / "decisions"
    core = decisions / "core"
    (core / "COR-900-a.md").write_text("no front matter\n", encoding="utf-8")
    _write_record(core / "COR-901-b.md", "COR-901", status="unknown")
    _write_record(core / "COR-902-c.md", "COR-901")
    capability = repo.root / ".pkit" / "capabilities" / "living-docs" / "decisions"
    (capability / "DEC-900-a.md").write_text("no front matter\n", encoding="utf-8")
    assert decisions_validate.outcome(repo.root).findings == ()

    (decisions / "project" / "PRJ-900-a.md").write_text("no front matter\n", encoding="utf-8")
    outcome = decisions_validate.outcome(repo.root)

    assert {finding.location for finding in outcome.findings} == {
        ".pkit/decisions/project/PRJ-900-a.md"
    }
    assert outcome.errors == outcome.findings


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
# Narration is a warning — never an error (ADR-058 point 6).

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


def test_the_validate_member_warns_of_narration_without_failing(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    body = "## Decision\n\n> **Amendment (#20) — the stance splits.**\n"
    _write_record(core / "COR-001-a.md", "COR-001", body, status="accepted")

    outcome = decisions_validate.outcome(project)

    assert outcome.errors == ()
    assert [(f.location, f.severity) for f in outcome.findings] == [
        (".pkit/decisions/core/COR-001-a.md:11", Severity.WARNING)
    ]
    assert "0 error(s), 1 warning(s)." in outcome.summary[0]


def test_cli_warns_of_narration_and_exits_zero(
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
    assert "1 warning(s) of revision narration" in result.output
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


# --- a record's points (COR-058 point 7; #1416) -------------------------------
#
# The decisions member reads each record's points through `record_points` and
# holds each stub to its entry there. A malformed `retired-points`, a stub that
# disagrees with its entry, a live point on a retired id and a successor the
# record neither holds nor retires fail. A duplicate id, a gap and a misspelt
# point heading warn. Each finding names the file and the id.

_REL = ".pkit/decisions/project/PRJ-900-a.md"


def _points_record(decision: str, *, extra: str = "", status: str = "accepted") -> str:
    """A record whose Decision is `decision`, with `extra` lines in its front matter.

    Without `extra` the front matter is six lines, fences included, and a blank
    line follows it, so the Decision's heading is line 12 and its text opens on
    line 14.
    """
    return (
        f"---\nid: PRJ-900\ntitle: A record\nstatus: {status}\ndate: 2026-10-13\n{extra}---\n\n"
        f"## Context\n\nWhy.\n\n## Decision\n\n{decision}\n## Rationale\n\nBecause.\n"
    )


_RETIRED_SIX = 'retired-points:\n  "6": ["7"]\n'

_POINTS_WITH_STUB = (
    "### 5. Fifth\n\nFive.\n\n### 6. Retired\n\nIts content is in point 7.\n\n"
    "### 7. Seventh\n\nSeven.\n"
)


def _numbered(*ids: str) -> str:
    """A point heading `### <id>. Point <id>` and one line of text for each id; four
    lines each."""
    return "".join(f"### {point_id}. Point {point_id}\n\nText.\n\n" for point_id in ids)


def _found(text: str) -> list[tuple[str, Severity]]:
    return [(f.location, f.severity) for f in decisions_validate.check_points(_REL, text)]


def _errors(text: str) -> list[Finding]:
    return [f for f in decisions_validate.check_points(_REL, text) if f.severity.fails]


def test_points_with_a_retired_point_and_its_stub_pass() -> None:
    text = _points_record(_numbered("1", "2", "3", "4") + _POINTS_WITH_STUB, extra=_RETIRED_SIX)
    assert decisions_validate.check_points(_REL, text) == []


def test_a_labelled_retired_point_with_its_stub_passes() -> None:
    decision = (
        "### D1 — First\n\nOne.\n\n### D2 — Retired\n\nIts content is in points D1 and D3.\n\n"
        "### D3 — Third\n\nThree.\n"
    )
    text = _points_record(decision, extra="retired-points:\n  D2: [D1, D3]\n")
    assert decisions_validate.check_points(_REL, text) == []


# --- what fails ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("extra", "names"),
    [
        ("retired-points: [6]\n", "is not a mapping"),
        ('retired-points: "6"\n', "is not a mapping"),
        ('retired-points:\n  "6": ["7"]\n  "6": []\n', "the front matter does not parse"),
    ],
)
def test_a_retired_points_field_that_cannot_be_read_fails_once(extra: str, names: str) -> None:
    """Nothing that rests on the retired ids is checked then, so the stub of 6 raises
    no second error."""
    text = _points_record(_numbered("1", "2", "3", "4") + _POINTS_WITH_STUB, extra=extra)
    errors = _errors(text)
    assert [f.location for f in errors] == [f"{_REL}:/retired-points"]
    assert names in errors[0].message


@pytest.mark.parametrize(
    ("entry", "names"),
    [
        ('  "six": ["2"]\n', "`six` in `retired-points` is no point id"),
        ('  "3": "2"\n', "the successors of `3`"),
        ('  "3": [{"a": 1}]\n', "the successors of `3`"),
    ],
)
def test_a_malformed_entry_fails_naming_its_id(entry: str, names: str) -> None:
    text = _points_record(_numbered("1", "2"), extra=f"retired-points:\n{entry}")
    malformed = [f for f in _errors(text) if f.location == f"{_REL}:/retired-points"]
    assert len(malformed) == 1
    assert names in malformed[0].message


def test_a_retired_id_with_no_stub_fails() -> None:
    text = _points_record(_numbered("1", "2", "3", "4", "5", "7"), extra=_RETIRED_SIX)
    errors = _errors(text)
    assert [f.location for f in errors] == [f"{_REL}#6"]
    assert "retired point `6` has no stub" in errors[0].message
    assert "`### 6. Retired`" in errors[0].message
    assert '"Its content is in point 7."' in errors[0].message


def test_a_stub_whose_id_is_not_retired_fails() -> None:
    text = _points_record(_numbered("1", "2", "3", "4") + _POINTS_WITH_STUB)
    errors = _errors(text)
    assert [f.location for f in errors] == [f"{_REL}#6"]
    assert "the stub of `6` at line 34 retires no id" in errors[0].message


def test_a_stub_beside_a_malformed_entry_says_to_mend_the_entry() -> None:
    """One typo in an entry's id fails the entry, and its stub, which then retires
    no id, points back at the entry rather than asking for a new one."""
    text = _points_record(
        _numbered("1", "2", "3", "4") + _POINTS_WITH_STUB,
        extra='retired-points:\n  "six": ["7"]\n',
    )
    errors = _errors(text)
    assert [f.location for f in errors] == [f"{_REL}:/retired-points", f"{_REL}#6"]
    assert "Mend the malformed entry of `retired-points`" in errors[1].message


def test_a_stub_whose_sentence_differs_from_its_entry_fails() -> None:
    text = _points_record(
        _numbered("1", "2", "3", "4") + _POINTS_WITH_STUB, extra='retired-points:\n  "6": []\n'
    )
    errors = _errors(text)
    assert [f.location for f in errors] == [f"{_REL}#6"]
    assert 'reads "Its content is in point 7."' in errors[0].message
    assert 'Its entry gives "Its content is in no other point."' in errors[0].message


def test_a_live_point_on_a_retired_id_fails_and_names_the_next_unused_number() -> None:
    decision = _numbered("1", "2", "3", "4") + _POINTS_WITH_STUB + "\n### 6. Sixth again\n\nNew.\n"
    errors = _errors(_points_record(decision, extra=_RETIRED_SIX))
    assert [f.location for f in errors] == [f"{_REL}#6"]
    assert "uses a retired id" in errors[0].message
    assert "the next unused number, `8`" in errors[0].message


def test_a_successor_the_record_neither_holds_nor_retires_fails() -> None:
    text = _points_record(
        _numbered("1", "2", "3", "4")
        + _POINTS_WITH_STUB.replace("in point 7.", "in points 7 and 12."),
        extra='retired-points:\n  "6": ["7", "12"]\n',
    )
    errors = _errors(text)
    assert [f.location for f in errors] == [f"{_REL}#6"]
    assert "`12`, a successor of retired point `6`, is neither a point" in errors[0].message


def test_a_retired_id_named_as_its_own_successor_fails() -> None:
    text = _points_record(
        _numbered("1", "2", "3", "4") + _POINTS_WITH_STUB.replace("point 7.", "point 6."),
        extra='retired-points:\n  "6": ["6"]\n',
    )
    errors = _errors(text)
    assert [f.location for f in errors] == [f"{_REL}#6"]
    assert "names itself as its successor" in errors[0].message


def test_a_successor_retired_later_passes() -> None:
    """A successor is live when its entry is written. Its own retirement later
    leaves the earlier entry as it stood (COR-058 point 5)."""
    decision = (
        _numbered("1", "2", "3", "4", "5")
        + "### 6. Retired\n\nIts content is in point 7.\n\n"
        + "### 7. Retired\n\nIts content is in point 8.\n\n"
        + _numbered("8")
    )
    text = _points_record(decision, extra='retired-points:\n  "6": ["7"]\n  "7": ["8"]\n')
    assert decisions_validate.check_points(_REL, text) == []


# --- what warns ----------------------------------------------------------------


def test_a_duplicate_id_warns_and_fails_nothing() -> None:
    text = _points_record(_numbered("1", "2", "2", "3"))
    found = decisions_validate.check_points(_REL, text)
    assert [(f.location, f.severity) for f in found] == [(f"{_REL}#2", Severity.WARNING)]
    assert "2 points take the id `2`, at lines 18 and 22" in found[0].message


def test_a_duplicate_stub_warns() -> None:
    stub = "\n### 6. Retired\n\nIts content is in point 7.\n"
    decision = _numbered("1", "2", "3", "4") + _POINTS_WITH_STUB + stub
    assert _found(_points_record(decision, extra=_RETIRED_SIX)) == [(f"{_REL}#6", Severity.WARNING)]


def test_a_gap_in_the_ids_warns_once_per_run() -> None:
    found = decisions_validate.check_points(
        _REL, _points_record(_numbered("1", "2", "5", "6", "8"))
    )
    assert [(f.location, f.severity) for f in found] == [
        (f"{_REL}#3", Severity.WARNING),
        (f"{_REL}#7", Severity.WARNING),
    ]
    assert "the ids skip `3` to `4`: no point holds them" in found[0].message
    assert "the ids skip `7`: no point holds it" in found[1].message


def test_a_gap_below_a_very_high_id_is_one_run_found_between_neighbours() -> None:
    """The runs are found between the held ids, so a mistyped id far above the rest
    costs one warning, and no walk up to it."""
    found = decisions_validate.check_points(_REL, _points_record(_numbered("1", "1000000000")))
    assert [f.location for f in found] == [f"{_REL}#2"]
    assert "the ids skip `2` to `999999999`" in found[0].message


def test_a_gap_counts_retired_ids() -> None:
    """Retired 6, with its stub, fills the ids between 5 and 7."""
    text = _points_record(_numbered("1", "2", "3", "4") + _POINTS_WITH_STUB, extra=_RETIRED_SIX)
    assert _found(text) == []


def test_a_gap_in_a_series_of_labels_warns_and_numbers_count_apart() -> None:
    decision = "### D1 — First\n\nOne.\n\n### D3 — Third\n\nThree.\n\n" + _numbered("1")
    assert _found(_points_record(decision)) == [(f"{_REL}#D2", Severity.WARNING)]


@pytest.mark.parametrize(
    ("heading", "token"),
    [("### 16 - Title", "16"), ("### 5.1 Title", "5.1"), ("### v1 scope: the first", "v1")],
)
def test_a_misspelt_point_heading_warns(heading: str, token: str) -> None:
    text = _points_record(_numbered("1", "2") + f"{heading}\n\nText.\n")
    found = decisions_validate.check_points(_REL, text)
    assert [(f.location, f.severity) for f in found] == [(f"{_REL}#{token}", Severity.WARNING)]
    assert f"the heading `{heading}` at line 22 opens with `{token}`" in found[0].message


# --- what is not read ------------------------------------------------------------


def test_a_projects_own_front_matter_fields_pass() -> None:
    """Only the new field's shape is read, so a field the methodology never names, of
    any shape, raises nothing (COR-058 point 7)."""
    extra = "owner: team-a\ntags: [x, y]\nreview:\n  every: 90d\n  by: [alice]\n" + _RETIRED_SIX
    text = _points_record(_numbered("1", "2", "3", "4") + _POINTS_WITH_STUB, extra=extra)
    assert decisions_validate.check_points(_REL, text) == []


@pytest.mark.parametrize("extra", ["retired-points:\n", "retired-points: {}\n"])
def test_an_empty_retired_points_retires_nothing_and_passes(extra: str) -> None:
    text = _points_record(_numbered("1", "2"), extra=extra)
    assert decisions_validate.check_points(_REL, text) == []


def test_front_matter_that_does_not_parse_without_the_field_raises_nothing() -> None:
    text = _points_record(_numbered("1", "2"), extra="owner: [unclosed\n")
    assert decisions_validate.check_points(_REL, text) == []


@pytest.mark.parametrize(
    "decision",
    [
        "1. **First.** One.\n2. **Second.** Two.\n4. **Fourth.** Four.\n",
        "**1. First.** One.\n\n**3. Third.** Three.\n\n**3. Third again.** Three.\n",
        "**D1 — First.** One.\n\n**D3 — Third.** Three.\n",
        "### Group\n\n1. **First.** One.\n\n### Another\n\n2. **Second.** Two.\n",
    ],
)
def test_a_record_in_list_form_raises_nothing(decision: str) -> None:
    """A project's record not yet converted keeps working: its list numbers are not
    permanent, so nothing fails on them and no gap is read (COR-058 point 9)."""
    assert decisions_validate.check_points(_REL, _points_record(decision)) == []


def test_the_member_reads_points_and_holds_stubs_through_record_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No second reading of points: the record is read by `read_points`, and each stub
    is held to its entry by `hold_stubs` (#1414)."""
    from project_kit import record_points

    calls: list[str] = []
    read, hold = record_points.read_points, record_points.hold_stubs

    def reading(text: str) -> record_points.RecordPoints:
        calls.append("read_points")
        return read(text)

    def holding(points: record_points.RecordPoints) -> tuple[record_points.StubMismatch, ...]:
        calls.append("hold_stubs")
        return hold(points)

    monkeypatch.setattr(record_points, "read_points", reading)
    monkeypatch.setattr(record_points, "hold_stubs", holding)
    text = _points_record(_numbered("1", "2", "3", "4") + _POINTS_WITH_STUB, extra=_RETIRED_SIX)
    decisions_validate.check_points(_REL, text)
    assert calls == ["read_points", "hold_stubs"]


# --- the walk, the member and the command ----------------------------------------

_STUB_NOT_RETIRED = "## Decision\n\n" + _numbered("1", "2", "3", "4") + _POINTS_WITH_STUB


def test_point_findings_name_the_file_and_the_id_in_every_id_space(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-001-a.md", "COR-001", _STUB_NOT_RETIRED)
    capability = _make_capability(project, "alpha")
    _write_record(capability / "DEC-001-a.md", "DEC-001", _STUB_NOT_RETIRED)
    assert [f.location for f in decisions_validate.point_findings(project)] == [
        ".pkit/decisions/core/COR-001-a.md#6",
        ".pkit/capabilities/alpha/decisions/DEC-001-a.md#6",
    ]


def test_a_superseded_record_is_not_checked_for_points(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    body = f"*Superseded by [COR-002].*\n\n{_STUB_NOT_RETIRED}"
    _write_record(core / "COR-001-a.md", "COR-001", body, status="superseded")
    assert decisions_validate.point_findings(project) == ()


def test_a_synced_copy_is_not_checked_for_points_and_the_projects_own_record_is(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The project cannot mend a record it receives by sync, which is checked where it
    is authored (COR-058 point 7)."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    decisions = repo.root / ".pkit" / "decisions"
    _write_record(decisions / "core" / "COR-900-a.md", "COR-900", _STUB_NOT_RETIRED)
    capability = repo.root / ".pkit" / "capabilities" / "living-docs" / "decisions"
    _write_record(capability / "DEC-900-a.md", "DEC-900", _STUB_NOT_RETIRED)
    _write_record(decisions / "project" / "PRJ-900-a.md", "PRJ-900", _STUB_NOT_RETIRED)

    found = decisions_validate.point_findings(repo.root)

    assert [f.location for f in found] == [".pkit/decisions/project/PRJ-900-a.md#6"]


def test_the_validate_member_fails_on_a_point_error_and_not_on_a_warning(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-001-a.md", "COR-001", _STUB_NOT_RETIRED)
    _write_record(core / "COR-002-b.md", "COR-002", "## Decision\n\n" + _numbered("1", "3"))

    outcome = decisions_validate.outcome(project)

    assert [(f.location, f.severity) for f in outcome.findings] == [
        (".pkit/decisions/core/COR-001-a.md#6", Severity.ERROR),
        (".pkit/decisions/core/COR-002-b.md#2", Severity.WARNING),
    ]
    assert "1 error(s), 1 warning(s)." in outcome.summary[0]


def test_cli_fails_on_a_point_error(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    _write_record(
        project / ".pkit" / "decisions" / "core" / "COR-001-a.md", "COR-001", _STUB_NOT_RETIRED
    )
    monkeypatch.chdir(project)
    result = CliRunner().invoke(main, ["decisions", "validate"])
    assert result.exit_code != 0
    assert "1 error(s) and 0 warning(s) on records' points" in result.output
    assert ".pkit/decisions/core/COR-001-a.md#6" in result.output
    assert "1 error(s) on records' points found." in result.output


def test_cli_warns_of_a_point_and_exits_zero(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    body = "## Decision\n\n### 16 - Title\n\nText.\n"
    _write_record(project / ".pkit" / "decisions" / "core" / "COR-001-a.md", "COR-001", body)
    monkeypatch.chdir(project)
    result = CliRunner().invoke(main, ["decisions", "validate"])
    assert result.exit_code == 0, result.output
    assert "0 error(s) and 1 warning(s) on records' points" in result.output
    assert ".pkit/decisions/core/COR-001-a.md#16" in result.output


# --- what the numbering check shares ------------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "space"),
    [
        (".pkit/decisions/core/COR-001-a.md", "core"),
        (".pkit/decisions/project/PRJ-001-a.md", "project"),
        ("docs/adr/ADR-001-a.md", "adr"),
        (".pkit/capabilities/alpha/decisions/DEC-001-a.md", "capability:alpha"),
        (".pkit/decisions/core/README.md", None),
        (".pkit/decisions/core/sub/COR-001-a.md", None),
        (".pkit/decisions/core/COR-001-a.txt", None),
        ("docs/COR-001-a.md", None),
    ],
)
def test_a_records_id_space_is_read_from_its_path(rel: str, space: str | None) -> None:
    """The numbering check reads records at a commit, where no folder is on disk, so it
    asks which file is a record by its path alone."""
    assert decisions_validate.record_space(rel, "docs/adr") == space


def test_the_records_found_on_disk_are_those_their_paths_name(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-001-a.md", "COR-001")
    capability = _make_capability(project, "alpha")
    _write_record(capability / "DEC-001-a.md", "DEC-001")
    found = decisions_validate.discover_decision_records(project)
    adr = decisions_validate.adr_folder(project)
    assert [
        decisions_validate.record_space(record.path.relative_to(project).as_posix(), adr)
        for record in found
    ] == [record.id_space for record in found]
    assert [decisions_validate.record_id_of(r.path.read_text()) for r in found] == [
        "COR-001",
        "DEC-001",
    ]


@pytest.mark.parametrize(
    ("held", "point_id", "unused"),
    [
        (["1", "2", "6"], "3", "7"),
        (["1", "D1", "D4"], "D2", "D5"),
        (["1", "2"], "D1", "D1"),
    ],
)
def test_the_next_unused_id_is_one_past_the_highest_of_its_series(
    held: list[str], point_id: str, unused: str
) -> None:
    assert decisions_validate.next_unused(held, point_id) == unused
