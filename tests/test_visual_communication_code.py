"""Written code (visual-communication DEC-002 point 1, DEC-005 points 7 to 9, DEC-006 points 4,
5 and 8): the declaration and where its code may go, a run that writes the code and its
record, and what the check finds about them. Run in this process, in a project in the
test's own folder, from the shipped foundations and the test brand."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import (
    FOUNDATIONS,
    TEST_BRAND,
    bound,
    copy_library,
    importable,
    project,
    write,
    yaml_text,
)

code, css, seam, files, fingerprint, reading, findings_ = load(
    "visual-communication",
    "code",
    "plugins.css",
    "plugins.seam",
    "files",
    "fingerprint",
    "reading",
    "findings",
)

NAME = "brand-css"
LOCK = {"foundations": "1.0.0", "test-brand": "1.0.0"}
NOW = datetime(2026, 11, 2, 10, 30, tzinfo=UTC)
TYPOGRAPHY = ("type.body", "type.heading")


@pytest.fixture(autouse=True)
def _writer_importable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The writer stands in for the import a run makes when it runs it, for the length of
    the test."""
    importable(monkeypatch, css)


def declare(root: Path, name: str = NAME, **fields: Any) -> Path:
    """The declaration `name`: the css writer, form 1, the test brand, `out` web/brand.css,
    unless `fields` say otherwise; a field given as None is left out."""
    data = {"writer": "css", "form": 1, "brand": "test-brand", "lock": dict(LOCK)}
    data["out"] = "web/brand.css"
    data.update(fields)
    data = {key: value for key, value in data.items() if value is not None}
    return write(root / "visual" / "code" / f"{name}.yaml", yaml_text(bound("code", **data)))


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A project holding the foundations and the test brand, and one declaration."""
    found = project(tmp_path)
    copy_library(found, FOUNDATIONS, "foundations", "1.0.0")
    copy_library(found, TEST_BRAND, "test-brand", "1.0.0")
    declare(found)
    return found


def run(root: Path, name: str = NAME) -> Any:
    return code.write(root, "visual", name, now=NOW)


def found(root: Path) -> list[tuple[str, str]]:
    """The check's findings on written code, as (code, level), losses left out."""
    return [(f.code, f.level) for f in code.findings(root, "visual") if f.code != "code-loss"]


def record_of(root: Path, out: str = "web/brand.css") -> dict[str, Any]:
    return reading.read_yaml(root / f"{out}.record.yaml")


# --- a run --------------------------------------------------------------------------------------


def test_a_run_writes_the_code_and_its_record_beside_it(root: Path) -> None:
    written = run(root)
    assert (written.code, written.record, written.changed) == (
        "web/brand.css",
        "web/brand.css.record.yaml",
        True,
    )
    sheet = (root / "web/brand.css").read_bytes()
    assert sheet.startswith(b"/* A brand's values as CSS custom properties")
    assert b"  --space--2: 8px;\n" in sheet
    record = record_of(root)
    assert files.binding_problem(record, "code-record") is None
    assert files.shape_problems(record, "code-record") == []
    assert record["sha256"] == reading.sha256(sheet)
    assert record["recorded"] == {
        "plugins": {"css": "1.0.0"},
        "programs": {},
        "machine": record["recorded"]["machine"],
        "time": "2026-11-02T10:30:00Z",
        "capability": "0.1.0",
    }
    text = (root / "web/brand.css.record.yaml").read_text(encoding="utf-8")
    assert text.startswith("# The record of the code `pkit visual write-code brand-css` writes")
    assert "  time: '2026-11-02T10:30:00Z'\n" in text


def test_the_record_fingerprints_the_declaration_each_value_written_and_the_writer(
    root: Path,
) -> None:
    run(root)
    entries = record_of(root)["fingerprint"]["inputs"]
    identities = [{k: v for k, v in entry.items() if k != "sha256"} for entry in entries]
    assert {"code": NAME} in identities
    assert {"plugin": "css", "version": "1.0.0"} in identities
    read = {(i["value"], i["key"]) for i in identities if "value" in i}
    tokens_written = {path for path, _ in read}
    assert not tokens_written & set(TYPOGRAPHY)
    assert len(tokens_written) == 14
    assert read == {
        (path, key)
        for path in tokens_written
        for key in (
            "default",
            "colour-scheme.dark",
            "contrast.high",
            "colour-scheme.dark+contrast.high",
        )
    }
    assert len(entries) == 2 + 14 * 4


def test_a_prefix_opens_every_name(root: Path) -> None:
    declare(root, prefix="brand")
    run(root)
    sheet = (root / "web/brand.css").read_text(encoding="utf-8")
    assert "  --brand--space--2: 8px;\n" in sheet
    assert "  --space--2" not in sheet


def test_a_run_whose_record_verifies_writes_nothing(root: Path) -> None:
    run(root)
    before = {p: p.stat().st_mtime_ns for p in (root / "web").iterdir()}
    again = code.write(root, "visual", NAME, now=datetime(2027, 1, 1, tzinfo=UTC))
    assert again.changed is False
    assert {p: p.stat().st_mtime_ns for p in (root / "web").iterdir()} == before
    assert record_of(root)["recorded"]["time"] == "2026-11-02T10:30:00Z"


def test_code_a_checkout_gave_crlf_endings_is_up_to_date_as_the_check_reads_it(
    root: Path,
) -> None:
    run(root)
    sheet = root / "web/brand.css"
    crlf = sheet.read_bytes().replace(b"\n", b"\r\n")
    sheet.write_bytes(crlf)
    again = code.write(root, "visual", NAME, now=datetime(2027, 1, 1, tzinfo=UTC))
    assert again.changed is False
    assert sheet.read_bytes() == crlf
    assert record_of(root)["recorded"]["time"] == "2026-11-02T10:30:00Z"


def test_a_run_reports_the_losses_its_declaration_does_not_accept(root: Path) -> None:
    written = run(root)
    assert [(loss.plugin, loss.what, loss.did) for loss in written.losses] == [
        ("css", "type.body", "left-out"),
        ("css", "type.heading", "left-out"),
    ]
    assert "typography" in written.losses[0].why
    accepted = [{"plugin": "css", "what": "type.body", "reason": "Pages set their own type."}]
    declare(root, NAME, **{"accept-losses": accepted})
    assert [loss.what for loss in run(root).losses] == ["type.heading"]


def test_the_lock_is_never_moved(root: Path) -> None:
    before = (root / "visual/code/brand-css.yaml").read_bytes()
    run(root)
    assert (root / "visual/code/brand-css.yaml").read_bytes() == before


# --- what a run refuses -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("out", "why"),
    [
        (".pkit/brand.css", "does not hold the schema"),
        (".hidden/brand.css", "does not hold the schema"),
        ("../brand.css", "does not hold the schema"),
        ("visual/libraries/test-brand/brand.css", "library folder"),
        ("visual/libraries", "library folder"),
        ("web", "is a folder"),
        ("visual/code/brand.css", "folder of declarations"),
        ("visual/pieces/flow/piece.yaml", "folder of pieces"),
    ],
)
def test_an_out_the_rules_refuse_is_refused(root: Path, out: str, why: str) -> None:
    (root / "web").mkdir()
    declare(root, out=out)
    with pytest.raises(code.CodeRefused, match=why):
        run(root)


def test_an_out_reached_through_a_link_is_refused(root: Path) -> None:
    (root / "elsewhere").mkdir()
    os.symlink(root / "elsewhere", root / "web")
    with pytest.raises(code.CodeRefused, match="through the link web"):
        run(root)
    assert list((root / "elsewhere").iterdir()) == []


@pytest.mark.parametrize(
    ("name", "why"),
    [("Brand", "is not the name"), ("missing", "there is no declaration")],
)
def test_a_name_that_names_no_declaration_is_refused(root: Path, name: str, why: str) -> None:
    with pytest.raises(code.CodeRefused, match=why):
        run(root, name)


def test_a_declaration_of_another_shape_or_binding_is_refused(root: Path) -> None:
    declare(root, flavour="mint")
    with pytest.raises(code.CodeRefused, match="flavour"):
        run(root)
    write(root / "visual/code/brand-css.yaml", "writer: css\n")
    with pytest.raises(code.CodeRefused, match="names no schema"):
        run(root)


@pytest.mark.parametrize(
    ("lock", "why"),
    [
        ({"test-brand": "1.0.0"}, "names no version of `foundations`"),
        ({**LOCK, "test-brand": "1.1.0"}, "does not hold"),
        ({**LOCK, "foundations": "2.0.0"}, "does not hold"),
    ],
)
def test_a_lock_that_does_not_hold_is_refused(root: Path, lock: dict[str, str], why: str) -> None:
    declare(root, lock=lock)
    with pytest.raises(code.CodeRefused, match=why):
        run(root)


def test_a_lock_whose_majors_do_not_fit_is_refused(root: Path) -> None:
    copy_library(root, FOUNDATIONS, "foundations", "2.0.0")
    library = root / "visual/libraries/foundations/2.0.0/library.yaml"
    library.write_text(library.read_text().replace("version: 1.0.0", "version: 2.0.0"))
    declare(root, lock={**LOCK, "foundations": "2.0.0"})
    with pytest.raises(code.CodeRefused, match="does not fit"):
        run(root)


def test_a_brand_that_is_no_brand_is_refused(root: Path) -> None:
    declare(root, brand="foundations", lock={"foundations": "1.0.0"})
    with pytest.raises(code.CodeRefused, match="not a brand"):
        run(root)


def test_a_brand_with_a_size_axis_is_refused(root: Path) -> None:
    roles = root / "visual/libraries/foundations/1.0.0/roles.yaml"
    text = roles.read_text(encoding="utf-8")
    text = text.replace(
        "axes:\n", "axes:\n  density: {kind: size, modes: [normal, tight], default: normal}\n"
    )
    roles.write_text(text, encoding="utf-8")
    with pytest.raises(code.CodeRefused, match="size axis `density`"):
        run(root)


# --- the findings -------------------------------------------------------------------------------


def test_code_written_and_fresh_has_no_finding_but_its_losses(root: Path) -> None:
    run(root)
    every = code.findings(root, "visual")
    assert [(f.code, f.level, f.where) for f in every] == [
        ("code-loss", "attention", "type.body"),
        ("code-loss", "attention", "type.heading"),
    ]
    assert every[0].file == "visual/code/brand-css.yaml"
    assert every[0].who


def test_an_accepted_loss_is_not_repeated(root: Path) -> None:
    accepted = [
        {"plugin": "css", "what": path, "reason": "Pages set their own type."}
        for path in TYPOGRAPHY
    ]
    declare(root, NAME, **{"accept-losses": accepted})
    run(root)
    assert code.findings(root, "visual") == []


def test_neither_the_code_nor_its_record_is_a_fact_naming_the_command(root: Path) -> None:
    (finding,) = [f for f in code.findings(root, "visual") if f.code != "code-loss"]
    assert (finding.code, finding.level) == ("code-not-written", "fact")
    assert "pkit visual write-code brand-css" in finding.fix
    assert finding.file == "visual/code/brand-css.yaml"


def test_code_without_its_record_fails(root: Path) -> None:
    run(root)
    (root / "web/brand.css.record.yaml").unlink()
    assert found(root) == [("code-record-missing", "fails")]


def test_a_record_naming_code_that_is_missing_fails(root: Path) -> None:
    run(root)
    (root / "web/brand.css").unlink()
    assert found(root) == [("code-missing", "fails")]


def test_a_record_that_cannot_be_read_fails(root: Path) -> None:
    run(root)
    record = root / "web/brand.css.record.yaml"
    record.write_text("fingerprint: [\n", encoding="utf-8")
    assert found(root) == [("code-record-unreadable", "fails")]
    record.write_text("sha256: x\n", encoding="utf-8")
    assert found(root) == [("code-record-unreadable", "fails")]


def test_code_stale_by_a_value_fails_naming_the_value(root: Path) -> None:
    run(root)
    base = root / "visual/libraries/test-brand/1.0.0/tokens/base.tokens.json"
    tokens = json.loads(base.read_text(encoding="utf-8"))
    tokens["accent"]["$value"] = "{scheme.ink}"
    base.write_text(json.dumps(tokens), encoding="utf-8")
    (finding,) = [f for f in code.findings(root, "visual") if f.code != "code-loss"]
    assert (finding.code, finding.level) == ("code-stale", "fails")
    assert "the value of `accent` in `default` changed" in finding.message
    assert finding.file == "web/brand.css.record.yaml"
    assert "pkit visual write-code brand-css" in finding.fix


def test_code_stale_by_its_declaration_fails(root: Path) -> None:
    run(root)
    declare(root, prefix="brand")
    (finding,) = [f for f in code.findings(root, "visual") if f.code != "code-loss"]
    assert (finding.code, finding.level) == ("code-stale", "fails")
    assert "the declaration `brand-css` changed" in finding.message


def test_code_stale_only_by_its_writers_version_asks_for_attention(root: Path) -> None:
    run(root)
    newer = {**seam.declaration("css"), "version": "1.1.0"}
    seam.register(newer, css)
    try:
        (finding,) = [f for f in code.findings(root, "visual") if f.code != "code-loss"]
    finally:
        seam.unregister("css")
    assert (finding.code, finding.level) == ("code-stale-writer", "attention")
    assert "1.0.0" in finding.message and "1.1.0" in finding.message
    assert finding.who


def test_a_newer_writer_and_a_changed_value_fail(root: Path) -> None:
    run(root)
    declare(root, prefix="brand")
    seam.register({**seam.declaration("css"), "version": "1.1.0"}, css)
    try:
        assert found(root) == [("code-stale", "fails")]
    finally:
        seam.unregister("css")


def test_an_edited_fingerprint_fails(root: Path) -> None:
    run(root)
    record = root / "web/brand.css.record.yaml"
    text = record.read_text(encoding="utf-8")
    first = record_of(root)["fingerprint"]["inputs"][0]["sha256"]
    record.write_text(text.replace(first, "0" * 64, 1), encoding="utf-8")
    assert found(root) == [("code-stale", "fails")]


def test_code_edited_by_hand_fails_and_line_endings_alone_do_not(root: Path) -> None:
    run(root)
    sheet = root / "web/brand.css"
    data = sheet.read_bytes()
    sheet.write_bytes(data.replace(b"\n", b"\r\n"))
    assert found(root) == []
    sheet.write_bytes(data.replace(b"8px", b"9px"))
    assert found(root) == [("code-edited", "fails")]


def test_an_out_the_rules_refuse_fails_at_the_declaration(root: Path) -> None:
    (root / "web").mkdir()
    declare(root, out="web")
    (finding,) = code.findings(root, "visual")
    assert (finding.code, finding.level, finding.where) == ("code-out", "fails", "out")


def test_a_declaration_that_cannot_be_checked_fails(root: Path) -> None:
    declare(root, lock={"test-brand": "1.0.0"})
    (finding,) = code.findings(root, "visual")
    assert (finding.code, finding.level) == ("code-unchecked", "fails")
    assert "foundations" in finding.message


def test_a_declaration_the_check_reports_by_its_binding_or_shape_gets_no_finding_here(
    root: Path,
) -> None:
    write(root / "visual/code/brand-css.yaml", "writer: css\n")
    write(root / "visual/code/broken.yaml", "writer: [\n")
    declare(root, "odd", writer=7)
    assert code.findings(root, "visual") == []


def test_a_declaration_whose_file_name_is_no_name_fails(root: Path) -> None:
    write(root / "visual/code/Brand CSS.yaml", "")
    names = [(f.code, f.file) for f in code.findings(root, "visual") if f.code == "code-name"]
    assert names == [("code-name", "visual/code/Brand CSS.yaml")]


def test_only_the_files_directly_in_the_code_folder_are_declarations(root: Path) -> None:
    write(root / "visual/code/notes/old.yaml", "")
    write(root / "visual/code/README.md", "")
    declare(root, "second", out="web/second.css")
    assert code.names(root, "visual") == ["brand-css", "second"]


def test_each_finding_has_a_level_and_names_its_file(root: Path) -> None:
    for finding in code.findings(root, "visual"):
        assert finding.level in findings_.LEVELS
        assert finding.file
        assert finding.fix
