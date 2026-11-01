"""The formula language: numbers, + - * /, parentheses, tokens, references, min, max, round.

A formula is a string starting with `=`. Nothing else is allowed: no comparison, no
condition, no loop, no function of one's own (point 19). A name is a reference the
evaluator resolves (a part's frame, a value, `width`, `index`, ...); `@a.b` is a token.
Put spaces around a minus that follows a token or a name with a hyphen in it.
"""

from __future__ import annotations

import re
from functools import lru_cache

FUNCTIONS = {"min": min, "max": max, "round": round}

_TOKEN = re.compile(
    r"\s*(?:"
    r"(?P<num>\d+(?:\.\d+)?)"
    r"|(?P<tok>@[A-Za-z0-9_][A-Za-z0-9_.\-]*[A-Za-z0-9_])"
    r"|(?P<name>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*)"
    r"|(?P<op>[-+*/(),×÷−])"
    r")"
)


class FormulaError(ValueError):
    pass


def is_formula(value) -> bool:
    return isinstance(value, str) and value.startswith("=")


def _lex(src: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    src = src.rstrip()
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        if not m or m.end() == pos:
            raise FormulaError(f"cannot read {src[pos:]!r} in {src!r}")
        kind = m.lastgroup
        text = m.group(kind)
        if kind == "op":
            text = {"×": "*", "÷": "/", "−": "-"}.get(text, text)
        out.append((kind, text))
        pos = m.end()
    return out


@lru_cache(maxsize=None)
def parse(src: str):
    """Parse a formula (with or without its leading '=') into a small tree."""
    text = src[1:] if src.startswith("=") else src
    toks = _lex(text)
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else (None, None)

    def take(expected=None):
        nonlocal pos
        tok = peek()
        if tok[0] is None or (expected and tok[1] != expected):
            raise FormulaError(f"expected {expected or 'more'} in {src!r}")
        pos += 1
        return tok

    def expr():
        node = term()
        while peek()[1] in ("+", "-"):
            op = take()[1]
            node = ("bin", op, node, term())
        return node

    def term():
        node = unary()
        while peek()[1] in ("*", "/"):
            op = take()[1]
            node = ("bin", op, node, unary())
        return node

    def unary():
        if peek()[1] == "-":
            take()
            return ("neg", unary())
        return primary()

    def primary():
        kind, text = take()
        if kind == "num":
            return ("num", float(text))
        if kind == "tok":
            return ("tok", text[1:])
        if kind == "name":
            if peek()[1] == "(":
                if text not in FUNCTIONS:
                    raise FormulaError(f"unknown function {text}() in {src!r}; only min, max and round")
                take("(")
                args = [expr()]
                while peek()[1] == ",":
                    take(",")
                    args.append(expr())
                take(")")
                return ("call", text, tuple(args))
            return ("ref", text)
        if text == "(":
            node = expr()
            take(")")
            return node
        raise FormulaError(f"unexpected {text!r} in {src!r}")

    tree = expr()
    if pos != len(toks):
        raise FormulaError(f"unexpected {toks[pos][1]!r} in {src!r}")
    return tree


def references(src: str) -> list[str]:
    out = []

    def walk(node):
        if node[0] == "ref":
            out.append(node[1])
        elif node[0] == "bin":
            walk(node[2])
            walk(node[3])
        elif node[0] == "neg":
            walk(node[1])
        elif node[0] == "call":
            for arg in node[2]:
                walk(arg)

    walk(parse(src))
    return out


def evaluate(src: str, ref, token) -> float:
    """Evaluate a formula; `ref(name)` and `token(path)` return numbers."""

    def ev(node):
        kind = node[0]
        if kind == "num":
            return node[1]
        if kind == "tok":
            return float(token(node[1]))
        if kind == "ref":
            return float(ref(node[1]))
        if kind == "neg":
            return -ev(node[1])
        if kind == "call":
            return float(FUNCTIONS[node[1]](*(ev(a) for a in node[2])))
        a, b = ev(node[2]), ev(node[3])
        op = node[1]
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if b == 0:
            raise FormulaError(f"division by zero in {src!r}")
        return a / b

    return ev(parse(src))
