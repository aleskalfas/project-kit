"""The framing of a producer's run, and what the check reports of its picture
(visual-communication DEC-006 points 1 to 5 and 8, DEC-005 points 5, 7 and 9).

A *producer* is a plugin of the capability that makes a picture while a piece is prepared.
The engine never runs it: a person or an agent runs `pkit visual produce <piece> <output>`,
and this module frames that run, step by step, so a later command that frames a project's
own script reuses the same steps. A final piece takes no such run (DEC-017 point 3): making
its pictures again would change it. `produce` refuses it, and `plan`, which an export and
the check read too, does not.

1. **The declaration.** `piece.yaml` declares each produced output under
   `produced.<output>`: the producer, its inputs, each naming a role by its token path,
   and the pixel size of each variant. The piece's lock says which brand version the
   values come from. A piece with no lock yet is refused: a draft's first render writes
   one, and a final or a published piece is set back to a draft for it.
2. **The values and the variants.** Each role the inputs name is resolved in every
   combination the piece names, and the combinations that give the same values share one
   *variant*, under the first key it serves (DEC-004 point 3, `values.variants`).
3. **The fingerprint before** the run: form 1's input set of a produced record
   (`fingerprint.produced_record_inputs`).
4. **The hand-over**, written to `project/local/handover/<piece>/<output>.json`.
5. **The run,** through the seam, into `project/local/handover/<piece>/<output>/`.
6. **The fingerprint after** the run, which must equal the one before: an input that
   changed during the run would be recorded as one the picture was made from.
7. **The checks:** each variant's file is a PNG of the declared pixel size; every variant
   exposes the same points; the variants one scene holds keep each point at one place;
   each point lies within the pixels.
8. **Only then** are the variants written into the piece's `produced/<output>/<key>.png`,
   then `produced/<output>/record.yaml` (schema `produced-record`), and a variant file
   left from before removed, as one change with the location's record: where a write
   fails, the variants and the record are as they were before the run, or each the run
   could not put back is named. Every check that can refuse, the files it keeps reached
   through a link included, runs before the location is recorded, so a refused run
   writes nothing in the location, and records no location.

**A producer's seam, version 1.** Its declaration is plain data (`seam.register`, or a
shipped `<name>_declaration.py`):

- `name`, `kind: producer`, `version` (`X.Y.Z`, raised when the same hand-over could give
  other pixels), `seam: 1`;
- `inputs`: the JSON Schema of the `inputs` mapping a piece declares, an object with
  `properties`, `required`, `additionalProperties: false`, and `description`. Each
  property marks its input as a role with `x-pkit-role: <DTCG type>`, the type of the role
  it takes. Format 1 reads no other keyword, and every input is a role, so a raw value is
  refused;
- `values`: the kinds of value it uses, as DTCG types (`color`, `dimension`, ...); each
  input's type is one of them;
- `programs`, `services`: what it needs beyond the project's files (DEC-005 point 9), the
  outside programs it calls and the services it reaches, each a list of names; left out,
  none. A run is refused before the producer runs where the machine lacks a program it
  names, or where it names a service, since format 1's configuration turns on no plugin
  that reaches one (DEC-002 point 8).

Its implementation has `produce(handover: dict, out_dir: Path) -> dict`.

- **It receives** the values document, version 1 (`values.document`), holding the roles
  its inputs name alone, under the lock of the brand and what it builds on, with three keys
  added: `inputs` (input -> token path); `variants` (variant key -> `{serves: [combination
  keys], pixels: {width, height}}`); and `frames: {}`, the measured frames it declared
  (none in format 1). A variant's values are those of its own key:
  `tokens[<token path>]["values"][<variant key>]`.
- **It writes** one PNG per variant, `out_dir/<variant key>.png`, at the variant's pixels.
  It writes nothing else that is kept.
- **It returns** `{"points": {<point>: {<variant key>: {"x": <number>, "y": <number>}}},
  "programs": {<outside program>: <its version>}, "losses": [<loss>, ...]}`: each exposed
  point in each variant's pixels, the origin at the top-left corner and y down (the format
  of exposed points, DEC-006 point 2); each outside program it called, one its declaration
  names, which is only recorded; and what it could not make as handed, in the seam's one
  form of loss (`seam.Loss`: `plugin`, its own name; `what`, a trace id or token path;
  `did`, one of `seam.OUTCOMES`; `why`). `programs` and `losses` may be left out; a result
  with any other key is refused, and nothing is kept.

The record keeps the losses. The command prints each one the piece does not accept under
`accept-losses`, and the check reports it, asking the piece's author for attention, as it
does a renderer's (DEC-005 points 9 and 14).

`findings(root, location, piece)` gives what the check reports of a piece's produced
outputs (DEC-006 points 5 and 8): a missing record or variant file fails, a record whose
fingerprint no longer verifies asks for attention, and so on.
"""

from __future__ import annotations

import json
import math
import platform
import shutil
import struct
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _lib import copies, fingerprint, keys, libraries, records, tokens, values
from _lib import location as loc
from _lib.files import (
    FORMAT,
    Change,
    FileError,
    WriteFailed,
    nearest,
    read_bound,
    refuse_links,
    schema_of,
)
from _lib.findings import ATTENTION, FAILS, Finding, accepted, loss_finding
from _lib.libraries import FOUNDATIONS
from _lib.names import is_name, is_token_path
from _lib.plugins import seam
from _lib.reading import ReadError, load_yaml, sha256
from _lib.root import LOCAL

#: The folder of the location that holds the pieces, one folder each.
PIECES = "pieces"

#: The folder of a piece that holds its produced outputs, one folder each.
PRODUCED = "produced"

#: The record beside a produced output's variants.
RECORD = "record.yaml"

#: Where a producer's hand-over and its run's output lie, local to each clone.
HANDOVER = f"{LOCAL}/handover"

#: The location's folder of fonts.
FONTS = "fonts"

#: The keyword that marks a producer's input as a role, with the DTCG type it takes.
ROLE = "x-pkit-role"

#: The commands a finding or a refusal names.
PRODUCE = "pkit visual produce"
RENDER = "pkit visual render"

#: Who acts on a produced output that asks for attention.
AUTHORS = "the piece's authors"

#: The keywords seam 1 reads in a producer's input schema, and in each of its properties.
_SCHEMA_KEYS = ("type", "properties", "required", "additionalProperties", "description")
_PROPERTY_KEYS = ("description", ROLE)

#: What a producer's result may hold.
_RESULT_KEYS = ("points", "programs", "losses")

#: What a producer's declaration may name that it needs beyond the project's files.
_NEEDS = ("programs", "services")

#: The kind of plugin a producer's loss names, in words.
_KIND = "producer"

#: A loss's keys, in the seam's one form (`seam.Loss`).
_LOSS_KEYS = ("plugin", "what", "did", "why")

#: A PNG file's first bytes, and where its header gives the width and the height.
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_SIZE = slice(16, 24)


class Refused(Exception):
    """A producer's run refused, nothing written in the location; the message says why and
    what to do. `declared` marks a fault in the piece's declaration of its output, which
    the check fails; any other lies in what the declaration is read against, such as the
    lock or the brand."""

    def __init__(self, message: str, *, declared: bool = False) -> None:
        super().__init__(message)
        self.declared = declared


@dataclass(frozen=True)
class Declaration:
    """A produced output as `piece.yaml` declares it under `produced.<output>`."""

    output: str
    producer: str
    inputs: dict[str, str]
    width: int
    height: int

    @property
    def pixels(self) -> dict[str, int]:
        return {"width": self.width, "height": self.height}


@dataclass(frozen=True)
class Plan:
    """What a producer's run reads, read once: a snapshot of the files taken before the
    run, and again after it.

    - `piece`, `folder`: the piece's name and folder.
    - `declaration`, `plugin`: the output's declaration and its producer's.
    - `axes`: the brand's axes, which say which combinations one scene holds.
    - `document`: the values document of the roles the inputs name, in every combination
      the piece names.
    - `variants`: each variant's key -> the keys of the combinations it serves.
    - `sources`: what form 1's input set of a produced record is worked out from.
    - `inputs`: that input set, read now.
    - `accepting`: the losses the piece accepts, its `accept-losses`.
    """

    piece: str
    folder: Path
    declaration: Declaration
    plugin: Mapping[str, Any]
    axes: Mapping[str, tokens.Axis]
    document: dict[str, Any]
    variants: dict[str, list[str]]
    sources: dict[str, Any]
    inputs: list[fingerprint.Input]
    accepting: tuple[Mapping[str, Any], ...] = ()

    @property
    def output(self) -> str:
        return self.declaration.output

    @property
    def combinations(self) -> list[str]:
        """The keys of the combinations the piece names, in key order."""
        return list(self.document["keys"])

    def fingerprint(self) -> dict[str, Any]:
        return fingerprint.fingerprint(self.inputs)

    def together(self) -> list[list[str]]:
        """The variants each scene holds."""
        return held_together(self.variants, self.axes)


@dataclass(frozen=True)
class Produced:
    """A run that kept its picture: the plan it ran, the record written, the variant files
    left from before that it removed, what it said when it recorded the location, and what
    the producer lost, each recorded."""

    plan: Plan
    record: Path
    removed: tuple[str, ...]
    location: str | None
    losses: tuple[seam.Loss, ...] = ()

    @property
    def unaccepted(self) -> tuple[seam.Loss, ...]:
        """The losses the piece does not accept, which the command prints."""
        return tuple(loss for loss in self.losses if not accepted(loss, self.plan.accepting))


# --- the run ------------------------------------------------------------------------------------


def produce(root: Path, where: loc.ForWriting, piece: str, output: str) -> Produced:
    """Run the producer a piece declares for `output`, in the location `where`, and keep
    its picture. Raises Refused, writing nothing in the location; loc.LocationRefused when
    the location cannot be recorded; WriteFailed where a write fails, every file in the
    location then as it was before the run, or named."""
    _refuse_final(root, where.path, piece)
    before = plan(root, where.path, piece, output)
    runnable(before)
    handed = handover(before)
    write_handover(root, before, handed)
    out = run_folder(root, before)
    result = run(before, handed, out)
    after = plan(root, where.path, piece, output)
    changed = fingerprint.changes(before.fingerprint(), after.inputs)
    if changed:
        raise Refused(
            f"an input changed while the producer ran, so nothing was kept: {'; '.join(changed)}. "
            f"Run `{PRODUCE} {piece} {output}` again"
        )
    checked = check(before, out, result)
    keepable(root, before)
    change = Change(root)
    said = loc.record(change, where)
    record, removed = keep(root, before, out, checked, change)
    shutil.rmtree(out, ignore_errors=True)
    return Produced(before, record, removed, said, checked.losses)


def _refuse_final(root: Path, location: str, piece: str) -> None:
    """Refuse a piece that is final, before anything else is read of it. Raises Refused."""
    if copies.final(_piece(root, _piece_folder(root, location, piece), piece)):
        raise Refused(
            f"the piece `{piece}` is final, and a final piece takes no producer's run: making "
            f"its pictures again would change it"
        )


def plan(
    root: Path, location: str, piece: str, output: str, held: libraries.Held | None = None
) -> Plan:
    """Read, from the files as they are now, what a run of the producer that the piece
    `piece` declares for `output` reads. The library versions come from `held` where it
    is given, as for a location git ignores, and otherwise as git lists them. Raises
    Refused."""
    folder = _piece_folder(root, location, piece)
    data = _piece(root, folder, piece)
    declaration = _declaration(data, piece, output)
    plugin = producer(declaration.producer)
    lock = data.get("lock")
    if not isinstance(lock, Mapping) or not lock:
        if copies.lock_stays(data):
            raise Refused(
                f"the piece `{piece}` is {data['state']} and has no lock: "
                f"{copies.FIRST_RENDER}, then produce"
            )
        raise Refused(
            f"the piece `{piece}` has no lock yet: run `{RENDER} {piece}` first, which writes "
            f"it, then produce"
        )
    brand, chain = _brand(root, location, piece, data.get("brand"), lock, held)
    _check_inputs(declaration, plugin, brand)
    modes = data.get("modes", {})
    if not isinstance(modes, Mapping):
        raise Refused(f"the `modes` of `{piece}` is not a mapping of axes to their modes")
    try:
        combinations = keys.combinations(modes, brand.axes)
    except keys.BadKey as exc:
        raise Refused(f"the `modes` of `{piece}`: {exc}") from exc
    document = values.document(
        brand, combinations, chain, tokens=sorted(set(declaration.inputs.values()))
    )
    variants = values.variants(document)
    sources: dict[str, Any] = {
        "piece": folder,
        "output": output,
        "values": {
            (path, key): token["values"][key]
            for path, token in document["tokens"].items()
            for key in document["keys"]
        },
        "pixels": {key: (declaration.width, declaration.height) for key in variants},
        "producer": (plugin["name"], plugin["version"]),
    }
    try:
        inputs = fingerprint.produced_record_inputs(**sources)
    except fingerprint.FingerprintError as exc:
        raise Refused(str(exc)) from exc
    return Plan(
        piece=piece,
        folder=folder,
        declaration=declaration,
        plugin=plugin,
        axes=brand.axes,
        document=document,
        variants=variants,
        sources=sources,
        inputs=inputs,
        accepting=tuple(_accepting(data)),
    )


def runnable(plan: Plan) -> None:
    """Refuse, before the producer runs, a run that needs what is not to hand: a service
    it reaches, which format 1's configuration never turns on (DEC-002 point 8), or an
    outside program it calls that this machine lacks. Raises Refused."""
    name, version = plan.plugin["name"], plan.plugin["version"]
    services = plan.plugin.get("services") or []
    if services:
        raise Refused(
            f"the producer `{name}` {version} reaches the service `{'`, `'.join(services)}`, "
            f"and the project's configuration turns on no plugin that reaches a service: "
            f"format 1 takes none, so it cannot run"
        )
    lacking = [
        program for program in plan.plugin.get("programs") or [] if not shutil.which(program)
    ]
    if lacking:
        raise Refused(
            f"the producer `{name}` {version} calls `{'`, `'.join(lacking)}`, which this machine "
            f"lacks: install it, then run `{PRODUCE} {plan.piece} {plan.output}` again"
        )


def handover(plan: Plan) -> dict[str, Any]:
    """What the producer receives: the values document of the roles it reads, with its
    inputs, its variants and the frames it declared."""
    declaration = plan.declaration
    return {
        **plan.document,
        "inputs": dict(sorted(declaration.inputs.items())),
        "variants": {
            key: {"serves": list(served), "pixels": declaration.pixels}
            for key, served in plan.variants.items()
        },
        "frames": {},
    }


def write_handover(root: Path, plan: Plan, handed: Mapping[str, Any]) -> Path:
    """Write the hand-over under the capability's local folder; returns its path. Raises
    WriteFailed where it cannot be written."""
    target = root / HANDOVER / plan.piece / f"{plan.output}.json"
    _refuse_links(root, target)
    text = json.dumps(handed, indent=2, ensure_ascii=False) + "\n"
    change = Change(root)
    change.write(target, text.encode("utf-8"))
    change.commit()
    return target


def run_folder(root: Path, plan: Plan) -> Path:
    """The folder the producer writes into, under the capability's local folder, emptied.
    Raises WriteFailed where it cannot be."""
    out = root / HANDOVER / plan.piece / plan.output
    _refuse_links(root, out)
    try:
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
    except OSError as exc:
        raise WriteFailed(root, out, exc, done="emptied") from exc
    return out


def run(plan: Plan, handed: Mapping[str, Any], out: Path) -> Mapping[str, Any]:
    """Run the producer through the seam into `out`; its result, of the keys seam 1 reads.
    Raises Refused when it fails or returns something else."""
    name, version = plan.plugin["name"], plan.plugin["version"]
    try:
        implementation = seam.implementation(name)
        result = implementation.produce(dict(handed), out)
    except Exception as exc:
        raise Refused(
            f"the producer `{name}` {version} failed, so nothing was kept: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(result, Mapping):
        raise Refused(f"the producer `{name}` {version} returned no mapping of its points")
    unknown = sorted(set(result) - set(_RESULT_KEYS))
    if unknown:
        raise Refused(
            f"the producer `{name}` {version} returned `{'`, `'.join(unknown)}`, which seam "
            f"{seam.SEAM_VERSION} does not read"
        )
    return result


@dataclass(frozen=True)
class Checked:
    """A producer's result that passed every check: each variant's hash, its points, the
    outside programs it called, and what it lost, each once."""

    digests: dict[str, str]
    points: dict[str, dict[str, dict[str, Any]]]
    programs: dict[str, str]
    losses: tuple[seam.Loss, ...] = ()


def check(plan: Plan, out: Path, result: Mapping[str, Any]) -> Checked:
    """Check what the producer wrote and returned. Raises Refused, naming every problem."""
    declaration = plan.declaration
    problems: list[str] = []
    digests: dict[str, str] = {}
    for key in plan.variants:
        path = out / f"{key}.png"
        if not path.is_file():
            problems.append(f"it wrote no file for the variant `{key}`, `{path.name}`")
            continue
        data = path.read_bytes()
        size = png_size(data)
        if size is None:
            problems.append(f"`{path.name}` is not a PNG")
        elif size != (declaration.width, declaration.height):
            problems.append(
                f"`{path.name}` is {size[0]}×{size[1]} pixels, and the piece declares "
                f"{declaration.width}×{declaration.height}"
            )
        digests[key] = sha256(data)
    pixels = {key: (declaration.width, declaration.height) for key in plan.variants}
    points = result.get("points")
    problems.extend(point_problems(points, pixels, plan.together()))
    programs = result.get("programs", {})
    if not isinstance(programs, Mapping) or not all(
        isinstance(name, str) and name.strip() and isinstance(version, str) and version.strip()
        for name, version in programs.items()
    ):
        problems.append("its `programs` is not a mapping of each outside program to its version")
    else:
        declared = plan.plugin.get("programs") or []
        problems.extend(
            f"it called `{program}`, which its declaration does not name under `programs`"
            for program in sorted(programs)
            if program not in declared
        )
    losses, lost = loss_problems(result.get("losses", []), plan.plugin["name"])
    problems.extend(lost)
    if problems:
        raise Refused(
            f"the producer `{plan.plugin['name']}` {plan.plugin['version']} made a picture "
            f"that cannot be kept, so nothing was kept: {'; '.join(problems)}. What it wrote "
            f"lies in `{HANDOVER}/{plan.piece}/{plan.output}/`"
        )
    assert isinstance(points, Mapping) and isinstance(programs, Mapping)
    return Checked(
        digests=digests,
        points={
            name: {key: dict(places[key]) for key in sorted(places, key=keys.key_order)}
            for name, places in sorted(points.items())
        },
        programs={name: programs[name] for name in sorted(programs)},
        losses=losses,
    )


def recorded_losses(record: Mapping[str, Any]) -> list[seam.Loss]:
    """The losses a produced record keeps. An entry not of the seam's one form is passed
    over: the record's schema refuses it, and the check reports that apart."""
    given = record.get("losses")
    found: list[seam.Loss] = []
    for entry in given if isinstance(given, list) else []:
        if not isinstance(entry, Mapping) or set(entry) != set(_LOSS_KEYS):
            continue
        if all(_text(entry[key]) for key in _LOSS_KEYS) and entry["did"] in seam.OUTCOMES:
            found.append(seam.Loss(**{key: entry[key] for key in _LOSS_KEYS}))
    return found


def loss_problems(given: Any, name: str) -> tuple[tuple[seam.Loss, ...], list[str]]:
    """A producer's losses, each once, in the order it gave them; and what is wrong with
    them: each is a mapping of `plugin`, its own name, `what`, a trace id or token path,
    `did`, one of the seam's outcomes, and `why`, a reason (DEC-005 point 9)."""
    if not isinstance(given, list):
        return (), ["its `losses` is not a list of losses, each `plugin`, `what`, `did` and `why`"]
    found: list[seam.Loss] = []
    problems: list[str] = []
    for number, entry in enumerate(given, start=1):
        at = f"its loss {number}"
        if not isinstance(entry, Mapping) or set(entry) != set(_LOSS_KEYS):
            problems.append(
                f"{at} is not of the seam's one form, a mapping of `plugin`, `what`, `did` and "
                f"`why`"
            )
            continue
        plugin, what, did, why = (entry[key] for key in _LOSS_KEYS)
        if plugin != name:
            problems.append(f"{at} names the plugin `{plugin}`, not `{name}`")
        elif did not in seam.OUTCOMES:
            problems.append(f"{at} did `{did}`, which is not one of {', '.join(seam.OUTCOMES)}")
        elif not (_text(what) and not any(c.isspace() for c in what) and _text(why)):
            problems.append(
                f"{at} names no trace id or token path under `what`, or no reason under `why`"
            )
        else:
            loss = seam.Loss(plugin, what, did, why)
            if loss not in found:
                found.append(loss)
    return tuple(found), problems


def keepable(root: Path, plan: Plan) -> None:
    """Refuse a run whose picture `keep` could not write whole: a variant's file or the
    record, or a folder above them, is a link. Raises Refused, writing nothing."""
    target = plan.folder / PRODUCED / plan.output
    for name in (*sorted(f"{key}.png" for key in plan.variants), RECORD):
        _refuse_links(root, target / name)


def keep(
    root: Path, plan: Plan, out: Path, checked: Checked, change: Change
) -> tuple[Path, tuple[str, ...]]:
    """Write the variants into the piece's `produced/<output>/`, then the record, and
    remove a variant file left from before, as the next steps of `change`, and take it;
    returns the record's path and what was removed. Raises Refused, writing nothing, where
    `keepable` refuses; WriteFailed where a write fails, the variants and the record then
    as they were before the run, or named."""
    target = plan.folder / PRODUCED / plan.output
    wanted = {f"{key}.png" for key in plan.variants}
    keepable(root, plan)
    for name in sorted(wanted):
        change.write(target / name, (out / name).read_bytes())
    record = target / RECORD
    change.write(record, record_text(record_of(plan, checked)).encode("utf-8"))
    held = sorted(target.iterdir()) if target.is_dir() else []
    removed = tuple(
        path.name
        for path in held
        if path.suffix == ".png" and path.is_file() and path.name not in wanted
    )
    for name in removed:
        change.remove(target / name)
    change.commit()
    return record, removed


def record_of(plan: Plan, checked: Checked) -> dict[str, Any]:
    """The record of a produced output (schema `produced-record`)."""
    declaration = plan.declaration
    name, version = plan.plugin["name"], plan.plugin["version"]
    served = {key: variant for variant, serves in plan.variants.items() for key in serves}
    return {
        "pkit_schema": schema_of("produced-record"),
        "schema_version": FORMAT,
        "fingerprint": plan.fingerprint(),
        "variants": {
            key: {
                "file": f"{key}.png",
                "pixels": declaration.pixels,
                "sha256": checked.digests[key],
            }
            for key in sorted(plan.variants, key=keys.key_order)
        },
        "combinations": {key: served[key] for key in plan.combinations},
        "points": checked.points,
        "losses": [loss.as_dict() for loss in checked.losses],
        "recorded": {
            "plugins": {name: version},
            "programs": checked.programs,
            "machine": _machine(),
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "capability": ".".join(map(str, libraries.installed_release())),
        },
    }


def record_text(record: Mapping[str, Any]) -> str:
    """The record as YAML, its time quoted, which reads back as `record`."""
    comment = (
        f"Written by `{PRODUCE}`, never by hand: what the picture was made from, its "
        f"variants and its exposed points."
    )
    text = records.text(records.quoted_time(record), [comment], apart=False)
    if load_yaml(text) != record:
        raise AssertionError("the record does not read back as it was written")
    return text


# --- the declaration, the producer and the brand ------------------------------------------------


def producer(name: str) -> Mapping[str, Any]:
    """The declaration of the producer `name`, checked against seam 1's form. Raises
    Refused."""
    if name not in seam.names():
        known = ", ".join(seam.names(seam.PRODUCER)) or "none"
        raise Refused(f"there is no producer `{name}` (the producers: {known})", declared=True)
    try:
        found = seam.declaration(name, seam.PRODUCER)
    except seam.PluginError as exc:
        raise Refused(str(exc), declared=True) from exc
    problem = declaration_problem(found)
    if problem is not None:
        raise Refused(f"the producer `{name}`'s declaration {problem}")
    return found


def declaration_problem(found: Mapping[str, Any]) -> str | None:
    """Why a producer's declaration does not take seam 1's form, or None."""
    kinds = found.get("values")
    if (
        not isinstance(kinds, (list, tuple))
        or not kinds
        or not all(kind in tokens.TYPES for kind in kinds)
    ):
        return f"names no kinds of value under `values`, each one of {', '.join(tokens.TYPES)}"
    schema = found.get("inputs")
    if not isinstance(schema, Mapping):
        return "has no `inputs` schema"
    unread = sorted(set(schema) - set(_SCHEMA_KEYS))
    if unread:
        return f"uses `{'`, `'.join(unread)}` in its `inputs` schema, which seam 1 does not read"
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        return (
            "has an `inputs` schema that is not `type: object` with `additionalProperties: false`"
        )
    properties = schema.get("properties", {})
    if not isinstance(properties, Mapping):
        return "has `inputs.properties` that is not a mapping"
    for name, spec in properties.items():
        if not is_name(name) or not isinstance(spec, Mapping):
            return f"has an input `{name}` that is not a name with a mapping"
        if set(spec) - set(_PROPERTY_KEYS):
            return f"has an input `{name}` with keys seam 1 does not read"
        if spec.get(ROLE) not in kinds:
            return f"has an input `{name}` not marked `{ROLE}` with one of its kinds of value"
    required = schema.get("required", [])
    if not isinstance(required, (list, tuple)) or not all(name in properties for name in required):
        return "requires an input its `inputs.properties` does not hold"
    for key in _NEEDS:
        needs = found.get(key, [])
        if not isinstance(needs, (list, tuple)) or not all(_text(need) for need in needs):
            return f"names its `{key}` other than as a list of names"
        twice = sorted({need for need in needs if needs.count(need) > 1})
        if twice:
            return f"names `{'`, `'.join(twice)}` twice under `{key}`"
    return None


def _piece_folder(root: Path, location: str, piece: str) -> Path:
    if not is_name(piece):
        raise Refused(f"`{piece}` is not a piece's name, lower-case words joined by hyphens")
    return root / location / PIECES / piece


def _piece(root: Path, folder: Path, piece: str) -> dict[str, Any]:
    path = folder / "piece.yaml"
    if not path.is_file():
        raise Refused(
            f"there is no piece `{piece}`: {path.relative_to(root).as_posix()} is missing"
        )
    try:
        return read_bound(path, "piece")
    except (ReadError, FileError) as exc:
        raise Refused(str(exc)) from exc


def _declaration(data: Mapping[str, Any], piece: str, output: str) -> Declaration:
    """The output's declaration in `piece.yaml`. Raises Refused."""
    at = f"`produced.{output}` of `{piece}`"
    produced = data.get("produced")
    declared = produced if isinstance(produced, Mapping) else {}
    if not is_name(output) or output not in declared:
        near = nearest(output, declared)
        hint = f" (did you mean `{near}`?)" if near else ""
        raise Refused(
            f"the piece `{piece}` declares no produced output `{output}`{hint}: declare it "
            f"under `produced:` in its piece.yaml",
            declared=True,
        )
    entry = declared[output]
    if not isinstance(entry, Mapping):
        raise Refused(f"{at} is not a mapping of `producer`, `inputs` and `pixels`", declared=True)
    name, inputs, pixels = entry.get("producer"), entry.get("inputs"), entry.get("pixels")
    if not isinstance(name, str) or not is_name(name):
        raise Refused(f"{at} names no `producer`", declared=True)
    if not isinstance(inputs, Mapping) or not all(isinstance(key, str) for key in inputs):
        raise Refused(f"{at} has no `inputs` mapping of each input to a role", declared=True)
    for key, role in inputs.items():
        if not is_token_path(role):
            raise Refused(
                f"the input `{key}` of {at} is `{role}`, which is no role: an input names a "
                f"role of the brand by its token path, such as `accent`, never a raw value",
                declared=True,
            )
    size = _size(pixels)
    if size is None:
        raise Refused(f"{at} has no `pixels` of a whole `width` and `height`", declared=True)
    return Declaration(output, name, dict(inputs), *size)


def _check_inputs(declaration: Declaration, plugin: Mapping[str, Any], brand: tokens.Brand) -> None:
    """Refuse an input the producer does not take, a role the brand does not have or of
    another type than the input takes, and a required input left out."""
    schema = plugin["inputs"]
    properties: Mapping[str, Any] = schema.get("properties", {})
    name = plugin["name"]
    for key, role in declaration.inputs.items():
        if key not in properties:
            near = nearest(key, properties)
            hint = f" (did you mean `{near}`?)" if near else ""
            takes = ", ".join(f"`{p}`" for p in sorted(properties)) or "none"
            raise Refused(
                f"the producer `{name}` takes no input `{key}`{hint}; its inputs: {takes}",
                declared=True,
            )
        if role not in brand.roles:
            near = nearest(role, brand.roles)
            hint = f" (did you mean `{near}`?)" if near else ""
            raise Refused(
                f"the input `{key}` names `{role}`, which is no role of the brand "
                f"{brand.name} {brand.version}{hint}",
                declared=True,
            )
        wanted, found = properties[key][ROLE], brand.type_of(role)
        if found != wanted:
            raise Refused(
                f"the input `{key}` of the producer `{name}` takes a role of type `{wanted}`, "
                f"and `{role}` is of type `{found}`",
                declared=True,
            )
    missing = [key for key in schema.get("required", []) if key not in declaration.inputs]
    if missing:
        raise Refused(
            f"`produced.{declaration.output}` leaves out the input "
            f"`{'`, `'.join(missing)}` that the producer `{name}` requires",
            declared=True,
        )


def _brand(
    root: Path,
    location: str,
    piece: str,
    name: Any,
    lock: Mapping[str, Any],
    held: libraries.Held | None,
) -> tuple[tokens.Brand, dict[str, str]]:
    """The brand version the piece's lock names, read against the shared roles the locked
    foundations declare, as the pipeline reads them; with the lock of the two, which is
    the brand and what it builds on in format 1. Raises Refused."""
    if not isinstance(name, str) or not is_name(name):
        raise Refused(f"the piece `{piece}` names no `brand`")
    held = libraries.Held(root, location) if held is None else held
    found: dict[str, libraries.Library] = {}
    for library in (name, FOUNDATIONS):
        text = lock.get(library)
        if text is None:
            raise Refused(
                f"the lock of `{piece}` names no version of `{library}`: run `{RENDER} {piece}` "
                f"to move it"
            )
        try:
            version = libraries.Version.parse(text)
        except ValueError as exc:
            raise Refused(f"the lock of `{piece}` names `{library}: {text}`: {exc}") from exc
        why = held.unreadable(library, version)
        if why is not None:
            raise Refused(f"{library}@{version}, which the lock of `{piece}` names: {why}")
        found[library] = held.library(library, version)
    brand, foundations = found[name], found[FOUNDATIONS]
    roles = foundations.folder / "roles.yaml"
    try:
        shared = tokens.read_declarations(
            roles, library=foundations.label, shown=roles.relative_to(root).as_posix()
        )
        read = tokens.read_brand(brand.folder, shared, fonts=root / location / FONTS, root=root)
    except tokens.TokenError as exc:
        raise Refused(f"the brand {brand.label} cannot be read: {exc}") from exc
    return read, {library: str(found[library].version) for library in sorted(found)}


# --- what the check reads -----------------------------------------------------------------------


def png_size(data: bytes) -> tuple[int, int] | None:
    """The width and the height a PNG's header gives, or None for bytes that are no PNG."""
    if len(data) < _PNG_SIZE.stop or not data.startswith(_PNG_SIGNATURE) or data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[_PNG_SIZE])
    return width, height


def held_together(
    variants: Mapping[str, Iterable[str]], axes: Mapping[str, tokens.Axis]
) -> list[list[str]]:
    """The variants each scene holds: those that serve a combination with one key over the
    size axes (DEC-005 point 5). A combination the axes do not hold is left out."""
    size = {name: axis for name, axis in axes.items() if axis.kind == "size"}
    by_scene: dict[str, set[str]] = {}
    for variant, served in variants.items():
        for key in served:
            try:
                combination = keys.parse_key(key, axes)
            except keys.BadKey:
                continue
            scene = keys.key_of({axis: combination[axis] for axis in size}, size)
            by_scene.setdefault(scene, set()).add(variant)
    return [sorted(group, key=keys.key_order) for _, group in sorted(by_scene.items())]


def point_problems(
    points: Any, pixels: Mapping[str, tuple[int, int]], together: Iterable[Iterable[str]]
) -> list[str]:
    """What is wrong with a picture's exposed points (DEC-006 points 2, 3 and 8): points
    not of the format, a point some variant lacks, one outside its variant's pixels, one at
    different places in the variants a scene holds. Variants a scene holds that differ in
    pixel size are named too. `pixels` gives each variant's size."""
    if not isinstance(points, Mapping):
        return ["it gave no `points`, a mapping of each point to its place in each variant"]
    found: list[str] = []
    variants = sorted(pixels, key=keys.key_order)
    places: dict[str, dict[str, tuple[float, float]]] = {}
    for name, given in points.items():
        if not is_name(name):
            found.append(f"the point `{name}` is not a name of lower-case words")
            continue
        if not isinstance(given, Mapping):
            found.append(f"the point `{name}` is not a mapping of each variant to its place")
            continue
        missing = [key for key in variants if key not in given]
        if missing:
            found.append(
                f"the point `{name}` is missing from the variant `{'`, `'.join(missing)}`: "
                f"every variant exposes the same points"
            )
        stray = sorted(key for key in given if key not in pixels)
        if stray:
            found.append(f"the point `{name}` names `{'`, `'.join(stray)}`, which no variant is")
        places[name] = {}
        for key in variants:
            if key not in given:
                continue
            place = _place(given[key])
            if place is None:
                found.append(f"the point `{name}` in `{key}` is not `{{x, y}}`, two numbers")
                continue
            width, height = pixels[key]
            x, y = place
            if not (0 <= x <= width and 0 <= y <= height):
                found.append(
                    f"the point `{name}` lies at ({_number(x)}, {_number(y)}) in `{key}`, "
                    f"outside its {width}×{height} pixels"
                )
            places[name][key] = place
    for group in together:
        held = [key for key in group if key in pixels]
        if len({pixels[key] for key in held}) > 1:
            found.append(
                f"the variants `{'`, `'.join(held)}`, which one scene holds, differ in pixel size"
            )
        for name, at in sorted(places.items()):
            distinct = {at[key] for key in held if key in at}
            if len(distinct) > 1:
                shown = ", ".join(
                    f"({_number(at[key][0])}, {_number(at[key][1])}) in `{key}`"
                    for key in held
                    if key in at
                )
                found.append(
                    f"the point `{name}` lies at different places in variants one scene holds: "
                    f"{shown}"
                )
    return found


def findings(root: Path, location: str, piece: str) -> list[Finding]:
    """What the check reports of the produced outputs of the piece `piece` in the location
    at `location` (relative to `root`) (DEC-006 points 5 and 8). A piece whose `piece.yaml`
    cannot be read gives none: the check reports that file itself."""
    if not is_name(piece):
        return []
    rel = f"{location}/{PIECES}/{piece}"
    try:
        data = read_bound(root / rel / "piece.yaml", "piece")
    except (ReadError, FileError):
        return []
    produced = data.get("produced")
    declared = sorted(produced) if isinstance(produced, Mapping) else []
    prefix = f"{rel}/{PRODUCED}/"
    listed = set(loc.files(root, prefix.rstrip("/")))
    found: list[Finding] = []
    present = sorted(
        {path[len(prefix) :].split("/")[0] for path in listed if "/" in path[len(prefix) :]}
    )
    for output in present:
        if output not in declared:
            found.append(
                Finding(
                    "produced-undeclared",
                    ATTENTION,
                    f"the piece `{piece}` declares no produced output `{output}`, yet "
                    f"`{PRODUCED}/{output}/` holds files",
                    file=f"{rel}/{PRODUCED}/{output}",
                    fix=f"declare `{output}` under `produced:` in piece.yaml, or remove the folder",
                    who=AUTHORS,
                )
            )
    accepting = _accepting(data)
    for output in declared:
        found.extend(_output_findings(root, location, piece, output, listed, accepting))
    return found


def _output_findings(
    root: Path,
    location: str,
    piece: str,
    output: str,
    listed: set[str],
    accepting: list[Mapping[str, Any]],
) -> list[Finding]:
    rel = f"{location}/{PIECES}/{piece}"
    base = f"{rel}/{PRODUCED}/{output}"
    record_rel = f"{base}/{RECORD}"
    fix = f"run `{PRODUCE} {piece} {output}`"
    if record_rel not in listed:
        holds = any(path.startswith(f"{base}/") for path in listed)
        return [
            Finding(
                "produced-record-missing",
                FAILS,
                f"the produced output `{output}` of `{piece}` has no record"
                + (", though its folder holds files" if holds else "")
                + ", so its picture can be neither drawn nor checked",
                file=record_rel,
                where=f"produced.{output}",
                fix=fix,
            )
        ]
    try:
        record = read_bound(root / record_rel, "produced-record")
    except (ReadError, FileError) as exc:
        return [Finding("produced-record-unreadable", FAILS, str(exc), file=record_rel, fix=fix)]
    found: list[Finding] = []
    given = record.get("variants")
    variants: Mapping[str, Any] = given if isinstance(given, Mapping) else {}
    pixels: dict[str, tuple[int, int]] = {}
    for key, entry in variants.items():
        if not isinstance(entry, Mapping) or not isinstance(entry.get("file"), str):
            continue
        size = _size(entry.get("pixels"))
        if size is not None:
            pixels[key] = size
        file = f"{base}/{entry['file']}"
        if file not in listed:
            found.append(
                Finding(
                    "produced-variant-missing",
                    FAILS,
                    f"the record of `{output}` names the variant `{key}`, whose file "
                    f"`{entry['file']}` is missing",
                    file=record_rel,
                    where=f"variants.{key}",
                    fix=fix,
                )
            )
        elif sha256((root / file).read_bytes()) != entry.get("sha256"):
            found.append(
                Finding(
                    "produced-variant-changed",
                    FAILS,
                    f"`{entry['file']}` is not the file the producer wrote for the variant "
                    f"`{key}`: its hash differs from the record's",
                    file=file,
                    where=f"variants.{key}",
                    fix=fix,
                )
            )
    mapped = record.get("combinations")
    combinations: Mapping[str, Any] = mapped if isinstance(mapped, Mapping) else {}
    try:
        current = plan(root, location, piece, output)
    except Refused as exc:
        found.append(
            Finding(
                "produced-unverified",
                FAILS if exc.declared else ATTENTION,
                f"the picture `{output}` of `{piece}` cannot be checked against what it was made "
                f"from: {exc}",
                file=f"{rel}/piece.yaml" if exc.declared else record_rel,
                where=f"produced.{output}",
                fix=f"mend that, then {fix}" if exc.declared else fix,
                who="" if exc.declared else AUTHORS,
            )
        )
        # Which variants one scene holds is read from the brand's axes, unread here.
        together: list[list[str]] = []
    else:
        recorded = record.get("fingerprint")
        stale = (
            fingerprint.verify(recorded, "produced-record", **current.sources)
            if isinstance(recorded, Mapping)
            else ["the record keeps no fingerprint"]
        )
        stale += [
            f"the combination `{key}` has no variant"
            for key in current.combinations
            if combinations.get(key) not in variants
        ]
        if stale:
            found.append(
                Finding(
                    "produced-stale",
                    ATTENTION,
                    f"the picture `{output}` of `{piece}` is stale: {'; '.join(stale)}",
                    file=record_rel,
                    where="fingerprint",
                    fix=fix,
                    who=AUTHORS,
                )
            )
        served: dict[str, list[str]] = {}
        for key, variant in combinations.items():
            served.setdefault(variant, []).append(key)
        together = held_together(served, current.axes)
    for problem in point_problems(record.get("points"), pixels, together):
        found.append(
            Finding(
                "produced-points",
                FAILS,
                f"the record of `{output}`: {problem}",
                file=record_rel,
                where="points",
                fix=fix,
            )
        )
    for loss in recorded_losses(record):
        if not accepted(loss, accepting):
            found.append(
                loss_finding(loss, _KIND, file=f"{rel}/piece.yaml", where=f"produced.{output}")
            )
    return found


# --- helpers ------------------------------------------------------------------------------------


def _size(given: Any) -> tuple[int, int] | None:
    """A `{width, height}` of whole numbers from 1, as a pair, or None."""
    if not isinstance(given, Mapping):
        return None
    width, height = given.get("width"), given.get("height")
    if isinstance(width, bool) or isinstance(height, bool):
        return None
    if isinstance(width, int) and isinstance(height, int) and width >= 1 and height >= 1:
        return width, height
    return None


def _accepting(data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The entries of a piece's `accept-losses`; a value of another shape the piece's
    schema refuses, so it accepts none."""
    given = data.get("accept-losses")
    return (
        [entry for entry in given if isinstance(entry, Mapping)] if isinstance(given, list) else []
    )


def _text(given: Any) -> bool:
    """Whether `given` is text that is not blank."""
    return isinstance(given, str) and bool(given.strip())


def _place(given: Any) -> tuple[float, float] | None:
    if not isinstance(given, Mapping) or set(given) != {"x", "y"}:
        return None
    x, y = given["x"], given["y"]
    if not all(
        isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n) for n in (x, y)
    ):
        return None
    return x, y


def _number(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def _machine() -> str:
    shown = f"{platform.system().lower()} {platform.machine()}".strip()
    return shown or "unknown"


def _refuse_links(root: Path, target: Path) -> None:
    try:
        refuse_links(root, target)
    except FileError as exc:
        raise Refused(str(exc)) from exc
