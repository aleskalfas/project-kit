"""Keys, combinations and variant keys (DEC-004 point 3)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tests.in_process import load

(keys,) = load("visual-communication", "keys")


@dataclass(frozen=True)
class Axis:
    modes: tuple[str, ...]
    default: str


AXES = {
    "contrast": Axis(("standard", "high"), "standard"),
    "colour-scheme": Axis(("light", "dark"), "light"),
}


@pytest.mark.parametrize(
    ("modes", "key"),
    [
        ({}, "default"),
        ({"colour-scheme": "light", "contrast": "standard"}, "default"),
        ({"colour-scheme": "dark"}, "colour-scheme.dark"),
        ({"contrast": "high"}, "contrast.high"),
        ({"contrast": "high", "colour-scheme": "dark"}, "colour-scheme.dark+contrast.high"),
    ],
)
def test_a_key_names_the_modes_that_are_not_defaults_in_the_order_of_the_axes(
    modes: dict[str, str], key: str
) -> None:
    assert keys.key_of(modes, AXES) == key
    assert keys.parse_key(key, AXES) == {
        "colour-scheme": modes.get("colour-scheme", "light"),
        "contrast": modes.get("contrast", "standard"),
    }


def test_a_key_stays_the_same_when_an_axis_with_a_default_is_added() -> None:
    more = {**AXES, "density": Axis(("regular", "compact"), "regular")}
    assert keys.key_of({"colour-scheme": "dark"}, more) == "colour-scheme.dark"


@pytest.mark.parametrize(
    ("modes", "said"),
    [({"size": "big"}, "not an axis"), ({"contrast": "low"}, "not a mode of `contrast`")],
)
def test_a_combination_of_an_unknown_axis_or_mode_has_no_key(
    modes: dict[str, str], said: str
) -> None:
    with pytest.raises(keys.BadKey, match=said):
        keys.key_of(modes, AXES)


@pytest.mark.parametrize(
    ("key", "said"),
    [
        ("", "is not `<axis>.<mode>`"),
        ("dark", "is not `<axis>.<mode>`"),
        ("colour-scheme.light", "names the default mode"),
        ("contrast.high+colour-scheme.dark", "in the order of their names"),
        ("contrast.high+contrast.high", "in the order of their names"),
        ("size.big", "not an axis"),
        ("contrast.low", "not a mode"),
    ],
)
def test_a_key_not_spelled_as_key_of_spells_it_is_refused(key: str, said: str) -> None:
    with pytest.raises(keys.BadKey, match=said):
        keys.parse_key(key, AXES)


def test_combinations_are_every_product_of_the_named_modes_in_key_order() -> None:
    every = keys.combinations(
        {"colour-scheme": ["light", "dark"], "contrast": ["high", "standard"]}, AXES
    )
    assert [keys.key_of(c, AXES) for c in every] == [
        "default",
        "colour-scheme.dark",
        "contrast.high",
        "colour-scheme.dark+contrast.high",
    ]


def test_an_axis_not_named_is_taken_at_its_default() -> None:
    assert keys.combinations({"contrast": ["high"]}, AXES) == [
        {"colour-scheme": "light", "contrast": "high"}
    ]
    assert keys.combinations({}, AXES) == [{"colour-scheme": "light", "contrast": "standard"}]


@pytest.mark.parametrize(
    ("named", "said"),
    [
        ({"size": ["big"]}, "not an axis"),
        ({"contrast": []}, "with no mode"),
        ({"contrast": ["high", "high"]}, "a mode twice"),
        ({"contrast": ["low"]}, "not a mode"),
    ],
)
def test_combinations_of_what_the_axes_do_not_hold_are_refused(
    named: dict[str, list[str]], said: str
) -> None:
    with pytest.raises(keys.BadKey, match=said):
        keys.combinations(named, AXES)


def test_a_variant_takes_the_key_with_fewest_segments_then_the_first_in_string_order() -> None:
    assert keys.variant_key(["contrast.high", "colour-scheme.dark+contrast.high"]) == (
        "contrast.high"
    )
    assert keys.variant_key(["contrast.high", "colour-scheme.dark"]) == "colour-scheme.dark"
    assert keys.variant_key(["colour-scheme.dark", "default"]) == "default"
    with pytest.raises(ValueError):
        keys.variant_key([])
