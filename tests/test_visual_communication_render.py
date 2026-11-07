"""`pkit visual render <piece>` (visual-communication DEC-002 point 5, DEC-003 point 9,
DEC-005 points 13 and 14): the lock moved and written, the findings record, the previews,
and what it prints. Run in this process, the SVG renderer standing in for the import a run
makes when it draws, and the test producer registered."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import (
    BLOCKS,
    LONG,
    NET,
    PATTERNS,
    PIECE,
    PIECE_FOLDER,
    ROW,
    TESTS,
    drawing_project,
    lab_lock,
    lab_project,
    list_drawing_libraries,
    stamped,
    write_content,
    write_picture,
)
from tests.visual_communication_project import CONFIG, importable, write, write_list
from tests.visual_communication_writes import FULL, failing

script, svg, seam, framing, files, reading, pl, checks, libraries = load(
    "visual-communication",
    "render.py",
    "plugins.svg",
    "plugins.seam",
    "framing",
    "files",
    "reading",
    "pipeline",
    "checks",
    "libraries",
)

PREVIEWS = ".pkit/capabilities/visual-communication/project/local/previews/flow"
FINDINGS = f"{PIECE_FOLDER}/findings.yaml"
TESTS_FOLDER = "visual/libraries/tests/1.0.0"
BRAND_FONT = "visual/libraries/test-brand/1.0.0/fonts/SourceSansPro-Regular.otf"
LOCATION = (
    f"recorded the location `visual` (the default, at the repository's top) in {CONFIG}; "
    f"to move the work, move the folder and change the `location:` line there"
)


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderer stands in for the import a run makes when it draws, and the test
    producer is registered, for the length of the test."""
    importable(monkeypatch, svg)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)
    seam.unregister("svg")


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=root)


def findings_of(root: Path) -> str:
    return (root / FINDINGS).read_text(encoding="utf-8")


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
    assert 'data-key="default"' in light and 'data-renderer="svg 1.0.1"' in light
    assert '<image data-id="figure/body/steps[note]/pictures[square]/image"' in light
    assert ">Here</tspan>" in light and ">The flow.</tspan>" in light
    assert '@font-face{font-family:"Source Sans Pro"' in light
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


def newer_tests(root: Path, *, released: bool = False) -> None:
    """The `tests` library at 1.1.0 too, every version listed as `released` says."""
    folder = root / "visual" / "libraries" / "tests" / "1.1.0"
    shutil.copytree(TESTS, folder)
    library = folder / "library.yaml"
    library.write_text(
        library.read_text(encoding="utf-8").replace("version: 1.0.0", "version: 1.1.0"),
        encoding="utf-8",
    )
    list_drawing_libraries(root, released=released)


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


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({"state": "final"}, id="final"),
        pytest.param({"state": "final", "pinned": True}, id="final-pinned"),
        pytest.param({"state": "published"}, id="published"),
        pytest.param({"state": "published", "pinned": False}, id="published-not-pinned"),
    ],
)
def test_no_render_moves_a_final_or_a_published_lock_with_a_newer_version_held(
    tmp_path: Path, fields: dict[str, Any]
) -> None:
    root = drawing_project(tmp_path, **fields)
    newer_tests(root)
    before = (root / PIECE_FOLDER / "piece.yaml").read_bytes()
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert "lock:" not in shown.stdout
    assert (root / PIECE_FOLDER / "piece.yaml").read_bytes() == before


@pytest.mark.parametrize("state", ["final", "published"])
def test_a_final_or_a_published_lock_that_cannot_be_drawn_refuses_and_says_the_state(
    tmp_path: Path, state: str
) -> None:
    lock = {"foundations": "1.0.0", "test-brand": "2.0.0", "tests": "1.0.0"}
    root = drawing_project(tmp_path, state=state, lock=lock)
    before = (root / PIECE_FOLDER / "piece.yaml").read_bytes()
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert shown.stderr == (
        f"error: visual/pieces/flow/piece.yaml: the piece is {state}, so no render moves its "
        f"lock: the lock names test-brand@2.0.0, which the project does not hold: "
        f"restore it\n"
    )
    assert (root / PIECE_FOLDER / "piece.yaml").read_bytes() == before
    assert not (root / CONFIG).exists()
    assert not (root / FINDINGS).exists()


@pytest.mark.parametrize(
    ("state", "fix"),
    [
        pytest.param(
            "final",
            "write back the lock of the version handed out, which is no move of it",
            id="final",
        ),
        pytest.param("published", "set it back to a draft for its first render", id="published"),
    ],
)
def test_a_final_or_a_published_piece_with_no_lock_is_refused_and_told_of_no_pin(
    tmp_path: Path, state: str, fix: str
) -> None:
    root = drawing_project(tmp_path, state=state, lock=None)
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == (
        f"error: visual/pieces/flow/piece.yaml: the piece is {state}, so no render moves its "
        f"lock: {fix}\n"
    )
    assert not (root / FINDINGS).exists()


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
            "visual/pieces/flow/piece.yaml: the lock names test-brand@2.0.0, which the "
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


def test_a_component_whose_file_cannot_be_read_is_reported_at_that_file(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    (root / TESTS_FOLDER / "components" / "broken.yaml").write_text("parts: [\n", encoding="utf-8")
    write_content(root, body={"use": "tests/broken"})
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    said = (
        f"fails: {TESTS_FOLDER}/components/broken.yaml: the component `tests/broken` cannot be "
        f"read: does not parse as YAML: "
    )
    assert [line for line in shown.stdout.splitlines() if line.startswith(said)]
    assert "unknown-component" not in shown.stdout
    kept = reading.read_yaml(root / FINDINGS)["findings"]
    [entry] = [e for e in kept if e["code"] == "component-unreadable"]
    assert (entry["level"], entry["file"], entry["library"], entry["where"]) == (
        "fails",
        "components/broken.yaml",
        "tests@1.0.0",
        "",
    )
    assert "unknown-component" not in [e["code"] for e in kept]
    assert str(tmp_path) not in entry["message"]


def test_a_font_file_that_cannot_be_read_refuses_the_render_naming_it(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    (root / BRAND_FONT).write_bytes(b"not a font")
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert (
        f"the render of `{PIECE}` is refused before anything is laid out: "
        f"the font file {root / BRAND_FONT} cannot be read: "
    ) in shown.stderr
    assert not (root / PREVIEWS).exists()


# --- what a failed render leaves ----------------------------------------------------------------


def state(root: Path) -> dict[str, bytes | None]:
    """The files a render writes, with their bytes, or None where one is absent."""
    paths = [CONFIG, f"{PIECE_FOLDER}/piece.yaml", FINDINGS]
    found: dict[str, bytes | None] = {
        rel: (root / rel).read_bytes() if (root / rel).exists() else None for rel in paths
    }
    folder = root / PREVIEWS
    for path in sorted(folder.iterdir()) if folder.is_dir() else []:
        found[path.relative_to(root).as_posix()] = path.read_bytes()
    return found


def rendered_once(tmp_path: Path) -> Path:
    """The piece rendered once, its location then unrecorded again, a newer `tests` held,
    so the next render moves its lock, and its first step's text changed, so the next
    render draws other previews."""
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    assert run(root, PIECE).returncode == 0
    (root / CONFIG).unlink()
    newer_tests(root)
    write_content(root, head="Plan the work again.")
    return root


def test_a_key_that_refuses_once_the_lock_is_chosen_leaves_every_file_as_it_was(
    tmp_path: Path,
) -> None:
    root = rendered_once(tmp_path)
    (root / PIECE_FOLDER / "notes.yaml").write_text(
        "pkit_schema: visual-communication:content\nschema_version: 2\n", encoding="utf-8"
    )
    before = state(root)
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert shown.stderr.startswith("error: the findings record's key cannot be taken: ")
    assert "notes.yaml is at format 2" in shown.stderr
    assert state(root) == before


@pytest.mark.parametrize("file", ["flow.en.colour-scheme.dark.svg", "findings.yaml"])
def test_a_write_that_fails_leaves_the_previews_and_every_record_as_they_were(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file: str
) -> None:
    root = rendered_once(tmp_path)
    before = state(root)
    with monkeypatch.context() as patch:
        failing(patch, write={file})
        shown = run(root, PIECE)
    assert shown.returncode == 1
    assert shown.stdout == ""
    folder = PIECE_FOLDER if file == "findings.yaml" else PREVIEWS
    assert shown.stderr == f"error: {folder}/{file} could not be written: {FULL}\n"
    assert state(root) == before
    assert run(root, PIECE).returncode == 0
    assert state(root) != before


def test_an_old_preview_is_removed_only_once_the_new_ones_are_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = rendered_once(tmp_path)
    path = root / PIECE_FOLDER / "piece.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("    - dark\n", ""), encoding="utf-8")
    before = state(root)
    failing(monkeypatch, write={"flow.en.default.svg"})
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert sorted(previews(root)) == ["flow.en.colour-scheme.dark.svg", "flow.en.default.svg"]
    assert state(root) == before


# --- a draft's lock held back from versions that do not fit (DEC-003 point 8, DEC-010 point 2,
# --- DEC-011 point 4) ---------------------------------------------------------------------------

#: Where the render states what it held back.
AT_LOCK = f"fact: {PIECE_FOLDER}/piece.yaml#lock:"


def locked(root: Path) -> dict[str, str]:
    return pl.read_piece(root, "visual", PIECE).lock


def kept_codes(root: Path) -> set[str]:
    return {entry["code"] for entry in reading.read_yaml(root / FINDINGS)["findings"]}


def test_a_draft_is_held_back_from_a_patterns_version_under_which_an_item_clashes(
    tmp_path: Path,
) -> None:
    root = lab_project(
        tmp_path,
        ROW,
        lab_lock("1.0.0", "1.0.0"),
        {"1.0.0": False},
        {"1.0.0": {}, "1.1.0": {"size": True}},
    )

    shown = run(root, PIECE)

    assert shown.returncode == 0, shown.stderr
    said = (
        f"{AT_LOCK} the render held back {PATTERNS}@1.1.0: under it, the item "
        f"`body.items[a]` carries `size`, which both its component `{BLOCKS}/sized` and its "
        "list declare"
    )
    assert said in shown.stdout.splitlines()
    assert locked(root) == lab_lock("1.0.0", "1.0.0")
    assert "held-clash" not in kept_codes(root)


@pytest.mark.parametrize(
    "lock",
    [
        pytest.param(lab_lock("1.0.0", "1.1.0"), id="under-its-lock"),
        pytest.param(None, id="under-a-first-lock"),
    ],
)
def test_a_clash_the_lock_shows_holds_nothing_back_and_its_finding_names_both_mends(
    tmp_path: Path, lock: dict[str, str] | None
) -> None:
    root = lab_project(
        tmp_path,
        ROW,
        lock,
        {"1.0.0": False},
        {"1.1.0": {"size": True}, "1.2.0": {"size": True}},
    )

    shown = run(root, PIECE)

    assert shown.returncode == 0, shown.stderr
    assert "held back" not in shown.stdout
    assert locked(root)[PATTERNS] == "1.2.0"
    [clash] = [f for f, _ in checks.check(root, only=PIECE).judged if f.code == "item-clash"]
    assert clash.fix == (
        "take the key off the item, or move the lock to versions under which the item's "
        "component and its list do not both declare it"
    )


def test_a_draft_is_held_back_from_a_blocks_version_that_draws_an_ends_list_twice(
    tmp_path: Path,
) -> None:
    root = lab_project(
        tmp_path,
        NET,
        lab_lock("1.0.0", "1.0.0"),
        {"1.0.0": False, "1.1.0": True},
        {"1.0.0": {"frame": True}},
    )

    shown = run(root, PIECE)

    assert shown.returncode == 0, shown.stderr
    said = (
        f"{AT_LOCK} the render held back {BLOCKS}@1.1.0: under it, the end `from` of the "
        "tie `body.links[ab]` would not be found; the end `to` of the tie `body.links[ab]` "
        "would not be found"
    )
    assert said in shown.stdout.splitlines()
    assert locked(root) == lab_lock("1.0.0", "1.0.0")
    assert "drawn 2 times" not in shown.stdout
    assert "held-end" not in kept_codes(root)


def test_a_loss_only_both_newest_versions_show_holds_back_the_later_library_alone(
    tmp_path: Path,
) -> None:
    """The content names the patterns, which build on the blocks: the search reaches the
    blocks last, so it backs them off first."""
    root = lab_project(
        tmp_path,
        NET,
        lab_lock("1.0.0", "1.0.0"),
        {"1.0.0": False, "1.1.0": True},
        {"1.0.0": {}, "1.1.0": {"frame": True}},
    )

    shown = run(root, PIECE)

    assert shown.returncode == 0, shown.stderr
    lines = shown.stdout.splitlines()
    assert lines[1:3] == [
        f"lock: foundations 1.0.0, {BLOCKS} 1.0.0, {PATTERNS} 1.1.0, test-brand 1.0.0",
        f"{AT_LOCK} the render held back {BLOCKS}@1.1.0: under it, the end `from` of the "
        "tie `body.links[ab]` would not be found; the end `to` of the tie `body.links[ab]` "
        "would not be found",
    ]


def test_past_its_bound_of_combinations_judged_the_render_keeps_the_lock_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = lab_project(
        tmp_path,
        NET,
        lab_lock("1.0.0", "1.0.0"),
        {"1.0.0": False, "1.1.0": True},
        {"1.0.0": {"frame": True}},
    )
    monkeypatch.setattr(libraries, "SEARCH_JUDGED", 1)

    shown = run(root, PIECE)

    assert shown.returncode == 0, shown.stderr
    said = (
        f"{AT_LOCK} the search for versions that fit together stopped at its bound, 1 "
        f"combinations judged, choosing among those of `foundations`, `{BLOCKS}`, `{PATTERNS}`, "
        "`test-brand`: the lock is kept, with the newest version that fits of each library it "
        "does not name yet; move the lock by hand, or take the versions no piece needs out of "
        "the library folder"
    )
    assert said in shown.stdout.splitlines()
    assert "held back" not in shown.stdout
    assert locked(root) == lab_lock("1.0.0", "1.0.0")


def proposed(root: Path, **given: Any) -> Any:
    """The move proposed for the piece, every version the list names marked released."""
    listed = reading.read_yaml(root / "visual" / "libraries" / "libraries.yaml")["libraries"]
    for library in listed.values():
        library["versions"] = {version: {"released": True} for version in library["versions"]}
    write_list(root, listed)
    piece = pl.read_piece(root, "visual", PIECE)
    held = libraries.Held(root, "visual")
    return libraries.propose_lock(
        held, pl.needed(piece), piece.lock, judge=pl.fit(piece, held), **given
    )


#: What a draft's render says under a version that clashes, and that loses an end.
CLASH = (
    f"the item `body.items[a]` carries `size`, which both its component `{BLOCKS}/sized` and "
    "its list declare"
)
LOST = [f"the end `{end}` of the tie `body.links[ab]` would not be found" for end in ("from", "to")]


def clashing(tmp_path: Path) -> Path:
    """A lab piece under a lock a newer version of the patterns would clash with."""
    lock = lab_lock("1.0.0", "1.0.0")
    return lab_project(
        tmp_path, ROW, lock, {"1.0.0": False}, {"1.0.0": {}, "1.1.0": {"size": True}}
    )


def losing(tmp_path: Path) -> Path:
    """A lab piece under a lock a newer version of the blocks would lose an end under."""
    lock = lab_lock("1.0.0", "1.0.0")
    blocks = {"1.0.0": False, "1.1.0": True}
    return lab_project(tmp_path, NET, lock, blocks, {"1.0.0": {"frame": True}})


def test_a_move_holds_back_a_clash_and_a_lost_end_in_the_words_a_render_uses(
    tmp_path: Path,
) -> None:
    clash = proposed(clashing(tmp_path / "clash"))
    lost = proposed(losing(tmp_path / "loss"))

    assert clash.lock == lost.lock == lab_lock("1.0.0", "1.0.0")
    [held_clash], [held_end] = clash.held_back, lost.held_back
    assert held_clash.label == f"{PATTERNS}@1.1.0"
    assert [(reason.rule, reason.said) for reason in held_clash.reasons] == [("clash", CLASH)]
    assert held_end.label == f"{BLOCKS}@1.1.0"
    assert [(reason.rule, reason.said) for reason in held_end.reasons] == [
        ("end", said) for said in LOST
    ]


def test_a_name_goes_past_a_clash_and_a_lost_end_and_the_check_still_finds_them(
    tmp_path: Path,
) -> None:
    clash = proposed(clashing(tmp_path / "clash"), names=[f"{PATTERNS}@1.1.0"])
    lost = proposed(losing(tmp_path / "loss"), names=[f"{BLOCKS}@1.1.0"])

    assert clash.lock == lab_lock("1.0.0", "1.1.0")
    assert lost.lock == lab_lock("1.1.0", "1.0.0")
    assert (clash.held_back, lost.held_back) == ((), ())
    assert [(misfit.rule, misfit.said) for misfit in clash.past] == [("clash", CLASH)]
    assert [(misfit.rule, misfit.said) for misfit in lost.past] == [("end", said) for said in LOST]


def test_a_pinned_lock_moved_by_hand_to_such_versions_shows_the_item_and_the_tie(
    tmp_path: Path,
) -> None:
    clashing = lab_project(
        tmp_path / "clash",
        ROW,
        lab_lock("1.0.0", "1.1.0"),
        {"1.0.0": False},
        {"1.0.0": {}, "1.1.0": {"size": True}},
        pinned=True,
    )
    losing = lab_project(
        tmp_path / "loss",
        NET,
        lab_lock("1.1.0", "1.0.0"),
        {"1.0.0": False, "1.1.0": True},
        {"1.0.0": {"frame": True}},
        pinned=True,
    )

    shown = run(clashing, PIECE)
    lost = run(losing, PIECE)

    assert (shown.returncode, lost.returncode) == (0, 0), shown.stderr + lost.stderr
    assert "held back" not in shown.stdout + lost.stdout
    report = checks.check(clashing, only=PIECE)
    assert [f.where for f, _ in report.judged if f.code == "item-clash"] == ["lock"]
    assert "the end `cards[a]` is drawn 2 times below `figure/body`" in lost.stdout


# --- the facts of an export ---------------------------------------------------------------------


@pytest.mark.parametrize("shows", ["number", "date", "narrow"])
def test_two_clones_with_different_exports_keep_the_same_findings(
    tmp_path: Path, shows: str
) -> None:
    """A render reads what no file holds from the stand-ins, so what either clone holds
    locally, and the day it runs, change nothing the record keeps (DEC-016 point 5)."""
    roots = [drawing_project(tmp_path / clone, picture=False) for clone in ("one", "two")]
    for root in roots:
        write_content(root, body={"use": "tests/stamp", "shows": shows})
    exports = ".pkit/capabilities/visual-communication/project/local/exports/flow"
    write(roots[1] / exports / "flow.v41.en.default.svg", "<svg/>")
    for root in roots:
        assert run(root, PIECE).returncode == 0
    assert findings_of(roots[0]) == findings_of(roots[1])
    assert ("text-overflow" in findings_of(roots[0])) == (shows == "narrow")


# --- a final piece ------------------------------------------------------------------------------


def handed_out_field(root: Path) -> None:
    """A record of exports that names a version handed out."""
    write(
        root / PIECE_FOLDER / "exports.yaml",
        "pkit_schema: visual-communication:exports\nschema_version: 1\nversions: []\n"
        "handed-out: 1\n",
    )


@pytest.mark.parametrize("by", ["state", "field"])
def test_a_final_pieces_render_draws_its_previews_and_keeps_no_findings_record(
    tmp_path: Path, by: str
) -> None:
    root = drawing_project(tmp_path, state="final" if by == "state" else "draft")
    if by == "field":
        handed_out_field(root)
    newer_tests(root, released=True)
    before = (root / PIECE_FOLDER / "piece.yaml").read_bytes()
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert (root / PIECE_FOLDER / "piece.yaml").read_bytes() == before
    assert "lock:" not in shown.stdout
    assert not (root / FINDINGS).exists()
    assert sorted(path.name for path in (root / PREVIEWS).iterdir()) == [
        "flow.en.colour-scheme.dark.svg",
        "flow.en.default.svg",
    ]
    assert shown.stdout.splitlines()[-1].startswith("findings: ")
    assert " kept in no record: `flow` is final (its " in shown.stdout


def test_a_final_pieces_render_prints_what_it_finds(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert "its library may still change it in any release" in shown.stdout
    assert not (root / FINDINGS).exists()


def test_a_findings_record_left_from_before_stays(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    assert run(root, PIECE).returncode == 0
    record = (root / FINDINGS).read_bytes()
    edit = root / PIECE_FOLDER / "piece.yaml"
    edit.write_text(edit.read_text(encoding="utf-8").replace("state: draft", "state: final"))
    assert run(root, PIECE).returncode == 0
    assert (root / FINDINGS).read_bytes() == record


@pytest.mark.parametrize(("shows", "word"), [("number", "version"), ("date", "date")])
def test_a_final_pieces_preview_takes_the_stand_ins_and_says_so(
    tmp_path: Path, shows: str, word: str
) -> None:
    root = stamped(tmp_path, shows=shows, state="final")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    said = [line for line in shown.stdout.splitlines() if line.startswith("preview: ")]
    assert len(said) == 1
    assert said[0].startswith("preview: a final piece has no next export, so a stand-in shows: `")
    assert word in said[0]


def test_a_final_piece_that_shows_no_fact_says_nothing_of_a_stand_in(tmp_path: Path) -> None:
    root = stamped(tmp_path, shows="files", state="final")
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert "stand-in" not in shown.stdout


def test_a_failed_render_of_a_final_piece_leaves_its_previews_as_they_were(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = drawing_project(tmp_path, state="final")
    assert run(root, PIECE).returncode == 0
    before = {path.name: path.read_bytes() for path in (root / PREVIEWS).iterdir()}
    failing(monkeypatch, write=["flow.en.default.svg"])
    shown = run(root, PIECE)
    assert shown.returncode == 1
    assert FULL in shown.stderr
    assert {path.name: path.read_bytes() for path in (root / PREVIEWS).iterdir()} == before
