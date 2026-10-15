"""software-analysis: a planned record's commit off the default branch (#1448).

`pkit analysis check-pointers` held to software-analysis DEC-001 point 6 — a
planned record names where the design it reviewed stood, and a commit of this
repository it names is one the default branch holds — and to the maintainer's
decision of 11 October: it fails only on a record the change adds, the one
place a pointer can still be fixed. A commit in a record the merge-base holds
is reported, and one a shallow clone cannot place is unknown; neither fails.
The commits are placed on the default branch alone (COR-054 point 5); the base
says only which records are new (point 3). It reads history beyond the working
tree, so it is a command of its own and not a validator (COR-055 points 1 and
2).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.friction_check import BASE_ENV
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo, sign_nothing
from tests.analysis_repo import (
    CAPABILITY,
    CONFIG,
    MAIN,
    RECORDS,
    SA,
    installed,
    load,
    load_lib,
    prepare,
)
from tests.analysis_repo import run_script as _run

POINTERS = SA / "scripts" / "check-pointers.py"

#: The design a planned record reviewed, and the records of these repositories.
DESIGN = "tech-docs/design.md"
OLD = f"{RECORDS}/2026-01-01-old.md"
NEW = f"{RECORDS}/2026-02-01-new.md"

#: A full commit id no repository here holds.
NOWHERE = "1234567890abcdef1234567890abcdef12345678"


def record(*sources: dict[str, str], trigger: str = "planned") -> str:
    """A revalidation record of `trigger` naming `sources` in `reviewed-against`."""
    lines = ["---", "change: '#1'", f"trigger: {trigger}", "reviewed-against:"]
    for source in sources:
        lines.append(f"  - title: {source['title']}")
        if "url" in source:
            lines.append(f"    url: {source['url']}")
        lines.append(f'    version: "{source["version"]}"')
    lines += ["date: 2026-02-01", "by: pkit-test", "outcomes:", "  UC-001: holds", "---", ""]
    return "\n".join(lines) + "# 2026-02-01 — Planned\n"


def _designed(repo: AdopterRepo) -> None:
    """`prepare`, then on main: a design landed (tag `landed`); the branch `design`
    reviewing it again, squash-merged; and a planned record naming the branch's commit,
    off main. The branch `topic` leaves main there."""
    prepare(repo)
    repo.commit("the design", {DESIGN: "first\n"})
    repo.git("tag", "landed")
    repo.checkout("design", create=True)
    repo.commit("the design, reviewed", {DESIGN: "second\n"})
    repo.checkout(MAIN)
    repo.squash_merge("design", "the design, reviewed (#2)")
    off = {"title": "the design's branch", "version": sha(repo, "design")}
    repo.commit("an old record", {OLD: record(off)})
    repo.checkout("topic", create=True)


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


@pytest.fixture
def designed(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The project with a design landed, a branch's review of it squash-merged, and an
    old record naming the branch's commit (`_designed`), on `topic`."""
    return installed(make_adopter_repo, monkeypatch, then=_designed)


def sha(repo: AdopterRepo, rev: str) -> str:
    return repo.git("rev-parse", f"{rev}^{{commit}}").stdout.strip()


def pointers(repo: AdopterRepo, *args: str) -> subprocess.CompletedProcess[str]:
    """`pkit analysis check-pointers …`, run as the dispatcher runs it."""
    return _run(repo, POINTERS, *args)


def document(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return json.loads(completed.stdout)


def pointer(
    rel: str, title: str, commit: str, *, added: bool, placement: str, source: int = 0
) -> dict[str, Any]:
    return {
        "record": rel,
        "source": source,
        "title": title,
        "commit": commit,
        "added": added,
        "placement": placement,
    }


def old_report(repo: AdopterRepo) -> dict[str, str]:
    """The report on the old record: its branch commit, which the merge-base holds."""
    return {
        "severity": "report",
        "location": f"{OLD}:/reviewed-against/0/version",
        "message": (
            f'"the design\'s branch" names {sha(repo, "design")[:12]}, which the default '
            f"branch, {MAIN}, does not hold. This change does not add the record: {MAIN} held it "
            f"where this branch left it, at {sha(repo, MAIN)[:12]}. A record is never rewritten, "
            "so this is reported, never failed (DEC-001 point 6)"
        ),
    }


# --- where it is registered -------------------------------------------------------------------


def test_it_is_a_query_command_and_not_a_validator() -> None:
    package = load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    leaf = package["commands"]["check-pointers"]
    assert (leaf["script"], leaf["query-contract"]) == ("scripts/check-pointers.py", True)
    assert package["validators"] == {"artefacts": {"command": "validate"}}
    result = CliRunner().invoke(main, ["analysis", "--help"])
    assert result.exit_code == 0, result.output
    assert "check-pointers " in result.output


# --- nothing to place -------------------------------------------------------------------------


def test_with_no_planned_record_it_reads_nothing_and_says_so(project: AdopterRepo) -> None:
    """No base is read — a base that names nothing passes — and a record of another
    trigger is not read, whatever it names."""
    completed = pointers(project, "--base", "nowhere", "--json")
    assert completed.returncode == 0, completed.stderr
    nothing = "pointers: no planned revalidation record here; nothing to place, no base read."
    assert document(completed) == {
        "schema_version": 1,
        "default_branch": None,
        "base": None,
        "summary": [nothing],
        "findings": [],
        "pointers": [],
    }
    off = {"title": "a design", "version": NOWHERE}
    project.write({NEW: record(off, trigger="drift")})
    completed = pointers(project, "--base", "nowhere")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [nothing]


def test_a_records_folder_the_backbone_skips_is_said_to_hold_nothing(
    project: AdopterRepo,
) -> None:
    """A project place equal to the records' folder oversteps its bounds (COR-050 point
    1), so the backbone skips it: no record is read, and the summary says why rather
    than show none as if there were none."""
    branch_commit = {"title": "a design", "version": NOWHERE}
    project.write(
        {
            CONFIG: f"docs:\n  internal: tech-docs\nfriction:\n  places: [{RECORDS}]\n",
            NEW: record(branch_commit),
        }
    )
    completed = pointers(project, "--base", "nowhere")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "pointers: the records' folder holds nothing — the backbone skipped it (overlap); "
        "`pkit validate` says why; nothing to place, no base read."
    ]


def test_this_change_and_a_source_with_a_url_are_not_placed(project: AdopterRepo) -> None:
    """`this change` names the commit the record lands in, found from the history; a
    source with a `url` lies outside this repository. Neither is placed, so a record
    naming nothing else reads no base."""
    sources = (
        {"title": "this design", "version": "this change"},
        {"title": "#7's body", "url": "https://tracker.example/7", "version": NOWHERE},
    )
    project.write({NEW: record(*sources)})
    completed = pointers(project, "--base", "nowhere")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "pointers: 1 planned record here, naming no commit of this repository; nothing to "
        "place, no base read.",
        "pointers: not placed: 1 source naming `this change` and 1 source outside this repository.",
    ]
    # A source in this repository of neither form — an abbreviated id — is counted, not
    # placed: validation fails its form.
    abbreviated = {"title": "a design", "version": NOWHERE[:12]}
    project.write({NEW: record(*sources, abbreviated)})
    completed = pointers(project, "--base", "nowhere")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines()[1] == (
        "pointers: not placed: 1 source naming `this change`, 1 source outside this repository "
        "and 1 source naming neither a commit's full id nor `this change` (`pkit analysis "
        "validate` says why)."
    )


# --- where each commit sits (DEC-001 point 6) -------------------------------------------------


def test_a_commit_the_default_branch_holds_passes(designed: AdopterRepo) -> None:
    """A record the change adds, uncommitted, naming a commit main holds, `this change`
    and a source outside: the commit is held. The old record's branch commit is
    reported, never failed: the merge-base holds the record."""
    landed = sha(designed, "landed")
    sources = (
        {"title": "the design", "version": landed},
        {"title": "this design", "version": "this change"},
        {"title": "#7's body", "url": "https://tracker.example/7", "version": NOWHERE},
    )
    designed.write({NEW: record(*sources)})
    completed = pointers(designed, "--json")
    assert completed.returncode == 0, completed.stderr
    answer = document(completed)
    tip = sha(designed, MAIN)
    assert answer["default_branch"] == {"name": MAIN, "ref": MAIN, "commit": tip}
    assert answer["base"] == {"ref": MAIN, "tip": tip, "commit": tip}
    assert answer["pointers"] == [
        pointer(
            OLD, "the design's branch", sha(designed, "design"), added=False, placement="not-held"
        ),
        pointer(NEW, "the design", landed, added=True, placement="held"),
    ]
    assert answer["findings"] == [old_report(designed)]
    assert answer["summary"] == [
        f"pointers: 2 commits named by 2 planned records, placed on {MAIN} ({tip[:12]}): 1 held, "
        "1 not held, 0 unknown.",
        f"pointers: this change adds 1 of those records, read against {MAIN}, which this branch "
        f"left at {tip[:12]}.",
        "pointers: not placed: 1 source naming `this change` and 1 source outside this repository.",
    ]


def test_a_branch_commit_in_a_record_the_change_adds_fails(designed: AdopterRepo) -> None:
    """The usual slip: the record names the design branch's commit, which the squash
    merge left off main. It fails, naming the record and the source — uncommitted, and
    committed on the branch alone."""
    branch = sha(designed, "design")
    designed.write({NEW: record({"title": "the design's review", "version": branch})})
    completed = pointers(designed, "--json")
    assert completed.returncode == 1, completed.stderr
    location = f"{NEW}:/reviewed-against/0/version"
    error = {
        "severity": "error",
        "location": location,
        "message": (
            f'"the design\'s review" names {branch[:12]}, which the default branch, {MAIN}, '
            "does not hold: a squash merge leaves a branch's commits off it, so the record "
            f"could not lead back to the design. Name the commit where the design landed on "
            f"{MAIN}, or `this change` when the design lands with this record (DEC-001 point 6)"
        ),
    }
    answer = document(completed)
    assert answer["findings"] == [old_report(designed), error]
    assert answer["pointers"][1] == pointer(
        NEW, "the design's review", branch, added=True, placement="not-held"
    )
    designed.commit("a new record")
    read_view = pointers(designed)
    assert read_view.returncode == 1
    assert f"  error  {location}\n" in read_view.stdout


def test_a_commit_missing_from_a_full_clone_fails(designed: AdopterRepo) -> None:
    """A full clone holds every commit of the default branch, so a commit it does not
    hold is not on it."""
    designed.write({NEW: record({"title": "a lost design", "version": NOWHERE})})
    completed = pointers(designed, "--json")
    assert completed.returncode == 1, completed.stderr
    error = document(completed)["findings"][1]
    assert error["severity"] == "error"
    assert error["message"].startswith(
        f'"a lost design" names {NOWHERE[:12]}, which the default branch, {MAIN}, does not '
        "hold, and this clone, which holds all of that branch's history, holds no such commit: "
    )


def test_a_commit_a_shallow_clone_cannot_place_is_unknown(
    designed: AdopterRepo, tmp_path: Path
) -> None:
    """A clone one commit deep holds main's tip and the design branch's, and nothing
    before: a commit it lacks may lie beyond its cut, and so may the branch's, which
    main's history in it does not reach. Each is unknown, and none fails; the tip is
    held."""
    landed, branch, tip = sha(designed, "landed"), sha(designed, "design"), sha(designed, MAIN)
    shallow = tmp_path / "shallow"
    source = f"file://{designed.root}"
    designed.git("clone", "-q", "--depth", "1", "--no-single-branch", source, str(shallow))
    clone = AdopterRepo(shallow, source_kit=designed.source_kit)
    sign_nothing(shallow)
    clone.checkout("mine", create=True)
    sources = (
        {"title": "the design", "version": landed},
        {"title": "the design's review", "version": branch},
        {"title": "the old record's commit", "version": tip},
    )
    clone.write({NEW: record(*sources)})
    completed = pointers(clone, "--json")
    assert completed.returncode == 0, completed.stderr
    answer = document(completed)
    assert answer["default_branch"]["ref"] == f"origin/{MAIN}"
    assert [(p["record"], p["commit"], p["placement"]) for p in answer["pointers"]] == [
        (OLD, branch, "unknown"),
        (NEW, landed, "unknown"),
        (NEW, branch, "unknown"),
        (NEW, tip, "held"),
    ]
    unknown = answer["findings"][1]
    assert unknown == {
        "severity": "report",
        "location": f"{NEW}:/reviewed-against/0/version",
        "message": (
            f'"the design" names {landed[:12]}, which cannot be placed: this clone is shallow, '
            f"and its history of origin/{MAIN} stops short, so the commit may lie beyond it. "
            "Unknown, never a failure, since the pointers are provenance (DEC-001 point 6); "
            "`git fetch --unshallow` reads the whole history"
        ),
    }


def test_a_shallow_clone_cut_off_the_default_branch_places_as_a_full_one(
    designed: AdopterRepo, tmp_path: Path
) -> None:
    """A full clone that fetched one branch a commit deep is shallow, but its history of
    main is whole: a commit main's history does not reach is not held, never unknown.
    The one way of placing a commit, `place`, which the stamp reuses."""
    full = tmp_path / "full"
    designed.git("clone", "-q", f"file://{designed.root}", str(full))
    designed.checkout("side", create=True)
    side = designed.commit("side, one", {"side.txt": "one\n"})
    designed.commit("side, two", {"side.txt": "two\n"})
    fetched = ["git", "fetch", "-q", "--depth", "1", "origin", "side"]
    subprocess.run(fetched, cwd=full, check=True, capture_output=True)
    (pointers_lib,) = load_lib("pointers")
    shallow = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"], cwd=full, capture_output=True, text=True
    )
    assert shallow.stdout.strip() == "true"
    tip = sha(designed, MAIN)
    assert pointers_lib.place(full, sha(designed, "landed"), tip) == "held"
    assert pointers_lib.place(full, sha(designed, "design"), tip) == "not-held"
    assert pointers_lib.place(full, side, tip) == "not-held"
    assert pointers_lib.place(full, NOWHERE, tip) == "not-held"


def test_a_partial_clone_fetches_nothing(designed: AdopterRepo, tmp_path: Path) -> None:
    """A clone without trees holds every commit, so it places each, and asks no remote
    for a tree it lacks: when the merge-base's is one, it fails, saying so, rather than
    fetch it."""
    designed.git("config", "uploadpack.allowFilter", "true")
    treeless = tmp_path / "treeless"
    source = f"file://{designed.root}"
    designed.git("clone", "-q", "--filter=tree:0", "--no-single-branch", source, str(treeless))
    clone = AdopterRepo(treeless, source_kit=designed.source_kit)
    sign_nothing(treeless)
    clone.checkout("mine", create=True)
    clone.write({NEW: record({"title": "the design", "version": sha(designed, "landed")})})
    placed = pointers(clone, "--json")
    assert placed.returncode == 0, placed.stderr
    assert [p["placement"] for p in document(placed)["pointers"]] == ["not-held", "held"]
    # Against the design branch, the merge-base is the commit the design landed in, whose
    # tree the clone never fetched.
    fork = sha(designed, "landed")
    completed = pointers(clone, "--base", "origin/design")
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr.startswith(
        f"error: whether origin/design held {OLD} where this branch left it, at {fork[:12]}, "
        "could not be read from this clone: "
    )
    assert completed.stderr.rstrip().endswith(
        "Nothing is fetched here, so a partial clone must hold that commit's tree"
    )


# --- the default branch and the base (COR-054) ------------------------------------------------


def test_the_base_says_only_which_records_the_change_adds(
    designed: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A base that holds the record makes it old: reported, never failed. A base that
    holds the branch's commit leaves it off the default branch, where every commit is
    placed. `$PKIT_CHECK_BASE` names the base as `--base` does."""
    branch = sha(designed, "design")
    designed.commit("a new record", {NEW: record({"title": "the review", "version": branch})})
    held = pointers(designed, "--base", "topic", "--json")
    assert held.returncode == 0, held.stderr
    assert [p["added"] for p in document(held)["pointers"]] == [False, False]
    assert [f["severity"] for f in document(held)["findings"]] == ["report", "report"]

    on_base = pointers(designed, "--base", "design", "--json")
    assert on_base.returncode == 1, on_base.stderr
    answer = document(on_base)
    assert answer["base"] == {
        "ref": "design",
        "tip": branch,
        "commit": sha(designed, "landed"),
    }
    assert answer["default_branch"]["commit"] == sha(designed, MAIN)
    assert [(p["added"], p["placement"]) for p in answer["pointers"]] == [
        (True, "not-held"),
        (True, "not-held"),
    ]

    monkeypatch.setenv(BASE_ENV, "topic")
    named = pointers(designed, "--json")
    assert named.returncode == 0, named.stderr
    assert document(named)["base"]["ref"] == "topic"


def test_no_default_branch_resolved_fails_and_says_why(designed: AdopterRepo) -> None:
    """A declared default branch that resolves nowhere: no commit can be placed, so it
    fails with the backbone's reason, whatever the base."""
    designed.write(
        {
            NEW: record({"title": "the design", "version": sha(designed, "landed")}),
            CONFIG: "docs:\n  internal: tech-docs\nrepository:\n  default-branch: trunk\n",
        }
    )
    completed = pointers(designed, "--base", MAIN)
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "error: the default branch 'trunk' resolves to no commit here" in completed.stderr


def test_a_base_it_cannot_compare_with_fails(designed: AdopterRepo) -> None:
    designed.write({NEW: record({"title": "the design", "version": sha(designed, "landed")})})
    completed = pointers(designed, "--base", "nowhere")
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr.startswith("error: ")
    assert "nowhere" in completed.stderr
