"""project-management's one start of a `pkit` call (`_lib/backbone.py`, #2322).

Every `pkit` call of the capability's `_lib` modules goes through `backbone.run`, which
hands it to `backbone._run`, looked up when called, as living-docs' do (ADR-057 point
1). A test answers every call in its own process by replacing `_run` alone
(`tests/in_process.py`). What this module pins: the call reaches `_run` as it was
given, and each reader and writer gives `pkit` the argument list and the keywords it
gave before its calls had one start, so the capability's behaviour is unchanged.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.in_process import InProcessPkit, Runner, load, route_pkit

#: The capability's one start of a `pkit` call, by its place in a capability's tree.
CAPABILITY = "project-management"


def _is_pm_lib(module: object) -> bool:
    """Whether `module` is a module of a project-management `_lib`, by its file's place."""
    if not isinstance(module, ModuleType):
        return False
    path = Path(getattr(module, "__file__", None) or "")
    in_lib = len(path.parents) > 2 and path.parent.name == "_lib"
    return in_lib and path.parents[2].name == CAPABILITY


def route_every_backbone(monkeypatch: pytest.MonkeyPatch, pkit: Runner | None = None) -> Runner:
    """Send every `pkit` call of project-management's `_lib` modules this process has
    imported to the in-process `pkit`, or to `pkit` when given. A module that imports its
    siblings in both forms, as part of the `_lib` package or standalone-by-path, may
    reach either copy of `_lib/backbone.py`, so each copy is routed (`tests/in_process.py`,
    `route_pkit`). A copy counts where a module reaches it, not only where `sys.modules`
    lists it: a module imported earlier keeps the copy it imported, as its runners'
    defaults do, after a loader took that copy out of `sys.modules` (`load`). So the
    walk starts at each `_lib` module `sys.modules` lists and follows the `_lib` modules
    each holds. Returns the runner."""
    runner = pkit if pkit is not None else InProcessPkit()
    pending = [module for module in list(sys.modules.values()) if _is_pm_lib(module)]
    reached: dict[int, ModuleType] = {}
    while pending:
        module = pending.pop()
        if id(module) in reached:
            continue
        reached[id(module)] = module
        pending.extend(value for value in vars(module).values() if _is_pm_lib(value))
    for module in reached.values():
        if Path(module.__file__ or "").name == "backbone.py":
            route_pkit(monkeypatch, module, runner)
    return runner


BASE = "b" * 40
HEAD = "c" * 40
UNROUTED = {"PKIT_NO_ROUTE": "1"}
#: The keywords of a reading that runs from the working directory with no bound.
READ = {"capture_output": True, "text": True, "check": False}


class Recorder:
    """`backbone._run` stood in: each argument list and its keywords, answered by a
    failed run, so each reader stops at its first call."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(self, argv: Any, **options: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append((list(argv), dict(options)))
        return subprocess.CompletedProcess(list(argv), 2, "", "")


@pytest.fixture
def lib() -> dict[str, ModuleType]:
    """The capability's `_lib` modules that start `pkit`, loaded together."""
    names = (
        "backbone",
        "accepted_records",
        "decision_ids",
        "default_branch",
        "doc_check",
        "drift",
        "fixers",
        "friction_answers",
        "move_journal",
        "proposals",
        "ruled_artefacts",
        "topology",
        "use_case_citations",
    )
    return dict(zip(names, load("project-management", *names), strict=True))


@pytest.fixture
def recorded(lib: dict[str, ModuleType], monkeypatch: pytest.MonkeyPatch) -> Recorder:
    """Every backbone a loaded module reaches, its `_run` the recorder."""
    recorder = Recorder()
    reached = {id(m.backbone): m.backbone for m in lib.values() if hasattr(m, "backbone")}
    for module in [*reached.values(), lib["backbone"]]:
        monkeypatch.setattr(module, "_run", recorder)
    return recorder


def _calls(recorder: Recorder, call: Callable[[], Any]) -> list[tuple[list[str], dict[str, Any]]]:
    recorder.calls.clear()
    with contextlib.suppress(Exception):
        call()
    return list(recorder.calls)


def test_run_hands_the_call_to_run_looked_up_when_called(
    lib: dict[str, ModuleType], monkeypatch: pytest.MonkeyPatch
) -> None:
    backbone = lib["backbone"]
    recorder = Recorder()
    monkeypatch.setattr(backbone, "_run", recorder)
    backbone.run(["pkit", "status"], cwd="/x", timeout=5)
    assert recorder.calls == [(["pkit", "status"], {"cwd": "/x", "timeout": 5})]


def test_the_one_start_is_a_process_with_the_arguments_given(
    lib: dict[str, ModuleType], monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[tuple[Any, dict[str, Any]]] = []

    def process(argv: Any, **options: Any) -> subprocess.CompletedProcess[str]:
        started.append((argv, options))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", process)
    lib["backbone"].run(["pkit", "status"], capture_output=True)
    assert started == [(["pkit", "status"], {"capture_output": True})]


def test_the_readers_give_pkit_the_argument_lists_they_gave(
    lib: dict[str, ModuleType], recorded: Recorder, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unrouted = {**os.environ, **UNROUTED}
    bounded = {**READ, "timeout": 120}
    point = ["pkit", "connections", "resolve"]
    assert _calls(recorded, lambda: lib["doc_check"].read_point()) == [
        ([*point, "pkit::work-tracking:doc-check", "--json"], READ)
    ]
    assert _calls(recorded, lambda: lib["fixers"].read_point()) == [
        ([*point, "pkit::work-tracking:fixers", "--json"], bounded)
    ]
    assert _calls(recorded, lambda: lib["fixers"].read_types()) == [
        (["pkit", "friction", "artefacts", "--json"], bounded)
    ]
    assert _calls(recorded, lambda: lib["use_case_citations"].read_point()) == [
        ([*point, "pkit::work-tracking:use-cases", "--json"], bounded)
    ]
    assert _calls(recorded, lambda: lib["decision_ids"].lookup(["COR-001", "ADR-002"])) == [
        (["pkit", "refs", "lookup", "--json", "--", "COR-001", "ADR-002"], {**READ, "timeout": 30})
    ]
    base = ["pkit", "repository", "base", "--json"]
    assert _calls(recorded, lambda: lib["default_branch"].check_base("trunk")) == [
        ([*base, "--base=trunk"], {**READ, "timeout": 60})
    ]
    for at, call in [
        ("a", lambda: lib["default_branch"].read(cwd=tmp_path / "a")),
        ("b", lambda: lib["drift"].pin_commit(tmp_path / "b")),
        ("c", lambda: lib["proposals"].pin(tmp_path / "c")),
    ]:
        at_cwd = {**READ, "timeout": 60, "cwd": str(tmp_path / at)}
        assert _calls(recorded, call) == [(base, at_cwd)]
    copy = tmp_path / "copy"
    at_copy = {**READ, "timeout": 900, "cwd": str(copy)}
    assert _calls(recorded, lambda: lib["drift"].explain(copy, "ADR-001")) == [
        (["pkit", "friction", "explain", "ADR-001", "--json"], at_copy)
    ]
    assert _calls(recorded, lambda: lib["drift"].upstreams_at(copy)) == [
        (["pkit", "friction", "artefacts", "--json"], at_copy)
    ]
    assert _calls(recorded, lambda: lib["drift"].read_at(copy, HEAD)) == [
        ([*point, "pkit::work-tracking:fixers", "--json"], {**bounded, "cwd": str(copy)})
    ]
    monkeypatch.setattr(lib["ruled_artefacts"], "local_commits", lambda *_a, **_k: "")
    assert _calls(recorded, lambda: lib["ruled_artefacts"].ruled_altered(BASE, HEAD)) == [
        (
            ["pkit", "rule-sets", "altered", "--json", "--base", BASE, "--head", HEAD],
            {
                **READ,
                "cwd": None,
                "env": unrouted,
                "encoding": "utf-8",
                "errors": "replace",
                "timeout": 600,
            },
        )
    ]


def test_the_change_check_s_readers_give_pkit_the_argument_lists_they_gave(
    lib: dict[str, ModuleType], recorded: Recorder, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fa = lib["friction_answers"]
    unrouted = {**os.environ, **UNROUTED}
    bounded = {**READ, "env": unrouted, "timeout": 600}
    assert _calls(recorded, lambda: fa._discovery_at(BASE)) == [
        (["pkit", "friction", "artefacts", "--json", "--at", BASE], bounded)
    ]
    check = ["pkit", "friction", "check", "--json", "--base", "main"]
    assert _calls(recorded, lambda: fa._run_check(None, "main", cwd=None)) == [
        (check, {**bounded, "cwd": None})
    ]
    own = {**bounded, "cwd": tmp_path, "env": {**unrouted, "PKIT_CHECK_HEAD": HEAD}}
    assert _calls(recorded, lambda: fa._run_check(BASE, "main", cwd=tmp_path, own_head=HEAD)) == [
        ([*check, "--head", BASE], own)
    ]
    monkeypatch.setattr(fa, "_refresh_base", lambda _base: None)
    monkeypatch.setattr(fa, "refresh_base", lambda _base: None)
    assert _calls(recorded, lambda: fa.covers(BASE, HEAD, "main")) == [
        (["pkit", "friction", "since", BASE, "--head", HEAD, "--base", "main", "--json"], bounded)
    ]
    assert _calls(recorded, lambda: fa.answers_folder(tmp_path)) == [
        (["pkit", "friction", "check", "--all", "--json"], {**bounded, "cwd": tmp_path})
    ]
    records = lib["accepted_records"]
    monkeypatch.setattr(records.friction_answers, "refresh_base", lambda _base: None)
    assert _calls(recorded, lambda: records.derive(HEAD, "main")) == [
        (["pkit", "decisions", "check-diff", "--json", "--base", "main", "--head", HEAD], bounded)
    ]


def test_the_writers_give_pkit_the_argument_lists_they_gave(
    lib: dict[str, ModuleType], recorded: Recorder
) -> None:
    move = [
        "pkit",
        "process",
        "move",
        "project-management:issue-lifecycle",
        "--to",
        "in-progress",
        "--from",
        "todo",
        "--subject",
        "7",
    ]
    journal = lib["move_journal"].journal_move
    assert _calls(recorded, lambda: journal(7, "todo", "in-progress", None)) == [(move, READ)]
    assert _calls(recorded, lambda: journal(7, "todo", "in-progress", "me", "why")) == [
        ([*move, "--actor", "me", "--reason", "why"], READ)
    ]


def test_every_backbone_is_routed_where_a_module_still_reaches_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A copy of `_lib/backbone.py` that `sys.modules` no longer lists, since the loader
    took it out, but that a module imported earlier still reaches, through its runners'
    defaults, is routed too: otherwise that module starts a real `pkit` (#2322)."""
    (fa,) = load("project-management", "friction_answers")
    copy = fa.default_branch.backbone
    assert all(module is not copy for module in sys.modules.values())
    monkeypatch.setitem(sys.modules, "pm_friction_answers_reached", fa)
    recorder = Recorder()
    route_every_backbone(monkeypatch, recorder)
    with pytest.raises(fa.default_branch.Unanswered):
        fa.default_branch.check_base("main")
    assert recorder.calls and recorder.calls[0][0][:4] == ["pkit", "repository", "base", "--json"]


def test_a_route_answers_every_call_in_this_process(
    lib: dict[str, ModuleType], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The route reaches the readers' calls, their bound and their routing off taken, and
    refuses an environment that adds more than routing off."""
    answered: list[list[str]] = []

    def pkit(argv: Any, **options: Any) -> subprocess.CompletedProcess[str]:
        answered.append(list(argv))
        assert set(options) <= {"cwd", "capture_output", "text", "check"}
        return subprocess.CompletedProcess(list(argv), 2, "", "")

    fa = lib["friction_answers"]
    route_pkit(monkeypatch, fa.backbone, pkit)
    assert isinstance(fa._discovery_at(BASE), str)
    assert isinstance(fa._run_check(None, "main", cwd=None), fa._NoDocument)
    assert answered == [
        ["pkit", "friction", "artefacts", "--json", "--at", BASE],
        ["pkit", "friction", "check", "--json", "--base", "main"],
    ]
    with pytest.raises(TypeError, match="routing off"):
        fa._run_check(BASE, "main", cwd=None, own_head=HEAD)
