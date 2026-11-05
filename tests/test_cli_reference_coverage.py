"""The command reference and the backbone's commands name the same list (#2029).

The commands are read from the backbone's Click tree in
``src/project_kit/cli.py``, walking each group's ``commands`` and running
nothing. ``commands`` holds what the backbone defines, so no capability's
command is read: those are documented in their capabilities' READMEs.

The reference, ``.pkit/cli/README.md``, is read by its sections. A command's
sections are each heading that opens with it in code, up to the next heading of
the same or a higher level, and each row of the Surface table whose first cell
names it. A command is named by its whole path, ``friction check``, never by its
last word alone. An option counts only when its section names it in code, a code
span or a fenced block, so an option named under another command does not count.
The root's own options are named under "Standard flags".

Both ways are checked:

- every command that runs, or takes options, has a section, and every option it
  takes is named in one of its sections
- every command a heading or a Surface row names exists, and so does every
  option it names for that command, in its signature or in a list item of its
  heading's section that opens with the option
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import click

from project_kit.cli import main

REFERENCE = Path(__file__).resolve().parents[1] / ".pkit" / "cli" / "README.md"

# The heading of the table whose rows name commands.
SURFACE = "Surface"
# The heading under which the root's own options are named.
ROOT_OPTIONS = "Standard flags"
# What a command with no section is told.
NO_SECTION = "has no section: no heading opens with it, and no Surface row names it"

_HEADING = re.compile(r"(#{1,6}) +(.*?)\s*\Z")
_FENCE = re.compile(r"\s*```")
_SPAN = re.compile(r"`([^`\n]+)`")
_WORD = re.compile(r"[a-z][a-z0-9-]*\Z")
_LONG_OPTION = re.compile(r"(?<![\w-])--[a-z0-9][a-z0-9-]*")
_OPTION_ITEM = re.compile(r"\s*[-*] +\*\*`(--[a-z0-9][a-z0-9-]*)")
_CELL_BORDER = re.compile(r"(?<!\\)\|")


# --- The backbone's commands ---------------------------------------------


def walk(root: click.Group) -> Iterator[tuple[tuple[str, ...], click.Command]]:
    """Each command under ``root``, the root first, with its path.

    It reads ``commands``, never ``list_commands``, which adds the commands of
    the capabilities installed where the test runs.
    """

    def visit(
        command: click.Command, path: tuple[str, ...]
    ) -> Iterator[tuple[tuple[str, ...], click.Command]]:
        yield path, command
        if isinstance(command, click.Group):
            for name, sub in sorted(command.commands.items()):
                if not sub.hidden:
                    yield from visit(sub, (*path, name))

    yield from visit(root, ())


def option_names(command: click.Command) -> list[str]:
    """Every name a person can type for one of the command's options.

    Click's own ``--help`` is no parameter of the command, so it is not here.
    """
    return [
        name
        for param in command.params
        if isinstance(param, click.Option) and not param.hidden
        for name in (*param.opts, *param.secondary_opts)
    ]


def runs_or_takes_options(command: click.Command) -> bool:
    """Whether the command needs a section of its own.

    A group that only hands over to its subcommands is named through them.
    """
    if isinstance(command, click.Group):
        return command.invoke_without_command or bool(option_names(command))
    return True


# --- The reference's sections --------------------------------------------


@dataclass
class Section:
    """A place in the reference that names commands.

    A heading that opens in code, with the text up to the next heading of its
    level or a higher one, or one row of the Surface table.
    """

    line: int
    names: list[str]
    code: str
    option_items: list[str] = field(default_factory=lambda: [])
    is_heading: bool = False


@dataclass
class Reference:
    sections: list[Section]
    root_options: str


def _front_matter_lines(lines: list[str]) -> int:
    if lines[:1] != ["---"]:
        return 0
    for index, line in enumerate(lines[1:], start=1):
        if line == "---":
            return index + 1
    return 0


def _code(lines: list[str]) -> str:
    """The code of a stretch of the reference: its code spans and fenced lines."""
    parts: list[str] = []
    fenced = False
    for line in lines:
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            parts.append(line)
        else:
            parts.extend(_SPAN.findall(line))
    return "\n".join(parts)


def _option_items(lines: list[str]) -> list[str]:
    """The options the list items of a stretch open with, outside fences."""
    items: list[str] = []
    fenced = False
    for line in lines:
        if _FENCE.match(line):
            fenced = not fenced
            continue
        match = None if fenced else _OPTION_ITEM.match(line)
        if match:
            items.append(match[1])
    return items


def read_reference(text: str) -> Reference:
    lines = text.splitlines()
    start = _front_matter_lines(lines)
    headings: list[tuple[int, int, str]] = []
    fenced = False
    for index in range(start, len(lines)):
        line = lines[index]
        if _FENCE.match(line):
            fenced = not fenced
            continue
        match = None if fenced else _HEADING.match(line)
        if match:
            headings.append((index, len(match[1]), match[2]))

    sections: list[Section] = []
    root_options = ""
    for position, (index, level, title) in enumerate(headings):
        end = next(
            (later for later, depth, _ in headings[position + 1 :] if depth <= level), len(lines)
        )
        body = lines[index:end]
        if title == ROOT_OPTIONS:
            root_options = _code(body)
        if title.startswith("`"):
            sections.append(
                Section(
                    line=index + 1,
                    names=_SPAN.findall(title),
                    code=_code(body),
                    option_items=_option_items(body[1:]),
                    is_heading=True,
                )
            )
        if title == SURFACE:
            for offset, row in enumerate(body):
                if not row.startswith("|"):
                    continue
                cells = _CELL_BORDER.split(row)
                names = _SPAN.findall(cells[1]) if len(cells) > 1 else []
                if names:
                    sections.append(
                        Section(line=index + offset + 1, names=names, code=_code([row]))
                    )
    return Reference(sections=sections, root_options=root_options)


@dataclass
class Naming:
    """What one code span names: a command's path, and the rest of the span."""

    path: tuple[str, ...]
    command: click.Command | None
    rest: str


def named(span: str, root: click.Group) -> Naming | None:
    """The command a code span names, by the words it opens with.

    The words are followed down the tree while they reach a group. A word after
    a group that is none of its subcommands is no command. Words after a
    command that is no group are its arguments. A span that opens with no word,
    such as ``--json`` or ``refs/``, names no command.
    """
    tokens = span.split()
    if tokens[:1] == ["pkit"]:
        tokens = tokens[1:]
    command: click.Command = root
    path: tuple[str, ...] = ()
    taken = 0
    for token in tokens:
        if not _WORD.match(token) or not isinstance(command, click.Group):
            break
        path = (*path, token)
        taken += 1
        sub = command.commands.get(token)
        if sub is None:
            return Naming(path, None, " ".join(tokens[taken:]))
        command = sub
    if not path:
        return None
    return Naming(path, command, " ".join(tokens[taken:]))


def _says(code: str, option: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(option)}(?![\w-])", code) is not None


def _command(path: tuple[str, ...]) -> str:
    return " ".join(path)


# --- The two checks --------------------------------------------------------


def missing_from_reference(root: click.Group, text: str) -> list[str]:
    """Each command or option of ``root`` its section of the reference does not name."""
    reference = read_reference(text)
    found: dict[tuple[str, ...], list[Section]] = {}
    for section in reference.sections:
        for span in section.names:
            naming = named(span, root)
            if naming and naming.command is not None:
                found.setdefault(naming.path, []).append(section)

    problems: list[str] = []
    for path, command in walk(root):
        if not path:
            problems.extend(
                f'the root\'s option `{option}` is not named under "{ROOT_OPTIONS}"'
                for option in option_names(command)
                if not _says(reference.root_options, option)
            )
            continue
        if not runs_or_takes_options(command):
            continue
        sections = found.get(path)
        if not sections:
            problems.append(f"`{_command(path)}` {NO_SECTION}")
            continue
        problems.extend(
            f"`{_command(path)}`: its option `{option}` is not named in its section"
            for option in option_names(command)
            if not any(_says(section.code, option) for section in sections)
        )
    return problems


def named_but_absent(root: click.Group, text: str) -> list[str]:
    """Each command or option the reference names that ``root`` does not define."""
    problems: list[str] = []
    for section in read_reference(text).sections:
        commands: list[tuple[tuple[str, ...], click.Command]] = []
        for span in section.names:
            naming = named(span, root)
            if naming is None:
                continue
            if naming.command is None:
                problems.append(f"line {section.line}: `{_command(naming.path)}` is no command")
                continue
            commands.append((naming.path, naming.command))
            names = option_names(naming.command)
            problems.extend(
                f"line {section.line}: `{_command(naming.path)}` has no option `{option}`"
                for option in _LONG_OPTION.findall(naming.rest)
                if option not in names
            )
        for option in section.option_items:
            if commands and not any(option in option_names(command) for _, command in commands):
                listed = ", ".join(f"`{_command(path)}`" for path, _ in commands)
                problems.append(
                    f"line {section.line}: no command of {listed} has the option `{option}`"
                    " a list item names"
                )
    return problems


# --- The reference against the backbone ------------------------------------


def test_every_backbone_command_and_option_is_named_in_its_section() -> None:
    problems = missing_from_reference(main, REFERENCE.read_text(encoding="utf-8"))
    assert not problems, "the command reference leaves out:\n" + "\n".join(problems)


def test_every_command_and_option_the_reference_names_exists() -> None:
    problems = named_but_absent(main, REFERENCE.read_text(encoding="utf-8"))
    assert not problems, (
        "the command reference names what the backbone does not define:\n" + "\n".join(problems)
    )


# --- How the check reads: a small tree and reference -----------------------


@click.group()
@click.option("--color")
def toy() -> None:
    """A root with an option of its own."""


@toy.group()
def things() -> None:
    """A group that only hands over to its subcommands."""


@things.command("make")
@click.argument("name")
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
def make(name: str, dry_run: bool, force: bool) -> None:
    """Make a thing."""


@things.command("drop")
@click.option("--yes", is_flag=True)
def drop(yes: bool) -> None:
    """Drop a thing."""


@toy.group("refs", invoke_without_command=True)
def refs() -> None:
    """A group that runs on its own."""


@refs.command("show")
def refs_show() -> None:
    """Show a reference."""


@toy.command("hidden", hidden=True)
def hidden() -> None:
    """A command the backbone hides."""


_COMPLETE = """\
---
reader: user
---

# CLI

## Surface

| Command | Operation |
|---|---|
| `things make <name> [--dry-run]` | make a thing; `--force` makes it again |
| `things drop [--yes]` | drop a thing |
| `refs` / `refs show` | list the references, or show one |

## Standard flags

- **`--color`** colours the output.
"""


def _without(text: str, old: str, new: str) -> str:
    assert old in text
    return text.replace(old, new)


def test_a_complete_reference_passes_both_ways() -> None:
    assert missing_from_reference(toy, _COMPLETE) == []
    assert named_but_absent(toy, _COMPLETE) == []


def test_a_command_with_no_section_is_named() -> None:
    text = _without(_COMPLETE, "| `things drop [--yes]` | drop a thing |\n", "")
    assert missing_from_reference(toy, text) == [f"`things drop` {NO_SECTION}"]


def test_an_option_named_under_another_command_does_not_count() -> None:
    text = _without(
        _COMPLETE, "`things drop [--yes]` | drop a thing", "`things drop` | drop a thing"
    )
    text += "\n## Making\n\n### `things make <name>`\n\nRun `things make --yes` to confirm.\n"
    assert missing_from_reference(toy, text) == [
        "`things drop`: its option `--yes` is not named in its section"
    ]


def test_an_option_named_in_prose_alone_does_not_count() -> None:
    text = _without(_COMPLETE, "`--force` makes it again", "--force makes it again")
    assert missing_from_reference(toy, text) == [
        "`things make`: its option `--force` is not named in its section"
    ]


def test_a_longer_option_does_not_name_a_shorter_one() -> None:
    text = _without(_COMPLETE, "[--dry-run]", "[--dry-run-all]")
    assert (
        "`things make`: its option `--dry-run` is not named in its section"
        in missing_from_reference(toy, text)
    )


def test_a_heading_section_ends_at_the_next_heading_of_its_level() -> None:
    text = _without(
        _COMPLETE,
        "| `things make <name> [--dry-run]` | make a thing; `--force` makes it again |\n",
        "",
    )
    text += "\n### `things make <name>`\n\nTakes `--dry-run`.\n"
    text += "\n### Other\n\n`--force` is named here.\n"
    assert missing_from_reference(toy, text) == [
        "`things make`: its option `--force` is not named in its section"
    ]
    text = text.replace("### Other", "#### Other")
    assert missing_from_reference(toy, text) == []


def test_an_option_in_a_fenced_example_counts_and_a_fenced_heading_is_none() -> None:
    text = _without(_COMPLETE, "`--force` makes it again", "see below")
    text += (
        "\n### `things make <name>`\n\n```\n# things make again\npkit things make x --force\n```\n"
    )
    assert missing_from_reference(toy, text) == []


def test_a_path_such_as_refs_folder_names_no_group() -> None:
    text = _without(_COMPLETE, "| `refs` / `refs show` | list the references, or show one |\n", "")
    text += "\n### `refs/` holds the references\n\n`refs show` is mentioned here.\n"
    assert missing_from_reference(toy, text) == [
        f"`refs` {NO_SECTION}",
        f"`refs show` {NO_SECTION}",
    ]
    assert named_but_absent(toy, text) == []


def test_a_group_that_only_hands_over_and_a_hidden_command_need_no_section() -> None:
    assert not runs_or_takes_options(things)
    assert runs_or_takes_options(refs)
    assert "hidden" not in {" ".join(path) for path, _ in walk(toy)}


def test_the_roots_options_count_only_under_standard_flags() -> None:
    text = _without(
        _COMPLETE, "- **`--color`** colours the output.", "Colours follow the terminal."
    )
    text += "\n## Elsewhere\n\n`--color` is named here.\n"
    assert missing_from_reference(toy, text) == [
        'the root\'s option `--color` is not named under "Standard flags"'
    ]


def test_a_command_the_reference_names_must_exist() -> None:
    text = _without(_COMPLETE, "`refs` / `refs show`", "`refs` / `refs list` / `show`")
    assert named_but_absent(toy, text) == [
        "line 13: `refs list` is no command",
        "line 13: `show` is no command",
    ]


def test_a_word_after_a_command_is_its_argument() -> None:
    naming = named("things make thing --force", toy)
    assert naming is not None
    assert naming.path == ("things", "make")
    assert naming.rest == "thing --force"


def test_an_option_the_reference_names_for_a_command_must_exist() -> None:
    text = _without(_COMPLETE, "`things drop [--yes]`", "`things drop [--yes] [--all]`")
    text += "\n### `things make <name>`\n\n"
    text += "- **`--again`** makes it again.\n- **`--force`** forces it.\n"
    assert named_but_absent(toy, text) == [
        "line 12: `things drop` has no option `--all`",
        "line 19: no command of `things make` has the option `--again` a list item names",
    ]
