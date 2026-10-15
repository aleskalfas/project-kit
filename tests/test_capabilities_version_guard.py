"""`pkit capabilities install` and `upgrade` stop wherever `pkit sync` stops (#1463).

Both copy the running pkit's content into the project, so each calls sync's
guard at its entry, in both directions ([ADR-065] point 7). Each stops, before
anything is read or written, under a pkit newer or older than the release the
project records and over an unfinished upgrade, under `--dry-run` too, and
names sync's remedies (point 8). At the project's version they run as before.
`pkit capabilities register` copies nothing and is not guarded.

`upgrade`, the transition of one capability, also refuses in its step 1 a
capability this pkit's bundle ships older than the project records, with no
override (point 7). The methodology's source is exempt from the guard, which
`test_capabilities_in_source.py` covers.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from project_kit import capabilities as caps
from project_kit import cli as cli_mod
from project_kit import install, router
from project_kit.cli import main
from project_kit.manifest import (
    ORIGIN_INCUBATED_IN_REPO,
    read_capability_origin,
    read_component_manifest,
    read_kit_version,
    record_backbone_target,
    record_completed_version,
)
from tests.adopter_repo import MakeAdopterRepo

# The version an installed fixture records: the real source kit's, which the
# scratch kit below carries as its own.
_PROJECTS_VERSION = read_kit_version(install.find_source_kit())
# A release before this pkit's, and a version no release reaches.
_OLDER = "1.0.0"
_NEWER = "999.0.0"
_NAME = "trial"


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, tmp_path: Path) -> Path:
    """An adopter at this pkit's version, its last upgrade complete."""
    return make_adopter_repo(root=tmp_path / "project").root


@pytest.fixture
def source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A usable kit at the project's version, outside the project, so sync's test
    never takes the project for the methodology's source. The CLI copies from it."""
    kit = tmp_path / "kit"
    (kit / "capabilities").mkdir(parents=True)
    (kit / "decisions").mkdir()
    (kit / "VERSION").write_text(f"{_PROJECTS_VERSION}\n", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit)
    return kit


def _stage(base: Path, version: str, *, skill: str = "# Trial\n") -> caps.CapabilitySource:
    """Capability `_NAME` at *version* under *base*, a kit's tree or a project's `.pkit/`."""
    cap_dir = base / "capabilities" / _NAME
    (cap_dir / "skills").mkdir(parents=True, exist_ok=True)
    (cap_dir / "package.yaml").write_text(
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        f"  name: {_NAME}\n"
        f"  version: {version}\n"
        "description: A trial capability.\n"
        'requires_backbone: ">=0.0.0"\n',
        encoding="utf-8",
    )
    (cap_dir / "README.md").write_text(f"# {_NAME}\n", encoding="utf-8")
    (cap_dir / "skills" / "try-it.md").write_text(skill, encoding="utf-8")
    staged = caps.find_capability_in_source(base, _NAME)
    assert staged is not None
    return staged


def _installed(project: Path, source: Path, version: str) -> None:
    """Install `_NAME` at *version* as an install at the project's version leaves it."""
    caps.install_capability(project, _stage(source, version))


def _record_states(project: Path, backbone: str | None, completed: str | None) -> None:
    """Record the backbone's two states, *completed* None leaving no completion,
    and *backbone* None removing the manifest."""
    path = project / ".pkit" / "manifest.yaml"
    if backbone is None:
        path.unlink()
        return
    record_backbone_target(project, backbone)
    if completed is None:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        path.write_text(
            "".join(line for line in lines if not line.startswith("completed_version:")),
            encoding="utf-8",
        )
    else:
        record_completed_version(project, completed)


def _tree_bytes(root: Path) -> dict[str, bytes | None]:
    """Every path under *root* outside `.git/`, with a file's bytes (None for a
    directory): what a refusal must leave exactly as it was."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
        if path.relative_to(root).parts[0] != ".git"
    }


def _cli(*args: str) -> Result:
    return CliRunner().invoke(main, ["capabilities", *args])


def _said(result: Result) -> str:
    return " ".join(result.output.split())


# Each state the guard stops in, set on the project, and what its message names.
_STATES = {
    "newer-pkit": (
        (_OLDER, _OLDER),
        [
            f"this pkit is {_PROJECTS_VERSION}, newer than this project's content, {_OLDER}",
            f"To move the project to {_PROJECTS_VERSION}: run `pkit upgrade`.",
            f"To stay at {_OLDER}: run `pkit pin`.",
            "In a pipeline: commit a pin",
        ],
    ),
    "older-pkit": (
        (_NEWER, _NEWER),
        [
            f"this pkit is {_PROJECTS_VERSION}, older than this project's content ({_NEWER}",
            "pkit never moves a project to an older version",
            f"{router.DISTRIBUTION_GIT_URL}@v{_NEWER} project-kit capabilities",
        ],
    ),
    "no-completion": (
        (_PROJECTS_VERSION, None),
        [
            "no completed upgrade is recorded for this project",
            "Run `pkit upgrade`: it runs every backbone migration up to its version once",
        ],
    ),
    "incomplete": (
        (_PROJECTS_VERSION, _OLDER),
        [
            "the last upgrade of this project is incomplete",
            f"Run `pkit upgrade`: it finishes the upgrade, running the backbone migrations "
            f"from {_OLDER}.",
        ],
    ),
    "no-version": (
        ("not-a-version", "not-a-version"),
        [
            "`backbone_version` in .pkit/manifest.yaml is 'not-a-version', which is no version",
            "Run `pkit upgrade`: it writes the manifest at its version",
        ],
    ),
    "no-manifest": (
        (None, None),
        [
            ".pkit/manifest.yaml is missing",
            "Run `pkit upgrade`: it writes the manifest at its version",
        ],
    ),
}

# Each command the guard stops, with the flags each run passes.
_COMMANDS = {
    "install": [("install", _NAME), ("install", _NAME, "--dry-run"), ("install", _NAME, "--plan")],
    "upgrade": [
        ("upgrade", _NAME),
        ("upgrade", _NAME, "--dry-run"),
        ("upgrade", _NAME, "--force", "--interactive"),
    ],
}


# --- the guard: each command, in each state it stops in (ADR-065 points 7, 8) ---


@pytest.mark.parametrize("state", list(_STATES))
@pytest.mark.parametrize("command", list(_COMMANDS))
def test_each_command_stops_where_sync_stops_writing_nothing_and_naming_its_remedy(
    project: Path, source: Path, command: str, state: str
) -> None:
    """Under a newer or an older pkit, over an unfinished upgrade, or with no
    manifest or no version recorded, `install` and `upgrade` stop before anything
    is written, under `--dry-run`, `--plan` and `--force` too, and name the remedy
    sync's guard names for that state."""
    if command == "upgrade":
        _installed(project, source, "0.1.0")
    _stage(source, "0.2.0")
    (backbone, completed), remedies = _STATES[state]
    _record_states(project, backbone, completed)
    before = _tree_bytes(project)

    for args in _COMMANDS[command]:
        result = _cli(*args)

        assert result.exit_code != 0, (args, result.output)
        said = _said(result)
        assert f"refusing to run `pkit capabilities {command} {_NAME}`:" in said, args
        assert "Nothing was written, and no flag overrides this refusal." in said, args
        for remedy in remedies:
            assert remedy in said, (args, remedy)
        assert _tree_bytes(project) == before, args


def test_a_pin_ahead_of_this_pkit_stops_both_and_names_the_pin(project: Path, source: Path) -> None:
    """The pin names the version the project runs at: one ahead of this pkit stops
    both commands, and the remedy is the pin's pkit, run for this command."""
    _installed(project, source, "0.1.0")
    router.pin_file_path(project).write_text(f"{_NEWER}\n", encoding="utf-8")
    before = _tree_bytes(project)

    for command in ("install", "upgrade"):
        said = _said(_cli(command, _NAME))

        assert f"older than this project's pin ({_NEWER}, in .pkit/version-pin)" in said
        assert (
            f"`uvx --from {router.DISTRIBUTION_GIT_URL}@v{_NEWER} project-kit capabilities "
            f"{command} {_NAME}`"
        ) in said
        assert _tree_bytes(project) == before


def test_under_the_routers_fallback_both_name_reconnecting_for_their_own_command(
    project: Path, source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pinned, and the router could not fetch the pin: each names reconnecting and
    running itself again, the pin through uvx, and moving on purpose with
    `pkit unpin` first, never a bare `pkit upgrade` (point 8, first row)."""
    _installed(project, source, "0.1.0")
    _record_states(project, _OLDER, _OLDER)
    router.pin_file_path(project).write_text(f"{_OLDER}\n", encoding="utf-8")
    monkeypatch.setenv(router._PIN_UNRESOLVED_ENV, _OLDER)
    monkeypatch.delenv(router._BYPASS_ENV, raising=False)

    for command in ("install", "upgrade"):
        said = _said(_cli(command, _NAME))

        assert f"This project pins pkit {_OLDER}, which the router could not fetch" in said
        assert f"Reconnect and run `pkit capabilities {command} {_NAME}` again" in said
        assert "`pkit unpin`, then `pkit upgrade`" in said
        assert "Run `pkit upgrade`" not in said


# --- at the project's version: both run as before --------------------------------


def test_install_runs_at_the_projects_version(project: Path, source: Path) -> None:
    _stage(source, "0.2.0")

    result = _cli("install", _NAME)

    assert result.exit_code == 0, result.output
    assert f"Installed capability '{_NAME}' v0.2.0" in result.output
    assert caps.is_installed(project, _NAME)


def test_upgrade_runs_at_the_projects_version(project: Path, source: Path) -> None:
    _installed(project, source, "0.1.0")
    _stage(source, "0.2.0")

    result = _cli("upgrade", _NAME)

    assert result.exit_code == 0, result.output
    assert f"Refreshed capability '{_NAME}' -> v0.2.0" in result.output
    record = read_component_manifest(
        project / ".pkit" / "capabilities" / _NAME / "project" / "manifest.yaml"
    )
    assert record is not None and record.version == "0.2.0"


def test_upgrade_of_an_incubated_capability_stops_too_and_runs_at_the_projects_version(
    project: Path, source: Path
) -> None:
    """The guard runs at `capabilities upgrade`'s entry, as sync's does, before the
    command reads the capability's origin (ADR-065 points 4 and 7). So the
    re-deploy of an incubated capability, which copies nothing, stops under another
    pkit too, as `pkit sync`, which also re-deploys it, does. At the project's
    version it re-deploys as before."""
    _stage(project / ".pkit", "0.1.0")
    assert _cli("register", _NAME).exit_code == 0

    ran = _cli("upgrade", _NAME)

    assert ran.exit_code == 0, ran.output
    assert f"Re-deployed incubated capability '{_NAME}'" in ran.output

    _record_states(project, _OLDER, _OLDER)
    before = _tree_bytes(project)

    stopped = _cli("upgrade", _NAME)

    assert stopped.exit_code != 0
    assert f"refusing to run `pkit capabilities upgrade {_NAME}`:" in _said(stopped)
    assert _tree_bytes(project) == before


# --- register copies nothing, and is not guarded ----------------------------------


@pytest.mark.parametrize("state", [state for state in _STATES if state != "no-manifest"])
def test_register_runs_in_every_state_the_guard_stops_in(
    project: Path, source: Path, state: str
) -> None:
    """`register` activates a capability authored in the project, copying nothing,
    so a pkit at another version, an unfinished upgrade or a recorded version that
    is no version does not stop it. With no manifest it refuses as before, by its
    own check: it registers the capability in the manifest."""
    _stage(project / ".pkit", "0.1.0")
    (backbone, completed), _remedies = _STATES[state]
    _record_states(project, backbone, completed)

    result = _cli("register", _NAME)

    assert result.exit_code == 0, result.output
    assert f"Registered incubated capability '{_NAME}'" in result.output
    assert read_capability_origin(project, _NAME) == ORIGIN_INCUBATED_IN_REPO


# --- upgrade refuses a capability this pkit ships older (ADR-065 point 7) --------


@pytest.mark.parametrize(
    "flags", [(), ("--force",), ("--dry-run",), ("--interactive",)], ids=lambda f: "-".join(f)
)
def test_upgrade_refuses_a_capability_this_pkit_ships_older_with_no_override(
    project: Path, source: Path, flags: tuple[str, ...]
) -> None:
    """At the project's version, the bundle ships the capability older than the
    project records, as an untagged install can leave it: copying it would move its
    recorded version down, so the transition refuses in its step 1, writing nothing
    and with no override. The message names both versions, and `pkit upgrade` run by
    a pkit whose bundle ships the recorded version or newer."""
    _installed(project, source, "0.3.0")
    _stage(source, "0.1.0", skill="# Older\n")
    before = _tree_bytes(project)

    result = _cli("upgrade", _NAME, *flags)

    assert result.exit_code != 0
    said = _said(result)
    assert (
        f"refusing to run `pkit capabilities upgrade {_NAME}`: this pkit's bundle ships "
        f"capability '{_NAME}' at 0.1.0, older than the 0.3.0 this project records."
    ) in said
    assert "Nothing was written, and no flag overrides this refusal." in said
    assert (
        f"Run `pkit upgrade` with a pkit whose bundle ships capability '{_NAME}' at 0.3.0 or "
        "newer: it moves the project to that pkit's release."
    ) in said
    assert _tree_bytes(project) == before


@pytest.mark.parametrize(
    ("recorded", "bundled", "expected"),
    [
        pytest.param("0.3.0", "0.1.0", ("0.3.0", True), id="bundled-older"),
        pytest.param("0.1.0", "0.2.0", ("0.1.0", False), id="bundled-newer"),
        pytest.param(None, "0.2.0", (None, False), id="no-record"),
        pytest.param("not-a-version", "0.2.0", ("not-a-version", False), id="record-no-version"),
        pytest.param("v0.2.0", "0.2.0", None, id="same-written-another-way"),
        pytest.param("0.2.0", "not-a-version", None, id="bundled-no-version"),
    ],
)
def test_capability_move_reads_one_capability_as_the_transition_of_the_backbone_does(
    recorded: str | None, bundled: str, expected: tuple[str | None, bool] | None
) -> None:
    """The move each transition reads for one capability: none at the bundled
    version or where the bundle names no version, and one *ahead* only where the
    record is a version newer than the bundle's (ADR-065 points 2 and 7)."""
    from project_kit.upgrade import capability_move

    move = capability_move(_NAME, recorded, bundled)

    if expected is None:
        assert move is None
    else:
        assert move is not None
        assert (move.kind, move.name, move.bundled) == ("capability", _NAME, bundled)
        assert (move.recorded, move.ahead) == expected


def test_upgrade_at_the_recorded_version_refreshes_without_refusing(
    project: Path, source: Path
) -> None:
    """The bundle ships the version the project records: no move, and no refusal.
    The refresh copies it again, as before."""
    _installed(project, source, "0.2.0")
    _stage(source, "0.2.0", skill="# Refreshed\n")

    result = _cli("upgrade", _NAME)

    assert result.exit_code == 0, result.output
    skill = project / ".pkit" / "capabilities" / _NAME / "skills" / "try-it.md"
    assert skill.read_text(encoding="utf-8") == "# Refreshed\n"
