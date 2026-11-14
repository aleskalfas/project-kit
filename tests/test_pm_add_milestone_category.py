"""Tests for add-milestone-category and the library it writes through (#3160).

The library, `_lib/milestone_categories`, holds the checks on a category and the
write into the project's configuration: every byte outside the block kept, and
nothing written where the file would not read back with only the category added.
The command's own tests run `main()` against a staged capability tree.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from ruamel.yaml import YAML

from tests.pm_workstream_fakes import stage_project

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
SCRIPT_PATH = SCRIPTS_DIR / "add-milestone-category.py"


def _load(path: Path, module_name: str) -> ModuleType:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mc() -> ModuleType:
    return _load(SCRIPTS_DIR / "_lib" / "milestone_categories.py", "pm_milestone_categories_test")


@pytest.fixture(scope="module")
def amc() -> ModuleType:
    return _load(SCRIPT_PATH, "pm_add_milestone_category_under_test")


SPRINT = {
    "title_format": "Sprint {n}: {name}",
    "close_trigger_default": "date-based",
    "description": "A two-week planning window.",
}


def _reads(path: Path) -> dict:
    return YAML(typ="safe").load(path.read_text(encoding="utf-8"))


# --- the checks -------------------------------------------------------------------


@pytest.mark.parametrize("title_format", ["Sprint {n}: {name}", "v{n} GA: {name}", "{name} ({n})"])
def test_a_format_with_both_placeholders_passes(mc, title_format) -> None:
    assert mc.title_format_problem(title_format) is None


@pytest.mark.parametrize(
    ("title_format", "said"),
    [
        ("", "empty"),
        ("Sprint {name}", "{n}"),
        ("Sprint {n}", "{name}"),
        ("Sprint {n}:\n{name}", "one line"),
        ("Sprint {n}: {name} {owner}", "other than"),
        ("Sprint {n}: {name} {0}", "other than"),
        ("Sprint {n}: {name} }", "other than"),
    ],
)
def test_a_format_create_milestone_cannot_fill_is_refused(mc, title_format, said) -> None:
    problem = mc.title_format_problem(title_format)
    assert problem is not None and said in problem


def test_a_category_within_the_rules_has_no_problem(mc) -> None:
    assert (
        mc.entry_problems(
            "sprint",
            title_format="Sprint {n}: {name}",
            close_trigger="date-based",
            description="d" * 200,
        )
        == []
    )


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("", {}),
        (" sprint", {}),
        ("two\nlines", {}),
        ("sprint", {"close_trigger": "weekly"}),
        ("sprint", {"description": "d" * 201}),
        ("sprint", {"description": "two\nlines"}),
        ("sprint", {"title_format": "Sprint"}),
    ],
)
def test_each_value_outside_the_rules_is_a_problem(mc, name, kwargs) -> None:
    values = {
        "title_format": "Sprint {n}: {name}",
        "close_trigger": "date-based",
        "description": None,
        **kwargs,
    }
    assert len(mc.entry_problems(name, **values)) == 1


def test_the_declare_line_names_the_category_and_each_trigger(mc) -> None:
    line = mc.declare_line("sprint")
    assert line.startswith("pkit pm add-milestone-category sprint --title-format ")
    assert "--close-trigger <date-based|content-based|either>" in line


# --- the write ----------------------------------------------------------------------

CONFIG = """\
# The project's configuration.
schema_version: 1

# Categories (DEC-016).
milestone_categories:   # declared before filing
  milestone:
    title_format: "Milestone {n}: {name}"
    close_trigger_default: content-based

# Review mode.
review:
  mode: agent
"""


def test_a_category_follows_the_last_one_and_every_other_byte_stays(mc, tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(CONFIG, encoding="utf-8")

    mc.declare(path, "sprint", SPRINT)

    text = path.read_text(encoding="utf-8")
    added = (
        "  sprint:\n"
        '    title_format: "Sprint {n}: {name}"\n'
        '    close_trigger_default: "date-based"\n'
        '    description: "A two-week planning window."\n'
    )
    marker = "    close_trigger_default: content-based\n"
    assert text == CONFIG.replace(marker, marker + added)
    assert _reads(path)["milestone_categories"]["sprint"] == SPRINT


def test_with_no_block_the_block_is_added_at_the_end(mc, tmp_path) -> None:
    path = tmp_path / "config.yaml"
    before = "schema_version: 1\nreview:\n  mode: agent\n"
    path.write_text(before, encoding="utf-8")

    mc.declare(path, "sprint", SPRINT)

    text = path.read_text(encoding="utf-8")
    assert text.startswith(before + "\n# Milestone categories")
    assert "`pkit pm add-milestone-category`" in text
    assert _reads(path) == {
        "schema_version": 1,
        "review": {"mode": "agent"},
        "milestone_categories": {"sprint": SPRINT},
    }


@pytest.mark.parametrize("empty", ["{}", "~", "null", ""])
def test_an_empty_block_takes_its_first_category(mc, tmp_path, empty) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(f"schema_version: 1\nmilestone_categories: {empty}  # none yet\n", "utf-8")

    mc.declare(path, "sprint", SPRINT)

    # The key's comment stays, and the category follows the key's line.
    text = path.read_text(encoding="utf-8")
    assert "\nmilestone_categories:  " in text
    assert "  # none yet\n  sprint:\n" in text
    assert _reads(path)["milestone_categories"] == {"sprint": SPRINT}


def test_the_entries_indent_is_followed(mc, tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "milestone_categories:\n"
        "    milestone:\n"
        "        title_format: 'M{n} {name}'\n"
        "        close_trigger_default: either\n",
        "utf-8",
    )

    mc.declare(path, "sprint", SPRINT)

    assert "\n    sprint:\n        title_format: " in path.read_text(encoding="utf-8")
    assert set(_reads(path)["milestone_categories"]) == {"milestone", "sprint"}


@pytest.mark.parametrize("name", ["true", "2026", "a: b", "#hash", "phase"])
def test_a_name_reads_back_as_itself(mc, tmp_path, name) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("schema_version: 1\n", "utf-8")

    mc.declare(path, name, SPRINT)

    assert list(_reads(path)["milestone_categories"]) == [name]


def test_values_with_quotes_and_unicode_read_back_as_given(mc, tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("schema_version: 1\n", "utf-8")
    value = {
        "title_format": 'Fáze {n} — "{name}" #1',
        "close_trigger_default": "either",
        "description": "It's a 'window': \\ and all.",
    }

    mc.declare(path, "faze", value)

    assert _reads(path)["milestone_categories"]["faze"] == value


def test_a_bom_and_crlf_line_endings_stay(mc, tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_bytes("﻿schema_version: 1\r\nmilestone_categories: {}\r\n".encode())

    mc.declare(path, "sprint", SPRINT)

    raw = path.read_bytes().decode("utf-8")
    assert raw.startswith("﻿schema_version: 1\r\n")
    assert "\n" not in raw.replace("\r\n", "")
    assert YAML(typ="safe").load(raw.lstrip("﻿"))["milestone_categories"] == {"sprint": SPRINT}


@pytest.mark.parametrize(
    ("config", "said"),
    [
        (CONFIG, "already declared"),
        ("milestone_categories:\n  - sprint\n", "not a mapping"),
        ("milestone_categories: {milestone: {title_format: x}}\n", "by hand"),
        ("schema_version: 1\r\nreview: {}\n", "mixes line endings"),
        ("schema_version: [1\n", "cannot be read"),
    ],
)
def test_a_file_the_category_cannot_be_written_into_is_left_as_it_was(
    mc, tmp_path, config, said
) -> None:
    path = tmp_path / "config.yaml"
    path.write_bytes(config.encode("utf-8"))
    name = "milestone" if said == "already declared" else "sprint"

    with pytest.raises(mc.Refused, match=said):
        mc.declare(path, name, SPRINT)

    assert path.read_bytes() == config.encode("utf-8")


def test_an_absent_file_is_refused(mc, tmp_path) -> None:
    with pytest.raises(mc.Refused, match="does not exist"):
        mc.declare(tmp_path / "config.yaml", "sprint", SPRINT)
    assert not (tmp_path / "config.yaml").exists()


# --- the command ----------------------------------------------------------------------

STAGED_CONFIG = "schema_version: 1\ndefault_branch: main\nworkstreams: []\n"
ARGS = ("sprint", "--title-format", "Sprint {n}: {name}", "--close-trigger", "date-based")


def _stage(tmp_path: Path, config: str = STAGED_CONFIG) -> Path:
    stage_project(tmp_path, "schema_version: 1\nworkstreams: {}\n")
    path = tmp_path / "project" / "config.yaml"
    path.write_text(config, encoding="utf-8")
    return path


def _run(amc, monkeypatch, cap_root: Path, *argv: str, yes: bool = True) -> int:
    # The invoker's login, without asking GitHub for it.
    monkeypatch.setenv("PM_INVOKER_LOGIN", "me")
    monkeypatch.setattr(
        sys,
        "argv",
        ["add-milestone-category.py", *argv, "--capability-root", str(cap_root)]
        + (["--yes"] if yes else []),
    )
    return amc.main()


class _Stdin:
    """A standard input that is a terminal or, as `echo y | …` gives, a pipe."""

    def __init__(self, terminal: bool) -> None:
        self.terminal = terminal

    def isatty(self) -> bool:
        return self.terminal


def _never_asked(question: str) -> str:
    raise AssertionError(f"asked off a terminal: {question!r}")


def test_the_command_declares_the_category(amc, tmp_path, monkeypatch, capsys) -> None:
    path = _stage(tmp_path)

    rc = _run(amc, monkeypatch, tmp_path, *ARGS, "--description", "A two-week planning window.")

    assert rc == 0
    assert _reads(path)["milestone_categories"] == {"sprint": SPRINT}
    out = capsys.readouterr().out
    assert "[ok] declared milestone category 'sprint'." in out
    assert "pkit pm create-milestone sprint --name" in out


def test_a_category_already_declared_is_refused(amc, tmp_path, monkeypatch, capsys) -> None:
    config = STAGED_CONFIG + (
        "milestone_categories:\n"
        "  sprint:\n"
        "    title_format: 'S{n} {name}'\n"
        "    close_trigger_default: either\n"
    )
    path = _stage(tmp_path, config)

    assert _run(amc, monkeypatch, tmp_path, *ARGS) == 1

    assert path.read_text(encoding="utf-8") == config
    assert "[refused] milestone category 'sprint' is already declared" in capsys.readouterr().err


@pytest.mark.parametrize(
    "extra",
    [
        ["--title-format", "Sprint {n}"],
        ["--description", "d" * 201],
        ["--description", "two\nlines"],
    ],
)
def test_a_value_outside_the_rules_writes_nothing(amc, tmp_path, monkeypatch, extra) -> None:
    path = _stage(tmp_path)

    assert _run(amc, monkeypatch, tmp_path, *ARGS, *extra) == 1

    assert path.read_text(encoding="utf-8") == STAGED_CONFIG


def test_a_dry_run_writes_nothing(amc, tmp_path, monkeypatch, capsys) -> None:
    path = _stage(tmp_path)

    assert _run(amc, monkeypatch, tmp_path, *ARGS, "--dry-run", yes=False) == 0

    assert path.read_text(encoding="utf-8") == STAGED_CONFIG
    assert "[dry-run] nothing written." in capsys.readouterr().out


def test_a_file_it_cannot_write_into_exits_2(amc, tmp_path, monkeypatch, capsys) -> None:
    config = STAGED_CONFIG + "milestone_categories: {milestone: {title_format: x}}\n"
    path = _stage(tmp_path, config)

    assert _run(amc, monkeypatch, tmp_path, *ARGS) == 2

    assert path.read_text(encoding="utf-8") == config
    assert "declare 'sprint' under `milestone_categories` by hand" in capsys.readouterr().err


def test_off_a_terminal_without_yes_nothing_is_declared(amc, tmp_path, monkeypatch, capsys) -> None:
    path = _stage(tmp_path)
    monkeypatch.setattr(sys, "stdin", _Stdin(terminal=False))
    monkeypatch.setattr("builtins.input", _never_asked)

    assert _run(amc, monkeypatch, tmp_path, *ARGS, yes=False) == 1

    assert path.read_text(encoding="utf-8") == STAGED_CONFIG
    err = capsys.readouterr().err
    assert "[refused] Declaring milestone category 'sprint' is the person's to authorise" in err
    assert "pkit pm add-milestone-category sprint" in err and "--yes" in err


@pytest.mark.parametrize(("reply", "declared"), [("y", True), ("n", False)])
def test_at_a_terminal_the_declaration_is_asked(
    amc, tmp_path, monkeypatch, reply, declared
) -> None:
    path = _stage(tmp_path)
    monkeypatch.setattr(sys, "stdin", _Stdin(terminal=True))
    monkeypatch.setattr("builtins.input", lambda q: reply)

    assert _run(amc, monkeypatch, tmp_path, *ARGS, yes=False) == 0

    assert ("sprint" in (_reads(path).get("milestone_categories") or {})) is declared
