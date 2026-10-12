"""Artefact types (COR-056, #1406): discovery resolves each artefact's type.

A component declares its types in a type registry (`friction.types`) and names
them on its places; the project names types on its own places, written
`{path, type}`. Discovery resolves every artefact's type from the places that
match its file, in COR-056 point 3's order, one test per step:

- every rule is `backbone:rule`;
- a project place yields to a component's place that is not root-wide, typed or
  not;
- a root-wide place comes last;
- the longer literal part wins;
- at equal length an exact file beats a glob, which beats a folder;
- a folder followed by `/**` reads as that folder;
- a tie counts as each type in contention;
- a kind field gates the type, with no fall-through (point 4).

Then one test per validation case the issue lists — what fails, at the member
discovery's one table names (ADR-057 point 2), and what is only reported — the
scope's `paths`, `exclude` and `types`, a list scope selecting as before, and
the artefacts document's new keys at version 1.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import config_validate as cv
from project_kit import friction_discovery as fd
from project_kit import package_validate as pv
from project_kit import rule_sets as rs
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

CONFIG = ".pkit/project/config.yaml"
EVIDENCE = "evidence"
DEMO = "demo-recording"
ROOTS = "docs:\n  user: handbook\n  internal: tech-docs\n"

# The evidence capability's registry: `run` admits project places, `page` asks for
# a kind, `log` is plain. Its places are appended per test.
REGISTRY = (
    "docs:\n"
    "  locations:\n"
    "    runs: {path: evidence}\n"
    "    whole: {path: .}\n"
    "friction:\n"
    "  types:\n"
    "    run: {description: A run., project-places: true}\n"
    "    page: {description: A page., kind-field: kind}\n"
    "    log: {description: A log.}\n"
    "  places:\n"
)

DOCUMENT = "---\ntitle: {title}\n---\n\n# {title}\n"


def _package(name: str) -> str:
    return f".pkit/capabilities/{name}/package.yaml"


def _declares(repo: AdopterRepo, name: str, blocks: str) -> None:
    """Append `docs` / `friction` blocks to an installed capability's package."""
    package = repo.root / _package(name)
    package.write_text(package.read_text(encoding="utf-8") + blocks, encoding="utf-8")


def _places(*entries: str) -> str:
    return "".join(f"    - {entry}\n" for entry in entries)


def _config(*places: str) -> str:
    listed = "".join(f"\n    - {place}" for place in places)
    return f"{ROOTS}friction:\n  places:{listed}\n"


def _files(repo: AdopterRepo, *paths: str) -> None:
    repo.write({path: DOCUMENT.format(title=path) for path in paths})


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo(capabilities=(EVIDENCE, DEMO))


def _document() -> dict[str, Any]:
    result = CliRunner().invoke(main, ["friction", "artefacts", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _types(repo: AdopterRepo) -> dict[str, fd.ArtefactType]:
    """Each artefact's type, by location, from the one resolution."""
    discovery = fd.discover_artefacts(repo.root)
    return {a.location: discovery.types.of(a) for a in discovery.artefacts}


def _type_of(repo: AdopterRepo) -> dict[str, str | None]:
    return {location: resolved.type for location, resolved in _types(repo).items()}


def _patterns(ranked: tuple[fd.RankedPlace, ...]) -> list[tuple[str, int]]:
    return [(r.place.pattern, r.rank) for r in ranked]


def _findings(repo: AdopterRepo) -> list[fd.TypeFinding]:
    return list(fd.discover_artefacts(repo.root).types.findings)


def _config_findings(repo: AdopterRepo) -> dict[str, tuple[cv.Severity, str]]:
    """The configuration pass's findings on the `friction` key, by pointer."""
    report = cv.run_configuration_pass(repo.root)
    return {
        f.path: (f.severity, f.message) for f in report.findings if f.path.startswith("/friction/")
    }


def _package_findings(repo: AdopterRepo, name: str) -> dict[str, tuple[pv.Severity, str]]:
    return {
        finding.path: (finding.severity, finding.message)
        for report in pv.validate_installed_packages(repo.root).reports
        if report.file == repo.root / _package(name)
        for finding in report.findings
    }


# --- the order of places (COR-056 point 3) -----------------------------------------------


def test_a_rule_is_backbone_rule_whatever_place_matches_its_file(repo: AdopterRepo) -> None:
    rules = "tech-docs/rule-sets/cmn.md"
    repo.write(
        {
            CONFIG: _config("{path: tech-docs, type: note}"),
            rules: (
                "---\nrule-set: CMN\nversion: 1.0.0\nrules:\n  RS-CMN-001: {}\n---\n\n"
                "## RS-CMN-001 — A rule\n\nThe statement.\n"
            ),
        }
    )
    _files(repo, "tech-docs/guide.md")
    types = _types(repo)
    rule = types[f"{rules}#RS-CMN-001"]
    assert (rule.type, rule.place, rule.conflict) == (fd.RULE_TYPE, None, ())
    assert fd.RULE_TYPE == "backbone:rule"
    assert types["tech-docs/guide.md"].type == "note"  # the place types what is no rule


def test_a_project_place_yields_to_a_components_place_typed_or_not(repo: AdopterRepo) -> None:
    """The project's places are more specific here, and still give no type where a
    component's own place that is not root-wide matches the file."""
    _declares(
        repo,
        EVIDENCE,
        REGISTRY
        + _places("{location: runs, path: 'typed/**', type: run}", "{location: runs, path: plain}"),
    )
    repo.write(
        {
            CONFIG: _config(
                "{path: tech-docs/evidence/typed/a.md, type: note}",
                "{path: tech-docs/evidence/plain/b.md, type: note}",
                "{path: tech-docs/evidence/c.md, type: note}",
            )
        }
    )
    _files(
        repo,
        "tech-docs/evidence/typed/a.md",
        "tech-docs/evidence/plain/b.md",
        "tech-docs/evidence/c.md",
    )
    types = _types(repo)
    assert types["tech-docs/evidence/typed/a.md"].type == "evidence:run"  # the component's type
    assert types["tech-docs/evidence/plain/b.md"].type is None  # an untyped place keeps it too
    assert types["tech-docs/evidence/c.md"].type == "note"  # no component's place: the project's
    # The project's place that yields comes after every place that does not.
    assert _patterns(types["tech-docs/evidence/typed/a.md"].places) == [
        ("tech-docs/evidence/typed/**", 1),
        ("tech-docs/evidence/typed/a.md", 2),
    ]
    # Reported, not failed, at the project's typed place (the configuration member).
    found = _config_findings(repo)
    for index in (0, 1):
        severity, message = found[f"/friction/places/{index}"]
        assert severity is cv.Severity.REPORT
        assert "yields to evidence's place" in message
    assert "/friction/places/2" not in found


def test_a_root_wide_place_comes_last(repo: AdopterRepo) -> None:
    """A component's root-wide place yields to a typed project place that is not:
    the project types a folder of its own under a root."""
    _declares(repo, EVIDENCE, REGISTRY + _places("{location: whole, path: '**', type: log}"))
    repo.write({CONFIG: _config("{path: 'tech-docs/notes/*.md', type: note}")})
    _files(repo, "tech-docs/notes/x.md", "tech-docs/other.md")
    types = _types(repo)
    assert types["tech-docs/notes/x.md"].type == "note"
    assert _patterns(types["tech-docs/notes/x.md"].places) == [
        ("tech-docs/notes/*.md", 1),
        ("tech-docs/**", 2),
    ]
    assert types["tech-docs/other.md"].type == "evidence:log"
    assert _config_findings(repo) == {}  # no yield: the component's place is root-wide


def test_the_longer_literal_part_wins(repo: AdopterRepo) -> None:
    """Counted in characters, up to the first wildcard: `notes/de*` (8) outranks
    the folder `notes` (`notes/`, 6) and loses to the folder `notes/deep` (11)."""
    repo.write(
        {
            CONFIG: _config(
                "{path: notes, type: broad}",
                "{path: 'notes/de*', type: star}",
                "{path: notes/deep, type: narrow}",
            )
        }
    )
    _files(repo, "notes/deep/x.md", "notes/deck.md", "notes/y.md")
    assert _type_of(repo) == {
        "notes/deck.md": "star",
        "notes/deep/x.md": "narrow",
        "notes/y.md": "broad",
    }


def test_at_equal_length_a_file_beats_a_glob_which_beats_a_folder(repo: AdopterRepo) -> None:
    """`notes/a.md` and `notes/a.md*` share a literal part of ten characters, and
    `notes/*.md` and the folder `notes` one of six."""
    repo.write(
        {
            CONFIG: _config(
                "{path: notes, type: folder}",
                "{path: 'notes/*.md', type: glob}",
                "{path: 'notes/a.md*', type: suffix}",
                "{path: notes/a.md, type: file}",
            )
        }
    )
    _files(repo, "notes/a.md", "notes/b.md")
    types = _types(repo)
    assert types["notes/a.md"].type == "file"
    assert _patterns(types["notes/a.md"].places) == [
        ("notes/a.md", 1),
        ("notes/a.md*", 2),
        ("notes/*.md", 3),
        ("notes", 4),
    ]
    assert types["notes/b.md"].type == "glob"


def test_a_folder_followed_by_double_star_reads_as_that_folder(repo: AdopterRepo) -> None:
    """`notes/**` ranks as `notes`, so two types on them tie, while `notes/**/*.md`
    is a glob and outranks the folder."""
    repo.write({CONFIG: _config("{path: notes, type: plain}", "{path: 'notes/**', type: starred}")})
    _files(repo, "notes/a.md")
    resolved = _types(repo)["notes/a.md"]
    assert _patterns(resolved.places) == [("notes", 1), ("notes/**", 1)]
    assert resolved.type is None and {t for t, _p in resolved.conflict} == {"plain", "starred"}
    repo.write(
        {CONFIG: _config("{path: notes, type: plain}", "{path: 'notes/**/*.md', type: glob}")}
    )
    assert _type_of(repo) == {"notes/a.md": "glob"}


def test_a_tie_counts_as_each_type_in_contention(repo: AdopterRepo) -> None:
    """A tie the project can mend fails at each of its places, and every scope that
    selects one of the tied types still reaches the artefact."""
    repo.write(
        {
            CONFIG: _config("{path: notes, type: plain}", "{path: 'notes/**', type: starred}"),
            "tech-docs/rule-sets/plain.md": _rule_set("PLAIN", "{types: [plain]}"),
            "tech-docs/rule-sets/starred.md": _rule_set("STARRED", "{types: [starred]}"),
            "tech-docs/rule-sets/other.md": _rule_set("OTHER", "{types: [other]}"),
        }
    )
    _files(repo, "notes/a.md")
    resolved = _types(repo)["notes/a.md"]
    assert resolved.counts_as == {"plain", "starred"}
    assert _in_scope_of()["notes/a.md"] == [
        "tech-docs/rule-sets/plain.md",
        "tech-docs/rule-sets/starred.md",
    ]
    found = _config_findings(repo)
    for index in (0, 1):
        severity, message = found[f"/friction/places/{index}"]
        assert severity is cv.Severity.ERROR
        assert "rank equal and give different types on 1 file(s), such as 'notes/a.md'" in message


def test_the_kind_field_gates_the_type_with_no_fall_through(repo: AdopterRepo) -> None:
    """The winning place gives `evidence:page`, which asks for `kind`: a document or
    an entry that declares no kind has no type, and the root-wide place that would
    type it `evidence:log` does not type it instead."""
    _declares(
        repo,
        EVIDENCE,
        REGISTRY
        + _places(
            "{location: runs, path: '**', type: page}", "{location: whole, path: '**', type: log}"
        ),
    )
    repo.write(
        {
            CONFIG: ROOTS,
            "tech-docs/evidence/with.md": "---\nkind: guide\n---\n",
            "tech-docs/evidence/without.md": "---\ntitle: No kind\n---\n",
            "tech-docs/evidence/blank.md": "---\nkind: '  '\n---\n",
            "tech-docs/evidence/entries.md": (
                "---\n"
                "one:\n  kind: term\n  pkit: {friction: {unanchored-because: A word.}}\n"
                "two:\n  meaning: none\n"
                "---\n"
            ),
            "tech-docs/other.md": "---\ntitle: Elsewhere\n---\n",
        }
    )
    assert _type_of(repo) == {
        "tech-docs/evidence/blank.md": None,
        "tech-docs/evidence/entries.md#one": "evidence:page",
        "tech-docs/evidence/entries.md#two": None,
        "tech-docs/evidence/with.md": "evidence:page",
        "tech-docs/evidence/without.md": None,
        "tech-docs/other.md": "evidence:log",
    }


# --- validation: what fails --------------------------------------------------------------


def test_a_project_place_gives_a_components_type_only_when_installed_declared_and_admitted(
    repo: AdopterRepo,
) -> None:
    _declares(repo, EVIDENCE, REGISTRY + _places("{location: runs, path: none}"))
    repo.write(
        {
            CONFIG: _config(
                "{path: a, type: 'ghost:thing'}",
                "{path: b, type: 'evidence:nope'}",
                "{path: c, type: 'evidence:page'}",
                "{path: d, type: 'evidence:run'}",
            )
        }
    )
    _files(repo, "a/x.md", "b/x.md", "c/x.md", "d/x.md")
    found = _config_findings(repo)
    assert {pointer for pointer in found} == {
        "/friction/places/0/type",
        "/friction/places/1/type",
        "/friction/places/2/type",
    }
    assert all(severity is cv.Severity.ERROR for severity, _m in found.values())
    assert "no installed component is named 'ghost'" in found["/friction/places/0/type"][1]
    assert "declares no type 'nope'" in found["/friction/places/1/type"][1]
    assert "does not admit on a project's places" in found["/friction/places/2/type"][1]
    # An unknown component's type gives no type; a declared one still counts.
    assert _type_of(repo) == {
        "a/x.md": None,
        "b/x.md": None,
        "c/x.md": None,  # counts, but `page` asks for a kind this document does not declare
        "d/x.md": "evidence:run",
    }


def test_a_bare_project_type_never_takes_a_declared_types_name(repo: AdopterRepo) -> None:
    _declares(repo, EVIDENCE, REGISTRY + _places("{location: runs, path: none}"))
    repo.write(
        {CONFIG: _config("{path: a, type: run}", "{path: b, type: rule}", "{path: c, type: own}")}
    )
    _files(repo, "a/x.md", "b/x.md", "c/x.md")
    found = _config_findings(repo)
    assert set(found) == {"/friction/places/0/type", "/friction/places/1/type"}
    assert "takes the name of evidence:run" in found["/friction/places/0/type"][1]
    assert "takes the name of backbone:rule" in found["/friction/places/1/type"][1]
    assert all(severity is cv.Severity.ERROR for severity, _m in found.values())
    assert _type_of(repo) == {"a/x.md": "run", "b/x.md": "rule", "c/x.md": "own"}


def test_the_configuration_schema_refuses_a_backbone_type_on_a_place(repo: AdopterRepo) -> None:
    """No place may name one of the backbone's types (COR-056 point 2): the schema
    refuses it, and a refused value gives no type."""
    repo.write({CONFIG: _config("{path: a, type: 'backbone:rule'}", "{path: b, type: 'a/b'}")})
    _files(repo, "a/x.md", "b/x.md")
    found = _config_findings(repo)
    assert set(found) == {"/friction/places/0/type", "/friction/places/1/type"}
    assert all(severity is cv.Severity.ERROR for severity, _m in found.values())
    assert _type_of(repo) == {"a/x.md": None, "b/x.md": None}


def test_a_typed_places_path_is_judged_once_at_its_path(repo: AdopterRepo) -> None:
    """One finding per mistake: a path the shape pass refuses is not judged again,
    and a typed place's pattern findings stand at its `path`."""
    repo.write({CONFIG: _config("{path: /abs, type: own}", "{path: nowhere, type: own}", "/bare")})
    found = _config_findings(repo)
    assert set(found) == {
        "/friction/places/0/path",
        "/friction/places/1/path",
        "/friction/places/2",
    }
    assert found["/friction/places/0/path"][0] is cv.Severity.ERROR  # the schema's refusal
    assert found["/friction/places/1/path"] == (
        cv.Severity.WARNING,
        "friction pattern 'nowhere' matches nothing in the repository; a dead pattern keeps "
        "silence looking like health (COR-050 point 12).",
    )


def test_a_scope_naming_a_type_no_owner_declares_fails(repo: AdopterRepo) -> None:
    _declares(repo, EVIDENCE, REGISTRY + _places("{location: runs, path: none}"))
    rules = "tech-docs/rule-sets/cmn.md"
    repo.write(
        {
            CONFIG: _config("{path: notes, type: own}"),
            rules: _rule_set(
                "CMN",
                "{types: ['evidence:run', 'backbone:rule', own, 'evidence:nope', "
                "'ghost:thing', 'backbone:nope', missing]}",
            ),
        }
    )
    result = rs.validate_rule_sets(repo.root)
    unknown = {
        f.pointer: f.message
        for f in result.findings
        if f.kind is rs.RuleSetFindingKind.UNKNOWN_SCOPE_TYPE
    }
    assert set(unknown) == {"/scope/types/3", "/scope/types/4", "/scope/types/5", "/scope/types/6"}
    assert all(
        f.severity is rs.Severity.ERROR
        for f in result.findings
        if f.kind is rs.RuleSetFindingKind.UNKNOWN_SCOPE_TYPE
    )
    assert "evidence's type registry declares no type 'nope'" in unknown["/scope/types/3"]
    assert "no installed component is named 'ghost'" in unknown["/scope/types/4"]
    assert "the backbone declares no type 'nope'" in unknown["/scope/types/5"]
    assert "no place of the project gives it" in unknown["/scope/types/6"]


def test_a_method_rule_sets_scope_fails(repo: AdopterRepo) -> None:
    method = ".pkit/capabilities/evidence/rule-sets/ev.md"
    repo.write({CONFIG: ROOTS, method: _rule_set("EV", "[handbook]")})
    result = rs.validate_rule_sets(repo.root)
    found = [f for f in result.findings if f.kind is rs.RuleSetFindingKind.METHOD_SCOPE]
    assert [(f.location, f.pointer, f.severity) for f in found] == [
        (method, "/scope", rs.Severity.ERROR)
    ]


# --- validation: what is reported ----------------------------------------------------------


def test_a_tie_between_components_places_is_reported(repo: AdopterRepo) -> None:
    _declares(
        repo, EVIDENCE, REGISTRY + _places("{location: runs, path: 'shared/*.md', type: run}")
    )
    _declares(
        repo,
        DEMO,
        "friction:\n  types:\n    clip: {description: A clip.}\n"
        "  places:\n    - {path: 'tech-docs/evidence/shared/*.md', type: clip}\n",
    )
    repo.write({CONFIG: ROOTS})
    _files(repo, "tech-docs/evidence/shared/x.md")
    resolved = _types(repo)["tech-docs/evidence/shared/x.md"]
    assert resolved.type is None and resolved.counts_as == {"evidence:run", "demo-recording:clip"}
    for name in (EVIDENCE, DEMO):
        severity, message = _package_findings(repo, name)["/friction/places/0"]
        assert severity is pv.Severity.REPORT
        assert "rank equal" in message and "the project cannot mend it" in message
    assert _config_findings(repo) == {}


def test_one_components_typed_place_over_anothers_is_reported(repo: AdopterRepo) -> None:
    _declares(repo, EVIDENCE, REGISTRY + _places("{location: runs, path: 'deep/*.md', type: run}"))
    _declares(repo, DEMO, "friction:\n  places:\n    - {path: tech-docs/evidence}\n")
    repo.write({CONFIG: ROOTS})
    _files(repo, "tech-docs/evidence/deep/x.md")
    assert _type_of(repo) == {"tech-docs/evidence/deep/x.md": "evidence:run"}  # the type stands
    severity, message = _package_findings(repo, EVIDENCE)["/friction/places/0"]
    assert severity is pv.Severity.REPORT
    assert "takes precedence over demo-recording's place 'tech-docs/evidence'" in message
    assert "/friction/places/0" not in _package_findings(repo, DEMO)


def test_a_components_place_naming_a_type_its_registry_lacks_is_reported(
    repo: AdopterRepo,
) -> None:
    _declares(repo, EVIDENCE, REGISTRY + _places("{location: runs, path: odd, type: missing}"))
    repo.write({CONFIG: ROOTS})
    _files(repo, "tech-docs/evidence/odd/x.md")
    severity, message = _package_findings(repo, EVIDENCE)["/friction/places/0/type"]
    assert severity is pv.Severity.REPORT
    assert "does not declare, so it gives no type" in message
    assert _type_of(repo) == {"tech-docs/evidence/odd/x.md": None}
    assert not pv.validate_installed_packages(repo.root).errors


def test_each_type_finding_has_one_member_and_severity() -> None:
    """The one table (ADR-057 point 2): what COR-056 fails is an error, what it
    reports a report, each at the member that validates the declaration."""
    table = {
        kind: (member, severity.value) for kind, (member, severity) in fd.TYPE_FINDINGS.items()
    }
    assert table == {
        fd.TypeFindingKind.NOT_ADMITTED: ("configuration", "error"),
        fd.TypeFindingKind.NAME_TAKEN: ("configuration", "error"),
        fd.TypeFindingKind.TIE: ("configuration", "error"),
        fd.TypeFindingKind.YIELDS: ("configuration", "report"),
        fd.TypeFindingKind.COMPONENT_TIE: ("packages", "report"),
        fd.TypeFindingKind.OUTRANKS: ("packages", "report"),
        fd.TypeFindingKind.UNDECLARED: ("packages", "report"),
        fd.TypeFindingKind.SCOPE_UNKNOWN: ("rule-sets", "error"),
    }


# --- the scope: paths, exclude and types (COR-051 point 2) ----------------------------------


def _rule_set(name: str, scope: str | None = None) -> str:
    scope_line = "" if scope is None else f"scope: {scope}\n"
    return f"---\nrule-set: {name}\nversion: 1.0.0\n{scope_line}rules: {{}}\n---\n"


def _in_scope_of() -> dict[str, list[str]]:
    document = _document()
    assert document["schema_version"] == 1
    return {a["location"]: a["in_scope_of"] for a in document["artefacts"]}


def test_a_list_scope_selects_as_it_did_and_a_mapping_adds_exclude_and_types(
    repo: AdopterRepo,
) -> None:
    repo.write(
        {
            CONFIG: _config("{path: notes/typed, type: own}", "notes"),
            "tech-docs/rule-sets/list.md": _rule_set("LIST", "[notes]"),
            "tech-docs/rule-sets/paths.md": _rule_set("PATHS", "{paths: [notes]}"),
            "tech-docs/rule-sets/less.md": _rule_set(
                "LESS", "{paths: [notes], exclude: ['notes/typed/**']}"
            ),
            "tech-docs/rule-sets/typed.md": _rule_set("TYPED", "{types: [own]}"),
            "tech-docs/rule-sets/both.md": _rule_set("BOTH", "{paths: [notes/y.md], types: [own]}"),
        }
    )
    _files(repo, "notes/typed/x.md", "notes/y.md")
    assert _in_scope_of() == {
        "notes/typed/x.md": [
            "tech-docs/rule-sets/list.md",
            "tech-docs/rule-sets/paths.md",
            "tech-docs/rule-sets/typed.md",
        ],
        "notes/y.md": [
            "tech-docs/rule-sets/less.md",
            "tech-docs/rule-sets/list.md",
            "tech-docs/rule-sets/paths.md",
        ],
    }
    assert not rs.validate_rule_sets(repo.root).errors


def test_a_scope_the_schema_refuses_is_a_shape_finding(repo: AdopterRepo) -> None:
    """A mapping with neither `paths` nor `types`, an empty list, or an unknown key."""
    repo.write(
        {
            CONFIG: ROOTS,
            "tech-docs/rule-sets/a.md": _rule_set("A", "{exclude: [notes]}"),
            "tech-docs/rule-sets/b.md": _rule_set("B", "{paths: []}"),
            "tech-docs/rule-sets/c.md": _rule_set("C", "{paths: [notes], type: [x]}"),
        }
    )
    shape = {
        (f.location, f.pointer)
        for f in rs.validate_rule_sets(repo.root).errors
        if f.kind in (rs.RuleSetFindingKind.SHAPE, rs.RuleSetFindingKind.UNKNOWN_KEY)
    }
    assert shape == {
        ("tech-docs/rule-sets/a.md", "/scope"),
        ("tech-docs/rule-sets/b.md", "/scope/paths"),
        ("tech-docs/rule-sets/c.md", "/scope/type"),
    }


# --- the artefacts document (COR-056 point 6) ---------------------------------------------


def test_the_document_gives_each_artefact_its_type_and_lists_the_registries(
    repo: AdopterRepo,
) -> None:
    _declares(repo, EVIDENCE, REGISTRY + _places("{location: runs, path: '**', type: run}"))
    repo.write(
        {CONFIG: _config("{path: tech-docs/evidence, type: own}", "{path: notes, type: own}")}
    )
    _files(repo, "tech-docs/evidence/a.md", "notes/b.md")
    document = _document()
    assert document["schema_version"] == 1  # keys added within the version
    places = document["places"]
    assert [(p["written"], p["type"]) for p in places] == [
        ("tech-docs/evidence", "own"),
        ("notes", "own"),
        ("**", "evidence:run"),
    ]
    artefacts = {a["location"]: a for a in document["artefacts"]}
    run = artefacts["tech-docs/evidence/a.md"]
    assert (run["type"], run["type_place"], run["type_conflict"]) == ("evidence:run", 2, [])
    assert run["ranked_places"] == [{"place": 2, "rank": 1}, {"place": 0, "rank": 2}]
    assert artefacts["notes/b.md"]["type"] == "own"
    assert document["types"]["backbone:rule"] == {
        "component": "backbone",
        "name": "rule",
        "description": "A rule: one entry of a rule-set file (COR-051 point 2).",
        "kind_field": None,
        "project_places": False,
    }
    assert document["types"]["evidence:page"]["kind_field"] == "kind"
    assert document["types"]["evidence:run"]["project_places"] is True
    assert set(document["types"]) == {
        "backbone:rule",
        "evidence:run",
        "evidence:page",
        "evidence:log",
    }


# --- the schemas -------------------------------------------------------------------------


def test_the_package_schema_takes_a_type_registry_and_a_places_type(repo: AdopterRepo) -> None:
    _declares(
        repo,
        EVIDENCE,
        "friction:\n"
        "  types:\n"
        "    Bad: {description: Not a name.}\n"
        "    bare: {}\n"
        "    inner: {description: Its kind in the container., kind-field: pkit}\n"
        "    page: {description: A page., kind-field: kind, project-places: true}\n"
        "  places:\n"
        "    - {path: notes, type: 'other:page'}\n"
        "    - {path: notes, type: page}\n",
    )
    repo.write({CONFIG: ROOTS})
    errors = {
        pointer
        for pointer, (severity, _message) in _package_findings(repo, EVIDENCE).items()
        if severity is pv.Severity.ERROR
    }
    assert errors == {
        "/friction/types",
        "/friction/types/bare",
        "/friction/types/inner/kind-field",
        "/friction/places/0/type",
    }
    # Read forgivingly: a name or a kind field the schema refuses declares no type,
    # since a type read without its kind field would type every document it reaches.
    settings = fd.read_friction_settings(repo.root)
    assert [t.type for t in settings.types] == ["evidence:bare", "evidence:page"]
