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
  resolve against the companion schema, a malformed one is the project's error;
  an entry is keyed by artefact, commit and check (#1143), so two providers'
  results for one artefact at one commit stand side by side, and only two that
  claim one check collide, which the project settles — and in the check: a
  record copies the evidence it draws on, whole, as support for an outcome and
  never in place of one; an entry's id is its own three fields; a journey's
  steps are use cases of the analysis; a result at odds with its outcome, or a
  copy that differs from what the point now holds, only warns, since evidence
  advises; an id the point no longer holds says nothing, since the record is
  history; and the point's own entries warn on an id not their own and on a
  capability's check that opens with another name.

The capability's scripts are pointed at this interpreter in the adopter copy,
and the `pkit` they read through is the real CLI under this interpreter
(`pkit_on_path`), so no test reaches `uv` or the network.
"""

from __future__ import annotations

import ast
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
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ACTORS,
    CAPABILITY,
    JOURNEYS,
    REPO,
    SA,
    USE_CASES,
    VALIDATE,
    installed,
    load,
    prepare_seeded,
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
def seeded(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The project with the seed stamped and filled (`prepare_seeded`)."""
    return installed(make_adopter_repo, monkeypatch, then=prepare_seeded)


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


def _constant(script: Path, name: str) -> Any:
    """A module-level constant of one of the capability's scripts, read from its
    source: the scripts run in their own environment, and their `_lib` is not
    importable beside living-docs'."""
    for node in ast.parse(script.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{script.name} defines no {name}")


def test_the_filler_answers_the_point_and_version_the_package_declares() -> None:
    """The envelope's `schema_version` is the filler's; the version the backbone binds
    the contribution by is the package's. Held equal, the filler never answers a
    version the contribution does not declare."""
    (contribution,) = _package(CAPABILITY)["connections"]["extensions"]["contributes"]
    readers = CAPABILITY / "scripts" / "_lib" / "readers.py"
    assert _constant(readers, "POINT") == contribution["point"]
    assert _constant(readers, "POINT_VERSION") == contribution["schema_version"]


#: An executed check's name, as a provider gives it: a test's name, slugged.
SANDBOX = "pytest-bridge.test-run.test-sandbox"

EVIDENCE_ENTRY = {
    "id": f"UC-003@{SHA}#{SANDBOX}",
    "artefact": "UC-003",
    "commit": SHA,
    "check": SANDBOX,
    "result": "passed",
    "ran": "tests/test_run.py::test_sandbox",
    "steps": ["1", "2", "2a"],
    "where": "https://ci.example/runs/42",
    "by": "the pipeline",
}


def _keyed(entry: Mapping[str, Any], **fields: Any) -> dict[str, Any]:
    """`entry` with `fields` changed and its id written from its own three fields."""
    changed = {**entry, **fields}
    return {**changed, "id": f"{changed['artefact']}@{changed['commit']}#{changed['check']}"}


def test_the_evidence_schema_keys_an_entry_by_artefact_commit_and_check() -> None:
    schema = _validator(CAPABILITY, "revalidation-evidence.schema.json")
    assert list(schema.iter_errors([EVIDENCE_ENTRY])) == []
    required = {
        k: EVIDENCE_ENTRY[k] for k in ("id", "artefact", "commit", "check", "result", "ran")
    }
    assert list(schema.iter_errors([required])) == []
    # `by` stays: who ran it — or, on an entry the project writes in a capability's stead,
    # who wrote it.
    assert schema.is_valid([{**EVIDENCE_ENTRY, "by": "Alex, rerun by hand"}])
    # A later word may begin with a digit; the check's other words are the provider's own.
    assert schema.is_valid([_keyed(EVIDENCE_ENTRY, check="trace-runner.2026-walk")])
    for broken in (
        {**EVIDENCE_ENTRY, "id": "UC-003"},
        {**EVIDENCE_ENTRY, "id": f"UC-3@{SHA}#{SANDBOX}"},
        {**EVIDENCE_ENTRY, "id": f"UC-003@{SHA}"},  # no check
        {**EVIDENCE_ENTRY, "id": f"UC-003@{SHA}#"},
        {k: v for k, v in EVIDENCE_ENTRY.items() if k != "check"},
        {**EVIDENCE_ENTRY, "artefact": "user"},
        {**EVIDENCE_ENTRY, "commit": "HEAD"},
        {**EVIDENCE_ENTRY, "commit": SHA[:7]},  # a short name: one commit, one spelling
        {**EVIDENCE_ENTRY, "id": f"UC-003@{SHA[:7]}#{SANDBOX}"},
        _keyed(EVIDENCE_ENTRY, check="pytest-bridge.test_run"),  # an underscore
        _keyed(EVIDENCE_ENTRY, check="Pytest-bridge.test-run"),  # a capital
        _keyed(EVIDENCE_ENTRY, check="2-bridge.test-run"),  # a leading digit
        _keyed(EVIDENCE_ENTRY, check="pytest-bridge..test-run"),  # an empty word
        _keyed(EVIDENCE_ENTRY, check="tests/test_run.py::test_sandbox"),  # not slugged
        {**EVIDENCE_ENTRY, "result": "flaky"},
        {**EVIDENCE_ENTRY, "ran": ""},
        {k: v for k, v in EVIDENCE_ENTRY.items() if k != "ran"},
        {**EVIDENCE_ENTRY, "outcome": "holds"},
    ):
        assert not schema.is_valid([broken]), broken


@pytest.mark.parametrize(
    ("artefact", "steps", "admitted"),
    [
        ("UC-003", ["1", "2", "2a"], True),  # a use case: steps and variants
        ("UC-003", ["two"], False),
        ("UC-003", ["UC-001"], False),
        ("UC-003", ["2", "2"], False),  # a set
        ("JRN-001", ["UC-001", "UC-002"], True),  # a journey: the use cases it passed through
        ("JRN-001", ["1", "2"], False),
        ("JRN-001", ["UC-001", "UC-001"], False),  # each once
        ("ACT-tester", ["1"], False),  # an actor or a term has none
        ("TERM-sandbox", ["UC-001"], False),
    ],
)
def test_the_evidence_steps_are_a_set_by_the_artefact_s_kind(
    artefact: str, steps: list[str], admitted: bool
) -> None:
    schema = _validator(CAPABILITY, "revalidation-evidence.schema.json")
    entry = _keyed(EVIDENCE_ENTRY, artefact=artefact, steps=steps)
    assert schema.is_valid([entry]) is admitted, entry
    if artefact.startswith(("ACT-", "TERM-")):
        bare = {k: v for k, v in _keyed(EVIDENCE_ENTRY, artefact=artefact).items() if k != "steps"}
        assert schema.is_valid([bare])


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
        "from": "resolution",
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
    # A withdrawn actor is history, not a reader: the page naming it fails living-docs'
    # check, while the analysis, withdrawing an actor soundly, passes its own.
    documented.write({"docs/guide.md": page.format(reader="act-retired")})
    completed = run_script(documented, validate.relative_to(documented.root), "--json")
    ((location, _message),) = _findings(json.loads(completed.stdout), "error")
    assert location == "docs/guide.md:/reader"
    assert run_script(documented, VALIDATE).returncode == 0


def test_an_entry_that_is_no_actor_is_no_reader(documented: AdopterRepo) -> None:
    """The actors file is judged as a whole, an entry alone: an entry whose key is no
    actor id is not a reader — the filler skips it and still answers — and the
    capability's own check reports it."""
    actors = {
        "ACT-tester": _actor("Test author", "active", "Run the suite"),
        "USER-stray": _actor("Stray", "active", "Anything"),
    }
    documented.write({ACTORS: f"---\n{json.dumps(actors, indent=2)}\n---\n\n# Actors\n"})
    completed = run_script(documented, FILL, "--json")
    assert completed.returncode == 0, completed.stderr
    assert [reader["id"] for reader in json.loads(completed.stdout)["value"]] == ["act-tester"]
    assert [e["id"] for e in _resolve(READERS)["entries"]] == ["act-tester", "maintainer", "user"]
    locations = [location for location, _message in _findings(_check(documented), "error")]
    assert f"{ACTORS}#USER-stray" in locations


def test_no_analysis_contributes_no_reader(documented: AdopterRepo) -> None:
    resolved = _resolve(READERS)
    assert resolved["resolved"], resolved["why"]
    assert [e["id"] for e in resolved["entries"]] == ["maintainer", "user"]
    ours = next(f for f in resolved["fillers"] if f["name"] == "software-analysis")
    assert (ours["state"], ours["query_contract"]) == ("taken", True)


def test_an_actors_file_that_cannot_be_read_leaves_the_readers_unresolved(
    documented: AdopterRepo,
) -> None:
    """A command filler fails closed whatever the point's policy (COR-052 point 6):
    without the actors it gives no answer, never an empty one; and under the
    readers point's `fail` policy no page's reader is checked against the rest."""
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


#: The check the project's own entries are reported under: its own opening name.
RUN = "project.run-suite"


def _evidence(*entries: Mapping[str, Any]) -> str:
    return json.dumps({"schema_version": 1, "value": list(entries)}, indent=2) + "\n"


def _id(artefact: str, commit: str = SHA, check: str = RUN) -> str:
    return f"{artefact}@{commit}#{check}"


def _entry(
    artefact: str, commit: str = SHA, result: str = "passed", check: str = RUN
) -> dict[str, Any]:
    return {
        "id": _id(artefact, commit, check),
        "artefact": artefact,
        "commit": commit,
        "check": check,
        "result": result,
        "ran": f"tests/test_{artefact.lower().replace('-', '_')}.py",
    }


def _reporter(repo: AdopterRepo, name: str, *entries: Mapping[str, Any]) -> None:
    """A capability of the test's own, registered in place, reporting `entries` to the
    evidence point as its value: a provider of executed results, which software-analysis
    never is (DEC-001 point 7). Staged again, it reports the new entries instead."""
    root = repo.pkit / "capabilities" / name
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "noop.py").write_text("", encoding="utf-8")
    package = {
        "schema_version": 2,
        "component": {"kind": "capability", "name": name, "version": "0.1.0"},
        "description": f"Reports executed results as {name}.",
        "requires_backbone": ">=0.0.0",
        "commands": {"noop": {"script": "scripts/noop.py", "help": "Nothing."}},
        "connections": {
            "extensions": {
                "contributes": [{"point": EVIDENCE, "schema_version": 1, "value": list(entries)}]
            }
        },
    }
    (root / "package.yaml").write_text(json.dumps(package, indent=2), encoding="utf-8")
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    if not any(component.name == name for component in backbone.components):
        backbone.components.append(
            ComponentRegistryEntry(
                kind="capability",
                name=name,
                manifest=f".pkit/capabilities/{name}/project/manifest.yaml",
                origin="incubated-in-repo",
            )
        )
        write_backbone_manifest(repo.root, backbone)


def _validate_connections() -> Any:
    """`pkit validate --only connections`, in the adopter."""
    return CliRunner().invoke(main, ["--color", "never", "validate", "--only", "connections"])


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
        (_id("UC-001"), "project filler"),
        (_id("UC-002"), "project filler"),
    ]
    # An entry its schema refuses is the project's error, whatever the inert policy.
    project.write({EVIDENCE_FILLER: _evidence({**_entry("UC-001"), "result": "flaky"})})
    result = _validate_connections()
    assert result.exit_code == 1
    assert EVIDENCE_FILLER in result.output
    assert "'flaky' is not one of ['passed', 'failed']" in result.output
    assert not _resolve(EVIDENCE)["resolved"]


# Each check a provider of the test's own runs, by the provider's name, as it names them.
BRIDGE = "pytest-bridge.test-run.test-sandbox"
TIMEOUT = "pytest-bridge.test-run.test-timeout"
TRACE = "trace-runner.walk"


def _held(resolved: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [(e["id"], e["origin"]) for e in resolved["entries"]]


def test_two_providers_report_one_artefact_at_one_commit_side_by_side(
    project: AdopterRepo,
) -> None:
    """A test runner and a trace runner covering one use case at one commit: each
    result under the provider's own check, so both stand and nothing collides."""
    _reporter(project, "pytest-bridge", _entry("UC-001", check=BRIDGE))
    _reporter(project, "trace-runner", _entry("UC-001", check=TRACE, result="failed"))
    resolved = _resolve(EVIDENCE)
    assert resolved["resolved"], resolved["why"]
    assert _held(resolved) == [
        (_id("UC-001", check=BRIDGE), "pytest-bridge"),
        (_id("UC-001", check=TRACE), "trace-runner"),
    ]
    result = _validate_connections()
    assert result.exit_code == 0, result.output
    assert "0 error(s), 0 warning(s)." in result.output


def test_two_providers_claiming_one_check_collide_until_the_project_settles_it(
    project: AdopterRepo,
) -> None:
    """Only a real double claim collides: the point is unresolved and `pkit validate`
    fails, `fallback` notwithstanding — the inert policy is about a filler that cannot
    answer, and both answered. An entry of the project's own under that id replaces
    both."""
    claimed = _entry("UC-001", check=BRIDGE)
    _reporter(project, "pytest-bridge", claimed)
    _reporter(project, "trace-runner", {**claimed, "result": "failed"})
    resolved = _resolve(EVIDENCE)
    assert resolved["inert_policy"] == "fallback"
    assert not resolved["resolved"]
    assert resolved["why"] == (
        f"entries collide: {_id('UC-001', check=BRIDGE)!r} (pytest-bridge, trace-runner)"
    )
    result = _validate_connections()
    assert result.exit_code == 1
    assert (
        f"'pytest-bridge' and 'trace-runner' both supply entry {_id('UC-001', check=BRIDGE)!r} "
        f"to union point {EVIDENCE!r}"
    ) in " ".join(result.output.split())

    settled = {**claimed, "result": "failed", "by": "Alex, rerun by hand"}
    project.write({EVIDENCE_FILLER: _evidence(settled)})
    resolved = _resolve(EVIDENCE)
    assert resolved["resolved"], resolved["why"]
    (entry,) = resolved["entries"]
    assert (entry["id"], entry["origin"], entry["replaces"], entry["value"]) == (
        _id("UC-001", check=BRIDGE),
        "project filler",
        ["pytest-bridge", "trace-runner"],
        settled,
    )
    assert _validate_connections().exit_code == 0


def test_one_provider_gives_each_result_its_own_check(project: AdopterRepo) -> None:
    """Two results of one provider for one artefact at one commit stand under two
    checks. Under one check the filler supplies an id twice: the whole filler is inert
    — all its evidence gone — and warned, and the other fillers still count."""
    sandbox, timeout = _entry("UC-001", check=BRIDGE), _entry("UC-001", check=TIMEOUT)
    _reporter(project, "pytest-bridge", sandbox, {**timeout, "result": "failed"})
    _reporter(project, "trace-runner", _entry("UC-001", check=TRACE))
    assert _held(_resolve(EVIDENCE)) == [
        (_id("UC-001", check=BRIDGE), "pytest-bridge"),
        (_id("UC-001", check=TIMEOUT), "pytest-bridge"),
        (_id("UC-001", check=TRACE), "trace-runner"),
    ]

    _reporter(project, "pytest-bridge", sandbox, {**sandbox, "result": "failed"})
    resolved = _resolve(EVIDENCE)
    assert resolved["resolved"], resolved["why"]
    assert _held(resolved) == [(_id("UC-001", check=TRACE), "trace-runner")]
    bridge = next(f for f in resolved["fillers"] if f["name"] == "pytest-bridge")
    assert bridge["state"] == "inert"
    assert f"entry id {_id('UC-001', check=BRIDGE)!r} appears twice" in bridge["reason"]
    result = _validate_connections()
    assert result.exit_code == 0, result.output
    output = " ".join(result.output.split())
    assert f"the contribution of 'pytest-bridge' to {EVIDENCE!r} is inert" in output
    assert "the point resolves from the remaining fillers" in output


def _record(outcomes: Mapping[str, str], evidence: list[Any] | None = None) -> str:
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


def test_a_record_copies_evidence_as_support_for_an_outcome(seeded: AdopterRepo) -> None:
    """The record shows the evidence it drew on: each entry copied whole, in the
    point's shape, and each equal to what the point holds under its id."""
    passed, failed = _entry("UC-001"), _entry("UC-002", result="failed")
    seeded.write(
        {
            EVIDENCE_FILLER: _evidence(passed, failed),
            RECORD: _record({"UC-001": "holds", "UC-002": "code-regressed"}, [passed, failed]),
        }
    )
    document = _check(seeded)
    # The evidence says nothing against the record; UC-002's regression is reported
    # open, as any is until its artefact is revalidated after the record.
    assert [f for f in document["findings"] if f["severity"] != "report"] == []
    ((location, message),) = _findings(document, "report")
    assert location == f"{RECORD}:/outcomes/UC-002"
    assert message.startswith("UC-002's regression is open")
    assert document["summary"][1] == (
        f"evidence ({EVIDENCE}): 2 held; 2 copied entry(ies) compared with it."
    )
    # The full entry, `steps`, `where` and `by` included, is a copy like any other.
    full = _keyed(EVIDENCE_ENTRY, artefact="UC-001")
    seeded.write({EVIDENCE_FILLER: _evidence(full), RECORD: _record({"UC-001": "holds"}, [full])})
    assert _check(seeded)["findings"] == []


def test_evidence_never_replaces_an_outcome(seeded: AdopterRepo) -> None:
    """Evidence for an artefact the record gives no outcome leaves the record
    incomplete: the evidence informs the revalidation, and is never it."""
    entries = [_entry("UC-001"), _entry("UC-002")]
    seeded.write(
        {
            EVIDENCE_FILLER: _evidence(*entries),
            RECORD: _record({"UC-001": "holds"}, entries),
        }
    )
    assert _findings(_check(seeded), "error") == [
        (
            f"{RECORD}:/evidence/1",
            f"cites evidence {_id('UC-002')} for UC-002, to which it gives no outcome: evidence "
            "supports a revalidation's outcome and never replaces it — give UC-002 its "
            "outcome, or drop the evidence (DEC-001 point 7)",
        )
    ]
    # The record alone decides it: with nothing filling the point, it is still incomplete.
    seeded.write({EVIDENCE_FILLER: None})
    assert [loc for loc, _ in _findings(_check(seeded), "error")] == [f"{RECORD}:/evidence/1"]
    # An entry of another shape is the schema's to refuse: a short commit, a bare id.
    seeded.write({RECORD: _record({"UC-001": "holds"}, [_entry("UC-001", commit=SHA[:7])])})
    assert sorted(loc for loc, _ in _findings(_check(seeded), "error")) == [
        f"{RECORD}:/evidence/0/commit",
        f"{RECORD}:/evidence/0/id",
    ]
    seeded.write({RECORD: _record({"UC-001": "holds"}, [_id("UC-001")])})
    ((location, message),) = _findings(_check(seeded), "error")
    assert location == f"{RECORD}:/evidence/0"
    assert "is not of type 'object'" in message


@pytest.mark.parametrize(
    ("commit", "check"), [(OTHER, RUN), (SHA, "project.other-run")], ids=["commit", "check"]
)
def test_an_evidence_entry_s_id_is_its_own_three_fields(
    seeded: AdopterRepo, commit: str, check: str
) -> None:
    """The id is the artefact, commit and check the result is for: an entry whose id
    names another commit or another check is an error naming the entry, and nothing
    more is read from it — which of the two is meant cannot be told."""
    miskeyed = {**_entry("UC-001"), "id": _id("UC-001", commit, check)}
    seeded.write(
        {
            # The point holds the id with other content: no second finding for one mistake.
            EVIDENCE_FILLER: _evidence(_entry("UC-001", commit, "failed", check)),
            RECORD: _record({"UC-002": "holds"}, [miskeyed]),
        }
    )
    document = _check(seeded)
    assert _findings(document, "warning") == []
    assert _findings(document, "error") == [
        (
            f"{RECORD}:/evidence/0",
            f"the evidence entry {_id('UC-001', commit, check)} is for {_id('UC-001')} by its "
            "own `artefact`, `commit` and `check`: an entry's id is the three parts it is for, "
            f"`<artefact>@<commit>#<check>` — write `id: {_id('UC-001')}`, or correct the "
            "fields (DEC-001 point 7)",
        )
    ]
    assert run_script(seeded, VALIDATE).returncode == 1


def _withdraw(repo: AdopterRepo, rel: str) -> None:
    path = repo.root / rel
    text = path.read_text(encoding="utf-8")
    assert "status: active" in text
    repo.write({rel: text.replace("status: active", "status: withdrawn", 1)})


def test_a_journey_s_evidence_names_use_cases_of_the_analysis(seeded: AdopterRepo) -> None:
    """A journey's steps are the use cases its run passed through: one the analysis
    does not hold is an error at that step; a withdrawn one is history, and stands."""
    walked = _entry("JRN-001", check=TRACE)
    walked["steps"] = ["UC-001", "UC-009", "UC-002"]
    seeded.write({RECORD: _record({"JRN-001": "holds"}, [walked])})
    assert _findings(_check(seeded), "error") == [
        (
            f"{RECORD}:/evidence/0/steps/1",
            "no use case UC-009 in the analysis: a journey's evidence names the use cases its "
            "run passed through, by id, withdrawn ones included (DEC-001 points 3 and 7)",
        )
    ]
    # Withdrawn since the run, the journey and its second use case with it: the record
    # still cites them, and its evidence with them.
    _withdraw(seeded, f"{JOURNEYS}/JRN-001-first-run.md")
    _withdraw(seeded, f"{USE_CASES}/UC-002-read-report.md")
    walked["steps"] = ["UC-001", "UC-002"]
    seeded.write({RECORD: _record({"JRN-001": "holds"}, [walked])})
    assert _findings(_check(seeded), "error") == []


@pytest.mark.parametrize(
    ("outcome", "result", "at_odds"),
    [
        ("holds", "failed", True),
        ("code-regressed", "passed", True),
        ("holds", "passed", False),
        ("code-regressed", "failed", False),
        ("analysis-stale", "failed", False),
        ("gap-found", "passed", False),
    ],
)
def test_a_result_at_odds_with_its_outcome_warns(
    seeded: AdopterRepo, outcome: str, result: str, at_odds: bool
) -> None:
    """DEC-001 point 7 pairs a passing result with holds and a failing one with a
    regression: evidence the other way round asks for attention, naming the
    artefact, and never fails — the revalidation decides."""
    entry = _entry("UC-001", result=result)
    seeded.write({EVIDENCE_FILLER: _evidence(entry), RECORD: _record({"UC-001": outcome}, [entry])})
    document = _check(seeded)
    assert _findings(document, "error") == []
    expected = (
        [
            (
                f"{RECORD}:/evidence/0",
                f"cites a {result} result, {_id('UC-001')}, for UC-001, whose outcome is "
                f"{outcome}: "
                "a passing result supports holds and a failing one is a regression's proof "
                "(DEC-001 point 7) — check UC-001's outcome against the evidence",
            )
        ]
        if at_odds
        else []
    )
    assert _findings(document, "warning") == expected


def test_a_copy_that_differs_from_the_point_warns(seeded: AdopterRepo) -> None:
    """The point now holds the id with other content: the copy strayed from its source,
    or the result at that commit was reported again otherwise. The evidence advises,
    so it only warns."""
    held = _entry("UC-001")
    copy = {**held, "ran": "tests/test_other.py", "where": "https://ci.example/runs/7"}
    seeded.write({EVIDENCE_FILLER: _evidence(held), RECORD: _record({"UC-001": "holds"}, [copy])})
    document = _check(seeded)
    assert _findings(document, "error") == []
    assert _findings(document, "warning") == [
        (
            f"{RECORD}:/evidence/0",
            f"its copy of {_id('UC-001')} differs from the entry {EVIDENCE} now holds under that "
            "id, in ran, where: the record keeps the evidence it drew on, so either the copy "
            "strayed from its source — correct it — or the result at that commit was reported "
            "again otherwise — revalidate UC-001 against it (DEC-001 point 7)",
        )
    ]
    assert run_script(seeded, VALIDATE).returncode == 0


def test_the_point_s_own_entries_warn_on_a_check_or_id_not_their_own(
    seeded: AdopterRepo,
) -> None:
    """Wherever the check reads the point — when a record copies evidence — each entry
    the point holds is read too. A capability's entry whose check opens with another
    name warns: the opening name is a convention, never refused. The project's entry
    under a capability's check does not — that is how the project replaces a
    capability's entry. An entry whose id is not its own three fields warns, whoever
    supplied it."""
    borrowed = _entry("UC-001", check=TRACE)  # pytest-bridge reporting under trace-runner's name
    _reporter(seeded, "pytest-bridge", borrowed, _entry("UC-002", check=BRIDGE, result="failed"))
    # The project replaces pytest-bridge's UC-002 entry, under pytest-bridge's check.
    replacing = {**_entry("UC-002", check=BRIDGE), "by": "Alex, rerun by hand"}
    smoke = "project.smoke"
    miskeyed = {**_entry("UC-001", check=smoke), "id": _id("UC-001", OTHER, smoke)}
    seeded.write(
        {
            EVIDENCE_FILLER: _evidence(replacing, miskeyed),
            RECORD: _record({"UC-002": "holds"}, [replacing]),
        }
    )
    document = _check(seeded)
    assert _findings(document, "error") == []
    assert _findings(document, "warning") == [
        (
            f"{EVIDENCE}#{_id('UC-001', check=TRACE)}",
            f"'pytest-bridge' reports it under the check {TRACE}, which opens with "
            "'trace-runner': a capability's checks open with its own name, so two providers' "
            "results for one artefact at one commit stand side by side and only a real double "
            "claim collides — 'pytest-bridge' names its checks pytest-bridge.… (DEC-001 point 7)",
        ),
        (
            f"{EVIDENCE}#{_id('UC-001', OTHER, smoke)}",
            f"the project's filler supplies it for {_id('UC-001', check=smoke)} by its own "
            "`artefact`, `commit` and `check`: an entry's id is the three parts it is for, "
            "`<artefact>@<commit>#<check>`, and a record that copies it is held to that — its "
            f"filler writes `id: {_id('UC-001', check=smoke)}`, or corrects the fields "
            "(DEC-001 point 7)",
        ),
    ]
    held = {e["id"]: e for e in _resolve(EVIDENCE)["entries"]}
    assert held[_id("UC-002", check=BRIDGE)]["replaces"] == ["pytest-bridge"]
    assert run_script(seeded, VALIDATE).returncode == 0


def test_a_copy_the_point_no_longer_holds_says_nothing(seeded: AdopterRepo) -> None:
    """A record is history: an id no filler reports any more, or a point that does not
    resolve, leaves the record's copy as the evidence, and says nothing."""
    old = _entry("UC-001", commit=OTHER)
    seeded.write(
        {EVIDENCE_FILLER: _evidence(_entry("UC-001")), RECORD: _record({"UC-001": "holds"}, [old])}
    )
    document = _check(seeded)
    assert document["findings"] == []
    assert document["summary"][1] == (
        f"evidence ({EVIDENCE}): 1 held; 1 copied entry(ies) compared with it."
    )
    seeded.write({EVIDENCE_FILLER: None})
    document = _check(seeded)
    assert document["findings"] == []
    assert document["summary"][1] == (
        f"evidence ({EVIDENCE}) unresolved — unfilled: no filler is declared and the point has "
        "no default; 1 copied entry(ies) not compared."
    )


# Slow by design: the seed stamped under a `pkit` of the test's own, so no template has it.
def test_the_point_is_read_only_when_a_record_copies_evidence(
    project: AdopterRepo,
    pkit_on_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `pkit` that answers nothing for the point is never asked while no record
    copies evidence; once one does, no document is an unresolved point, which says
    nothing but the summary line."""
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
    project.write({RECORD: _record({"UC-001": "holds"}, [_entry("UC-001")])})
    document = _check(project)
    assert document["findings"] == []
    assert f"`pkit connections resolve {EVIDENCE} --json` exited 3" in document["summary"][1]
