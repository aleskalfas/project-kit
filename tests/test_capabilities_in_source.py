"""The capability verbs in the methodology's source repository, run by its own code (#1107).

Under the checkout's own code sync's test holds (ADR-059 point 2): the methodology
tree the running code resolves is the checkout's own `.pkit/`, so a capability's
subtree `.pkit/capabilities/<name>/` is the tree `install` and `upgrade` copy
*from* — the capability's source, not a copy of it. The verbs act on it in place:

- `uninstall` never deletes it. It says what it would have deleted, asks, and
  unregisters only (COR-031 D4: deletion is for a disposable copy); `--purge` is
  refused.
- `install` of an unregistered capability registers it without copying.
- `upgrade` re-deploys it without copying and runs no migration.

The tree is source-shaped (an installed tree with the package source beside it)
and run by its own package: `install.__file__` is placed in the tree's package
source, so `find_source_kit()` resolves the tree's own `.pkit/` — what route 1
establishes (ADR-059 point 4). The adopter side, where the subtree is a copy, is
covered unchanged by `test_capabilities.py`; the gap, where other code runs the
source, by `test_source_repository_refusal.py`.
"""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner, Result

from project_kit import capabilities as caps
from project_kit import install
from project_kit.cli import main
from project_kit.manifest import (
    ORIGIN_INCUBATED_IN_REPO,
    ORIGIN_KIT_SHIPPED,
    read_capability_origin,
)
from tests.adopter_repo import MakeAdopterRepo

_NAME = "homework"


@pytest.fixture
def source_repo(make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The methodology's source repository, run by its own code, authoring `_NAME`."""
    root = make_adopter_repo().root
    package = root / "src" / "project_kit"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(install, "__file__", str(package / "install.py"))
    assert install.is_self_host(root, install.find_source_kit())
    _author_capability(root / ".pkit" / "capabilities" / _NAME)
    # Deploy and provisioning are observed, not run: the tree shape is what is asserted.
    monkeypatch.setattr(install, "provision_query_commands", lambda _ctx, **_kw: None)
    return root


def _author_capability(cap_dir: Path) -> None:
    """A capability authored in place: a skill (its own, so never a collision against
    itself), a `project/` tree with content, and a migration an upgrade would run from
    the recorded version were it treated as a copy."""
    cap_dir.mkdir(parents=True)
    (cap_dir / "package.yaml").write_text(
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        f"  name: {_NAME}\n"
        "  version: 0.2.0\n"
        "description: Authored in the source.\n"
        'requires_backbone: ">=0.1.0,<99.0.0"\n',
        encoding="utf-8",
    )
    (cap_dir / "README.md").write_text(f"# {_NAME}\n", encoding="utf-8")
    (cap_dir / "skills").mkdir()
    (cap_dir / "skills" / "do-homework.md").write_text(
        "---\nname: do-homework\ndescription: t\n---\n# do-homework\n", encoding="utf-8"
    )
    (cap_dir / "project").mkdir()
    (cap_dir / "project" / "config.yaml").write_text("mine: true\n", encoding="utf-8")
    migration = cap_dir / "migrations" / "0.2.0" / "001-mark.sh"
    migration.parent.mkdir(parents=True)
    migration.write_text('#!/usr/bin/env bash\ntouch "$ROOT/migration-ran"\n', encoding="utf-8")
    migration.chmod(0o755)


def _snapshot(cap_dir: Path) -> dict[str, bytes]:
    """Every file under the subtree, by relative path, with its bytes."""
    return {
        path.relative_to(cap_dir).as_posix(): path.read_bytes()
        for path in sorted(cap_dir.rglob("*"))
        if path.is_file()
    }


def _cap_dir(root: Path) -> Path:
    return root / ".pkit" / "capabilities" / _NAME


def _registered(root: Path, *, origin: str = ORIGIN_KIT_SHIPPED) -> dict[str, bytes]:
    """Register `_NAME` as the source's manifest does (kit-shipped by default), with an
    install receipt recording an older version — so a refresh treating the subtree as a
    copy would have a migration to run — and return the subtree's bytes as they stand."""
    caps._register_in_backbone_manifest(root, _NAME, origin=origin)
    (_cap_dir(root) / "manifest.yaml").write_text(
        f"schema_version: 1\ncomponent:\n  kind: capability\n  name: {_NAME}\n  version: 0.1.0\n",
        encoding="utf-8",
    )
    return _snapshot(_cap_dir(root))


def _output(result: Result) -> str:
    return " ".join(result.output.split())


# --- the predicate ------------------------------------------------------------


def test_the_subtree_is_the_source_only_where_the_running_code_resolves_it(
    source_repo: Path, tmp_path: Path
) -> None:
    """Every capability subtree in the source run by its own code is the source; the
    same name in a project the running code does not resolve is a copy."""
    assert caps.authored_in_source(source_repo, install.find_source_kit(), _NAME)
    assert not caps.authored_in_source(tmp_path / "adopter", install.find_source_kit(), _NAME)


# --- uninstall: never deletes the source ---------------------------------------


def test_uninstall_says_what_it_would_have_deleted_and_unregisters_only(
    source_repo: Path,
) -> None:
    before = _registered(source_repo)

    result = CliRunner().invoke(main, ["capabilities", "uninstall", _NAME], input="y\n")

    assert result.exit_code == 0, result.output
    said = _output(result)
    assert f"'{_NAME}' is authored in this repository, the methodology's source" in said
    assert (
        f"Uninstalling a kit-shipped capability deletes its subtree; here that would delete "
        f".pkit/capabilities/{_NAME}/, the capability's source." in said
    )
    assert f"Unregister '{_NAME}' and keep .pkit/capabilities/{_NAME}/?" in said
    assert (
        f"Unregistered capability '{_NAME}'; nothing was deleted: its source stays at "
        f".pkit/capabilities/{_NAME}/." in said
    )
    assert "--purge" not in said
    assert not caps.is_installed(source_repo, _NAME)
    assert _snapshot(_cap_dir(source_repo)) == before


def test_declining_the_unregister_writes_nothing(source_repo: Path) -> None:
    before = _registered(source_repo)
    manifest = (source_repo / ".pkit" / "manifest.yaml").read_bytes()

    result = CliRunner().invoke(main, ["capabilities", "uninstall", _NAME], input="n\n")

    assert result.exit_code == 1, result.output
    assert caps.is_installed(source_repo, _NAME)
    assert (source_repo / ".pkit" / "manifest.yaml").read_bytes() == manifest
    assert _snapshot(_cap_dir(source_repo)) == before


@pytest.mark.parametrize(
    ("flags", "installed_after", "line"),
    [
        pytest.param(
            ["--yes"],
            False,
            f"Unregistered capability '{_NAME}'; nothing was deleted",
            id="yes",
        ),
        pytest.param(
            ["--dry-run"],
            True,
            f"Would unregister capability '{_NAME}'; nothing would be deleted",
            id="dry-run",
        ),
    ],
)
def test_uninstall_without_a_prompt(
    source_repo: Path, flags: list[str], installed_after: bool, line: str
) -> None:
    """`--yes` confirms for a non-interactive run; `--dry-run` asks nothing and writes nothing."""
    before = _registered(source_repo)

    result = CliRunner().invoke(main, ["capabilities", "uninstall", _NAME, *flags])

    assert result.exit_code == 0, result.output
    assert line in _output(result)
    assert caps.is_installed(source_repo, _NAME) is installed_after
    assert _snapshot(_cap_dir(source_repo)) == before


@pytest.mark.parametrize("origin", [ORIGIN_KIT_SHIPPED, ORIGIN_INCUBATED_IN_REPO])
def test_purge_is_refused_in_the_source(source_repo: Path, origin: str) -> None:
    before = _registered(source_repo, origin=origin)

    result = CliRunner().invoke(main, ["capabilities", "uninstall", _NAME, "--purge", "--yes"])

    assert result.exit_code == 1, result.output
    said = _output(result)
    assert "refusing `--purge`" in said
    assert "Nothing was written" in said
    assert f"`git rm -r .pkit/capabilities/{_NAME}`" in said
    assert caps.is_installed(source_repo, _NAME)
    assert _snapshot(_cap_dir(source_repo)) == before


def test_an_incubated_capability_in_the_source_unregisters_in_place_as_before(
    source_repo: Path,
) -> None:
    """Uninstall of an incubated one keeps its files anyway (COR-031 D4): no prompt, but
    no pointer to `--purge` either, which the source refuses."""
    before = _registered(source_repo, origin=ORIGIN_INCUBATED_IN_REPO)

    result = CliRunner().invoke(main, ["capabilities", "uninstall", _NAME])

    assert result.exit_code == 0, result.output
    said = _output(result)
    assert f"Unregistered incubated capability '{_NAME}' in place" in said
    assert "--purge" not in said
    assert not caps.is_installed(source_repo, _NAME)
    assert _snapshot(_cap_dir(source_repo)) == before


def test_uninstall_undeploys_the_kept_source_through_the_adapters(
    source_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The subtree stays, so a deploy re-run would not see the capability as gone: each
    adapter's undeploy primitive is told its name, as for an incubated one."""
    _registered(source_repo)
    ran: list[tuple[str, tuple[str, ...]]] = []

    def _record(script: Path, _ctx: install.InstallContext, *args: str) -> None:
        ran.append((script.name, args))

    monkeypatch.setattr(install, "_run_adapter_primitive", _record)

    outcome = caps.uninstall_capability(source_repo, _NAME)

    assert outcome.in_source and not outcome.files_deleted
    assert ran == [(install.ADAPTER_UNDEPLOY_PRIMITIVE, (_NAME,))]
    assert outcome.adapters_without_undeploy == ()


def test_the_library_never_deletes_the_source(source_repo: Path) -> None:
    """The guard is structural: a caller that skips the CLI still cannot delete it."""
    before = _registered(source_repo)

    with pytest.raises(click.ClickException, match="never deletes a capability's source"):
        caps.uninstall_capability(source_repo, _NAME, purge=True)
    assert caps.is_installed(source_repo, _NAME)

    outcome = caps.uninstall_capability(source_repo, _NAME)

    assert outcome.in_source and not outcome.files_deleted
    assert not caps.is_installed(source_repo, _NAME)
    assert _snapshot(_cap_dir(source_repo)) == before


# --- install and upgrade: never copy a tree onto itself -------------------------


def test_install_registers_an_authored_capability_without_copying(source_repo: Path) -> None:
    before = _snapshot(_cap_dir(source_repo))

    result = CliRunner().invoke(main, ["capabilities", "install", _NAME])

    assert result.exit_code == 0, result.output
    assert (
        f"Registered capability '{_NAME}' v0.2.0 in place at .pkit/capabilities/{_NAME}/: it is "
        "authored in this repository, the methodology's source, so nothing was copied"
    ) in _output(result)
    assert caps.is_installed(source_repo, _NAME)
    assert read_capability_origin(source_repo, _NAME) == ORIGIN_KIT_SHIPPED
    # Nothing written into the tree: no copy, no receipt, no `project/` stub.
    assert _snapshot(_cap_dir(source_repo)) == before


def test_install_dry_run_in_the_source_writes_nothing(source_repo: Path) -> None:
    before = _snapshot(_cap_dir(source_repo))

    result = CliRunner().invoke(main, ["capabilities", "install", _NAME, "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "Would register capability" in result.output
    assert "nothing would be copied" in _output(result)
    assert not caps.is_installed(source_repo, _NAME)
    assert _snapshot(_cap_dir(source_repo)) == before


def test_register_in_the_source_names_no_second_copy(source_repo: Path) -> None:
    """The in-repo tree and the kit source are one tree here, so `register` has no
    same-named kit-shipped capability to surface (the COR-031 boundary note is for
    an adopter whose incubated capability later ships from the kit too)."""
    result = CliRunner().invoke(main, ["capabilities", "register", _NAME])

    assert result.exit_code == 0, result.output
    assert "ships from kit source" not in _output(result)
    assert "kit-shipped one is not installed" not in _output(result)
    assert caps.is_installed(source_repo, _NAME)


def test_upgrade_redeploys_an_authored_capability_without_copying(
    source_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The source is already the state, as sync's self-host path has it: the deploy
    primitives re-run, and no copy, receipt or migration touches the tree."""
    before = _registered(source_repo)
    deployed: list[Path] = []
    monkeypatch.setattr(
        install, "run_installed_adapter_primitives", lambda ctx: deployed.append(ctx.target_root)
    )

    result = CliRunner().invoke(main, ["capabilities", "upgrade", _NAME])

    assert result.exit_code == 0, result.output
    assert (
        f"Re-deployed capability '{_NAME}' v0.2.0 from its source at .pkit/capabilities/{_NAME}/: "
        "it is authored in this repository, the methodology's source, so nothing was copied "
        "and no migration ran"
    ) in _output(result)
    assert deployed == [source_repo]
    assert not (source_repo / "migration-ran").exists()
    assert caps.is_installed(source_repo, _NAME)
    assert _snapshot(_cap_dir(source_repo)) == before


def test_a_refresh_onto_itself_is_refused_before_anything_runs(source_repo: Path) -> None:
    """A caller that skips the CLI and refreshes the source from itself is refused before
    its migrations or its copy, rather than crashing mid-copy or pruning a skipped
    artefact out of the source."""
    before = _registered(source_repo)
    source = caps.find_capability_in_source(install.find_source_kit(), _NAME)
    assert source is not None

    with pytest.raises(click.ClickException, match="onto itself"):
        caps.refresh_capability(source_repo, source, skipped_artifacts=(("skill", "do-homework"),))

    assert not (source_repo / "migration-ran").exists()
    assert _snapshot(_cap_dir(source_repo)) == before
