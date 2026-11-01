"""Tokens resolve, every foundations role has a value in every brand, profile and mode, and a
mode's file holds colours only."""

import json

import pytest

from engine.checks import brand_problems, role_paths
from engine.model import Brand, EngineError, Library
from engine.tokens import TokenError, TokenSet


@pytest.mark.parametrize("name", ["ibm", "neutral"])
def test_every_role_has_a_value_in_every_mode(friday, name):
    brand = Brand(friday.library(name))
    assert brand_problems(friday, brand, brand.modes()) == []
    assert len(role_paths(friday)) > 100


@pytest.mark.parametrize("name", ["ibm", "neutral"])
def test_every_colour_role_is_a_colour(friday, name):
    brand = Brand(friday.library(name))
    for profile in brand.profiles:
        for mode in brand.modes():
            tokens = brand.tokens(profile, mode)
            for path in role_paths(friday):
                if path.startswith("color."):
                    assert tokens.colour(path).startswith("#")


def test_an_alias_loop_is_refused_naming_it(tmp_path):
    f = tmp_path / "loop.tokens.json"
    f.write_text(json.dumps({"a": {"$type": "color", "$value": "{b}"}, "b": {"$type": "color", "$value": "{a}"}}))
    with pytest.raises(TokenError, match="a -> b -> a"):
        TokenSet([f]).resolve("a")


def test_a_mode_file_with_a_dimension_is_refused(friday, tmp_path):
    lib = friday.library("ibm")
    brand = Brand(lib)
    bad = tmp_path / "bad.tokens.json"
    bad.write_text(json.dumps({"space": {"$type": "dimension", "05": {"$value": {"value": 40, "unit": "px"}}}}))
    brand.themes = {"carbon": {"light": str(bad)}}
    with pytest.raises(EngineError, match="a mode's file holds colours only"):
        brand.tokens("standard", "carbon/light")
