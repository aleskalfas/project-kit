"""Where the check places what the engine finds: in the file a person edits to mend it
(visual-communication DEC-002 point 7, DEC-005 point 14; #2428).

Each piece here is the project the check tests draw (`drawing_project`, with no produced
picture), its body a component written for the test, in the `tests` library's locked
version or in the piece's own `components/`. Each finding is read as the check reports it.

- a fault in a component, read with it or found while the scene is computed: in that
  component's file, a library's or the piece's own; a local top that is no top;
- a fault in what a component's part gave the component it places: in the giver's file;
- a fault in what the content gave, passed on by a part or not: in the content file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.in_process import load
from tests.test_visual_communication_pipeline import (
    PIECE,
    PIECE_FOLDER,
    drawing_project,
    write_content,
)
from tests.visual_communication_project import bound, write, yaml_text

(checks,) = load("visual-communication", "checks")

LIBRARY = "visual/libraries/tests/1.0.0/components"
OWN = f"{PIECE_FOLDER}/components"
CONTENT = f"{PIECE_FOLDER}/content.en.yaml"

#: A box a component draws at a size of its own.
BOX = {"box": {"fill": "surface"}, "width": "=@space.1", "height": "=@space.1"}


def component(**keys: Any) -> str:
    """A component's file: a block as large as @space.4, `keys` added or replacing."""
    data = bound(
        "component",
        status="experimental",
        about="A component a test of the check draws.",
        fields={"type": "object", "properties": {}},
        parts={"b": BOX},
        preferred={"width": "=@space.4", "height": "=@space.4"},
    )
    data.update(keys)
    return yaml_text(data)


def placed(root: Path) -> dict[str, list[str]]:
    """Where each failing finding of the piece lies, by label."""
    found: dict[str, list[str]] = {}
    for finding, level in checks.check(root, only=PIECE).judged:
        if level == "fails":
            found.setdefault(finding.code, []).append(checks.place(finding))
    return found


def test_a_fault_in_the_pieces_own_component_points_at_its_file(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    painted = {"box": {"fill": ":colour.fill"}, "width": "=:width - 6", "height": "=@space.1"}
    write(root / OWN / "own.yaml", component(parts={"b": painted}))
    write_content(root, body={"use": "piece/own"})

    found = placed(root)

    assert found["formula-dimension"] == [f"{OWN}/own.yaml#parts.b.width"]
    assert found["no-colour"] == [f"{OWN}/own.yaml#figure/body/b"]


def test_a_local_top_that_declares_no_layouts_points_at_its_file(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, top="piece/own")
    write(root / OWN / "own.yaml", component())

    assert placed(root)["not-top"] == [f"{OWN}/own.yaml#own"]


def test_a_fault_the_engine_finds_at_a_part_points_at_its_component(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    fields = {
        "label": {"type": "string"},
        "items": {"type": "array", "items": {"type": "object"}},
    }
    parts = {
        "b": {**BOX, "box": {"fill": ":colour.fill"}},
        "t": {"text": {"content": "label", "style": "type.none"}},
        "items": {"repeat": "items", "draw": "tests/card", "row": {"sizes": "equal"}},
        "p": {"use": "tests/nothing"},
        "me": {"use": "tests/faulty"},
    }
    write(
        root / LIBRARY / "faulty.yaml",
        component(fields={"type": "object", "properties": fields}, parts=parts),
    )
    write_content(
        root, body={"use": "tests/faulty", "label": "x", "items": [{"id": "a", "head": "A"}]}
    )

    found = placed(root)

    file = f"{LIBRARY}/faulty.yaml"
    assert found["no-colour"] == [f"{file}#figure/body/b"]
    assert found["unknown-role"] == [f"{file}#figure/body/t"]
    assert found["no-size"] == [f"{file}#figure/body/items"]
    assert found["unknown-component"] == [f"{file}#figure/body/p"]
    assert found["places-itself"] == [f"{file}#figure/body/me"]


def test_a_fault_in_what_a_part_gave_points_at_the_component_that_gave_it(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False)
    inner = component(
        fields={"type": "object", "properties": {"label": {"type": "string"}}},
        options={"size": ["small", "large"]},
        parts={"b": BOX, "t": {"text": {"content": "label", "style": "type.body"}}},
    )
    outer = component(
        fields={"type": "object", "properties": {"title": {"type": "string"}}},
        parts={
            "inner": {
                "use": "tests/inner",
                "fields": {"label": "title"},
                "options": {"size": "huge"},
            }
        },
    )
    write(root / LIBRARY / "inner.yaml", inner)
    write(root / LIBRARY / "outer.yaml", outer)
    # The title is a list where text belongs: the content gave it, and the part passed it on.
    write_content(root, body={"use": "tests/outer", "title": ["no text"]})

    found = placed(root)

    assert found["option-word"] == [f"{LIBRARY}/outer.yaml#figure/body/inner"]
    assert found["content-shape"] == [f"{CONTENT}#figure/body/inner/t"]


def test_a_fault_in_what_the_content_gave_points_at_the_content(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    write(root / LIBRARY / "inner.yaml", component(options={"size": ["small", "large"]}))
    write_content(root, body={"use": "tests/inner", "size": "huge"})

    assert placed(root)["option-word"] == [f"{CONTENT}#figure/body"]
