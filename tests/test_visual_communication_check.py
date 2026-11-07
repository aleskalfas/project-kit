"""`pkit visual check` (visual-communication DEC-002 points 6 and 7, DEC-005 point 13): the
validator of `pkit validate`, under the query contract — `--json` prints the findings
document and exits 0; without it, it exits 1 when a finding fails. Its findings are
`test_visual_communication_checks.py`'s; here, the command: the findings record read while
its key verifies, the validation's bound, the time it takes, one run through `pkit
validate`'s runner as a process of its own, what a state owes of a current copy, read after
each state's real export, and what a final piece owes of the version handed out, read after a
real mark (DEC-006 point 8, DEC-017 points 3 to 7)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from tests import visual_communication_producer as producer
from tests.adopter_repo import MakeAdopterRepo
from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import (
    LOCK,
    PHONE,
    PHONE_WIDE,
    PIECE,
    PIECE_FOLDER,
    drawing_project,
    lay_out_drawing,
    list_drawing_libraries,
    on_devices,
    write_content,
    write_picture,
)
from tests.test_visual_communication_render import newer_tests
from tests.visual_communication_project import importable, yaml_text

check, render, export, mark_final, svg, seam, framing, fingerprint, reading = load(
    "visual-communication",
    "check.py",
    "render.py",
    "export.py",
    "mark-final.py",
    "plugins.svg",
    "plugins.seam",
    "framing",
    "fingerprint",
    "reading",
)

# The picture the piece declares and nobody made: the producer's check reports it once,
# at the record that is missing.
MISSING = f"{PIECE_FOLDER}/produced/square/record.yaml#produced.square"

# A word with no place to break, wider than the figure: its text overflows its box.
LONG_WORD = "Unbreakable" * 40

BRAND_FONT = "visual/libraries/test-brand/1.0.0/fonts/SourceSansPro-Regular.otf"


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderer stands in for the import a render makes when it draws, and the test
    producer is registered, for the length of the test."""
    importable(monkeypatch, svg)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def run(root: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return run_main(check, *args, cwd=root, env={"PKIT_COMMAND_DEADLINE": None, **env})


def document(root: Path, *args: str, **env: str) -> dict[str, Any]:
    shown = run(root, "--json", *args, **env)
    assert shown.returncode == 0, shown.stderr
    return json.loads(shown.stdout)


def drawn(tmp_path: Path) -> Path:
    """The skeleton piece with its picture, rendered: its findings record committed."""
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    assert run_main(render, PIECE, cwd=root).returncode == 0
    return root


# --- the query contract -------------------------------------------------------------------------


def test_json_prints_the_document_and_exits_0_though_a_finding_fails(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    found = document(root)
    assert found["summary"] == [
        "1 piece(s) in `visual`: the scenes of 0 read from their findings record, of 1 "
        "computed now, of 0 not checked."
    ]
    errors = [f for f in found["findings"] if f["severity"] == "error"]
    [missing] = [f for f in errors if f["label"] == "produced-record-missing"]
    assert missing["location"] == MISSING
    assert "pkit visual produce flow square" in missing["message"]


def test_without_json_it_lists_the_findings_and_exits_1_when_one_fails(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    shown = run(root)
    assert shown.returncode == 1
    lines = shown.stdout.splitlines()
    assert lines[0].startswith("1 piece(s) in `visual`")
    assert f"  error   {MISSING}  [produced-record-missing]" in lines


def test_a_font_file_that_cannot_be_read_fails_as_a_missing_font_does(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    (root / BRAND_FONT).write_bytes(b"not a font")
    [found] = [f for f in document(root)["findings"] if f["label"] == "font-missing"]
    assert found["severity"] == "error"
    assert "cannot be read" in found["message"]


def test_a_piece_whose_findings_do_not_fail_exits_0(tmp_path: Path) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stdout
    assert shown.stdout.splitlines()[0] == (
        "the piece `flow` in `visual`: the scenes of 0 read from their findings record, of 1 "
        "computed now, of 0 not checked."
    )
    assert "  info    " in shown.stdout


# --- the findings record ------------------------------------------------------------------------


def test_the_record_is_read_while_its_key_verifies_and_the_scenes_computed_after(
    tmp_path: Path,
) -> None:
    root = drawn(tmp_path)
    assert "the scenes of 1 read from their findings record" in document(root)["summary"][0]
    write_content(root, head="Plan the work again.")
    assert "of 1 computed now" in document(root)["summary"][0]


def test_a_record_that_no_longer_verifies_is_not_believed(tmp_path: Path) -> None:
    root = drawn(tmp_path)
    (root / PIECE_FOLDER / "produced" / "square" / "record.yaml").unlink()
    found = document(root)
    assert "of 1 computed now" in found["summary"][0]
    assert ("produced-record-missing", MISSING) in [
        (f["label"], f["location"]) for f in found["findings"]
    ]


def test_a_finding_at_one_size_reads_the_same_from_the_record_as_computed(tmp_path: Path) -> None:
    root = on_devices(tmp_path, head=PHONE_WIDE)
    computed = [f for f in document(root)["findings"] if f["label"] == "text-overflow"]
    assert run_main(render, PIECE, cwd=root).returncode == 0
    found = document(root)
    assert "the scenes of 1 read from their findings record" in found["summary"][0]
    [overflow] = [f for f in found["findings"] if f["label"] == "text-overflow"]
    assert [overflow] == computed
    assert overflow["severity"] == "error"
    assert overflow["message"].startswith(f"`{PHONE}`: figure/body/steps[plan]/head: ")


def test_past_the_validations_bound_a_piece_without_a_record_fails_as_not_checked(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    found = document(root, PKIT_COMMAND_DEADLINE=str(time.time()))
    assert [(f["severity"], f["location"], f["label"]) for f in found["findings"]] == [
        ("error", f"{PIECE_FOLDER}/findings.yaml", "not-checked")
    ]
    # A record that verifies is read whatever the bound.
    assert run_main(render, PIECE, cwd=root).returncode == 0
    found = document(root, PKIT_COMMAND_DEADLINE=str(time.time()))
    assert "not-checked" not in [f["label"] for f in found["findings"]]


def test_a_final_piece_with_only_a_fact_at_its_lock_exits_0(tmp_path: Path) -> None:
    root = marked(tmp_path)
    path = root / "visual/libraries/tests/1.0.0/library.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("version: 1.0.0", "version: 1.0.1"),
        encoding="utf-8",
    )
    list_drawing_libraries(root, released=True)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stdout
    lines = shown.stdout.splitlines()
    assert lines[0] == (
        "the piece `flow` in `visual`: the scenes of 0 read from their findings record, of 0 "
        "computed now, of 0 not checked, of 1 left out as final."
    )
    assert any("[lock-unreadable]" in line and line.startswith("  info") for line in lines)


def test_it_checks_the_skeleton_piece_within_a_few_seconds(tmp_path: Path) -> None:
    """The validation runs it on every `pkit validate`: computing the skeleton piece's
    scenes, and reading them from its record, each take well under its bound."""
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    for case, said in (("computed", "of 1 computed now"), ("read", "of 1 read from")):
        started = time.monotonic()
        found = document(root)
        took = time.monotonic() - started
        assert said in found["summary"][0]
        assert took < 3.0, f"{case}: {took:.2f} s"
        assert run_main(render, PIECE, cwd=root).returncode == 0


# --- through pkit validate ----------------------------------------------------------------------


@pytest.mark.process(
    "the validator's end-to-end test: `pkit validate` finds the `visual-communication:check` "
    "member, starts its script as a process of its own and reads its document and its exit"
)
def test_it_is_the_check_member_of_pkit_validate(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo = make_adopter_repo(capabilities=("visual-communication",))
    script = repo.root / ".pkit/capabilities/visual-communication/scripts/check.py"
    body = script.read_text(encoding="utf-8").split("\n", 1)[1]
    script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    # No produced picture: the test producer is registered in this process alone, so the
    # check's own process would not know it (DEC-005 point 12).
    root = lay_out_drawing(repo.root, picture=False)
    only = ["--color", "never", "validate", "--only", "visual-communication:check"]
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 0, result.output
    assert "visual-communication:check" in result.output
    write_content(root, body={"use": "tests/steps", "steps": [{"id": "plan", "head": LONG_WORD}]})
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 1, result.output
    assert "text-overflow" in result.output


# --- what a state owes of a current copy --------------------------------------------------------

PIECE_FILE = f"{PIECE_FOLDER}/piece.yaml"
RECORD = f"{PIECE_FOLDER}/exports.yaml"
LIGHT = f"{PIECE_FOLDER}/current-copy/flow.en.default.svg"
DARK = f"{PIECE_FOLDER}/current-copy/flow.en.colour-scheme.dark.svg"
AT_THE_RECORD = f"{RECORD}#current-copy"

#: The place the piece names for its copy in some tests, and the copy's files there.
PLACE = "docs/figures"
PLACED_LIGHT = f"{PLACE}/flow.en.default.svg"
PLACED_DARK = f"{PLACE}/flow.en.colour-scheme.dark.svg"

#: What each finding on a current copy says of the export that mends it.
EXPORT_AGAIN = "run `pkit visual export flow`, which makes the copy again"

#: What a fix adds where the piece's lock differs from the one its copy was made under.
WAYS_PAST_THE_GATE = (
    "write back the lock of version 1, foundations@1.0.0, test-brand@1.0.0, tests@1.0.0, which "
    f"is no move of it, and {EXPORT_AGAIN}; or run `pkit visual upgrade flow` to propose a move "
    "of the lock"
)


def exported(root: Path, *args: str) -> Path:
    shown = run_main(export, PIECE, *args, cwd=root)
    assert shown.returncode == 0, shown.stderr
    return root


def marked(tmp_path: Path) -> Path:
    """The skeleton piece, showing no produced picture, exported under libraries listed
    released, and its first version marked final."""
    root = exported(drawing_project(tmp_path, picture=False, released=True))
    return mark(root)


def mark(root: Path) -> Path:
    shown = run_main(mark_final, PIECE, "1", cwd=root)
    assert shown.returncode == 0, shown.stderr
    return root


def published(tmp_path: Path, **fields: Any) -> Path:
    """The skeleton piece, published and exported, showing no produced picture."""
    return exported(drawing_project(tmp_path, state="published", picture=False, **fields))


def published_with_picture(tmp_path: Path) -> Path:
    root = drawing_project(tmp_path, state="published")
    write_picture(root, framing)
    return exported(root)


def made_over_a_stale_output(tmp_path: Path) -> Path:
    """The piece published, its copy made with its picture named while stale."""
    root = drawing_project(tmp_path, state="published")
    write_picture(root, framing)
    path = root / PIECE_FILE
    path.write_text(
        path.read_text(encoding="utf-8").replace("width: 100", "width: 120"), encoding="utf-8"
    )
    return exported(root, "--use-stale", "square")


def owed(root: Path, *args: str) -> list[dict[str, str]]:
    """Each finding on what a state owes of a current copy, in the order of the run."""
    return [
        finding
        for finding in document(root, *args)["findings"]
        if finding["label"].startswith(("current-copy-", "published-"))
    ]


def said(found: list[dict[str, str]]) -> list[tuple[str, str, str]]:
    """Each finding's label, severity and location."""
    return [(each["label"], each["severity"], each["location"]) for each in found]


def set_fields(root: Path, folder: str = PIECE_FOLDER, **fields: Any) -> None:
    """Set fields of the piece's own file, by their names with `_` for `-`."""
    path = root / folder / "piece.yaml"
    data = reading.read_yaml(path)
    data.update({name.replace("_", "-"): value for name, value in fields.items()})
    path.write_text(yaml_text(data), encoding="utf-8")


def move_lock(root: Path, version: str) -> None:
    """Write `version` for the `tests` library into the piece's lock by hand."""
    set_fields(root, lock={**LOCK, "tests": version})


def edit_content(root: Path) -> None:
    path = root / PIECE_FOLDER / "content.en.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("Plan the work.", "Plan it."), encoding="utf-8"
    )


def edit_record(root: Path, folder: str = PIECE_FOLDER, **current: Any) -> None:
    """Set fields of the record's `current-copy` by hand."""
    path = root / folder / "exports.yaml"
    record = reading.read_yaml(path)
    record["current-copy"].update(current)
    path.write_text(yaml_text(record), encoding="utf-8")


def hand_copy(root: Path, name: str = "flow-two") -> str:
    """A folder copied by hand from the piece: the copy's record names the piece."""
    folder = f"visual/pieces/{name}"
    shutil.copytree(
        root / PIECE_FOLDER, root / folder, ignore=shutil.ignore_patterns("__pycache__")
    )
    return folder


def test_a_published_piece_with_a_whole_copy_that_nothing_changed_owes_nothing(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    assert owed(root) == []
    assert owed(root, PIECE) == []
    assert run(root).returncode == 0


def test_a_copy_stale_by_its_content_fails_naming_the_change_and_the_export(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    edit_content(root)
    [finding] = owed(root)
    assert finding == {
        "severity": "error",
        "location": AT_THE_RECORD,
        "message": (
            "the current copy of `flow`, which version 1 wrote, is stale: `content.en.yaml` "
            f"changed — {EXPORT_AGAIN}"
        ),
        "label": "current-copy-stale",
    }
    assert run(root).returncode == 1
    assert owed(exported(root)) == []


def test_a_copy_stale_by_its_lock_names_the_lock_and_both_ways_past_the_export_s_refusal(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    newer_tests(root, released=True)
    move_lock(root, "1.1.0")
    [finding] = owed(root)
    assert finding["label"] == "current-copy-stale"
    assert "`piece.yaml` changed" in finding["message"]
    assert "`library.yaml` of tests@1.0.0 is no longer read" in finding["message"]
    assert "`library.yaml` of tests@1.1.0 is read now" in finding["message"]
    assert finding["message"].endswith(f" — {WAYS_PAST_THE_GATE}")
    assert run_main(export, PIECE, cwd=root).returncode == 1
    move_lock(root, "1.0.0")
    assert owed(root) == []


def test_a_copy_stale_by_a_produced_output_fails_naming_its_record(tmp_path: Path) -> None:
    root = published_with_picture(tmp_path)
    assert owed(root) == []
    write_picture(root, framing, (0, 0, 255, 255))
    [finding] = owed(root)
    assert finding["label"] == "current-copy-stale"
    assert "stale: `produced/square/record.yaml` changed" in finding["message"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("accept-losses", [{"plugin": "svg", "element": "text", "property": "kerning"}]),
        ("audience", "Everyone else"),
        ("copy-place", "docs/figures"),
        ("explains", False),
        ("pinned", True),
        ("shown", "Somewhere else"),
    ],
)
def test_a_change_to_a_listed_field_leaves_the_copy_fresh(
    tmp_path: Path, field: str, value: Any
) -> None:
    assert field in fingerprint.PIECE_FIELDS_LEFT_OUT
    root = published(tmp_path)
    set_fields(root, **{field: value})
    assert owed(root) == []


def test_a_field_no_list_names_counts_and_the_copy_goes_stale(tmp_path: Path) -> None:
    root = published(tmp_path)
    set_fields(root, modes={"colour-scheme": ["dark"]})
    assert [finding["label"] for finding in owed(root)] == ["current-copy-stale"]


def test_a_published_piece_with_no_copy_fails_and_the_export_mends_it(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="published", picture=False)
    [finding] = owed(root)
    assert finding == {
        "severity": "error",
        "location": AT_THE_RECORD,
        "message": (f"the published piece `flow` has no current copy of its own — {EXPORT_AGAIN}"),
        "label": "current-copy-none",
    }
    assert owed(exported(root)) == []


def test_a_copy_of_another_piece_is_none_of_its_own(tmp_path: Path) -> None:
    root = published(tmp_path)
    hand_copy(root)
    assert said(owed(root, "flow-two")) == [
        ("current-copy-none", "error", "visual/pieces/flow-two/exports.yaml#current-copy")
    ]
    assert owed(root, PIECE) == []


def test_a_renamed_piece_keeps_its_copy_and_is_held_to_it(tmp_path: Path) -> None:
    root = published(tmp_path)
    renamed = "visual/pieces/flow-renamed"
    (root / PIECE_FOLDER).rename(root / renamed)
    assert owed(root) == []
    (root / renamed / "current-copy/flow.en.default.svg").unlink()
    assert said(owed(root)) == [
        (
            "current-copy-file-missing",
            "error",
            f"{renamed}/current-copy/flow.en.default.svg",
        )
    ]


def test_a_file_of_the_copy_missing_fails_naming_it_and_the_export_mends_it(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    (root / LIGHT).unlink()
    [finding] = owed(root)
    assert finding == {
        "severity": "error",
        "location": LIGHT,
        "message": f"a file of the current copy of `flow` is missing — {EXPORT_AGAIN}",
        "label": "current-copy-file-missing",
    }
    assert owed(exported(root)) == []


def test_a_file_of_the_copy_changed_fails_naming_it_and_the_export_mends_it(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    (root / DARK).write_bytes((root / DARK).read_bytes() + b" ")
    [finding] = owed(root)
    assert finding == {
        "severity": "error",
        "location": DARK,
        "message": (
            f"a file of the current copy of `flow` is not the one its export wrote — {EXPORT_AGAIN}"
        ),
        "label": "current-copy-file-changed",
    }
    assert owed(exported(root)) == []


def at_a_place(tmp_path: Path) -> Path:
    """The piece, published and exported, its copy at the place it names."""
    return published(tmp_path, **{"copy-place": PLACE})


def test_a_copy_at_a_place_that_is_whole_owes_nothing(tmp_path: Path) -> None:
    root = at_a_place(tmp_path)
    assert (root / PLACED_LIGHT).is_file()
    assert not (root / LIGHT).exists()
    assert owed(root) == []
    assert owed(root, PIECE) == []
    assert run(root).returncode == 0


def test_a_file_at_a_place_missing_fails_naming_it_and_the_export_mends_it(tmp_path: Path) -> None:
    root = at_a_place(tmp_path)
    (root / PLACED_LIGHT).unlink()
    [finding] = owed(root)
    assert finding == {
        "severity": "error",
        "location": PLACED_LIGHT,
        "message": f"a file of the current copy of `flow` is missing — {EXPORT_AGAIN}",
        "label": "current-copy-file-missing",
    }
    assert run(root).returncode == 1
    assert owed(exported(root)) == []


def test_a_file_at_a_place_changed_fails_and_the_export_mends_it_once_a_person_removes_it(
    tmp_path: Path,
) -> None:
    root = at_a_place(tmp_path)
    (root / PLACED_DARK).write_bytes(b"another figure")
    [finding] = owed(root)
    assert finding == {
        "severity": "error",
        "location": PLACED_DARK,
        "message": (
            "a file of the current copy of `flow` is not the one its export wrote — remove it, "
            f"then {EXPORT_AGAIN}"
        ),
        "label": "current-copy-file-changed",
    }
    refused = run_main(export, PIECE, cwd=root)
    assert refused.returncode == 1
    assert f"the export would write over {PLACED_DARK}" in refused.stderr
    (root / PLACED_DARK).unlink()
    assert owed(exported(root)) == []


def test_each_file_is_read_at_the_path_the_record_names_not_the_place_the_piece_names(
    tmp_path: Path,
) -> None:
    root = at_a_place(tmp_path)
    set_fields(root, copy_place="docs/other")
    assert owed(root) == []
    (root / PLACED_LIGHT).unlink()
    assert said(owed(root)) == [("current-copy-file-missing", "error", PLACED_LIGHT)]


def test_a_drafts_file_at_a_place_stands_as_one_in_its_folder(tmp_path: Path) -> None:
    root = at_a_place(tmp_path)
    set_fields(root, state="draft")
    (root / PLACED_LIGHT).unlink()
    assert said(owed(root)) == [("current-copy-standing", "warning", PLACED_DARK)]


def test_a_published_piece_with_no_format_fails_and_the_fix_names_declaring_one(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, state="published", picture=False, exports=[])
    found = owed(root)
    assert found[0] == {
        "severity": "error",
        "location": f"{PIECE_FILE}#exports",
        "message": (
            "the published piece `flow` declares no format under `exports` — declare one there: "
            "`svg` or `pdf`"
        ),
        "label": "published-no-format",
    }
    assert [finding["label"] for finding in found[1:]] == ["current-copy-none"]


def test_a_format_taken_off_a_published_piece_stands_beside_the_stale_copy(tmp_path: Path) -> None:
    root = published(tmp_path)
    set_fields(root, exports=[])
    assert [finding["label"] for finding in owed(root)] == [
        "published-no-format",
        "current-copy-stale",
    ]


@pytest.mark.parametrize("args", [(), (PIECE,)], ids=["every-piece", "the-piece"])
def test_a_stale_copy_stands_beside_a_lock_that_differs_from_its_own(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    root = published(tmp_path)
    move_lock(root, "1.2.0")
    labels = [finding["label"] for finding in document(root, *args)["findings"]]
    assert "lock-not-held" in labels
    assert "current-copy-stale" in labels


def test_a_stale_copy_stands_beside_a_lock_finding_that_leaves_the_lock_as_it_was(
    tmp_path: Path,
) -> None:
    """The lock holds what the copy was made under, so only the pass over the copy, run
    before the lock's finding stops the piece, can tell that the content changed."""
    root = published(tmp_path)
    list_drawing_libraries(root, released=False)
    edit_content(root)
    answer = document(root)
    labels = [finding["label"] for finding in answer["findings"]]
    assert "lock-not-released" in labels
    assert "of 1 not checked" in answer["summary"][0]
    [stale] = [each for each in answer["findings"] if each["label"] == "current-copy-stale"]
    assert "`content.en.yaml` changed" in stale["message"]


def test_every_rule_of_a_published_piece_stands_beside_a_lock_finding(tmp_path: Path) -> None:
    root = made_over_a_stale_output(tmp_path)
    (root / LIGHT).unlink()
    list_drawing_libraries(root, released=False)
    set_fields(root, exports=[])
    labels = [finding["label"] for finding in document(root)["findings"]]
    assert "lock-not-released" in labels
    assert [label for label in labels if label.startswith(("current-copy-", "published-"))] == [
        "published-no-format",
        "current-copy-stale",
        "current-copy-file-missing",
        "current-copy-over-stale",
    ]


def test_a_copy_made_over_a_stale_output_asks_for_attention_and_fails_nothing(
    tmp_path: Path,
) -> None:
    root = made_over_a_stale_output(tmp_path)
    [finding] = owed(root)
    assert finding == {
        "severity": "warning",
        "location": AT_THE_RECORD,
        "message": (
            "the current copy of `flow`, which version 1 wrote, was made over the stale produced "
            "picture `square` — for the piece's author — run `pkit visual produce flow square`, "
            f"then {EXPORT_AGAIN}"
        ),
        "label": "current-copy-over-stale",
    }
    assert run(root).returncode == 0


def test_a_draft_with_a_file_of_its_copy_standing_asks_for_attention_whatever_it_holds(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    set_fields(root, state="draft")
    found = owed(root)
    assert said(found) == [
        ("current-copy-standing", "warning", DARK),
        ("current-copy-standing", "warning", LIGHT),
    ]
    assert found[1]["message"] == (
        "the draft `flow` keeps a file of its current copy, which no check holds to its sources "
        f"— for the piece's author — remove it, or publish the piece again in {PIECE_FILE}"
    )
    assert run(root).returncode == 0

    (root / LIGHT).write_bytes(b"a byte changed")
    assert owed(root) == found

    (root / LIGHT).unlink()
    assert said(owed(root)) == [("current-copy-standing", "warning", DARK)]
    (root / DARK).unlink()
    assert owed(root) == []


def test_a_draft_is_held_to_nothing_else_of_its_copy(tmp_path: Path) -> None:
    root = published(tmp_path)
    set_fields(root, state="draft", exports=[])
    edit_content(root)
    assert {finding["label"] for finding in owed(root)} == {"current-copy-standing"}


def test_a_draft_copied_by_hand_keeps_no_copy_of_another_piece(tmp_path: Path) -> None:
    root = published(tmp_path)
    folder = hand_copy(root)
    set_fields(root, folder, state="draft")
    assert owed(root, "flow-two") == []


def test_a_renamed_draft_keeps_its_copy_and_is_told_of_it(tmp_path: Path) -> None:
    root = published(tmp_path)
    set_fields(root, state="draft")
    renamed = "visual/pieces/flow-renamed"
    (root / PIECE_FOLDER).rename(root / renamed)
    assert {finding["label"] for finding in owed(root, "flow-renamed")} == {"current-copy-standing"}


def test_a_piece_set_back_to_published_is_held_to_the_version_that_wrote_its_copy(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    set_fields(root, state="draft")
    edit_content(root)
    exported(root)
    set_fields(root, state="published")
    [finding] = owed(root)
    assert finding["label"] == "current-copy-stale"
    assert finding["message"].startswith(
        "the current copy of `flow`, which version 1 wrote, is stale: `content.en.yaml` changed"
    )
    record = reading.read_yaml(root / RECORD)
    assert [entry["version"] for entry in record["versions"]] == [1, 2]
    assert record["current-copy"]["version"] == 1

    assert owed(exported(root)) == []
    assert reading.read_yaml(root / RECORD)["current-copy"]["version"] == 3


def test_a_piece_set_back_to_published_with_nothing_changed_stays_fresh(tmp_path: Path) -> None:
    root = published(tmp_path)
    set_fields(root, state="draft")
    set_fields(root, state="published")
    assert owed(root) == []


def test_a_final_piece_raises_none_of_these(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit_content(root)
    (root / LIGHT).unlink()
    (root / DARK).write_bytes(b"changed")
    set_fields(root, state="final", exports=[])
    assert owed(root) == []


def test_a_final_piece_made_over_a_stale_output_raises_nothing_of_it(tmp_path: Path) -> None:
    root = made_over_a_stale_output(tmp_path)
    set_fields(root, state="final")
    assert owed(root) == []


@pytest.mark.parametrize("state", ["published", "draft"])
def test_a_current_copy_of_no_shape_fails_as_the_record_cannot_be_read(
    tmp_path: Path, state: str
) -> None:
    root = published(tmp_path)
    set_fields(root, state=state)
    edit_record(root, version="one")
    [finding] = owed(root)
    assert (finding["label"], finding["location"]) == ("current-copy-unreadable", RECORD)
    assert "keeps a `current-copy` that names no piece, version and files" in finding["message"]


def test_a_record_that_cannot_be_read_takes_no_finding_on_the_copy(tmp_path: Path) -> None:
    root = published(tmp_path)
    (root / RECORD).write_text("versions: [\n", encoding="utf-8")
    labels = [finding["label"] for finding in document(root)["findings"]]
    assert "file-unreadable" in labels
    assert not any(label.startswith("current-copy-") for label in labels)


def test_a_version_the_record_no_longer_keeps_gives_no_lock_and_fails(tmp_path: Path) -> None:
    root = published(tmp_path)
    edit_record(root, version=7)
    [finding] = owed(root)
    assert (finding["label"], finding["location"]) == ("current-copy-unreadable", AT_THE_RECORD)
    assert finding["message"] == (
        f"{RECORD} gives no lock of version 7, which wrote the current copy: no fingerprint is "
        f"kept — mend {RECORD}, then {EXPORT_AGAIN}"
    )


# --- what a final piece owes of the version handed out ------------------------------------------

HANDED_OUT_LIGHT = f"{PIECE_FOLDER}/handed-out/flow.v1.en.default.svg"
HANDED_OUT_DARK = f"{PIECE_FOLDER}/handed-out/flow.v1.en.colour-scheme.dark.svg"
AT_THE_FIELD = f"{RECORD}#handed-out"
RESTORE_THE_FILE = "restore it from the repository's history, as it was handed out"
RESTORE_THE_RECORD = f"restore what {RECORD} kept of version 1 from the repository's history"
WRITE_BACK = (
    "write back the lock of version 1, foundations@1.0.0, test-brand@1.0.0, tests@1.0.0, which "
    "is no move of it"
)
CONFLICT = "pkit_schema: visual-communication:exports\n<<<<<<< HEAD\nversions: []\n"
LEFT_OUT = "of 1 left out as final."

#: A run over the location, and a run on the piece alone.
EACH_RUN = pytest.mark.parametrize("args", [(), (PIECE,)], ids=["location", "alone"])


def held_to(root: Path, *args: str) -> list[dict[str, str]]:
    """Each finding on what a final piece owes of the version handed out, in the run's order."""
    return [
        finding
        for finding in document(root, *args)["findings"]
        if finding["label"].startswith(("handed-out-", "exports-"))
    ]


def edit_exports(root: Path, **fields: Any) -> None:
    """Set top-level fields of the record of exports by hand, `handed_out` for its field."""
    path = root / RECORD
    record = reading.read_yaml(path)
    record.update({name.replace("_", "-"): value for name, value in fields.items()})
    path.write_text(yaml_text(record), encoding="utf-8")


def edit_version(root: Path, **fields: Any) -> None:
    """Set fields of the record's first version by hand."""
    versions = reading.read_yaml(root / RECORD)["versions"]
    versions[0].update(fields)
    edit_exports(root, versions=versions)


def write_lock_back(root: Path) -> None:
    set_fields(root, lock=LOCK)


def take_the_lock_out(root: Path) -> None:
    path = root / PIECE_FILE
    data = reading.read_yaml(path)
    del data["lock"]
    path.write_text(yaml_text(data), encoding="utf-8")


@EACH_RUN
def test_a_piece_marked_final_owes_nothing_and_is_left_out_as_final(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    root = marked(tmp_path)
    assert held_to(root, *args) == []
    assert document(root, *args)["summary"][0].endswith(LEFT_OUT)
    assert run(root, *args).returncode == 0


@EACH_RUN
def test_a_file_handed_out_that_is_missing_fails_naming_it_and_the_version(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    root = marked(tmp_path)
    (root / HANDED_OUT_LIGHT).unlink()
    assert held_to(root, *args) == [
        {
            "severity": "error",
            "location": HANDED_OUT_LIGHT,
            "message": (
                f"a file of version 1 of `flow`, handed out, is missing — {RESTORE_THE_FILE}"
            ),
            "label": "handed-out-file-missing",
        }
    ]
    assert run(root, *args).returncode == 1


@EACH_RUN
def test_a_file_handed_out_that_changed_fails_naming_it_and_the_version(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    root = marked(tmp_path)
    (root / HANDED_OUT_DARK).write_bytes(b"changed")
    assert held_to(root, *args) == [
        {
            "severity": "error",
            "location": HANDED_OUT_DARK,
            "message": (
                f"a file of version 1 of `flow`, handed out, has changed — {RESTORE_THE_FILE}"
            ),
            "label": "handed-out-file-changed",
        }
    ]
    assert run(root, *args).returncode == 1


@EACH_RUN
def test_state_final_with_no_version_handed_out_fails_and_the_command_mends_it(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    root = exported(drawing_project(tmp_path, picture=False, released=True))
    set_fields(root, state="final")
    assert held_to(root, *args) == [
        {
            "severity": "error",
            "location": f"{PIECE_FILE}#state",
            "message": (
                f"the piece `flow` is final, and {RECORD} names no version handed out — run "
                "`pkit visual mark-final flow <version>`, which takes such a piece, or set its "
                "state back"
            ),
            "label": "handed-out-none",
        }
    ]
    assert held_to(mark(root), *args) == []


def test_state_final_with_no_record_of_exports_fails_as_with_no_version(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, state="final", picture=False)
    assert said(held_to(root)) == [("handed-out-none", "error", f"{PIECE_FILE}#state")]


@EACH_RUN
@pytest.mark.parametrize("state", ["draft", "published"])
def test_a_version_handed_out_with_another_state_fails_and_setting_it_back_mends_it(
    tmp_path: Path, state: str, args: tuple[str, ...]
) -> None:
    root = marked(tmp_path)
    set_fields(root, state=state)
    assert held_to(root, *args) == [
        {
            "severity": "error",
            "location": f"{PIECE_FILE}#state",
            "message": (
                f"{RECORD} hands out version 1, and the state of `flow` is {state} — set its "
                "state back to final, and copy the piece for new work"
            ),
            "label": "handed-out-state",
        }
    ]
    assert document(root, *args)["summary"][0].endswith(LEFT_OUT)
    set_fields(root, state="final")
    assert held_to(root, *args) == []


def test_a_piece_final_by_the_field_alone_is_read_by_its_files_and_lock(tmp_path: Path) -> None:
    root = marked(tmp_path)
    set_fields(root, state="draft")
    write_content(root, body={"use": "later/steps", "steps": []})
    labels = [finding["label"] for finding in document(root, PIECE)["findings"]]
    assert labels == ["handed-out-state"]


@EACH_RUN
def test_a_version_handed_out_with_another_lock_fails_naming_the_lock_to_write_back(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    root = marked(tmp_path)
    newer_tests(root, released=True)
    move_lock(root, "1.1.0")
    assert held_to(root, *args) == [
        {
            "severity": "error",
            "location": f"{PIECE_FILE}#lock",
            "message": (
                f"the lock of `flow` is not the one version 1, handed out, was made under — "
                f"{WRITE_BACK}"
            ),
            "label": "handed-out-lock",
        }
    ]
    write_lock_back(root)
    assert held_to(root, *args) == []


@EACH_RUN
def test_a_fingerprint_it_cannot_read_is_a_finding_naming_the_record(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    root = marked(tmp_path)
    kept = reading.read_yaml(root / RECORD)["versions"][0]["fingerprint"]
    edit_version(root, fingerprint={**kept, "value": "0" * 64})
    assert held_to(root, *args) == [
        {
            "severity": "error",
            "location": AT_THE_FIELD,
            "message": (
                f"{RECORD} gives no lock of version 1, handed out: the fingerprint's value does "
                f"not match its own inputs: it was edited — {RESTORE_THE_RECORD}"
            ),
            "label": "handed-out-unreadable",
        }
    ]
    assert run(root, *args).returncode == 1


def test_a_fingerprint_it_cannot_read_leaves_the_version_s_files_read(tmp_path: Path) -> None:
    root = marked(tmp_path)
    edit_version(root, fingerprint={})
    (root / HANDED_OUT_LIGHT).unlink()
    assert [each["label"] for each in held_to(root)] == [
        "handed-out-unreadable",
        "handed-out-file-missing",
    ]


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        pytest.param(
            {"handed_out": 7},
            f"{RECORD} hands out version 7, and keeps no such one",
            id="no-such-version",
        ),
        pytest.param(
            {"versions": "none"},
            f"{RECORD} keeps no list of numbered versions",
            id="no-list",
        ),
    ],
)
def test_a_version_the_record_does_not_keep_fails_at_the_record(
    tmp_path: Path, fields: dict[str, Any], message: str
) -> None:
    root = marked(tmp_path)
    edit_exports(root, **fields)
    [finding] = held_to(root)
    assert (finding["label"], finding["location"]) == ("handed-out-unreadable", AT_THE_FIELD)
    assert finding["message"].startswith(f"{message} — ")


def test_a_version_that_names_no_file_fails_at_the_record(tmp_path: Path) -> None:
    root = marked(tmp_path)
    edit_version(root, files={})
    [finding] = held_to(root)
    assert (finding["label"], finding["location"]) == ("handed-out-unreadable", AT_THE_FIELD)
    assert finding["message"] == (
        f"{RECORD} names no file of version 1, handed out — {RESTORE_THE_RECORD}"
    )


@EACH_RUN
@pytest.mark.parametrize(
    ("spoil", "label"),
    [
        pytest.param(
            lambda root: shutil.rmtree(root / "visual/libraries/tests/1.0.0"),
            "lock-not-held",
            id="not-held",
        ),
        pytest.param(take_the_lock_out, "lock-missing", id="no-lock"),
        pytest.param(
            lambda root: set_fields(root, lock={**LOCK, "tests": "one"}),
            "lock-version",
            id="no-version",
        ),
    ],
)
def test_a_lock_finding_stops_no_check_of_the_files_handed_out(
    tmp_path: Path, spoil: Any, label: str, args: tuple[str, ...]
) -> None:
    root = marked(tmp_path)
    spoil(root)
    (root / HANDED_OUT_LIGHT).unlink()
    labels = [finding["label"] for finding in document(root, *args)["findings"]]
    assert label in labels
    assert "handed-out-file-missing" in labels


def test_no_lock_on_a_marked_piece_names_the_lock_to_write_back(tmp_path: Path) -> None:
    root = marked(tmp_path)
    take_the_lock_out(root)
    [finding] = held_to(root)
    assert finding["label"] == "handed-out-lock"
    assert finding["message"].endswith(WRITE_BACK)


@EACH_RUN
@pytest.mark.parametrize("state", ["draft", "published", "final"])
def test_a_record_that_conflicts_on_a_merge_reads_the_piece_as_final_and_says_why(
    tmp_path: Path, state: str, args: tuple[str, ...]
) -> None:
    root = marked(tmp_path)
    set_fields(root, state=state)
    (root / RECORD).write_text(CONFLICT, encoding="utf-8")
    (root / HANDED_OUT_LIGHT).unlink()
    found = document(root, *args)
    [finding] = held_to(root, *args)
    assert (finding["label"], finding["severity"]) == ("exports-unreadable", "error")
    assert finding["location"] == RECORD
    assert finding["message"].startswith(
        "the piece `flow` reads as final, held to no version handed out: its record of exports "
        "cannot be read: "
    )
    assert finding["message"].endswith(
        " — mend the record, and each command reads the piece by its state again"
    )
    assert str(root) not in finding["message"]
    assert "file-unreadable" in [each["label"] for each in found["findings"]]
    assert found["summary"][0].endswith(LEFT_OUT)
    assert run(root, *args).returncode == 1


def test_a_published_piece_whose_record_cannot_be_read_owes_nothing_of_its_copy(
    tmp_path: Path,
) -> None:
    root = published(tmp_path)
    (root / RECORD).write_text(CONFLICT, encoding="utf-8")
    (root / LIGHT).unlink()
    assert owed(root) == []
    assert said(held_to(root)) == [("exports-unreadable", "error", RECORD)]


def test_a_record_read_as_a_file_that_names_no_number_alone_says_why(tmp_path: Path) -> None:
    """No pass over the bindings names this record, so the finding here is all the check says
    of it."""
    root = marked(tmp_path)
    edit_exports(root, handed_out="first")
    [finding] = document(root, PIECE)["findings"]
    assert finding["label"] == "exports-unreadable"
    assert "`handed-out` holds no version's number" in finding["message"]
