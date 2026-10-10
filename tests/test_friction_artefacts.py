"""`pkit friction artefacts`: the one discovery, as a document a script reads (#1099).

Artefact discovery (`friction_discovery`) is the one home of where artefacts
are (ADR-057 point 2); this is its reading command, which a capability's script
calls instead of re-reading the declarations or walking the places itself:

- the **places**, the project's and each capability's — with the location and
  root a capability place names — each with the files it matches and the skips
  validation applies: a synced copy, a place outside the repository, a
  malformed declaration;
- every **file** the walk read, with the places matching it, its rule-set
  claim, whether it is excluded, and its front matter's own fields;
- every **artefact**, with its id, kind, place and own fields — an entry with
  the span of its section, exactly the text friction compares, and each
  artefact with the rule sets whose scope covers it (#1361);
- every **folder of held documents**, declared as a place is, and every file it
  holds, with the places that left it out — never a file or an artefact of any
  place (#1130);
- the exit codes: 0 answered, 1 when the configuration cannot be read, 2 on a
  usage error — and the same bytes for the same state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import friction_discovery as fd
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

CONFIG = ".pkit/project/config.yaml"
EVIDENCE_PACKAGE = ".pkit/capabilities/evidence/package.yaml"
EVIDENCE_README = ".pkit/capabilities/evidence/README.md"

ANCHORED = """---
id: {id}
reader: user
kind: signpost
pkit:
  friction:
    anchors:
      path: [src/**]
---

# {id}
"""

COLLECTION = """---
title: Common rules
RS-CMN-001:
  status: accepted
  pkit:
    friction:
      anchors: {path: [src/**]}
---
# Common rules

## RS-CMN-001 — Name things
"""


# A collection whose sections open after blank lines: one with a sub-heading and
# blank lines after it, one last in the file with no line break at its end, and
# an entry with no section of its own.
SECTIONED = """---
title: Terms
term-a:
  pkit:
    friction:
      anchors: {path: [src/**]}
term-b:
  pkit:
    friction:
      anchors: {path: [src/**]}
term-c:
  meaning: no section of its own
---


# Terms

## term-a — First

The first term.

### term-a detail

More of it.


## term-b: Second

The second term, last in the file"""

TERMS = "notes/terms.md"


def _run(*args: str) -> Any:
    return CliRunner().invoke(main, ["friction", "artefacts", *args])


def _document() -> dict[str, Any]:
    result = _run("--json")
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _evidence_declares(adopter: AdopterRepo, blocks: str) -> None:
    package = adopter.root / EVIDENCE_PACKAGE
    package.write_text(package.read_text(encoding="utf-8") + blocks, encoding="utf-8")


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """Project places and a capability's, a document, a collection, a plain file and
    an excluded one."""
    repo = make_adopter_repo(capabilities=("evidence",))
    _evidence_declares(
        repo,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "    guides: {path: guides, root: user}\n"
        "friction:\n"
        "  places:\n"
        "    - {location: runs, path: '**/*.md'}\n"
        "    - {location: guides, path: '*.md'}\n",
    )
    repo.write(
        {
            CONFIG: (
                "docs:\n  user: handbook\n  internal: tech-docs\n"
                "friction:\n  places: [notes, notes/rules.md]\n  exclude: [notes/old.md]\n"
            ),
            "notes/guide.md": ANCHORED.format(id="guide"),
            "notes/rules.md": COLLECTION,
            "notes/plain.md": "# No front matter\n",
            "notes/old.md": "# Excluded\n",
            "tech-docs/evidence/run.md": ANCHORED.format(id="run"),
            "handbook/guides/start.md": ANCHORED.format(id="start"),
        }
    )
    return repo


# --- the places ------------------------------------------------------------------------


def test_the_places_are_the_project_s_then_each_capability_s_with_their_location(
    adopter: AdopterRepo,
) -> None:
    document = _document()
    assert document["schema_version"] == fd.ARTEFACTS_SCHEMA_VERSION
    assert document["roots"] == {"internal": "tech-docs", "user": "handbook"}
    places = document["places"]
    assert [(p["source"], p["pointer"], p["written"], p["path"]) for p in places] == [
        ("project", "/friction/places/0", "notes", "notes"),
        ("project", "/friction/places/1", "notes/rules.md", "notes/rules.md"),
        ("capability:evidence", "/friction/places/0", "**/*.md", "tech-docs/evidence/**/*.md"),
        ("capability:evidence", "/friction/places/1", "*.md", "handbook/guides/*.md"),
    ]
    assert [p["file"] for p in places] == [CONFIG, CONFIG, EVIDENCE_PACKAGE, EVIDENCE_PACKAGE]
    assert [p["location"] for p in places] == [
        None,
        None,
        {"name": "runs", "path": "tech-docs/evidence", "root": "internal"},
        {"name": "guides", "path": "handbook/guides", "root": "user"},
    ]
    assert all(p["declared"] and p["skipped"] is None for p in places)
    # Every file a place matches, however many places match it.
    assert places[0]["files"] == [
        "notes/guide.md",
        "notes/old.md",
        "notes/plain.md",
        "notes/rules.md",
    ]
    assert places[1]["files"] == ["notes/rules.md"]
    assert places[2]["files"] == ["tech-docs/evidence/run.md"]
    assert places[3]["files"] == ["handbook/guides/start.md"]


def test_a_place_encloses_a_root_only_when_it_reaches_every_document_in_it(
    adopter: AdopterRepo,
) -> None:
    places = "[handbook, 'handbook/*.md', '**']"
    adopter.write({CONFIG: f"docs:\n  user: handbook\nfriction:\n  places: {places}\n"})
    places = _document()["places"]
    assert [p["encloses"] for p in places[:3]] == [["user"], [], ["internal", "user"]]


# --- the skips validation applies --------------------------------------------------------


def test_a_synced_copy_is_matched_but_never_walked(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    adopter.write({CONFIG: f"friction:\n  places: [{EVIDENCE_README}]\n"})
    (place,) = _document()["places"]
    assert (place["files"], place["synced"]) == ([], [EVIDENCE_README])


def test_a_malformed_capability_place_is_listed_where_it_is_written_with_why(
    adopter: AdopterRepo,
) -> None:
    _evidence_declares(adopter, "    - {location: runs}\n")
    places = _document()["places"]
    malformed = places[4]
    assert (malformed["source"], malformed["pointer"], malformed["path"]) == (
        "capability:evidence",
        "/friction/places/2",
        None,
    )
    assert malformed["skipped"] == {"reason": "malformed", "detail": "the place has no `path`"}
    assert malformed["files"] == []


def test_a_place_leaving_the_repository_is_skipped(adopter: AdopterRepo) -> None:
    outside = adopter.root.parent / f"{adopter.root.name}-outside"
    outside.mkdir()
    (outside / "stray.md").write_text(ANCHORED.format(id="stray"), encoding="utf-8")
    (adopter.root / "linked").symlink_to(outside, target_is_directory=True)
    adopter.write({CONFIG: "friction:\n  places: [linked, ../elsewhere]\n"})
    places = _document()["places"]
    assert [(p["path"], p["skipped"]["reason"], p["files"]) for p in places[:2]] == [
        ("linked", "outside-repository", []),
        ("../elsewhere", "outside-repository", []),
    ]


# --- files and artefacts -------------------------------------------------------------------


def test_each_file_names_the_places_matching_it_and_its_own_fields(adopter: AdopterRepo) -> None:
    files = {f["path"]: f for f in _document()["files"]}
    assert files["notes/rules.md"]["places"] == [0, 1]  # read under the first
    guide = {"id": "guide", "reader": "user", "kind": "signpost"}
    assert files["notes/guide.md"]["fields"] == guide
    assert files["notes/plain.md"]["fields"] is None
    assert [path for path, f in files.items() if f["excluded"]] == ["notes/old.md"]
    assert all(f["rule_set"] is None and f["unreadable"] is None for f in files.values())


def test_every_artefact_with_its_place_and_its_own_fields(adopter: AdopterRepo) -> None:
    artefacts = _document()["artefacts"]
    assert [(a["location"], a["kind"], a["place"]) for a in artefacts] == [
        ("notes/guide.md", "document", 0),
        ("notes/rules.md#RS-CMN-001", "entry", 0),
        ("tech-docs/evidence/run.md", "document", 2),
        ("handbook/guides/start.md", "document", 3),
    ]
    guide, rule = artefacts[0], artefacts[1]
    assert guide["fields"] == {"id": "guide", "reader": "user", "kind": "signpost"}
    assert (guide["container"], guide["friction"]) == (True, True)
    assert rule["fields"] == {"status": "accepted"}
    # Its anchors, by kind, as its friction block lists them.
    assert (guide["anchors"], rule["anchors"]) == ({"path": ["src/**"]}, {"path": ["src/**"]})


def test_an_artefact_without_anchors_lists_none(adopter: AdopterRepo) -> None:
    adopter.write({"notes/guide.md": "---\nid: guide\npkit:\n  friction: {}\n---\n"})
    (guide,) = [a for a in _document()["artefacts"] if a["path"] == "notes/guide.md"]
    assert (guide["friction"], guide["anchors"], guide["unanchored_because"]) == (True, {}, None)


def test_an_artefact_accepted_unanchored_carries_its_reason(adopter: AdopterRepo) -> None:
    """COR-050 point 1: the reason a person accepted it with no anchors, folded, and a
    key added within the document's version."""
    reason = "A signpost:\n  nothing   it lists is its own."
    block = json.dumps({"friction": {"unanchored-because": reason}})
    adopter.write({"notes/guide.md": f"---\nid: guide\npkit: {block}\n---\n"})
    document = _document()
    assert document["schema_version"] == 1
    artefacts = {a["path"]: a for a in document["artefacts"]}
    guide = artefacts["notes/guide.md"]
    assert (guide["anchors"], guide["unanchored_because"]) == (
        {},
        "A signpost: nothing it lists is its own.",
    )
    assert "unanchored-because" not in guide["fields"]  # inside the container, not its own
    assert artefacts["tech-docs/evidence/run.md"]["unanchored_because"] is None


def test_a_rule_set_file_names_the_rule_set_place_claiming_it(adopter: AdopterRepo) -> None:
    adopter.write(
        {"tech-docs/rule-sets/cmn.md": "---\nrule-set: CMN\nversion: 1.0.0\nrules: {}\n---\n"}
    )
    document = _document()
    places = document["places"]
    (rule_set,) = [f for f in document["files"] if f["path"] == "tech-docs/rule-sets/cmn.md"]
    claimant = places[rule_set["rule_set"]]
    assert (claimant["path"], claimant["declared"], claimant["rule_sets"]) == (
        "tech-docs/rule-sets",
        False,
        {"component": None},
    )
    assert rule_set["fields"] == {"rule-set": "CMN", "version": "1.0.0", "rules": {}}


# --- an entry's span (#1361) --------------------------------------------------------------


def _spans(document: dict[str, Any], path: str) -> dict[str, Any]:
    return {a["location"]: a["span"] for a in document["artefacts"] if a["path"] == path}


def _lines(text: str, span: dict[str, int]) -> str:
    """The span's lines of `text`, joined as a section's text is: one line break after each."""
    return "\n".join(text.split("\n")[span["first_line"] - 1 : span["last_line"]]) + "\n"


def test_an_entry_gives_the_lines_of_its_section(adopter: AdopterRepo) -> None:
    """COR-050 point 1: the section headed by the entry's id, the blank lines after it
    left out; a key added within the document's version."""
    adopter.write({TERMS: SECTIONED})
    document = _document()
    assert document["schema_version"] == 1
    assert _spans(document, TERMS) == {
        f"{TERMS}#term-a": {"first_line": 18, "last_line": 24},  # its sub-heading included
        f"{TERMS}#term-b": {"first_line": 27, "last_line": 29},  # last, no line break at its end
        f"{TERMS}#term-c": None,  # no section of its own
    }
    assert _spans(document, "notes/guide.md") == {"notes/guide.md": None}  # a document


def test_a_span_covers_exactly_the_text_friction_compares(adopter: AdopterRepo) -> None:
    """ADR-057 point 2: one home for an entry's extent, so the span and the body agree."""
    adopter.write({TERMS: SECTIONED})
    spans = _spans(_document(), TERMS)
    bodies = {a.location: a.body for a in fd.discover_artefacts(adopter.root).artefacts}
    for location in (f"{TERMS}#term-a", f"{TERMS}#term-b"):
        assert _lines(SECTIONED, spans[location]) == bodies[location]


def test_a_rule_gives_the_lines_of_its_section(adopter: AdopterRepo) -> None:
    rule_set = (
        "---\nrule-set: CMN\nversion: 1.0.0\nrules:\n  RS-CMN-001: {status: proposed}\n---\n\n"
        "# Common rules\n\n## RS-CMN-001 — Name things\n\nName things by their role.\n"
    )
    adopter.write({"tech-docs/rule-sets/cmn.md": rule_set})
    spans = _spans(_document(), "tech-docs/rule-sets/cmn.md")
    assert spans == {"tech-docs/rule-sets/cmn.md#RS-CMN-001": {"first_line": 10, "last_line": 12}}
    span = spans["tech-docs/rule-sets/cmn.md#RS-CMN-001"]
    assert _lines(rule_set, span) == "## RS-CMN-001 — Name things\n\nName things by their role.\n"


def test_a_span_counts_lines_whatever_the_file_s_line_breaks(adopter: AdopterRepo) -> None:
    """A file written with `\\r\\n` has the lines the same file written with `\\n` has."""
    adopter.write({TERMS: SECTIONED})
    spans = _spans(_document(), TERMS)
    (adopter.root / TERMS).write_bytes(SECTIONED.replace("\n", "\r\n").encode("utf-8"))
    assert _spans(_document(), TERMS) == spans


def test_at_a_commit_the_span_is_that_state_s(adopter: AdopterRepo) -> None:
    adopter.write({TERMS: SECTIONED})
    adopter.commit("terms")
    adopter.write({TERMS: SECTIONED.replace("# Terms\n", "# Terms\n\nTwo more lines.\n")})
    assert _spans(_document(), TERMS)[f"{TERMS}#term-a"] == {"first_line": 20, "last_line": 26}
    at_head = json.loads(_run("--at", "HEAD", "--json").output)
    assert _spans(at_head, TERMS)[f"{TERMS}#term-a"] == {"first_line": 18, "last_line": 24}


# --- the rule sets whose scope covers an artefact (#1361) -----------------------------------


def _rule_set(name: str, scope: str | None = None) -> str:
    scope_line = "" if scope is None else f"scope: {scope}\n"
    return f"---\nrule-set: {name}\nversion: 1.0.0\n{scope_line}rules: {{}}\n---\n"


def _in_scope_of() -> dict[str, list[str]]:
    document = _document()
    assert document["schema_version"] == 1  # a key added within the document's version
    return {a["location"]: a["in_scope_of"] for a in document["artefacts"]}


def test_each_artefact_names_the_rule_sets_whose_scope_covers_it(adopter: AdopterRepo) -> None:
    """COR-051 point 2: a scope is given as places, so it is read as a place is — a
    folder covers every document beneath it, a glob what it matches, a file itself."""
    notes = "tech-docs/rule-sets/notes.md"
    guides = "tech-docs/rule-sets/guides.md"
    method = ".pkit/capabilities/evidence/rule-sets/ev.md"
    adopter.write(
        {
            notes: _rule_set("NOTES", "[notes]"),
            guides: _rule_set("GUIDES", "['handbook/**', notes/guide.md]"),
            method: _rule_set("EV", "['handbook/guides/*.md']"),
            "tech-docs/rule-sets/none.md": _rule_set("NONE"),  # no scope: it covers nothing
        }
    )
    assert _in_scope_of() == {
        "notes/guide.md": [guides, notes],  # in path order
        "notes/rules.md#RS-CMN-001": [notes],  # an entry, by its file
        "tech-docs/evidence/run.md": [],  # no rule set covers it
        "handbook/guides/start.md": [method, guides],  # a method rule set's scope too
    }


def test_a_scope_leaving_the_repository_covers_nothing(adopter: AdopterRepo) -> None:
    adopter.write({"tech-docs/rule-sets/away.md": _rule_set("AWAY", "['../notes', '/notes']")})
    assert all(sets == [] for sets in _in_scope_of().values())


def test_a_scope_entry_that_is_not_text_is_passed_over(adopter: AdopterRepo) -> None:
    """Read forgivingly, as discovery reads a declaration; the rule-set pass judges the shape."""
    notes = "tech-docs/rule-sets/notes.md"
    adopter.write({notes: _rule_set("NOTES", "[{not: text}, notes/guide.md]")})
    assert _in_scope_of()["notes/guide.md"] == [notes]


def test_without_a_rule_set_no_artefact_is_in_scope(adopter: AdopterRepo) -> None:
    assert all(sets == [] for sets in _in_scope_of().values())


def test_the_document_is_the_one_discovery(adopter: AdopterRepo) -> None:
    """The same artefacts, in the same order, as the discovery validation reads."""
    discovery = fd.discover_artefacts(adopter.root)
    assert [a["location"] for a in _document()["artefacts"]] == [
        a.location for a in discovery.artefacts
    ]
    assert [f["path"] for f in _document()["files"]] == [f.path for f in discovery.files]


# --- another state: --at ---------------------------------------------------------------


def test_at_a_commit_the_document_is_that_state_s(adopter: AdopterRepo) -> None:
    """`--at` reads one commit from git objects — its configuration, its places,
    its files — so a script reads another state through the one discovery."""
    committed = _document()
    adopter.commit("state one")
    adopter.write(
        {
            CONFIG: "docs:\n  user: handbook\nfriction:\n  places: [notes]\n",
            "notes/later.md": ANCHORED.format(id="later"),
            "tech-docs/evidence/run.md": None,
        }
    )
    now = _document()
    assert "notes/later.md" in [f["path"] for f in now["files"]]
    result = _run("--at", "HEAD", "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == committed
    assert _run("--at", "HEAD", "--json").output == result.output


def test_at_a_commit_the_roots_are_that_state_s(adopter: AdopterRepo) -> None:
    adopter.commit("state one")
    adopter.write({CONFIG: "docs:\n  internal: elsewhere\n"})
    assert _document()["roots"] == {"internal": "elsewhere", "user": "docs"}
    at_head = json.loads(_run("--at", "HEAD", "--json").output)
    assert at_head["roots"] == {"internal": "tech-docs", "user": "handbook"}


@pytest.mark.parametrize("rev", ["no-such-branch", "-x", ""])
def test_at_a_name_that_is_no_commit_exits_1(adopter: AdopterRepo, rev: str) -> None:
    adopter.commit("state one")
    result = _run("--at", rev, "--json")
    assert result.exit_code == 1
    assert "names no commit of this repository" in result.output


def test_at_a_commit_whose_configuration_cannot_be_read_exits_1(adopter: AdopterRepo) -> None:
    adopter.write({CONFIG: "friction: [places\n"})
    adopter.commit("broken configuration")
    adopter.write({CONFIG: "friction:\n  places: [notes]\n"})
    assert _run("--json").exit_code == 0
    result = _run("--at", "HEAD", "--json")
    assert result.exit_code == 1
    assert "the configuration .pkit/project/config.yaml does not parse" in result.output


# --- the command -----------------------------------------------------------------------


# --- held documents (COR-050 point 1) -------------------------------------------------------


def test_held_folders_are_declared_as_places_are_with_the_files_each_holds(
    adopter: AdopterRepo,
) -> None:
    """A folder of held documents is declared as a place is — its owner, where it is
    written, its location and resolved path, the files it holds and why it is
    skipped — and each held file is listed apart, with the folder holding it and
    the places that left it out; it is never among the files or the artefacts. A
    folder holding nothing yet is listed with no files; a malformed one where it
    was written. Keys added: the version stays."""
    package = adopter.root / EVIDENCE_PACKAGE
    package.write_text(
        package.read_text(encoding="utf-8").replace(
            "    guides: {path: guides, root: user}\n",
            "    guides: {path: guides, root: user}\n    logs: {path: logs}\n",
        )
        + "  held:\n"
        "    - {location: logs, path: records, description: Run records.}\n"
        "    - {location: logs, path: empty}\n"
        "    - {path: stray}\n",
        encoding="utf-8",
    )
    config = adopter.root / CONFIG
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "places: [notes, notes/rules.md]", "places: [notes, notes/rules.md, tech-docs/logs]"
        ),
        encoding="utf-8",
    )
    record = "tech-docs/logs/records/2026-10-01-run.md"
    adopter.write({record: "---\ndate: '2026-10-01'\n---\n\n# A run\n"})
    document = _document()

    assert fd.ARTEFACTS_SCHEMA_VERSION == 1
    assert document["schema_version"] == 1
    logs = {"name": "logs", "path": "tech-docs/logs", "root": "internal"}
    declared = {"source": "capability:evidence", "file": EVIDENCE_PACKAGE}
    assert document["held"] == [
        {
            **declared,
            "pointer": "/friction/held/0",
            "written": "records",
            "location": logs,
            "path": "tech-docs/logs/records",
            "files": [record],
            "skipped": None,
        },
        {
            **declared,
            "pointer": "/friction/held/1",
            "written": "empty",
            "location": logs,
            "path": "tech-docs/logs/empty",
            "files": [],
            "skipped": None,
        },
        {
            **declared,
            "pointer": "/friction/held/2",
            "written": None,
            "location": None,
            "path": None,
            "files": [],
            "skipped": {
                "reason": "malformed",
                "detail": (
                    "the held folder names no `location`: a held folder lies within one of "
                    "the component's `docs.locations`"
                ),
            },
        },
    ]
    assert document["held_files"] == [
        {
            "path": record,
            "held": 0,
            "places": [2],
            "excluded": False,
            "fields": {"date": "2026-10-01"},
            "unreadable": None,
        }
    ]
    assert document["places"][2]["path"] == "tech-docs/logs"
    assert record not in document["places"][2]["files"]
    assert record not in [f["path"] for f in document["files"]]
    assert record not in [a["path"] for a in document["artefacts"]]
    human = _run().output.rstrip().split("\n")
    assert human[-4:] == [
        "3 held folder(s), whose files no place walks:",
        "  tech-docs/logs/records  (capability:evidence, location logs)  1 file(s)",
        "  tech-docs/logs/empty  (capability:evidence, location logs)  0 file(s)",
        f"  {EVIDENCE_PACKAGE} /friction/held/2  (capability:evidence)  0 file(s); skipped, "
        "malformed: the held folder names no `location`: a held folder lies within one of the "
        "component's `docs.locations`",
    ]


def test_a_held_file_says_whether_friction_exclude_leaves_it_out(adopter: AdopterRepo) -> None:
    """A held document under an excluded path is still held — its owner still claims it, and
    validation still reads it — and says it is excluded, as a walked file does, so its owner
    counts it no more than the measures count an excluded artefact (COR-050 point 7)."""
    package = adopter.root / EVIDENCE_PACKAGE
    package.write_text(
        package.read_text(encoding="utf-8").replace(
            "    guides: {path: guides, root: user}\n",
            "    guides: {path: guides, root: user}\n    logs: {path: logs}\n",
        )
        + "  held:\n    - {location: logs, path: records}\n",
        encoding="utf-8",
    )
    config = adopter.root / CONFIG
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "exclude: [notes/old.md]", "exclude: [notes/old.md, tech-docs/logs/records/old]"
        ),
        encoding="utf-8",
    )
    kept, old = "tech-docs/logs/records/kept.md", "tech-docs/logs/records/old/one.md"
    adopter.write({kept: "# Kept\n", old: "# Old\n"})
    document = _document()
    (folder,) = document["held"]
    assert folder["files"] == [kept, old]
    assert [(h["path"], h["excluded"]) for h in document["held_files"]] == [
        (kept, False),
        (old, True),
    ]


def test_without_a_held_folder_the_lists_are_empty(adopter: AdopterRepo) -> None:
    document = _document()
    assert (document["held"], document["held_files"]) == ([], [])
    assert "held folder" not in _run().output


def test_the_same_state_prints_the_same_bytes(adopter: AdopterRepo) -> None:
    assert _run("--json").output == _run("--json").output


def test_without_json_a_line_per_place_and_the_counts(adopter: AdopterRepo) -> None:
    result = _run()
    assert result.exit_code == 0, result.output
    assert "  tech-docs/evidence/**/*.md  (capability:evidence, location runs)  1 file(s)" in (
        result.output
    )
    assert result.output.rstrip().endswith(
        "6 file(s): 1 excluded, 0 unreadable.\n"
        "4 artefact(s): 4 carrying the `pkit` container, 4 with a `friction` block."
    )


@pytest.mark.parametrize("config", ["friction: [places\n", "- a list\n"])
def test_a_configuration_that_cannot_be_read_exits_1(adopter: AdopterRepo, config: str) -> None:
    adopter.write({CONFIG: config})
    result = _run("--json")
    assert result.exit_code == 1
    assert "the configuration .pkit/project/config.yaml" in result.output
    assert "`pkit validate` reports it" in result.output


def test_an_empty_configuration_is_no_places(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo()
    adopter.write({CONFIG: ""})
    document = _document()
    assert (document["places"], document["artefacts"]) == ([], [])


def test_a_usage_error_exits_2(adopter: AdopterRepo) -> None:
    assert _run("--yaml").exit_code == 2


def test_outside_a_project_it_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert _run("--json").exit_code == 1
