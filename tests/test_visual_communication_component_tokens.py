"""Component tokens (visual-communication DEC-035): a component declares them in its own
file, under `tokens`, each with a type and a default that aliases a role; only it reads
them, by their full paths; a brand that names its library may give them values and
exports those it gives, a base may open one alone, and the document of values holds them
all. What the checks report of them is found at its place and level (DEC-035 point 9).

The test library `test-parts` fills its tag's box through a token of its own, `fill`,
which defaults to the library's paper. A test that needs a token of another shape writes
a library of its own, `lab`, in its own folder, or holds its components in memory, since
the repository's validation reads every bound YAML file under `tests/`. One that needs a
token of the foundations' components gives its own copy of the foundations' figure one,
`back`, since no shipped component declares a token.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from tests import visual_engine as engine
from tests.in_process import load
from tests.visual_communication_project import (
    FOUNDATIONS,
    RELEASED_FOUNDATIONS,
    TEST_BRAND,
    TEST_EDITION,
    TEST_PARTS,
    add_library,
    bound,
    copy_library,
    project,
    write,
    write_list,
    write_piece,
    yaml_text,
)

tokens, findings, files, full_read, libraries, pl = load(
    "visual-communication", "tokens", "findings", "files", "full_read", "libraries", "pipeline"
)

ROLES = FOUNDATIONS / "roles.yaml"
#: The libraries the test library's roles and tokens are read with.
PARTS = {"foundations": FOUNDATIONS, "test-parts": TEST_PARTS}
#: The tag's token, and the test brand's token files.
FILL = "component.test-parts.tag.fill"
BASE = "tokens/base.tokens.json"
EDITION = "tokens/edition.tokens.json"

WHITE = {"colorSpace": "srgb", "components": [1.0, 1.0, 1.0], "alpha": 1}


@pytest.fixture(scope="module")
def parts() -> Any:
    return tokens.read_scope(PARTS)


def codes(found: Any) -> list[str]:
    return [finding.code for finding in found]


def replace_in(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def add_tokens(path: Path, given: Mapping[str, Any]) -> None:
    """The token file at `path`, with the groups `given` added at its top."""
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(given)
    path.write_text(json.dumps(data), encoding="utf-8")


def naming(folder: Path) -> Path:
    """The brand at `folder`, naming `test-parts` 1 among the libraries it builds on."""
    replace_in(
        folder / "library.yaml",
        "  - {name: foundations, major: 1}\n",
        "  - {name: foundations, major: 1}\n  - {name: test-parts, major: 1}\n",
    )
    return folder


def brand_copy(tmp_path: Path, *, names: bool, given: Mapping[str, Any] | None = None) -> Path:
    """A copy of the test brand, naming `test-parts` where `names`, `given` added to its base
    tokens. A brand that names it gives the library's warning, which has no default, a
    value."""
    folder = tmp_path / "test-brand" / "1.0.0"
    shutil.copytree(TEST_BRAND, folder, ignore=shutil.ignore_patterns("__pycache__"))
    if names:
        naming(folder)
        add_tokens(
            folder / BASE, {"test-parts": {"warning": {"$type": "color", "$value": "{scheme.ink}"}}}
        )
    if given:
        add_tokens(folder / BASE, given)
    return folder


#: The token the figure of a test's copy of the foundations declares (`figure_token`).
BACK = "component.foundations.figure.back"


def figure_token(folder: Path) -> Path:
    """The copy of the foundations at `folder`, its figure declaring the token `back`, which
    defaults to the shared `background`, and filling its background with it."""
    figure = folder / "components" / "figure.yaml"
    replace_in(figure, "box: {fill: background}", f"box: {{fill: {BACK}}}")
    replace_in(
        figure,
        "\nparts:\n",
        "\ntokens:\n  back: {type: color, default: '{background}'}\n\nparts:\n",
    )
    return folder


def shared_scope(tmp_path: Path, *, back: bool = False) -> Any:
    """The scope of the foundations and the test library, the foundations copied into a
    folder of their version, which a brand names by its major; with `back`, their figure
    declares the token `back` (`figure_token`)."""
    shared = copy_library(tmp_path, FOUNDATIONS, "foundations", "1.0.0")
    if back:
        figure_token(shared)
    return tokens.read_scope({"foundations": shared, "test-parts": TEST_PARTS})


def tag_fill(value: Any, kind: str = "color", name: str = "fill") -> dict[str, Any]:
    """A brand's tokens that give the tag's token `name` `value`."""
    return {"component": {"test-parts": {"tag": {name: {"$type": kind, "$value": value}}}}}


def lab(
    root: Path,
    components: Mapping[str, Any],
    *,
    builds_on: Mapping[str, int] | None = None,
    roles: Mapping[str, Any] | None = None,
) -> Path:
    """The library `lab` 1.0.0 in the location at `root`, with `components`, each a mapping
    of its file's fields, and `roles`, its own roles, if any."""
    folder = add_library(root, "lab", "1.0.0", builds_on=builds_on or {"foundations": 1})
    for name, data in components.items():
        write(folder / "components" / f"{name}.yaml", yaml_text(bound("component", **data)))
    if roles:
        write(folder / "roles.yaml", yaml_text(bound("roles", roles=dict(roles))))
    return folder


def box(tokens_: Mapping[str, Any], fill: str = "component.lab.box.fill", **keys: Any) -> dict:
    """A component `box` that declares `tokens_` and fills its one part with `fill`."""
    return {
        "status": "experimental",
        "about": "A box.",
        "tokens": dict(tokens_),
        "parts": {"back": {"box": {"fill": fill}, "width": "=:width", "height": "=:height"}},
        **keys,
    }


def lab_scope(tmp_path: Path, components: Mapping[str, Any], **more: Any) -> Any:
    root = project(tmp_path)
    shared = copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    folder = lab(root, components, **more)
    return tokens.read_scope({"foundations": shared, "lab": folder}, root=root)


# --- what a component declares ------------------------------------------------------------------


def test_a_component_declares_its_tokens_in_its_own_file_and_the_scope_reads_them(
    parts: Any,
) -> None:
    token = parts.tokens[FILL]
    assert (token.type, token.default, token.component, token.name) == (
        "color",
        "test-parts.paper",
        "tag",
        "fill",
    )
    assert token.file.endswith("test-parts/1.0.0/components/tag.yaml")
    assert parts.owner[FILL] == "test-parts"
    assert parts.type_of(FILL) == "color"
    assert parts.default_of(FILL) == "test-parts.paper"
    # A token is no own role of its library: its roles' file holds none.
    assert FILL not in parts.libraries["test-parts"].roles
    assert codes(parts.findings) == ["role-brand-only"]


def test_a_library_with_no_roles_of_its_own_declares_tokens_still(tmp_path: Path) -> None:
    scope = lab_scope(tmp_path, {"box": box({"fill": {"type": "color", "default": "{surface}"}})})
    assert (
        scope.tokens["component.lab.box.fill"].file
        == "visual/libraries/lab/1.0.0/components/box.yaml"
    )
    assert scope.default_of("component.lab.box.fill") == "surface"
    assert scope.findings == []


@pytest.mark.parametrize(
    ("declared", "code", "where"),
    [
        ([], "component-token-shape", "tokens"),
        (
            {"Fill": {"type": "color", "default": "{surface}"}},
            "component-token-shape",
            "tokens.Fill",
        ),
        ({"fill": "{surface}"}, "component-token-shape", "tokens.fill"),
        (
            {"fill": {"type": "color", "default": "{surface}", "x": 1}},
            "component-token-shape",
            "tokens.fill",
        ),
        (
            {"fill": {"type": "picture", "default": "{picture.logo}"}},
            "component-token-shape",
            "tokens.fill",
        ),
        (
            {"fill": {"type": "colour", "default": "{surface}"}},
            "component-token-shape",
            "tokens.fill",
        ),
        ({"fill": {"type": "color"}}, "role-default", "tokens.fill"),
        ({"fill": {"type": "color", "default": "surface"}}, "role-default", "tokens.fill"),
    ],
    ids=[
        "not-a-mapping",
        "name",
        "declaration",
        "key",
        "picture",
        "type",
        "no-default",
        "no-alias",
    ],
)
def test_a_token_that_cannot_be_read_is_left_out_and_found_in_its_components_file(
    tmp_path: Path, declared: Any, code: str, where: str
) -> None:
    scope = lab_scope(tmp_path, {"box": {**box({}), "tokens": declared}})
    (finding,) = scope.findings
    assert (finding.code, finding.level, finding.where) == (code, findings.FAILS, where)
    assert finding.file == "visual/libraries/lab/1.0.0/components/box.yaml"
    assert finding.library == "lab@1.0.0"
    assert scope.tokens == {}


@pytest.mark.parametrize(
    ("default", "code", "said"),
    [
        ("{component.lab.other.fill}", "role-default", "a component token"),
        ("{space.2}", "role-default", "of type `dimension`, not `color`"),
        ("{test-parts.ink}", "role-default", "which `lab` does not build on"),
        ("{lab.nothing}", "default-dangling", "which neither `lab` nor a library it builds on"),
    ],
    ids=["token", "type", "not-built-on", "dangling"],
)
def test_a_tokens_default_that_does_not_hold_is_found_and_gives_it_no_default(
    tmp_path: Path, default: str, code: str, said: str
) -> None:
    root = project(tmp_path)
    shared = copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    folder = lab(
        root,
        {
            "box": box({"fill": {"type": "color", "default": default}}),
            "other": box(
                {"fill": {"type": "color", "default": "{surface}"}}, "component.lab.other.fill"
            ),
        },
    )
    held = copy_library(root, TEST_PARTS, "test-parts", "1.0.0")
    scope = tokens.read_scope({"foundations": shared, "lab": folder, "test-parts": held}, root=root)
    (finding,) = scope.findings_of("lab")
    assert (finding.code, finding.where) == (code, "tokens.fill")
    assert finding.file.endswith("components/box.yaml")
    assert said in finding.message
    assert "component.lab.box.fill" in scope.tokens
    assert scope.default_of("component.lab.box.fill") is None


def test_a_token_whose_chain_ends_at_no_shared_role_is_stated_as_a_fact(tmp_path: Path) -> None:
    root = project(tmp_path)
    shared = copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    folder = copy_library(root, TEST_PARTS, "test-parts", "1.0.0")
    replace_in(folder / "components" / "tag.yaml", "'{test-parts.paper}'", "'{test-parts.warning}'")
    scope = tokens.read_scope({"foundations": shared, "test-parts": folder}, root=root)
    facts = {finding.where: finding for finding in scope.findings}
    fact = facts["tokens.fill"]
    assert (fact.code, fact.level) == ("role-brand-only", findings.FACT)
    assert fact.file == "visual/libraries/test-parts/1.0.0/components/tag.yaml"
    assert "ends at `test-parts.warning`" in fact.message


def test_no_pair_names_a_component_token(tmp_path: Path) -> None:
    path = write(
        tmp_path / "roles.yaml",
        yaml_text(
            bound(
                "roles",
                roles={"test-parts.ink": {"type": "color", "default": "{text-primary}"}},
                pairs=[{"text": "test-parts.ink", "under": FILL, "level": "text"}],
            )
        ),
    )
    declared = tokens.read_own_roles(path, name="test-parts", library="test-parts@1.0.0")
    (finding,) = declared.findings
    assert (finding.code, finding.where) == ("pair-shape", "pairs.0")
    assert f"names `{FILL}`, a component token" in finding.message
    assert declared.pairs == ()


def test_the_component_schema_takes_tokens_of_a_role_type_with_an_alias_for_a_default() -> None:
    def problems(declared: Any) -> list[str]:
        data = bound("component", **{**box({}), "tokens": declared})
        return files.shape_problems(data, "component")

    assert problems({"fill": {"type": "color", "default": "{surface}"}}) == []
    assert problems({"fill": {"type": "picture", "default": "{picture.logo}"}}) != []
    assert problems({"fill": {"type": "color"}}) != []
    assert problems({"fill": {"type": "color", "default": "surface"}}) != []
    assert problems({"Fill": {"type": "color", "default": "{surface}"}}) != []


# --- a brand -------------------------------------------------------------------------------------


def test_a_brand_that_does_not_name_the_library_draws_a_token_at_its_default(parts: Any) -> None:
    brand = tokens.read_brand(TEST_BRAND, parts)
    assert brand.findings == ()
    for combination in brand.combinations():
        assert brand.resolve(FILL, combination) == brand.resolve("background", combination)
    assert FILL in brand.valued
    assert FILL not in brand.roles


def test_a_brand_that_names_the_library_gives_a_token_a_value_and_exports_it(
    tmp_path: Path, parts: Any
) -> None:
    folder = brand_copy(tmp_path, names=True, given=tag_fill("{palette.white}"))
    brand = tokens.read_brand(folder, parts)
    assert brand.findings == ()
    for combination in brand.combinations():
        assert brand.resolve(FILL, combination) == WHITE
    assert FILL in brand.roles


@pytest.mark.parametrize(
    ("given", "said"),
    [
        (tag_fill("{palette.white}", name="fil"), "is none of its components' tokens"),
        (tag_fill("{space.2}", kind="dimension"), "but the component token"),
    ],
    ids=["misspelt", "type"],
)
def test_a_token_under_a_named_librarys_component_group_that_gives_nothing_is_a_finding(
    tmp_path: Path, parts: Any, given: Any, said: str
) -> None:
    brand = tokens.read_brand(brand_copy(tmp_path, names=True, given=given), parts)
    (finding,) = brand.findings
    assert (finding.code, finding.level) == ("library-token", findings.FAILS)
    assert finding.where.startswith("component.test-parts.tag.")
    assert finding.library == "test-brand@1.0.0"
    assert said in finding.message
    assert brand.resolve(FILL, {}) == brand.resolve("background", {})


def test_a_token_under_the_component_group_of_a_library_the_brand_does_not_name_stays_private(
    tmp_path: Path, parts: Any
) -> None:
    folder = brand_copy(tmp_path, names=False, given=tag_fill("{palette.white}"))
    brand = tokens.read_brand(folder, parts)
    (finding,) = brand.findings
    assert (finding.code, finding.level) == ("library-token-private", findings.ATTENTION)
    assert "lies under `component.test-parts`" in finding.message
    assert brand.resolve(FILL, {}) == brand.resolve("background", {})
    assert FILL not in brand.roles
    # Checked alone, with no lock that holds the library, it asks nothing.
    assert tokens.read_brand(folder, tokens.read_declarations(ROLES)).findings == ()


def test_a_token_under_the_component_group_of_the_brands_own_name_stays_private(
    tmp_path: Path, parts: Any
) -> None:
    given = {
        "component": {
            "test-brand": {"note": {"fill": {"$type": "color", "$value": "{palette.white}"}}}
        }
    }
    brand = tokens.read_brand(brand_copy(tmp_path, names=True, given=given), parts)
    assert brand.findings == ()
    assert "component.test-brand.note.fill" not in brand.roles


def test_a_token_under_the_foundations_component_group_that_names_none_of_theirs_fails(
    tmp_path: Path,
) -> None:
    stray = {"$type": "color", "$value": "{palette.white}"}
    given = {
        "component": {"foundations": {"x": {"fill": stray}}},
        # The foundations have no own roles, so a token under their name stays private.
        "foundations": {"x": stray},
    }
    folder = brand_copy(tmp_path / "brand", names=False, given=given)
    brand = tokens.read_brand(folder, shared_scope(tmp_path))
    (finding,) = brand.findings
    assert (finding.code, finding.level) == ("library-token", findings.FAILS)
    assert (finding.where, finding.library) == ("component.foundations.x.fill", "test-brand@1.0.0")
    assert "is none of its components' tokens" in finding.message


@pytest.mark.parametrize(
    ("value", "kind", "code"),
    [
        (None, "", None),
        ("{palette.white}", "color", None),
        ("{space.2}", "dimension", "library-token"),
    ],
    ids=["default", "value", "type"],
)
def test_the_foundations_components_declare_tokens_a_brand_gives_values_as_any_librarys(
    tmp_path: Path, value: str | None, kind: str, code: str | None
) -> None:
    scope = shared_scope(tmp_path, back=True)
    assert (scope.owner[BACK], scope.type_of(BACK), scope.default_of(BACK)) == (
        "foundations",
        "color",
        "background",
    )
    assert scope.findings_of("foundations") == []
    given = {"component": {"foundations": {"figure": {"back": {"$type": kind, "$value": value}}}}}
    brand = tokens.read_brand(
        brand_copy(tmp_path / "brand", names=False, given=given if value else None), scope
    )
    assert codes(brand.findings) == ([code] if code else [])
    for combination in brand.combinations():
        drawn_in = WHITE if kind == "color" else brand.resolve("background", combination)
        assert brand.resolve(BACK, combination) == drawn_in
    assert (BACK in brand.roles) == (kind == "color")


def chain(tmp_path: Path, *, base_names: bool, opens: str = FILL) -> tuple[Path, Path]:
    """The test brand as a base that opens `opens`, naming `test-parts` where `base_names`,
    and the edition over it, which names `test-parts` and gives the tag's token a value."""
    base = brand_copy(tmp_path, names=base_names)
    replace_in(base / "library.yaml", "open: [accent, space]", f"open: [accent, space, {opens}]")
    edition = tmp_path / "test-edition" / "1.0.0"
    shutil.copytree(TEST_EDITION, edition, ignore=shutil.ignore_patterns("__pycache__"))
    naming(edition)
    add_tokens(edition / EDITION, tag_fill(WHITE))
    return base, edition


@pytest.mark.parametrize("opens", [FILL, "component.test-parts"], ids=["token", "group"])
def test_a_base_opens_a_component_token_and_a_brand_built_on_it_gives_it_a_value(
    tmp_path: Path, parts: Any, opens: str
) -> None:
    base, edition = chain(tmp_path, base_names=True, opens=opens)
    read = tokens.read_brand(edition, parts, locked={"test-brand": base})
    assert read.findings == ()
    assert read.base is not None and FILL in read.base.opened
    assert read.resolve(FILL, {}) == WHITE
    assert read.base.resolve(FILL, {}) == read.base.resolve("background", {})
    assert FILL in read.roles


def test_a_base_that_does_not_name_the_library_opens_none_of_its_tokens(
    tmp_path: Path, parts: Any
) -> None:
    base, edition = chain(tmp_path, base_names=False)
    read = tokens.read_brand(edition, parts, locked={"test-brand": base})
    found = {(finding.code, finding.library) for finding in read.findings}
    assert ("open-unknown", "test-brand@1.0.0") in found
    assert ("role-not-open", "test-edition@1.0.0") in found
    assert read.resolve(FILL, {}) == read.resolve("background", {})


# --- what reads a token --------------------------------------------------------------------------


#: A card of the library `lab` that declares two tokens and reads both: its box's fill, and
#: its height, by a formula.
CARD = engine.block(
    {
        "back": {
            "box": {"fill": "component.lab.card.fill"},
            "width": "=:width",
            "height": "=@component.lab.card.gap * 2",
        }
    },
    tokens={
        "fill": {"type": "color", "default": "{surface}"},
        "gap": {"type": "dimension", "default": "{space.2}"},
    },
)
GAP = {"component.lab.card.gap": {"value": 12, "unit": "px"}}


def drawn(*parts_: str, content: Mapping[str, Any] | None = None, **components: Any) -> Any:
    """The scene of `lab/top`, which places each component of `parts_` as a part of its own,
    and its slot `body`, with `CARD` and `components` beside it."""
    placed = {f"p{index}": {"use": use, "width": "=:width"} for index, use in enumerate(parts_)}
    top = engine.top(
        {**placed, "body": {"slot": "body", "width": "=:width"}},
        fields={"body": {"type": "object"}},
    )
    return engine.draw(
        content,
        components={"lab/top": top, "lab/card": CARD, **components},
        roles=GAP,
    )


def test_a_component_reads_its_own_tokens_by_their_full_paths(tmp_path: Path) -> None:
    result = drawn("lab/card")
    assert result.findings == []
    back = result.scene.find("top/p0/back")
    assert back is not None
    assert back.properties["fill"] == "component.lab.card.fill"
    assert back.properties["height"] == 24


def test_a_component_that_reads_a_token_it_does_not_declare_fails_in_its_file() -> None:
    other = engine.block(
        {
            "label": {
                "text": {"content": "label", "style": "component.lab.card.type", "fill": FILL},
                "width": "=@component.lab.card.gap",
            }
        },
        fields={"label": {"type": "string"}},
    )
    result = drawn("lab/other", **{"lab/other": other})
    found = [finding for finding in result.findings if finding.code == "component-token-undeclared"]
    assert {finding.where for finding in found} == {
        "parts.label.text.style",
        "parts.label.text.fill",
        "parts.label.width",
    }
    assert all(finding.extra["component"] == "lab/other" for finding in found)
    assert all(finding.library == "lab@1.0.0" for finding in found)


def test_a_pieces_own_component_declares_no_token() -> None:
    badge = engine.block(
        {"back": {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}},
        tokens={"fill": {"type": "color", "default": "{surface}"}},
    )
    result = drawn("piece/badge", **{"piece/badge": badge})
    (finding,) = [f for f in result.findings if f.code == "component-token-local"]
    assert (finding.where, finding.library, finding.extra["component"]) == (
        "tokens",
        "",
        "piece/badge",
    )


def test_contents_override_points_a_part_at_no_component_token() -> None:
    content = {"body": {"use": "lab/card", "override": {"back": "component.lab.card.fill"}}}
    result = drawn(content=content)
    (finding,) = result.findings
    assert finding.code == "override"
    assert "a component token, which only its component reads" in finding.message
    back = result.scene.find("top/body/back")
    assert back is not None and back.properties["fill"] == "component.lab.card.fill"


@pytest.mark.parametrize(
    ("status", "level", "who"),
    [
        ("experimental", findings.ATTENTION, "the owner of `lab`"),
        ("stable", findings.FACT, ""),
        ("deprecated", findings.FACT, ""),
    ],
)
def test_a_token_its_component_reads_nowhere_asks_attention_or_states_a_fact(
    status: str, level: str, who: str
) -> None:
    card = {**CARD, "status": status, "tokens": {**CARD["tokens"], "edge": CARD["tokens"]["fill"]}}
    ctx = engine.layout.Context(engine.FakeEnv(components={"lab/card": card}, roles=GAP), "en")
    component = ctx.component("lab/card")
    assert component is not None
    found = engine.layout.unread_token_findings(component, file="card.yaml", library="lab@1.0.0")
    (finding,) = found
    assert (finding.code, finding.level, finding.who) == ("component-token-unread", level, who)
    assert (finding.file, finding.where, finding.library) == (
        "card.yaml",
        "tokens.edge",
        "lab@1.0.0",
    )


# --- under a lock --------------------------------------------------------------------------------


#: The tag's second token, which the test `tags_project` adds where asked: a gap its label
#: is placed by, defaulting to a role of the library with no default.
GAP_TOKEN = "component.test-parts.tag.gap"


def tags_project(
    tmp_path: Path, brand: Path | None = None, gap: bool = False, back: bool = False
) -> Any:
    """The foundations, a brand and the test library, and the draft `tags`, a figure of the
    library's tag, under a lock of the three. `brand` is the brand's folder, else the test
    brand. With `gap`, the library has a dimension role with no default, `test-parts.far`,
    and the tag places its label by a token `gap` that defaults to it. With `back`, the
    foundations' figure fills its background through its token `back` (`figure_token`)."""
    root = project(tmp_path)
    shared = copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    if back:
        figure_token(shared)
    shutil.copytree(
        brand or TEST_BRAND,
        root / "visual" / "libraries" / "test-brand" / "1.0.0",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    folder = copy_library(root, TEST_PARTS, "test-parts", "1.0.0")
    if gap:
        far = "  test-parts.far: {type: dimension}\n"
        replace_in(folder / "roles.yaml", "pairs:\n", f"{far}pairs:\n")
        tag = folder / "components" / "tag.yaml"
        token = "  fill: {type: color, default: '{test-parts.paper}'}\n"
        replace_in(
            tag, token, f"{token}  gap: {{type: dimension, default: '{{test-parts.far}}'}}\n"
        )
        replace_in(tag, 'x: "=@test-parts.gap"', f'x: "=@{GAP_TOKEN}"')
    unreleased = {"1.0.0": {"released": False}}
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": unreleased},
            "test-brand": {"source": {"kind": "project"}, "versions": unreleased},
            "test-parts": {"source": {"kind": "project"}, "versions": unreleased},
        },
    )
    write_piece(
        root,
        "tags",
        lock={"foundations": "1.0.0", "test-brand": "1.0.0", "test-parts": "1.0.0"},
    )
    content = bound("content", body={"use": "test-parts/tag", "label": "Ready"})
    write(root / "visual" / "pieces" / "tags" / "content.en.yaml", yaml_text(content))
    piece = pl.read_piece(root, "visual", "tags")
    return pl.Project(piece, piece.lock, pl.Held(root, "visual"))


def test_a_part_draws_in_the_value_a_brand_that_names_its_library_gives_its_token(
    tmp_path: Path,
) -> None:
    brand = brand_copy(tmp_path / "brand", names=True, given=tag_fill("{palette.white}"))
    project_ = tags_project(tmp_path, brand)
    [(_, result)] = project_.scenes(facts=project_.piece.stand_ins)
    assert result.findings == []
    back = result.scene.find("figure/body/box")
    assert back is not None and back.properties["fill"] == FILL
    assert project_.env.role(FILL) == WHITE
    assert FILL in project_.brand.roles
    assert project_.values()["tokens"][FILL]["type"] == "color"


def test_a_part_reading_a_token_of_the_foundations_figure_draws_in_its_default(
    tmp_path: Path,
) -> None:
    project_ = tags_project(tmp_path, back=True)
    [(_, result)] = project_.scenes(facts=project_.piece.stand_ins)
    assert result.findings == []
    background = result.scene.find("figure/background")
    assert background is not None and background.properties["fill"] == BACK
    assert project_.env.role(BACK) == project_.env.role("background")


def test_the_document_of_values_holds_a_token_the_brand_gives_no_value(tmp_path: Path) -> None:
    project_ = tags_project(tmp_path)
    held = project_.values()["tokens"]
    assert held[FILL] == held["background"]
    assert FILL not in project_.brand.roles


def test_a_part_reading_a_token_with_no_value_under_the_brand_fails_at_the_lock(
    tmp_path: Path,
) -> None:
    project_ = tags_project(tmp_path, gap=True)
    [(_, result)] = project_.scenes(facts=project_.piece.stand_ins)
    (finding,) = [f for f in result.findings if f.code == "unknown-role"]
    assert (finding.where, finding.library, finding.extra) == ("lock", "", {"piece": True})
    assert f"`@{GAP_TOKEN}`" in finding.message
    assert GAP_TOKEN not in project_.values()["tokens"]


# --- a version read in full ----------------------------------------------------------------------


def test_a_version_read_in_full_finds_each_token_its_component_reads_nowhere(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    unread = {"fill": {"type": "color", "default": "{surface}"}}
    lab(
        root,
        {
            "draft": box(unread, "surface"),
            "kept": box(unread, "surface", status="stable"),
            "read": box(unread, "component.lab.read.fill"),
        },
    )
    read = full_read.read(libraries.Held(root, "visual"), "lab", libraries.Version.parse("1.0.0"))
    found = {finding.file.rpartition("/")[2]: finding for finding in read.findings}
    assert set(found) == {"draft.yaml", "kept.yaml"}
    assert {finding.code for finding in found.values()} == {"component-token-unread"}
    assert found["draft.yaml"].level == findings.ATTENTION
    assert found["kept.yaml"].level == findings.FACT
