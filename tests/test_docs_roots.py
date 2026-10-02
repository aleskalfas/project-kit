"""Tests for the documentation roots (COR-049): resolution with source,
derivation by precedence, record on first use, no migration, and the status
lines. Every test stands up an adopter repository with the shared fixture."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import agents_overlay as ao
from project_kit import docs_roots as dr
from project_kit import project_config as pc
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

OVERLAY = Path(".pkit") / "agents" / "project" / "overlay.yaml"
YES = pc.Consent(yes=True)


def _write_config(repo: AdopterRepo, text: str) -> None:
    path = pc.project_config_path(repo.root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _set_internal_root(repo: AdopterRepo, root: str) -> None:
    """Change the root the way a project would: through the configuration command."""

    def mutate(data):
        data.setdefault("docs", {})["internal"] = root

    pc.write_config(repo.root, mutate, consent=YES)


def _overlay(repo: AdopterRepo, text: str) -> Path:
    path = repo.root / OVERLAY
    path.write_text(text, encoding="utf-8")
    return path


def _core_agent(repo: AdopterRepo, name: str, *owns: str) -> None:
    lines = ["---", "owns:", *[f"  - {o}" for o in owns], "---", "body", ""]
    (repo.pkit / "agents" / "core" / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")


def _deploy_ok(_root: Path, _name: str) -> bool:
    return True


# --- resolution --------------------------------------------------------------


def test_fresh_adopter_resolves_both_roots_to_docs_by_default(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    # No migration: an absent file means defaults (COR-049 point 1, COR-048 point 3).
    repo = make_adopter_repo()
    assert not pc.project_config_path(repo.root).exists()
    roots = dr.resolve_roots(repo.root)
    assert roots.user == Path("docs")
    assert roots.internal == Path("docs")
    assert roots.user_source is dr.Source.DEFAULT
    assert roots.internal_source is dr.Source.DEFAULT


def test_explicit_roots_carry_their_source(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "docs:\n  internal: tech-docs/\n")
    roots = dr.resolve_roots(repo.root)
    assert (roots.internal, roots.internal_source) == (Path("tech-docs"), dr.Source.EXPLICIT)
    assert (roots.user, roots.user_source) == (Path("docs"), dr.Source.DEFAULT)


def test_unreadable_or_invalid_configuration_yields_defaults(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    # Forgiving read (COR-048 point 4): validation reports it, readers default.
    repo = make_adopter_repo()
    _write_config(repo, "docs: [not\n")
    assert dr.resolve_roots(repo.root).internal_source is dr.Source.DEFAULT
    _write_config(repo, "docs:\n  internal: /absolute\n  user: 42\n")
    roots = dr.resolve_roots(repo.root)
    assert roots.internal_source is dr.Source.DEFAULT
    assert roots.user_source is dr.Source.DEFAULT


# --- derivation --------------------------------------------------------------


def test_derive_location_precedence_explicit_then_root_then_default() -> None:
    explicit = dr.derive_location("tech-docs", "adr-records", explicit="decisions/adr")
    assert explicit == dr.Location(Path("decisions/adr"), dr.Source.EXPLICIT)

    derived = dr.derive_location("tech-docs", "adr-records")
    assert derived == dr.Location(Path("tech-docs/architecture/decisions"), dr.Source.DERIVED)

    default = dr.derive_location(None, "adr-records")
    assert default == dr.Location(Path("docs/architecture/decisions"), dr.Source.DEFAULT)

    # A kind with no conventional sub-path cannot be chosen here.
    assert dr.derive_location("tech-docs", "project-root-docs") is None
    # An explicit value wins even for such a kind.
    explicit = dr.derive_location(None, "anything", explicit="x")
    assert explicit is not None and explicit.source is dr.Source.EXPLICIT


def test_conventional_defaults_equal_the_historical_literals_under_the_default_root(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    literals = {
        "architecture-docs": "docs/architecture",
        "adr-records": "docs/architecture/decisions",
    }
    assert literals == ao.CONVENTIONAL_CATEGORY_DEFAULTS
    assert literals == ao.conventional_category_defaults(repo.root)


def test_conventional_defaults_derive_from_an_explicit_internal_root(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "docs:\n  internal: tech-docs\n")
    assert ao.conventional_category_defaults(repo.root) == {
        "architecture-docs": "tech-docs/architecture",
        "adr-records": "tech-docs/architecture/decisions",
    }


# --- a capability's locations: the one reading (#1051) -----------------------


def _declare_locations(repo: AdopterRepo, capability: str, entries: str) -> None:
    """Append a `docs.locations` block — `entries` are its YAML lines — to an
    installed capability's package metadata."""
    package = repo.pkit / "capabilities" / capability / "package.yaml"
    package.write_text(
        package.read_text(encoding="utf-8") + "docs:\n  locations:\n" + entries,
        encoding="utf-8",
    )


def test_capability_locations_are_read_in_the_package_schema_shape(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A `docs.locations` entry is `{path, root?}`: under the internal root by
    default, under the user root with `root: user`. The old text shape, or any
    other, places no location."""
    repo = make_adopter_repo(capabilities=("project-management",))
    # Today's package metadata declares none.
    assert dr.capability_subpaths(repo.root, "project-management") == {}
    assert dr.capability_subpaths(repo.root, "not-installed") == {}
    _write_config(repo, "docs:\n  internal: tech-docs\n  user: handbook\n")
    _declare_locations(
        repo,
        "project-management",
        "    analysis: {path: analysis}\n"
        "    pages: {path: pages/, root: user, description: The user pages.}\n"
        "    legacy: guides\n"
        "    bare: {root: user}\n"
        "    shared: {path: shared, root: team}\n",
    )
    assert dr.capability_subpaths(repo.root, "project-management") == {
        "analysis": dr.DeclaredLocation(path="analysis", root="internal"),
        "pages": dr.DeclaredLocation(path="pages/", root="user"),
    }

    def location(name: str) -> dr.Location | None:
        return dr.capability_location(repo.root, "project-management", name)

    assert location("analysis") == dr.Location(Path("tech-docs/analysis"), dr.Source.DERIVED)
    assert location("pages") == dr.Location(Path("handbook/pages"), dr.Source.DERIVED)
    assert [location(n) for n in ("legacy", "bare", "shared", "undeclared")] == [None] * 4


def test_the_one_reading_keeps_declaration_order_and_says_why_an_entry_is_not_read() -> None:
    """`read_capability_locations` is pure: callers hand it the parsed files."""
    roots = dr.roots_from({"internal": "tech-docs/", "user": "handbook"})
    package = {
        "docs": {
            "locations": {
                "runs": {"path": "runs"},
                "legacy": "runs",
                "bare": {"root": "user"},
                "shared": {"path": "shared", "root": "team"},
                "pages": {"path": "pages", "root": "user"},
            }
        }
    }
    resolved = dr.read_capability_locations(package, None, roots)
    assert list(resolved) == ["runs", "legacy", "bare", "shared", "pages"]
    assert resolved == {
        "runs": dr.Location(Path("tech-docs/runs"), dr.Source.DERIVED),
        "legacy": dr.UnreadableLocation("is not an object `{path, root?}`"),
        "bare": dr.UnreadableLocation("has no `path` naming a sub-path of its root"),
        "shared": dr.UnreadableLocation("names `root` 'team', not one of ['internal', 'user']"),
        "pages": dr.Location(Path("handbook/pages"), dr.Source.DERIVED),
    }
    # No `docs.locations`, or one that is not a mapping, declares nothing.
    assert dr.read_capability_locations({}, None, roots) == {}
    assert dr.read_capability_locations({"docs": {"locations": ["runs"]}}, None, roots) == {}


def test_a_recorded_location_wins_over_the_declared_one(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """COR-049 point 5: once recorded, a location is read from the record — a
    later root change moves nothing, and a declaration the reading cannot place
    no longer matters. A recorded name the capability does not declare is not
    one of its locations."""
    repo = make_adopter_repo(capabilities=("project-management",))
    _declare_locations(
        repo, "project-management", "    guides: {path: guides}\n    legacy: notes\n"
    )

    def location(name: str) -> dr.Location | None:
        return dr.capability_location(repo.root, "project-management", name)

    assert location("guides") == dr.Location(Path("docs/guides"), dr.Source.DERIVED)
    assert location("legacy") is None
    dr.record_location(repo.root, "project-management", "guides", "docs/guides")
    dr.record_location(repo.root, "project-management", "legacy", "docs/notes")
    dr.record_location(repo.root, "project-management", "orphan", "docs/orphan")
    _set_internal_root(repo, "tech-docs")

    assert location("guides") == dr.Location(Path("docs/guides"), dr.Source.EXPLICIT)
    assert location("legacy") == dr.Location(Path("docs/notes"), dr.Source.EXPLICIT)
    assert location("orphan") is None


# --- reconcile / adopt derive at resolution time ----------------------------


def test_reconcile_auto_fills_from_the_derived_location(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "docs:\n  internal: tech-docs\n")
    _overlay(repo, "workflow-docs:\n  - README.md\n")
    _core_agent(repo, "a", "<adr-records>")
    (repo.root / "tech-docs" / "architecture" / "decisions").mkdir(parents=True)
    # The historical literal directory exists too, and must not be what wins.
    (repo.root / "docs" / "architecture" / "decisions").mkdir(parents=True)

    added, _report = ao.reconcile_overlay(repo.root, write=True)
    assert "adr-records" in added
    text = (repo.root / OVERLAY).read_text(encoding="utf-8")
    assert re.search(r"(?m)^adr-records:\n  - tech-docs/architecture/decisions$", text)
    assert "recorded by `pkit agents reconcile`" in text


def test_adopt_creates_and_records_the_derived_directories(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _write_config(repo, "docs:\n  internal: tech-docs\n")
    _overlay(repo, "workflow-docs:\n  - README.md\n")
    _core_agent(repo, "a", "<adr-records>", "<architecture-docs>")

    result = ao.adopt_agent(repo.root, "a", deploy_fn=_deploy_ok)
    assert set(result.categories_wired) == {"adr-records", "architecture-docs"}
    assert (repo.root / "tech-docs" / "architecture" / "decisions" / "README.md").is_file()
    assert not (repo.root / "docs" / "architecture").exists()
    text = (repo.root / OVERLAY).read_text(encoding="utf-8")
    assert re.search(r"(?m)^adr-records:\n  - tech-docs/architecture/decisions$", text)
    assert re.search(r"(?m)^architecture-docs:\n  - tech-docs/architecture$", text)


# --- record on first use (COR-049 point 5) -----------------------------------


def test_record_location_writes_once_and_never_overwrites(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _overlay(repo, "workflow-docs:\n  - README.md\n")
    written = dr.record_location(
        repo.root, dr.BACKBONE, "adr-records", "docs/architecture/decisions/"
    )
    assert written is not None
    assert written == repo.root / OVERLAY
    text = written.read_text(encoding="utf-8")
    assert re.search(r"(?m)^adr-records:\n  - docs/architecture/decisions$", text)

    # A second recording — even of another path — changes nothing: explicit wins.
    assert dr.record_location(repo.root, dr.BACKBONE, "adr-records", "elsewhere") is None
    assert written.read_text(encoding="utf-8") == text


def test_reading_never_records(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    overlay_before = (repo.root / OVERLAY).read_text(encoding="utf-8")
    dr.resolve_roots(repo.root)
    ao.conventional_category_defaults(repo.root)
    dr.derive_location(dr.resolve_roots(repo.root).internal, "adr-records")
    dr.recorded_locations(repo.root)
    dr.outside_root(repo.root)
    dr.capability_location(repo.root, "project-management", "guides")
    assert (repo.root / OVERLAY).read_text(encoding="utf-8") == overlay_before
    assert not pc.project_config_path(repo.root).exists()
    assert not dr.capability_locations_path(repo.root, "project-management").exists()


def test_record_location_for_a_capability_lands_in_its_project_namespace(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo(capabilities=("project-management",))
    _declare_locations(repo, "project-management", "    guides: {path: guides}\n")
    written = dr.record_location(repo.root, "project-management", "guides", "docs/guides")
    assert written is not None
    assert written == dr.capability_locations_path(repo.root, "project-management")
    assert written.parent == repo.pkit / "capabilities" / "project-management" / "project"
    assert dr.recorded_capability_locations(repo.root, "project-management") == {
        "guides": "docs/guides"
    }
    # The capability's own config file is not touched (its schema is strict):
    # the fixture install leaves it absent, and recording does not create it.
    assert not (written.parent / "config.yaml").exists()

    assert dr.record_location(repo.root, "project-management", "guides", "other") is None
    assert dr.record_location(repo.root, "project-management", "notes", "docs/notes") == written
    assert dr.recorded_capability_locations(repo.root, "project-management") == {
        "guides": "docs/guides",
        "notes": "docs/notes",
    }
    recorded = dr.capability_location(repo.root, "project-management", "guides")
    assert recorded == dr.Location(Path("docs/guides"), dr.Source.EXPLICIT)


def _record_location(*args: str, input: str | None = None) -> tuple[int, str]:
    result = CliRunner().invoke(
        main, ["--color", "never", "docs", "record-location", *args], input=input
    )
    return result.exit_code, result.output


GUIDES_RECORDED_IN = ".pkit/capabilities/project-management/project/docs-locations.yaml"


def _guides(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """An adopter whose project-management declares a `guides` location, under `tech-docs/`."""
    repo = make_adopter_repo(capabilities=("project-management",))
    _write_config(repo, "docs:\n  internal: tech-docs\n")
    _declare_locations(repo, "project-management", "    guides: {path: guides}\n")
    return repo


def test_record_location_records_a_derived_capability_location_once(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """`pkit docs record-location` is the backbone's recording on first use for a
    capability's own script: it writes where the location lies now, once."""
    repo = _guides(make_adopter_repo)
    assert _record_location("project-management", "guides", "--yes") == (
        0,
        f"recorded project-management guides = tech-docs/guides  ({GUIDES_RECORDED_IN})\n",
    )
    assert dr.recorded_capability_locations(repo.root, "project-management") == {
        "guides": "tech-docs/guides"
    }
    # A later root change moves nothing already recorded, and recording again writes
    # nothing — with or without consent, since there is nothing to consent to.
    _set_internal_root(repo, "handbook")
    before = (repo.root / GUIDES_RECORDED_IN).read_text(encoding="utf-8")
    for consent in (("--yes",), ()):
        assert _record_location("project-management", "guides", *consent) == (
            0,
            "project-management guides = tech-docs/guides  (recorded already)\n",
        )
    assert (repo.root / GUIDES_RECORDED_IN).read_text(encoding="utf-8") == before


def test_record_location_writes_only_with_consent(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """COR-048 point 5, as the sibling backbone writers ask it: `--yes`, or a terminal's
    confirmation; a non-interactive run without `--yes` refuses and names the commands."""
    repo = _guides(make_adopter_repo)
    written = dr.capability_locations_path(repo.root, "project-management")
    code, output = _record_location("project-management", "guides")
    assert code == 1
    assert (
        f"refusing to write {GUIDES_RECORDED_IN} without consent: stdin is not a terminal "
        "and --yes was not given (COR-048 point 5). Nothing was written.\n"
        "To see the change first, run:\n"
        "  pkit docs record-location project-management guides --dry-run\n"
        "To consent non-interactively, run:\n"
        "  pkit docs record-location project-management guides --yes\n"
    ) in output
    assert _record_location("project-management", "guides", "--dry-run") == (
        0,
        f"would record project-management guides = tech-docs/guides  ({GUIDES_RECORDED_IN})\n"
        "Dry run: nothing written.\n",
    )
    code, output = _record_location("project-management", "guides", "--yes", "--dry-run")
    assert code == 2
    assert "--yes and --dry-run exclude each other" in output
    assert not written.exists()
    # On a terminal it asks once; declining writes nothing, agreeing records.
    monkeypatch.setattr(pc, "stdin_is_tty", lambda: True)
    code, _output = _record_location("project-management", "guides", input="n\n")
    assert code == 1
    assert not written.exists()
    code, output = _record_location("project-management", "guides", input="y\n")
    assert code == 0, output
    assert output.startswith(
        f"Record project-management guides = tech-docs/guides in {GUIDES_RECORDED_IN}? [Y/n]: y"
    )
    assert dr.recorded_capability_locations(repo.root, "project-management") == {
        "guides": "tech-docs/guides"
    }


def test_record_location_refuses_what_no_installed_capability_declares(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo(capabilities=("project-management",))
    _declare_locations(repo, "project-management", "    guides: {path: guides}\n")
    code, output = _record_location("project-management", "notes", "--yes")
    assert code == 1
    assert "declares no documentation location 'notes'" in output
    assert "(declared: guides)" in output
    code, output = _record_location("living-docs", "definitions", "--yes")
    assert code == 1
    assert "no capability named 'living-docs' is installed" in output
    assert not dr.capability_locations_path(repo.root, "project-management").exists()


def test_a_root_change_after_recording_moves_nothing(make_adopter_repo: MakeAdopterRepo) -> None:
    # COR-049 point 6: recorded locations are explicit; changing a root later
    # affects only locations chosen afterwards.
    repo = make_adopter_repo()
    _overlay(repo, "workflow-docs:\n  - README.md\n")
    _core_agent(repo, "a", "<adr-records>")
    ao.adopt_agent(repo.root, "a", deploy_fn=_deploy_ok)
    recorded = dr.recorded_locations(repo.root)
    assert recorded == [
        dr.RecordedLocation(dr.BACKBONE, "adr-records", Path("docs/architecture/decisions"))
    ]

    _set_internal_root(repo, "tech-docs")
    assert dr.resolve_roots(repo.root).internal == Path("tech-docs")
    # The derived default moved; the recorded choice did not.
    derived = ao.conventional_category_defaults(repo.root)["adr-records"]
    assert derived == "tech-docs/architecture/decisions"
    assert dr.recorded_locations(repo.root) == recorded
    assert (repo.root / "docs" / "architecture" / "decisions").is_dir()
    # It now shows as outside the internal root.
    assert dr.outside_root(repo.root) == recorded
    # And adopt leaves the explicit value alone.
    again = ao.adopt_agent(repo.root, "a", deploy_fn=_deploy_ok)
    assert again.categories_wired == () and again.categories_already_set == ("adr-records",)


def test_existing_explicit_overlay_values_survive_introducing_the_roots(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    # No migration: the seeded overlay's explicit values stay authoritative.
    repo = make_adopter_repo()
    _overlay(repo, "adr-records:\n  - decisions/adr\n")
    _set_internal_root(repo, "tech-docs")
    assert dr.recorded_locations(repo.root) == [
        dr.RecordedLocation(dr.BACKBONE, "adr-records", Path("decisions/adr"))
    ]
    assert dr.derive_location(
        dr.resolve_roots(repo.root).internal, "adr-records", explicit="decisions/adr"
    ) == dr.Location(Path("decisions/adr"), dr.Source.EXPLICIT)


# --- status lines ------------------------------------------------------------


def _status_lines(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")
    result = CliRunner().invoke(main, ["--color", "never", "status"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    start = lines.index("  Documentation")
    end = next(i for i in range(start + 1, len(lines)) if not lines[i].strip())
    return [line.strip() for line in lines[start + 1 : end]]


def test_status_shows_both_roots_with_their_source(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo()
    _overlay(repo, "workflow-docs:\n  - README.md\n")
    assert _status_lines(monkeypatch) == [
        "user root          docs/   (default)",
        "internal root      docs/   (default)",
    ]
    _write_config(repo, "docs:\n  internal: tech-docs\n")
    assert _status_lines(monkeypatch)[1] == "internal root      tech-docs/   (explicit)"


def test_status_lists_every_recorded_location_inside_then_outside_the_internal_root(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo(capabilities=("project-management",))
    _overlay(
        repo,
        "architecture-docs:\n  - CONTRIBUTING.md\n  - docs/architecture\n"
        "adr-records:\n  - decisions/adr\n",
    )
    dr.record_location(repo.root, "project-management", "guides", "docs/guides")
    dr.record_location(repo.root, "project-management", "notes", "elsewhere/notes")
    lines = _status_lines(monkeypatch)
    assert lines[2:] == [
        "inside root        2 recorded location(s) inside the internal root:",
        "architecture-docs -> docs/architecture",
        "guides (project-management) -> docs/guides",
        "outside root       3 recorded location(s) outside the internal root:",
        "adr-records -> decisions/adr",
        "architecture-docs -> CONTRIBUTING.md",
        "notes (project-management) -> elsewhere/notes",
    ]
    # Deterministic: the same state renders the same lines.
    assert _status_lines(monkeypatch) == lines

    # A root change moves nothing recorded; only which side of the root each lies on.
    _set_internal_root(repo, "decisions")
    lines = _status_lines(monkeypatch)
    assert lines[2:4] == [
        "inside root        1 recorded location(s) inside the internal root:",
        "adr-records -> decisions/adr",
    ]
    assert lines[4] == "outside root       4 recorded location(s) outside the internal root:"
    assert "architecture-docs -> docs/architecture" in lines[5:]
    assert "guides (project-management) -> docs/guides" in lines[5:]


def _friction_lines(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")
    result = CliRunner().invoke(main, ["--color", "never", "status"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    start = lines.index("  Friction")
    end = next(i for i in range(start + 1, len(lines)) if not lines[i].strip())
    return [line.strip() for line in lines[start + 1 : end]]


def test_status_says_when_no_place_is_declared(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo()
    assert _friction_lines(monkeypatch) == [
        "mode               warning   (default)",
        "places             none declared",
    ]
    # A mode the reader does not recognise reads as the default; validation reports it.
    _write_config(repo, "friction:\n  mode: loud\n")
    assert _friction_lines(monkeypatch)[0] == "mode               warning   (default)"


def test_status_lists_the_declared_places_surface_and_exclusions(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo(capabilities=("project-management",))
    _write_config(
        repo,
        "docs:\n  internal: tech-docs\n"
        "friction:\n  mode: enforcing\n"
        "  places: [README.md, guides/**/*.md]\n"
        "  exclude: [generated/]\n",
    )
    package = repo.pkit / "capabilities" / "project-management" / "package.yaml"
    package.write_text(
        package.read_text(encoding="utf-8")
        + "docs:\n  locations:\n    boards: {path: boards}\n"
        + "friction:\n  places:\n    - {location: boards, path: '**/*.md'}\n",
        encoding="utf-8",
    )
    assert _friction_lines(monkeypatch) == [
        "mode               enforcing   (explicit)",
        "places             3 declared:",
        "README.md",
        "guides/**/*.md",
        # A capability's place resolves inside its location under the internal
        # root, tagged with its owner.
        "tech-docs/boards/**/*.md (project-management)",
        "exclude            1 declared:",
        "generated/",
    ]


def test_status_shows_a_capability_place_under_its_recorded_location_and_its_surface_as_written(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lines show what discovery reads: the place inside the location the
    project recorded, not the declared one, and the surface repository-relative."""
    repo = make_adopter_repo(capabilities=("project-management",))
    _write_config(repo, "docs:\n  internal: tech-docs\n")
    package = repo.pkit / "capabilities" / "project-management" / "package.yaml"
    package.write_text(
        package.read_text(encoding="utf-8")
        + "docs:\n  locations:\n    boards: {path: boards}\n"
        + "friction:\n  places:\n    - {location: boards, path: '**/*.md'}\n"
        + "  surface: ['src/**']\n",
        encoding="utf-8",
    )
    dr.record_location(repo.root, "project-management", "boards", "planning/boards")
    assert _friction_lines(monkeypatch) == [
        "mode               warning   (default)",
        "places             1 declared:",
        "planning/boards/**/*.md (project-management)",
        "surface            1 declared:",
        "src/** (project-management)",
    ]
