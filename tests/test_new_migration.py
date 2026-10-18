"""Tests for `pkit new migration` (the Python port stamping migration scripts)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import click
import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.default_branch import CHECK_BASE_ENV
from project_kit.manifest import BackboneManifest, write_backbone_manifest
from project_kit.scaffolds import MigrationScaffoldResult, stamp_migration
from tests.adopter_repo import GitRepo


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Synthesise a minimal kit tree with backbone + an adapter + a capability."""
    pkit = tmp_path / ".pkit"
    pkit.mkdir()
    (pkit / "VERSION").write_text("1.0.0\n", encoding="utf-8")

    # Adapter: adapters/sample/
    adapter = pkit / "adapters" / "sample"
    adapter.mkdir(parents=True)
    (adapter / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: adapter\n  name: sample\n  version: 0.5.0\n"
        'requires_backbone: ">=1.0.0,<2.0.0"\n',
        encoding="utf-8",
    )

    # Capability: capabilities/evidence/
    capability = pkit / "capabilities" / "evidence"
    capability.mkdir(parents=True)
    (capability / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: evidence\n  version: 0.2.0\n"
        'requires_backbone: ">=1.0.0,<2.0.0"\n',
        encoding="utf-8",
    )

    write_backbone_manifest(tmp_path, BackboneManifest(backbone_version="1.0.0"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_stamp_migration_backbone_targets_the_next_minor_past_pkit_version(
    kit_target: Path,
) -> None:
    """Outside a repository the default branch cannot be read: the stamp says so and
    targets the next minor past the working tree's version, never the released one."""
    said: list[str] = []
    result = stamp_migration(
        kit_target,
        tier="backbone",
        version=None,
        slug="my-change",
        warn=said.append,
    )
    expected = kit_target / ".pkit" / "migrations" / "backbone" / "1.1.0" / "001-my-change.sh"
    assert result.script == expected
    assert result.script.is_file()
    assert result.target is not None
    assert (
        result.target.reason == "the next minor past backbone 1.0.0, which the working tree records"
    )
    assert len(said) == 1 and "judged against the working tree alone" in said[0]
    text = result.script.read_text(encoding="utf-8")
    assert "set -euo pipefail" in text
    assert "ROOT" in text
    assert "Backbone migration 1.1.0" in text


def test_stamp_migration_script_is_executable(kit_target: Path) -> None:
    result = stamp_migration(kit_target, tier="backbone", version=None, slug="exec-check")
    mode = result.script.stat().st_mode
    assert mode & os.X_OK


def test_stamp_migration_picks_next_number(kit_target: Path) -> None:
    stamp_migration(kit_target, tier="backbone", version="1.0.0", slug="one")
    stamp_migration(kit_target, tier="backbone", version="1.0.0", slug="two")
    result = stamp_migration(kit_target, tier="backbone", version="1.0.0", slug="three")
    assert result.script.name == "003-three.sh"


def test_stamp_migration_adapter_targets_past_its_component_version(kit_target: Path) -> None:
    result = stamp_migration(
        kit_target,
        tier="adapter",
        component="sample",
        version=None,
        slug="tweak-settings",
    )
    expected = (
        kit_target
        / ".pkit"
        / "adapters"
        / "sample"
        / "migrations"
        / "0.6.0"
        / "001-tweak-settings.sh"
    )
    assert result.script == expected


def test_stamp_migration_capability_targets_past_its_component_version(kit_target: Path) -> None:
    """Per COR-017 capability tier: migration lands under
    capabilities/<name>/migrations/<X.Y.0>/."""
    result = stamp_migration(
        kit_target,
        tier="capability",
        component="evidence",
        version=None,
        slug="bump-schema",
    )
    expected = (
        kit_target
        / ".pkit"
        / "capabilities"
        / "evidence"
        / "migrations"
        / "0.3.0"
        / "001-bump-schema.sh"
    )
    assert result.script == expected
    text = result.script.read_text(encoding="utf-8")
    assert "evidence 0.3.0" in text
    # The safe-over-any-state contract binds a backbone migration only (COR-010).
    assert "positive sign" not in text


def test_a_backbone_migration_is_stamped_with_its_contract(kit_target: Path) -> None:
    """A version transition may replay every backbone migration, so the stamped
    script states the contract it must meet (COR-010)."""
    result = stamp_migration(kit_target, tier="backbone", version=None, slug="contract")
    text = result.script.read_text(encoding="utf-8")
    assert "Safe over any state (COR-010)" in text
    assert "Act only on a positive sign that" in text
    assert "never delete by a path's name or position alone" in text


def test_stamp_migration_capability_requires_component(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="--component"):
        stamp_migration(kit_target, tier="capability", version="0.2.0", slug="x")


def test_stamp_migration_capability_refuses_unknown_component(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="capability"):
        stamp_migration(kit_target, tier="capability", component="ghost", version="0.2.0", slug="x")


def test_stamp_migration_refuses_invalid_version(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match=r"X\.Y\.0"):
        stamp_migration(kit_target, tier="backbone", version="1.0.3", slug="bad-version")


def test_stamp_migration_refuses_missing_slug(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="--name"):
        stamp_migration(kit_target, tier="backbone", version="1.0.0", slug=None)


def test_stamp_migration_refuses_invalid_slug(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="kebab-case"):
        stamp_migration(kit_target, tier="backbone", version="1.0.0", slug="Bad_Slug")


def test_stamp_migration_adapter_requires_component(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="--component"):
        stamp_migration(kit_target, tier="adapter", version="1.0.0", slug="x")


def test_stamp_migration_backbone_refuses_component(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="--component"):
        stamp_migration(
            kit_target,
            tier="backbone",
            component="sample",
            version="1.0.0",
            slug="x",
        )


def test_stamp_migration_refuses_unknown_adapter(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="not found"):
        stamp_migration(
            kit_target,
            tier="adapter",
            component="ghost-adapter",
            version="1.0.0",
            slug="x",
        )


def test_stamp_migration_explicit_version_overrides_package_yaml(kit_target: Path) -> None:
    result = stamp_migration(
        kit_target,
        tier="adapter",
        component="sample",
        version="2.5.0",
        slug="future-change",
    )
    assert "2.5.0" in str(result.script)


def test_stamp_migration_includes_scope_in_comment(kit_target: Path) -> None:
    result = stamp_migration(
        kit_target,
        tier="backbone",
        version="1.0.0",
        slug="struct-change",
        scope="structural",
    )
    text = result.script.read_text(encoding="utf-8")
    assert "structural" in text


# --- the version, past what the default branch has released (COR-010, COR-054 point 3) ----


_EVIDENCE = ".pkit/capabilities/evidence/package.yaml"


def _package(name: str, version: str) -> str:
    return (
        f"schema_version: 1\ncomponent:\n  kind: capability\n  name: {name}\n  version: {version}\n"
    )


@pytest.fixture
def released(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GitRepo:
    """A repository whose default branch, `main`, records backbone 1.149.0 and the
    evidence capability at 0.54.0, checked out on a branch `topic` cut from it."""
    monkeypatch.delenv(CHECK_BASE_ENV, raising=False)
    repo = GitRepo.init(tmp_path / "kit")
    repo.commit(
        "released", {".pkit/VERSION": "1.149.0\n", _EVIDENCE: _package("evidence", "0.54.0")}
    )
    repo.git("checkout", "-q", "-b", "topic")
    monkeypatch.chdir(repo.root)
    return repo


def _stamp(repo: GitRepo, said: list[str] | None = None, **kwargs: Any) -> MigrationScaffoldResult:
    sink: list[str] = [] if said is None else said
    return stamp_migration(
        repo.root,
        tier=kwargs.pop("tier", "backbone"),
        version=kwargs.pop("version", None),
        slug=kwargs.pop("slug", "change"),
        warn=sink.append,
        **kwargs,
    )


def _folder(result: MigrationScaffoldResult) -> str:
    return f"{result.script.parent.name}/{result.script.name}"


def test_without_a_version_the_stamp_targets_the_next_minor_past_the_default_branch(
    released: GitRepo,
) -> None:
    said: list[str] = []
    result = _stamp(released, said)
    assert _folder(result) == "1.150.0/001-change.sh"
    assert result.target is not None
    assert result.target.reason == (
        "the next minor past backbone 1.149.0, which the default branch 'main' records"
    )
    # The repository has no remote, so the default branch is the local `main`, said so.
    assert said and all("local branch 'main'" in line for line in said)


def test_a_branch_cut_before_a_release_targets_past_that_release(released: GitRepo) -> None:
    """The working tree still records 1.149.0, but the default branch released 1.150.0
    since the branch was cut: a folder 1.150.0/ would never run for a project at it."""
    released.git("checkout", "-q", "main")
    released.commit("chore(release): v1.150.0", {".pkit/VERSION": "1.150.0\n"})
    released.git("checkout", "-q", "topic")
    assert (released.root / ".pkit" / "VERSION").read_text() == "1.149.0\n"
    assert _folder(_stamp(released)) == "1.151.0/001-change.sh"


def test_a_branch_that_bumps_its_own_version_targets_that_version(released: GitRepo) -> None:
    """A project whose change bumps its version on its branch: the bumped version is the
    target, above the one the default branch records."""
    released.commit("bump", {".pkit/VERSION": "1.152.3\n"})
    result = _stamp(released)
    assert _folder(result) == "1.152.0/001-change.sh"
    assert result.target is not None
    assert result.target.reason == (
        "the version the working tree records for backbone, 1.152.3, above 1.149.0 on the "
        "default branch 'main'"
    )


def test_a_pending_major_folder_is_joined_and_numbered_past_the_default_branch(
    released: GitRepo,
) -> None:
    """A folder for the next major already waits on the default branch, merged after
    this branch was cut: the script joins it, so it runs after that change's own
    migrations, and takes the number after the default branch's script there."""
    released.git("checkout", "-q", "main")
    released.commit(
        "a breaking change", {".pkit/migrations/backbone/2.0.0/001-breaking.sh": "#!/bin/sh\n"}
    )
    released.git("checkout", "-q", "topic")
    assert not (released.root / ".pkit" / "migrations").exists()
    result = _stamp(released)
    assert _folder(result) == "2.0.0/002-change.sh"
    assert result.target is not None
    assert result.target.reason == (
        "the next major past backbone 1.149.0, whose folder 2.0.0/ already waits"
    )


def test_a_folder_further_ahead_is_not_joined(released: GitRepo) -> None:
    """A folder past the next minor that is not the next major may be a later target on
    purpose (#465): the stamp does not join it."""
    released.commit(
        "later targets",
        {
            ".pkit/migrations/backbone/1.152.0/001-later.sh": "#!/bin/sh\n",
            ".pkit/migrations/backbone/3.0.0/001-much-later.sh": "#!/bin/sh\n",
        },
    )
    assert _folder(_stamp(released)) == "1.150.0/001-change.sh"


def test_a_given_version_already_released_is_refused(released: GitRepo) -> None:
    for given in ("1.149.0", "1.148.0", "0.9.0"):
        with pytest.raises(click.ClickException) as refused:
            _stamp(released, version=given)
        assert refused.value.message == (
            f"--version {given} is already released: the default branch 'main' records "
            f"backbone 1.149.0, so a project at 1.149.0 never runs a migration in {given}/. "
            "Give --version 1.150.0, the version the stamp picks without --version, or a "
            "later one."
        )
    assert not (released.root / ".pkit" / "migrations").exists()
    assert _folder(_stamp(released, version="1.150.0")) == "1.150.0/001-change.sh"
    assert _folder(_stamp(released, version="2.0.0", slug="later")) == "2.0.0/001-later.sh"


def test_a_component_targets_past_its_released_version(released: GitRepo) -> None:
    result = _stamp(released, tier="capability", component="evidence")
    assert _folder(result) == "0.55.0/001-change.sh"
    assert result.script.parent.parent == released.root / ".pkit/capabilities/evidence/migrations"
    with pytest.raises(click.ClickException, match=r"capability evidence 0\.54\.0"):
        _stamp(released, tier="capability", component="evidence", version="0.54.0")


def test_a_component_the_default_branch_lacks_targets_past_the_working_tree(
    released: GitRepo,
) -> None:
    """A capability this branch adds has no released version: the stamp targets past
    the working tree's, and refuses no given version."""
    fresh = ".pkit/capabilities/fresh/package.yaml"
    released.commit("a new capability", {fresh: _package("fresh", "0.1.0")})
    assert _folder(_stamp(released, tier="capability", component="fresh")) == "0.2.0/001-change.sh"
    given = _stamp(released, tier="capability", component="fresh", version="0.1.0", slug="x")
    assert _folder(given) == "0.1.0/001-x.sh"


def test_the_check_base_never_reaches_the_stamp(
    released: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stamp allocates from settled state: the base a pipeline sets for its checks is
    not read (COR-054 point 3)."""
    released.git("checkout", "-q", "-b", "elsewhere", "main")
    released.commit("far ahead", {".pkit/VERSION": "1.200.0\n"})
    released.git("checkout", "-q", "topic")
    monkeypatch.setenv(CHECK_BASE_ENV, "elsewhere")
    assert _folder(_stamp(released)) == "1.150.0/001-change.sh"


def test_the_command_says_the_version_it_chose_and_why(released: GitRepo) -> None:
    result = CliRunner().invoke(main, ["new", "migration", "--tier", "backbone", "--name", "x"])
    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [
        "Version: 1.150.0, the next minor past backbone 1.149.0, which the default branch "
        "'main' records.",
        "Stamped: .pkit/migrations/backbone/1.150.0/001-x.sh",
    ]
    refused = CliRunner().invoke(
        main, ["new", "migration", "--tier", "backbone", "--version", "1.149.0", "--name", "y"]
    )
    assert refused.exit_code == 1
    assert "--version 1.149.0 is already released" in refused.output
