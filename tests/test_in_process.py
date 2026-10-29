"""A capability's code run in a test's own process, and the guard on its processes (#2315).

`tests/in_process.py`, held to the shared choices of #2314:

- **the in-process `pkit`** (choice 1), one test for each clause of its contract,
  on a stand-in for the backbone's CLI that says what it saw, and then on the CLI
  itself, through each capability's one private function;
- **the loader** (choice 3): each capability's `_lib` kept apart, a script and its
  `_lib` from one call, and a script's `main` run as its process ran;
- **the guard** (choice 4): what counts as a start of `pkit` or a capability
  script, a test that starts one without the mark failed, and what is not
  counted: a template's build, and a test of the runner;
- **the reverse seam** (choice 5): a component's validator started in this process
  through the runner's one lookup, for living-docs and software-analysis, and a
  broken registration still failing;
- **no capability code imports the backbone** (ADR-057 point 1), the premise of all
  of it: a capability reaches the backbone only through `pkit`'s commands.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import click
import pytest
from click.testing import CliRunner

from project_kit import cli, command_runner, default_branch
from project_kit import friction_discovery as fd
from project_kit.cli import main
from project_kit.command_runner import Ending
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import installed
from tests.in_process import (
    BASELINE,
    CAPABILITIES,
    MARK,
    InProcessPkit,
    ProcessStarts,
    baseline,
    judge,
    load,
    route_pkit,
    run_main,
    start_in_process,
    starts_pkit_or_a_capability_script,
)

REPO = Path(__file__).resolve().parent.parent
LD_SCRIPTS = CAPABILITIES / "living-docs" / "scripts"

# --- the in-process `pkit` (choice 1) -------------------------------------------------------


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("words", nargs=-1, type=click.UNPROCESSED)
def said(words: tuple[str, ...]) -> None:
    """A `pkit` that says what it saw on standard output, and a line on standard error:
    `fail` raises, `exit <n>` exits `n`."""
    click.echo(
        json.dumps(
            {
                "words": list(words),
                "cwd": os.getcwd(),
                "offline": [os.environ.get("PKIT_OFFLINE"), os.environ.get("UV_OFFLINE")],
                "base": os.environ.get(default_branch.CHECK_BASE_ENV),
                "head": os.environ.get(default_branch.CHECK_HEAD_ENV),
                "cached": fd._targets_patterns.cache_info().currsize,
            }
        )
    )
    click.echo("a line on standard error", err=True)
    if words[:1] == ("fail",):
        raise RuntimeError("the command broke")
    if words[:1] == ("exit",):
        sys.exit(int(words[1]))


@pytest.fixture
def stand_in(monkeypatch: pytest.MonkeyPatch) -> InProcessPkit:
    """The in-process `pkit`, with the backbone's CLI standing in as `said`."""
    monkeypatch.setattr(cli, "main", said)
    return InProcessPkit()


def _seen(completed: subprocess.CompletedProcess[Any]) -> dict[str, Any]:
    return json.loads(completed.stdout)


def test_it_gives_a_completed_process_with_its_streams_apart(stand_in: InProcessPkit) -> None:
    completed = stand_in(["pkit", "friction", "check"], capture_output=True, text=True)
    assert completed.args == ["pkit", "friction", "check"]
    assert _seen(completed)["words"] == ["friction", "check"]
    assert completed.stderr == "a line on standard error\n"
    assert stand_in.calls == [["pkit", "friction", "check"]]
    # Without `text`, bytes; without `capture_output`, the caller's own streams.
    raw = stand_in(["pkit"], capture_output=True)
    assert isinstance(raw.stdout, bytes) and raw.stderr == b"a line on standard error\n"


def test_without_capture_it_writes_to_the_caller_s_streams(
    stand_in: InProcessPkit, capsys: pytest.CaptureFixture[str]
) -> None:
    completed = stand_in(["pkit", "config", "set"])
    assert (completed.stdout, completed.stderr) == (None, None)
    out, err = capsys.readouterr()
    assert json.loads(out)["words"] == ["config", "set"]
    assert err == "a line on standard error\n"


def test_its_exit_code_is_the_command_s(stand_in: InProcessPkit) -> None:
    assert stand_in(["pkit", "exit", "3"], capture_output=True, text=True).returncode == 3
    assert stand_in(["pkit"], capture_output=True, text=True).returncode == 0
    with pytest.raises(subprocess.CalledProcessError):
        stand_in(["pkit", "exit", "3"], capture_output=True, check=True)


def test_it_runs_from_the_directory_given_and_leaves_the_caller_s_as_it_was(
    stand_in: InProcessPkit, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    there, here = tmp_path / "there", tmp_path / "here"
    there.mkdir()
    here.mkdir()
    monkeypatch.chdir(here)
    seen = _seen(stand_in(["pkit"], cwd=there, capture_output=True, text=True))
    assert Path(seen["cwd"]).resolve() == there.resolve()
    assert Path.cwd().resolve() == here.resolve()
    # With none given, the current directory, as a process inherits it.
    seen = _seen(stand_in(["pkit"], capture_output=True, text=True))
    assert Path(seen["cwd"]).resolve() == here.resolve()


def test_it_runs_in_the_environment_the_runner_gives_a_query(
    stand_in: InProcessPkit, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The offline marker set, the base override and the change's own head removed (the
    lifecycle README, "How a registered command is run"), and the caller's kept after."""
    monkeypatch.setenv(default_branch.CHECK_BASE_ENV, "origin/feature")
    monkeypatch.setenv(default_branch.CHECK_HEAD_ENV, "abc123")
    monkeypatch.delenv("PKIT_OFFLINE", raising=False)
    seen = _seen(stand_in(["pkit"], capture_output=True, text=True))
    assert seen["offline"] == ["1", "1"]
    assert (seen["base"], seen["head"]) == (None, None)
    assert os.environ[default_branch.CHECK_BASE_ENV] == "origin/feature"
    assert "PKIT_OFFLINE" not in os.environ


def test_an_exception_is_exit_1_with_its_traceback_on_standard_error(
    stand_in: InProcessPkit,
) -> None:
    completed = stand_in(["pkit", "fail"], capture_output=True, text=True)
    assert completed.returncode == 1
    assert "Traceback (most recent call last)" in completed.stderr
    assert completed.stderr.rstrip().endswith("RuntimeError: the command broke")


@pytest.mark.parametrize("keyword", ["env", "input", "timeout", "stdin", "encoding"])
def test_a_keyword_it_does_not_model_is_refused(stand_in: InProcessPkit, keyword: str) -> None:
    with pytest.raises(
        TypeError, match=f"models only cwd, capture_output, text, check, not {keyword}"
    ):
        unmodelled: dict[str, Any] = {keyword: None}
        stand_in(["pkit"], **unmodelled)
    with pytest.raises(ValueError, match="answers `pkit` alone"):
        stand_in(["git", "status"])
    assert stand_in.calls == []


def test_the_backbone_s_caches_are_cleared_before_each_call(stand_in: InProcessPkit) -> None:
    """A process of `pkit` starts with no cache of its own, so neither does a call."""
    fd._targets_patterns(("a link",))
    assert fd._targets_patterns.cache_info().currsize > 0
    assert _seen(stand_in(["pkit"], capture_output=True, text=True))["cached"] == 0


def test_it_answers_through_the_backbone_s_own_cli(
    make_adopter_repo: MakeAdopterRepo, process_starts: ProcessStarts
) -> None:
    repo = make_adopter_repo(capabilities=("living-docs",))
    pkit = InProcessPkit()
    completed = pkit(
        ["pkit", "friction", "artefacts", "--json"], cwd=repo.root, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["roots"] == {"user": "docs", "internal": "docs"}
    assert process_starts.started == []


def test_living_docs_sends_every_pkit_call_through_its_one_private_function(
    make_adopter_repo: MakeAdopterRepo,
    monkeypatch: pytest.MonkeyPatch,
    process_starts: ProcessStarts,
) -> None:
    """Each reading's default runner hands its call to `_run`, looked up when called."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    artefacts, binding, backbone = load("living-docs", "artefacts", "binding", "backbone")
    pkit = route_pkit(monkeypatch, backbone)
    assert isinstance(pkit, InProcessPkit)
    reading = artefacts.read_artefacts(repo.root)
    assert reading.roots == {"user": "docs", "internal": "docs"}
    binding.read_binding(repo.root)
    assert pkit.calls == [
        ["pkit", "friction", "artefacts", "--json"],
        ["pkit", "rule-sets", "reach", "--json"],
    ]
    assert process_starts.started == []


def test_software_analysis_s_private_function_is_used_unchanged(
    make_adopter_repo: MakeAdopterRepo,
    monkeypatch: pytest.MonkeyPatch,
    process_starts: ProcessStarts,
) -> None:
    """`backbone._run(root, argv, run)` runs as it is: its default runner is the in-process
    `pkit`, and a runner a caller passes is kept."""
    repo = installed(make_adopter_repo, monkeypatch)
    (backbone,) = load("software-analysis", "backbone")
    pkit = route_pkit(monkeypatch, backbone)
    assert isinstance(pkit, InProcessPkit)
    assert backbone.read_analysis(repo.root).artefacts == ()
    assert pkit.calls == [["pkit", "friction", "artefacts", "--json"]]
    passed: list[list[str]] = []

    def own(argv: list[str], **options: Any) -> subprocess.CompletedProcess[str]:
        passed.append(argv)
        return pkit(argv, **options)

    backbone.read_analysis(repo.root, run=own)
    assert passed == [["pkit", "friction", "artefacts", "--json"]]
    assert process_starts.started == []


def test_a_capability_without_a_route_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    backbone = ModuleType("_lib.backbone")
    backbone.__file__ = str(CAPABILITIES / "evidence" / "scripts" / "_lib" / "backbone.py")
    with pytest.raises(LookupError, match="no route to the in-process `pkit` for 'evidence'"):
        route_pkit(monkeypatch, backbone)


# --- the loader (choice 3) ------------------------------------------------------------------


def _ours() -> set[str]:
    return {name for name in sys.modules if name == "_lib" or name.startswith("_lib.")}


def test_each_capability_s_lib_is_kept_apart(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both capabilities name their library `_lib`: each loads its own, and neither is
    left importable, nor in `sys.modules`, nor is one already there disturbed."""
    before = ModuleType("_lib")
    monkeypatch.setitem(sys.modules, "_lib", before)
    path = list(sys.path)
    names = _ours()
    (spaces,) = load("living-docs", "spaces")
    (check,) = load("software-analysis", "check")
    assert Path(spaces.__file__ or "").is_relative_to(CAPABILITIES / "living-docs")
    assert Path(check.__file__ or "").is_relative_to(CAPABILITIES / "software-analysis")
    assert spaces.__name__ == check.__name__.replace("check", "spaces") == "_lib.spaces"
    assert sys.modules["_lib"] is before
    assert _ours() == names
    assert sys.path == path


def test_a_script_and_its_lib_from_one_call_share_their_modules() -> None:
    validate, backbone = load("software-analysis", "validate.py", "backbone")
    assert validate.backbone is backbone
    assert validate.__name__ == "_script_software_analysis_validate"
    # Two calls share nothing: each is a run of its own.
    (again,) = load("software-analysis", "backbone")
    assert again is not backbone


def test_a_script_s_main_runs_as_its_process_ran(tmp_path: Path) -> None:
    """`sys.argv`, the exit code and the two streams as a process gives them, from the
    directory given; the caller's directory and `sys.argv` left as they were."""
    (validate,) = load("living-docs", "validate.py")
    argv, cwd = list(sys.argv), Path.cwd()
    helped = run_main(validate, "--help", cwd=tmp_path)
    assert (helped.returncode, helped.stderr) == (0, "")
    assert helped.stdout.startswith("usage: validate.py [-h] [--json]")
    refused = run_main(validate, "--bogus")
    assert refused.returncode == 2
    assert "unrecognized arguments: --bogus" in refused.stderr
    assert (sys.argv, Path.cwd()) == (argv, cwd)


def test_an_exception_in_main_is_exit_1_with_its_traceback() -> None:
    script = ModuleType("broken")

    def main() -> int:
        raise RuntimeError("the script broke")

    script.main = main  # pyright: ignore[reportAttributeAccessIssue] a module made for the test
    completed = run_main(script)
    assert completed.returncode == 1
    assert completed.stderr.rstrip().endswith("RuntimeError: the script broke")


# --- the reverse seam (choice 5) ------------------------------------------------------------


def test_pkit_validate_starts_living_docs_validator_in_this_process(
    make_adopter_repo: MakeAdopterRepo,
    monkeypatch: pytest.MonkeyPatch,
    process_starts: ProcessStarts,
) -> None:
    repo = make_adopter_repo(capabilities=("living-docs",))
    started = start_in_process(monkeypatch)
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 0, result.output
    assert "living-docs:spaces" in result.output
    assert started == [
        repo.root / ".pkit" / "capabilities" / "living-docs" / "scripts" / "validate.py"
    ]
    assert process_starts.started == []


def test_pkit_validate_starts_software_analysis_validator_in_this_process(
    make_adopter_repo: MakeAdopterRepo,
    monkeypatch: pytest.MonkeyPatch,
    process_starts: ProcessStarts,
) -> None:
    installed(make_adopter_repo, monkeypatch)
    started = start_in_process(monkeypatch)
    only = ["--color", "never", "validate", "--only", "software-analysis:artefacts"]
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 0, result.output
    assert "0 actor(s), 0 term(s)" in result.output
    assert [script.name for script in started] == ["validate.py"]
    assert process_starts.started == []


def test_a_broken_registration_still_fails(
    make_adopter_repo: MakeAdopterRepo,
    monkeypatch: pytest.MonkeyPatch,
    process_starts: ProcessStarts,
) -> None:
    """Only the start is replaced: the runner's lookup still resolves the command, so a
    validator registered with another command's script runs that script, and fails."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    package = repo.root / ".pkit" / "capabilities" / "living-docs" / "package.yaml"
    text = package.read_text(encoding="utf-8")
    wrong = text.replace("script: scripts/validate.py", "script: scripts/new.py")
    package.write_text(wrong, encoding="utf-8")
    started = start_in_process(monkeypatch)
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 1
    assert "exited 2" in result.output
    assert [script.name for script in started] == ["new.py"]
    assert process_starts.started == []


def test_a_script_that_cannot_be_started_is_not_started(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    start_in_process(monkeypatch)
    run = command_runner.run_command(tmp_path / "missing.py", ["--json"], cwd=tmp_path)
    assert run.ending is Ending.NOT_STARTED
    assert "No such file or directory" in run.detail


# --- the guard (choice 4) -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("args", "counted"),
    [
        (["pkit", "friction", "check"], True),
        (["/tmp/bin/pkit", "validate"], True),
        ([sys.executable, "-m", "project_kit", "status"], True),
        ([sys.executable, "/x/.pkit/capabilities/living-docs/scripts/validate.py"], True),
        ("/x/.pkit/capabilities/software-analysis/scripts/new.py actor a", True),
        ([sys.executable, "-c", "import _lib", "/x/.pkit/capabilities/living-docs/scripts"], True),
        (["bash", "/x/.pkit/capabilities/project-management/scripts/hook.sh"], True),
        (["uv", "run", "pkit", "validate"], True),
        (["git", "add", "/x/.pkit/capabilities/living-docs/scripts/validate.py"], False),
        (["git", "status"], False),
        ([sys.executable, "-m", "pytest"], False),
        (["gh", "pr", "view", "pkit"], False),
        ([sys.executable, "/x/.pkit/capabilities/living-docs/templates/page.md"], False),
    ],
)
def test_what_counts_as_a_start_of_pkit_or_a_capability_script(args: Any, counted: bool) -> None:
    assert starts_pkit_or_a_capability_script(args) is counted


class _Test:
    """What the guard reads of a test, written by hand."""

    def __init__(self, *marks: pytest.MarkDecorator, module: str = "test_new.py") -> None:
        self._marks = [mark.mark for mark in marks]
        self._path = Path("tests") / module

    @property
    def path(self) -> Path:
        return self._path

    def iter_markers(self, name: str | None = None) -> Iterator[pytest.Mark]:
        return iter([mark for mark in self._marks if name is None or mark.name == name])


def _started(*argv: list[str]) -> ProcessStarts:
    starts = ProcessStarts(lambda: False)
    starts.started.extend(argv)
    return starts


def test_a_test_that_starts_one_without_the_mark_fails() -> None:
    why = judge(_Test(), _started(["pkit", "validate"]), frozenset())
    assert why is not None
    assert why.startswith(
        "the test started 1 process(es) of `pkit` or a capability script without "
        "`@pytest.mark.process(<reason>)`, the first `pkit validate`."
    )
    # Marked with its reason, or in a module the guard does not hold yet, it passes.
    marked = _Test(pytest.mark.process("the validate command's end-to-end test"))
    assert judge(marked, _started(["pkit", "validate"]), frozenset()) is None
    assert judge(_Test(), _started(["pkit"]), frozenset({"test_new.py"})) is None
    # A test that starts none needs no mark.
    assert judge(_Test(), _started(), frozenset()) is None


@pytest.mark.parametrize("mark", [pytest.mark.process(), pytest.mark.process("  ")])
def test_a_mark_without_its_reason_fails(mark: pytest.MarkDecorator) -> None:
    assert judge(_Test(mark), _started(), frozenset()) == (
        "`@pytest.mark.process` needs its reason: why the process is the point"
    )


@pytest.mark.process("the guard's own test: it counts the process this test starts")
def test_the_guard_counts_the_processes_a_test_starts(
    process_starts: ProcessStarts, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Counted from the start itself, so the count is the same on every run; a template's
    build is not counted, whichever test pays it."""
    building = ProcessStarts(lambda: True).watch(monkeypatch)
    script = LD_SCRIPTS / "resolve-source.py"
    subprocess.run([sys.executable, str(script), "--help"], capture_output=True, check=True)
    subprocess.run(["git", "--version"], capture_output=True, check=True)
    assert process_starts.started == [[sys.executable, str(script), "--help"]]
    assert building.started == []


def test_a_test_of_the_runner_is_not_counted(tmp_path: Path, process_starts: ProcessStarts) -> None:
    """A test that asks `run_command` itself to run a script tests the process the runner
    starts, so the start is its subject, not a cost: it needs no mark."""
    script = tmp_path / ".pkit" / "capabilities" / "sample" / "scripts" / "answer.py"
    script.parent.mkdir(parents=True)
    script.write_text(f"#!{sys.executable}\nprint('{{}}')\n", encoding="utf-8")
    script.chmod(0o755)
    run = command_runner.run_command(script, [], cwd=tmp_path)
    assert run.ending is Ending.ANSWERED
    assert process_starts.started == []


def test_the_baseline_names_only_modules_that_are_there() -> None:
    """A module the baseline lists is one of the suite's, and this one is held."""
    listed = baseline()
    assert listed
    assert sorted(name for name in listed if not (BASELINE.parent / name).is_file()) == []
    assert Path(__file__).name not in listed
    assert MARK == "process"


# --- no capability code imports the backbone (ADR-057 point 1) ------------------------------


#: The calls that import a module named as text.
_IMPORTERS = ("import_module", "__import__")


def _named(node: ast.expr) -> str:
    return node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", "")


def _backbone_imports(source: str) -> list[str]:
    """Each import of the backbone's package in `source`: a statement, or a call of
    `importlib.import_module` or `__import__` naming it. Finding where the package lies,
    as a reading of its version does, imports nothing."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names if a.name.split(".")[0] == "project_kit"]
        elif (
            isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "project_kit"
        ):
            found.append(node.module or "")
        elif (
            isinstance(node, ast.Call)
            and _named(node.func) in _IMPORTERS
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and str(node.args[0].value).split(".")[0] == "project_kit"
        ):
            found.append(str(node.args[0].value))
    return found


def test_the_check_finds_an_import_of_the_backbone() -> None:
    source = (
        "import project_kit\nfrom project_kit.cli import main\nimport importlib\n"
        "importlib.import_module('project_kit.friction_check')\nimport json\n"
        "from _lib import backbone\nimportlib.util.find_spec('project_kit')\n"
    )
    assert _backbone_imports(source) == [
        "project_kit",
        "project_kit.cli",
        "project_kit.friction_check",
    ]


def test_no_capability_code_imports_the_backbone() -> None:
    """A capability's scripts run in their own environment and reach the backbone only
    through `pkit`'s commands (ADR-057 point 1; the lifecycle README, "How a registered
    command is run"): what lets a test answer those commands in its own process."""
    files = sorted(CAPABILITIES.glob("*/**/*.py"))
    assert files
    found = {
        path.relative_to(REPO).as_posix(): imports
        for path in files
        if (imports := _backbone_imports(path.read_text(encoding="utf-8")))
    }
    assert found == {}


def test_a_repository_s_capabilities_hold_the_scripts_the_loader_reads(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The loader reads this checkout's capabilities by name, and the adopter's copies are
    the same code, so a test that loads them tests what an adopter runs."""
    repo: AdopterRepo = make_adopter_repo(capabilities=("living-docs",))
    copied = repo.root / ".pkit" / "capabilities" / "living-docs" / "scripts" / "_lib"
    for path in sorted((LD_SCRIPTS / "_lib").glob("*.py")):
        assert (copied / path.name).read_text(encoding="utf-8") == path.read_text(
            encoding="utf-8"
        ), path.name
