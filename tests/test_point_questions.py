"""The questions data points declare (COR-061, #1766): a data point's definer
names a command of its own that asks the person and records the answer, and the
backbone runs it at the end of a capability's install, register and upgrade and
of a transition of the backbone, only where a person can answer. With nobody to
answer it runs none and prints the line that asks later. Sync never asks.

The fixture point is synthetic: `defs` accepts `pkit::tracking:grants` and names
its `ask` command as the point's question. The command appends the point's
address to `asked.log` at the project root, so a test reads which questions ran,
and from where.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result
from ruamel.yaml import YAML

from project_kit import cli as cli_mod
from project_kit import connections as cx
from project_kit import install, point_questions, sync, upgrade
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    read_kit_version,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

ROLE = "pkit::tracking"
GRANTS = f"{ROLE}:grants"
OTHER = f"{ROLE}:other"
LOG = "asked.log"

# The version an installed fixture records: the real source kit's.
_PROJECTS_VERSION = read_kit_version(install.find_source_kit())

# The question's command: it records where it ran and which point asked.
_ASK_SCRIPT = """#!/bin/sh
printf '%s %s\\n' "$1" "$(pwd -P)" >> asked.log
"""


def _write_capability(
    cap_dir: Path,
    name: str,
    *,
    version: str = "0.1.0",
    role: str = ROLE,
    defines: dict[str, dict[str, Any]] | None = None,
    contributes_to: tuple[str, ...] = (),
) -> Path:
    """A capability subtree at `cap_dir`: an `ask` command whose script logs the
    point it is passed, `defines` points of its own under `pkit::tracking` (address
    → extra keys, `question` among them), and a value contributed to each point in
    `contributes_to`. `defines` sits under `role`, which it provides."""
    (cap_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (cap_dir / "schemas").mkdir(exist_ok=True)
    (cap_dir / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    (cap_dir / "schemas" / "grants.schema.json").write_text(
        json.dumps({"type": "array", "items": {"type": "string"}}), encoding="utf-8"
    )
    script = cap_dir / "scripts" / "ask.sh"
    script.write_text(_ASK_SCRIPT, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    package: dict[str, Any] = {
        "schema_version": 2,
        "component": {"kind": "capability", "name": name, "version": version},
        "description": f"Synthetic {name}.",
        "requires_backbone": ">=0.0.0",
        "commands": {"ask": {"script": "scripts/ask.sh", "help": "Ask about the grants."}},
    }
    connections: dict[str, Any] = {}
    if defines:
        connections["roles"] = [role]
        connections["extension-points"] = {
            "accepts": {
                address: {
                    "schema_version": 1,
                    "schema": "grants.schema.json",
                    "description": "What the project grants.",
                    "combination": "union",
                    **extra,
                }
                for address, extra in defines.items()
            }
        }
    if contributes_to:
        connections["extensions"] = {
            "contributes": [
                {"point": address, "schema_version": 1, "value": [name]}
                for address in contributes_to
            ]
        }
    if connections:
        package["connections"] = connections
    with (cap_dir / "package.yaml").open("w", encoding="utf-8") as handle:
        YAML().dump(package, handle)
    return cap_dir


def _register(repo: AdopterRepo, name: str) -> None:
    """Register `.pkit/capabilities/<name>/` as incubated: its package file is its
    version of record, and sync leaves it alone."""
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name=name,
            manifest=f".pkit/capabilities/{name}/project/manifest.yaml",
            origin="incubated-in-repo",
        )
    )
    write_backbone_manifest(repo.root, backbone)


def _stage(repo: AdopterRepo, name: str, **kwargs: Any) -> None:
    _write_capability(repo.pkit / "capabilities" / name, name, **kwargs)
    _register(repo, name)


def _asked(root: Path) -> list[str]:
    """The points whose question ran, in order; each ran from `root`."""
    log = root / LOG
    if not log.is_file():
        return []
    lines = log.read_text(encoding="utf-8").splitlines()
    for line in lines:
        assert line.split(" ", 1)[1] == str(root.resolve())
    return [line.split(" ", 1)[0] for line in lines]


# A point's extra keys that declare its question: the definer's `ask` command.
QUESTION = {"question": "ask"}


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


@pytest.fixture
def at_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """A person can answer: the terminal test answers yes."""
    monkeypatch.setattr(point_questions, "at_a_terminal", lambda: True)


@pytest.fixture
def logs_the_address(monkeypatch: pytest.MonkeyPatch) -> None:
    """The question's command is passed its point's address, so the log names it.
    The backbone passes no parameter; this stands in for the definer reading it."""

    def run(question: point_questions.Question, target_root: Path) -> int:
        import subprocess

        assert question.script is not None
        return subprocess.run(
            [str(question.script), question.address], cwd=str(target_root), check=False
        ).returncode

    monkeypatch.setattr(point_questions, "_run", run)


# --- which questions an operation runs -----------------------------------------


def test_an_install_runs_the_questions_of_the_points_the_capability_defines(
    repo: AdopterRepo,
) -> None:
    _stage(repo, "defs", defines={GRANTS: QUESTION, OTHER: {}})
    wiring = cx.resolve_wiring(repo.root)

    questions = point_questions.questions_for(wiring, capability="defs")

    assert [(q.address, q.definer, q.command) for q in questions] == [(GRANTS, "defs", "ask")]
    assert questions[0].line == "pkit defs ask"
    assert questions[0].script == repo.pkit / "capabilities" / "defs" / "scripts" / "ask.sh"


def test_an_install_runs_the_questions_of_the_points_its_contributions_reach(
    repo: AdopterRepo,
) -> None:
    _stage(repo, "defs", defines={GRANTS: QUESTION})
    _stage(repo, "giver", contributes_to=(GRANTS,))
    _stage(repo, "bystander")
    wiring = cx.resolve_wiring(repo.root)

    assert [q.address for q in point_questions.questions_for(wiring, capability="giver")] == [
        GRANTS
    ]
    assert point_questions.questions_for(wiring, capability="bystander") == ()


def test_a_transition_of_the_backbone_runs_every_question(repo: AdopterRepo) -> None:
    _stage(repo, "defs", defines={GRANTS: QUESTION})
    _stage(repo, "more", role="pkit::more", defines={"pkit::more:asks": QUESTION})

    questions = point_questions.questions_for(cx.resolve_wiring(repo.root))

    assert [q.address for q in questions] == ["pkit::more:asks", GRANTS]  # by address


def test_a_point_no_active_provider_defines_asks_nothing(repo: AdopterRepo) -> None:
    """Two providers of one role and no selection: neither defines its points
    (COR-053 point 1), so neither question runs."""
    _stage(repo, "defs", defines={GRANTS: QUESTION})
    _stage(repo, "rival", defines={GRANTS: QUESTION})

    assert point_questions.questions_for(cx.resolve_wiring(repo.root)) == ()


def test_a_question_naming_no_script_is_kept_with_no_script(repo: AdopterRepo) -> None:
    _stage(repo, "defs", defines={GRANTS: {"question": "missing"}})

    (question,) = point_questions.questions_for(cx.resolve_wiring(repo.root))

    assert question.script is None


# --- how the questions run -----------------------------------------------------


def _questions(*addresses: str) -> list[point_questions.Question]:
    return [point_questions.Question(a, "defs", "ask", Path("/bin/true")) for a in addresses]


def test_a_preview_names_each_question_and_runs_none(capsys: pytest.CaptureFixture[str]) -> None:
    ran: list[str] = []

    point_questions.ask(
        Path("."),
        _questions(GRANTS),
        dry_run=True,
        interactive=True,
        run=lambda q, _root: ran.append(q.address) or 0,
    )

    assert ran == []
    assert f"would ask    {GRANTS}: pkit defs ask" in capsys.readouterr().out


def test_with_nobody_to_answer_none_runs_and_each_line_is_printed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ran: list[str] = []

    point_questions.ask(
        Path("."),
        _questions(GRANTS, OTHER),
        interactive=False,
        run=lambda q, _root: ran.append(q.address) or 0,
    )

    out = capsys.readouterr().out
    assert ran == []
    assert "nothing was recorded" in out
    assert "not both terminals" in out
    assert f"not asked    {GRANTS}: pkit defs ask" in out
    assert f"not asked    {OTHER}: pkit defs ask" in out


def test_no_question_prints_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    point_questions.ask(Path("."), [], interactive=False)
    point_questions.ask(Path("."), [], dry_run=True)

    assert capsys.readouterr().out == ""


def test_a_failing_question_is_reported_and_the_next_still_runs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ran: list[str] = []

    def run(question: point_questions.Question, _root: Path) -> int:
        ran.append(question.address)
        return 3 if question.address == GRANTS else 0

    point_questions.ask(Path("."), _questions(GRANTS, OTHER), interactive=True, run=run)

    out = capsys.readouterr().out
    assert ran == [GRANTS, OTHER]
    assert f"warning      {GRANTS}: pkit defs ask exited 3. Run it again at a terminal" in out


def test_a_question_ended_by_a_signal_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    point_questions.ask(Path("."), _questions(GRANTS), interactive=True, run=lambda _q, _r: -15)

    assert "was ended by signal 15" in capsys.readouterr().out


def test_a_question_with_no_script_is_reported_and_not_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ran: list[str] = []
    question = point_questions.Question(GRANTS, "defs", "missing", None)

    point_questions.ask(
        Path("."), [question], interactive=True, run=lambda q, _r: ran.append(q.address) or 0
    )

    assert ran == []
    assert "names no script that exists, so it was not asked" in capsys.readouterr().out


def test_an_interrupt_stops_the_questions_and_prints_each_left(
    capsys: pytest.CaptureFixture[str],
) -> None:
    third = f"{ROLE}:third"
    ran: list[str] = []

    def run(question: point_questions.Question, _root: Path) -> int:
        ran.append(question.address)
        if question.address == OTHER:
            raise KeyboardInterrupt
        return 0

    point_questions.ask(Path("."), _questions(GRANTS, OTHER, third), interactive=True, run=run)

    out = capsys.readouterr().out
    assert ran == [GRANTS, OTHER]
    assert "stopped" in out
    assert f"not asked    {OTHER}: pkit defs ask" in out
    assert f"not asked    {third}: pkit defs ask" in out
    assert f"not asked    {GRANTS}" not in out


def test_the_command_runs_from_the_project_root_with_no_parameter(repo: AdopterRepo) -> None:
    _stage(repo, "defs", defines={GRANTS: QUESTION})
    questions = point_questions.questions_for(cx.resolve_wiring(repo.root))

    point_questions.ask(repo.root, questions, interactive=True)

    log = (repo.root / LOG).read_text(encoding="utf-8")
    assert log == f" {repo.root.resolve()}\n"


def test_the_terminal_test_needs_both_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Stream:
        def __init__(self, tty: bool) -> None:
            self._tty = tty

        def isatty(self) -> bool:
            return self._tty

    monkeypatch.setattr("sys.stdin", _Stream(True))
    monkeypatch.setattr("sys.stdout", _Stream(False))
    assert point_questions.at_a_terminal() is False
    monkeypatch.setattr("sys.stdout", _Stream(True))
    assert point_questions.at_a_terminal() is True
    monkeypatch.setattr("sys.stdin", None)
    assert point_questions.at_a_terminal() is False


# --- the operations that run them ----------------------------------------------


@pytest.fixture
def kit_source(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch kit source the CLI installs and upgrades from, at the version the
    project records, so sync's guard lets `install` and `upgrade` run."""
    source = tmp_path_factory.mktemp("kit-source")
    (source / "capabilities").mkdir(parents=True)
    (source / "decisions").mkdir()
    (source / "VERSION").write_text(f"{_PROJECTS_VERSION}\n", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: source)
    return source


def _invoke(*args: str) -> Result:
    result = CliRunner().invoke(main, list(args), catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return result


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_install_asks_at_a_terminal(repo: AdopterRepo, kit_source: Path) -> None:
    _write_capability(kit_source / "capabilities" / "defs", "defs", defines={GRANTS: QUESTION})

    _invoke("capabilities", "install", "defs")

    assert _asked(repo.root) == [GRANTS]


@pytest.mark.usefixtures("logs_the_address")
def test_install_without_a_terminal_asks_nothing_and_prints_the_line(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _write_capability(kit_source / "capabilities" / "defs", "defs", defines={GRANTS: QUESTION})

    result = _invoke("capabilities", "install", "defs")

    assert _asked(repo.root) == []
    assert f"not asked    {GRANTS}: pkit defs ask" in result.output


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_install_dry_run_names_the_questions_of_the_version_it_would_bring(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _write_capability(kit_source / "capabilities" / "defs", "defs", defines={GRANTS: QUESTION})

    result = _invoke("capabilities", "install", "defs", "--dry-run")

    assert _asked(repo.root) == []
    assert f"would ask    {GRANTS}: pkit defs ask" in result.output


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_installing_a_contributor_asks_the_definers_question(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _stage(repo, "defs", defines={GRANTS: QUESTION})
    _write_capability(kit_source / "capabilities" / "giver", "giver", contributes_to=(GRANTS,))

    result = _invoke("capabilities", "install", "giver")

    assert _asked(repo.root) == [GRANTS]
    assert f"asking       {GRANTS}: pkit defs ask" in result.output


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_installing_an_unrelated_capability_asks_nothing(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _stage(repo, "defs", defines={GRANTS: QUESTION})
    _write_capability(kit_source / "capabilities" / "bystander", "bystander")

    result = _invoke("capabilities", "install", "bystander")

    assert _asked(repo.root) == []
    assert "question" not in result.output


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_register_asks_at_a_terminal(repo: AdopterRepo, kit_source: Path) -> None:
    _write_capability(repo.pkit / "capabilities" / "defs", "defs", defines={GRANTS: QUESTION})

    _invoke("capabilities", "register", "defs")

    assert _asked(repo.root) == [GRANTS]


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_a_capability_upgrade_asks_at_a_terminal(repo: AdopterRepo, kit_source: Path) -> None:
    source = kit_source / "capabilities" / "defs"
    _write_capability(source, "defs", defines={GRANTS: {}})
    _invoke("capabilities", "install", "defs")
    assert _asked(repo.root) == []
    _write_capability(source, "defs", version="0.2.0", defines={GRANTS: QUESTION})

    _invoke("capabilities", "upgrade", "defs")

    assert _asked(repo.root) == [GRANTS]


@pytest.mark.usefixtures("logs_the_address")
def test_a_capability_upgrade_without_a_terminal_prints_the_line(
    repo: AdopterRepo, kit_source: Path
) -> None:
    source = kit_source / "capabilities" / "defs"
    _write_capability(source, "defs", defines={GRANTS: QUESTION})
    _invoke("capabilities", "install", "defs")
    _write_capability(source, "defs", version="0.2.0", defines={GRANTS: QUESTION})

    result = _invoke("capabilities", "upgrade", "defs")

    assert _asked(repo.root) == []
    assert f"not asked    {GRANTS}: pkit defs ask" in result.output


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_a_capability_upgrade_dry_run_names_the_new_versions_questions(
    repo: AdopterRepo, kit_source: Path
) -> None:
    source = kit_source / "capabilities" / "defs"
    _write_capability(source, "defs", defines={GRANTS: {}})
    _invoke("capabilities", "install", "defs")
    _write_capability(source, "defs", version="0.2.0", defines={GRANTS: QUESTION})

    result = _invoke("capabilities", "upgrade", "defs", "--dry-run")

    assert _asked(repo.root) == []
    assert f"would ask    {GRANTS}: pkit defs ask" in result.output


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_an_incubated_capabilitys_upgrade_asks_at_a_terminal(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _stage(repo, "defs", defines={GRANTS: QUESTION})

    _invoke("capabilities", "upgrade", "defs")

    assert _asked(repo.root) == [GRANTS]


@pytest.fixture
def transition(repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project with a capability whose point declares a question, recorded at
    an older backbone, so `pkit upgrade` runs a transition. No release is looked
    up, so the tool step goes on offline."""
    _stage(repo, "defs", defines={GRANTS: QUESTION})
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    backbone.backbone_version = "0.1.0"
    write_backbone_manifest(repo.root, backbone)
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: None)
    return repo.root


@pytest.mark.usefixtures("at_a_terminal")
def test_a_transition_of_the_backbone_asks_once_it_is_complete(
    transition: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completed: list[str | None] = []

    def run(question: point_questions.Question, target_root: Path) -> int:
        manifest = read_backbone_manifest(target_root)
        completed.append(manifest.completed_version if manifest is not None else None)
        return 0

    monkeypatch.setattr(point_questions, "_run", run)

    upgrade.run_upgrade(transition, pin=False)

    assert completed == [_PROJECTS_VERSION]


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_a_transition_of_the_backbone_runs_the_question(transition: Path) -> None:
    upgrade.run_upgrade(transition, pin=False)

    assert _asked(transition) == [GRANTS]


@pytest.mark.usefixtures("logs_the_address")
def test_a_transition_without_a_terminal_prints_the_line(
    transition: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    upgrade.run_upgrade(transition, pin=False)

    assert _asked(transition) == []
    assert f"not asked    {GRANTS}: pkit defs ask" in capsys.readouterr().out


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_a_transition_dry_run_names_the_question(
    transition: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    upgrade.run_upgrade(transition, dry_run=True, pin=False)

    assert _asked(transition) == []
    assert f"would ask    {GRANTS}: pkit defs ask" in capsys.readouterr().out


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_a_project_already_current_asks_nothing(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stage(repo, "defs", defines={GRANTS: QUESTION})
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: None)

    upgrade.run_upgrade(repo.root, pin=False)

    assert "Already at backbone" in capsys.readouterr().out
    assert _asked(repo.root) == []


@pytest.mark.usefixtures("at_a_terminal", "logs_the_address")
def test_sync_never_asks(repo: AdopterRepo, capsys: pytest.CaptureFixture[str]) -> None:
    _stage(repo, "defs", defines={GRANTS: QUESTION})

    sync.run_sync(repo.root)

    assert _asked(repo.root) == []
    assert "question" not in capsys.readouterr().out


def test_show_names_a_points_question(repo: AdopterRepo) -> None:
    """What an install would ask is readable before it runs (COR-053 point 8)."""
    _stage(repo, "defs", defines={GRANTS: QUESTION})

    result = _invoke("capabilities", "show", "defs")
    document = json.loads(_invoke("capabilities", "show", "defs", "--json").output)

    assert f"{GRANTS} (data v1, union, question: ask)" in result.output
    assert [p["question"] for p in document["accepts"]] == ["ask"]


def _script_question(tmp_path: Path, body: str) -> point_questions.Question:
    script = tmp_path / "ask.sh"
    script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return point_questions.Question(GRANTS, "defs", "ask", script)


@pytest.mark.parametrize(
    "body",
    ["kill -INT $$", "exit 130", "kill -INT $PPID"],
    ids=["ended-by-an-interrupt", "exits-as-interrupted", "interrupt-while-it-ran"],
)
def test_an_interrupt_during_a_question_stops_the_questions(tmp_path: Path, body: str) -> None:
    """The command is left to handle the interrupt, and the questions stop."""
    with pytest.raises(KeyboardInterrupt):
        point_questions._run(_script_question(tmp_path, body), tmp_path)  # pyright: ignore[reportPrivateUsage] -- the runner under test


def test_an_interrupt_handler_is_put_back_after_a_question(tmp_path: Path) -> None:
    import signal

    before = signal.getsignal(signal.SIGINT)

    assert point_questions._run(_script_question(tmp_path, "exit 0"), tmp_path) == 0  # pyright: ignore[reportPrivateUsage] -- the runner under test
    assert signal.getsignal(signal.SIGINT) is before
