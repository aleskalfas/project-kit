"""The one project rule set a capability declares, which its install creates (COR-017).

Installing a capability that declares a set creates it once for that install, in
`rule-sets/` under the internal documentation root, inheriting the capability's
method set at its major — only where no set of the project's own inherits that
method set, directly or not, and never over a file, under a name another set
declares, or while a project rule-set file cannot be read. Sync, a later install
and an upgrade never write it again. Uninstall counts it as a reference.
`pkit capabilities project-rule-set` gives the same answer, for the migration of
an earlier install to read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from project_kit import capabilities as caps
from project_kit import declared_rule_sets as drs
from project_kit import install as install_mod
from project_kit import rule_sets as rs
from project_kit import sync as sync_mod
from project_kit.cli import main
from project_kit.manifest import read_kit_version
from tests.adopter_repo import GitRepo, MakeAdopterRepo

_PROJECTS_VERSION = read_kit_version(install_mod.find_source_kit())

NAME = "demo"
CREATED = "docs/rule-sets/ours.md"

METHOD_SET = """\
---
rule-set: MTH
version: {version}
rules: {{}}
---

# MTH — the demo method
"""

PACKAGE = """\
schema_version: 1
component:
  kind: capability
  name: {name}
  version: {version}
description: A capability that declares a project rule set.
requires_backbone: ">=0.1.0,<99.0.0"
friction:
  types:
    page:
      description: A page.
    note:
      description: A note.
{declaration}"""

DECLARATION = """\
project_rule_set:
  name: OURS
  inherits: MTH
  scope:
    types: [demo:page, demo:note]
  title: The project's rules for its pages
"""


def _stage(
    source: Path,
    *,
    version: str = "0.1.0",
    method_version: str = "2.3.0",
    declaration: str = DECLARATION,
) -> Path:
    """The demo capability in the source kit: a method set, MTH, and a declared set, OURS."""
    cap = source / "capabilities" / NAME
    (cap / "rule-sets").mkdir(parents=True, exist_ok=True)
    (cap / "package.yaml").write_text(
        PACKAGE.format(name=NAME, version=version, declaration=declaration), encoding="utf-8"
    )
    (cap / "README.md").write_text(f"# {NAME}\n", encoding="utf-8")
    (cap / "rule-sets" / "mth.md").write_text(
        METHOD_SET.format(version=method_version), encoding="utf-8"
    )
    return cap


@pytest.fixture
def target(make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")
    return make_adopter_repo().root


@pytest.fixture
def source(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A source kit at the project's version, so sync's guard lets install run."""
    kit = tmp_path_factory.mktemp("kit-source")
    (kit / "decisions").mkdir()
    (kit / "VERSION").write_text(f"{_PROJECTS_VERSION}\n", encoding="utf-8")
    from project_kit import cli as cli_mod

    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: kit)
    monkeypatch.setattr(install_mod, "find_source_kit", lambda: kit)
    return kit


def _cli(*args: str) -> Result:
    return CliRunner().invoke(main, list(args))


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _project_set(name: str, inherits: str, scope: str = "paths: [docs/**]") -> str:
    return (
        f"---\nrule-set: {name}\nversion: 1.0.0\ninherits: {inherits}\n"
        f"scope: {{{scope}}}\nrules: {{}}\n---\n\n# {name}\n"
    )


# --- install creates the set ---------------------------------------------------


def test_install_creates_the_declared_set_pinned_at_the_method_set_s_major(
    target: Path, source: Path
) -> None:
    _stage(source)

    result = _cli("capabilities", "install", NAME)

    assert result.exit_code == 0, result.output
    assert f"created the project rule set OURS at {CREATED}, inheriting demo:MTH@2" in result.output
    text = (target / CREATED).read_text(encoding="utf-8")
    assert text.startswith(
        "---\nrule-set: OURS\nversion: 1.0.0\ninherits: [demo:MTH@2]\n"
        "scope:\n  types: [demo:page, demo:note]\nrules: {}\n---\n"
    )
    assert "# OURS — The project's rules for its pages" in text
    # The backbone reads it as a project rule set of its own, inheriting the method set.
    discovery = rs.discover_rule_sets(target)
    created = [s for s in discovery.rule_sets if s.path == CREATED]
    assert len(created) == 1 and created[0].component is None
    assert [s.path for s in rs.inheritors(discovery, NAME, "MTH")] == [CREATED]
    findings = [f for f in rs.validate_rule_sets(target).findings if f.location.startswith(CREATED)]
    assert [f for f in findings if f.severity is rs.Severity.ERROR] == []


def test_install_creates_it_under_the_internal_documentation_root(
    target: Path, source: Path
) -> None:
    _stage(source)
    _write(target, ".pkit/project/config.yaml", "docs:\n  internal: tech-docs/\n")

    result = _cli("capabilities", "install", NAME)

    assert result.exit_code == 0, result.output
    assert (target / "tech-docs" / "rule-sets" / "ours.md").is_file()


def test_install_dry_run_says_what_it_would_create_and_writes_nothing(
    target: Path, source: Path
) -> None:
    _stage(source)

    result = _cli("capabilities", "install", NAME, "--dry-run")

    assert result.exit_code == 0, result.output
    assert f"would create the project rule set OURS at {CREATED}" in result.output
    assert not (target / CREATED).exists()


def test_a_capability_that_declares_no_set_creates_none(target: Path, source: Path) -> None:
    _stage(source, declaration="")

    result = _cli("capabilities", "install", NAME)

    assert result.exit_code == 0, result.output
    assert "project rule set" not in result.output
    assert not (target / "docs" / "rule-sets").exists()


# --- where a set of the project's own inherits the method set ---------------------


def test_install_leaves_a_set_that_inherits_the_method_set_alone(
    target: Path, source: Path
) -> None:
    _stage(source)
    own = _write(target, "docs/rule-sets/mine.md", _project_set("MINE", "[demo:MTH@1]"))
    before = own.read_bytes()

    result = _cli("capabilities", "install", NAME)

    assert result.exit_code == 0, result.output
    assert (
        "no project rule set created: docs/rule-sets/mine.md inherits demo:MTH already"
        in result.output
    )
    assert not (target / CREATED).exists()
    assert own.read_bytes() == before


def test_install_leaves_a_set_that_inherits_it_through_another_set_alone(
    target: Path, source: Path
) -> None:
    """Directly or not: OUTER inherits SHARED, a set of no scope, which inherits MTH."""
    _stage(source)
    _write(
        target,
        "docs/rule-sets/shared.md",
        "---\nrule-set: SHARED\nversion: 1.0.0\ninherits: [demo:MTH@2]\nrules: {}\n---\n\n"
        "# SHARED\n",
    )
    _write(target, "docs/rule-sets/outer.md", _project_set("OUTER", "[SHARED@1]"))

    result = _cli("capabilities", "install", NAME)

    assert result.exit_code == 0, result.output
    assert not (target / CREATED).exists()
    assert "inherits demo:MTH already" in result.output


def test_the_inheritors_are_found_through_a_component_s_method_set(target: Path) -> None:
    """A project set inheriting another component's method set that inherits the named set."""
    for name, text in (
        ("first", "---\nrule-set: FIRST\nversion: 1.0.0\nrules: {}\n---\n\n# FIRST\n"),
        (
            "second",
            "---\nrule-set: SECOND\nversion: 1.0.0\ninherits: [first:FIRST@1]\nrules: {}\n"
            "---\n\n# SECOND\n",
        ),
    ):
        cap = target / ".pkit" / "capabilities" / name
        _write(cap, "rule-sets/set.md", text)
        _write(
            cap,
            "package.yaml",
            PACKAGE.format(name=name, version="0.1.0", declaration=""),
        )
        source = caps.find_capability_in_repo(target, name)
        assert source is not None
        caps.register_incubated_capability(target, source)
    _write(target, "docs/rule-sets/mine.md", _project_set("MINE", "[second:SECOND@1]"))
    _write(target, "docs/rule-sets/other.md", _project_set("OTHER", "[MINE@1]"))
    _write(target, "docs/rule-sets/apart.md", _project_set("APART", "[]"))

    discovery = rs.discover_rule_sets(target)

    assert [s.path for s in rs.inheritors(discovery, "first", "FIRST")] == [
        "docs/rule-sets/mine.md",
        "docs/rule-sets/other.md",
    ]
    assert rs.inheritors(discovery, "first", "NONE") == ()


# --- what stops the creation ---------------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "text", "why"),
    [
        (
            "docs/rule-sets/taken.md",
            _project_set("OURS", "[]"),
            "rule set OURS is declared already, by docs/rule-sets/taken.md",
        ),
        (
            CREATED,
            _project_set("ELSE", "[]"),
            f"{CREATED} exists already, and install never writes over a file",
        ),
        (
            "docs/rule-sets/broken.md",
            "no front matter here\n",
            "docs/rule-sets/broken.md cannot be read as a rule set, so whether it inherits "
            "demo:MTH cannot be told",
        ),
    ],
    ids=["name-taken", "file-exists", "unreadable-set"],
)
def test_install_creates_no_set_where_it_cannot_and_says_why(
    target: Path, source: Path, rel: str, text: str, why: str
) -> None:
    _stage(source)
    blocker = _write(target, rel, text)
    before = blocker.read_bytes()

    result = _cli("capabilities", "install", NAME)

    assert result.exit_code == 0, result.output
    assert f"warning: no project rule set created: {why}" in result.output
    assert "inherits demo:MTH@2 makes its rules bind" in result.output
    assert blocker.read_bytes() == before
    assert caps.is_installed(target, NAME)


def test_install_writes_nothing_through_a_link(
    target: Path, source: Path, tmp_path_factory
) -> None:
    _stage(source)
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    (target / "docs").mkdir(exist_ok=True)
    (target / "docs" / "rule-sets").symlink_to(elsewhere, target_is_directory=True)

    result = _cli("capabilities", "install", NAME)

    assert result.exit_code == 0, result.output
    assert "docs/rule-sets is a link, and install writes nothing through one" in result.output
    assert list(elsewhere.iterdir()) == []


def test_register_creates_no_set(target: Path, source: Path) -> None:
    """Only install creates it: registering a capability authored in the project is no
    install (COR-001 names no other writer)."""
    cap = target / ".pkit" / "capabilities" / NAME
    _stage(target / ".pkit", version="0.1.0")
    assert cap.is_dir()

    result = _cli("capabilities", "register", NAME)

    assert result.exit_code == 0, result.output
    assert not (target / CREATED).exists()


# --- created once, for each install -----------------------------------------------------


def test_sync_a_later_install_and_an_upgrade_never_write_the_set_again(
    target: Path, source: Path
) -> None:
    _stage(source)
    assert _cli("capabilities", "install", NAME).exit_code == 0
    created = target / CREATED
    edited = created.read_text(encoding="utf-8") + "\nThe project's own words.\n"
    created.write_text(edited, encoding="utf-8")

    sync_mod.run_sync(target)
    assert created.read_text(encoding="utf-8") == edited

    again = _cli("capabilities", "install", NAME)
    assert again.exit_code != 0
    assert created.read_text(encoding="utf-8") == edited

    _stage(source, version="0.2.0", method_version="3.0.0")
    upgraded = _cli("capabilities", "upgrade", NAME)
    assert upgraded.exit_code == 0, upgraded.output
    assert created.read_text(encoding="utf-8") == edited

    # Removed on purpose, it stays removed while the capability stays installed.
    created.unlink()
    sync_mod.run_sync(target)
    _stage(source, version="0.3.0", method_version="3.0.0")
    assert _cli("capabilities", "upgrade", NAME).exit_code == 0
    assert not created.exists()


# --- uninstall counts it as a reference ---------------------------------------------------


@pytest.mark.parametrize(
    "inherits",
    ["[demo:MTH@2]", "[OTHER@1, demo:MTH@2]", "\n  - demo:MTH@2"],
    ids=["flow", "second-parent", "block"],
)
def test_uninstall_refuses_a_set_that_inherits_the_capability_s_method_set(
    target: Path, source: Path, inherits: str
) -> None:
    _stage(source, declaration="")
    assert _cli("capabilities", "install", NAME).exit_code == 0
    _write(
        target,
        "docs/rule-sets/mine.md",
        f"---\nrule-set: MINE\nversion: 1.0.0\ninherits: {inherits}\nscope:\n  paths: [docs/**]\n"
        "rules: {}\n---\n\n# MINE\n",
    )
    GitRepo(target).commit("the project's set")

    refused = _cli("capabilities", "uninstall", NAME)

    assert refused.exit_code != 0
    assert "docs/rule-sets/mine.md: inherits demo:MTH@2" in refused.output
    assert caps.is_installed(target, NAME)
    forced = _cli("capabilities", "uninstall", NAME, "--force")
    assert forced.exit_code == 0, forced.output
    assert not caps.is_installed(target, NAME)
    assert (target / "docs" / "rule-sets" / "mine.md").is_file()


def test_uninstall_refuses_while_the_created_set_stands(target: Path, source: Path) -> None:
    _stage(source)
    assert _cli("capabilities", "install", NAME).exit_code == 0

    refused = _cli("capabilities", "uninstall", NAME)

    assert refused.exit_code != 0
    assert f"{CREATED}: inherits demo:MTH@2" in refused.output


# --- the reading a migration takes ------------------------------------------------------------


def test_the_reading_says_install_would_create_it_with_the_text(target: Path, source: Path) -> None:
    _stage(source, declaration="")
    assert _cli("capabilities", "install", NAME).exit_code == 0
    # The installed copy gains the declaration, as an upgrade's copy brings it.
    _stage(target / ".pkit")

    result = _cli("capabilities", "project-rule-set", NAME, "--json")

    assert result.exit_code == 0, result.output
    document = json.loads(result.output)
    assert document["declared"] is True and document["creates"] is True
    assert document["path"] == CREATED and document["pin"] == "demo:MTH@2"
    assert document["inherited_by"] == [] and document["blocked"] is None
    planned = drs.plan(target, NAME, target / ".pkit" / "capabilities" / NAME)
    assert planned is not None and document["text"] == planned.text
    assert not (target / CREATED).exists()


def test_the_reading_names_the_set_that_inherits_it(target: Path, source: Path) -> None:
    _stage(source)
    assert _cli("capabilities", "install", NAME).exit_code == 0

    result = _cli("capabilities", "project-rule-set", NAME, "--json")
    text = _cli("capabilities", "project-rule-set", NAME)

    document = json.loads(result.output)
    assert document["creates"] is False and document["text"] is None
    assert document["inherited_by"] == [CREATED]
    assert f"inherited by: {CREATED}, so install creates none" in text.output


def test_the_reading_refuses_a_capability_not_installed(target: Path, source: Path) -> None:
    _stage(source)

    result = _cli("capabilities", "project-rule-set", NAME)

    assert result.exit_code == 1
    assert "is not installed" in result.output


def test_create_never_writes_over_a_file(target: Path, source: Path) -> None:
    cap = _stage(source)
    planned = drs.plan(target, NAME, cap)
    assert planned is not None and planned.creates
    _write(target, CREATED, "the project's\n")

    with pytest.raises(FileExistsError):
        drs.create(target, planned)
    assert (target / CREATED).read_text(encoding="utf-8") == "the project's\n"
