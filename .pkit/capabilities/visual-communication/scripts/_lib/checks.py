"""The check: what the project's visual work breaks, within the project's validation
(visual-communication DEC-002 points 3, 4, 6 and 7, DEC-003 point 9, DEC-004 points 8, 9
and 11, DEC-005 points 9, 13 and 14, DEC-006 point 8).

**File-level findings, every run:**

- the binding of each file of the capability's format in the location, read from its
  name, and of the configuration: a file that names no schema, or another one, fails (a
  file at another format number the core's data validation reports, so this check does
  not repeat it);
- the library folder and its list (`libraries.Held.findings`);
- each piece's lock: a version the project does not hold or the capability cannot read,
  a library the piece uses that the lock does not name, libraries that build on another
  major than the one locked; a piece with no lock yet;
- the brand each piece locks, and its findings: open roles, fonts, declared pairs;
- the ids in each content file, and each content file against the fields and options of
  the components it fills, the nearest known key named.

**Scene findings** (`scene_findings`): what computing a piece's scenes finds, in every
language: the engine's own (overflow, a component that gets less than it asks for, two
owners of a value, a loop, a missing exposed part or point, a page inside a page), a
produced picture that is missing, contrast as drawn, a colour role the brand lacks, each
loss of the renderers that draw the piece that nobody accepted, and the components it uses
that are experimental or deprecated. A render keeps them in the piece's `findings.yaml`,
keyed by a fingerprint of every file they were computed from. The check reads that record
while its key verifies, and computes the scenes now otherwise. It computes no more once
the validator's bound (`PKIT_COMMAND_DEADLINE`) is near: each piece left fails as not
checked, naming `pkit visual render <piece>`.

**Severity** is computed when a finding is read: a failing finding in a released library
version asks for attention instead (`findings.level_where`), and whether a version is
released is read from the list.

In the findings record, a finding's file is relative to the piece's folder, or, where it
lies in a library version, to that version's folder, so the record stays true when the
location moves or the piece is copied. The check gives every file relative to the project
root.
"""

from __future__ import annotations

import dataclasses
import math
import re
import time
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from _lib import code, fingerprint, framing, location, names, tokens
from _lib import pipeline as pl
from _lib.env import MissingFont
from _lib.files import FileError, binding_problem, nearest, read_bound, schema_of
from _lib.findings import ATTENTION, FACT, FAILS, SEVERITY, Finding, level_where
from _lib.libraries import FOLDER, Held, Version
from _lib.plugins import seam
from _lib.reading import ReadError, read_yaml
from _lib.root import CONFIG
from _lib.scene import Scene, SceneResult

#: The renderers that draw every piece: its previews, and its SVG exports.
RENDERERS = ("svg",)

#: The environment variable that carries the validator's deadline, in seconds since the
#: epoch.
DEADLINE = "PKIT_COMMAND_DEADLINE"

#: What the check keeps of its bound to answer, in seconds.
MARGIN = 1.0

#: WCAG's large text: at least 24 px, or 18.66 px and bold (DEC-004 point 8).
LARGE = 24.0
LARGE_BOLD = 18.66
BOLD = 700

#: The colour a text with no fill is drawn in.
BLACK = {"colorSpace": "srgb", "components": [0, 0, 0], "alpha": 1}

#: The properties of a scene element that are no property it draws.
_STRUCTURE = ("type", "id", "sources", "children")

#: What a renderer did with a loss, in words.
_DID = {
    seam.APPROXIMATED: "approximates",
    seam.PICTURE: "draws as a picture",
    seam.LEFT_OUT: "leaves out",
    seam.REFUSED: "refuses",
}

_CONTENT_FILE = re.compile(r"^content\.(?P<language>[^.]+)\.yaml$")


@dataclasses.dataclass(frozen=True)
class Report:
    """What the check found: its summary, and each finding with the level it takes where
    it lies, its file relative to the project root."""

    summary: list[str]
    judged: list[tuple[Finding, str]]

    def failed(self) -> bool:
        return any(level == FAILS for _, level in self.judged)


def deadline_from(environ: Mapping[str, str]) -> float | None:
    """The validator's deadline the environment gives, or None."""
    try:
        value = float(environ.get(DEADLINE, ""))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


# --- the check ----------------------------------------------------------------------------------


def check(root: Path, *, only: str | None = None, deadline: float | None = None) -> Report:
    """The check of the project at `root`: every piece, or the piece `only`."""
    found: list[Finding] = []
    config = _config_findings(root)
    try:
        where = location.for_reading(root)
    except location.LocationRefused as exc:
        found.append(Finding("location", FAILS, str(exc), file=CONFIG))
        return Report(
            ["The location cannot be read, so nothing is checked."], _plain(config + found)
        )
    if where is None:
        summary = [
            f"No visual work: {CONFIG} records no location, and `{location.DEFAULT}/` holds none."
        ]
        return Report(summary, _plain(config))
    run = _Run(root, where.path, deadline)
    try:
        run.all(only)
    except location.GitFailed as exc:
        run.add(Finding("files-unlisted", FAILS, f"the location's files cannot be listed: {exc}"))
    judged = [(finding, run.level(finding)) for finding in [*config, *run.found]]
    return Report(run.summary(only), judged)


def _plain(found: list[Finding]) -> list[tuple[Finding, str]]:
    return [(finding, finding.level) for finding in found]


def _config_findings(root: Path) -> list[Finding]:
    path = root / CONFIG
    if not path.is_file():
        return []
    try:
        data = read_yaml(path)
    except ReadError as exc:
        return [Finding("file-unreadable", FAILS, str(exc), file=CONFIG)]
    problem = _binding(data, "config")
    return (
        [Finding("binding", FAILS, f"the configuration {problem}", file=CONFIG)] if problem else []
    )


def _binding(data: Any, kind: str) -> str | None:
    """Why a file of `kind` is not bound to its schema, or None. A file bound to it at
    another format number is the core's data validation's to report."""
    if isinstance(data, Mapping) and data.get("pkit_schema") == schema_of(kind):
        return None
    return binding_problem(data, kind)


class _Run:
    """One run of the check over a location."""

    def __init__(self, root: Path, location_path: str, deadline: float | None) -> None:
        self.root = root
        self.location = location_path
        self.deadline = deadline
        self.found: list[Finding] = []
        self.held = Held(root, location_path)
        self.unbound: set[str] = set()
        self.brands: set[str] = set()
        self.counts = {"pieces": 0, "read": 0, "computed": 0, "unchecked": 0}

    def add(self, finding: Finding) -> None:
        self.found.append(finding)

    def level(self, finding: Finding) -> str:
        name, _, text = finding.library.partition("@")
        try:
            released = self.held.released(name, Version.parse(text))
        except ValueError:
            released = False
        return level_where(finding, released)

    def summary(self, only: str | None) -> list[str]:
        c = self.counts
        what = f"the piece `{only}`" if only else f"{c['pieces']} piece(s)"
        return [
            f"{what} in `{self.location}`: the scenes of {c['read']} read from their findings "
            f"record, of {c['computed']} computed now, of {c['unchecked']} not checked."
        ]

    def all(self, only: str | None) -> None:
        files = location.files(self.root, self.location)
        if only is None:
            self._bindings(files)
            self.found.extend(self.held.findings())
        names_ = pl.piece_names(self.root, self.location)
        if only is not None:
            if only not in names_:
                self.add(
                    Finding(
                        "piece-missing",
                        FAILS,
                        f"the location holds no piece `{only}`",
                        file=f"{self.location}/{pl.PIECES}",
                    )
                )
                return
            self._bindings(
                [rel for rel in files if rel.startswith(f"{self.location}/{pl.PIECES}/{only}/")]
            )
            names_ = [only]
        for name in names_:
            self.counts["pieces"] += 1
            self._piece(name)
        if only is None:
            self.found.extend(_code_findings(self.root, self.location))

    # -- bindings

    def _bindings(self, files: Sequence[str]) -> None:
        prefix = f"{self.location}/"
        for rel in files:
            inside = rel[len(prefix) :]
            kind = kind_of(inside)
            if kind is None:
                continue
            library = _library_of(inside)
            try:
                data = read_yaml(self.root / rel)
            except ReadError as exc:
                self.unbound.add(rel)
                self.add(Finding("file-unreadable", FAILS, str(exc), file=rel, library=library))
                continue
            problem = _binding(data, kind)
            if problem is not None:
                self.unbound.add(rel)
                self.add(
                    Finding(
                        "binding",
                        FAILS,
                        f"a file of the capability's format {problem}",
                        file=rel,
                        library=library,
                    )
                )

    # -- a piece

    def _piece(self, name: str) -> None:
        rel = f"{self.location}/{pl.PIECES}/{name}"
        try:
            piece = pl.read_piece(self.root, self.location, name)
        except pl.Refused as exc:
            if not any(path.startswith(f"{rel}/") for path in self.unbound):
                self.add(
                    Finding("piece-unreadable", FAILS, str(exc), file=f"{rel}/{pl.PIECE_FILE}")
                )
            self.counts["unchecked"] += 1
            return
        self.found.extend(id_findings(piece))
        lock = lock_findings(self.held, piece)
        self.found.extend(lock)
        if lock:
            self.counts["unchecked"] += 1
            return
        try:
            project = pl.Project(piece, piece.lock, self.held)
        except pl.Refused as exc:
            self.add(Finding("piece-unreadable", FAILS, str(exc), file=piece.file(pl.PIECE_FILE)))
            self.counts["unchecked"] += 1
            return
        except tokens.TokenError as exc:
            self._brand_findings(piece.brand, piece.lock.get(piece.brand, ""), exc.findings)
            self.counts["unchecked"] += 1
            return
        self._brand_findings(piece.brand, project.lock[piece.brand], project.brand.findings)
        self.found.extend(content_findings(project))
        produced = _produced_findings(self.root, self.location, piece)
        self.found.extend(produced)
        self._scenes(project, _unmade(produced))

    def _brand_findings(self, brand: str, version: str, found: Sequence[Finding]) -> None:
        label = f"{brand}@{version}"
        if label not in self.brands:
            self.brands.add(label)
            self.found.extend(found)

    def _scenes(self, project: pl.Project, unmade: set[str]) -> None:
        piece = project.piece
        if piece.state != "draft":
            return
        stored = read_findings_record(self.root, self.held, piece)
        if stored is not None:
            self.counts["read"] += 1
            self.found.extend(
                rooted(finding, piece) for finding in stored if not _said(finding, unmade)
            )
            return
        if self.deadline is not None and time.time() > self.deadline - MARGIN:
            self.counts["unchecked"] += 1
            self.add(
                Finding(
                    "not-checked",
                    FAILS,
                    f"the scenes of `{piece.name}` were not checked within the validation's "
                    f"bound, and its findings record is missing or out of date",
                    file=piece.file(pl.FINDINGS_FILE),
                    fix=f"run {pl.render_command(piece.name)} and commit its findings record",
                )
            )
            return
        self.counts["computed"] += 1
        self.found.extend(
            rooted(finding, piece) for finding in computed(project) if not _said(finding, unmade)
        )


def kind_of(inside: str) -> str | None:
    """The kind of file of the capability's format a path within the location names, by
    its name and place; None for a file no name makes one."""
    parts = inside.split("/")
    if not inside.endswith(".yaml"):
        return None
    if parts == [FOLDER, "libraries.yaml"]:
        return "libraries"
    if parts[0] == FOLDER and len(parts) >= 4:
        within = parts[3:]
        if within == ["library.yaml"]:
            return "library"
        if within == ["roles.yaml"]:
            return "roles"
        if len(within) == 2 and within[0] == pl.COMPONENTS:
            return "component"
        return None
    if parts[0] == pl.PIECES and len(parts) >= 3:
        within = parts[2:]
        single = {
            (pl.PIECE_FILE,): "piece",
            (pl.FINDINGS_FILE,): "findings",
            (pl.EXPORTS_FILE,): "exports",
        }
        if tuple(within) in single:
            return single[tuple(within)]
        if len(within) == 1 and _CONTENT_FILE.match(within[0]):
            return "content"
        if len(within) == 2 and within[0] == pl.COMPONENTS:
            return "component"
        if len(within) == 3 and within[0] == pl.PRODUCED and within[2] == pl.RECORD:
            return "produced-record"
        return None
    if parts[0] == "code" and len(parts) == 2:
        return "code"
    return None


def _library_of(inside: str) -> str:
    parts = inside.split("/")
    if parts[0] == FOLDER and len(parts) >= 4:
        try:
            return f"{parts[1]}@{Version.parse(parts[2])}"
        except ValueError:
            return ""
    return ""


def _produced_findings(root: Path, location_path: str, piece: pl.Piece) -> list[Finding]:
    """The findings on a piece's produced pictures (DEC-006 point 8): an output with no
    record, a record that names a missing variant file, a stale picture. The producer's
    framing owns them (`framing.findings`)."""
    return framing.findings(root, location_path, piece.name)


# The producer's findings that say a produced output has no picture to draw.
_UNMADE = ("produced-record-missing", "produced-record-unreadable", "produced-variant-missing")


def _unmade(produced: Sequence[Finding]) -> set[str]:
    """The produced outputs the producer's findings already report as having no picture
    to draw, by name: the folder above each record they lie in."""
    return {
        PurePosixPath(finding.file).parent.name
        for finding in produced
        if finding.code in _UNMADE and finding.file.endswith("/record.yaml")
    }


def _said(finding: Finding, unmade: set[str]) -> bool:
    """Whether a scene finding only repeats what a producer's finding says: a picture the
    scene could not draw, of an output already reported as having none (one owner per
    finding, DEC-002 point 6)."""
    return finding.code == "missing-picture" and any(
        f"`{output}`" in finding.message for output in unmade
    )


def _code_findings(root: Path, location_path: str) -> list[Finding]:
    """The findings on written code (DEC-006 points 4 and 8): a missing record, a record
    naming a missing file, stale code. The code writer's module owns them
    (`code.findings`)."""
    return code.findings(root, location_path)


# --- the lock -----------------------------------------------------------------------------------


def lock_findings(held: Held, piece: pl.Piece) -> list[Finding]:
    """What is wrong with a piece's lock as its file holds it (DEC-003 point 9)."""
    file = piece.file(pl.PIECE_FILE)
    if piece.pinned:
        fix = "change the lock by hand, or unpin the piece and run " + pl.render_command(piece.name)
    else:
        fix = f"run {pl.render_command(piece.name)}, which moves a draft's lock"

    def fails(code: str, message: str) -> Finding:
        return Finding(code, FAILS, message, file=file, where="lock", fix=fix)

    lock = piece.lock
    if not lock:
        return [fails("lock-missing", "the piece has no lock yet, so its scenes cannot be drawn")]
    found = []
    read = {}
    for name, text in sorted(lock.items()):
        try:
            version = Version.parse(text)
        except ValueError:
            found.append(
                fails("lock-version", f"the lock names `{name}: {text}`, which is no version")
            )
            continue
        if version not in held.folders.get(name, {}):
            found.append(
                fails(
                    "lock-not-held",
                    f"the lock names {name}@{text}, which the project does not hold",
                )
            )
            continue
        why = held.unreadable(name, version)
        if why is not None:
            found.append(fails("lock-unreadable", f"the lock names {name}@{text}: {why}"))
            continue
        read[name] = held.library(name, version)
    for name in pl.needed(piece):
        if name not in lock:
            found.append(
                fails("lock-incomplete", f"the lock does not name `{name}`, which the piece uses")
            )
    for library in read.values():
        for need in library.builds_on:
            if need.name not in lock:
                found.append(
                    fails(
                        "lock-incomplete",
                        f"{library.label} builds on `{need.name}`, which the lock does not name",
                    )
                )
                continue
            try:
                major = Version.parse(lock[need.name]).major
            except ValueError:
                continue
            if major != need.major:
                found.append(
                    fails(
                        "lock-majors",
                        f"{library.label} builds on `{need.name}` {need.major}, but the lock "
                        f"names {need.name}@{lock[need.name]}: a piece locks one version of each "
                        f"library",
                    )
                )
    return found


# --- content ------------------------------------------------------------------------------------


def id_findings(piece: pl.Piece) -> list[Finding]:
    """The ids of a piece's content (DEC-002 point 4): each of the id shape, unique in its
    list, and the same in every language."""
    found: list[Finding] = []
    lists: dict[str, dict[str, list[Any]]] = {}
    for language, content in piece.contents.items():
        file = piece.file(pl.content_file(language))
        for path, items in _lists(content, ""):
            ids = [item.get("id") for item in items if isinstance(item, Mapping) and "id" in item]
            lists.setdefault(path, {})[language] = ids
            for item in ids:
                if not names.is_id(item):
                    found.append(
                        Finding(
                            "id-shape",
                            FAILS,
                            f"`{item}` is not an id: a letter, then letters, digits, `-` and "
                            f"`_`, and no word YAML reads as a yes-or-no",
                            file=file,
                            where=path,
                        )
                    )
            twice = sorted({str(item) for item in ids if ids.count(item) > 1})
            if twice:
                found.append(
                    Finding(
                        "id-twice",
                        FAILS,
                        f"the ids {', '.join(f'`{item}`' for item in twice)} appear twice in "
                        f"one list: an id is unique in its list",
                        file=file,
                        where=path,
                    )
                )
    source = piece.languages[0]
    for path, by_language in lists.items():
        expected = by_language.get(source, [])
        for language, ids in by_language.items():
            if ids != expected:
                found.append(
                    Finding(
                        "id-languages",
                        FAILS,
                        f"`{path}` holds the ids {ids} in `{language}` and {expected} in "
                        f"`{source}`: an item keeps its id in every language",
                        file=piece.file(pl.content_file(language)),
                        where=path,
                    )
                )
    return found


def _lists(value: Any, path: str) -> Iterator[tuple[str, list[Any]]]:
    """Each list of a content value, by a path of keys and places that is the same in
    every language."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from _lists(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        yield path, value
        for index, item in enumerate(value, start=1):
            yield from _lists(item, f"{path}#{index}")


def content_findings(project: pl.Project) -> list[Finding]:
    """Each content file against the components it fills (DEC-001 point 3, DEC-002 point
    4): a key no component declares as a field or an option, a required field missing, a
    value of another type, a word an option does not take; the nearest known key or word
    named."""
    found: list[Finding] = []
    piece = project.piece
    for language, content in piece.contents.items():
        reader = _Fields(project.env, piece.file(pl.content_file(language)), found)
        reader.placed(piece.top, content, "")
    return found


class _Fields:
    """Reads content against the `fields` of the components it fills: the fixed subset of
    JSON Schema format 1 takes (`type`, `properties`, `required`, `items`, `minItems`,
    `maxItems`, `enum`, `const`, a local `$ref`), a key no property names refused."""

    def __init__(self, env: pl.ProjectEnv, file: str, found: list[Finding]) -> None:
        self.env = env
        self.file = file
        self.found = found

    def _fail(self, code: str, path: str, message: str) -> None:
        self.found.append(Finding(code, FAILS, message, file=self.file, where=path))

    def placed(self, use: str, value: Mapping[str, Any], path: str) -> None:
        """A mapping that places the component `use`."""
        try:
            component = self.env.component(use)
        except KeyError:
            return  # the scene reports a component that does not exist
        fields = component.get("fields") if isinstance(component.get("fields"), Mapping) else {}
        options = component.get("options") if isinstance(component.get("options"), Mapping) else {}
        repeats = {
            spec["repeat"]: spec.get("draw")
            for spec in (component.get("parts") or {}).values()
            if isinstance(spec, Mapping) and isinstance(spec.get("repeat"), str)
        }
        known = {*(fields.get("properties") or {}), *options, *names.RESERVED_PLACING_KEYS}
        self._keys(value, known, path, f"`{use}` takes no field or option")
        for name, option in options.items():
            if name in value and isinstance(option, list) and value[name] not in option:
                close = nearest(str(value[name]), [str(word) for word in option])
                hint = f"; did you mean `{close}`?" if close else ""
                self._fail(
                    "content-option",
                    _join(path, name),
                    f"`{value[name]}` is no word of the option `{name}` of `{use}` "
                    f"({', '.join(map(str, option))}){hint}",
                )
        self._object(fields, value, path, fields, repeats, keys_checked=True)

    def _keys(self, value: Mapping[str, Any], known: set[str], path: str, lead: str) -> None:
        for key in value:
            if key not in known:
                close = nearest(str(key), sorted(known - set(names.RESERVED_PLACING_KEYS)))
                hint = f"; did you mean `{close}`?" if close else ""
                self._fail("content-key", _join(path, str(key)), f"{lead} `{key}`{hint}")

    def _object(
        self,
        schema: Mapping[str, Any],
        value: Mapping[str, Any],
        path: str,
        root: Mapping[str, Any],
        repeats: Mapping[str, Any] | None = None,
        *,
        keys_checked: bool = False,
    ) -> None:
        properties = schema.get("properties") or {}
        if not keys_checked:
            self._keys(value, set(properties), path, "no field is named")
        for key in schema.get("required") or []:
            if key not in value:
                self._fail("content-required", _join(path, key), f"the field `{key}` is required")
        for key, item in value.items():
            if key not in properties:
                continue
            at = _join(path, key)
            draw = (repeats or {}).get(key)
            if draw is not None and isinstance(item, list):
                self._value(properties[key], item, at, root, items=False)
                for place, entry in enumerate(item, start=1):
                    if isinstance(entry, Mapping):
                        use = entry.get("use", draw)
                        if isinstance(use, str):
                            self.placed(use, entry, f"{at}{_item(entry, place)}")
            elif isinstance(item, Mapping) and isinstance(item.get("use"), str):
                self.placed(item["use"], item, at)
            else:
                self._value(properties[key], item, at, root)

    def _value(
        self, schema: Any, value: Any, path: str, root: Mapping[str, Any], *, items: bool = True
    ) -> None:
        schema = _resolved(schema, root)
        if not isinstance(schema, Mapping):
            return
        wanted = schema.get("type")
        if wanted is not None and not any(_is_type(value, t) for t in _as_list(wanted)):
            self._fail(
                "content-type",
                path,
                f"the field holds {_type_name(value)}, not {' or '.join(_as_list(wanted))}",
            )
            return
        if "enum" in schema and value not in schema["enum"]:
            self._fail("content-value", path, f"`{value}` is not one of {schema['enum']}")
        if "const" in schema and value != schema["const"]:
            self._fail("content-value", path, f"`{value}` is not `{schema['const']}`")
        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0):
                self._fail(
                    "content-count",
                    path,
                    f"the list holds {len(value)} item(s), fewer than {schema['minItems']}",
                )
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                self._fail(
                    "content-count",
                    path,
                    f"the list holds {len(value)} item(s), more than {schema['maxItems']}",
                )
            if items and "items" in schema:
                for place, entry in enumerate(value, start=1):
                    self._value(schema["items"], entry, f"{path}{_item(entry, place)}", root)
        elif isinstance(value, Mapping) and (
            "properties" in schema or schema.get("type") == "object"
        ):
            self._object(schema, value, path, root)


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _item(entry: Any, place: int) -> str:
    """An item's step in a path, as a trace id writes it: by its id, else its place."""
    if isinstance(entry, Mapping) and names.is_id(entry.get("id")):
        return f"[{entry['id']}]"
    return f"#{place}"


def _as_list(value: Any) -> list[str]:
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def _is_type(value: Any, wanted: str) -> bool:
    if wanted == "object":
        return isinstance(value, Mapping)
    if wanted == "array":
        return isinstance(value, list)
    if wanted == "string":
        return isinstance(value, str)
    if wanted == "boolean":
        return isinstance(value, bool)
    if wanted == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if wanted == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if wanted == "null":
        return value is None
    return True


def _type_name(value: Any) -> str:
    for wanted in ("object", "array", "string", "boolean", "integer", "number", "null"):
        if _is_type(value, wanted):
            return f"a{'n' if wanted[0] in 'aeiou' else ''} {wanted}"
    return type(value).__name__


def _resolved(schema: Any, root: Mapping[str, Any]) -> Any:
    """`schema`, its local `$ref` (`#/...`) followed within the component's fields."""
    seen = 0
    while isinstance(schema, Mapping) and isinstance(schema.get("$ref"), str) and seen < 16:
        ref: str = schema["$ref"]
        if not ref.startswith("#"):
            return None
        target: Any = root
        for part in [p for p in ref[1:].split("/") if p]:
            part = part.replace("~1", "/").replace("~0", "~")
            target = target.get(part) if isinstance(target, Mapping) else None
        schema, seen = target, seen + 1
    return schema


# --- the findings record ------------------------------------------------------------------------


def read_findings_record(root: Path, held: Held, piece: pl.Piece) -> list[Finding] | None:
    """The findings a piece's `findings.yaml` keeps, while its key verifies against the
    current files; None when it is missing, cannot be read, or does not verify."""
    path = piece.folder / pl.FINDINGS_FILE
    if not path.is_file():
        return None
    try:
        data = read_bound(path, "findings")
        key = data["key"]
        sources = pl.findings_key_sources(
            root, held, piece, piece.lock, pl.recorded_fonts(root, piece.location, key)
        )
        if fingerprint.verify(key, "findings-key", **sources):
            return None
        return [_stored(entry) for entry in data["findings"]]
    except (ReadError, FileError, KeyError, TypeError, ValueError, AttributeError):
        return None


def _stored(entry: Mapping[str, Any]) -> Finding:
    return Finding(
        str(entry["code"]),
        str(entry["level"]),
        str(entry["message"]),
        file=str(entry.get("file", "")),
        where=str(entry.get("where", "")),
        fix=str(entry.get("fix", "")),
        library=str(entry.get("library", "")),
        who=str(entry.get("who", "")),
    )


def record_entry(finding: Finding) -> dict[str, Any]:
    """A scene finding as the findings record keeps it."""
    entry: dict[str, Any] = {
        "code": finding.code,
        "level": finding.level,
        "message": finding.message,
    }
    if finding.file:
        entry["file"] = finding.file
    entry["where"] = finding.where
    for name in ("fix", "library", "who"):
        if getattr(finding, name):
            entry[name] = getattr(finding, name)
    return entry


def rooted(finding: Finding, piece: pl.Piece) -> Finding:
    """A scene finding with its file relative to the project root: from a library
    version's folder where it lies in one, else from the piece's folder."""
    name, _, version = finding.library.partition("@")
    if version:
        base = f"{piece.location}/{FOLDER}/{name}/{version}"
        file = f"{base}/{finding.file}" if finding.file else base
    else:
        file = piece.file(finding.file)
    return dataclasses.replace(finding, file=file)


# --- scene findings -----------------------------------------------------------------------------


def computed(project: pl.Project) -> list[Finding]:
    """The scene findings of a piece, its scenes computed now; a font that refuses the
    render is one."""
    try:
        results = project.scenes()
    except MissingFont as exc:
        return [
            Finding(
                "font-missing",
                FAILS,
                f"the render is refused before anything is laid out: {exc}",
                file=pl.PIECE_FILE,
                where="brand",
                fix="commit the font's file and name it in the brand, or name another family",
            )
        ]
    return scene_findings(project, results)


def scene_findings(
    project: pl.Project, results: Sequence[tuple[str, SceneResult]]
) -> list[Finding]:
    """What computing a piece's scenes found, each finding once, in a fixed order; files
    relative to the piece's folder, or to a library version's folder where the finding
    lies in one (the findings record keeps them so)."""
    piece = project.piece
    document = project.values()
    colours = {
        path: token["values"]
        for path, token in document["tokens"].items()
        if token["type"] == "color"
    }
    found: list[Finding] = []
    for language, result in results:
        content = pl.content_file(language)
        found.extend(
            _placed(finding, content, project, result.scene) for finding in result.findings
        )
        scene = result.scene.to_dict()
        found.extend(drawn_contrast(scene, colours, project.keys))
        found.extend(_unknown_colours(scene, colours))
        for renderer in RENDERERS:
            declared = seam.declaration(renderer, seam.RENDERER)
            for loss in losses(scene, declared):
                if not accepted(loss, piece.accepted_losses):
                    found.append(loss_finding(loss))
        found.extend(_statuses(scene, project.env))
    unique = {}
    for finding in found:
        unique.setdefault(
            (finding.code, finding.file, finding.where, finding.message, finding.library), finding
        )
    return sorted(unique.values(), key=lambda f: (f.file, f.where, f.code, f.message))


def _placed(finding: Finding, content: str, project: pl.Project, scene: Scene) -> Finding:
    """An engine finding placed in its file: a library's component where it lies in one,
    else the content file; a missing picture with why, and the command that makes it. The
    component is the one the finding names, or else the one drawn at its trace."""
    name, _, version = finding.library.partition("@")
    if not version:
        finding = dataclasses.replace(finding, library="", file=content)
    else:
        component = str(finding.extra.get("component") or _drawn_at(scene, finding.where))
        library, _, part = component.partition("/")
        file = f"{pl.COMPONENTS}/{part}.yaml" if library == name and part else ""
        finding = dataclasses.replace(finding, file=file)
    if finding.code == "missing-picture":
        for output, why in project.env.missing.items():
            if f"`{output}`" in finding.message:
                return dataclasses.replace(
                    finding,
                    message=f"{finding.message}: {why}",
                    fix=f"run {pl.produce_command(project.piece.name, output)}",
                )
    return finding


def _drawn_at(scene: Scene, trace: str) -> str:
    """The component drawn at `trace` in a scene; empty where no group lies there."""
    element = scene.find(trace)
    if element is None:
        return ""
    return str(element.properties.get("component") or "")


def _walk(
    elements: Sequence[Mapping[str, Any]], x: float = 0.0, y: float = 0.0
) -> Iterator[tuple[Mapping[str, Any], float, float]]:
    """Each element in draw order, with the place of its parent's origin."""
    for element in elements:
        yield element, x, y
        if element.get("type") == "group":
            yield from _walk(
                element.get("children", []),
                x + float(element.get("x", 0)),
                y + float(element.get("y", 0)),
            )


def _pages(scene: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    wanted = set(scene.get("pages", []))
    for element, _, _ in _walk(scene.get("children", [])):
        if element.get("id") in wanted:
            yield element


def drawn_contrast(
    scene: Mapping[str, Any], colours: Mapping[str, Mapping[str, Any]], keys: Sequence[str]
) -> list[Finding]:
    """Each text of a scene measured against the fill under it, in each combination
    `keys` names, at WCAG's level for its size (DEC-004 point 8). The fill under a line is
    that of the last box or ellipse drawn before the text that holds the line's middle; a
    translucent one is laid over the one under it. A text over a picture is not measured,
    nor one with nothing under it."""
    found = []
    for page in _pages(scene):
        painted: list[tuple[Mapping[str, Any], float, float]] = []
        for element, x, y in _walk(page.get("children", [])):
            kind = element.get("type")
            if kind in ("box", "ellipse", "image"):
                painted.append((element, x, y))
            elif kind == "text" and element.get("lines"):
                found.extend(_text_contrast(element, x, y, painted, colours, keys))
    return found


def _text_contrast(
    text: Mapping[str, Any],
    x: float,
    y: float,
    painted: Sequence[tuple[Mapping[str, Any], float, float]],
    colours: Mapping[str, Mapping[str, Any]],
    keys: Sequence[str],
) -> list[Finding]:
    role = text.get("fill")
    if role is not None and role not in colours:
        return []  # a colour role the brand lacks is a finding of its own
    size, weight = float(text["font-size"]), text.get("font-weight")
    bold = isinstance(weight, (int, float)) and weight >= BOLD
    level = "large-text" if size >= LARGE or (size >= LARGE_BOLD and bold) else "text"
    minimum = tokens.LEVELS[level]
    left, width = x + float(text["x"]), float(text["width"])
    step = float(text["line-height"])
    unders: list[list[str]] = []
    for index, line in enumerate(text["lines"]):
        drawn = float(line.get("width", 0))
        start = {"middle": left + (width - drawn) / 2, "end": left + width - drawn}.get(
            str(text.get("text-anchor")), left
        )
        middle = (start + drawn / 2, y + float(text["y"]) + index * step + step / 2)
        stack = _under(middle, painted)
        if stack is None:
            return []  # over a picture: a reviewer judges it
        if stack and stack not in unders:
            unders.append(stack)
    found = []
    for stack in unders:
        if any(fill not in colours for fill in stack):
            continue
        for key in keys:
            ground = _ground([colours[fill][key] for fill in stack])
            if ground is None:
                continue
            ink = colours[role][key] if role is not None else BLACK
            ratio = tokens.contrast_ratio(ink, ground)
            if ratio < minimum:
                found.append(
                    Finding(
                        "contrast-drawn",
                        FAILS,
                        f"`{role or 'black'}` on `{stack[-1]}` has the contrast {ratio:.2f} in "
                        f"the combination `{key}`, below the {minimum} a text of {size:g} px "
                        f"needs (`{level}`)",
                        file=pl.PIECE_FILE,
                        where=str(text["id"]),
                        fix="change the colour roles of the text or of what lies under it, in "
                        "the component, its content's `override`, or the brand",
                    )
                )
    return found


def _under(
    point: tuple[float, float], painted: Sequence[tuple[Mapping[str, Any], float, float]]
) -> list[str] | None:
    """The fills under a point, bottom first, down to the first opaque one; None when a
    picture lies over it. Translucent fills are judged in `_ground`."""
    stack: list[str] = []
    for element, x, y in reversed(painted):
        if not _holds(element, x, y, point):
            continue
        if element.get("type") == "image":
            return stack or None
        fill = element.get("fill")
        if fill is None:
            continue
        stack.insert(0, str(fill))
        if len(stack) > 8:
            break
    return stack


def _ground(stack: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    """The colour a stack of fills shows, bottom first; None when nothing opaque lies under
    a translucent one."""
    ground: Mapping[str, Any] | None = None
    for fill in stack:
        alpha = float(fill.get("alpha", 1))
        if alpha >= 1:
            ground = fill
        elif ground is not None:
            ground = {
                "colorSpace": "srgb",
                "components": [
                    f * alpha + g * (1 - alpha)
                    for f, g in zip(fill["components"], ground["components"], strict=True)
                ],
                "alpha": 1,
            }
    return ground


def _holds(element: Mapping[str, Any], x: float, y: float, point: tuple[float, float]) -> bool:
    left, top = x + float(element.get("x", 0)), y + float(element.get("y", 0))
    width, height = float(element.get("width", 0)), float(element.get("height", 0))
    px, py = point
    if element.get("type") == "ellipse":
        if width <= 0 or height <= 0:
            return False
        dx = (px - left - width / 2) / (width / 2)
        dy = (py - top - height / 2) / (height / 2)
        return dx * dx + dy * dy <= 1
    return left <= px <= left + width and top <= py <= top + height


def _unknown_colours(
    scene: Mapping[str, Any], colours: Mapping[str, Mapping[str, Any]]
) -> list[Finding]:
    found = []
    for element, _, _ in _walk(scene.get("children", [])):
        for prop in ("fill", "stroke"):
            role = element.get(prop)
            if role is not None and role not in colours:
                found.append(
                    Finding(
                        "unknown-colour",
                        FAILS,
                        f"paints its {prop} with `{role}`, which is no colour role of the brand",
                        file=pl.PIECE_FILE,
                        where=str(element.get("id")),
                        fix="name a colour role the brand gives a value, in the component or "
                        "its content's `override`",
                    )
                )
    return found


def _statuses(scene: Mapping[str, Any], env: pl.ProjectEnv) -> list[Finding]:
    """A fact for each experimental component the piece uses, and a call for attention for
    each deprecated one (DEC-003 point 9)."""
    found = []
    seen: set[str] = set()
    for element, _, _ in _walk(scene.get("children", [])):
        use = element.get("component")
        if not isinstance(use, str) or use in seen:
            continue
        seen.add(use)
        try:
            status = env.component(use).get("status")
        except KeyError:
            continue
        if status == "experimental":
            found.append(
                Finding(
                    "component-experimental",
                    FACT,
                    f"the piece uses `{use}`, which is experimental: its library may still "
                    f"change it in any release",
                    file=pl.PIECE_FILE,
                    where=str(element["id"]),
                )
            )
        elif status == "deprecated":
            found.append(
                Finding(
                    "component-deprecated",
                    ATTENTION,
                    f"the piece uses `{use}`, which is deprecated",
                    file=pl.PIECE_FILE,
                    where=str(element["id"]),
                    fix="replace it with the component its library names in its place",
                    who="the piece's author",
                )
            )
    return found


# --- losses -------------------------------------------------------------------------------------


def losses(scene: Mapping[str, Any], declaration: Mapping[str, Any]) -> list[seam.Loss]:
    """What a renderer will lose of a scene, known from its declaration before it runs
    (DEC-005 point 9): a primitive it does not draw it refuses, and a property it does not
    draw it leaves out."""
    plugin = str(declaration["name"])
    draws: Mapping[str, Mapping[str, Any]] = declaration.get("draws", {})
    found: list[seam.Loss] = []
    for element, _, _ in _walk(scene.get("children", [])):
        kind, what = str(element.get("type")), str(element.get("id"))
        if kind not in draws:
            found.append(
                seam.Loss(plugin, what, seam.REFUSED, f"the {plugin} renderer draws no `{kind}`")
            )
            continue
        for prop in element:
            if prop not in _STRUCTURE and prop not in draws[kind]:
                found.append(
                    seam.Loss(
                        plugin,
                        what,
                        seam.LEFT_OUT,
                        f"the {plugin} renderer draws no `{prop}` of a {kind}",
                    )
                )
    return found


def accepted(loss: seam.Loss, accepting: Sequence[Mapping[str, Any]]) -> bool:
    """Whether the piece accepts a loss: an entry of its `accept-losses` names the plugin
    and what it loses."""
    return any(
        entry.get("plugin") == loss.plugin and entry.get("what") == loss.what for entry in accepting
    )


def loss_finding(loss: seam.Loss) -> Finding:
    """A loss nobody accepted, which asks the piece's author for attention (DEC-005
    point 14)."""
    return Finding(
        "loss",
        ATTENTION,
        f"the {loss.plugin} renderer {_DID[loss.did]} `{loss.what}`: {loss.why}",
        file=pl.PIECE_FILE,
        where=loss.what,
        fix=f"accept it under `accept-losses` with `plugin: {loss.plugin}`, `what: {loss.what}` "
        f"and a reason, or change what draws it",
        who="the piece's author",
    )


# --- the validator's document -------------------------------------------------------------------


def document(report: Report) -> dict[str, Any]:
    """The findings document `pkit validate` reads (COR-055 point 3)."""
    return {
        "summary": list(report.summary),
        "findings": [
            {
                "severity": SEVERITY[level],
                "location": place(finding),
                "message": said(finding),
                "label": finding.code,
            }
            for finding, level in report.judged
        ],
    }


def place(finding: Finding) -> str:
    """Where a finding lies: its file, and what within it after `#`."""
    return f"{finding.file}#{finding.where}" if finding.where else finding.file or "."


def said(finding: Finding) -> str:
    """A finding's message, with who is to act and what mends it."""
    parts = [finding.message]
    if finding.who:
        parts.append(f"for {finding.who}")
    if finding.fix:
        parts.append(finding.fix)
    return " — ".join(parts)
