"""The project's Milestone categories ([project-management:DEC-016-time-bound-containers]).

A project that files Milestones declares each category it files them in, in the
`milestone_categories:` block of this capability's project configuration, before
the first Milestone of it. The methodology declares none by default. A category
carries the title format its Milestones take, the close trigger each takes unless
it names its own, and an optional line saying what it means (`config.schema.json`,
its `milestone_category`).

- `title_format_problem` says why a title format is one `create-milestone` cannot
  file under, so `add-milestone-category` declares no category nothing can be
  filed in;
- `entry_problems` checks a new category's values against the schema's rules;
- `declare` writes a category into the configuration as text. Every byte outside
  the block is kept, and the file must read back as it was with only the category
  added, or nothing is written;
- `declare_line` is the command that declares one, which `create-milestone`'s
  refusal names.
"""

from __future__ import annotations

import json
import re
import shlex
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

#: The block's key in this capability's project configuration, and the file's
#: place under the capability's root.
CONFIG_KEY = "milestone_categories"
CONFIG_RELATIVE = Path("project") / "config.yaml"

#: The close triggers a category may default to (DEC-016, "Close triggers").
CLOSE_TRIGGERS = ("date-based", "content-based", "either")

#: The schema's bound on a category's description.
DESCRIPTION_MAX_LENGTH = 200

#: The command that declares a category, as a printed line names it.
COMMAND = "pkit pm"
ADD_VERB = "add-milestone-category"

#: A byte-order mark: kept where a file opens with one.
BOM = "﻿"


class Refused(Exception):
    """A category that cannot be written, and why. Nothing was written."""


def title_format_problem(title_format: str) -> str | None:
    """Why `create-milestone` cannot file under `title_format`, or None.

    The format is one line, holds both `{n}` and `{name}`, and no other
    placeholder, since `create-milestone` fills those two alone.
    """
    if not title_format.strip():
        return "the title format is empty."
    if not _single_line(title_format):
        return "the title format must be one line."
    if "{n}" not in title_format or "{name}" not in title_format:
        return (
            f"title format {title_format!r} must contain both {{n}} (number) and "
            "{name} (semantic) placeholders."
        )
    try:
        title_format.format(n=1, name="name")
    except (KeyError, IndexError, ValueError, AttributeError, TypeError):
        return (
            f"title format {title_format!r} holds a placeholder other than {{n}} and "
            "{name}, which create-milestone cannot fill."
        )
    return None


def entry_problems(
    name: str, *, title_format: str, close_trigger: str, description: str | None
) -> list[str]:
    """Each way a new category breaks the rules; empty when none does.

    A name is non-empty, one line, with no space around it. A close trigger is
    one of `CLOSE_TRIGGERS`. A description, where given, is one line of at most
    `DESCRIPTION_MAX_LENGTH` characters.
    """
    problems: list[str] = []
    if not name.strip():
        problems.append("the category's name must not be empty.")
    elif name != name.strip() or not _single_line(name):
        problems.append(f"the category's name {name!r} must be one line, with no space around it.")
    problem = title_format_problem(title_format)
    if problem is not None:
        problems.append(problem)
    if close_trigger not in CLOSE_TRIGGERS:
        problems.append(
            f"the close trigger must be one of {', '.join(CLOSE_TRIGGERS)}; got {close_trigger!r}."
        )
    if description is not None:
        if len(description) > DESCRIPTION_MAX_LENGTH:
            problems.append(
                f"the description is {len(description)} chars; at most "
                f"{DESCRIPTION_MAX_LENGTH} are allowed."
            )
        if not _single_line(description):
            problems.append("the description must be one line.")
    return problems


def entry(title_format: str, close_trigger: str, description: str | None) -> dict[str, str]:
    """A category's value, as the configuration holds it."""
    value = {"title_format": title_format, "close_trigger_default": close_trigger}
    if description:
        value["description"] = description
    return value


def declared(config: Mapping[str, Any]) -> Mapping[str, Any]:
    """The categories the configuration declares; empty where it declares none or
    the block is no mapping."""
    categories = config.get(CONFIG_KEY)
    return categories if isinstance(categories, Mapping) else {}


def declare_line(name: str = "<category>") -> str:
    """The command line that declares the category `name`, its values left for the
    person to fill."""
    return (
        f"{COMMAND} {ADD_VERB} {shlex.quote(name)} "
        "--title-format '<a format with {n} and {name}>' "
        f"--close-trigger <{'|'.join(CLOSE_TRIGGERS)}>"
    )


def declare(path: Path, name: str, value: Mapping[str, str]) -> None:
    """Write the category `name`, with `value`, into the configuration at `path`.

    The `milestone_categories` block takes the category after its last category,
    or is added at the end of the file where it is absent. Every other byte is
    kept, a byte-order mark and CRLF line endings among them. The file is read
    here, right before the write, and must read back as it was with only the
    category added.

    Raises Refused, with nothing written, where the file is absent or unreadable,
    already declares `name`, holds a block that is no mapping or is written in
    flow style, or would not read back as it should.
    """
    if not path.is_file():
        raise Refused(
            f"{path} does not exist: author project-management's configuration first "
            '(its README, "Adopter setup")'
        )
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Refused(f"{path} cannot be read: {exc}") from exc
    bom = BOM if text.startswith(BOM) else ""
    text = text[len(bom) :]
    crlf = "\r\n" in text
    if crlf and text.count("\r\n") != text.count("\n"):
        raise Refused(f"{path} mixes line endings; give it one, then run the command again")
    lf = text.replace("\r\n", "\n")
    config = _config_of(lf, path)
    raw = config.get(CONFIG_KEY)
    if raw is not None and not isinstance(raw, Mapping):
        raise Refused(f"`{CONFIG_KEY}` in {path} is not a mapping; fix it first")
    if name in declared(config):
        raise Refused(f"category {name!r} is already declared in {path}")
    updated = _spliced(lf, name, value)
    try:
        reads = YAML(typ="safe").load(updated)
    except YAMLError:
        reads = None
    wanted = {**dict(config), CONFIG_KEY: {**dict(declared(config)), name: dict(value)}}
    if reads != wanted:
        raise Refused(
            f"{path} would not read back unchanged around the `{CONFIG_KEY}` block, so "
            f"nothing was written: declare {name!r} under `{CONFIG_KEY}` by hand"
        )
    path.write_bytes((bom + (updated.replace("\n", "\r\n") if crlf else updated)).encode("utf-8"))


def _config_of(text: str, path: Path) -> Mapping[str, Any]:
    try:
        data = YAML(typ="safe").load(text)
    except YAMLError as exc:
        raise Refused(f"{path} cannot be read: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise Refused(f"{path} is not a mapping")
    return data


#: The top-level key's line: `milestone_categories:`, then a value on the line or
#: a comment.
_KEY_LINE = re.compile(rf"^{CONFIG_KEY}:(?P<rest>.*)$")
#: A value on the key's line that declares no category, so the block may take
#: its first beneath the key.
_EMPTY_VALUES = frozenset({"", "{}", "~", "null"})
_LEAD = (
    "# Milestone categories (project-management DEC-016): each one's title format,",
    "# the close trigger its Milestones take unless they name their own, and what it",
    f"# means. Written by `{COMMAND} {ADD_VERB}`.",
)


def _spliced(text: str, name: str, value: Mapping[str, str]) -> str:
    """`text` with the category added to its top-level `milestone_categories` block,
    after the block's last indented line, or with the block added at the end under
    a comment. A comment on the key's own line stays.

    The category is indented as the block's first entry is, two spaces where it has
    none, and its values twice that. A key's line that holds anything but an empty
    value is left for the read-back to refuse, as a block in flow style is.
    """
    lines = text.split("\n")
    found = next(
        ((i, m) for i, line in enumerate(lines) if (m := _KEY_LINE.match(line)) is not None),
        None,
    )
    if found is None:
        lead = "" if not text or text.endswith("\n") else "\n"
        gap = "\n" if text.strip() else ""
        block = [*_LEAD, f"{CONFIG_KEY}:", *_entry_lines(name, value, "  ")]
        return text + lead + gap + "\n".join(block) + "\n"
    start, match = found
    on_line, hash_sign, comment = match["rest"].partition("#")
    if on_line.strip() not in _EMPTY_VALUES:
        return text
    head = lines[start]
    if on_line.strip():
        head = f"{CONFIG_KEY}:" + (f"  {hash_sign}{comment}" if hash_sign else "")
    last = start
    indent = ""
    for i in range(start + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            continue
        if lines[i][:1] not in (" ", "\t"):
            break
        indent = indent or lines[i][: len(lines[i]) - len(lines[i].lstrip())]
        last = i
    new = _entry_lines(name, value, indent or "  ")
    return "\n".join([*lines[:start], head, *lines[start + 1 : last + 1], *new, *lines[last + 1 :]])


def _entry_lines(name: str, value: Mapping[str, str], indent: str) -> list[str]:
    """The category's lines: its name at `indent`, each value at twice it. A value
    is double-quoted, as JSON writes a string, which YAML reads alike."""
    lines = [f"{indent}{_key(name)}:"]
    lines += [f"{indent * 2}{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in value.items()]
    return lines


def _key(name: str) -> str:
    """`name` as a key: bare where YAML reads it back as the same string, such as
    `sprint`, and double-quoted where it would not, such as `true` or `2026`."""
    try:
        reads = YAML(typ="safe").load(f"{name}: x")
    except YAMLError:
        reads = None
    return name if reads == {name: "x"} else json.dumps(name, ensure_ascii=False)


def _single_line(value: str) -> bool:
    return "\n" not in value and "\r" not in value
