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
  artefact with the rule sets whose scope covers it (#1361) and the span each
  of its part anchors resolves to: an entry's section (#1414), or a record's
  point, read through the one reading of a record's points (#1552);
- every **folder of held documents**, declared as a place is, and every file it
  holds, with the places that left it out — never a file or an artefact of any
  place (#1130);
- the exit codes: 0 answered, 1 when the configuration cannot be read, 2 on a
  usage error — and the same bytes for the same state.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import friction_discovery as fd
from project_kit import record_points as rp
from project_kit import working_tree
from project_kit.cli import main
from project_kit.friction_check import Side
from project_kit.friction_git import CommitTree
from project_kit.line_breaks import universal_newlines
from project_kit.working_tree import WorkingTree
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import POINTED, POINTS, pointed_record

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


# --- each part anchor's span (#1414) ---------------------------------------------------------

# A page anchoring two entries, a whole document, a missing artefact and a path.
PAGE = """---
id: page
pkit:
  friction:
    anchors:
      path: [src/**]
      artefact: [term-a, guide, term-c, notes/guide.md, no-such-entry]
---

# Page
"""

DOC_RULES = (
    "---\nrule-set: DOC\nversion: 1.0.0\nrules:\n  RS-DOC-001: {status: proposed}\n---\n\n"
    "# Documentation rules\n\n## RS-DOC-001 — Say who reads it\n\nName the reader.\n"
)


def _part_anchors(document: dict[str, Any]) -> dict[str, Any]:
    """Each artefact listing a part anchor, by location."""
    return {a["location"]: a["part_anchors"] for a in document["artefacts"] if a["part_anchors"]}


def test_an_anchor_on_an_entry_gives_the_span_its_part_resolves_to(adopter: AdopterRepo) -> None:
    """Beside each anchor that names a part, the span it resolves to: the entry's own,
    so a script reads what the anchor stands on without resolving it (ADR-057 point 2).
    A whole document, a dead anchor and a path name no part."""
    adopter.write({TERMS: SECTIONED, "notes/page.md": PAGE})
    document = _document()
    assert document["schema_version"] == 1  # a key added within the document's version
    spans = _spans(document, TERMS)
    assert _part_anchors(document) == {
        "notes/page.md": [
            {
                "kind": "artefact",
                "value": "term-a",
                "path": TERMS,
                "span": spans[f"{TERMS}#term-a"],
            },
            {"kind": "artefact", "value": "term-c", "path": TERMS, "span": None},  # no section
        ]
    }
    assert spans[f"{TERMS}#term-a"] == {"first_line": 18, "last_line": 24}
    assert all(isinstance(a["part_anchors"], list) for a in document["artefacts"])


def test_an_anchor_on_a_rule_gives_the_rule_s_span(adopter: AdopterRepo) -> None:
    page = PAGE.replace("[term-a, guide, term-c, notes/guide.md, no-such-entry]", "[RS-DOC-001]")
    adopter.write({"tech-docs/rule-sets/doc.md": DOC_RULES, "notes/page.md": page})
    found = _part_anchors(_document())["notes/page.md"]
    assert found == [
        {
            "kind": "artefact",
            "value": "RS-DOC-001",
            "path": "tech-docs/rule-sets/doc.md",
            "span": {"first_line": 10, "last_line": 12},
        }
    ]
    span = found[0]["span"]
    assert _lines(DOC_RULES, span) == "## RS-DOC-001 — Say who reads it\n\nName the reader.\n"


def test_at_a_commit_a_part_anchor_s_span_is_that_state_s(adopter: AdopterRepo) -> None:
    adopter.write({TERMS: SECTIONED, "notes/page.md": PAGE})
    adopter.commit("terms")
    adopter.write({TERMS: SECTIONED.replace("# Terms\n", "# Terms\n\nTwo more lines.\n")})
    now = _part_anchors(_document())["notes/page.md"][0]["span"]
    at_head = _part_anchors(json.loads(_run("--at", "HEAD", "--json").output))
    assert now == {"first_line": 20, "last_line": 26}
    assert at_head["notes/page.md"][0]["span"] == {"first_line": 18, "last_line": 24}


# --- each point anchor's span (#1552) ---------------------------------------------------------


def _page(**anchors: list[str]) -> str:
    """A page in a project place, its anchors by kind in the order given."""
    lines = "".join(f"      {kind}: [{', '.join(values)}]\n" for kind, values in anchors.items())
    return f"---\nid: page\npkit:\n  friction:\n    anchors:\n{lines}---\n\n# Page\n"


def test_an_anchor_on_a_record_s_point_gives_the_span_of_the_point_s_section(
    adopter: AdopterRepo,
) -> None:
    """COR-050 point 2: an anchor may name one point of a record. Its span is the lines of
    the record's file the point's section spans, read through the one reading of a record's
    points (ADR-057 point 2): exactly the section the checks compare. `artefact` anchors
    come first, then `record` anchors, each in written order. A whole record, a dead point
    and a missing record name no part."""
    record = pointed_record()
    page = _page(
        record=["PRJ-900#3", "PRJ-900", "PRJ-900#9", "PRJ-999#1", "PRJ-900#1"],
        artefact=["term-a"],  # written after the record anchors, listed before them
    )
    adopter.write({POINTED: record, TERMS: SECTIONED, "notes/page.md": page})
    document = _document()
    assert document["schema_version"] == 1  # a key added within the document's version
    found = _part_anchors(document)["notes/page.md"]
    assert [(a["kind"], a["value"]) for a in found] == [
        ("artefact", "term-a"),
        ("record", "PRJ-900#3"),
        ("record", "PRJ-900#1"),
    ]
    third, first = found[1], found[2]
    assert third == {
        "kind": "record",
        "value": "PRJ-900#3",
        "path": POINTED,
        "span": {"first_line": 27, "last_line": 29},
    }
    assert _lines(record, third["span"]) == "### 3. Third\n\nThe third point.\n"
    assert _lines(record, first["span"]) == "### 1. First\n\nThe first point.\n"
    standing = rp.read_points(record).standing("3")
    assert standing is not None and _lines(record, third["span"]) == standing.section


def test_an_anchor_on_a_retired_point_is_listed_with_no_span(adopter: AdopterRepo) -> None:
    """COR-050 points 5 and 7: an anchor on a retired point resolves, since the record says
    where the point went, and stands on nothing, so it has no span."""
    points = (POINTS[0], ("2", "Retired", "Its content is in point 3."), POINTS[2])
    adopter.write(
        {
            POINTED: pointed_record(points, retired={"2": ["3"]}),
            "notes/page.md": _page(record=["PRJ-900#2"]),
        }
    )
    assert _part_anchors(_document())["notes/page.md"] == [
        {"kind": "record", "value": "PRJ-900#2", "path": POINTED, "span": None}
    ]


@pytest.mark.parametrize(
    "decision",
    [
        pytest.param("### 1. First\n\nOne.\n\n### 1. Again\n\nTwo.\n", id="ambiguous"),
        pytest.param("1. **First.** One.\n2. **Second.** Two.\n", id="list-form"),
    ],
)
def test_an_ambiguous_point_anchor_or_one_on_a_record_in_list_form_names_no_part(
    adopter: AdopterRepo, decision: str
) -> None:
    """COR-050 point 7: an id two live points share is ambiguous, and a record in list form
    holds no point an anchor can name; neither names a part."""
    record = pointed_record().split("## Decision\n\n")[0] + f"## Decision\n\n{decision}\n"
    adopter.write({POINTED: record, "notes/page.md": _page(record=["PRJ-900#1"])})
    document = _document()
    assert _part_anchors(document) == {}
    page = next(a for a in document["artefacts"] if a["path"] == "notes/page.md")
    assert page["part_anchors"] == []


def test_a_point_of_an_adr_or_of_a_capability_s_decision_gives_its_span(
    adopter: AdopterRepo,
) -> None:
    """The record is found as the checks find it: an ADR in the folder the agents overlay
    names, and a capability's decision as `<capability>:DEC-NNN`, with or without its
    slug."""
    adr = "docs/architecture/decisions/ADR-007-pointed.md"
    decision = ".pkit/capabilities/evidence/decisions/DEC-003-pointed.md"
    record = pointed_record()
    adopter.write(
        {
            ".pkit/agents/project/overlay.yaml": "adr-records:\n  - docs/architecture/decisions/\n",
            adr: record.replace("PRJ-900", "ADR-007"),
            decision: record.replace("PRJ-900", "DEC-003"),
            "notes/page.md": _page(
                record=["ADR-007#2", "evidence:DEC-003#1", "evidence:DEC-003-pointed#3"]
            ),
        }
    )
    found = _part_anchors(_document())["notes/page.md"]
    assert [(a["value"], a["path"], a["span"]) for a in found] == [
        ("ADR-007#2", adr, {"first_line": 23, "last_line": 25}),
        ("evidence:DEC-003#1", decision, {"first_line": 19, "last_line": 21}),
        ("evidence:DEC-003-pointed#3", decision, {"first_line": 27, "last_line": 29}),
    ]


def test_at_a_commit_a_point_anchor_s_span_is_that_state_s(adopter: AdopterRepo) -> None:
    """With `--at`, the record is read at that commit: its listing finds the record and its
    text gives the lines."""
    record = pointed_record()
    adopter.write({POINTED: record, "notes/page.md": _page(record=["PRJ-900#2"])})
    adopter.commit("a pointed record")
    adopter.write({POINTED: pointed_record(context="Why it came up.\n\nTwo more lines.")})
    now = _part_anchors(_document())["notes/page.md"][0]["span"]
    at_head = _part_anchors(json.loads(_run("--at", "HEAD", "--json").output))
    assert now == {"first_line": 25, "last_line": 27}
    assert at_head["notes/page.md"][0]["span"] == {"first_line": 23, "last_line": 25}
    (adopter.root / POINTED).unlink()
    assert _part_anchors(_document()) == {}  # gone from the working tree: a dead anchor
    at_head = _part_anchors(json.loads(_run("--at", "HEAD", "--json").output))
    assert at_head["notes/page.md"][0]["path"] == POINTED


def _record_bytes(transform: Callable[[str], bytes]) -> Callable[[AdopterRepo], None]:
    """Write `PRJ-900` as the bytes `transform` makes of its text."""

    def write(repo: AdopterRepo) -> None:
        path = repo.root / POINTED
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(transform(pointed_record()))

    return write


def _record_link(repo: AdopterRepo) -> None:
    """Write `PRJ-900` as a link to a file holding its text: a link is never read as a
    document (ADR-057 point 2)."""
    repo.write({".pkit/decisions/project/real.txt": pointed_record()})
    (repo.root / POINTED).symlink_to("real.txt")


@pytest.mark.parametrize(
    ("write", "listed"),
    [
        pytest.param(_record_bytes(lambda t: t.replace("\n", "\r\n").encode()), True, id="crlf"),
        pytest.param(_record_bytes(lambda t: t.replace("\n", "\r").encode()), True, id="lone-cr"),
        pytest.param(_record_bytes(lambda t: b"\xef\xbb\xbf" + t.encode()), True, id="bom"),
        pytest.param(
            _record_bytes(lambda t: t.replace("third", "thi\xe9rd").encode("latin-1")),
            False,
            id="not-utf-8",
        ),
        pytest.param(_record_link, False, id="link"),
    ],
)
def test_a_point_anchor_is_listed_exactly_where_the_friction_checks_resolve_it(
    adopter: AdopterRepo, write: Callable[[AdopterRepo], None], listed: bool
) -> None:
    """The listing agrees with the friction checks' own reading of each state
    (`friction_check.Side`), at the working tree and at a commit. An anchor is listed where
    it resolves there, and its span's lines are the section the checks compare."""
    values = ["PRJ-900#1", "PRJ-900#3", "PRJ-900#9"]
    write(adopter)
    adopter.write({"notes/page.md": _page(record=values)})
    adopter.commit("a pointed record")
    head = adopter.head()
    states = [
        (_document(), WorkingTree(adopter.root)),
        (json.loads(_run("--at", head, "--json").output), CommitTree(adopter.root, head)),
    ]
    for document, tree in states:
        side = Side(adopter.root, tree, fd.discover_artefacts(adopter.root, tree=tree))
        found = {a["value"]: a for a in _part_anchors(document).get("notes/page.md", [])}
        assert sorted(found) == (["PRJ-900#1", "PRJ-900#3"] if listed else [])
        for value in values:
            anchor = fd.Anchor("record", value)
            assert (value in found) == side.resolves(anchor), value
            if value in found:
                standing = side.standing(anchor, side.record_path(value))
                raw = tree.read_bytes([POINTED])[POINTED]
                text = universal_newlines(raw.decode("utf-8"))
                assert standing is not None
                assert _lines(text, found[value]["span"]) == standing.section


# --- each section or lead anchor's span (#1423) -----------------------------------------------

HANDBOOK = """---
id: handbook
title: A handbook
---

# Handbook

What the handbook is for.

## Installing

Run the installer.

## Using

Run the tool.

## Using

Again.
"""


def test_an_anchor_on_a_section_or_the_lead_gives_the_span_its_part_resolves_to(
    adopter: AdopterRepo,
) -> None:
    """COR-050 point 2: an artefact anchor may name one section of a document by its
    heading's slug, or its lead by a bare `#`. Its span is the lines of the document's file
    that part spans, read through the one reading of an artefact anchor's part
    (`artefact_parts`): exactly the text the checks compare. A dead, ambiguous or refused
    part anchor names no part, and neither does a whole document."""
    page = _page(
        artefact=[
            '"notes/handbook.md#installing"',
            '"notes/handbook.md#"',
            '"handbook#installing"',
            '"notes/handbook.md#using"',  # two headings share the slug: ambiguous
            '"notes/handbook.md#upgrading"',  # no heading has the slug: dead
            '"notes/terms.md#term-a"',  # a collection file's part: refused
            '"notes/handbook.md"',  # a whole document
        ]
    )
    adopter.write({"notes/handbook.md": HANDBOOK, TERMS: SECTIONED, "notes/page.md": page})
    found = _part_anchors(_document())["notes/page.md"]
    section = {"first_line": 10, "last_line": 12}
    assert found == [
        {
            "kind": "artefact",
            "value": "notes/handbook.md#installing",
            "path": "notes/handbook.md",
            "span": section,
        },
        {
            "kind": "artefact",
            "value": "notes/handbook.md#",
            "path": "notes/handbook.md",
            "span": {"first_line": 6, "last_line": 8},
        },
        {
            "kind": "artefact",
            "value": "handbook#installing",
            "path": "notes/handbook.md",
            "span": section,
        },
    ]
    assert _lines(HANDBOOK, section) == "## Installing\n\nRun the installer.\n"
    assert _lines(HANDBOOK, found[1]["span"]) == "# Handbook\n\nWhat the handbook is for.\n"
    side = Side(adopter.root, WorkingTree(adopter.root), fd.discover_artefacts(adopter.root))
    for entry in found:
        standing = side.part_of(entry["value"]).standing
        assert standing is not None and _lines(HANDBOOK, entry["span"]) == standing.section


def test_an_empty_lead_spans_no_lines(adopter: AdopterRepo) -> None:
    """A document whose body opens with a second-level heading has an empty lead: the
    anchor resolves, and spans no lines."""
    opening = HANDBOOK.replace("# Handbook\n\nWhat the handbook is for.\n\n", "")
    adopter.write({"notes/handbook.md": opening, "notes/page.md": _page(artefact=['"handbook#"'])})
    assert _part_anchors(_document())["notes/page.md"] == [
        {"kind": "artefact", "value": "handbook#", "path": "notes/handbook.md", "span": None}
    ]


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


# --- a capability's location, outside its places (#1724) ------------------------------------

LOGS = "tech-docs/logs"


def _logs_declared(adopter: AdopterRepo, held: str) -> None:
    """The evidence capability given a third location, `logs`, with one place in it,
    `kept`, and the folders of held documents `held` lists."""
    package = adopter.root / EVIDENCE_PACKAGE
    package.write_text(
        package.read_text(encoding="utf-8").replace(
            "    guides: {path: guides, root: user}\n",
            "    guides: {path: guides, root: user}\n    logs: {path: logs}\n",
        )
        + "    - {location: logs, path: kept}\n"
        + (f"  held:\n{held}" if held else ""),
        encoding="utf-8",
    )


def _unplaced(document: dict[str, Any], location: str) -> list[tuple[str, bool]]:
    entry = document["unplaced"]["evidence"][location]
    return [(f["path"], f["excluded"]) for f in entry["files"]]


def test_each_capability_location_lists_the_files_no_place_or_held_folder_of_its_holds(
    adopter: AdopterRepo,
) -> None:
    """Each location an installed capability declares, by the capability and the
    location, with where it lies and the Markdown files within it that no place or
    held folder of that capability holds, each saying whether `friction.exclude` leaves
    it out. Another component's place, or the project's, holds nothing for it. A
    location holding none is listed with no files. A key added: the version stays."""
    _logs_declared(adopter, "    - {location: logs, path: records}\n")
    config = adopter.root / CONFIG
    config.write_text(
        config.read_text(encoding="utf-8")
        .replace(
            "places: [notes, notes/rules.md]", f"places: [notes, notes/rules.md, {LOGS}/shared]"
        )
        .replace("exclude: [notes/old.md]", f"exclude: [notes/old.md, {LOGS}/old.md]"),
        encoding="utf-8",
    )
    adopter.write(
        {
            f"{LOGS}/kept/a.md": "# Kept\n",
            f"{LOGS}/records/2026-10-01.md": "# A record\n",
            f"{LOGS}/loose.md": "# Loose\n",
            f"{LOGS}/old.md": "# Old\n",
            f"{LOGS}/shared/b.md": ANCHORED.format(id="b"),
            f"{LOGS}/plain.txt": "not a document\n",
            "handbook/guides/deep/c.md": "# Deeper than the place's glob\n",
        }
    )
    document = _document()
    assert document["schema_version"] == fd.ARTEFACTS_SCHEMA_VERSION == 1
    assert document["unplaced"] == {
        "evidence": {
            "runs": {"path": "tech-docs/evidence", "files": []},
            "guides": {
                "path": "handbook/guides",
                "files": [{"path": "handbook/guides/deep/c.md", "excluded": False}],
            },
            "logs": {
                "path": LOGS,
                "files": [
                    {"path": f"{LOGS}/loose.md", "excluded": False},
                    {"path": f"{LOGS}/old.md", "excluded": True},
                    {"path": f"{LOGS}/shared/b.md", "excluded": False},
                ],
            },
        }
    }
    # The project's place walks the shared file, and still no place of the capability's holds it.
    assert f"{LOGS}/shared/b.md" in [f["path"] for f in document["files"]]
    human = _run().output.rstrip().split("\n")
    assert human[-3:] == [
        "2 capability location(s) holding files no place or held folder of the capability holds:",
        "  handbook/guides  (capability:evidence, location guides)  1 file(s), 0 excluded",
        f"  {LOGS}  (capability:evidence, location logs)  3 file(s), 1 excluded",
    ]


def test_a_held_folder_that_holds_nothing_leaves_its_files_unplaced(adopter: AdopterRepo) -> None:
    """Two held folders that would share a file each hold nothing (`overlap`), so no
    folder of the capability holds what lies in them."""
    _logs_declared(
        adopter, "    - {location: logs, path: records}\n    - {location: logs, path: records/x}\n"
    )
    adopter.write({f"{LOGS}/records/r.md": "# A record\n"})
    document = _document()
    assert [h["skipped"]["reason"] for h in document["held"]] == ["overlap", "overlap"]
    assert _unplaced(document, "logs") == [(f"{LOGS}/records/r.md", False)]


def test_the_unplaced_files_are_read_from_the_walk_s_one_listing(
    adopter: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inside a git work tree a file git ignores is no file of the listing, so neither the
    walk nor this list reads it. Outside one, where every file is listed, both read it
    (ADR-057 point 2)."""
    _logs_declared(adopter, "")
    config = adopter.root / CONFIG
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "places: [notes, notes/rules.md]", f"places: [notes, notes/rules.md, {LOGS}]"
        ),
        encoding="utf-8",
    )
    ignored = f"{LOGS}/ignored.md"
    adopter.write({".gitignore": f"{ignored}\n", ignored: "# Ignored\n"})
    inside = _document()
    assert _unplaced(inside, "logs") == []
    assert ignored not in [f["path"] for f in inside["files"]]
    monkeypatch.setattr(working_tree, "in_git_work_tree", lambda _root: False)
    outside = _document()
    assert _unplaced(outside, "logs") == [(ignored, False)]
    assert ignored in [f["path"] for f in outside["files"]]


def test_at_a_commit_the_unplaced_files_are_that_state_s(adopter: AdopterRepo) -> None:
    _logs_declared(adopter, "")
    adopter.write({f"{LOGS}/loose.md": "# Loose\n"})
    adopter.commit("a loose file")
    adopter.write({f"{LOGS}/loose.md": None, f"{LOGS}/later.md": "# Later\n"})
    assert _unplaced(_document(), "logs") == [(f"{LOGS}/later.md", False)]
    at_head = json.loads(_run("--at", "HEAD", "--json").output)
    assert _unplaced(at_head, "logs") == [(f"{LOGS}/loose.md", False)]


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
