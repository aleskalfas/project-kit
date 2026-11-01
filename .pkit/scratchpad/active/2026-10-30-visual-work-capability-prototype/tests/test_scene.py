"""The scene: deterministic, one geometry for every mode, unique ids on each page, both content
files of one structure."""

import json
import re

import pytest

from engine import render_svg
from engine.checks import same_structure
from engine.render_svg import render_page
from engine.scene import build, page_ids

COLOUR = re.compile(r"#[0-9a-fA-F]{6}")


def scenes(piece):
    for lang in piece.languages:
        for entry in dict.fromkeys(e for e, _ in piece.preview_targets()):
            for profile in ("standard", "mural"):
                yield lang, entry, profile


def test_the_same_content_renders_identically_twice(piece):
    for lang, entry, profile in scenes(piece):
        brand, _ = piece.brand(entry)
        first = build(piece, lang, entry, profile)
        render_svg._SUBSETS.clear()
        second = build(piece, lang, entry, profile)
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
        if profile == "standard":
            tokens = brand.tokens(profile, brand.modes()[0])
            for a, b in zip(first["pages"], second["pages"]):
                assert render_page(first, a, tokens, piece.root) == render_page(second, b, tokens, piece.root)


def test_a_mode_switch_changes_no_geometry(piece):
    for entry in dict.fromkeys(e for e, _ in piece.preview_targets()):
        brand, _ = piece.brand(entry)
        scene = build(piece, piece.source, entry, "standard")
        for page in scene["pages"]:
            drawn = {m: render_page(scene, page, brand.tokens("standard", m), piece.root) for m in brand.modes()}
            stripped = {m: COLOUR.sub("#", re.sub(r'id="tint-[0-9a-f]+"|url\(#tint-[0-9a-f]+\)', "tint", svg)) for m, svg in drawn.items()}
            assert len(set(stripped.values())) == 1, f"{page['id']}: modes differ in more than colour"
            assert len(set(drawn.values())) == len(drawn), f"{page['id']}: two modes drew the same colours"


def test_each_page_ids_are_unique(piece):
    for lang, entry, profile in scenes(piece):
        for page in build(piece, lang, entry, profile)["pages"]:
            ids = page_ids(page)
            assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]


def test_the_content_files_share_their_structure(piece):
    source = piece.content(piece.source)
    for lang in piece.languages:
        assert same_structure(source, piece.content(lang)) == []


def test_a_changed_structure_is_reported(piece):
    source = piece.content(piece.source)
    changed = json.loads(json.dumps(source))
    changed["extra"] = "x"
    assert same_structure(source, changed)


@pytest.mark.parametrize("lang", ["en", "cs"])
def test_every_text_records_how_it_was_measured(friday, lang):
    scene = build(friday, lang, friday.brand_entry, "standard")
    from engine.scene import walk
    texts = [n for p in scene["pages"] for n, *_ in walk(p["root"]) if n["type"] == "text"]
    assert texts and all(t["font"]["measured"]["by"] == "file" and len(t["font"]["measured"]["sha256"]) == 64 for t in texts)
    mural = build(friday, lang, friday.brand_entry, "mural")
    texts = [n for p in mural["pages"] for n, *_ in walk(p["root"]) if n["type"] == "text"]
    assert {t["font"]["measured"]["by"] for t in texts} == {"file", "estimate"}


def test_czech_keeps_one_letter_words_with_the_next(friday):
    scene = build(friday, "cs", friday.brand_entry, "standard")
    from engine.scene import walk
    for page in scene["pages"]:
        for node, *_ in walk(page["root"]):
            if node["type"] == "text" and not node["font"]["family"].endswith("Mono"):
                for line in node["lines"]:
                    text = "".join(r["text"] for r in line["runs"])
                    assert not re.search(r"(?:^|\s)[kKsSvVzZoOuUaAiI]$", text), text
