"""The formula and reference grammar, with dimensions (visual-communication DEC-005 points 1, 3).

A *formula* is a string that starts with `=` and computes one number. It holds:

- numbers with no unit (`2`, `0.5`), the four operations `+ - * /` and parentheses;
- the functions `min(a, b, …)`, `max(a, b, …)` and `round(a)`, known by the parenthesis
  that follows the name at once;
- `@<token path>`: a role, such as `@space.2`; its value is a length or a number;
- the engine's names, each marked with `:`, a mark no name holds, so the engine can add
  names later without taking any from authors: `:width` and `:height`, the size the
  component gets, and `:index` and `:count`, an item's place among the items its list
  draws (from 1) and how many it draws;
- a value of the component, by its name alone: `gap`;
- a *path*: a part, then each exposed part below it, one name a step, then the
  measure of the frame it reads, one of `x y width height right bottom center
  middle`. The last segment is always the measure, so a part named `width` is still
  read as `width.x`. A step into a list follows the list's part as `<list>:first`,
  `<list>:last` or `<list>[<id>]`. A picture's exposed point reads as a part of zero
  size: `<part>.<point>.x`. A path may start with `{<option>}`, the path an option
  gives when it names an item, or an item's point: `={at}.x + @space.2`.

A binary minus has a space on each side: names hold hyphens, so `a-b` is one name.

**Dimensions.** Each term has a dimension, a power of length: a number has none, a
length one. A sum's terms share one dimension, so a number is never added to a
length; a product adds the powers and a quotient subtracts them. The caller says what
each reference's dimension is (`dimension`), and what each reference's value is
(`evaluate`). A formula never compares, chooses, loops or holds text.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

#: The measures a path may end in.
MEASURES = ("x", "y", "width", "height", "right", "bottom", "center", "middle")

#: The engine's names, without their mark.
ENGINE_NAMES = ("width", "height", "index", "count")

#: The functions a formula may call, each with the least and the most arguments it takes.
FUNCTIONS = {"min": (2, None), "max": (2, None), "round": (1, 1)}

#: The dimension of a number with no unit, and of a length (powers of length).
NUMBER = 0
LENGTH = 1

_NAME = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
_ID = r"[A-Za-z][A-Za-z0-9_-]*"
_SEGMENT = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_STEP = rf"{_NAME}(?::first|:last|\[{_ID}\])?"
_TOKEN = re.compile(
    rf"(?P<number>[0-9]+(?:\.[0-9]+)?)"
    rf"|(?P<role>@{_SEGMENT}(?:\.{_SEGMENT})*)"
    rf"|(?P<engine>:[a-z]+)"
    rf"|(?P<function>(?:min|max|round)\()"
    rf"|(?P<path>(?:\{{{_NAME}\}}|{_STEP})(?:\.{_STEP})*)"
    rf"|(?P<op>[-+*/(),])"
)
_STEP_PARTS = re.compile(rf"^({_NAME})(?::(first|last)|\[({_ID})\])?$")


class FormulaError(ValueError):
    """A formula that cannot be read, or whose dimensions do not agree. The message names
    the formula and says why."""

    def __init__(self, formula: str, why: str) -> None:
        super().__init__(f"the formula `{formula}` {why}")
        self.formula = formula
        self.why = why


class DivisionByZero(FormulaError):
    """A formula that divides by zero, found when it is computed."""


# --- references ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Engine:
    """One of the engine's names: `:width`, `:height`, `:index`, `:count`."""

    name: str

    def __str__(self) -> str:
        return f":{self.name}"


@dataclass(frozen=True)
class Role:
    """A role, by its token path."""

    path: str

    def __str__(self) -> str:
        return f"@{self.path}"


@dataclass(frozen=True)
class Value:
    """A value the component names in `values`."""

    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Step:
    """One step of a path: a part or an exposed part, and, for a list, the item:
    `"first"`, `"last"`, or an id."""

    name: str
    item: str | None = None
    by_id: bool = False

    def __str__(self) -> str:
        if self.item is None:
            return self.name
        return f"{self.name}[{self.item}]" if self.by_id else f"{self.name}:{self.item}"


@dataclass(frozen=True)
class Path:
    """A path to a frame or a point, and the measure it reads; `option` when it starts
    with the path an option gives."""

    option: str | None
    steps: tuple[Step, ...]
    measure: str

    def __str__(self) -> str:
        head = [f"{{{self.option}}}"] if self.option else []
        return ".".join([*head, *(str(step) for step in self.steps), self.measure])


Reference = Engine | Role | Value | Path


# --- the tree -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Num:
    value: float


@dataclass(frozen=True)
class Ref:
    ref: Reference


@dataclass(frozen=True)
class Neg:
    operand: Node


@dataclass(frozen=True)
class Bin:
    op: str
    left: Node
    right: Node


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple[Node, ...]


Node = Num | Ref | Neg | Bin | Call


def spell(node: Node) -> str:
    """A node written out again, for messages."""
    if isinstance(node, Num):
        return f"{node.value:g}"
    if isinstance(node, Ref):
        return str(node.ref)
    if isinstance(node, Neg):
        return f"-{spell(node.operand)}"
    if isinstance(node, Call):
        return f"{node.name}({', '.join(spell(arg) for arg in node.args)})"
    return f"({spell(node.left)} {node.op} {spell(node.right)})"


@dataclass(frozen=True)
class Formula:
    """A formula, read: its text as written, and its tree."""

    text: str
    tree: Node

    def references(self) -> tuple[Reference, ...]:
        """Every reference, in the order written."""
        found: list[Reference] = []

        def walk(node: Node) -> None:
            if isinstance(node, Ref):
                found.append(node.ref)
            elif isinstance(node, Neg):
                walk(node.operand)
            elif isinstance(node, Bin):
                walk(node.left)
                walk(node.right)
            elif isinstance(node, Call):
                for arg in node.args:
                    walk(arg)

        walk(self.tree)
        return tuple(found)


def is_formula(value: object) -> bool:
    """Whether a value of a component is written as a formula."""
    return isinstance(value, str) and value.startswith("=")


# --- reading ------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Token:
    kind: str
    text: str
    spaced_before: bool


def _tokens(formula: str) -> list[_Token]:
    body = formula[1:]
    found: list[_Token] = []
    at = 0
    while at < len(body):
        spaced = False
        while at < len(body) and body[at].isspace():
            at += 1
            spaced = True
        if at == len(body):
            break
        match = _TOKEN.match(body, at)
        if match is None:
            raise FormulaError(formula, f"cannot be read from `{body[at:]}`")
        kind = match.lastgroup or ""
        found.append(_Token(kind, match.group(kind), spaced or at == 0))
        at = match.end()
    return found


def _step(segment: str) -> Step:
    match = _STEP_PARTS.match(segment)
    if match is None:  # the token's pattern admits only steps
        raise ValueError(segment)
    name, item, by_id = match.groups()
    return Step(name, item or by_id, by_id is not None)


def _reference(formula: str, text: str) -> Reference:
    option = None
    rest = text
    if text.startswith("{"):
        option, _, rest = text[1:].partition("}")
        rest = rest[1:] if rest.startswith(".") else rest
    steps = [_step(segment) for segment in rest.split(".")] if rest else []
    if option is None and len(steps) == 1 and steps[0].item is None:
        return Value(steps[0].name)
    if not steps:
        raise FormulaError(formula, f"reads `{text}`, which ends in no measure")
    measure = steps.pop()
    if measure.item is not None or measure.name not in MEASURES:
        raise FormulaError(
            formula,
            f"reads `{text}`, which must end in a measure, one of {' '.join(MEASURES)}",
        )
    return Path(option, tuple(steps), measure.name)


@lru_cache(maxsize=4096)
def parse(formula: str) -> Formula:
    """A formula read into its tree. Raises `FormulaError` naming the formula."""
    if not is_formula(formula):
        raise FormulaError(formula, "does not start with `=`")
    tokens = _tokens(formula)
    at = 0

    def peek() -> _Token | None:
        return tokens[at] if at < len(tokens) else None

    def take() -> _Token:
        nonlocal at
        token = peek()
        if token is None:
            raise FormulaError(formula, "ends too early")
        at += 1
        return token

    def expect(text: str) -> None:
        token = take()
        if token.text != text:
            raise FormulaError(formula, f"has `{token.text}` where `{text}` belongs")

    def sum_() -> Node:
        node = product()
        while (token := peek()) is not None and token.text in ("+", "-"):
            take()
            if token.text == "-":
                following = peek()
                if not token.spaced_before or following is None or not following.spaced_before:
                    raise FormulaError(formula, "has a minus that needs a space on each side")
            node = Bin(token.text, node, product())
        return node

    def product() -> Node:
        node = unary()
        while (token := peek()) is not None and token.text in ("*", "/"):
            take()
            node = Bin(token.text, node, unary())
        return node

    def unary() -> Node:
        token = peek()
        if token is not None and token.text == "-":
            take()
            return Neg(unary())
        return primary()

    def primary() -> Node:
        token = take()
        if token.kind == "number":
            return Num(float(token.text))
        if token.kind == "role":
            return Ref(Role(token.text[1:]))
        if token.kind == "engine":
            name = token.text[1:]
            if name not in ENGINE_NAMES:
                known = " ".join(f":{n}" for n in ENGINE_NAMES)
                raise FormulaError(formula, f"names `{token.text}`; the engine's names are {known}")
            return Ref(Engine(name))
        if token.kind == "function":
            return call(token.text[:-1])
        if token.kind == "path":
            return Ref(_reference(formula, token.text))
        if token.text == "(":
            node = sum_()
            expect(")")
            return node
        raise FormulaError(formula, f"has `{token.text}` where a number or a name belongs")

    def call(name: str) -> Node:
        args = [sum_()]
        while (token := peek()) is not None and token.text == ",":
            take()
            args.append(sum_())
        expect(")")
        least, most = FUNCTIONS[name]
        if len(args) < least or (most is not None and len(args) > most):
            wanted = f"{least}" if least == most else f"{least} or more"
            raise FormulaError(formula, f"gives {name}() {len(args)} arguments; it takes {wanted}")
        return Call(name, tuple(args))

    if not tokens:
        raise FormulaError(formula, "is empty")
    tree = sum_()
    if at != len(tokens):
        raise FormulaError(formula, f"has `{tokens[at].text}` after its end")
    return Formula(formula, tree)


# --- dimensions ---------------------------------------------------------------------------


def dimension_name(power: int) -> str:
    """A dimension in words."""
    if power == NUMBER:
        return "a number with no unit"
    if power == LENGTH:
        return "a length"
    return f"a length to the power {power}"


def dimension(formula: Formula, dimension_of: Callable[[Reference], int | None]) -> int | None:
    """The dimension of a formula's result, from each reference's (`None` where it is not
    known, which then checks nothing). Raises `FormulaError` where terms disagree."""

    def power(node: Node) -> int | None:
        if isinstance(node, Num):
            return NUMBER
        if isinstance(node, Ref):
            return dimension_of(node.ref)
        if isinstance(node, Neg):
            return power(node.operand)
        if isinstance(node, Call):
            powers = [power(arg) for arg in node.args]
            known = {p for p in powers if p is not None}
            if len(known) > 1:
                raise FormulaError(
                    formula.text, f"gives {node.name}() arguments of different dimensions"
                )
            return known.pop() if known and None not in powers else None
        left, right = power(node.left), power(node.right)
        if left is None or right is None:
            return None
        if node.op in ("+", "-"):
            if left != right:
                raise FormulaError(
                    formula.text,
                    f"{'adds' if node.op == '+' else 'subtracts'} {dimension_name(right)} "
                    f"(`{spell(node.right)}`) {'to' if node.op == '+' else 'from'} "
                    f"{dimension_name(left)} (`{spell(node.left)}`)",
                )
            return left
        return left + right if node.op == "*" else left - right

    return power(formula.tree)


# --- computing ----------------------------------------------------------------------------


def rounded(value: float, places: int = 0) -> float:
    """A number rounded to `places` decimal places, half away from zero, from its exact
    binary value: one rule, the same on every machine."""
    step = Decimal(1).scaleb(-places)
    return float(Decimal(value).quantize(step, rounding=ROUND_HALF_UP))


def evaluate(formula: Formula, read: Callable[[Reference], float]) -> float:
    """A formula's value, from each reference's. Raises `DivisionByZero` naming it."""

    def value(node: Node) -> float:
        if isinstance(node, Num):
            return node.value
        if isinstance(node, Ref):
            return read(node.ref)
        if isinstance(node, Neg):
            return -value(node.operand)
        if isinstance(node, Call):
            args = [value(arg) for arg in node.args]
            if node.name == "min":
                return min(args)
            if node.name == "max":
                return max(args)
            return rounded(args[0])
        left, right = value(node.left), value(node.right)
        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        if right == 0:
            raise DivisionByZero(formula.text, f"divides by zero: `{spell(node.right)}` is 0")
        return left / right

    return value(formula.tree)
