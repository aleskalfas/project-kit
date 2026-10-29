"""Tests for the `pkit` CLI entry point.

Phase 1's surface is `version` only; Phase 2 (PR-D / PR-E / PR-F) ports
the bash dispatcher's other commands and grows this test file alongside.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import (
    __version__,
    agent_runs,
    cli,
    default_branch,
    friction_check,
    friction_write,
    session_guard,
)
from project_kit import pull_request_landing as landing
from project_kit.cli import main
from tests.adopter_repo import MakeAdopterRepo

# The modules every start runs in: the root group, how output renders, and where
# the project is (`project_kit.cli`'s imports).
_FRAME = ("project_kit.cli_render", "project_kit.dispatcher", "project_kit.install")


def _loaded_by(statements: str, cwd: Path, tmp_path: Path) -> set[str]:
    """The `project_kit` modules a fresh interpreter has loaded once it has run
    `statements` in `cwd`."""
    loaded = tmp_path / f"loaded-{len(list(tmp_path.iterdir()))}.json"
    probe = (
        f"{statements}\n"
        "import json, pathlib, sys\n"
        f"pathlib.Path({str(loaded)!r}).write_text(json.dumps(sorted(sys.modules)))\n"
    )
    subprocess.run([sys.executable, "-c", probe], cwd=cwd, check=True, capture_output=True)
    return {name for name in json.loads(loaded.read_text()) if name.startswith("project_kit")}


def _imports(*modules: str) -> str:
    return "\n".join(f"import {module}" for module in modules)


def test_version_subcommand_prints_pkit_then_version() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"pkit {__version__}"


def test_version_flag_uses_click_default_format() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    # Click's standard --version output uses the "<prog>, version <X>" form.
    assert result.output.strip() == f"pkit, version {__version__}"


def test_root_invocation_with_no_args_shows_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "version" in result.output  # the version subcommand is listed


def test_kit_version_is_semver_three_segment() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3, f"expected major.minor.patch, got {__version__!r}"
    for part in parts:
        assert part.isdigit(), f"non-numeric segment in version {__version__!r}"


@pytest.mark.parametrize("subcommand", ["area", "adapter", "migration", "capability", "decision"])
def test_new_subcommand_surfaces_help(subcommand: str) -> None:
    """The core `new <subcommand>` commands all expose --help."""
    runner = CliRunner()
    result = runner.invoke(main, ["new", subcommand, "--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output


# --- a start loads what the command it runs uses (#2310) ---------------------


def test_importing_the_cli_loads_no_module_that_runs_a_command(tmp_path: Path) -> None:
    """Every start imports the CLI, so what it imports loads whatever command
    runs: only the frame every start runs in, never a command's own modules."""
    frame = _loaded_by(_imports(*_FRAME), tmp_path, tmp_path)
    loaded = _loaded_by(_imports("project_kit.cli"), tmp_path, tmp_path)
    assert loaded - frame == {"project_kit.cli"}


def test_a_start_of_repository_base_loads_only_the_modules_it_runs(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    """`pkit repository base --json` loads the frame and `default_branch`, with
    what they import, and no module of a command it does not run."""
    root = make_adopter_repo().root
    runs = _imports(*_FRAME, "project_kit.default_branch")
    start = (
        "from project_kit.cli import main\n"
        "try:\n"
        "    main(['repository', 'base', '--json'], prog_name='pkit')\n"
        "except SystemExit as stop:\n"
        "    assert not stop.code, stop.code\n"
    )
    needed = _loaded_by(runs, root, tmp_path)
    loaded = _loaded_by(start, root, tmp_path)
    assert "project_kit.default_branch" in loaded
    assert loaded - needed == {"project_kit.cli"}


def test_every_stand_in_names_a_module_or_function_that_exists() -> None:
    """Type checkers read the imports a stand-in takes the place of, never the
    stand-in, so a wrong name in one shows only when a command uses it."""
    stand_ins = {
        name: value for name, value in vars(cli).items() if isinstance(value, cli._OnFirstUse)
    }
    assert {"friction_check", "refs_mod", "run_sync", "apply_release"} <= stand_ins.keys()
    for name, stand_in in stand_ins.items():
        target = stand_in._target()
        if stand_in._name:
            assert stand_in._name == name
            assert callable(target), name
        else:
            assert type(target).__name__ == "module", name


def test_a_name_only_type_checkers_see_is_used_in_annotations_alone() -> None:
    """A name imported for type checkers, with no stand-in beside it, is unbound
    when the CLI runs: used outside an annotation, it fails only once a command
    reaches it, so each such name stays in annotations."""
    tree = ast.parse(Path(cli.__file__).read_text(encoding="utf-8"))
    for_type_checkers = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.If) and ast.unparse(node.test) == "TYPE_CHECKING"
        for statement in node.body
        if isinstance(statement, ast.ImportFrom)
        for alias in statement.names
    }
    unbound = for_type_checkers - set(vars(cli))
    assert {"Changeset", "ReleasePlan", "CommentedMap"} <= unbound
    in_annotations: set[int] = set()
    for node in ast.walk(tree):
        annotations: list[ast.expr | None] = []
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            arguments = node.args
            every = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
            every += [arg for arg in (arguments.vararg, arguments.kwarg) if arg is not None]
            annotations = [arg.annotation for arg in every] + [node.returns]
        elif isinstance(node, ast.AnnAssign):
            annotations = [node.annotation]
        for annotation in annotations:
            if annotation is not None:
                in_annotations.update(id(sub) for sub in ast.walk(annotation))
    used_at_run_time = sorted(
        f"{node.id} (line {node.lineno})"
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id in unbound and id(node) not in in_annotations
    )
    assert used_at_run_time == []


def test_a_stand_in_calls_and_reads_through_to_what_it_stands_in_for() -> None:
    assert cli.default_branch.CHECK_BASE_ENV == default_branch.CHECK_BASE_ENV
    assert cli.report_status.__name__ == "report_status"
    wait_limit = cli._OnFirstUse("project_kit.pull_request_landing", "wait_limit")
    assert wait_limit(90.0) == landing.wait_limit(90.0) == "up to 1.5 min"


def test_the_values_the_declarations_show_are_those_the_commands_run_on() -> None:
    """The CLI writes out the values its options show, so declaring them loads
    no module that runs a command; each is the value that module runs on."""
    assert cli._CHECK_BASE_ENV == default_branch.CHECK_BASE_ENV == friction_check.BASE_ENV
    assert cli._CHECK_HEAD_ENV == default_branch.CHECK_HEAD_ENV == friction_check.HEAD_ENV
    assert cli._AGENT_RUN_MAX_LIMIT_SECONDS == agent_runs.MAX_LIMIT_SECONDS
    assert cli._AGENT_RUN_EFFORT_LEVELS == agent_runs.EFFORT_LEVELS
    assert cli._REVALIDATION_OUTCOMES == friction_write.OUTCOMES
    assert cli._REVISIT_OUTCOMES == friction_write.REVISIT_OUTCOMES
    assert cli._QUEUE_ETA_MARGIN_SECONDS == landing.ETA_MARGIN_SECONDS
    assert cli._QUEUE_MAX_WAIT_SECONDS == landing.MAX_WAIT_SECONDS
    assert landing.wait_limit(None) == cli._QUEUE_WAIT_DEFAULT
    assert (cli._SHAPE_REFUSE, cli._SHAPE_WARN) == (landing.SHAPE_REFUSE, landing.SHAPE_WARN)
    assert cli._CONFIRM_OPTION == session_guard.CONFIRM_OPTION
    assert cli._LAND_EXITS == {
        landing.END_MERGED: 0,
        landing.END_MERGED_ELSEWHERE: 0,
        landing.END_PLANNED: 0,
        landing.END_QUEUED: 4,
        landing.END_UNCONFIRMED: 4,
        landing.END_HEAD_MOVED: 3,
        landing.END_DROPPED: 3,
        landing.END_NOT_MERGED: 3,
    }
