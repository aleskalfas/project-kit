"""The framing of a producer's run (visual-communication DEC-006 points 1 to 5), and what
the check reports of its picture (point 8), with the producer kept for the tests
(`tests/visual_communication_producer.py`), registered in this process.

The piece `flow` declares `marker`, a square filled with `accent`. The test brand's colour
scheme changes `accent` and its contrast does not, so two variants serve its four
combinations. Every refusal leaves the piece's `produced/` folder unwritten and the
location unrecorded.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests import visual_communication_producer as producer
from tests.in_process import load
from tests.visual_communication_producer import LOCK, OUTPUT, PIECE, producing_project
from tests.visual_communication_project import CONFIG, write_piece, yaml_text

framing, seam, location, files, findings_module = load(
    "visual-communication", "framing", "plugins.seam", "location", "files", "findings"
)

PIECE_FOLDER = f"visual/pieces/{PIECE}"
PRODUCED = f"{PIECE_FOLDER}/produced/{OUTPUT}"
RECORD = f"{PRODUCED}/record.yaml"
PALETTE = "visual/libraries/test-brand/1.0.0/tokens/palette.tokens.json"

#: The test brand's `accent`, 8-bit, in each colour scheme (`palette.blue.600`, `.400`).
LIGHT_ACCENT = (9, 105, 218, 255)
DARK_ACCENT = (68, 147, 248, 255)


@pytest.fixture(autouse=True)
def square() -> Iterator[None]:
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def produce(root: Path) -> Any:
    return framing.produce(root, location.for_writing(root), PIECE, OUTPUT)


def refusal(root: Path) -> str:
    """Why a run is refused; and that it wrote nothing in the location."""
    with pytest.raises(framing.Refused) as caught:
        produce(root)
    assert not (root / PIECE_FOLDER / "produced").exists()
    assert not (root / CONFIG).exists()
    return str(caught.value)


def replace_producer(make: Callable[[Mapping[str, Any], Path], Any]) -> None:
    """Register, in the test producer's place, one that runs `make`."""
    producer.register(seam, implementation=SimpleNamespace(produce=make))


def tipped(places: Mapping[str, Any]) -> Callable[[Mapping[str, Any], Path], Any]:
    """A producer that writes the squares and gives `tip` at `places`, by variant."""

    def make(handover: Mapping[str, Any], out: Path) -> Any:
        producer.produce(handover, out)
        return {"points": {"tip": dict(places)}}

    return make


def set_blue(root: Path, shade: str, components: list[float]) -> None:
    """Repaint a blue of the project's copy of the test brand's palette."""
    path = root / PALETTE
    palette = json.loads(path.read_text(encoding="utf-8"))
    palette["palette"]["blue"][shade]["$value"] = {"colorSpace": "srgb", "components": components}
    path.write_text(json.dumps(palette, indent=2), encoding="utf-8")


def edit_record(root: Path, change: Callable[[dict[str, Any]], None]) -> None:
    reader = YAML(typ="safe", pure=True)
    record = reader.load((root / RECORD).read_text(encoding="utf-8"))
    change(record)
    (root / RECORD).write_text(yaml_text(record), encoding="utf-8")


def found(root: Path) -> list[Any]:
    return framing.findings(root, "visual", PIECE)


def coded(root: Path) -> dict[str, Any]:
    """Each finding by its code; one of each."""
    every = found(root)
    by_code = {finding.code: finding for finding in every}
    assert len(by_code) == len(every), every
    return by_code


# --- the plan and the hand-over -----------------------------------------------------------------


def test_one_variant_serves_each_distinct_set_of_the_values_read(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    plan = framing.plan(root, "visual", PIECE, OUTPUT)
    assert plan.combinations == [
        "default",
        "colour-scheme.dark",
        "contrast.high",
        "colour-scheme.dark+contrast.high",
    ]
    assert plan.variants == {
        "default": ["default", "contrast.high"],
        "colour-scheme.dark": ["colour-scheme.dark", "colour-scheme.dark+contrast.high"],
    }


def test_the_hand_over_holds_the_roles_read_alone_with_the_inputs_and_variants(
    tmp_path: Path,
) -> None:
    root = producing_project(tmp_path)
    handed = framing.handover(framing.plan(root, "visual", PIECE, OUTPUT))
    assert handed["document"] == "visual-communication/values"
    assert handed["version"] == 1
    assert handed["lock"] == LOCK
    assert list(handed["tokens"]) == ["accent"]
    assert handed["inputs"] == {"fill": "accent"}
    assert handed["variants"] == {
        "default": {"serves": ["default", "contrast.high"], "pixels": {"width": 64, "height": 64}},
        "colour-scheme.dark": {
            "serves": ["colour-scheme.dark", "colour-scheme.dark+contrast.high"],
            "pixels": {"width": 64, "height": 64},
        },
    }
    assert handed["frames"] == {}


# --- a run --------------------------------------------------------------------------------------


def test_a_run_keeps_each_variant_and_a_record_the_schema_holds(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    done = produce(root)
    assert done.record == root / RECORD
    assert done.removed == ()
    assert done.location is not None and "recorded the location `visual`" in done.location
    assert sorted(path.name for path in (root / PRODUCED).iterdir()) == [
        "colour-scheme.dark.png",
        "default.png",
        "record.yaml",
    ]
    assert producer.pixel((root / PRODUCED / "default.png").read_bytes()) == LIGHT_ACCENT
    assert producer.pixel((root / PRODUCED / "colour-scheme.dark.png").read_bytes()) == DARK_ACCENT
    record = files.read_bound(root / RECORD, "produced-record")
    assert files.shape_problems(record, "produced-record") == []
    assert record["combinations"] == {
        "default": "default",
        "colour-scheme.dark": "colour-scheme.dark",
        "contrast.high": "default",
        "colour-scheme.dark+contrast.high": "colour-scheme.dark",
    }
    assert record["points"] == {
        "tip": {"default": {"x": 32, "y": 0}, "colour-scheme.dark": {"x": 32, "y": 0}}
    }
    assert record["recorded"]["plugins"] == {"square": "1.0.0"}
    assert record["recorded"]["programs"] == {}
    assert record["recorded"]["capability"] == "0.1.0"
    assert "time: '" in (root / RECORD).read_text(encoding="utf-8")
    assert found(root) == []


def test_the_fingerprint_reads_the_declaration_each_value_each_size_and_the_producer(
    tmp_path: Path,
) -> None:
    root = producing_project(tmp_path)
    produce(root)
    identities = [
        {key: value for key, value in entry.items() if key != "sha256"}
        for entry in files.read_bound(root / RECORD, "produced-record")["fingerprint"]["inputs"]
    ]
    assert identities == [
        {"file": "piece.yaml", "keys": ["produced", "marker"]},
        {"pixels": "colour-scheme.dark", "width": 64, "height": 64},
        {"pixels": "default", "width": 64, "height": 64},
        {"value": "accent", "key": "colour-scheme.dark"},
        {"value": "accent", "key": "colour-scheme.dark+contrast.high"},
        {"value": "accent", "key": "contrast.high"},
        {"value": "accent", "key": "default"},
        {"plugin": "square", "version": "1.0.0"},
    ]


def test_the_hand_over_stays_local_and_the_run_folder_goes(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    produce(root)
    local = root / framing.HANDOVER / PIECE
    assert json.loads((local / f"{OUTPUT}.json").read_text(encoding="utf-8"))["inputs"] == {
        "fill": "accent"
    }
    assert not (local / OUTPUT).exists()


def test_a_variant_left_from_before_is_removed(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    produce(root)
    write_piece(
        root,
        PIECE,
        modes={"colour-scheme": ["light"]},
        produced=files.read_bound(root / PIECE_FOLDER / "piece.yaml", "piece")["produced"],
        lock=LOCK,
    )
    done = produce(root)
    assert done.removed == ("colour-scheme.dark.png",)
    assert sorted(path.name for path in (root / PRODUCED).iterdir()) == [
        "default.png",
        "record.yaml",
    ]
    assert found(root) == []


# --- staleness ----------------------------------------------------------------------------------


def test_the_picture_is_stale_when_a_value_it_read_changes_in_the_brand(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    produce(root)
    set_blue(root, "600", [0.1, 0.2, 0.3])
    stale = coded(root)["produced-stale"]
    assert stale.level == findings_module.ATTENTION
    assert stale.file == RECORD
    assert stale.who
    assert "the value of `accent` in `default` changed" in stale.message
    assert "the value of `accent` in `contrast.high` changed" in stale.message
    assert "colour-scheme.dark" not in stale.message
    assert stale.fix == f"run `pkit visual produce {PIECE} {OUTPUT}`"
    produce(root)
    assert found(root) == []


def test_a_value_it_does_not_read_changing_leaves_it_fresh(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    produce(root)
    path = root / PALETTE
    palette = json.loads(path.read_text(encoding="utf-8"))
    palette["palette"]["grey"]["900"]["$value"]["components"] = [0.1, 0.1, 0.1]
    path.write_text(json.dumps(palette, indent=2), encoding="utf-8")
    assert found(root) == []


def test_a_combination_the_record_maps_to_no_variant_is_stale(tmp_path: Path) -> None:
    root = producing_project(tmp_path, modes={"colour-scheme": ["light", "dark"]})
    produce(root)
    produced = files.read_bound(root / PIECE_FOLDER / "piece.yaml", "piece")["produced"]
    write_piece(root, PIECE, modes=producer.EVERY_MODE, produced=produced, lock=LOCK)
    stale = coded(root)["produced-stale"]
    assert "the combination `contrast.high` has no variant" in stale.message
    assert "the combination `colour-scheme.dark+contrast.high` has no variant" in stale.message


# --- what a run refuses -------------------------------------------------------------------------


def test_a_piece_with_no_lock_is_refused_naming_its_first_render(tmp_path: Path) -> None:
    root = producing_project(tmp_path, lock=None)
    assert "run `pkit visual render flow` first" in refusal(root)


@pytest.mark.parametrize(
    ("lock", "why"),
    [
        (
            {"test-brand": "1.0.0"},
            "the lock of `flow` names no version of `foundations`: run `pkit visual render flow`",
        ),
        (
            {"foundations": "1.0.0", "test-brand": "2.0.0"},
            "test-brand@2.0.0, which the lock of `flow` names: the project holds no version",
        ),
    ],
    ids=["foundations", "version"],
)
def test_a_lock_that_does_not_name_a_version_held_is_refused(
    tmp_path: Path, lock: dict[str, str], why: str
) -> None:
    root = producing_project(tmp_path, lock=lock)
    assert why in refusal(root)


def test_an_input_changed_during_the_run_is_refused(tmp_path: Path) -> None:
    root = producing_project(tmp_path)

    def repaint(handover: Mapping[str, Any], out: Path) -> Any:
        set_blue(root, "400", [0.5, 0.5, 0.5])
        return producer.produce(handover, out)

    replace_producer(repaint)
    why = refusal(root)
    assert "an input changed while the producer ran" in why
    assert "the value of `accent` in `colour-scheme.dark` changed" in why


def test_a_variant_file_left_unwritten_is_refused(tmp_path: Path) -> None:
    root = producing_project(tmp_path)

    def one(handover: Mapping[str, Any], out: Path) -> Any:
        result = producer.produce(handover, out)
        (out / "colour-scheme.dark.png").unlink()
        return result

    replace_producer(one)
    assert "it wrote no file for the variant `colour-scheme.dark`" in refusal(root)


def test_a_variant_of_another_pixel_size_is_refused(tmp_path: Path) -> None:
    root = producing_project(tmp_path)

    def small(handover: Mapping[str, Any], out: Path) -> Any:
        result = producer.produce(handover, out)
        (out / "default.png").write_bytes(producer.png(32, 64, LIGHT_ACCENT))
        return result

    replace_producer(small)
    assert "`default.png` is 32×64 pixels, and the piece declares 64×64" in refusal(root)


def test_a_variant_that_is_no_png_is_refused(tmp_path: Path) -> None:
    root = producing_project(tmp_path)

    def text(handover: Mapping[str, Any], out: Path) -> Any:
        result = producer.produce(handover, out)
        (out / "default.png").write_text("a square", encoding="utf-8")
        return result

    replace_producer(text)
    assert "`default.png` is not a PNG" in refusal(root)


def test_a_point_some_variant_lacks_is_refused(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    replace_producer(tipped({"default": {"x": 32, "y": 0}}))
    assert "the point `tip` is missing from the variant `colour-scheme.dark`" in refusal(root)


def test_a_point_at_another_place_in_a_variant_one_scene_holds_is_refused(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    replace_producer(
        tipped({"default": {"x": 32, "y": 0}, "colour-scheme.dark": {"x": 30, "y": 0}})
    )
    why = refusal(root)
    assert "the point `tip` lies at different places in variants one scene holds" in why
    assert "(32, 0) in `default`, (30, 0) in `colour-scheme.dark`" in why


def test_a_point_outside_the_pixels_is_refused(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    replace_producer(
        tipped({"default": {"x": 65, "y": 0}, "colour-scheme.dark": {"x": 65, "y": 0}})
    )
    assert "the point `tip` lies at (65, 0) in `default`, outside its 64×64 pixels" in refusal(root)


@pytest.mark.parametrize(
    ("result", "why"),
    [
        ({"points": {"tip": "top"}}, "the point `tip` is not a mapping"),
        ({"points": {"Tip": {}}}, "the point `Tip` is not a name"),
        (
            {"points": {"tip": {"default": {"x": "32", "y": 0}, "colour-scheme.dark": {}}}},
            "the point `tip` in `default` is not `{x, y}`, two numbers",
        ),
        ({}, "it gave no `points`"),
        ({"points": {}, "programs": ["blender"]}, "its `programs` is not a mapping"),
        (
            {"points": {}, "programs": {"blender": "4.2"}},
            "it called `blender`, which its declaration does not name under `programs`",
        ),
        ({"points": {}, "frames": {}}, "returned `frames`, which seam 3 does not read"),
        ({"points": {}, "losses": {}}, "its `losses` is not a list"),
        (
            {"points": {}, "losses": [{"plugin": "square", "what": "line", "did": "lost"}]},
            "its loss 1 is not of the seam's one form",
        ),
        (
            {
                "points": {},
                "losses": [{"plugin": "svg", "what": "line", "did": "left-out", "why": "no edge"}],
            },
            "its loss 1 names the plugin `svg`, not `square`",
        ),
        (
            {
                "points": {},
                "losses": [{"plugin": "square", "what": "line", "did": "lost", "why": "no edge"}],
            },
            "its loss 1 did `lost`, which is not one of approximated, picture, left-out, refused",
        ),
        (
            {
                "points": {},
                "losses": [{"plugin": "square", "what": "the line", "did": "left-out", "why": " "}],
            },
            "its loss 1 names no trace id or token path under `what`, or no reason under `why`",
        ),
    ],
    ids=[
        "place",
        "name",
        "number",
        "no-points",
        "programs",
        "undeclared-program",
        "unread-key",
        "losses",
        "loss-keys",
        "loss-plugin",
        "loss-did",
        "loss-blank",
    ],
)
def test_a_result_not_of_seam_1s_form_is_refused(
    tmp_path: Path, result: dict[str, Any], why: str
) -> None:
    root = producing_project(tmp_path)

    def give(handover: Mapping[str, Any], out: Path) -> Any:
        producer.produce(handover, out)
        return result

    replace_producer(give)
    assert why in refusal(root)


def test_a_picture_kept_through_a_link_is_refused_before_the_location_is_recorded(
    tmp_path: Path,
) -> None:
    root = producing_project(tmp_path)
    elsewhere = root / "elsewhere"
    elsewhere.mkdir()
    (root / PIECE_FOLDER / "produced").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(framing.Refused, match="is reached through the link"):
        produce(root)
    assert not (root / CONFIG).exists()
    assert list(elsewhere.iterdir()) == []


def test_a_producer_that_fails_is_refused_naming_its_error(tmp_path: Path) -> None:
    root = producing_project(tmp_path)

    def fail(handover: Mapping[str, Any], out: Path) -> Any:
        raise RuntimeError("no GPU")

    replace_producer(fail)
    assert "the producer `square` 1.0.0 failed, so nothing was kept: RuntimeError: no GPU" in (
        refusal(root)
    )


def marker(**changed: Any) -> dict[str, Any]:
    """`marker`'s declaration, with `changed` laid over it."""
    declared = {
        "producer": "square",
        "inputs": {"fill": "accent"},
        "pixels": {"width": 64, "height": 64},
    }
    return {OUTPUT: {**declared, **changed}}


@pytest.mark.parametrize(
    ("produced", "why"),
    [
        ({"markers": marker()[OUTPUT]}, "declares no produced output `marker`"),
        (marker(producer="cube"), "there is no producer `cube` (the producers: square)"),
        (
            marker(inputs={"fil": "accent"}),
            "the producer `square` takes no input `fil` (did you mean `fill`?)",
        ),
        (marker(inputs={"fill": "#0969da"}), "is `#0969da`, which is no role"),
        (
            marker(inputs={"fill": "acent"}),
            "names `acent`, which is no role of the brand test-brand 1.0.0 (did you mean "
            "`accent`?)",
        ),
        (
            marker(inputs={"fill": "space.1"}),
            "takes a role of type `color`, and `space.1` is of type `dimension`",
        ),
        (marker(inputs={}), "leaves out the input `fill` that the producer `square` requires"),
        (marker(pixels={"width": 64}), "has no `pixels` of a whole `width` and `height`"),
    ],
    ids=["output", "producer", "input", "raw", "role", "type", "required", "pixels"],
)
def test_a_declaration_the_producer_cannot_take_is_refused(
    tmp_path: Path, produced: dict[str, Any], why: str
) -> None:
    root = producing_project(tmp_path, produced=produced)
    assert why in refusal(root)


def test_a_producer_whose_declaration_breaks_seam_1_is_refused(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    broken = json.loads(json.dumps(producer.DECLARATION))
    del broken["inputs"]["properties"]["fill"]["x-pkit-role"]
    producer.register(seam, declaration=broken)
    assert "has an input `fill` not marked `x-pkit-role`" in refusal(root)


@pytest.mark.parametrize(
    ("needs", "why"),
    [
        ({"programs": "blender"}, "names its `programs` other than as a list of names"),
        ({"services": [""]}, "names its `services` other than as a list of names"),
        ({"programs": ["blender", "blender"]}, "names `blender` twice under `programs`"),
    ],
    ids=["programs", "services", "twice"],
)
def test_a_declaration_naming_its_needs_out_of_form_is_refused(
    tmp_path: Path, needs: dict[str, Any], why: str
) -> None:
    root = producing_project(tmp_path)
    producer.register(seam, declaration={**producer.DECLARATION, **needs})
    assert f"the producer `square`'s declaration {why}" in refusal(root)


def test_a_producer_that_reaches_a_service_is_refused_before_it_runs(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    ran: list[str] = []
    producer.register(
        seam,
        declaration={**producer.DECLARATION, "services": ["whiteboard"]},
        implementation=SimpleNamespace(produce=lambda handover, out: ran.append("ran")),
    )
    why = refusal(root)
    assert why.startswith(
        "the producer `square` 1.0.0 reaches the service `whiteboard`, and the project's "
        "configuration turns on no plugin that reaches a service"
    )
    assert ran == []


def test_a_program_the_producer_calls_that_the_machine_lacks_is_refused_before_it_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = producing_project(tmp_path)
    monkeypatch.setattr(framing.shutil, "which", lambda name: None)
    ran: list[str] = []
    producer.register(
        seam,
        declaration={**producer.DECLARATION, "programs": ["blender"]},
        implementation=SimpleNamespace(produce=lambda handover, out: ran.append("ran")),
    )
    assert refusal(root) == (
        "the producer `square` 1.0.0 calls `blender`, which this machine lacks: install it, "
        "then run `pkit visual produce flow marker` again"
    )
    assert ran == []


def test_a_program_it_declares_and_calls_is_recorded_with_its_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = producing_project(tmp_path)
    monkeypatch.setattr(framing.shutil, "which", lambda name: f"/usr/bin/{name}")

    def calling(handover: Mapping[str, Any], out: Path) -> Any:
        return {**producer.produce(handover, out), "programs": {"blender": "4.2"}}

    producer.register(
        seam,
        declaration={**producer.DECLARATION, "programs": ["blender"]},
        implementation=SimpleNamespace(produce=calling),
    )
    produce(root)
    assert files.read_bound(root / RECORD, "produced-record")["recorded"]["programs"] == {
        "blender": "4.2"
    }


# --- what a producer loses ----------------------------------------------------------------------

#: What the square loses of a piece that names it an edge (`line`), in the seam's one form.
EDGE_LOSS = {"plugin": "square", "what": "line", "did": "left-out", "why": producer.NO_EDGE}


def edged(tmp_path: Path, **fields: Any) -> Path:
    """The project, its `marker` given an edge the square leaves out."""
    return producing_project(
        tmp_path, produced=marker(inputs={"fill": "accent", "edge": "line"}), **fields
    )


def test_a_loss_the_producer_reports_is_kept_in_its_record_and_asks_for_attention(
    tmp_path: Path,
) -> None:
    root = edged(tmp_path)
    done = produce(root)
    assert done.losses == (seam.Loss(**EDGE_LOSS),)
    assert done.unaccepted == done.losses
    record = files.read_bound(root / RECORD, "produced-record")
    assert files.shape_problems(record, "produced-record") == []
    assert record["losses"] == [EDGE_LOSS]
    loss = coded(root)["loss"]
    assert loss.level == findings_module.ATTENTION
    assert loss.message == (
        "the square producer leaves out `line`: a square of one colour draws no edge"
    )
    assert (loss.file, loss.where) == (f"{PIECE_FOLDER}/piece.yaml", f"produced.{OUTPUT}")
    assert loss.who == "the piece's author"
    assert loss.fix.startswith(
        "accept it under `accept-losses` with `plugin: square`, `what: line`"
    )


def test_a_loss_the_piece_accepts_is_kept_and_reported_no_more(tmp_path: Path) -> None:
    accepting = {"plugin": "square", "what": "line", "reason": "The marker needs no edge."}
    root = edged(tmp_path, accept_losses=[accepting])
    done = produce(root)
    assert done.unaccepted == ()
    assert files.read_bound(root / RECORD, "produced-record")["losses"] == [EDGE_LOSS]
    assert found(root) == []


def test_a_run_that_loses_nothing_records_no_loss(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    assert produce(root).losses == ()
    assert files.read_bound(root / RECORD, "produced-record")["losses"] == []


def test_a_loss_reported_twice_is_kept_once(tmp_path: Path) -> None:
    root = edged(tmp_path)

    def twice(handover: Mapping[str, Any], out: Path) -> Any:
        result = producer.produce(handover, out)
        return {**result, "losses": result["losses"] * 2}

    replace_producer(twice)
    assert produce(root).losses == (seam.Loss(**EDGE_LOSS),)


# --- what the check reports ---------------------------------------------------------------------


def test_a_declared_output_never_produced_fails_for_its_missing_record(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    missing = coded(root)["produced-record-missing"]
    assert missing.level == findings_module.FAILS
    assert missing.file == RECORD
    assert missing.fix == f"run `pkit visual produce {PIECE} {OUTPUT}`"


def test_a_record_naming_a_missing_variant_file_fails(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    produce(root)
    (root / PRODUCED / "colour-scheme.dark.png").unlink()
    missing = coded(root)["produced-variant-missing"]
    assert missing.level == findings_module.FAILS
    assert missing.where == "variants.colour-scheme.dark"


def test_a_variant_file_replaced_by_hand_fails(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    produce(root)
    (root / PRODUCED / "default.png").write_bytes(producer.png(64, 64, (255, 0, 0, 255)))
    changed = coded(root)["produced-variant-changed"]
    assert changed.level == findings_module.FAILS
    assert changed.file == f"{PRODUCED}/default.png"


def test_a_record_whose_points_differ_between_variants_fails(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    produce(root)

    def move(record: dict[str, Any]) -> None:
        record["points"]["tip"]["colour-scheme.dark"]["x"] = 10

    edit_record(root, move)
    points = coded(root)["produced-points"]
    assert points.level == findings_module.FAILS
    assert "lies at different places in variants one scene holds" in points.message


def test_a_declaration_the_producer_no_longer_takes_fails_the_check(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    produce(root)
    write_piece(
        root,
        PIECE,
        modes=producer.EVERY_MODE,
        produced=marker(inputs={"fill": "space.1"}),
        lock=LOCK,
    )
    unverified = coded(root)["produced-unverified"]
    assert unverified.level == findings_module.FAILS
    assert unverified.file == f"{PIECE_FOLDER}/piece.yaml"
    assert "`space.1` is of type `dimension`" in unverified.message


def test_a_record_that_cannot_be_checked_for_its_lock_asks_for_attention(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    produce(root)
    produced = files.read_bound(root / PIECE_FOLDER / "piece.yaml", "piece")["produced"]
    write_piece(root, PIECE, modes=producer.EVERY_MODE, produced=produced)
    unverified = coded(root)["produced-unverified"]
    assert unverified.level == findings_module.ATTENTION
    assert "run `pkit visual render flow` first" in unverified.message


def test_a_produced_folder_the_piece_does_not_declare_asks_for_attention(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    produce(root)
    (root / PIECE_FOLDER / "produced" / "old").mkdir()
    (root / PIECE_FOLDER / "produced" / "old" / "default.png").write_bytes(b"")
    undeclared = coded(root)["produced-undeclared"]
    assert undeclared.level == findings_module.ATTENTION
    assert undeclared.file == f"{PIECE_FOLDER}/produced/old"


def test_a_final_piece_refuses_a_run_and_what_only_reads_its_picture_still_runs(
    tmp_path: Path,
) -> None:
    root = producing_project(tmp_path)
    produce(root)
    record = (root / RECORD).read_bytes()
    piece = root / PIECE_FOLDER / "piece.yaml"
    piece.write_text(
        piece.read_text(encoding="utf-8").replace("state: draft", "state: final"), encoding="utf-8"
    )
    with pytest.raises(framing.Refused, match="a final piece takes no producer's run"):
        produce(root)
    assert (root / RECORD).read_bytes() == record
    assert framing.plan(root, "visual", PIECE, OUTPUT).output == OUTPUT
    assert framing.findings(root, "visual", PIECE) == []


def test_a_piece_that_declares_nothing_produced_has_no_findings(tmp_path: Path) -> None:
    root = producing_project(tmp_path)
    write_piece(root, PIECE, lock=LOCK)
    assert found(root) == []
    assert framing.findings(root, "visual", "no-such-piece") == []


def test_the_record_says_who_writes_it_and_shares_no_node(tmp_path: Path) -> None:
    """Its variants' pixel sizes are equal, and are still written out each time, never
    as an anchor and its aliases."""
    root = producing_project(tmp_path)
    produce(root)
    text = (root / RECORD).read_text(encoding="utf-8")
    assert text.startswith("# Written by `pkit visual produce`, never by hand")
    assert "&id" not in text and "*id" not in text
