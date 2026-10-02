"""project-kit's tracking issue for the whole-repository friction check (#1266).

`.github/workflows/friction-report.yml` runs the check on `main` with the full
history, after every push and once a day; `scripts/friction_report_body.py`
renders its findings; `scripts/friction_tracking_issue.py` keeps one GitHub
issue in step with them (ADR-055 point 5). A schedule cannot be run from here,
so:

- the **publisher** runs as the workflow runs it — a subprocess, `gh` found on
  the path — against a fake `gh` that keeps issues and labels in a file and logs
  every call, over publications the real renderer made. The issue is open
  exactly while a finding needs an answer; the same findings change nothing; it
  is the token's own issue with the marker or the label, whichever sign a hand
  removed put back; a person's issue is never taken for it; a second one, a
  listing that may be incomplete, a publication it cannot read or a call `gh`
  refuses fails the run, saying why;
- one run goes **end to end** over a real history: the real check, the real
  renderer, the publisher;
- the **workflow** is read as YAML: its triggers, that only `main` publishes,
  its least privilege, the full history it fetches and checks before the check
  runs, nothing it fails on but the check or the publication, and no finding
  reaching a shell line.
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
from scripts import friction_tracking_issue as publisher

from project_kit import friction_repository as fr
from tests.adopter_repo import MakeAdopterRepo
from tests.friction_documents import Timeline, guide

REPO = Path(__file__).resolve().parent.parent
PUBLISHER = REPO / "scripts" / "friction_tracking_issue.py"
RENDERER = REPO / "scripts" / "friction_report_body.py"
WORKFLOW = REPO / ".github" / "workflows" / "friction-report.yml"

MARKER = publisher.MARKER
NOTICE = publisher.NOTICE
LABEL = publisher.LABEL
BOT = "app/github-actions"

#: A `gh` that keeps issues and labels in the JSON file `FAKE_GH_STATE` names,
#: answers the calls the publisher makes as `gh` does, and logs every call.
#: `FAKE_GH_FAIL` names one call (`issue edit`, say) that fails. The listing is
#: `gh`'s own by author: it finds the token's issues under the name
#: `github-actions[bot]`, gives their author as `app/github-actions`, newest
#: first, no more than `--limit`; a label filter, which would go through the
#: search index, is refused. With `FAKE_GH_LISTS_EVERY_AUTHOR` it ignores the
#: author it is asked for, so the publisher's own reading of the author is what
#: keeps a person's issue out.
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


def field(i, name):
    return [{"name": label} for label in i["labels"]] if name == "labels" else i[name]


if " ".join(args[:2]) == os.environ.get("FAKE_GH_FAIL"):
    done(code=1, err="HTTP 502: Bad Gateway\n")
command = args[:2]
if command == ["issue", "list"]:
    if "--label" in args or "--search" in args:
        done(code=2, err="fake gh: a label or search filter goes through the search index\n")
    listed_as = {"github-actions[bot]": "app/github-actions"}.get(opt("--author"), opt("--author"))
    every_author = os.environ.get("FAKE_GH_LISTS_EVERY_AUTHOR")
    states = {"all": ("OPEN", "CLOSED"), "closed": ("CLOSED",)}.get(opt("--state"), ("OPEN",))
    fields = opt("--json").split(",")
    listed = [
        {name: field(i, name) for name in fields}
        for i in sorted(state["issues"], key=lambda i: -i["number"])
        if (every_author or i["author"]["login"] == listed_as) and i["state"] in states
    ]
    done(json.dumps(listed[: int(opt("--limit") or 30)]))
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
    if opt("--body-file"):
        with open(opt("--body-file"), encoding="utf-8") as f:
            issue(args[2])["body"] = f.read()
    label = opt("--add-label")
    if label:
        if label not in state["labels"]:
            done(code=1, err=f"could not add label: '{label}' not found\n")
        issue(args[2])["labels"].append(label)
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

    def seed(self, body: str, *, labels: list[str], author: str = BOT, state: str = "OPEN") -> int:
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
        current["labels"] = sorted({*current["labels"], *labels})
        self.save(current)
        return number

    def issues(self) -> dict[int, dict[str, Any]]:
        return {issue["number"]: issue for issue in self.load()["issues"]}

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


def _finding(kind: str, location: str, message: str, day: str) -> dict[str, Any]:
    return {
        "artefact": location,
        "location": location,
        "kind": kind,
        "anchor": {"kind": "path", "value": "src/cli/**"},
        "origin": {
            "commit": "a" * 40,
            "author": "Alice",
            "date": f"{day}T09:00:00+00:00",
            "change": "x",
        },
        "message": message,
    }


def _stale(location: str, day: str = "2026-09-30") -> dict[str, Any]:
    message = f'changed after its revalidation point: first in aaaaaaa "x" (Alice, {day})'
    return _finding("stale", location, message, day)


def _deferred(location: str, day: str = "2026-09-30") -> dict[str, Any]:
    return _finding("deferred", location, "deferred: after the engine settles", day)


def _render(directory: Path, document: dict[str, Any]) -> Path:
    """The real renderer's publication of `document`, in a file, as the workflow writes it."""
    report = directory / "friction.json"
    report.write_text(json.dumps(document), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(RENDERER), str(report), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    publication = directory / "friction-report.json"
    publication.write_text(proc.stdout, encoding="utf-8")
    return publication


def _publish(gh: FakeGh, publication: Path, **environment: str) -> subprocess.CompletedProcess[str]:
    """The publisher as the workflow runs it, with the fake `gh` first on the path and
    no step summary to write to — the suite's own, when it runs in a workflow — unless
    `environment` names one."""
    env = {
        **os.environ,
        "PATH": f"{gh.bin}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GH_STATE": str(gh.state_file),
        "GITHUB_STEP_SUMMARY": "",
        **environment,
    }
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


def _body(gh: FakeGh) -> str:
    """The body the last rendering publishes: the marker, the notice, the rendering."""
    rendered = json.loads((gh.directory / "friction-report.json").read_text(encoding="utf-8"))
    return f"{MARKER}\n{NOTICE}\n\n{rendered['body']}"


# --- the issue's life ----------------------------------------------------------------------


def test_findings_open_one_labelled_issue_whose_body_is_the_rendering(gh: FakeGh) -> None:
    proc = _run(gh, _document([_stale("docs/guide.md")], unanchored=("docs/plain.md",)))
    assert "opened the tracking issue: https://github.com/owner/repo/issues/1" in proc.stdout
    (issue,) = gh.issues().values()
    assert issue["state"] == "OPEN" and issue["labels"] == [LABEL]
    assert issue["body"] == _body(gh)
    assert issue["body"].splitlines()[:2] == [MARKER, NOTICE]
    assert "rewrites this body, and edits to it are lost" in NOTICE
    assert "- `docs/guide.md` · `path:src/cli/**` · since `2026-09-30`" in issue["body"]
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
    (issue,) = gh.issues().values()
    assert "`docs/notes.md`" in issue["body"] and issue["state"] == "OPEN"
    assert [call[:2] for call in gh.writes()] == [["issue", "edit"]]


def test_nothing_to_answer_closes_it_saying_so_and_findings_reopen_it(gh: FakeGh) -> None:
    _run(gh, _document([_stale("docs/guide.md")]))

    gh.forget_calls()
    closing = _run(gh, _document([], unanchored=("docs/plain.md",)))
    (issue,) = gh.issues().values()
    assert issue["state"] == "CLOSED"
    assert "\n\n**Nothing needs an answer.**" in issue["body"]
    assert "- `docs/plain.md`" in issue["body"]  # the measures stay in it
    assert [call[:2] for call in gh.writes()] == [["issue", "edit"], ["issue", "close"]]
    assert "closed it: nothing needs an answer" in closing.stdout

    gh.forget_calls()
    _run(gh, _document([], unanchored=("docs/plain.md",)))
    assert gh.writes() == []  # closed, and nothing changed: left alone

    gh.forget_calls()
    reopening = _run(gh, _document([_stale("docs/notes.md")]))
    (issue,) = gh.issues().values()
    assert issue["state"] == "OPEN" and "`docs/notes.md`" in issue["body"]
    assert [call[:2] for call in gh.writes()] == [["issue", "edit"], ["issue", "reopen"]]
    assert "reopened it" in reopening.stdout


def test_nothing_to_answer_and_no_issue_opens_none(gh: FakeGh) -> None:
    proc = _run(gh, _document([], unanchored=("docs/plain.md",)))
    assert gh.issues() == {} and gh.writes() == []
    assert "nothing needs an answer and there is no tracking issue" in proc.stdout


def test_a_deferral_opens_no_issue_and_holds_none_open(gh: FakeGh) -> None:
    """A deferral is an answer: listed in the body, and never what the issue is open for."""
    proc = _run(gh, _document([_deferred("docs/notes.md")]))
    assert gh.issues() == {} and gh.writes() == []
    assert "nothing needs an answer and there is no tracking issue" in proc.stdout

    _run(gh, _document([_stale("docs/guide.md"), _deferred("docs/notes.md")]))
    (issue,) = gh.issues().values()
    assert issue["state"] == "OPEN"

    _run(gh, _document([_deferred("docs/guide.md"), _deferred("docs/notes.md")]))
    (issue,) = gh.issues().values()
    assert issue["state"] == "CLOSED"
    assert "**Nothing needs an answer.**" in issue["body"]
    deferred = issue["body"].split("### Deferred", 1)[1].split("###", 1)[0]
    assert "- `docs/guide.md`" in deferred and "- `docs/notes.md`" in deferred


def test_an_existing_label_is_kept_as_it_is(gh: FakeGh) -> None:
    state = gh.load()
    state["labels"] = [LABEL]
    gh.save(state)
    _run(gh, _document([_stale("docs/guide.md")]))
    (issue,) = gh.issues().values()
    assert issue["labels"] == [LABEL]


# --- which issue it is ---------------------------------------------------------------------


def test_the_listing_is_by_author_alone_and_reads_every_state(gh: FakeGh) -> None:
    """No label filter: that listing goes through the search index, which lags a write."""
    _run(gh, _document([_stale("docs/guide.md")]))
    (listing,) = [call for call in gh.load()["calls"] if call[:2] == ["issue", "list"]]
    assert listing[2:] == [
        "--author",
        "github-actions[bot]",
        "--state",
        "all",
        "--limit",
        "1000",
        "--json",
        "number,state,body,labels,author",
    ]


def test_a_note_above_the_marker_does_not_make_a_second_issue(gh: FakeGh) -> None:
    document = _document([_stale("docs/guide.md")])
    _run(gh, document)
    state = gh.load()
    state["issues"][0]["body"] = "A note someone wrote on top.\n\n" + state["issues"][0]["body"]
    gh.save(state)

    gh.forget_calls()
    proc = _run(gh, document)
    (issue,) = gh.issues().values()  # the same one: none opened beside it
    assert issue["body"] == _body(gh)  # rewritten, the note gone as the notice says
    assert [call[:2] for call in gh.writes()] == [["issue", "edit"]]
    assert "tracking issue #1: rewrote its body" in proc.stdout


def test_a_removed_label_is_put_back(gh: FakeGh) -> None:
    document = _document([_stale("docs/guide.md")])
    _run(gh, document)
    state = gh.load()
    state["issues"][0]["labels"] = []
    gh.save(state)

    gh.forget_calls()
    proc = _run(gh, document)
    (issue,) = gh.issues().values()
    assert issue["labels"] == [LABEL] and issue["body"] == _body(gh)
    assert gh.writes()[-1] == ["issue", "edit", "1", "--add-label", LABEL]
    assert "tracking issue #1: put its label back" in proc.stdout


def test_a_removed_marker_is_put_back(gh: FakeGh) -> None:
    document = _document([_stale("docs/guide.md")])
    _run(gh, document)
    state = gh.load()
    state["issues"][0]["body"] = "Someone replaced the whole body."
    gh.save(state)

    gh.forget_calls()
    proc = _run(gh, document)
    (issue,) = gh.issues().values()
    assert issue["body"] == _body(gh) and issue["body"].startswith(f"{MARKER}\n")
    assert "tracking issue #1: rewrote its body" in proc.stdout


@pytest.mark.parametrize(
    ("labels", "author", "body"),
    [
        ([LABEL], "someone", f"{MARKER}\nA person's issue with both signs."),
        ([], BOT, "The token's own issue, with neither sign."),
    ],
)
def test_an_issue_that_is_not_the_tracking_issue_is_never_touched(
    gh: FakeGh, labels: list[str], author: str, body: str
) -> None:
    other = gh.seed(body, labels=labels, author=author)
    _run(gh, _document([_stale("docs/guide.md")]))
    issues = gh.issues()
    assert issues[other]["body"] == body and issues[other]["state"] == "OPEN"
    assert len(issues) == 2  # its own was opened beside it


def test_another_authors_issue_the_listing_returns_is_not_taken(gh: FakeGh) -> None:
    """The author is read here too, not left to the listing's filter."""
    body = f"{MARKER}\nA person's issue with both signs."
    other = gh.seed(body, labels=[LABEL], author="someone")
    proc = _publish(
        gh,
        _render(gh.directory, _document([_stale("docs/guide.md")])),
        FAKE_GH_LISTS_EVERY_AUTHOR="1",
    )
    assert proc.returncode == 0, proc.stderr
    issues = gh.issues()
    assert issues[other]["body"] == body
    assert len(issues) == 2 and "opened the tracking issue" in proc.stdout


def test_two_tracking_issues_fail_the_run_naming_both_with_the_oldest_kept_in_step(
    gh: FakeGh,
) -> None:
    oldest = gh.seed(f"{MARKER}\nAn earlier body.", labels=[LABEL], state="CLOSED")
    newer_body = "A second one, found by its label."
    newer = gh.seed(newer_body, labels=[LABEL])
    summary = gh.directory / "summary.md"

    proc = _publish(
        gh,
        _render(gh.directory, _document([_stale("docs/guide.md")])),
        GITHUB_STEP_SUMMARY=str(summary),
    )
    assert proc.returncode == 1
    issues = gh.issues()
    assert issues[oldest]["body"] == _body(gh) and issues[oldest]["state"] == "OPEN"
    assert issues[newer]["body"] == newer_body and issues[newer]["state"] == "OPEN"
    assert len(issues) == 2  # none opened, none closed
    for said in (proc.stderr, summary.read_text(encoding="utf-8")):
        assert f"there is more than one tracking issue: #{oldest}, #{newer}." in said
        assert f"#{oldest}, the oldest, was kept in step" in said
        assert f"Close #{newer} and remove the marker line `{MARKER}`" in said
        assert f"the `{LABEL}` label" in said
    assert "more than one" not in issues[oldest]["body"]  # never in the issue


def test_a_listing_at_its_limit_fails_the_run_and_opens_nothing(gh: FakeGh) -> None:
    """As many issues as were asked for: one more may exist, the tracking issue among them."""
    state = gh.load()
    state["issues"] = [
        {
            "number": number,
            "title": "another of the token's issues",
            "body": "",
            "state": "CLOSED",
            "labels": [],
            "author": {"login": BOT, "is_bot": True},
        }
        for number in range(1, publisher.LISTING_LIMIT + 1)
    ]
    state["next"] = publisher.LISTING_LIMIT + 1
    gh.save(state)

    proc = _publish(gh, _render(gh.directory, _document([_stale("docs/guide.md")])))
    assert proc.returncode == 1
    assert "the listing may be incomplete" in proc.stderr
    assert gh.writes() == [] and len(gh.issues()) == publisher.LISTING_LIMIT


# --- when it fails -------------------------------------------------------------------------


def test_a_refused_call_fails_the_run_saying_why(gh: FakeGh) -> None:
    _run(gh, _document([_stale("docs/guide.md")]))
    publication = _render(gh.directory, _document([]))
    proc = _publish(gh, publication, FAKE_GH_FAIL="issue edit")
    assert proc.returncode == 1
    assert "`gh issue edit` exited 1: HTTP 502: Bad Gateway" in proc.stderr
    (issue,) = gh.issues().values()
    assert issue["state"] == "OPEN"  # nothing after the refusal was done


@pytest.mark.parametrize(
    ("text", "says"),
    [
        ("not json", "holds no publication of `scripts/friction_report_body.py --json`"),
        (json.dumps({"schema_version": 2, "needs_answer": 0, "body": ""}), "schema_version 2"),
        (
            json.dumps({"schema_version": 1, "body": "x"}),
            "no count of findings that need an answer",
        ),
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


def test_a_body_no_utf8_can_hold_is_published_escaped(gh: FakeGh) -> None:
    """A publication the renderer did not make, carrying a lone surrogate: no crash."""
    publication = gh.directory / "friction-report.json"
    made = {"schema_version": 1, "needs_answer": 1, "body": "- docs/caf\udce9.md\n"}
    publication.write_text(json.dumps(made), encoding="utf-8")
    proc = _publish(gh, publication)
    assert proc.returncode == 0, proc.stderr
    (issue,) = gh.issues().values()
    assert r"- docs/caf\udce9.md" in issue["body"]


# --- end to end ----------------------------------------------------------------------------


def test_a_real_history_end_to_end(make_adopter_repo: MakeAdopterRepo, gh: FakeGh) -> None:
    timeline = Timeline(make_adopter_repo())
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"})
    root = timeline.adopter.root

    def check() -> dict[str, Any]:
        return json.loads(fr.render_json(fr.run_repository_check(root)))

    _run(gh, check())
    (issue,) = gh.issues().values()
    assert issue["state"] == "OPEN" and "- `docs/guide.md` · `path:src/cli/**`" in issue["body"]

    # Deferred with a reason: answered, so the issue closes, the deferral listed in it.
    timeline.commit(
        "defer the guide",
        {"docs/guide.md": guide(deferred=[("path", "src/cli/**", "after the release")])},
    )
    _run(gh, check())
    (issue,) = gh.issues().values()
    assert issue["state"] == "CLOSED" and "**Nothing needs an answer.**" in issue["body"]
    assert "after the release" in issue["body"].split("### Deferred", 1)[1]

    timeline.commit(
        "revalidate the guide",
        {"docs/guide.md": guide(at="2026-11-01T00:00:00Z", because="the CLI reads the same")},
    )
    _run(gh, check())
    (issue,) = gh.issues().values()
    assert issue["state"] == "CLOSED" and "### Deferred" not in issue["body"]


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


def test_it_runs_after_every_push_to_main_daily_and_by_hand_and_on_nothing_else(
    workflow: dict[str, Any],
) -> None:
    triggers = workflow["on"]
    assert set(triggers) == {"push", "schedule", "workflow_dispatch"}  # no gate among them
    assert triggers["push"] == {"branches": ["main"]}
    assert [entry["cron"] for entry in triggers["schedule"]] == ["41 5 * * *"]
    assert triggers["workflow_dispatch"] == {}


def test_only_main_publishes(workflow: dict[str, Any]) -> None:
    """One job, guarded as a whole: a run dispatched from another branch writes no issue."""
    (job,) = workflow["jobs"].values()
    assert job["if"] == "github.ref == 'refs/heads/main'"


def test_least_privilege_and_one_run_at_a_time(workflow: dict[str, Any]) -> None:
    assert workflow["permissions"] == {"contents": "read", "issues": "write"}
    assert workflow["concurrency"] == {"group": "friction-report", "cancel-in-progress": False}
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in text  # the built-in token only
    handed_the_token = [s["name"] for s in _steps(workflow) if "github.token" in str(s)]
    assert handed_the_token == ["Publish to the tracking issue"]


def test_the_full_history_is_fetched_and_confirmed_before_the_check(
    workflow: dict[str, Any],
) -> None:
    steps = _steps(workflow)
    checkout = steps[_index(workflow, "Checkout")]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"] == {"fetch-depth": 0, "persist-credentials": False}
    confirm = _index(workflow, "Confirm the full history")
    assert "git rev-parse --is-shallow-repository" in steps[confirm]["run"]
    assert confirm < _index(workflow, "Whole-repository friction check")


def test_the_query_commands_are_provisioned_before_the_check_as_the_required_check_does(
    workflow: dict[str, Any],
) -> None:
    """The same step, in the same place, as `checks.yml` runs before its aggregator."""
    checks = YAML(typ="safe").load((WORKFLOW.parent / "checks.yml").read_text(encoding="utf-8"))
    (theirs,) = [
        s for s in checks["jobs"]["checks"]["steps"] if s.get("name", "").startswith("Sync")
    ]
    sync = _index(workflow, "Sync")
    assert _steps(workflow)[sync] == theirs
    assert theirs["run"] == "uv run pkit sync"
    assert _index(workflow, "Install project") < sync
    assert sync < _index(workflow, "Whole-repository friction check")


def test_it_runs_the_check_renders_it_and_publishes_it(workflow: dict[str, Any]) -> None:
    steps = _steps(workflow)
    check = steps[_index(workflow, "Whole-repository friction check")]["run"]
    assert check.startswith("uv run pkit friction check --all --json >")
    render = steps[_index(workflow, "Render the findings")]["run"].splitlines()
    script = 'uv run python scripts/friction_report_body.py "$RUNNER_TEMP/friction.json"'
    assert render == [
        f'{script} --json > "$RUNNER_TEMP/friction-report.json"',
        f'{script} >> "$GITHUB_STEP_SUMMARY"',
    ]
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
