"""The head of the next graphic-design calibration's analysis, `analyse.py` (project-kit#3397):

- **the restraint check** flags each file a document lists as read outside the allowlist, and
  no file a document names only to say it was not handed;
- **the model check** compares the model id each document's name for its model holds, as the
  reference pins it.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tech-docs/calibrations/graphic-design-review/next/run/analyse.py"
PINNED = "claude-fable-5-2"
#: The files a document's own folder holds, by the key's digests.
OWN = {"content.en.yaml": "0" * 64, "handed.md": "1" * 64}


@pytest.fixture(scope="module")
def analyse() -> Iterator[ModuleType]:
    spec = importlib.util.spec_from_file_location("graphic_design_calibration_analyse", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Its dataclasses look their module up by name while it loads.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        del sys.modules[spec.name]


def _head(analyse: ModuleType, root: Path, fronts: list[tuple[str | None, list[str]]]) -> dict:
    """The head over one run whose documents give `fronts`: each its model's name and the words
    of what it lists as read. The allowlist is `rules/`, which holds one file."""
    (root / "rules").mkdir(exist_ok=True)
    (root / "rules" / "graphic.md").write_text("rules\n")
    ref = analyse.Reference(
        {
            "piece": "piece",
            "bar": {
                "covers": ["RS-GRAPHIC-001"],
                "at-least": "professional",
                "majors": {"GRAPHIC": 4},
            },
            "places": {"RS-GRAPHIC-001": ["page"]},
            "page-ids": ["one"],
            "order": "counting",
            "model": PINNED,
            "reads": {"review": ["rules/"], "judge": ["rules/"]},
        }
    )
    folders: dict[str, Any] = {}
    readings = {}
    for n, (model, reads) in enumerate(fronts):
        code, version = f"C{n:03}", f"version-{n}"
        entry = {"version": version, "pages": {"1": {"id": "one"}}, "digests": OWN}
        folders[code] = entry
        front = analyse.Front(model, [("read-before-grading", "rule-set", what) for what in reads])
        readings[version] = analyse.Reading("run-1", code, entry, None, None, front, ref, None)
    source = analyse.Source("run-1", "review", {"folders": folders}, readings)
    return analyse.head(ref, root, {"run-1": source}, {"review": None, "judge": None}, {})


def _flagged(found: dict) -> dict[str, list[str]]:
    """Each flagged document's code, with the files it names outside the allowlist."""
    return {
        each["code"]: sorted(each["names outside the allowlist"])
        for each in found["reads"]["run-1"]["flagged"]
    }


# --- the restraint check ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "words",
    [
        "content.en.yaml. No piece.yaml was handed.",
        "content.en.yaml and handed.md. No piece.yaml and no component was handed.",
        "content.en.yaml. No piece.yaml and no component file was handed.",
        "content.en.yaml. No piece.yaml and no brand was handed.",
        "content.en.yaml and handed.md. No piece.yaml, brand or source file was handed.",
        "content.en.yaml; no brand and no piece.yaml were handed",
    ],
)
def test_a_file_named_only_as_not_handed_is_no_read(analyse: ModuleType, words: str) -> None:
    read, not_handed = analyse.said_read(words)
    assert "piece.yaml" not in read
    assert "content.en.yaml" in read
    assert not_handed == ["piece.yaml"]


def test_the_head_flags_no_document_for_a_file_it_was_not_handed(
    analyse: ModuleType, tmp_path: Path
) -> None:
    found = _head(
        analyse,
        tmp_path,
        [(PINNED, ["content.en.yaml and handed.md. No piece.yaml and no component was handed."])],
    )
    assert _flagged(found) == {}
    assert found["reads"]["run-1"]["files named"] == 2
    assert found["reads"]["run-1"]["files named as not handed"] == 1


def test_a_file_named_as_read_beside_a_clause_of_not_handed_is_still_read(
    analyse: ModuleType, tmp_path: Path
) -> None:
    words = "No piece.yaml was handed, so I read .pkit/capabilities/x/piece.yaml instead."
    assert analyse.said_read(words) == ([".pkit/capabilities/x/piece.yaml"], ["piece.yaml"])
    found = _head(analyse, tmp_path, [(PINNED, [words])])
    assert _flagged(found) == {"C000": [".pkit/capabilities/x/piece.yaml"]}


def test_a_clause_that_says_a_file_was_handed_sets_none_aside(analyse: ModuleType) -> None:
    assert analyse.said_read("handed.md and piece.yaml were handed") == (
        ["handed.md", "piece.yaml"],
        [],
    )


def test_the_head_flags_every_file_listed_as_read_outside_the_allowlist(
    analyse: ModuleType, tmp_path: Path
) -> None:
    found = _head(
        analyse,
        tmp_path,
        [
            (PINNED, ["rules/graphic.md and content.en.yaml"]),
            (PINNED, ["rules/graphic.md, notes/elsewhere.md and piece.yaml"]),
        ],
    )
    assert _flagged(found) == {"C001": ["notes/elsewhere.md", "piece.yaml"]}


# --- the model check ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "id_"),
    [
        ("claude-fable-5-2", "claude-fable-5-2"),
        ("claude-fable-5-2 (Fable 5.2)", "claude-fable-5-2"),
        ("Fable 5.2, model ID claude-fable-5-2", "claude-fable-5-2"),
        (
            "claude-fable-5-2 (Fable 5.2), as the harness names it. The harness states no effort.",
            "claude-fable-5-2",
        ),
        ("Claude Opus 5.5 (claude-opus-5-5)", "claude-opus-5-5"),
        ("Fable 5.2", None),
        ("claude-fable-5-2 or claude-opus-5-5", None),
    ],
)
def test_the_model_id_is_the_one_a_name_holds(
    analyse: ModuleType, name: str, id_: str | None
) -> None:
    assert analyse.model_id(name) == id_


def test_the_head_finds_one_pinned_id_however_each_review_words_its_model(
    analyse: ModuleType, tmp_path: Path
) -> None:
    names = [
        "claude-fable-5-2",
        "claude-fable-5-2 (Fable 5.2)",
        "Fable 5.2, model ID claude-fable-5-2",
        "claude-fable-5-2 (Fable 5.2). The harness names no effort.",
    ]
    model = _head(analyse, tmp_path, [(name, []) for name in names])["model"]
    assert model["review ids"] == {PINNED: 4}
    assert model["one id"] is True
    assert model["the pinned id"] is True
    assert sorted(model["review names as written"]) == sorted(names)


@pytest.mark.parametrize(
    ("other", "counted"),
    [
        ("Claude Opus 5.5 (claude-opus-5-5)", "claude-opus-5-5"),
        ("Fable 5.2", "Fable 5.2 (no one model id)"),
        (None, "(no name)"),
    ],
)
def test_the_head_finds_no_one_id_where_a_review_names_another_or_none(
    analyse: ModuleType, tmp_path: Path, other: str | None, counted: str
) -> None:
    model = _head(analyse, tmp_path, [(PINNED, []), (other, [])])["model"]
    assert model["review ids"] == {PINNED: 1, counted: 1}
    assert model["one id"] is False
    assert model["the pinned id"] is False
