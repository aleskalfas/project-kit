"""The one primitive for the commands a component registers (ADR-057 point 5; #1035).

- the lookup: one walk of the `commands:` tree keys every leaf by its token
  path, a reference is a path through it, a package file is read defensively,
  and every reader — the dispatcher, package validation, the validator
  registry, the predicate runner — resolves through it;
- the run: an answered run parses its document, every other ending is named,
  exceeding the bound kills the whole process group — a grandchild interpreter
  included, under the primitive and under the predicate policy (the query
  policy's case is `test_validators`) — and an interrupt kills it too;
- a run inside a run (#1144): every run tells its command its deadline; a
  nested run takes the time remaining, joins its caller's group, and starts
  nothing with none left; the outer deadline and an interrupt reach a nested
  run's command and what it started; the innermost overrun is the one named,
  and what it started ends with the outermost run;
- the predicate policy passes the subject and `--json` and leaves the
  environment as it is: no offline marker, a predicate may reach the network.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import command_runner, dispatcher, package_validate, process, validators
from project_kit.cli import main
from project_kit.command_runner import (
    CommandRun,
    Ending,
    command_leaves,
    registered_commands,
    resolve_command,
    run_command,
)
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from project_kit.process import PredicateRunner
from tests.adopter_repo import MakeAdopterRepo

# A script that starts a grandchild sharing its pipes — what a `uv run --script`
# shebang does with its interpreter — records the grandchild's pid beside
# itself, and outlives any bound a test sets.
_SPAWNS_A_GRANDCHILD = (
    "import subprocess, sys, time\n"
    'child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\n'
    'open(sys.argv[0] + ".pid", "w").write(str(child.pid))\n'
    "time.sleep(60)\n"
)

_TREE = {
    "detect": {"script": "scripts/detect.py", "help": "Detect."},
    "grp": {
        "help": "A group.",
        "check": {"script": "scripts/check.py", "help": "Check things.", "query-contract": True},
        "note": "not a mapping, skipped",
    },
    "stray": "not a mapping, skipped",
}


def _script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _package(component_dir: Path, commands_yaml: str, extra_yaml: str = "") -> None:
    component_dir.mkdir(parents=True, exist_ok=True)
    name = component_dir.name
    (component_dir / "package.yaml").write_text(
        f"schema_version: 2\ncomponent:\n  kind: capability\n  name: {name}\n  version: 0.1.0\n"
        "description: Synthetic capability for command-runner tests.\n"
        'requires_backbone: ">=0.1.0"\n'
        f"{commands_yaml}{extra_yaml}",
        encoding="utf-8",
    )


def _assert_gone(pid: int) -> None:
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    os.kill(pid, 9)
    pytest.fail("the grandchild survived the process-group kill")


# --- the lookup ----------------------------------------------------------------


def test_the_walk_keys_every_leaf_by_its_path_and_skips_what_is_not_a_mapping() -> None:
    leaves = command_leaves(_TREE)
    assert list(leaves) == [("detect",), ("grp", "check")]
    assert leaves[("grp", "check")]["query-contract"] is True


def test_a_reference_is_a_path_through_the_tree(tmp_path: Path) -> None:
    commands = command_runner.commands_of(tmp_path, _TREE)
    check = resolve_command(commands, "grp check")
    assert check is not None
    assert (check.reference, check.name, check.help) == ("grp check", "check", "Check things.")
    assert check.script == tmp_path / "scripts" / "check.py"
    assert resolve_command(commands, "  grp   check ") is check
    assert resolve_command(commands, "check") is None  # a leaf's name alone is not its path
    assert resolve_command(commands, "grp") is None  # a group is not a command


@pytest.mark.parametrize(
    "package",
    [None, "commands: [not, a, mapping]\n", "commands: {unclosed\n", "- a list, not a mapping\n"],
    ids=["absent", "commands-not-a-mapping", "unparsable", "file-not-a-mapping"],
)
def test_a_package_file_is_read_defensively(tmp_path: Path, package: str | None) -> None:
    if package is not None:
        (tmp_path / "package.yaml").write_text(package, encoding="utf-8")
    assert registered_commands(tmp_path) == {}


def test_every_reader_resolves_a_command_through_the_one_lookup(
    make_adopter_repo: MakeAdopterRepo, capfd: pytest.CaptureFixture[str]
) -> None:
    root = make_adopter_repo().root
    cap_dir = root / ".pkit" / "capabilities" / "cap"
    _package(
        cap_dir,
        "commands:\n"
        "  detect:\n    script: scripts/detect.py\n    help: Detect.\n"
        "  grp:\n"
        "    check:\n      script: scripts/check.py\n      help: Check things.\n"
        "      query-contract: true\n",
        "validators:\n  thing:\n    command: grp check\n",
    )
    _script(cap_dir / "scripts" / "detect.py", "print('{}')\n")
    _script(
        cap_dir / "scripts" / "check.py",
        'import json\nprint(json.dumps({"summary": ["check.py answered."], "findings": []}))\n',
    )
    backbone = read_backbone_manifest(root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability", name="cap", manifest=".pkit/capabilities/cap/manifest.yaml"
        )
    )
    write_backbone_manifest(root, backbone)

    registered = registered_commands(cap_dir)
    check = registered[("grp", "check")]

    # Package validation walks with the same function, and finds nothing to report.
    assert package_validate.command_leaves is command_runner.command_leaves
    [report] = [
        r
        for r in package_validate.validate_installed_packages(root).reports
        if r.file.parent == cap_dir
    ]
    assert report.errors == ()
    # The predicate runner addresses the same leaves by their names.
    assert process._load_command_registry(cap_dir) == {
        "detect": registered[("detect",)].script,
        "check": check.script,
    }
    # The dispatcher's lookup, and its command tree.
    assert dispatcher.resolve_capability_script(root, "cap", "grp check") == check.script
    assert CliRunner().invoke(main, ["cap", "grp", "check"]).exit_code == 0
    assert "check.py answered." in capfd.readouterr().out
    # The validator registry runs the leaf its entry names.
    [member] = [v for v in validators.registered_validators(root) if v.name == "cap:thing"]
    assert member.help == "Check things."
    assert member.run(root).summary == ("check.py answered.",)


# --- the run -------------------------------------------------------------------


def test_an_answered_run_parses_its_document_from_the_working_directory(tmp_path: Path) -> None:
    script = _script(
        tmp_path / "answer.py",
        "import json, os, sys\n"
        'print(json.dumps({"args": sys.argv[1:], "cwd": os.getcwd(),'
        ' "marker": os.environ.get("MARK")}))\n'
        'sys.stderr.write("diagnostics\\n")\n',
    )
    run = run_command(script, ["a", "--json"], cwd=tmp_path, extra_env={"MARK": "set"})
    assert run.ending is Ending.ANSWERED
    assert run.document == {
        "args": ["a", "--json"],
        "cwd": str(tmp_path.resolve()),
        "marker": "set",
    }
    assert (run.returncode, run.stderr, run.bound_seconds) == (0, "diagnostics\n", 30)


@pytest.mark.parametrize(
    ("body", "ending", "returncode"),
    [
        ("print('not json')\n", Ending.UNPARSABLE, 0),
        ("import sys\nsys.stdout.buffer.write(b'\\xff\\xfe')\n", Ending.UNPARSABLE, 0),
        # a bad byte inside a JSON string: with a replacing decoder this would
        # parse and answer; the answer must be no answer
        (
            "import sys\nsys.stdout.buffer.write(b'{\"result\": true, \"note\": \"\\xff\"}')\n",
            Ending.UNPARSABLE,
            0,
        ),
        ("print('{} trailing')\n", Ending.UNPARSABLE, 0),
        (
            "import sys\nprint('{}')\nsys.stderr.write('boom\\n')\nsys.exit(3)\n",
            Ending.ABNORMAL_EXIT,
            3,
        ),
    ],
    ids=["not-json", "undecodable", "undecodable-inside-a-string", "trailing-text", "non-zero-exit"],
)
def test_every_ending_but_an_answer_is_named(
    tmp_path: Path, body: str, ending: Ending, returncode: int
) -> None:
    run = run_command(_script(tmp_path / "cmd.py", body), [], cwd=tmp_path)
    assert (run.ending, run.returncode) == (ending, returncode)
    if ending is Ending.ABNORMAL_EXIT:
        assert run.stderr == "boom\n"


def test_a_script_that_cannot_start_is_not_started(tmp_path: Path) -> None:
    script = tmp_path / "not-executable.py"
    script.write_text("print('{}')\n", encoding="utf-8")
    run = run_command(script, [], cwd=tmp_path)
    assert run.ending is Ending.NOT_STARTED
    assert "Permission denied" in run.detail


def test_exceeding_the_bound_kills_the_whole_process_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _script(tmp_path / "slow.py", _SPAWNS_A_GRANDCHILD)
    monkeypatch.setattr(command_runner, "COMMAND_TIMEOUT_SECONDS", 1)
    started = time.monotonic()
    run = run_command(script, [], cwd=tmp_path)
    assert time.monotonic() - started < 15  # not the grandchild's sixty seconds
    assert (run.ending, run.bound_seconds) == (Ending.TIMED_OUT, 1)
    _assert_gone(int((tmp_path / "slow.py.pid").read_text()))


def test_an_interrupt_kills_the_group_before_it_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _script(tmp_path / "slow.py", _SPAWNS_A_GRANDCHILD)
    pid_file = tmp_path / "slow.py.pid"

    def interrupted(
        self: subprocess.Popen[bytes], input: bytes | None = None, timeout: float | None = None
    ) -> None:
        for _ in range(100):
            if pid_file.is_file() and pid_file.read_text():
                break
            time.sleep(0.1)
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess.Popen, "communicate", interrupted)
    with pytest.raises(KeyboardInterrupt):
        run_command(script, [], cwd=tmp_path)
    _assert_gone(int(pid_file.read_text()))


# --- a run inside a run (#1144) -------------------------------------------------

# A command that starts a child sharing its pipes, records its own pid and the
# child's beside itself, and outlives any bound a test sets: a filler, and the
# `pkit` reading command it starts.
_STARTS_A_CHILD = (
    "import os, subprocess, sys, time\n"
    'child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\n'
    'open(sys.argv[0] + ".pids", "w").write(f"{os.getpid()} {child.pid}")\n'
    "time.sleep(60)\n"
)

# A command that prints what the runner told it, as JSON.
_TELLS_ITS_RUN = (
    "import json, os\n"
    "print(json.dumps({'deadline': os.environ.get('PKIT_COMMAND_DEADLINE'),"
    " 'strays': os.environ.get('PKIT_COMMAND_STRAYS'),"
    " 'pid': os.getpid(), 'pgid': os.getpgrp(), 'sid': os.getsid(0)}))\n"
)


def _nested_runner(path: Path, then: str = "") -> Path:
    """A command that runs the script its argument names through this runner — as
    a `pkit` a query starts runs a filler — prints how that run ended, then runs
    `then`. Under this interpreter, so it imports the runner under test."""
    path.write_text(
        f"#!{sys.executable}\n"
        "import json, sys, time\n"
        "from pathlib import Path\n"
        "from project_kit.command_runner import run_command\n"
        "run = run_command(Path(sys.argv[1]), [], cwd=Path.cwd())\n"
        "print(json.dumps({'ending': run.ending.value, 'bound': run.bound_seconds}), flush=True)\n"
        + then,
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _pids(script: Path) -> list[int]:
    """The pids a `_STARTS_A_CHILD` script recorded, once it has."""
    record = script.with_name(script.name + ".pids")
    for _ in range(100):
        if record.is_file() and record.read_text():
            return [int(pid) for pid in record.read_text().split()]
        time.sleep(0.1)
    pytest.fail(f"{script.name} never started")


@pytest.fixture
def outermost(monkeypatch: pytest.MonkeyPatch) -> None:
    """This process runs inside no run, whatever started the test suite."""
    monkeypatch.delenv(command_runner.DEADLINE_ENV, raising=False)
    monkeypatch.delenv(command_runner.STRAYS_ENV, raising=False)


def test_a_run_tells_its_command_its_deadline_and_gives_it_a_group_of_its_own(
    tmp_path: Path, outermost: None
) -> None:
    started = time.time()
    run = run_command(_script(tmp_path / "tell.py", _TELLS_ITS_RUN), [], cwd=tmp_path)
    assert (run.ending, run.bound_seconds) == (Ending.ANSWERED, 30)
    told = run.document
    assert told["pid"] == told["pgid"] == told["sid"]  # a session and a group of its own
    # Its own end less the time the command keeps to answer.
    margin = command_runner.ANSWER_MARGIN_SECONDS
    assert started + 30 - margin - 0.01 <= float(told["deadline"]) <= time.time() + 30 - margin
    assert told["strays"] and not Path(told["strays"]).exists()  # named, not created


def test_a_run_inside_a_run_takes_the_time_remaining_and_joins_its_callers_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inherited = time.time() + 5
    monkeypatch.setenv(command_runner.DEADLINE_ENV, f"{inherited:.3f}")
    monkeypatch.setenv(command_runner.STRAYS_ENV, str(tmp_path / "strays"))
    run = run_command(_script(tmp_path / "tell.py", _TELLS_ITS_RUN), [], cwd=tmp_path)
    assert run.ending is Ending.ANSWERED
    assert 4 <= run.bound_seconds <= 5  # the time remaining, never its own thirty seconds
    told = run.document
    assert told["pgid"] == os.getpgrp()  # the caller's group, which the outer kill reaches
    assert float(told["deadline"]) <= inherited - command_runner.ANSWER_MARGIN_SECONDS + 0.01
    assert told["strays"] == str(tmp_path / "strays")  # the outermost run's record, passed on


def test_a_run_inside_a_run_with_no_time_left_does_not_start_its_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(command_runner.DEADLINE_ENV, f"{time.time() - 1:.3f}")
    script = _script(tmp_path / "touch.py", "open(__file__ + '.ran', 'w')\nprint('{}')\n")
    run = run_command(script, [], cwd=tmp_path)
    assert (run.ending, run.bound_seconds, run.detail) == (
        Ending.NOT_STARTED,
        0,
        command_runner.NO_TIME_LEFT,
    )
    assert not (tmp_path / "touch.py.ran").exists()
    assert validators.why_no_answer(run, "fill") == (
        f"command 'fill' could not start: {command_runner.NO_TIME_LEFT}"
    )


def test_a_deadline_that_is_no_number_is_no_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(command_runner.DEADLINE_ENV, "soon")
    run = run_command(_script(tmp_path / "tell.py", _TELLS_ITS_RUN), [], cwd=tmp_path)
    assert (run.ending, run.bound_seconds) == (Ending.ANSWERED, 30)
    assert run.document["pgid"] == run.document["pid"]


def test_the_outer_deadline_ends_a_nested_run_and_everything_its_command_started(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outermost: None
) -> None:
    # The caller hangs after its nested run: only the outer kill can end it, and
    # the filler's child, which the nested run could not reach, goes with it.
    filler = _script(tmp_path / "filler.py", _STARTS_A_CHILD)
    caller = _nested_runner(tmp_path / "caller.py", then="time.sleep(60)\n")
    monkeypatch.setattr(command_runner, "COMMAND_TIMEOUT_SECONDS", 5)
    monkeypatch.setattr(command_runner, "ANSWER_MARGIN_SECONDS", 2)
    started = time.monotonic()
    run = run_command(caller, [str(filler)], cwd=tmp_path)
    assert time.monotonic() - started < 15  # not the sixty seconds any of them sleeps
    assert (run.ending, run.bound_seconds) == (Ending.TIMED_OUT, 5)
    for pid in _pids(filler):
        _assert_gone(pid)


def test_an_interrupt_of_the_outer_run_ends_a_nested_run_s_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outermost: None
) -> None:
    # A nested run's command shares the outer run's group, so the one kill an
    # interrupt sends reaches it — in a session of its own, it would outlive it.
    filler = _script(tmp_path / "filler.py", _STARTS_A_CHILD)
    caller = _nested_runner(tmp_path / "caller.py")

    def interrupted(
        self: subprocess.Popen[bytes], input: bytes | None = None, timeout: float | None = None
    ) -> None:
        _pids(filler)
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess.Popen, "communicate", interrupted)
    with pytest.raises(KeyboardInterrupt):
        run_command(caller, [str(filler)], cwd=tmp_path)
    for pid in _pids(filler):
        _assert_gone(pid)


def test_the_innermost_overrun_is_named_and_what_it_started_ends_with_the_outermost_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outermost: None
) -> None:
    # The nested run's deadline comes first, so its caller answers in time, naming
    # the overrun; the filler's child it could not kill ends with the outer run.
    filler = _script(tmp_path / "filler.py", _STARTS_A_CHILD)
    caller = _nested_runner(tmp_path / "caller.py")
    monkeypatch.setattr(command_runner, "COMMAND_TIMEOUT_SECONDS", 6)
    monkeypatch.setattr(command_runner, "ANSWER_MARGIN_SECONDS", 2.5)
    started = time.monotonic()
    run = run_command(caller, [str(filler)], cwd=tmp_path)
    assert time.monotonic() - started < 6  # answered within the outer bound
    assert run.ending is Ending.ANSWERED
    assert run.document["ending"] == "timed-out"
    assert 0 < run.document["bound"] < 3.5  # the time remaining, less the caller's margin
    for pid in _pids(filler):
        _assert_gone(pid)


# --- the predicate policy ------------------------------------------------------


def _predicate_capability(tmp_path: Path, body: str) -> PredicateRunner:
    cap_dir = tmp_path / ".pkit" / "capabilities" / "cap"
    _package(cap_dir, "commands:\n  probe:\n    script: scripts/probe.py\n    help: A predicate.\n")
    _script(cap_dir / "scripts" / "probe.py", body)
    return PredicateRunner(
        capability="cap", capability_dir=cap_dir, repo_root=tmp_path, subject="S-1"
    )


def test_the_predicate_policy_passes_the_subject_and_marks_nothing_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PKIT_OFFLINE", raising=False)
    monkeypatch.delenv("UV_OFFLINE", raising=False)
    runner = _predicate_capability(
        tmp_path,
        "import json, os, sys\n"
        'print(json.dumps({"result": True, "args": sys.argv[1:], "cwd": os.getcwd(),'
        ' "offline": [os.environ.get(k) for k in ("PKIT_OFFLINE", "UV_OFFLINE")]}))\n',
    )
    payload = runner.run_raw({"run": "probe"})
    assert payload == {
        "result": True,
        "args": ["S-1", "--json"],
        "cwd": str(tmp_path.resolve()),
        "offline": [None, None],
    }


@pytest.mark.parametrize(
    "body",
    [
        "print('[1, 2]')\n",
        "print('not json')\n",
        "import sys\nsys.stdout.buffer.write(b'\\xff\\xfe')\n",  # a crash before the shared runner
        "import sys\nprint('{}')\nsys.exit(1)\n",
    ],
    ids=["not-an-object", "not-json", "undecodable", "non-zero-exit"],
)
def test_the_predicate_policy_reads_anything_but_an_answered_object_as_indeterminate(
    tmp_path: Path, body: str
) -> None:
    assert _predicate_capability(tmp_path, body).run_raw({"run": "probe"}) is None


def test_the_predicate_policy_stops_a_grandchild_at_the_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _predicate_capability(tmp_path, _SPAWNS_A_GRANDCHILD)
    monkeypatch.setattr(command_runner, "COMMAND_TIMEOUT_SECONDS", 1)
    started = time.monotonic()
    assert runner.run_raw({"run": "probe"}) is None
    assert time.monotonic() - started < 15
    _assert_gone(int((runner.capability_dir / "scripts" / "probe.py.pid").read_text()))


def test_a_run_reports_rather_than_raises(tmp_path: Path) -> None:
    # The primitive's contract with every policy: what the command did is an
    # ending, never an exception.
    run = run_command(tmp_path / "absent.py", [], cwd=tmp_path)
    assert isinstance(run, CommandRun)
    assert run.ending is Ending.NOT_STARTED
