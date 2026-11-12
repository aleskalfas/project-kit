"""The release's comparison of two versions of one library: a version, and an earlier
released one (visual-communication DEC-003 points 6 and 7, DEC-004 point 5, DEC-013 point 3).

It names each *break*, a change that breaks what the earlier version promises, and each
*addition*, and says the segment the later version's number needs: a major where it finds a
break, at least a minor where it finds an addition, and otherwise at least a patch. Whether
a change of look makes a patch a minor is the owner's judgement (DEC-013 point 3). It is code
the commands call, never a validator (DEC-002 point 7).

**Its callers** each read the two versions in full (`full_read.read`), each with the versions
it is checked with, and pass both to `compare`:

- the release of a version the capability ships, with the library's previous release;
- the capability's own checks, with the newest released version of the major the version
  being built carries, failing each break they find (DEC-013 point 6);
- the release of a project's own library, with its previous release.

The result (`Comparison`) holds each break and each addition (`Change`: what changed, how,
and the record that sets it), the segment, and whether the later number allows its breaks
(`allowed`). `lines` says it in words, for a command to show or a check to report.

**What it compares,** kind by kind, as `files.md`, "What a release compares", lists it:

- *any library:* its kind, and the major of each library it builds on (DEC-003 point 6);
- *components,* a component library's or a brand's: each component the earlier version
  marks stable or deprecated, its fields, options, states, exposed parts, ends, lists and
  layouts with their slots, whether a top asks for a height, and a top's physical size
  (DEC-003 points 6 and 7, DEC-009 to DEC-012, DEC-022 point 8, DEC-034 point 3). An
  experimental component may change in any release, so only its arrival is named, as for
  any new component. A drawing carries no status, so it is passed over, its look and its
  parts, and so are a drawing new and one removed, a base's that begins to serve a top
  among them. One the earlier version promises, which the later declares a drawing,
  breaks, as one removed does, and a drawing that ceases to be one is new (DEC-034 point 8);
- *a component's tokens:* those of each component the earlier version marks stable or
  deprecated, as its component promises them (DEC-035 point 6): a token removed, of
  another type, or whose chain of defaults no longer ends at a shared role where it did,
  breaks; a new one is an addition, whatever its chain ends at. A brand's own components'
  tokens are read from their files, since no scope reads them (DEC-035 point 7);
- *a library's own roles:* those its stable and deprecated components read, directly or
  through a default, a token's default among them, and a new one such a component reads
  (DEC-008 point 7, DEC-035 point 4);
- *pairs:* every pair a library declares, whatever reads it (DEC-008 point 7);
- *the foundations:* their shared roles and the top groups they lie in, axes and colour
  families, whatever reads them (DEC-004 point 5);
- *a brand:* the token paths it exports, a shared picture role among them only where it
  gives it a value (DEC-025 point 4), its axes and modes, every shared value axis whole
  and each size it gives (DEC-021 point 2), the component tokens it gives values among its
  token paths, and the roles it opens to a brand built on it (DEC-004 point 5).

**What a field's schema breaks.** A field changes what it means where what content gave it
may no longer be taken: it no longer takes a type, a value or a count of items it took, a
key below it is removed or newly required, or the field itself is newly required. Another
change of its schema, such as its description, is neither a break nor an addition.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from _lib import formula as fm
from _lib import layout, names, tokens
from _lib.full_read import FullRead
from _lib.libraries import FOUNDATIONS, Library, Version

#: The statuses whose components a library promises (DEC-003 point 7).
PROMISED = ("stable", "deprecated")

MAJOR, MINOR, PATCH = "major", "minor", "patch"

#: How far a side of a physical size, written in whole millimetres, may lie from the length
#: it rounds (DEC-034 point 3).
MM_ROUNDING = 0.5


class ComparisonError(Exception):
    """Two versions the comparison cannot compare: the message says why."""


@dataclass(frozen=True)
class Change:
    """A change the comparison names: `where` it lies, such as a component's field, `what`
    changed, and the `record` that counts it a break or an addition."""

    where: str
    what: str
    record: str

    def __str__(self) -> str:
        return f"{self.where}: {self.what} ({self.record})"


@dataclass(frozen=True)
class Comparison:
    """What the comparison of `earlier` with `later`, two versions of the library `name`,
    found: each break and each addition, in the order of what they lie in."""

    name: str
    earlier: Version
    later: Version
    breaks: tuple[Change, ...] = ()
    additions: tuple[Change, ...] = ()

    @property
    def segment(self) -> str:
        """The segment the later number needs at least: a major for a break, a minor for an
        addition, else a patch."""
        return MAJOR if self.breaks else MINOR if self.additions else PATCH

    @property
    def allowed(self) -> bool:
        """Whether the later number allows each break: none is found, or its major is higher
        than the earlier's."""
        return not self.breaks or self.later.major > self.earlier.major

    def lines(self) -> list[str]:
        """The comparison in words: what it compares and the segment it finds, whether the
        later number keeps the major its breaks need raised, then each break and each
        addition, a line each."""
        needs = "a major" if self.breaks else f"at least a {self.segment}"
        head = f"{self.name} {self.earlier} to {self.later}: the number needs {needs}"
        if not self.allowed:
            head += f", and {self.later} keeps major {self.earlier.major}"
        return [
            head,
            *(f"  break: {change}" for change in self.breaks),
            *(f"  addition: {change}" for change in self.additions),
        ]


@dataclass
class _Found:
    breaks: list[Change] = field(default_factory=list)
    additions: list[Change] = field(default_factory=list)

    def broken(self, where: str, what: str, record: str) -> None:
        self.breaks.append(Change(where, what, record))

    def added(self, where: str, what: str, record: str) -> None:
        self.additions.append(Change(where, what, record))


def compare(earlier: FullRead, later: FullRead) -> Comparison:
    """The comparison of `later` with `earlier`, two versions of one library, each read in
    full with the versions it is checked with (`full_read.read`). Raises ComparisonError
    where they are versions of two libraries, where either could not be read with its bases,
    where a brand could not be read, or where the later version cannot read a component the
    earlier one promises."""
    if earlier.name != later.name:
        raise ComparisonError(f"{earlier.label} and {later.label} are versions of two libraries")
    kind, now = _library(earlier).kind, _library(later).kind
    found = _Found()
    if kind != now:
        found.broken(
            f"`{earlier.name}`", f"is of kind `{now}`, where it was `{kind}`", "DEC-003 point 6"
        )
    else:
        _builds_on(earlier, later, found)
        if kind == "components":
            _components(earlier, later, found)
            if earlier.name == FOUNDATIONS:
                _shared(earlier, later, found)
            else:
                _own_roles(earlier, later, found)
            _pairs(earlier, later, found)
        elif kind == "brand":
            _components(earlier, later, found)
            _brand(earlier, later, found)
    return Comparison(
        earlier.name, earlier.version, later.version, tuple(found.breaks), tuple(found.additions)
    )


def _library(read: FullRead) -> Library:
    """The library version read, its `library.yaml`. Raises ComparisonError where it could
    not be read with its bases."""
    if read.library is None or read.scope is None:
        why = "; ".join(finding.message for finding in read.findings) or "it could not be read"
        raise ComparisonError(f"{read.label} cannot be compared: {why}")
    return read.library


def _builds_on(earlier: FullRead, later: FullRead, found: _Found) -> None:
    """A library it builds on, at a new major (DEC-003 point 6)."""
    assert earlier.library is not None and later.library is not None
    majors = {need.name: need.major for need in later.library.builds_on}
    for need in earlier.library.builds_on:
        major = majors.get(need.name)
        if major is not None and major != need.major:
            found.broken(
                f"`{earlier.name}`, builds on `{need.name}`",
                f"major {major}, where it built on major {need.major}",
                "DEC-003 point 6",
            )


# --- components ---------------------------------------------------------------------------------


def _status(read: FullRead, name: str) -> Any:
    """The status a component's file gives it."""
    return read.data[name].get("status")


def _is_drawing(read: FullRead, name: str) -> bool:
    """Whether the component `name` of the version is a drawing: it declares `draws`
    (DEC-034 point 1)."""
    return read.components[name].draws is not None


def _components(earlier: FullRead, later: FullRead, found: _Found) -> None:
    """Each component the earlier version marks stable or deprecated, against the later
    version; and each component new in the later version. A drawing promises nothing, so
    neither version's drawings are compared or named (DEC-034 point 8)."""
    for name in sorted(earlier.components):
        status = _status(earlier, name)
        if _is_drawing(earlier, name) or status not in PROMISED:
            continue
        use = f"{earlier.name}/{name}"
        if name in later.unread:
            raise ComparisonError(
                f"`{use}` cannot be read in {later.label}, so it cannot be compared"
            )
        if name not in later.components:
            record = "DEC-003 points 6 and 7" if status == "stable" else "DEC-003 point 7"
            found.broken(f"`{use}`", f"is removed, where it was {status}", record)
            continue
        if _is_drawing(later, name):
            found.broken(f"`{use}`", f"is a drawing, where it was {status}", "DEC-034 point 8")
            continue
        if _status(later, name) not in PROMISED:
            found.broken(
                f"`{use}`",
                f"is marked {_status(later, name)}, where it was {status}",
                "DEC-003 point 7",
            )
        _component(
            f"`{use}`",
            earlier.components[name],
            later.components[name],
            earlier.data[name],
            later.data[name],
            found,
        )
        _tokens(f"`{use}`", name, earlier, later, found)
    for name in sorted(set(later.components) - set(earlier.unread)):
        if _is_drawing(later, name):
            continue
        if name not in earlier.components:
            found.added(f"`{later.name}/{name}`", "is new", "DEC-003 point 1")
        elif _is_drawing(earlier, name):
            found.added(
                f"`{later.name}/{name}`", "is new, where it was a drawing", "DEC-034 point 8"
            )


def _component(
    where: str,
    earlier: layout.Component,
    later: layout.Component,
    data_e: Mapping[str, Any],
    data_l: Mapping[str, Any],
    found: _Found,
) -> None:
    _fields(
        where, "field", earlier.fields, later.fields, _required(data_e), _required(data_l), found
    )
    _runs(where, "field", earlier.runs, later.runs, earlier.fields, later.fields, found)
    _options(where, earlier.options, later.options, found)
    _named(
        where, "state", earlier.states, later.states, "DEC-003 point 6", "DEC-003 point 1", found
    )
    _named(
        where,
        "exposed part",
        earlier.exposes,
        later.exposes,
        "DEC-003 point 6, DEC-005 point 3",
        "DEC-009 point 7",
        found,
    )
    if earlier.takes_ends and not later.takes_ends:
        found.broken(where, "ceases to take ends", "DEC-011 point 6")
    _lists(where, earlier.list_fields, later.list_fields, earlier.fields, later.fields, found)
    if earlier.top:
        _layouts(where, earlier, later, data_e, data_l, found)


def _tokens_of(read: FullRead, component: str) -> dict[str, tokens.ComponentToken]:
    """The component tokens the component `component` of the version declares, by path: as
    the scope reads them, or, in a brand, whose own components' tokens no scope reads
    (DEC-035 point 7), as its file declares them."""
    assert read.scope is not None and read.library is not None
    if read.library.kind == "brand":
        declared, _ = tokens.read_component_tokens(read.library.folder, name=read.name)
        return {path: token for path, token in declared.items() if token.component == component}
    return {
        path: token
        for path, token in read.scope.tokens.items()
        if token.component == component and read.scope.owner[path] == read.name
    }


def _tokens(where: str, name: str, earlier: FullRead, later: FullRead, found: _Found) -> None:
    """A compared component's tokens, as it promises them (DEC-035 point 6): a token
    removed, of another type, or whose chain of defaults no longer ends at a shared role
    where it did, breaks; a new token is an addition, whatever its chain ends at. Any other
    change, such as a default pointed at another role, is neither."""
    assert earlier.scope is not None and later.scope is not None
    tokens_e, tokens_l = _tokens_of(earlier, name), _tokens_of(later, name)
    for path, token in sorted(tokens_e.items()):
        at = f"{where}, token `{path}`"
        now = tokens_l.get(path)
        if now is None:
            found.broken(at, "is removed", "DEC-003 point 6, DEC-035 point 6")
            continue
        if now.type != token.type:
            found.broken(
                at,
                f"is of type `{now.type}`, where it was `{token.type}`",
                "DEC-003 point 6, DEC-035 point 6",
            )
        if _token_ends_shared(earlier.scope, token) and not _token_ends_shared(later.scope, now):
            found.broken(
                at, "no longer ends its chain of defaults at a shared role", "DEC-035 point 6"
            )
    for path in sorted(set(tokens_l) - set(tokens_e)):
        found.added(f"{where}, token `{path}`", "is new", "DEC-035 point 6")


def _required(data: Mapping[str, Any]) -> set[str]:
    fields = data.get("fields")
    required = fields.get("required") if isinstance(fields, Mapping) else None
    return {str(name) for name in required} if isinstance(required, list) else set()


def _fields(
    where: str,
    noun: str,
    earlier: Mapping[str, Any],
    later: Mapping[str, Any],
    required_e: set[str],
    required_l: set[str],
    found: _Found,
) -> None:
    """A component's fields, or a layout's slots: each removed, newly required, or narrowed
    in what it takes, breaks (DEC-003 point 6, DEC-009 point 7); each new one that is
    optional is an addition, and one that is required breaks (DEC-009 point 7)."""
    for name, schema in earlier.items():
        at = f"{where}, {noun} `{name}`"
        if name not in later:
            found.broken(at, "is removed", "DEC-003 point 6")
            continue
        if name in required_l and name not in required_e:
            found.broken(at, "is required, where it was optional", "DEC-009 point 7")
        for what in _narrowed(schema, later[name]):
            found.broken(at, what, "DEC-003 point 6")
    for name in later:
        if name in earlier:
            continue
        at = f"{where}, {noun} `{name}`"
        if name in required_l:
            found.broken(at, "is new, and required", "DEC-009 point 7")
        else:
            found.added(at, "is new", "DEC-009 point 7")


def _narrowed(earlier: Any, later: Any, at: str = "") -> list[str]:
    """How a field's schema `later` no longer takes what `earlier` took: a type, a value or a
    count of items; and, below it, a key removed or newly required. `at` is the key path
    below the field."""
    if not isinstance(earlier, Mapping) or not isinstance(later, Mapping):
        return []
    said = f"at `{at}`, " if at else ""
    found = []
    types_e, types_l = _types(earlier), _types(later)
    if types_l is not None and (types_e is None or types_e - types_l):
        lost = ", ".join(f"`{kind}`" for kind in sorted(types_e - types_l)) if types_e else ""
        found.append(
            f"{said}no longer takes {lost}"
            if lost
            else f"{said}takes only {_listed(types_l)}, where it took any type"
        )
    values_e, values_l = _values(earlier), _values(later)
    if values_l is not None:
        if values_e is None:
            found.append(f"{said}takes only {_listed(values_l)}, where it took any value")
        else:
            lost_values = [value for value in values_e if value not in values_l]
            if lost_values:
                found.append(f"{said}no longer takes {_listed(lost_values)}")
    least_e, least_l = earlier.get("minItems", 0), later.get("minItems", 0)
    if _count(least_l) and _count(least_e) and least_l > least_e:
        found.append(f"{said}takes at least {least_l} items, where it took {least_e}")
    most_e, most_l = earlier.get("maxItems"), later.get("maxItems")
    if _count(most_l) and (not _count(most_e) or most_l < most_e):
        was = f", where it took {most_e}" if _count(most_e) else ""
        found.append(f"{said}takes at most {most_l} items{was}")
    keys_e, keys_l = earlier.get("properties"), later.get("properties")
    keys_e = keys_e if isinstance(keys_e, Mapping) else {}
    keys_l = keys_l if isinstance(keys_l, Mapping) else {}
    required_e, required_l = _required({"fields": earlier}), _required({"fields": later})
    for key, schema in keys_e.items():
        below = f"{at}.{key}" if at else str(key)
        if key not in keys_l:
            found.append(f"no longer takes the key `{below}`")
            continue
        if key in required_l and key not in required_e:
            found.append(f"requires the key `{below}`, where it was optional")
        found.extend(_narrowed(schema, keys_l[key], below))
    for key in keys_l:
        if key not in keys_e and key in required_l:
            found.append(f"requires the new key `{f'{at}.{key}' if at else key}`")
    found.extend(
        _narrowed(earlier.get("items"), later.get("items"), f"{at}.items" if at else "items")
    )
    return found


def _types(schema: Mapping[str, Any]) -> set[str] | None:
    """The types a schema takes, or None for any."""
    kind = schema.get("type")
    if isinstance(kind, str):
        return {kind}
    if isinstance(kind, list):
        return {str(each) for each in kind}
    return None


def _values(schema: Mapping[str, Any]) -> list[Any] | None:
    """The values a schema takes, by `enum` or `const`, or None for any."""
    if "const" in schema:
        return [schema["const"]]
    enum = schema.get("enum")
    return list(enum) if isinstance(enum, list) else None


def _count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _listed(values: Iterable[Any]) -> str:
    return ", ".join(f"`{value}`" for value in sorted(values, key=str))


def _runs(
    where: str,
    noun: str,
    earlier: Mapping[str, tuple[str, ...]],
    later: Mapping[str, tuple[str, ...]],
    fields_e: Mapping[str, Any],
    fields_l: Mapping[str, Any],
    found: _Found,
) -> None:
    """The fields of runs, by their words (DEC-012 point 6): a field that ceases to take
    runs, a change of its first word, and a word removed, break; a field that comes to take
    runs, and a new word, are additions."""
    for name, words in earlier.items():
        if name not in fields_l:
            continue  # its removal is named
        at = f"{where}, {noun} `{name}`"
        if name not in later:
            found.broken(at, "ceases to take runs", "DEC-012 point 6")
            continue
        now = later[name]
        if now[0] != words[0]:
            found.broken(
                at, f"takes runs of `{now[0]}` first, where it took `{words[0]}`", "DEC-012 point 6"
            )
        for word in words:
            if word not in now:
                found.broken(f"{at}, run style `{word}`", "is removed", "DEC-012 point 6")
        for word in now:
            if word not in words:
                found.added(f"{at}, run style `{word}`", "is new", "DEC-012 point 6")
    for name in later:
        if name in fields_e and name not in earlier:
            found.added(f"{where}, {noun} `{name}`", "comes to take runs", "DEC-012 point 6")


def _options(
    where: str,
    earlier: Mapping[str, layout.Option],
    later: Mapping[str, layout.Option],
    found: _Found,
) -> None:
    """Each option, and the words of each (DEC-003 point 6, DEC-009 point 7)."""
    for name, option in earlier.items():
        at = f"{where}, option `{name}`"
        now = later.get(name)
        if now is None:
            found.broken(at, "is removed", "DEC-003 point 6")
            continue
        if _names(option) != _names(now):
            found.broken(
                at, f"{_names(now)}, where it {_names(option, past=True)}", "DEC-003 point 6"
            )
            continue
        for word in option.words:
            if word not in now.words:
                found.broken(f"{at}, word `{word}`", "is removed", "DEC-003 point 6")
        for word in now.words:
            if word not in option.words:
                found.added(f"{at}, word `{word}`", "is new", "DEC-009 point 7")
    for name in later:
        if name not in earlier:
            found.added(f"{where}, option `{name}`", "is new", "DEC-009 point 7")


def _names(option: layout.Option, *, past: bool = False) -> str:
    """What an option takes, in words."""
    takes = "took" if past else "takes"
    names_ = "named" if past else "names"
    if option.items is None:
        return f"{takes} words"
    point = ", and its point" if option.point else ""
    return f"{names_} an item of `{option.items}`{point}"


def _named(
    where: str,
    noun: str,
    earlier: Iterable[str],
    later: Iterable[str],
    removed: str,
    added: str,
    found: _Found,
) -> None:
    """Names a component declares, such as its states: each removed breaks, each new one is
    an addition."""
    earlier, later = list(earlier), list(later)
    for name in earlier:
        if name not in later:
            found.broken(f"{where}, {noun} `{name}`", "is removed", removed)
    for name in later:
        if name not in earlier:
            found.added(f"{where}, {noun} `{name}`", "is new", added)


def _lists(
    where: str,
    earlier: Mapping[str, layout.ListFields],
    later: Mapping[str, layout.ListFields],
    fields_e: Mapping[str, Any],
    fields_l: Mapping[str, Any],
    found: _Found,
) -> None:
    """What a component declares for each list it repeats, of a list field held in both
    versions: its component field (DEC-010 point 7), its arrangement fields and their words
    (DEC-010 point 7), and its end fields (DEC-011 point 6). `fields_e` and `fields_l` are
    the fields, or a layout's slots, the lists are of."""
    for name in sorted(set(earlier) | set(later)):
        if name not in fields_l:
            continue  # its field's removal is named
        at = f"{where}, list `{name}`"
        was, now = earlier.get(name), later.get(name)
        component_e = was.component if was else None
        component_l = now.component if now else None
        if component_e is not None and component_l != component_e:
            found.broken(
                at, f"no longer names its component in the field `{component_e}`", "DEC-010 point 7"
            )
        if component_l is not None and component_l != component_e:
            if component_l in fields_e:
                found.broken(
                    at,
                    f"marks the field `{component_l}` it held as its component field",
                    "DEC-010 point 7",
                )
            else:
                found.added(
                    at, f"names its component in the new field `{component_l}`", "DEC-010 point 7"
                )
        _arrangement(at, was.arrangement if was else {}, now.arrangement if now else {}, found)
        _ends(at, was.ends if was else None, now.ends if now else None, name in fields_e, found)


def _arrangement(
    where: str,
    earlier: Mapping[str, layout.ArrangementField],
    later: Mapping[str, layout.ArrangementField],
    found: _Found,
) -> None:
    for name, field_e in earlier.items():
        at = f"{where}, arrangement field `{name}`"
        if name not in later:
            found.broken(at, "is removed", "DEC-010 point 7")
            continue
        _named(
            at,
            "word",
            field_e.words,
            later[name].words,
            "DEC-010 point 7",
            "DEC-010 point 7",
            found,
        )
    for name in later:
        if name not in earlier:
            found.added(f"{where}, arrangement field `{name}`", "is new", "DEC-010 point 7")


def _ends(
    where: str,
    earlier: tuple[str, str] | None,
    later: tuple[str, str] | None,
    held: bool,
    found: _Found,
) -> None:
    """A list's end fields (DEC-011 point 6). `held` says whether the earlier version held
    the list field."""
    if earlier is not None and later != earlier:
        if later == (earlier[1], earlier[0]):
            found.broken(
                where,
                f"swaps its end fields: each tie starts at `{later[0]}`, where it started at "
                f"`{earlier[0]}`",
                "DEC-011 point 6",
            )
        for name in earlier:
            if later is None or name not in later:
                found.broken(f"{where}, end field `{name}`", "is removed", "DEC-011 point 6")
    if later is not None and earlier is None:
        if held:
            found.broken(
                where,
                f"declares the end fields `{later[0]}` and `{later[1]}` for a list it held",
                "DEC-011 point 6",
            )
        else:
            found.added(where, "is a new list of ties", "DEC-011 point 6")


def _layouts(
    where: str,
    earlier: layout.Component,
    later: layout.Component,
    data_e: Mapping[str, Any],
    data_l: Mapping[str, Any],
    found: _Found,
) -> None:
    """A top's layouts and their slots (DEC-003 point 6, DEC-009 point 7), whether its
    layouts are its pages' forms (DEC-010 point 7), its physical size (`_physical_size`),
    and whether it asks for a height, by a formula or through that size, which every page's
    size follows (DEC-022 point 8). A layout's height, said, changed or dropped, breaks
    nothing: a top that asks for no height needs one in each of its layouts, which
    validation holds to, and a page under a top that asks for one gets it."""
    if later.top and earlier.forms != later.forms:
        what = (
            "makes its layouts its pages' forms"
            if later.forms
            else "ceases to make its layouts its pages' forms"
        )
        found.broken(where, what, "DEC-010 point 7")
        return
    if later.top and not _physical_size(where, earlier, later, found):
        if earlier.asks_for("height") != later.asks_for("height"):
            what = (
                "comes to ask for a height"
                if later.asks_for("height")
                else "ceases to ask for a height"
            )
            found.broken(where, what, "DEC-022 point 8")
    layouts_e, layouts_l = _layouts_of(data_e), _layouts_of(data_l)
    _named(where, "layout", layouts_e, layouts_l, "DEC-003 point 6", "DEC-009 point 7", found)
    forms_e, forms_l = layout.page_forms(data_e), layout.page_forms(data_l)
    for name in layouts_e:
        if name not in layouts_l:
            continue
        at = f"{where}, layout `{name}`"
        if forms_e is not None and forms_l is not None:
            slots_e, required_e = forms_e.layouts[name]
            slots_l, required_l = forms_l.layouts[name]
            _fields(at, "slot", slots_e, slots_l, set(required_e), set(required_l), found)
            drawing_e, drawing_l = earlier.drawings.get(name), later.drawings.get(name)
            if drawing_e is not None and drawing_l is not None:
                runs_e = {slot: words for slot, words in drawing_e.runs.items() if slot in slots_e}
                runs_l = {slot: words for slot, words in drawing_l.runs.items() if slot in slots_l}
                _runs(at, "slot", runs_e, runs_l, slots_e, slots_l, found)
                _lists(at, drawing_e.list_fields, drawing_l.list_fields, slots_e, slots_l, found)
        else:
            slots_e, slots_l = layouts_e[name], layouts_l[name]
            _named(at, "slot", slots_e, slots_l, "DEC-003 point 6", "DEC-009 point 7", found)
            for slot in slots_e:
                if slot in slots_l and _holds_pages(slots_e[slot]) != _holds_pages(slots_l[slot]):
                    what = (
                        "comes to hold pages"
                        if _holds_pages(slots_l[slot])
                        else "ceases to hold pages"
                    )
                    found.broken(f"{at}, slot `{slot}`", what, "DEC-003 point 6")


def _physical_size(
    where: str, earlier: layout.Component, later: layout.Component, found: _Found
) -> bool:
    """A top's physical size (DEC-034 point 3): one it comes to declare, ceases to, or whose
    proportion changes breaks, since every page's height follows it. A size changed in the
    same proportion (`_same_proportion`) is a change of how its pages look, and breaks
    nothing: each page draws as before, only larger or smaller in print. Gives whether it
    found a break, so a change of the height the top asks for is not reported twice."""
    size_e, size_l = earlier.physical_size, later.physical_size
    if size_e is None and size_l is None:
        return False
    if size_e is None or size_l is None:
        what = "comes to declare" if size_e is None else "ceases to declare"
        found.broken(where, f"{what} a physical size", "DEC-034 point 3")
        return True
    if not _same_proportion(size_e, size_l):
        found.broken(
            where,
            f"changes its physical size's proportion, from {_mm(size_e)} to {_mm(size_l)}",
            "DEC-034 point 3",
        )
        return True
    return False


def _same_proportion(earlier: tuple[float, float], later: tuple[float, float]) -> bool:
    """Whether two physical sizes have one proportion within the rounding of whole
    millimetres: where one, scaled to the other's width, gives the other's height, each side
    of each size taken as any length within `MM_ROUNDING` of it. So A2 after A1, 420 by 594
    mm after 594 by 841 mm, keeps the proportion, though their sides, rounded, differ in it."""
    least_e, most_e = _proportions(earlier)
    least_l, most_l = _proportions(later)
    return least_e <= most_l and least_l <= most_e


def _proportions(size: tuple[float, float]) -> tuple[float, float]:
    """The least and the greatest proportion, height over width, of a size whose sides each
    lie within `MM_ROUNDING` of those it names."""
    width, height = size
    least = max(height - MM_ROUNDING, 0.0) / (width + MM_ROUNDING)
    most = math.inf if width <= MM_ROUNDING else (height + MM_ROUNDING) / (width - MM_ROUNDING)
    return least, most


def _mm(size: tuple[float, float]) -> str:
    """A physical size, as a message names it."""
    return f"{size[0]} by {size[1]} mm"


def _layouts_of(data: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Each layout a top declares, with its slots."""
    layouts = data.get("layouts")
    found = {}
    for name, decl in (layouts if isinstance(layouts, Mapping) else {}).items():
        slots = decl.get("slots") if isinstance(decl, Mapping) else None
        found[str(name)] = slots if isinstance(slots, Mapping) else {}
    return found


def _holds_pages(slot: Any) -> bool:
    return isinstance(slot, Mapping) and slot.get("pages") is True


# --- roles and pairs ----------------------------------------------------------------------------


def _roles_read(component: layout.Component) -> set[str]:
    """The roles a component reads directly, by their token paths: in its formulas, and as
    the paint or the style of a part, each branch of a switch included; a top's drawings of
    its layouts included."""
    found: set[str] = set()
    for read in component.formulas.values():
        if read is not None:
            found.update(ref.path for ref in read.references() if isinstance(ref, fm.Role))
    for part in component.parts.values():
        for key in (*layout.PAINTS, "style"):
            found.update(leaf for leaf in _leaves(part.props.get(key)) if names.is_token_path(leaf))
    for drawing in component.drawings.values():
        found |= _roles_read(drawing)
    return found


def _leaves(value: Any) -> list[Any]:
    """The values a property may take: itself, or each branch of its switch, at any depth."""
    if isinstance(value, Mapping) and layout.SWITCH in value:
        return [
            leaf for key, each in value.items() if key != layout.SWITCH for leaf in _leaves(each)
        ]
    return [value]


def _promised(read: FullRead) -> set[str]:
    """The library's own roles its stable and deprecated components read, directly or
    through a default, the default of each token such a component declares among them
    (DEC-008 point 7, DEC-035 point 4)."""
    scope = read.scope
    assert scope is not None
    found: set[str] = set()
    for name, component in read.components.items():
        if _status(read, name) not in PROMISED:
            continue
        for path in sorted(_roles_read(component) | set(_tokens_of(read, name))):
            step: str | None = path
            while step is not None and step not in found and scope.owner.get(step) == read.name:
                found.add(step)
                step = scope.default_of(step)
    return found


def _ends_shared(scope: tokens.Scope, path: str) -> bool:
    """Whether the role's chain of defaults ends at a shared role."""
    seen: set[str] = set()
    step: str | None = path
    while step is not None and step not in seen and step in scope.roles:
        if not scope.owner.get(step):
            return True
        seen.add(step)
        step = scope.default_of(step)
    return False


def _token_ends_shared(scope: tokens.Scope, token: tokens.ComponentToken) -> bool:
    """Whether a component token's chain of defaults ends at a shared role: followed from
    the token where the scope holds it, and else, as for a brand's own component, from the
    role its default aliases."""
    return _ends_shared(scope, token.path if token.path in scope.roles else token.default)


def _own_roles(earlier: FullRead, later: FullRead, found: _Found) -> None:
    """A library's own roles (DEC-003 point 6, DEC-008 point 7). One its stable or deprecated
    components read breaks where it is removed, changes type, or no longer ends its chain of
    defaults at a shared role where it did. A new one such a component reads breaks where its
    chain ends at none. Any other new own role is an addition."""
    scope_e, scope_l = earlier.scope, later.scope
    assert scope_e is not None and scope_l is not None
    own_e = {
        path: role
        for path, role in scope_e.roles.items()
        if scope_e.owner[path] == earlier.name and path not in scope_e.tokens
    }
    own_l = {
        path: role
        for path, role in scope_l.roles.items()
        if scope_l.owner[path] == later.name and path not in scope_l.tokens
    }
    promised_e, promised_l = _promised(earlier), _promised(later)
    for path, role in sorted(own_e.items()):
        at = f"role `{path}`"
        if path not in own_l:
            if path in promised_e:
                found.broken(at, "is removed", "DEC-003 point 6, DEC-008 point 7")
            continue
        if path in promised_e and own_l[path].type != role.type:
            found.broken(
                at,
                f"is of type `{own_l[path].type}`, where it was `{role.type}`",
                "DEC-003 point 6",
            )
        if (path in promised_e or path in promised_l) and (
            _ends_shared(scope_e, path) and not _ends_shared(scope_l, path)
        ):
            found.broken(
                at, "no longer ends its chain of defaults at a shared role", "DEC-008 point 7"
            )
    for path in sorted(set(own_l) - set(own_e)):
        at = f"role `{path}`"
        if path in promised_l and not _ends_shared(scope_l, path):
            found.broken(
                at,
                "is new, read by a stable or deprecated component, and its chain of defaults "
                "ends at no shared role",
                "DEC-008 point 7",
            )
        else:
            found.added(at, "is new", "DEC-008 point 7")


def _declared_pairs(read: FullRead) -> tuple[tokens.Pair, ...]:
    scope = read.scope
    assert scope is not None
    if read.name == FOUNDATIONS:
        return scope.foundations.pairs
    own = scope.libraries.get(read.name)
    return own.pairs if own is not None else ()


def _strictest(pairs: Iterable[tokens.Pair]) -> dict[frozenset[str], tokens.Pair]:
    """Each pair of roles, in either order, at the strictest level declared for it."""
    found: dict[frozenset[str], tokens.Pair] = {}
    for pair in pairs:
        key = frozenset((pair.text, pair.under))
        if key not in found or pair.minimum > found[key].minimum:
            found[key] = pair
    return found


def _pairs(earlier: FullRead, later: FullRead, found: _Found) -> None:
    """The pairs a library declares, the foundations' included, whatever reads them: a pair
    removed, or its level lowered, breaks; a new pair is an addition (DEC-008 point 7)."""
    pairs_e, pairs_l = _strictest(_declared_pairs(earlier)), _strictest(_declared_pairs(later))
    for key, pair in pairs_e.items():
        at = f"pair `{pair.text}` on `{pair.under}`"
        now = pairs_l.get(key)
        if now is None:
            found.broken(at, "is removed", "DEC-008 point 7")
        elif now.minimum < pair.minimum:
            found.broken(
                at, f"is at `{now.level}`, where it was at `{pair.level}`", "DEC-008 point 7"
            )
    for key, pair in pairs_l.items():
        if key not in pairs_e:
            found.added(f"pair `{pair.text}` on `{pair.under}`", "is new", "DEC-008 point 7")


# --- the foundations and brands -----------------------------------------------------------------


def _shared(earlier: FullRead, later: FullRead, found: _Found) -> None:
    """The foundations' shared roles, axes, colour families and shapes, whatever reads them
    (DEC-003 point 6, DEC-004 point 5, DEC-036 point 7). A new top group of the shared roles
    breaks, whatever its roles carry, since no library takes its name (DEC-004 point 7,
    DEC-025 point 10). A new picture role is an addition, since no brand owes it a value
    (DEC-025 point 4). A shape removed, or renamed, breaks, as a notation names it; a new one
    is an addition, and one whose outline is redrawn changes only how a piece looks."""
    assert earlier.scope is not None and later.scope is not None
    declared_e, declared_l = earlier.scope.foundations, later.scope.foundations
    for path, role in sorted(declared_e.roles.items()):
        at = f"shared role `{path}`"
        now = declared_l.roles.get(path)
        if now is None:
            found.broken(at, "is removed", "DEC-003 point 6")
            continue
        if now.type != role.type:
            found.broken(
                at, f"is of type `{now.type}`, where it was `{role.type}`", "DEC-004 point 5"
            )
        if role.default is not None and now.default is None:
            found.broken(
                at, "loses its default, so every brand gives it a value", "DEC-004 points 5 and 7"
            )
    for group in sorted(set(declared_l.top_groups) - set(declared_e.top_groups)):
        found.broken(
            f"shared group `{group}`",
            "is new, a name no library takes, so it fails a library already named so",
            "DEC-004 point 5",
        )
    for path in sorted(set(declared_l.roles) - set(declared_e.roles)):
        at = f"shared role `{path}`"
        if declared_l.roles[path].type == tokens.PICTURE:
            found.added(
                at, "is new, a picture role, which no brand owes a value", "DEC-004 point 5"
            )
        elif declared_l.roles[path].default is None:
            found.broken(at, "is new, with no default", "DEC-004 point 5")
        else:
            found.added(at, "is new, with a default", "DEC-004 point 5")
    _axes("shared axis", declared_e.axes, declared_l.axes, found)
    for name, members in sorted(declared_e.families.items()):
        at = f"colour family `{name}`"
        if name not in declared_l.families:
            found.broken(at, "is removed", "DEC-003 point 6")
            continue
        _named(
            at,
            "member",
            members,
            declared_l.families[name],
            "DEC-003 point 6",
            "DEC-003 point 1",
            found,
        )
    for name in sorted(set(declared_l.families) - set(declared_e.families)):
        found.added(f"colour family `{name}`", "is new", "DEC-003 point 1")
    for name in sorted(set(declared_e.shapes) - set(declared_l.shapes)):
        found.broken(f"shape `{name}`", "is removed", "DEC-036 point 7")
    for name in sorted(set(declared_l.shapes) - set(declared_e.shapes)):
        found.added(f"shape `{name}`", "is new", "DEC-036 point 7")


def _axes(
    noun: str, earlier: Mapping[str, tokens.Axis], later: Mapping[str, tokens.Axis], found: _Found
) -> None:
    """Axes and their modes (DEC-004 point 5): an axis removed, of another kind or with
    another default, and a mode removed, break; a new axis and a new mode are additions. A
    new shared axis is one too, since format 1 lets no brand hold an axis of its own that
    its name could meet. A brand's axes are those it has (`tokens.Brand.axes`), so a brand
    that comes to give a size adds an axis, and one that ceases to removes it."""
    for name, axis in sorted(earlier.items()):
        at = f"{noun} `{name}`"
        now = later.get(name)
        if now is None:
            found.broken(at, "is removed", "DEC-004 point 5")
            continue
        if now.kind != axis.kind:
            found.broken(
                at, f"is a {now.kind} axis, where it was a {axis.kind} axis", "DEC-004 point 5"
            )
        if now.default != axis.default:
            found.broken(
                at,
                f"takes `{now.default}` by default, where it took `{axis.default}`",
                "DEC-004 point 5",
            )
        _named(at, "mode", axis.modes, now.modes, "DEC-004 point 5", "DEC-004 point 5", found)
    for name in sorted(set(later) - set(earlier)):
        found.added(f"{noun} `{name}`", "is new", "DEC-004 point 5")


def _brand(earlier: FullRead, later: FullRead, found: _Found) -> None:
    """A brand's exported names (DEC-004 point 5): each token path it exports, its axes and
    modes, the sizes it gives among them, and the roles it opens to a brand built on it."""
    brand_e, brand_l = earlier.brand, later.brand
    for read, brand in ((earlier, brand_e), (later, brand_l)):
        if brand is None:
            why = "; ".join(finding.message for finding in read.findings) or "it could not be read"
            raise ComparisonError(f"{read.label} cannot be compared as a brand: {why}")
    assert brand_e is not None and brand_l is not None
    for path in brand_e.roles:
        at = f"exported token `{path}`"
        if path not in brand_l.roles:
            found.broken(at, "is removed", "DEC-004 point 5")
        elif brand_l.type_of(path) != brand_e.type_of(path):
            found.broken(
                at,
                f"is of type `{brand_l.type_of(path)}`, where it was `{brand_e.type_of(path)}`",
                "DEC-004 point 5",
            )
    for path in brand_l.roles:
        if path not in brand_e.roles:
            found.added(f"exported token `{path}`", "is new", "DEC-004 point 5")
    _axes("axis", brand_e.axes, brand_l.axes, found)
    for path in sorted(brand_e.opened - brand_l.opened):
        found.broken(f"open role `{path}`", "is no longer open", "DEC-004 point 5")
    for path in sorted(brand_l.opened - brand_e.opened):
        found.added(f"open role `{path}`", "is newly open", "DEC-004 point 5")
