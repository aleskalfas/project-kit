"""Tests for the debt listing and the per-artefact explanation (Task #993, COR-050 points 9 and 13).

`pkit friction debt` and `pkit friction explain` are views of the
whole-repository check, so every test holds them to it: the debt is exactly
the check's stale and deferred findings, oldest first; an explanation's
findings are exactly the check's for that artefact, each with the commits
behind it and what clears it. Every test stands up a real adopter repository
and lays down dated history (`Timeline`); the read-only test compares every
byte of the repository, `.git` included, before and after each command.
"""

from __future__ import annotations

import json
import os
import shlex
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result

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
CAROL = Author("Carol", "carol@example.com")

# A fixed "now" for ages in the human view, well after every scripted commit.
NOW = HISTORY_EPOCH + timedelta(days=100)

CLI = Anchor("path", "src/cli/**")
CORE = Anchor("path", "src/core/**")


@pytest.fixture
def timeline(make_adopter_repo: MakeAdopterRepo) -> Timeline:
    return Timeline(make_adopter_repo())


def _cli(*args: str) -> Result:
    return CliRunner().invoke(main, ["friction", *args])


def _notes(**overrides: Any) -> str:
    """`notes`, anchored to the engine, revalidated at T1."""
    values: dict[str, Any] = {"anchors": {"path": ["src/core/**"]}, "at": T1, "outcome": "updated"}
    values.update(overrides)
    return document("notes", **values)


def _debt_history(timeline: Timeline) -> dict[str, str]:
    """`a-notes` deferred late, `b-guide` stale early: the check lists them the other way round."""
    timeline.start({"docs/a-notes.md": _notes(), "docs/b-guide.md": guide()})
    changed = timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"}, author=ALICE)
    timeline.commit("change the engine", {"src/core/engine.py": "ENGINE = 2\n"}, author=BOB)
    deferred = timeline.commit(
        "defer the notes",
        {"docs/a-notes.md": _notes(deferred=[("path", "src/core/**", "after the engine settles")])},
        author=CAROL,
    )
    timeline.commit("change the CLI again", {"src/cli/main.py": "print('3')\n"})
    return {"changed": changed, "deferred": deferred}


def _excluded_history(timeline: Timeline) -> None:
    """`docs/generated`, excluded by the second `friction.exclude` entry, holds an artefact
    gone stale with a dead anchor, a deferred one and an unanchored one; `guide` is outside."""
    timeline.start(
        {
            "docs/guide.md": guide(),
            "docs/generated/api.md": "---\nid: api\n---\n\nGenerated.\n",
            "docs/generated/cli.md": document(
                "gen-cli", anchors={"path": ["src/cli/**", "src/gone/**"]}, at=T1, outcome="updated"
            ),
            "docs/generated/notes.md": _notes(
                deferred=[("path", "src/core/**", "regenerated later")]
            ),
        },
        friction_config(exclude=["vendor", "docs/generated"]),
    )
    timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"}, author=ALICE)
    timeline.commit("change the engine", {"src/core/engine.py": "ENGINE = 2\n"}, author=BOB)


def _debt_key(kind: str, location: str, anchor: Any, origin: Any) -> tuple[str, str, str, str]:
    return (kind, location, json.dumps(anchor, sort_keys=True), origin["commit"])


# --- the debt listing ------------------------------------------------------------------


def test_debt_lists_both_kinds_oldest_first_with_their_origins(timeline: Timeline) -> None:
    shas = _debt_history(timeline)
    root = timeline.adopter.root

    listing = frep.run_debt(root)
    assert [
        (
            e.finding.kind.value,
            e.finding.location,
            e.finding.anchor,
            e.origin.sha,
            e.origin.author,
            e.origin.date,
            e.origin.subject,
            e.reason,
        )
        for e in listing.entries
    ] == [
        (
            "stale",
            "docs/b-guide.md",
            CLI,
            shas["changed"],
            "Alice",
            HISTORY_EPOCH + timedelta(days=2),
            "change the CLI",
            None,
        ),
        (
            "deferred",
            "docs/a-notes.md",
            CORE,
            shas["deferred"],
            "Carol",
            HISTORY_EPOCH + timedelta(days=4),
            "defer the notes",
            "after the engine settles",
        ),
    ]
    # The check reports them in walk order; the listing is by the age of the debt.
    check = fr.run_repository_check(root)
    assert [(f.kind.value, f.location) for f in check.findings] == [
        ("deferred", "docs/a-notes.md"),
        ("stale", "docs/b-guide.md"),
    ]


def test_debt_matches_the_whole_repository_check(timeline: Timeline) -> None:
    timeline.start(
        {
            "notes/moved.md": document("moved", anchors={"path": ["src/core/**"]}, at=T1),
            "docs/guide.md": guide(anchors={"path": ["src/cli/**", "src/gone/**", "."]}),
            "docs/notes.md": _notes(),
        },
        friction_config(places=("docs", "notes")),
    )
    timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"}, author=ALICE)
    timeline.commit(
        "defer the notes",
        {"docs/notes.md": _notes(deferred=[("path", "src/core/**", "later")])},
        author=BOB,
    )
    timeline.commit("change the engine", {"src/core/engine.py": "ENGINE = 2\n"})
    timeline.rename("notes/moved.md", "docs/moved.md")

    check = _cli("check", "--all", "--json")
    debt = _cli("debt", "--json")
    assert check.exit_code == 0 and debt.exit_code == 0, check.output + debt.output
    reported = json.loads(check.output)["findings"]
    listed = json.loads(debt.output)["debt"]
    assert {f["kind"] for f in reported} > {"stale", "deferred"}  # dead and over-broad too
    assert sorted(
        _debt_key(f["kind"], f["location"], f["anchor"], f["origin"])
        for f in reported
        if f["kind"] in ("stale", "deferred")
    ) == sorted(_debt_key(d["kind"], d["location"], d["anchor"], d["origin"]) for d in listed)
    assert {d["message"] for d in listed} == {
        f["message"] for f in reported if f["kind"] in ("stale", "deferred")
    }
    # Oldest first; the two debts of one commit keep the check's order.
    assert [
        (d["kind"], d["location"], d["anchor"] and d["anchor"]["value"], d["origin"]["change"])
        for d in listed
    ] == [
        ("stale", "docs/guide.md", "src/cli/**", "change the CLI"),
        ("stale", "docs/guide.md", ".", "change the CLI"),
        ("deferred", "docs/notes.md", "src/core/**", "defer the notes"),
        ("stale", "docs/moved.md", "src/core/**", "change the engine"),
        ("stale", "docs/notes.md", "src/core/**", "change the engine"),
        ("stale", "docs/moved.md", None, "rename notes/moved.md -> docs/moved.md"),
    ]


def test_debt_json_document_shape(timeline: Timeline) -> None:
    shas = _debt_history(timeline)
    result = _cli("debt", "--json")
    assert result.exit_code == 0, result.output
    doc = json.loads(result.output)
    assert sorted(doc) == ["counts", "debt", "dormant", "head", "history", "report", "unreachable"]
    assert (doc["report"], doc["dormant"], doc["history"]) == ("debt", False, {"shallow": False})
    assert doc["counts"] == {"deferred": 1, "stale": 1, "unreachable": 0}
    assert doc["unreachable"] == []
    stale, deferred = doc["debt"]
    assert stale == {
        "kind": "stale",
        "artefact": "guide",
        "location": "docs/b-guide.md",
        "anchor": {"kind": "path", "value": "src/cli/**"},
        "origin": {
            "commit": shas["changed"],
            "author": "Alice",
            "date": (HISTORY_EPOCH + timedelta(days=2)).isoformat(),
            "change": "change the CLI",
        },
        "reason": None,
        "message": stale["message"],
    }
    assert (deferred["kind"], deferred["reason"]) == ("deferred", "after the engine settles")


def test_debt_human_view(timeline: Timeline) -> None:
    shas = _debt_history(timeline)
    human = frep.render_debt_human(frep.run_debt(timeline.adopter.root), now=NOW)
    assert human.startswith("Friction debt — 1 stale, 1 deferred")
    lines = human.splitlines()
    stale = next(line for line in lines if shas["changed"][:12] in line)
    deferred = next(line for line in lines if shas["deferred"][:12] in line)
    assert lines.index(stale) < lines.index(deferred)
    for text in ("2026-01-03", "stale", "docs/b-guide.md", "path src/cli/**", "Alice"):
        assert text in stale
    assert stale.endswith('"change the CLI"   98 days ago')
    assert deferred.endswith("96 days ago — after the engine settles")
    assert "Legend" in human and "pkit friction explain <artefact>" in human


def test_debt_when_there_is_none_and_while_dormant(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide()})
    result = _cli("debt")
    assert result.exit_code == 0, result.output
    assert "nothing stale or deferred" in result.output

    timeline.commit("drop the places", {CONFIG: json.dumps({"friction": {}}) + "\n"})
    dormant = _cli("debt")
    assert dormant.exit_code == 0, dormant.output
    assert "no places declared; dormant." in dormant.output
    assert json.loads(_cli("debt", "--json").output)["dormant"] is True


def test_debt_leaves_out_an_artefact_under_an_excluded_path(timeline: Timeline) -> None:
    """COR-050 point 7: excluded paths are left out of the measures, the debt with them."""
    _excluded_history(timeline)
    listing = frep.run_debt(timeline.adopter.root)
    assert [(e.finding.kind.value, e.finding.location) for e in listing.entries] == [
        ("stale", "docs/guide.md")
    ]
    result = _cli("debt", "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["counts"] == {"deferred": 0, "stale": 1, "unreachable": 0}


def test_debt_names_the_artefacts_a_shallow_clone_cannot_judge(
    timeline: Timeline, tmp_path: Path
) -> None:
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    for version in (2, 3, 4):
        timeline.commit(f"cli {version}", {"src/cli/main.py": f"print('cli {version}')\n"})
    shallow = tmp_path / "shallow"
    repo.git("clone", "-q", "--depth", "2", f"file://{repo.root}", str(shallow))

    listing = frep.run_debt(shallow)
    assert (listing.shallow, listing.entries) == (True, ())
    assert [r.location for r in listing.unreachable] == ["docs/guide.md"]
    human = frep.render_debt_human(listing, now=NOW)
    assert "NOT JUDGED" in human and "git fetch --unshallow" in human


# --- the explanation ---------------------------------------------------------------------


def test_explain_names_each_changed_anchor_with_the_commits_behind_it(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide(anchors={"path": ["src/cli/**", "src/core/**"]})})
    first = timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"}, author=ALICE)
    timeline.commit("unrelated", {"README.txt": "Hello.\n"})
    second = timeline.commit(
        "change the CLI again", {"src/cli/main.py": "print('3')\n"}, author=BOB
    )

    explanation = frep.run_explain(timeline.adopter.root, "guide")
    assert explanation.state == "stale"
    assert [(a.anchor, a.state, a.changes) for a in explanation.anchors] == [
        (CLI, "stale", 2),
        (CORE, "current", 0),
    ]
    (stale,) = explanation.findings
    assert stale.finding.origin is not None and stale.finding.origin.sha == first
    assert [(c.commit.sha, c.paths) for c in stale.commits] == [
        (first, ("src/cli/main.py",)),
        (second, ("src/cli/main.py",)),
    ]
    assert [(a.answer, a.command) for a in stale.answers] == [
        ("updated", "pkit friction revalidate docs/guide.md --outcome updated"),
        (
            "unchanged",
            "pkit friction revalidate docs/guide.md --outcome unchanged "
            "--because '<why the content still holds>'",
        ),
        (
            "deferred",
            "pkit friction defer docs/guide.md --anchor 'path:src/cli/**' "
            "--reason '<why it can wait>'",
        ),
    ]
    human = frep.render_explain_human(explanation, now=NOW)
    assert f"{first[:12]}  2026-01-03  Alice  change the CLI" in human
    assert f"{second[:12]}  2026-01-05  Bob    change the CLI again" in human
    assert "changed in 2 commits since its point" in human
    assert "unchanged since the revalidation point" in human


@pytest.mark.parametrize("answer", ["unchanged", "deferred"])
def test_the_commands_named_clear_the_finding(timeline: Timeline, answer: str) -> None:
    timeline.start({"docs/guide.md": guide()})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"})
    (stale,) = frep.run_explain(timeline.adopter.root, "docs/guide.md").findings
    (command,) = [a.command for a in stale.answers if a.answer == answer]

    words = shlex.split(command)
    words = [{frep.BECAUSE: "still true", frep.REASON: "next sprint"}.get(w, w) for w in words]
    assert words[:2] == ["pkit", "friction"]
    written = CliRunner().invoke(main, [*words[1:], "--yes"])
    assert written.exit_code == 0, written.output
    timeline.commit("answer the friction", None)

    assert [e.finding.kind.value for e in frep.run_debt(timeline.adopter.root).entries] == (
        [] if answer == "unchanged" else ["deferred"]
    )


def test_explain_findings_are_the_whole_repository_checks(timeline: Timeline) -> None:
    anchors = {"path": ["src/cli/**", "src/core/**", "src/gone/**", "."], "use-case": ["UC-1"]}
    timeline.start({"docs/guide.md": guide(anchors=anchors), "docs/other.md": _notes()})
    timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"})
    timeline.commit(
        "defer the engine",
        {"docs/guide.md": guide(anchors=anchors, deferred=[("path", "src/core/**", "later")])},
    )
    root = timeline.adopter.root

    def summary(findings: Any) -> list[tuple[str, Any, Any, str]]:
        return [
            (f.kind.value, f.anchor, None if f.origin is None else f.origin.sha, f.message)
            for f in findings
        ]

    reported = [f for f in fr.run_repository_check(root).findings if f.location == "docs/guide.md"]
    explanation = frep.run_explain(root, "guide")
    assert summary(f.finding for f in explanation.findings) == summary(reported)
    assert [(f.finding.kind.value, f.finding.anchor) for f in explanation.findings] == [
        ("stale", CLI),
        ("stale", Anchor("path", ".")),
        ("deferred", CORE),
        ("dead-anchor", Anchor("path", "src/gone/**")),
        ("unresolved-kind", Anchor("use-case", "UC-1")),
        ("over-broad", Anchor("path", ".")),
    ]
    assert [(a.anchor.value, a.state, a.over_broad) for a in explanation.anchors] == [
        ("src/cli/**", "stale", False),
        ("src/core/**", "deferred", False),
        ("src/gone/**", "dead-anchor", False),
        (".", "stale", True),
        ("UC-1", "unresolved-kind", False),
    ]
    by_kind = {f.finding.kind.value: f for f in explanation.findings}
    for kind in ("dead-anchor", "unresolved-kind", "over-broad"):
        assert by_kind[kind].answers == () and by_kind[kind].commits == ()
    assert "the writers do not edit anchors" in by_kind["dead-anchor"].clears
    assert "resolves `use-case` anchors" in by_kind["unresolved-kind"].clears
    assert by_kind["over-broad"].clears.startswith("narrow path:.")


def test_explain_a_deferral_what_it_postpones_and_what_came_after(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide()})
    before = timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"})
    deferred = timeline.commit(
        "defer the guide",
        {"docs/guide.md": guide(deferred=[("path", "src/cli/**", "waiting")])},
        author=BOB,
    )
    after = timeline.commit("change the CLI again", {"src/cli/main.py": "print('3')\n"})

    explanation = frep.run_explain(timeline.adopter.root, "docs/guide.md")
    stale, postponed = explanation.findings
    assert (stale.finding.kind.value, [c.commit.sha for c in stale.commits]) == ("stale", [after])
    assert (postponed.finding.kind.value, [c.commit.sha for c in postponed.commits]) == (
        "deferred",
        [before],
    )
    assert (
        postponed.clears
        == "a revalidation that does not keep it (`--keep path:src/cli/**` keeps it)"
    )
    assert [a.answer for a in postponed.answers] == ["updated", "unchanged"]
    assert explanation.report is not None
    assert [(a, p and p.sha) for a, p in explanation.report.deferral_points] == [(CLI, deferred)]
    human = frep.render_explain_human(explanation, now=NOW)
    assert "    postpones, oldest first:" in human and "    changed in, oldest first:" in human
    assert f"deferral      {deferred[:12]}  2026-01-04" in human
    assert "name each one kept with --keep (path:src/cli/**)" in human
    assert "waiting; since" in human and "97 days ago" in human


def test_explain_an_artefact_anchor_lists_each_change_of_the_targets_content(
    timeline: Timeline,
) -> None:
    def engine(at: str, body: str) -> str:
        return document(
            "engine-notes", anchors={"path": ["src/core/**"]}, at=at, outcome="updated", body=body
        )

    overview = document(
        "overview", anchors={"artefact": ["engine-notes"]}, at=T1, outcome="updated"
    )
    timeline.start({"docs/a-engine.md": engine(T1, "One."), "docs/b-overview.md": overview})
    first = timeline.commit("engine notes: two", {"docs/a-engine.md": engine(T1, "Two.")})
    timeline.commit("engine notes: revalidated only", {"docs/a-engine.md": engine(T2, "Two.")})
    third = timeline.commit("engine notes: three", {"docs/a-engine.md": engine(T2, "Three.")})

    explanation = frep.run_explain(timeline.adopter.root, "overview")
    (stale,) = explanation.findings
    assert stale.finding.anchor == Anchor("artefact", "engine-notes")
    assert stale.finding.origin is not None and stale.finding.origin.sha == first
    # The middle commit changed only the container: not content, so nothing behind the change.
    assert [c.commit.sha for c in stale.commits] == [first, third]
    assert {c.paths for c in stale.commits} == {("docs/a-engine.md",)}


def test_explain_an_artefact_anchor_names_no_merge_that_only_kept_a_sides_content(
    timeline: Timeline,
) -> None:
    def engine(at: str, body: str) -> str:
        return document(
            "engine-notes", anchors={"path": ["src/core/**"]}, at=at, outcome="updated", body=body
        )

    overview = document(
        "overview", anchors={"artefact": ["engine-notes"]}, at=T1, outcome="updated"
    )
    repo = timeline.adopter
    timeline.start({"docs/a-engine.md": engine(T1, "One."), "docs/b-overview.md": overview})
    repo.checkout("side", create=True)
    side = timeline.commit("side: engine notes two", {"docs/a-engine.md": engine(T1, "Two.")})
    repo.checkout("main")
    timeline.commit("main: engine notes revalidated only", {"docs/a-engine.md": engine(T2, "One.")})
    timeline.merge("side")

    # The merge combined both sides' edits of the file, but its content is the side's: the
    # side's commit is the one change behind the finding, never the merge that kept it.
    explanation = frep.run_explain(timeline.adopter.root, "overview")
    (stale,) = explanation.findings
    assert stale.finding.origin is not None and stale.finding.origin.sha == side
    assert [c.commit.sha for c in stale.commits] == [side]


def test_explain_a_move(timeline: Timeline) -> None:
    timeline.start({"notes/guide.md": guide()}, friction_config(places=("docs", "notes")))
    moved = timeline.rename("notes/guide.md", "docs/guide.md")

    explanation = frep.run_explain(timeline.adopter.root, "guide")
    (stale,) = explanation.findings
    assert (stale.finding.anchor, [c.commit.sha for c in stale.commits]) == (None, [moved])
    assert [c.paths for c in stale.commits] == [("docs/guide.md", "notes/guide.md")]
    assert stale.clears == "revalidate the artefact: a move cannot be deferred"
    assert [a.answer for a in stale.answers] == ["updated", "unchanged"]
    assert "    moved in:" in frep.render_explain_human(explanation, now=NOW)


def test_explain_names_the_artefact_as_the_writers_do(timeline: Timeline) -> None:
    rules = {
        entry: {"pkit": {"friction": {"anchors": {"path": ["src/core/**"]}}}}
        for entry in ("RS-1", "RS-2")
    }
    timeline.start(
        {
            "docs/guide.md": guide(),
            "docs/rules.md": f"---\n{json.dumps(rules)}\n---\n\n## RS-1 — One\n\nOne.\n",
            "docs/twin-a.md": document("twin", anchors={"path": ["src/cli/**"]}),
            "docs/twin-b.md": document("twin", anchors={"path": ["src/cli/**"]}),
        }
    )
    root = timeline.adopter.root
    for reference in ("guide", "docs/guide.md"):
        assert frep.run_explain(root, reference).artefact.location == "docs/guide.md"
    for reference in ("docs/rules.md#RS-2", "RS-2"):
        assert frep.run_explain(root, reference).artefact.location == "docs/rules.md#RS-2"
    assert frep.run_explain(root, "docs/twin-b.md").artefact.location == "docs/twin-b.md"

    with pytest.raises(frep.FrictionReportError, match=r"names 2 artefacts at HEAD"):
        frep.run_explain(root, "twin")
    with pytest.raises(frep.FrictionReportError, match=r"The file holds docs/rules.md#RS-1"):
        frep.run_explain(root, "docs/rules.md#RS-9")

    timeline.adopter.write({"docs/new.md": document("new", anchors={"path": ["src/cli/**"]})})
    result = _cli("explain", "new")
    assert result.exit_code == 1
    assert "no artefact at HEAD is named 'new'" in result.output
    assert "commit a new artefact first" in result.output


def test_explain_an_unanchored_artefact(timeline: Timeline) -> None:
    timeline.start({"docs/guide.md": guide(), "docs/plain.md": "---\nid: plain\n---\n\nText.\n"})
    explanation = frep.run_explain(timeline.adopter.root, "plain")
    assert (explanation.state, explanation.report, explanation.findings) == (
        "unanchored",
        None,
        (),
    )
    result = _cli("explain", "plain")
    assert result.exit_code == 0, result.output
    assert "State: unanchored" in result.output and "FINDINGS" not in result.output


def test_explain_an_excluded_artefact_names_the_setting_that_leaves_it_out(
    timeline: Timeline,
) -> None:
    _excluded_history(timeline)
    root = timeline.adopter.root
    explanation = frep.run_explain(root, "gen-cli")
    assert (explanation.state, explanation.report) == ("excluded", None)
    setting = explanation.artefact.excluded_by
    assert setting is not None
    assert (setting.value, setting.file, setting.pointer) == (
        "docs/generated",
        CONFIG,
        "/friction/exclude/1",
    )
    # Never judged stale; what it declares is still checked, as `check --all` does.
    assert [(a.anchor.value, a.state) for a in explanation.anchors] == [
        ("src/cli/**", "excluded"),
        ("src/gone/**", "dead-anchor"),
    ]
    assert [f.finding.kind.value for f in explanation.findings] == ["dead-anchor"]
    # Its path anchors' files are listed all the same; with no points, none at the point, and
    # nothing lies behind a finding on its declarations.
    assert [a.files for a in explanation.anchors] == [
        fr.AnchorFiles(None, ("src/cli/main.py",), ()),
        fr.AnchorFiles(None, (), ()),
    ]
    (dead,) = explanation.findings
    assert (dead.finding.message, dead.commits) == ("matches no file", ())

    human = _cli("explain", "gen-cli")
    assert human.exit_code == 0, human.output
    assert "State: excluded" in human.output
    assert (
        "Excluded by: friction.exclude 'docs/generated' "
        "(.pkit/project/config.yaml, /friction/exclude/1)" in human.output
    )
    assert "FINDINGS" in human.output and "POINTS" not in human.output

    result = _cli("explain", "gen-cli", "--json")
    assert result.exit_code == 0, result.output
    doc = json.loads(result.output)
    assert (doc["state"], doc["revalidation_point"]) == ("excluded", None)
    assert doc["excluded_by"] == {
        "value": "docs/generated",
        "file": CONFIG,
        "pointer": "/friction/exclude/1",
    }

    # Deferred or unanchored, an excluded artefact is excluded, and nothing is judged.
    for reference in ("notes", "api"):
        unjudged = frep.run_explain(root, reference)
        assert (unjudged.state, unjudged.report, unjudged.findings) == ("excluded", None, ())


def test_explain_refuses_without_places_and_before_the_first_commit(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo()
    adopter.write({CONFIG: friction_config(), "docs/guide.md": guide()})
    with pytest.raises(fr.FrictionCheckError, match="commit first"):
        frep.run_explain(adopter.root, "guide")

    adopter.commit("no places", {CONFIG: json.dumps({"friction": {}}) + "\n"})
    result = _cli("explain", "guide")
    assert result.exit_code == 1
    assert "no places are declared at HEAD" in result.output


def test_explain_in_a_shallow_clone(timeline: Timeline, tmp_path: Path) -> None:
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    for version in (2, 3, 4):
        timeline.commit(f"cli {version}", {"src/cli/main.py": f"print('cli {version}')\n"})
    shallow = tmp_path / "shallow"
    repo.git("clone", "-q", "--depth", "2", f"file://{repo.root}", str(shallow))

    explanation = frep.run_explain(shallow, "guide")
    assert (explanation.state, explanation.shallow) == ("unreachable", True)
    assert [a.state for a in explanation.anchors] == ["unreachable"]
    # The point lies beyond the clone, so its files cannot be listed; HEAD's can.
    assert [a.files for a in explanation.anchors] == [
        fr.AnchorFiles(None, ("src/cli/main.py",), ())
    ]
    (finding,) = explanation.findings
    assert finding.finding.kind is fr.RepositoryFindingKind.UNREACHABLE
    assert finding.clears == "fetch the full history (`git fetch --unshallow`) and run again"


def test_explain_a_deferral_point_beyond_a_shallow_clone(
    timeline: Timeline, tmp_path: Path
) -> None:
    """The revalidation point is in the clone, a kept deferral's point is not: the artefact is
    not judged, but the files its path anchor stood on at the point are listed all the same."""
    repo = timeline.adopter
    timeline.start({"docs/guide.md": guide()})
    kept = [("path", "src/cli/**", "waiting")]
    timeline.commit("defer the guide", {"docs/guide.md": guide(deferred=kept)})
    timeline.commit("cli 2", {"src/cli/main.py": "print('cli 2')\n"})
    revalidated = timeline.commit(
        "revalidate the guide",
        {"docs/guide.md": guide(at=T2, because="still as described", deferred=kept)},
    )
    timeline.commit("cli 3", {"src/cli/main.py": "print('cli 3')\n"})
    shallow = tmp_path / "shallow"
    # Three commits: `cli 3`, the revalidation, and `cli 2`, where the clone is cut.
    repo.git("clone", "-q", "--depth", "3", f"file://{repo.root}", str(shallow))

    explanation = frep.run_explain(shallow, "guide")
    assert (explanation.state, explanation.shallow) == ("unreachable", True)
    assert explanation.report is not None and explanation.report.revalidation_point is not None
    assert explanation.report.revalidation_point.sha == revalidated
    assert [(a, p) for a, p in explanation.report.deferral_points] == [(CLI, None)]
    assert [(a.state, a.files) for a in explanation.anchors] == [
        ("unreachable", fr.AnchorFiles(("src/cli/main.py",), ("src/cli/main.py",), ()))
    ]
    (finding,) = explanation.findings
    assert finding.finding.kind is fr.RepositoryFindingKind.UNREACHABLE
    assert "the deferral point of path src/cli/**" in finding.finding.message
    assert finding.commits == ()
    doc = json.loads(frep.render_explain_json(explanation))
    assert doc["anchors"][0]["files"]["point"] == ["src/cli/main.py"]


def test_explain_json_document_shape(timeline: Timeline) -> None:
    base = timeline.start({"docs/guide.md": guide()})
    changed = timeline.commit("change the CLI", {"src/cli/main.py": "print('2')\n"}, author=ALICE)
    result = _cli("explain", "guide", "--json")
    assert result.exit_code == 0, result.output
    doc = json.loads(result.output)
    assert sorted(doc) == [
        "anchors",
        "artefact",
        "body",
        "deferral_points",
        "excluded_by",
        "findings",
        "head",
        "history",
        "location",
        "report",
        "revalidation_point",
        "state",
    ]
    assert (doc["report"], doc["artefact"], doc["location"], doc["state"]) == (
        "explain",
        "guide",
        "docs/guide.md",
        "stale",
    )
    assert doc["body"] == "Body.\n"
    assert doc["excluded_by"] is None
    assert doc["revalidation_point"]["commit"] == base and doc["deferral_points"] == []
    assert doc["anchors"] == [
        {
            "kind": "path",
            "value": "src/cli/**",
            "state": "stale",
            "changes": 1,
            "over_broad": False,
            "files": {"point": ["src/cli/main.py"], "head": ["src/cli/main.py"], "excluded": []},
        }
    ]
    (finding,) = doc["findings"]
    assert sorted(finding) == [
        "anchor",
        "answers",
        "clears",
        "commits",
        "kind",
        "message",
        "origin",
    ]
    assert [c["commit"] for c in finding["commits"]] == [changed]
    assert sorted(finding["commits"][0]) == ["author", "change", "commit", "date", "paths"]
    assert finding["commits"][0]["paths"] == ["src/cli/main.py"]
    assert finding["origin"]["commit"] == changed
    assert [a["answer"] for a in finding["answers"]] == ["updated", "unchanged", "deferred"]


# --- what a reader of the explanation would otherwise compute again (ADR-057 point 2) -------


def test_explain_lists_each_path_anchors_files_at_the_point_and_at_head(
    timeline: Timeline,
) -> None:
    """Matched as the check decides a dead anchor: a file under `friction.exclude` is never
    among them, even where the anchor's glob covers it, and a change to it alone is no change;
    `excluded` lists it."""
    anchors = {
        "path": ["src/cli/**", "src/core/**", "src/cli/vendor/**"],
        "record": ["ADR-404"],
    }
    config = friction_config(exclude=["src/cli/vendor/**"])
    vendored = {"src/cli/vendor/lib.py": "LIB = 1\n", "src/cli/old.py": "OLD = 1\n"}
    base = timeline.start({"docs/guide.md": guide(anchors=anchors), **vendored}, config)
    reworked = timeline.commit(
        "rework the CLI",
        {"src/cli/new.py": "NEW = 1\n", "src/cli/old.py": None, "src/cli/main.py": "print('2')\n"},
    )
    timeline.commit("update the vendored library", {"src/cli/vendor/lib.py": "LIB = 2\n"})

    explanation = frep.run_explain(timeline.adopter.root, "guide")
    assert explanation.report is not None and explanation.report.revalidation_point is not None
    assert explanation.report.revalidation_point.sha == base
    assert [(a.anchor.value, a.state, a.files) for a in explanation.anchors] == [
        (
            "src/cli/**",
            "stale",
            fr.AnchorFiles(
                point=("src/cli/main.py", "src/cli/old.py"),
                head=("src/cli/main.py", "src/cli/new.py"),
                excluded=("src/cli/vendor/lib.py",),
            ),
        ),
        (
            "src/core/**",
            "current",
            fr.AnchorFiles(("src/core/engine.py",), ("src/core/engine.py",), ()),
        ),
        # Only excluded files match it: dead, standing on nothing at either state.
        ("src/cli/vendor/**", "dead-anchor", fr.AnchorFiles((), (), ("src/cli/vendor/lib.py",))),
        ("ADR-404", "dead-anchor", None),
    ]
    by_anchor = {f.finding.anchor: f for f in explanation.findings}
    assert [c.commit.sha for c in by_anchor[CLI].commits] == [reworked]
    # A dead anchor's commits say where the files it matched went: excluded ones never count,
    # and a record that resolves to nothing names no file whose history could be read.
    assert by_anchor[Anchor("path", "src/cli/vendor/**")].commits == ()
    assert by_anchor[Anchor("record", "ADR-404")].commits == ()

    doc = json.loads(frep.render_explain_json(explanation))
    listed = {a["value"]: a["files"] for a in doc["anchors"]}
    assert listed["src/cli/**"] == {
        "point": ["src/cli/main.py", "src/cli/old.py"],
        "head": ["src/cli/main.py", "src/cli/new.py"],
        "excluded": ["src/cli/vendor/lib.py"],
    }
    assert listed["ADR-404"] is None
    assert all(
        "src/cli/vendor/lib.py" not in files[state]
        for files in listed.values()
        if files is not None
        for state in ("point", "head")
    )


def test_a_commits_paths_are_what_the_check_reads_never_the_artefacts_own_file(
    timeline: Timeline,
) -> None:
    """`commits[].paths` is what the change rule reads — the anchor's matched paths the commit
    touched, less the artefact's own file — while `files` is the two trees' view, own file in."""
    anchors = {"path": ["docs/**"]}
    base = timeline.start({"docs/guide.md": guide(anchors=anchors), "docs/notes.txt": "One.\n"})
    both = timeline.commit(
        "the guide and its notes",
        {"docs/guide.md": guide(anchors=anchors, body="Two."), "docs/notes.txt": "Two.\n"},
    )
    timeline.commit("the guide alone", {"docs/guide.md": guide(anchors=anchors, body="Three.")})

    explanation = frep.run_explain(timeline.adopter.root, "guide")
    (stale,) = explanation.findings
    assert stale.finding.origin is not None and stale.finding.origin.sha == both
    # The guide's own edits are never its anchor's change: one commit, and not its own file.
    assert [(c.commit.sha, c.paths) for c in stale.commits] == [(both, ("docs/notes.txt",))]
    (anchor,) = explanation.anchors
    assert anchor.files == fr.AnchorFiles(
        ("docs/guide.md", "docs/notes.txt"), ("docs/guide.md", "docs/notes.txt"), ()
    )
    assert explanation.report is not None and explanation.report.revalidation_point is not None
    assert explanation.report.revalidation_point.sha == base


def test_a_file_that_lived_only_between_the_point_and_head_is_in_the_commits_paths(
    timeline: Timeline,
) -> None:
    """Neither tree holds it, so `files` never lists it; the commits that added and removed it
    changed the anchor, and each names it."""
    timeline.start({"docs/guide.md": guide()})
    added = timeline.commit("a scratch module", {"src/cli/scratch.py": "S = 1\n"})
    removed = timeline.commit("drop the scratch module", {"src/cli/scratch.py": None})

    explanation = frep.run_explain(timeline.adopter.root, "guide")
    (stale,) = explanation.findings
    assert [(c.commit.sha, c.paths) for c in stale.commits] == [
        (added, ("src/cli/scratch.py",)),
        (removed, ("src/cli/scratch.py",)),
    ]
    (anchor,) = explanation.anchors
    assert anchor.files == fr.AnchorFiles(("src/cli/main.py",), ("src/cli/main.py",), ())


def test_a_dead_path_anchor_says_whether_it_matches_no_file_or_only_excluded_ones(
    timeline: Timeline,
) -> None:
    """A typo and a glob covering only excluded files are both dead (COR-050 point 7), and
    read apart: the finding's message says which, and `files.excluded` lists what is left out."""
    anchors = {"path": ["src/cli/**", "src/clj/**", "src/cli/vendor/**"]}
    vendored = {"src/cli/vendor/a.py": "A = 1\n", "src/cli/vendor/b.py": "B = 1\n"}
    timeline.start(
        {"docs/guide.md": guide(anchors=anchors), **vendored},
        friction_config(exclude=["src/cli/vendor/**"]),
    )

    explanation = frep.run_explain(timeline.adopter.root, "guide")
    dead = {
        f.finding.anchor.value: f.finding.message
        for f in explanation.findings
        if f.finding.anchor is not None and f.finding.kind is fr.RepositoryFindingKind.DEAD_ANCHOR
    }
    assert dead == {
        "src/clj/**": "matches no file",
        "src/cli/vendor/**": "matches only excluded files (2)",
    }
    doc = json.loads(frep.render_explain_json(explanation))
    assert {a["value"]: a["files"]["excluded"] for a in doc["anchors"]} == {
        "src/cli/**": ["src/cli/vendor/a.py", "src/cli/vendor/b.py"],
        "src/clj/**": [],
        "src/cli/vendor/**": ["src/cli/vendor/a.py", "src/cli/vendor/b.py"],
    }
    human = frep.render_explain_human(explanation, now=NOW)
    assert "src/cli/vendor/**  dead-anchor  matches only excluded files (2)" in human
    assert "src/clj/**         dead-anchor  matches no file" in human


def test_explain_names_an_exclusion_added_since_the_point_as_why_an_anchor_is_dead(
    timeline: Timeline,
) -> None:
    """Each state is read under its own `friction.exclude` (COR-050 point 7): the point's
    files are what the anchor stood on there, so an anchor an exclusion killed since shows
    them; its finding says `excluded since <commit>`, and that commit is where its files
    went — the configuration file its change. The anchor that lost a file to it is stale."""
    anchors = {"path": ["src/cli/**", "src/cli/generated/**"]}
    generated = {"src/cli/generated/table.py": "T = 1\n"}
    base = timeline.start({"docs/guide.md": guide(anchors=anchors), **generated})
    widened = timeline.commit(
        "exclude the generated code",
        {CONFIG: friction_config(exclude=["src/cli/generated"])},
        author=ALICE,
    )

    explanation = frep.run_explain(timeline.adopter.root, "guide")
    assert explanation.report is not None and explanation.report.revalidation_point is not None
    assert explanation.report.revalidation_point.sha == base
    assert [(a.anchor.value, a.state, a.files) for a in explanation.anchors] == [
        (
            "src/cli/**",
            "stale",
            fr.AnchorFiles(
                point=("src/cli/generated/table.py", "src/cli/main.py"),
                head=("src/cli/main.py",),
                excluded=("src/cli/generated/table.py",),
            ),
        ),
        (
            "src/cli/generated/**",
            "dead-anchor",
            fr.AnchorFiles(
                point=("src/cli/generated/table.py",),
                head=(),
                excluded=("src/cli/generated/table.py",),
            ),
        ),
    ]
    by_anchor = {f.finding.anchor: f for f in explanation.findings}
    dead = by_anchor[Anchor("path", "src/cli/generated/**")]
    day = (HISTORY_EPOCH + timedelta(days=2)).date().isoformat()
    assert dead.finding.message == (
        f'matches only excluded files (1), excluded since {widened[:12]} "exclude the generated '
        f'code" (Alice, {day})'
    )
    assert [(c.commit.sha, c.paths) for c in dead.commits] == [(widened, (CONFIG,))]
    stale = by_anchor[CLI]
    assert stale.finding.origin is not None and stale.finding.origin.sha == widened
    assert [(c.commit.sha, c.paths) for c in stale.commits] == [(widened, (CONFIG,))]

    doc = json.loads(frep.render_explain_json(explanation))
    listed = {a["value"]: a["files"] for a in doc["anchors"]}
    assert listed["src/cli/generated/**"] == {
        "point": ["src/cli/generated/table.py"],
        "head": [],
        "excluded": ["src/cli/generated/table.py"],
    }
    human = frep.render_explain_human(explanation, now=NOW)
    assert f"matches only excluded files (1), excluded since {widened[:12]}" in human


def test_explain_names_where_a_dead_path_anchors_files_went(timeline: Timeline) -> None:
    """For each file the anchor matched, the last commit that touched it — its removal or its
    rename away — even where the artefact was revalidated over the dead anchor since."""
    anchors = {"path": ["src/cli/**", "src/old/**"]}
    old = {"src/old/a.py": "A = 1\n", "src/old/b.py": "B = 1\n"}
    timeline.start({"docs/guide.md": guide(anchors=anchors), **old})
    timeline.commit("change the old code", {"src/old/a.py": "A = 2\n"}, author=ALICE)
    moved = timeline.rename("src/old/b.py", "src/new/b.py")
    removed = timeline.commit("remove the old code", {"src/old/a.py": None}, author=BOB)
    # Warning mode lets a revalidation stand over a dead anchor: the point is after both.
    revalidated = timeline.commit(
        "revalidate the guide",
        {"docs/guide.md": guide(anchors=anchors, at=T2, because="the CLI surface holds")},
    )

    explanation = frep.run_explain(timeline.adopter.root, "guide")
    assert explanation.report is not None and explanation.report.revalidation_point is not None
    assert explanation.report.revalidation_point.sha == revalidated
    old_anchor = Anchor("path", "src/old/**")
    (dead,) = explanation.findings
    assert (dead.finding.kind.value, dead.finding.anchor) == ("dead-anchor", old_anchor)
    # The earlier change to a file is not where it went; the rename names only its old path.
    assert [(c.commit.sha, c.paths) for c in dead.commits] == [
        (moved, ("src/old/b.py",)),
        (removed, ("src/old/a.py",)),
    ]
    # `changes` counts a stale anchor's commits only: these are no changes to answer.
    assert [(a.anchor, a.state, a.changes, a.files) for a in explanation.anchors] == [
        (CLI, "current", 0, fr.AnchorFiles(("src/cli/main.py",), ("src/cli/main.py",), ())),
        (old_anchor, "dead-anchor", 0, fr.AnchorFiles((), (), ())),
    ]
    (finding,) = json.loads(frep.render_explain_json(explanation))["findings"]
    assert [(c["commit"], c["change"], c["paths"]) for c in finding["commits"]] == [
        (moved, "rename src/old/b.py -> src/new/b.py", ["src/old/b.py"]),
        (removed, "remove the old code", ["src/old/a.py"]),
    ]
    human = frep.render_explain_human(explanation, now=NOW)
    assert "    where its files went, oldest first:" in human
    assert f"{removed[:12]}  2026-01-05  Bob        remove the old code" in human


def test_a_deferral_of_a_dead_path_anchor_postpones_no_commits(timeline: Timeline) -> None:
    """A deferral postpones friction (COR-050 point 4) and a dead anchor is an error (point 7):
    the deferred finding lists nothing, and the dead-anchor finding says where its files went."""
    anchors = {"path": ["src/cli/**", "src/old/**"]}
    timeline.start({"docs/guide.md": guide(anchors=anchors), "src/old/a.py": "A = 1\n"})
    timeline.commit("change the old code", {"src/old/a.py": "A = 2\n"})
    timeline.commit(
        "defer the old code",
        {"docs/guide.md": guide(anchors=anchors, deferred=[("path", "src/old/**", "going")])},
    )
    removed = timeline.commit("remove the old code", {"src/old/a.py": None})

    explanation = frep.run_explain(timeline.adopter.root, "guide")
    old_anchor = Anchor("path", "src/old/**")
    assert [
        (f.finding.kind.value, f.finding.anchor, [c.commit.sha for c in f.commits])
        for f in explanation.findings
    ] == [("deferred", old_anchor, []), ("dead-anchor", old_anchor, [removed])]
    assert [(a.anchor, a.state, a.changes) for a in explanation.anchors] == [
        (CLI, "current", 0),
        (old_anchor, "dead-anchor", 0),
    ]


def test_explain_carries_the_artefacts_body(timeline: Timeline) -> None:
    """A document's body; a collection entry's section headed by its id (COR-050 point 1)."""
    rules = {
        entry: {"pkit": {"friction": {"anchors": {"path": ["src/core/**"]}}}}
        for entry in ("RS-1", "RS-2")
    }
    body = "## RS-1 — One\n\nOne `first`.\n\n## RS-2 — Two\n\nTwo `second`.\n"
    timeline.start(
        {"docs/guide.md": guide(), "docs/rules.md": f"---\n{json.dumps(rules)}\n---\n\n{body}"}
    )
    root = timeline.adopter.root

    def body_of(reference: str) -> str:
        return json.loads(frep.render_explain_json(frep.run_explain(root, reference)))["body"]

    assert body_of("guide") == "Body.\n"
    assert body_of("RS-1") == "## RS-1 — One\n\nOne `first`.\n"
    assert body_of("docs/rules.md#RS-2") == "## RS-2 — Two\n\nTwo `second`.\n"


# --- read-only, deterministic --------------------------------------------------------------


def _snapshot(root: Path) -> dict[str, tuple[int, bytes]]:
    """Every file, link and directory under `root`, `.git` included: its mode and bytes."""
    found: dict[str, tuple[int, bytes]] = {}
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        if path.is_symlink():
            data = os.readlink(path).encode()
        elif path.is_file():
            data = path.read_bytes()
        else:
            data = b""
        found[path.relative_to(root).as_posix()] = (mode, data)
    return found


def test_neither_command_writes(timeline: Timeline) -> None:
    """The commands write nothing: every byte under the repository, `.git`
    included, is the same after each. The test repository has git's automatic
    maintenance off from its first commit (`GitRepo.init`): a detached
    `gc --auto` would otherwise add `info/refs`, `objects/info/packs` and the
    multi-pack index under `.git` at any later moment — git's housekeeping,
    not the commands' writing (seen on the CI runner, #1065). A failure here
    is a real write."""
    _debt_history(timeline)
    timeline.adopter.write({"src/cli/main.py": "print('uncommitted')\n"})  # a dirty tree, too
    root = timeline.adopter.root
    before = _snapshot(root)
    for args in (
        ("debt",),
        ("debt", "--json"),
        ("explain", "guide"),
        ("explain", "docs/a-notes.md", "--json"),
        ("explain", "nothing-by-this-name"),
    ):
        _cli(*args)
        assert _snapshot(root) == before, args
    # the comparison still sees a write: one file under the tree, one under .git
    (root / "docs" / "written.md").write_text("a write\n")
    assert _snapshot(root) != before
    (root / "docs" / "written.md").unlink()
    assert _snapshot(root) == before
    (root / ".git" / "written").write_text("a write\n")
    assert _snapshot(root) != before


def test_output_is_deterministic(timeline: Timeline) -> None:
    _debt_history(timeline)
    root = timeline.adopter.root
    GitRepo(root).git("commit", "-q", "--allow-empty", "-m", "an empty commit")
    first_debt, second_debt = frep.run_debt(root), frep.run_debt(root)
    assert frep.render_debt_json(first_debt) == frep.render_debt_json(second_debt)
    assert frep.render_debt_human(first_debt, now=NOW) == frep.render_debt_human(
        second_debt, now=NOW
    )
    for reference in ("guide", "notes"):
        first, second = frep.run_explain(root, reference), frep.run_explain(root, reference)
        assert frep.render_explain_json(first) == frep.render_explain_json(second)
        assert frep.render_explain_human(first, now=NOW) == frep.render_explain_human(
            second, now=NOW
        )
