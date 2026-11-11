"""Tests for the install script, `.pkit/cli/install-pkit.sh` (ADR-090 points 3 to 8).

Each test copies the script into a project of its own and runs it with `sh`,
on a PATH of stand-ins: a `uv` that answers `tool list`, `tool dir --bin` and
`tool install` from a state folder and logs each call, and `pkit` commands
that report a version and log each run. The PATH holds no real `uv` and no
real `pkit`, so no test reaches the network or the machine's tools.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from project_kit import install, router

SCRIPT = install.find_source_kit() / "cli" / "install-pkit.sh"

#: The folders the stand-ins share the PATH with, for `sh`, `sed`, `awk` and the like.
SYSTEM_PATH = "/usr/bin:/bin"

#: The `uv` stand-in. Its state folder, `$STUB_STATE`, holds what `uv tool list`
#: prints (`tools`), the folder `uv tool dir --bin` names (`uv-bin`), and a
#: marker that fails the install (`install-fails`). An install writes a `pkit`
#: into `uv-bin` that reports the version installed, and lists it as a tool.
UV_STAND_IN = r"""#!/bin/sh
state=$STUB_STATE
printf '%s|%s\n' "${GIT_TERMINAL_PROMPT-unset}" "$*" >>"$state/uv.log"
case "$1 $2" in
    "tool list")
        [ -f "$state/tools" ] && cat "$state/tools"
        exit 0
        ;;
    "tool dir")
        printf '%s\n' "$state/uv-bin"
        exit 0
        ;;
    "tool install")
        if [ -f "$state/install-fails" ]; then
            echo "error: the stand-in install fails" >&2
            exit 1
        fi
        version=${3##*@v}
        mkdir -p "$state/uv-bin"
        cat >"$state/uv-bin/pkit" <<EOF
#!/bin/sh
printf '%s|%s|%s|%s\n' "\$0" "\$PWD" "\${GIT_TERMINAL_PROMPT-unset}" "\$*" >>"$state/pkit.log"
echo "pkit, version $version"
EOF
        chmod +x "$state/uv-bin/pkit"
        printf 'project-kit v%s\n- pkit\n' "$version" >"$state/tools"
        exit 0
        ;;
esac
exit 3
"""


def _pkit_stand_in(path: Path, version: str, state: Path, *, runs_the_pin: bool = False) -> Path:
    """Write a `pkit` at *path* that logs each run and reports *version*. One that
    *runs_the_pin* reports the pin of the project it runs in, where there is one,
    as the router of another version does when it can fetch the pin."""
    report = f'echo "pkit, version {version}"'
    if runs_the_pin:
        report = (
            'if [ -s .pkit/version-pin ]; then echo "pkit, version $(cat .pkit/version-pin)"; '
            f"else {report}; fi"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        'printf \'%s|%s|%s|%s\\n\' "$0" "$PWD" "${GIT_TERMINAL_PROMPT-unset}" "$*" '
        f'>>"{state}/pkit.log"\n'
        f"{report}\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


@dataclass
class Clone:
    """A project's clone that carries the install script, and the stand-ins it runs with."""

    root: Path
    state: Path
    tools: Path
    others: list[Path] = field(default_factory=list)

    @property
    def cli(self) -> Path:
        return self.root / ".pkit" / "cli"

    @property
    def uv_bin(self) -> Path:
        return self.state / "uv-bin"

    def pin(self, text: str) -> None:
        (self.root / ".pkit" / "version-pin").write_text(text, encoding="utf-8")

    def record(self, manifest: str | None) -> None:
        path = self.root / ".pkit" / "manifest.yaml"
        if manifest is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(manifest, encoding="utf-8")

    def uv_lists(self, version: str) -> None:
        """uv lists pkit at *version*, with its command in uv's folder."""
        (self.state / "tools").write_text(f"project-kit v{version}\n- pkit\n", encoding="utf-8")
        _pkit_stand_in(self.uv_bin / "pkit", version, self.state)

    def other_pkit(self, version: str, *, runs_the_pin: bool = False) -> Path:
        """A pkit at *version* in a folder of its own, not uv's."""
        folder = self.state / f"other-{len(self.others)}"
        self.others.append(folder)
        return _pkit_stand_in(folder / "pkit", version, self.state, runs_the_pin=runs_the_pin)

    def run(self, *path: Path, uv: bool = True, args: tuple[str, ...] = ()) -> Run:
        """Run the script with `sh` from outside the project, its PATH the
        stand-in tools (where *uv*), then *path*, then the system's folders."""
        folders = [*([self.tools] if uv else []), *path]
        completed = subprocess.run(
            ["sh", str(self.cli / "install-pkit.sh"), *args],
            capture_output=True,
            text=True,
            cwd=self.state,
            env={
                "PATH": ":".join([*(str(f) for f in folders), SYSTEM_PATH]),
                "HOME": str(self.state),
                "STUB_STATE": str(self.state),
            },
            check=False,
        )
        return Run(completed, self.state)


@dataclass
class Run:
    completed: subprocess.CompletedProcess[str]
    state: Path

    @property
    def code(self) -> int:
        return self.completed.returncode

    @property
    def out(self) -> str:
        return self.completed.stdout

    @property
    def err(self) -> str:
        return " ".join(self.completed.stderr.split())

    @property
    def installs(self) -> list[tuple[str, str]]:
        """Each `uv tool install` the script ran: git's terminal prompt switch,
        and the requirement it named."""
        return [
            (prompt, call.split(" ", 2)[2])
            for prompt, call in self._uv_calls()
            if call.startswith("tool install ")
        ]

    @property
    def checks(self) -> list[tuple[str, str, str, str]]:
        """Each run of a `pkit` stand-in: its path, working directory, git's
        terminal prompt switch and arguments."""
        log = self.state / "pkit.log"
        if not log.is_file():
            return []
        return [
            (path, cwd, prompt, args)
            for path, cwd, prompt, args in (
                line.split("|") for line in log.read_text(encoding="utf-8").splitlines()
            )
        ]

    def _uv_calls(self) -> list[tuple[str, str]]:
        log = self.state / "uv.log"
        if not log.is_file():
            return []
        return [
            (prompt, call)
            for prompt, call in (
                line.split("|", 1) for line in log.read_text(encoding="utf-8").splitlines()
            )
        ]


@pytest.fixture
def clone(tmp_path: Path) -> Clone:
    """A project's clone at backbone 1.0.0, pinned to nothing, with the install
    script and a dispatcher stand-in in its CLI area, and no pkit installed."""
    root = tmp_path / "project"
    cli = root / ".pkit" / "cli"
    cli.mkdir(parents=True)
    shutil.copy2(SCRIPT, cli / "install-pkit.sh")
    state = (tmp_path / "state").resolve()
    state.mkdir()
    _pkit_stand_in(cli / "pkit", "dispatcher", state)
    tools = tmp_path / "tools"
    tools.mkdir()
    uv = tools / "uv"
    uv.write_text(UV_STAND_IN, encoding="utf-8")
    uv.chmod(0o755)
    made = Clone(root=root.resolve(), state=state, tools=tools)
    made.record("schema_version: 1\nbackbone_version: 1.0.0\ncomponents: []\n")
    return made


def _install_of(version: str) -> tuple[str, str]:
    """The install the script runs for *version*, with git's prompt off."""
    return ("0", f"{router.DISTRIBUTION_GIT_URL}@v{version}")


# --- The URL --------------------------------------------------------------------


def test_the_scripts_url_is_the_routers() -> None:
    """The script keeps its own copy of the compiled URL, since it runs before any
    pkit exists, and this test holds the two equal, so a fork's script carries
    the fork's URL (ADR-090 point 7)."""
    text = SCRIPT.read_text(encoding="utf-8")
    [url] = re.findall(r'^DISTRIBUTION_GIT_URL="([^"]*)"$', text, re.MULTILINE)

    assert url == router.DISTRIBUTION_GIT_URL


# --- The version it installs -----------------------------------------------------


def test_it_installs_the_pin_and_checks_it_from_the_projects_root(clone: Clone) -> None:
    """It installs the version the project pins, from the URL at its release tag,
    with git's prompt off, then runs the `pkit` the PATH finds from the
    project's root, with the prompt off, and succeeds on the project's version
    (ADR-090 points 4, 5 and 7). It acts on the project it sits in, not the
    working directory."""
    clone.pin("1.2.3\n")

    run = clone.run(clone.uv_bin)

    assert run.code == 0, run.err
    assert run.installs == [_install_of("1.2.3")]
    assert run.checks == [(str(clone.uv_bin / "pkit"), str(clone.root), "0", "--version")]
    assert "this project's commands run pkit 1.2.3" in run.out


def test_it_installs_the_recorded_version_where_nothing_is_pinned(clone: Clone) -> None:
    clone.record("schema_version: 1\nbackbone_version: 1.4.0\ncomponents: []\n")

    run = clone.run(clone.uv_bin)

    assert run.code == 0, run.err
    assert run.installs == [_install_of("1.4.0")]


@pytest.mark.parametrize(
    "line",
    [
        'backbone_version: "1.4.0"\r\n',
        "backbone_version: '1.4.0'  # recorded by the transition\n",
    ],
)
def test_it_reads_the_recorded_version_from_its_own_line(clone: Clone, line: str) -> None:
    clone.record(f"schema_version: 1\n{line}completed_version: 1.0.0\ncomponents: []\n")

    run = clone.run(clone.uv_bin)

    assert run.code == 0, run.err
    assert run.installs == [_install_of("1.4.0")]


@pytest.mark.parametrize(
    "text",
    ["1.2.3", "1.2.3\n", "  1.2.3 \r\n", "\n\t1.2.3\n\n", "", "\n", " \r\n"],
)
def test_it_reads_the_pin_as_the_router_does(clone: Clone, text: str) -> None:
    """The whole file, the whitespace around it stripped, a carriage return
    included, and an empty file as no pin, as the router reads it (ADR-090
    point 4)."""
    clone.pin(text)
    expected = router.read_version_pin(clone.root) or "1.0.0"

    run = clone.run(clone.uv_bin)

    assert run.code == 0, run.err
    assert run.installs == [_install_of(expected)]


@pytest.mark.parametrize("pin", ["v1.2.3", "main", "1.2", "01.2.3", "1.2.3rc1", "1.2.3\n4.5.6"])
def test_it_refuses_a_pin_the_router_cannot_route(clone: Clone, pin: str) -> None:
    """A pin that is no bare release version is one the router can never route.
    The script installs nothing, names the pin to mend, and does not fall back to
    the recorded version (ADR-090 point 4)."""
    clone.pin(pin + "\n")

    run = clone.run(clone.uv_bin)

    assert run.code == 1
    assert "this project's pin" in run.err
    assert "pkit pin <version>" in run.err
    assert run.installs == []
    assert run.checks == []


@pytest.mark.parametrize(
    "manifest",
    [
        None,
        "schema_version: 1\ncomponents: []\n",
        "schema_version: 1\nbackbone_version:\ncomponents: []\n",
        "schema_version: 1\nbackbone_version: main\ncomponents: []\n",
        "schema_version: 1\n  backbone_version: 1.0.0\n",
    ],
)
def test_it_refuses_a_manifest_with_no_recorded_version(clone: Clone, manifest: str | None) -> None:
    """With nothing pinned and no version recorded, it installs nothing, names
    the CLI reference's section on installing pkit, and prints no install of
    `latest` (ADR-090 point 4)."""
    clone.record(manifest)

    run = clone.run(clone.uv_bin)

    assert run.code == 1
    assert "this project pins no version" in run.err
    assert '"Installing pkit on PATH"' in run.err
    assert "latest" not in run.out + run.err
    assert run.installs == []
    assert run.checks == []


# --- What it finds installed ------------------------------------------------------


def test_it_installs_nothing_where_uv_lists_a_pkit(clone: Clone) -> None:
    clone.uv_lists("1.0.0")

    run = clone.run(clone.uv_bin)

    assert run.code == 0, run.err
    assert run.installs == []
    assert "installs nothing" in run.out


def test_it_installs_nothing_where_the_path_finds_a_pkit(clone: Clone) -> None:
    other = clone.other_pkit("1.0.0")

    run = clone.run(other.parent)

    assert run.code == 0, run.err
    assert run.installs == []
    assert f"the PATH finds {other}" in run.out


def test_it_counts_the_projects_own_dispatcher_as_no_pkit(clone: Clone) -> None:
    """The project's own dispatcher on the PATH is no installed pkit, so the
    script installs, and the check runs uv's command ahead of it (ADR-090 point
    5)."""
    run = clone.run(clone.uv_bin, clone.cli)

    assert run.code == 0, run.err
    assert run.installs == [_install_of("1.0.0")]
    assert [check[0] for check in run.checks] == [str(clone.uv_bin / "pkit")]


# --- The check ----------------------------------------------------------------------


def test_it_succeeds_beside_another_version_whose_router_runs_the_pin(clone: Clone) -> None:
    """Beside an installed pkit of another version, whose router runs the pin, the
    project's commands run its version: the script installs nothing and
    succeeds (ADR-090 point 5)."""
    clone.pin("1.2.3\n")
    other = clone.other_pkit("2.0.0", runs_the_pin=True)

    run = clone.run(other.parent)

    assert run.code == 0, run.err
    assert run.installs == []
    assert "this project's commands run pkit 1.2.3" in run.out


def test_it_fails_and_leaves_the_pkit_where_the_router_falls_back(clone: Clone) -> None:
    """Where the installed pkit of another version runs itself, as its router does
    when it cannot fetch the pin, the script fails and leaves it in place. It
    names that pkit, the run through `uvx` and the forced install (ADR-090
    point 5)."""
    clone.pin("1.2.3\n")
    other = clone.other_pkit("2.0.0")

    run = clone.run(other.parent)

    assert run.code == 1
    assert run.installs == []
    assert f"{other}, runs pkit 2.0.0, not 1.2.3" in run.err
    assert "The installed pkit was left as it is." in run.err
    assert f"uvx --from {router.DISTRIBUTION_GIT_URL}@v1.2.3 project-kit <command>" in run.err
    assert f"uv tool install --force {router.DISTRIBUTION_GIT_URL}@v1.2.3" in run.err


def test_it_fails_where_the_path_finds_another_pkit_before_the_one_uv_lists(
    clone: Clone,
) -> None:
    clone.uv_lists("1.0.0")
    other = clone.other_pkit("0.9.0")

    run = clone.run(other.parent, clone.uv_bin)

    assert run.code == 1
    assert run.installs == []
    assert f"{other}, runs pkit 0.9.0, not 1.0.0" in run.err


def test_it_fails_naming_uvs_folder_where_the_path_finds_no_pkit(clone: Clone) -> None:
    """uv installed the command in a folder the PATH lacks: the clone is not
    ready, and the script names the folder to add, changing no PATH itself
    (ADR-090 point 6)."""
    run = clone.run()

    assert run.code == 1
    assert run.installs == [_install_of("1.0.0")]
    assert "the PATH finds no `pkit`" in run.err
    assert f"uv put the command in {clone.uv_bin}" in run.err


def test_it_fails_without_running_it_where_the_path_finds_the_dispatcher_first(
    clone: Clone,
) -> None:
    """In a project's clone, the dispatcher ahead of the installed pkit only names
    this script again, so the check does not run it, and says it shadows the
    installed pkit (ADR-090 point 5)."""
    run = clone.run(clone.cli, clone.uv_bin)

    assert run.code == 1
    assert run.installs == [_install_of("1.0.0")]
    assert "the PATH finds this project's own dispatcher" in run.err
    assert f"Put uv's command folder, {clone.uv_bin}, before it on the PATH" in run.err
    assert run.checks == []


def test_in_the_source_repository_it_checks_the_dispatcher_as_any_pkit(clone: Clone) -> None:
    """In the methodology's source repository the dispatcher runs the checkout's
    own code, so the check runs it as it runs any `pkit` (ADR-090 points 3 and
    5)."""
    package = clone.root / "src" / "project_kit"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    _pkit_stand_in(clone.cli / "pkit", "1.0.0", clone.state)

    run = clone.run(clone.cli, clone.uv_bin)

    assert run.code == 0, run.err
    assert [check[0] for check in run.checks] == [str(clone.cli / "pkit")]


# --- What ends the run before the check -------------------------------------------------


def test_a_failed_install_ends_the_run_before_the_check(clone: Clone) -> None:
    (clone.state / "install-fails").touch()

    run = clone.run(clone.uv_bin)

    assert run.code == 1
    assert "the install of pkit 1.0.0 failed" in run.err
    assert "sandbox" in run.err
    assert run.checks == []


def test_a_missing_uv_ends_the_run_before_the_check(clone: Clone) -> None:
    """Without `uv` the script fails, even beside a pkit at the project's version,
    since pkit needs it (ADR-090 point 5)."""
    other = clone.other_pkit("1.0.0")

    run = clone.run(other.parent, uv=False)

    assert run.code == 1
    assert "`uv` is not on the PATH" in run.err
    assert run.checks == []


def test_it_takes_no_arguments(clone: Clone) -> None:
    run = clone.run(clone.uv_bin, args=("--force",))

    assert run.code == 2
    assert "takes no arguments" in run.err
    assert run.installs == []
