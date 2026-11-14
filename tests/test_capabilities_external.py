"""Externally-sourced capabilities: install at a pin, sync to it, uninstall (COR-041; ADR-040).

Each source is a git repository the test makes, read through a local path, so
no test reaches the network. The capability is incubated there at
`.pkit/capabilities/<name>/`, as in the repository that authors it (COR-031).
"""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result

from project_kit import capabilities as caps
from project_kit import capability_fetch, install, router, status, sync, upgrade
from project_kit.cli import main
from project_kit.manifest import (
    ORIGIN_EXTERNALLY_SOURCED,
    ORIGIN_INCUBATED_IN_REPO,
    ORIGIN_KIT_SHIPPED,
    CapabilityPin,
    ComponentManifest,
    read_backbone_manifest,
    read_capability_origin,
    read_component_manifest,
    read_kit_version,
    write_component_manifest,
)
from tests.adopter_repo import GitRepo, MakeAdopterRepo
from tests.agent_definitions_support import stage_picker

# The version an installed fixture records: the real source kit's.
_RECORDED = read_kit_version(install.find_source_kit())

_NAME = "fetched"
_SKILL = Path("skills") / "fetched-skill.md"
_SCRIPT = Path("scripts") / "run.sh"


# --- fixtures --------------------------------------------------------------------


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An adopter with the backbone installed, the process's working directory."""
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")
    return make_adopter_repo().root


@pytest.fixture
def kit(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The running pkit's tree, at the version the project records, shipping no
    capability, so sync's guard lets each command run (ADR-065 point 7)."""
    from project_kit import cli as cli_mod

    source = tmp_path_factory.mktemp("kit") / ".pkit"
    (source / "decisions").mkdir(parents=True)
    (source / "VERSION").write_text(f"{_RECORDED}\n", encoding="utf-8")
    stage_picker(source)
    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: source)
    monkeypatch.setattr(install, "find_source_kit", lambda: source)
    monkeypatch.setattr(status, "find_source_kit", lambda: source)
    return source


@pytest.fixture
def upstream(tmp_path_factory: pytest.TempPathFactory) -> GitRepo:
    """The repository that authors the capability, outside the project."""
    return GitRepo.init(tmp_path_factory.mktemp("upstream") / "repo")


def _package(
    version: str,
    *,
    requires_backbone: str = ">=0.1.0,<99.0.0",
    requires_capabilities: list[dict[str, str]] | None = None,
    name: str = _NAME,
) -> str:
    required = ""
    if requires_capabilities:
        lines = ["requires_capabilities:"]
        for dependency in requires_capabilities:
            lines += [f"  - name: {dependency['name']}", f'    version: "{dependency["version"]}"']
        required = "\n".join(lines) + "\n"
    return (
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        f"  name: {name}\n"
        f"  version: {version}\n"
        "description: A capability kept in another repository.\n"
        f'requires_backbone: "{requires_backbone}"\n'
        f"{required}"
    )


def _author(
    upstream: GitRepo,
    version: str = "1.0.0",
    *,
    files: dict[str, str | None] | None = None,
    tag: str | None = None,
    **package: Any,
) -> str:
    """Write the capability in *upstream* at *version* and commit it, tagging the
    commit *tag* where given. Returns the commit's id."""
    base = f".pkit/capabilities/{_NAME}"
    written: dict[str, str | None] = {
        f"{base}/package.yaml": _package(version, **package),
        f"{base}/README.md": f"# {_NAME}\n\nv{version}\n",
        f"{base}/{_SKILL.as_posix()}": (
            f"---\nname: fetched-skill\ndescription: t\n---\n# v{version}\n"
        ),
        f"{base}/{_SCRIPT.as_posix()}": "#!/bin/sh\necho run\n",
        f"{base}/project/seed.md": "the source project's own state\n",
    }
    written.update({f"{base}/{rel}": text for rel, text in (files or {}).items()})
    upstream.write(written)
    (upstream.root / base / _SCRIPT).chmod(0o755)
    commit = upstream.commit(f"{_NAME} v{version}", files=None)
    if tag is not None:
        upstream.git("tag", "-a", "-f", tag, "-m", tag)
    return commit


def _install(*args: str) -> Result:
    return CliRunner().invoke(main, ["capabilities", "install", _NAME, *args])


def _copy(project: Path) -> Path:
    return project / ".pkit" / "capabilities" / _NAME


def _assert_nothing_installed(project: Path) -> None:
    assert not _copy(project).exists()
    manifest = read_backbone_manifest(project)
    assert manifest is not None
    assert _NAME not in {entry.name for entry in manifest.components}


def _said(result: Result) -> str:
    return " ".join(result.output.split())


# --- install at a pin (ADR-040 points 1 to 4) --------------------------------------


def test_install_at_a_tag_lands_the_tags_content_and_records_the_pin(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    """The subtree lands whole at exactly the tag, outside the copy's `project/` tier,
    which arrives empty; the registration records the origin, and the manifest the
    source and the ref beside the version (points 1 and 3)."""
    _author(upstream, "1.0.0", tag="v1.0.0")
    _author(upstream, "1.1.0")  # a later commit the tag does not reach

    result = _install("--from", str(upstream.root), "--ref", "v1.0.0")

    assert result.exit_code == 0, result.output
    copy = _copy(project)
    assert "# v1.0.0" in (copy / _SKILL).read_text(encoding="utf-8")
    assert os.stat(copy / _SCRIPT).st_mode & stat.S_IXUSR
    assert not (copy / "project" / "seed.md").exists()
    assert sorted(path.name for path in (copy / "project").iterdir()) == [
        ".gitkeep",
        "manifest.yaml",
    ]
    assert read_capability_origin(project, _NAME) == ORIGIN_EXTERNALLY_SOURCED
    manifest = read_component_manifest(copy / "project" / "manifest.yaml")
    assert manifest is not None
    assert manifest.version == "1.0.0"
    assert manifest.pin == CapabilityPin(str(upstream.root), "v1.0.0")
    assert f"externally sourced from {upstream.root} at v1.0.0" in _said(result)


def test_install_at_a_commits_full_id_takes_exactly_that_commit(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    """A commit no ref names any more is fetched by its full id."""
    first = _author(upstream, "1.0.0")
    _author(upstream, "2.0.0")

    result = _install("--from", str(upstream.root), "--ref", first)

    assert result.exit_code == 0, result.output
    assert "# v1.0.0" in (_copy(project) / _SKILL).read_text(encoding="utf-8")
    assert caps.read_capability_pin(project, _NAME) == CapabilityPin(str(upstream.root), first)


def test_install_dry_run_and_plan_fetch_and_write_nothing(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    _author(upstream, tag="v1.0.0")

    dry = _install("--from", str(upstream.root), "--ref", "v1.0.0", "--dry-run")
    plan = _install("--from", str(upstream.root), "--ref", "v1.0.0", "--plan")

    assert dry.exit_code == 0, dry.output
    assert "Would install capability 'fetched' v1.0.0" in _said(dry)
    assert plan.exit_code == 0, plan.output
    _assert_nothing_installed(project)


def test_install_names_from_and_ref_together(project: Path, kit: Path) -> None:
    result = _install("--from", "/somewhere")

    assert result.exit_code == 2
    assert "--from and --ref go together" in result.output


# --- refusals that write nothing ---------------------------------------------------


def test_install_refuses_a_branch_naming_where_a_branch_pin_waits(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    _author(upstream)

    result = _install("--from", str(upstream.root), "--ref", "main")

    assert result.exit_code == 1, result.output
    assert "names a branch" in _said(result)
    assert "#3229" in result.output
    _assert_nothing_installed(project)


def test_install_refuses_a_commits_abbreviated_id(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    commit = _author(upstream)

    result = _install("--from", str(upstream.root), "--ref", commit[:10])

    assert result.exit_code == 1, result.output
    assert "pinned by its full id" in _said(result)
    _assert_nothing_installed(project)


def test_install_refuses_a_source_that_carries_a_credential_and_never_prints_it(
    project: Path, kit: Path
) -> None:
    """Refused before git runs, so nothing is passed on, recorded or printed (point 2)."""
    result = _install("--from", "https://someone:s3cr3t@example.invalid/x.git", "--ref", "v1")

    assert result.exit_code == 1, result.output
    assert "carries a credential" in _said(result)
    assert "s3cr3t" not in result.output
    assert "someone" not in result.output
    _assert_nothing_installed(project)


def test_install_refuses_a_fetched_package_the_backbone_gate_refuses(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    """The gate reads the fetched manifest, before anything is written (point 4)."""
    _author(upstream, tag="v1.0.0", requires_backbone=">=99.0.0")

    result = _install("--from", str(upstream.root), "--ref", "v1.0.0")

    assert result.exit_code == 1, result.output
    assert "requires backbone >=99.0.0" in _said(result)
    _assert_nothing_installed(project)


def test_install_refuses_a_fetched_package_whose_dependency_is_not_installed(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    _author(
        upstream, tag="v1.0.0", requires_capabilities=[{"name": "absent", "version": ">=1.0.0"}]
    )

    result = _install("--from", str(upstream.root), "--ref", "v1.0.0")

    assert result.exit_code == 1, result.output
    assert "'absent' (>=1.0.0) is not installed" in _said(result)
    _assert_nothing_installed(project)


def test_install_refuses_a_subtree_holding_a_symbolic_link(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    """A link could reach outside the copy once it lands, so the fetch takes files only."""
    _author(upstream)
    (upstream.root / ".pkit" / "capabilities" / _NAME / "elsewhere").symlink_to("/etc")
    upstream.commit("a link", files=None)
    upstream.git("tag", "v1.0.0")

    result = _install("--from", str(upstream.root), "--ref", "v1.0.0")

    assert result.exit_code == 1, result.output
    assert "is a symbolic link" in _said(result)
    _assert_nothing_installed(project)


def test_install_refuses_a_source_holding_no_such_capability(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    upstream.commit("nothing here", files={"README.md": "# upstream\n"})
    upstream.git("tag", "v1.0.0")

    result = _install("--from", str(upstream.root), "--ref", "v1.0.0")

    assert result.exit_code == 1, result.output
    assert "holds no capability at .pkit/capabilities/fetched/" in _said(result)
    _assert_nothing_installed(project)


@pytest.mark.parametrize(
    ("origin", "held_by"),
    [
        (ORIGIN_KIT_SHIPPED, "the kit-shipped capability 'fetched' installed here"),
        (ORIGIN_INCUBATED_IN_REPO, "the incubated capability 'fetched' installed here"),
        (
            ORIGIN_EXTERNALLY_SOURCED,
            "already installed from a pin its manifest does not record",
        ),
    ],
)
def test_install_refuses_a_name_another_capability_holds(
    project: Path, kit: Path, upstream: GitRepo, origin: str, held_by: str
) -> None:
    """Reported and refused, never overwritten, before anything is fetched (point 6)."""
    _author(upstream, tag="v1.0.0")
    held = _copy(project) / "README.md"
    held.parent.mkdir(parents=True)
    held.write_text("# the project's\n", encoding="utf-8")
    caps._register_in_backbone_manifest(project, _NAME, origin=origin)

    result = _install("--from", str(upstream.root), "--ref", "v1.0.0")

    assert result.exit_code == 1, result.output
    assert held_by in _said(result)
    assert "Nothing was fetched or written" in _said(result)
    assert held.read_text(encoding="utf-8") == "# the project's\n"


def test_install_refuses_files_at_the_landing_path_no_registration_names(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    """A capability authored here and never registered holds its name too."""
    _author(upstream, tag="v1.0.0")
    authored = _copy(project) / "package.yaml"
    authored.parent.mkdir(parents=True)
    authored.write_text(_package("0.1.0"), encoding="utf-8")

    result = _install("--from", str(upstream.root), "--ref", "v1.0.0")

    assert result.exit_code == 1, result.output
    assert "authored in this repository" in _said(result)
    assert authored.read_text(encoding="utf-8") == _package("0.1.0")


def test_install_again_from_its_pin_names_sync_and_from_another_names_uninstall(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    """Moving an installed capability's pin waits on #3229."""
    _author(upstream, "1.0.0", tag="v1.0.0")
    _author(upstream, "2.0.0", tag="v2.0.0")
    assert _install("--from", str(upstream.root), "--ref", "v1.0.0").exit_code == 0

    again = _install("--from", str(upstream.root), "--ref", "v1.0.0")
    other = _install("--from", str(upstream.root), "--ref", "v2.0.0")

    assert again.exit_code == 1
    assert "`pkit sync` brings its copy to that pin" in _said(again)
    assert other.exit_code == 1
    assert "#3229" in other.output
    assert "uninstall it first" in _said(other)
    assert "# v1.0.0" in (_copy(project) / _SKILL).read_text(encoding="utf-8")


# --- a fetch that fails degrades loudly (point 7) ------------------------------------


@pytest.mark.parametrize("unreachable", [True, False], ids=["unreachable", "no-such-ref"])
def test_install_that_cannot_fetch_warns_and_activates_nothing(
    project: Path, kit: Path, upstream: GitRepo, tmp_path: Path, unreachable: bool
) -> None:
    """A source that cannot be reached, or a ref it does not hold: a loud warning, nothing
    installed, and the command ends without failing."""
    _author(upstream, tag="v1.0.0")
    source = str(tmp_path / "gone") if unreachable else str(upstream.root)

    result = _install("--from", source, "--ref", "v9.9.9")

    assert result.exit_code == 0, result.output
    assert "⚠ WARNING: capability 'fetched' could not be fetched" in _said(result)
    assert "Nothing was installed or activated" in _said(result)
    _assert_nothing_installed(project)


def test_the_fetch_turns_gits_prompt_off_and_reads_no_other_repository(
    project: Path, kit: Path, upstream: GitRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git runs with its terminal prompt off, so a credential no helper answers fails at
    once, and without the variables that point it at another repository (point 2)."""
    _author(upstream, tag="v1.0.0")
    real = shutil.which("git")
    assert real is not None
    log = tmp_path / "git.log"
    wrapper = tmp_path / "bin" / "git"
    wrapper.parent.mkdir()
    wrapper.write_text(
        f'#!/bin/sh\necho "prompt=$GIT_TERMINAL_PROMPT dir=${{GIT_DIR:-}}" >> {log}\n'
        f'exec {real} "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    monkeypatch.setenv("PATH", f"{wrapper.parent}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GIT_DIR", str(project / ".git"))

    with capability_fetch.fetched(CapabilityPin(str(upstream.root), "v1.0.0"), _NAME) as got:
        assert (got.path / "package.yaml").is_file()

    lines = log.read_text(encoding="utf-8").splitlines()
    assert lines
    assert set(lines) == {"prompt=0 dir="}


@pytest.mark.parametrize(
    ("url", "shown"),
    [
        ("https://token@example.com/a.git", "https://<credential>@example.com/a.git"),
        ("https://u:p@example.com/a.git", "https://<credential>@example.com/a.git"),
        ("ssh://u:p@example.com/a.git", "ssh://<credential>@example.com/a.git"),
        ("u:p@example.com:a.git", "<credential>@example.com:a.git"),
        ("git@example.com:org/a.git", "git@example.com:org/a.git"),
        ("ssh://git@example.com/a.git", "ssh://git@example.com/a.git"),
        ("/srv/git/a.git", "/srv/git/a.git"),
    ],
)
def test_a_credential_in_a_source_is_never_shown(url: str, shown: str) -> None:
    assert capability_fetch.shown(url) == shown


# --- sync keeps the copy at its pin (points 3 and 7) --------------------------------


def _installed(upstream: GitRepo, ref: str = "v1.0.0") -> None:
    result = _install("--from", str(upstream.root), "--ref", ref)
    assert result.exit_code == 0, result.output


def test_sync_brings_the_copy_to_its_pins_content_and_never_moves_the_pin(
    project: Path, kit: Path, upstream: GitRepo, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file the pin holds is restored, one it does not hold is removed, the project's
    own tier stays, and the manifest is not rewritten (COR-059 point 2)."""
    _author(upstream, "1.0.0", tag="v1.0.0")
    _author(upstream, "1.1.0")
    _installed(upstream)
    copy = _copy(project)
    (copy / _SKILL).write_text("edited here\n", encoding="utf-8")
    (copy / "README.md").unlink()
    (copy / "stray.md").write_text("not the pin's\n", encoding="utf-8")
    (copy / "project" / "notes.md").write_text("the project's own\n", encoding="utf-8")
    manifest = (copy / "project" / "manifest.yaml").read_bytes()

    sync.run_sync(project)
    out = capsys.readouterr().out

    assert "# v1.0.0" in (copy / _SKILL).read_text(encoding="utf-8")
    assert (copy / "README.md").is_file()
    assert not (copy / "stray.md").exists()
    assert (copy / "project" / "notes.md").read_text(encoding="utf-8") == "the project's own\n"
    assert (copy / "project" / "manifest.yaml").read_bytes() == manifest
    assert f"matched      'fetched' at v1.0.0, {upstream.root} at v1.0.0" in out


def test_sync_keeps_the_copy_and_warns_where_its_source_cannot_be_reached(
    project: Path, kit: Path, upstream: GitRepo, capsys: pytest.CaptureFixture[str]
) -> None:
    """The rest of sync runs: it ends complete."""
    _author(upstream, tag="v1.0.0")
    _installed(upstream)
    (_copy(project) / _SKILL).write_text("edited here\n", encoding="utf-8")
    shutil.rmtree(upstream.root)

    sync.run_sync(project)
    captured = capsys.readouterr()

    assert (_copy(project) / _SKILL).read_text(encoding="utf-8") == "edited here\n"
    assert "⚠ WARNING: capability 'fetched' was not brought to its pin" in captured.err
    assert "kept         'fetched'" in captured.out
    assert "Sync complete." in captured.out


def test_sync_keeps_the_copy_where_its_tag_has_moved_to_another_version(
    project: Path, kit: Path, upstream: GitRepo, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sync moves no version: a tag moved at its source is the person's to take."""
    _author(upstream, "1.0.0", tag="v1.0.0")
    _installed(upstream)
    _author(upstream, "2.0.0", tag="v1.0.0")

    sync.run_sync(project)
    captured = capsys.readouterr()

    assert "# v1.0.0" in (_copy(project) / _SKILL).read_text(encoding="utf-8")
    assert "now holds v2.0.0, and the project records v1.0.0" in " ".join(captured.err.split())


def test_sync_keeps_the_copy_whose_range_excludes_the_recorded_backbone(
    project: Path, kit: Path, upstream: GitRepo, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sync gates what it lands as install does (ADR-040 point 4): the pin's content
    at the recorded version, whose `requires_backbone` now excludes the backbone the
    project records, is not landed, and the rest of sync runs."""
    _author(upstream, "1.0.0", tag="v1.0.0")
    _installed(upstream)
    (_copy(project) / _SKILL).write_text("edited here\n", encoding="utf-8")
    _author(upstream, "1.0.0", tag="v1.0.0", requires_backbone=">=99.0.0")

    sync.run_sync(project)
    captured = capsys.readouterr()

    assert (_copy(project) / _SKILL).read_text(encoding="utf-8") == "edited here\n"
    said = " ".join(captured.err.split())
    assert "⚠ WARNING: capability 'fetched' was not brought to its pin" in said
    assert "requires backbone >=99.0.0" in said
    assert "kept         'fetched'" in captured.out
    assert "Sync complete." in captured.out


def test_sync_dry_run_fetches_nothing(
    project: Path, kit: Path, upstream: GitRepo, capsys: pytest.CaptureFixture[str]
) -> None:
    _author(upstream, tag="v1.0.0")
    _installed(upstream)
    (_copy(project) / _SKILL).write_text("edited here\n", encoding="utf-8")
    shutil.rmtree(upstream.root)

    sync.run_sync(project, dry_run=True)
    captured = capsys.readouterr()

    assert "would match  'fetched'" in captured.out
    assert "WARNING" not in captured.err
    assert (_copy(project) / _SKILL).read_text(encoding="utf-8") == "edited here\n"


# --- the verbs that move or adopt a capability refuse it ----------------------------


def test_upgrade_refuses_an_externally_sourced_capability(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    _author(upstream, tag="v1.0.0")
    _installed(upstream)

    result = CliRunner().invoke(main, ["capabilities", "upgrade", _NAME])

    assert result.exit_code == 1, result.output
    assert "moves by its pin" in _said(result)
    assert "#3229" in result.output


def test_a_transition_reads_its_range_from_the_copy_never_a_shipped_one_of_its_name(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    """The compatibility check reads an externally-sourced capability's installed
    copy, never the `package.yaml` of a capability the bundle ships by its name,
    which would refuse here (ADR-065 point 1)."""
    _author(upstream, tag="v1.0.0")
    _installed(upstream)
    shipped = kit / "capabilities" / _NAME
    shipped.mkdir(parents=True)
    (shipped / "package.yaml").write_text(
        _package("9.0.0", requires_backbone=">=99.0.0"), encoding="utf-8"
    )
    manifest = read_backbone_manifest(project)
    assert manifest is not None
    entries = [entry for entry in manifest.components if entry.name == _NAME]

    assert upgrade._resolve_package_yaml(project, kit, entries[0]) == (
        _copy(project) / "package.yaml"
    )
    upgrade._resolve_compatibility(entries, project, kit, _RECORDED)


def test_register_refuses_an_externally_sourced_capability(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    _author(upstream, tag="v1.0.0")
    _installed(upstream)

    result = CliRunner().invoke(main, ["capabilities", "register", _NAME])

    assert result.exit_code == 1, result.output
    assert "never registered as incubated" in _said(result)
    assert read_capability_origin(project, _NAME) == ORIGIN_EXTERNALLY_SOURCED


# --- uninstall ----------------------------------------------------------------------


def test_uninstall_removes_the_copy_and_keeps_the_projects_own_tier(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    _author(upstream, tag="v1.0.0")
    _installed(upstream)
    notes = _copy(project) / "project" / "notes.md"
    notes.write_text("the project's own\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["capabilities", "uninstall", _NAME])

    assert result.exit_code == 0, result.output
    assert sorted(path.name for path in _copy(project).iterdir()) == ["project"]
    assert sorted(path.name for path in notes.parent.iterdir()) == [".gitkeep", "notes.md"]
    assert "the project's own files stay at .pkit/capabilities/fetched/project/" in _said(result)
    manifest = read_backbone_manifest(project)
    assert manifest is not None
    assert _NAME not in {entry.name for entry in manifest.components}


def test_uninstall_removes_the_folder_whole_where_nothing_of_the_projects_is_in_it(
    project: Path, kit: Path, upstream: GitRepo
) -> None:
    """And the name is free again: an install of it lands afresh."""
    _author(upstream, tag="v1.0.0")
    _installed(upstream)

    result = CliRunner().invoke(main, ["capabilities", "uninstall", _NAME])

    assert result.exit_code == 0, result.output
    assert not _copy(project).exists()
    _installed(upstream)


# --- what list and status show --------------------------------------------------------


def test_list_and_status_show_the_source_and_the_ref_beside_the_origin(
    project: Path, kit: Path, upstream: GitRepo, capsys: pytest.CaptureFixture[str]
) -> None:
    _author(upstream, tag="v1.0.0")
    _installed(upstream)

    listed = CliRunner().invoke(main, ["capabilities", "list"])
    status.report_status()
    reported = " ".join(capsys.readouterr().out.split())

    assert listed.exit_code == 0, listed.output
    rows = [line.split() for line in listed.output.splitlines()]
    assert [_NAME, "installed", "externally-sourced", str(upstream.root), "v1.0.0"] in rows
    assert f"fetched (externally-sourced from {upstream.root} at v1.0.0)" in reported


def test_the_pin_reads_back_from_the_component_manifest(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    pin = CapabilityPin("git@example.com:org/caps.git", "v1.2.3")
    write_component_manifest(
        path,
        ComponentManifest(
            kind="capability",
            name=_NAME,
            version="1.2.3",
            installed_at="2026-11-14T00:00:00+00:00",
            requires_backbone=">=1.0.0",
            pin=pin,
        ),
    )

    read = read_component_manifest(path)

    assert read is not None
    assert read.pin == pin


# --- the methodology's source repository (ADR-059) ----------------------------------


def test_install_in_the_source_run_by_its_own_code_refuses_and_fetches_nothing(
    project: Path, upstream: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """There every capability at `.pkit/capabilities/` is authored and bundled from, and
    install copies nothing."""
    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: project / ".pkit")
    _author(upstream, tag="v1.0.0")

    result = _install("--from", str(upstream.root), "--ref", "v1.0.0")

    assert result.exit_code == 1, result.output
    assert "methodology's source repository" in _said(result)
    _assert_nothing_installed(project)


def test_install_in_the_source_run_by_other_code_refuses_in_the_gap(
    project: Path, upstream: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project / "src" / "project_kit").mkdir(parents=True)
    (project / "src" / "project_kit" / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)
    monkeypatch.setenv(router._BYPASS_ENV, "1")
    _author(upstream, tag="v1.0.0")

    result = _install("--from", str(upstream.root), "--ref", "v1.0.0")

    assert result.exit_code == 1, result.output
    assert "land a fetched capability in the tree it is built from" in _said(result)
    _assert_nothing_installed(project)
