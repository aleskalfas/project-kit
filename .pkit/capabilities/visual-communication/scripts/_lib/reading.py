"""One reading of every file the capability reads (DEC-006 point 6).

The same file must give the same value on every machine, so each kind is read one way:

- **YAML** by ruamel's safe loader, in pure Python, at YAML 1.2, with a timestamp read as
  the text it is written as. A document that names another YAML version in a `%YAML`
  directive is refused rather than read under other rules, so `no` is always text. A
  duplicate key, a second document, and any value JSON cannot hold (a binary, a set, a key
  that is not text, an infinity) are refused too: every value the capability reads is one
  JSON can hold.
- **JSON** as its value. A duplicate key, `NaN` and the infinities are refused.
- **Canonical text** of a value is the JSON Canonicalization Scheme (RFC 8785): keys in
  the order of their UTF-16 code units, no white space, strings escaped as ECMAScript's
  `JSON.stringify` escapes them, and numbers written as ECMAScript writes them. An integer
  beyond the doubles' exact range is refused, since JCS reads numbers as doubles.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.constructor import SafeConstructor
from ruamel.yaml.error import YAMLError

#: The one YAML version the capability reads.
YAML_VERSION = "1.2"

#: The largest integer a double holds exactly; JCS reads every number as a double.
_EXACT = 2**53 - 1

#: A `%YAML` directive, which only the lines before a document's first content may hold.
_DIRECTIVE = re.compile(r"^%YAML[ \t]+(\S+)")

#: A SHA-256 in lower-case hexadecimal.
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReadError(Exception):
    """A file, or a value, the capability cannot read under its one reading."""


class _Constructor(SafeConstructor):
    """The safe constructor, with a timestamp read as the text it is written as."""


_Constructor.add_constructor("tag:yaml.org,2002:timestamp", SafeConstructor.construct_yaml_str)


def _yaml() -> YAML:
    loader = YAML(typ="safe", pure=True)
    loader.Constructor = _Constructor
    return loader


def load_yaml(text: str, source: str = "") -> Any:
    """The value of the YAML document `text`. `source` names it in a refusal."""
    where = f"{source}: " if source else ""
    version = _declared_version(text)
    if version is not None and version != YAML_VERSION:
        raise ReadError(
            f"{where}declares YAML {version}; the capability reads YAML {YAML_VERSION} only, "
            f"so remove the `%YAML` line"
        )
    try:
        value = _yaml().load(text)
    except YAMLError as exc:
        raise ReadError(f"{where}does not parse as YAML: {_first_line(exc)}") from exc
    _check_json_value(value, where)
    return value


def read_yaml(path: Path) -> Any:
    """The value of the YAML file at `path`."""
    return load_yaml(_text(path), str(path))


def load_json(text: str, source: str = "") -> Any:
    """The value of the JSON document `text`. `source` names it in a refusal."""
    where = f"{source}: " if source else ""
    try:
        return json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ReadError(f"{where}does not parse as JSON: {exc}") from exc


def read_json(path: Path) -> Any:
    """The value of the JSON file at `path`."""
    return load_json(_text(path), str(path))


def canonical_json(value: Any) -> str:
    """The canonical text of `value` (RFC 8785). Raises ReadError for a value JSON cannot
    hold."""
    out: list[str] = []
    _write(value, out)
    return "".join(out)


def canonical_bytes(value: Any) -> bytes:
    """The canonical text of `value` as UTF-8, the bytes a hash is taken of."""
    try:
        return canonical_json(value).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ReadError(f"a string holds a lone surrogate, which UTF-8 cannot hold: {exc}") from exc


def sha256(data: bytes) -> str:
    """The SHA-256 of `data`, in lower-case hexadecimal."""
    return hashlib.sha256(data).hexdigest()


def is_sha256(value: object) -> bool:
    """Whether `value` takes the shape of a SHA-256 in lower-case hexadecimal."""
    return isinstance(value, str) and _SHA256.match(value) is not None


# --- YAML ---------------------------------------------------------------------------------------


def _text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except OSError as exc:
        raise ReadError(f"{path}: cannot be read: {exc.strerror or exc}") from exc
    except UnicodeDecodeError as exc:
        raise ReadError(f"{path}: is not UTF-8: {exc}") from exc


def _declared_version(text: str) -> str | None:
    """The version a `%YAML` directive names before the document's content, or None."""
    for line in text.lstrip("﻿").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _DIRECTIVE.match(line)
        if match:
            return match.group(1)
        if not line.startswith("%"):
            return None
    return None


def _first_line(exc: Exception) -> str:
    lines = [line.strip() for line in str(exc).splitlines() if line.strip()]
    return "; ".join(lines[:3]) if lines else type(exc).__name__


def _check_json_value(value: Any, where: str, at: str = "") -> None:
    """Refuse what JSON cannot hold, naming where it lies."""
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ReadError(f"{where}{at or 'the document'} is {value}, which JSON cannot hold")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ReadError(
                    f"{where}{at or 'the document'} has the key {key!r}, which is not text: "
                    f"quote it"
                )
            _check_json_value(item, where, f"{at}/{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_json_value(item, where, f"{at}/{index}")
        return
    raise ReadError(
        f"{where}{at or 'the document'} is a {type(value).__name__}, which JSON cannot hold"
    )


# --- JSON ---------------------------------------------------------------------------------------


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"the key {key!r} appears twice in one object")
        out[key] = value
    return out


def _no_constant(name: str) -> Any:
    raise ValueError(f"{name} is not a JSON number")


# --- canonical text -----------------------------------------------------------------------------


def _write(value: Any, out: list[str]) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, str):
        out.append(json.dumps(value, ensure_ascii=False))
    elif isinstance(value, (int, float)):
        out.append(_number(value))
    elif isinstance(value, Mapping):
        keys = list(value.keys())
        if not all(isinstance(key, str) for key in keys):
            raise ReadError(f"an object has a key that is not text: {keys!r}")
        out.append("{")
        for index, key in enumerate(sorted(keys, key=lambda k: k.encode("utf-16-be"))):
            if index:
                out.append(",")
            out.append(json.dumps(key, ensure_ascii=False))
            out.append(":")
            _write(value[key], out)
        out.append("}")
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        out.append("[")
        for index, item in enumerate(value):
            if index:
                out.append(",")
            _write(item, out)
        out.append("]")
    else:
        raise ReadError(f"a {type(value).__name__} has no JSON form")


def _number(value: int | float) -> str:
    """`value` as ECMAScript's `Number.prototype.toString` writes it (RFC 8785 section 3.2.2.3)."""
    if isinstance(value, int):
        if abs(value) > _EXACT:
            raise ReadError(f"the integer {value} lies beyond the range a double holds exactly")
        return str(value)
    if not math.isfinite(value):
        raise ReadError(f"{value} is not a JSON number")
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    digits, point = _shortest(abs(value))
    k = len(digits)
    if k <= point <= 21:
        return sign + digits + "0" * (point - k)
    if 0 < point <= 21:
        return sign + digits[:point] + "." + digits[point:]
    if -6 < point <= 0:
        return sign + "0." + "0" * -point + digits
    exponent = point - 1
    mark = "+" if exponent >= 0 else "-"
    mantissa = digits if k == 1 else digits[0] + "." + digits[1:]
    return f"{sign}{mantissa}e{mark}{abs(exponent)}"


def _shortest(value: float) -> tuple[str, int]:
    """The shortest digits that give back `value`, and where the decimal point falls
    among them: `value` is `0.<digits>` times ten to the power of the point."""
    text = repr(value)
    mantissa, _, exponent = text.partition("e")
    whole, _, fraction = mantissa.partition(".")
    digits = whole + fraction
    point = len(whole) + (int(exponent) if exponent else 0)
    stripped = digits.lstrip("0")
    point -= len(digits) - len(stripped)
    return stripped.rstrip("0"), point
