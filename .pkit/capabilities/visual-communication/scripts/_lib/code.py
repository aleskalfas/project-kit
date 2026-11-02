"""Written code: a brand written out by a code writer, as the project's declaration asks
(visual-communication DEC-002 point 1, DEC-005 points 7 to 9, DEC-006 points 4, 5 and 8).

- **The declaration** is `code/<name>.yaml` in the location (format `code`): the code
  writer, the form of its spelling, the brand, a lock of the brand and what it builds on,
  where the code goes (`out`), and optionally a `prefix` and the losses a person
  accepted. Its name is the file's name.
- **Where the code goes.** `out` is a file of the project's tree. It is refused outside
  the repository, under `.pkit/`, under a hidden folder, reached through a link, as a
  folder, in the location's library folder, whose copies no command writes (DEC-002 point
  9), and in its folder of declarations, where the record would read as one. Its record
  lies beside it, `<out>.record.yaml` (format `code-record`). The CRLF line endings a
  checkout may give the code are read as the LF it was written with, by the check and by a
  run alike (`as_written`), so a run leaves such code as it is.
- **The lock is the declaration's,** which a person moves on purpose (DEC-005 point 7).
  The command reads the brand at the versions it names, and never moves it.
- **A run** resolves every token the brand exports in every combination of its axes
  (the values document, version 1), and knows its losses before the writer runs: each
  token of a type the writer's declaration has no form for is left out, and reported
  unless the declaration accepts it. The writer gets the rest. The command writes the
  code, then its record: the fingerprint, form 1, over the declaration file, each value
  written in each combination, and the writer's version (`fingerprint.code_record_inputs`);
  the hash of the code; and what is only recorded. Where the record verifies and the code
  is what it would write, nothing is written.
- **The findings** (DEC-006 points 4 and 8): a record missing beside the code, or naming
  code that is missing, fails; code stale by a value or by its declaration fails, and so
  does code that differs from what was written; code stale only by its writer's version
  asks for attention, since its values still hold; neither the code nor its record
  present is a fact naming the command. A loss nobody accepted asks for attention (DEC-005
  point 9). A declaration the capability cannot read as one, by its binding or its shape,
  gets no finding here: the check's binding rule and the core's data validation report it.

Reads the location's files; imports a code writer only when it runs.
"""

from __future__ import annotations

import io
import platform
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _lib import fingerprint, libraries, tokens, values
from _lib import location as loc
from _lib.files import (
    FORMAT,
    FileError,
    binding_problem,
    read_bound,
    schema_of,
    shape_problems,
    write_whole,
)
from _lib.findings import ATTENTION, FACT, FAILS, Finding
from _lib.names import is_name
from _lib.plugins import seam
from _lib.reading import ReadError, load_yaml, read_yaml, sha256

#: The folder of the location that holds the declarations, one file each.
FOLDER = "code"

#: What follows `out` in the name of the record beside the code.
RECORD_SUFFIX = ".record.yaml"

#: The library whose `roles.yaml` declares the shared roles and axes a brand gives values.
FOUNDATIONS = "foundations"

#: Who acts on a finding that asks for attention.
WHO = "the project, which keeps the declaration"


class CodeRefused(Exception):
    """Written code that cannot be written or checked; the message says why and what to do."""


@dataclass(frozen=True)
class Declaration:
    """A declaration of written code, as `code/<name>.yaml` gives it.

    - `file`: its path, relative to the project root.
    - `accepted`: each loss a person accepted, as `(plugin, what)`.
    """

    name: str
    file: str
    writer: str
    form: int
    brand: str
    lock: dict[str, str]
    out: str
    prefix: str | None
    accepted: frozenset[tuple[str, str]]

    @property
    def record(self) -> str:
        """The record's path, relative to the project root."""
        return f"{self.out}{RECORD_SUFFIX}"

    @property
    def command(self) -> str:
        return f"pkit visual write-code {self.name}"


@dataclass(frozen=True)
class Plan:
    """What a run of the writer is handed, and what its record compares.

    - `writer`: the code writer's declaration (`seam`).
    - `axes`: each axis of the brand, `{kind, modes, default}`, its modes in declared order.
    - `document`: the values document the writer gets: the tokens it has a form for.
    - `losses`: each token left out, whether a person accepted it or not.
    - `sources`: what the record's input set is worked out from, but the writer.
    """

    declaration: Declaration
    writer: Mapping[str, Any]
    axes: dict[str, dict[str, Any]]
    document: dict[str, Any]
    losses: tuple[seam.Loss, ...]
    sources: dict[str, Any]

    @property
    def unaccepted(self) -> list[seam.Loss]:
        """The losses the declaration does not accept."""
        return [
            loss
            for loss in self.losses
            if (loss.plugin, loss.what) not in self.declaration.accepted
        ]

    @property
    def inputs(self) -> list[fingerprint.Input]:
        """The record's inputs, form 1, with the writer's version now."""
        return fingerprint.code_record_inputs(
            **self.sources, writer=(self.writer["name"], self.writer["version"])
        )


@dataclass(frozen=True)
class Written:
    """What a run wrote: the code's and its record's paths, relative to the project root,
    whether it wrote them or found them up to date, and the losses nobody accepted."""

    code: str
    record: str
    changed: bool
    losses: tuple[seam.Loss, ...]


# --- the declarations ---------------------------------------------------------------------------


def file_of(location: str, name: str) -> str:
    """The declaration `name`'s path, relative to the project root."""
    return f"{location}/{FOLDER}/{name}.yaml"


def names(root: Path, location: str) -> list[str]:
    """The names of the location's declarations, as git sees its files, in name order: each
    YAML file directly in its `code/` folder."""
    prefix = f"{location}/{FOLDER}/"
    found = []
    for rel in loc.files(root, f"{location}/{FOLDER}"):
        rest = rel[len(prefix) :]
        if "/" not in rest and rest.endswith(".yaml"):
            found.append(rest[: -len(".yaml")])
    return sorted(found)


def read(root: Path, location: str, name: str) -> Declaration:
    """The declaration `name`, read and checked as the command needs it: bound to `code`,
    of its schema's shape, and with an `out` the rules allow. Raises CodeRefused."""
    if not is_name(name):
        raise CodeRefused(
            f"`{name}` is not the name of a declaration, which takes lower-case words of "
            f"letters and digits joined by hyphens"
        )
    rel = file_of(location, name)
    path = root / rel
    if not path.is_file():
        raise CodeRefused(
            f"there is no declaration {rel}: write one, naming the writer, the form, the "
            f"brand, its lock and `out`"
        )
    try:
        data = read_bound(path, "code")
    except (ReadError, FileError) as exc:
        raise CodeRefused(str(exc)) from exc
    problems = shape_problems(data, "code")
    if problems:
        raise CodeRefused(
            f"{rel} does not hold the schema `{schema_of('code')}`: " + "; ".join(problems)
        )
    declaration = _parsed(name, rel, data)
    if declaration is None:  # the schema holds every field `_parsed` reads
        raise CodeRefused(f"{rel} cannot be read as a declaration of written code")
    problem = out_problem(root, location, declaration.out)
    if problem is not None:
        raise CodeRefused(f"{rel}: `out: {declaration.out}` {problem}")
    return declaration


def out_problem(root: Path, location: str, out: str) -> str | None:
    """Why the code cannot go to `out`, a path relative to the project root, or None."""
    if out in ("", "."):
        return "names no file"
    found = loc.shape_problem(out)
    if found is not None:
        return found
    for folder, why in (
        (libraries.FOLDER, "lies in the library folder, whose copies no command writes"),
        (FOLDER, "lies in the folder of declarations, where its record would read as one"),
    ):
        inside = f"{location}/{folder}"
        if out == inside or out.startswith(f"{inside}/"):
            return why
    for rel in (out, f"{out}{RECORD_SUFFIX}"):
        target = root / rel
        for path in (target, *target.parents):
            if path == root:
                break
            if path.is_symlink():
                return f"is reached through the link {path.relative_to(root).as_posix()}"
        if target.is_dir():
            return f"is a folder where a file belongs: `{rel}`"
    return None


def _parsed(name: str, rel: str, data: Mapping[str, Any]) -> Declaration | None:
    """The declaration in `data`, or None where a field it needs is not of its shape."""
    writer, form, brand = data.get("writer"), data.get("form"), data.get("brand")
    lock, out, prefix = data.get("lock"), data.get("out"), data.get("prefix")
    if not (
        isinstance(writer, str)
        and isinstance(form, int)
        and not isinstance(form, bool)
        and is_name(brand)
        and isinstance(lock, Mapping)
        and all(isinstance(k, str) and isinstance(v, str) for k, v in lock.items())
        and isinstance(out, str)
        and (prefix is None or is_name(prefix))
    ):
        return None
    accepted = data.get("accept-losses") or []
    if not isinstance(accepted, list):
        return None
    return Declaration(
        name=name,
        file=rel,
        writer=writer,
        form=form,
        brand=str(brand),
        lock=dict(lock),
        out=out,
        prefix=prefix,
        accepted=frozenset(
            (entry["plugin"], entry["what"])
            for entry in accepted
            if isinstance(entry, Mapping) and "plugin" in entry and "what" in entry
        ),
    )


# --- a run --------------------------------------------------------------------------------------


def plan(root: Path, location: str, declaration: Declaration) -> Plan:
    """What the declaration's writer would be handed now, its losses and its record's
    sources: the brand read at the versions the lock names. Raises CodeRefused."""
    try:
        writer = seam.declaration(declaration.writer, seam.CODE_WRITER)
    except seam.PluginError as exc:
        raise CodeRefused(f"{declaration.file}: {exc}") from exc
    if declaration.form not in writer.get("forms", ()):
        forms = ", ".join(str(form) for form in writer.get("forms", ()))
        raise CodeRefused(
            f"{declaration.file}: the {writer['name']} writer {writer['version']} writes "
            f"form {forms}, not form {declaration.form}"
        )
    brand = _brand(root, location, declaration)
    axes = {
        axis.name: {"kind": axis.kind, "modes": list(axis.modes), "default": axis.default}
        for axis in sorted(brand.axes.values(), key=lambda axis: axis.name)
    }
    for name, axis in axes.items():
        if axis["kind"] not in writer.get("axis-kinds", ()):
            raise CodeRefused(
                f"the brand {brand.name} {brand.version} has the {axis['kind']} axis `{name}`, "
                f"which form {declaration.form} of the {writer['name']} writer does not spell"
            )
    document = values.document(brand, brand.combinations(), declaration.lock)
    kinds = writer.get("kinds", ())
    written = {path: token for path, token in document["tokens"].items() if token["type"] in kinds}
    losses = tuple(
        seam.Loss(
            writer["name"],
            path,
            seam.LEFT_OUT,
            f"form {declaration.form} of the {writer['name']} writer has no form for a "
            f"{token['type']} value",
        )
        for path, token in document["tokens"].items()
        if path not in written
    )
    sources = {
        "name": declaration.name,
        "declaration": root / declaration.file,
        "values": {
            (path, key): value
            for path, token in written.items()
            for key, value in token["values"].items()
        },
    }
    return Plan(
        declaration=declaration,
        writer=writer,
        axes=axes,
        document={**document, "tokens": written},
        losses=losses,
        sources=sources,
    )


def write(root: Path, location: str, name: str, *, now: datetime | None = None) -> Written:
    """Write the code the declaration `name` asks for, and its record; or nothing, where
    the record verifies and the code is what the writer writes now. Raises CodeRefused."""
    declaration = read(root, location, name)
    planned = plan(root, location, declaration)
    implementation = seam.implementation(declaration.writer)
    try:
        text = implementation.write(
            planned.document, planned.axes, form=declaration.form, prefix=declaration.prefix
        )
    except ValueError as exc:
        raise CodeRefused(f"the {declaration.writer} writer refused: {exc}") from exc
    data = text.encode("utf-8")
    taken = fingerprint.fingerprint(planned.inputs)
    code, record = root / declaration.out, root / declaration.record
    unaccepted = tuple(planned.unaccepted)
    if _up_to_date(code, record, taken, data):
        return Written(declaration.out, declaration.record, changed=False, losses=unaccepted)
    kept = {
        "pkit_schema": schema_of("code-record"),
        "schema_version": FORMAT,
        "fingerprint": taken,
        "sha256": sha256(data),
        "recorded": {
            "plugins": {planned.writer["name"]: planned.writer["version"]},
            "programs": {},
            "machine": _machine(),
            "time": _time(now),
            "capability": ".".join(map(str, libraries.installed_release())),
        },
    }
    record_text = _record_text(declaration, kept)
    code.parent.mkdir(parents=True, exist_ok=True)
    write_whole(code, data)
    write_whole(record, record_text.encode("utf-8"))
    return Written(declaration.out, declaration.record, changed=True, losses=unaccepted)


def _brand(root: Path, location: str, declaration: Declaration) -> tokens.Brand:
    """The declaration's brand, read at the versions its lock names, against the shared
    roles of the foundations it locks. Raises CodeRefused."""
    held = libraries.Held(root, location)
    reached = _check_lock(held, declaration)
    brand_version = libraries.Version.parse(declaration.lock[declaration.brand])
    if held.library(declaration.brand, brand_version).kind != "brand":
        raise CodeRefused(
            f"{declaration.file}: `brand: {declaration.brand}` names a library that is not a brand"
        )
    if FOUNDATIONS not in reached:
        raise CodeRefused(
            f"{declaration.file}: the brand {declaration.brand} builds on no `{FOUNDATIONS}`, "
            f"which declares the roles it gives values"
        )
    version = libraries.Version.parse(declaration.lock[FOUNDATIONS])
    folder = held.folders[FOUNDATIONS][version]
    try:
        shared = tokens.read_declarations(
            folder / "roles.yaml",
            library=f"{FOUNDATIONS}@{version}",
            shown=(folder / "roles.yaml").relative_to(root).as_posix(),
        )
        return tokens.read_brand(
            held.folders[declaration.brand][brand_version],
            shared,
            fonts=root / location / "fonts",
            root=root,
        )
    except tokens.TokenError as exc:
        raise CodeRefused(
            f"the brand {declaration.brand} {brand_version} cannot be resolved: {exc}"
        ) from exc


def _check_lock(held: libraries.Held, declaration: Declaration) -> set[str]:
    """The libraries the code needs, the brand and every library it builds on, once the
    lock is checked to name each at a version the project holds and the capability reads,
    fitting together. Raises CodeRefused, naming the first fault."""
    lock, file = declaration.lock, declaration.file
    pending, seen = [declaration.brand], set()
    needs: list[tuple[libraries.Library, libraries.BuildsOn]] = []
    while pending:
        name = pending.pop(0)
        if name in seen:
            continue
        seen.add(name)
        if name not in lock:
            raise CodeRefused(
                f"{file}: the lock names no version of `{name}`, which the code needs: add "
                f"it, at the version the code should hold"
            )
        try:
            version = libraries.Version.parse(lock[name])
        except ValueError as exc:
            raise CodeRefused(f"{file}: the lock names `{name}: {lock[name]}`: {exc}") from exc
        if version not in held.folders.get(name, {}):
            raise CodeRefused(
                f"{file}: the lock names {name}@{version}, which the project does not hold: "
                f"bring it in, or move the lock"
            )
        why = held.unreadable(name, version)
        if why is not None:
            raise CodeRefused(
                f"{file}: the lock names {name}@{version}, which cannot be read: {why}"
            )
        library = held.library(name, version)
        for need in library.builds_on:
            needs.append((library, need))
            pending.append(need.name)
    for library, need in needs:
        locked = libraries.Version.parse(lock[need.name])
        if locked.major != need.major:
            raise CodeRefused(
                f"{file}: the lock does not fit: {library.label} builds on `{need.name}` "
                f"{need.major}, but the lock names {need.name}@{locked}"
            )
    return seen


def as_written(code: Path) -> bytes:
    """The code's bytes as the writer wrote them: the CRLF line endings a checkout may give
    it read as LF. The check and a run compare the code so."""
    return code.read_bytes().replace(b"\r\n", b"\n")


def _up_to_date(code: Path, record: Path, taken: Mapping[str, Any], data: bytes) -> bool:
    """Whether the record beside the code holds the fingerprint just taken and the hash of
    `data`, and the code, read as written (`as_written`), is `data`."""
    if not (code.is_file() and record.is_file()):
        return False
    try:
        kept = read_yaml(record)
    except ReadError:
        return False
    return (
        isinstance(kept, Mapping)
        and binding_problem(kept, "code-record") is None
        and kept.get("fingerprint") == taken
        and kept.get("sha256") == sha256(data)
        and as_written(code) == data
    )


def _record_text(declaration: Declaration, record: Mapping[str, Any]) -> str:
    """The record as YAML, its time quoted, read back to be sure it holds what was meant.
    Raises CodeRefused otherwise."""
    from ruamel.yaml import YAML
    from ruamel.yaml.scalarstring import SingleQuotedScalarString

    shown = {
        **record,
        "recorded": {
            **record["recorded"],
            "time": SingleQuotedScalarString(record["recorded"]["time"]),
        },
    }
    dumper = YAML()
    dumper.indent(mapping=2, sequence=4, offset=2)
    dumper.width = 4096
    stream = io.StringIO()
    dumper.dump(shown, stream)
    text = (
        f"# The record of the code `{declaration.command}` writes to {declaration.out}: "
        f"write it again, never edit it.\n{stream.getvalue()}"
    )
    if load_yaml(text, declaration.record) != record:
        raise CodeRefused(f"the record {declaration.record} does not read back as it was meant")
    return text


def _machine() -> str:
    found = " ".join(part for part in (platform.system().lower(), platform.machine()) if part)
    return found or "unknown"


def _time(now: datetime | None) -> str:
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


# --- the findings -------------------------------------------------------------------------------


def findings(root: Path, location: str) -> list[Finding]:
    """What the check finds about the written code the location's declarations ask for
    (DEC-006 points 4 and 8, DEC-005 point 9), declaration by declaration."""
    found: list[Finding] = []
    for name in names(root, location):
        found.extend(_findings_of(root, location, name))
    return found


def _findings_of(root: Path, location: str, name: str) -> list[Finding]:
    rel = file_of(location, name)
    if not is_name(name):
        return [
            Finding(
                "code-name",
                FAILS,
                f"`{name}` is not the name of a declaration, which takes lower-case words of "
                f"letters and digits joined by hyphens",
                file=rel,
                fix="rename the file",
            )
        ]
    try:
        data = read_yaml(root / rel)
    except ReadError:
        return []
    if binding_problem(data, "code") is not None:
        return []
    declaration = _parsed(name, rel, data)
    if declaration is None:
        return []
    problem = out_problem(root, location, declaration.out)
    if problem is not None:
        return [
            Finding(
                "code-out",
                FAILS,
                f"`out: {declaration.out}` {problem}",
                file=rel,
                where="out",
                fix="name a file of the project's tree in `out`",
            )
        ]
    try:
        planned = plan(root, location, declaration)
    except CodeRefused as exc:
        return [
            Finding(
                "code-unchecked",
                FAILS,
                f"the code `{name}` declares cannot be checked: {exc}",
                file=rel,
                fix=f"mend the declaration, then run `{declaration.command}`",
            )
        ]
    return [*_losses(planned), *_written(root, planned)]


def _losses(planned: Plan) -> list[Finding]:
    declaration = planned.declaration
    return [
        Finding(
            "code-loss",
            ATTENTION,
            f"the code `{declaration.name}` leaves out `{loss.what}`: {loss.why}",
            file=declaration.file,
            where=loss.what,
            fix=(
                f"accept the loss under `accept-losses` (plugin `{loss.plugin}`, what "
                f"`{loss.what}`, and why), or have the code read the value another way"
            ),
            who=WHO,
        )
        for loss in planned.unaccepted
    ]


def _written(root: Path, planned: Plan) -> list[Finding]:
    """The findings on the code and its record."""
    declaration = planned.declaration
    fix = f"run `{declaration.command}`"
    code, record = root / declaration.out, root / declaration.record
    if not code.is_file() and not record.is_file():
        return [
            Finding(
                "code-not-written",
                FACT,
                f"the code `{declaration.name}` declares is not written here: neither "
                f"{declaration.out} nor its record is present",
                file=declaration.file,
                fix=fix,
            )
        ]
    if not record.is_file():
        return [
            Finding(
                "code-record-missing",
                FAILS,
                f"{declaration.out} has no record beside it, so nothing says what it was "
                f"written from",
                file=declaration.out,
                fix=fix,
            )
        ]
    if not code.is_file():
        return [
            Finding(
                "code-missing",
                FAILS,
                f"the record {declaration.record} names {declaration.out}, which is missing",
                file=declaration.record,
                fix=fix,
            )
        ]
    kept, problem = _record(record)
    if kept is None:
        return [
            Finding(
                "code-record-unreadable",
                FAILS,
                f"the record {declaration.record} {problem}",
                file=declaration.record,
                fix=fix,
            )
        ]
    found = []
    if sha256(as_written(code)) != kept["sha256"]:
        found.append(
            Finding(
                "code-edited",
                FAILS,
                f"{declaration.out} is not the code its record says was written: it was "
                f"edited, or written by something else",
                file=declaration.out,
                fix=f"{fix}, which writes it again; change the brand or the declaration instead",
            )
        )
    return found + _staleness(planned, kept["fingerprint"])


def _record(path: Path) -> tuple[dict[str, Any] | None, str]:
    """The record at `path` with a fingerprint and a hash, or None and why not."""
    try:
        data = read_yaml(path)
    except ReadError as exc:
        return None, f"cannot be read: {exc}"
    problem = binding_problem(data, "code-record")
    if problem is not None:
        return None, problem
    if not isinstance(data.get("fingerprint"), Mapping) or not isinstance(data.get("sha256"), str):
        return None, "keeps no fingerprint and hash of the code"
    return dict(data), ""


def _staleness(planned: Plan, recorded: Mapping[str, Any]) -> list[Finding]:
    """Stale by a value or the declaration fails; stale by the writer's version alone asks
    for attention. The record is verified under the form it names."""
    declaration = planned.declaration
    writer = planned.writer["name"]
    sources = planned.sources
    changes = fingerprint.verify(
        recorded, "code-record", **sources, writer=(writer, planned.writer["version"])
    )
    if not changes:
        return []
    fix = f"run `{declaration.command}`"
    then = _recorded_version(recorded, writer)
    if then is not None and not fingerprint.verify(
        recorded, "code-record", **sources, writer=(writer, then)
    ):
        return [
            Finding(
                "code-stale-writer",
                ATTENTION,
                f"{declaration.out} was written by the {writer} writer {then}, and "
                f"{planned.writer['version']} is installed; its values still hold",
                file=declaration.record,
                fix=fix,
                who=WHO,
            )
        ]
    return [
        Finding(
            "code-stale",
            FAILS,
            f"{declaration.out} is stale: " + "; ".join(changes),
            file=declaration.record,
            fix=fix,
        )
    ]


def _recorded_version(recorded: Mapping[str, Any], writer: str) -> str | None:
    """The writer's version the fingerprint names, or None."""
    entries = recorded.get("inputs")
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, Mapping) and entry.get("plugin") == writer:
            version = entry.get("version")
            return version if isinstance(version, str) else None
    return None
