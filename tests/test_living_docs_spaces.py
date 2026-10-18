"""living-docs' places, the LDOC rule set, and the space and page templates (#1003).

The capability's first artefacts, each held to living-docs DEC-001:

- the **validator**, `pkit living-docs validate` — the `living-docs:spaces`
  member of `pkit validate` — over an adopter repository with the capability
  installed: one test per rule it applies (an out-of-root place without an
  assignment, a place enclosing a root, a decision record that declares a page
  kind, another owner's document by its type, place or holder, an entry point
  outside its space, a page's fields, the backbone's order of places, a
  definition that does not inherit LDOC), and the readers each page's reader
  resolves against, named in its summary (reader resolution itself is
  `test_living_docs_points.py`'s);
- **types** (#1411; DEC-001 points 1, 2 and 4; COR-056): the page and template
  types the package declares and its places give, a page as a document of the
  page type, the pages of a project place that gives no type, and the
  assignment held to the definitions' scopes — each page an assigned place
  gives a space inside that definition's scope and no other's, and an
  assigned place giving the page type where its definition selects by type;
- the **LDOC rule set** validating as a method rule set with its origins and
  the parts its validator enforces, and a space definition instantiated from
  the template inheriting it;
- the **page templates** — the signpost and the reference page — each
  validating: its own fields by the capability's schema, its friction block
  by the core's;
- **page formats** (RS-LDOC-004; #1267): a page's body against the structure
  its kind declares in `schemas/page-kinds.yaml` — a title missing, or written
  as something that is not read as one; a kind declaring no structure,
  reported and never failed; the severity the rule's status gives; a
  declaration that gives no reading, which is one error. What no shipped kind
  declares — a section out of order, fixed text, sections in any order — is
  tested on a declaration of the test's own, read from a file outside the
  repository: no test rewrites the declaration the capability ships. Then
  what a heading is, and each template following its kind's structure;
- **one home for discovery**: the capability's scripts read the places and
  their documents through `pkit friction artefacts` and carry no matcher,
  listing or place reader of their own (#1099; ADR-057 point 2).

The validator runs as a subprocess under this interpreter, as the backbone
runs it (its `--json` findings document); where `pkit validate` runs it, the
script's `uv run --script` shebang is pointed at this interpreter, and the
`pkit` it reads the places and the readers point through is the real CLI under
this interpreter (`pkit_on_path`), so no test reaches `uv` or the network.
project-kit's own configuration passing is in `test_self_host_documentation.py`.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit import backbone_schemas as bs
from project_kit import document_parts
from project_kit import friction_discovery as fd
from project_kit import rule_sets as rs
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.test_rule_sets import anchored_to, rule_set_text, rules

REPO = Path(__file__).resolve().parent.parent
CAPABILITY = REPO / ".pkit" / "capabilities" / "living-docs"
LD = Path(".pkit") / "capabilities" / "living-docs"
SCRIPT = LD / "scripts" / "validate.py"
CONFIG = ".pkit/project/config.yaml"
LD_CONFIG = f"{LD.as_posix()}/project/config.yaml"
DEFINITIONS = "tech-docs/living-docs/rule-sets"

PAGE = "---\nreader: user\nkind: signpost\n---\n\n# Guide\n"
RECORD = "---\nid: ADR-001\ntitle: A decision\nstatus: accepted\n---\n\n## Context\n"


def _yaml(data: Mapping[str, Any]) -> str:
    buffer = io.StringIO()
    YAML().dump(dict(data), buffer)
    return buffer.getvalue()


#: The template's scope: its line and the lines indented under it.
TEMPLATE_SCOPE = re.compile(r"^scope:.*\n(?:[ \t]+.*\n)*", re.MULTILINE)

#: The scope each fixture definition is given in place of the template's: the
#: space's root and the place assigned to it, by path alone. The fixture's places
#: outside the roots give no type, and DEC-001 point 1 asks one of them only where
#: a definition selects by type.
SPACE_SCOPES: dict[str, Any] = {"USER": ["docs/**", "README.md"], "TECH": ["tech-docs/**"]}

#: A definition written without a scope.
UNSCOPED = object()


def _definition(set_name: str, inherits: list[str] | None = None, scope: Any = None) -> str:
    """A space definition instantiated from the capability's template, with `scope` —
    the space's own in `SPACE_SCOPES` by default, none for `UNSCOPED`."""
    template = (CAPABILITY / "templates" / "space-definition.md").read_text(encoding="utf-8")
    text = template.replace("rule-set: SPACE", f"rule-set: {set_name}").replace(
        "<space>", set_name.lower()
    )
    if inherits is not None:
        text = text.replace("inherits: [living-docs:LDOC@1]", f"inherits: {json.dumps(inherits)}")
    scope = SPACE_SCOPES.get(set_name) if scope is None else scope
    written = "" if scope is UNSCOPED or scope is None else f"scope: {json.dumps(scope)}\n"
    text, replaced = TEMPLATE_SCOPE.subn(written, text, count=1)
    assert replaced == 1
    return text


def declare(
    repo: AdopterRepo,
    *,
    places: list[str] | None = None,
    assignments: Mapping[str, str] | None = None,
    spaces: Mapping[str, Mapping[str, str]] | None = None,
    roots: Mapping[str, str] | None = None,
) -> None:
    """The backbone configuration (roots, project places) and living-docs' own."""
    config = {
        "docs": dict(roots or {"user": "docs/", "internal": "tech-docs/"}),
        "friction": {"places": list(places if places is not None else ["README.md"])},
    }
    repo.write({CONFIG: _yaml(config)})
    own = {
        "pkit_schema": "living-docs:config",
        "schema_version": 1,
        "spaces": dict(
            spaces
            if spaces is not None
            else {
                "user": {"entry-point": "README.md", "definition": f"{DEFINITIONS}/user.md"},
                "technical": {
                    "entry-point": "tech-docs/README.md",
                    "definition": f"{DEFINITIONS}/technical.md",
                },
            }
        ),
        "places": dict(assignments if assignments is not None else {"README.md": "user"}),
    }
    repo.write({LD_CONFIG: _yaml(own)})


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path) -> AdopterRepo:
    """An adopter with living-docs installed, two separate roots, one page per
    space's entry, a decision record, and both spaces' definitions — clean."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    script = repo.root / SCRIPT
    body = script.read_text(encoding="utf-8").split("\n", 1)[1]
    script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    declare(repo)
    repo.write(
        {
            "README.md": PAGE,
            "docs/guide.md": PAGE,
            "tech-docs/README.md": "---\nreader: maintainer\nkind: signpost\n---\n\n# Tech\n",
            "tech-docs/architecture/decisions/ADR-001-a-decision.md": RECORD,
            f"{DEFINITIONS}/user.md": _definition("USER"),
            f"{DEFINITIONS}/technical.md": _definition("TECH"),
        }
    )
    return repo


def unscoped(repo: AdopterRepo) -> None:
    """Both spaces' definitions written without a scope, for a test of the places
    alone: the scopes joined with the assignment are tested on their own (DEC-001
    point 1), and a definition with no scope is reported, never failed."""
    repo.write(
        {
            f"{DEFINITIONS}/user.md": _definition("USER", scope=UNSCOPED),
            f"{DEFINITIONS}/technical.md": _definition("TECH", scope=UNSCOPED),
        }
    )


def outside_every_space(repo: AdopterRepo) -> None:
    """The user definition's scope leaves `docs/drafts/` out, so a page there lies in
    the user space, under its root, and in no definition's scope: no rule of LDOC
    binds on it (COR-051 point 7; DEC-001 point 3)."""
    scope = {"paths": ["docs/**", "README.md"], "exclude": ["docs/drafts/**"]}
    repo.write({f"{DEFINITIONS}/user.md": _definition("USER", scope=scope)})


def left_out(*pages: str) -> dict[str, str]:
    """The report on the user space's pages its definition's scope leaves out (DEC-001
    point 2): no rule binds on them through it, so nothing is checked there."""
    named = pages[0] + (f" and {len(pages) - 1} other page(s)" if len(pages) > 1 else "")
    return {
        "severity": "report",
        "location": f"{DEFINITIONS}/user.md",
        "message": (
            f"the scope of space 'user''s definition, {DEFINITIONS}/user.md, leaves out {named} "
            "of the space's pages, so neither living-docs:LDOC's rules nor the space's own bind "
            "on them through it (COR-051 point 7). Widen the scope to them — its `paths` name "
            "the space's root and the places assigned to it, and a placeholder such as `<root>` "
            "names nothing — or move them to the space they belong to. A scope may leave pages "
            "out on purpose, with `exclude`, so this is reported, never failed (DEC-001 point 2)."
        ),
    }


def run(repo: AdopterRepo) -> dict[str, Any]:
    """The validator's findings document, run as the backbone runs it."""
    completed = subprocess.run(
        [sys.executable, str(repo.root / SCRIPT), "--json"],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def errors(document: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [(f["location"], f["message"]) for f in document["findings"] if f["severity"] == "error"]


def only_error(document: Mapping[str, Any]) -> tuple[str, str]:
    (found,) = errors(document)
    return found


# --- a clean project, and what is dormant -----------------------------------------------


def test_a_clean_project_answers_with_no_finding_and_names_the_readers(
    project: AdopterRepo,
) -> None:
    document = run(project)
    assert document["findings"] == []
    summary = document["summary"]
    assert summary[1] == (
        "user: 2 page(s); entry point README.md, a page; definition "
        "tech-docs/living-docs/rule-sets/user.md."
    )
    assert summary[2] == (
        "technical: 1 page(s); entry point tech-docs/README.md, a page; definition "
        "tech-docs/living-docs/rule-sets/technical.md."
    )
    assert "1 decision record(s)" in summary[3] and "2 in the definitions location" in summary[3]
    assert summary[4] == (
        "readers (pkit::documentation:readers): maintainer, user; 3 page reader(s) checked."
    )


def test_the_validator_is_a_member_of_pkit_validate(project: AdopterRepo) -> None:
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 0, result.output
    assert "living-docs:spaces" in result.output
    assert "readers (pkit::documentation:readers): maintainer, user" in result.output
    project.write({"docs/guide.md": "---\nreader: 42\nkind: signpost\n---\n"})
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 1
    assert "docs/guide.md:/reader" in result.output
    # A well-formed reader the readers point does not hold fails the page too.
    project.write({"docs/guide.md": "---\nreader: guest\nkind: signpost\n---\n"})
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 1
    assert "reader 'guest', which does not resolve" in result.output


# --- places and their assignment (DEC-001 point 1) ---------------------------------------


def test_an_out_of_root_place_holding_a_document_needs_an_assignment(project: AdopterRepo) -> None:
    declare(project, places=["README.md", "CONTRIBUTING.md"])
    project.write({"CONTRIBUTING.md": "# Contributing\n"})
    location, message = only_error(run(project))
    assert location == f"{CONFIG}:/friction/places/1"
    assert (
        "lies outside every documentation root and holds a document nothing else claims" in message
    )
    assert "add `CONTRIBUTING.md: <space>` under `places`" in message


def test_an_out_of_root_place_holding_only_what_something_else_claims_needs_none(
    project: AdopterRepo,
) -> None:
    declare(project, places=["README.md", "records/"])
    project.write({"records/ADR-002-other.md": RECORD.replace("ADR-001", "ADR-002")})
    assert errors(run(project)) == []


def test_a_records_folder_s_readme_outside_every_root_still_needs_an_assignment(
    project: AdopterRepo,
) -> None:
    """Only a place of rule sets is set apart: a README beside records owes one."""
    declare(project, places=["README.md", "records/"])
    project.write(
        {
            "records/ADR-002-other.md": RECORD.replace("ADR-001", "ADR-002"),
            "records/README.md": "# Records\n",
        }
    )
    location, message = only_error(run(project))
    assert location == f"{CONFIG}:/friction/places/1"
    assert "holds a document nothing else claims (records/README.md)" in message


#: A folder of rule sets the change of the internal root left behind outside every
#: root, declared as a place by `pkit config set docs.internal` (COR-051 point 6).
OLD_RULE_SETS = "old-docs/rule-sets"
SIGNPOST = f"{OLD_RULE_SETS}/README.md"
OLD_SET = "---\nrule-set: OLD\nversion: 1.0.0\nrules: {}\n---\n"
#: What a place of rule sets passed over is, as the validator words it.
PASSED_OVER = (
    "is declared to hold rule sets, gives no type, lies outside every documentation root and "
    "is assigned to no space"
)


def _rule_sets_left_behind(project: AdopterRepo, signpost: str, **declared: Any) -> None:
    declare(project, places=["README.md", OLD_RULE_SETS], **declared)
    project.write({f"{OLD_RULE_SETS}/old.md": OLD_SET, SIGNPOST: signpost})


def test_a_place_of_rule_sets_outside_every_root_owes_no_assignment(
    project: AdopterRepo,
) -> None:
    """Its signpost is in no space: no page, no unclassified document (DEC-001 point 1)."""
    _rule_sets_left_behind(project, "# Rule sets\n")
    document = run(project)
    assert document["findings"] == []
    summary = document["summary"]
    assert summary[0].startswith(
        "2 space(s); roots docs/ (user) and tech-docs/ (internal); 2 project place(s), "
        "1 assigned, 1 of rule sets outside every root in no space;"
    )
    assert summary[1].startswith("user: 2 page(s);")
    assert summary[3].endswith("0 unclassified document(s) for onboarding (DEC-001 point 4).")


def test_a_signpost_declaring_a_page_kind_there_is_reported_never_failed(
    project: AdopterRepo,
) -> None:
    _rule_sets_left_behind(project, "---\nreader: user\nkind: signpost\n---\n\n# Rule sets\n")
    document = run(project)
    assert errors(document) == []
    (finding,) = document["findings"]
    assert finding["severity"] == "report"
    assert finding["location"] == f"{SIGNPOST}:/kind"
    assert finding["message"] == (
        f"{SIGNPOST} declares its page kind, but it lies only in project place "
        f"'{OLD_RULE_SETS}', which {PASSED_OVER}, so it is no page and no space counts it. To "
        f"make it a page, add `{OLD_RULE_SETS}: <space>` under `places` in {LD_CONFIG}, naming "
        "one of ['user', 'technical'] (DEC-001 point 1)."
    )
    assert document["summary"][1].startswith("user: 2 page(s);")


def test_a_place_of_rule_sets_once_assigned_gives_its_space_as_any_place(
    project: AdopterRepo,
) -> None:
    unscoped(project)
    signpost = "---\nreader: user\nkind: signpost\n---\n\n# Rule sets\n"
    _rule_sets_left_behind(
        project, signpost, assignments={"README.md": "user", OLD_RULE_SETS: "user"}
    )
    document = run(project)
    assert errors(document) == []
    assert document["summary"][1].startswith("user: 3 page(s);")
    assert "of rule sets outside every root in no space" not in document["summary"][0]
    _rule_sets_left_behind(
        project, "# Rule sets\n", assignments={"README.md": "user", OLD_RULE_SETS: "user"}
    )
    assert run(project)["summary"][3].endswith(
        "1 unclassified document(s) for onboarding (DEC-001 point 4)."
    )


def test_a_place_of_rule_sets_given_a_type_is_held_to_an_assignment_as_any_place(
    project: AdopterRepo,
) -> None:
    """A type is the project's aim at the spaces, so nothing is set apart."""
    typed: Any = {"path": OLD_RULE_SETS, "type": "living-docs:page"}
    declare(project, places=["README.md", typed])
    project.write(
        {
            f"{OLD_RULE_SETS}/old.md": OLD_SET,
            SIGNPOST: "---\nreader: user\nkind: signpost\n---\n\n# Rule sets\n",
        }
    )
    location, message = only_error(run(project))
    assert location == f"{CONFIG}:/friction/places/1"
    assert f"holds a document nothing else claims ({SIGNPOST})" in message


def test_a_rule_set_folder_s_signpost_under_a_root_stays_a_page_of_its_space(
    project: AdopterRepo,
) -> None:
    """The default folder lies under the internal root, so nothing is set apart."""
    project.write(
        {
            "tech-docs/rule-sets/cmn.md": OLD_SET.replace("OLD", "CMN"),
            "tech-docs/rule-sets/README.md": (
                "---\nreader: maintainer\nkind: signpost\n---\n\n# Rule sets\n"
            ),
        }
    )
    document = run(project)
    assert document["findings"] == []
    assert document["summary"][2].startswith("technical: 2 page(s);")


def test_a_signpost_also_in_an_unassigned_place_of_no_rule_sets_owes_it_an_assignment(
    project: AdopterRepo,
) -> None:
    """Setting the place of rule sets apart leaves every other place as it is."""
    declare(project, places=["README.md", "old-docs", OLD_RULE_SETS])
    project.write({f"{OLD_RULE_SETS}/old.md": OLD_SET, SIGNPOST: "# Rule sets\n"})
    location, message = only_error(run(project))
    assert location == f"{CONFIG}:/friction/places/1"
    assert "project place 'old-docs' lies outside every documentation root" in message
    assert f"({SIGNPOST})" in message


@pytest.mark.parametrize(("rule_sets", "held"), [({"component": None}, True), (None, False)])
def test_a_place_holds_rule_sets_as_the_backbone_s_answer_marks_it(
    rule_sets: Any, held: bool
) -> None:
    """Read from the answer's `rule_sets`, never from the path: a place the answer
    does not mark, or an answer without the key, holds none."""
    artefacts = _library("artefacts")
    place = {"source": "project", "declared": True, "written": OLD_RULE_SETS}
    answer = {
        "schema_version": 1,
        "roots": {"user": "docs", "internal": "tech-docs"},
        "places": [place if rule_sets is None else {**place, "rule_sets": rule_sets}],
        "files": [],
        "artefacts": [],
        "types": {},
    }
    (read,) = artefacts.reading_of(answer).places
    assert read.rule_sets is held


def test_an_entry_point_in_a_place_of_rule_sets_set_apart_names_the_place(
    project: AdopterRepo,
) -> None:
    spaces = {
        "user": {"entry-point": SIGNPOST, "definition": f"{DEFINITIONS}/user.md"},
        "technical": {
            "entry-point": "tech-docs/README.md",
            "definition": f"{DEFINITIONS}/technical.md",
        },
    }
    _rule_sets_left_behind(project, "# Rule sets\n", spaces=spaces)
    location, message = only_error(run(project))
    assert location == f"{LD_CONFIG}:/spaces/user/entry-point"
    assert f"lies only in project place '{OLD_RULE_SETS}', which {PASSED_OVER}" in message


def test_an_assignment_names_a_declared_place_and_a_declared_space(project: AdopterRepo) -> None:
    declare(
        project,
        places=["README.md", "NOTES.md"],
        assignments={"README.md": "user", "./NOTES.md/": "readers", "GHOST.md": "user"},
    )
    found = errors(run(project))
    assert [location for location, _ in found] == [
        f"{LD_CONFIG}:/places/.~1NOTES.md~1",
        f"{LD_CONFIG}:/places/GHOST.md",
    ]
    # The join is a normalised path: `./NOTES.md/` is NOTES.md, so only its space is wrong.
    assert "to space 'readers', which is not a space of this project" in found[0][1]
    assert "which `friction.places` in .pkit/project/config.yaml does not declare" in found[1][1]


def test_a_place_is_assigned_to_exactly_one_space(project: AdopterRepo) -> None:
    declare(project, assignments={"README.md": "user", "./README.md": "technical"})
    location, message = only_error(run(project))
    assert location == f"{LD_CONFIG}:/places/.~1README.md"
    assert "the place already assigned as 'README.md'" in message


@pytest.mark.parametrize("place", ["docs/", "docs", "docs/**", "**/*.md", ".", "**"])
def test_a_place_equal_to_or_enclosing_a_root_is_refused(project: AdopterRepo, place: str) -> None:
    declare(project, places=["README.md", place])
    found = errors(run(project))
    assert found[0][0] == f"{CONFIG}:/friction/places/1"
    assert "is equal to or encloses the user root 'docs'" in found[0][1]


def test_a_place_inside_a_root_is_not_refused_and_takes_the_root_s_space(
    project: AdopterRepo,
) -> None:
    declare(project, places=["README.md", "docs/*.md"])
    document = run(project)
    assert errors(document) == []
    assert document["summary"][1].startswith("user: 2 page(s)")


def test_the_most_specific_place_wins(project: AdopterRepo) -> None:
    """A project place inside the user root, assigned to the technical space, takes
    its pages from the root: a project place beats a root."""
    declare(
        project,
        places=["README.md", "docs/internal/"],
        assignments={"README.md": "user", "docs/internal/": "technical"},
    )
    project.write({"docs/internal/notes.md": PAGE})
    summary = run(project)["summary"]
    assert summary[1].startswith("user: 2 page(s)")
    assert summary[2].startswith("technical: 2 page(s)")


def test_a_file_two_project_places_claim_at_equal_rank_is_an_error(
    project: AdopterRepo,
) -> None:
    declare(
        project,
        places=["README.md", "extra/*.md", "extra/[ab].md"],
        assignments={"README.md": "user", "extra/*.md": "user", "extra/[ab].md": "technical"},
    )
    unscoped(project)
    project.write({"extra/a.md": PAGE})
    location, message = only_error(run(project))
    assert location == f"{CONFIG}:/friction/places/2"
    assert (
        "'extra/*.md' and 'extra/[ab].md' both claim extra/a.md at equal rank in the backbone's "
        "order of places (COR-056 point 3)" in message
    )


def test_the_backbone_s_order_of_places_gives_a_page_its_space(project: AdopterRepo) -> None:
    """DEC-001 point 1 takes the core's order (COR-056 point 3): at equal length of
    literal part, a glob beats a folder. `extra/` and `extra/*.md` both have the
    literal part `extra/`, so the glob gives extra/a.md its space. The capability
    reads the order from the backbone and ranks no place itself."""
    declare(
        project,
        places=["README.md", "extra/", "extra/*.md"],
        assignments={"README.md": "user", "extra/": "user", "extra/*.md": "technical"},
    )
    unscoped(project)
    project.write({"extra/a.md": PAGE, "extra/deeper/b.md": PAGE})
    document = run(project)
    assert errors(document) == []
    # extra/a.md takes the glob's space; extra/deeper/b.md only the folder matches.
    assert document["summary"][1].startswith("user: 3 page(s)")
    assert document["summary"][2].startswith("technical: 2 page(s)")


def test_a_file_without_front_matter_in_nested_places_is_reported_never_failed(
    project: AdopterRepo,
) -> None:
    """The backbone ranks the places of artefacts only. A file with no front matter
    holds no artefact, so where its places would give it different spaces, or one
    lies outside every root with no assignment, which holds it cannot be told: it
    is reported and unclassified, never a false failure of a place it may not
    belong to."""
    declare(
        project,
        places=["README.md", "extra/", "extra/README.md"],
        assignments={"README.md": "user", "extra/README.md": "technical"},
    )
    project.write({"extra/README.md": "# Extra\n"})
    document = run(project)
    assert errors(document) == []
    (report,) = [f for f in document["findings"] if f["location"] == "extra/README.md"]
    assert report["severity"] == "report"
    assert "holds no artefact — no front matter the backbone reads" in report["message"]
    assert "project place 'extra/', project place 'extra/README.md'" in report["message"]
    assert "1 unclassified document(s)" in document["summary"][3]


def test_an_entry_point_without_front_matter_in_nested_places_is_not_failed(
    project: AdopterRepo,
) -> None:
    """An entry point not yet a page, in places that would give it different spaces:
    one of them gives its space, so it is no failure (DEC-001 point 1)."""
    declare(
        project,
        places=["README.md", "guides/", "guides/api/"],
        assignments={"README.md": "user", "guides/": "user", "guides/api/": "technical"},
        spaces={
            "user": {"entry-point": "README.md", "definition": f"{DEFINITIONS}/user.md"},
            "technical": {
                "entry-point": "guides/api/README.md",
                "definition": f"{DEFINITIONS}/technical.md",
            },
        },
    )
    project.write({"guides/api/README.md": "# API\n"})
    document = run(project)
    assert errors(document) == []
    assert (
        "entry point guides/api/README.md, not yet a page (its space not told)"
        in document["summary"][2]
    )


def test_a_file_without_front_matter_whose_places_agree_takes_their_space(
    project: AdopterRepo,
) -> None:
    """Where every place of a file without front matter gives the same space and none
    lies outside every root, the order between them is moot."""
    declare(project, places=["README.md", "docs/guides/"], assignments={"README.md": "user"})
    project.write({"docs/guides/old.md": "# Old\n"})
    document = run(project)
    assert errors(document) == []
    assert [f for f in document["findings"] if f["location"] == "docs/guides/old.md"] == []
    assert "1 unclassified document(s)" in document["summary"][3]


def test_a_file_without_front_matter_only_in_unassigned_places_needs_an_assignment(
    project: AdopterRepo,
) -> None:
    """Every place of the file lies outside every root with no assignment, so
    whichever holds it owes one: that fails, without ranking the places."""
    declare(project, places=["README.md", "extra/", "extra/sub/"])
    project.write({"extra/sub/a.md": "# A\n"})
    location, message = only_error(run(project))
    assert location == "extra/sub/a.md"
    assert "whichever of them holds it, that place needs an assignment" in message


def test_an_entry_point_without_front_matter_only_in_places_of_no_space_fails(
    project: AdopterRepo,
) -> None:
    declare(
        project,
        places=["README.md", "extra/", "extra/sub/"],
        spaces={
            "user": {"entry-point": "README.md", "definition": f"{DEFINITIONS}/user.md"},
            "technical": {
                "entry-point": "extra/sub/README.md",
                "definition": f"{DEFINITIONS}/technical.md",
            },
        },
    )
    project.write({"extra/sub/README.md": "# Sub\n"})
    found = dict(errors(run(project)))
    message = found[f"{LD_CONFIG}:/spaces/technical/entry-point"]
    assert "'extra/sub/README.md', lies only in places of no space;" in message
    assert "whichever of them holds it" in found["extra/sub/README.md"]


def test_a_file_without_front_matter_in_an_assigned_place_and_a_root_of_one_space(
    project: AdopterRepo,
) -> None:
    """An assigned place outside every root owes no assignment, so where it and the
    root give the file one space, the order between them is moot: no report."""
    declare(
        project,
        places=["README.md", "**/CHANGES.md"],
        assignments={"README.md": "user", "**/CHANGES.md": "user"},
    )
    project.write({"docs/CHANGES.md": "# Changes\n"})
    document = run(project)
    assert errors(document) == []
    assert [f for f in document["findings"] if f["location"] == "docs/CHANGES.md"] == []


def test_the_capability_s_scripts_rank_no_place_themselves() -> None:
    """The order of places is the backbone's answer, `ranked_places` (COR-056 point
    6); no script of the capability measures a place's specificity."""
    for path in sorted((CAPABILITY / "scripts").rglob("*.py")):
        code = path.read_text(encoding="utf-8")
        assert "specificity" not in code, path
        assert "literal_text_prefix" not in code, path


# --- what is never a page (DEC-001 points 1 and 4) ---------------------------------------


def test_a_decision_record_that_declares_a_page_kind_is_an_error(project: AdopterRepo) -> None:
    """A decision record under a root that declares a page kind takes the page type
    (COR-056 point 4); it is never a page, so validation fails it (DEC-001 point 4).
    One that names a reader alone declares no kind, takes no type, and is a record."""
    adr = "tech-docs/architecture/decisions/ADR-001-a-decision.md"
    project.write(
        {adr: RECORD.replace("status: accepted\n", "status: accepted\nreader: maintainer\n")}
    )
    document = run(project)
    assert errors(document) == []
    assert "1 decision record(s)" in document["summary"][3]
    project.write({adr: RECORD.replace("status: accepted\n", "status: accepted\nkind: signpost\n")})
    document = run(project)
    location, message = only_error(document)
    assert location == f"{adr}:/kind"
    assert (
        "is a decision record (ADR-001), an anchor target (COR-050), and declares a page kind"
        in (message)
    )
    assert "so it takes the type living-docs:page, or counts as it in a tie" in message
    assert "remove `kind`" in message
    assert "1 decision record(s)" in document["summary"][3]


def test_a_decision_record_in_an_untyped_out_of_root_place_declaring_a_kind_fails_too(
    project: AdopterRepo,
) -> None:
    declare(project, places=["README.md", "records/"], assignments={"README.md": "user"})
    project.write({"records/ADR-002-other.md": RECORD.replace("ADR-001", "ADR-002") + ""})
    assert errors(run(project)) == []
    project.write(
        {
            "records/ADR-002-other.md": RECORD.replace("ADR-001", "ADR-002").replace(
                "status: accepted\n", "status: accepted\nkind: signpost\n"
            )
        }
    )
    location, message = only_error(run(project))
    assert location == "records/ADR-002-other.md:/kind"
    assert "outside every root that gives no type, so it would be a page" in message


def test_a_rule_set_file_is_never_a_page_and_its_fields_are_the_rule_set_pass_s(
    project: AdopterRepo,
) -> None:
    """A rule-set file holds rules, each of the backbone's type for rules (COR-056
    point 3). living-docs reads none of its fields: the rule-sets pass refuses a
    key the rule-set shape does not know."""
    rule_set = "tech-docs/rule-sets/cmn.md"
    front = "rule-set: CMN\nversion: 1.0.0\nrules: {}\nreader: user\nkind: signpost\n"
    project.write({rule_set: f"---\n{front}---\n"})
    document = run(project)
    assert errors(document) == []
    assert "1 rule-set file(s)" in document["summary"][3]
    refused = [f.pointer for f in rs.validate_rule_sets(project.root).errors]
    assert "/reader" in refused and "/kind" in refused


def _install_component_with_place(
    repo: AdopterRepo, friction: Mapping[str, Any] | None = None
) -> None:
    """Another capability, declaring a place under the internal root — or, with
    `friction`, what that block says."""
    cap = repo.root / ".pkit" / "capabilities" / "analysis-test"
    cap.mkdir(parents=True)
    (cap / "package.yaml").write_text(
        _yaml(
            {
                "schema_version": 1,
                "component": {"kind": "capability", "name": "analysis-test", "version": "0.1.0"},
                "description": "An analysis capability, for the test.",
                "requires_backbone": ">=0.0.0",
                "docs": {"locations": {"analysis": {"path": "analysis"}}},
                "friction": dict(friction or {"places": [{"location": "analysis", "path": "."}]}),
            }
        ),
        encoding="utf-8",
    )
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name="analysis-test",
            manifest=".pkit/capabilities/analysis-test/project/manifest.yaml",
            origin="incubated-in-repo",
        )
    )
    write_backbone_manifest(repo.root, backbone)


def test_a_document_of_another_component_s_type_is_never_a_page(project: AdopterRepo) -> None:
    """The type the backbone gives says whose a document is (DEC-001 point 1): one of
    another component's type is that component's, never a page, and its own fields
    are its owner's — a `kind` it carries is never read as a page kind."""
    _install_component_with_place(
        project,
        {
            "types": {"use-case": {"description": "A use case."}},
            "places": [{"location": "analysis", "path": ".", "type": "use-case"}],
        },
    )
    project.write({"tech-docs/analysis/uc-001.md": "---\nid: UC-001\nkind: main\n---\n"})
    document = run(project)
    assert errors(document) == []
    assert "1 of another component" in document["summary"][3]
    assert "0 unclassified document(s)" in document["summary"][3]
    assert document["summary"][2].startswith("technical: 1 page(s)")


def test_a_document_that_counts_as_the_page_type_in_a_tie_is_a_page(project: AdopterRepo) -> None:
    """Another component's typed place over the whole internal root ties with the
    root's page type (COR-056 point 3). While the tie stands the document counts
    as each type, so it is a page until the tie is mended (DEC-001 point 4)."""
    _install_component_with_place(
        project,
        {
            "types": {"note": {"description": "A note."}},
            "places": [{"location": "whole", "path": "**", "type": "note"}],
        },
    )
    package = project.root / ".pkit" / "capabilities" / "analysis-test" / "package.yaml"
    package.write_text(
        package.read_text(encoding="utf-8").replace(
            "analysis:\n      path: analysis", "whole:\n      path: .\n      root: internal"
        ),
        encoding="utf-8",
    )
    found = _artefacts(project)
    (readme,) = [a for a in found["artefacts"] if a["location"] == "tech-docs/README.md"]
    assert readme["type"] is None
    assert {tied["type"] for tied in readme["type_conflict"]} == {
        "living-docs:page",
        "analysis-test:note",
    }
    document = run(project)
    assert errors(document) == []
    assert document["summary"][2].startswith("technical: 1 page(s)")


def test_a_document_of_no_type_in_another_component_s_place_is_that_component_s(
    project: AdopterRepo,
) -> None:
    """A component's place that names no type gives none and shadows no other place
    (COR-056 point 3). A document there that declares no page kind takes no type
    and stays the component's. One that declares a page kind takes the page type
    from the root around it, so it is a page."""
    _install_component_with_place(project)
    project.write({"tech-docs/analysis/uc-001.md": "---\nid: UC-001\n---\n"})
    document = run(project)
    assert errors(document) == []
    assert "1 of another component" in document["summary"][3]
    project.write(
        {"tech-docs/analysis/uc-001.md": "---\nreader: maintainer\nkind: signpost\n---\n\n# UC\n"}
    )
    document = run(project)
    assert errors(document) == []
    assert "0 of another component" in document["summary"][3]
    assert document["summary"][2].startswith("technical: 2 page(s)")


def test_a_document_another_component_holds_is_never_a_page_nor_unclassified(
    project: AdopterRepo,
) -> None:
    """A folder of held documents (COR-050 point 1) under the internal root: no place
    walks its files, and each is its owner's — counted "of another component",
    never an unclassified document, and never a page (DEC-001 point 1)."""
    _install_component_with_place(project, {"held": [{"location": "analysis", "path": "records"}]})
    record = "tech-docs/analysis/records/2026-10-01-run.md"
    project.write({record: "---\ndate: '2026-10-01'\n---\n\n# A run\n"})
    document = run(project)
    assert errors(document) == []
    assert "1 of another component" in document["summary"][3]
    assert "0 unclassified document(s)" in document["summary"][3]
    # Its own fields are its holder's: a `kind` there is never read as a page kind.
    project.write({record: "---\ndate: '2026-10-01'\nreader: user\nkind: signpost\n---\n"})
    document = run(project)
    assert errors(document) == []
    assert "1 of another component" in document["summary"][3]


# --- entry points (DEC-001 point 1) ------------------------------------------------------


@pytest.mark.parametrize(
    ("entry", "problem"),
    [
        ("README.md", "belongs to space 'user', by its root or its assignment"),
        ("docs/guide.md", "belongs to space 'user', by its root or its assignment"),
        ("tech-docs/missing.md", "is not a Markdown document of the working tree"),
        (
            "tech-docs/architecture/decisions/ADR-001-a-decision.md",
            "is a decision record (ADR-001), an anchor target (COR-050), never a page",
        ),
        ("notes/elsewhere.md", "lies in no place of any space"),
    ],
)
def test_an_entry_point_outside_its_space_is_an_error(
    project: AdopterRepo, entry: str, problem: str
) -> None:
    project.write({"notes/elsewhere.md": PAGE})
    declare(
        project,
        spaces={
            "user": {"entry-point": "README.md", "definition": f"{DEFINITIONS}/user.md"},
            "technical": {"entry-point": entry, "definition": f"{DEFINITIONS}/technical.md"},
        },
    )
    location, message = only_error(run(project))
    assert location == f"{LD_CONFIG}:/spaces/technical/entry-point"
    assert f"the entry point of space 'technical', {entry!r}, {problem}" in message


def test_an_entry_point_not_yet_a_page_is_shown_not_failed(project: AdopterRepo) -> None:
    project.write({"README.md": "# Project\n"})
    document = run(project)
    assert errors(document) == []
    assert "entry point README.md, not yet a page" in document["summary"][1]


# --- pages' own fields (DEC-001 point 4) -------------------------------------------------


@pytest.mark.parametrize(
    ("front", "location"),
    [
        ("reader: User Guide\nkind: signpost", "docs/guide.md:/reader"),
        ("reader: [user, maintainer]\nkind: signpost", "docs/guide.md:/reader"),
        ("reader: user\nkind: 3", "docs/guide.md:/kind"),
    ],
)
def test_a_page_with_a_wrong_reader_or_kind_field_fails(
    project: AdopterRepo, front: str, location: str
) -> None:
    project.write({"docs/guide.md": f"---\n{front}\n---\n\n# Guide\n"})
    found_location, message = only_error(run(project))
    assert found_location == location
    assert "schemas/page.schema.json; DEC-001 point 4" in message


def test_a_page_rs_ldoc_003_binds_on_names_its_reader(project: AdopterRepo) -> None:
    """Where RS-LDOC-003 binds, the part its set declares is checked: the page names
    its reader (DEC-001 point 3; COR-051 point 2)."""
    project.write({"docs/guide.md": "---\nkind: signpost\n---\n\n# Guide\n"})
    assert only_error(run(project)) == (
        "docs/guide.md",
        "docs/guide.md names no reader, and RS-LDOC-003 binds on it: the page names its reader "
        "in its `reader` field, a word that names a reader the readers point holds — add "
        "`reader: <id>` (DEC-001 point 3; RS-LDOC-003).",
    )


@pytest.mark.parametrize(
    "front",
    ["kind: signpost", "reader: User Guide\nkind: signpost", "reader: guest\nkind: signpost"],
)
def test_a_page_rs_ldoc_003_does_not_bind_on_has_no_reader_read(
    project: AdopterRepo, front: str
) -> None:
    """A check enforces its part of a rule only where the rule binds (COR-051 point 2):
    a page no definition's scope selects is bound by no LDOC rule, so its reader is
    not read — absent, malformed or one the readers point does not hold."""
    outside_every_space(project)
    project.write({"docs/drafts/guide.md": f"---\n{front}\n---\n\n# Guide\n"})
    document = run(project)
    assert document["findings"] == [left_out("docs/drafts/guide.md")]
    (line,) = [line for line in document["summary"] if line.startswith("readers")]
    assert line == (
        "readers (pkit::documentation:readers): maintainer, user; 3 page reader(s) checked; "
        "1 page(s) RS-LDOC-003 does not bind on, not checked."
    )


def test_a_document_carrying_neither_field_is_unclassified_for_onboarding(
    project: AdopterRepo,
) -> None:
    project.write({"docs/old.md": "# An old page\n"})
    document = run(project)
    assert errors(document) == []
    assert "1 unclassified document(s) for onboarding" in document["summary"][3]


@pytest.mark.parametrize("front", ["reader: user", "reader: user\nkind: ''", "kind:"])
def test_a_document_that_declares_no_page_kind_takes_no_type_and_is_unclassified(
    project: AdopterRepo, front: str
) -> None:
    """The page type's kind field gates it (COR-056 point 4; DEC-001 point 4): a
    document in a root that declares no page kind — the field absent or empty —
    takes no type, so it is no page."""
    project.write({"docs/old.md": f"---\n{front}\n---\n\n# An old page\n"})
    document = run(project)
    assert errors(document) == []
    assert document["summary"][1].startswith("user: 2 page(s)")
    assert "1 unclassified document(s) for onboarding" in document["summary"][3]


def test_a_page_left_unanchored_counts_unless_its_block_gives_an_accepted_reason(
    project: AdopterRepo,
) -> None:
    """DEC-001 point 8: onboarding leaves no page unanchored without an accepted reason —
    the reason the page's friction block gives for having no anchors, the core's
    `unanchored-because` (COR-050 point 1), read as the backbone reads it. Counted
    apart, never failed; an anchored page is in neither count."""
    reason = "A signpost: nothing it lists is its own."
    project.write(
        {
            "docs/sponsor.md": (
                "---\nreader: user\nkind: signpost\npkit:\n  friction:\n"
                f"    unanchored-because: '{reason}'\n---\n\n# Sponsor\n"
            ),
            "docs/anchored.md": (
                "---\nreader: user\nkind: signpost\npkit:\n  friction:\n"
                "    anchors: {path: [README.md]}\n---\n\n# Anchored\n"
            ),
        }
    )
    document = run(project)
    assert errors(document) == []
    (line,) = [line for line in document["summary"] if line.startswith("pages unanchored:")]
    assert line == (
        "pages unanchored: 3 without an accepted reason, 1 accepted with one "
        "(`unanchored-because`); onboarding leaves none without (DEC-001 point 8)."
    )

    human = subprocess.run(
        [sys.executable, str(project.root / SCRIPT)],
        cwd=project.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert human.returncode == 0, human.stderr
    lines = human.stdout.splitlines()
    forgotten = lines.index(
        "page(s) unanchored without an accepted reason, for onboarding to anchor or accept (3):"
    )
    assert lines[forgotten + 1 : forgotten + 4] == [
        "  README.md",
        "  docs/guide.md",
        "  tech-docs/README.md",
    ]
    accepted = lines.index("page(s) accepted unanchored, each with its reason (1):")
    assert lines[accepted + 1] == f"  docs/sponsor.md — {reason}"


def test_a_page_anchored_only_on_parts_is_anchored(project: AdopterRepo) -> None:
    """A part anchor is an anchor (COR-050 point 2): a page whose only anchors name a
    record's point, another page's section or its lead is anchored, and onboarding
    leaves it out of the pages still to anchor (DEC-001 point 8). Each anchor names a
    live part, as the backbone resolves it, so validation fails none of them."""

    def page(anchors: str) -> str:
        return (
            "---\nreader: user\nkind: signpost\npkit:\n  friction:\n"
            f"    anchors: {anchors}\n---\n\n# Page\n"
        )

    project.write(
        {
            "docs/cli.md": (
                "---\nreader: user\nkind: signpost\npkit:\n  friction:\n"
                "    anchors: {path: [README.md]}\n---\n\n# CLI\n\nThe lead.\n\n"
                "## Output\n\nWhere it writes.\n"
            ),
            "docs/section.md": page('{artefact: ["docs/cli.md#output"]}'),
            "docs/lead.md": page('{artefact: ["docs/cli.md#"]}'),
            "docs/point.md": page('{record: ["living-docs:DEC-001#3"]}'),
        }
    )
    document = run(project)
    assert errors(document) == []
    (line,) = [line for line in document["summary"] if line.startswith("pages unanchored:")]
    assert line.startswith("pages unanchored: 3 without an accepted reason,")
    human = subprocess.run(
        [sys.executable, str(project.root / SCRIPT)],
        cwd=project.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert human.returncode == 0, human.stderr
    lines = human.stdout.splitlines()
    forgotten = lines.index(
        "page(s) unanchored without an accepted reason, for onboarding to anchor or accept (3):"
    )
    assert lines[forgotten + 1 : forgotten + 4] == [
        "  README.md",
        "  docs/guide.md",
        "  tech-docs/README.md",
    ]
    # The backbone reads each as a live part: the one reading of a part anchor.
    listed = json.loads(CliRunner().invoke(main, ["friction", "artefacts", "--json"]).output)[
        "artefacts"
    ]
    parts = {
        artefact["path"]: [(part["kind"], part["value"]) for part in artefact["part_anchors"]]
        for artefact in listed
        if artefact["path"] in {"docs/section.md", "docs/lead.md", "docs/point.md"}
    }
    assert parts == {
        "docs/section.md": [("artefact", "docs/cli.md#output")],
        "docs/lead.md": [("artefact", "docs/cli.md#")],
        "docs/point.md": [("record", "living-docs:DEC-001#3")],
    }


# --- definitions (DEC-001 point 2) -------------------------------------------------------


def test_a_definition_inherits_the_shared_method(project: AdopterRepo) -> None:
    project.write({f"{DEFINITIONS}/technical.md": _definition("TECH", inherits=["USER@1"])})
    location, message = only_error(run(project))
    assert location == f"{LD_CONFIG}:/spaces/technical/definition"
    assert (
        "does not inherit the shared method: add `living-docs:LDOC@1` to its `inherits`" in message
    )


def test_a_definition_lives_in_the_definitions_location_s_rule_sets(project: AdopterRepo) -> None:
    project.write({"tech-docs/rule-sets/technical.md": _definition("TECH")})
    declare(
        project,
        spaces={
            "user": {"entry-point": "README.md", "definition": f"{DEFINITIONS}/user.md"},
            "technical": {
                "entry-point": "tech-docs/README.md",
                "definition": "tech-docs/rule-sets/technical.md",
            },
        },
    )
    location, message = only_error(run(project))
    assert location == f"{LD_CONFIG}:/spaces/technical/definition"
    assert f"lies outside {DEFINITIONS}/" in message


def test_a_definition_with_no_scope_is_reported_naming_the_scope_to_give_it(
    project: AdopterRepo,
) -> None:
    """A definition with no scope selects no page, so no rule binds through it
    (COR-051 point 7): reported, never failed, naming the scope that selects the
    space's pages — its root, the places assigned to it, by the page type — and the
    places a scope that selects by type asks to give the page type (DEC-001 points
    1 and 2). Nothing is checked on the space's pages meanwhile."""
    declare(
        project,
        places=["README.md", "docs/internal/"],
        assignments={"README.md": "user", "docs/internal/": "technical"},
    )
    unscoped(project)
    project.write({"docs/ref.md": _page("reference", "No title.\n")})
    document = run(project)
    assert errors(document) == []
    reports = {
        f["location"]: f["message"]
        for f in document["findings"]
        if f["severity"] == "report" and f["location"].startswith(DEFINITIONS)
    }
    assert reports == {
        f"{DEFINITIONS}/user.md": (
            f"the definition of space 'user', {DEFINITIONS}/user.md, carries no scope, so it "
            "selects no page itself: neither living-docs:LDOC's rules nor its own reach the "
            "space's pages through it, nor do the checks of their parts (COR-051 points 2 and "
            "7). Give it the scope of the space's pages, `scope: {paths: "
            "[docs/**, README.md], exclude: [docs/internal/], types: "
            "[living-docs:page]}` (DEC-001 point 2). Give README.md the page type in "
            "`friction.places` too, as a scope that selects by type asks (DEC-001 point 1)."
        ),
        f"{DEFINITIONS}/technical.md": (
            f"the definition of space 'technical', {DEFINITIONS}/technical.md, carries no scope, "
            "so it selects no page itself: neither living-docs:LDOC's rules nor its own reach "
            "the space's pages through it, nor do the checks of their parts (COR-051 points 2 "
            "and 7). Give it the scope of the space's pages, `scope: {paths: "
            "[tech-docs/**, docs/internal/], types: [living-docs:page]}` (DEC-001 point 2)."
        ),
    }
    assert _format_line(document).startswith(
        "page formats: not checked — RS-LDOC-004 binds on none of the 4 page(s)"
    )


def test_a_definition_whose_scope_leaves_its_pages_out_is_reported(project: AdopterRepo) -> None:
    """A scope whose path misses the root — a typo, say — leaves every page there out,
    so nothing is checked on them, and that is reported rather than silent: a scope
    may leave part of a space out on purpose, so never failed (DEC-001 point 2)."""
    project.write(
        {
            f"{DEFINITIONS}/user.md": _definition("USER", scope=["doc/**", "README.md"]),
            "docs/ref.md": _page("reference", "No title.\n"),
        }
    )
    document = run(project)
    assert document["findings"] == [left_out("docs/guide.md", "docs/ref.md")]


def test_a_definition_copied_with_the_template_s_placeholder_is_reported(
    project: AdopterRepo,
) -> None:
    """The template's `<root>` names no file: a definition copied without writing the
    space's paths is reported as soon as it exists, naming the paths to write, and
    the pages it leaves out besides (DEC-001 point 2)."""
    template = (CAPABILITY / "templates" / "space-definition.md").read_text(encoding="utf-8")
    project.write({f"{DEFINITIONS}/user.md": template.replace("rule-set: SPACE", "rule-set: USER")})
    document = run(project)
    # README.md, the place assigned to the user space outside the roots, fails point 1
    # on its own: the copied scope selects by type and names the place nowhere.
    assert [location for location, _message in errors(document)] == [f"{CONFIG}:/friction/places/0"]
    placeholder = {
        "severity": "report",
        "location": f"{DEFINITIONS}/user.md",
        "message": (
            f"the scope of space 'user''s definition, {DEFINITIONS}/user.md, still holds the "
            "template's placeholder `<root>/**`, which names no file: write the space's root "
            "and the places assigned to it in its place — `paths: [docs/**, README.md]` "
            "(DEC-001 point 2). Until then the join with the assignment fails each place "
            "assigned to the space that the scope misses (DEC-001 point 1)."
        ),
    }
    assert placeholder in document["findings"]
    assert left_out("docs/guide.md") in document["findings"]


def test_the_scope_named_for_nested_roots_leaves_the_inner_one_out(project: AdopterRepo) -> None:
    """With the internal root inside the user root, the user space's scope leaves the
    inner root out, and names back a place in it assigned to the user space; the
    technical space's scope leaves that place out (DEC-001 points 1 and 2)."""
    tech = "docs/tech/living-docs/rule-sets"
    declare(
        project,
        roots={"user": "docs/", "internal": "docs/tech/"},
        places=["README.md", "docs/tech/guide/"],
        assignments={"README.md": "user", "docs/tech/guide/": "user"},
        spaces={
            "user": {"entry-point": "README.md", "definition": f"{tech}/user.md"},
            "technical": {
                "entry-point": "docs/tech/README.md",
                "definition": f"{tech}/technical.md",
            },
        },
    )
    project.write(
        {
            "docs/tech/README.md": "---\nreader: maintainer\nkind: signpost\n---\n\n# Tech\n",
            f"{tech}/user.md": _definition("USER", scope=UNSCOPED),
            f"{tech}/technical.md": _definition("TECH", scope=UNSCOPED),
        }
    )
    reports = {
        f["location"]: f["message"]
        for f in run(project)["findings"]
        if f["severity"] == "report" and f["location"].startswith(tech)
    }
    assert (
        "`scope: {paths: [docs/**, README.md, docs/tech/guide/], exclude: [docs/tech/**], "
        "types: [living-docs:page]}`" in reports[f"{tech}/user.md"]
    )
    assert (
        "`scope: {paths: [docs/tech/**], exclude: [docs/tech/guide/], types: [living-docs:page]}`"
        in reports[f"{tech}/technical.md"]
    )


def test_a_reader_is_not_checked_while_rs_ldoc_003_is_not_accepted(project: AdopterRepo) -> None:
    """A rule of any status but accepted binds nothing (COR-051 point 4): no page's
    reader is read, and the summary says why."""
    ldoc = project.root / LD / "rule-sets" / "ldoc.md"
    accepted = "  RS-LDOC-003:\n    status: accepted\n"
    text = ldoc.read_text(encoding="utf-8")
    assert accepted in text
    ldoc.write_text(text.replace(accepted, "  RS-LDOC-003:\n    status: proposed\n"), "utf-8")
    project.write({"docs/guide.md": "---\nkind: signpost\n---\n\n# Guide\n"})
    document = run(project)
    assert document["findings"] == []
    (line,) = [line for line in document["summary"] if line.startswith("readers")]
    assert line == (
        "readers: not checked — RS-LDOC-003 is proposed, so it binds nothing (COR-051 point 4)."
    )


def test_a_space_definition_from_the_template_carries_a_scope_selecting_pages() -> None:
    """Creating a space gives its definition a scope (DEC-001 point 2): the template
    carries one, selecting by path and by the page type, its paths a placeholder
    the writer replaces with the space's root and places."""
    front = _template_front_matter("space-definition")
    assert front["scope"] == {"paths": ["<root>/**"], "types": ["living-docs:page"]}
    assert front["inherits"] == ["living-docs:LDOC@1"]


def test_a_definition_written_from_the_template_makes_ldoc_bind_on_its_space_s_pages(
    project: AdopterRepo,
) -> None:
    """The fixture's definitions are the template with their paths written in: LDOC's
    rules bind on every page of their spaces, so the structure and the reader are
    checked from the first page (DEC-001 point 2)."""
    document = run(project)
    assert document["findings"] == []
    assert _format_line(document).startswith(
        "page formats (RS-LDOC-004, accepted): 3 page(s) checked"
    )
    assert not _format_line(document).endswith("does not bind on, not checked.")


def test_a_space_without_a_definition_yet_is_reported(project: AdopterRepo) -> None:
    declare(project, spaces={"user": {"entry-point": "README.md"}})
    document = run(project)
    assert errors(document) == []
    reports = [f["location"] for f in document["findings"] if f["severity"] == "report"]
    assert reports == [f"{LD_CONFIG}:/spaces/user", f"{LD_CONFIG}:/spaces/technical"]


# --- the places, read through the backbone --------------------------------------------


def test_places_the_backbone_gives_no_reading_of_are_one_error_and_nothing_checked(
    project: AdopterRepo,
    pkit_on_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A backbone without the read command: the spaces cannot be told, which is
    one error — never a pass on no places."""
    old = tmp_path_factory.mktemp("old-pkit")
    (old / "pkit").write_text(
        '#!/bin/sh\nif [ "$1" = friction ]; then echo "Error: No such command." >&2; exit 2; fi\n'
        f'exec "{pkit_on_path}/pkit" "$@"\n',
        encoding="utf-8",
    )
    (old / "pkit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{old}{os.pathsep}{os.environ['PATH']}")
    document = run(project)
    location, message = only_error(document)
    assert location == CONFIG
    assert message.startswith(
        "the documentation places cannot be read — `pkit friction artefacts --json` exited 2 "
        "without its document: Error: No such command. No space is checked until they can"
    )
    assert document["summary"][0] == "places unreadable: no space checked."


# --- separation (DEC-001 point 1) --------------------------------------------------------


def test_roots_that_are_one_folder_are_reported_not_failed(project: AdopterRepo) -> None:
    declare(project, roots={"user": "docs/", "internal": "docs/"}, spaces={})
    document = run(project)
    assert errors(document) == []
    separation = [f for f in document["findings"] if f["location"] == f"{CONFIG}:/docs"]
    assert [f["severity"] for f in separation] == ["report"]
    assert "both documentation roots are 'docs'" in separation[0]["message"]


# --- the package metadata ----------------------------------------------------------------


def test_the_package_declares_the_roots_and_the_definitions_as_places(project: AdopterRepo) -> None:
    settings = fd.read_friction_settings(project.root)
    ours = [(p.resolved, p.type) for p in settings.places if p.source == "capability:living-docs"]
    assert ours == [
        ("docs/**", "living-docs:page"),
        ("tech-docs/**", "living-docs:page"),
        ("tech-docs/living-docs/rule-sets", None),
        ("tech-docs/living-docs/**", "living-docs:template"),
    ]
    # The definitions are project rule sets: the backbone reads them there.
    places = fd.rule_set_places(project.root, settings)
    definitions = [p for p in places if p.pattern == "tech-docs/living-docs/rule-sets"]
    assert [p.component for p in definitions] == [None]


def test_the_package_declares_the_page_and_template_types(project: AdopterRepo) -> None:
    """DEC-001 points 2 and 4 (COR-056 point 2): `page`, with `kind` as its kind
    field and project places admitted, and `template`, which admits none."""
    document = _artefacts(project)
    types = {name: entry for name, entry in document["types"].items() if "living-docs" in name}
    assert {name: (t["kind_field"], t["project_places"]) for name, t in types.items()} == {
        "living-docs:page": ("kind", True),
        "living-docs:template": (None, False),
    }


def _artefacts(repo: AdopterRepo) -> dict[str, Any]:
    """The backbone's artefacts document over `repo`, as the validator reads it."""
    completed = subprocess.run(
        ["pkit", "friction", "artefacts", "--json"],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _type_of(document: Mapping[str, Any], location: str) -> str | None:
    (artefact,) = [a for a in document["artefacts"] if a["location"] == location]
    return artefact["type"]


def test_a_page_under_a_root_is_of_the_page_type_and_a_template_is_not(
    project: AdopterRepo,
) -> None:
    """A root gives the page type to what declares its page kind; the definitions
    location gives the template type and ranks ahead of the internal root, so a
    page template copied there is a template, never a page (DEC-001 point 2)."""
    template = "tech-docs/living-docs/templates/signpost.md"
    project.write({template: (CAPABILITY / "templates" / "signpost.md").read_text("utf-8")})
    found = _artefacts(project)
    assert _type_of(found, "docs/guide.md") == "living-docs:page"
    assert _type_of(found, "tech-docs/README.md") == "living-docs:page"
    assert _type_of(found, template) == "living-docs:template"
    assert _type_of(found, "tech-docs/architecture/decisions/ADR-001-a-decision.md") is None
    document = run(project)
    assert errors(document) == []
    assert "3 in the definitions location" in document["summary"][3]
    assert document["summary"][2].startswith("technical: 1 page(s)")


def test_a_project_place_may_give_the_page_type_or_a_type_of_its_own(project: AdopterRepo) -> None:
    """The page type admits project places (COR-056 point 2): an out-of-root place
    that gives it holds pages by their type. A project place inside a root that
    gives a type of the project's own outranks the root: its documents are the
    project's, and their `kind` is never read as a page kind."""
    config = {
        "docs": {"user": "docs/", "internal": "tech-docs/"},
        "friction": {
            "places": [
                {"path": "README.md", "type": "living-docs:page"},
                {"path": "docs/changes", "type": "change-note"},
            ]
        },
    }
    project.write(
        {
            CONFIG: _yaml(config),
            "docs/changes/2026-10-01.md": "---\nkind: fix\n---\n\n# A change\n",
        }
    )
    found = _artefacts(project)
    assert _type_of(found, "README.md") == "living-docs:page"
    assert _type_of(found, "docs/changes/2026-10-01.md") == "change-note"
    document = run(project)
    assert errors(document) == []
    assert document["summary"][1].startswith("user: 2 page(s)")
    assert "1 of a type the project gives" in document["summary"][3]
    assert "0 unclassified document(s)" in document["summary"][3]


def test_a_document_declaring_no_kind_in_a_place_giving_the_page_type_is_unclassified(
    project: AdopterRepo,
) -> None:
    config = {
        "docs": {"user": "docs/", "internal": "tech-docs/"},
        "friction": {"places": [{"path": "README.md", "type": "living-docs:page"}]},
    }
    project.write({CONFIG: _yaml(config), "README.md": "---\nreader: user\n---\n\n# Project\n"})
    document = run(project)
    assert errors(document) == []
    assert "entry point README.md, not yet a page" in document["summary"][1]
    assert "1 unclassified document(s)" in document["summary"][3]


def test_a_backbone_that_gives_no_types_is_one_error_and_nothing_checked(
    project: AdopterRepo,
    pkit_on_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A backbone whose artefacts document predates types: the validator cannot tell
    a page by its type, which is one error — never every page read as untyped."""
    old = tmp_path_factory.mktemp("untyped-pkit")
    strip = old / "strip.py"
    strip.write_text(
        "import json, sys\n"
        "document = json.load(sys.stdin)\n"
        "document.pop('types', None)\n"
        "for artefact in document.get('artefacts', []):\n"
        "    for key in ('type', 'type_place', 'type_conflict', 'ranked_places'):\n"
        "        artefact.pop(key, None)\n"
        "json.dump(document, sys.stdout)\n",
        encoding="utf-8",
    )
    (old / "pkit").write_text(
        '#!/bin/sh\nif [ "$1" = friction ] && [ "$2" = artefacts ]; then\n'
        f'  "{pkit_on_path}/pkit" "$@" | "{sys.executable}" "{strip}"; exit $?\nfi\n'
        f'exec "{pkit_on_path}/pkit" "$@"\n',
        encoding="utf-8",
    )
    (old / "pkit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{old}{os.pathsep}{os.environ['PATH']}")
    location, message = only_error(run(project))
    assert location == CONFIG
    assert "answered without each artefact's type and ranked places" in message


# --- the definitions' scopes joined with the assignment (DEC-001 point 1) ----------------


def _scoped_definition(set_name: str, scope: Mapping[str, Any] | list[str]) -> str:
    """A space definition from the template, with `scope` (COR-051 point 2)."""
    return _definition(set_name, scope=scope)


def _out_of_root(project: AdopterRepo, *, typed: bool) -> None:
    """README.md and CONTRIBUTING.md outside both roots, assigned to the user and
    the technical space, each given the page type or none."""
    places: list[Any] = ["README.md", "CONTRIBUTING.md"]
    if typed:
        places = [{"path": path, "type": "living-docs:page"} for path in places]
    declare(project, assignments={"README.md": "user", "CONTRIBUTING.md": "technical"})
    config = {"docs": {"user": "docs/", "internal": "tech-docs/"}, "friction": {"places": places}}
    project.write({CONFIG: _yaml(config), "CONTRIBUTING.md": PAGE.replace("user", "maintainer")})


def test_a_definition_with_no_scope_joins_nothing(project: AdopterRepo) -> None:
    _out_of_root(project, typed=False)
    unscoped(project)
    document = run(project)
    assert errors(document) == []
    assert (
        "scopes: no space's definition carries one, so no assigned place is joined with a "
        "scope (DEC-001 point 1)."
    ) in document["summary"]


def test_an_assigned_place_lies_in_its_own_definition_s_scope(project: AdopterRepo) -> None:
    _out_of_root(project, typed=False)
    project.write(
        {
            f"{DEFINITIONS}/user.md": _scoped_definition("USER", ["docs/**", "README.md"]),
            f"{DEFINITIONS}/technical.md": _scoped_definition("TECH", ["tech-docs/**"]),
        }
    )
    location, message = only_error(run(project))
    assert location == f"{LD_CONFIG}:/places/CONTRIBUTING.md"
    assert (
        "place 'CONTRIBUTING.md' is assigned to space 'technical' and gives it "
        "CONTRIBUTING.md, which the scope of that space's definition, "
        f"{DEFINITIONS}/technical.md, does not cover" in message
    )
    project.write(
        {
            f"{DEFINITIONS}/technical.md": _scoped_definition(
                "TECH", ["tech-docs/**", "CONTRIBUTING.md"]
            )
        }
    )
    document = run(project)
    assert errors(document) == []
    assert any(
        line.startswith("scopes: technical, user — 2 page(s)") for line in document["summary"]
    )


def test_an_assigned_place_lies_in_no_other_definition_s_scope(project: AdopterRepo) -> None:
    """Checked against every other definition with a scope, even where the place's
    own space's definition carries none (DEC-001 point 1)."""
    _out_of_root(project, typed=False)
    project.write(
        {
            f"{DEFINITIONS}/user.md": _scoped_definition("USER", ["*.md", "docs/**"]),
            f"{DEFINITIONS}/technical.md": _definition("TECH", scope=UNSCOPED),
        }
    )
    location, message = only_error(run(project))
    assert location == f"{LD_CONFIG}:/places/CONTRIBUTING.md"
    assert (
        "which the scope of space 'user''s definition, "
        f"{DEFINITIONS}/user.md, also covers" in message
    )
    assert "leave the place out of that scope with its `exclude`" in message
    project.write(
        {
            f"{DEFINITIONS}/user.md": _scoped_definition(
                "USER", {"paths": ["*.md", "docs/**"], "exclude": ["CONTRIBUTING.md"]}
            )
        }
    )
    assert errors(run(project)) == []


def test_a_place_assigned_where_the_definition_selects_by_type_gives_the_page_type(
    project: AdopterRepo,
) -> None:
    """Where a space's definition selects by type, an assigned place outside every
    root that gives no page type would hold pages the scope misses without a word:
    validation fails the place (DEC-001 point 1)."""
    _out_of_root(project, typed=False)
    by_type = {"paths": ["docs/**", "README.md"], "types": ["living-docs:page"]}
    project.write(
        {
            f"{DEFINITIONS}/user.md": _scoped_definition("USER", by_type),
            f"{DEFINITIONS}/technical.md": _definition("TECH", scope=UNSCOPED),
        }
    )
    location, message = only_error(run(project))
    assert location == f"{CONFIG}:/friction/places/0"
    assert (
        "project place 'README.md' lies outside every documentation root and is assigned to "
        f"space 'user', whose definition, {DEFINITIONS}/user.md, selects by type, but it names "
        "no type" in message
    )
    assert "`{path: README.md, type: living-docs:page}`" in message
    _out_of_root(project, typed=True)
    assert errors(run(project)) == []
    # A definition that selects by paths alone asks no type of the places.
    _out_of_root(project, typed=False)
    project.write({f"{DEFINITIONS}/user.md": _scoped_definition("USER", ["docs/**", "README.md"])})
    assert errors(run(project)) == []


# --- the LDOC rule set and the space definition template (DEC-001 points 2 and 3) --------


def test_ldoc_validates_as_a_method_rule_set_with_its_origins(project: AdopterRepo) -> None:
    result = rs.validate_rule_sets(project.root)
    assert result.errors == ()
    (ldoc,) = result.discovery.sets_named("LDOC")
    assert (ldoc.component, ldoc.version, ldoc.path) == (
        "living-docs",
        "1.0.0",
        ".pkit/capabilities/living-docs/rule-sets/ldoc.md",
    )
    assert [rule.id for rule in ldoc.rules] == [f"RS-LDOC-00{n}" for n in range(1, 7)]
    # Each rule anchors the point of DEC-001 that states it (point 3), and the two whose
    # field the page's front matter carries also the point that gives the field (point 4).
    with_field = {"RS-LDOC-003", "RS-LDOC-004"}
    for rule in ldoc.rules:
        assert rule.status == "accepted"
        assert rule.origin == {"decision": "living-docs:DEC-001"}
        expected = ("living-docs:DEC-001#3",)
        if rule.id in with_field:
            expected += ("living-docs:DEC-001#4",)
        assert rule.anchors("record") == expected


def test_ldoc_declares_the_parts_its_validation_enforces(project: AdopterRepo) -> None:
    """DEC-001 point 6 (COR-051 point 2): RS-LDOC-004's structure and RS-LDOC-003's
    field are the capability's validator's, a command its package registers; the
    declarations name no check that is not there."""
    result = rs.validate_rule_sets(project.root)
    assert result.errors == ()
    assert [f for f in result.findings if "check" in f.kind.value] == []
    (ldoc,) = result.discovery.sets_named("LDOC")
    declared = {
        rule.id: [(part.owner, part.name) for part in rule.checks]
        for rule in ldoc.rules
        if rule.checks
    }
    assert declared == {
        "RS-LDOC-003": [("living-docs", "validate")],
        "RS-LDOC-004": [("living-docs", "validate")],
    }
    format_rule, reader_rule = ldoc.rule("RS-LDOC-004"), ldoc.rule("RS-LDOC-003")
    assert format_rule is not None and reader_rule is not None
    (structure,) = format_rule.checks
    assert "sections its kind's declared structure names" in structure.part
    (field,) = reader_rule.checks
    assert "`reader` field" in field.part


def test_a_space_definition_from_the_template_inherits_ldoc(project: AdopterRepo) -> None:
    result = rs.validate_rule_sets(project.root)
    assert result.errors == ()
    for name in ("USER", "TECH"):
        (definition,) = result.discovery.sets_named(name)
        assert definition.component is None  # a project rule set, cited bare
        assert [str(pin) for _index, pin in definition.pins] == ["living-docs:LDOC@1"]
    checks = rs.pin_checks(result.discovery)
    assert {c.rule_set.name for c in checks} == {"USER", "TECH"}
    assert all(c.problem is None for c in checks)


# --- the page template (DEC-001 points 3 and 4) ------------------------------------------


def _page_schema() -> Draft202012Validator:
    schema = json.loads((CAPABILITY / "schemas" / "page.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _template_front_matter(name: str) -> dict[str, Any]:
    text = (CAPABILITY / "templates" / f"{name}.md").read_text(encoding="utf-8")
    front, _body = document_parts.split_front_matter(text)
    assert front is not None
    return YAML(typ="safe").load(front)


#: Every template but the space definition's is a page template, named for its kind:
#: a kind arrives with its template (RS-LDOC-004; the page schema's `kind`).
PAGE_TEMPLATES = sorted(
    path.stem for path in (CAPABILITY / "templates").glob("*.md") if path.stem != "space-definition"
)


def test_the_page_templates_are_the_signpost_and_the_reference_page() -> None:
    assert PAGE_TEMPLATES == ["reference", "signpost"]


@pytest.mark.parametrize("kind", PAGE_TEMPLATES)
def test_the_page_template_validates_its_fields_and_its_friction_block(kind: str) -> None:
    front = _template_front_matter(kind)
    assert (front["reader"], front["kind"]) == ("user", kind)
    assert list(_page_schema().iter_errors(front)) == []
    container = bs.load_backbone_schema(REPO, "container")
    result = bs.validate_container(front, container, wiring=bs.ContainerWiring())
    assert result.findings == ()
    # The page's reader is its own field, outside the container: no role block.
    assert set(front["pkit"]) == {"friction"}


@pytest.mark.parametrize("reader", ["User", "", 7, None, ["user"], "a reader"])
def test_the_page_schema_refuses_a_wrong_reader(reader: Any) -> None:
    assert not _page_schema().is_valid({"reader": reader, "kind": "signpost"})


# --- page formats: a page's body against its kind's structure (RS-LDOC-004; #1267) -------


def _library(name: str) -> ModuleType:
    """A module of the capability's script library, under a name of its own: the
    library is `_lib` in every capability, so it is never imported by that name."""
    spec = importlib.util.spec_from_file_location(
        f"living_docs_lib_{name}", CAPABILITY / "scripts" / "_lib" / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


formats = _library("formats")

PAGE_KINDS = CAPABILITY / "schemas" / "page-kinds.yaml"
PAGE_KINDS_PATH = f"{LD.as_posix()}/schemas/page-kinds.yaml"
LDOC = CAPABILITY / "rule-sets" / "ldoc.md"

#: What the validator says of a reference page, docs/ref.md, without its title.
LACKS_TITLE = (
    "docs/ref.md, a page of kind 'reference', lacks a title written as `# Title` at the start "
    "of a line: the structure its kind declares is a title written as `# Title` "
    f"({PAGE_KINDS_PATH}) — add it; a heading that is underlined, written in HTML, indented, "
    "empty or a template's unfilled `<placeholder>` is not read. A page may carry other "
    "sections besides (RS-LDOC-004)."
)

INSTALL, USE = {"level": 2, "text": "Install"}, {"level": 2, "text": "Use"}

#: Runs the validator's check with the kinds' declaration read from another file.
KINDS_DRIVER = """
import json, sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from _lib import spaces
from _lib.declarations import project_root

spaces.PAGE_KINDS = Path(sys.argv[2])
print(json.dumps(spaces.check(project_root()).document()))
"""


def _page(kind: str, body: str) -> str:
    return f"---\nreader: user\nkind: {kind}\n---\n\n{body}"


def _format_line(document: Mapping[str, Any]) -> str:
    (line,) = [line for line in document["summary"] if line.startswith("page formats")]
    return line


def _declaration(folder: Path, kinds: Mapping[str, Any]) -> Path:
    """A declaration of `kinds` in a file of its own, outside any repository."""
    path = folder / "page-kinds.yaml"
    path.write_text(_yaml({"schema_version": 1, "kinds": kinds}), encoding="utf-8")
    return path


def run_declaring(repo: AdopterRepo, declaration: Path) -> dict[str, Any]:
    """The validator's findings document with the kinds' structures read from
    `declaration`: what the adopter's copy of the capability ships stays as synced."""
    completed = subprocess.run(
        [sys.executable, "-c", KINDS_DRIVER, str(repo.root / LD / "scripts"), str(declaration)],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_a_page_that_follows_its_kind_s_structure_passes(project: AdopterRepo) -> None:
    """The fixture's signposts and a reference page each carry their title: no
    finding, and the summary counts each checked."""
    project.write({"docs/ref.md": _page("reference", "# Ref\n\nWhat it is.\n")})
    document = run(project)
    assert document["findings"] == []
    assert _format_line(document) == (
        "page formats (RS-LDOC-004, accepted): 4 page(s) checked against the structure their "
        f"kind declares in {PAGE_KINDS_PATH}, 0 departing from it; 0 page(s) not checked, of "
        "0 kind(s) that declare no structure."
    )


def test_a_page_lacking_a_section_fails_naming_the_page_its_kind_the_section_and_the_structure(
    project: AdopterRepo,
) -> None:
    project.write({"docs/ref.md": _page("reference", "What it is, and nothing more.\n")})
    document = run(project)
    assert [f["severity"] for f in document["findings"]] == ["error"]
    assert only_error(document) == ("docs/ref.md", LACKS_TITLE)
    assert ", 1 departing from it; " in _format_line(document)


@pytest.mark.parametrize(
    "body",
    [
        "- ```sh\n# install\n```\n",  # the only `#` line is code, fenced on a list item's line
        "- A step:\n\n  # Under a list item\n",  # indented
        "<!--\n# Commented out\n-->\n\nProse.\n",
        "#\n\nProse.\n",  # an empty heading
        "# <Surface>\n\nProse.\n",  # the template's placeholder, unfilled
        "Ref\n===\n\nProse.\n",  # an underlined (setext) title
        '<h1 align="center">Ref</h1>\n\nProse.\n',
    ],
)
def test_what_is_not_read_as_a_title_leaves_the_page_without_one(
    project: AdopterRepo, body: str
) -> None:
    project.write({"docs/ref.md": _page("reference", body)})
    assert only_error(run(project)) == ("docs/ref.md", LACKS_TITLE)


def test_a_title_after_code_fenced_under_a_list_item_is_read(project: AdopterRepo) -> None:
    """The fence a list item's line opens is closed by the indented fence under it,
    which opens nothing: the title below is read."""
    body = "- ```sh\n  # install\n  ```\n\n# Ref\n"
    project.write({"docs/ref.md": _page("reference", body)})
    assert run(project)["findings"] == []


def test_pkit_validate_fails_on_a_page_departing_from_its_kind_s_structure(
    project: AdopterRepo,
) -> None:
    project.write({"docs/ref.md": _page("reference", "What it is, and nothing more.\n")})
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 1
    assert "docs/ref.md, a page of kind 'reference', lacks a title" in result.output


def test_a_kind_that_declares_no_structure_is_reported_with_its_pages_and_never_failed(
    project: AdopterRepo,
) -> None:
    """A kind the project adds, and a kind mistyped: each is one report naming the
    kind, the pages that name it and the kinds that are declared."""
    project.write(
        {
            "docs/notes.md": _page("tutorial", "Only prose, no heading at all.\n"),
            "docs/steps.md": _page("tutorial", "# Steps\n"),
            "docs/ref.md": _page("refrence", "# Ref\n"),
        }
    )
    document = run(project)
    assert errors(document) == []
    declared = f"{PAGE_KINDS_PATH} declares ['reference', 'signpost'] — name one of them where"
    closing = "a page is of that kind; a kind the project adds is reported, never failed"
    assert [(f["severity"], f["location"], f["message"]) for f in document["findings"]] == [
        (
            "report",
            "docs/ref.md:/kind",
            "kind 'refrence' declares no structure, so the body of the 1 page(s) that name it "
            f"is not checked: docs/ref.md. {declared} {closing} (DEC-001 point 3).",
        ),
        (
            "report",
            "docs/notes.md:/kind",
            "kind 'tutorial' declares no structure, so the body of the 2 page(s) that name it "
            f"is not checked: docs/notes.md, docs/steps.md. {declared} {closing} "
            "(DEC-001 point 3).",
        ),
    ]
    assert _format_line(document).endswith(
        "3 page(s) checked against the structure their kind declares in "
        f"{PAGE_KINDS_PATH}, 0 departing from it; 3 page(s) not checked, of 2 kind(s) that "
        "declare no structure."
    )
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 0, result.output
    assert "kind 'tutorial' declares no structure" in result.output


def test_the_rule_the_check_names_is_an_accepted_rule_of_the_shipped_method() -> None:
    """The check applies one rule by its id (`FORMAT_RULE`): were the shipped LDOC to
    supersede or withdraw it, the check would stop while its successor binds."""
    front, _body = document_parts.split_front_matter(LDOC.read_text(encoding="utf-8"))
    assert front is not None
    rules = YAML(typ="safe").load(front)["rules"]
    assert rules[formats.FORMAT_RULE]["status"] == "accepted"


@pytest.mark.parametrize(
    ("status", "line"),
    [
        ("    status: proposed\n", "RS-LDOC-004 is proposed"),
        ("    status: superseded\n", "RS-LDOC-004 is superseded"),
        ("    status: withdrawn\n", "RS-LDOC-004 is withdrawn"),
        ("", "RS-LDOC-004 is proposed"),  # a rule without a status is proposed
    ],
)
def test_the_severity_is_the_one_the_rule_s_status_gives(
    project: AdopterRepo, status: str, line: str
) -> None:
    """An accepted RS-LDOC-004 binds, so a departure is an error (above); a rule of any
    other status binds nothing (COR-051 point 4), so no page's body is checked."""
    project.write({"docs/ref.md": _page("reference", "No title.\n")})
    assert errors(run(project)) != []
    ldoc = project.root / LD / "rule-sets" / "ldoc.md"
    accepted = "  RS-LDOC-004:\n    status: accepted\n"
    text = ldoc.read_text(encoding="utf-8")
    assert accepted in text
    ldoc.write_text(text.replace(accepted, f"  RS-LDOC-004:\n{status}"), encoding="utf-8")
    document = run(project)
    assert document["findings"] == []
    assert _format_line(document) == (
        f"page formats: not checked — {line}, so it binds nothing (COR-051 point 4)."
    )


def test_a_shared_method_without_the_rule_checks_no_body_and_says_so(
    project: AdopterRepo,
) -> None:
    """The rule set's own defects are the backbone's `rule-sets` findings; here the
    summary says the check did not run, and why."""
    project.write({"docs/ref.md": _page("reference", "No title.\n")})
    ldoc = project.root / LD / "rule-sets" / "ldoc.md"
    text = ldoc.read_text(encoding="utf-8")
    assert "  RS-LDOC-004:\n" in text
    ldoc.write_text(text.replace("  RS-LDOC-004:\n", "  RS-LDOC-014:\n"), encoding="utf-8")
    document = run(project)
    assert document["findings"] == []
    assert _format_line(document) == (
        f"page formats: not checked — {LD.as_posix()}/rule-sets/ldoc.md holds no RS-LDOC-004."
    )


def test_a_page_outside_every_space_is_not_checked_against_its_kind_s_structure(
    project: AdopterRepo,
) -> None:
    """RS-LDOC-004 binds on a page only through a set of the project's own whose scope
    selects it (COR-051 point 7; DEC-001 point 3). A page no definition's scope
    selects departs from its kind's structure and fails nothing, and the summary
    counts it apart."""
    outside_every_space(project)
    project.write({"docs/drafts/ref.md": _page("reference", "No title.\n")})
    document = run(project)
    # The page is reported as left out of its space's scope, never failed.
    assert document["findings"] == [left_out("docs/drafts/ref.md")]
    assert _format_line(document) == (
        "page formats (RS-LDOC-004, accepted): 3 page(s) checked against the structure their "
        f"kind declares in {PAGE_KINDS_PATH}, 0 departing from it; 0 page(s) not checked, of "
        "0 kind(s) that declare no structure; 1 page(s) RS-LDOC-004 does not bind on, not "
        "checked."
    )
    # The same page inside the scope fails.
    project.write({"docs/ref.md": _page("reference", "No title.\n")})
    assert only_error(run(project)) == ("docs/ref.md", LACKS_TITLE)


def test_a_page_reached_through_a_pin_behind_ldoc_s_major_is_not_checked(
    project: AdopterRepo,
) -> None:
    """No rule binds through a pin behind its set (COR-051 point 7): the definitions
    pin LDOC at a major it has left, so no page's structure or reader is checked,
    and the backbone's own `rule-sets` member names the pin."""
    for name, space in (("USER", "user"), ("TECH", "technical")):
        project.write({f"{DEFINITIONS}/{space}.md": _definition(name, ["living-docs:LDOC@0"])})
    project.write({"docs/ref.md": _page("reference", "No title.\n")})
    document = run(project)
    assert errors(document) == []
    assert _format_line(document) == (
        "page formats: not checked — RS-LDOC-004 binds on none of the 4 page(s) (COR-051 point "
        "7): living-docs:LDOC binds only through a set of the project's own whose scope selects "
        "a page, such as a space's definition (DEC-001 point 2)."
    )
    (line,) = [line for line in document["summary"] if line.startswith("readers")]
    assert line == (
        "readers: not checked — RS-LDOC-003 binds on none of the 4 page(s), so "
        "pkit::documentation:readers is not read (COR-051 point 7)."
    )


def test_where_the_rules_bind_unread_is_one_error_and_no_structure_or_reader_checked(
    project: AdopterRepo,
    pkit_on_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `pkit` that gives no answer of where the rules bind: a check of a rule's part
    runs only where the rule binds, which cannot be told, so neither part is
    checked, and that is one error (DEC-001 point 3)."""
    broken = tmp_path_factory.mktemp("no-reach-pkit")
    (broken / "pkit").write_text(
        '#!/bin/sh\nif [ "$1" = rule-sets ]; then echo "no reach here" >&2; exit 2; fi\n'
        f'exec "{pkit_on_path}/pkit" "$@"\n',
        encoding="utf-8",
    )
    (broken / "pkit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{broken}{os.pathsep}{os.environ['PATH']}")
    project.write({"docs/ref.md": _page("reference", "No title.\n")})
    document = run(project)
    location, message = only_error(document)
    assert location == CONFIG
    assert message == (
        "where living-docs:LDOC's rules bind cannot be read — `pkit rule-sets reach --json` "
        "exited 2 without its document: no reach here. No page's structure or reader is "
        "checked until it can: living-docs checks each part of a rule only where the rule "
        "binds, read through the backbone's `pkit rule-sets reach --json` (DEC-001 point 3; "
        "COR-051 point 7)."
    )
    assert _format_line(document) == (
        "page formats: not checked — where RS-LDOC-004 binds cannot be read."
    )


binding = _library("binding")


def test_the_answer_of_where_rules_bind_reads_each_document_s_rules() -> None:
    """The `pkit rule-sets reach --json` document, read as the validator reads it:
    each document artefact's rules as cited; an entry of a collection file is no
    page, so it is left out; a version other than 1 is no answer."""
    answer = {
        "schema_version": 1,
        "commit": None,
        "artefacts": [
            {
                "path": "docs/a.md",
                "kind": "document",
                "rules": [{"rule": "living-docs:RS-LDOC-003"}, {"rule": "RS-USER-001"}],
            },
            {"path": "rules.md", "kind": "entry", "rules": [{"rule": "living-docs:RS-LDOC-001"}]},
        ],
    }
    read = binding.binding_of(answer)
    assert read.binds("docs/a.md", "living-docs:RS-LDOC-003")
    assert not read.binds("docs/a.md", "living-docs:RS-LDOC-004")
    assert not read.binds("rules.md", "living-docs:RS-LDOC-001")
    assert not read.binds("docs/b.md", "living-docs:RS-LDOC-003")
    for wrong in ({**answer, "schema_version": 2}, {"schema_version": 1}):
        with pytest.raises(binding.Unreadable):
            binding.binding_of(wrong)
    # A gate reads where rules bind, never where they would bind (#1607, ADR-057 point 2).
    assert "--preview" not in binding.ARGV


def test_the_validator_reads_a_fill_only_where_the_rule_it_fills_binds(
    project: AdopterRepo,
) -> None:
    """The validator reads where rules bind from the backbone's one answer, so a fill
    binds for it only where the rule it fills binds (COR-051 point 7; #1616). The shared
    MID's accepted RS-MID-001 fills a point of the proposed RS-CMN-001, so it binds
    nowhere, and neither does RS-GUIDE-001, which fills a point RS-MID-001 offers."""

    def sets(status: str) -> dict[str, str]:
        cmn = rules("RS-CMN-001", offers=["where"], status=status)
        mid = rules(
            "RS-MID-001",
            offers=["how"],
            fills=["RS-CMN-001#where"],
            **anchored_to("RS-CMN-001"),
        )
        guide = rules("RS-GUIDE-001", fills=["RS-MID-001#how"], **anchored_to("RS-MID-001"))
        fronts = {
            "cmn": {"rule-set": "CMN", "version": "1.0.0", "rules": cmn},
            "mid": {"rule-set": "MID", "version": "1.0.0", "inherits": ["CMN@1"], "rules": mid},
            "guide": {
                "rule-set": "GUIDE",
                "version": "1.0.0",
                "inherits": ["MID@1"],
                "scope": ["docs/**"],
                "rules": guide,
            },
        }
        return {f"tech-docs/rule-sets/{key}.md": rule_set_text(f) for key, f in fronts.items()}

    project.write(sets("proposed"))
    read = binding.read_binding(project.root)
    assert read.binds("docs/guide.md", "living-docs:RS-LDOC-003")
    assert not read.binds("docs/guide.md", "RS-GUIDE-001")
    assert not read.binds("docs/guide.md", "RS-MID-001")
    project.write(sets("accepted"))
    read = binding.read_binding(project.root)
    assert read.binds("docs/guide.md", "RS-GUIDE-001")
    assert read.binds("docs/guide.md", "RS-MID-001")


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (None, "the file cannot be read"),
        ("kinds: [unclosed\n", "the file is not YAML"),
        (
            "schema_version: 1\nkinds:\n  reference:\n    sections: []\n",
            "the file does not fit schemas/page-kinds.schema.json: at `/kinds/reference/sections`",
        ),
    ],
)
def test_a_declaration_that_gives_no_reading_is_one_error_and_no_body_is_checked(
    project: AdopterRepo,
    tmp_path_factory: pytest.TempPathFactory,
    content: str | None,
    why: str,
) -> None:
    declaration = tmp_path_factory.mktemp("kinds") / "page-kinds.yaml"
    if content is not None:
        declaration.write_text(content, encoding="utf-8")
    project.write({"docs/ref.md": _page("reference", "No title.\n")})
    document = run_declaring(project, declaration)
    assert [f["severity"] for f in document["findings"]] == ["error"]
    location, message = only_error(document)
    assert location == PAGE_KINDS_PATH
    assert message.startswith(f"structures unreadable — {why}")
    assert message.endswith(
        ". No page's body is checked until the page kinds' structures can be read: the file "
        "is living-docs's own, never the project's to edit — restore it as the capability "
        "ships it (DEC-001 point 3)."
    )
    assert _format_line(document) == (
        "page formats: structures unreadable, so no page's body is checked."
    )


def test_a_section_out_of_order_fails_naming_its_line_and_the_declared_order(
    project: AdopterRepo, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """No shipped kind declares two sections, so the declaration is one of the test's
    own, read in place of the shipped one — which reads as the validator reads it."""
    assert run_declaring(project, project.root / PAGE_KINDS_PATH) == run(project)
    declaration = _declaration(
        tmp_path_factory.mktemp("kinds"),
        {
            "guide": {"sections": [{"level": 1}, INSTALL, USE]},
            "faq": {"ordered": False, "sections": [INSTALL, USE]},
        },
    )
    project.write(
        {
            "docs/guide.md": _page("guide", "# Guide\n\n## Use\n\n## Install\n"),
            "docs/faq.md": _page("faq", "## Use\n\n## Install\n"),
        }
    )
    document = run_declaring(project, declaration)
    assert only_error(document) == (
        "docs/guide.md",
        "docs/guide.md, a page of kind 'guide', carries the section `## Use` out of order, at "
        "line 8: the structure its kind declares is a title written as `# Title`, then the "
        f"section `## Install`, then the section `## Use` ({PAGE_KINDS_PATH}) — move the "
        "section into that order. A page may carry other sections besides (RS-LDOC-004).",
    )
    # The guide and the list of questions are checked; the two signposts left are of a
    # kind this declaration does not list.
    assert "2 page(s) checked" in _format_line(document)
    assert "1 departing from it; 2 page(s) not checked, of 1 kind(s)" in _format_line(document)


# The declaration, read whole or not at all.


def test_a_declaration_reads_as_each_kind_s_sections_and_their_order(tmp_path: Path) -> None:
    structures = formats.read_structures(
        _declaration(
            tmp_path,
            {
                "guide": {"sections": [{"level": 1}, INSTALL, USE]},
                "faq": {"ordered": False, "sections": [INSTALL, USE]},
                "note": {"ordered": True, "sections": [{"level": 1}, {"level": 2}]},
            },
        )
    )
    install, use = formats.Section(2, "Install"), formats.Section(2, "Use")
    assert structures == {
        "guide": formats.Structure((formats.Section(1), install, use)),
        "faq": formats.Structure((install, use), ordered=False),
        "note": formats.Structure((formats.Section(1), formats.Section(2))),
    }
    assert structures["guide"].described() == (
        "a title written as `# Title`, then the section `## Install`, then the section `## Use`"
    )
    assert structures["faq"].described() == (
        "the section `## Install` and the section `## Use`, in any order"
    )
    assert structures["note"].described() == (
        "a title written as `# Title`, then a section written as `## Heading`"
    )


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (None, "the file cannot be read"),
        ("kinds: [unclosed\n", "the file is not YAML ("),
        ("", "does not fit schemas/page-kinds.schema.json: at `/`"),
        ("kinds: {}\n", "'schema_version' is a required property"),
        ("schema_version: 2\nkinds: {}\n", "at `/schema_version`"),
        ("schema_version: 1\nkinds: []\n", "at `/kinds`"),
        ("schema_version: 1\nkinds:\n  Bad Kind:\n    sections: [{level: 1}]\n", "at `/kinds`"),
        ("schema_version: 1\nkinds:\n  guide: {}\n", "at `/kinds/guide`"),
        ("schema_version: 1\nkinds:\n  guide:\n    sections: []\n", "at `/kinds/guide/sections`"),
        (
            "schema_version: 1\nkinds:\n  guide:\n    sections: [{level: 7}]\n",
            "at `/kinds/guide/sections/0/level`",
        ),
        (
            "schema_version: 1\nkinds:\n  guide:\n    sections: [{level: true}]\n",
            "at `/kinds/guide/sections/0/level`",
        ),
        (
            "schema_version: 1\nkinds:\n  guide:\n    sections: [{level: 1, text: '  '}]\n",
            "at `/kinds/guide/sections/0/text`",
        ),
        (
            "schema_version: 1\nkinds:\n  guide:\n    sections: [{level: 1}]\n    order: yes\n",
            "at `/kinds/guide`",
        ),
    ],
)
def test_a_declaration_absent_unparsable_or_unfit_gives_no_reading(
    tmp_path: Path, content: str | None, why: str
) -> None:
    path = tmp_path / "page-kinds.yaml"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    with pytest.raises(formats.Unreadable) as refused:
        formats.read_structures(path)
    assert why in str(refused.value)


# A body against a structure.


def test_a_section_the_body_lacks_is_missing(tmp_path: Path) -> None:
    structures = formats.read_structures(
        _declaration(
            tmp_path,
            {
                "note": {"sections": [{"level": 1}, {"level": 2}]},
                "guide": {"sections": [{"level": 1}, INSTALL, USE]},
            },
        )
    )
    assert formats.departures(formats.headings("# Note\n\nProse.\n"), structures["note"]) == [
        formats.Departure(formats.Section(2), formats.MISSING)
    ]
    assert formats.departures(formats.headings("# Guide\n\n## Use\n"), structures["guide"]) == [
        formats.Departure(formats.Section(2, "Install"), formats.MISSING)
    ]
    assert formats.departures(formats.headings("# Note\n\n## Part\n"), structures["note"]) == []


def test_sections_out_of_order_depart_only_where_the_kind_says_order_matters(
    tmp_path: Path,
) -> None:
    structures = formats.read_structures(
        _declaration(
            tmp_path,
            {
                "guide": {"sections": [{"level": 1}, INSTALL, USE]},
                "faq": {"ordered": False, "sections": [INSTALL, USE]},
            },
        )
    )
    swapped = formats.headings("# Guide\n\n## Use\n\n## Install\n")
    assert formats.departures(swapped, structures["guide"]) == [
        formats.Departure(formats.Section(2, "Use"), formats.OUT_OF_ORDER, 3)
    ]
    assert formats.departures(swapped, structures["faq"]) == []
    # In any order, each section is still owed.
    assert formats.departures(formats.headings("# Guide\n\n## Use\n"), structures["faq"]) == [
        formats.Departure(formats.Section(2, "Install"), formats.MISSING)
    ]


def test_a_section_s_text_compares_ignoring_case_space_and_trailing_punctuation() -> None:
    section = formats.Section(2, "Getting started")
    assert section.matches(formats.Heading(2, "getting   STARTED:", 1))
    assert section.matches(formats.Heading(2, "Getting started?", 1))
    assert not section.matches(formats.Heading(3, "Getting started", 1))
    assert not section.matches(formats.Heading(2, "Getting started fast", 1))


def test_a_section_the_writer_words_takes_a_heading_with_words_of_its_own() -> None:
    title = formats.Section(1)
    assert title.matches(formats.Heading(1, "Anything the writer says", 1))
    assert title.matches(formats.Heading(1, "The <kbd> element", 1))
    assert not title.matches(formats.Heading(1, "", 1))  # `#` alone
    assert not title.matches(formats.Heading(1, "<Surface>", 1))  # a placeholder, unfilled


def test_each_declared_section_takes_a_heading_of_its_own() -> None:
    two = formats.Structure((formats.Section(2), formats.Section(2)))
    one_h2 = [formats.Heading(2, "Only", 3)]
    assert formats.departures(one_h2, two) == [
        formats.Departure(formats.Section(2), formats.MISSING)
    ]
    # Text fixed first: the one `## Install` serves the section that names it.
    either = formats.Structure((formats.Section(2), formats.Section(2, "Install")), ordered=False)
    assert formats.departures([formats.Heading(2, "Install", 3)], either) == [
        formats.Departure(formats.Section(2), formats.MISSING)
    ]


# What a section is: a `#` heading at the start of a line, below the front matter,
# outside fenced code and outside an HTML comment.


def _headings(text: str) -> list[tuple[int, str, int]]:
    return [(h.level, h.text, h.line) for h in formats.headings(text)]


def test_a_heading_is_a_line_of_hashes_at_the_start_of_a_line_below_the_front_matter() -> None:
    text = (
        "---\n# a YAML comment, not a heading\nkind: reference\n---\n"  # lines 1-4
        "# Title ##\n"  # 5: the closing run of `#` is not text
        "#Not a heading\n"  # 6: no space after the `#`
        " ## One space in\n"  # 7: indented, as under a list item
        "    # four spaces: indented code\n"  # 8
        "####### seven\n"  # 9: more than six
        "## Closing# kept\n"  # 10
        "#\n"  # 11: an empty heading
        "Underlined\n==========\n"  # 12-13: a setext heading
        "<h2>In HTML</h2>\n"  # 14
        "> ## In a block quote\n"  # 15
        "- ## On a list item's line\n"  # 16
    )
    assert _headings(text) == [(1, "Title", 5), (2, "Closing# kept", 10), (1, "", 11)]
    assert _headings("# One\r\n\r\n## Two\r\n") == [(1, "One", 1), (2, "Two", 3)]


def test_a_line_inside_fenced_code_is_no_heading() -> None:
    text = (
        "```python\n# in code\n```\n"  # lines 1-3
        "~~~~\n# in code\n~~~\n# still in: a closing fence is as long as the opening\n~~~~\n"
        "``` `not` a fence\n"  # 9: a backtick fence's info has no backtick
        "## Read\n"  # 10
    )
    assert _headings(text) == [(2, "Read", 10)]
    assert _headings("```\n# never closed\n") == []


@pytest.mark.parametrize(
    ("opening", "inside", "closing"),
    [
        ("- ```sh", "  # install", "  ```"),  # under a list item, as a renderer indents it
        ("- ```sh", "# install", "```"),
        ("1. ~~~", "# install", "   ~~~"),
        ("> ```", "> # install", "> ```"),
        ("- > ```", "# install", "  > ```"),
        ("      ```", "# install", "```"),  # under a nested list item
    ],
)
def test_a_fence_opens_after_list_and_quote_markers_and_closes_at_any_indentation(
    opening: str, inside: str, closing: str
) -> None:
    """The closing fence closes the one that is open and opens none: what follows is read."""
    text = f"# Tool\n\n{opening}\n{inside}\n{closing}\n\n## Usage\n"
    assert _headings(text) == [(1, "Tool", 1), (2, "Usage", 7)]


def test_a_line_inside_an_html_comment_is_no_heading() -> None:
    text = (
        "<!--\n# Hidden\n-->\n"  # lines 1-3
        "# Shown\n"  # 4
        "<!-- closed on its own line -->\n"  # 5
        "## Also shown\n"  # 6
        "  <!-- opens\n## Hidden too\nand closes --> here\n"  # 7-9
        "### Last\n"  # 10
    )
    assert _headings(text) == [(1, "Shown", 4), (2, "Also shown", 6), (3, "Last", 10)]
    # Fenced code holds no comment: the `<!--` in it opens none.
    assert _headings("```html\n<!--\n```\n# Read\n") == [(1, "Read", 4)]


@pytest.mark.parametrize(
    "text",
    [
        "# No front matter\n\n## Part\n",
        "---\r\nkind: reference\r\n---\r\n\r\n# Title\r\n",
        "---\nkind: reference\n---\n\n# Title\n\n---\n\n## After a rule in the body\n",
        "---\n# never closed, so no front matter\nkind: reference\n",
        "--- \n# a YAML comment\n---\t\n# Title\n",
        "Prose first.\n\n---\n# Between two rules\n---\n",
    ],
)
def test_the_body_starts_where_the_backbone_s_front_matter_split_puts_it(text: str) -> None:
    """The capability's scripts import nothing of the backbone, so the reader finds
    the body itself; it finds the one the backbone's split gives."""
    _front, body = document_parts.split_front_matter(text)
    assert [(h.level, h.text) for h in formats.headings(text)] == [
        (h.level, h.text) for h in formats.headings(body)
    ]


# The one declaration: the templates follow it, and it is what the schema says.


def test_the_declared_kinds_are_the_page_templates_and_validate() -> None:
    data = YAML(typ="safe").load(PAGE_KINDS.read_text(encoding="utf-8"))
    schema = json.loads((CAPABILITY / "schemas" / "page-kinds.schema.json").read_text("utf-8"))
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(data)) == []
    assert sorted(formats.read_structures(PAGE_KINDS)) == sorted(data["kinds"]) == PAGE_TEMPLATES


@pytest.mark.parametrize("kind", PAGE_TEMPLATES)
def test_each_page_template_filled_in_follows_the_structure_its_kind_declares(kind: str) -> None:
    """A template is the starting shape a writer fills in: with its placeholders
    worded it satisfies its kind's structure, and left as shipped it lacks every
    section the writer words."""
    structure = formats.read_structures(PAGE_KINDS)[kind]
    template = (CAPABILITY / "templates" / f"{kind}.md").read_text(encoding="utf-8")
    filled = re.sub(r"<[^<>\n]+>", "words", template)
    assert formats.departures(formats.headings(filled), structure) == []
    assert formats.departures(formats.headings(template), structure) == [
        formats.Departure(section, formats.MISSING)
        for section in structure.sections
        if section.text is None
    ]


# --- one home for discovery (#1099; ADR-057 point 2) -------------------------------------

#: What re-reading the declarations, walking the places or matching an anchor would
#: take — each a pattern over a script's code (comments and docstrings left out)
#: and what it would mean. Where artefacts are is the backbone's discovery, read
#: through `pkit friction artefacts --json`, and what an anchor matches its
#: explanation's, `pkit friction explain --json`; a second computation drifts.
DISCOVERY_TOKENS = {
    r"\bfnmatch\b": "a glob matcher (fnmatch)",
    r"\b(?:import|from)\s+glob\b": "a glob matcher (glob)",
    r"\.r?glob\(": "a walk by glob",
    r"compile_glob|_segment_regex|pattern_matcher": "a ported glob matcher",
    r"['\"]\*\*['\"]": "`**`-matching code",
    r"\bos\.walk\b": "a walk of the working tree",
    r"ls-files": "a listing of the working tree",
    r"\.get\(\s*['\"]friction['\"]|\[\s*['\"]friction['\"]\s*\]": (
        "`friction.places` parsing (the friction settings)"
    ),
    r"\.get\(\s*['\"]locations['\"]|docs-locations": "a capability's locations resolved",
    r"manifest\.yaml": "the installed capabilities read",
    r":\([^)]*\bglob\b[^)]*\)|GIT_GLOB_PATHSPECS": "a pattern matched as git's glob pathspec",
}


def _code(text: str) -> str:
    """A script's code without its comments and docstrings."""
    tree = ast.parse(text)
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (
            isinstance(body, list)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body[0] = ast.Pass()
    return ast.unparse(tree)


def _discovery_tokens(text: str) -> list[str]:
    code = _code(text)
    return [meaning for token, meaning in DISCOVERY_TOKENS.items() if re.search(token, code)]


def test_the_guard_recognises_a_ported_discovery() -> None:
    """The guard is not vacuous: the reading this capability carried before #1099
    trips it, while prose about the same things does not."""
    ported = (
        '"""Places are read from `friction.places`, matched with fnmatch and `**`."""\n'
        "import fnmatch\n"
        "def _compile_glob(p):\n    return p.replace('**', '.*')\n"
        "places = config.get('friction', {}).get('places')\n"
        "listed = run(['git', 'ls-files'])\n"
    )
    assert _discovery_tokens(ported) == [
        "a glob matcher (fnmatch)",
        "a ported glob matcher",
        "`**`-matching code",
        "a listing of the working tree",
        "`friction.places` parsing (the friction settings)",
    ]
    assert _discovery_tokens('"""fnmatch, `**`, ls-files and manifest.yaml, in prose."""\n') == []


def test_the_capability_s_scripts_carry_no_discovery_of_their_own() -> None:
    """living-docs reads the places, the files each matches and their front matter
    through `pkit friction artefacts`; no script of it matches, lists or reads a
    place declaration itself."""
    scripts = sorted((CAPABILITY / "scripts").rglob("*.py"))
    assert scripts
    found = {
        path.relative_to(CAPABILITY).as_posix(): tokens
        for path in scripts
        if (tokens := _discovery_tokens(path.read_text(encoding="utf-8")))
    }
    assert found == {}
