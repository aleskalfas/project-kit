"""The check's findings (visual-communication DEC-002 point 4, DEC-003 point 9, DEC-004
points 8, 9 and 11, DEC-005 points 9 and 14): the lock, the ids and fields of the content,
contrast as drawn, the losses a renderer's declaration predicts, and the document the
validator reads. The command around it is `test_visual_communication_check.py`."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load
from tests.test_visual_communication_pipeline import (
    LOCK,
    PIECE,
    PIECE_FOLDER,
    drawing_project,
    write_content,
    write_picture,
)
from tests.visual_communication_project import bound, write, yaml_text

checks, pl, framing, seam, findings_, svg_declaration = load(
    "visual-communication",
    "checks",
    "pipeline",
    "framing",
    "plugins.seam",
    "findings",
    "plugins.svg_declaration",
)

PIECE_FILE = f"{PIECE_FOLDER}/piece.yaml"
CONTENT = f"{PIECE_FOLDER}/content.en.yaml"


@pytest.fixture(autouse=True)
def square() -> Any:
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def piece_of(root: Path) -> Any:
    return pl.read_piece(root, "visual", PIECE)


def project_of(root: Path) -> Any:
    piece = piece_of(root)
    return pl.Project(piece, piece.lock, pl.Held(root, "visual"))


def codes(found: list[Any]) -> list[str]:
    return [finding.code for finding in found]


# --- the lock -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("lock", "code", "message"),
    [
        pytest.param(
            None,
            "lock-missing",
            "the piece has no lock yet, so its scenes cannot be drawn",
            id="missing",
        ),
        pytest.param(
            {"foundations": "1.0.0", "test-brand": "1.0.0"},
            "lock-incomplete",
            "the lock does not name `tests`, which the piece uses",
            id="incomplete",
        ),
        pytest.param(
            {**LOCK, "tests": "1.2.0"},
            "lock-not-held",
            "the lock names tests@1.2.0, which the project does not hold",
            id="not-held",
        ),
        pytest.param(
            {**LOCK, "tests": "one"},
            "lock-version",
            "the lock names `tests: one`, which is no version",
            id="no-version",
        ),
    ],
)
def test_a_lock_that_cannot_draw_the_piece_fails_naming_render(
    tmp_path: Path, lock: dict[str, str] | None, code: str, message: str
) -> None:
    root = drawing_project(tmp_path, lock=lock)
    [finding] = checks.lock_findings(pl.Held(root, "visual"), piece_of(root))
    assert (finding.code, finding.message) == (code, message)
    assert (finding.file, finding.where, finding.level) == (PIECE_FILE, "lock", "fails")
    assert finding.fix == "run `pkit visual render flow`, which moves a draft's lock"


def test_a_pinned_pieces_lock_is_mended_by_hand(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, lock={**LOCK, "tests": "1.2.0"}, pinned=True)
    [finding] = checks.lock_findings(pl.Held(root, "visual"), piece_of(root))
    assert finding.fix == (
        "change the lock by hand, or unpin the piece and run `pkit visual render flow`"
    )


def test_a_whole_lock_has_no_finding(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    assert checks.lock_findings(pl.Held(root, "visual"), piece_of(root)) == []


# --- the content --------------------------------------------------------------------------------


def steps(*entries: dict[str, Any]) -> dict[str, Any]:
    return {"use": "tests/steps", "steps": list(entries)}


def test_ids_are_of_the_id_shape_unique_in_their_list_and_the_same_in_every_language(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, languages=["en", "cs"])
    write_content(root, body=steps({"id": "plan", "head": "A"}, {"id": "plan", "head": "B"}))
    write_content(root, "cs", body=steps({"id": "yes", "head": "A"}, {"id": "plan", "head": "B"}))
    found = checks.id_findings(piece_of(root))
    assert [(f.code, f.file, f.where) for f in found] == [
        ("id-twice", CONTENT, "body.steps"),
        ("id-shape", f"{PIECE_FOLDER}/content.cs.yaml", "body.steps"),
        ("id-languages", f"{PIECE_FOLDER}/content.cs.yaml", "body.steps"),
    ]
    assert found[0].message == (
        "the ids `plan` appear twice in one list: an id is unique in its list"
    )


def test_content_is_checked_against_the_fields_of_each_component_it_fills(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)
    write_content(
        root,
        caption=["not", "text"],
        body=steps(
            {"id": "plan", "haed": "A"},
            {"id": "note", "use": "tests/callout", "pictures": [{"id": "square"}]},
        ),
    )
    found = checks.content_findings(project_of(root))
    assert [(f.code, f.where, f.message) for f in found] == [
        (
            "content-key",
            "body.steps[plan].haed",
            "`tests/card` takes no field or option `haed`; did you mean `head`?",
        ),
        ("content-required", "body.steps[plan].head", "the field `head` is required"),
        ("content-required", "body.steps[note].label", "the field `label` is required"),
        (
            "content-required",
            "body.steps[note].pictures[square].output",
            "the field `output` is required",
        ),
        ("content-type", "caption", "the field holds an array, not string"),
    ]
    assert {f.file for f in found} == {CONTENT}


def test_content_that_fills_its_components_has_no_finding(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    assert checks.content_findings(project_of(root)) == []


# --- contrast as drawn --------------------------------------------------------------------------


def colour(grey: float, alpha: float = 1) -> dict[str, Any]:
    return {"colorSpace": "srgb", "components": [grey, grey, grey], "alpha": alpha}


COLOURS = {
    "paper": {"default": colour(1), "colour-scheme.dark": colour(0)},
    "ink": {"default": colour(0), "colour-scheme.dark": colour(1)},
    "pale": {"default": colour(0.9), "colour-scheme.dark": colour(0.1)},
    "veil": {"default": colour(0, 0.5), "colour-scheme.dark": colour(0, 0.5)},
    "mist": {"default": colour(0.7)},
    "dim": {"default": colour(0.55)},
}
KEYS = ["default", "colour-scheme.dark"]


def text(trace: str, fill: str, *, x: float = 0, size: float = 16, weight: int = 400) -> Any:
    return {
        "type": "text",
        "id": trace,
        "x": x,
        "y": 0,
        "width": 100,
        "height": 20,
        "fill": fill,
        "font-size": size,
        "font-weight": weight,
        "line-height": 20,
        "text-anchor": "start",
        "lines": [{"text": "Word", "width": 40}],
    }


def page(*children: Any) -> dict[str, Any]:
    group = {"type": "group", "id": "figure", "x": 0, "y": 0, "width": 400, "height": 100}
    return {"pages": ["figure"], "children": [{**group, "children": list(children)}]}


def box(trace: str, fill: str, *, x: float = 0, width: float = 400) -> dict[str, Any]:
    return {"type": "box", "id": trace, "x": x, "y": 0, "width": width, "height": 100, "fill": fill}


def test_each_text_is_measured_against_the_fill_under_it_in_every_combination() -> None:
    scene = page(box("figure/back", "paper"), text("figure/low", "pale"), text("figure/ok", "ink"))
    found = checks.drawn_contrast(scene, COLOURS, KEYS)
    assert [(f.code, f.where) for f in found] == [
        ("contrast-drawn", "figure/low"),
        ("contrast-drawn", "figure/low"),
    ]
    assert found[0].message == (
        "`pale` on `paper` has the contrast 1.25 in the combination `default`, below the 4.5 a "
        "text of 16 px needs (`text`)"
    )
    assert found[0].file == "piece.yaml"


def test_large_text_needs_less_and_a_translucent_fill_is_laid_over_the_one_under_it() -> None:
    scene = page(
        box("figure/back", "paper"),
        box("figure/veil", "veil", width=200),
        text("figure/large", "mist", size=24),
        text("figure/bold", "dim", x=210, size=19, weight=700),
        text("figure/regular", "dim", x=210, size=19),
    )
    found = checks.drawn_contrast(scene, COLOURS, ["default"])
    # Mist on half-black over white, a mid grey, falls below large text's 3. Dim on white
    # passes the 3 bold text of 18.66 px needs, and fails the 4.5 the same text needs
    # unbolded.
    assert [(f.where, f.message.split(" in ")[0]) for f in found] == [
        ("figure/large", "`mist` on `veil` has the contrast 1.89"),
        ("figure/regular", "`dim` on `paper` has the contrast 3.35"),
    ]


def test_a_text_over_a_picture_or_over_nothing_is_not_measured() -> None:
    picture = {"type": "image", "id": "figure/pic", "x": 0, "y": 0, "width": 400, "height": 100}
    assert checks.drawn_contrast(page(picture, text("figure/t", "pale")), COLOURS, KEYS) == []
    assert checks.drawn_contrast(page(text("figure/t", "pale")), COLOURS, KEYS) == []


# --- losses -------------------------------------------------------------------------------------


def test_a_renderers_losses_are_known_from_its_declaration_before_it_runs() -> None:
    declaration = {"name": "flat", "draws": {"group": {}, "box": {"x": "draws", "fill": "draws"}}}
    scene = page(
        box("figure/back", "paper"),
        {"type": "ellipse", "id": "figure/dot", "x": 0, "y": 0, "width": 4, "height": 4},
    )
    lost = checks.losses(scene, declaration)
    assert [loss.as_dict() for loss in lost] == [
        {
            "plugin": "flat",
            "what": "figure",
            "did": "left-out",
            "why": "the flat renderer draws no `x` of a group",
        },
        {
            "plugin": "flat",
            "what": "figure",
            "did": "left-out",
            "why": "the flat renderer draws no `y` of a group",
        },
        {
            "plugin": "flat",
            "what": "figure",
            "did": "left-out",
            "why": "the flat renderer draws no `width` of a group",
        },
        {
            "plugin": "flat",
            "what": "figure",
            "did": "left-out",
            "why": "the flat renderer draws no `height` of a group",
        },
        {
            "plugin": "flat",
            "what": "figure/back",
            "did": "left-out",
            "why": "the flat renderer draws no `y` of a box",
        },
        {
            "plugin": "flat",
            "what": "figure/back",
            "did": "left-out",
            "why": "the flat renderer draws no `width` of a box",
        },
        {
            "plugin": "flat",
            "what": "figure/back",
            "did": "left-out",
            "why": "the flat renderer draws no `height` of a box",
        },
        {
            "plugin": "flat",
            "what": "figure/dot",
            "did": "refused",
            "why": "the flat renderer draws no `ellipse`",
        },
    ]


def test_the_svg_renderer_loses_nothing_of_the_skeleton_piece(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    [(_, result)] = project_of(root).scenes()
    assert checks.losses(result.scene.to_dict(), svg_declaration.DECLARATION) == []


def test_a_loss_the_piece_accepts_is_no_finding_and_one_it_does_not_asks_its_author() -> None:
    loss = seam.Loss("svg", "figure/arrow", seam.REFUSED, "the svg renderer draws no `path`")
    accepting = [{"plugin": "svg", "what": "figure/arrow", "reason": "The arrow is drawn apart."}]
    assert checks.accepted(loss, accepting)
    assert not checks.accepted(loss, [{"plugin": "css", "what": "figure/arrow"}])
    finding = checks.loss_finding(loss)
    assert (finding.code, finding.level, finding.who) == ("loss", "attention", "the piece's author")
    assert finding.message == (
        "the svg renderer refuses `figure/arrow`: the svg renderer draws no `path`"
    )
    assert finding.fix == (
        "accept it under `accept-losses` with `plugin: svg`, `what: figure/arrow` and a "
        "reason, or change what draws it"
    )


# --- the run ------------------------------------------------------------------------------------


def test_scene_findings_name_the_component_file_and_the_command_that_makes_a_picture(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)
    report = checks.check(root)
    failing = [(f.code, checks.place(f)) for f, level in report.judged if level == "fails"]
    # The producer's check says the picture is missing, once: the scene's own note of the
    # picture it could not draw repeats it, and is left out.
    assert failing == [
        ("produced-record-missing", f"{PIECE_FOLDER}/produced/square/record.yaml#produced.square"),
        (
            "missing-exposed",
            "visual/libraries/tests/1.0.0/components/callout.yaml#figure/body/steps[note]",
        ),
        (
            "missing-exposed",
            "visual/libraries/tests/1.0.0/components/callout.yaml#figure/body/steps[note]",
        ),
    ]
    [missing] = [f for f, _ in report.judged if f.code == "produced-record-missing"]
    assert "pkit visual produce flow square" in missing.fix


def test_the_skeleton_piece_with_its_picture_fails_nothing(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    report = checks.check(root)
    assert not report.failed()
    assert {f.code for f, _ in report.judged} == {"component-experimental"}
    assert report.summary == [
        "1 piece(s) in `visual`: the scenes of 0 read from their findings record, of 1 "
        "computed now, of 0 not checked."
    ]


def test_past_the_deadline_a_piece_without_a_record_fails_as_not_checked(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    report = checks.check(root, deadline=time.time())
    [(finding, level)] = [(f, level) for f, level in report.judged if f.code == "not-checked"]
    assert level == "fails"
    assert checks.place(finding) == f"{PIECE_FOLDER}/findings.yaml"
    assert finding.fix == "run `pkit visual render flow` and commit its findings record"
    assert "of 0 computed now, of 1 not checked" in report.summary[0]


def test_a_released_pieces_scenes_are_never_computed(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final")
    write_picture(root, framing)
    report = checks.check(root)
    assert [f.code for f, _ in report.judged] == []


def test_a_file_bound_to_another_schema_fails_and_a_piece_named_alone_is_checked_alone(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)
    write(root / PIECE_FOLDER / "exports.yaml", yaml_text(bound("findings", versions=[])))
    write(root / "visual/pieces/other/piece.yaml", "top: [\n")
    report = checks.check(root, only=PIECE)
    bindings = [(f.code, f.file) for f, _ in report.judged if f.code == "binding"]
    assert bindings == [("binding", f"{PIECE_FOLDER}/exports.yaml")]
    assert not any("other" in f.file for f, _ in report.judged)
    missing = checks.check(root, only="nowhere")
    assert [(f.code, f.message) for f, _ in missing.judged] == [
        ("piece-missing", "the location holds no piece `nowhere`")
    ]


def test_no_visual_work_is_said_and_finds_nothing(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / ".pkit" / "capabilities" / "visual-communication").mkdir(parents=True)
    report = checks.check(root)
    assert report.judged == []
    assert report.summary[0].startswith("No visual work: ")


# --- the document -------------------------------------------------------------------------------


def test_the_document_gives_each_finding_its_severity_place_and_what_mends_it() -> None:
    finding = findings_.Finding(
        "loss", "attention", "it is lost", file="a.yaml", where="figure", fix="fix it", who="you"
    )
    plain = findings_.Finding("other", "fact", "a fact", file="b.yaml")
    report = checks.Report(["One."], [(finding, "attention"), (plain, "fact")])
    assert checks.document(report) == {
        "summary": ["One."],
        "findings": [
            {
                "severity": "warning",
                "location": "a.yaml#figure",
                "message": "it is lost — for you — fix it",
                "label": "loss",
            },
            {"severity": "info", "location": "b.yaml", "message": "a fact", "label": "other"},
        ],
    }


@pytest.mark.parametrize(
    ("value", "deadline"),
    [("1700000000.5", 1700000000.5), ("", None), ("soon", None), ("inf", None)],
)
def test_the_deadline_is_read_from_the_environment(value: str, deadline: float | None) -> None:
    assert checks.deadline_from({checks.DEADLINE: value}) == deadline


@pytest.mark.parametrize(
    ("inside", "kind"),
    [
        ("libraries/libraries.yaml", "libraries"),
        ("libraries/tests/1.0.0/library.yaml", "library"),
        ("libraries/tests/1.0.0/components/card.yaml", "component"),
        ("libraries/foundations/1.0.0/roles.yaml", "roles"),
        ("pieces/flow/piece.yaml", "piece"),
        ("pieces/flow/content.en.yaml", "content"),
        ("pieces/flow/findings.yaml", "findings"),
        ("pieces/flow/exports.yaml", "exports"),
        ("pieces/flow/components/own.yaml", "component"),
        ("pieces/flow/produced/square/record.yaml", "produced-record"),
        ("code/brand-css.yaml", "code"),
        ("pieces/flow/notes.yaml", None),
        ("libraries/test-brand/1.0.0/tokens/colour.tokens.json", None),
    ],
)
def test_a_files_kind_is_read_from_its_name_and_place(inside: str, kind: str | None) -> None:
    assert checks.kind_of(inside) == kind
