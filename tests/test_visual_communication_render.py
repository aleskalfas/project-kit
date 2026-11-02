"""`pkit visual render <piece>` (visual-communication DEC-002 point 5, DEC-003 point 9,
DEC-005 points 13 and 14): the lock moved and written, the findings record, the previews,
and what it prints. Run in this process, the SVG renderer standing in for the import a run
makes when it draws, and the test producer registered."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import (
    LONG,
    PIECE,
    PIECE_FOLDER,
    TESTS,
    drawing_project,
    write_picture,
)
from tests.visual_communication_project import CONFIG, write_list

script, svg, seam, framing, files, reading, pl = load(
    "visual-communication",
    "render.py",
    "plugins.svg",
    "plugins.seam",
    "framing",
    "files",
    "reading",
    "pipeline",
)

PREVIEWS = ".pkit/capabilities/visual-communication/project/local/previews/flow"
FINDINGS = f"{PIECE_FOLDER}/findings.yaml"
LOCATION = (
    f"recorded the location `visual` (the default, at the repository's top) in {CONFIG}; "
    f"to move the work, move the folder and change the `location:` line there"
)


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A run imports its renderer when it draws (`seam.implementation`); `load` keeps no
    `_lib` in `sys.modules`, so the renderer it loaded stands in for that import. The test
    producer is registered for the length of the test."""
    monkeypatch.setitem(sys.modules, "_lib.plugins.svg", svg)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)
    seam.unregister("svg")


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=root)


def previews(root: Path) -> dict[str, str]:
    folder = root / PREVIEWS
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(folder.glob("*.svg"))}


def height(svg_text: str) -> float:
    found = re.match(r'<svg [^>]*height="([0-9.]+)"', svg_text)
    assert found is not None
    return float(found.group(1))


def experimental(*traces: tuple[str, str]) -> list[str]:
    return [
        f"fact: {PIECE_FOLDER}/piece.yaml#{trace}: the piece uses `{use}`, which is "
        f"experimental: its library may still change it in any release"
        for trace, use in traces
    ]


EXPERIMENTAL = experimental(
    ("figure", "foundations/figure"),
    ("figure/body", "tests/steps"),
    ("figure/body/steps[note]", "tests/callout"),
    ("figure/body/steps[note]/pictures[square]", "tests/picture"),
    ("figure/body/steps[plan]", "tests/card"),
)


# --- the walking skeleton, end to end -----------------------------------------------------------


def test_it_draws_a_figure_of_steps_and_a_callout_over_a_produced_picture(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, lock=None, head=LONG)
    piece_yaml = (root / PIECE_FOLDER / "piece.yaml").read_text(encoding="utf-8")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    # Without a lock, the piece's picture cannot be produced: the first render writes it.
    assert shown.stdout.splitlines()[:2] == [
        LOCATION,
        "lock: foundations 1.0.0, test-brand 1.0.0, tests 1.0.0",
    ]
    assert (root / PIECE_FOLDER / "piece.yaml").read_text(encoding="utf-8") == (
        piece_yaml + "lock:\n  foundations: 1.0.0\n  test-brand: 1.0.0\n  tests: 1.0.0\n"
    )

    write_picture(root, framing)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.splitlines() == [
        f"previews: 2 file(s) in {PREVIEWS}/",
        *EXPERIMENTAL,
        f"findings: 5 kept in {FINDINGS}",
    ]
    drawn = previews(root)
    assert sorted(drawn) == ["flow.en.colour-scheme.dark.svg", "flow.en.default.svg"]
    light = drawn["flow.en.default.svg"]
    assert 'data-key="default"' in light and 'data-renderer="svg 1.0.0"' in light
    assert '<image data-id="figure/body/steps[note]/pictures[square]/image"' in light
    assert ">Here</tspan>" in light and ">The flow.</tspan>" in light
    assert "@font-face{font-family:'Source Sans Pro'" in light
    assert drawn["flow.en.colour-scheme.dark.svg"] != light

    record = reading.read_yaml(root / FINDINGS)
    assert files.shape_problems(record, "findings") == []
    assert {entry["code"] for entry in record["findings"]} == {"component-experimental"}
    assert all(entry["file"] == "piece.yaml" for entry in record["findings"])


def test_the_figure_grows_with_its_steps_texts_and_nothing_overflows(tmp_path: Path) -> None:
    def drawn(case: str, head: str) -> tuple[float, Any]:
        root = drawing_project(tmp_path / case, head=head)
        write_picture(root, framing)
        assert run(root, PIECE).returncode == 0
        piece = pl.read_piece(root, "visual", PIECE)
        [(_, result)] = pl.Project(piece, piece.lock, pl.Held(root, "visual")).scenes()
        return height(previews(root)["flow.en.default.svg"]), result

    short, _ = drawn("short", "Plan.")
    tall, result = drawn("long", LONG + LONG)
    assert tall > short
    assert [f.code for f in result.findings] == []
    for element in _texts(result.scene.to_dict()):
        assert not element.get("overflow"), element["id"]
        assert element["measured-height"] <= element["height"], element["id"]


def _texts(element: dict[str, Any]) -> Iterator[dict[str, Any]]:
    if element.get("type") == "text":
        yield element
    for child in element.get("children", []):
        yield from _texts(child)


# --- the lock -----------------------------------------------------------------------------------


def newer_tests(root: Path) -> None:
    """The `tests` library at 1.1.0 too, listed."""
    folder = root / "visual" / "libraries" / "tests" / "1.1.0"
    shutil.copytree(TESTS, folder)
    library = folder / "library.yaml"
    library.write_text(
        library.read_text(encoding="utf-8").replace("version: 1.0.0", "version: 1.1.0"),
        encoding="utf-8",
    )
    unreleased = {"released": False}
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": {"1.0.0": unreleased}},
            "test-brand": {"source": {"kind": "project"}, "versions": {"1.0.0": unreleased}},
            "tests": {
                "source": {"kind": "project"},
                "versions": {"1.0.0": unreleased, "1.1.0": unreleased},
            },
        },
    )


def test_a_drafts_lock_moves_to_the_newest_in_its_major_keeping_every_other_byte(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)
    newer_tests(root)
    path = root / PIECE_FOLDER / "piece.yaml"
    path.write_text("# Kept.\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert "lock: foundations 1.0.0, test-brand 1.0.0, tests 1.1.0" in shown.stdout
    assert path.read_text(encoding="utf-8") == before.replace("tests: 1.0.0", "tests: 1.1.0")
    assert files.shape_problems(reading.read_yaml(path), "piece") == []


def test_a_pinned_pieces_lock_stays(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, pinned=True)
    newer_tests(root)
    before = (root / PIECE_FOLDER / "piece.yaml").read_text(encoding="utf-8")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert "lock:" not in shown.stdout
    assert (root / PIECE_FOLDER / "piece.yaml").read_text(encoding="utf-8") == before


# --- findings, losses and refusals --------------------------------------------------------------


def test_a_missing_picture_is_a_finding_naming_produce_and_never_a_refusal(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert (
        f"fails: {PIECE_FOLDER}/content.en.yaml#figure/body/steps[note]/pictures[square]/image: "
        f"figure/body/steps[note]/pictures[square]/image: the piece has no produced output "
        f"`square`: {PIECE_FOLDER}/produced/square/record.yaml does not exist: the picture was "
        f"never produced — run `pkit visual produce flow square`"
    ) in shown.stdout.splitlines()
    assert len(previews(root)) == 2


def test_it_prints_each_loss_the_piece_does_not_accept(tmp_path: Path) -> None:
    """A renderer that declares no `rx` and no `stroke-width` of a box: what the cards lose
    is printed and kept, unless the piece accepts it."""
    declaration = dict(seam.declaration("svg", seam.RENDERER))
    draws = dict(declaration["draws"])
    draws["box"] = {k: v for k, v in draws["box"].items() if k != "stroke-width"}
    seam.register({**declaration, "draws": draws}, svg)
    accepting = [{"plugin": "svg", "what": "figure/body/steps[plan]/box", "reason": "Thin."}]
    root = drawing_project(tmp_path, **{"accept-losses": accepting})
    write_picture(root, framing)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    printed = [line for line in shown.stdout.splitlines() if line.startswith("loss: ")]
    assert printed == [
        "loss: the svg renderer leaves out `figure/body/steps[build]/box`: the svg renderer "
        "draws no `stroke-width` of a box",
    ]
    record = reading.read_yaml(root / FINDINGS)
    assert [entry["where"] for entry in record["findings"] if entry["code"] == "loss"] == [
        "figure/body/steps[build]/box"
    ]


def test_the_previews_of_before_are_replaced(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    assert run(root, PIECE).returncode == 0
    path = root / PIECE_FOLDER / "piece.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("    - dark\n", ""), encoding="utf-8")
    assert run(root, PIECE).returncode == 0
    assert sorted(previews(root)) == ["flow.en.default.svg"]


@pytest.mark.parametrize(
    ("fields", "said"),
    [
        pytest.param(
            {"lock": {"foundations": "1.0.0", "test-brand": "2.0.0", "tests": "1.0.0"}},
            "visual/pieces/flow/piece.yaml: the pinned lock names test-brand@2.0.0, which the "
            "project does not hold",
            id="brand-not-held",
        ),
        pytest.param(
            {"modes": {"colour-scheme": ["sepia"]}},
            "visual/pieces/flow/piece.yaml: `modes`:",
            id="no-such-mode",
        ),
    ],
)
def test_a_refusal_exits_1_and_writes_nothing(
    tmp_path: Path, fields: dict[str, Any], said: str
) -> None:
    pinned = {"pinned": True} if "lock" in fields else {}
    root = drawing_project(tmp_path, **fields, **pinned)
    before = (root / PIECE_FOLDER / "piece.yaml").read_text(encoding="utf-8")
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert shown.stderr.startswith("error: ") and said in shown.stderr
    assert not (root / CONFIG).exists()
    assert not (root / FINDINGS).exists()
    assert not (root / PREVIEWS).exists()
    assert (root / PIECE_FOLDER / "piece.yaml").read_text(encoding="utf-8") == before


def _flow_mapping(root: Path) -> None:
    """`piece.yaml` written as one flow mapping, which cannot take a lock as text."""
    path = root / PIECE_FOLDER / "piece.yaml"
    path.write_text(json.dumps(reading.read_yaml(path)) + "\n", encoding="utf-8")


def _linked_record(root: Path) -> None:
    """The findings record a link to a file elsewhere, which a render never writes through."""
    elsewhere = root / "elsewhere.yaml"
    elsewhere.write_text("", encoding="utf-8")
    (root / FINDINGS).symlink_to(elsewhere)


@pytest.mark.parametrize(
    ("given", "said"),
    [
        pytest.param(_flow_mapping, "piece.yaml cannot take the lock as text", id="lock-text"),
        pytest.param(
            _linked_record,
            f"{FINDINGS} is reached through the link {FINDINGS}",
            id="record-linked",
        ),
    ],
)
def test_a_refusal_found_before_the_first_write_records_no_location(
    tmp_path: Path, given: Any, said: str
) -> None:
    root = drawing_project(tmp_path, lock=None)
    given(root)
    before = (root / PIECE_FOLDER / "piece.yaml").read_text(encoding="utf-8")
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert said in shown.stderr
    assert shown.stdout == ""
    assert not (root / CONFIG).exists()
    assert (root / PIECE_FOLDER / "piece.yaml").read_text(encoding="utf-8") == before
    assert not (root / PREVIEWS).exists()


def test_a_piece_the_location_lacks_is_refused(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    shown = run(root, "other")
    assert shown.returncode == 1
    assert "the location holds no piece `other`" in shown.stderr
