"""The warning on an over-broad anchor, `pkit friction check --all` (COR-050 point 7; #2636).

An anchor is over-broad when it flagged its artefact in more than `OVER_BROAD_FLAGS`
of the newest `OVER_BROAD_WINDOW` changes on the first-parent line, each read against
its first parent (ADR-080). Every test lays down a real history on an adopter whose
install is committed once per session (`committed_adopter`): the install's commit is
the root, and the base the first change. Most tests set a small window and bar, so a
few commits cross it; one holds the record's own numbers.

Held to: every kind counted — path, record, artefact, a registered kind's elsewhere
(`test_friction_anchor_kinds`) — each by what it stands on at HEAD; a flag reached
through another artefact counted only where that artefact changed; a change to a placed
file's containers alone flagging no path anchor; only the window's changes counted; a
merge read as one change against its first parent; the root and a shallow clone's cut
no change; an artefact that owes no answer never flagged; and one count for a history
shorter than the window.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from project_kit import friction_history as fh
from project_kit import friction_repository as fr
from project_kit.friction_discovery import Anchor
from tests.adopter_repo import AdopterRepo
from tests.friction_documents import (
    ADR,
    ADR_OVERLAY,
    T2,
    Timeline,
    adr,
    document,
    friction_config,
    guide,
)

#: The documents here say each artefact's answers beside its anchors, and each write
#: takes them into answer files, as a change writes them (COR-062 point 1).
pytestmark = pytest.mark.usefixtures("answers_in_files")

CLI = Anchor("path", "src/cli/**")
CORE = Anchor("path", "src/core/**")


@pytest.fixture
def timeline(committed_adopter: AdopterRepo) -> Timeline:
    return Timeline(committed_adopter)


def _window(monkeypatch: pytest.MonkeyPatch, window: int, flags: int) -> None:
    """A window of `window` changes and a bar of `flags`, so a few commits cross it."""
    monkeypatch.setattr(fr, "OVER_BROAD_WINDOW", window)
    monkeypatch.setattr(fr, "OVER_BROAD_FLAGS", flags)


def _broad(timeline: Timeline) -> dict[tuple[str | None, Anchor | None], str]:
    """Each over-broad finding's message, by its artefact's location and its anchor."""
    result = fr.run_repository_check(timeline.adopter.root)
    return {
        (f.location, f.anchor): f.message
        for f in result.findings
        if f.kind is fr.RepositoryFindingKind.OVER_BROAD
    }


def _count(message: str) -> tuple[int, int]:
    """The count and the window's size an over-broad finding's message names."""
    found = re.match(r"flagged its artefact in (\d+) of the last (\d+) changes", message)
    assert found is not None, message
    return int(found[1]), int(found[2])


def _cli(timeline: Timeline, version: int) -> str:
    return timeline.commit(f"cli {version}", {"src/cli/main.py": f"print('cli {version}')\n"})


PAGE = "docs/page.md"


def _page(
    busy: str = "Busy.",
    quiet: str = "Quiet.",
    *,
    anchors: dict[str, list[str]] | None = None,
    at: str = "2026-10-01T09:00:00Z",
    outcome: str | None = None,
    because: str | None = None,
) -> str:
    """`page`, anchored to the engine, with a section that changes and one that does not."""
    return document(
        "page",
        anchors=anchors if anchors is not None else {"path": ["src/core/**"]},
        at=at,
        outcome=outcome,
        because=because,
        body=f"## Busy\n\n{busy}\n\n## Quiet\n\n{quiet}",
    )


# --- the record's numbers --------------------------------------------------------------------


def test_the_window_and_the_bar_are_the_record_s() -> None:
    """A hundred changes, and more than ten of them (ADR-080 points 2 and 3)."""
    assert (fr.OVER_BROAD_WINDOW, fr.OVER_BROAD_FLAGS) == (100, 10)


def test_an_anchor_that_flagged_its_artefact_in_more_than_ten_changes_is_over_broad(
    timeline: Timeline,
) -> None:
    """At the record's numbers: the base adds the CLI, and ten changes edit it, so its
    anchor flagged the guide in 11 of 12 changes. The engine's, in one, is not named."""
    timeline.start({"docs/guide.md": guide(anchors={"path": ["src/cli/**", "src/core/**"]})})
    for version in range(2, 12):
        _cli(timeline, version)
    timeline.commit("engine", {"src/core/engine.py": "ENGINE = 2\n"})

    broad = _broad(timeline)
    assert list(broad) == [("docs/guide.md", CLI)]
    message = broad["docs/guide.md", CLI]
    assert _count(message) == (11, 12)
    assert message == (
        "flagged its artefact in 11 of the last 12 changes, more than 10: so many "
        "revalidations teach people to bump the marker blindly — narrow it"
    )


def test_a_history_shorter_than_the_window_is_held_to_the_same_count(
    timeline: Timeline,
) -> None:
    """Ten flags in a history of ten changes are every change, yet not more than ten: a
    young project's few changes warn of nothing by chance (ADR-080 point 3)."""
    timeline.start({"docs/guide.md": guide(anchors={"path": ["."]})})
    for version in range(2, 11):
        _cli(timeline, version)
    assert _broad(timeline) == {}

    _cli(timeline, 11)
    assert _count(_broad(timeline)["docs/guide.md", Anchor("path", ".")]) == (11, 11)


# --- what an anchor stands on, kind by kind --------------------------------------------------


def test_a_path_anchor_counts_the_changes_that_touched_what_it_stands_on(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    _window(monkeypatch, 10, 2)
    timeline.start({"docs/guide.md": guide(anchors={"path": ["src/cli/**", "src/core/**"]})})
    for version in (2, 3, 4):
        _cli(timeline, version)
    timeline.commit("engine", {"src/core/engine.py": "ENGINE = 2\n"})
    timeline.commit("unrelated", {"README.md": "Hello.\n"})

    broad = _broad(timeline)
    assert list(broad) == [("docs/guide.md", CLI)]  # the engine's anchor flagged two
    assert _count(broad["docs/guide.md", CLI]) == (4, 6)


def test_an_artefact_anchor_on_a_busy_page_is_over_broad_and_one_on_a_quiet_section_is_not(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The issue's case: a page anchoring another whole is asked at each of its edits;
    anchored on the section it rests on, it is asked only when that section changes."""
    _window(monkeypatch, 10, 2)
    whole, quiet = Anchor("artefact", PAGE), Anchor("artefact", f"{PAGE}#quiet")
    hub = document("hub", anchors={"artefact": [PAGE, f"{PAGE}#quiet"]}, at=T2, outcome="updated")
    timeline.start({"docs/hub.md": hub, PAGE: _page()})
    for edit in (1, 2, 3):
        timeline.commit(f"busy {edit}", {PAGE: _page(busy=f"Busy {edit}.")})

    broad = _broad(timeline)
    assert list(broad) == [("docs/hub.md", whole)]
    assert _count(broad["docs/hub.md", whole]) == (4, 4)
    assert broad["docs/hub.md", whole].endswith(
        "anchor only the points or sections the artefact rests on"
    )
    assert ("docs/hub.md", quiet) not in broad  # flagged once, where the base added it


def test_a_flag_reached_through_another_artefact_counts_only_where_it_changed(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The engine flags the page twice. Revalidated `unchanged`, the page stops the flag;
    updated, it passes the flag on to the hub that anchors it, as the change check's
    cascade reads it (ADR-080 point 1)."""
    _window(monkeypatch, 10, 0)
    on_page = Anchor("artefact", PAGE)
    hub = document("hub", anchors={"artefact": [PAGE]}, at=T2, outcome="updated")
    timeline.start({"docs/hub.md": hub, PAGE: _page()})
    timeline.commit(
        "engine, the page unchanged",
        {
            "src/core/engine.py": "ENGINE = 2\n",
            PAGE: _page(at=T2, outcome="unchanged", because="it still says what it does"),
        },
    )
    timeline.commit(
        "engine, the page updated",
        {
            "src/core/engine.py": "ENGINE = 3\n",
            PAGE: _page(busy="Busy, again.", at="2026-10-03T09:00:00Z", outcome="updated"),
        },
    )

    broad = _broad(timeline)
    assert _count(broad[PAGE, CORE]) == (3, 3)  # the base, and each engine change
    assert _count(broad["docs/hub.md", on_page]) == (2, 3)  # the base, and the update


def test_a_change_to_a_placed_file_s_containers_alone_flags_no_path_anchor(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Markdown file a place holds is read by its content (COR-050 point 5): a change
    that wrote only its `pkit` container is no change to a path anchor on it."""
    _window(monkeypatch, 10, 0)
    on_page = Anchor("path", PAGE)
    timeline.start({"docs/guide.md": guide(anchors={"path": [PAGE]}), PAGE: _page()})
    timeline.commit("anchor the page wider", {PAGE: _page(anchors={"path": ["src/**"]})})
    timeline.commit("anchor it back", {PAGE: _page()})
    assert _count(_broad(timeline)["docs/guide.md", on_page]) == (1, 3)  # the base alone

    timeline.commit("edit the page", {PAGE: _page(quiet="Quiet, edited.")})
    assert _count(_broad(timeline)["docs/guide.md", on_page]) == (2, 4)


def test_a_record_anchor_counts_the_changes_to_what_its_point_stands_on(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    _window(monkeypatch, 10, 2)
    one, three = Anchor("record", "ADR-007#1"), Anchor("record", "ADR-007#3")
    anchored = guide(anchors={"record": ["ADR-007#1", "ADR-007#3"]})
    timeline.start({**ADR_OVERLAY, ADR: adr(), "docs/guide.md": anchored})
    for edit in (1, 2, 3):
        decision = (
            "## Decision\n\nThe engine stays one module.\n\n### 1. One\n\nOne.\n\n"
            f"### 3. Three\n\nThree, edited {edit}.\n"
        )
        timeline.commit(f"point 3, edit {edit}", {ADR: adr(body=decision)})

    broad = _broad(timeline)
    assert ("docs/guide.md", one) not in broad
    assert _count(broad["docs/guide.md", three]) == (4, 4)


# --- the window ----------------------------------------------------------------------------


def test_only_the_window_s_changes_count(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    timeline.start({"docs/guide.md": guide()})
    for version in (2, 3, 4):
        _cli(timeline, version)
    for n in (1, 2):
        timeline.commit(f"unrelated {n}", {"README.md": f"Hello {n}.\n"})

    _window(monkeypatch, 3, 0)  # the two unrelated changes and the last CLI change
    assert _count(_broad(timeline)["docs/guide.md", CLI]) == (1, 3)
    _window(monkeypatch, 5, 0)
    assert _count(_broad(timeline)["docs/guide.md", CLI]) == (3, 5)


def test_a_merge_on_the_line_is_one_change_against_its_first_parent(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The branch's two CLI commits are not on the line; the merge that brings them in is
    one change, read against its first parent, which lists the CLI though git's combined
    diff does not."""
    _window(monkeypatch, 10, 0)
    repo = timeline.adopter
    base = timeline.start({"docs/guide.md": guide()})
    repo.checkout("topic", create=True)
    _cli(timeline, 2)
    _cli(timeline, 3)
    repo.checkout("main")
    beside = timeline.commit("unrelated", {"README.md": "Hello.\n"})
    merge = timeline.merge("topic")

    history = fh.read_history(repo.root, merge)
    changes = fh.first_parent_changes(repo.root, history, 10)
    assert [history.commits[c.index].sha for c in changes] == [merge, beside, base]
    assert [e.path for e in changes[0].entries] == ["src/cli/main.py"]
    assert history.commits[0].entries == ()  # the combined diff lists nothing of it
    assert _count(_broad(timeline)["docs/guide.md", CLI]) == (2, 3)


def test_the_line_ends_before_the_root_and_before_a_shallow_clone_s_cut(
    timeline: Timeline, tmp_path: Path
) -> None:
    """Neither has a parent in the clone to be compared with, so neither is a change."""
    repo = timeline.adopter
    base = timeline.start({"docs/guide.md": guide()})
    second, third = _cli(timeline, 2), _cli(timeline, 3)

    history = fh.read_history(repo.root, third)
    changes = fh.first_parent_changes(repo.root, history, 10)
    assert [history.commits[c.index].sha for c in changes] == [third, second, base]
    assert len(fh.first_parent_changes(repo.root, history, 2)) == 2

    shallow = tmp_path / "shallow"
    repo.git("clone", "-q", "--depth", "2", f"file://{repo.root}", str(shallow))
    cut = fh.read_history(shallow, third)
    assert [cut.commits[c.index].sha for c in fh.first_parent_changes(shallow, cut, 10)] == [third]


# --- what is never over-broad --------------------------------------------------------------


def test_an_artefact_that_owes_no_answer_has_no_over_broad_anchor(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An artefact under an excluded path is never asked for an answer, so no change
    flags it (ADR-080 point 1)."""
    _window(monkeypatch, 10, 1)
    files = {"docs/guide.md": guide(), "docs/vendored/copy.md": guide()}
    timeline.start(files, friction_config(exclude=["docs/vendored"]))
    for version in (2, 3):
        _cli(timeline, version)
    assert list(_broad(timeline)) == [("docs/guide.md", CLI)]


def test_the_human_view_names_the_record_s_bar_in_its_legend(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    _window(monkeypatch, 10, 1)
    timeline.start({"docs/guide.md": guide()})
    _cli(timeline, 2)
    human = fr.render_human(fr.run_repository_check(timeline.adopter.root))
    assert "1 over-broad anchor" in human
    assert "an anchor that flagged its artefact in more than 10 of the last 100 changes" in human
