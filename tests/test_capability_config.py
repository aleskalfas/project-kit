"""Tests for recording one key in a capability's own configuration, `pkit config
record` (COR-049 point 5): the key's line goes in as text, every other byte kept;
an absent file is created bound to the capability's configuration schema; nothing
is written where the result would not read back as the file plus that key, or would
bring an error of the schema the file did not have; and a write takes the backbone
configuration's consent forms (COR-048 point 5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import capability_config as cc
from project_kit import data_validate as dv
from project_kit import project_config as pc
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

VISUAL = "visual-communication"
DOCS = "living-docs"
VISUAL_CONFIG = f".pkit/capabilities/{VISUAL}/project/config.yaml"
DOCS_CONFIG = f".pkit/capabilities/{DOCS}/project/config.yaml"


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """An adopter with two capabilities that keep a configuration of their own."""
    return make_adopter_repo(capabilities=(VISUAL, DOCS))


def _record(*args: str, yes: bool = True, input: str | None = None) -> tuple[int, str]:
    """Run `pkit config record`, with `--yes` unless `yes` is False."""
    consent = ["--yes"] if yes else []
    result = CliRunner().invoke(
        main, ["--color", "never", "config", "record", *args, *consent], input=input
    )
    return result.exit_code, result.output


def _write(repo: AdopterRepo, rel: str, data: bytes) -> Path:
    path = repo.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _errors(repo: AdopterRepo, rel: str) -> list[str]:
    issues = dv.validate_data_file(repo.root / rel, repo.root)
    return [i.message for i in issues if i.severity == "error"]


# --- the write -------------------------------------------------------------------


def test_an_absent_file_is_created_bound_to_the_schema(repo: AdopterRepo) -> None:
    """The file the command creates opens with the editor directive, names its schema
    and the schema's version, then holds the key; it validates against the schema."""
    path = repo.root / VISUAL_CONFIG
    assert not path.exists()
    assert _record(VISUAL, "location", "visual") == (
        0,
        f"recorded {VISUAL} location = visual  ({VISUAL_CONFIG})\n",
    )
    assert path.read_text(encoding="utf-8") == (
        "# yaml-language-server: $schema=../schemas/config.schema.json\n"
        f"pkit_schema: {VISUAL}:config\n"
        "schema_version: 1\n"
        "location: visual\n"
    )
    assert _errors(repo, VISUAL_CONFIG) == []


def test_comments_crlf_and_a_byte_order_mark_are_kept(repo: AdopterRepo) -> None:
    """Every byte but the key's line stays as written: the comments, the order, the
    CRLF line endings and the byte-order mark; the line itself ends CRLF."""
    written = (
        "\ufeff# The project's visual work.\r\n"
        "\r\n"
        f"pkit_schema: {VISUAL}:config   # its schema\r\n"
        "schema_version: 1\r\n"
        "# moved by hand only\r\n"
    )
    path = _write(repo, VISUAL_CONFIG, written.encode("utf-8"))
    assert _record(VISUAL, "location", "work/visual") == (
        0,
        f"recorded {VISUAL} location = work/visual  ({VISUAL_CONFIG})\n",
    )
    assert (
        path.read_bytes()
        == (
            "\ufeff# The project's visual work.\r\n"
            "\r\n"
            f"pkit_schema: {VISUAL}:config   # its schema\r\n"
            "schema_version: 1\r\n"
            "location: work/visual\r\n"
            "# moved by hand only\r\n"
        ).encode()
    )
    assert _errors(repo, VISUAL_CONFIG) == []


def test_a_nested_key_goes_under_its_mapping_in_the_file_s_layout(repo: AdopterRepo) -> None:
    written = (
        f"pkit_schema: {DOCS}:config\n"
        "schema_version: 1\n"
        "\n"
        "spaces:\n"
        "    technical:\n"
        "        definition: docs/rule-sets/technical.md   # the space's rules\n"
        "    # the user space comes next\n"
    )
    path = _write(repo, DOCS_CONFIG, written.encode("utf-8"))
    assert _record(DOCS, "spaces.user.definition", "docs/rule-sets/user.md")[0] == 0
    assert path.read_text(encoding="utf-8") == (
        f"pkit_schema: {DOCS}:config\n"
        "schema_version: 1\n"
        "\n"
        "spaces:\n"
        "    technical:\n"
        "        definition: docs/rule-sets/technical.md   # the space's rules\n"
        "    user:\n"
        "        definition: docs/rule-sets/user.md\n"
        "    # the user space comes next\n"
    )


def test_a_file_holding_no_mapping_yet_gains_the_binding(repo: AdopterRepo) -> None:
    path = _write(repo, VISUAL_CONFIG, b"# Filled in by the commands that need it.\n")
    assert _record(VISUAL, "location", "visual")[0] == 0
    assert path.read_text(encoding="utf-8") == (
        "# Filled in by the commands that need it.\n"
        f"pkit_schema: {VISUAL}:config\n"
        "schema_version: 1\n"
        "location: visual\n"
    )


@pytest.mark.parametrize("value", ["yes", "Off", "null", "1.0", "2026-11-03", "a: b", "#x", "x y"])
def test_a_value_any_yaml_reader_would_read_otherwise_is_quoted(
    repo: AdopterRepo, value: str
) -> None:
    """A value is text: written plain only where YAML 1.1 and 1.2 both read it back as
    that text, double-quoted otherwise."""
    path = _write(repo, VISUAL_CONFIG, f"pkit_schema: {VISUAL}:config\n".encode())
    plan = cc.plan(repo.root, VISUAL, "location", value)
    assert plan.after is not None
    assert plan.after.decode("utf-8").endswith(f"location: {json.dumps(value)}\n")
    assert path.read_text(encoding="utf-8") == f"pkit_schema: {VISUAL}:config\n"
    assert YAML(typ="safe").load(plan.after.decode("utf-8"))["location"] == value


def test_the_value_recorded_already_writes_nothing(repo: AdopterRepo) -> None:
    path = _write(repo, VISUAL_CONFIG, f"pkit_schema: {VISUAL}:config\nlocation: visual\n".encode())
    before = path.read_bytes()
    assert _record(VISUAL, "location", "visual") == (
        0,
        f"{VISUAL} location = visual  (recorded already)\n",
    )
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("held", "named"), [("location: art\n", "`art`"), ("location:\n", "an empty value")]
)
def test_another_value_is_never_moved(repo: AdopterRepo, held: str, named: str) -> None:
    """A recorded value is explicit and always wins (COR-049 point 3): only a person
    moves it, an empty one included."""
    path = _write(repo, VISUAL_CONFIG, f"pkit_schema: {VISUAL}:config\n{held}".encode())
    before = path.read_bytes()
    code, output = _record(VISUAL, "location", "visual")
    assert code == 1
    assert f"records {named} at `location` already; a recording never moves it" in output
    assert path.read_bytes() == before


# --- nothing written ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("written", "why"),
    [
        (
            "defaults: &shared\n  technical: {definition: a.md}\nspaces: *shared\n",
            "shared through a YAML alias",
        ),
        ("pkit_schema: living-docs:config\r\nschema_version: 1\n", "mixes line endings"),
    ],
)
def test_a_result_that_would_not_read_back_writes_nothing(
    repo: AdopterRepo, written: str, why: str
) -> None:
    """Where the key's line cannot go in as text so that the file reads back as it was
    plus that key, nothing is written, and the message names the line to add by hand."""
    path = _write(repo, DOCS_CONFIG, written.encode("utf-8"))
    before = path.read_bytes()
    code, output = _record(DOCS, "spaces.user.definition", "docs/user.md")
    assert code == 1
    assert "would not read back as it is plus `spaces.user.definition`" in output
    assert why in output
    assert "add `spaces.user.definition: docs/user.md` there by hand" in output
    assert path.read_bytes() == before


def test_a_result_the_schema_refuses_writes_nothing(repo: AdopterRepo) -> None:
    code, output = _record(VISUAL, "locaton", "visual")
    assert code == 1
    assert "the result would not validate against visual-communication:config" in output
    assert "unknown key 'locaton'; did you mean 'location'?" in output
    assert not (repo.root / VISUAL_CONFIG).exists()


def test_an_error_the_file_already_had_does_not_block_the_recording(repo: AdopterRepo) -> None:
    """A recording is not where the file is mended: `pkit validate` reports an error
    it had before, and the key still goes in."""
    path = _write(repo, VISUAL_CONFIG, f"pkit_schema: {VISUAL}:config\nsize: 3\n".encode())
    assert _record(VISUAL, "location", "visual")[0] == 0
    assert path.read_text(encoding="utf-8").endswith("size: 3\nlocation: visual\n")
    assert any("unknown key 'size'" in message for message in _errors(repo, VISUAL_CONFIG))


def test_a_dry_run_says_what_it_would_record_and_writes_nothing(repo: AdopterRepo) -> None:
    assert _record(VISUAL, "location", "visual", "--dry-run") == (
        0,
        f"would record {VISUAL} location = visual  ({VISUAL_CONFIG})\nDry run: nothing written.\n",
    )
    assert not (repo.root / VISUAL_CONFIG).exists()
    code, _output = _record(VISUAL, "locaton", "visual", "--dry-run")
    assert code == 1


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("backbone", "name", "x"), "is set with `pkit config set <key> <value>`"),
        (("evidence", "x", "y"), "no capability named 'evidence' is installed"),
        (("claude-code", "x", "y"), "'claude-code' is an adapter; an adapter keeps no"),
        ((VISUAL, "a..b", "y"), "is not a dotted path of non-empty segments"),
        ((VISUAL, "location", ""), "a recording records a value: VALUE is empty"),
        ((DOCS, "spaces.no.definition", "y"), "the segment 'no' is no word every YAML reader"),
        ((DOCS, "spaces.2nd.definition", "y"), "the segment '2nd' is no word every YAML reader"),
        ((DOCS, "spaces.Yes.definition", "y"), "the segment 'Yes' is no word every YAML reader"),
        ((DOCS, "NULL", "y"), "the segment 'NULL' is no word every YAML reader"),
        ((DOCS, "pkit_schema", "software-analysis:config"), "binds the configuration"),
        ((DOCS, "schema_version", "x"), "binds the configuration"),
    ],
)
def test_what_no_recording_may_write_is_refused(
    repo: AdopterRepo, args: tuple[str, ...], message: str
) -> None:
    code, output = _record(*args)
    assert code == 1
    assert message in output


def test_a_capability_without_a_configuration_schema_is_refused(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo(capabilities=("project-management", "software-engineering"))
    code, output = _record("software-engineering", "x", "y")
    assert code == 1
    assert "software-engineering ships no configuration schema" in output
    assert not (repo.root / ".pkit/capabilities/software-engineering/project/config.yaml").exists()


def test_a_value_where_a_mapping_is_needed_is_refused(repo: AdopterRepo) -> None:
    path = _write(repo, DOCS_CONFIG, f"pkit_schema: {DOCS}:config\nspaces: none\n".encode())
    before = path.read_bytes()
    code, output = _record(DOCS, "spaces.user.definition", "docs/user.md")
    assert code == 1
    assert "holds a value at `spaces`, not a mapping" in output
    assert path.read_bytes() == before


def test_an_empty_value_where_a_mapping_is_needed_says_so(repo: AdopterRepo) -> None:
    """An empty value on the way is refused as one, so a person sees that the empty
    mapping mends it; recorded under that mapping, the key goes in."""
    written = f"pkit_schema: {DOCS}:config\nschema_version: 1\nspaces:\n"
    path = _write(repo, DOCS_CONFIG, written.encode())
    code, output = _record(DOCS, "spaces.user.definition", "docs/user.md")
    assert code == 1
    assert "holds an empty value at `spaces`, not a mapping" in output
    assert "Give `spaces` the empty mapping `{}` and record again" in output
    assert path.read_text(encoding="utf-8") == written
    _write(repo, DOCS_CONFIG, written.replace("spaces:", "spaces: {}").encode())
    assert _record(DOCS, "spaces.user.definition", "docs/user.md")[0] == 0
    assert _errors(repo, DOCS_CONFIG) == []


def test_a_file_reached_through_a_link_is_refused(repo: AdopterRepo) -> None:
    """A whole-file write would replace the link it was reached by."""
    elsewhere = _write(repo, "elsewhere.yaml", f"pkit_schema: {VISUAL}:config\n".encode())
    (repo.root / VISUAL_CONFIG).parent.mkdir(parents=True, exist_ok=True)
    (repo.root / VISUAL_CONFIG).symlink_to(elsewhere)
    code, output = _record(VISUAL, "location", "visual")
    assert code == 1
    assert f"{VISUAL_CONFIG} is reached through the link {VISUAL_CONFIG}" in output
    assert elsewhere.read_text(encoding="utf-8") == f"pkit_schema: {VISUAL}:config\n"


@pytest.mark.parametrize("written", [None, b"# nothing recorded yet\n"])
def test_a_schema_declaring_no_version_binds_no_file(
    repo: AdopterRepo, written: bytes | None
) -> None:
    """Where the writer would bind the file, absent or holding no mapping yet, a schema
    that declares no `schema_version` gives the binding no version to name: the key is
    refused and nothing is written, never `schema_version: null` (COR-023)."""
    schema = repo.root / f".pkit/capabilities/{VISUAL}/schemas/config.yaml"
    schema.write_text(
        schema.read_text(encoding="utf-8").replace("schema_version: 1\n", ""), encoding="utf-8"
    )
    path = repo.root / VISUAL_CONFIG
    if written is not None:
        _write(repo, VISUAL_CONFIG, written)
    code, output = _record(VISUAL, "location", "visual")
    assert code == 1
    assert f"{VISUAL}'s `schemas/config.yaml` declares no whole-number `schema_version`" in output
    assert (path.read_bytes() if path.exists() else None) == written


# --- the document a script reads -----------------------------------------------------


def test_the_json_document_names_each_outcome(repo: AdopterRepo) -> None:
    def document(*args: str, yes: bool = True) -> tuple[int, dict[str, object]]:
        code, output = _record(VISUAL, "location", *args, "--json", yes=yes)
        return code, json.loads(output)

    base = {
        "schema_version": 1,
        "capability": VISUAL,
        "key": "location",
        "value": "visual",
        "file": VISUAL_CONFIG,
        "reason": None,
    }
    assert document("visual", "--dry-run") == (0, {**base, "outcome": "would-record"})
    code, unconsented = document("visual", yes=False)
    assert (code, unconsented["outcome"]) == (1, "refused")
    assert "without consent" in str(unconsented["reason"])
    assert not (repo.root / VISUAL_CONFIG).exists()
    assert document("visual") == (0, {**base, "outcome": "recorded"})
    assert document("visual") == (0, {**base, "outcome": "recorded-already"})
    code, refused = document("art")
    assert code == 1
    assert refused["outcome"] == "refused"
    assert refused["file"] is None
    assert "a recording never moves it" in str(refused["reason"])


# --- consent -------------------------------------------------------------------------


def test_off_a_terminal_a_write_without_yes_is_refused(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run with nobody to ask and no `--yes` writes nothing and names the command
    to run; one that has nothing to write asks nothing (COR-048 point 5)."""
    monkeypatch.setattr(pc, "stdin_is_tty", lambda: False)
    code, output = _record(VISUAL, "location", "visual", yes=False)
    assert code == 1
    assert f"refusing to write {VISUAL_CONFIG} without consent" in output
    assert f"pkit config record {VISUAL} location visual --yes" in output
    assert f"pkit config record {VISUAL} location visual --dry-run" in output
    assert not (repo.root / VISUAL_CONFIG).exists()
    assert _record(VISUAL, "location", "visual")[0] == 0
    assert _record(VISUAL, "location", "visual", yes=False) == (
        0,
        f"{VISUAL} location = visual  (recorded already)\n",
    )


@pytest.mark.parametrize(("answer", "code"), [("y\n", 0), ("n\n", 1)])
def test_at_a_terminal_it_asks_once(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch, answer: str, code: int
) -> None:
    monkeypatch.setattr(pc, "stdin_is_tty", lambda: True)
    result_code, output = _record(VISUAL, "location", "visual", yes=False, input=answer)
    assert result_code == code
    assert f"Record location = visual in {VISUAL_CONFIG}?" in output
    assert (repo.root / VISUAL_CONFIG).exists() is (code == 0)


# --- a file the schema cannot judge ------------------------------------------------------


def test_a_file_in_an_older_format_is_refused(repo: AdopterRepo) -> None:
    """A file whose `schema_version` its migration has not carried over yet is judged by
    no schema at hand, so nothing is recorded in it (COR-023)."""
    path = _write(
        repo, VISUAL_CONFIG, f"pkit_schema: {VISUAL}:config\nschema_version: 0\n".encode()
    )
    before = path.read_bytes()
    code, output = _record(VISUAL, "locaton", "visual")
    assert code == 1
    assert f"declares `schema_version: 0`, and {VISUAL}:config is at 1" in output
    assert path.read_bytes() == before


def test_a_file_naming_another_schema_is_refused(repo: AdopterRepo) -> None:
    path = _write(repo, DOCS_CONFIG, b"pkit_schema: software-analysis:config\n")
    before = path.read_bytes()
    code, output = _record(DOCS, "spaces.user.definition", "docs/user.md")
    assert code == 1
    assert "names the schema `software-analysis:config`, not `living-docs:config`" in output
    assert path.read_bytes() == before
