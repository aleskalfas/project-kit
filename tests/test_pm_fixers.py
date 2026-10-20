"""The fixers point and the grant list (#1743; project-management DEC-056 points 1 and 2).

project-management defines `pkit::work-tracking:fixers`: which agent fixes the
artefacts of each type, `union`, inert `fail`, no default. A fixer starts on its
own only where the project granted it, in the grant list `fixers` of the
capability's project configuration, empty by default.

Three layers:

- the pieces — the package declaration and the companion schemas, reading the
  point document, the checks on each entry over fixture agents, the grant list
  read and written as text, the question and its line, what may start, and the
  validator's findings;
- the commands through the real backbone, in an adopter repository with a
  capability that contributes a fixer: `list-fixers`, `grant-fixer`,
  `revoke-fixer`, and `ask-fixers` with a terminal and with none;
- `pkit validate`'s `project-management:fixers` member over the same
  repository.
"""

from __future__ import annotations

import io
import json
import os
import pty
import select
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _lib import fixer_cli, fixers  # noqa: E402

POINT = "pkit::work-tracking:fixers"
PM = "project-management"
DOCS = "docs-test"
FIXER = "page-fixer"
PAGE = f"{DOCS}:page"
GUIDE = f"{DOCS}:guide"
PM_REL = Path(".pkit") / "capabilities" / PM
CONFIG_REL = PM_REL / "project" / "config.yaml"
CONFIG = "schema_version: 1\n# Our workstreams.\nworkstreams: []\naudit:\n  projection: audit\n"
PROPOSING = (
    "---\nname: {name}\ndescription: Proposes.\ntools: [Read, Grep, Bash, Write]\n---\n\nBody.\n"
)


# --- the pieces: declaration and schemas -------------------------------------------------


def _package() -> dict[str, Any]:
    return YAML(typ="safe").load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))


def test_pm_accepts_the_point_with_its_companion_schema_and_no_default() -> None:
    point = _package()["connections"]["extension-points"]["accepts"][POINT]
    assert {k: point[k] for k in ("schema_version", "schema", "combination", "inert")} == {
        "schema_version": 1,
        "schema": "fixers.schema.json",
        "combination": "union",
        "inert": "fail",
    }
    assert "default" not in point
    assert point["description"].strip()
    assert (CAPABILITY / "schemas" / "fixers.schema.json").is_file()


def test_the_commands_and_the_validator_are_registered() -> None:
    package = _package()
    commands = package["commands"]
    for verb in ("list-fixers", "grant-fixer", "revoke-fixer", "ask-fixers", "check-fixers"):
        assert (CAPABILITY / commands[verb]["script"]).is_file(), verb
        assert os.access(CAPABILITY / commands[verb]["script"], os.X_OK), verb
    assert package["validators"] == {"fixers": {"command": "check-fixers"}}
    assert commands["check-fixers"]["query-contract"] is True


def _schema(name: str) -> Draft202012Validator:
    schema = json.loads((CAPABILITY / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


GOOD_ENTRY = {"id": PAGE, "agent": FIXER, "description": "your pages"}


@pytest.mark.parametrize(
    "entry",
    [
        GOOD_ENTRY,
        {**GOOD_ENTRY, "id": "handbook"},  # a project's bare type
        {**GOOD_ENTRY, "id": "backbone:rule"},
    ],
)
def test_the_companion_schema_takes_an_entry(entry: dict[str, str]) -> None:
    assert _schema("fixers.schema.json").is_valid([entry])


@pytest.mark.parametrize(
    "entry",
    [
        {k: v for k, v in GOOD_ENTRY.items() if k != "description"},
        {**GOOD_ENTRY, "description": ""},
        {**GOOD_ENTRY, "agent": "Page_Fixer"},
        {**GOOD_ENTRY, "id": "docs-test:"},
        {**GOOD_ENTRY, "id": "docs-test:page/kind"},
        {**GOOD_ENTRY, "extra": 1},
    ],
)
def test_the_companion_schema_refuses_a_bad_entry(entry: dict[str, str]) -> None:
    assert not _schema("fixers.schema.json").is_valid([entry])


def test_the_config_schema_takes_the_grant_list_and_refuses_another_shape() -> None:
    schema = _schema("config.schema.json")
    base = {"schema_version": 1, "workstreams": []}
    assert schema.is_valid({**base, "fixers": {}})
    assert schema.is_valid(
        {**base, "fixers": {FIXER: {"granted": [PAGE], "refused": ["handbook"]}}}
    )
    for bad in (
        {FIXER: {"allowed": [PAGE]}},
        {FIXER: {"granted": PAGE}},
        {FIXER: {"granted": [PAGE, PAGE]}},
        {"Page_Fixer": {"granted": [PAGE]}},
        [FIXER],
    ):
        assert not schema.is_valid({**base, "fixers": bad}), bad


# --- the pieces: reading the point ----------------------------------------------------------


def _document(entries: list[tuple[dict[str, str], str]], **extra: Any) -> dict[str, Any]:
    """A `pkit connections resolve --json` document of the point, resolved."""
    origins = list(dict.fromkeys(origin for _entry, origin in entries))
    return {
        "schema_version": 1,
        "address": POINT,
        "defined": True,
        "outcome": "resolved",
        "resolved": True,
        "why": "",
        "entries": [
            {"id": e["id"], "origin": origin, "replaces": [], "value": e} for e, origin in entries
        ],
        "fillers": [
            {
                "source": "project filler" if o == "project filler" else "contribution",
                "name": "docs/pkit/fillers/pkit/work-tracking/fixers.yaml"
                if o == "project filler"
                else o,
                "supplies": "file" if o == "project filler" else "value",
                "state": "taken",
                "reason": "",
            }
            for o in origins
        ],
        **extra,
    }


def test_a_resolved_point_gives_its_entries_with_who_declares_each() -> None:
    project = {"id": "handbook", "agent": "editor", "description": "your handbook"}
    point = fixers.point_of(_document([(GOOD_ENTRY, DOCS), (project, "project filler")]))
    assert point.resolved
    assert point.entries == (
        fixers.Entry(
            PAGE, FIXER, "your pages", DOCS, "value", f".pkit/capabilities/{DOCS}/package.yaml"
        ),
        fixers.Entry(
            "handbook",
            "editor",
            "your handbook",
            "project filler",
            "file",
            "docs/pkit/fillers/pkit/work-tracking/fixers.yaml",
        ),
    )
    assert point.agents == (FIXER, "editor")
    assert point.types_of(FIXER) == (PAGE,)


@pytest.mark.parametrize(
    "document",
    [
        {"schema_version": 1, "defined": False, "outcome": "undefined", "why": "no provider"},
        {"schema_version": 1, "defined": True, "outcome": "unfilled", "why": "unfilled"},
    ],
    ids=["undefined", "unfilled"],
)
def test_no_provider_or_no_filler_declares_no_fixer(document: dict[str, Any]) -> None:
    point = fixers.point_of(document)
    assert (point.resolved, point.entries, point.why) == (True, (), document["why"])


def test_an_unresolved_point_names_each_inert_filler_and_its_fix() -> None:
    document = {
        "schema_version": 1,
        "defined": True,
        "outcome": "inert-fail",
        "resolved": False,
        "why": "a filler meant to answer is inert",
        "fillers": [
            {
                "source": "contribution",
                "name": DOCS,
                "supplies": "value",
                "state": "inert",
                "reason": "it targets version 2",
            },
            {
                "source": "project filler",
                "name": "docs/f.yaml",
                "supplies": "file",
                "state": "inert",
                "reason": "malformed",
            },
        ],
    }
    point = fixers.point_of(document)
    assert (point.resolved, point.entries, point.why) == (
        False,
        (),
        "a filler meant to answer is inert",
    )
    assert point.inert == (
        f"{DOCS} (value): it targets version 2 — fix: update {DOCS}, pin it, or uninstall it",
        "docs/f.yaml (file): malformed — fix: mend docs/f.yaml",
    )


def test_a_document_of_another_version_is_not_read() -> None:
    point = fixers.point_of({**_document([(GOOD_ENTRY, DOCS)]), "schema_version": 2})
    assert not point.resolved
    assert "version 2" in point.why


def test_reading_the_point_takes_the_document_whatever_the_exit_code() -> None:
    def unresolved(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        assert argv == ["pkit", "connections", "resolve", POINT, "--json"]
        body = {"schema_version": 1, "defined": True, "outcome": "collision", "why": "two claim"}
        return subprocess.CompletedProcess(argv, 1, json.dumps(body), "")

    assert fixers.read_point(unresolved).why == "two claim"

    def silent(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 2, "", "Error: No such command.\n")

    with pytest.raises(fixers.Unreadable, match="No such command"):
        fixers.read_point(silent)

    def absent(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(argv[0])

    with pytest.raises(fixers.Unreadable, match="not on PATH"):
        fixers.read_point(absent)


def test_the_type_registries_are_read_from_the_backbone_s_one_answer() -> None:
    def artefacts(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        assert argv == ["pkit", "friction", "artefacts", "--json"]
        body = {"schema_version": 1, "types": {PAGE: {"component": DOCS, "name": "page"}}}
        return subprocess.CompletedProcess(argv, 0, json.dumps(body), "")

    assert fixers.read_types(artefacts) == {PAGE: DOCS}

    def older(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, json.dumps({"schema_version": 1}), "")

    with pytest.raises(fixers.Unreadable, match="predates"):
        fixers.read_types(older)


# --- the pieces: the checks on each entry ---------------------------------------------------


def _agent(
    root: Path, name: str, *, capability: str | None = DOCS, deployed: str | None = None
) -> None:
    """Ship agent `name` in `capability` and deploy it with `deployed` as its file."""
    if capability is not None:
        shipped = root / ".pkit" / "capabilities" / capability / "agents" / name / f"{name}.md"
        shipped.parent.mkdir(parents=True, exist_ok=True)
        shipped.write_text(PROPOSING.format(name=name), encoding="utf-8")
    if deployed is not None:
        target = root / ".claude" / "agents" / f"{name}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(deployed, encoding="utf-8")


def _entry(**changes: str) -> fixers.Entry:
    base = {
        "type": PAGE,
        "agent": FIXER,
        "description": "your pages",
        "origin": DOCS,
        "supplies": "value",
        "where": f".pkit/capabilities/{DOCS}/package.yaml",
    }
    return fixers.Entry(**{**base, **changes})


def _check(
    root: Path, *entries: fixers.Entry, types: Mapping[str, str] | None = None
) -> list[fixers.Checked]:
    registry = {PAGE: DOCS, GUIDE: DOCS} if types is None else types
    return fixers.check(fixers.Point(True, entries=entries), root, lambda: registry)


def _problems(checked: fixers.Checked) -> list[tuple[str, str]]:
    return [(p.severity, p.text) for p in checked.problems]


def test_a_shipped_deployed_proposing_agent_of_the_capability_s_own_type_passes(
    tmp_path: Path,
) -> None:
    _agent(tmp_path, FIXER, deployed=PROPOSING.format(name=FIXER))
    (checked,) = _check(tmp_path, _entry())
    assert checked.startable


@pytest.mark.parametrize(
    ("entry", "problem"),
    [
        (_entry(type="other-cap:page"), "other-cap:page is not a type of docs-test's own"),
        (_entry(type="page"), "page is not a type of docs-test's own"),
        (_entry(type=f"{DOCS}:term"), f"{DOCS} declares no type {DOCS}:term in its type registry"),
        (
            _entry(supplies="command 'fill-fixers'"),
            f"{DOCS} gives it through a command filler (command 'fill-fixers'), and a "
            "capability gives its fixers as a static value",
        ),
    ],
    ids=["another-component-s-type", "a-bare-type", "undeclared-type", "command-filler"],
)
def test_a_capability_s_bad_entry_is_reported_and_starts_no_agent(
    tmp_path: Path, entry: fixers.Entry, problem: str
) -> None:
    _agent(tmp_path, FIXER, deployed=PROPOSING.format(name=FIXER))
    (checked,) = _check(tmp_path, entry)
    assert _problems(checked) == [("report", problem)]


def test_a_capability_s_agent_must_be_its_own_and_deployed(tmp_path: Path) -> None:
    _agent(tmp_path, FIXER, capability="another", deployed=PROPOSING.format(name=FIXER))
    (unshipped,) = _check(tmp_path, _entry())
    assert _problems(unshipped) == [("report", f"{DOCS} ships no agent {FIXER}")]
    _agent(tmp_path, "idle")
    (undeployed,) = _check(tmp_path, _entry(agent="idle"))
    assert _problems(undeployed) == [
        (
            "report",
            "agent idle is not deployed (`pkit sync` deploys the agents of the installed "
            "components)",
        )
    ]


def test_the_project_s_entry_may_name_any_deployed_agent_and_fails_on_an_undeployed_one(
    tmp_path: Path,
) -> None:
    _agent(tmp_path, "editor", capability=None, deployed=PROPOSING.format(name="editor"))
    project = {"origin": "project filler", "supplies": "file", "where": "docs/f.yaml"}
    good, bad = _check(
        tmp_path,
        _entry(type="handbook", agent="editor", **project),
        _entry(type="handbook", agent="ghost", **project),
    )
    assert good.startable
    assert [p.severity for p in bad.problems] == ["error"]


@pytest.mark.parametrize(
    ("front_matter", "problem"),
    [
        (
            "tools: [Read, Write]\nowns: [docs/]",
            f"agent {FIXER} claims paths (docs/), and a fixer only proposes",
        ),
        (
            "tools: [Read, Edit, Write]",
            f"agent {FIXER} holds Edit, a tool that changes existing files, and a fixer only "
            "proposes",
        ),
        (
            "tools: Read, Agent",
            f"agent {FIXER} holds Agent, a tool that starts agents, and a fixer only proposes",
        ),
        (
            "tools: [Read, Write, 'Agent(worker)']",
            f"agent {FIXER} holds Agent, a tool that starts agents, and a fixer only proposes",
        ),
        (
            "tools: Read, Agent(a, b), Write",
            f"agent {FIXER} holds Agent, a tool that starts agents, and a fixer only proposes",
        ),
        *(
            (
                front_matter,
                f"agent {FIXER} lists no tools, so the harness grants it every tool, those "
                "that change existing files and start agents among them, and a fixer only "
                "proposes",
            )
            for front_matter in ("description: Proposes.", "tools:", "tools: []", "tools: ''")
        ),
    ],
    ids=[
        "claims-paths",
        "changes-files",
        "starts-agents",
        "a-parameterised-tool",
        "a-parameterised-tool-in-a-string",
        "no-tools-key",
        "null-tools",
        "an-empty-list",
        "an-empty-string",
    ],
)
def test_an_agent_that_does_more_than_propose_starts_no_fixer(
    tmp_path: Path, front_matter: str, problem: str
) -> None:
    _agent(tmp_path, FIXER, deployed=f"---\nname: {FIXER}\n{front_matter}\n---\n")
    (capability,) = _check(tmp_path, _entry())
    assert _problems(capability) == [("report", problem)]
    (project,) = _check(tmp_path, _entry(type="handbook", origin="project filler", supplies="file"))
    assert _problems(project) == [("warning", problem)]


def test_a_type_that_cannot_be_checked_starts_no_agent_and_registries_are_read_once(
    tmp_path: Path,
) -> None:
    _agent(tmp_path, FIXER, deployed=PROPOSING.format(name=FIXER))
    calls: list[int] = []

    def unreadable() -> Mapping[str, str]:
        calls.append(1)
        raise fixers.Unreadable("no answer")

    point = fixers.Point(True, entries=(_entry(), _entry(type=GUIDE)))
    checked = fixers.check(point, tmp_path, unreadable)
    assert [_problems(c) for c in checked] == [
        [("warning", "its type could not be checked: no answer")]
    ] * 2
    assert calls == [1]
    # Only the project's entries: the registries are not read at all.
    project = _entry(type="handbook", origin="project filler", supplies="file")
    fixers.check(fixers.Point(True, entries=(project,)), tmp_path, unreadable)
    assert calls == [1]


# --- the pieces: the grant list --------------------------------------------------------------


def test_the_grant_list_is_empty_by_default_and_read_as_written() -> None:
    assert fixers.answers_of({}).agents == {}
    assert fixers.answers_of({"fixers": None}).agents == {}
    answers = fixers.answers_of(
        {"fixers": {FIXER: {"granted": [PAGE], "refused": [GUIDE]}, "editor": None}}
    )
    assert answers.of(FIXER, PAGE) == "granted"
    assert answers.of(FIXER, GUIDE) == "refused"
    assert answers.of("editor", PAGE) is None
    assert answers.granted(FIXER) == (PAGE,)


@pytest.mark.parametrize(
    ("block", "said"),
    [
        ([FIXER], "maps each agent"),
        ({FIXER: {"allowed": [PAGE]}}, f"`fixers.{FIXER}` is not"),
        ({FIXER: {"granted": PAGE}}, "is not a list of types"),
        ({FIXER: {"granted": [PAGE], "refused": [PAGE]}}, f"both grants and refuses {PAGE}"),
        ({"Bad_Name": {}}, "is not an agent's name"),
    ],
)
def test_a_grant_list_in_another_shape_is_never_guessed_at(block: Any, said: str) -> None:
    with pytest.raises(fixers.Malformed, match=said):
        fixers.answers_of({"fixers": block})


def _config(tmp_path: Path, text: str = CONFIG) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_an_answer_is_added_at_the_end_under_its_comment_and_every_other_byte_is_kept(
    tmp_path: Path,
) -> None:
    path = _config(tmp_path)
    assert fixers.record(path, FIXER, [PAGE], "granted")
    text = path.read_text(encoding="utf-8")
    assert text.startswith(CONFIG)
    assert text[len(CONFIG) :] == (
        "\n# Fixers: each agent you were asked about, and the types you granted or refused it\n"
        "# (project-management DEC-056 point 2). Written by `pkit pm ask-fixers`,\n"
        "# `pkit pm grant-fixer` and `pkit pm revoke-fixer`.\n"
        "fixers:\n"
        f"  {FIXER}:\n"
        "    granted:\n"
        f"      - {PAGE}\n"
    )


def test_a_later_answer_rewrites_only_the_block_and_moves_a_type_between_lists(
    tmp_path: Path,
) -> None:
    path = _config(
        tmp_path,
        CONFIG
        + "fixers:  # asked at install\n"
        + f"  {FIXER}:\n    refused: [{PAGE}]\n"
        + "# The rest.\nreview:\n  mode: agent\n",
    )
    assert fixers.record(path, FIXER, [PAGE, GUIDE], "granted")
    assert path.read_text(encoding="utf-8") == (
        CONFIG
        + "fixers:  # asked at install\n"
        + f"  {FIXER}:\n    granted:\n      - {GUIDE}\n      - {PAGE}\n"
        + "# The rest.\nreview:\n  mode: agent\n"
    )
    assert fixers.record(path, FIXER, [PAGE], "refused")
    answers = fixers.answers_of(fixers.load_config(path))
    assert (answers.of(FIXER, PAGE), answers.of(FIXER, GUIDE)) == ("refused", "granted")
    assert not fixers.record(path, FIXER, [PAGE], "refused")  # nothing changes


def test_a_flow_written_block_and_crlf_line_endings_are_kept_as_far_as_the_block(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config.yaml"
    path.write_bytes(b"schema_version: 1\r\nworkstreams: []\r\nfixers: {}\r\n")
    assert fixers.record(path, FIXER, [PAGE], "refused")
    assert path.read_bytes() == (
        b"schema_version: 1\r\nworkstreams: []\r\nfixers:\r\n"
        + f"  {FIXER}:\r\n    refused:\r\n      - {PAGE}\r\n".encode()
    )


def test_a_byte_order_mark_is_kept(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_bytes(b"\xef\xbb\xbfschema_version: 1\nworkstreams: []\n")
    assert fixers.record(path, FIXER, [PAGE], "granted")
    written = path.read_bytes()
    assert written.startswith(b"\xef\xbb\xbfschema_version: 1\nworkstreams: []\n\n# Fixers:")
    assert written.count(b"\xef\xbb\xbf") == 1


def test_a_config_that_is_not_utf8_is_malformed_not_a_crash(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_bytes(b"schema_version: 1\nname: \xff\n")
    with pytest.raises(fixers.Malformed, match="cannot be read"):
        fixers.load_config(path)


def test_an_answer_is_refused_where_it_cannot_be_written_and_nothing_is_written(
    tmp_path: Path,
) -> None:
    with pytest.raises(fixers.Refused, match="does not exist"):
        fixers.record(tmp_path / "absent.yaml", FIXER, [PAGE], "granted")
    malformed = _config(tmp_path, CONFIG + "fixers: [x]\n")
    with pytest.raises(fixers.Refused, match="maps each agent"):
        fixers.record(malformed, FIXER, [PAGE], "granted")
    # A block written where a text edit cannot reach it reads back wrong, and is refused.
    nested = _config(tmp_path, "schema_version: 1\nworkstreams: []\n? fixers\n: {}\n")
    before = nested.read_bytes()
    with pytest.raises(fixers.Refused, match="would not read back"):
        fixers.record(nested, FIXER, [PAGE], "granted")
    assert nested.read_bytes() == before


# --- the pieces: the question ---------------------------------------------------------------


def _checked(*entries: fixers.Entry) -> list[fixers.Checked]:
    return [fixers.Checked(e) for e in entries]


def test_one_question_per_agent_about_the_types_nobody_answered() -> None:
    entries = (
        _entry(),
        _entry(type=GUIDE, description="your guides"),
        _entry(
            type="handbook", agent="editor", origin="project filler", description="your handbook"
        ),
    )
    point = fixers.Point(True, entries=entries)
    broken = fixers.Checked(
        _entry(type=f"{DOCS}:x", agent="idle"), (fixers.Problem("report", "x"),)
    )
    answers = fixers.answers_of({"fixers": {FIXER: {"refused": [PAGE]}}})
    asked = fixers.questions(point, [*_checked(*entries), broken], answers)
    assert [(q.agent, q.types, q.all_types) for q in asked] == [
        (FIXER, (GUIDE,), (PAGE, GUIDE)),
        ("editor", ("handbook",), ("handbook",)),
    ]
    # The line names each type the question named, so a type the point gives the
    # agent later is never granted by a line printed before it.
    assert fixers.grant_line(asked[0]) == f"pkit pm grant-fixer {FIXER} --type {GUIDE}"
    assert fixers.grant_line(asked[1]) == "pkit pm grant-fixer editor --type handbook"


def test_the_question_is_built_from_the_capability_s_name_and_the_descriptions() -> None:
    question = fixers.Question(
        FIXER, (_entry(), _entry(type=GUIDE, description="your guides")), (PAGE, GUIDE)
    )
    assert fixers.question_text(question) == (
        f"{DOCS} can keep your pages and your guides true on its own. After each merge, its "
        f"agent {FIXER} proposes a fix for each one that went out of date, and nothing is "
        "applied until you approve it. Turn this on?"
    )
    project = _entry(
        type="handbook", agent="editor", origin="project filler", description="your handbook"
    )
    assert fixers.question_text(fixers.Question("editor", (project,), ("handbook",))) == (
        "The agent editor can keep your handbook true on its own. After each merge, it "
        "proposes a fix for each one that went out of date, and nothing is applied until you "
        "approve it. Turn this on?"
    )


def test_asking_records_yes_by_default_no_and_stops_where_the_input_ends() -> None:
    asked = [fixers.Question(a, (_entry(agent=a),), (PAGE,)) for a in ("a", "b", "c", "d")]
    replies = iter(["\n", "maybe\n", "n\n", "YES\n"])
    written: list[str] = []
    answered: list[tuple[str, str]] = []

    def read() -> str:
        try:
            return next(replies)
        except StopIteration:
            raise EOFError from None

    left = fixers.ask(
        asked, read=read, write=written.append, answer=lambda q, a: answered.append((q.agent, a))
    )
    assert answered == [("a", "granted"), ("b", "refused"), ("c", "granted")]
    assert left == [asked[3]]
    assert written.count("Answer y or n.\n") == 1
    assert written[0].endswith("Turn this on? [Y/n] ")


# --- the pieces: what may start, and what validation says ------------------------------------


def test_only_a_granted_entry_that_passes_the_checks_may_start(tmp_path: Path) -> None:
    good, guide = _entry(), _entry(type=GUIDE)
    broken = fixers.Checked(_entry(type=f"{DOCS}:x"), (fixers.Problem("report", "x"),))
    answers = fixers.answers_of(
        {"fixers": {FIXER: {"granted": [PAGE, f"{DOCS}:x"], "refused": [GUIDE]}}}
    )
    assert fixers.startable([fixers.Checked(good), fixers.Checked(guide), broken], answers) == [
        good
    ]


def test_validation_reports_each_problem_and_each_grant_no_entry_names() -> None:
    point = fixers.Point(True, entries=(_entry(),))
    checked = [fixers.Checked(_entry(), (fixers.Problem("report", "it is bad"),))]
    answers = fixers.answers_of(
        {"fixers": {FIXER: {"granted": [PAGE, GUIDE]}, "gone": {"granted": ["x"]}}}
    )
    found = fixers.findings(point, checked, answers, "cfg.yaml")
    assert [(f.severity, f.location, f.message) for f in found] == [
        (
            "report",
            f".pkit/capabilities/{DOCS}/package.yaml",
            f"the fixer of {PAGE} (agent {FIXER}, from {DOCS}) starts no agent: it is bad.",
        ),
        (
            "warning",
            f"cfg.yaml:/fixers/{FIXER}/granted",
            f"the grant of {GUIDE} to {FIXER} names what no entry of {POINT} gives it, so it "
            f"starts nothing. Revoke it: `pkit pm revoke-fixer {FIXER} --type {GUIDE}`.",
        ),
        (
            "warning",
            "cfg.yaml:/fixers/gone/granted",
            f"the grant of x to gone names what no entry of {POINT} gives it, so it starts "
            "nothing. Revoke it: `pkit pm revoke-fixer gone --type x`.",
        ),
    ]


# --- the commands through the backbone ----------------------------------------------------------


def _stage_docs(repo: AdopterRepo, value: list[dict[str, str]] | None = None) -> None:
    """A capability with a type registry, an agent it ships and deploys, and a
    static contribution to the point."""
    cap = repo.pkit / "capabilities" / DOCS
    cap.mkdir(parents=True, exist_ok=True)
    package = {
        "schema_version": 2,
        "component": {"kind": "capability", "name": DOCS, "version": "0.1.0"},
        "description": "A documentation capability, for the test.",
        "requires_backbone": ">=0.0.0",
        "friction": {
            "types": {
                "page": {"description": "A page."},
                "guide": {"description": "A guide."},
            }
        },
        "connections": {
            "extensions": {
                "contributes": [
                    {
                        "point": POINT,
                        "schema_version": 1,
                        "value": value
                        if value is not None
                        else [{"id": PAGE, "agent": FIXER, "description": "your pages"}],
                    }
                ]
            }
        },
    }
    with (cap / "package.yaml").open("w", encoding="utf-8") as handle:
        YAML().dump(package, handle)
    _agent(repo.root, FIXER, deployed=PROPOSING.format(name=FIXER))
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    if not any(e.name == DOCS for e in backbone.components):
        backbone.components.append(
            ComponentRegistryEntry(
                kind="capability",
                name=DOCS,
                manifest=f".pkit/capabilities/{DOCS}/project/manifest.yaml",
                origin="incubated-in-repo",
            )
        )
        write_backbone_manifest(repo.root, backbone)


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path) -> AdopterRepo:
    """An adopter with project-management installed and configured, and a
    capability contributing one fixer; the real `pkit` first on PATH."""
    repo = make_adopter_repo(capabilities=(PM,))
    (repo.root / CONFIG_REL).parent.mkdir(parents=True, exist_ok=True)
    (repo.root / CONFIG_REL).write_text(CONFIG, encoding="utf-8")
    _stage_docs(repo)
    return repo


def _run(repo: AdopterRepo, verb: str, *args: str) -> subprocess.CompletedProcess[str]:
    """A fixer verb of the adopter's copy of the capability, with no terminal."""
    return subprocess.run(
        [sys.executable, str(repo.root / PM_REL / "scripts" / f"{verb}.py"), *args],
        cwd=repo.root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def _listed(repo: AdopterRepo) -> dict[str, Any]:
    result = _run(repo, "list-fixers", "--json")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _answers(repo: AdopterRepo) -> dict[str, Any]:
    return YAML(typ="safe").load((repo.root / CONFIG_REL).read_text(encoding="utf-8")).get("fixers")


def test_list_shows_each_declared_fixer_and_that_nobody_was_asked(project: AdopterRepo) -> None:
    listed = _listed(project)
    assert (listed["resolved"], listed["stale"]) == (True, [])
    assert listed["fixers"] == [
        {
            "agent": FIXER,
            "types": [
                {
                    "type": PAGE,
                    "description": "your pages",
                    "origin": DOCS,
                    "answer": None,
                    "problems": [],
                }
            ],
        }
    ]
    human = _run(project, "list-fixers")
    assert human.stdout.splitlines() == [
        f"{POINT}: 1 type(s), 1 agent(s)",
        FIXER,
        f"  {PAGE} (your pages, from {DOCS}): not asked",
    ]


def test_with_nobody_at_a_terminal_the_question_grants_nothing_and_prints_the_line(
    project: AdopterRepo,
) -> None:
    result = _run(project, "ask-fixers")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        f"{DOCS} can keep your pages true on its own. After each merge, its agent {FIXER} "
        "proposes a fix for each one that went out of date, and nothing is applied until you "
        "approve it. Turn this on?",
        f"  To turn it on: pkit pm grant-fixer {FIXER} --type {PAGE}",
        "Nothing was granted: nobody was at a terminal to answer.",
    ]
    assert (project.root / CONFIG_REL).read_text(encoding="utf-8") == CONFIG


PROMPT = b"[Y/n] "


def _at_a_terminal(repo: AdopterRepo, typed: str, *, ahead: str = "") -> tuple[int, str]:
    """`ask-fixers` with a terminal on its standard input and output: `ahead` typed
    before it starts, and `typed` once the question is shown."""
    controller, terminal = pty.openpty()
    os.write(controller, ahead.encode())
    proc = subprocess.Popen(
        [sys.executable, str(repo.root / PM_REL / "scripts" / "ask-fixers.py")],
        cwd=repo.root,
        stdin=terminal,
        stdout=terminal,
        stderr=terminal,
    )
    os.close(terminal)  # the child holds the terminal now
    chunks: list[bytes] = []
    answered = False
    deadline = time.monotonic() + 60
    try:
        while True:
            ready, _, _ = select.select([controller], [], [], max(deadline - time.monotonic(), 0))
            if not ready:
                proc.kill()
                pytest.fail("ask-fixers did not finish at a terminal within 60s")
            try:
                data = os.read(controller, 4096)
            except OSError:  # the child closed the terminal
                break
            if not data:
                break
            chunks.append(data)
            if not answered and b"".join(chunks).endswith(PROMPT):
                os.write(controller, typed.encode())
                answered = True
    finally:
        os.close(controller)
    return proc.wait(timeout=60), b"".join(chunks).decode("utf-8", "replace").replace("\r\n", "\n")


@pytest.mark.parametrize(("typed", "answer"), [("\n", "granted"), ("n\n", "refused")])
def test_at_a_terminal_each_answer_is_recorded_as_it_is_given(
    project: AdopterRepo, typed: str, answer: str
) -> None:
    code, output = _at_a_terminal(project, typed)
    assert code == 0, output
    assert "Turn this on? [Y/n]" in output
    assert f"Recorded: {FIXER} {answer} {PAGE}." in output
    assert f"Commit {CONFIG_REL}" in output
    assert _answers(project) == {FIXER: {answer: [PAGE]}}
    # Asked once: nothing waits now.
    again = _run(project, "ask-fixers")
    assert again.stdout == "No fixer waits for an answer.\n"


def test_input_that_ends_unanswered_records_nothing(project: AdopterRepo) -> None:
    code, output = _at_a_terminal(project, "\x04")  # end of input, at the terminal
    assert code == 0, output
    assert f"pkit pm grant-fixer {FIXER} --type {PAGE}" in output
    assert (project.root / CONFIG_REL).read_text(encoding="utf-8") == CONFIG


def test_input_typed_before_the_question_answers_nothing(project: AdopterRepo) -> None:
    """An Enter pressed before the question is shown, during a slow install say, is
    dropped: only the answer typed to the question shown counts."""
    code, output = _at_a_terminal(project, "n\n", ahead="y\n")
    assert code == 0, output
    assert _answers(project) == {FIXER: {"refused": [PAGE]}}


def test_grant_and_revoke_write_the_list_and_list_shows_each_answer(project: AdopterRepo) -> None:
    dry = _run(project, "grant-fixer", FIXER, "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert "Nothing was written (--dry-run)" in dry.stdout
    assert _answers(project) is None

    granted = _run(project, "grant-fixer", FIXER)
    assert granted.returncode == 0, granted.stderr
    assert f"Recorded in {CONFIG_REL}: {FIXER} granted {PAGE}." in granted.stdout
    assert f'It answers yes to: "{DOCS} can keep your pages true' in granted.stdout
    assert _answers(project) == {FIXER: {"granted": [PAGE]}}
    assert _listed(project)["fixers"][0]["types"][0]["answer"] == "granted"
    assert "already has" in _run(project, "grant-fixer", FIXER).stdout

    revoked = _run(project, "revoke-fixer", FIXER)
    assert revoked.returncode == 0, revoked.stderr
    assert _answers(project) == {FIXER: {"refused": [PAGE]}}
    assert _listed(project)["fixers"][0]["types"][0]["answer"] == "refused"
    # A refusal is an answer: the question does not ask again.
    assert _run(project, "ask-fixers").stdout == "No fixer waits for an answer.\n"


def test_grant_refuses_what_no_entry_names(project: AdopterRepo) -> None:
    unknown = _run(project, "grant-fixer", "ghost")
    assert unknown.returncode == 1
    assert f"no entry of {POINT} names agent ghost" in unknown.stderr
    foreign = _run(project, "grant-fixer", FIXER, "--type", GUIDE)
    assert foreign.returncode == 1
    assert f"the point does not give {FIXER} {GUIDE}" in foreign.stderr
    assert _answers(project) is None


def test_a_grant_no_entry_names_stays_revocable_and_is_listed(project: AdopterRepo) -> None:
    text = CONFIG + f"fixers:\n  gone:\n    granted: [{PAGE}]\n"
    (project.root / CONFIG_REL).write_text(text, encoding="utf-8")
    listed = _listed(project)
    assert listed["stale"] == [
        {"agent": "gone", "type": PAGE, "revoke": f"pkit pm revoke-fixer gone --type {PAGE}"}
    ]
    revoked = _run(project, "revoke-fixer", "gone", "--type", PAGE)
    assert revoked.returncode == 0, revoked.stderr
    assert _answers(project) == {"gone": {"refused": [PAGE]}}


def test_an_entry_that_fails_a_check_is_not_asked_about(project: AdopterRepo) -> None:
    _stage_docs(project, [{"id": "elsewhere:page", "agent": FIXER, "description": "your pages"}])
    result = _run(project, "ask-fixers")
    assert result.stdout == "No fixer waits for an answer.\n"
    problems = _listed(project)["fixers"][0]["types"][0]["problems"]
    assert problems == [
        {"severity": "report", "text": f"elsewhere:page is not a type of {DOCS}'s own"}
    ]


def test_an_unresolved_point_asks_nothing_and_says_why(project: AdopterRepo) -> None:
    # Two capabilities claim one type: the point does not resolve.
    other = project.pkit / "capabilities" / "other-test"
    other.mkdir(parents=True)
    (other / "package.yaml").write_text(
        (project.pkit / "capabilities" / DOCS / "package.yaml")
        .read_text(encoding="utf-8")
        .replace(f"name: {DOCS}", "name: other-test"),
        encoding="utf-8",
    )
    backbone = read_backbone_manifest(project.root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name="other-test",
            manifest=".pkit/capabilities/other-test/project/manifest.yaml",
            origin="incubated-in-repo",
        )
    )
    write_backbone_manifest(project.root, backbone)
    asked = _run(project, "ask-fixers")
    assert asked.returncode == 1
    assert f"[unresolved] {POINT} does not resolve" in asked.stderr
    granted = _run(project, "grant-fixer", FIXER)
    assert granted.returncode == 1
    assert "so no fixer can be granted" in granted.stderr


# --- pkit validate's member -----------------------------------------------------------------------


def _validate(repo: AdopterRepo) -> Any:
    script = repo.root / PM_REL / "scripts" / "check-fixers.py"
    body = script.read_text(encoding="utf-8").split("\n", 1)[1]
    script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    return CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "project-management:fixers"]
    )


def test_validation_passes_a_good_declaration(project: AdopterRepo) -> None:
    result = _validate(project)
    assert result.exit_code == 0, result.output
    assert f"{POINT}: 1 type(s) for 1 agent(s); 1 pass the checks, 0 granted" in result.output


def test_validation_fails_the_project_s_entry_naming_an_undeployed_agent(
    project: AdopterRepo,
) -> None:
    filler = project.root / "docs" / "pkit" / "fillers" / "pkit" / "work-tracking" / "fixers.yaml"
    filler.parent.mkdir(parents=True, exist_ok=True)
    filler.write_text(
        "schema_version: 1\nvalue:\n"
        "  - id: handbook\n    agent: ghost\n    description: your handbook\n",
        encoding="utf-8",
    )
    (project.root / CONFIG_REL).write_text(
        CONFIG + f"fixers:\n  gone:\n    granted: [{PAGE}]\n", encoding="utf-8"
    )
    result = _validate(project)
    assert result.exit_code == 1, result.output
    assert "agent ghost is not deployed" in result.output
    assert "pkit pm revoke-fixer gone --type docs-test:page" in result.output


class _Terminal(io.StringIO):
    """An output stream that keeps what was flushed, as a terminal shows it."""

    shown = ""

    def flush(self) -> None:
        self.shown = self.getvalue()


def test_the_ask_entry_point_can_be_called_by_another_command(project: AdopterRepo) -> None:
    """The drift command asks through the same function: it hands the point, the
    terminal and the answer's reader in. Each prompt reaches the terminal before
    the answer is read."""
    out = _Terminal()

    def read() -> str:
        assert out.shown.endswith("Turn this on? [Y/n] ")
        return "y\n"

    code = fixer_cli.ask_pending(
        point=fixers.read_point(),
        repo_root=project.root,
        config_path=project.root / CONFIG_REL,
        interactive=True,
        read=read,
        out=out,
    )
    assert code == 0
    assert _answers(project) == {FIXER: {"granted": [PAGE]}}
    assert f"Recorded: {FIXER} granted {PAGE}." in out.getvalue()


def test_validation_s_document_exits_zero_whatever_its_findings(project: AdopterRepo) -> None:
    """With `--json` the validator answers, so it exits 0 even when a finding is an
    error: a non-zero exit would be no answer (COR-055 point 6)."""
    (project.root / CONFIG_REL).write_text(CONFIG + "fixers: [x]\n", encoding="utf-8")
    result = _run(project, "check-fixers", "--json")
    assert result.returncode == 0, result.stderr
    (finding,) = json.loads(result.stdout)["findings"]
    assert (finding["severity"], finding["location"]) == ("error", f"{CONFIG_REL}:/fixers")
    assert _run(project, "check-fixers").returncode == 1


# --- the question in process: who is asked, and what is written ------------------------------


class _Stream(io.StringIO):
    def __init__(self, tty: bool) -> None:
        super().__init__()
        self.tty = tty

    def isatty(self) -> bool:
        return self.tty


@pytest.mark.parametrize(
    ("stdin", "stdout", "person"),
    [(True, True, True), (False, True, False), (True, False, False), (False, False, False)],
    ids=["both", "piped-input", "piped-output", "neither"],
)
def test_a_person_answers_only_with_a_terminal_on_both_ends(
    stdin: bool, stdout: bool, person: bool
) -> None:
    assert fixer_cli.at_a_terminal(_Stream(stdin), _Stream(stdout)) is person


def _repo_with_a_fixer(root: Path, *agents: str) -> tuple[fixers.Point, Path]:
    """A repository whose point names each agent as the fixer of its own type,
    each shipped and deployed, and the project's configuration."""
    entries = []
    for agent in agents:
        _agent(root, agent, deployed=PROPOSING.format(name=agent))
        entries.append(_entry(type=f"{DOCS}:{agent}", agent=agent))
    config = root / "config.yaml"
    config.write_text(CONFIG, encoding="utf-8")
    return fixers.Point(True, entries=tuple(entries)), config


def _ask(point: fixers.Point, root: Path, config: Path, **options: Any) -> tuple[int, str]:
    out = io.StringIO()
    code = fixer_cli.ask_pending(
        point=point,
        repo_root=root,
        config_path=config,
        out=out,
        err=out,
        types=lambda: {e.type: DOCS for e in point.entries},
        **options,
    )
    return code, out.getvalue()


def test_the_default_reader_never_takes_a_caller_s_word_for_a_terminal(tmp_path: Path) -> None:
    """Under the test runner standard input is no terminal, so a piped `yes`
    behind a caller's `interactive=True` is still nobody's answer."""
    point, config = _repo_with_a_fixer(tmp_path, FIXER)
    code, said = _ask(point, tmp_path, config, interactive=True)
    assert code == 0
    assert "Nothing was granted: nobody was at a terminal to answer." in said
    assert config.read_text(encoding="utf-8") == CONFIG


def test_a_refusing_guard_writes_nothing(tmp_path: Path) -> None:
    point, config = _repo_with_a_fixer(tmp_path, FIXER)
    code, _said = _ask(
        point, tmp_path, config, interactive=True, read=lambda: "y\n", guard=lambda: False
    )
    assert code == 1
    assert config.read_text(encoding="utf-8") == CONFIG


def test_an_answer_that_cannot_be_written_stops_and_keeps_those_before_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    point, config = _repo_with_a_fixer(tmp_path, "first", "second")
    record = fixers.record
    calls: list[str] = []

    def failing_second(path: Path, agent: str, types: Any, answer: str) -> bool:
        calls.append(agent)
        if agent == "second":
            raise fixers.Refused("the disk is full")
        return record(path, agent, types, answer)

    monkeypatch.setattr(fixers, "record", failing_second)
    code, said = _ask(point, tmp_path, config, interactive=True, read=lambda: "y\n")
    assert (code, calls) == (1, ["first", "second"])
    assert "error: the answer could not be recorded: the disk is full" in said
    assert "Recorded: first granted docs-test:first." in said
    assert fixers.answers_of(fixers.load_config(config)).agents == {
        "first": {f"{DOCS}:first": "granted"}
    }


def test_the_schemas_name_agents_and_types_as_the_readers_do() -> None:
    """The patterns live in two schemas and the library: they say the same."""
    point = json.loads((CAPABILITY / "schemas" / "fixers.schema.json").read_text("utf-8"))
    config = json.loads((CAPABILITY / "schemas" / "config.schema.json").read_text("utf-8"))
    fixer = point["$defs"]["fixer"]["properties"]
    assert fixer["id"]["pattern"] == f"^{fixers.TYPE_NAME.pattern}$"
    assert fixer["agent"]["pattern"] == f"^{fixers.AGENT_NAME.pattern}$"
    assert config["$defs"]["fixer_types"]["items"]["pattern"] == f"^{fixers.TYPE_NAME.pattern}$"
    grants = config["properties"]["fixers"]
    assert grants["propertyNames"]["pattern"] == f"^{fixers.AGENT_NAME.pattern}$"


def test_a_resolved_point_with_no_entry_says_so() -> None:
    point = fixers.point_of(_document([]))
    assert (point.resolved, point.entries, point.why) == (True, (), "the point holds no entry")


# --- #1744: a stray refusal, the dry run's configuration, the grant list at a commit -------------


def test_validation_reports_a_refusal_no_entry_names_with_how_to_remove_it() -> None:
    """A refusal for a type the point never gives the agent asks nothing and starts
    nothing, and no command removes it, so it is reported with the words to remove
    it by hand. A refusal an entry names is no finding."""
    point = fixers.Point(True, entries=(_entry(),))
    answers = fixers.answers_of(
        {"fixers": {FIXER: {"refused": [PAGE, GUIDE]}, "gone": {"refused": ["x"]}}}
    )
    assert fixers.stale_refusals(point, answers) == [(FIXER, GUIDE), ("gone", "x")]
    found = fixers.findings(point, [fixers.Checked(_entry())], answers, "cfg.yaml")
    assert [(f.severity, f.location, f.message) for f in found] == [
        (
            "report",
            f"cfg.yaml:/fixers/{FIXER}/refused",
            f"the refusal of {GUIDE} to {FIXER} names what no entry of {POINT} gives it, so it "
            f"asks nothing and starts nothing. To remove it, delete {GUIDE} from "
            f"`fixers.{FIXER}.refused` in cfg.yaml by hand.",
        ),
        (
            "report",
            "cfg.yaml:/fixers/gone/refused",
            f"the refusal of x to gone names what no entry of {POINT} gives it, so it asks "
            "nothing and starts nothing. To remove it, delete x from `fixers.gone.refused` in "
            "cfg.yaml by hand.",
        ),
    ]


def test_validation_of_a_stray_refusal_fails_nothing(project: AdopterRepo) -> None:
    (project.root / CONFIG_REL).write_text(
        CONFIG + f"fixers:\n  gone:\n    refused: [{PAGE}]\n", encoding="utf-8"
    )
    result = _run(project, "check-fixers", "--json")
    assert result.returncode == 0, result.stderr
    (finding,) = json.loads(result.stdout)["findings"]
    location = f"{CONFIG_REL}:/fixers/gone/refused"
    assert (finding["severity"], finding["location"]) == ("report", location)
    assert _run(project, "check-fixers").returncode == 0


@pytest.mark.parametrize("verb", ["grant-fixer", "revoke-fixer"])
def test_a_dry_run_checks_the_configuration_exists_as_the_write_does(
    project: AdopterRepo, verb: str
) -> None:
    dry = _run(project, verb, FIXER, "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert f"Would record in {CONFIG_REL}, which exists:" in dry.stdout
    (project.root / CONFIG_REL).unlink()
    dry = _run(project, verb, FIXER, "--dry-run")
    real = _run(project, verb, FIXER)
    assert (dry.returncode, real.returncode) == (1, 1)
    missing = "does not exist: author project-management's configuration first"
    assert missing in dry.stderr
    assert missing in real.stderr
    assert "Nothing was written (--dry-run)." in dry.stderr
    assert not (project.root / CONFIG_REL).exists()


def _answers_of(**agents: dict[str, list[str]]) -> fixers.Answers:
    return fixers.answers_of({"fixers": agents})


def test_the_grant_list_s_change_is_each_grant_and_refusal_added_or_removed() -> None:
    before = _answers_of(a={"granted": ["t:1", "t:2"], "refused": ["t:3"]}, b={"granted": ["t:1"]})
    after = _answers_of(a={"granted": ["t:1", "t:3"], "refused": ["t:2"]}, c={"refused": ["t:9"]})
    change = fixers.grant_change(before, after)
    assert [c.said() for c in change] == [
        "Fixer grant removed: a no longer starts on its own on t:2",
        "Fixer refusal added: a is refused t:2",
        "Fixer refusal removed: a is no longer refused t:3",
        "Fixer grant added: a may start on its own on t:3",
        "Fixer grant removed: b no longer starts on its own on t:1",
        "Fixer refusal added: c is refused t:9",
    ]
    assert fixers.grant_change(before, before) == ()
    assert fixers.grant_change(fixers.Answers(), fixers.Answers()) == ()


_GIT = ("git", "-c", "commit.gpgsign=false", "-c", "user.email=o@example.com", "-c", "user.name=O")


def _commit(root: Path, message: str) -> str:
    subprocess.run([*_GIT, "add", "-A"], cwd=root, check=True)
    subprocess.run([*_GIT, "commit", "-q", "--allow-empty", "-m", message], cwd=root, check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    return head.stdout.strip()


def test_the_grant_list_is_read_at_a_commit_from_git_objects(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    config, path = tmp_path / CONFIG_REL, CONFIG_REL.as_posix()
    absent = _commit(tmp_path, "nothing")
    config.parent.mkdir(parents=True)
    config.write_text(CONFIG + f"fixers:\n  {FIXER}:\n    granted: [{PAGE}]\n", encoding="utf-8")
    granted = _commit(tmp_path, "grant")
    config.write_text(CONFIG + "fixers: [x]\n", encoding="utf-8")
    malformed = _commit(tmp_path, "malformed")
    config.unlink()
    config.symlink_to("elsewhere.yaml")
    linked = _commit(tmp_path, "link")
    # The working tree says something else: the commit's object is what is read.
    config.unlink()
    config.write_text(CONFIG, encoding="utf-8")
    assert fixers.answers_at(absent, path, cwd=tmp_path) == fixers.Answers()
    assert fixers.answers_at(granted, path, cwd=tmp_path).agents == {FIXER: {PAGE: "granted"}}
    with pytest.raises(fixers.Malformed, match="maps each agent"):
        fixers.answers_at(malformed, path, cwd=tmp_path)
    with pytest.raises(fixers.Malformed, match="is not a file"):
        fixers.answers_at(linked, path, cwd=tmp_path)
    with pytest.raises(fixers.Unreadable, match="could not be read"):
        fixers.answers_at("0" * 40, path, cwd=tmp_path)
