"""Written code (visual-communication DEC-002 point 1, DEC-005 points 7 to 9, DEC-006 points 4,
5 and 8): the declaration and where its code may go, a run that writes the code and its
record, what a write that fails leaves, and what the check finds about them. Run in this
process, in a project in the test's own folder, from the shipped foundations and the test
brand."""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import (
    RELEASED_FOUNDATIONS,
    TEST_BRAND,
    TEST_EDITION,
    TEST_PARTS,
    bound,
    capability_version,
    copy_library,
    hold_shipped,
    importable,
    project,
    write,
    yaml_text,
)
from tests.visual_communication_writes import FULL, failing

code, css, json_writer, seam, files, fingerprint, reading, findings_, before_after, copies = load(
    "visual-communication",
    "code",
    "plugins.css",
    "plugins.json",
    "plugins.seam",
    "files",
    "fingerprint",
    "reading",
    "findings",
    "before_after",
    "copies",
)

NAME = "brand-css"
LOCK = {"foundations": "1.0.0", "test-brand": "1.0.0"}
NOW = datetime(2026, 11, 2, 10, 30, tzinfo=UTC)
TYPOGRAPHY = ("type.body", "type.code", "type.heading", "type.strong")


@pytest.fixture(autouse=True)
def _writer_importable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The writers stand in for the import a run makes when it runs one, for the length of
    the test."""
    importable(monkeypatch, css, json_writer)


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
    copy_library(found, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
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
        "capability": capability_version(),
    }
    text = (root / "web/brand.css.record.yaml").read_text(encoding="utf-8")
    assert text.startswith("# The record of the code `pkit visual write-code brand-css` writes")
    assert "  time: '2026-11-02T10:30:00Z'\n" in text


#: The tokens the CSS writer writes of the test brand: the shared roles but the typographies,
#: the colours of the foundations' six colour families among them.
WRITTEN = 34


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
    assert len(tokens_written) == WRITTEN
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
    assert len(entries) == 2 + WRITTEN * 4


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
        ("css", "type.code", "left-out"),
        ("css", "type.heading", "left-out"),
        ("css", "type.strong", "left-out"),
    ]
    assert "typography" in written.losses[0].why
    accepted = [{"plugin": "css", "what": "type.body", "reason": "Pages set their own type."}]
    declare(root, NAME, **{"accept-losses": accepted})
    assert [loss.what for loss in run(root).losses] == [
        "type.code",
        "type.heading",
        "type.strong",
    ]


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
    copy_library(root, RELEASED_FOUNDATIONS, "foundations", "2.0.0")
    library = root / "visual/libraries/foundations/2.0.0/library.yaml"
    library.write_text(library.read_text().replace("version: 1.0.0", "version: 2.0.0"))
    declare(root, lock={**LOCK, "foundations": "2.0.0"})
    with pytest.raises(code.CodeRefused, match="does not fit"):
        run(root)


def test_a_brand_that_is_no_brand_is_refused(root: Path) -> None:
    declare(root, brand="foundations", lock={"foundations": "1.0.0"})
    with pytest.raises(code.CodeRefused, match="not a brand"):
        run(root)


def add_size_axis(root: Path) -> None:
    """The size axis `device` on the foundations the location holds (DEC-021 point 1), which
    the test brand does not give unless `give_sizes` makes it."""
    roles = root / "visual/libraries/foundations/1.0.0/roles.yaml"
    text = roles.read_text(encoding="utf-8")
    device = "  device: {kind: size, modes: [desktop, tablet, phone], default: desktop}\n"
    roles.write_text(text.replace("axes:\n", f"axes:\n{device}"), encoding="utf-8")


def give_sizes(root: Path) -> None:
    """The test brand the location holds made to give `device` at `desktop`, as it is, and
    on a `phone`, with a narrower `space.3` (DEC-021 point 2)."""
    folder = root / "visual/libraries/test-brand/1.0.0"
    narrow = {"space": {"$type": "dimension", "3": {"$value": {"value": 8, "unit": "px"}}}}
    write(folder / "tokens/phone.tokens.json", json.dumps(narrow))
    resolver = folder / "test-brand.resolver.json"
    document = json.loads(resolver.read_text(encoding="utf-8"))
    contexts = {"desktop": [], "phone": [{"$ref": "tokens/phone.tokens.json"}]}
    document["modifiers"]["device"] = {"contexts": contexts, "default": "desktop"}
    document["resolutionOrder"].append({"$ref": "#/modifiers/device"})
    resolver.write_text(json.dumps(document), encoding="utf-8")


def test_a_brand_that_gives_no_size_is_written_as_before(root: Path) -> None:
    before = run(root)
    sheet = (root / "web/brand.css").read_bytes()
    add_size_axis(root)
    after = run(root)
    assert (after.changed, after.losses) == (False, before.losses)
    assert (root / "web/brand.css").read_bytes() == sheet


def test_a_brand_that_gives_a_size_is_written_at_the_default_size_with_its_losses(
    root: Path,
) -> None:
    """The CSS writer spells no size axis (DEC-021 point 8): it writes the values at
    `device`'s default, and reports each token a size changes as approximated."""
    run(root)
    sheet = (root / "web/brand.css").read_bytes()
    add_size_axis(root)
    give_sizes(root)
    planned = code.plan(root, "visual", code.read(root, "visual", NAME))
    assert list(planned.axes) == ["colour-scheme", "contrast"]
    assert planned.document["keys"] == [
        "default",
        "colour-scheme.dark",
        "contrast.high",
        "colour-scheme.dark+contrast.high",
    ]
    (approximated,) = [loss for loss in planned.losses if loss.did == "approximated"]
    assert approximated.as_dict() == {
        "plugin": "css",
        "what": "space.3",
        "did": "approximated",
        "why": "form 1 of the css writer spells no size axis, so it writes the value at "
        "`device`'s default, `desktop`",
    }
    assert code.text_of(planned).encode("utf-8") == sheet
    written = run(root)
    assert "space.3" in {loss.what for loss in written.losses}
    assert (root / "web/brand.css").read_bytes() == sheet
    assert ("code-loss", "attention", "space.3") in [
        (f.code, f.level, f.where) for f in code.findings(root, "visual")
    ]


# --- the findings -------------------------------------------------------------------------------


def test_code_written_and_fresh_has_no_finding_but_its_losses(root: Path) -> None:
    run(root)
    every = code.findings(root, "visual")
    assert [(f.code, f.level, f.where) for f in every] == [
        ("code-loss", "attention", "type.body"),
        ("code-loss", "attention", "type.code"),
        ("code-loss", "attention", "type.heading"),
        ("code-loss", "attention", "type.strong"),
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


# --- what a failed run leaves -------------------------------------------------------------------


def written_files(root: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted((root / "web").iterdir())}


@pytest.mark.parametrize("file", ["brand.css", "brand.css.record.yaml"])
def test_a_write_that_fails_leaves_the_code_and_its_record_as_they_were(
    root: Path, monkeypatch: pytest.MonkeyPatch, file: str
) -> None:
    run(root)
    declare(root, prefix="brand")
    before = written_files(root)
    with monkeypatch.context() as patch:
        failing(patch, write={file})
        with pytest.raises(files.WriteFailed) as failed:
            run(root)
    assert str(failed.value) == f"web/{file} could not be written: {FULL}"
    assert written_files(root) == before
    assert found(root) == [("code-stale", "fails")]


def test_a_failed_first_run_writes_neither_the_code_nor_its_record(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with monkeypatch.context() as patch:
        failing(patch, write={"brand.css.record.yaml"})
        with pytest.raises(files.WriteFailed):
            run(root)
    assert not (root / "web").exists()
    assert found(root) == [("code-not-written", "fact")]


def test_code_a_failed_run_could_not_take_back_is_named_and_never_read_as_edited(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with monkeypatch.context() as patch:
        failing(patch, write={"brand.css.record.yaml"}, remove={"brand.css"})
        with pytest.raises(files.WriteFailed) as failed:
            run(root)
    assert str(failed.value).endswith(
        "these could not be put back as they were before the run: web/brand.css"
    )
    assert found(root) == [("code-record-missing", "fails")]


# --- the libraries the lock names (DEC-008 point 5) ---------------------------------------------


def test_code_holds_each_role_of_a_library_its_lock_names_at_the_brands_value_or_default(
    root: Path,
) -> None:
    copy_library(root, TEST_PARTS, "test-parts", "1.0.0")
    declare(root, lock={**LOCK, "test-parts": "1.0.0"})
    planned = code.plan(root, "visual", code.read(root, "visual", NAME))
    tokens_ = planned.document["tokens"]
    assert tokens_["test-parts.note"]["values"] == tokens_["text-primary"]["values"]
    assert "test-parts.warning" not in tokens_
    assert planned.document["lock"]["test-parts"] == "1.0.0"
    run(root)
    assert b"  --test-parts--gap: 8px;\n" in (root / "web/brand.css").read_bytes()


def test_code_of_a_brand_built_on_a_base_reads_the_base_its_lock_names(root: Path) -> None:
    copy_library(root, TEST_EDITION, "test-edition", "1.0.0")
    declare(root, brand="test-edition", lock={**LOCK, "test-edition": "1.0.0"})
    planned = code.plan(root, "visual", code.read(root, "visual", NAME))
    assert planned.document["tokens"]["space.4"]["values"]["default"] == {
        "value": 40,
        "unit": "px",
    }


def test_a_library_the_lock_names_that_the_project_does_not_hold_is_refused(root: Path) -> None:
    declare(root, lock={**LOCK, "test-parts": "1.0.0"})
    with pytest.raises(code.CodeRefused, match=r"test-parts@1\.0\.0, which the project does not"):
        run(root)


# --- the json writer (DEC-005 points 7 to 9, DEC-006 points 4 and 8) ----------------------------

JSON_OUT = "web/brand.json"


def declare_json(root: Path, **fields: Any) -> Path:
    """The declaration of the json writer, under the name the tests run."""
    return declare(root, writer="json", out=JSON_OUT, **fields)


def test_a_json_declaration_holds_its_schema(root: Path) -> None:
    data = reading.read_yaml(declare_json(root))
    assert files.shape_problems(data, "code") == []


def test_the_json_writer_writes_the_document_under_the_lock_with_its_record(root: Path) -> None:
    declared = code.read(root, "visual", declare_json(root).stem)
    document = code.plan(root, "visual", declared).document
    written = run(root)
    assert (written.code, written.record) == (JSON_OUT, f"{JSON_OUT}.record.yaml")
    assert written.losses == ()
    data = (root / JSON_OUT).read_bytes()
    assert json.loads(data) == {**document, "version": 1}
    assert document["version"] == 2
    assert document["lock"] == LOCK
    assert document["keys"] == [
        "default",
        "colour-scheme.dark",
        "contrast.high",
        "colour-scheme.dark+contrast.high",
    ]
    record = record_of(root, JSON_OUT)
    assert files.shape_problems(record, "code-record") == []
    assert record["sha256"] == reading.sha256(data)
    assert record["recorded"]["plugins"] == {"json": "1.0.0"}


def test_the_json_writer_loses_no_token_and_its_record_compares_every_value(root: Path) -> None:
    declare_json(root)
    planned = code.plan(root, "visual", code.read(root, "visual", NAME))
    assert planned.losses == ()
    run(root)
    assert set(TYPOGRAPHY) <= set(json.loads((root / JSON_OUT).read_bytes())["tokens"])
    entries = record_of(root, JSON_OUT)["fingerprint"]["inputs"]
    assert {e["value"] for e in entries if "value" in e} >= set(TYPOGRAPHY)
    assert len(entries) == 2 + (WRITTEN + len(TYPOGRAPHY)) * 4
    assert code.findings(root, "visual") == []


def test_the_json_writer_holds_the_keys_of_each_size_the_brand_gives(root: Path) -> None:
    """A size axis the brand does not give adds no key; one it gives adds the keys of its
    modes, in the document's form (DEC-021 point 8)."""
    declare_json(root)
    run(root)
    before = (root / JSON_OUT).read_bytes()
    add_size_axis(root)
    assert run(root).changed is False
    assert (root / JSON_OUT).read_bytes() == before

    give_sizes(root)
    written = run(root)
    held = json.loads((root / JSON_OUT).read_bytes())
    assert held["keys"] == [
        "default",
        "colour-scheme.dark",
        "contrast.high",
        "device.phone",
        "colour-scheme.dark+contrast.high",
        "colour-scheme.dark+device.phone",
        "contrast.high+device.phone",
        "colour-scheme.dark+contrast.high+device.phone",
    ]
    assert held["tokens"]["space.3"]["values"]["device.phone"] == {"value": 8, "unit": "px"}
    assert files.shape_problems(held, "values") == []
    assert written.losses == ()
    assert code.findings(root, "visual") == []


def neutral(tmp_path: Path, **fields: Any) -> Any:
    """What the declaration of the neutral brand being built, on the foundations being
    built, would hand its writer: the css writer's unless `fields` say otherwise."""
    root = project(tmp_path)
    lock = {name: hold_shipped(root, name).version for name in ("foundations", "neutral")}
    declare(root, brand="neutral", lock=lock, **fields)
    return code.plan(root, "visual", code.read(root, "visual", NAME))


#: The keys of the neutral brand's value axes, with no size.
VALUE_KEYS = [
    "default",
    "colour-scheme.dark",
    "contrast.high",
    "colour-scheme.dark+contrast.high",
]


def test_the_neutral_brand_is_written_as_css_at_a_desktops_values_losing_size_site(
    tmp_path: Path,
) -> None:
    """The neutral brand gives the three sizes of `device`, and `size.site` alone changes
    with them (DEC-022 point 3). The CSS writer spells no size axis, so it writes a
    desktop's width, and reports the role as approximated (DEC-021 point 8)."""
    planned = neutral(tmp_path)
    assert planned.document["keys"] == VALUE_KEYS
    approximated = [loss.as_dict() for loss in planned.losses if loss.did == "approximated"]
    assert approximated == [
        {
            "plugin": "css",
            "what": "size.site",
            "did": "approximated",
            "why": "form 1 of the css writer spells no size axis, so it writes the value at "
            "`device`'s default, `desktop`",
        }
    ]
    assert "  --size--site: 1280px;\n" in code.text_of(planned)


def test_the_neutral_brand_written_as_json_holds_the_keys_of_device(tmp_path: Path) -> None:
    planned = neutral(tmp_path, writer="json", out=JSON_OUT)
    sizes = ["device.tablet", "device.phone"]
    assert set(planned.document["keys"]) == {
        "+".join(part for part in (key, size) if part != "default") or "default"
        for key in VALUE_KEYS
        for size in ("default", *sizes)
    }
    site = planned.document["tokens"]["size.site"]["values"]
    assert [site[key]["value"] for key in ("default", *sizes)] == [1280, 768, 390]
    assert planned.losses == ()


def test_the_json_writer_refuses_a_prefix_naming_why(root: Path) -> None:
    declare_json(root, prefix="brand")
    with pytest.raises(code.CodeRefused) as refused:
        run(root)
    assert str(refused.value) == (
        "visual/code/brand-css.yaml: the json writer takes no `prefix`, since a token path "
        "stays as the brand exports it: remove `prefix: brand`"
    )
    assert not (root / "web").exists()


def test_the_check_names_why_a_json_declaration_takes_no_prefix(root: Path) -> None:
    declare_json(root, prefix="brand")
    (finding,) = code.findings(root, "visual")
    assert (finding.code, finding.level) == ("code-unchecked", "fails")
    assert "a token path stays as the brand exports it" in finding.message


def test_a_writer_that_says_nothing_of_a_prefix_takes_one(root: Path) -> None:
    assert "prefix" not in seam.declaration("css")
    declare(root, prefix="brand")
    assert code.plan(root, "visual", code.read(root, "visual", NAME)).declaration.prefix == "brand"


def test_json_code_with_neither_file_is_a_fact_naming_the_command(root: Path) -> None:
    declare_json(root)
    assert found(root) == [("code-not-written", "fact")]


def test_json_code_without_its_record_fails(root: Path) -> None:
    declare_json(root)
    run(root)
    (root / f"{JSON_OUT}.record.yaml").unlink()
    assert found(root) == [("code-record-missing", "fails")]


def test_a_record_naming_json_code_that_is_missing_fails(root: Path) -> None:
    declare_json(root)
    run(root)
    (root / JSON_OUT).unlink()
    assert found(root) == [("code-missing", "fails")]


def test_json_code_stale_by_a_typography_value_fails_naming_the_value(root: Path) -> None:
    declare_json(root)
    run(root)
    base = root / "visual/libraries/test-brand/1.0.0/tokens/base.tokens.json"
    text = base.read_text(encoding="utf-8")
    base.write_text(text.replace('"lineHeight": 1.4', '"lineHeight": 1.6', 1), encoding="utf-8")
    (finding,) = code.findings(root, "visual")
    assert (finding.code, finding.level) == ("code-stale", "fails")
    assert "the value of `type.body` in `default` changed" in finding.message
    assert finding.file == f"{JSON_OUT}.record.yaml"


def test_json_code_edited_by_hand_fails_and_line_endings_alone_do_not(root: Path) -> None:
    declare_json(root)
    run(root)
    file = root / JSON_OUT
    data = file.read_bytes()
    file.write_bytes(data.replace(b"\n", b"\r\n"))
    assert found(root) == []
    file.write_bytes(data.replace(b'"version": 1', b'"version": 2'))
    assert found(root) == [("code-edited", "fails")]


def test_json_code_stale_only_by_its_writers_version_asks_for_attention(root: Path) -> None:
    declare_json(root)
    run(root)
    seam.register({**seam.declaration("json"), "version": "1.1.0"}, json_writer)
    try:
        (finding,) = code.findings(root, "visual")
    finally:
        seam.unregister("json")
    assert (finding.code, finding.level) == ("code-stale-writer", "attention")
    assert "1.0.0" in finding.message and "1.1.0" in finding.message


# --- a side of a before-and-after (DEC-005 point 7, DEC-013 point 5) ----------------------------

PARTS_LOCK = {**LOCK, "test-parts": "1.0.0"}


def shipped_parts(tmp_path: Path) -> Any:
    """What a capability ships under `test-parts`' number: its gap on another spacing."""
    folder = tmp_path / "shipped"
    shutil.copytree(TEST_PARTS, folder)
    roles = folder / "roles.yaml"
    text = roles.read_text(encoding="utf-8")
    roles.write_text(text.replace("{space.2}", "{space.3}"), encoding="utf-8")
    files = tuple(
        path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()
    )
    number = copies.Version.parse("1.0.0")
    return copies.Source("test-parts", number, folder, files, {"released": False}, None)


def test_a_side_is_the_code_the_writer_writes_under_the_lock(root: Path) -> None:
    copy_library(root, TEST_PARTS, "test-parts", "1.0.0")
    declare(root, lock=PARTS_LOCK)
    side = before_after.writing(root, "visual", NAME, PARTS_LOCK)
    assert side.why == ""
    assert not (root / "web").exists()
    run(root)
    assert side.files == {"web/brand.css": (root / "web/brand.css").read_text(encoding="utf-8")}


def test_a_version_given_stands_in_for_the_copy_and_changes_the_code(
    root: Path, tmp_path: Path
) -> None:
    copy_library(root, TEST_PARTS, "test-parts", "1.0.0")
    declare(root, lock=PARTS_LOCK)
    before = before_after.writing(root, "visual", NAME, PARTS_LOCK)
    after = before_after.writing(root, "visual", NAME, PARTS_LOCK, [shipped_parts(tmp_path)])
    assert before_after.differing(before, after) == ["web/brand.css"]
    assert "--test-parts--gap: 8px;" in before.files["web/brand.css"]
    assert "--test-parts--gap: 16px;" in after.files["web/brand.css"]


def test_the_difference_in_json_code_is_the_lines_of_the_values_that_changed(
    root: Path, tmp_path: Path
) -> None:
    copy_library(root, TEST_PARTS, "test-parts", "1.0.0")
    declare_json(root, lock=PARTS_LOCK)
    before = before_after.writing(root, "visual", NAME, PARTS_LOCK)
    after = before_after.writing(root, "visual", NAME, PARTS_LOCK, [shipped_parts(tmp_path)])
    lines = zip(
        before.files[JSON_OUT].splitlines(), after.files[JSON_OUT].splitlines(), strict=True
    )
    differing = [new for old, new in lines if old != new]
    assert len(differing) == 4
    assert all('{"unit":"px","value":16}' in line for line in differing)


def test_a_side_that_cannot_be_written_says_why(root: Path) -> None:
    side = before_after.writing(root, "visual", NAME, PARTS_LOCK)
    assert side.files == {}
    assert "test-parts@1.0.0, which the project does not hold" in side.why
