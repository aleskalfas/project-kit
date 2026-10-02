"""project-kit's tracking issue for the whole-repository friction check (#1266).

`.github/workflows/friction-report.yml` runs the check daily and after every
push to `main`, with the full history; living-docs' `friction-report` renders
its findings; `scripts/friction_tracking_issue.py` keeps one GitHub issue in
step with them. A schedule cannot be run from here, so:

- the **publisher** runs as the workflow runs it — a subprocess, `gh` found on
  the path — against a fake `gh` that keeps issues and labels in a file and logs
  every call, over publications the real renderer made: findings open the issue,
  the same findings change nothing, none close it, their return reopens it; an
  issue that quotes the marker is never taken for it; and a run that cannot read
  its publication or that `gh` refuses fails saying why;
- one run goes **end to end** over a real history: the real check, the real
  renderer, the publisher;
- the **workflow** is read as YAML: its triggers, its least privilege, the full
  history it fetches and checks before the check runs, nothing it fails on but
  the check or the publication, and no finding reaching a shell line.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import friction_repository as fr
from tests.adopter_repo import MakeAdopterRepo
from tests.friction_documents import Timeline, guide

REPO = Path(__file__).resolve().parent.parent
PUBLISHER = REPO / "scripts" / "friction_tracking_issue.py"
RENDERER = REPO / ".pkit" / "capabilities" / "living-docs" / "scripts" / "friction-report.py"
WORKFLOW = REPO / ".github" / "workflows" / "friction-report.yml"

MARKER = "<!-- pkit-friction-report -->"
LABEL = "friction-report"
BOT = "app/github-actions"

#: A `gh` that keeps issues and labels in the JSON file `FAKE_GH_STATE` names,
#: answers the calls the publisher makes as `gh` does, and logs every call.
#: `FAKE_GH_FAIL` names one call (`issue edit`, say) that fails.
FAKE_GH = r"""
import json, os, sys

path = os.environ["FAKE_GH_STATE"]
with open(path, encoding="utf-8") as f:
    state = json.load(f)
args = sys.argv[1:]
state["calls"].append(args)


def done(out="", code=0, err=""):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f)
    sys.stdout.write(out)
    sys.stderr.write(err)
    sys.exit(code)


def opt(name):
    return args[args.index(name) + 1] if name in args else None


def issue(number):
    return next(i for i in state["issues"] if i["number"] == int(number))


if " ".join(args[:2]) == os.environ.get("FAKE_GH_FAIL"):
    done(code=1, err="HTTP 502: Bad Gateway\n")
command = args[:2]
if command == ["issue", "list"]:
    label, author, fields = opt("--label"), opt("--author"), opt("--json").split(",")
    listed = [
        {field: i[field] for field in fields}
        for i in sorted(state["issues"], key=lambda i: -i["number"])
        if (label is None or label in i["labels"])
        and (author is None or i["author"]["login"] == author)
    ]
    done(json.dumps(listed))
if command == ["issue", "create"]:
    label = opt("--label")
    if label not in state["labels"]:
        done(code=1, err=f"could not add label: '{label}' not found\n")
    number = state["next"]
    state["next"] += 1
    with open(opt("--body-file"), encoding="utf-8") as f:
        body = f.read()
    state["issues"].append(
        {"number": number, "title": opt("--title"), "body": body, "state": "OPEN",
         "labels": [label], "author": {"login": "app/github-actions", "is_bot": True}}
    )
    done(f"https://github.com/owner/repo/issues/{number}\n")
if command == ["issue", "edit"]:
    with open(opt("--body-file"), encoding="utf-8") as f:
        issue(args[2])["body"] = f.read()
    done()
if command == ["issue", "close"]:
    issue(args[2])["state"] = "CLOSED"
    done()
if command == ["issue", "reopen"]:
    issue(args[2])["state"] = "OPEN"
    done()
if command == ["label", "create"]:
    if args[2] in state["labels"]:
        done(code=1, err=f'label with name "{args[2]}" already exists; use `--force` to update\n')
    state["labels"].append(args[2])
    done()
done(code=2, err=f"fake gh: unsupported {args}\n")
"""


class FakeGh:
    """The fake `gh`'s state, read and seeded by the tests."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.state_file = directory / "gh-state.json"
        gh = directory / "bin" / "gh"
        gh.parent.mkdir()
        gh.write_text(f"#!{sys.executable}\n{FAKE_GH}", encoding="utf-8")
        gh.chmod(0o755)
        self.bin = gh.parent
        self.save({"issues": [], "labels": [], "calls": [], "next": 1})

    def load(self) -> dict[str, Any]:
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def save(self, state: dict[str, Any]) -> None:
        self.state_file.write_text(json.dumps(state), encoding="utf-8")

    def seed(self, body: str, *, labels: list[str], author: str, state: str = "OPEN") -> int:
        current = self.load()
        number = current["next"]
        current["next"] += 1
        current["issues"].append(
            {
                "number": number,
                "title": "seeded",
                "body": body,
                "state": state,
                "labels": labels,
                "author": {"login": author, "is_bot": author.startswith("app/")},
            }
        )
        self.save(current)
        return number

    def issues(self) -> list[dict[str, Any]]:
        return self.load()["issues"]

    def writes(self) -> list[list[str]]:
        """Every call that changes something: all but the reading of the issue list."""
        return [call for call in self.load()["calls"] if call[:2] != ["issue", "list"]]

    def forget_calls(self) -> None:
        current = self.load()
        current["calls"] = []
        self.save(current)


@pytest.fixture
def gh(tmp_path: Path) -> FakeGh:
    return FakeGh(tmp_path)


def _document(findings: list[dict[str, Any]], unanchored: tuple[str, ...] = ()) -> dict[str, Any]:
    """A whole-repository document, shaped as the backbone writes it."""
    return {
        "schema_version": 1,
        "check": "repository",
        "mode": "warning",
        "dormant": False,
        "failed": False,
        "head": {"commit": "0" * 40, "uncommitted_paths": 0},
        "history": {"shallow": False},
        "counts": {},
        "states": {},
        "artefacts": [],
        "findings": findings,
        "measures": {
            "accepted_unanchored": [],
            "unanchored": list(unanchored),
            "uncovered_surface": [],
        },
    }


def _stale(location: str, day: str = "2026-09-30") -> dict[str, Any]:
    return {
        "artefact": location,
        "location": location,
        "kind": "stale",
        "anchor": {"kind": "path", "value": "src/cli/**"},
        "origin": {
            "commit": "a" * 40,
            "author": "Alice",
            "date": f"{day}T09:00:00+00:00",
            "change": "x",
        },
        "message": f'changed after its revalidation point: first in aaaaaaa "x" (Alice, {day})',
    }


def _render(directory: Path, document: dict[str, Any]) -> Path:
    """The real renderer's publication of `document`, in a file, as the workflow writes it."""
    report = directory / "friction.json"
    report.write_text(json.dumps(document), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(RENDERER), "--report", str(report), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    publication = directory / "friction-report.json"
    publication.write_text(proc.stdout, encoding="utf-8")
    return publication


def _publish(gh: FakeGh, publication: Path) -> subprocess.CompletedProcess[str]:
    """The publisher as the workflow runs it, with the fake `gh` first on the path."""
    env = {**os.environ, "PATH": f"{gh.bin}{os.pathsep}{os.environ['PATH']}"}
    env["FAKE_GH_STATE"] = str(gh.state_file)
    return subprocess.run(
        [sys.executable, str(PUBLISHER), str(publication)],
        cwd=gh.directory,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _run(gh: FakeGh, document: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    proc = _publish(gh, _render(gh.directory, document))
    assert proc.returncode == 0, proc.stderr
    return proc


# --- the issue's life ----------------------------------------------------------------------


def test_findings_open_one_labelled_issue_whose_body_is_the_rendering(gh: FakeGh) -> None:
    proc = _run(gh, _document([_stale("docs/guide.md")], unanchored=("docs/plain.md",)))
    assert "opened the tracking issue: https://github.com/owner/repo/issues/1" in proc.stdout
    (issue,) = gh.issues()
    assert issue["state"] == "OPEN" and issue["labels"] == [LABEL]
    rendered = json.loads((gh.directory / "friction-report.json").read_text(encoding="utf-8"))
    assert issue["body"] == f"{MARKER}\n{rendered['body']}"
    assert "- `docs/guide.md` · `path:src/cli/**` · since 2026-09-30" in issue["body"]
    assert "- `docs/plain.md`" in issue["body"]
    assert gh.load()["labels"] == [LABEL]


def test_the_same_findings_again_change_nothing(gh: FakeGh) -> None:
    document = _document([_stale("docs/guide.md")])
    _run(gh, document)
    before = gh.issues()
    gh.forget_calls()
    proc = _run(gh, document)
    assert gh.writes() == []
    assert gh.issues() == before
    assert "tracking issue #1: unchanged" in proc.stdout


def test_changed_findings_rewrite_the_body_in_place(gh: FakeGh) -> None:
    _run(gh, _document([_stale("docs/guide.md")]))
    gh.forget_calls()
    _run(gh, _document([_stale("docs/guide.md"), _stale("docs/notes.md")]))
    (issue,) = gh.issues()
    assert "`docs/notes.md`" in issue["body"] and issue["state"] == "OPEN"
    assert [call[:2] for call in gh.writes()] == [["issue", "edit"]]


def test_nothing_outstanding_closes_it_saying_so_and_findings_reopen_it(gh: FakeGh) -> None:
    _run(gh, _document([_stale("docs/guide.md")]))

    gh.forget_calls()
    closing = _run(gh, _document([], unanchored=("docs/plain.md",)))
    (issue,) = gh.issues()
    assert issue["state"] == "CLOSED"
    assert issue["body"].startswith(f"{MARKER}\n**Nothing outstanding.**")
    assert "- `docs/plain.md`" in issue["body"]  # the measures stay in it
    assert [call[:2] for call in gh.writes()] == [["issue", "edit"], ["issue", "close"]]
    assert "closed it: nothing outstanding" in closing.stdout

    gh.forget_calls()
    _run(gh, _document([], unanchored=("docs/plain.md",)))
    assert gh.writes() == []  # closed, and nothing changed: left alone

    gh.forget_calls()
    reopening = _run(gh, _document([_stale("docs/notes.md")]))
    (issue,) = gh.issues()
    assert issue["state"] == "OPEN" and "`docs/notes.md`" in issue["body"]
    assert [call[:2] for call in gh.writes()] == [["issue", "edit"], ["issue", "reopen"]]
    assert "reopened it" in reopening.stdout


def test_nothing_outstanding_and_no_issue_opens_none(gh: FakeGh) -> None:
    proc = _run(gh, _document([], unanchored=("docs/plain.md",)))
    assert gh.issues() == [] and gh.writes() == []
    assert "nothing outstanding and no tracking issue" in proc.stdout


@pytest.mark.parametrize(
    ("labels", "author", "first_line"),
    [
        ([LABEL], "someone", MARKER),  # a person's issue quoting the marker, labelled
        ([], BOT, MARKER),  # the automation's, without its label
        ([LABEL], BOT, "Quoting it: <!-- pkit-friction-report -->"),  # marker not its first line
    ],
)
def test_an_issue_that_only_quotes_the_marker_is_never_taken_for_it(
    gh: FakeGh, labels: list[str], author: str, first_line: str
) -> None:
    other = gh.seed(f"{first_line}\nSomething else.", labels=labels, author=author)
    _run(gh, _document([_stale("docs/guide.md")]))
    issues = {issue["number"]: issue for issue in gh.issues()}
    assert issues[other]["body"] == f"{first_line}\nSomething else."
    assert issues[other]["state"] == "OPEN"
    assert len(issues) == 2  # its own was opened beside it


def test_an_existing_label_is_kept_as_it_is(gh: FakeGh) -> None:
    state = gh.load()
    state["labels"] = [LABEL]
    gh.save(state)
    _run(gh, _document([_stale("docs/guide.md")]))
    assert gh.issues()[0]["labels"] == [LABEL]


# --- when it fails -------------------------------------------------------------------------


def test_a_refused_call_fails_the_run_saying_why(
    gh: FakeGh, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run(gh, _document([_stale("docs/guide.md")]))
    publication = _render(gh.directory, _document([]))
    monkeypatch.setenv("FAKE_GH_FAIL", "issue edit")
    proc = _publish(gh, publication)
    assert proc.returncode == 1
    assert "`gh issue edit` exited 1: HTTP 502: Bad Gateway" in proc.stderr
    assert gh.issues()[0]["state"] == "OPEN"  # nothing after the refusal was done


@pytest.mark.parametrize(
    ("text", "says"),
    [
        ("not json", "holds no publication of `pkit living-docs friction-report --json`"),
        (json.dumps({"schema_version": 2, "outstanding": 0, "body": ""}), "schema_version 2"),
        (json.dumps({"schema_version": 1, "body": "x"}), "no count of outstanding findings"),
    ],
)
def test_a_publication_it_cannot_read_fails_the_run_and_calls_nothing(
    gh: FakeGh, text: str, says: str
) -> None:
    publication = gh.directory / "friction-report.json"
    publication.write_text(text, encoding="utf-8")
    proc = _publish(gh, publication)
    assert proc.returncode == 1 and says in proc.stderr
    assert gh.load()["calls"] == []


# --- end to end ----------------------------------------------------------------------------


def test_a_real_history_end_to_end(make_adopter_repo: MakeAdopterRepo, gh: FakeGh) -> None:
    timeline = Timeline(make_adopter_repo())
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"})
    root = timeline.adopter.root

    def check() -> dict[str, Any]:
        return json.loads(fr.render_json(fr.run_repository_check(root)))

    _run(gh, check())
    (issue,) = gh.issues()
    assert issue["state"] == "OPEN" and "- `docs/guide.md` · `path:src/cli/**`" in issue["body"]

    timeline.commit(
        "revalidate the guide",
        {"docs/guide.md": guide(at="2026-11-01T00:00:00Z", because="the CLI reads the same")},
    )
    _run(gh, check())
    (issue,) = gh.issues()
    assert issue["state"] == "CLOSED" and "**Nothing outstanding.**" in issue["body"]


# --- the workflow --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def workflow() -> dict[str, Any]:
    # YAML 1.2, so the `on:` key stays the string "on".
    return YAML(typ="safe").load(WORKFLOW.read_text(encoding="utf-8"))


def _steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return workflow["jobs"]["friction-report"]["steps"]


def _index(workflow: dict[str, Any], name_prefix: str) -> int:
    return next(
        i for i, s in enumerate(_steps(workflow)) if s.get("name", "").startswith(name_prefix)
    )


def test_it_runs_on_a_schedule_and_after_every_push_to_main(workflow: dict[str, Any]) -> None:
    triggers = workflow["on"]
    assert triggers["push"] == {"branches": ["main"]}
    assert [entry["cron"] for entry in triggers["schedule"]] == ["41 5 * * *"]
    assert "workflow_dispatch" in triggers
    assert "pull_request" not in triggers and "merge_group" not in triggers  # no gate


def test_least_privilege_and_one_run_at_a_time(workflow: dict[str, Any]) -> None:
    assert workflow["permissions"] == {"contents": "read", "issues": "write"}
    assert workflow["concurrency"] == {"group": "friction-report", "cancel-in-progress": False}
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in text  # the built-in token only


def test_the_full_history_is_fetched_and_confirmed_before_the_check(
    workflow: dict[str, Any],
) -> None:
    steps = _steps(workflow)
    checkout = steps[_index(workflow, "Checkout")]
    assert checkout["uses"].startswith("actions/checkout@") and checkout["with"]["fetch-depth"] == 0
    confirm = _index(workflow, "Confirm the full history")
    assert "git rev-parse --is-shallow-repository" in steps[confirm]["run"]
    assert confirm < _index(workflow, "Whole-repository friction check")


def test_it_runs_the_check_renders_it_and_publishes_it(workflow: dict[str, Any]) -> None:
    steps = _steps(workflow)
    check = steps[_index(workflow, "Whole-repository friction check")]["run"]
    assert check.startswith("uv run pkit friction check --all --json >")
    render = steps[_index(workflow, "Render the findings")]["run"]
    assert "uv run pkit living-docs friction-report --report" in render and "--json" in render
    assert "$GITHUB_STEP_SUMMARY" in render
    publish = steps[_index(workflow, "Publish to the tracking issue")]
    assert publish["run"].startswith("uv run python scripts/friction_tracking_issue.py ")
    assert publish["env"] == {"GH_TOKEN": "${{ github.token }}"}


def test_nothing_fails_on_findings_and_no_finding_reaches_a_shell_line(
    workflow: dict[str, Any],
) -> None:
    """No step is skipped or tolerated on an outcome, and no run line expands an
    expression: what the check found travels in files, never in a command."""
    for step in _steps(workflow):
        assert "if" not in step and "continue-on-error" not in step
        assert "${{" not in step.get("run", "")
