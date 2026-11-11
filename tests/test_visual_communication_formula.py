"""The formulas a component's values are written in (visual-communication DEC-005 point 2;
#2428).

A formula starts with `=` and reads numbers, `+ - * /`, parentheses and `min max round`;
the engine's names `:width :height :index :count`; paths to a part's frame,
`<part>.<exposed>….<measure>`, with `<list>:first`, `<list>:last` and `<list>[<id>]`; the
path an option gives, `{<option>}`; a value by its name; a role, `@<token path>`. A minus
between two terms needs a space on each side, so `a-b` stays a name. Dimensions are
checked: a length and a number never add. Each refusal names the formula and says why.
"""

from __future__ import annotations

import pytest

from tests.visual_engine import formula

Engine, Path, Role, Step, Value = (
    formula.Engine,
    formula.Path,
    formula.Role,
    formula.Step,
    formula.Value,
)


def value(text: str, **known: float) -> float:
    """A formula's value, each reference read from `known` by how it is written."""
    return formula.evaluate(formula.parse(text), lambda ref: known[str(ref)])


def refused(text: str) -> str:
    with pytest.raises(formula.FormulaError) as raised:
        formula.parse(text)
    return str(raised.value)


# --- numbers and operators ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("=2 + 3 * 4", 14),
        ("=(2 + 3) * 4", 20),
        ("=10 - 2 - 3", 5),
        ("=8 / 2 / 2", 2),
        ("=-2 * 3", -6),
        ("=2 * -3", -6),
        ("=-(1 + 2)", -3),
        ("=1.5 * 2", 3),
        ("=min(3, 1, 2)", 1),
        ("=max(3, 1, 2)", 3),
        ("=round(2.5)", 3),
        ("=round(-2.5)", -3),
        ("=round(2.4999)", 2),
        ("=max(1, min(4, 2)) + round(0.5)", 3),
    ],
)
def test_a_formula_computes_with_the_usual_precedence(text: str, expected: float) -> None:
    assert value(text) == expected


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("2 + 3", "does not start with `=`"),
        ("=", "is empty"),
        ("=1 +", "ends too early"),
        ("=(1 + 2", "ends too early"),
        ("=1 2", "has `2` after its end"),
        ("=1 $ 2", "cannot be read from `$ 2`"),
        ("=* 2", "has `*` where a number or a name belongs"),
        ("=round(1, 2)", "gives round() 2 arguments; it takes 1"),
        ("=min(1)", "gives min() 1 arguments; it takes 2 or more"),
        ("=floor(1.5)", "has `(` after its end"),
        ("=min(1, 2]", "cannot be read from `]`"),
    ],
)
def test_a_formula_that_cannot_be_read_is_refused_naming_it(text: str, why: str) -> None:
    assert refused(text) == f"the formula `{text}` {why}"


def test_a_binary_minus_needs_a_space_on_each_side() -> None:
    assert value("=a - b", a=5, b=2) == 3
    assert value("=-a + b", a=5, b=2) == -3
    assert value("=a * -b", a=5, b=2) == -10
    for text in ("=a -b", "=a- b", "=2-3", "=2 -3"):
        assert refused(text) == f"the formula `{text}` has a minus that needs a space on each side"


def test_a_hyphen_inside_a_name_is_part_of_the_name() -> None:
    assert formula.parse("=a-b").references() == (Value("a-b"),)
    assert formula.parse("=@space.wide-gap").references() == (Role("space.wide-gap"),)


# --- references ---------------------------------------------------------------------------


def test_a_formula_reads_the_engine_s_names() -> None:
    parsed = formula.parse("=:width - :height + :index * :count")

    assert parsed.references() == tuple(Engine(name) for name in formula.ENGINE_NAMES)
    assert (
        refused("=:size")
        == "the formula `=:size` names `:size`; the engine's names are :width :height :index :count"
    )


def test_a_formula_reads_a_role_and_a_value() -> None:
    parsed = formula.parse("=@space.2 * gap")

    assert parsed.references() == (Role("space.2"), Value("gap"))
    assert value("=@space.2 * gap", **{"@space.2": 8, "gap": 2}) == 16


def test_a_path_reads_a_measure_of_a_part_or_of_a_part_it_exposes() -> None:
    parsed = formula.parse("=head.bottom + card.box.right")

    assert parsed.references() == (
        Path(None, (Step("head"),), "bottom"),
        Path(None, (Step("card"), Step("box")), "right"),
    )
    for measure in formula.MEASURES:
        assert formula.parse(f"=b.{measure}").references() == (Path(None, (Step("b"),), measure),)


def test_a_path_steps_into_a_list_by_its_first_last_or_an_id() -> None:
    parsed = formula.parse("=steps:first.x + steps:last.right + steps[plan].tag.width")

    assert parsed.references() == (
        Path(None, (Step("steps", "first"),), "x"),
        Path(None, (Step("steps", "last"),), "right"),
        Path(None, (Step("steps", "plan", by_id=True), Step("tag")), "width"),
    )
    assert [str(ref) for ref in parsed.references()] == [
        "steps:first.x",
        "steps:last.right",
        "steps[plan].tag.width",
    ]


def test_a_path_starts_with_the_path_an_option_gives() -> None:
    assert formula.parse("={at}.x").references() == (Path("at", (), "x"),)
    assert formula.parse("={at}.image.y").references() == (Path("at", (Step("image"),), "y"),)
    assert str(formula.parse("={at}.image.y").references()[0]) == "{at}.image.y"


@pytest.mark.parametrize(
    ("text", "why"),
    [
        (
            "=head.tail",
            "reads `head.tail`, which must end in a measure, one of "
            "x y width height right bottom center middle",
        ),
        ("=steps:first", "reads `steps:first`, which must end in a measure"),
        ("=steps:first.box", "reads `steps:first.box`, which must end in a measure"),
        ("=head.x:last", "reads `head.x:last`, which must end in a measure"),
        ("={at}", "reads `{at}`, which ends in no measure"),
        ("=head.{at}.x", "cannot be read from `.{at}.x`"),
    ],
)
def test_a_path_that_ends_in_no_measure_is_refused(text: str, why: str) -> None:
    assert refused(text).startswith(f"the formula `{text}` {why}")


# --- dimensions ---------------------------------------------------------------------------


DIMENSIONS = {
    "@space.1": formula.LENGTH,
    ":width": formula.LENGTH,
    "scale": formula.NUMBER,
    ":index": formula.NUMBER,
}


def dimension(text: str) -> int | None:
    return formula.dimension(formula.parse(text), lambda ref: DIMENSIONS.get(str(ref)))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("=@space.1 + :width", formula.LENGTH),
        ("=@space.1 * 2", formula.LENGTH),
        ("=@space.1 * :index * scale", formula.LENGTH),
        ("=:width / @space.1", formula.NUMBER),
        ("=@space.1 * :width", 2),
        ("=:width * :width / @space.1", formula.LENGTH),
        ("=2 * 3", formula.NUMBER),
        ("=min(:width, @space.1 * 3)", formula.LENGTH),
        ("=round(:width / 3)", formula.LENGTH),
        ("=-@space.1", formula.LENGTH),
    ],
)
def test_a_formula_s_dimension_follows_its_terms(text: str, expected: int) -> None:
    assert dimension(text) == expected


def test_a_length_and_a_number_never_add() -> None:
    with pytest.raises(formula.FormulaError) as raised:
        dimension("=:width - 6")

    assert str(raised.value) == (
        "the formula `=:width - 6` subtracts a number with no unit (`6`) from a length (`:width`)"
    )
    with pytest.raises(formula.FormulaError, match=r"adds a length \(`@space.1`\) to a number"):
        dimension("=scale + @space.1")
    with pytest.raises(
        formula.FormulaError, match=r"adds a length \(`:width`\) to a length to the power 2"
    ):
        dimension("=@space.1 * :width + :width")


def test_a_function_s_arguments_share_one_dimension() -> None:
    with pytest.raises(
        formula.FormulaError,
        match=r"`=max\(:width, 3\)` gives max\(\) arguments of different dimensions",
    ):
        dimension("=max(:width, 3)")


def test_a_term_of_unknown_dimension_checks_nothing() -> None:
    assert dimension("=unknown + 6") is None
    assert dimension("=min(unknown, :width)") is None


def test_the_dimension_names_say_what_they_are() -> None:
    assert [formula.dimension_name(p) for p in (0, 1, 2, -1)] == [
        "a number with no unit",
        "a length",
        "a length to the power 2",
        "a length to the power -1",
    ]


# --- computing ----------------------------------------------------------------------------


def test_dividing_by_zero_names_the_formula_and_the_divisor() -> None:
    with pytest.raises(formula.DivisionByZero) as raised:
        value("=:width / (a - b)", **{":width": 10, "a": 2, "b": 2})

    assert str(raised.value) == "the formula `=:width / (a - b)` divides by zero: `(a - b)` is 0"
    assert isinstance(raised.value, formula.FormulaError)


def test_rounding_is_half_away_from_zero_from_the_exact_value() -> None:
    assert [formula.rounded(v) for v in (0.5, 1.5, 2.5, -0.5, -1.5)] == [1, 2, 3, -1, -2]
    # 2.675 is 2.67499999… in binary, so it rounds down; 0.125 is exact, so it rounds up.
    assert formula.rounded(2.675, 2) == 2.67
    assert formula.rounded(0.125, 2) == 0.13
    assert formula.rounded(197.33333333, 2) == 197.33


def test_only_a_string_starting_with_an_equals_sign_is_a_formula() -> None:
    assert formula.is_formula("=1")
    assert not formula.is_formula("1")
    assert not formula.is_formula(1)
    assert not formula.is_formula(None)
