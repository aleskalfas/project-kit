"""`pkit visual check` (visual-communication DEC-002 points 6 and 7, DEC-005 point 13): the
validator of `pkit validate`, under the query contract — `--json` prints the findings
document and exits 0; without it, it exits 1 when a finding fails. Its findings are
`test_visual_communication_checks.py`'s; here, the command: the findings record read while
its key verifies, the validation's bound, the time it takes, one run through `pkit
validate`'s runner as a process of its own, and what a state owes of a current copy, read
after each state's real export (DEC-006 point 8, DEC-017 points 5 to 7)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from tests import visual_communication_producer as producer
from tests.adopter_repo import MakeAdopterRepo
from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import (
    LOCK,
    PIECE,
    PIECE_FOLDER,
    drawing_project,
    lay_out_drawing,
    list_drawing_libraries,
    write_content,
    write_picture,
)
from tests.test_visual_communication_render import newer_tests
from tests.visual_communication_project import importable, write, yaml_text

check, render, export, svg, seam, framing, checks, exports, fingerprint, libraries, pl, reading = (
    load(
        "visual-communication",
        "check.py",
        "render.py",
        "export.py",
        "plugins.svg",
        "plugins.seam",
        "framing",
        "checks",
        "exports",
        "fingerprint",
        "libraries",
        "pipeline",
        "reading",
    )
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
    lock = {"foundations": "1.0.0", "tests": "1.0.0"}
    root = drawing_project(tmp_path, state="final", picture=False, lock=lock)
    shown = run(root, PIECE)
    assert shown.returncode == 0, shown.stdout
    lines = shown.stdout.splitlines()
    assert lines[0] == (
        "the piece `flow` in `visual`: the scenes of 0 read from their findings record, of 0 "
        "computed now, of 0 not checked, of 1 left out as final."
    )
    assert any("[lock-incomplete]" in line and line.startswith("  info") for line in lines)


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


class AtAPlace(NamedTuple):
    """A published piece whose copy lies at a place, as an export writes one there."""

    held: Any
    piece: Any
    entry: dict[str, Any]
    versions: list[dict[str, Any]]
    dark: str
    light: str

    def findings(self) -> list[Any]:
        return checks.published_findings(self.held, self.piece, self.entry, self.versions)


def at_a_place(root: Path) -> AtAPlace:
    """The piece, its copy moved to a place, its record's entry naming each file from the
    root."""
    piece = pl.read_piece(root, "visual", PIECE)
    record = exports.recorded(piece)
    files = {}
    for path, digest in record["current-copy"]["files"].items():
        place = f"docs/figures/{Path(path).name}"
        write(root / place, "")
        (root / PIECE_FOLDER / path).replace(root / place)
        files[place] = digest
    dark, light = sorted(files)
    entry = {**record["current-copy"], "files": files}
    return AtAPlace(libraries.Held(root, "visual"), piece, entry, record["versions"], dark, light)


def test_a_file_at_a_place_missing_fails_naming_it_and_the_export(tmp_path: Path) -> None:
    copy = at_a_place(published(tmp_path))
    (copy.piece.root / copy.light).unlink()
    assert copy.findings() == [
        checks.Finding(
            "current-copy-file-missing",
            "fails",
            "a file of the current copy of `flow` is missing",
            file=copy.light,
            fix=EXPORT_AGAIN,
        )
    ]


def test_a_file_at_a_place_changed_fails_and_a_person_removes_it_first(tmp_path: Path) -> None:
    copy = at_a_place(published(tmp_path))
    (copy.piece.root / copy.dark).write_bytes(b"another figure")
    assert copy.findings() == [
        checks.Finding(
            "current-copy-file-changed",
            "fails",
            "a file of the current copy of `flow` is not the one its export wrote",
            file=copy.dark,
            fix=f"remove it, then {EXPORT_AGAIN}",
        )
    ]


def test_a_copy_at_a_place_that_is_whole_owes_nothing(tmp_path: Path) -> None:
    assert at_a_place(published(tmp_path)).findings() == []


def test_a_drafts_file_at_a_place_stands_as_one_in_its_folder(tmp_path: Path) -> None:
    copy = at_a_place(published(tmp_path))
    (copy.piece.root / copy.light).unlink()
    [finding] = checks.standing_findings(copy.piece, copy.entry)
    assert (finding.code, finding.file) == ("current-copy-standing", copy.dark)


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


def test_a_record_the_binding_pass_names_takes_no_finding_of_its_own(tmp_path: Path) -> None:
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
