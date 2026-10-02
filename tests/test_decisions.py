"""Tests for `pkit new decision` (the Python port of the bash dispatcher's `cmd_new_decision`)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import decisions
from project_kit import project_config as pc
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo


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
    assert output == DERIVED_NOTICE + f"Stamped: {DERIVED}/ADR-001-first.md\n"
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
    assert output == DERIVED_NOTICE + f"Stamped: {DERIVED}/ADR-001-first.md\n"
    assert (repo.root / DERIVED / "ADR-001-first.md").is_file()


def test_new_adr_derives_from_the_declared_internal_root(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _unset(make_adopter_repo)
    _set_internal_root(repo, "tech-docs")

    code, output = _new_adr(monkeypatch, "first", terminal=False)

    assert code == 0, output
    assert output.startswith(
        "recorded adr-records = tech-docs/architecture/decisions  "
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
    assert output == DERIVED_NOTICE + f"Stamped: {DERIVED}/ADR-002-second.md\n"
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
    assert output == f"Stamped: {DERIVED}/ADR-002-second.md\n"
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
    assert output == "Stamped: decisions/adr/ADR-002-second.md\n"
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
