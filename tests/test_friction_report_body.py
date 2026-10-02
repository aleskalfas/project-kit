"""`scripts/friction_report_body.py`: the whole-repository check's findings, to publish (#1266).

The script renders the document of the backbone's whole-repository friction
check (COR-050 point 6), `pkit friction check --all --json`, as one Markdown
body, and counts the findings that need an answer. It is a function of that
document, so the tests call it over a document the real backbone wrote for a
real history, or one shaped like it where the backbone cannot be made to report
a kind; the command itself runs as a subprocess, as the workflow runs it.

Held to: stale debt with what changed and since when; deferrals listed with
their reason and never counted; the other findings; both measures, never
counted; the same findings giving the same body; what the findings carry staying
inert text, a path that is no UTF-8 included; the body within its size, cut by
whole entries, the findings that need an answer last; and nothing rendered from
a document it cannot fully read.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from scripts import friction_report_body as report

from project_kit import friction_repository as fr
from tests.adopter_repo import HISTORY_EPOCH, Author, MakeAdopterRepo
from tests.friction_documents import T1, Timeline, document, friction_config, guide

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "friction_report_body.py"

ALICE = Author("Alice", "alice@example.com")
CAROL = Author("Carol", "carol@example.com")
REASON = "after the engine settles; ask @carol, see #12 and `</details>`"
LATER = "2026-11-01T00:00:00Z"


def _run(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    """The script as the workflow runs it."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _notes(**overrides: Any) -> str:
    values: dict[str, Any] = {"anchors": {"path": ["src/core/**"]}, "at": T1, "outcome": "updated"}
    values.update(overrides)
    return document("notes", **values)


def _history(timeline: Timeline) -> dict[str, str]:
    """`guide` stale (the CLI changed), `notes` deferred with a reason, one artefact
    unanchored, one accepted without anchors, and one path of the surface uncovered."""
    timeline.start(
        {
            "docs/guide.md": guide(),
            "docs/notes.md": _notes(),
            "docs/plain.md": "---\nid: plain\n---\n\nPlain.\n",
            "docs/why.md": document("why", unanchored_because="a person's part of the work"),
            "src/extra/tool.py": "TOOL = 1\n",
        },
        friction_config(surface=["src"]),
    )
    changed = timeline.commit(
        "change the CLI (#7)", {"src/cli/main.py": "print('2')\n"}, author=ALICE
    )
    timeline.commit("change the engine", {"src/core/engine.py": "ENGINE = 2\n"})
    deferred = timeline.commit(
        "defer the notes",
        {"docs/notes.md": _notes(deferred=[("path", "src/core/**", REASON)])},
        author=CAROL,
    )
    return {"changed": changed, "deferred": deferred}


def _check(root: Path) -> dict[str, Any]:
    """The real whole-repository check's document for `root`."""
    return json.loads(fr.render_json(fr.run_repository_check(root)))


def _day(days: int) -> str:
    return (HISTORY_EPOCH + timedelta(days=days)).date().isoformat()


def _document(**overrides: Any) -> dict[str, Any]:
    """A whole-repository document with nothing found, shaped as the backbone writes it."""
    base: dict[str, Any] = {
        "schema_version": 1,
        "check": "repository",
        "mode": "warning",
        "dormant": False,
        "failed": False,
        "head": {"commit": "0" * 40, "uncommitted_paths": 0},
        "history": {"shallow": False},
        "counts": {},
        "states": {"current": 0, "deferred": 0, "stale": 0, "unreachable": 0},
        "artefacts": [],
        "findings": [],
        "measures": {"accepted_unanchored": [], "unanchored": [], "uncovered_surface": []},
    }
    base.update(overrides)
    return base


def _finding(kind: str, location: str, message: str, **extra: Any) -> dict[str, Any]:
    return {
        "artefact": location,
        "location": location,
        "kind": kind,
        "anchor": extra.get("anchor"),
        "origin": extra.get("origin"),
        "message": message,
    }


def _section(body: str, title: str) -> str:
    return body.split(f"### {title}", 1)[1].split("###", 1)[0]


@pytest.fixture
def timeline(make_adopter_repo: MakeAdopterRepo) -> Timeline:
    return Timeline(make_adopter_repo())


# --- what needs an answer, and what the body says ------------------------------------------


def test_stale_debt_needs_an_answer_and_a_deferral_is_listed_with_its_reason(
    timeline: Timeline,
) -> None:
    shas = _history(timeline)
    made = report.publication(_check(timeline.adopter.root))

    assert made["schema_version"] == 1
    assert made["needs_answer"] == 1  # the stale guide; the deferral is an answer
    body = made["body"]
    assert body.startswith("**Needs an answer: 1 stale.**\n")
    stale = _section(body, "Stale")
    assert f"- `docs/guide.md` · `path:src/cli/**` · since `{_day(2)}`" in stale
    assert shas["changed"][:7] in stale and '"change the CLI (#7)" (Alice' in stale
    deferred = _section(body, "Deferred")
    assert f"- `docs/notes.md` · `path:src/core/**` · since `{_day(4)}`" in deferred
    assert "after the engine settles" in deferred and shas["deferred"][:7] in deferred


def test_with_only_deferrals_nothing_needs_an_answer_and_they_stay_listed(
    timeline: Timeline,
) -> None:
    _history(timeline)
    timeline.commit(
        "revalidate the guide",
        {"docs/guide.md": guide(at=LATER, because="the CLI still reads so")},
    )
    made = report.publication(_check(timeline.adopter.root))
    assert made["needs_answer"] == 0
    assert made["body"].startswith("**Nothing needs an answer.**\n")
    assert "### Stale" not in made["body"]
    assert "after the engine settles" in _section(made["body"], "Deferred")


def test_the_measures_are_rendered_and_never_counted(timeline: Timeline) -> None:
    _history(timeline)
    root = timeline.adopter.root
    measures = _section(report.publication(_check(root))["body"], "Measures")
    assert (
        "<summary>Unanchored artefacts: 1 (1 accepted with a reason, listed apart)</summary>"
        in measures
    )
    assert "- `docs/plain.md`" in measures
    assert "- `docs/why.md`: `a person's part of the work`" in measures
    assert "<summary>Uncovered surface: 1 path nothing anchors</summary>" in measures
    assert "- `src/extra/tool.py`" in measures

    # Answered, the debt goes; the measures stay, and are counted for nothing.
    timeline.commit(
        "revalidate both",
        {
            "docs/guide.md": guide(at=LATER, because="the CLI still reads so"),
            "docs/notes.md": _notes(at=LATER),
        },
    )
    answered = report.publication(_check(root))
    assert answered["needs_answer"] == 0
    assert answered["body"].startswith("**Nothing needs an answer.**\n")
    assert "### Stale" not in answered["body"] and "### Deferred" not in answered["body"]
    assert "- `src/extra/tool.py`" in answered["body"]


def test_other_findings_need_an_answer_and_left_out_is_reported_apart() -> None:
    document_ = _document(
        findings=[
            _finding(
                "dead-anchor",
                "docs/a.md",
                "matches no file",
                anchor={"kind": "path", "value": "gone/**"},
            ),
            _finding(
                "left-out",
                "docs/c.md",
                "`friction.exclude` now leaves out 1 file this anchor stood on",
                anchor={"kind": "path", "value": "src/**"},
            ),
        ]
    )
    made = report.publication(document_)
    assert made["needs_answer"] == 1
    assert made["body"].startswith("**Needs an answer: 1 other finding.**\n")
    other = _section(made["body"], "Other findings that need an answer")
    assert "- `docs/a.md` · `dead-anchor` · `path:gone/**`\n  `matches no file`" in other
    apart = _section(made["body"], "Reported, nothing owed")
    assert "- `docs/c.md` · `left-out` · `path:src/**`" in apart

    only_left_out = report.publication(_document(findings=[document_["findings"][1]]))
    assert only_left_out["needs_answer"] == 0
    assert only_left_out["body"].startswith("**Nothing needs an answer.**")


def test_both_things_that_do_not_read_are_told_as_the_check_tells_them() -> None:
    """Front matter that does not parse, and a revalidation point whose
    `friction.exclude` does not read: one kind, two messages, both under the
    section whose lead names both."""
    front = "front matter does not parse (line 3); its artefacts cannot be checked"
    exclude = '`friction.exclude` does not read at abc1234 "edit the config" (not a list)'
    made = report.publication(
        _document(
            findings=[
                _finding("unreadable", "docs/broken.md", front),
                _finding(
                    "unreadable",
                    ".pkit/project/config.yaml",
                    exclude,
                    origin={"commit": "a" * 40, "date": "2026-09-30T09:00:00+00:00"},
                ),
            ]
        )
    )
    assert made["needs_answer"] == 2
    other = _section(made["body"], "Other findings that need an answer")
    assert "a file's front matter, or `friction.exclude` at a revalidation point" in other
    assert f"- `docs/broken.md` · `unreadable`\n  `{front}`" in other
    assert "- `.pkit/project/config.yaml` · `unreadable` · since `2026-09-30`" in other
    assert 'does not read at abc1234 "edit the config"' in other


def test_a_dormant_check_needs_no_answer() -> None:
    made = report.publication(_document(dormant=True))
    assert made["needs_answer"] == 0
    assert made["body"].startswith("**Nothing needs an answer.**\n")
    assert "The check is dormant" in made["body"]


# --- how the body is made -----------------------------------------------------------------


def test_the_same_findings_render_the_same_body(timeline: Timeline) -> None:
    """No age, no run time, no HEAD: a later commit that changes no finding leaves it."""
    _history(timeline)
    root = timeline.adopter.root
    earlier = _check(root)
    timeline.commit("unrelated", {"README.md": "Hello.\n"})
    later = _check(root)
    assert later["head"]["commit"] != earlier["head"]["commit"]
    assert report.publication(later) == report.publication(earlier)


def test_an_over_broad_anchor_keeps_the_body_while_the_tracked_files_change(
    timeline: Timeline,
) -> None:
    """The check's message counts the tracked files, which most pushes change; the
    body tells the finding without the count."""
    timeline.start({"docs/guide.md": guide(anchors={"path": ["**"]})})
    root = timeline.adopter.root
    timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"})
    earlier = _check(root)
    timeline.commit("add a module", {"src/extra/tool.py": "TOOL = 1\n"})
    later = _check(root)

    def over_broad(check: dict[str, Any]) -> str:
        (finding,) = [f for f in check["findings"] if f["kind"] == "over-broad"]
        return finding["message"]

    assert over_broad(earlier) != over_broad(later)  # the count moved
    body = report.publication(later)["body"]
    assert body == report.publication(earlier)["body"]
    assert "- `docs/guide.md` · `over-broad` · `path:**`\n  matches most of the tracked" in body


def test_since_when_is_the_utc_day_the_checks_message_names() -> None:
    """An origin committed late in the evening west of Greenwich: the document's
    date is in the author's zone, the message names the UTC day, the body one day."""
    stale = _finding(
        "stale",
        "docs/guide.md",
        'changed after its revalidation point: first in aaaaaaa "x" (Alice, 2026-10-01)',
        anchor={"kind": "path", "value": "src/cli/**"},
        origin={"commit": "a" * 40, "date": "2026-09-30T23:30:00-05:00"},
    )
    body = report.publication(_document(findings=[stale]))["body"]
    assert "· since `2026-10-01`" in body and "2026-09-30" not in body


def test_what_the_findings_carry_stays_inert(timeline: Timeline) -> None:
    """A reason naming `@someone`, `#12` or a closing tag is set in a code span whose
    fence is longer than any run of backticks it holds."""
    _history(timeline)
    body = report.publication(_check(timeline.adopter.root))["body"]
    line = next(text for text in body.splitlines() if "after the engine settles" in text)
    span = line.strip()
    assert span.startswith("``") and span.endswith("``") and not span.startswith("```")
    assert "@carol" in span and "#12" in span and "`</details>`" in span
    # Outside code spans nothing the findings carry appears: no mention, no reference,
    # no date.
    prose = re.sub(r"(`+)(?:(?!\1).)+\1", "", body)
    assert "@carol" not in prose and "#12" not in prose and "#7" not in prose
    assert not re.search(r"\d{4}-\d{2}-\d{2}", prose)
    assert prose.count("<details>") == prose.count("</details>")


# --- a path that is no UTF-8 ---------------------------------------------------------------


def test_a_path_that_is_no_utf8_is_set_escaped() -> None:
    """The check decodes a path with `surrogateescape`; the body sets the byte escaped,
    and the command prints it."""
    document_ = _document(
        findings=[_finding("unreadable", "docs/caf\udce9.md", "front matter does not parse")],
        measures={
            "accepted_unanchored": [],
            "unanchored": ["docs/caf\udce9.md"],
            "uncovered_surface": [],
        },
    )
    body = report.publication(document_)["body"]
    assert body.count(r"`docs/caf\xe9.md`") == 2
    body.encode("utf-8")  # nothing left that cannot be written

    text = json.dumps(document_)
    plain = _run("-", stdin=text)
    assert plain.returncode == 0 and plain.stdout == body, plain.stderr
    as_json = _run("-", "--json", stdin=text)
    assert as_json.returncode == 0 and json.loads(as_json.stdout)["body"] == body


def test_a_tracked_path_that_is_no_utf8_through_the_real_check(timeline: Timeline) -> None:
    """A file in a place whose name holds the byte `\\xe9`, committed through git's
    index so that no file system has to hold the name."""
    timeline.start({"docs/guide.md": guide()})
    adopter = timeline.adopter
    blob = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=adopter.root,
        input=b"---\nid: cafe\n---\n\nPlain.\n",
        capture_output=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        [
            b"git",
            b"update-index",
            b"--add",
            b"--cacheinfo",
            b"100644," + blob + b",docs/caf\xe9.md",
        ],
        cwd=adopter.root,
        check=True,
    )
    adopter.git("commit", "-q", "-m", "a name that is no UTF-8")

    made = report.publication(_check(adopter.root))
    assert r"- `docs/caf\xe9.md`" in _section(made["body"], "Measures")
    made["body"].encode("utf-8")


# --- within a body's size ------------------------------------------------------------------


def _shown(body: str) -> list[str]:
    """The entries of `body`: each list line, with the line under it when it has one."""
    return re.findall(r"^- .*(?:\n  .*)?", body, flags=re.MULTILINE)


def _not_shown(body: str) -> int:
    return sum(int(n) for n in re.findall(r"^- … (\d+) not shown here", body, flags=re.MULTILINE))


def _stale(n: int, message: str = "changed after its revalidation point") -> dict[str, Any]:
    return _finding(
        "stale", f"docs/page_{n:04d}.md", message, anchor={"kind": "path", "value": "src/**"}
    )


def _deferred(n: int) -> dict[str, Any]:
    return _finding(
        "deferred",
        f"docs/later_{n:04d}.md",
        "deferred: after the engine settles",
        anchor={"kind": "path", "value": "src/**"},
    )


def test_the_measures_are_shortened_first_and_the_body_says_how_many_are_not_shown() -> None:
    surface = [f"src/generated/module_{n:05d}/a_rather_long_file_name.py" for n in range(3000)]
    findings = [_stale(n) for n in range(150)] + [_deferred(n) for n in range(150)]
    body = report.publication(
        _document(
            findings=findings,
            measures={"accepted_unanchored": [], "unanchored": [], "uncovered_surface": surface},
        )
    )["body"]
    assert len(body) <= report.BUDGET
    assert "<summary>Uncovered surface: 3000 paths nothing anchors</summary>" in body
    assert "- … 2900 not shown here: `pkit friction check --all` lists them all" in body
    assert "_Shortened to fit the body's size: 2900 entries are not shown." in body
    # Every finding is still there: only the measures gave way.
    assert all(f"`docs/page_{n:04d}.md`" in body for n in range(150))
    assert all(f"`docs/later_{n:04d}.md`" in body for n in range(150))


def test_the_findings_that_need_an_answer_are_shortened_last_and_never_split() -> None:
    """More than fits: the measures and the deferrals give way entirely before one
    stale finding does, every entry shown is whole, and no block is left open."""
    message = "changed after its revalidation point: " + "x" * 250
    findings = [_stale(n, message) for n in range(400)] + [_deferred(n) for n in range(40)]
    document_ = _document(
        findings=findings,
        measures={
            "accepted_unanchored": [{"location": "docs/why.md", "reason": "a person's part"}],
            "unanchored": [f"docs/plain_{n}.md" for n in range(40)],
            "uncovered_surface": [f"src/module_{n}.py" for n in range(40)],
        },
    )
    assert len(report.render(document_)) > report.BUDGET  # whole, it does not fit
    made = report.publication(document_)
    body = made["body"]
    assert len(body) <= report.BUDGET
    assert made["needs_answer"] == 400  # counted whole, however many are shown

    assert "docs/plain_" not in body and "src/module_" not in body and "docs/why.md" not in body
    assert "docs/later_" not in body
    stale = _section(body, "Stale")
    assert stale.count("`docs/page_") == 100 and "- … 300 not shown here" in stale
    for entry in _shown(body):
        if "`docs/page_" in entry:
            assert entry.endswith(f"\n  `{message}`")  # the finding and what is said of it
    assert body.count("<details>") == body.count("</details>") == 2
    dropped = 300 + 40 + 40 + 1 + 40
    assert _not_shown(body) == dropped
    assert f"_Shortened to fit the body's size: {dropped} entries are not shown." in body


def test_one_entry_larger_than_the_budget_is_left_out_whole() -> None:
    vast = _finding(
        "deferred",
        "docs/notes.md",
        "deferred: " + "y" * (report.BUDGET + 1),
        anchor={"kind": "path", "value": "src/**"},
    )
    body = report.publication(_document(findings=[_stale(1), vast]))["body"]
    assert len(body) <= report.BUDGET
    assert "`docs/page_0001.md`" in body and "yyyy" not in body
    assert "_Shortened to fit the body's size: 1 entry is not shown." in body


# --- the command ---------------------------------------------------------------------------


def test_the_command_prints_the_body_or_the_publication(tmp_path: Path) -> None:
    document_ = _document(findings=[_stale(1)])
    path = tmp_path / "friction.json"
    path.write_text(json.dumps(document_), encoding="utf-8")
    made = report.publication(document_)

    plain = _run(str(path))
    assert plain.returncode == 0 and plain.stdout == made["body"]
    as_json = _run(str(path), "--json")
    assert as_json.returncode == 0 and json.loads(as_json.stdout) == made
    piped = _run("-", stdin=json.dumps(document_))
    assert piped.returncode == 0 and piped.stdout == made["body"]


def _without(key: str) -> dict[str, Any]:
    document_ = _document()
    del document_[key]
    return document_


@pytest.mark.parametrize(
    ("text", "says"),
    [
        ("not json", "holds no JSON document"),
        ("[]", "holds no document of `pkit friction check --all --json`"),
        (
            json.dumps({**_document(), "check": "change"}),
            "holds no document of `pkit friction check --all --json`",
        ),
        (json.dumps({**_document(), "schema_version": 2}), "schema_version 2; this script reads 1"),
        (json.dumps(_without("schema_version")), "schema_version None; this script reads 1"),
        (json.dumps(_without("findings")), "gives no list of findings"),
        (json.dumps({**_document(), "findings": [{"location": "x"}]}), "gives no list of findings"),
        (json.dumps(_without("measures")), "gives no measures"),
    ],
)
def test_a_document_it_cannot_fully_read_is_refused_and_nothing_is_rendered(
    tmp_path: Path, text: str, says: str
) -> None:
    path = tmp_path / "friction.json"
    path.write_text(text, encoding="utf-8")
    proc = _run(str(path), "--json")
    assert proc.returncode == 1 and proc.stdout == ""
    assert says in proc.stderr and "nothing to render" in proc.stderr


def test_a_file_that_is_not_there_is_refused(tmp_path: Path) -> None:
    proc = _run(str(tmp_path / "missing.json"))
    assert proc.returncode == 1 and proc.stdout == ""
    assert "cannot be read" in proc.stderr and "nothing to render" in proc.stderr
