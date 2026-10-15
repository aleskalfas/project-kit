"""Tests for `pkit new decision` (the Python port of the bash dispatcher's `cmd_new_decision`)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import decisions, decisions_validate, default_branch, record_points
from project_kit import project_config as pc
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, GitRepo, MakeAdopterRepo


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Synthesise a minimal project tree with `.pkit/decisions/{core,project}/`."""
    (tmp_path / ".pkit" / "decisions" / "core").mkdir(parents=True)
    (tmp_path / ".pkit" / "decisions" / "project").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin `decisions._today()` so frontmatter dates are deterministic."""
    monkeypatch.setattr(decisions, "_today", lambda: "2026-05-09")


@pytest.fixture(autouse=True)
def fixed_git_author(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin git config user.name + user.email lookups so author is deterministic."""

    def _fake_git_config(key: str) -> str:
        return {"user.name": "Test Author", "user.email": "test@example.com"}.get(key, "")

    monkeypatch.setattr(decisions, "_git_config", _fake_git_config)


def test_stamp_decision_writes_cor_in_core_namespace(kit_target: Path) -> None:
    target = decisions.stamp_decision(kit_target, namespace="core", slug="my-rule")
    assert target.name == "COR-001-my-rule.md"
    assert target.parent == kit_target / ".pkit" / "decisions" / "core"

    content = target.read_text(encoding="utf-8")
    assert "id: COR-001" in content
    assert "title: <short imperative title>" in content
    assert "status: proposed" in content
    assert "date: 2026-05-09" in content
    assert "author: Test Author <test@example.com>" in content
    for header in ("## Context", "## Decision", "## Rationale", "## Implications"):
        assert header in content


def test_stamp_decision_writes_its_first_point_as_a_point_heading(kit_target: Path) -> None:
    """The stamped record's Decision holds point 1 as a heading (COR-058 point 1), so a new record
    starts with its points in the heading form: no list form, and nothing validation reports."""
    target = decisions.stamp_decision(kit_target, namespace="project", slug="pointed")
    content = target.read_text(encoding="utf-8")

    points = record_points.read_points(content)
    assert points.level == 3
    assert [(point.id, point.title) for point in points.points] == [("1", "Point title")]
    assert not points.in_list_form
    assert points.misspelt == ()
    assert decisions_validate.check_points(target.name, content) == []


def test_stamp_decision_puts_the_point_heading_in_the_decision_only(kit_target: Path) -> None:
    """The point heading sits under `## Decision`, before `## Rationale`. A numbered heading
    anywhere else would be no point, so a record stamped with it there would start with none."""
    content = decisions.stamp_decision(kit_target, namespace="core", slug="placed").read_text(
        encoding="utf-8"
    )
    decision, point, rationale = (
        content.index("## Decision\n"),
        content.index("### 1. Point title\n"),
        content.index("## Rationale\n"),
    )
    assert decision < point < rationale
    assert content.count("### ") == 1


README = Path(__file__).resolve().parent.parent / ".pkit" / "decisions" / "README.md"


def _schema_example() -> str:
    """The record the decisions README's "Schema" section shows, its fenced example."""
    text = README.read_text(encoding="utf-8")
    section = text[text.index("\n## Schema\n") :]
    start = section.index("```markdown\n") + len("```markdown\n")
    return section[start : section.index("\n```\n", start) + 1]


def test_readme_schema_example_is_a_record_validation_passes() -> None:
    """The README's example writes its points as headings and retires one, with the entry and
    the stub agreeing word for word (COR-058 points 1, 4 and 6), so a reader who copies the
    form writes a record validation passes."""
    example = _schema_example()
    points = record_points.read_points(example)
    assert [point.id for point in points.points] == ["1", "3"]
    assert [stub.id for stub in points.stubs] == ["2"]
    assert dict(points.retired) == {"2": ("3",)}
    assert decisions_validate.check_points("PRJ-NNN-example.md", example) == []


def test_readme_schema_example_would_fail_with_a_stub_out_of_step() -> None:
    """The check the example passes is a real one: a stub whose sentence names another point
    than its entry fails validation."""
    example = _schema_example().replace("Its content is in point 3.", "Its content is in point 1.")
    findings = decisions_validate.check_points("PRJ-NNN-example.md", example)
    assert findings
    assert all(finding.severity.fails for finding in findings)


def test_stamp_decision_writes_prj_in_project_namespace(kit_target: Path) -> None:
    target = decisions.stamp_decision(kit_target, namespace="project", slug="my-decision")
    assert target.name == "PRJ-001-my-decision.md"
    assert "id: PRJ-001" in target.read_text(encoding="utf-8")


def test_stamp_decision_picks_next_number_per_namespace(kit_target: Path) -> None:
    core_dir = kit_target / ".pkit" / "decisions" / "core"
    (core_dir / "COR-001-first.md").write_text("dummy", encoding="utf-8")
    (core_dir / "COR-002-second.md").write_text("dummy", encoding="utf-8")
    (core_dir / "COR-005-fifth.md").write_text("dummy", encoding="utf-8")

    target = decisions.stamp_decision(kit_target, namespace="core", slug="next")
    assert target.name == "COR-006-next.md"


def test_stamp_decision_numbering_is_independent_across_namespaces(kit_target: Path) -> None:
    core_dir = kit_target / ".pkit" / "decisions" / "core"
    (core_dir / "COR-001-x.md").write_text("dummy", encoding="utf-8")
    (core_dir / "COR-002-y.md").write_text("dummy", encoding="utf-8")

    target = decisions.stamp_decision(kit_target, namespace="project", slug="first-prj")
    # No PRJs exist yet → next number is 1, not 3.
    assert target.name == "PRJ-001-first-prj.md"


def test_stamp_decision_refuses_invalid_slug(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="kebab-case"):
        decisions.stamp_decision(kit_target, namespace="core", slug="Has_Underscore")


def test_stamp_decision_refuses_duplicate_slug(kit_target: Path) -> None:
    decisions.stamp_decision(kit_target, namespace="core", slug="dupe")
    with pytest.raises(click.ClickException, match="already exists"):
        decisions.stamp_decision(kit_target, namespace="core", slug="dupe")


def test_stamp_decision_refuses_when_namespace_dir_missing(tmp_path: Path) -> None:
    # Only .pkit/ exists; no decisions/<ns>/ subdir.
    (tmp_path / ".pkit").mkdir()
    with pytest.raises(click.ClickException, match="does not exist"):
        decisions.stamp_decision(tmp_path, namespace="core", slug="x")


def _empty_git_config(_key: str) -> str:
    return ""


def _name_only_git_config(key: str) -> str:
    return "Just A Name" if key == "user.name" else ""


def test_stamp_decision_falls_back_to_unknown_author_when_git_unset(
    kit_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(decisions, "_git_config", _empty_git_config)
    target = decisions.stamp_decision(kit_target, namespace="core", slug="anonymous")
    assert "author: <unknown>" in target.read_text(encoding="utf-8")


def test_stamp_decision_uses_name_only_when_email_missing(
    kit_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(decisions, "_git_config", _name_only_git_config)
    target = decisions.stamp_decision(kit_target, namespace="core", slug="name-only")
    assert "author: Just A Name" in target.read_text(encoding="utf-8")


# ---------------------------------------------------------------- ADR namespace


def _write_overlay(kit_target: Path, content: str) -> Path:
    overlay = kit_target / ".pkit" / "agents" / "project" / "overlay.yaml"
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text(content, encoding="utf-8")
    return overlay


def test_stamp_decision_writes_adr_at_overlay_path(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - docs/architecture/decisions/\n")
    adr_dir = kit_target / "docs" / "architecture" / "decisions"
    adr_dir.mkdir(parents=True)

    target = decisions.stamp_decision(kit_target, namespace="adr", slug="first-adr")
    assert target.name == "ADR-001-first-adr.md"
    assert target.parent == adr_dir
    content = target.read_text(encoding="utf-8")
    assert "id: ADR-001" in content
    assert "status: proposed" in content
    for header in ("## Context", "## Decision", "## Rationale", "## Implications"):
        assert header in content


def test_stamp_decision_adr_numbering_is_independent(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - docs/architecture/decisions/\n")
    adr_dir = kit_target / "docs" / "architecture" / "decisions"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-existing.md").write_text("dummy", encoding="utf-8")
    (adr_dir / "ADR-003-skip.md").write_text("dummy", encoding="utf-8")
    # COR records in .pkit/decisions/core/ must not affect ADR numbering.
    (kit_target / ".pkit" / "decisions" / "core" / "COR-007-x.md").write_text(
        "dummy", encoding="utf-8"
    )

    target = decisions.stamp_decision(kit_target, namespace="adr", slug="next-adr")
    assert target.name == "ADR-004-next-adr.md"


def test_stamp_decision_adr_refuses_when_overlay_missing(kit_target: Path) -> None:
    # No overlay.yaml seeded.
    with pytest.raises(click.ClickException, match="overlay"):
        decisions.stamp_decision(kit_target, namespace="adr", slug="orphan")


def test_stamp_decision_adr_derives_and_records_when_overlay_lacks_adr_records(
    kit_target: Path,
) -> None:
    """With the category unset the location is derived from the internal root and
    recorded before the record is stamped there (COR-049 points 3 to 5)."""
    overlay = _write_overlay(kit_target, "workflow-docs:\n  - README.md\n")
    said: list[str] = []
    target = decisions.stamp_decision(kit_target, namespace="adr", slug="no-key", say=said.append)
    assert target == (kit_target / "docs" / "architecture" / "decisions").resolve() / (
        "ADR-001-no-key.md"
    )
    assert "adr-records:\n  - docs/architecture/decisions\n" in overlay.read_text(encoding="utf-8")
    assert said[0].startswith("recorded adr-records = docs/architecture/decisions  (")


def test_stamp_decision_adr_refuses_when_adr_records_empty_list(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records: []\n")
    with pytest.raises(click.ClickException, match="missing or empty"):
        decisions.stamp_decision(kit_target, namespace="adr", slug="empty-list")


def test_stamp_decision_adr_refuses_when_path_inside_pkit(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - .pkit/decisions/adr/\n")
    (kit_target / ".pkit" / "decisions" / "adr").mkdir(parents=True)
    with pytest.raises(click.ClickException, match=r"outside \.pkit/"):
        decisions.stamp_decision(kit_target, namespace="adr", slug="inside-pkit")


def test_stamp_decision_adr_refuses_when_directory_missing(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - docs/architecture/decisions/\n")
    # Directory deliberately not created.
    with pytest.raises(click.ClickException, match="does not exist"):
        decisions.stamp_decision(kit_target, namespace="adr", slug="no-dir")


def test_stamp_decision_adr_refuses_duplicate_slug(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - docs/architecture/decisions/\n")
    (kit_target / "docs" / "architecture" / "decisions").mkdir(parents=True)
    decisions.stamp_decision(kit_target, namespace="adr", slug="dupe")
    with pytest.raises(click.ClickException, match="already exists"):
        decisions.stamp_decision(kit_target, namespace="adr", slug="dupe")


def test_resolve_adr_records_dir_returns_absolute_path(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - docs/architecture/decisions/\n")
    adr_dir = kit_target / "docs" / "architecture" / "decisions"
    adr_dir.mkdir(parents=True)
    resolved = decisions.resolve_adr_records_dir(kit_target)
    assert resolved == adr_dir.resolve()


# ---------------------------------------------------------------- capability DEC namespace


def _make_capability(kit_target: Path, name: str, *, with_decisions: bool = False) -> Path:
    """Create a minimal valid capability dir; return its path."""
    cap_dir = kit_target / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True)
    (cap_dir / "package.yaml").write_text(
        f"component:\n  kind: capability\n  name: {name}\n  version: 0.1.0\n",
        encoding="utf-8",
    )
    if with_decisions:
        (cap_dir / "decisions").mkdir()
    return cap_dir


def test_stamp_decision_writes_dec_in_capability_namespace(kit_target: Path) -> None:
    _make_capability(kit_target, "my-cap")
    target = decisions.stamp_decision(kit_target, namespace="my-cap", slug="first-dec")
    assert target.name == "DEC-001-first-dec.md"
    assert target.parent == kit_target / ".pkit" / "capabilities" / "my-cap" / "decisions"

    content = target.read_text(encoding="utf-8")
    assert "id: DEC-001" in content
    assert "title: <short imperative title>" in content
    assert "status: proposed" in content
    assert "date: 2026-05-09" in content
    assert "author: Test Author <test@example.com>" in content
    for header in ("## Context", "## Decision", "## Rationale", "## Implications"):
        assert header in content


def test_stamp_decision_dec_numbering_is_per_capability(kit_target: Path) -> None:
    cap_dir = _make_capability(kit_target, "alpha", with_decisions=True)
    dec_dir = cap_dir / "decisions"
    (dec_dir / "DEC-001-a.md").write_text("dummy", encoding="utf-8")
    (dec_dir / "DEC-004-b.md").write_text("dummy", encoding="utf-8")

    target = decisions.stamp_decision(kit_target, namespace="alpha", slug="next-dec")
    assert target.name == "DEC-005-next-dec.md"


def test_stamp_decision_dec_numbering_independent_across_capabilities(kit_target: Path) -> None:
    alpha = _make_capability(kit_target, "alpha", with_decisions=True)
    (alpha / "decisions" / "DEC-009-a.md").write_text("dummy", encoding="utf-8")
    _make_capability(kit_target, "beta")

    # beta has no DECs yet → starts at 1, unaffected by alpha's DEC-009.
    target = decisions.stamp_decision(kit_target, namespace="beta", slug="first")
    assert target.name == "DEC-001-first.md"


def test_stamp_decision_creates_decisions_dir_on_first_dec(kit_target: Path) -> None:
    _make_capability(kit_target, "fresh")  # no decisions/ subdir yet
    target = decisions.stamp_decision(kit_target, namespace="fresh", slug="first")
    assert target.parent.is_dir()
    assert target.name == "DEC-001-first.md"


def test_stamp_decision_refuses_unknown_capability(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="unknown namespace"):
        decisions.stamp_decision(kit_target, namespace="does-not-exist", slug="x")


def test_stamp_decision_refuses_capability_without_package_yaml(kit_target: Path) -> None:
    # A directory under capabilities/ but missing package.yaml is not a capability.
    (kit_target / ".pkit" / "capabilities" / "bogus").mkdir(parents=True)
    with pytest.raises(click.ClickException, match="unknown namespace"):
        decisions.stamp_decision(kit_target, namespace="bogus", slug="x")


def test_stamp_decision_refuses_a_path_as_capability_name(kit_target: Path) -> None:
    """A namespace walking out of `.pkit/capabilities/` names no capability, package.yaml or not."""
    adapter = kit_target / ".pkit" / "adapters" / "some-adapter"
    adapter.mkdir(parents=True)
    (adapter / "package.yaml").write_text("component:\n  kind: adapter\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="unknown namespace"):
        decisions.stamp_decision(kit_target, namespace="../adapters/some-adapter", slug="x")
    assert not (adapter / "decisions").exists()


def test_stamp_decision_dec_refuses_duplicate_slug(kit_target: Path) -> None:
    _make_capability(kit_target, "cap")
    decisions.stamp_decision(kit_target, namespace="cap", slug="dupe")
    with pytest.raises(click.ClickException, match="already exists"):
        decisions.stamp_decision(kit_target, namespace="cap", slug="dupe")


# ------------------------------------- `pkit new decision adr`: the documentation roots (COR-049)


OVERLAY = Path(".pkit") / "agents" / "project" / "overlay.yaml"
DERIVED = "docs/architecture/decisions"

#: What the command says when it records the location derived from the default root.
DERIVED_NOTICE = (
    "recorded adr-records = docs/architecture/decisions  (.pkit/agents/project/overlay.yaml)\n"
    "  derived from the internal root, docs (default). Agents that reference adr-records "
    "now reach this folder. To change it: edit that entry, then pkit sync.\n"
    "run `pkit sync` to deploy the agent(s) that reference adr-records.\n"
)

#: What a run off a terminal without `--yes` says over a folder holding documents.
REFUSAL = (
    "refusing to write .pkit/agents/project/overlay.yaml without consent: stdin is not a "
    "terminal and --yes was not given (COR-049 point 5).\n"
    "These folders already hold documents; recording each category puts them within "
    "reach of the agents named:\n"
    "  adr-records = docs/architecture/decisions  (reached by architect)\n"
    "Nothing was written. To consent non-interactively, run:\n"
    "  pkit new decision adr second --yes\n"
)


def _unset(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """An adopter whose overlay leaves `adr-records` unset."""
    repo = make_adopter_repo()
    (repo.root / OVERLAY).write_text("workflow-docs:\n  - README.md\n", encoding="utf-8")
    return repo


def _holding_documents(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """`adr-records` unset, and the derived folder already holding a record."""
    repo = _unset(make_adopter_repo)
    (repo.root / DERIVED).mkdir(parents=True)
    (repo.root / DERIVED / "ADR-001-existing.md").write_text("# kept\n", encoding="utf-8")
    return repo


def _set_internal_root(repo: AdopterRepo, root: str) -> None:
    path = pc.project_config_path(repo.root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"docs:\n  internal: {root}\n", encoding="utf-8")


def _told(record_id: str) -> str:
    """The notice line of a stamp in an adopter with no commit yet, whose default branch
    holds nothing (COR-054 point 4)."""
    return _unborn(record_id) + "\n"


def _new_adr(
    monkeypatch: pytest.MonkeyPatch, *args: str, terminal: bool, answer: str | None = None
) -> tuple[int, str]:
    """Run `pkit new decision adr` at a terminal or off one; return (exit code, output)."""
    monkeypatch.setattr(pc, "stdin_is_tty", lambda: terminal)
    result = CliRunner().invoke(
        main, ["--color", "never", "new", "decision", "adr", *args], input=answer
    )
    return result.exit_code, result.output


def _tree(root: Path) -> dict[str, bytes | None]:
    """Every path under `root` outside `.git`, a file's bytes or None for a dir — what
    "nothing was written" is held to."""
    return {
        p.relative_to(root).as_posix(): (p.read_bytes() if p.is_file() else None)
        for p in sorted(root.rglob("*"))
        if ".git" not in p.relative_to(root).parts
    }


@pytest.mark.parametrize("terminal", [False, True])
def test_new_adr_with_the_category_unset_creates_the_derived_folder_records_and_stamps(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch, terminal: bool
) -> None:
    """A folder the command creates hands no document over: recorded without asking, at
    a terminal or off one, and the command says what it recorded (COR-049 point 5)."""
    repo = _unset(make_adopter_repo)

    code, output = _new_adr(monkeypatch, "first", terminal=terminal)

    assert code == 0, output
    assert output == _told("ADR-001") + DERIVED_NOTICE + f"Stamped: {DERIVED}/ADR-001-first.md\n"
    assert (repo.root / DERIVED / "ADR-001-first.md").is_file()
    assert (
        "# --- adr-records: recorded by `pkit new decision adr` from the documentation roots "
        "(COR-049 point 5) ---\n"
        "adr-records:\n"
        "  - docs/architecture/decisions\n"
    ) in (repo.root / OVERLAY).read_text(encoding="utf-8")


def test_new_adr_over_an_empty_derived_folder_records_without_asking(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _unset(make_adopter_repo)
    (repo.root / DERIVED).mkdir(parents=True)

    code, output = _new_adr(monkeypatch, "first", terminal=False)

    assert code == 0, output
    assert output == _told("ADR-001") + DERIVED_NOTICE + f"Stamped: {DERIVED}/ADR-001-first.md\n"
    assert (repo.root / DERIVED / "ADR-001-first.md").is_file()


def test_new_adr_derives_from_the_declared_internal_root(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _unset(make_adopter_repo)
    _set_internal_root(repo, "tech-docs")

    code, output = _new_adr(monkeypatch, "first", terminal=False)

    assert code == 0, output
    assert output.startswith(
        _told("ADR-001") + "recorded adr-records = tech-docs/architecture/decisions  "
        "(.pkit/agents/project/overlay.yaml)\n"
        "  derived from the internal root, tech-docs (explicit). "
    )
    assert output.endswith("Stamped: tech-docs/architecture/decisions/ADR-001-first.md\n")
    assert not (repo.root / "docs" / "architecture").exists()


def test_new_adr_over_a_folder_holding_documents_off_a_terminal_refuses_without_yes(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recording over existing documents hands them to every agent that references the
    category: off a terminal without `--yes` the run records nothing and stamps nothing,
    exit 1, naming the command with `--yes`."""
    repo = _holding_documents(make_adopter_repo)
    before = _tree(repo.root)

    code, output = _new_adr(monkeypatch, "second", terminal=False)

    assert code == 1
    assert REFUSAL in output
    assert _tree(repo.root) == before


def test_new_adr_over_a_folder_holding_documents_with_yes_records_and_stamps(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _holding_documents(make_adopter_repo)

    code, output = _new_adr(monkeypatch, "second", "--yes", terminal=False)

    assert code == 0, output
    assert output == _told("ADR-002") + DERIVED_NOTICE + f"Stamped: {DERIVED}/ADR-002-second.md\n"
    assert (repo.root / DERIVED / "ADR-001-existing.md").read_text(encoding="utf-8") == "# kept\n"
    assert "adr-records:\n  - docs/architecture/decisions\n" in (repo.root / OVERLAY).read_text(
        encoding="utf-8"
    )


def test_new_adr_at_a_terminal_asks_once_and_a_no_records_and_stamps_nothing(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _holding_documents(make_adopter_repo)
    before = _tree(repo.root)

    code, output = _new_adr(monkeypatch, "second", terminal=True, answer="n\n")

    assert code == 1
    assert output.count("[Y/n]") == 1
    assert _tree(repo.root) == before


def test_new_adr_at_a_terminal_a_yes_records_and_stamps(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one question says what the recording puts within reach, and of which agents."""
    repo = _holding_documents(make_adopter_repo)

    code, output = _new_adr(monkeypatch, "second", terminal=True, answer="y\n")

    assert code == 0, output
    assert output == (
        "These folders already hold documents; recording each category puts them within "
        "reach of the agents named:\n"
        "  adr-records = docs/architecture/decisions  (reached by architect)\n"
        "Record it in .pkit/agents/project/overlay.yaml? [Y/n]: y\n"
        + _told("ADR-002")
        + DERIVED_NOTICE
        + f"Stamped: {DERIVED}/ADR-002-second.md\n"
    )
    assert (repo.root / DERIVED / "ADR-002-second.md").is_file()


def test_new_adr_a_root_change_after_recording_moves_nothing(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Once recorded the location is explicit: a later root change, and a folder now
    holding documents, change nothing — no recording, no question (COR-049 point 6)."""
    repo = _unset(make_adopter_repo)
    assert _new_adr(monkeypatch, "first", terminal=False)[0] == 0
    _set_internal_root(repo, "handbook")
    overlay = (repo.root / OVERLAY).read_text(encoding="utf-8")

    code, output = _new_adr(monkeypatch, "second", terminal=False)

    assert code == 0, output
    assert output == _told("ADR-002") + f"Stamped: {DERIVED}/ADR-002-second.md\n"
    assert (repo.root / OVERLAY).read_text(encoding="utf-8") == overlay
    assert not (repo.root / "handbook").exists()


def test_new_adr_an_explicit_value_wins_over_the_root(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo()
    _set_internal_root(repo, "tech-docs")
    (repo.root / OVERLAY).write_text("adr-records:\n  - decisions/adr/\n", encoding="utf-8")
    (repo.root / "decisions" / "adr").mkdir(parents=True)
    (repo.root / "decisions" / "adr" / "ADR-001-existing.md").write_text("x", encoding="utf-8")

    code, output = _new_adr(monkeypatch, "second", terminal=False)

    assert code == 0, output
    assert output == _told("ADR-002") + "Stamped: decisions/adr/ADR-002-second.md\n"
    assert (repo.root / OVERLAY).read_text(encoding="utf-8") == "adr-records:\n  - decisions/adr/\n"
    assert not (repo.root / "tech-docs").exists()


def test_new_adr_refuses_a_location_derived_inside_pkit(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path inside the methodology's own tree is refused, derived as explicit."""
    repo = _unset(make_adopter_repo)
    _set_internal_root(repo, ".pkit/docs")
    before = _tree(repo.root)

    code, output = _new_adr(monkeypatch, "first", "--yes", terminal=False)

    assert code == 1
    assert (
        "adr-records path '.pkit/docs/architecture/decisions' (derived from the internal "
        "documentation root, .pkit/docs) is inside .pkit/."
    ) in output
    assert _tree(repo.root) == before


# --------------------------------- the number: past the default branch too (COR-054, #1501)


#: Each namespace, the folder it stamps into and its prefix, in the project `_git_project` builds.
NAMESPACES = [
    ("core", ".pkit/decisions/core", "COR"),
    ("project", ".pkit/decisions/project", "PRJ"),
    ("adr", "docs/adr", "ADR"),
    ("cap", ".pkit/capabilities/cap/decisions", "DEC"),
]
NAMESPACE_IDS = [namespace for namespace, _folder, _prefix in NAMESPACES]

#: The backbone configuration, where the default branch is declared.
CONFIG = pc.PROJECT_CONFIG_RELPATH.as_posix()

#: What the stamp says after the reason the default branch was not read.
ALONE = (
    "is numbered past the working tree alone, so a record on the default branch may already "
    "hold its number (COR-054 point 4)."
)


def _record(folder: str, prefix: str, number: int, slug: str) -> dict[str, str | None]:
    return {f"{folder}/{prefix}-{number:03d}-{slug}.md": f"---\nid: {prefix}-{number:03d}\n---\n"}


def _git_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GitRepo:
    """A git project on `main`, with no remote, whose first commit holds record 001 in every
    namespace's folder, the capability `cap` and an overlay naming `docs/adr/` as
    `adr-records`. No `$PKIT_CHECK_BASE` a developer set reaches it."""
    monkeypatch.delenv(default_branch.CHECK_BASE_ENV, raising=False)
    repo = GitRepo.init(tmp_path / "work")
    files: dict[str, str | None] = {
        OVERLAY.as_posix(): "adr-records:\n  - docs/adr/\n",
        ".pkit/capabilities/cap/package.yaml": (
            "component:\n  kind: capability\n  name: cap\n  version: 0.1.0\n"
        ),
    }
    for _namespace, folder, prefix in NAMESPACES:
        files |= _record(folder, prefix, 1, "first")
    repo.commit("first", files)
    return repo


def _with_remote(repo: GitRepo, tmp_path: Path) -> None:
    """A remote `origin` holding the repository as it stands, fetched."""
    remote = tmp_path / "origin.git"
    repo.git("clone", "-q", "--bare", str(repo.root), str(remote))
    repo.git("remote", "add", "origin", str(remote))
    repo.git("fetch", "-q", "origin")


def _cut_before(repo: GitRepo, files: dict[str, str | None]) -> None:
    """`topic` cut from `main`, then `files` committed on `main` — another branch's work
    merged — and `topic` checked out again, its working tree without them."""
    repo.checkout("topic", create=True)
    repo.checkout("main")
    repo.commit("another branch's work", files)
    repo.checkout("topic")


def _stamp(repo: GitRepo, namespace: str, slug: str = "next") -> tuple[str, list[str]]:
    """Stamp a record; return its file name and what the stamp said of the default branch."""
    said: list[str] = []
    target = decisions.stamp_decision(repo.root, namespace=namespace, slug=slug, warn=said.append)
    return target.name, said


@pytest.mark.parametrize(("namespace", "folder", "prefix"), NAMESPACES, ids=NAMESPACE_IDS)
def test_a_record_only_the_default_branch_holds_is_numbered_past(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, namespace: str, folder: str, prefix: str
) -> None:
    """A branch cut before another branch's record merged numbers past that record, so the
    two never take one number (COR-054 point 3)."""
    repo = _git_project(tmp_path, monkeypatch)
    _cut_before(repo, _record(folder, prefix, 2, "landed"))
    _with_remote(repo, tmp_path)
    assert not list((repo.root / folder).glob(f"{prefix}-002-*.md"))

    assert _stamp(repo, namespace) == (f"{prefix}-003-next.md", [])


@pytest.mark.parametrize(("namespace", "folder", "prefix"), NAMESPACES, ids=NAMESPACE_IDS)
def test_a_record_only_the_working_tree_holds_is_numbered_past(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, namespace: str, folder: str, prefix: str
) -> None:
    """The working tree counts, an uncommitted record too: the number goes past both sides."""
    repo = _git_project(tmp_path, monkeypatch)
    _cut_before(repo, _record(folder, prefix, 2, "landed"))
    _with_remote(repo, tmp_path)
    repo.write(_record(folder, prefix, 7, "uncommitted"))

    assert _stamp(repo, namespace) == (f"{prefix}-008-next.md", [])


def test_only_the_namespace_s_own_folder_counts_on_the_default_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A record of another id-space, of another capability, or in a folder beneath the
    namespace's takes no number of it."""
    repo = _git_project(tmp_path, monkeypatch)
    _cut_before(
        repo,
        {
            ".pkit/decisions/core/PRJ-009-misplaced.md": "x\n",
            ".pkit/decisions/project/old/PRJ-008-nested.md": "x\n",
            ".pkit/capabilities/other/decisions/DEC-009-other.md": "x\n",
        },
    )
    _with_remote(repo, tmp_path)

    assert _stamp(repo, "project")[0] == "PRJ-002-next.md"
    assert _stamp(repo, "cap")[0] == "DEC-002-next.md"


@pytest.mark.parametrize("named", ["ahead", "nowhere"])
def test_the_variable_a_pipeline_sets_for_its_checks_never_changes_the_number(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, named: str
) -> None:
    """`$PKIT_CHECK_BASE` names a comparison's base, never what allocation reads (COR-054
    point 3): a base holding a higher number does not raise the number, and one that
    resolves nowhere is neither read nor reported."""
    repo = _git_project(tmp_path, monkeypatch)
    _cut_before(repo, _record(".pkit/decisions/project", "PRJ", 2, "landed"))
    _with_remote(repo, tmp_path)
    repo.checkout("ahead", create=True)
    repo.commit("ahead", _record(".pkit/decisions/project", "PRJ", 9, "ahead"))
    repo.checkout("topic")
    monkeypatch.setenv(default_branch.CHECK_BASE_ENV, named)

    assert _stamp(repo, "project") == ("PRJ-003-next.md", [])


@pytest.mark.parametrize(("namespace", "folder", "prefix"), NAMESPACES, ids=NAMESPACE_IDS)
def test_an_unreadable_default_branch_is_reported_and_the_working_tree_numbers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, namespace: str, folder: str, prefix: str
) -> None:
    """A remote whose copy of the default branch was never fetched: the stamp says so, with
    the backbone's reason and fixes — the fetch and the declaration, never a base — and
    numbers past the working tree alone (COR-054 point 4)."""
    repo = _git_project(tmp_path, monkeypatch)
    repo.write(_record(folder, prefix, 4, "here"))
    repo.git("remote", "add", "origin", str(tmp_path / "never-fetched.git"))

    assert _stamp(repo, namespace) == (
        f"{prefix}-005-next.md",
        [
            "the default branch 'main' resolves to no commit here: 'origin/main' names none — "
            "fetch it (`git fetch origin main`), or declare the right one "
            "(`repository.default-branch` in .pkit/project/config.yaml). The local branch "
            "'main' is not read while a remote holds the shared one — it can lag it or carry "
            f"work nobody pushed. {prefix}-005 {ALONE}"
        ],
    )


def test_a_default_branch_whose_files_cannot_be_read_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The branch resolves, and git cannot read the files of its commit: that is said too,
    and the working tree numbers."""
    repo = _git_project(tmp_path, monkeypatch)
    _cut_before(repo, _record(".pkit/decisions/project", "PRJ", 2, "landed"))
    _with_remote(repo, tmp_path)
    tip = repo.git("rev-parse", "origin/main").stdout.strip()
    # Made here, the commit's objects are loose here: the remote keeps its own copy.
    repo.lose_object(repo.git("rev-parse", "origin/main^{tree}").stdout.strip())

    name, said = _stamp(repo, "project")

    assert name == "PRJ-002-next.md"
    assert len(said) == 1
    assert said[0].startswith(
        f"the default branch 'main' (origin/main at {tip[:12]}) could not be read: `git ls-tree` "
        "failed: "
    )
    assert said[0].endswith(f". PRJ-002 {ALONE}")


def test_a_default_branch_read_from_the_local_branch_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no remote the local branch is read, and the stamp says so, as every reader of
    the default branch does (COR-054 point 2); its records still count."""
    repo = _git_project(tmp_path, monkeypatch)
    _cut_before(repo, _record(".pkit/decisions/project", "PRJ", 2, "landed"))

    assert _stamp(repo, "project") == (
        "PRJ-003-next.md",
        [
            "the default branch 'main' is read from the local branch 'main': this repository "
            "has no remote to read the shared one from, and a local branch can lag it or carry "
            "work nobody pushed (COR-054 point 2)"
        ],
    )


def test_a_default_branch_with_no_commit_yet_holds_nothing_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before the first commit the default branch holds nothing yet, which is no failure to
    read it, and the reader reports that (COR-054 point 4): the working tree numbers, and
    the stamp says so as a notice, never a warning."""
    monkeypatch.delenv(default_branch.CHECK_BASE_ENV, raising=False)
    repo = GitRepo.init(tmp_path / "work")
    repo.write(_record(".pkit/decisions/project", "PRJ", 2, "here"))

    told: list[str] = []
    warned: list[str] = []
    target = decisions.stamp_decision(
        repo.root, namespace="project", slug="next", say=told.append, warn=warned.append
    )

    assert (target.name, told, warned) == ("PRJ-003-next.md", [_unborn("PRJ-003")], [])


def _unborn(record_id: str, name: str = "main") -> str:
    """What the stamp says of a default branch with no commit yet."""
    return (
        f"the default branch {name!r} has no commit yet, so it holds no record: {record_id} is "
        f"numbered past the working tree (COR-054 point 4)."
    )


def test_the_declared_default_branch_is_the_one_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project that declares `trunk` numbers past `trunk`, never past a `main` it also
    has (COR-054 point 1)."""
    monkeypatch.delenv(default_branch.CHECK_BASE_ENV, raising=False)
    repo = GitRepo.init(tmp_path / "work", branch="trunk")
    repo.commit(
        "first",
        {
            CONFIG: "repository:\n  default-branch: trunk\n",
            **_record(".pkit/decisions/project", "PRJ", 1, "first"),
        },
    )
    repo.git("branch", "main")
    repo.checkout("topic", create=True)
    repo.checkout("main")
    repo.commit("a stale main", _record(".pkit/decisions/project", "PRJ", 9, "stale"))
    repo.checkout("trunk")
    repo.commit("trunk's own", _record(".pkit/decisions/project", "PRJ", 2, "landed"))
    _with_remote(repo, tmp_path)
    repo.checkout("topic")

    assert _stamp(repo, "project") == ("PRJ-003-next.md", [])


def test_a_declaration_read_as_the_default_is_said(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A declared value that is no branch name is read as `main`, and the stamp says so,
    as every reader of the default branch does (COR-048 point 4)."""
    repo = _git_project(tmp_path, monkeypatch)
    repo.write({CONFIG: "repository:\n  default-branch: two words\n"})
    _cut_before(repo, _record(".pkit/decisions/project", "PRJ", 2, "landed"))
    _with_remote(repo, tmp_path)

    assert _stamp(repo, "project") == (
        "PRJ-003-next.md",
        [
            "repository.default-branch 'two words' is not a branch name; read as 'main' — "
            "`pkit validate` fails on it"
        ],
    )


@pytest.mark.parametrize(
    ("namespace", "folder", "prefix"),
    [("project", "proj/.pkit/decisions/project", "PRJ"), ("adr", "adr", "ADR")],
    ids=["project", "adr-beside-the-project"],
)
def test_a_project_below_the_repository_s_top_reads_its_folders_from_the_top(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, namespace: str, folder: str, prefix: str
) -> None:
    """A project root below the repository's top, and an ADR folder beside it rather than
    in it, are read at the default branch's commit by their paths from the top."""
    monkeypatch.delenv(default_branch.CHECK_BASE_ENV, raising=False)
    repo = GitRepo.init(tmp_path / "work")
    repo.commit(
        "first",
        {
            f"proj/{OVERLAY.as_posix()}": "adr-records:\n  - ../adr/\n",
            **_record("proj/.pkit/decisions/project", "PRJ", 1, "first"),
            **_record("adr", "ADR", 1, "first"),
        },
    )
    _cut_before(repo, _record(folder, prefix, 2, "landed"))
    _with_remote(repo, tmp_path)

    said: list[str] = []
    target = decisions.stamp_decision(
        repo.root / "proj", namespace=namespace, slug="next", warn=said.append
    )

    assert (target.name, said) == (f"{prefix}-003-next.md", [])


def test_outside_a_repository_the_reason_is_that_git_finds_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no repository here, the stamp gives git's own reason, rather than a fix to a
    branch that cannot help, and the working tree numbers."""
    monkeypatch.delenv(default_branch.CHECK_BASE_ENV, raising=False)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    project = tmp_path / "plain"
    (project / ".pkit" / "decisions" / "project").mkdir(parents=True)

    said: list[str] = []
    target = decisions.stamp_decision(project, namespace="project", slug="x", warn=said.append)

    assert target.name == "PRJ-001-x.md"
    assert len(said) == 1
    assert said[0].startswith("the default branch 'main' cannot be read: `git rev-parse` failed: ")
    assert "not a git repository" in said[0]
    assert said[0].endswith(f". PRJ-001 {ALONE}")


def test_with_no_git_to_run_the_reason_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repository git is missing to read: the reason is that git cannot run."""
    repo = _git_project(tmp_path, monkeypatch)
    monkeypatch.setenv("PATH", "")

    name, said = _stamp(repo, "project")

    assert name == "PRJ-002-next.md"
    assert len(said) == 1
    assert said[0].startswith("the default branch 'main' cannot be read: cannot run git: ")
    assert said[0].endswith(f". PRJ-002 {ALONE}")


def test_a_head_git_cannot_read_keeps_the_branch_s_own_reason_and_fixes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Where git finds the repository and the branch resolves to no commit, the backbone's
    reason stands, with the references it tried and its fixes (COR-054 point 4), even
    when HEAD names an object git cannot read."""
    repo = _git_project(tmp_path, monkeypatch)
    repo.git("remote", "add", "origin", str(tmp_path / "never-fetched.git"))
    (repo.root / ".git" / "HEAD").write_text("0123456789abcdef0123456789abcdef01234567\n")

    name, said = _stamp(repo, "project")

    assert name == "PRJ-002-next.md"
    assert said == [
        "the default branch 'main' resolves to no commit here: 'origin/main' names none — "
        "fetch it (`git fetch origin main`), or declare the right one "
        "(`repository.default-branch` in .pkit/project/config.yaml). The local branch "
        "'main' is not read while a remote holds the shared one — it can lag it or carry "
        f"work nobody pushed. PRJ-002 {ALONE}"
    ]


def test_a_repository_git_finds_keeps_the_branch_s_fixes_though_it_names_no_top(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repository configured bare is one git finds, though it names no top: a default
    branch never fetched keeps the backbone's reason and its fixes."""
    repo = _git_project(tmp_path, monkeypatch)
    repo.git("remote", "add", "origin", str(tmp_path / "never-fetched.git"))
    repo.git("config", "core.bare", "true")

    name, said = _stamp(repo, "project")

    assert name == "PRJ-002-next.md"
    assert len(said) == 1
    assert said[0].startswith(
        "the default branch 'main' resolves to no commit here: 'origin/main' names none — "
        "fetch it (`git fetch origin main`)"
    )
    assert said[0].endswith(f". PRJ-002 {ALONE}")


def test_a_repository_whose_top_git_cannot_name_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The branch resolves, and git cannot name the repository's top to list its commit
    from — a repository configured bare, say: that is said, and the working tree numbers."""
    repo = _git_project(tmp_path, monkeypatch)
    _cut_before(repo, _record(".pkit/decisions/project", "PRJ", 2, "landed"))
    _with_remote(repo, tmp_path)
    tip = repo.git("rev-parse", "origin/main").stdout.strip()
    repo.git("config", "core.bare", "true")

    name, said = _stamp(repo, "project")

    assert name == "PRJ-002-next.md"
    assert len(said) == 1
    assert said[0].startswith(
        f"the default branch 'main' (origin/main at {tip[:12]}) could not be read: "
        "`git rev-parse` failed: "
    )
    assert said[0].endswith(f". PRJ-002 {ALONE}")


def test_the_command_warns_on_standard_error_and_stamps_on_standard_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit new decision` prints what it says of the default branch as a warning on
    standard error; the stamped line stays alone on standard output."""
    repo = _git_project(tmp_path, monkeypatch)
    repo.git("remote", "add", "origin", str(tmp_path / "never-fetched.git"))
    monkeypatch.chdir(repo.root)

    result = CliRunner().invoke(main, ["new", "decision", "project", "next"])

    assert result.exit_code == 0, result.output
    assert result.stdout == "Stamped: .pkit/decisions/project/PRJ-002-next.md\n"
    assert result.stderr.startswith("warning: the default branch 'main' resolves to no commit")
    assert result.stderr.endswith(f"PRJ-002 {ALONE}\n")
