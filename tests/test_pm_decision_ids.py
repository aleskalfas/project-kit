"""The decision ids an issue body cites, and whether a record holds each (project-management
DEC-010, #1970).

DEC-010 forbids a predicted decision id in a body: an id that no record holds, written as
if one did. The body check reads the ids a body cites — a core, project or architecture
record's, and a capability's decision named with its capability — and asks the backbone,
`pkit refs lookup --json`, whether a record holds each. One that none holds is a warning
naming it; a lookup that fails is one notice that the ids were not checked.

Three layers:

- the pieces — what a body cites, reading the backbone's document, and the rule over it;
- the lookup through the real backbone, in this repository, for each namespace;
- the rule on the three verbs that apply it — `validate-issue`, `edit-issue` and
  `create-issue` — with `gh` mocked: a report that never changes a verb's exit.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS_DIR = CAPABILITY_ROOT / "scripts"
PM = "project-management"

_yaml: Any = YAML(typ="safe")

#: The shipped body-format schema, and the labels the rule reports under: a cited id
#: that no record holds, and the notice that the ids were not checked.
BODY_FORMAT: Any = _yaml.load(
    (CAPABILITY_ROOT / "schemas" / "body-format.yaml").read_text(encoding="utf-8")
)
RULE = "body.predicted-decision-id"
UNCHECKED = "body.decision-ids-unchecked"

#: Each namespace a cited id lives in: how a body writes it, and the id it is asked as.
NAMESPACES = {
    "core": ("COR-064", "COR-064"),
    "project": ("PRJ-064", "PRJ-064"),
    "architecture": ("ADR-064", "ADR-064"),
    "capability": (f"[{PM}:DEC-061-a-slug]", f"{PM}:DEC-061"),
}


def _load(module_name: str, path: Path) -> ModuleType:
    inserted = str(SCRIPTS_DIR) not in sys.path
    if inserted:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and str(SCRIPTS_DIR) in sys.path:
            sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def vi() -> ModuleType:
    return _load("pm_validate_issue_for_decision_ids", SCRIPTS_DIR / "validate-issue.py")


@pytest.fixture(scope="module")
def ei() -> ModuleType:
    return _load("pm_edit_issue_for_decision_ids", SCRIPTS_DIR / "edit-issue.py")


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return _load("pm_create_issue_for_decision_ids", SCRIPTS_DIR / "create-issue.py")


@pytest.fixture(scope="module")
def dc(vi: ModuleType, ei: ModuleType, ci: ModuleType) -> ModuleType:
    """The module the three verbs check decision ids through — one module, so a test
    that replaces its lookup replaces it for every verb."""
    module: ModuleType = vi.decision_ids
    assert ei.decision_ids is module and ci.decision_ids is module
    return module


def _document(*answers: tuple[str, bool]) -> dict[str, Any]:
    """A `pkit refs lookup --json` document answering each `(id, resolved)`."""
    return {
        "schema_version": 1,
        "lookups": [
            {
                "id": record,
                "resolved": resolved,
                "paths": [f"somewhere/{record}.md"] if resolved else [],
                "problem": None if resolved else f"no record matches {record!r}",
            }
            for record, resolved in answers
        ],
    }


def _body(extra: str = "") -> str:
    """A Task body that passes every other body rule, with `extra` in its `## What`."""
    return (
        f"Feature: #10\n\n## What\n\nThe work.{extra}\n\n## Acceptance criteria\n\n"
        "- [ ] done\n\n## Doc impact\n\nNo doc impact — internal.\n"
    )


# --- what a body cites -----------------------------------------------------------------


@pytest.mark.parametrize("namespace", sorted(NAMESPACES))
def test_each_namespace_is_cited(dc: ModuleType, namespace: str) -> None:
    written, asked = NAMESPACES[namespace]
    assert dc.cited(f"See {written} for it.") == [asked]


def test_a_capability_s_decision_is_cited_with_its_slug_or_without(dc: ModuleType) -> None:
    body = f"[{PM}:DEC-010-issue-body-minimum-structure], {PM}:DEC-010 and living-docs:DEC-002."
    assert dc.cited(body) == [f"{PM}:DEC-010", "living-docs:DEC-002"]


def test_ids_are_cited_once_in_the_order_first_cited(dc: ModuleType) -> None:
    body = f"PRJ-002, then [{PM}:DEC-010-x], then COR-001 (COR-050#16), PRJ-002 again."
    assert dc.cited(body) == ["PRJ-002", f"{PM}:DEC-010", "COR-001", "COR-050"]


@pytest.mark.parametrize(
    "body",
    [
        "A bare DEC-061 names no capability.",
        "project-management DEC-061, named in prose.",
        "A rule's id, RS-ADR-001, is no record's.",
        "A longer token, XCOR-001 or COR-001x, is none.",
    ],
)
def test_what_is_not_cited(dc: ModuleType, body: str) -> None:
    assert dc.cited(body) == []


@pytest.mark.parametrize(
    "body",
    [
        "```\nCOR-064\n```\n",
        "~~~sh\npkit refs lookup PRJ-064\n~~~\n",
        "<!--\nper [project-management:DEC-061-x]\n-->\n",
        "It was ~~ADR-064~~ once.\n",
        "Text.\n\n<!-- pkit-provenance:start -->\n\n---\nCOR-064\n<!-- pkit-provenance:end -->\n",
    ],
)
def test_ids_the_body_parser_skips_are_not_cited(dc: ModuleType, body: str) -> None:
    """A fenced code block, an HTML comment, a struck-through span and the provenance
    footer are not read, as the backbone's body parser skips them (COR-013)."""
    assert dc.cited(body) == []


def test_text_around_a_comment_is_read(dc: ModuleType) -> None:
    """Text between two comments is read, and a comment never closed hides the rest,
    as a page shows it."""
    body = "COR-001<!-- PRJ-064 -->ADR-001 <!-- a --> PRJ-002 <!-- never closed COR-064"
    assert dc.cited(body) == ["COR-001", "ADR-001", "PRJ-002"]


@pytest.mark.parametrize("unit", ["<!--", "a-", "ab", "~~a", "COR-", "a:", "```\n"])
def test_the_reading_stays_linear_on_a_long_body(dc: ModuleType, unit: str) -> None:
    """A body file has no length limit before `create-issue` checks it, so no shape of
    text makes the reading backtrack over it."""
    import time

    started = time.monotonic()
    dc.cited(unit * 100_000)
    assert time.monotonic() - started < 2


@pytest.mark.parametrize("template", ["EPIC", "Feature", "Umbrella", "Task"])
def test_a_template_stamped_body_cites_nothing(dc: ModuleType, template: str) -> None:
    """The issue templates cite records only in their comments, so a body stamped from
    one asks the backbone nothing."""
    text = (CAPABILITY_ROOT / "templates" / f"{template}.md").read_text(encoding="utf-8")
    assert dc.cited(text.split("---\n", 2)[2]) == []


# --- reading the backbone's document -------------------------------------------------


class _Answering:
    """Stands in for `subprocess.run`: answers what `pkit` would print, and keeps each
    command it was asked to run."""

    def __init__(self, stdout: str, code: int = 0, stderr: str = "") -> None:
        self.stdout, self.code, self.stderr = stdout, code, stderr
        self.argvs: list[list[str]] = []

    def __call__(self, argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        self.argvs.append(argv)
        return subprocess.CompletedProcess(argv, self.code, self.stdout, self.stderr)


def test_the_lookup_asks_every_id_in_one_run(dc: ModuleType) -> None:
    run = _Answering(json.dumps(_document(("COR-001", True), ("COR-064", False))))
    reading = dc.lookup(["COR-001", "COR-064"], run=run)
    assert run.argvs == [["pkit", "refs", "lookup", "--json", "--", "COR-001", "COR-064"]]
    assert reading == dc.Answered({"COR-001": True, "COR-064": False})


def _raising(error: Exception) -> Callable[..., Any]:
    def run(*_a: Any, **_kw: Any) -> Any:
        raise error

    return run


@pytest.mark.parametrize(
    ("run", "why"),
    [
        (_raising(FileNotFoundError("pkit")), "`pkit` is not on PATH"),
        (
            _raising(subprocess.TimeoutExpired(["pkit"], 30)),
            "`pkit refs lookup` did not answer within 30s",
        ),
        (_raising(PermissionError("denied")), "`pkit` could not be run (denied)"),
        (
            _Answering("", 2, "Error: No such option: --json\n"),
            "the installed backbone predates `pkit refs lookup --json`",
        ),
        (
            _Answering("", 2, "Error: No such command 'lookup'.\n"),
            "the installed backbone predates `pkit refs lookup --json`",
        ),
        (
            _Answering("", 1, "Error: not in a project tree.\n"),
            "exited 1 without its document: Error: not in a project tree.",
        ),
        (_Answering("not json"), "exited 0 without its document"),
        (
            _Answering(json.dumps({"schema_version": 2, "lookups": []})),
            "answered schema_version 2; this reading understands 1",
        ),
    ],
)
def test_no_document_it_understands_is_not_checked(
    dc: ModuleType, run: Callable[..., Any], why: str
) -> None:
    reading = dc.lookup(["COR-064"], run=run)
    assert isinstance(reading, dc.NotChecked)
    assert why in reading.why


def test_an_entry_it_cannot_read_is_left_unanswered(dc: ModuleType) -> None:
    document = {
        "schema_version": 1,
        "lookups": [{"id": "COR-001", "resolved": True}, {"id": "COR-064"}, "junk"],
    }
    assert dc.reading_of(document) == dc.Answered({"COR-001": True})


# --- the rule ------------------------------------------------------------------------


class _Lookup:
    """Stands in for `pkit refs lookup`: answers from `held`, counts the asking."""

    def __init__(self, dc: ModuleType, held: Mapping[str, bool] | None = None) -> None:
        self.dc, self.held, self.asked = dc, held, []

    def __call__(self, ids: Sequence[str]) -> Any:
        self.asked.append(list(ids))
        if self.held is None:
            return self.dc.NotChecked("`pkit` is not on PATH")
        return self.dc.Answered({i: self.held[i] for i in ids if i in self.held})


@pytest.mark.parametrize("namespace", sorted(NAMESPACES))
def test_an_id_a_record_holds_passes(dc: ModuleType, namespace: str) -> None:
    written, asked = NAMESPACES[namespace]
    lookup = _Lookup(dc, {asked: True})
    assert dc.findings(_body(f" See {written}."), BODY_FORMAT, lookup) == []
    assert lookup.asked == [[asked]]


@pytest.mark.parametrize("namespace", sorted(NAMESPACES))
def test_an_id_no_record_holds_is_a_warning_naming_it(dc: ModuleType, namespace: str) -> None:
    written, asked = NAMESPACES[namespace]
    findings = dc.findings(_body(f" See {written}."), BODY_FORMAT, _Lookup(dc, {asked: False}))
    assert findings == [
        (
            "warning",
            RULE,
            f"cites {asked}, which no record holds. Cite a decision only once its record "
            "exists, and describe one not yet written without an id.",
        )
    ]


def test_every_id_no_record_holds_is_named_in_one_finding(dc: ModuleType) -> None:
    body = _body(f" COR-001, COR-064 and [{PM}:DEC-061-x].")
    held = {"COR-001": True, "COR-064": False, f"{PM}:DEC-061": False}
    [finding] = dc.findings(body, BODY_FORMAT, _Lookup(dc, held))
    assert finding[1] == RULE
    assert finding[2].startswith(f"cites COR-064 and {PM}:DEC-061, which no record holds.")


@pytest.mark.parametrize("namespace", sorted(NAMESPACES))
def test_a_failed_lookup_is_one_notice_and_no_predicted_id(dc: ModuleType, namespace: str) -> None:
    written, asked = NAMESPACES[namespace]
    findings = dc.findings(_body(f" See {written} and COR-001."), BODY_FORMAT, _Lookup(dc))
    assert findings == [
        (
            "warning",
            UNCHECKED,
            f"decision ids not checked ({asked} and COR-001): the records could not be "
            "read — `pkit` is not on PATH. None is reported as predicted on that ground.",
        )
    ]


def test_an_id_left_unanswered_is_not_checked(dc: ModuleType) -> None:
    findings = dc.findings(
        _body(" COR-001 and COR-064."), BODY_FORMAT, _Lookup(dc, {"COR-001": True})
    )
    assert [(s, label) for s, label, _ in findings] == [("warning", UNCHECKED)]
    assert findings[0][2].startswith("decision ids not checked (COR-064): `pkit refs lookup`")


def test_a_body_citing_nothing_asks_nothing(dc: ModuleType) -> None:
    lookup = _Lookup(dc, {})
    assert dc.findings(_body(" A bare DEC-061."), BODY_FORMAT, lookup) == []
    assert lookup.asked == []


def test_no_reader_asks_nothing(dc: ModuleType) -> None:
    assert dc.findings(_body(" COR-064."), BODY_FORMAT, None) == []


def test_the_schema_carries_the_rule_under_its_id_at_a_warning() -> None:
    [rule] = [r for r in BODY_FORMAT["universal_body_rules"] if r.get("id") == RULE]
    assert rule["severity"] == "[validation-severity:warning]"
    assert "predicted decision IDs" in rule["rule"]


def test_the_severity_is_the_schema_s(dc: ModuleType) -> None:
    schema = {
        "universal_body_rules": [
            {"id": RULE, "rule": "x", "severity": "[validation-severity:bypassable-with-audit]"}
        ]
    }
    lookup = _Lookup(dc, {"COR-064": False})
    assert dc.findings(_body(" COR-064."), schema, lookup)[0][:2] == (
        "bypassable-with-audit",
        RULE,
    )
    assert dc.findings(_body(" COR-064."), {}, lookup)[0][:2] == ("warning", RULE)


# --- the lookup through the real backbone ----------------------------------------------


def test_the_real_backbone_answers_each_namespace(
    dc: ModuleType, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End to end in this repository: an id a record holds, and one none holds, in each
    namespace, answered by one run of the real `pkit refs lookup --json`."""
    monkeypatch.chdir(REPO_ROOT)
    held = ["COR-001", "PRJ-002", "ADR-001", f"{PM}:DEC-010"]
    unheld = ["COR-9999", "PRJ-9999", "ADR-9999", f"{PM}:DEC-9999"]
    reading = dc.lookup([*held, *unheld])
    assert reading == dc.Answered({**dict.fromkeys(held, True), **dict.fromkeys(unheld, False)})


# --- the rule on the three verbs ---------------------------------------------------------

TITLE = "[Task] Do a thing with a long enough title"


def _allow(*_args: object, **_kwargs: object) -> bool:
    return True


def _staged(root: Path) -> Path:
    """project-management's schemas and templates under `root`, bootstrapped and
    configured; returns the capability root."""
    capability_root = root / ".pkit" / "capabilities" / PM
    for folder in ("schemas", "templates"):
        shutil.copytree(CAPABILITY_ROOT / folder, capability_root / folder)
    (capability_root / "project").mkdir(parents=True)
    (capability_root / "project" / "config.yaml").write_text(
        "schema_version: 1\nworkstreams: [core]\n", encoding="utf-8"
    )
    (capability_root / "project" / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\nbootstrap:\n  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.0.0-test\n  by: bootstrap\n  repo:\n",
        encoding="utf-8",
    )
    return capability_root


Verb = Callable[[str], tuple[int, str]]


@pytest.fixture
def verbs(
    vi: ModuleType,
    ei: ModuleType,
    ci: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> dict[str, Verb]:
    """Each verb run on a Task body, `gh` mocked: `(exit code, what it printed)`."""
    capability_root = _staged(tmp_path)
    monkeypatch.setenv("PM_INVOKER_LOGIN", "someone")
    for module in (vi, ei, ci):
        monkeypatch.setattr(module.bootstrap_gate, "enforce", _allow)
    monkeypatch.setattr(ei.session_guard, "enforce", _allow)
    monkeypatch.setattr(ci.session_guard, "enforce", _allow)
    root = ["--capability-root", str(capability_root)]

    def run(module: ModuleType, argv: list[str]) -> tuple[int, str]:
        monkeypatch.setattr(sys, "argv", argv)
        code = module.main()
        out = capsys.readouterr()
        return code, out.out + out.err

    def validate(body: str) -> tuple[int, str]:
        issue = {"number": 7, "title": TITLE, "body": body, "labels": []}
        monkeypatch.setattr(vi, "_gh_get_issue", lambda *_a: issue)
        return run(vi, ["validate-issue", "7", *root])

    def edit(body: str) -> tuple[int, str]:
        issue = {"number": 7, "title": TITLE, "body": "", "labels": []}
        monkeypatch.setattr(ei, "_gh_get_issue", lambda *_a: issue)
        body_file = tmp_path / "edit.md"
        body_file.write_text(body, encoding="utf-8")
        return run(ei, ["edit-issue", "7", *root, "--body-file", str(body_file), "--dry-run"])

    def create(body: str) -> tuple[int, str]:
        def gh(cmd: list[str], *_a: Any, **_kw: Any) -> Any:
            stdout = json.dumps({"title": "[Feature] A capability"}) if "view" in cmd else ""
            return subprocess.CompletedProcess(cmd, 0, stdout, "")

        monkeypatch.setattr(ci.subprocess, "run", gh)
        body_file = tmp_path / "create.md"
        body_file.write_text(body, encoding="utf-8")
        argv = ["create-issue", "--type", "task", "--title", TITLE.split("] ", 1)[1]]
        argv += ["--workstream", "core", "--body-file", str(body_file), "--parent", "10"]
        return run(ci, [*argv, *root, "--dry-run"])

    return {"validate-issue": validate, "edit-issue": edit, "create-issue": create}


VERBS = ("validate-issue", "edit-issue", "create-issue")


@pytest.mark.parametrize("verb", VERBS)
def test_an_id_a_record_holds_passes_silently(
    verbs: dict[str, Verb], dc: ModuleType, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    lookup = _Lookup(dc, {"COR-001": True, f"{PM}:DEC-010": True})
    monkeypatch.setattr(dc, "lookup", lookup)
    _code, out = verbs[verb](_body(f" Per COR-001 and [{PM}:DEC-010-x]."))
    assert lookup.asked == [["COR-001", f"{PM}:DEC-010"]]
    assert "decision" not in out


@pytest.mark.parametrize("verb", VERBS)
def test_an_id_no_record_holds_warns_and_leaves_the_exit_alone(
    verbs: dict[str, Verb], dc: ModuleType, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    monkeypatch.setattr(dc, "lookup", _Lookup(dc, {"COR-001": True, "COR-064": False}))
    clean, _ = verbs[verb](_body(" Per COR-001."))
    code, out = verbs[verb](_body(" Per COR-001 and COR-064."))
    assert code == clean
    assert "[warning]" in out and f"{RULE}: cites COR-064, which no record holds." in out


@pytest.mark.parametrize("verb", VERBS)
def test_a_failed_lookup_warns_that_it_could_not_check_and_goes_on(
    verbs: dict[str, Verb], dc: ModuleType, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    monkeypatch.setattr(dc, "lookup", _Lookup(dc))
    clean, _ = verbs[verb](_body())
    code, out = verbs[verb](_body(" Per COR-064."))
    assert code == clean
    assert "[warning]" in out and f"{UNCHECKED}: decision ids not checked (COR-064)" in out
    assert RULE not in out


@pytest.mark.parametrize("verb", VERBS)
def test_a_body_citing_no_id_asks_nothing(
    verbs: dict[str, Verb], dc: ModuleType, monkeypatch: pytest.MonkeyPatch, verb: str
) -> None:
    lookup = _Lookup(dc, {})
    monkeypatch.setattr(dc, "lookup", lookup)
    verbs[verb](_body(" A bare DEC-061 is not checked."))
    assert lookup.asked == []


def test_validate_issue_json_carries_the_finding(
    vi: ModuleType,
    dc: ModuleType,
    verbs: dict[str, Verb],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(dc, "lookup", _Lookup(dc, {"PRJ-064": False}))
    issue = {"number": 7, "title": TITLE, "body": _body(" Per PRJ-064."), "labels": []}
    monkeypatch.setattr(vi, "_gh_get_issue", lambda *_a: issue)
    capability_root = tmp_path / ".pkit" / "capabilities" / PM
    monkeypatch.setattr(
        sys, "argv", ["validate-issue", "7", "--capability-root", str(capability_root), "--json"]
    )
    vi.main()
    document = json.loads(capsys.readouterr().out)
    assert [f for f in document["findings"] if f["label"] == RULE] == [
        {
            "severity": "warning",
            "label": RULE,
            "detail": "cites PRJ-064, which no record holds. Cite a decision only once its "
            "record exists, and describe one not yet written without an id.",
        }
    ]
