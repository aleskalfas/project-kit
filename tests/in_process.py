"""A capability's code run in the test's own process, and the guard on the processes a test starts.

A capability script runs in its own environment and reaches the backbone only
through `pkit`'s commands, an argument list in and one JSON document out
(ADR-057 point 1). Starting a process for each costs a third of a second to a
second, and most tests check what the code answers, not that a process ran it
(#2313). Four parts let such a test call the code in its own process, the
argument lists and the documents unchanged (`tests/README.md`, "Running the
suite"):

- **The in-process `pkit`** (`InProcessPkit`): `pkit`, answered by the
  backbone's CLI in this process under the contract a process gives.
  `route_pkit` sends every `pkit` call of a capability to it, through the one
  private function the capability's calls go through, `_lib.backbone._run`.
- **The loader** (`load`): a capability's scripts and `_lib`, imported in this
  process, each capability's `_lib` kept apart; `run_main` runs a script's
  `main` as its process ran.
- **The reverse seam** (`start_in_process`): the commands the backbone's runner
  starts for a component, started in this process. The runner's one lookup
  still resolves each command, and only its start is replaced.
- **The guard** (`ProcessStarts`, `judge`): a test that starts `pkit` or a
  capability script carries the `process` mark with its reason, or fails.
"""

from __future__ import annotations

import contextlib
import importlib
import importlib.util
import inspect
import io
import itertools
import os
import shlex
import subprocess
import sys
import traceback
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from pathlib import Path
from types import FrameType, ModuleType
from typing import Any, Protocol

import pytest
from click.testing import CliRunner

from project_kit import cli, command_runner, data_points, process, report_context, validators
from project_kit.command_runner import CommandRun, Ending

REPO = Path(__file__).resolve().parent.parent
#: This checkout's capabilities, whose code `load` reads by a capability's name.
CAPABILITIES = REPO / ".pkit" / "capabilities"

# --- the in-process `pkit` ------------------------------------------------------------------

#: What the backbone's runner gives a query, and so the `pkit` a query starts (the
#: lifecycle README, "How a registered command is run"): the offline marker set, the
#: base override and the change's own head removed.
QUERY_ENVIRONMENT: Mapping[str, str | None] = {
    **validators.OFFLINE_MARKER,
    **{name: None for name in validators.QUERY_DROPPED_ENV},
}

#: The keywords of `subprocess.run` the in-process `pkit` models. It refuses any other.
MODELLED = ("cwd", "capture_output", "text", "check")

#: What runs `pkit` for a capability: `subprocess.run`'s signature, the argument list first.
Runner = Callable[..., subprocess.CompletedProcess[Any]]


def reset_caches() -> None:
    """Clear every cache a module of the backbone keeps for the life of its process, each
    function `functools.cache` or `functools.lru_cache` wraps, as a new process of `pkit`
    holds none."""
    for name, module in list(sys.modules.items()):
        if module is None or not (name == "project_kit" or name.startswith("project_kit.")):
            continue
        for value in list(vars(module).values()):
            clear = getattr(value, "cache_clear", None)
            if callable(clear) and getattr(value, "__module__", None) == name:
                clear()


class InProcessPkit:
    """`pkit`, answered by the backbone's CLI in this process: what `subprocess.run` gives
    for `["pkit", ...]`, under the contract a process gives (#2314, choice 1).

    - It returns a `CompletedProcess` whose `args` is the argument list, with standard
      output and standard error apart.
    - Its `returncode` is the command's exit code.
    - The command runs from `cwd`, or the current directory, which is restored after.
    - It runs in the environment the backbone's runner gives a query
      (`QUERY_ENVIRONMENT`), and the caller's is restored after.
    - An exception the command raises is exit 1, its traceback on standard error, as a
      crashed process ends.
    - A keyword it does not model (`MODELLED`) is refused with `TypeError`, so a call it
      would answer wrongly fails at once.
    - The backbone's process-wide caches are cleared before each call (`reset_caches`).

    A call uses the process's directory, environment and standard streams, so it is not
    safe beside another in a thread. A script that reads in threads, as `fill-doc-check`
    does, has its readings called one by one, or stood in for. `calls` holds each
    argument list it was given, in order."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(
        self,
        args: Sequence[str | os.PathLike[str]],
        *,
        cwd: str | os.PathLike[str] | None = None,
        capture_output: bool = False,
        text: bool = False,
        check: bool = False,
        **unmodelled: Any,
    ) -> subprocess.CompletedProcess[Any]:
        if unmodelled:
            raise TypeError(
                f"the in-process `pkit` models only {', '.join(MODELLED)}, not "
                f"{', '.join(sorted(unmodelled))}: run this call as a process, marked, or "
                f"model the keyword here"
            )
        argv = [os.fspath(word) for word in args]
        if not argv or Path(argv[0]).name != "pkit":
            raise ValueError(f"the in-process `pkit` answers `pkit` alone, not {argv[:1]}")
        self.calls.append(argv)
        reset_caches()
        with contextlib.chdir(os.fspath(cwd) if cwd is not None else os.getcwd()):
            result = CliRunner().invoke(cli.main, argv[1:], env=QUERY_ENVIRONMENT, prog_name="pkit")
        returncode, stdout, stderr = result.exit_code, result.stdout, result.stderr
        crashed = result.exception is not None and not isinstance(result.exception, SystemExit)
        if crashed and result.exc_info is not None:
            returncode = 1
            stderr += "".join(traceback.format_exception(*result.exc_info))
        out: Any = None
        err: Any = None
        if capture_output:
            out, err = (stdout, stderr) if text else (stdout.encode(), stderr.encode())
        else:
            sys.stdout.write(stdout)
            sys.stderr.write(stderr)
        completed = subprocess.CompletedProcess(argv, returncode, out, err)
        if check:
            completed.check_returncode()
        return completed


#: `subprocess.run` as the capabilities' runners bind it by default.
_SUBPROCESS_RUN = subprocess.run


def _software_analysis(original: Callable[..., Any], pkit: Runner) -> Callable[..., Any]:
    """software-analysis' `_run(root, argv, run)`, used unchanged: its default runner,
    `subprocess.run`, swapped for the in-process `pkit`, and a runner a test passes kept."""

    def run(root: Path, argv: list[str], run: Any) -> subprocess.CompletedProcess[str]:
        return original(root, argv, pkit if run is _SUBPROCESS_RUN else run)

    return run


def _living_docs(original: Callable[..., Any], pkit: Runner) -> Callable[..., Any]:
    """living-docs' `_run(argv, **options)`, `subprocess.run`'s signature: the in-process
    `pkit` in its place."""
    return pkit


#: How each capability's one private function is replaced, by the capability's name.
ROUTES: Mapping[str, Callable[[Callable[..., Any], Runner], Callable[..., Any]]] = {
    "living-docs": _living_docs,
    "software-analysis": _software_analysis,
}


def route_pkit(
    monkeypatch: pytest.MonkeyPatch, backbone: ModuleType, pkit: Runner | None = None
) -> Runner:
    """Send every `pkit` call of a capability to the in-process `pkit`, or to `pkit` when
    given, such as one that stands for an older backbone around it. `backbone` is the
    capability's `_lib.backbone`, as `load` gave it, whose `_run` every call goes through,
    looked up when called. Returns the runner, whose `calls` a test may read."""
    capability = Path(backbone.__file__ or "").parents[2].name
    if capability not in ROUTES:
        raise LookupError(f"no route to the in-process `pkit` for {capability!r}: add it to ROUTES")
    runner = pkit if pkit is not None else InProcessPkit()
    monkeypatch.setattr(backbone, "_run", ROUTES[capability](backbone._run, runner))
    return runner


# --- the loader -----------------------------------------------------------------------------


def _scripts_of(capability: str | Path) -> Path:
    return CAPABILITIES / capability / "scripts" if isinstance(capability, str) else capability


def _ours() -> list[str]:
    return [name for name in sys.modules if name == "_lib" or name.startswith("_lib.")]


def load(capability: str | Path, *names: str) -> tuple[ModuleType, ...]:
    """A capability's scripts and `_lib` modules, imported in this process together, as one
    run of its scripts imports them: a name ending `.py` is a script of its `scripts/`, any
    other a module of its `_lib`. `capability` is the name of a capability in this
    checkout, or the `scripts/` folder of one elsewhere, such as an adopter's copy.

    Each capability's `_lib` is kept apart. Its `scripts/` folder is on the import path,
    and its `_lib` in `sys.modules`, only while they load. Both are left after as they
    were, so another capability's `_lib` loads later, and one loaded before keeps working.
    Each call imports afresh: the modules of one call share their `_lib`, and two calls
    share nothing. A script is known by `_script_<capability>_<name>`."""
    scripts = _scripts_of(capability)
    saved = {name: sys.modules.pop(name) for name in _ours()}
    path = list(sys.path)
    sys.path.insert(0, str(scripts))
    try:
        return tuple(
            _script(scripts, name) if name.endswith(".py") else _lib(name) for name in names
        )
    finally:
        sys.path[:] = path
        for name in _ours():
            del sys.modules[name]
        sys.modules.update(saved)


def _lib(name: str) -> ModuleType:
    return importlib.import_module(f"_lib.{name}")


def _script(scripts: Path, name: str) -> ModuleType:
    """A script loaded as a module. It stays in `sys.modules` under its own name, which no
    other script shares, so what it defines can be found by its module."""
    module_name = f"_script_{scripts.parent.name}_{Path(name).stem}".replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, scripts / name)
    if spec is None or spec.loader is None:
        raise ImportError(f"{scripts / name} cannot be loaded as a module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def _environment(extra: Mapping[str, str | None]) -> Iterator[None]:
    """`os.environ` with `extra` laid over it, a `None` removing its variable, restored after."""
    saved = dict(os.environ)
    try:
        for name, value in extra.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)


def run_main(
    script: ModuleType,
    *args: str,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str | None] | None = None,
) -> subprocess.CompletedProcess[str]:
    """A script's `main`, run in this process as its process ran: `sys.argv` its path and
    `args`, from `cwd` (the current directory by default), with `env` laid over the
    environment, standard output and standard error captured apart. Its exit code is
    what `main` returned or exited with. An exception is exit 1, with its traceback on
    standard error, as a crashed process ends. The directory, the environment and
    `sys.argv` are restored after."""
    stdout, stderr = io.StringIO(), io.StringIO()
    argv = [getattr(script, "__file__", None) or script.__name__, *args]
    saved_argv = sys.argv
    returncode: Any = 0
    with (
        contextlib.chdir(os.fspath(cwd) if cwd is not None else os.getcwd()),
        _environment(env or {}),
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
    ):
        sys.argv = argv
        try:
            returncode = script.main()
        except SystemExit as exc:
            returncode = exc.code
        except Exception:
            returncode = 1
            stderr.write(traceback.format_exc())
        finally:
            sys.argv = saved_argv
    if returncode is None:
        returncode = 0
    elif not isinstance(returncode, int):
        stderr.write(f"{returncode}\n")
        returncode = 1
    return subprocess.CompletedProcess(argv, returncode, stdout.getvalue(), stderr.getvalue())


# --- the reverse seam -----------------------------------------------------------------------

#: The backbone's modules that start a registered command through the runner, each holding
#: `run_command` under that name.
STARTERS: tuple[ModuleType, ...] = (
    command_runner,
    validators,
    data_points,
    process,
    report_context,
)


def start_in_process(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Start in this process every command the backbone's runner starts for a component:
    `run_command` replaced in each module that calls it (`STARTERS`). The runner's one
    lookup still resolves the command to its script, so a registration that names no
    script, or another one, fails as it does with a process: only the start is replaced.

    The script the lookup resolved is loaded from its own `scripts/` folder, its `pkit`
    calls routed to the in-process `pkit` where its capability has a route (`ROUTES`), and
    its `main` run with the run's arguments, from the run's directory, in the environment
    the run gives it. Its answer is read as `run_command` reads one (`CommandRun`). Nothing
    bounds the run in this process, so the bound and the grace are not used. A request on
    standard input is not modelled, and is refused. Returns the scripts started, in order:
    a generalisation of `answer_from_tracker` (`tests/pm_lifecycle_world.py`)."""
    started: list[Path] = []

    def start(
        script: Path,
        args: Sequence[str],
        *,
        cwd: Path,
        extra_env: Mapping[str, str] | None = None,
        drop_env: Collection[str] = (),
        bound_seconds: float | None = None,
        stdin: bytes | None = None,
        grace_seconds: float | None = None,
    ) -> CommandRun:
        if stdin is not None:
            raise TypeError("the in-process start does not model a request on standard input")
        started.append(script)
        own = command_runner.COMMAND_TIMEOUT_SECONDS if bound_seconds is None else bound_seconds
        try:
            modules = _loaded(script)
        except (OSError, ImportError, SyntaxError) as exc:
            return CommandRun(
                Ending.NOT_STARTED, own, detail=str(exc), own_bound_seconds=bound_seconds
            )
        environment: dict[str, str | None] = {**(extra_env or {})}
        environment.update({name: None for name in drop_env})
        with monkeypatch.context() as patched:
            if modules[1] is not None and Path(script).parents[1].name in ROUTES:
                route_pkit(patched, modules[1])
            completed = run_main(modules[0], *args, cwd=cwd, env=environment)
        return _read(completed, own, bound_seconds)

    for module in STARTERS:
        monkeypatch.setattr(module, "run_command", start)
    return started


def _loaded(script: Path) -> tuple[ModuleType, ModuleType | None]:
    """A script the runner would start, loaded, with its capability's `_lib.backbone`
    where it has one."""
    if not script.is_file():
        raise FileNotFoundError(f"[Errno 2] No such file or directory: {str(script)!r}")
    scripts = script.parent
    if (scripts / "_lib" / "backbone.py").is_file():
        loaded, backbone = load(scripts, script.name, "backbone")
        return loaded, backbone
    (loaded,) = load(scripts, script.name)
    return loaded, None


def _read(
    completed: subprocess.CompletedProcess[str], own: float, bound_seconds: float | None
) -> CommandRun:
    """A run in this process read as `run_command` reads a process's."""
    common: dict[str, Any] = {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "own_bound_seconds": bound_seconds,
    }
    if completed.returncode != 0:
        return CommandRun(Ending.ABNORMAL_EXIT, own, **common)
    try:
        document = command_runner.parse_document(completed.stdout)
    except ValueError:
        return CommandRun(Ending.UNPARSABLE, own, **common)
    return CommandRun(Ending.ANSWERED, own, document=document, **common)


# --- the guard ------------------------------------------------------------------------------

#: The mark a test that keeps a real process carries, with its reason (#2314, choice 4):
#: `@pytest.mark.process("<why the process is the point>")`.
MARK = "process"

#: The modules the guard does not hold yet, one name a line, in a file beside this one.
#: Each slice of #2313 takes out the modules it converts; a module not listed is held.
BASELINE = Path(__file__).with_name("process_guard_baseline.txt")

#: Programs that run a script named among their arguments.
_INTERPRETERS = ("bash", "sh", "zsh", "uv", "env")


def _words(args: Any) -> list[str]:
    if isinstance(args, bytes):
        args = args.decode(errors="replace")
    if isinstance(args, str):
        return shlex.split(args)
    if isinstance(args, os.PathLike):
        return [os.fspath(args)]
    return [os.fsdecode(word) if isinstance(word, bytes) else os.fspath(word) for word in args]


def _capability_script(word: str) -> bool:
    """Whether `word` is a path in a capability's `scripts/` folder, or the folder itself."""
    parts = Path(word).parts
    return any(
        part == "capabilities" and len(parts) > i + 2 and parts[i + 2] == "scripts"
        for i, part in enumerate(parts)
    )


def starts_pkit_or_a_capability_script(args: Any) -> bool:
    """Whether a process started with `args` runs `pkit` or a capability script: `pkit`
    itself, `python -m project_kit`, a capability script, or an interpreter handed one or
    a capability's `scripts/` folder, such as a driver that imports its `_lib`."""
    words = _words(args)
    if not words:
        return False
    program = Path(words[0]).name
    if program == "pkit" or _capability_script(words[0]):
        return True
    if not (program.startswith("python") or program in _INTERPRETERS):
        return False
    rest = words[1:]
    return (
        any(_capability_script(word) for word in rest)
        or any(a == "-m" and b == "project_kit" for a, b in itertools.pairwise(rest))
        or (program == "uv" and "pkit" in rest)
    )


def _asked_of_the_runner(frame: FrameType | None) -> bool:
    """Whether a start comes from a test's own call of `run_command`: the runner's tests,
    whose subject is the process the runner starts."""
    while frame is not None:
        if frame.f_code.co_name == "run_command" and frame.f_globals.get("__name__") == (
            command_runner.__name__
        ):
            caller = frame.f_back
            return caller is not None and str(caller.f_globals.get("__name__", "")).startswith(
                "tests."
            )
        frame = frame.f_back
    return False


class ProcessStarts:
    """The processes of `pkit` or a capability script a test starts, each argument list in
    order, counted from `subprocess.Popen`, which every way the standard library starts a
    process goes through. Not counted: what an adopter template's build starts, which
    whichever test first asks for the template pays (`adopter_repo.building_template`),
    and what a test of the runner asks of `run_command` itself."""

    def __init__(self, building: Callable[[], bool]) -> None:
        self.started: list[list[str]] = []
        self._building = building

    def watch(self, monkeypatch: pytest.MonkeyPatch) -> ProcessStarts:
        original = subprocess.Popen.__init__
        starts = self

        def counted(popen: subprocess.Popen[Any], args: Any, *rest: Any, **kwargs: Any) -> None:
            if (
                starts_pkit_or_a_capability_script(args)
                and not starts._building()
                and not _asked_of_the_runner(inspect.currentframe())
            ):
                starts.started.append(_words(args))
            original(popen, args, *rest, **kwargs)

        monkeypatch.setattr(subprocess.Popen, "__init__", counted)
        return self


def baseline() -> frozenset[str]:
    """The modules the guard does not hold yet (`BASELINE`)."""
    lines = BASELINE.read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip() for line in lines if line.strip() and not line.startswith("#"))


class Judged(Protocol):
    """What the guard reads of a test: its module's file and its marks, as a `pytest.Item`
    gives them."""

    @property
    def path(self) -> Path: ...

    def iter_markers(self, name: str | None = None) -> Iterator[pytest.Mark]: ...


def judge(item: Judged, starts: ProcessStarts, unheld: Collection[str]) -> str | None:
    """Why the guard fails `item`, or `None`: a `process` mark with no reason, or a start of
    `pkit` or a capability script by a test without the mark, in a module the guard holds."""
    marks = list(item.iter_markers(MARK))
    for mark in marks:
        reason = mark.args[0] if mark.args else mark.kwargs.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return f"`@pytest.mark.{MARK}` needs its reason: why the process is the point"
    if marks or not starts.started or item.path.name in unheld:
        return None
    first = " ".join(starts.started[0])
    return (
        f"the test started {len(starts.started)} process(es) of `pkit` or a capability "
        f"script without `@pytest.mark.{MARK}(<reason>)`, the first `{first}`. Call the code "
        f"in this process (tests/in_process.py), or keep the process and mark the test with "
        f'why it is the point (tests/README.md, "Running the suite")'
    )
