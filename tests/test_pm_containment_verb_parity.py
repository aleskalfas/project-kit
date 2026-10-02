"""Every verb that checks the containment graph judges a pair alike (#1313).

`create-issue`, `set-field --parent` and `link-parent` refuse a parent the
issue's type may not sit under; `validate-issue` reports an issue already under
one. Each types the issue and its parent through `containment_graph.issue_type`
with the adopter's substrate map, so for the same (map, child, parent) the three
writers and the validator give one verdict — refused, allowed, or outside the
graph (a type that cannot be told: under a map, only the map's title-prefix
binding tells one). These drive each verb's real `main()` against the shipped
schemas, `--dry-run` for the writers, with the tracker answered at the
containment seam; `_lib/containment_graph`'s own parity suite pins the same table
below the verbs.

`create-issue` files its issue with the kit's title prefix (`--type`), which a
map need not read, and `set-field` and `link-parent` read an issue's own form
from the kit's prefixes — so a row whose child title only the map reads
(`[Story]`) is judged by `create-issue` and `validate-issue` alone; that the
writers do not yet honour a map's prefixes is a follow-up.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import bootstrap_gate, containment, session_guard  # noqa: E402


def _load(script: str):
    name = f"pm_{script.replace('-', '_')}_containment_parity"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{script}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def verbs() -> dict:
    return {v: _load(v) for v in ("create-issue", "set-field", "link-parent", "validate-issue")}


REFUSED, ALLOWED, OUTSIDE = "refused", "allowed", "outside the graph"
CREATE, SET_FIELD, LINK_PARENT, VALIDATE = "create-issue", "set-field", "link-parent", "validate"
EVERY_VERB = (CREATE, SET_FIELD, LINK_PARENT, VALIDATE)

STORY_MAP = "axes:\n  type:\n    title-prefix:\n      remap: {feature: '[Story]', task: '[Task]'}\n"
TYPE_BY_LABEL_MAP = "axes:\n  type:\n    label:\n      remap: {bug: 'kind/bug'}\n"

# The first line each child type names #9 with, in a form it allows.
_FIRST_LINE = {"task": "Feature: #9", "feature": "EPIC: #9"}

# (map, child type, child title, parent title, parent labels, verdict, verbs)
_ROWS = [
    (None, "task", "[Task] the child", "[Task] the parent", (), REFUSED, EVERY_VERB),
    (None, "task", "[Task] the child", "[Feature] the parent", (), ALLOWED, EVERY_VERB),
    (None, "task", "[Task] the child", "[Bug] Login crashes", (), REFUSED, EVERY_VERB),
    (None, "task", "[Task] the child", "Login crashes", ("type:bug",), REFUSED, EVERY_VERB),
    (None, "feature", "[Feature] the child", "[Feature] the parent", (), REFUSED, EVERY_VERB),
    (None, "task", "[Task] the child", "no type at all", (), OUTSIDE, EVERY_VERB),
    (TYPE_BY_LABEL_MAP, "task", "[Task] the child", "[Bug] Login crashes", (), OUTSIDE, EVERY_VERB),
    (TYPE_BY_LABEL_MAP, "task", "[Task] the child", "[Task] the parent", (), OUTSIDE, EVERY_VERB),
    (
        STORY_MAP,
        "feature",
        "[Story] the child",
        "[Story] the parent",
        (),
        REFUSED,
        (CREATE, VALIDATE),
    ),
    (STORY_MAP, "task", "[Task] the child", "[Story] the parent", (), ALLOWED, EVERY_VERB),
    (STORY_MAP, "task", "[Task] the child", "[Task] the parent", (), REFUSED, EVERY_VERB),
]


def _map_name(map_text: str | None) -> str:
    return {None: "greenfield", STORY_MAP: "story-map", TYPE_BY_LABEL_MAP: "type-by-label"}[
        map_text
    ]


_CASES = [
    pytest.param(m, ct, c, p, pl, v, verb, id=f"{verb}:{_map_name(m)}:{c}<-{p}")
    for m, ct, c, p, pl, v, applies in _ROWS
    for verb in applies
]


def _stage(tmp_path: Path, map_text: str | None) -> Path:
    root = tmp_path / ".pkit" / "capabilities" / "project-management"
    shutil.copytree(CAPABILITY / "schemas", root / "schemas")
    shutil.copytree(CAPABILITY / "templates", root / "templates")
    (root / "project").mkdir(parents=True)
    (root / "project" / "config.yaml").write_text(
        "schema_version: 1\ndefault_branch: main\nworkstreams: [ws]\n", encoding="utf-8"
    )
    (root / "project" / "members.yaml").write_text("members: []\n", encoding="utf-8")
    if map_text is not None:
        (root / "project" / "substrate-map.yaml").write_text(
            f"schema_version: 1\n{map_text}", encoding="utf-8"
        )
    return root


def _answer_the_tracker(monkeypatch, child: dict, parent: dict) -> None:
    """The seam's record reads answer #42 (the child) and #9 (its parent); no
    other gh call may run (git, for the invoker's identity, answers nothing)."""
    records = {42: child, 9: parent}

    def read_issue_record(config, *, issue_number):
        issue = records[int(issue_number)]
        return containment.IssueRecord(issue=issue, parent=None)

    def no_gh(cmd, *args, **kwargs):
        if cmd and str(cmd[0]) == "gh":
            raise AssertionError(f"unexpected gh call: {cmd}")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(containment, "read_issue_record", read_issue_record)
    monkeypatch.setattr(
        containment,
        "read_link_state",
        lambda config, *, issue_number: containment.IssueLinkState(1, None),
    )
    monkeypatch.setattr(bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr("subprocess.run", no_gh)
    monkeypatch.setenv("PM_INVOKER_LOGIN", "me")


def _issue(title: str, body: str, labels: tuple[str, ...] = ()) -> dict:
    return {
        "title": title,
        "body": body,
        "labels": [{"name": name} for name in labels],
        "state": "OPEN",
        "milestone": None,
    }


def _run(
    verbs, verb: str, root: Path, child_type: str, child: dict, parent: dict, monkeypatch, capsys
) -> str:
    """Run ``verb`` on the pair; return its verdict."""
    common = ["--capability-root", str(root)]
    if verb == CREATE:
        module = verbs["create-issue"]
        argv = ["--type", child_type, "--title", "a pair every verb judges alike", "--parent", "9"]
        argv += ["--workstream", "ws", "--dry-run", *common]
    elif verb == SET_FIELD:
        module = verbs["set-field"]
        monkeypatch.setattr(
            module, "gh_get_issue", lambda n, *a, **k: {**child, "id": "I", "url": "u"}
        )
        argv = ["42", "--parent", "9", "--dry-run", *common]
    elif verb == LINK_PARENT:
        module = verbs["link-parent"]
        # link-parent reads both issues from the issue list, not the record read.
        rows = ({**child, "number": 42}, {**parent, "number": 9})
        monkeypatch.setattr(
            containment,
            "fetch_issue_corpus",
            lambda config, **kw: containment.IssueCorpus(rows=rows, complete=True),
        )
        monkeypatch.setattr(module, "check_native_links", lambda entries, config, reads: entries)
        argv = ["42", "--dry-run", *common]
    else:
        module = verbs["validate-issue"]
        monkeypatch.setattr(module, "_gh_get_issue", lambda n, config: child)
        argv = ["42", "--json", "--phase", "create", *common]
    monkeypatch.setattr(sys, "argv", [verb, *argv])
    rc = module.main()
    out, err = capsys.readouterr()
    said = out + err
    refused = "may not sit under #9" in said
    if verb == VALIDATE:
        findings = json.loads(out)["findings"]
        refused = any(f["label"] == "body.parent-ref.containment" for f in findings)
        return REFUSED if refused else "not refused"
    if verb == LINK_PARENT:
        if refused:
            return REFUSED
        return "not refused" if "#42  would link under #9" in out else f"neither: {said}"
    assert rc == ({CREATE: 2, SET_FIELD: 1}[verb] if refused else 0), said
    if refused:
        return REFUSED
    return OUTSIDE if "type cannot be told" in said else ALLOWED


@pytest.mark.parametrize(
    ("map_text", "child_type", "child_title", "parent_title", "parent_labels", "verdict", "verb"),
    _CASES,
)
def test_every_verb_judges_the_pair_alike(
    verbs,
    tmp_path,
    monkeypatch,
    capsys,
    map_text,
    child_type,
    child_title,
    parent_title,
    parent_labels,
    verdict,
    verb,
) -> None:
    root = _stage(tmp_path, map_text)
    child = _issue(child_title, f"{_FIRST_LINE[child_type]}\n\n## What\nx\n")
    parent = _issue(parent_title, "", parent_labels)
    _answer_the_tracker(monkeypatch, child, parent)

    got = _run(verbs, verb, root, child_type, child, parent, monkeypatch, capsys)

    if verb in (VALIDATE, LINK_PARENT):
        # These two say only whether the pair is refused.
        assert got == (REFUSED if verdict == REFUSED else "not refused")
    else:
        assert got == verdict
