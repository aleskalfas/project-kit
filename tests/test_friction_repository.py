"""Tests for the whole-repository friction check, `pkit friction check --all` (Task #991, COR-050).

Every test stands up a real adopter repository (`make_adopter_repo`) and lays
down real history — dated commits by named authors, renames, a squash merge,
a shallow clone — before running the check at HEAD. The documents come from
`tests.friction_documents`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import friction_repository as fr
from project_kit.cli import main
from project_kit.friction_discovery import Anchor
from tests.adopter_repo import HISTORY_EPOCH, AdopterRepo, Author, GitRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, T1, T2, document, friction_config, guide

ALICE = Author("Alice", "alice@example.com")
BOB = Author("Bob", "bob@example.com")

# A fixed "now" for ages in the human view, well after every scripted commit.
NOW = HISTORY_EPOCH + timedelta(days=100)

CLI = Anchor("path", "src/cli/**")


class Timeline:
    """Commits on an adopter repository, each a day after the last, so origins have known dates."""

    def __init__(self, adopter: AdopterRepo) -> None:
        self.adopter = adopter
        self.days = 0

    def _next(self) -> datetime:
        self.days += 1
        return HISTORY_EPOCH + timedelta(days=self.days)

    def start(self, files: Mapping[str, str], config: str | None = None) -> str:
        """The base commit on `main`: the install, the configuration, the sources and `files`."""
        self.adopter.write({CONFIG: config or friction_config(), **SOURCE, **files})
        return self.commit("base")

    def commit(
        self,
        message: str,
        files: Mapping[str, str | None] | None = None,
        *,
        author: Author | None = None,
    ) -> str:
        return self.adopter.commit(message, files, author=author, date=self._next())

    def rename(self, src: str, dst: str) -> str:
        return self.adopter.rename(src, dst, date=self._next())

    def merge(self, branch: str) -> str:
        return self.adopter.merge(branch, date=self._next())

    def squash_merge(self, branch: str) -> str:
        return self.adopter.squash_merge(branch, date=self._next())


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
    assert f"first in {changed[:12]} \"change the CLI\"" in finding.message
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
        "matches no file (or only excluded ones)",
        "names no record",
    ]
    assert "no installed component registers a resolver" in result.findings[2].message
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
        "states",
    ]
    assert (doc["check"], doc["mode"], doc["dormant"], doc["failed"]) == (
        "repository",
        "enforcing",
        False,
        False,
    )
    assert doc["history"] == {"shallow": False}
    assert sorted(doc["head"]) == ["commit", "uncommitted_paths"]
    assert doc["counts"]["stale"] == 1 and doc["counts"]["checked"] == 1
    assert doc["states"] == {"current": 0, "deferred": 0, "stale": 1, "unreachable": 0}
    assert doc["measures"] == {"unanchored": [], "uncovered_surface": []}
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
        "deferral_points",
        "location",
        "revalidation_point",
        "state",
    ]
    assert report["state"] == "stale" and sorted(report["revalidation_point"]) == [
        "author",
        "change",
        "commit",
        "date",
    ]


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
