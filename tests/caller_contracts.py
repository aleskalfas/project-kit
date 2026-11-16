"""How a caller project-kit ships reads a document a command prints (ADR-097 points 3 and 7).

A caller finds what it needs by a key, and never takes what it does not know for what it
knows. It ignores a key it does not read. It reads a key it needs and does not find, a
null its contract does not explain, and a value of a set it does not know as the contract
says, or as *could not tell* where the contract says nothing. It refuses a version it
does not know, and reads a run that gave no document as no answer.

`check` hands a caller one document it reads, and each document made from it:

- **a key it does not know** in every object of the document: the reading is the same;
- **for each own key it read,** the document without that key, and with it null where the
  contract never prints it null: the reading says it could not tell;
- **for each key of a set it read,** the document with a value the set does not list: the
  same;
- **a version it does not know:** the reading says it could not tell, as a refusal does;
- **no document at all:** the same.

Where the contract names another reading for one of them, such as a document without
`schema_version` read as version `1`, the caller names it in `readings`.

**Which keys a caller reads** is seen, never listed by hand: every object of the document it
is handed records each key looked up in it, present or not. So a key the caller reads and
defaults when it is missing is found, though its reading may not change. Only an own key
is varied: a mapping keyed by data and another owner's payload are the contract's `data`
and `payloads`, as `tests/document_contracts.py` names them, and their keys are values.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from tests.document_contracts import VERSION_KEY, Contract

#: A key no contract pins, added to every object of a document.
UNKNOWN_KEY = "zz_a_key_no_caller_knows"

#: A value no set lists.
UNKNOWN_VALUE = "zz-a-value-no-caller-knows"

#: A version no caller knows.
UNKNOWN_VERSION = 9999

#: The ways a key is varied, by the word a reading is named with in `Caller.readings`.
MISSING, NULL, UNKNOWN = "missing", "null", "unknown"

#: Where a key lies in a document: the keys and the indices that lead to it.
Locator = tuple[str | int, ...]


@dataclass(frozen=True)
class Raised:
    """A reading that raised, in place of a value it returned."""

    error: BaseException

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Raised)
            and type(other.error) is type(self.error)
            and str(other.error) == str(self.error)
        )

    def __hash__(self) -> int:
        return hash((type(self.error), str(self.error)))


#: What a caller gives back for one document: what it returned, or `Raised`.
Outcome = Any

#: A reading the contract names: whether `outcome`, read from a varied document, reads
#: as the contract says, given `base`, read from the document it was made from.
Reading = Callable[[Outcome, Outcome], bool]


@dataclass(frozen=True)
class Caller:
    """One caller of one document (ADR-097 point 7).

    - `name`: the caller and the document, as a failure names them.
    - `contract`: the document's contract, which names the sets, which values the contract
      prints null, the mappings keyed by data and the payloads.
    - `read`: the caller's reading of a document, as a mapping.
    - `untold`: whether an outcome says the caller could not tell: a refusal it raised, or
      a value that says so.
    - `nothing`: the caller's reading when the command gives no document, such as a run
      that exits 1 and prints nothing.
    - `sets`: each key the caller reads as a set beyond those the contract lists, such as
      a kind of entry it skips where it does not know it, with the values it knows.
    - `readings`: each reading other than could not tell, by the way the key is varied
      and its name, `"missing:schema_version"`, `"null:<name>"` or `"unknown:<name>"`:
      one the contract names, or, for a value the caller does not know, one where
      nothing the caller decides rests on the value, so it learns nothing from it.
    - `compared`: what of an outcome two readings are compared on, where an outcome holds
      something that does not compare.
    """

    name: str
    contract: Contract
    read: Callable[[Mapping[str, Any]], Any]
    untold: Callable[[Outcome], bool]
    nothing: Callable[[], Any]
    sets: Mapping[str, frozenset[str]] = field(default_factory=dict)
    readings: Mapping[str, Reading] = field(default_factory=dict)
    compared: Callable[[Outcome], Any] = lambda outcome: outcome


def raises(*errors: type[BaseException]) -> Callable[[Outcome], bool]:
    """An `untold` that holds where the caller raised one of `errors`."""
    return lambda outcome: isinstance(outcome, Raised) and isinstance(outcome.error, errors)


def same(outcome: Outcome, base: Outcome) -> bool:
    """A reading the contract names that gives what the document it was made from gives."""
    return outcome == base


def check(caller: Caller, document: Mapping[str, Any]) -> None:
    """Hold `caller` to ADR-097 point 3 on `document` and on each made from it."""
    problems = judge(caller, document)
    assert not problems, f"{caller.name}:\n" + "\n".join(f"  - {p}" for p in problems)


def judge(caller: Caller, document: Mapping[str, Any]) -> list[str]:
    """What `check` fails on, one sentence each, empty when the caller holds."""
    log: list[tuple[str, Locator]] = []
    base = _outcome(caller.read, _watch(caller.contract, document, log))
    if caller.untold(base):
        return [f"it could not tell from the document it was handed: {_said(base)}"]
    problems: list[str] = []
    added = _outcome(caller.read, _with_unknown_keys(caller.contract, document))
    if caller.compared(added) != caller.compared(base):
        problems.append(
            f"a key it does not know, `{UNKNOWN_KEY}`, changed its reading, to {_said(added)}: "
            f"a caller ignores a key it does not read (ADR-097 point 3)"
        )
    pinned = _pinned(caller.contract)
    sets = {**caller.contract.sets, **caller.sets}
    seen: set[str] = set()
    for name, at in log:
        if name in seen or name.endswith("{}"):
            continue
        seen.add(name)
        if name not in pinned:
            problems.append(f"it reads `{name}`, which the document's contract does not pin")
            continue
        if not _holds(document, at):
            continue
        for way, varied_name, varied in _variants(sets, pinned[name], name, document, at):
            problems += _judged(caller, base, way, varied_name, _outcome(caller.read, varied))
    if caller.contract.version is not None:
        version = {**document, VERSION_KEY: UNKNOWN_VERSION}
        problems += _judged(
            caller, base, UNKNOWN, VERSION_KEY, _outcome(caller.read, version), version=True
        )
    nothing = _outcome(lambda _: caller.nothing(), {})
    if not caller.untold(nothing):
        problems.append(
            f"a run that gave no document read as {_said(nothing)}: a caller reads no "
            f"document as no answer (ADR-097 point 3)"
        )
    return problems


def _variants(
    sets: Mapping[str, frozenset[str]],
    types: str,
    name: str,
    document: Mapping[str, Any],
    at: Locator,
) -> Iterator[tuple[str, str, Mapping[str, Any]]]:
    """Each document made from `document` by varying the key `name` at `at`, with the
    way it is varied and the name the variation reads under: without it, null where the
    contract never prints it null, and with a value its set does not list. A list whose
    items are a set gains such a value, beside those it holds, under `<name>[]`."""
    yield MISSING, name, _varied(document, at, delete=True)
    if "null" not in types.split("|"):
        yield NULL, name, _varied(document, at, value=None)
    found = _at(document, at)
    if name in sets and isinstance(found, str):
        yield UNKNOWN, name, _varied(document, at, value=UNKNOWN_VALUE)
    if f"{name}[]" in sets and isinstance(found, list):
        yield UNKNOWN, f"{name}[]", _varied(document, at, value=[*found, UNKNOWN_VALUE])


def _judged(
    caller: Caller,
    base: Outcome,
    way: str,
    name: str,
    outcome: Outcome,
    *,
    version: bool = False,
) -> list[str]:
    """The problem, if any, with how `caller` read `name` varied `way`."""
    named = caller.readings.get(f"{way}:{name}")
    if named is not None:
        if named(outcome, base):
            return []
        return [f"`{name}` {_how(way, version)} read as {_said(outcome)}, not as its contract says"]
    if caller.untold(outcome):
        return []
    return [
        f"`{name}` {_how(way, version)} read as {_said(outcome)}: where its contract names no "
        f"reading, a caller reads it as could not tell (ADR-097 point 3)"
    ]


def _how(way: str, version: bool) -> str:
    if version:
        return f"at version {UNKNOWN_VERSION}, one it does not know,"
    return {
        MISSING: "left out",
        NULL: "null, which its contract does not explain,",
        UNKNOWN: f"at {UNKNOWN_VALUE!r}, a value its set does not list,",
    }[way]


def _said(outcome: Outcome) -> str:
    if isinstance(outcome, Raised):
        return f"raising {type(outcome.error).__name__}: {outcome.error}"
    text = repr(outcome)
    return text if len(text) <= 160 else f"{text[:157]}..."


def _outcome(read: Callable[[Mapping[str, Any]], Any], document: Mapping[str, Any]) -> Outcome:
    try:
        return read(document)
    except Exception as exc:
        return Raised(exc)


# --- the names of a document's keys, as `tests/document_contracts.py` writes them ---------


def _pinned(contract: Contract) -> dict[str, str]:
    """Every key the contract pins, by name, with every type it is printed with."""
    found: dict[str, set[str]] = {}
    for form in contract.forms.values():
        for path, types in form.keys.items():
            found.setdefault(path, set()).update(types.split("|"))
    for shape_name, shape in contract.shapes.items():
        for path, types in shape.keys.items():
            found.setdefault(f"{shape_name}:{path}", set()).update(types.split("|"))
    return {name: "|".join(sorted(types)) for name, types in found.items()}


def _name(shape: str | None, path: str) -> str:
    return path if shape is None else f"{shape}:{path}"


def _child(contract: Contract, shape: str | None, path: str, key: str) -> tuple[str | None, str]:
    """The shape and the path of the key `key` of the object at `path`: `""` is the
    document."""
    if not path:
        return None, key
    held = contract.refs.get(_name(shape, path))
    if held is not None:
        return held, key
    if _name(shape, path) in contract.data:
        return shape, f"{path}{{}}"
    return shape, f"{path}.{key}"


class _Watched(dict[str, Any]):
    """An object of a document that records the name of each key looked up in it, and
    where it lies, present or not."""

    def __init__(
        self,
        items: Mapping[str, Any],
        contract: Contract,
        shape: str | None,
        path: str,
        at: Locator,
        log: list[tuple[str, Locator]],
    ) -> None:
        super().__init__(items)
        self._contract, self._shape, self._path, self._at, self._log = (
            contract,
            shape,
            path,
            at,
            log,
        )

    def _saw(self, key: object) -> None:
        if isinstance(key, str):
            shape, path = _child(self._contract, self._shape, self._path, key)
            self._log.append((_name(shape, path), (*self._at, key)))

    def _saw_all(self) -> None:
        for key in super().__iter__():
            self._saw(key)

    def __getitem__(self, key: str) -> Any:
        self._saw(key)
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        self._saw(key)
        return super().get(key, default)

    def __contains__(self, key: object) -> bool:
        self._saw(key)
        return super().__contains__(key)

    def __iter__(self) -> Iterator[str]:
        self._saw_all()
        return super().__iter__()

    def keys(self) -> Any:
        self._saw_all()
        return super().keys()

    def values(self) -> Any:
        self._saw_all()
        return super().values()

    def items(self) -> Any:
        self._saw_all()
        return super().items()


def _watch(contract: Contract, document: Mapping[str, Any], log: list[tuple[str, Locator]]) -> Any:
    """`document`, every object of it but a payload's watched (`_Watched`)."""

    def wrap(value: Any, shape: str | None, path: str, at: Locator) -> Any:
        if path and _name(shape, path) in contract.payloads:
            return value
        if isinstance(value, Mapping):
            items: dict[str, Any] = {}
            for key, item in value.items():
                inner_shape, inner = _child(contract, shape, path, str(key))
                items[str(key)] = wrap(item, inner_shape, inner, (*at, str(key)))
            return _Watched(items, contract, shape, path, at, log)
        if isinstance(value, list):
            return [wrap(item, shape, f"{path}[]", (*at, i)) for i, item in enumerate(value)]
        return value

    return wrap(document, None, "", ())


def _with_unknown_keys(contract: Contract, document: Mapping[str, Any]) -> dict[str, Any]:
    """`document` with `UNKNOWN_KEY` in every object of it whose keys are own keys."""

    def add(value: Any, shape: str | None, path: str) -> Any:
        name = _name(shape, path)
        if path and name in contract.payloads:
            return copy.deepcopy(value)
        if isinstance(value, Mapping):
            items: dict[str, Any] = {}
            for key, item in value.items():
                inner_shape, inner = _child(contract, shape, path, str(key))
                items[str(key)] = add(item, inner_shape, inner)
            if not path or name not in contract.data:
                items[UNKNOWN_KEY] = "a value of a key no caller knows"
            return items
        if isinstance(value, list):
            return [add(item, shape, f"{path}[]") for item in value]
        return value

    return add(document, None, "")


def _at(document: Any, at: Locator) -> Any:
    for step in at:
        document = document[step]
    return document


def _holds(document: Any, at: Locator) -> bool:
    """Whether `document` holds a key at `at`."""
    found: Any = document
    for step in at:
        if isinstance(step, int):
            if not isinstance(found, list) or step >= len(found):
                return False
            found = found[step]
        elif isinstance(found, Mapping) and step in found:
            found = found[step]
        else:
            return False
    return True


def _varied(
    document: Mapping[str, Any], at: Locator, *, delete: bool = False, value: Any = None
) -> dict[str, Any]:
    """A copy of `document` without the key at `at`, or with `value` there."""
    varied = copy.deepcopy(dict(document))
    parent = _at(varied, at[:-1])
    if delete:
        del parent[at[-1]]
    else:
        parent[at[-1]] = value
    return varied
