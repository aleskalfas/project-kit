"""Tests for the whole-repository friction check, `pkit friction check --all` (Task #991, COR-050).

Every test stands up a real adopter repository (`make_adopter_repo`) and lays
down real history — dated commits by named authors, renames, a squash merge,
merge commits, a shallow clone — before running the check at HEAD. The
documents come from `tests.friction_documents`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import friction_check as fc
from project_kit import friction_history as fh
from project_kit import friction_report as frep
from project_kit import friction_repository as fr
from project_kit.cli import main
from project_kit.friction_discovery import Anchor
from tests.adopter_repo import HISTORY_EPOCH, Author, GitRepo, MakeAdopterRepo
from tests.friction_documents import (
    CONFIG,
    T1,
    T2,
    Timeline,
    document,
    friction_config,
    guide,
)

ALICE = Author("Alice", "alice@example.com")
BOB = Author("Bob", "bob@example.com")

# A fixed "now" for ages in the human view, well after every scripted commit.
NOW = HISTORY_EPOCH + timedelta(days=100)

CLI = Anchor("path", "src/cli/**")


@pytest.fixture
def timeline(make_adopter_repo: MakeAdopterRepo) -> Timeline:
    return Timeline(make_adopter_repo())


def _run(timeline: Timeline, **kwargs: Any) -> fr.RepositoryCheck:
    return fr.run_repository_check(timeline.adopter.root, **kwargs)


def _summary(result: fr.RepositoryCheck) -> list[tuple[str, str | None, str | None, str | None]]:
    """(kind, location, anchor, origin commit) per finding, in report order."""
    return [
        (
            f.kind.value,
            f.location,
            None if f.anchor is None else f"{f.anchor.kind}:{f.anchor.value}",
            None if f.origin is None else f.origin.sha,
        )
        for f in result.findings
    ]


def _point(result: fr.RepositoryCheck, location: str = "docs/guide.md") -> str | None:
    (report,) = [r for r in result.artefact_reports if r.location == location]
    return None if report.revalidation_point is None else report.revalidation_point.sha


def _cli(*args: str) -> Any:
    return CliRunner().invoke(main, ["friction", "check", "--all", *args])


# --- the revalidation point ---------------------------------------------------------


def test_the_revalidation_point_follows_a_rename_and_a_squash_merge(timeline: Timeline) -> None:
    repo = timeline.adopter
    timeline.start({"notes/guide.md": guide()}, friction_config(places=("docs", "notes")))
    timeline.rename("notes/guide.md", "docs/guide.md")
    repo.checkout("topic", create=True)
    timeline.commit(
        "topic: revalidate the moved guide",
        {"docs/guide.md": guide(at=T2, because="checked after the move")},
    )
    timeline.commit("topic: an extra page", {"docs/extra.md": "Extra.\n"})
    repo.checkout("main")
    squash = timeline.squash_merge("topic")
    changed = timeline.commit(
        "change the CLI", {"src/cli/main.py": "print('cli v2')\n"}, author=ALICE
    )

    result = _run(timeline)
    assert _point(result) == squash
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", changed)]
    (finding,) = result.findings
    assert finding.origin is not None and finding.origin.author == "Alice"
    assert f'first in {changed[:12]} "change the CLI"' in finding.message
    assert result.artefact_reports[0].state is fr.ArtefactState.STALE


def test_a_move_after_the_revalidation_point_is_stale(timeline: Timeline) -> None:
    base = timeline.start({"notes/guide.md": guide()}, friction_config(places=("docs", "notes")))
    moved = timeline.rename("notes/guide.md", "docs/guide.md")

    result = _run(timeline)
    assert _point(result) == base
    assert _summary(result) == [("stale", "docs/guide.md", None, moved)]
    assert "moved here from notes/guide.md" in result.findings[0].message


def test_a_move_revalidated_in_the_same_change_is_answered(timeline: Timeline) -> None:
    timeline.start({"notes/guide.md": guide()}, friction_config(places=("docs", "notes")))
    # A delete and an add git pairs as a rename: the content is nearly the same.
    moved = timeline.commit(
        "move and revalidate",
        {"notes/guide.md": None, "docs/guide.md": guide(at=T2, because="moved")},
    )

    result = _run(timeline)
    assert _point(result) == moved
    assert _summary(result) == []


def test_an_artefact_without_at_has_the_commit_that_introduced_its_block(
    timeline: Timeline,
) -> None:
    timeline.start({"docs/guide.md": "---\nid: guide\n---\n\nBody.\n"})
    timeline.commit("change the CLI before the block", {"src/cli/main.py": "print('before')\n"})
    introduced = timeline.commit(
        "anchor the guide", {"docs/guide.md": document("guide", anchors={"path": ["src/cli/**"]})}
    )
    result = _run(timeline)
    assert _point(result) == introduced
    assert result.artefact_reports[0].state is fr.ArtefactState.CURRENT

    after = timeline.commit("change the CLI after", {"src/cli/main.py": "print('after')\n"})
    assert _summary(_run(timeline)) == [("stale", "docs/guide.md", "path:src/cli/**", after)]


def test_a_reformatted_marker_does_not_move_the_point(timeline: Timeline) -> None:
    written = (
        "---\nid: guide\npkit:\n  friction:\n    anchors: {path: [src/cli/**]}\n"
        "    revalidated: {at: %s, outcome: unchanged, unchanged-because: holds}\n---\n\nBody.\n"
    )
    base = timeline.start({"docs/guide.md": written % f'"{T1}"'})
    changed = timeline.commit("change the CLI", {"src/cli/main.py": "print('x')\n"})
    timeline.commit("write the same instant unquoted", {"docs/guide.md": written % T1})

    result = _run(timeline)
    assert _point(result) == base
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", changed)]


def test_stale_debt_originates_in_the_first_change_after_the_point(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide()})
    first = timeline.commit("first change", {"src/cli/main.py": "print('1')\n"}, author=ALICE)
    timeline.commit("second change", {"src/cli/main.py": "print('2')\n"}, author=BOB)

    (finding,) = _run(timeline).findings
    assert finding.origin is not None
    assert (finding.origin.sha, finding.origin.author, finding.origin.subject) == (
        first,
        "Alice",
        "first change",
    )
    assert finding.origin.date == HISTORY_EPOCH + timedelta(days=2)


def test_a_record_anchor_changes_with_its_file(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide(anchors={"record": ["COR-050"]})})
    record = ".pkit/decisions/core/COR-050-anchors-and-friction.md"
    text = (timeline.adopter.root / record).read_text(encoding="utf-8")
    amended = timeline.commit("amend the record", {record: text + "\nAmended.\n"})
    assert _summary(_run(timeline)) == [("stale", "docs/guide.md", "record:COR-050", amended)]


def test_collection_entries_have_their_own_points(timeline: Timeline) -> None:
    def collection(rs1_at: str, rs2_at: str) -> str:
        front = {
            entry: {
                "pkit": {
                    "friction": {
                        "anchors": {"path": ["src/core/**"]},
                        "revalidated": {"at": at, "outcome": "updated"},
                    }
                }
            }
            for entry, at in (("RS-1", rs1_at), ("RS-2", rs2_at))
        }
        return f"---\n{json.dumps(front)}\n---\n\n## RS-1 — One\n\nOne.\n\n## RS-2 — Two\n\nTwo.\n"

    timeline.start({"docs/rules.md": collection(T1, T1)})
    changed = timeline.commit("change the engine", {"src/core/engine.py": "ENGINE = 2\n"})
    timeline.commit("revalidate RS-2", {"docs/rules.md": collection(T1, T2)})

    result = _run(timeline)
    assert _summary(result) == [("stale", "docs/rules.md#RS-1", "path:src/core/**", changed)]
    assert {r.location: r.state for r in result.artefact_reports} == {
        "docs/rules.md#RS-1": fr.ArtefactState.STALE,
        "docs/rules.md#RS-2": fr.ArtefactState.CURRENT,
    }


# --- deferrals ---------------------------------------------------------------------------


def test_a_deferral_covers_changes_up_to_its_point(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    deferred = timeline.commit(
        "defer the guide",
        {"docs/guide.md": guide(deferred=[("path", "src/cli/**", "rewrite after the rename")])},
        author=BOB,
    )

    result = _run(timeline)
    assert _summary(result) == [("deferred", "docs/guide.md", "path:src/cli/**", deferred)]
    (report,) = result.artefact_reports
    assert report.state is fr.ArtefactState.DEFERRED
    assert [(a, p.sha if p else None) for a, p in report.deferral_points] == [(CLI, deferred)]
    assert "rewrite after the rename" in result.findings[0].message
    assert "(Bob, 2026-01-04)" in result.findings[0].message
    assert "97 days ago" in fr.render_human(result, now=NOW)


def test_a_deferral_point_is_unmoved_by_rewording(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    deferred = timeline.commit(
        "defer the guide",
        {"docs/guide.md": guide(deferred=[("path", "src/cli/**", "waiting")])},
    )
    after = timeline.commit("change the CLI again", {"src/cli/main.py": "print('cli v3')\n"})
    timeline.commit(
        "reword the deferral",
        {"docs/guide.md": guide(deferred=[("path", "src/cli/**", "waiting, reworded")])},
    )

    result = _run(timeline)
    assert _summary(result) == [
        ("stale", "docs/guide.md", "path:src/cli/**", after),
        ("deferred", "docs/guide.md", "path:src/cli/**", deferred),
    ]
    assert "its deferral at" in result.findings[0].message
    assert "covers only earlier changes" in result.findings[0].message
    assert "waiting, reworded" in result.findings[1].message
    assert result.artefact_reports[0].state is fr.ArtefactState.STALE


def test_a_kept_deferral_covers_nothing_after_the_revalidation(timeline: Timeline) -> None:
    deferred = [("path", "src/cli/**", "kept")]
    timeline.start({"docs/guide.md": guide(deferred=deferred)})
    revalidated = timeline.commit(
        "revalidate, keeping the deferral",
        {"docs/guide.md": guide(at=T2, because="still true", deferred=deferred)},
    )
    changed = timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})

    result = _run(timeline)
    assert _point(result) == revalidated
    assert [s[:1] for s in _summary(result)] == [("stale",), ("deferred",)]
    assert result.findings[0].origin is not None and result.findings[0].origin.sha == changed


# --- a real merge: branch commits interleaved by date -----------------------------------


@dataclass(frozen=True)
class Merged:
    """The commits `_interleaved_merge` lays down."""

    base: str
    first: str  # main: the first edit of the guide
    cli: str  # main: the CLI changed
    side: str  # side: the guide's body edited, dated between main's two edits
    last: str  # main: the last edit of the guide
    merge: str  # main: `side` merged with a merge commit


def _interleaved_merge(timeline: Timeline, first: str, last: str) -> Merged:
    """`base`; on main `first`, a CLI change and `last`; on `side`, off `base`, one body edit
    dated between them; then `side` merged into main with `--no-ff`. In log order the side
    edit sits between main's two edits of the guide, though its parent is `base`."""
    repo = timeline.adopter
    base = timeline.start({"docs/guide.md": guide()})
    repo.checkout("side", create=True)
    repo.checkout("main")
    first_sha = timeline.commit("main: first edit", {"docs/guide.md": first})
    cli = timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"}, author=ALICE)
    repo.checkout("side")
    side = timeline.commit("side: edit the body", {"docs/guide.md": guide(body="Edited on side.")})
    repo.checkout("main")
    last_sha = timeline.commit("main: last edit", {"docs/guide.md": last})
    merge = timeline.merge("side")
    return Merged(base, first_sha, cli, side, last_sha, merge)


def test_the_revalidation_point_is_judged_against_each_commits_own_parent(
    timeline: Timeline,
) -> None:
    history = _interleaved_merge(timeline, first=guide(at=T2), last=guide(at=T2, title="Guide"))
    result = _run(timeline)
    # `last` kept `at`, though the log lists the side edit — still at T1 — right after it;
    # `first` is where `at` changed against its own parent, and the CLI change lies after it.
    assert _point(result) == history.first
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", history.cli)]
    assert result.artefact_reports[0].state is fr.ArtefactState.STALE


def test_a_deferral_point_is_judged_against_each_commits_own_parent(timeline: Timeline) -> None:
    deferred = [("path", "src/cli/**", "waiting")]
    history = _interleaved_merge(
        timeline, first=guide(deferred=deferred), last=guide(deferred=deferred, title="Guide")
    )
    result = _run(timeline)
    # `first` introduced the deferral, `last` only kept it: the CLI change is not covered.
    assert _point(result) == history.base
    assert _summary(result) == [
        ("stale", "docs/guide.md", "path:src/cli/**", history.cli),
        ("deferred", "docs/guide.md", "path:src/cli/**", history.first),
    ]


# --- what a merge commit writes itself (#1113) -----------------------------------------

T3 = "2026-10-03T11:20:00Z"


def _merge_writing(timeline: Timeline, branch: str, files: dict[str, str]) -> str:
    """Merge `branch` with `--no-ff` and write `files` into the merge commit itself, as the
    person resolving it — revalidating the combined state (COR-050 point 3) — does."""
    timeline.adopter.git("merge", "-q", "--no-ff", "--no-commit", branch)
    return timeline.commit(f"merge {branch}", files)


@dataclass(frozen=True)
class RevalidatedWhileMerging:
    """The commits `_revalidated_while_merging` lays down."""

    earlier: str  # topic: the guide revalidated before the CLI changed
    changed: str  # main: the CLI changed
    merge: str  # topic: main merged in, the guide revalidated in the merge commit


def _revalidated_while_merging(timeline: Timeline) -> RevalidatedWhileMerging:
    """`base`; on `topic` the guide revalidated; on main the CLI changed; then `topic`
    merges main with `--no-ff` and revalidates the guide in the merge commit."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    repo.checkout("topic", create=True)
    earlier = timeline.commit(
        "topic: revalidate the guide",
        {"docs/guide.md": guide(at=T2, because="checked on the topic")},
    )
    repo.checkout("main")
    changed = timeline.commit(
        "change the CLI", {"src/cli/main.py": "print('cli v2')\n"}, author=ALICE
    )
    repo.checkout("topic")
    merge = _merge_writing(
        timeline, "main", {"docs/guide.md": guide(at=T3, because="checked against the new CLI")}
    )
    return RevalidatedWhileMerging(earlier, changed, merge)


def test_a_revalidation_written_in_a_merge_commit_is_the_revalidation_point(
    timeline: Timeline,
) -> None:
    history = _revalidated_while_merging(timeline)
    result = _run(timeline)
    # The merge wrote an `at` neither parent had: it is the point, and it reaches the CLI
    # change. Read without the merge, the point was `earlier`, and the change stale after it.
    assert _point(result) == history.merge
    assert _summary(result) == []
    assert result.artefact_reports[0].state is fr.ArtefactState.CURRENT


def test_the_change_check_and_the_whole_repository_check_agree_on_that_point(
    timeline: Timeline,
) -> None:
    history = _revalidated_while_merging(timeline)
    root = timeline.adopter.root

    # On the branch: the change check reads the revalidation in its diff, the
    # whole-repository check at the merge commit — the guide is answered in both.
    change = fc.run_change_check(root, "main")
    assert [(f.kind, f.answer) for f in change.findings] == [
        (fc.FindingKind.REVALIDATED, fc.Answer.UNCHANGED)
    ]
    assert not change.failed
    assert _summary(_run(timeline)) == []

    # Merged into main with `--no-ff`: the point is still the branch's merge commit.
    timeline.adopter.checkout("main")
    timeline.merge("topic")
    result = _run(timeline)
    assert _point(result) == history.merge
    assert _summary(result) == []


def test_a_merge_that_keeps_a_sides_revalidation_is_not_its_point(timeline: Timeline) -> None:
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    repo.checkout("side", create=True)
    revalidated = timeline.commit(
        "side: revalidate the guide", {"docs/guide.md": guide(at=T2, because="checked on side")}
    )
    repo.checkout("main")
    changed = timeline.commit(
        "change the CLI", {"src/cli/main.py": "print('cli v2')\n"}, author=ALICE
    )
    timeline.commit("main: edit the body", {"docs/guide.md": guide(body="Edited on main.")})
    merge = timeline.merge("side")

    # The merge combined both sides' edits of the guide, so git lists it among its paths...
    newest = fr.read_history(repo.root, merge).commits[0]
    assert (newest.sha, [e.path for e in newest.entries]) == (merge, ["docs/guide.md"])
    # ...but its `at` is the side's: the side's commit wrote it, before the CLI changed. A
    # merge keeping one side's timestamp claims no revalidation (COR-050 point 3).
    result = _run(timeline)
    assert _point(result) == revalidated
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", changed)]


def test_a_deferral_written_in_a_merge_commit_has_its_point_there(timeline: Timeline) -> None:
    repo = timeline.adopter
    base = timeline.start({"docs/guide.md": guide()})
    repo.checkout("topic", create=True)
    repo.checkout("main")
    timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"}, author=ALICE)
    repo.checkout("topic")
    deferred = [("path", "src/cli/**", "the CLI rework is not settled")]
    merge = _merge_writing(timeline, "main", {"docs/guide.md": guide(deferred=deferred)})

    result = _run(timeline)
    assert _point(result) == base
    # The deferral point is the merge, which reaches the CLI change: deferred, not stale.
    assert _summary(result) == [("deferred", "docs/guide.md", "path:src/cli/**", merge)]
    assert result.artefact_reports[0].state is fr.ArtefactState.DEFERRED


def test_a_merge_reads_each_parent_under_the_files_name_there(timeline: Timeline) -> None:
    repo = timeline.adopter
    timeline.start({"notes/guide.md": guide()}, friction_config(places=("docs", "notes")))
    repo.checkout("side", create=True)
    revalidated = timeline.commit(
        "side: revalidate the guide", {"notes/guide.md": guide(at=T2, because="checked on side")}
    )
    repo.checkout("main")
    moved = timeline.rename("notes/guide.md", "docs/guide.md")
    timeline.commit("main: edit the body", {"docs/guide.md": guide(body="Edited on main.")})
    timeline.merge("side")

    # The merge's `at` is the side's, read there under the file's old name — so the merge is
    # not the point. The move on main came after the side's revalidation, with none since.
    result = _run(timeline)
    assert _point(result) == revalidated
    assert _summary(result) == [("stale", "docs/guide.md", None, moved)]


# --- a merge that keeps the base side's revalidation (#1217) -----------------------------

T4 = "2026-10-04T08:15:00Z"


@dataclass(frozen=True)
class KeptBaseSide:
    """The commits `_kept_base_side` lays down."""

    revalidated: str  # main: the guide revalidated after main changed the CLI
    changed: str  # topic: the CLI changed, dated after main's revalidation
    dropped: str  # topic: the guide revalidated against that change, dated later still
    merge: str  # topic: main merged in, keeping main's revalidation


def _kept_base_side(timeline: Timeline, *, edits_body: bool) -> KeptBaseSide:
    """`base`; on main the CLI changed and the guide revalidated; on `topic`, off `base` and
    dated after both, the CLI changed elsewhere and the guide revalidated — its `at` conflicting
    with main's; then `topic` merges main and keeps main's revalidation, the state `pkit
    friction resolve` leaves where both sides revalidated. With `edits_body`, topic's
    revalidation edited the body too, kept by the merge beside main's block, so the merge
    commit lists the guide; without, the merged guide is main's, and the merge lists nothing.
    """
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    repo.checkout("topic", create=True)
    repo.checkout("main")
    timeline.commit("main: change the CLI", {"src/cli/main.py": "print('cli v2')\n"}, author=ALICE)
    revalidated = timeline.commit(
        "main: revalidate the guide", {"docs/guide.md": guide(at=T2, because="checked on main")}
    )
    repo.checkout("topic")
    changed = timeline.commit(
        "topic: add a flag", {"src/cli/flags.py": "FLAGS = ('--all',)\n"}, author=BOB
    )
    body = "Edited on topic." if edits_body else "Body."
    answer: dict[str, Any] = (
        {"outcome": "updated", "because": None} if edits_body else {"because": "checked on topic"}
    )
    dropped = timeline.commit(
        "topic: revalidate the guide", {"docs/guide.md": guide(at=T3, body=body, **answer)}
    )
    merging = repo.git("merge", "-q", "--no-ff", "--no-commit", "main", check=False)
    assert merging.returncode == 1, merging.stdout + merging.stderr  # the blocks conflict
    merge = timeline.commit(
        "merge main", {"docs/guide.md": guide(at=T2, because="checked on main", body=body)}
    )
    return KeptBaseSide(revalidated, changed, dropped, merge)


@pytest.mark.parametrize("edits_body", [False, True], ids=["main's-file", "main's-block"])
def test_a_merge_keeping_the_base_sides_revalidation_has_the_base_sides_point(
    timeline: Timeline, edits_body: bool
) -> None:
    history = _kept_base_side(timeline, edits_body=edits_body)
    result = _run(timeline)
    # Topic's revalidation is the newest commit that changed `at`, but the guide no longer
    # carries the `at` it wrote: main's commit wrote the one it carries, so that is the point.
    # What topic's revalidation covered — topic's change of the CLI — is stale after it.
    assert _point(result) == history.revalidated
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", history.changed)]
    assert result.artefact_reports[0].state is fr.ArtefactState.STALE


def test_the_change_check_and_the_whole_repository_check_agree_on_the_base_sides_point(
    timeline: Timeline,
) -> None:
    history = _kept_base_side(timeline, edits_body=False)
    root = timeline.adopter.root

    # The change check compares with main's tip, whose `at` the guide still carries: no
    # revalidation stands in the diff, so topic's change of the CLI is friction. The
    # whole-repository check reads its point at that same commit, the same change stale after.
    change = fc.run_change_check(root, "main")
    assert change.base is not None and change.base.commit == history.revalidated
    assert [(f.kind, f.anchor) for f in change.findings] == [(fc.FindingKind.FRICTION, CLI)]
    result = _run(timeline)
    assert _point(result) == change.base.commit
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", history.changed)]

    # Revalidating the combined state answers it in both, from the one commit that wrote it.
    combined = timeline.commit(
        "revalidate the combined state",
        {"docs/guide.md": guide(at=T4, because="checked against both sides' CLI")},
    )
    change = fc.run_change_check(root, "main")
    assert [(f.kind, f.answer) for f in change.findings] == [
        (fc.FindingKind.ANSWERED, fc.Answer.UNCHANGED)
    ]
    result = _run(timeline)
    assert _point(result) == combined
    assert _summary(result) == []


# --- the cascade along artefact anchors, upstream first -------------------------------


def _chain() -> dict[str, str]:
    """`c` anchors `b`, `b` anchors `a`, `a` anchors the engine."""
    return {
        "docs/a-engine.md": document(
            "engine-notes", anchors={"path": ["src/core/**"]}, at=T1, outcome="updated"
        ),
        "docs/b-overview.md": document(
            "overview", anchors={"artefact": ["engine-notes"]}, at=T1, outcome="updated"
        ),
        "docs/c-intro.md": document(
            "intro", anchors={"artefact": ["overview"]}, at=T1, outcome="updated"
        ),
    }


def test_a_target_content_change_flags_its_dependants(timeline: Timeline) -> None:
    timeline.start(_chain())
    updated = timeline.commit(
        "the engine changed and its notes were updated",
        {
            "src/core/engine.py": "ENGINE = 2\n",
            "docs/a-engine.md": document(
                "engine-notes",
                anchors={"path": ["src/core/**"]},
                at=T2,
                outcome="updated",
                body="Engine 2.",
            ),
        },
    )
    result = _run(timeline)
    assert _summary(result) == [("stale", "docs/b-overview.md", "artefact:engine-notes", updated)]

    timeline.commit(
        "the overview still holds",
        {
            "docs/b-overview.md": document(
                "overview",
                anchors={"artefact": ["engine-notes"]},
                at=T2,
                outcome="unchanged",
                because="the notes' change is internal",
            )
        },
    )
    assert _summary(_run(timeline)) == []


def test_the_container_is_not_content(timeline: Timeline) -> None:
    timeline.start(_chain())
    timeline.commit(
        "defer on the engine notes",
        {
            "docs/a-engine.md": document(
                "engine-notes",
                anchors={"path": ["src/core/**"]},
                at=T1,
                outcome="updated",
                deferred=[("path", "src/core/**", "later")],
            )
        },
    )
    assert [s[0] for s in _summary(_run(timeline))] == ["deferred"]


def test_a_change_of_line_endings_alone_is_no_change_of_content(timeline: Timeline) -> None:
    """The target committed again with `\\r\\n`, its text as it was: no dependant is stale."""
    timeline.start(_chain())
    crlf = _chain()["docs/a-engine.md"].replace("\n", "\r\n")
    timeline.commit("the engine notes, with CRLF", {"docs/a-engine.md": crlf})
    assert _summary(_run(timeline)) == []


def test_findings_run_upstream_first_along_artefact_anchors(timeline: Timeline) -> None:
    timeline.start(
        {
            "docs/a-dependant.md": document(
                "dependant", anchors={"artefact": ["target"]}, at=T1, outcome="updated"
            ),
            "docs/z-target.md": document(
                "target", anchors={"path": ["src/core/**"]}, at=T1, outcome="updated"
            ),
        }
    )
    timeline.commit(
        "the engine and the target reworked, no revalidation",
        {
            "src/core/engine.py": "ENGINE = 2\n",
            "docs/z-target.md": document(
                "target", anchors={"path": ["src/core/**"]}, at=T1, outcome="updated", body="New."
            ),
        },
    )
    result = _run(timeline)
    assert [(f.location, f.anchor and f.anchor.value) for f in result.findings] == [
        ("docs/z-target.md", "src/core/**"),
        ("docs/a-dependant.md", "target"),
    ]


# --- dead anchors, kinds, over-broad anchors ------------------------------------------------


def test_dead_anchors_and_unresolved_kinds_are_all_reported(timeline: Timeline) -> None:
    timeline.start(
        {
            "docs/guide.md": guide(
                anchors={
                    "path": ["src/cli/**", "src/gone/**"],
                    "record": ["COR-999"],
                    "use-case": ["UC-1"],
                }
            )
        }
    )
    result = _run(timeline)
    assert _summary(result) == [
        ("dead-anchor", "docs/guide.md", "path:src/gone/**", None),
        ("dead-anchor", "docs/guide.md", "record:COR-999", None),
        ("unresolved-kind", "docs/guide.md", "use-case:UC-1", None),
    ]
    assert [f.message for f in result.findings[:2]] == [
        "matches no file",
        "names no record",
    ]
    assert "no installed component registers a resolver" in result.findings[2].message
    # A dead anchor leaves the artefact judged on its others; an anchor nothing resolves
    # leaves it not judged — never current.
    assert result.artefact_reports[0].state is fr.ArtefactState.UNRESOLVED
    assert result.state_count(fr.ArtefactState.CURRENT) == 0


def test_a_dead_anchor_leaves_the_artefact_judged_on_its_other_anchors(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide(anchors={"path": ["src/cli/**", "src/gone/**"]})})
    result = _run(timeline)
    assert [f.kind for f in result.findings] == [fr.RepositoryFindingKind.DEAD_ANCHOR]
    assert result.artefact_reports[0].state is fr.ArtefactState.CURRENT


def test_an_over_broad_anchor_is_warned_about(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide(anchors={"path": [".", "src/cli/**"]})})
    result = _run(timeline)
    assert _summary(result) == [("over-broad", "docs/guide.md", "path:.", None)]
    assert fr.OVER_BROAD_SHARE == 0.5
    message = result.findings[0].message
    assert "tracked files (100%)" in message and "most changes" in message
    assert result.artefact_reports[0].state is fr.ArtefactState.CURRENT


# --- the two measures, excluded paths ---------------------------------------------------------


def test_the_two_measures(timeline: Timeline) -> None:
    timeline.start(
        {
            "docs/guide.md": guide(),
            "docs/plain.md": "---\ntitle: Plain\n---\n\nText.\n",
            "docs/none.md": "No front matter: not an artefact.\n",
            "docs/notes.md": document(
                "notes", anchors={"record": ["COR-050"]}, at=T1, outcome="updated"
            ),
        },
        friction_config(surface=["src"]),
    )
    result = _run(timeline)
    assert result.artefacts == 3
    assert result.unanchored == ("docs/plain.md",)
    assert (result.surface, result.uncovered) == (2, ("src/core/engine.py",))
    human = fr.render_human(result, now=NOW)
    assert "Unanchored artefacts: 1 of 3 in the places" in human
    assert "Uncovered surface: 1 of 2 paths in the declared surface" in human


def test_an_artefact_accepted_unanchored_is_listed_apart_and_never_counted(
    timeline: Timeline,
) -> None:
    """COR-050 points 1 and 8: an artefact whose block gives the reason a person accepted
    it with no anchors is listed apart, with its reason; only the forgotten ones count.
    An excluded one is in neither list (point 7)."""
    sponsor = "No code embodies the sponsor: it funds the project."
    timeline.start(
        {
            "docs/guide.md": guide(),
            "docs/plain.md": "---\ntitle: Plain\n---\n\nText.\n",
            "docs/sponsor.md": document("sponsor", unanchored_because=sponsor),
            "docs/index.md": document(None, unanchored_because="A signpost:\n  lists   pages."),
            "docs/generated/api.md": document("api", unanchored_because="Generated."),
        },
        friction_config(exclude=["docs/generated"]),
    )
    result = _run(timeline)
    assert result.unanchored == ("docs/plain.md",)
    assert result.accepted_unanchored == (
        fr.AcceptedUnanchored("docs/index.md", "docs/index.md", "A signpost: lists pages."),
        fr.AcceptedUnanchored("sponsor", "docs/sponsor.md", sponsor),
    )
    # Nothing to judge: an accepted artefact has no anchors, so no state either.
    assert [r.location for r in result.artefact_reports] == ["docs/guide.md"]

    human = fr.render_human(result, now=NOW)
    counted = (
        "Unanchored artefacts: 1 of 4 in the places (2 accepted with a reason, listed apart; "
        "excluded paths left out: 1 artefact)"
    )
    assert counted in human
    assert "  Accepted unanchored: 2, not counted — each with its reason" in human
    assert f"    docs/sponsor.md  {sponsor}" in human
    measures = json.loads(fr.render_json(result))["measures"]
    assert measures["unanchored"] == ["docs/plain.md"]
    assert measures["accepted_unanchored"] == [
        {
            "artefact": "docs/index.md",
            "location": "docs/index.md",
            "reason": "A signpost: lists pages.",
        },
        {"artefact": "sponsor", "location": "docs/sponsor.md", "reason": sponsor},
    ]


def test_the_measures_are_reported_while_nothing_is_anchored_yet(timeline: Timeline) -> None:
    timeline.start(
        {"docs/plain.md": "---\ntitle: Plain\n---\n\nText.\n"}, friction_config(surface=["src"])
    )
    result = _run(timeline)
    assert not result.dormant and result.artefact_reports == ()
    assert result.unanchored == ("docs/plain.md",)
    assert result.uncovered == ("src/cli/main.py", "src/core/engine.py")


def test_a_capability_surface_is_measured_repository_relative(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A capability's `friction.surface` names repository paths (the package
    schema), so its uncovered paths are the repository's — not paths under one
    of the capability's documentation locations."""
    timeline = Timeline(make_adopter_repo(capabilities=("evidence",)))
    package = ".pkit/capabilities/evidence/package.yaml"
    declared = (timeline.adopter.root / package).read_text(encoding="utf-8") + (
        "docs:\n  locations:\n    runs: {path: evidence}\nfriction:\n  surface: [src/core]\n"
    )
    timeline.start({package: declared, "docs/guide.md": guide()})
    result = _run(timeline)
    assert (result.surface, result.uncovered) == (1, ("src/core/engine.py",))


def test_excluded_paths_are_ignored_for_anchoring_and_the_measures(timeline: Timeline) -> None:
    timeline.start(
        {
            "src/cli/generated/table.py": "T = 1\n",
            "docs/guide.md": guide(anchors={"path": ["src/cli/**", "src/cli/generated/**"]}),
        },
        friction_config(exclude=["src/cli/generated"], surface=["src"]),
    )
    timeline.commit("regenerate", {"src/cli/generated/table.py": "T = 2\n"})
    result = _run(timeline)
    assert _summary(result) == [
        ("dead-anchor", "docs/guide.md", "path:src/cli/generated/**", None),
    ]
    assert (result.surface, result.uncovered) == (2, ("src/core/engine.py",))


def test_an_artefact_under_an_excluded_path_is_left_out_of_the_measures(
    timeline: Timeline,
) -> None:
    """COR-050 point 7: an excluded artefact is neither listed nor counted as
    unanchored, and never judged stale or deferred — while what it declares is
    still checked, since a dead anchor is never silence."""
    timeline.start(
        {
            "docs/guide.md": guide(),
            "docs/plain.md": "---\ntitle: Plain\n---\n\nText.\n",
            "docs/generated/api.md": "---\ntitle: API\n---\n\nGenerated.\n",
            "docs/generated/cli.md": guide(anchors={"path": ["src/cli/**", "src/gone/**"]}),
            "docs/generated/engine.md": document(
                "engine",
                anchors={"path": ["src/core/**"]},
                at=T1,
                outcome="updated",
                deferred=[("path", "src/core/**", "regenerated later")],
            ),
        },
        friction_config(exclude=["docs/generated"]),
    )
    timeline.commit("change the CLI", {"src/cli/main.py": "print('x')\n"})
    timeline.commit("change the engine", {"src/core/engine.py": "ENGINE = 2\n"})

    result = _run(timeline)
    assert (result.artefacts, result.excluded) == (5, 3)
    assert result.unanchored == ("docs/plain.md",)
    assert [r.location for r in result.artefact_reports] == ["docs/guide.md"]
    assert [(kind, location, anchor) for kind, location, anchor, _ in _summary(result)] == [
        ("dead-anchor", "docs/generated/cli.md", "path:src/gone/**"),
        ("stale", "docs/guide.md", "path:src/cli/**"),
    ]
    measure = "Unanchored artefacts: 1 of 2 in the places (excluded paths left out: 3 artefacts)"
    assert measure in fr.render_human(result, now=NOW)
    counts = json.loads(fr.render_json(result))["counts"]
    assert (counts["artefacts"], counts["excluded"], counts["checked"]) == (5, 3, 1)
    assert (counts["stale"], counts["deferred"]) == (1, 0)


# --- each state under its own exclusions (COR-050 point 7) -----------------------------------

GENERATED = {"src/cli/generated/table.py": "T = 1\n"}


def test_a_widening_over_files_that_did_not_change_is_reported_not_stale(
    timeline: Timeline,
) -> None:
    """The point is read under its own `friction.exclude`: HEAD's leaves out a file the
    anchor stood on there, but nothing changed it while the anchor stood on it — a change
    made once it was left out is not the anchor's — so it is reported, never owed."""
    timeline.start({"docs/guide.md": guide(), **GENERATED})
    widened = timeline.commit(
        "exclude the generated code",
        {CONFIG: friction_config(exclude=["src/cli/generated"])},
        author=ALICE,
    )
    timeline.commit("regenerate, excluded", {"src/cli/generated/table.py": "T = 2\n"})

    result = _run(timeline)
    assert _summary(result) == [("left-out", "docs/guide.md", "path:src/cli/**", widened)]
    assert result.findings[0].message == (
        "`friction.exclude` now leaves out 1 file this anchor stood on at its revalidation "
        "point (src/cli/generated/table.py); no change to it since, left out in "
        f'{widened[:12]} "exclude the generated code" (Alice, '
        f"{(HISTORY_EPOCH + timedelta(days=2)).date().isoformat()})"
    )
    assert result.artefact_reports[0].state is fr.ArtefactState.CURRENT


def test_a_widening_never_erases_a_change_made_before_it(timeline: Timeline) -> None:
    """A file the anchor stood on, changed while it did, then left out: the change is still
    the anchor's, its origin the edit — never the widening that came after."""
    timeline.start({"docs/guide.md": guide(), **GENERATED})
    edited = timeline.commit(
        "regenerate the table", {"src/cli/generated/table.py": "T = 2\n"}, author=BOB
    )
    timeline.commit(
        "exclude the generated code", {CONFIG: friction_config(exclude=["src/cli/generated"])}
    )

    result = _run(timeline)
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", edited)]
    assert (
        f"; `friction.exclude` changed over it since (now leaves out src/cli/generated/table.py, "
        f"changed since its revalidation point ({edited[:12]})) — revalidate"
    ) in result.findings[0].message


def test_a_file_added_after_the_point_and_then_left_out_stays_a_change(
    timeline: Timeline,
) -> None:
    """COR-050 point 7: the files an anchor stood on are sought among those touched since
    the point too, so a file added under it — a change nobody answered — is not erased by a
    later widening that leaves it out."""
    timeline.start({"docs/guide.md": guide()})
    added = timeline.commit("generate a table", GENERATED, author=ALICE)
    timeline.commit(
        "exclude the generated code", {CONFIG: friction_config(exclude=["src/cli/generated"])}
    )

    result = _run(timeline)
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", added)]
    assert (
        f"(now leaves out src/cli/generated/table.py, changed since its revalidation point "
        f"({added[:12]}))"
    ) in result.findings[0].message


def test_a_widening_never_hides_a_change_to_the_same_anchor(timeline: Timeline) -> None:
    """A change to a file the anchor stands on at both states is stale as ever; the widening
    beside it, over a file that did not change, is reported apart and asks nothing."""
    timeline.start({"docs/guide.md": guide(), **GENERATED})
    changed = timeline.commit(
        "change the CLI, and exclude the generated code",
        {
            "src/cli/main.py": "print('cli v2')\n",
            CONFIG: friction_config(exclude=["src/cli/generated"]),
        },
    )
    result = _run(timeline)
    assert _summary(result) == [
        ("stale", "docs/guide.md", "path:src/cli/**", changed),
        ("left-out", "docs/guide.md", "path:src/cli/**", changed),
    ]
    assert "`friction.exclude`" not in result.findings[0].message
    human = fr.render_human(result, now=NOW)
    assert "1 stale, 1 left-out anchor" in human
    assert "  left-out  `friction.exclude` took files from an anchor" in human


def test_an_exclusion_narrowed_since_the_point_is_stale_from_the_narrowing(
    timeline: Timeline,
) -> None:
    """A change made while the file was left out is no change to the anchor: the narrowing
    that let the file in is, so the debt is dated from it — never from older commits — and
    the change made while it was left out is named."""
    timeline.start(
        {"docs/guide.md": guide(), **GENERATED}, friction_config(exclude=["src/cli/generated"])
    )
    regenerated = timeline.commit(
        "regenerate, still excluded", {"src/cli/generated/table.py": "T = 2\n"}
    )
    narrowed = timeline.commit("stop excluding the generated code", {CONFIG: friction_config()})

    result = _run(timeline)
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", narrowed)]
    assert (
        f"; `friction.exclude` changed over it since (now lets in src/cli/generated/table.py, "
        f"changed since it was left out ({regenerated[:12]}))"
    ) in result.findings[0].message


def test_a_change_made_while_left_out_counts_where_the_point_and_head_leave_it_in(
    timeline: Timeline,
) -> None:
    """Each check compares two states: excluded after the point, changed, and let back in to
    the point's exclusions, the file is one the anchor stands on at both, and its change
    counts. Where HEAD leaves it out, the same change does not."""
    timeline.start({"docs/guide.md": guide(), **GENERATED})
    timeline.commit(
        "exclude the generated code", {CONFIG: friction_config(exclude=["src/cli/generated"])}
    )
    edited = timeline.commit("regenerate, excluded", {"src/cli/generated/table.py": "T = 2\n"})
    assert [kind for kind, *_ in _summary(_run(timeline))] == ["left-out"]

    timeline.commit("stop excluding the generated code", {CONFIG: friction_config()})
    result = _run(timeline)
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", edited)]
    assert "`friction.exclude`" not in result.findings[0].message


def test_a_file_removed_under_a_later_exclusion_is_a_change_never_left_out(
    timeline: Timeline,
) -> None:
    timeline.start({"docs/guide.md": guide(), **GENERATED})
    removed = timeline.commit("drop the table", {"src/cli/generated/table.py": None})
    timeline.commit(
        "exclude where it was", {CONFIG: friction_config(exclude=["src/cli/generated"])}
    )

    result = _run(timeline)
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", removed)]
    assert "now leaves out" not in result.findings[0].message


def test_an_exclusion_that_changed_nothing_the_anchor_stood_on_is_no_change(
    timeline: Timeline,
) -> None:
    """A file added and excluded in one commit was never stood on, and a configuration change
    that leaves the exclusions alone reads as no change at all."""
    timeline.start({"docs/guide.md": guide()})
    timeline.commit(
        "generate a table, and exclude it",
        {**GENERATED, CONFIG: friction_config(exclude=["src/cli/generated"])},
    )
    timeline.commit(
        "enforce friction",
        {CONFIG: friction_config(mode="enforcing", exclude=["src/cli/generated"])},
    )
    result = _run(timeline)
    assert _summary(result) == []
    assert result.artefact_reports[0].state is fr.ArtefactState.CURRENT


def test_record_and_artefact_anchors_are_untouched_by_an_exclusion(timeline: Timeline) -> None:
    record = ".pkit/decisions/core/COR-050-anchors-and-friction.md"
    target = document("target", anchors={"path": ["src/core/**"]}, at=T1, outcome="updated")
    anchored = guide(anchors={"record": ["COR-050"], "artefact": ["target"]})
    timeline.start({"docs/guide.md": anchored, "docs/target.md": target})
    timeline.commit(
        "exclude the record and the target",
        {CONFIG: friction_config(exclude=[".pkit/decisions", "docs/target.md"])},
    )
    result = _run(timeline)
    assert [(f.kind.value, f.location) for f in result.findings] == []

    text = (timeline.adopter.root / record).read_text(encoding="utf-8")
    amended = timeline.commit("amend the record", {record: text + "\nAmended.\n"})
    assert _summary(_run(timeline)) == [("stale", "docs/guide.md", "record:COR-050", amended)]


def test_a_dead_anchor_names_the_exclusion_added_since_the_point(timeline: Timeline) -> None:
    anchors = {"path": ["src/cli/**", "src/cli/generated/**"]}
    timeline.start({"docs/guide.md": guide(anchors=anchors), **GENERATED})
    widened = timeline.commit(
        "exclude the generated code",
        {CONFIG: friction_config(exclude=["src/cli/generated"])},
        author=BOB,
    )
    day = (HISTORY_EPOCH + timedelta(days=2)).date().isoformat()

    result = _run(timeline)
    dead = next(f for f in result.findings if f.kind is fr.RepositoryFindingKind.DEAD_ANCHOR)
    assert dead.message == (
        f'matches only excluded files (1), excluded since {widened[:12]} "exclude the generated '
        f'code" (Bob, {day})'
    )
    assert dead.origin is None


def test_the_two_checks_agree_on_an_exclusion_change_and_an_excluded_artefact(
    timeline: Timeline,
) -> None:
    """What the change check asks of a pull request, the whole-repository check reports once
    it lands unanswered, and what one only reports the other does (#1152): a widening over
    a file the change leaves alone is reported by both; one over a file it changes is
    friction, then stale; an excluded artefact is asked nothing, then never judged stale."""
    repo = timeline.adopter
    generated = document("gen-cli", anchors={"path": ["src/cli/**"]}, at=T1, outcome="updated")
    listing = {"src/cli/tables/list.py": "L = 1\n"}
    timeline.start(
        {"docs/guide.md": guide(), "docs/generated/cli.md": generated, **GENERATED, **listing},
        friction_config(exclude=["docs/generated"]),
    )
    repo.checkout("topic", create=True)
    widened = timeline.commit(
        "exclude the generated code",
        {CONFIG: friction_config(exclude=["docs/generated", "src/cli/generated"])},
    )
    change = fc.run_change_check(repo.root, "main")
    assert [(f.kind.value, f.location) for f in change.findings] == [("left-out", "docs/guide.md")]
    repo.checkout("main")
    timeline.merge("topic")
    result = _run(timeline)
    assert _summary(result) == [("left-out", "docs/guide.md", "path:src/cli/**", widened)]
    assert [(r.location, r.state) for r in result.artefact_reports] == [
        ("docs/guide.md", fr.ArtefactState.CURRENT)
    ]

    repo.checkout("second", create=True)
    edited = timeline.commit(
        "regenerate the list, and exclude it",
        {
            "src/cli/tables/list.py": "L = 2\n",
            CONFIG: friction_config(
                exclude=["docs/generated", "src/cli/generated", "src/cli/tables"]
            ),
        },
    )
    change = fc.run_change_check(repo.root, "main")
    assert [(f.kind.value, f.location) for f in change.findings] == [("friction", "docs/guide.md")]
    assert "(now leaves out src/cli/tables/list.py, which this diff also changes)" in (
        change.findings[0].message
    )
    repo.checkout("main")
    timeline.merge("second")
    result = _run(timeline)
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", edited)]
    assert (
        f"(now leaves out src/cli/tables/list.py, changed since its revalidation point "
        f"({edited[:12]}), and src/cli/generated/table.py)"
    ) in result.findings[0].message


def test_an_artefact_let_back_in_is_stale_from_the_narrowing_in_both_checks(
    timeline: Timeline,
) -> None:
    """COR-050 point 7, as a move is read (point 3): the change check asks an artefact a
    narrowing lets back in to revalidate in that change, and unanswered, the
    whole-repository check finds it stale from the commit that let it in."""
    repo = timeline.adopter
    timeline.start(
        {"docs/guide.md": guide(), "docs/generated/cli.md": guide()},
        friction_config(exclude=["docs/generated"]),
    )
    repo.checkout("topic", create=True)
    narrowed = timeline.commit("stop excluding the generated pages", {CONFIG: friction_config()})
    change = fc.run_change_check(repo.root, "main")
    assert [(f.kind.value, f.location, f.anchor) for f in change.findings] == [
        ("friction", "docs/generated/cli.md", None)
    ]
    repo.checkout("main")
    timeline.merge("topic")

    result = _run(timeline)
    assert _summary(result) == [("stale", "docs/generated/cli.md", None, narrowed)]
    assert result.findings[0].message.startswith(
        f'let back in by `friction.exclude` in {narrowed[:12]} "stop excluding the generated pages"'
    )

    timeline.commit(
        "revalidate the page let back in",
        {"docs/generated/cli.md": guide(at=T2, because="the page still describes the CLI")},
    )
    assert _summary(_run(timeline)) == []


def test_a_point_whose_exclusions_do_not_read_is_reported_and_read_as_head(
    timeline: Timeline,
) -> None:
    """A revalidation point whose `friction.exclude` cannot be read is not one that leaves
    nothing out: no widening is made up from it, and the point is named."""
    point = timeline.start({"docs/guide.md": guide(), **GENERATED}, friction_config(exclude=5))
    timeline.commit(
        "write the exclusions as a list", {CONFIG: friction_config(exclude=["src/cli/generated"])}
    )
    result = _run(timeline)
    assert _summary(result) == [("unreadable", CONFIG, None, point)]
    assert f'`friction.exclude` does not read at {point[:12]} "base"' in result.findings[0].message
    assert result.artefact_reports[0].state is fr.ArtefactState.CURRENT


# --- modes, dormancy, the working tree, output ----------------------------------------------


def test_exit_zero_in_enforcing_mode(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide()}, friction_config(mode="enforcing"))
    timeline.commit("change the CLI", {"src/cli/main.py": "print('e')\n"})
    result = _cli()
    assert result.exit_code == 0, result.output
    assert "1 stale" in result.output and "Result: reported" in result.output
    assert "never fails" in result.output


def test_dormant_without_places(timeline: Timeline) -> None:
    timeline.start(
        {"docs/guide.md": guide()}, json.dumps({"friction": {"mode": "enforcing"}}) + "\n"
    )
    result = _cli()
    assert result.exit_code == 0, result.output
    assert "no places declared; dormant." in result.output


def test_dormant_demands_no_repository(tmp_path: Path) -> None:
    result = fr.run_repository_check(tmp_path)
    assert (result.dormant, result.head, result.exit_code) == (True, None, 0)


def test_before_the_first_commit_the_check_says_so(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo()
    adopter.write({CONFIG: friction_config(), "docs/guide.md": guide()})
    with pytest.raises(fr.FrictionCheckError, match="commit first"):
        fr.run_repository_check(adopter.root)


def test_uncommitted_work_is_not_read(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide()})
    timeline.adopter.write({"src/cli/main.py": "print('uncommitted')\n"})
    result = _run(timeline)
    assert result.findings == ()
    assert result.head is not None and result.head.uncommitted == 1
    assert "1 uncommitted path not read" in fr.render_human(result, now=NOW)


def test_unparsable_front_matter_is_reported(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide(), "docs/broken.md": "---\nid: [unclosed\n---\n"})
    assert _summary(_run(timeline)) == [("unreadable", "docs/broken.md", None, None)]


def test_json_document_shape(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide()}, friction_config(mode="enforcing"))
    changed = timeline.commit("change the CLI", {"src/cli/main.py": "print('j')\n"}, author=ALICE)
    result = _cli("--json")
    assert result.exit_code == 0, result.output
    doc = json.loads(result.output)
    assert sorted(doc) == [
        "artefacts",
        "check",
        "counts",
        "dormant",
        "failed",
        "findings",
        "head",
        "history",
        "measures",
        "mode",
        "schema_version",
        "states",
    ]
    assert doc["schema_version"] == fr.REPOSITORY_SCHEMA_VERSION == 1
    assert (doc["check"], doc["mode"], doc["dormant"], doc["failed"]) == (
        "repository",
        "enforcing",
        False,
        False,
    )
    assert doc["history"] == {"shallow": False}
    assert sorted(doc["head"]) == ["commit", "uncommitted_paths"]
    assert doc["counts"]["stale"] == 1 and doc["counts"]["checked"] == 1
    assert doc["states"] == {
        "current": 0,
        "deferred": 0,
        "stale": 1,
        "unreachable": 0,
        "unresolved": 0,
    }
    assert doc["measures"] == {
        "accepted_unanchored": [],
        "unanchored": [],
        "uncovered_surface": [],
    }
    (finding,) = doc["findings"]
    assert finding == {
        "artefact": "guide",
        "location": "docs/guide.md",
        "kind": "stale",
        "anchor": {"kind": "path", "value": "src/cli/**"},
        "origin": {
            "commit": changed,
            "author": "Alice",
            "date": (HISTORY_EPOCH + timedelta(days=2)).isoformat(),
            "change": "change the CLI",
        },
        "message": finding["message"],
    }
    (report,) = doc["artefacts"]
    assert sorted(report) == [
        "artefact",
        "cut",
        "deferral_points",
        "location",
        "revalidation_point",
        "revalidation_points",
        "state",
    ]
    assert report["cut"] is False
    assert report["state"] == "stale" and sorted(report["revalidation_point"]) == [
        "author",
        "change",
        "commit",
        "date",
    ]
    assert report["revalidation_points"] == [report["revalidation_point"]]


def test_output_is_deterministic(timeline: Timeline) -> None:
    files = _chain()
    files["docs/guide.md"] = guide(deferred=[("path", "src/cli/**", "later")])
    timeline.start(files, friction_config(surface=["src"]))
    timeline.commit(
        "several changes",
        {"src/cli/main.py": "print('z')\n", "src/core/engine.py": "ENGINE = 9\n"},
    )
    first, second = _run(timeline), _run(timeline)
    assert fr.render_json(first) == fr.render_json(second)
    assert fr.render_human(first, now=NOW) == fr.render_human(second, now=NOW)
    assert [(f.location, f.kind.value) for f in first.findings] == [
        ("docs/a-engine.md", "stale"),
        ("docs/guide.md", "stale"),
        ("docs/guide.md", "deferred"),
    ]


# --- a shallow clone ------------------------------------------------------------------------


def test_a_shallow_clone_that_cannot_reach_a_point_is_reported_not_guessed(
    timeline: Timeline, tmp_path: Path
) -> None:
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    for version in (2, 3, 4):
        timeline.commit(f"cli {version}", {"src/cli/main.py": f"print('cli {version}')\n"})

    shallow = tmp_path / "shallow"
    repo.git("clone", "-q", "--depth", "2", f"file://{repo.root}", str(shallow))
    result = fr.run_repository_check(shallow)
    assert result.shallow is True
    assert _summary(result) == [("unreachable", "docs/guide.md", None, None)]
    (report,) = result.artefact_reports
    assert (report.state, report.revalidation_point) == (fr.ArtefactState.UNREACHABLE, None)
    assert "git fetch --unshallow" in result.findings[0].message
    assert "shallow clone" in fr.render_human(result, now=NOW)

    # A depth of exactly four still records the root commit as the cut — the
    # clone cannot tell a root from a cut, so it is reported the same way. One
    # deeper than the history is not shallow: the same answer as the full clone.
    deep = tmp_path / "deep"
    repo.git("clone", "-q", "--depth", "5", f"file://{repo.root}", str(deep))
    deep_result = fr.run_repository_check(deep)
    assert deep_result.shallow is False
    assert _summary(deep_result)[0][0] == "stale"


# --- the root commit, whatever log.showRoot says ----------------------------------------------


def test_the_root_commit_is_read_whatever_log_showroot_says(
    timeline: Timeline, tmp_path: Path
) -> None:
    repo = timeline.adopter
    repo.git("config", "log.showRoot", "false")
    base = timeline.start({"docs/guide.md": guide()})
    timeline.commit("edit the body", {"docs/guide.md": guide(body="Edited.")})
    changed = timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})

    # With `log.showRoot=false` the root commit lists no paths unless asked; unlisted, the
    # file's history would end at the body edit and the point be guessed there.
    result = _run(timeline)
    assert _point(result) == base
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", changed)]

    # A shallow clone shows its boundary commit as a root: unlisted, the cut would go
    # unseen and the point be guessed the same way; listed, the artefact is reported.
    shallow = tmp_path / "shallow"
    repo.git("clone", "-q", "--depth", "3", f"file://{repo.root}", str(shallow))
    GitRepo(shallow).git("config", "log.showRoot", "false")
    shallow_result = fr.run_repository_check(shallow)
    assert shallow_result.shallow is True
    assert _summary(shallow_result) == [("unreachable", "docs/guide.md", None, None)]
    (finding,) = shallow_result.findings
    assert "its revalidation point is not in this clone's history" in finding.message


# --- edits put back, and answers written back (#1233) ---------------------------------------
#
# COR-050 points 3 to 5 and 9: a revalidation point is where the artefact first carried the
# `at` it carries; an anchor has changed where what it stands on differs between two states;
# a deferral covers its anchor as it stood at its point. Each history below is read by both
# checks: what the change check asks of a pull request is what `check --all` reports once
# it lands unanswered.

RECORD = ".pkit/decisions/core/COR-050-anchors-and-friction.md"
ANCHORED = {"path": ["src/cli/**"], "record": ["COR-050"]}
CLI_SOURCE = "print('cli')\n"
NOTE = {"docs/notes.txt": "A note.\n"}  # an unanchored file, so a squash is never empty


def _record(timeline: Timeline) -> str:
    return (timeline.adopter.root / RECORD).read_text(encoding="utf-8")


def _friction(change: fc.ChangeCheck) -> list[tuple[str, str | None]]:
    """(location, anchor) of each friction finding of a change check."""
    return [
        (f.location or "", None if f.anchor is None else f"{f.anchor.kind}:{f.anchor.value}")
        for f in change.findings
        if f.kind is fc.FindingKind.FRICTION
    ]


def _land(timeline: Timeline, branch: str, landing: str) -> str:
    """Land `branch` on main, with a merge commit or as one squashed commit."""
    timeline.adopter.checkout("main")
    if landing == "merge":
        return timeline.merge(branch)
    return timeline.squash_merge(branch)


@pytest.mark.parametrize("landing", ["merge", "squash"])
def test_an_edit_put_back_is_no_change_however_it_lands(timeline: Timeline, landing: str) -> None:
    """A path anchor's file and a record anchor's file, each edited and restored on a branch:
    the change check compares the base with the head and asks nothing, and `check --all`,
    after a merge that keeps the two commits as after a squash that folds them, finds the
    guide current at its point."""
    repo = timeline.adopter
    base = timeline.start({"docs/guide.md": guide(anchors=ANCHORED)})
    text = _record(timeline)
    repo.checkout("topic", create=True)
    timeline.commit(
        "edit the CLI and the record",
        {"src/cli/main.py": "print('edited')\n", RECORD: text + "\nEdited.\n"},
    )
    timeline.commit("put them back", {"src/cli/main.py": CLI_SOURCE, RECORD: text, **NOTE})

    change = fc.run_change_check(repo.root, "main")
    assert [f.kind for f in change.findings] == []
    _land(timeline, "topic", landing)
    result = _run(timeline)
    assert _point(result) == base
    assert _summary(result) == []
    assert result.artefact_reports[0].state is fr.ArtefactState.CURRENT


@pytest.mark.parametrize("landing", ["merge", "squash"])
@pytest.mark.parametrize("debt", [False, True], ids=["no-earlier-debt", "earlier-debt"])
def test_a_record_edited_and_re_answered_then_both_reverted(
    timeline: Timeline, debt: bool, landing: str
) -> None:
    """The issue's history: on a branch, the record is amended and the guide re-answered,
    then that commit is reverted. Nothing differs from the base, so the change check asks
    nothing; once landed, merged or squashed, the guide is current at its first point — or,
    with an unanswered change Y before the branch, stale from Y, as it was before: the pair
    erases no debt."""
    repo = timeline.adopter
    base = timeline.start({"docs/guide.md": guide(anchors=ANCHORED)})
    earlier = (
        timeline.commit("Y: change the CLI", {"src/cli/main.py": "print('Y')\n"}) if debt else None
    )
    owed = [("stale", "docs/guide.md", "path:src/cli/**", earlier)] if debt else []
    assert _summary(_run(timeline)) == owed

    text = _record(timeline)
    repo.checkout("topic", create=True)
    amended = timeline.commit(
        "amend the record and re-answer the guide",
        {
            RECORD: text + "\nAmended.\n",
            "docs/guide.md": guide(anchors=ANCHORED, at=T2, because="checked the amended record"),
        },
    )
    timeline.revert(amended)
    timeline.commit("a note", NOTE)
    change = fc.run_change_check(repo.root, "main")
    assert [f.kind for f in change.findings] == []

    _land(timeline, "topic", landing)
    result = _run(timeline)
    assert _point(result) == base
    assert _summary(result) == owed


@pytest.mark.parametrize("outcome", ["unchanged", "updated"])
def test_reverting_a_revalidation_with_the_change_it_answered_owes_nothing(
    timeline: Timeline, outcome: str
) -> None:
    """A revalidation and the record change it answered, reverted together as their own pull
    request: the written-back `at` answers nothing and is no bump, and nothing differs from
    its point — so no friction; once landed the guide is current at that first point."""
    repo = timeline.adopter
    base = timeline.start({"docs/guide.md": guide(anchors=ANCHORED)})
    text = _record(timeline)
    answer: dict[str, Any] = (
        {"because": "checked the amended record"}
        if outcome == "unchanged"
        else {"outcome": "updated", "because": None, "body": "Rewritten for the record."}
    )
    amended = timeline.commit(
        "amend the record and revalidate the guide",
        {RECORD: text + "\nAmended.\n", "docs/guide.md": guide(anchors=ANCHORED, at=T2, **answer)},
    )
    repo.checkout("undo", create=True)
    timeline.revert(amended)

    change = fc.run_change_check(repo.root, "main")
    assert [f.kind for f in change.findings] == []
    (written,) = change.answers
    assert (written.status, written.asked) == (fc.AnswerStatus.WRITTEN_BACK, False)
    assert "written back: an `at` it carried before, which answers nothing" in fc.render_human(
        change
    )

    timeline.adopter.checkout("main")
    timeline.merge("undo")
    result = _run(timeline)
    assert _point(result) == base
    assert _summary(result) == []


@dataclass(frozen=True)
class Answered:
    """The commits `_answered_then_reverted` lays down."""

    base: str
    owed: str  # Y: the record amended, nobody answering
    answered: str  # X: the record amended again, the guide revalidated against both


def _answered_then_reverted(timeline: Timeline) -> Answered:
    """`base`; Y amends the record unanswered; X amends it again and revalidates the guide,
    answering both; then a branch `undo` reverts X."""
    base = timeline.start(
        {"docs/guide.md": guide(anchors=ANCHORED)}, friction_config(mode="enforcing")
    )
    text = _record(timeline)
    owed = timeline.commit("Y: amend the record", {RECORD: text + "\nY.\n"}, author=ALICE)
    answered = timeline.commit(
        "X: amend the record again, revalidate the guide",
        {
            RECORD: text + "\nY.\n\nX.\n",
            "docs/guide.md": guide(anchors=ANCHORED, at=T2, because="checked against Y and X"),
        },
        author=BOB,
    )
    timeline.adopter.checkout("undo", create=True)
    timeline.revert(answered)
    return Answered(base, owed, answered)


def test_reverting_a_revalidation_brings_back_the_debt_it_answered(timeline: Timeline) -> None:
    """The issue's acceptance criterion: X's revalidation answered Y and X; reverting it takes
    X away and keeps Y, and puts back an `at` that answered neither. The change check judges
    the written-back `at` against its own point and asks about the record — enforcing mode
    fails — and once landed, `check --all` finds the guide stale from Y, at the first point."""
    history = _answered_then_reverted(timeline)
    repo = timeline.adopter
    timeline.adopter.checkout("main")
    result = _run(timeline)
    assert (_point(result), _summary(result)) == (history.answered, [])
    repo.checkout("undo")

    change = fc.run_change_check(repo.root, "main")
    assert _friction(change) == [("docs/guide.md", "record:COR-050")]
    (finding,) = [f for f in change.findings if f.kind is fc.FindingKind.FRICTION]
    assert finding.message == (
        f"changed since its revalidation point {history.base[:12]} "
        f"({(HISTORY_EPOCH + timedelta(days=1)).date().isoformat()}), whose `at` this diff writes "
        f"back — that revalidation answered only what it saw; revalidate the artefact, or defer "
        f"the anchor"
    )
    assert change.failed and change.exit_code == 1
    assert [f.kind for f in change.findings if f.kind is fc.FindingKind.BUMP] == []

    repo.checkout("main")
    timeline.merge("undo")
    result = _run(timeline)
    assert _point(result) == history.base
    assert _summary(result) == [("stale", "docs/guide.md", "record:COR-050", history.owed)]
    assert result.findings[0].message.startswith(
        f"changed after its revalidation point {history.base[:12]}"
    )
    assert "a change not put back since" in result.findings[0].message


def test_reverting_the_revert_owes_nothing(timeline: Timeline) -> None:
    """The revert landed, then reverted in turn: X's `at` comes back, written back to the
    point that answered Y and X, and nothing differs from it — no friction; current at X."""
    history = _answered_then_reverted(timeline)
    repo = timeline.adopter
    repo.checkout("main")
    landed = timeline.merge("undo")
    repo.checkout("redo", create=True)
    timeline.revert(landed, mainline=1)

    change = fc.run_change_check(repo.root, "main")
    assert [f.kind for f in change.findings] == []
    assert [a.status for a in change.answers] == [fc.AnswerStatus.WRITTEN_BACK]
    repo.checkout("main")
    timeline.merge("redo")
    result = _run(timeline)
    assert _point(result) == history.answered
    assert _summary(result) == []


@pytest.mark.parametrize("edits_body", [False, True], ids=["main's-file", "main's-block"])
def test_a_merge_keeping_the_base_sides_revalidation_landed_as_a_squash(
    timeline: Timeline, edits_body: bool
) -> None:
    """The kept-side case of #1217 landed as a squash: the squash brings none of the dropped
    side's commits into main's history, so the point is main's revalidation and the topic's
    change of the CLI is stale from the squash that brought it — as the change check on the
    topic asked."""
    history = _kept_base_side(timeline, edits_body=edits_body)
    repo = timeline.adopter
    change = fc.run_change_check(repo.root, "main")
    assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]

    repo.checkout("main")
    squash = timeline.squash_merge("topic")
    result = _run(timeline)
    assert _point(result) == history.revalidated
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", squash)]


def test_an_earlier_looking_at_written_by_hand_is_a_revalidation(timeline: Timeline) -> None:
    """Which came first is read from the history, never the timestamps: an `at` the guide
    never carried, though earlier than the one it replaces, revalidates in both checks."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide(at=T2)})
    repo.checkout("topic", create=True)
    timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    revalidated = timeline.commit(
        "revalidate, the clock behind",
        {"docs/guide.md": guide(at=T1, because="checked against the CLI change")},
    )
    change = fc.run_change_check(repo.root, "main")
    assert [(f.kind, f.answer) for f in change.findings] == [
        (fc.FindingKind.ANSWERED, fc.Answer.UNCHANGED)
    ]
    assert [a.status for a in change.answers] == [fc.AnswerStatus.STANDS]
    repo.checkout("main")
    timeline.merge("topic")
    result = _run(timeline)
    assert _point(result) == revalidated
    assert _summary(result) == []


@dataclass(frozen=True)
class Dropped:
    """The commits `_deferral_dropped` lays down."""

    base: str
    deferred: str  # d0: the CLI deferred
    revalidated: str  # r1: revalidated, the deferral dropped
    changed: str  # c2: the CLI changed again


REASON = "the CLI rework is not settled"


def _deferral_dropped(timeline: Timeline) -> Dropped:
    """`base` at T1; the CLI changes; d0 defers it; r1 revalidates and drops the deferral;
    c2 changes the CLI again; then a branch `undo` is cut from main."""
    base = timeline.start({"docs/guide.md": guide()}, friction_config(mode="enforcing"))
    timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    deferred = timeline.commit(
        "defer the CLI", {"docs/guide.md": guide(deferred=[("path", "src/cli/**", REASON)])}
    )
    revalidated = timeline.commit(
        "revalidate, dropping the deferral",
        {"docs/guide.md": guide(at=T2, because="the CLI rework settled")},
    )
    changed = timeline.commit("change the CLI again", {"src/cli/main.py": "print('cli v3')\n"})
    timeline.adopter.checkout("undo", create=True)
    return Dropped(base, deferred, revalidated, changed)


@pytest.mark.parametrize("how", ["revert", "by-hand"])
def test_a_dropped_deferral_put_back_covers_only_what_it_did(timeline: Timeline, how: str) -> None:
    """Reverting the revalidation that dropped a deferral — or writing the same entry back by
    hand — puts back an entry the guide carried before: it keeps its first point, d0, and
    covers the CLI only as it stood there. The CLI changed since, so the change check asks,
    naming the put-back; once landed, the guide is stale from c2, its deferral point d0."""
    history = _deferral_dropped(timeline)
    if how == "revert":
        timeline.revert(history.revalidated)
    else:
        timeline.commit(
            "write the deferral back",
            {"docs/guide.md": guide(deferred=[("path", "src/cli/**", REASON)])},
        )
    repo = timeline.adopter
    change = fc.run_change_check(repo.root, "main")
    assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]
    (finding,) = [f for f in change.findings if f.kind is fc.FindingKind.FRICTION]
    assert (
        f"its deferral repeats one it carried before (since {history.deferred[:12]}), which "
        f"covers only what that one did — revalidate the artefact, or defer with a new reason"
    ) in finding.message
    assert change.failed
    deferral = next(a for a in change.answers if a.anchor is not None)
    assert (deferral.status, deferral.asked) == (fc.AnswerStatus.WRITTEN_BACK, False)

    repo.checkout("main")
    timeline.merge("undo")
    result = _run(timeline)
    assert _point(result) == history.base
    assert _summary(result) == [
        ("stale", "docs/guide.md", "path:src/cli/**", history.changed),
        ("deferred", "docs/guide.md", "path:src/cli/**", history.deferred),
    ]


def test_a_deferral_with_a_new_reason_covers_the_anchor_as_it_stands(timeline: Timeline) -> None:
    """The same history, the deferral written back with a new reason: it is new, so it covers
    the CLI as it stands — answered in the change check, deferred once landed."""
    _deferral_dropped(timeline)
    written = timeline.commit(
        "defer the CLI anew",
        {"docs/guide.md": guide(deferred=[("path", "src/cli/**", "waiting for the v3 docs")])},
    )
    repo = timeline.adopter
    change = fc.run_change_check(repo.root, "main")
    assert [(f.kind, f.answer) for f in change.findings] == [
        (fc.FindingKind.ANSWERED, fc.Answer.DEFERRED)
    ]
    deferral = next(a for a in change.answers if a.anchor is not None)
    assert (deferral.status, deferral.asked) == (fc.AnswerStatus.STANDS, True)
    repo.checkout("main")
    timeline.merge("undo")
    result = _run(timeline)
    assert _summary(result) == [("deferred", "docs/guide.md", "path:src/cli/**", written)]
    assert result.artefact_reports[0].state is fr.ArtefactState.DEFERRED


# --- where stale debt originates (COR-050 point 9) -----------------------------------------

LINES = "a\nb\nc\nd\ne\nf\ng\n"


def test_an_edit_put_back_and_made_again_is_dated_from_the_second_edit(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("first edit", {"src/cli/main.py": "print('one')\n"})
    timeline.commit("put it back", {"src/cli/main.py": CLI_SOURCE})
    second = timeline.commit("second edit", {"src/cli/main.py": "print('two')\n"})
    assert _summary(_run(timeline)) == [("stale", "docs/guide.md", "path:src/cli/**", second)]


def test_a_change_landed_beside_a_branch_that_undid_its_own_is_dated_from_it(
    timeline: Timeline,
) -> None:
    """Y lands on main while a branch edits the record, re-answers the guide and reverts it
    all; merged, the branch's commits touched the record, but the record is as the point saw
    it — only Y stands."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide(anchors=ANCHORED)})
    text = _record(timeline)
    repo.checkout("topic", create=True)
    amended = timeline.commit(
        "amend the record and re-answer",
        {
            RECORD: text + "\nAmended.\n",
            "docs/guide.md": guide(anchors=ANCHORED, at=T2, because="x"),
        },
    )
    timeline.revert(amended)
    repo.checkout("main")
    landed = timeline.commit("Y: change the CLI", {"src/cli/main.py": "print('Y')\n"})
    timeline.merge("topic")
    assert _summary(_run(timeline)) == [("stale", "docs/guide.md", "path:src/cli/**", landed)]


@pytest.mark.parametrize("order", ["Y-X-revert", "X-Y-revert"])
def test_a_revert_of_one_edit_leaves_the_file_dated_from_its_oldest_edit_standing(
    timeline: Timeline, order: str
) -> None:
    """Origins are read per file: Y and X edit different lines of one file, X is reverted.
    The file differs from the point by Y alone, and its oldest change no commit put back is
    the older of the two — X itself where it came first: the file was never put back."""
    timeline.start({"docs/guide.md": guide(), "src/cli/lines.txt": LINES})
    first, second = ("Y", "X") if order == "Y-X-revert" else ("X", "Y")
    edits = {"Y": ("b", "B"), "X": ("f", "F")}
    text = LINES
    made: dict[str, str] = {}
    for name in (first, second):
        old, new = edits[name]
        text = text.replace(old, new)
        made[name] = timeline.commit(f"{name}: edit a line", {"src/cli/lines.txt": text})
    timeline.revert(made["X"])
    assert _summary(_run(timeline)) == [("stale", "docs/guide.md", "path:src/cli/**", made[first])]


# --- a revalidation copied onto another line of work (COR-050 point 3) ----------------------


@pytest.mark.parametrize("both", [False, True], ids=["release-alone-differs", "both-differ"])
def test_a_revalidation_copied_onto_a_release_line_and_merged_back(
    timeline: Timeline, both: bool
) -> None:
    """Main changes the CLI and revalidates; the revalidation is cherry-picked onto a release
    line cut before the change. Each copy is a point, and the CLI has changed only where it
    differs from both: merged back with nothing new, the guide is current and the merge's
    change check asks nothing; with the CLI changed since on both lines, it is stale and the
    change check asks."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    repo.checkout("release", create=True)
    repo.checkout("main")
    timeline.commit("main: change the CLI", {"src/cli/main.py": "print('main')\n"})
    revalidated = timeline.commit(
        "main: revalidate the guide", {"docs/guide.md": guide(at=T2, because="checked on main")}
    )
    repo.checkout("release")
    copied = timeline.cherry_pick(revalidated)
    if both:
        timeline.commit("release: add a flag", {"src/cli/flags.py": "FLAGS = ()\n"})
        repo.checkout("main")
        timeline.commit("main: change the CLI again", {"src/cli/main.py": "print('again')\n"})
    repo.checkout("main")
    repo.checkout("land", create=True)
    timeline.merge("release")

    change = fc.run_change_check(repo.root, "main")
    result = _run(timeline)
    assert _point(result) in (revalidated, copied)
    if both:
        assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]
        assert [kind for kind, *_ in _summary(result)] == ["stale"]
    else:
        assert _friction(change) == []
        assert _summary(result) == []


# --- the stated limits, pinned (COR-050 points 3 and 6) ------------------------------------


def test_a_page_deleted_and_restored_reads_as_new_in_both_checks(timeline: Timeline) -> None:
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    timeline.commit("drop the guide", {"docs/guide.md": None})
    repo.checkout("restore", create=True)
    restored = timeline.commit("restore the guide", {"docs/guide.md": guide()})
    change = fc.run_change_check(repo.root, "main")
    assert [(f.kind, f.answer) for f in change.findings] == [
        (fc.FindingKind.ANSWERED, fc.Answer.NEW)
    ]
    repo.checkout("main")
    timeline.merge("restore")
    result = _run(timeline)
    assert _point(result) == restored
    assert _summary(result) == []


def _rules(**entries: dict[str, Any]) -> str:
    """A collection file: each entry anchored to the engine, revalidated at its `at`."""
    front = {
        entry: {
            "pkit": {
                "friction": {
                    "anchors": {"path": ["src/core/**"]},
                    "revalidated": {
                        "at": fields["at"],
                        "outcome": "unchanged",
                        "unchanged-because": fields.get("because", "holds"),
                    },
                }
            }
        }
        for entry, fields in entries.items()
    }
    body = "".join(f"## {entry} — Rule\n\nText of {entry}.\n\n" for entry in entries)
    return f"---\n{json.dumps(front)}\n---\n\n{body}"


def test_a_collection_entry_deleted_and_restored_reads_as_new_in_both_checks(
    timeline: Timeline,
) -> None:
    repo = timeline.adopter
    timeline.start({"docs/rules.md": _rules(**{"RS-1": {"at": T1}, "RS-2": {"at": T1}})})
    changed = timeline.commit("change the engine", {"src/core/engine.py": "ENGINE = 2\n"})
    timeline.commit("drop RS-1", {"docs/rules.md": _rules(**{"RS-2": {"at": T1}})})
    repo.checkout("restore", create=True)
    restored = timeline.commit(
        "restore RS-1", {"docs/rules.md": _rules(**{"RS-1": {"at": T1}, "RS-2": {"at": T1}})}
    )
    change = fc.run_change_check(repo.root, "main")
    assert [(f.location, f.answer) for f in change.findings] == [
        ("docs/rules.md#RS-1", fc.Answer.NEW)
    ]
    repo.checkout("main")
    timeline.merge("restore")
    result = _run(timeline)
    assert _point(result, "docs/rules.md#RS-1") == restored
    assert _summary(result) == [("stale", "docs/rules.md#RS-2", "path:src/core/**", changed)]


def test_an_entry_moved_to_another_collection_with_an_earlier_at_reads_as_new(
    timeline: Timeline,
) -> None:
    """An entry's history starts where it was added to its file: moved to another collection
    with an `at` it carried before, the value is new there — a revalidation, never a write-back."""
    repo = timeline.adopter
    timeline.start({"docs/rules.md": _rules(**{"RS-1": {"at": T1}, "RS-2": {"at": T1}})})
    timeline.commit(
        "revalidate RS-1",
        {"docs/rules.md": _rules(**{"RS-1": {"at": T2, "because": "checked"}, "RS-2": {"at": T1}})},
    )
    repo.checkout("move", create=True)
    moved = timeline.commit(
        "move RS-1 to the other collection, its earlier at back",
        {
            "docs/rules.md": _rules(**{"RS-2": {"at": T1}}),
            "docs/more.md": _rules(**{"RS-1": {"at": T1, "because": "moved; still holds"}}),
        },
    )
    change = fc.run_change_check(repo.root, "main")
    assert [(f.location, f.kind, f.answer) for f in change.findings] == [
        ("docs/more.md#RS-1", fc.FindingKind.ANSWERED, fc.Answer.UNCHANGED)
    ]
    assert [a.status for a in change.answers] == [fc.AnswerStatus.STANDS]
    repo.checkout("main")
    timeline.merge("move")
    result = _run(timeline)
    assert _point(result, "docs/more.md#RS-1") == moved
    assert _summary(result) == []


def test_a_mode_change_is_a_change_in_both_checks(timeline: Timeline) -> None:
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    repo.checkout("topic", create=True)
    (repo.root / "src/cli/main.py").chmod(0o755)
    made = timeline.commit("make the CLI executable", {})
    change = fc.run_change_check(repo.root, "main")
    assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]
    repo.checkout("main")
    timeline.merge("topic")
    assert _summary(_run(timeline)) == [("stale", "docs/guide.md", "path:src/cli/**", made)]


def _notes(body: str) -> str:
    return document(
        "engine-notes", anchors={"path": ["src/core/**"]}, at=T1, outcome="updated", body=body
    )


def _overview(at: str, because: str | None = None) -> str:
    return document(
        "overview",
        anchors={"artefact": ["engine-notes"]},
        at=at,
        outcome="unchanged",
        because=because or "the notes hold",
    )


def test_an_artefact_anchors_target_is_read_at_the_points_commit(timeline: Timeline) -> None:
    """The point's commit took the target whole from a merged side, while main's own edit is
    newer in the log: the target is read at the point's commit, never at the newest covered
    version — so an edit put back to what the point saw is no change."""
    repo = timeline.adopter
    timeline.start({"docs/a-engine.md": _notes("Engine."), "docs/b-overview.md": _overview(T1)})
    repo.checkout("side", create=True)
    timeline.commit("side: rewrite the notes", {"docs/a-engine.md": _notes("Engine, side.")})
    repo.checkout("main")
    timeline.commit("main: rewrite the notes", {"docs/a-engine.md": _notes("Engine, main.")})
    merging = repo.git("merge", "-q", "--no-ff", "--no-commit", "side", check=False)
    assert merging.returncode == 1, merging.stdout + merging.stderr
    timeline.commit("merge side, taking its notes", {"docs/a-engine.md": _notes("Engine, side.")})
    timeline.commit(
        "revalidate the overview", {"docs/b-overview.md": _overview(T2, "the side's notes hold")}
    )
    timeline.commit("edit the notes", {"docs/a-engine.md": _notes("Engine, edited.")})
    timeline.commit("put the notes back", {"docs/a-engine.md": _notes("Engine, side.")})
    result = _run(timeline)
    assert _summary(result) == []
    assert {r.location: r.state for r in result.artefact_reports}["docs/b-overview.md"] is (
        fr.ArtefactState.CURRENT
    )


# --- widenings, read as the file stood when they took it (COR-050 points 5 and 7) ----------


def test_a_widening_reads_the_file_as_the_newest_widening_took_it(timeline: Timeline) -> None:
    """Widened, narrowed, edited while the anchor stood on the file, widened again: the file
    as the last widening took it differs from the point, so the guide is stale from the edit."""
    timeline.start({"docs/guide.md": guide(), **GENERATED})
    timeline.commit("exclude the table", {CONFIG: friction_config(exclude=["src/cli/generated"])})
    timeline.commit("stop excluding it", {CONFIG: friction_config()})
    edited = timeline.commit("regenerate the table", {"src/cli/generated/table.py": "T = 2\n"})
    timeline.commit("exclude it again", {CONFIG: friction_config(exclude=["src/cli/generated"])})
    result = _run(timeline)
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", edited)]


def test_a_widening_then_an_edit_of_what_it_left_out_asks_more_in_the_change_check(
    timeline: Timeline,
) -> None:
    """One change widens `friction.exclude` over a file, then edits it while left out: the
    change check compares base and head and asks; `check --all` reads the file as the
    widening took it — unchanged — and reports `left-out`. One of the cases where the checks
    part (COR-050, "Where the two checks part")."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide(), **GENERATED})
    repo.checkout("topic", create=True)
    widened = timeline.commit(
        "exclude the table", {CONFIG: friction_config(exclude=["src/cli/generated"])}
    )
    timeline.commit("regenerate the table, excluded", {"src/cli/generated/table.py": "T = 2\n"})
    change = fc.run_change_check(repo.root, "main")
    assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]
    repo.checkout("main")
    timeline.merge("topic")
    assert _summary(_run(timeline)) == [("left-out", "docs/guide.md", "path:src/cli/**", widened)]


def test_a_deferred_anchor_put_back_as_it_stood_at_the_deferral_is_deferred(
    timeline: Timeline,
) -> None:
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    deferred = timeline.commit(
        "defer the CLI", {"docs/guide.md": guide(deferred=[("path", "src/cli/**", REASON)])}
    )
    timeline.commit("change the CLI again", {"src/cli/main.py": "print('cli v3')\n"})
    timeline.commit("put it back as it was deferred", {"src/cli/main.py": "print('cli v2')\n"})
    result = _run(timeline)
    assert _summary(result) == [("deferred", "docs/guide.md", "path:src/cli/**", deferred)]
    assert result.artefact_reports[0].state is fr.ArtefactState.DEFERRED


# --- a shallow clone, and the write-back search ----------------------------------------------


def _clone(repo: GitRepo, target: Path, depth: int) -> GitRepo:
    repo.git("clone", "-q", "--depth", str(depth), f"file://{repo.root}", str(target))
    clone = GitRepo(target)
    clone.git("config", "user.name", "Clone")
    clone.git("config", "user.email", "clone@example.com")
    clone.git("config", "commit.gpgsign", "false")
    return clone


def test_a_value_first_carried_inside_a_shallow_clone_has_its_point_there(
    timeline: Timeline, tmp_path: Path
) -> None:
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("cli 2", {"src/cli/main.py": "print('2')\n"})
    timeline.commit("cli 3", {"src/cli/main.py": "print('3')\n"})
    revalidated = timeline.commit(
        "revalidate", {"docs/guide.md": guide(at=T2, because="checked against cli 3")}
    )
    changed = timeline.commit("cli 4", {"src/cli/main.py": "print('4')\n"})
    clone = _clone(timeline.adopter, tmp_path / "shallow", depth=3)
    result = fr.run_repository_check(clone.root)
    assert result.shallow is True
    (report,) = result.artefact_reports
    assert report.revalidation_point is not None and report.revalidation_point.sha == revalidated
    assert report.cut is True
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", changed)]
    assert json.loads(fr.render_json(result))["artefacts"][0]["cut"] is True
    assert "the clone is cut before it" in fr.render_human(result, now=NOW)


def test_the_change_check_reads_a_write_back_past_the_cut_as_new_and_says_so(
    timeline: Timeline, tmp_path: Path
) -> None:
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("revalidate", {"docs/guide.md": guide(at=T2, because="checked")})
    timeline.commit("cli 2", {"src/cli/main.py": "print('2')\n"})
    timeline.commit("cli 3", {"src/cli/main.py": "print('3')\n"})
    clone = _clone(timeline.adopter, tmp_path / "shallow", depth=2)
    clone.checkout("topic", create=True)
    clone.commit("write the first at back", {"docs/guide.md": guide(because="read again")})

    change = fc.run_change_check(clone.root, "main")
    assert (change.shallow, change.cut) == (True, ("docs/guide.md",))
    assert [a.status for a in change.answers] == [fc.AnswerStatus.STANDS]
    document_ = json.loads(fc.render_json(change))
    assert document_["history"] == {"shallow": True, "cut": ["docs/guide.md"]}
    assert document_["schema_version"] == 1
    assert (
        "History: shallow — 1 artefact read without history beyond the cut (docs/guide.md)"
        in fc.render_human(change)
    )


def test_a_value_first_written_by_a_merge_resolution_is_found_by_the_write_back_search(
    timeline: Timeline,
) -> None:
    """The search is `git log -S` read against each parent of a merge (`-m`): an `at` first
    written while resolving a merge is found, so writing it back later is a write-back."""
    history = _revalidated_while_merging(timeline)
    repo = timeline.adopter
    repo.checkout("main")
    timeline.merge("topic")
    later = timeline.commit(
        "revalidate again", {"docs/guide.md": guide(at=T4, because="checked once more")}
    )
    repo.checkout("undo", create=True)
    timeline.revert(later)
    change = fc.run_change_check(repo.root, "main")
    assert [a.status for a in change.answers] == [fc.AnswerStatus.WRITTEN_BACK]
    assert [f.kind for f in change.findings] == []
    repo.checkout("main")
    timeline.merge("undo")
    assert _point(_run(timeline)) == history.merge


# --- an `at` in any spelling YAML's timestamp grammar allows (COR-050 point 3) -----------
#
# Validation accepts any spelling YAML's timestamp grammar resolves to a UTC instant, so
# both checks must find a value however it was typed: the walk's byte prefilter and the
# change check's reading of a file's history (`friction_history.stamps_in`).

#: The instant 2026-01-01T09:00:00Z as a hand might type it, each a spelling validation
#: accepts — unquoted, the parsed time is what is checked; quoted, only the canonical form.
SPELLINGS = {
    "space": "2026-01-01 09:00:00Z",
    "lowercase-t": "2026-01-01t09:00:00Z",
    "unpadded": "2026-1-1 9:00:00Z",
    "spaces-and-zone": "2026-01-01   09:00:00 Z",
    "fraction": "2026-01-01T09:00:00.000Z",
    "utc-offset": "2026-01-01 09:00:00 +00:00",
    "two-lines": "2026-01-01\n        09:00:00Z",
    "quoted": '"2026-01-01T09:00:00Z"',
    "unquoted": "2026-01-01T09:00:00Z",
}


def _typed_guide(at: str, because: str = "the CLI surface is as described") -> str:
    """The guide anchored to the CLI and to COR-050, its front matter in block YAML, so
    `at` stands in the file exactly as typed."""
    return (
        "---\nid: guide\npkit:\n  friction:\n    anchors:\n      path: [src/cli/**]\n"
        "      record: [COR-050]\n    revalidated:\n"
        f"      at: {at}\n      outcome: unchanged\n      unchanged-because: {because}\n"
        "---\n\nBody.\n"
    )


@pytest.mark.parametrize(
    "written",
    [*SPELLINGS.values(), "2026-01-01T11:00:00+02:00", "2026-01-01 04:00:00 -05"],
)
def test_every_spelling_of_a_time_reads_as_the_instant_it_denotes(written: str) -> None:
    assert fh.stamps_in(f"at: {written}\n".encode()) == {"2026-01-01T09:00:00": 1}


def test_the_history_reading_lists_a_time_changed_in_its_last_digit(timeline: Timeline) -> None:
    """A collection's front matter is one line, so a revalidation that changes one entry's
    `at` in its last digit shares all but that with the line before it: the reading still
    lists the commit for both times, and for no time it left alone."""
    base = timeline.start(
        {"docs/rules.md": _rules(**{"RS-1": {"at": "2026-10-01T09:00:01Z"}, "RS-2": {"at": T1}})}
    )
    changed = timeline.commit(
        "revalidate RS-1",
        {
            "docs/rules.md": _rules(
                **{"RS-1": {"at": "2026-10-01T09:00:02Z", "because": "checked"}, "RS-2": {"at": T1}}
            )
        },
    )

    def at(text: str) -> datetime:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))

    writes = fh.read_writes(timeline.adopter.root, "HEAD", "docs/rules.md")
    assert writes.of(at("2026-10-01T09:00:02Z")) == {changed}
    assert writes.of(at("2026-10-01T09:00:01Z")) == {base, changed}
    assert writes.of(at(T1)) == {base}


@pytest.mark.parametrize("spelling", sorted(SPELLINGS))
def test_reverting_a_revalidation_back_to_a_stamp_in_any_spelling_brings_back_its_debt(
    timeline: Timeline, spelling: str
) -> None:
    """The critic's history A: c0 types its `at` in one spelling; Y amends the record,
    unanswered; X amends it again and revalidates with a canonical `at`; a branch reverts
    X. The value written back is found whatever its spelling: the change check judges it
    against c0 and asks about the record — enforcing mode fails — and once landed the
    guide is stale from Y, at c0."""
    repo = timeline.adopter
    base = timeline.start(
        {"docs/guide.md": _typed_guide(SPELLINGS[spelling])}, friction_config(mode="enforcing")
    )
    text = _record(timeline)
    owed = timeline.commit("Y: amend the record", {RECORD: text + "\nY.\n"})
    answered = timeline.commit(
        "X: amend the record again, revalidate the guide",
        {
            RECORD: text + "\nY.\n\nX.\n",
            "docs/guide.md": _typed_guide(T2, "checked against Y and X"),
        },
    )
    repo.checkout("undo", create=True)
    timeline.revert(answered)

    change = fc.run_change_check(repo.root, "main")
    assert _friction(change) == [("docs/guide.md", "record:COR-050")]
    assert change.failed
    assert [a.status for a in change.answers] == [fc.AnswerStatus.WRITTEN_BACK]
    repo.checkout("main")
    timeline.merge("undo")
    result = _run(timeline)
    assert _point(result) == base
    assert _summary(result) == [("stale", "docs/guide.md", "record:COR-050", owed)]


@pytest.mark.parametrize("spelling", sorted(SPELLINGS))
def test_restating_a_stamp_in_another_spelling_is_no_revalidation(
    timeline: Timeline, spelling: str
) -> None:
    """The critic's history B: c0 types its `at` in one spelling; Y changes the CLI; F
    writes the same instant in another. F is no revalidation: the change check lists no
    answer, and once landed the point is still c0 and Y's debt stays."""
    repo = timeline.adopter
    base = timeline.start({"docs/guide.md": _typed_guide(SPELLINGS[spelling])})
    owed = timeline.commit("Y: change the CLI", {"src/cli/main.py": "print('Y')\n"})
    repo.checkout("restate", create=True)
    restated = SPELLINGS["unpadded" if spelling == "quoted" else "quoted"]
    timeline.commit("F: restate the stamp", {"docs/guide.md": _typed_guide(restated)})

    change = fc.run_change_check(repo.root, "main")
    assert (change.findings, change.answers) == ((), ())
    repo.checkout("main")
    timeline.merge("restate")
    result = _run(timeline)
    assert _point(result) == base
    assert _summary(result) == [("stale", "docs/guide.md", "path:src/cli/**", owed)]


# --- an anchor judged as a whole (COR-050 points 3, 4 and 9) ---------------------------------
#
# With several answering states, an anchor has changed only where what it stands on
# differs from what it stood on at every one of them — at each, some part — never part by
# part. Both checks judge by that rule (`friction_history.changed_since`).


def _parts(a: str, b: str) -> dict[str, str]:
    """Two files under the CLI anchor, `a.py` and `b.py`, holding `a` and `b`."""
    return {"src/cli/a.py": f"A = '{a}'\n", "src/cli/b.py": f"B = '{b}'\n"}


def test_an_anchor_is_judged_as_a_whole_against_its_point_and_its_deferral(
    timeline: Timeline,
) -> None:
    """The critic's history: P is revalidated at (a0, b0); c1 changes both files; d defers
    the anchor at (a1, b1); c2 puts a.py back. (a0, b1) is no file-by-file match for
    either state, yet differs from P's (a0, b0) and from d's (a1, b1) as a whole: new
    friction — the change check on c2 asks, and once landed the guide is stale from c2,
    its debt dated where it came to differ from both."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide(), **_parts("a0", "b0")})
    timeline.commit("c1: change both", _parts("a1", "b1"))
    deferred = timeline.commit(
        "d: defer the CLI", {"docs/guide.md": guide(deferred=[("path", "src/cli/**", REASON)])}
    )
    repo.checkout("partial", create=True)
    put_back = timeline.commit("c2: put a.py back", {"src/cli/a.py": "A = 'a0'\n"})

    change = fc.run_change_check(repo.root, "main")
    assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]
    repo.checkout("main")
    timeline.merge("partial")
    result = _run(timeline)
    assert _summary(result) == [
        ("stale", "docs/guide.md", "path:src/cli/**", put_back),
        ("deferred", "docs/guide.md", "path:src/cli/**", deferred),
    ]
    assert result.artefact_reports[0].state is fr.ArtefactState.STALE


@dataclass(frozen=True)
class Copied:
    """The commits `_copied_onto_release` lays down."""

    revalidated: str  # P1, on main
    copied: str  # P2, its cherry-pick on the release line


def _copied_onto_release(timeline: Timeline) -> Copied:
    """Main changes a.py and revalidates (P1, at (a1, b0)); the release line, cut at the
    base, changes b.py and takes the revalidation (P2, at (a0, b1)); a branch `land` off
    main merges the release line: (a1, b1)."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide(), **_parts("a0", "b0")})
    repo.checkout("release", create=True)
    repo.checkout("main")
    timeline.commit("main: change a.py", {"src/cli/a.py": "A = 'a1'\n"})
    revalidated = timeline.commit(
        "main: revalidate", {"docs/guide.md": guide(at=T2, because="checked a1")}
    )
    repo.checkout("release")
    timeline.commit("release: change b.py", {"src/cli/b.py": "B = 'b1'\n"})
    copied = timeline.cherry_pick(revalidated)
    repo.checkout("main")
    repo.checkout("land", create=True)
    timeline.merge("release")
    return Copied(revalidated, copied)


def test_a_revalidation_copied_onto_a_release_line_is_judged_as_a_whole(timeline: Timeline) -> None:
    """The critic's cherry-pick variant: merged, HEAD's a.py matches P1 and its b.py
    matches P2, but the anchor as a whole matches neither — stale, as the merge's change
    check asks. Both points are reported, in the JSON documents and in `explain`."""
    history = _copied_onto_release(timeline)
    repo = timeline.adopter
    change = fc.run_change_check(repo.root, "main")
    assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]

    result = _run(timeline)
    assert [kind for kind, *_ in _summary(result)] == ["stale"]
    (report,) = result.artefact_reports
    points = {history.revalidated, history.copied}
    assert {p.sha for p in report.revalidation_points} == points
    assert report.revalidation_point == report.revalidation_points[0]
    listed = json.loads(fr.render_json(result))["artefacts"][0]["revalidation_points"]
    assert {p["commit"] for p in listed} == points

    explanation = frep.run_explain(repo.root, "docs/guide.md")
    explained = json.loads(frep.render_explain_json(explanation))
    assert {p["commit"] for p in explained["revalidation_points"]} == points
    human = frep.render_explain_human(explanation, now=NOW)
    assert all(f"revalidation  {sha[:12]}" in human for sha in points)


@pytest.mark.parametrize("both", [False, True], ids=["one-point-differs", "both-differ"])
def test_an_at_written_back_with_two_points_is_asked_only_where_it_differs_from_both(
    timeline: Timeline, both: bool
) -> None:
    """A revalidation copied onto a release line merged back leaves its `at` with two
    points. Main revalidates again and a branch reverts that: the `at` written back is
    judged against both points, and the change check asks only where the anchor differs
    from each — not where the CLI matches main's point and differs only from the release
    line's, yes once main changed it again. `check --all` agrees once it lands."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    repo.checkout("release", create=True)
    repo.checkout("main")
    timeline.commit("main: change the CLI", {"src/cli/main.py": "print('main')\n"})
    revalidated = timeline.commit(
        "main: revalidate", {"docs/guide.md": guide(at=T2, because="checked on main")}
    )
    repo.checkout("release")
    timeline.cherry_pick(revalidated)
    repo.checkout("main")
    timeline.merge("release")
    if both:
        timeline.commit("main: change the CLI again", {"src/cli/main.py": "print('again')\n"})
    again = timeline.commit(
        "main: revalidate again", {"docs/guide.md": guide(at=T3, because="checked once more")}
    )
    repo.checkout("undo", create=True)
    timeline.revert(again)

    change = fc.run_change_check(repo.root, "main")
    assert [a.status for a in change.answers] == [fc.AnswerStatus.WRITTEN_BACK]
    assert _friction(change) == ([("docs/guide.md", "path:src/cli/**")] if both else [])
    repo.checkout("main")
    timeline.merge("undo")
    result = _run(timeline)
    assert len(result.artefact_reports[0].revalidation_points) == 2
    assert [kind for kind, *_ in _summary(result)] == (["stale"] if both else [])


def test_merging_the_original_revalidation_into_its_copys_line_asks_in_the_change_check_only(
    timeline: Timeline,
) -> None:
    """Main changes the CLI and revalidates; the release line takes the revalidation. A
    branch off release merges main, bringing the change the revalidation answered: the
    change check compares release with the merge and asks; `check --all`, with both
    points, finds the guide current — a case where the two checks part (CLI README)."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    repo.checkout("release", create=True)
    repo.checkout("main")
    timeline.commit("main: change the CLI", {"src/cli/main.py": "print('main')\n"})
    revalidated = timeline.commit(
        "main: revalidate", {"docs/guide.md": guide(at=T2, because="checked on main")}
    )
    repo.checkout("release")
    timeline.cherry_pick(revalidated)
    repo.checkout("forward", create=True)
    timeline.merge("main")

    change = fc.run_change_check(repo.root, "release")
    assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]
    assert _summary(_run(timeline)) == []


def test_each_answering_state_is_read_under_its_own_exclusions(timeline: Timeline) -> None:
    """The table is excluded at the revalidation point; a narrowing lets it in, a deferral
    then covers the anchor, and the table is edited and put back. Read under its own
    exclusions, the deferral's state holds the table as HEAD does: the guide is deferred,
    not stale — read under the point's exclusions, the table would be a let-in, which
    always counts, and the edit put back a change nothing answered. A change to the table
    that stands makes it stale."""
    timeline.start(
        {"docs/guide.md": guide(), **GENERATED}, friction_config(exclude=["src/cli/generated"])
    )
    timeline.commit("let the table in", {CONFIG: friction_config()})
    deferred = timeline.commit(
        "defer the CLI", {"docs/guide.md": guide(deferred=[("path", "src/cli/**", REASON)])}
    )
    timeline.commit("regenerate the table", {"src/cli/generated/table.py": "T = 9\n"})
    timeline.commit("put the table back", GENERATED)
    assert _summary(_run(timeline)) == [("deferred", "docs/guide.md", "path:src/cli/**", deferred)]

    edited = timeline.commit("regenerate it again", {"src/cli/generated/table.py": "T = 2\n"})
    assert _summary(_run(timeline)) == [
        ("stale", "docs/guide.md", "path:src/cli/**", edited),
        ("deferred", "docs/guide.md", "path:src/cli/**", deferred),
    ]


# --- what a merge that takes one side whole hides from `check --all` (stated limits) --------


def test_an_edit_undone_by_a_merge_taking_one_side_whole_still_dates_the_debt(
    timeline: Timeline,
) -> None:
    """A stated limit: e1 edits the CLI after the point; a merge that takes the CLI file
    whole from the other side undoes it; e2 edits it again. git's combined diff does not
    list the file for that merge, so it is never read as putting the file back: the debt
    is dated from e1, where the record dates it from e2."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    repo.checkout("side", create=True)
    timeline.commit("side: a note", NOTE)
    repo.checkout("main")
    first = timeline.commit("e1: edit the CLI", {"src/cli/main.py": "print('e1')\n"})
    repo.git("merge", "-q", "--no-ff", "--no-commit", "side", check=False)
    timeline.commit("merge side, taking its CLI", {"src/cli/main.py": CLI_SOURCE})
    timeline.commit("e2: edit the CLI again", {"src/cli/main.py": "print('e2')\n"})
    assert _summary(_run(timeline)) == [("stale", "docs/guide.md", "path:src/cli/**", first)]


def test_a_merge_taking_back_a_file_from_before_the_point_reads_as_no_change(
    timeline: Timeline,
) -> None:
    """A stated limit: after the point P that answered c's edit of the CLI, a merge takes
    the file whole from a line cut before c, putting back what it was before c. git's
    combined diff does not list it and no commit after P touched it, so `check --all`
    reads no change though HEAD differs from P; the change check, comparing its base with
    the merge, asks."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    repo.checkout("old", create=True)
    timeline.commit("old: a note", NOTE)
    repo.checkout("main")
    timeline.commit("c: edit the CLI", {"src/cli/main.py": "print('c')\n"})
    timeline.commit("P: revalidate", {"docs/guide.md": guide(at=T2, because="checked c")})
    repo.checkout("take", create=True)
    repo.git("merge", "-q", "--no-ff", "--no-commit", "old", check=False)
    timeline.commit("merge old, taking its CLI", {"src/cli/main.py": CLI_SOURCE})

    change = fc.run_change_check(repo.root, "main")
    assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]
    repo.checkout("main")
    timeline.merge("take")
    assert _summary(_run(timeline)) == []


# --- the change check's write-back paths, and its answers list (COR-050 points 3, 4, 6) -----


def test_an_at_removed_is_judged_against_the_blocks_introduction_and_listed_edited(
    timeline: Timeline,
) -> None:
    """The CLI changed and was answered; a branch removes the `at`. The block's own marker
    is written back, so the guide is judged against the commit that introduced the block
    and asked about the CLI; the revalidation it removed is listed `edited`, never
    `written-back`, and no bump."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"})
    timeline.commit("revalidate", {"docs/guide.md": guide(at=T2, because="checked the CLI")})
    repo.checkout("drop", create=True)
    timeline.commit("drop the at", {"docs/guide.md": guide(at=None, outcome=None, because=None)})

    change = fc.run_change_check(repo.root, "main")
    assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]
    assert change.count(fc.FindingKind.BUMP) == 0
    (answer,) = change.answers
    assert (answer.status, answer.asked, answer.kept) == (fc.AnswerStatus.EDITED, False, ())


def test_a_write_back_of_a_value_the_cut_already_carries_answers_nothing(
    timeline: Timeline, tmp_path: Path
) -> None:
    """In a shallow clone whose cut already carries the value written back, its point is
    beyond the clone: the value answers nothing and is no bump, the guide is judged
    against the base — asked about the CLI the change edits — and the header names it."""
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("cli 2", {"src/cli/main.py": "print('2')\n"})
    timeline.commit("revalidate", {"docs/guide.md": guide(at=T2, because="checked cli 2")})
    timeline.commit("cli 3", {"src/cli/main.py": "print('3')\n"})
    clone = _clone(timeline.adopter, tmp_path / "shallow", depth=3)
    clone.checkout("topic", create=True)
    clone.commit(
        "write the first at back, edit the CLI",
        {"docs/guide.md": guide(because="read again"), "src/cli/main.py": "print('4')\n"},
    )

    change = fc.run_change_check(clone.root, "main")
    assert change.cut == ("docs/guide.md",)
    assert [a.status for a in change.answers] == [fc.AnswerStatus.WRITTEN_BACK]
    assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]
    assert change.count(fc.FindingKind.BUMP) == 0


def test_a_submodule_bumped_under_a_path_anchor_is_a_change_in_both_checks(
    timeline: Timeline,
) -> None:
    """A gitlink under a path anchor is one of its parts, compared by its object: moving
    the submodule to another commit is a change — the change check asks, and once landed
    the guide is stale from the move."""
    repo = timeline.adopter
    first = timeline.start({"docs/guide.md": guide()})
    repo.git("update-index", "--add", "--cacheinfo", f"160000,{first},src/cli/vendor")
    repo.write({"docs/guide.md": guide(at=T2, because="checked with the submodule")})
    repo.git("add", "docs/guide.md")
    other = timeline.commit_index("vendor a submodule under the CLI, revalidate")
    assert _summary(_run(timeline)) == []

    repo.checkout("bump", create=True)
    repo.git("update-index", "--cacheinfo", f"160000,{other},src/cli/vendor")
    moved = timeline.commit_index("move the submodule")
    change = fc.run_change_check(repo.root, "main", named=fc.named_head(repo.root, moved))
    assert _friction(change) == [("docs/guide.md", "path:src/cli/**")]
    repo.checkout("main")
    timeline.merge("bump")
    assert _summary(_run(timeline)) == [("stale", "docs/guide.md", "path:src/cli/**", moved)]


def test_a_deferral_put_back_that_covers_its_anchor_stands_flagged_put_back(
    timeline: Timeline,
) -> None:
    """The CLI changes, d0 defers it, r1 revalidates and drops the deferral; a branch
    reverts r1. The `at` written back answers nothing; the deferral put back keeps d0's
    point and covers the CLI as it stood there, which it still is — so the check accepts
    it: `stands`, flagged `put_back`, asked for. Once landed the guide is deferred."""
    repo = timeline.adopter
    base = timeline.start({"docs/guide.md": guide()}, friction_config(mode="enforcing"))
    timeline.commit("change the CLI", {"src/cli/main.py": "print('cli v2')\n"})
    deferred = timeline.commit(
        "defer the CLI", {"docs/guide.md": guide(deferred=[("path", "src/cli/**", REASON)])}
    )
    revalidated = timeline.commit(
        "revalidate, dropping the deferral",
        {"docs/guide.md": guide(at=T2, because="the CLI rework settled")},
    )
    repo.checkout("undo", create=True)
    timeline.revert(revalidated)

    change = fc.run_change_check(repo.root, "main")
    assert [(f.kind, f.answer) for f in change.findings] == [
        (fc.FindingKind.ANSWERED, fc.Answer.DEFERRED)
    ]
    assert not change.failed
    revalidation, deferral = change.answers
    assert revalidation.status is fc.AnswerStatus.WRITTEN_BACK
    assert (deferral.status, deferral.put_back, deferral.asked) == (
        fc.AnswerStatus.STANDS,
        True,
        True,
    )
    assert json.loads(fc.render_json(change))["answers"][1]["put_back"] is True
    assert "put back: an entry it carried before, covering the anchor" in fc.render_human(change)

    repo.checkout("main")
    timeline.merge("undo")
    result = _run(timeline)
    assert _point(result) == base
    assert _summary(result) == [("deferred", "docs/guide.md", "path:src/cli/**", deferred)]


def test_a_written_back_revalidation_names_the_deferrals_it_kept(timeline: Timeline) -> None:
    """A revalidation that kept the engine's deferral, reverted: its `at` is written back
    and answers nothing, and like any revalidation whose `at` changed it names the
    deferral it keeps."""
    repo = timeline.adopter
    anchors = {"path": ["src/cli/**", "src/core/**"]}
    kept = [("path", "src/core/**", "waiting on the engine")]
    timeline.start({"docs/guide.md": guide(anchors=anchors, deferred=kept)})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"})
    revalidated = timeline.commit(
        "revalidate, keeping the engine's deferral",
        {"docs/guide.md": guide(anchors=anchors, deferred=kept, at=T2, because="checked")},
    )
    repo.checkout("undo", create=True)
    timeline.revert(revalidated)

    (answer,) = fc.run_change_check(repo.root, "main").answers
    assert answer.status is fc.AnswerStatus.WRITTEN_BACK
    assert [k.as_json() for k in answer.kept] == [
        {"anchor": {"kind": "path", "value": "src/core/**"}, "reason": "waiting on the engine"}
    ]


def test_a_side_line_that_dropped_an_entry_does_not_make_a_write_back_a_point(
    timeline: Timeline,
) -> None:
    """Where an entry was last added is read by ancestry: a side line that dropped RS-1,
    merged after main wrote RS-1's `at` back, is no place RS-1 was absent from main's
    line — so the write-back is not a point, and RS-1 is stale from the engine change its
    reverted revalidation had answered."""
    repo = timeline.adopter
    base = timeline.start({"docs/rules.md": _rules(**{"RS-1": {"at": T1}, "RS-2": {"at": T1}})})
    repo.checkout("side", create=True)
    repo.checkout("main")
    changed = timeline.commit("change the engine", {"src/core/engine.py": "ENGINE = 2\n"})
    revalidated = timeline.commit(
        "revalidate RS-1",
        {"docs/rules.md": _rules(**{"RS-1": {"at": T2, "because": "checked"}, "RS-2": {"at": T1}})},
    )
    repo.checkout("side")
    timeline.commit("side: drop RS-1", {"docs/rules.md": _rules(**{"RS-2": {"at": T1}})})
    repo.checkout("main")
    timeline.revert(revalidated)
    repo.git("merge", "-q", "--no-ff", "--no-commit", "side", check=False)
    timeline.commit(
        "merge side, keeping RS-1",
        {"docs/rules.md": _rules(**{"RS-1": {"at": T1}, "RS-2": {"at": T1}})},
    )

    result = _run(timeline)
    assert _point(result, "docs/rules.md#RS-1") == base
    assert ("stale", "docs/rules.md#RS-1", "path:src/core/**", changed) in _summary(result)
