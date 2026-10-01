"""Tests for the backbone configuration writer and `pkit config set` (COR-048
points 4 and 5): forgiving reads, one consent-gated write that validates before
writing, and the configuration command that uses it."""

from __future__ import annotations

import difflib
from pathlib import Path

import click
import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import project_config as pc
from project_kit import report_context
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO_ROOT = Path(__file__).resolve().parents[1]


def _config_path(repo: AdopterRepo) -> Path:
    return pc.project_config_path(repo.root)


def _write_raw(repo: AdopterRepo, text: str) -> Path:
    path = _config_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _set(key: str, value):
    def mutate(data):
        data[key] = value

    return mutate


YES = pc.Consent(yes=True)
NON_INTERACTIVE = pc.Consent(yes=False, interactive=False, rerun="pkit config set k v --yes")


# --- forgiving read ----------------------------------------------------------


def test_read_config_yields_empty_for_every_zero_config_state(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    assert pc.read_config(repo.root) == {}  # absent
    _write_raw(repo, "")
    assert pc.read_config(repo.root) == {}  # empty
    _write_raw(repo, "- just\n- a list\n")
    assert pc.read_config(repo.root) == {}  # not a mapping
    _write_raw(repo, "name: [unclosed\n")
    assert pc.read_config(repo.root) == {}  # unparsable


def test_read_config_returns_the_mapping(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_raw(repo, "name: alpha\ndocs:\n  internal: tech-docs\n")
    assert pc.read_config(repo.root) == {"name": "alpha", "docs": {"internal": "tech-docs"}}


# --- the write primitive -----------------------------------------------------


def test_write_creates_the_file_with_the_editor_directive(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    path = pc.write_config(repo.root, _set("name", "alpha"), consent=YES)
    text = path.read_text(encoding="utf-8")
    assert text.startswith(pc.EDITOR_DIRECTIVE + "\n")
    assert "name: alpha" in text
    assert not path.with_name(path.name + ".tmp").exists()  # the atomic step left nothing behind


def test_write_keeps_an_existing_header_comments_and_other_keys(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_raw(repo, "# my header\nname: old  # the name\ndocs:\n  user: guide\n")
    pc.write_config(repo.root, _set("name", "new"), consent=YES)
    text = _config_path(repo).read_text(encoding="utf-8")
    assert text.startswith("# my header\n")
    assert pc.EDITOR_DIRECTIVE not in text
    assert "name: new  # the name" in text
    assert "user: guide" in text


def test_write_refuses_an_invalid_result_and_writes_nothing(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_raw(repo, "name: alpha\n")
    before = _config_path(repo).read_text(encoding="utf-8")
    with pytest.raises(pc.InvalidConfigWrite) as excinfo:
        pc.write_config(repo.root, _set("nmae", "typo"), consent=YES)
    assert "Nothing was written" in excinfo.value.format_message()
    assert "nmae" in excinfo.value.format_message()
    assert _config_path(repo).read_text(encoding="utf-8") == before


def test_write_refuses_an_unparsable_existing_file(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_raw(repo, "name: [unclosed\n")
    with pytest.raises(pc.UnwritableConfig):
        pc.write_config(repo.root, _set("name", "alpha"), consent=YES)
    assert _config_path(repo).read_text(encoding="utf-8") == "name: [unclosed\n"


def test_write_without_a_schema_in_the_tree_skips_validation(tmp_path: Path) -> None:
    # A tree recorded before the schema landed (ADR-056 point 1): no shape to
    # check against, so the write proceeds.
    path = pc.write_config(tmp_path, _set("anything", "goes"), consent=YES)
    assert "anything: goes" in path.read_text(encoding="utf-8")


# --- consent (COR-048 point 5) -----------------------------------------------


def test_non_interactive_without_yes_refuses_naming_the_command(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    with pytest.raises(pc.ConsentRefused) as excinfo:
        pc.write_config(repo.root, _set("name", "alpha"), consent=NON_INTERACTIVE)
    message = excinfo.value.format_message()
    assert "pkit config set k v --yes" in message
    assert "Nothing was written" in message
    assert not _config_path(repo).exists()


def test_yes_writes_without_a_prompt(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo()
    monkeypatch.setattr(pc.click, "confirm", lambda *a, **k: pytest.fail("prompted despite --yes"))
    pc.write_config(repo.root, _set("name", "alpha"), consent=YES)
    assert pc.read_config(repo.root)["name"] == "alpha"


def test_interactive_confirmation_writes_and_a_decline_aborts(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo()
    asked: list[str] = []

    def confirm_yes(prompt, **kwargs):
        asked.append(prompt)
        return True

    monkeypatch.setattr(pc.click, "confirm", confirm_yes)
    pc.write_config(
        repo.root, _set("name", "alpha"), consent=pc.Consent(interactive=True), description="Save"
    )
    assert asked == ["Save in .pkit/project/config.yaml?"]
    assert pc.read_config(repo.root)["name"] == "alpha"

    def confirm_no(prompt, **kwargs):
        raise click.Abort()

    monkeypatch.setattr(pc.click, "confirm", confirm_no)
    with pytest.raises(click.Abort):
        pc.write_config(repo.root, _set("name", "beta"), consent=pc.Consent(interactive=True))
    assert pc.read_config(repo.root)["name"] == "alpha"


def test_validation_runs_before_consent_is_asked(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An invalid result is refused outright; nobody is asked to consent to it.
    repo = make_adopter_repo()
    monkeypatch.setattr(
        pc.click, "confirm", lambda *a, **k: pytest.fail("asked for an invalid write")
    )
    with pytest.raises(pc.InvalidConfigWrite):
        pc.write_config(repo.root, _set("nmae", "x"), consent=pc.Consent(interactive=True))


# --- the name write-back rides on the primitive ------------------------------


def test_write_project_name_goes_through_the_primitive(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_raw(repo, "docs:\n  internal: tech-docs\n")
    report_context.write_project_name(repo.root, "alpha")
    assert pc.read_config(repo.root) == {"docs": {"internal": "tech-docs"}, "name": "alpha"}
    with pytest.raises(pc.ConsentRefused):
        report_context.write_project_name(repo.root, "beta", consent=NON_INTERACTIVE)
    assert report_context.read_project_name(repo.root) == "alpha"


# --- key resolution against the schema ---------------------------------------


def _schema(repo: AdopterRepo) -> dict:
    return pc.load_config_schema(repo.root)


def test_resolve_key_finds_scalar_leaves_through_refs(make_adopter_repo: MakeAdopterRepo) -> None:
    schema = _schema(make_adopter_repo())
    assert pc.resolve_key(schema, "name").leaf["type"] == "string"
    assert pc.resolve_key(schema, "docs.internal").leaf["type"] == "string"
    assert pc.resolve_key(schema, "friction.mode").leaf["enum"] == ["warning", "enforcing"]
    # A pattern-keyed map: the address segment matches the pattern, the leaf is a name.
    provider = pc.resolve_key(schema, "connections.providers.pkit::work-tracking")
    assert provider.leaf["type"] == "string"


@pytest.mark.parametrize(
    ("key", "fragment"),
    [
        ("nmae", "did you mean 'name'"),
        ("docs.nope", "did you mean 'user'"),
        ("project", "reserved `project` block"),
        ("project.anything", "reserved `project` block"),
        ("docs", "holds a mapping"),
        ("friction.places", "holds a list"),
        ("connections.providers.not-an-address", "address form"),
        ("", "non-empty segments"),
        ("docs..internal", "non-empty segments"),
    ],
)
def test_resolve_key_refuses_what_it_cannot_set(
    make_adopter_repo: MakeAdopterRepo, key: str, fragment: str
) -> None:
    schema = _schema(make_adopter_repo())
    with pytest.raises(pc.UnknownConfigKey) as excinfo:
        pc.resolve_key(schema, key)
    assert fragment in excinfo.value.format_message()


def test_coerce_value_follows_the_leaf_type() -> None:
    string = pc.ResolvedKey(("k",), {"type": "string"})
    integer = pc.ResolvedKey(("k",), {"type": "integer"})
    boolean = pc.ResolvedKey(("k",), {"type": "boolean"})
    assert pc.coerce_value(string, "12") == "12"
    assert pc.coerce_value(integer, "12") == 12
    assert pc.coerce_value(boolean, "yes") is True
    assert pc.coerce_value(boolean, "off") is False
    with pytest.raises(pc.UnknownConfigKey):
        pc.coerce_value(integer, "twelve")
    with pytest.raises(pc.UnknownConfigKey):
        pc.coerce_value(boolean, "maybe")


# --- `pkit config set` -------------------------------------------------------


def _run(*args: str, input: str | None = None):
    return CliRunner().invoke(main, ["config", "set", *args], input=input)


def test_config_set_writes_with_yes(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    result = _run("docs.internal", "tech-docs", "--yes")
    assert result.exit_code == 0, result.output
    assert "set docs.internal = tech-docs" in result.output
    assert pc.read_config(repo.root) == {"docs": {"internal": "tech-docs"}}
    text = _config_path(repo).read_text(encoding="utf-8")
    assert text.startswith(pc.EDITOR_DIRECTIVE + "\n")


def test_config_set_refuses_non_interactively_without_yes(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo()
    monkeypatch.setattr(pc, "stdin_is_tty", lambda: False)
    result = _run("docs.internal", "tech-docs")
    assert result.exit_code != 0
    assert "pkit config set docs.internal tech-docs --yes" in result.output
    assert not _config_path(repo).exists()


def test_config_set_asks_once_on_a_terminal(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo()
    monkeypatch.setattr(pc, "stdin_is_tty", lambda: True)
    result = _run("docs.internal", "tech-docs", input="y\n")
    assert result.exit_code == 0, result.output
    assert result.output.count("?") == 1
    assert pc.read_config(repo.root)["docs"]["internal"] == "tech-docs"

    declined = _run("docs.internal", "elsewhere", input="n\n")
    assert declined.exit_code != 0
    assert pc.read_config(repo.root)["docs"]["internal"] == "tech-docs"


def test_config_set_validates_key_and_value(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    unknown = _run("docs.nope", "x", "--yes")
    assert unknown.exit_code != 0
    assert "did you mean 'user'" in unknown.output

    reserved = _run("project.x", "y", "--yes")
    assert reserved.exit_code != 0
    assert "reserved `project` block" in reserved.output

    bad_enum = _run("friction.mode", "loud", "--yes")
    assert bad_enum.exit_code != 0
    assert "'loud' is not one of" in bad_enum.output

    absolute = _run("docs.internal", "/abs", "--yes")
    assert absolute.exit_code != 0
    assert "Nothing was written" in absolute.output
    assert not _config_path(repo).exists()


def test_config_set_preserves_the_rest_of_the_file(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_raw(repo, "# header\nname: alpha\n")
    result = _run("friction.mode", "enforcing", "--yes")
    assert result.exit_code == 0, result.output
    text = _config_path(repo).read_text(encoding="utf-8")
    assert text.startswith("# header\n")
    assert pc.read_config(repo.root) == {"name": "alpha", "friction": {"mode": "enforcing"}}


# --- a write changes only the keys it sets (#1198) ---------------------------

# A hand-kept configuration: comments, blank lines, nested lists in two
# layouts, a flow list and quoted strings.
KEPT = """\
# yaml-language-server: $schema=../schemas/backbone/config.schema.json
name: "alpha"  # the declared name

# Documentation roots.
docs:
  user: 'docs/'
  internal: tech-docs/
friction:
  mode: enforcing
  # The places, by space.
  places:
    # technical
    - CONTRIBUTING.md
    - "README.md"

  exclude: [.claude/, 'CHANGELOG.md']
  surface:
  - src/**
  - tests/**
  # Left out of the measures.
process:
  journal:
    enabled: true
"""


def _changed_lines(before: str, after: str) -> list[str]:
    """The lines a diff of the two texts removes and adds, in order."""
    return [
        line
        for line in difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True), n=0
        )
        if line.startswith(("-", "+")) and not line.startswith(("---", "+++"))
    ]


def test_config_set_on_project_kits_own_config_changes_the_one_line(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    before = (REPO_ROOT / pc.PROJECT_CONFIG_RELPATH).read_text(encoding="utf-8")
    current = YAML(typ="safe").load(before)["friction"]["mode"]
    flipped = "warning" if current == "enforcing" else "enforcing"
    path = _write_raw(repo, before)

    result = _run("friction.mode", flipped, "--yes")

    assert result.exit_code == 0, result.output
    after = path.read_text(encoding="utf-8")
    assert _changed_lines(before, after) == [f"-  mode: {current}\n", f"+  mode: {flipped}\n"]


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_config_set_keeps_every_byte_outside_the_key(
    make_adopter_repo: MakeAdopterRepo, newline: str
) -> None:
    repo = make_adopter_repo()
    path = _config_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    before = KEPT.replace("\n", newline).encode("utf-8")
    path.write_bytes(before)

    result = _run("friction.mode", "warning", "--yes")

    assert result.exit_code == 0, result.output
    assert path.read_bytes() == before.replace(b"  mode: enforcing", b"  mode: warning")


def test_config_set_adds_a_nested_key_the_file_lacks_after_its_siblings(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    path = _write_raw(repo, KEPT)

    assert _run("process.journal.committed", "false", "--yes").exit_code == 0
    assert _run("repository.default-branch", "main", "--yes").exit_code == 0

    assert path.read_text(encoding="utf-8") == (
        KEPT + "    committed: false\nrepository:\n  default-branch: main\n"
    )


def test_writing_a_list_replaces_only_the_lines_of_its_key(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    path = _write_raw(repo, KEPT)

    pc.write_config(
        repo.root,
        lambda data: pc.set_path(data, ("friction", "surface"), ["src/**", "lib/**"]),
        consent=YES,
    )

    # The list keeps its own layout, and the comment after it stays.
    assert path.read_text(encoding="utf-8") == KEPT.replace("  - tests/**\n", "  - lib/**\n")


def test_setting_the_value_already_set_neither_asks_nor_writes(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo()
    path = _write_raw(repo, KEPT)
    written = path.stat().st_mtime_ns
    monkeypatch.setattr(pc, "stdin_is_tty", lambda: False)  # a write would need --yes

    result = _run("friction.mode", "enforcing")

    assert result.exit_code == 0, result.output
    assert "friction.mode is already enforcing; nothing to write." in result.output
    pc.write_config(repo.root, _set("name", "alpha"), consent=NON_INTERACTIVE)
    assert path.read_text(encoding="utf-8") == KEPT
    assert path.stat().st_mtime_ns == written


def test_a_change_the_edit_cannot_make_is_refused_and_nothing_written(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    mixed = "name: alpha\r\ndocs:\n  user: docs/\n"
    path = _config_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(mixed.encode("utf-8"))

    with pytest.raises(pc.UnwritableConfig) as excinfo:
        pc.write_config(repo.root, _set("name", "beta"), consent=YES)

    message = excinfo.value.format_message()
    assert "mixes line endings" in message
    assert "Nothing was written" in message
    assert path.read_bytes() == mixed.encode("utf-8")
