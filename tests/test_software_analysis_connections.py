"""software-analysis' connections (#1001; DEC-001 points 7 and 8, COR-052, COR-053).

The capability provides the `pkit::analysis` role and defines one data point
under it, `revalidation-evidence` (`union`, no default, inert `fallback`), and
contributes the analysis' actors to the documentation role's readers point,
`pkit::documentation:readers`, through its command filler, `fill-readers`.

- the pieces: the package declaration and the evidence point's companion schema;
- the contribution through the real backbone: with software-analysis alone it
  is inert — no documentation provider, its filler never run; with living-docs
  installed, the actors in force are readers beside the default ones, a page
  may name one, and an actors file that cannot be read leaves the readers
  point unresolved rather than answer without them;
- the evidence point through the real backbone — a project filler's entries
  resolve against the companion schema, a malformed one is the project's error
  — and in the check: a record cites evidence as support for an outcome and
  never in place of one; a citation the point does not hold only warns, since
  evidence advises.

The capability's scripts are pointed at this interpreter in the adopter copy,
and the `pkit` they read through is the real CLI under this interpreter
(`pkit_on_path`), so no test reaches `uv` or the network.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ACTORS,
    CAPABILITY,
    REPO,
    SA,
    VALIDATE,
    installed,
    load,
    run_script,
    seed,
)

FILL = SA / "scripts" / "fill-readers.py"
LD = Path(".pkit") / "capabilities" / "living-docs"
LIVING_DOCS = REPO / LD

ROLE = "pkit::analysis"
EVIDENCE = "pkit::analysis:revalidation-evidence"
READERS = "pkit::documentation:readers"
EVIDENCE_FILLER = "tech-docs/pkit/fillers/pkit/analysis/revalidation-evidence.yaml"
RECORD = "tech-docs/analysis/revalidations/2026-10-01-first-run.md"

#: Commits by their full names, as the evidence point writes them.
SHA = "78981922613b2afb6025042ff6bd878ac1994e85"
OTHER = "d670460b4b4aece5915caf5c68d12f560a9fe3e4"


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """An adopter with software-analysis alone."""
    return installed(make_adopter_repo, monkeypatch)


@pytest.fixture
def documented(project: AdopterRepo) -> AdopterRepo:
    """The adopter with living-docs installed beside it, its validator under this
    interpreter: a provider of the documentation role."""
    project.install_capabilities("living-docs")
    path = project.root / LD / "scripts" / "validate.py"
    body = path.read_text(encoding="utf-8").split("\n", 1)[1]
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    return project


def _package(root: Path) -> dict[str, Any]:
    return load((root / "package.yaml").read_text(encoding="utf-8"))


def _validator(root: Path, name: str) -> Any:
    """A companion schema's validator, its `$ref`s resolved over its siblings as the
    backbone resolves a point's companion. Untyped: its methods' stubs are partly
    unknown."""
    schemas = [json.loads(p.read_text(encoding="utf-8")) for p in (root / "schemas").glob("*.json")]
    registry = Registry[Any]().with_resources(
        (schema["$id"], Resource[Any].from_contents(schema))
        for schema in schemas
        if "$id" in schema
    )
    schema = json.loads((root / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator: Any = Draft202012Validator(schema, registry=registry)
    return validator


def _resolve(address: str) -> dict[str, Any]:
    """`pkit connections resolve <address> --json`, in the adopter."""
    result = CliRunner().invoke(main, ["connections", "resolve", address, "--json"])
    return json.loads(result.output)


def _check(repo: AdopterRepo) -> dict[str, Any]:
    """The validator's findings document, run as the backbone runs it."""
    completed = run_script(repo, VALIDATE, "--json")
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _findings(document: Mapping[str, Any], severity: str) -> list[tuple[str, str]]:
    return [
        (f["location"], f["message"]) for f in document["findings"] if f["severity"] == severity
    ]


# --- the pieces --------------------------------------------------------------------------


def test_the_package_provides_the_role_and_declares_the_point_and_the_contribution() -> None:
    package = _package(CAPABILITY)
    connections = package["connections"]
    assert connections["roles"] == [ROLE]
    (address,) = connections["extension-points"]["accepts"]
    point = connections["extension-points"]["accepts"][address]
    assert address == EVIDENCE
    assert point == {  # no default takes part (DEC-001 point 7)
        "schema_version": 1,
        "schema": "revalidation-evidence.schema.json",
        "description": point["description"],
        "combination": "union",
        "inert": "fallback",
    }
    assert point["description"].strip()
    assert (CAPABILITY / "schemas" / point["schema"]).is_file()

    (contribution,) = connections["extensions"]["contributes"]
    assert contribution == {
        "point": READERS,
        "schema_version": 1,
        "command": "fill-readers",
        "description": contribution["description"],
    }
    # The version living-docs defines the point at: in step, so the contribution binds.
    readers = _package(LIVING_DOCS)["connections"]["extension-points"]["accepts"][READERS]
    assert readers["schema_version"] == contribution["schema_version"]
    command = package["commands"]["fill-readers"]
    assert command["query-contract"] is True
    assert (CAPABILITY / command["script"]).is_file()


EVIDENCE_ENTRY = {
    "id": f"UC-003@{SHA}",
    "artefact": "UC-003",
    "commit": SHA,
    "result": "passed",
    "ran": "tests/test_run.py::test_sandbox",
    "steps": ["1", "2", "2a"],
    "where": "https://ci.example/runs/42",
    "by": "the pipeline",
}


def test_the_evidence_schema_keys_an_entry_by_artefact_and_commit() -> None:
    schema = _validator(CAPABILITY, "revalidation-evidence.schema.json")
    assert list(schema.iter_errors([EVIDENCE_ENTRY])) == []
    required = {k: EVIDENCE_ENTRY[k] for k in ("id", "artefact", "commit", "result", "ran")}
    assert list(schema.iter_errors([required])) == []
    for broken in (
        {**EVIDENCE_ENTRY, "id": "UC-003"},
        {**EVIDENCE_ENTRY, "id": f"UC-3@{SHA}"},
        {**EVIDENCE_ENTRY, "artefact": "user"},
        {**EVIDENCE_ENTRY, "commit": "HEAD"},
        {**EVIDENCE_ENTRY, "commit": SHA[:7]},  # a short name: one pair, one spelling
        {**EVIDENCE_ENTRY, "id": f"UC-003@{SHA[:7]}"},
        {**EVIDENCE_ENTRY, "result": "flaky"},
        {**EVIDENCE_ENTRY, "ran": ""},
        {**EVIDENCE_ENTRY, "steps": ["two"]},
        {k: v for k, v in EVIDENCE_ENTRY.items() if k != "ran"},
        {**EVIDENCE_ENTRY, "outcome": "holds"},
    ):
        assert not schema.is_valid([broken]), broken


# --- the contribution to the readers point (DEC-001 point 8) ---------------------------------


def test_alone_the_contribution_is_inert_and_its_filler_never_runs(project: AdopterRepo) -> None:
    """No capability provides the documentation role: the contribution is reported as
    having no active provider, never as an error, and its filler never runs."""
    (project.root / FILL).write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["--color", "never", "validate", "--only", "connections"])
    assert result.exit_code == 0, result.output
    assert "pkit::analysis → software-analysis" in result.output
    assert f"software-analysis contributes {READERS!r}: no active provider" in result.output
    assert "0 error(s), 0 warning(s)." in result.output
    assert _resolve(READERS) == {
        "address": READERS,
        "defined": False,
        "resolved": False,
        "value": None,
        "why": "role 'pkit::documentation' has no active provider",
    }
    shown = CliRunner().invoke(main, ["capabilities", "show", "software-analysis"])
    assert shown.exit_code == 0, shown.output
    assert "Roles it provides (1)\n    pkit::analysis — software-analysis" in shown.output
    assert f"contributes {READERS} (v1, command fill-readers)" in shown.output
    assert shown.output.endswith(
        f"What connects here (1)\n    out software-analysis contributes {READERS}: "
        "no active provider\n"
    )


def _actor(name: str, status: str, *needs: str) -> dict[str, Any]:
    anchors = {"path": ["src/**"]}
    return {
        "name": name,
        "status": status,
        "needs": list(needs),
        "pkit": {"friction": {"anchors": anchors}},
    }


def _actors(repo: AdopterRepo) -> None:
    """Two actors in force with their needs, and a withdrawn one, in the actors'
    collection file — front matter written as JSON, valid YAML and exact about strings."""
    actors = {
        "ACT-operator": _actor("Operator", "active", "Keep the service up."),
        "ACT-retired": _actor("Retired", "withdrawn", "Nothing any more"),
        "ACT-tester": _actor(
            "Test author",
            "active",
            "Run the suite against a clean sandbox",
            "Read a failure's cause",
        ),
    }
    repo.write({ACTORS: f"---\n{json.dumps(actors, indent=2)}\n---\n\n# Actors\n"})


def test_the_actors_in_force_are_readers_beside_the_defaults(documented: AdopterRepo) -> None:
    _actors(documented)
    entries = {e["id"]: e for e in _resolve(READERS)["entries"]}
    assert sorted(entries) == ["act-operator", "act-tester", "maintainer", "user"]
    assert {i: e["origin"] for i, e in entries.items()} == {
        "act-operator": "software-analysis",
        "act-tester": "software-analysis",
        "maintainer": "the default",
        "user": "the default",
    }
    ours = [entries["act-operator"]["value"], entries["act-tester"]["value"]]
    assert ours == [
        {
            "id": "act-operator",
            "description": (
                "Operator, the analysis' actor ACT-operator. Needs: Keep the service up."
            ),
        },
        {
            "id": "act-tester",
            "description": "Test author, the analysis' actor ACT-tester. Needs: Run the suite "
            "against a clean sandbox; Read a failure's cause.",
        },
    ]
    # The filler's own envelope, in living-docs' shape of the point.
    completed = run_script(documented, FILL, "--json")
    assert completed.returncode == 0, completed.stderr
    envelope = json.loads(completed.stdout)
    assert envelope == {"schema_version": 1, "value": ours}
    readers_schema = _validator(LIVING_DOCS, "readers.schema.json")
    assert list(readers_schema.iter_errors(envelope["value"])) == []
    human = run_script(documented, FILL)
    assert human.stdout.splitlines()[:2] == [
        f"{READERS}: 2 reader(s) from the analysis' actors",
        f"  act-operator — {ours[0]['description']}",
    ]


def test_a_page_may_name_an_actor_as_its_reader(documented: AdopterRepo) -> None:
    _actors(documented)
    page = "---\nreader: {reader}\nkind: signpost\n---\n\n# A page\n"
    documented.write({"docs/guide.md": page.format(reader="act-tester")})
    validate = documented.root / LD / "scripts" / "validate.py"
    completed = run_script(documented, validate.relative_to(documented.root), "--json")
    assert completed.returncode == 0, completed.stderr
    document = json.loads(completed.stdout)
    assert _findings(document, "error") == []
    assert (
        "readers (pkit::documentation:readers): act-operator, act-tester, maintainer, user; "
        "1 page reader(s) checked."
    ) in document["summary"]
    # A withdrawn actor is history, not a reader.
    documented.write({"docs/guide.md": page.format(reader="act-retired")})
    completed = run_script(documented, validate.relative_to(documented.root), "--json")
    ((location, _message),) = _findings(json.loads(completed.stdout), "error")
    assert location == "docs/guide.md:/reader"


def test_no_analysis_contributes_no_reader(documented: AdopterRepo) -> None:
    resolved = _resolve(READERS)
    assert resolved["resolved"], resolved["why"]
    assert [e["id"] for e in resolved["entries"]] == ["maintainer", "user"]
    ours = next(f for f in resolved["fillers"] if f["name"] == "software-analysis")
    assert (ours["state"], ours["query_contract"]) == ("taken", True)


def test_an_actors_file_that_cannot_be_read_leaves_the_readers_unresolved(
    documented: AdopterRepo,
) -> None:
    """The point's inert policy is `fail`: without the actors the filler gives no
    answer, never an empty one, and no page's reader is checked against the rest."""
    _actors(documented)
    documented.write({ACTORS: "---\nACT-tester: [unclosed\n---\n\n# Actors\n"})
    completed = run_script(documented, FILL, "--json")
    assert (completed.returncode, completed.stdout) == (1, "")
    assert completed.stderr == (
        f"error: the actors cannot be read: {ACTORS}'s front matter does not parse; "
        "no readers can be given.\n"
    )
    resolved = _resolve(READERS)
    assert not resolved["resolved"]
    ours = next(f for f in resolved["fillers"] if f["name"] == "software-analysis")
    assert ours["state"] == "inert"
    assert ours["reason"] == (
        "command 'fill-readers' exited 1: error: the actors cannot be read: "
        f"{ACTORS}'s front matter does not parse; no readers can be given"
    )
    # A file that is no collection of actors is no answer either.
    documented.write({ACTORS: "# Actors, in prose only\n"})
    completed = run_script(documented, FILL, "--json")
    assert completed.returncode == 1
    assert completed.stderr.startswith(f"error: the actors cannot be read: {ACTORS} has no ")


# --- the evidence point (DEC-001 point 7) ----------------------------------------------------


def _evidence(*entries: Mapping[str, Any]) -> str:
    return json.dumps({"schema_version": 1, "value": list(entries)}, indent=2) + "\n"


def _entry(artefact: str, commit: str = SHA, result: str = "passed") -> dict[str, str]:
    return {
        "id": f"{artefact}@{commit}",
        "artefact": artefact,
        "commit": commit,
        "result": result,
        "ran": f"tests/test_{artefact.lower().replace('-', '_')}.py",
    }


def test_the_evidence_point_resolves_from_the_project_filler(project: AdopterRepo) -> None:
    unfilled = _resolve(EVIDENCE)
    assert (unfilled["defined"], unfilled["provider"], unfilled["resolved"]) == (
        True,
        "software-analysis",
        False,
    )
    assert unfilled["why"] == "unfilled: no filler is declared and the point has no default"
    project.write({EVIDENCE_FILLER: _evidence(_entry("UC-001"), _entry("UC-002", result="failed"))})
    resolved = _resolve(EVIDENCE)
    assert resolved["resolved"], resolved["why"]
    assert (resolved["policy"], resolved["inert_policy"]) == ("union", "fallback")
    assert [(e["id"], e["origin"]) for e in resolved["entries"]] == [
        (f"UC-001@{SHA}", "project filler"),
        (f"UC-002@{SHA}", "project filler"),
    ]
    # An entry its schema refuses is the project's error, whatever the inert policy.
    project.write({EVIDENCE_FILLER: _evidence({**_entry("UC-001"), "result": "flaky"})})
    result = CliRunner().invoke(main, ["--color", "never", "validate", "--only", "connections"])
    assert result.exit_code == 1
    assert EVIDENCE_FILLER in result.output
    assert "'flaky' is not one of ['passed', 'failed']" in result.output
    assert not _resolve(EVIDENCE)["resolved"]


def _record(outcomes: Mapping[str, str], evidence: list[str] | None = None) -> str:
    front: dict[str, Any] = {
        "change": "#1001",
        "trigger": "drift",
        "date": "2026-10-01",
        "by": "Alex",
        "outcomes": dict(outcomes),
    }
    if evidence is not None:
        front["evidence"] = evidence
    return f"---\n{json.dumps(front, indent=2)}\n---\n\n# 2026-10-01 — First run\n"


def test_a_record_cites_evidence_as_support_for_an_outcome(project: AdopterRepo) -> None:
    seed(project)
    project.write(
        {
            EVIDENCE_FILLER: _evidence(_entry("UC-001"), _entry("UC-002", result="failed")),
            RECORD: _record(
                {"UC-001": "holds", "UC-002": "code-regressed"},
                [f"UC-001@{SHA}", f"UC-002@{SHA}"],
            ),
        }
    )
    document = _check(project)
    assert document["findings"] == []
    assert document["summary"][1] == (f"evidence ({EVIDENCE}): 2 held; 2 citation(s) checked.")


def test_evidence_never_replaces_an_outcome(project: AdopterRepo) -> None:
    """Evidence for an artefact the record gives no outcome leaves the record
    incomplete: the evidence informs the revalidation, and is never it."""
    seed(project)
    project.write(
        {
            EVIDENCE_FILLER: _evidence(_entry("UC-001"), _entry("UC-002")),
            RECORD: _record({"UC-001": "holds"}, [f"UC-001@{SHA}", f"UC-002@{SHA}"]),
        }
    )
    assert _findings(_check(project), "error") == [
        (
            f"{RECORD}:/evidence/1",
            f"cites evidence UC-002@{SHA} for UC-002, to which it gives no outcome: evidence "
            "supports a revalidation's outcome and never replaces it — give UC-002 its "
            "outcome, or drop the citation (DEC-001 point 7)",
        )
    ]
    # The record alone decides it: with nothing filling the point, it is still incomplete.
    project.write({EVIDENCE_FILLER: None})
    assert [loc for loc, _ in _findings(_check(project), "error")] == [f"{RECORD}:/evidence/1"]
    # And a citation that is no evidence id is the schema's to refuse.
    project.write({RECORD: _record({"UC-001": "holds"}, ["UC-001@HEAD"])})
    ((location, message),) = _findings(_check(project), "error")
    assert location == f"{RECORD}:/evidence/0"
    assert message.startswith("'UC-001@HEAD' does not match")


def test_a_citation_the_point_does_not_hold_only_warns(project: AdopterRepo) -> None:
    """The evidence advises: a citation the point does not hold — a typo, or a result
    no filler gives any more — asks for attention and never fails."""
    seed(project)
    project.write(
        {
            EVIDENCE_FILLER: _evidence(_entry("UC-001")),
            RECORD: _record({"UC-001": "holds"}, [f"UC-001@{OTHER}"]),
        }
    )
    document = _check(project)
    assert _findings(document, "error") == []
    assert _findings(document, "warning") == [
        (
            f"{RECORD}:/evidence/0",
            f"cites evidence UC-001@{OTHER}, which {EVIDENCE} does not hold: cite an entry the "
            "point holds, by its `<artefact>@<commit>` id, or drop the citation (DEC-001 "
            "point 7)",
        )
    ]
    assert run_script(project, VALIDATE).returncode == 0


def test_an_unresolved_evidence_point_is_one_warning(project: AdopterRepo) -> None:
    seed(project)
    project.write(
        {
            RECORD: _record(
                {"UC-001": "holds", "UC-002": "holds"}, [f"UC-001@{SHA}", f"UC-002@{SHA}"]
            )
        }
    )
    document = _check(project)
    assert _findings(document, "error") == []
    assert _findings(document, "warning") == [
        (
            EVIDENCE,
            "evidence unresolved — unfilled: no filler is declared and the point has no "
            "default. No record's citation can be checked until the point resolves; evidence "
            "advises, so nothing fails on it (DEC-001 point 7)",
        )
    ]
    assert document["summary"][1] == (
        f"evidence ({EVIDENCE}) unresolved: 2 citation(s) not checked."
    )


def test_the_point_is_read_only_when_a_record_cites_evidence(
    project: AdopterRepo,
    pkit_on_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `pkit` that answers nothing for the point is never asked while no record
    cites evidence; once one does, no document is an unresolved point, never a pass."""
    broken = tmp_path_factory.mktemp("broken-pkit")
    (broken / "pkit").write_text(
        f'#!/bin/sh\nif [ "$1" = connections ]; then exit 3; fi\nexec "{pkit_on_path}/pkit" "$@"\n',
        encoding="utf-8",
    )
    (broken / "pkit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{broken}{os.pathsep}{os.environ['PATH']}")
    seed(project)
    project.write({RECORD: _record({"UC-001": "holds"})})
    document = _check(project)
    assert document["findings"] == []
    assert len(document["summary"]) == 1
    project.write({RECORD: _record({"UC-001": "holds"}, [f"UC-001@{SHA}"])})
    ((location, message),) = _findings(_check(project), "warning")
    assert location == EVIDENCE
    assert f"`pkit connections resolve {EVIDENCE} --json` exited 3" in message
