"""Stamping a page, and a space's definition (DEC-001 points 2 and 4; COR-005).

`pkit living-docs new page` writes one new page of a declared kind into a
declared space, from the kind's template: its front matter names its reader and
its kind and carries the friction block with the anchors given, an empty block
with none; its body is the template's, its title written in place of the
level-1 heading's placeholder and every other placeholder left for the writer.
A page's place within its space is the writer's choice, so the command takes
the file's path.

`pkit living-docs new space` writes a space's definition when the project
creates the space (DEC-001 point 2), the three writes the record names:

- the definition, `<definitions>/rule-sets/<space>.md`: a project rule set
  inheriting `living-docs:LDOC` at its current major, with the scope that
  selects the space's pages — the paths the validator names for a definition
  without one (`spaces.space_paths`), by the page type — and, for the user
  space, its one rule of its own, reader paths stay unbroken (point 3);
- its path, as `definition` in the space's entry of the capability's project
  configuration, which declares a space the project adds; the line goes in as
  text, every other byte kept, and the file read back;
- the definitions location, recorded on first use through `pkit docs
  record-location` (COR-049 point 5), once the check after the write passed.

**One judgment, validation's.** Neither stamp decides for itself whether what
it writes is right for the spaces. Each runs the validator's own check
(`spaces.checked`) before and after the write. An error after the write that
was not there before — the same check at the same location — puts back every
file written and refuses, quoting it. A page stamp refuses too when the file
is not a page of the space named, by the check's own classification. A space
stamp judges the write against where the rules bound before it, so it refuses
only what the stamp itself breaks; the errors of the rules the new definition
then makes bind on the space's pages are reported, and the stamp stands. When
the check cannot read what it judges — the places, where the rules bind, the
readers, the kinds' structures — the stamp refuses, before the write or after
it. An interruption during the check puts back what was written, then goes on.

A dry run makes the checks the stamp makes before writing, prints each file it
would write, and writes nothing.

Every file is written whole, to a temporary file beside it then moved over it,
keeping its mode. A path reached through a link is refused: the discovery never
reads one.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from _lib import formats, spaces
from _lib.binding import Binding, read_binding
from _lib.binding import Unreadable as Unbound
from _lib.declarations import (
    CAPABILITY,
    DEFINITIONS_LOCATION,
    DOCUMENT_SUFFIX,
    LDOC_FILE,
    LIVING_DOCS_CONFIG,
    Declarations,
    normalise,
)
from _lib.readers import Readers, read_readers

#: The capability's templates: one per page kind, and a space's definition.
TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
DEFINITION_TEMPLATE = TEMPLATES / "space-definition.md"

#: A word: a reader's id, a space's id (schemas/page.schema.json, config.schema.json).
WORD = re.compile(r"[a-z][a-z0-9-]*")

#: A rule set's name (COR-051 point 3).
SET_NAME = re.compile(r"[A-Z][A-Z0-9]*")

#: The methodology's container, which holds the friction block (COR-053 point 10).
CONTAINER = "pkit"

#: The anchor kinds a page takes, in the order a friction block lists them: the
#: core's three, then the `source` kind this capability registers (DEC-001 point 4).
ANCHOR_KINDS = ("path", "record", "artefact", "source")

#: The user space's one rule of its own (DEC-001 point 3).
USER_RULE_TITLE = "Reader paths stay unbroken"
USER_RULE_TEXT = "The paths the user space's readers take through its pages stay unbroken."
DECISION = f"{CAPABILITY}:DEC-001"

#: How the definitions location is recorded on first use (COR-049 point 5).
RECORD = ("pkit", "docs", "record-location", CAPABILITY, DEFINITIONS_LOCATION)

Runner = Callable[..., subprocess.CompletedProcess[str]]
Read = Callable[[], Readers]
Reach = Callable[[Path], Binding]
Recorder = Callable[[Path], str | None]
IsRecorded = Callable[[Path], bool]


class Refused(Exception):
    """The stamp cannot be made; the message says why and what to do."""


class NotRecorded(Exception):
    """The definitions location could not be recorded; the message says why."""


@dataclass(frozen=True)
class File:
    """A file a stamp writes: its path from the repository root, and its text."""

    path: str
    text: str


@dataclass(frozen=True)
class Stamped:
    """What a stamp wrote, or would write on a dry run, and what it has to say."""

    files: tuple[File, ...]
    notes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    written: bool = True


@dataclass(frozen=True)
class PageRequest:
    """A page to stamp: its file, its space, its kind, its reader, its title and its anchors."""

    file: str
    space: str
    kind: str
    reader: str
    title: str
    paths: tuple[str, ...] = ()
    records: tuple[str, ...] = ()
    artefacts: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpaceRequest:
    """A space to create: its id, and its rule set's name when not the default."""

    space: str
    set_name: str | None = None


# --- a page -------------------------------------------------------------------------------------


def stamp_page(
    root: Path,
    request: PageRequest,
    *,
    dry_run: bool = False,
    read: Read = read_readers,
    reach: Reach = read_binding,
) -> Stamped:
    """Stamp the page `request` names in the project at `root`, or refuse."""
    rel = _new_file(root, request.file)
    _check_word("--reader", request.reader, "a reader's id")
    _check_title(request.title)
    template = _page_template(request.kind)
    anchors = _anchors(request)
    before = _checked(root, read, reach, "before the write")
    decl = _decl(before)
    if request.space not in spaces.known_spaces(decl):
        raise Refused(
            f"space {request.space!r} is not a space of this project, whose spaces are "
            f"{spaces.known_spaces(decl)}: name one of them, or create the space first with "
            f"`pkit {CAPABILITY} new space {request.space}` (DEC-001 point 1)"
        )
    page = File(rel, _page_text(template, request, anchors))
    warnings = _undefined(decl, request.space)
    if dry_run:
        note = (
            f"dry run: nothing written. The checks before the write passed; whether {rel} "
            f"would be a page of space {request.space!r}, and whether it would bring a "
            f"validation error, is known only once it is written."
        )
        return Stamped((page,), (note,), warnings, written=False)
    writes = _Writes(root)
    with writes.undone_on_failure():
        writes.write(page)
        after = _checked(root, read, reach, "after the write")
        standing = after.standing(rel)
        if standing.space != request.space:
            why = (
                f"it would be a page of space {standing.space!r}, by its root or its place's "
                f"assignment"
                if standing.space is not None
                else standing.why
            )
            raise Refused(
                f"{rel} would not be a page of space {request.space!r}: {why}. Put it under the "
                f"space's root, or in a place assigned to the space (DEC-001 point 1); nothing "
                f"is written"
            )
        _refuse_new_errors(before.outcome, after.outcome, rel)
    notes = [
        f"stamped {rel}: a {request.kind} page of space {request.space!r}, for reader "
        f"{request.reader!r}.",
        *_placeholders_left(template, page.text, rel),
        f"Anchor each statement on what makes it true (RS-LDOC-001), then run `pkit {CAPABILITY} "
        f"validate`, `pkit validate` and `pkit friction check`.",
    ]
    return Stamped((page,), tuple(notes), warnings)


def _new_file(root: Path, file: str) -> str:
    """The new page's path from the repository root, refused when it is not a Markdown
    file inside the repository, is reached through a link, or exists."""
    written = file.strip().replace("\\", "/")
    if not written or written.startswith("/") or Path(written).is_absolute():
        raise Refused(
            f"{file!r} is not a path from the repository root: give one, such as docs/guide.md"
        )
    if ".." in written.split("/"):
        raise Refused(f"{file!r} leads outside the repository: a page lies inside it")
    rel = normalise(written)
    if not rel.endswith(DOCUMENT_SUFFIX) or rel == DOCUMENT_SUFFIX:
        raise Refused(
            f"{rel} does not end `{DOCUMENT_SUFFIX}`: only a Markdown file is a document (the "
            f"discovery reads no other)"
        )
    target = root / rel
    refuse_links(root, target, rel)
    if target.exists() or target.is_symlink():
        raise Refused(f"{rel} exists already: a stamp writes a new page, never over a file")
    return rel


def _check_word(option: str, value: str, what: str) -> None:
    if not WORD.fullmatch(value):
        raise Refused(
            f"{option} {value!r} is not {what}: a word, a lowercase letter then lowercase letters, "
            f"digits and hyphens"
        )


def _check_title(title: str) -> None:
    """The title as validation reads a page's level-1 heading (`formats`): one line,
    with words of its own, never empty nor a placeholder whole (`<…>`)."""
    if "\n" in title or "\r" in title:
        raise Refused("--title is one line: a page's title is its level-1 heading")
    found = formats.headings(f"# {title.strip()}\n")
    if len(found) != 1 or not found[0].worded:
        raise Refused(
            f"--title {title!r} is not a title validation reads: it is empty, or a placeholder "
            f"whole (`<…>`), which a page's title never is — write the title itself"
        )


def _page_template(kind: str) -> str:
    """The kind's template, for a kind the capability declares: listed in its
    declaration of structures, with its template beside the others."""
    try:
        structures = formats.read_structures(spaces.PAGE_KINDS)
    except formats.Unreadable as exc:
        raise Refused(
            f"the page kinds' structures cannot be read — {str(exc).rstrip('.')}: the file is "
            f"{CAPABILITY}'s own, {spaces.PAGE_KINDS_PATH} — restore it as the capability ships "
            f"it (DEC-001 point 3)"
        ) from exc
    declared = sorted(k for k in structures if (TEMPLATES / f"{k}.md").is_file())
    if kind not in declared:
        raise Refused(
            f"kind {kind!r} is not one {CAPABILITY} declares, {declared}. A kind the project adds "
            f"has its own template: write the page by hand from it (DEC-001 point 3)"
        )
    return (TEMPLATES / f"{kind}.md").read_text(encoding="utf-8")


def _anchors(request: PageRequest) -> dict[str, list[str]]:
    """The anchors given, by kind, each once, in the order given."""
    given = dict(
        zip(
            ANCHOR_KINDS,
            (request.paths, request.records, request.artefacts, request.sources),
            strict=True,
        )
    )
    for kind, values in given.items():
        if any(not value.strip() for value in values):
            raise Refused(f"--{kind} is empty: give the {kind} the page rests on")
    return {
        kind: list(dict.fromkeys(v.strip() for v in values))
        for kind, values in given.items()
        if values
    }


def _page_text(template: str, request: PageRequest, anchors: Mapping[str, list[str]]) -> str:
    """The page: its own fields and the friction block, then the template's body with
    the title in its level-1 heading. The template's front matter, with its comments,
    is not copied."""
    _front, body = _split(template)
    block: dict[str, Any] = {"anchors": dict(anchors)} if anchors else {}
    front = {"reader": request.reader, "kind": request.kind, CONTAINER: {"friction": block}}
    return f"---\n{_dump(front)}---\n{_titled(body, request.title.strip())}"


def _titled(body: str, title: str) -> str:
    """`body` with `title` in its first level-1 heading, or headed by it when it has none."""
    lines = body.split("\n")
    heading = next((h for h in formats.headings(body) if h.level == 1), None)
    if heading is None:
        return f"\n# {title}\n{body}"
    lines[heading.line - 1] = f"# {title}"
    return "\n".join(lines)


def _placeholders_left(template: str, text: str, rel: str) -> list[str]:
    """The page's lines that still hold one of the template's own placeholders, matched
    exactly as the template writes them, so words of the writer's own in angle brackets
    are never listed."""
    _front, body = _split(template)
    held = set(spaces.PLACEHOLDER.findall(body))
    lines = [
        f"  {rel}:{number}: {line.strip()}"
        for number, line in enumerate(text.split("\n"), 1)
        if any(placeholder in line for placeholder in held)
    ]
    if not lines:
        return []
    return [
        "These lines still hold the template's placeholders: write in each what it asks for.",
        *lines,
    ]


def _undefined(decl: Declarations, space: str) -> tuple[str, ...]:
    config = decl.spaces.get(space)
    if config is not None and config.definition is not None:
        return ()
    return (
        f"space {space!r} has no definition yet, so no rule binds on its pages and validation "
        f"checks neither the page's reader nor its structure: create it with `pkit {CAPABILITY} "
        f"new space {space}` (DEC-001 point 2)",
    )


# --- a space ------------------------------------------------------------------------------------


def stamp_space(
    root: Path,
    request: SpaceRequest,
    *,
    dry_run: bool = False,
    read: Read = read_readers,
    reach: Reach = read_binding,
    record: Recorder | None = None,
    is_recorded: IsRecorded | None = None,
) -> Stamped:
    """Write the definition of the space `request` names in the project at `root`, name
    it in the capability's project configuration and record the definitions location
    on first use, or refuse."""
    record = record or record_location
    is_recorded = is_recorded or location_recorded
    space = request.space
    _check_word("the space", space, "a space's id")
    set_name = request.set_name if request.set_name is not None else space.upper().replace("-", "")
    if not SET_NAME.fullmatch(set_name):
        raise Refused(
            f"--set {set_name!r} is not a rule set's name: an upper-case letter, then upper-case "
            f"letters and digits (COR-051 point 3)"
        )
    try:
        bound = reach(root)
    except Unbound as exc:
        raise Refused(
            f"where the rules bind cannot be read — {str(exc).rstrip('.')}. The stamp judges its "
            f"write against where they bind, so it writes nothing until they can be read"
        ) from exc

    def bound_before(_root: Path) -> Binding:
        return bound

    before = _checked(root, read, bound_before, "before the write")
    decl = _decl(before)
    rel = _definition_path(root, decl, space)
    taken = _set_named(decl, set_name)
    if taken is not None:
        raise Refused(
            f"rule set {set_name} is declared already, by {taken}: rule-set names are unique "
            f"(COR-051 point 3) — name the space's set with --set"
        )
    paths, exclude = spaces.space_paths(space, decl)
    if not paths:
        raise Refused(_no_scope(space, decl))
    major = spaces.ldoc_major(decl)
    if not major.isdigit():
        raise Refused(
            f"the shared method's version cannot be read from {LDOC_FILE}, so its major, which "
            f"a definition pins, is not known: restore the file as {CAPABILITY} ships it"
        )
    definition = File(rel, _definition_text(space, set_name, major, paths, exclude))
    added = space not in spaces.known_spaces(decl)
    config = File(LIVING_DOCS_CONFIG, _config_text(root, space, rel))
    recording = not is_recorded(root)
    rule = f"RS-{set_name}-001" if space == spaces.USER_SPACE else None
    if dry_run:
        notes = [
            "dry run: nothing written. The checks before the write passed; the check after it "
            "runs only on a write."
        ]
        if recording:
            notes.append(
                f"It would record the definitions location, {decl.definitions} (COR-049 point 5)."
            )
        return Stamped((definition, config), tuple(notes), written=False)
    writes = _Writes(root)
    with writes.undone_on_failure():
        writes.write(definition)
        writes.write(config)
        after = _checked(root, read, bound_before, "after the write")
        _refuse_new_errors(before.outcome, after.outcome, rel)
        live = _checked(root, read, reach, "after the write")
        failing = _new_errors(after.outcome, live.outcome)
        recorded = None
        if recording:
            try:
                recorded = record(root)
            except NotRecorded as exc:
                raise Refused(
                    f"the definitions location could not be recorded: {exc}; nothing is written"
                ) from exc
    scope = ", ".join(paths) + (f", leaving out {', '.join(exclude)}" if exclude else "")
    notes = [
        f"stamped {rel}: the definition of space {space!r}, rule set {set_name}, inheriting "
        f"{spaces.LDOC}@{major}, scoped to the space's pages ({scope}).",
        f"named it as the space's `definition` in {LIVING_DOCS_CONFIG}"
        + (", which declares the space." if added else "."),
    ]
    if recorded:
        notes.append(recorded)
    if rule is not None:
        notes.append(
            f"{rule}, {USER_RULE_TITLE.lower()}, is written accepted: the review of the change "
            f"that carries this definition accepts it (COR-051 point 4)."
        )
    notes.append(
        f"Name the space's entry point in {LIVING_DOCS_CONFIG} once its page exists (`pkit "
        f"{CAPABILITY} new page … --space {space}`); then run `pkit {CAPABILITY} validate`, "
        f"`pkit validate` and `pkit friction check`."
    )
    warnings = [
        f"the space's rules now bind on its pages, and validation fails {f.location}: {f.message}"
        for f in failing
    ]
    return Stamped((definition, config), tuple(notes), tuple(warnings))


def _definition_path(root: Path, decl: Declarations, space: str) -> str:
    """Where the space's definition goes, refused when the space has one already."""
    if decl.definitions is None:
        raise Refused(
            f"{CAPABILITY}'s package declares no definitions location, so a definition has no "
            f"place: restore the package as {CAPABILITY} ships it (DEC-001 point 2)"
        )
    config = decl.spaces.get(space)
    if config is not None and config.definition is not None:
        raise Refused(
            f"space {space!r} exists: {LIVING_DOCS_CONFIG} names its definition, "
            f"{config.definition}. A stamp writes no definition that exists (DEC-001 point 2)"
        )
    rel = f"{decl.definitions}/{spaces.RULE_SETS}/{space}{DOCUMENT_SUFFIX}"
    target = root / rel
    refuse_links(root, target, rel)
    if target.exists() or target.is_symlink():
        raise Refused(
            f"{rel} exists already: space {space!r} has a definition {LIVING_DOCS_CONFIG} does not "
            f"name — name it there as the space's `definition`. A stamp writes no definition "
            f"that exists (DEC-001 point 2)"
        )
    return rel


def _set_named(decl: Declarations, name: str) -> str | None:
    """The rule-set file that declares `name` already, as the backbone's reading shows."""
    for rel, document in sorted(decl.documents.items()):
        if document.rule_set and (document.fields or {}).get("rule-set") == name:
            return rel
    return None


def _no_scope(space: str, decl: Declarations) -> str:
    """Why no scope selects the space's pages yet, and the fix."""
    if decl.user_root == decl.internal_root and space in spaces.SPACE_OF_ROOT.values():
        why = (
            f"the two documentation roots are one folder, {decl.user_root!r}, so neither space "
            f"has a root of its own, and no place is assigned to {space!r}"
        )
        fix = (
            "separate the roots first — `docs.user` and `docs.internal` in the backbone "
            "configuration, onboarding's first step — or declare the space's places in "
            "`friction.places` and assign them to it under `places`"
        )
    else:
        why = f"space {space!r} has no root of its own and no place assigned to it"
        fix = (
            f"declare its places in `friction.places`, each giving the page type where it lies "
            f"outside every root, and assign them to {space!r} under `places` in "
            f"{LIVING_DOCS_CONFIG}"
        )
    return (
        f"no scope can select the space's pages: {why}. A definition's scope names the space's "
        f"root and the places assigned to it (DEC-001 point 2) — {fix}, then stamp again"
    )


def _definition_text(
    space: str, set_name: str, major: str, paths: Sequence[str], exclude: Sequence[str]
) -> str:
    """The space's definition: the set, its pin on the shared method, its scope and, for
    the user space, its one rule with its body section (DEC-001 points 2 and 3); the body
    the template's, the space named."""
    scope: dict[str, Any] = {"paths": list(paths)}
    if exclude:
        scope["exclude"] = list(exclude)
    scope["types"] = [spaces.PAGE_TYPE]
    rules: dict[str, Any] = {}
    sections = ""
    if space == spaces.USER_SPACE:
        rule = f"RS-{set_name}-001"
        rules[rule] = {
            "status": "accepted",
            "origin": {"decision": DECISION},
            CONTAINER: {"friction": {"anchors": {"record": [f"{DECISION}#3"]}}},
        }
        sections = f"\n## {rule} — {USER_RULE_TITLE}\n\n{USER_RULE_TEXT}\n"
    front = {
        "rule-set": set_name,
        "version": "1.0.0",
        "inherits": [f"{spaces.LDOC}@{major}"],
        "scope": scope,
        "rules": rules,
    }
    _front, body = _split(DEFINITION_TEMPLATE.read_text(encoding="utf-8"))
    return f"---\n{_dump(front, flow=True)}---\n{body.replace('<space>', space)}{sections}"


# --- the capability's project configuration -------------------------------------------------------

#: A top-level key's line opening a block: `spaces:`, with nothing after it but a comment.
_BLOCK_KEY = r"^{key}:[ \t]*(?:#.*)?$"


def _config_text(root: Path, space: str, definition: str) -> str:
    """The capability's project configuration with `definition` under `spaces.<space>`:
    the line goes in as text, every other byte kept, line endings included, and the
    file must read back as it was plus that entry. An absent file is created."""
    value = definition if re.fullmatch(r"[A-Za-z0-9._/-]+", definition) else json.dumps(definition)
    target = root / LIVING_DOCS_CONFIG
    refuse_links(root, target, LIVING_DOCS_CONFIG)
    if not target.exists():
        return (
            "pkit_schema: living-docs:config\nschema_version: 1\n\n"
            f"spaces:\n  {space}:\n    definition: {value}\n"
        )
    try:
        written = target.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Refused(f"{LIVING_DOCS_CONFIG} could not be read: {exc}") from exc
    crlf = _crlf(written)
    text = written.replace("\r\n", "\n") if crlf else written
    was = _load(text)
    updated = _inserted(text, space, value)
    wanted = copy.deepcopy(dict(was))
    entries = wanted.get("spaces") if isinstance(wanted.get("spaces"), dict) else {}
    entry = entries.get(space) if isinstance(entries.get(space), dict) else {}
    wanted["spaces"] = {**entries, space: {**entry, "definition": definition}}
    try:
        reads = _load(updated)
    except Refused:
        reads = None
    if reads != wanted:
        raise Refused(
            f"{LIVING_DOCS_CONFIG} would not read back as it is plus the space's definition — "
            f"its `spaces` is not written as the stamp can edit it, a block mapping: add "
            f"`definition: {value}` under `spaces.{space}` there by hand, then stamp again"
        )
    return updated.replace("\n", "\r\n") if crlf else updated


def _load(text: str) -> Mapping[str, Any]:
    try:
        data = YAML(typ="safe").load(text)
    except YAMLError as exc:
        raise Refused(f"{LIVING_DOCS_CONFIG} does not parse; fix it first ({exc})") from exc
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise Refused(f"{LIVING_DOCS_CONFIG} is not a mapping; fix it first")
    return data


def _crlf(text: str) -> bool:
    """Whether every line of `text` ends CRLF — the file is then edited as LF and
    written back CRLF; mixed line endings are refused."""
    if "\r" not in text:
        return False
    if text.count("\r\n") == text.count("\n") == text.count("\r"):
        return True
    raise Refused(
        f"{LIVING_DOCS_CONFIG} has mixed line endings: the stamp writes its line with the file's "
        f"own ending, and this file has no one ending — make them one, then stamp again"
    )


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _content(line: str) -> bool:
    """Whether a line holds a key or a value: not blank, and not a comment alone."""
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def _inserted(text: str, space: str, value: str) -> str:
    """The LF file `text` with `definition: <value>` under `spaces.<space>`, written as a
    block mapping: after the space's last line, or a new entry after the last line of
    `spaces`, or a new `spaces` at the end. What is not a block mapping is read back
    wrong, and refused there."""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if re.match(_BLOCK_KEY.format(key="spaces"), line)]
    if not starts:
        lead = "" if not text or text.endswith("\n") else "\n"
        return f"{text}{lead}spaces:\n  {space}:\n    definition: {value}\n"
    start = starts[0]
    end = start + 1
    while end < len(lines) and (not _content(lines[end]) or lines[end][:1] in (" ", "\t")):
        end += 1
    block = [i for i in range(start + 1, end) if _content(lines[i])]
    if not block:
        return _at(lines, start, [f"  {space}:", f"    definition: {value}"])
    step = min(_indent(lines[i]) for i in block)
    keyed = re.compile(rf"^[ \t]{{{step}}}{re.escape(space)}:[ \t]*(?:#.*)?$")
    own = next((i for i in block if _indent(lines[i]) == step and keyed.match(lines[i])), None)
    if own is None:
        return _at(
            lines, block[-1], [f"{' ' * step}{space}:", f"{' ' * (2 * step)}definition: {value}"]
        )
    children = []
    for i in block:
        if i <= own:
            continue
        if _indent(lines[i]) <= step:
            break
        children.append(i)
    if not children:
        return _at(lines, own, [f"{' ' * (2 * step)}definition: {value}"])
    deeper = _indent(lines[children[0]])
    return _at(lines, children[-1], [f"{' ' * deeper}definition: {value}"])


def _at(lines: list[str], after: int, added: Sequence[str]) -> str:
    """`lines` joined, with `added` after line `after`."""
    return "\n".join([*lines[: after + 1], *added, *lines[after + 1 :]])


# --- the check, before and after ------------------------------------------------------------------


def _checked(root: Path, read: Read, reach: Reach, when: str) -> spaces.Checked:
    """The validator's own check, refused when it cannot read what it judges: then the
    stamp cannot tell what its write would break."""
    result = spaces.checked(root, read, reach)
    unread = [f for f in result.outcome.errors if f.check in spaces.UNREAD]
    if unread or result.decl is None:
        first = unread[0] if unread else None
        why = first.message if first is not None else "the places cannot be read."
        raise Refused(
            f"{when}, the check cannot read all it judges: {why} The stamp judges its write by "
            f"that check, so it writes nothing until the check can"
        )
    return result


def _decl(result: spaces.Checked) -> Declarations:
    assert result.decl is not None  # `_checked` refuses without it
    return result.decl


def _key(finding: spaces.Finding) -> tuple[str, str, str]:
    """What tells one error from another: its severity, location and check — never its
    message, which names what the state holds."""
    return finding.severity, finding.location, finding.check


def _new_errors(before: spaces.Outcome, after: spaces.Outcome) -> list[spaces.Finding]:
    known = {_key(finding) for finding in before.errors}
    return [finding for finding in after.errors if _key(finding) not in known]


def _refuse_new_errors(before: spaces.Outcome, after: spaces.Outcome, rel: str) -> None:
    new = _new_errors(before, after)
    if not new:
        return
    found = "; ".join(f"{f.location}: {f.message}" for f in new)
    raise Refused(
        f"writing {rel} would bring validation errors the project did not have — {found} "
        f"Nothing is written"
    )


# --- recording the definitions location ----------------------------------------------------------


def location_recorded(root: Path, run: Runner = subprocess.run) -> bool:
    """Whether the definitions location is recorded already (COR-049 point 5), as `pkit
    docs record-location --dry-run` says, writing nothing; `False` when it cannot tell,
    so the stamp records, and a recording that fails refuses the stamp."""
    try:
        proc = run([*RECORD, "--dry-run"], cwd=root, capture_output=True, text=True, check=False)
    except OSError:
        return False
    return proc.returncode == 0 and (proc.stdout or "").strip().endswith("(recorded already)")


def record_location(root: Path, run: Runner = subprocess.run) -> str | None:
    """Record the definitions location where it now lies, through `pkit docs
    record-location`, the backbone's one writer of it, which asks nothing: the value is
    the one already in use (COR-049 point 5). Returns what it printed when it recorded,
    `None` when it was recorded already. Raises NotRecorded when it fails."""
    argv = [*RECORD, "--yes"]
    try:
        proc = run(argv, cwd=root, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise NotRecorded(f"`pkit` could not be run ({exc})") from exc
    if proc.returncode != 0:
        detail = [line for line in (proc.stderr or proc.stdout or "").splitlines() if line.strip()]
        raise NotRecorded(
            f"`{' '.join(argv)}` exited {proc.returncode}" + (f": {detail[-1]}" if detail else "")
        )
    out = (proc.stdout or "").strip()
    return out if out.startswith("recorded ") else None


# --- writing --------------------------------------------------------------------------------------


class _Writes:
    """The files a stamp writes, each with what it was, so they can be put back."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.done: list[tuple[Path, bytes | None, list[Path]]] = []

    def write(self, file: File) -> None:
        target = self.root / file.path
        refuse_links(self.root, target, file.path)
        before = target.read_bytes() if target.is_file() else None
        made = [folder for folder in (target.parent, *target.parent.parents) if not folder.exists()]
        self.done.append((target, before, made))
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            write_whole(target, file.text.encode("utf-8"))
        except OSError as exc:
            raise Refused(f"{file.path} could not be written: {exc}") from exc

    def put_back(self) -> list[str]:
        """Every file as it was — its bytes, or no file — and the folders made for it
        gone; the paths it could not put back."""
        left: list[str] = []
        for target, before, made in reversed(self.done):
            try:
                if before is not None:
                    write_whole(target, before)
                elif target.is_file():
                    target.unlink()
                for folder in made:  # the deepest first
                    folder.rmdir()
            except OSError:
                left.append(target.relative_to(self.root).as_posix())
        self.done.clear()
        return left

    @contextlib.contextmanager
    def undone_on_failure(self) -> Iterator[None]:
        """Put back what was written when the block fails or is interrupted, then go
        on with the failure; name each file that could not be put back."""
        try:
            yield
        except BaseException as exc:
            left = self.put_back()
            if left:
                note = (
                    f"putting back what the stamp wrote failed, so these are left as written: "
                    f"{', '.join(left)} — restore or remove them by hand"
                )
                if isinstance(exc, Refused):
                    raise Refused(f"{exc}; {note}") from exc
                print(f"error: {note}", file=sys.stderr)
            raise


def refuse_links(root: Path, target: Path, location: str) -> None:
    """Refuse `target` when it, or a folder between it and `root`, is a link: the
    discovery never reads a link as a document, nor anything beneath a linked folder,
    and a file written whole would replace the link it was reached by."""
    for path in (target, *target.parents):
        if path == root:
            return
        if path.is_symlink():
            raise Refused(
                f"{location} is reached through the link {path.relative_to(root).as_posix()}: the "
                f"discovery never reads a link as a document, nor anything beneath a linked "
                f"folder — put the file or folder itself in the link's place, then stamp again"
            )


def write_whole(target: Path, data: bytes) -> None:
    """Write `data` to `target` whole or not at all: to a temporary file beside it, then
    moved over it. A file keeps its mode; a new one takes what the umask gives."""
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o666 & ~_umask()
    handle, temporary = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


# --- text -----------------------------------------------------------------------------------------


def _split(text: str) -> tuple[str, str]:
    """A template's front matter and its body, the body from the line after the
    closing fence."""
    lines = text.split("\n")
    if lines and lines[0].rstrip() == "---":
        for index in range(1, len(lines)):
            if lines[index].rstrip() == "---":
                return "\n".join(lines[1:index]), "\n".join(lines[index + 1 :])
    return "", text


def _dump(data: Mapping[str, Any], *, flow: bool = False) -> str:
    """`data` as YAML: in block style, or with each list and mapping of plain values in
    flow style, as a rule set's front matter is written."""
    yaml = YAML()
    yaml.default_flow_style = None if flow else False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096
    buffer = io.StringIO()
    yaml.dump(dict(data), buffer)
    return buffer.getvalue()
