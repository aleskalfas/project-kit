"""The contract of a document a command prints for a program, held against what it prints
(ADR-097 points 2, 4, 5 and 7).

A document's contract is its own keys, what each means and the values of its sets. A
key or a value added misleads no caller; one that goes is a declared break, which
raises the document's version where it carries one; and a key or a value means one
thing for good. A `Contract` pins what a test can see of that from the output: each own
key with the types of its value, each set with its values, and each key and value that
went, with the version that dropped it. `check` holds the documents a test printed to
it, and fails:

- on a key the contract does not pin, or a value of a set it does not: pin it, as an
  addition (point 4);
- on a pinned key no document printed, or a value of a set that neither a document nor
  the code gives: it went, so the contract moves it to `gone` at a raised version, and
  the changeset declares the break at `major` (point 4);
- on a key or a value that went and is printed again: it never comes back to mean
  anything else (point 5), so only a review that finds its old meaning moves it back;
- on a value of another type than the key's: a key's type is part of its meaning
  (point 2), which never changes (point 5);
- on a version the contract does not pin, or a version raised with nothing gone and no
  reason recorded from before ADR-097 (point 4, "The version rises").

**Naming a key.** A key is named by its path: `base.ref` for a key of an object,
`findings[]` for the items of a list and `findings[].kind` for a key of each. A document
that is a list names its items `[]`, and a key of each `[].kind`. A mapping
keyed by data, such as one keyed by path or by a type's name (point 2, "A key that is
data is a value"), is named in `data`; its keys are values, and `types{}.component`
names a field of each entry. A key that carries another owner's payload is named in
`payloads`: its own type is pinned, and nothing inside it is (point 2, "A payload keeps
its owner's contract").

**Forms and shapes.** A document may have several *forms* (point 1), each with keys of
its own: a key that leaves one form goes from it, though another form still prints it.
An object one function builds wherever the document holds it, such as an artefact with
the rules that bind on it, is a *shape*: `refs` names each path that holds it, its keys
are pinned once, named `<shape>:<key>`, and a key no occurrence prints has gone from
all of them.

No test sees what a key means, so a change of meaning in place is review's (point 7).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

#: The key a document carries its own version in.
VERSION_KEY = "schema_version"

#: The types a key's value may take, by the name a contract writes them with.
TYPES = ("str", "int", "float", "bool", "null", "list", "object")

#: The type of a key whose value may be any JSON value, as a payload's may.
ANY = "|".join(TYPES)

#: A document as a command prints it: an object, or a list of its items.
Document = Mapping[str, Any] | list[Any]

#: The name of the items of a document that is a list.
ITEMS = "[]"


@dataclass(frozen=True)
class Form:
    """One form of a document, or one shape: each own key it prints, by path, with the
    types its value may take, written `"str|null"`; and each key that went from it, with
    the version that dropped it, `None` for a document that carries no version."""

    keys: Mapping[str, str]
    gone: Mapping[str, int | None] = field(default_factory=dict)


@dataclass(frozen=True)
class Contract:
    """What a document's contract holds that a test can see (ADR-097 point 2).

    - `name`: the command and the document, as a failure names it.
    - `forms`: each form by name, such as `answer` and `no answer`.
    - `version`: the version the document carries under `schema_version`, `None` for one
      that carries none.
    - `shapes`: each shape by name, its keys named from its own root; `refs`: each path
      that holds a shape, with the shape's name.
    - `sets`: each key whose values the contract lists, by name, with its values.
    - `gone_values`: each value that went from a set, by the set's name, with the version
      that dropped it.
    - `data`: the names of the mappings keyed by data.
    - `payloads`: the names of the keys that carry another owner's payload.
    - `raised_before`: each version raised before ADR-097 for a change of meaning, with
      what changed; such a change stands under the version that marked it (point 5,
      "From this record on").
    """

    name: str
    forms: Mapping[str, Form]
    version: int | None = None
    shapes: Mapping[str, Form] = field(default_factory=dict)
    refs: Mapping[str, str] = field(default_factory=dict)
    sets: Mapping[str, frozenset[str]] = field(default_factory=dict)
    gone_values: Mapping[str, Mapping[str, int | None]] = field(default_factory=dict)
    data: frozenset[str] = frozenset()
    payloads: frozenset[str] = frozenset()
    raised_before: Mapping[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class _Key:
    """One key printed: the shape it belongs to, `None` for the form's own, its path
    there, its name as a contract writes it, and its value."""

    shape: str | None
    path: str
    name: str
    value: Any


def check(
    contract: Contract,
    printed: Mapping[str, Iterable[Document]],
    *,
    enumerations: Mapping[str, Iterable[str]] | None = None,
) -> None:
    """Hold the documents `printed`, by form, to `contract`. `enumerations` gives, for a
    set, every value the code can give it, such as an enum's: a value it gives that the
    contract does not pin fails, and so does a pinned value it no longer gives. A set
    with no enumeration is held to the values the documents print."""
    problems = judge(contract, printed, enumerations=enumerations or {})
    assert not problems, f"{contract.name}:\n" + "\n".join(f"  - {p}" for p in problems)


def judge(
    contract: Contract,
    printed: Mapping[str, Iterable[Document]],
    *,
    enumerations: Mapping[str, Iterable[str]],
) -> list[str]:
    """What `check` fails on, one sentence each, empty when the documents hold."""
    problems = _contract_problems(contract)
    problems += [
        f"the contract has no form {form!r}" for form in sorted(set(printed) - set(contract.forms))
    ]
    seen_values: dict[str, set[str]] = {}
    seen_in_shapes: dict[str, set[str]] = {shape: set() for shape in contract.shapes}
    for form_name, form in contract.forms.items():
        documents = list(printed.get(form_name, ()))
        if not documents:
            problems.append(f"no document of the form {form_name!r} was printed")
            continue
        seen: set[str] = set()
        for document in documents:
            problems += _version_problems(contract, form_name, document)
            for key in _walk(contract, document):
                if key.shape is None:
                    seen.add(key.path)
                    scope, where = form, f"the form {form_name!r}"
                else:
                    seen_in_shapes[key.shape].add(key.path)
                    scope, where = contract.shapes[key.shape], f"the shape {key.shape!r}"
                problems += _key_problems(contract, scope, where, key, seen_values)
        problems += [
            _gone_unmarked(path, f"the form {form_name!r}")
            for path in sorted(set(form.keys) - seen)
        ]
    for shape_name, shape in sorted(contract.shapes.items()):
        problems += [
            _gone_unmarked(f"{shape_name}:{path}", f"the shape {shape_name!r}")
            for path in sorted(set(shape.keys) - seen_in_shapes[shape_name])
        ]
    problems += _set_problems(contract, seen_values, enumerations)
    return problems


def _gone_unmarked(name: str, where: str) -> str:
    return (
        f"`{name}` is pinned in {where} and no document printed it: a key that goes is a "
        f"breaking change, so move it to `gone` at a raised version and declare the break "
        f"at `major` (ADR-097 point 4)"
    )


def _set_problems(
    contract: Contract,
    seen_values: Mapping[str, set[str]],
    enumerations: Mapping[str, Iterable[str]],
) -> list[str]:
    problems: list[str] = []
    for name, values in sorted(contract.sets.items()):
        given = set(seen_values.get(name, set()))
        if name in enumerations:
            code = set(enumerations[name])
            problems += [
                f"`{name}` may take {value!r}, which its contract does not list: pin it, as a "
                f"value added (ADR-097 point 4)"
                for value in sorted(code - values)
            ]
            given |= code
        problems += [
            f"`{name}` lists {value!r}, which nothing gives: a value that goes is a breaking "
            f"change, so move it to `gone_values` at a raised version and declare the break "
            f"at `major` (ADR-097 point 4)"
            for value in sorted(values - given)
        ]
    return problems


def _names(contract: Contract) -> set[str]:
    """Every key the contract pins, by name."""
    names = {path for form in contract.forms.values() for path in form.keys}
    names |= {
        f"{shape_name}:{path}"
        for shape_name, shape in contract.shapes.items()
        for path in shape.keys
    }
    return names


def _contract_problems(contract: Contract) -> list[str]:
    """Where the contract contradicts itself, or raises a version for nothing."""
    problems: list[str] = []
    scopes = [(f"the form {name!r}", form) for name, form in contract.forms.items()]
    scopes += [(f"the shape {name!r}", shape) for name, shape in contract.shapes.items()]
    for where, scope in scopes:
        problems += [
            f"`{path}` is pinned and gone at once in {where}"
            for path in sorted(set(scope.keys) & set(scope.gone))
        ]
        problems += [
            f"`{path}` is typed {kind!r} in {where}, which is not one of {', '.join(TYPES)}"
            for path, types in sorted(scope.keys.items())
            for kind in types.split("|")
            if kind not in TYPES
        ]
    every = _names(contract)
    problems += [
        f"`{name}` is named in `{part}` and pinned nowhere"
        for part, names in (
            ("sets", set(contract.sets)),
            ("data", set(contract.data)),
            ("payloads", set(contract.payloads)),
            ("refs", set(contract.refs)),
        )
        for name in sorted(names - every)
    ]
    problems += [
        f"`{name}` holds the shape {shape!r}, which the contract does not define"
        for name, shape in sorted(contract.refs.items())
        if shape not in contract.shapes
    ]
    problems += [
        f"`{name}` lists {value!r} as a value and as gone at once"
        for name, gone in sorted(contract.gone_values.items())
        for value in sorted(set(gone) & contract.sets.get(name, frozenset()))
    ]
    return problems + _raise_problems(contract, [scope for _where, scope in scopes])


def _raise_problems(contract: Contract, scopes: list[Form]) -> list[str]:
    """Where a version names a raise the document's version does not bear out."""
    raised = [version for scope in scopes for version in scope.gone.values()]
    raised += [version for gone in contract.gone_values.values() for version in gone.values()]
    named = {version for version in raised if version is not None}
    if contract.version is None:
        if named or contract.raised_before:
            return ["a document with no version names a version raised"]
        return []
    problems = [
        f"version {version} dropped a key or a value, and the document is at version "
        f"{contract.version}: the version rises in the change that drops it (ADR-097 point 4)"
        for version in sorted(named)
        if not 1 < version <= contract.version
    ]
    if None in raised:
        problems.append("a key or a value went with no version named, from a versioned document")
    problems += [
        f"version {version} was raised with no key or value gone: the version rises only "
        f"when one goes (ADR-097 point 4)"
        for version in range(2, contract.version + 1)
        if version not in named and version not in contract.raised_before
    ]
    return problems


def _version_problems(contract: Contract, form: str, document: Document) -> list[str]:
    if contract.version is None:
        return []
    found = document.get(VERSION_KEY) if isinstance(document, Mapping) else None
    if found == contract.version and type(found) is int:
        return []
    return [
        f"a document of the form {form!r} carries {VERSION_KEY} {found!r}, and the contract "
        f"is pinned at version {contract.version}"
    ]


def _key_problems(
    contract: Contract, scope: Form, where: str, key: _Key, seen_values: dict[str, set[str]]
) -> list[str]:
    if key.path in scope.gone:
        return [
            f"`{key.name}` went from {where} at version {scope.gone[key.path]} and is "
            f"printed again: a key that went never comes back to name anything else "
            f"(ADR-097 point 5)"
        ]
    if key.path not in scope.keys:
        return [
            f"`{key.name}` is printed in {where} and not pinned: an own key is in the "
            f"contract (ADR-097 point 2), so pin it, as a key added (point 4)"
        ]
    kind = type_of(key.value)
    if kind not in scope.keys[key.path].split("|"):
        return [
            f"`{key.name}` printed a {kind}, and its contract types it {scope.keys[key.path]}: "
            f"a key's type is part of its meaning (ADR-097 point 2), which never changes "
            f"(point 5)"
        ]
    if key.name not in contract.sets or not isinstance(key.value, str):
        return []
    seen_values.setdefault(key.name, set()).add(key.value)
    gone = contract.gone_values.get(key.name, {})
    if key.value in gone:
        return [
            f"`{key.name}` printed {key.value!r}, which went at version {gone[key.value]}: a "
            f"value that went never comes back to mean anything else (ADR-097 point 5)"
        ]
    if key.value not in contract.sets[key.name]:
        return [
            f"`{key.name}` printed {key.value!r}, which its contract does not list: pin it, as "
            f"a value added (ADR-097 point 4)"
        ]
    return []


def _walk(contract: Contract, document: Document) -> Iterator[_Key]:
    """Each own key of `document` with its value, the document's own keys first: of a
    list, each item as `[]`."""
    if isinstance(document, list):
        for item in document:
            yield from _walk_value(contract, None, ITEMS, item)
        return
    for key, value in document.items():
        yield from _walk_value(contract, None, str(key), value)


def _walk_value(contract: Contract, shape: str | None, path: str, value: Any) -> Iterator[_Key]:
    name = path if shape is None else f"{shape}:{path}"
    yield _Key(shape, path, name, value)
    if name in contract.payloads:
        return
    held = contract.refs.get(name)
    if held is not None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                yield from _walk_value(contract, held, str(key), item)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            inner = f"{path}{{}}" if name in contract.data else f"{path}.{key}"
            yield from _walk_value(contract, shape, inner, item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_value(contract, shape, f"{path}[]", item)


def type_of(value: Any) -> str:
    """The name a contract types `value` by."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, Mapping):
        return "object"
    raise TypeError(f"a document holds JSON values only, not {type(value).__name__}")


def shape(contract: Contract, documents: Iterable[Document]) -> dict[str, str]:
    """Each key the documents print, by name, with the types they print it with: what a
    contract pins, to read before writing one by hand."""
    found: dict[str, set[str]] = {}
    for document in documents:
        for key in _walk(contract, document):
            found.setdefault(key.name, set()).add(type_of(key.value))
    return {name: "|".join(sorted(kinds)) for name, kinds in sorted(found.items())}
