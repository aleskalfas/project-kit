"""A small reader for design tokens in the DTCG format (`$value`, `$type`, aliases `{a.b}`).

Files are merged in order, later files winning per token. A group's `$type` passes to the
tokens below it. Aliases are resolved after merging, inside composite values too, and a loop of
aliases is refused, naming it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ALIAS = re.compile(r"^\{([^{}]+)\}$")


class TokenError(ValueError):
    pass


class Token:
    __slots__ = ("path", "type", "value", "extensions", "source")

    def __init__(self, path, type_, value, extensions, source):
        self.path, self.type, self.value, self.extensions, self.source = path, type_, value, extensions, source


def read_file(path: Path) -> dict[str, Token]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: dict[str, Token] = {}

    def walk(node, prefix, inherited):
        group_type = node.get("$type", inherited)
        if "$value" in node:
            out[prefix] = Token(prefix, group_type, node["$value"], node.get("$extensions", {}), str(path))
            return
        for key, child in node.items():
            if key.startswith("$"):
                continue
            if not isinstance(child, dict):
                raise TokenError(f"{path}: {prefix + '.' if prefix else ''}{key} is neither a group nor a token")
            walk(child, f"{prefix}.{key}" if prefix else key, group_type)

    walk(data, "", None)
    return out


class TokenSet:
    """The tokens of one brand for one font profile, theme and mode."""

    def __init__(self, files: list[Path]):
        self.files = [Path(f) for f in files]
        self.tokens: dict[str, Token] = {}
        for f in self.files:
            self.tokens.update(read_file(f))
        self._resolved: dict[str, object] = {}

    def __contains__(self, path):
        return path in self.tokens

    def raw(self, path) -> Token:
        if path not in self.tokens:
            raise TokenError(f"no token {path}")
        return self.tokens[path]

    def resolve(self, path, _seen=()):
        if path in self._resolved:
            return self._resolved[path]
        if path in _seen:
            raise TokenError("alias loop: " + " -> ".join((*_seen, path)))
        tok = self.raw(path)
        value = self._resolve_value(tok.value, (*_seen, path))
        self._resolved[path] = value
        return value

    def _resolve_value(self, value, seen):
        if isinstance(value, str):
            m = ALIAS.match(value)
            if m:
                return self.resolve(m.group(1), seen)
            return value
        if isinstance(value, dict):
            return {k: self._resolve_value(v, seen) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_value(v, seen) for v in value]
        return value

    def type_of(self, path):
        tok = self.raw(path)
        if tok.type:
            return tok.type
        m = ALIAS.match(tok.value) if isinstance(tok.value, str) else None
        return self.type_of(m.group(1)) if m else None

    def number(self, path) -> float:
        return as_number(self.resolve(path), path)

    def colour(self, path) -> str:
        return as_colour(self.resolve(path), path)

    def extensions(self, path) -> dict:
        """The `$extensions` of a token, following its alias to the token that holds them."""
        tok = self.raw(path)
        if tok.extensions:
            return tok.extensions
        m = ALIAS.match(tok.value) if isinstance(tok.value, str) else None
        return self.extensions(m.group(1)) if m else {}

    def paths(self, prefix=""):
        return sorted(p for p in self.tokens if p.startswith(prefix))


def as_number(value, path="") -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict) and "value" in value:
        return float(value["value"])
    if isinstance(value, str):
        m = re.match(r"^(-?\d+(?:\.\d+)?)(px)?$", value.strip())
        if m:
            return float(m.group(1))
    raise TokenError(f"token {path} is not a number: {value!r}")


def as_colour(value, path="") -> str:
    if isinstance(value, str) and re.match(r"^#[0-9A-Fa-f]{6}$", value):
        return value.lower()
    if isinstance(value, dict) and isinstance(value.get("hex"), str):
        return value["hex"].lower()
    if isinstance(value, dict) and value.get("colorSpace") == "srgb":
        r, g, b = (round(c * 255) for c in value["components"][:3])
        return f"#{r:02x}{g:02x}{b:02x}"
    raise TokenError(f"token {path} is not a colour: {value!r}")
