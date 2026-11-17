"""What the viewing step's report says of the checks (visual-communication DEC-062 points 1
and 2): the step runs the checks a render runs on the scenes it computes, gives each image
the findings that hold on it, lists apart those on no image drawn, and names the checks that
measured each image, by their ids, with their reach and the capability's version.

- **The findings of the files as they stand,** whatever a render last kept, and at each key
  over the size axes of each language drawn, whichever keys are drawn.
- **Each image, only what holds on it:** a finding on several pages, in several languages or
  at several places is given to each image that shows it; one that names no place, to each
  image of its languages and keys; one at a key not drawn, to none, and is listed apart.
- **The checks that measured an image** are those that state a reach and ran on its scene,
  none of colour on a forced image, none where the checks' code stopped on the scene, and
  none that compares a scene the code stopped on.

Run in this process, the renderers standing in for the import a run makes when it draws, as
`test_visual_communication_look.py` runs them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests import test_visual_communication_site as site
from tests.test_visual_communication_boxes import COVERED, LOCAL
from tests.test_visual_communication_checks import project_of
from tests.test_visual_communication_look import (  # noqa: F401
    plugins,
    report_of,
    reports_hold_their_schema,
    run_look,
    viewing,
)
from tests.test_visual_communication_pipeline import (
    EVERY_WIDE,
    PHONE,
    PIECE,
    drawing_project,
    flipping,
    on_devices,
    two_steps,
    write_content,
)
from tests.visual_communication_project import project, write, yaml_text

#: The modules the look the tests run imports, so a test patches what it runs.
checks = viewing.checks
signs = checks.signs

#: The ids of the checks that state a reach.
REACHING = [check.id for check in checks.SCENE_CHECKS if check.reach is not None]


def looked(root: Path, *args: str, piece: str = PIECE) -> dict[str, Any]:
    done = run_look(root, piece, *args)
    assert done.returncode == 0, done.stderr
    return report_of(root, piece)


def labels(image: dict[str, Any]) -> list[str]:
    return [each["label"] for each in image["findings"]]


def test_the_report_names_the_release_and_carries_each_reach_as_the_code_states_it(
    tmp_path: Path,
) -> None:
    report = looked(drawing_project(tmp_path, picture=False))
    assert report["capability"]["name"] == "visual-communication"
    assert report["capability"]["version"] == ".".join(
        map(str, viewing.libraries.installed_release())
    )
    assert list(report["reaches"]) == REACHING
    near = report["reaches"]["edges-nearly-in-line"]
    assert near["statements"] == ["near-alignment-unmeasured"]
    assert near["measures"] == list(checks.boxes.NEAR_ALIGNMENT_CHECK.reach.measures)
    assert report["reaches"]["contrast-as-drawn"]["colour"] is True
    assert report["reaches"]["content-a-size-hides"]["compares"] == ["sizes"]
    [image] = report["images"]
    assert image["measured-by"] == REACHING
    assert image["not-measured"] == []


def test_a_look_after_an_edit_gives_the_findings_of_the_files_as_they_stand(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False)
    [before] = looked(root)["images"]
    assert "text-overflow" not in labels(before)
    write_content(root, body=two_steps(EVERY_WIDE))
    [after] = looked(root)["images"]
    [overflow] = [each for each in after["findings"] if each["label"] == "text-overflow"]
    assert (overflow["check"], overflow["language"], overflow["key"], overflow["page"]) == (
        None,
        "en",
        "default",
        "figure",
    )
    assert not (root / "visual/pieces" / PIECE / "findings.yaml").exists()


def test_a_look_of_one_key_gives_content_a_size_hides_there_and_lists_it_apart_elsewhere(
    tmp_path: Path,
) -> None:
    root = flipping(tmp_path)
    [phone] = looked(root, "--key", PHONE)["images"]
    [hidden] = [each for each in phone["findings"] if each["label"] == "size-hidden"]
    assert hidden == {
        "check": "content-a-size-hides",
        "label": "size-hidden",
        "level": "fact",
        "location": "visual/pieces/flow/content.en.yaml#body.note",
        "message": "`body.note` is drawn at `default`, and not at this size",
        "language": "en",
        "key": PHONE,
        "page": None,
    }
    report = looked(root)
    [default] = report["images"]
    assert "size-hidden" not in labels(default)
    assert [each for each in report["on-no-image"] if each["label"] == "size-hidden"] == [hidden]


def test_a_finding_read_alike_on_two_pages_is_given_to_each_page_s_image(tmp_path: Path) -> None:
    sites = site.site_location(project(tmp_path))
    portal = sites / "visual/pieces/portal/content.en.yaml"
    content = YAML(typ="safe").load(portal.read_text(encoding="utf-8"))
    content["header"]["head"] = "Pneumonoultramicroscopicsilicovolcanoconiosis"
    write(portal, yaml_text(content))
    report = looked(sites, "--key", PHONE, "--renderer", "svg", piece="portal")
    overflows = {
        image["page"]: [
            each["location"] for each in image["findings"] if each["label"] == "text-overflow"
        ]
        for image in report["images"]
    }
    assert overflows == {
        "site/pages[home]": ["visual/pieces/portal/content.en.yaml#site/pages[home]/header/head"],
        "site/pages[guide]": ["visual/pieces/portal/content.en.yaml#site/pages[guide]/header/head"],
        "site/pages[notice]": [],
    }


def test_a_finding_in_two_languages_drawn_is_given_to_each_language_s_image(
    tmp_path: Path,
) -> None:
    root = on_devices(tmp_path, head=EVERY_WIDE, languages=["en", "cs"])
    write_content(root, "cs", body=two_steps(EVERY_WIDE))
    report = looked(root, "--every-language")
    found = {
        image["language"]: [
            each["language"] for each in image["findings"] if each["label"] == "text-overflow"
        ]
        for image in report["images"]
    }
    assert found == {"en": ["en"], "cs": ["cs"]}
    assert {
        each["language"] for each in report["on-no-image"] if each["label"] == "text-overflow"
    } == {
        "en",
        "cs",
    }


#: A concept told by its colour alone, as the checks of signs find it in each scene.
ALONE = checks.Finding(
    "sign-missing",
    checks.ATTENTION,
    "figure/body names the concept `sys/store`, and its colour alone tells it apart",
    file="piece.yaml",
    where="parts",
    extra={"component": "piece/flow", "place": "figure/body"},
)


def test_a_concept_told_by_its_colour_alone_on_two_images_is_given_to_each(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = drawing_project(tmp_path, picture=False, languages=["en", "cs"])
    write_content(root, "cs", body=two_steps("Naplánovat."))
    monkeypatch.setattr(signs, "left_to_colour", lambda shown: [ALONE])
    report = looked(root, "--every-language")
    given = {
        image["language"]: [
            (each["check"], each["page"])
            for each in image["findings"]
            if each["label"] == "sign-missing"
        ]
        for image in report["images"]
    }
    assert given == {"en": [(None, "figure")], "cs": [(None, "figure")]}


def test_a_finding_that_names_no_place_is_given_to_each_image_of_its_languages_and_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = on_devices(tmp_path, languages=["en", "cs"])
    write_content(root, "cs", body=two_steps("Naplánovat."))
    stated = checks.Finding(
        "brand-forms", checks.FACT, "the brand draws it", file="piece.yaml", where="brand"
    )
    monkeypatch.setattr(checks, "_brand_forms", lambda project: [stated])
    report = looked(root, "--every-language", "--every-key")
    assert len(report["images"]) == 4
    for image in report["images"]:
        [each] = [each for each in image["findings"] if each["label"] == "brand-forms"]
        assert (each["language"], each["key"], each["page"]) == (None, None, None)
    assert [each for each in report["on-no-image"] if each["label"] == "brand-forms"] == []


def test_an_overlap_of_a_covered_text_is_given_with_its_check_s_id(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    write(root / LOCAL / "covered.yaml", COVERED)
    write_content(root, body={"use": "piece/covered", "head": "Plan the work."})
    [image] = looked(root)["images"]
    [overlap] = [each for each in image["findings"] if each["label"] == "box-overlap"]
    assert (overlap["check"], overlap["location"], overlap["page"]) == (
        "boxes-that-overlap",
        "visual/pieces/flow/piece.yaml#figure/body/head",
        "figure",
    )


def test_a_check_with_no_reach_is_named_for_no_image_though_its_findings_are_given(
    tmp_path: Path,
) -> None:
    [image] = looked(drawing_project(tmp_path, picture=False))["images"]
    statuses = [each for each in image["findings"] if each["label"] == "component-experimental"]
    assert statuses and {each["check"] for each in statuses} == {None}
    assert image["measured-by"] == REACHING


def test_two_checks_that_share_a_label_are_told_apart_by_their_ids(tmp_path: Path) -> None:
    drawn = project_of(drawing_project(tmp_path, picture=False))
    reach = checks.Reach(measures=("a",), leaves_out=("b",))
    one = checks.SceneCheck("one", id="one", labels=("shared",), reach=reach)
    other = checks.SceneCheck("other", id="other", labels=("shared",), reach=reach)
    finding = checks.Finding("shared", checks.FACT, "found", file="piece.yaml", where="figure")
    said = [
        viewing._said_found(drawn, checks.Found(finding, check, "en", "default"), "default")
        for check in (one, other)
    ]
    assert [each["check"] for each in said] == ["one", "other"]
    assert said[0]["label"] == said[1]["label"] == "shared"


def test_a_forced_image_gets_no_finding_of_colour_that_names_a_combination(
    tmp_path: Path,
) -> None:
    drawn = project_of(drawing_project(tmp_path, picture=False))
    faint = checks.Finding(
        "contrast-drawn", checks.FAILS, "faint", file="piece.yaml", where="figure/t"
    )
    named = checks.Found(faint, checks.CONTRAST, "en", "default", ("default",), "figure")
    unnamed = checks.Found(faint, checks.CONTRAST, "en", "default", (), "figure")
    image = {"language": "en", "key": "default", "page": "figure", viewing.FORCED: None}
    forced = {**image, viewing.FORCED: "dark"}
    assert viewing._holds_on(drawn, named, image) == "default"
    assert viewing._holds_on(drawn, named, forced) is None
    assert viewing._holds_on(drawn, unnamed, forced) == "default"
    made = viewing._Made(drawn, viewing.HTML, viewing.Measured((), {}, {}, "0.0.0"))
    assert "check of colour" in made._unmeasured(checks.CONTRAST, forced)
    assert made._unmeasured(checks.CONTRAST, image) == ""
    assert made._unmeasured(checks.CONTENT_HIDDEN, forced) == ""


def test_a_look_whose_checks_code_stops_still_draws_and_says_no_check_measured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def stops(*_: Any) -> list[Any]:
        raise RuntimeError("planted")

    monkeypatch.setattr(checks, "drawn_contrast", stops)
    [image] = looked(drawing_project(tmp_path, picture=False))["images"]
    assert image["measured-by"] == []
    assert [each["check"] for each in image["not-measured"]] == REACHING
    for each in image["not-measured"]:
        assert (
            each["why"] == "the checks' code stopped on this image's scene: RuntimeError: planted"
        )


def test_a_scene_computed_only_for_its_findings_that_stops_leaves_the_images_drawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    measure = checks.drawn_contrast

    def stops_at_the_phone(scene: Any, colours: Any, keys: Any) -> list[Any]:
        if any(PHONE in key for key in keys):
            raise RuntimeError("planted")
        return measure(scene, colours, keys)

    monkeypatch.setattr(checks, "drawn_contrast", stops_at_the_phone)
    [image] = looked(on_devices(tmp_path))["images"]
    assert image["key"] == "default"
    assert image["measured-by"] == [id_ for id_ in REACHING if id_ != "content-a-size-hides"]
    [why] = image["not-measured"]
    assert why == {
        "check": "content-a-size-hides",
        "why": f"it compares this image's scene with that of `en` at `{PHONE}`, and the checks' "
        "code stopped on it: RuntimeError: planted",
    }
