"""The document of a brand's resolved values, version 2 (DEC-005 points 7 and 8, DEC-025
point 4), its version 1, and the variants a program makes from it (DEC-006 point 3), read
from the test brand, and from the brand `test-logo`, which gives its logo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_logo as logo
from tests.in_process import load
from tests.visual_communication_project import FOUNDATIONS, TEST_BRAND

values, tokens, keys, reading = load("visual-communication", "values", "tokens", "keys", "reading")

LOCK = {"test-brand": "1.0.0", "foundations": "1.0.0"}


@pytest.fixture(scope="module")
def brand() -> Any:
    return tokens.read_brand(TEST_BRAND, tokens.read_declarations(FOUNDATIONS / "roles.yaml"))


def test_the_document_holds_every_exported_token_in_each_combination(brand: Any) -> None:
    doc = values.document(brand, reversed(brand.combinations()), LOCK)
    assert doc["document"] == "visual-communication/values"
    assert doc["version"] == 2
    assert list(doc["lock"]) == ["foundations", "test-brand"]
    assert doc["keys"] == [
        "default",
        "colour-scheme.dark",
        "contrast.high",
        "colour-scheme.dark+contrast.high",
    ]
    assert list(doc["tokens"]) == sorted(brand.roles)
    assert doc["tokens"]["space.2"] == {
        "type": "dimension",
        "values": {key: {"value": 8, "unit": "px"} for key in doc["keys"]},
    }
    background = doc["tokens"]["background"]["values"]["default"]
    assert background == {"colorSpace": "srgb", "components": [1.0, 1.0, 1.0], "alpha": 1}
    reading.canonical_json(doc)


def test_the_document_may_hold_the_tokens_asked_for_alone(brand: Any) -> None:
    doc = values.document(brand, [{}, {}], LOCK, tokens=["space.1", "background", "space.1"])
    assert doc["keys"] == ["default"]
    assert list(doc["tokens"]) == ["background", "space.1"]


def test_a_token_or_a_combination_the_brand_lacks_is_refused(brand: Any) -> None:
    with pytest.raises(tokens.UnknownRole):
        values.document(brand, [{}], LOCK, tokens=["scheme.paper"])
    with pytest.raises(keys.BadKey):
        values.document(brand, [{"contrast": "low"}], LOCK)


def test_a_token_no_axis_changes_has_one_variant(brand: Any) -> None:
    doc = values.document(brand, brand.combinations(), LOCK, tokens=["space.1", "type.body"])
    assert values.variants(doc) == {"default": doc["keys"]}


def test_combinations_with_the_same_values_share_one_variant_under_its_first_key(
    brand: Any,
) -> None:
    """Light at high contrast paints the background white, as light at standard does; the
    dark scheme paints it otherwise at each contrast."""
    doc = values.document(brand, brand.combinations(), LOCK, tokens=["background"])
    assert values.variants(doc) == {
        "default": ["default", "contrast.high"],
        "colour-scheme.dark": ["colour-scheme.dark"],
        "colour-scheme.dark+contrast.high": ["colour-scheme.dark+contrast.high"],
    }


def test_every_combination_of_every_role_is_a_variant_of_its_own_where_values_differ(
    brand: Any,
) -> None:
    doc = values.document(brand, brand.combinations(), LOCK)
    grouped = values.variants(doc)
    assert sorted(key for group in grouped.values() for key in group) == sorted(doc["keys"])
    assert set(grouped) == set(doc["keys"])


# --- a picture role (DEC-025 point 4) -----------------------------------------------------------


def logo_brand(tmp_path: Path) -> Any:
    folder = logo.logo_brand(tmp_path)
    return tokens.read_brand(folder, tokens.read_declarations(FOUNDATIONS / "roles.yaml"))


def test_version_2_holds_the_file_the_brand_gives_its_logo_in_each_combination(
    tmp_path: Path,
) -> None:
    brand = logo_brand(tmp_path)
    doc = values.document(brand, brand.combinations(), {"foundations": "1.0.0", logo.NAME: "1.0.0"})

    assert doc["version"] == 2
    light = {"file": logo.LIGHT, "library": logo.NAME}
    dark = {"file": logo.DARK, "library": logo.NAME}
    assert doc["tokens"]["picture.logo"] == {
        "type": "picture",
        "values": {
            "default": light,
            "colour-scheme.dark": dark,
            "contrast.high": light,
            "colour-scheme.dark+contrast.high": dark,
        },
    }
    assert list(doc["tokens"]) == sorted(doc["tokens"])


def test_a_brand_that_gives_no_logo_holds_none_and_version_1_holds_no_picture_role(
    tmp_path: Path, brand: Any
) -> None:
    """Version 1 is version 2 without its picture roles; every other token reads the same."""
    plain = values.document(brand, brand.combinations(), LOCK)
    assert "picture.logo" not in plain["tokens"]
    pictured = logo_brand(tmp_path)
    lock = {"foundations": "1.0.0", logo.NAME: "1.0.0"}
    doc = values.document(pictured, pictured.combinations(), lock)
    first = values.as_version(doc, 1)
    assert first["version"] == 1
    assert "picture.logo" not in first["tokens"]
    assert first["tokens"] == {p: t for p, t in doc["tokens"].items() if p != "picture.logo"}
    assert values.as_version(doc, 2) == doc
    with pytest.raises(ValueError, match="no version 3"):
        values.as_version(doc, 3)
