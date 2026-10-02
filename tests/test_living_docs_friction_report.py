"""living-docs' `friction-report`: the whole-repository check's findings, to publish (#1266).

The command reads the backbone's whole-repository friction check (COR-050 point
6) — through `pkit friction check --all --json`, or from a file that document was
written to — and prints one Markdown body and, with `--json`, how many findings
are outstanding. Every test runs the script as a subprocess under this
interpreter, as the dispatcher runs it, over a document the real backbone wrote
for a real history, or one shaped like it where the backbone cannot be made to
report a kind; the `pkit` it reads through is the real CLI (`pkit_on_path`).

Held to: stale debt with what changed and since when, deferrals with their
reason and since when, the other findings, both measures; outstanding counting
every finding but `left-out`, never the measures; the same findings giving the
same body; what the findings carry staying inert text; the body fitting a
tracker's size; and exit 0 whatever the check found, 1 only without a document.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import friction_repository as fr
from tests.adopter_repo import HISTORY_EPOCH, Author, MakeAdopterRepo
from tests.friction_documents import T1, Timeline, document, friction_config, guide

REPO = Path(__file__).resolve().parent.parent
CAPABILITY = REPO / ".pkit" / "capabilities" / "living-docs"
SCRIPT = CAPABILITY / "scripts" / "friction-report.py"

ALICE = Author("Alice", "alice@example.com")
CAROL = Author("Carol", "carol@example.com")
REASON = "after the engine settles; ask @carol, see #12 and `</details>`"


def _render(
    root: Path, *args: str, report: dict[str, Any] | str | None = None
) -> subprocess.CompletedProcess[str]:
    """`pkit living-docs friction-report` as the dispatcher runs it, from `root`; a
    `report` is written to a file outside it, as a pipeline's temporary folder holds it."""
    with tempfile.TemporaryDirectory() as folder:
        argv = [sys.executable, str(SCRIPT), *args]
        if report is not None:
            path = Path(folder) / "friction.json"
            text = report if isinstance(report, str) else json.dumps(report)
            path.write_text(text, encoding="utf-8")
            argv += ["--report", str(path)]
        return subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False)


def _publication(root: Path, report: dict[str, Any]) -> dict[str, Any]:
    proc = _render(root, "--json", report=report)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


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


@pytest.fixture
def timeline(make_adopter_repo: MakeAdopterRepo) -> Timeline:
    return Timeline(make_adopter_repo())


# --- the command -------------------------------------------------------------------------


def test_the_package_declares_the_command_as_a_query() -> None:
    package = YAML(typ="safe").load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    entry = package["commands"]["friction-report"]
    assert entry["script"] == "scripts/friction-report.py"
    assert entry["query-contract"] is True
    assert "reads" not in entry  # no point's filler: nothing the backbone runs it for
    assert SCRIPT.stat().st_mode & 0o111, "the dispatcher runs the script directly"


# --- what the body says --------------------------------------------------------------------


def test_stale_and_deferred_debt_with_what_changed_since_when_and_the_reason(
    timeline: Timeline,
) -> None:
    shas = _history(timeline)
    root = timeline.adopter.root
    publication = _publication(root, _check(root))

    assert publication["schema_version"] == 1
    assert publication["outstanding"] == 2
    body = publication["body"]
    assert body.startswith("**Outstanding: 1 stale, 1 deferred.**\n")
    stale = body.split("### Stale", 1)[1].split("###", 1)[0]
    assert f"- `docs/guide.md` · `path:src/cli/**` · since {_day(2)}" in stale
    assert shas["changed"][:7] in stale and '"change the CLI (#7)" (Alice' in stale
    deferred = body.split("### Deferred", 1)[1].split("###", 1)[0]
    assert f"- `docs/notes.md` · `path:src/core/**` · since {_day(4)}" in deferred
    assert "after the engine settles" in deferred and shas["deferred"][:7] in deferred


def test_the_measures_are_rendered_and_never_outstanding(timeline: Timeline) -> None:
    _history(timeline)
    root = timeline.adopter.root
    body = _publication(root, _check(root))["body"]
    measures = body.split("### Measures", 1)[1]
    assert (
        "<summary>Unanchored artefacts: 1 (1 accepted with a reason, listed apart)</summary>"
        in (measures)
    )
    assert "- `docs/plain.md`" in measures
    assert "- `docs/why.md`: `a person's part of the work`" in measures
    assert "<summary>Uncovered surface: 1 path nothing anchors</summary>" in measures
    assert "- `src/extra/tool.py`" in measures

    # Answered, the debt goes; the measures stay, and hold nothing open.
    timeline.commit(
        "revalidate both",
        {
            "docs/guide.md": guide(at="2026-11-01T00:00:00Z", because="the CLI still reads so"),
            "docs/notes.md": _notes(at="2026-11-01T00:00:00Z"),
        },
    )
    answered = _publication(root, _check(root))
    assert answered["outstanding"] == 0
    assert answered["body"].startswith("**Nothing outstanding.**\n")
    assert "### Stale" not in answered["body"] and "### Deferred" not in answered["body"]
    assert "- `src/extra/tool.py`" in answered["body"]


def test_the_check_is_read_through_pkit_when_no_file_is_given(
    timeline: Timeline, pkit_on_path: Path
) -> None:
    _history(timeline)
    root = timeline.adopter.root
    through_pkit = _render(root, "--json")
    assert through_pkit.returncode == 0, through_pkit.stderr
    assert json.loads(through_pkit.stdout) == _publication(root, _check(root))
    plain = _render(root)
    assert plain.returncode == 0 and plain.stdout == json.loads(through_pkit.stdout)["body"]


def test_other_findings_count_and_left_out_is_reported_apart_never_outstanding(
    tmp_path: Path,
) -> None:
    report = _document(
        findings=[
            _finding(
                "dead-anchor",
                "docs/a.md",
                "matches no file",
                anchor={"kind": "path", "value": "gone/**"},
            ),
            _finding(
                "over-broad",
                "docs/b.md",
                "matches 9 of 10 tracked files",
                anchor={"kind": "path", "value": "**"},
            ),
            _finding(
                "left-out",
                "docs/c.md",
                "`friction.exclude` now leaves out 1 file this anchor stood on",
                anchor={"kind": "path", "value": "src/**"},
            ),
        ]
    )
    publication = _publication(tmp_path, report)
    assert publication["outstanding"] == 2
    body = publication["body"]
    assert body.startswith("**Outstanding: 2 other findings.**\n")
    other = body.split("### Other findings", 1)[1].split("###", 1)[0]
    assert "- `docs/a.md` · `dead-anchor` · `path:gone/**`" in other
    assert "- `docs/b.md` · `over-broad` · `path:**`" in other
    apart = body.split("### Reported, nothing owed", 1)[1].split("###", 1)[0]
    assert "- `docs/c.md` · `left-out` · `path:src/**`" in apart

    only_left_out = _publication(tmp_path, _document(findings=[report["findings"][2]]))
    assert only_left_out["outstanding"] == 0
    assert only_left_out["body"].startswith("**Nothing outstanding.**")


def test_a_dormant_check_has_nothing_outstanding(tmp_path: Path) -> None:
    publication = _publication(tmp_path, _document(dormant=True))
    assert publication["outstanding"] == 0
    assert "The check is dormant" in publication["body"]


# --- how the body is made -----------------------------------------------------------------


def test_the_same_findings_render_the_same_body(timeline: Timeline) -> None:
    """No age, no run time, no HEAD: a later commit that changes no finding leaves it."""
    _history(timeline)
    root = timeline.adopter.root
    earlier = _check(root)
    timeline.commit("unrelated", {"README.md": "Hello.\n"})
    later = _check(root)
    assert later["head"]["commit"] != earlier["head"]["commit"]
    assert _publication(root, later) == _publication(root, earlier)


def test_what_the_findings_carry_stays_inert(timeline: Timeline) -> None:
    """A reason naming `@someone`, `#12` or a closing tag is set in a code span whose
    fence is longer than any run of backticks it holds."""
    _history(timeline)
    root = timeline.adopter.root
    body = _publication(root, _check(root))["body"]
    line = next(text for text in body.splitlines() if "after the engine settles" in text)
    span = line.strip()
    assert span.startswith("``") and span.endswith("``") and not span.startswith("```")
    assert "@carol" in span and "#12" in span and "`</details>`" in span
    # Outside code spans nothing the findings carry appears: no mention, no reference.
    prose = re.sub(r"(`+)(?:(?!\1).)+\1", "", body)
    assert "@carol" not in prose and "#12" not in prose and "#7" not in prose
    assert prose.count("<details>") == prose.count("</details>")


def test_the_body_fits_a_trackers_size(tmp_path: Path) -> None:
    surface = [f"src/generated/module_{n:05d}/a_rather_long_file_name.py" for n in range(3000)]
    report = _document(
        measures={"accepted_unanchored": [], "unanchored": [], "uncovered_surface": surface}
    )
    body = _publication(tmp_path, report)["body"]
    assert len(body) <= 60_000
    assert "<summary>Uncovered surface: 3000 paths nothing anchors</summary>" in body
    assert re.search(r"- … and \d+ more: `pkit friction check --all` lists them all", body)


# --- what it refuses -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("report", "says"),
    [
        ("not json", "holds no document of `pkit friction check --all --json`"),
        ({"findings": []}, "holds no document of `pkit friction check --all --json`"),
        (
            {**_document(), "schema_version": 2},
            "answered schema_version 2; this capability reads 1",
        ),
    ],
)
def test_no_document_to_render_exits_1_saying_why(
    tmp_path: Path, report: dict[str, Any] | str, says: str
) -> None:
    proc = _render(tmp_path, report=report)
    assert proc.returncode == 1 and proc.stdout == ""
    assert says in proc.stderr and "nothing to render" in proc.stderr


def test_a_document_without_its_version_reads_as_version_1(tmp_path: Path) -> None:
    report = _document()
    del report["schema_version"]
    assert _publication(tmp_path, report)["outstanding"] == 0
