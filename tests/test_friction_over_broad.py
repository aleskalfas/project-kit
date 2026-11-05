"""The warning on an over-broad anchor, `pkit friction check --all` (COR-050 point 7; #2636).

Of the newest `OVER_BROAD_WINDOW` commits on the first-parent line, each read against its
first parent, an anchor is over-broad when it flagged its artefact in more than
`OVER_BROAD_SHARE` of them, judged only where the line holds the whole window. An
artefact asked in more than `OVER_BROAD_UNCHANGED_ASKS` such commits for a revalidation
that left it as it was has the anchors that drive that count over-broad too: an anchor
flagged it in the commit, and its next revalidation on the line, in that commit or a later
one, left its content as it was when the commit flagged it. Its anchors are named by
their share, the largest first, until the asks in which only they asked are more than
`OVER_BROAD_CLEARED` of the artefact's asks (ADR-080). Every test lays down a real history
on an adopter whose install is committed once per session (`committed_adopter`): the
install's commit is the root, and the base the first commit counted. Some tests hold the
record's own numbers; the others set a window as long as the line (`_whole_line`), or a
bar of nothing, so a few commits show the counts. A window longer than the line keeps the
first bar away, and every test names by the shipped naming rule.

Held to: both bars, each on its own, and the first judged only over a whole window; the
second bar counted for the artefact, whichever of its anchors asked, each anchor with its
share, so splitting an anchor into section anchors leaves the count as it was; the anchors
it names — a single anchor, two that always ask together, five beside one, a tail of
small shares left out once the named anchors clear more than half, and a tie broken by the
order of declaration; an ask answered by a later revalidation, a sweep's or one in a commit
of its own, counted, and one an update answered, or that no revalidation follows, never; a
revalidation read from an answer file added or rewritten, or from a block, and none read
where a commit moved an answer from the block, renamed an answer file or wrote back an
earlier value; what a commit wrote read, never which answers are live
after it, as the change check reads them; every kind counted — path, record, artefact, a
registered kind's elsewhere (`test_friction_anchor_kinds`) — each by what it stands on at
HEAD; a collection entry counted apart from its file's other entries; renames of the
artefact and of its target followed; a flag reached through another artefact counted only
where that artefact changed; a change to a placed file's containers alone flagging no path
anchor; a commit before the artefact was there counted by the first bar and not the
second; only the window's commits counted; a merge read as one commit against its first
parent; the root and a shallow clone's cut not counted, and a window a shallow clone cut
short named so; an artefact that owes no answer, or an anchor reported dead, never
over-broad; a fix that suits what the anchor names; and the findings as the views show
them — the first bar's one for each anchor, the second bar's one for the artefact, its
anchors in order of share, while the JSON document lists each named anchor with its bar and
its share, and counts each, an anchor over both bars in both.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from project_kit import answer_files as af
from project_kit import friction_check as fc
from project_kit import friction_history as fh
from project_kit import friction_report as frep
from project_kit import friction_repository as fr
from project_kit.friction_discovery import Anchor
from project_kit.friction_write import answer_file_text
from tests.adopter_repo import AdopterRepo
from tests.friction_documents import (
    ADR,
    ADR_OVERLAY,
    T2,
    Timeline,
    adr,
    blocks_in_history,
    document,
    friction_config,
    guide,
    move_answers,
)

#: The documents here say each artefact's answers beside its anchors, and each write
#: takes them into answer files, as a change writes them (COR-062 point 1).
pytestmark = pytest.mark.usefixtures("answers_in_files")

REPO = Path(__file__).resolve().parents[1]
RECORD = REPO / "tech-docs/architecture/decisions/ADR-080-over-broad-anchor-flags.md"

CLI = Anchor("path", "src/cli/**")
CORE = Anchor("path", "src/core/**")
GUIDE = "docs/guide.md"
BOTH = {"path": ["src/cli/**", "src/core/**"]}


@pytest.fixture
def timeline(committed_adopter: AdopterRepo) -> Timeline:
    return Timeline(committed_adopter)


def _window(
    monkeypatch: pytest.MonkeyPatch, window: int, share: float = 0.0, unchanged: int = 10
) -> None:
    """A window of `window` commits and the bars `share` and `unchanged`. A share of
    nothing names by the first bar every anchor that flagged its artefact at all, with its
    counts, where the line holds the whole window; a window longer than the line names none
    by it. The second bar names by the shipped rule (`OVER_BROAD_CLEARED`), whatever the
    share."""
    monkeypatch.setattr(fr, "OVER_BROAD_WINDOW", window)
    monkeypatch.setattr(fr, "OVER_BROAD_SHARE", share)
    monkeypatch.setattr(fr, "OVER_BROAD_UNCHANGED_ASKS", unchanged)


def _broad(timeline: Timeline) -> dict[tuple[str | None, Anchor | None], str]:
    """Each over-broad finding's message, by its artefact's location and its anchor."""
    return _broad_in(timeline.adopter.root)


def _broad_in(root: Path) -> dict[tuple[str | None, Anchor | None], str]:
    result = fr.run_repository_check(root)
    return {
        (f.location, f.anchor): f.message
        for f in result.findings
        if f.kind is fr.RepositoryFindingKind.OVER_BROAD
    }


_COUNTS = re.compile(
    r"flagged its artefact in (\d+) of (?:the last (\d+) commits on the first-parent line"
    r"(, more than \d+% of them)?|the (\d+) commits on the first-parent line that this "
    r"shallow clone holds); in (\d+) of them(, more than \d+,)? its anchors asked it for a "
    r"revalidation that left it as it was, this anchor in (\d+) — "
)


def _count(message: str) -> tuple[int, int, int, int]:
    """What a message names: the anchor's flags, the window's size, the artefact's asks
    that left it as it was, and the anchor's share of those asks."""
    found = _COUNTS.match(message)
    assert found is not None, message
    return int(found[1]), int(found[2] or found[4]), int(found[5]), int(found[7])


def _whole_line(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch, share: float = 0.0, unchanged: int = 10
) -> dict[tuple[str | None, Anchor | None], str]:
    """Each over-broad finding's message, the window as long as the line the history holds
    now, so the first bar is judged on it (`_window`)."""
    commits = timeline.adopter.git("rev-list", "--first-parent", "--count", "HEAD").stdout
    _window(monkeypatch, int(commits) - 1, share, unchanged)  # the root is not counted
    return _broad(timeline)


def _bars(message: str) -> tuple[bool, bool]:
    """Which bars a message says the anchor crossed: the share, the asks that left the
    artefact as it was."""
    found = _COUNTS.match(message)
    assert found is not None, message
    return found[3] is not None, found[6] is not None


def _at(n: int) -> str:
    """A revalidation's `at`, a new one for each `n`."""
    return f"2026-10-05T{n // 60:02d}:{n % 60:02d}:00Z"


def _cli(
    timeline: Timeline,
    version: int,
    *,
    answered: bool = False,
    anchors: dict[str, list[str]] | None = None,
) -> str:
    """A commit to the CLI; with `answered`, one that revalidates the guide as it was, its
    `anchors` those of the CLI unless given."""
    files = {"src/cli/main.py": f"print('cli {version}')\n"}
    if answered:
        files[GUIDE] = guide(at=_at(version), **({} if anchors is None else {"anchors": anchors}))
    return timeline.commit(f"cli {version}", files)


def _engine(timeline: Timeline, version: int, **documents: str) -> str:
    return timeline.commit(
        f"engine {version}", {"src/core/engine.py": f"ENGINE = {version}\n", **documents}
    )


def _unrelated(timeline: Timeline, n: int) -> str:
    return timeline.commit(f"unrelated {n}", {"README.md": f"Hello {n}.\n"})


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


def _hub(anchors: list[str], n: int = 0) -> str:
    """`hub`, anchored to parts of other documents, revalidated as it was at `_at(n)`."""
    return document(
        "hub",
        anchors={"artefact": anchors},
        at=_at(n) if n else T2,
        outcome="unchanged" if n else "updated",
        because="it still says what it does" if n else None,
    )


# --- the record's numbers --------------------------------------------------------------------


def test_the_window_and_the_bars_are_the_record_s() -> None:
    """A hundred commits, more than half of them, or more than ten asks of the artefact
    that left it as it was, its anchors named until they clear more than half of those
    asks, in one finding for the artefact: the numbers ADR-080's decision states, which
    the message, the legend and `explain` render from these constants. The naming has a
    constant of its own, so a test that moves the first bar leaves it as shipped."""
    assert (
        fr.OVER_BROAD_WINDOW,
        fr.OVER_BROAD_SHARE,
        fr.OVER_BROAD_UNCHANGED_ASKS,
        fr.OVER_BROAD_CLEARED,
    ) == (100, 0.5, 10, 0.5)
    decision = RECORD.read_text(encoding="utf-8").split("## Decision", 1)[1]
    line = " ".join(decision.split("\n\n", 2)[1].split()).lower()
    assert (
        f"of the last {fr.OVER_BROAD_WINDOW} commits on the first-parent line" in line
        and "more than half of them" in line
        and f"in more than {fr.OVER_BROAD_UNCHANGED_ASKS} of them" in line
        and "only named anchors asked are more than half of the artefact's asks" in line
        and "in one finding for the artefact" in line
    ), line


def test_an_anchor_that_flagged_most_of_the_window_s_commits_is_over_broad(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first bar, over a window as long as the line: the CLI's anchor flagged the guide
    in the base and two edits, 3 of 4 commits, one of which revalidated the guide as it
    was. The engine's, in the base alone, is not named. No kind is registered, so nothing
    names less of the one file the CLI's glob stands on."""
    timeline.start({GUIDE: guide(anchors=BOTH)})
    _cli(timeline, 2, answered=True, anchors=BOTH)
    _cli(timeline, 3)
    _unrelated(timeline, 1)

    monkeypatch.setattr(fr, "OVER_BROAD_WINDOW", 4)
    broad = _broad(timeline)
    assert list(broad) == [(GUIDE, CLI)]
    assert broad[GUIDE, CLI] == (
        "flagged its artefact in 3 of the last 4 commits on the first-parent line, more than "
        "50% of them; in 1 of them its anchors asked it for a revalidation that left it as "
        "it was, this anchor in 1 — nothing names less of what it stands on: remove it "
        "unless the artefact rests on all of it, or split what it stands on into parts an "
        "anchor can name, or the artefact into parts that each rest on less"
    )


def test_a_line_shorter_than_the_window_is_not_judged_by_the_first_bar(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At the record's numbers, an anchor on `.` flags the guide in 1 of 1 commits, then 10
    of 10, and is not warned of: a young line's few commits say nothing of the line's. Over
    a window of 10, the line holds the whole window, and 10 of 10 crosses the first bar;
    over 4, the newest four, two of them unrelated (COR-050 point 7; ADR-080 point 3)."""
    whole = Anchor("path", ".")
    timeline.start({GUIDE: guide(anchors={"path": ["."]})})
    assert _broad(timeline) == {}

    for version in range(2, 11):
        _cli(timeline, version, answered=True, anchors={"path": ["."]})
    assert _broad(timeline) == {}
    monkeypatch.setattr(fr, "OVER_BROAD_WINDOW", 10)
    assert _count(_broad(timeline)[GUIDE, whole]) == (10, 10, 9, 9)
    assert _bars(_broad(timeline)[GUIDE, whole]) == (True, False)

    monkeypatch.setattr(fr, "OVER_BROAD_WINDOW", 4)  # two CLI commits, two unrelated
    _unrelated(timeline, 1)
    _unrelated(timeline, 2)
    assert _count(_broad(timeline)[GUIDE, whole]) == (4, 4, 2, 2)


def test_an_anchor_at_exactly_half_of_the_window_is_not_over_broad(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    timeline.start({GUIDE: guide()})
    _cli(timeline, 2)
    _unrelated(timeline, 1)
    _unrelated(timeline, 2)
    monkeypatch.setattr(fr, "OVER_BROAD_WINDOW", 4)
    assert _broad(timeline) == {}  # the CLI's anchor flagged 2 of 4


def test_an_anchor_whose_asks_bring_updates_is_not_warned_however_often_it_asks(
    timeline: Timeline,
) -> None:
    """At the record's numbers, the second bar. In 25 commits the engine's anchor flagged
    the page in the base and in eleven commits that updated the page, and the CLI's
    flagged the guide in the base and in eleven that revalidated it as it was: 12 of 25
    each, no more than half. Eleven asks that left the guide as it was are more than ten;
    none left the page so."""
    timeline.start({GUIDE: guide(), PAGE: _page()})
    for version in range(2, 13):
        _engine(timeline, version, **{PAGE: _page(busy=f"Busy {version}.", at=_at(version))})
    for version in range(2, 13):
        _cli(timeline, version, answered=True)
    _unrelated(timeline, 1)
    _unrelated(timeline, 2)

    broad = _broad(timeline)
    assert list(broad) == [(GUIDE, CLI)]
    assert _count(broad[GUIDE, CLI]) == (12, 25, 11, 11)
    assert _bars(broad[GUIDE, CLI]) == (False, True)


def test_a_commit_before_the_artefact_was_there_counts_for_the_first_bar_not_the_second(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI changed in the base and three times before the guide was added: each is a
    flag of the guide's anchor, which measures its breadth, but no ask that left it as it
    was, since the guide was not there at its first parent. Nor is the commit that added
    the guide. One CLI commit after it, revalidating the guide, is one such ask."""
    timeline.start({"docs/other.md": document("other", anchors={"path": ["src/core/**"]})})
    for version in (2, 3, 4):
        _cli(timeline, version)
    timeline.commit("add the guide", {GUIDE: guide()})
    broad = _whole_line(timeline, monkeypatch, share=0.5, unchanged=0)
    assert _count(broad[GUIDE, CLI]) == (4, 5, 0, 0)
    assert _bars(broad[GUIDE, CLI]) == (True, False)

    _cli(timeline, 5, answered=True)
    assert _count(_whole_line(timeline, monkeypatch, 0.5, 0)[GUIDE, CLI]) == (5, 6, 1, 1)


# --- the second bar, counted for the artefact ------------------------------------------------


def test_the_second_bar_counts_the_artefact_s_asks_whichever_anchor_asked(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At the record's second bar, the first out of reach on a line shorter than the
    window: six commits to the CLI and
    six to the engine each revalidate the guide as it was. Neither anchor asked it more
    than ten times; the guide was asked twelve times. Each anchor's six are no more than
    half of them, so both are warned of, each with its own six (ADR-080 point 3)."""
    _window(monkeypatch, 100)
    timeline.start({GUIDE: guide(anchors=BOTH)})
    for version in range(2, 8):
        _cli(timeline, version, answered=True, anchors=BOTH)
        _engine(timeline, version, **{GUIDE: guide(anchors=BOTH, at=_at(100 + version))})

    broad = _broad(timeline)
    assert sorted(broad, key=str) == [(GUIDE, CLI), (GUIDE, CORE)]
    assert _count(broad[GUIDE, CLI]) == (7, 13, 12, 6)
    assert _count(broad[GUIDE, CORE]) == (7, 13, 12, 6)
    assert _bars(broad[GUIDE, CLI]) == (False, True)

    monkeypatch.setattr(fr, "OVER_BROAD_UNCHANGED_ASKS", 12)
    assert _broad(timeline) == {}


def test_splitting_an_anchor_into_section_anchors_leaves_the_artefact_s_count(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hub anchors the page whole, and three edits of its busy section each revalidate
    the hub as it was: three asks. Split into anchors on the two sections, the hub is
    asked as often: the busy section's anchor asked it each time, and the quiet one's is
    not warned of, having asked nothing (critic C1, ADR-080 point 3)."""
    _window(monkeypatch, 10, unchanged=2)
    whole = Anchor("artefact", PAGE)
    busy, quiet = Anchor("artefact", f"{PAGE}#busy"), Anchor("artefact", f"{PAGE}#quiet")
    timeline.start({"docs/hub.md": _hub([PAGE]), PAGE: _page()})
    for edit in (1, 2, 3):
        timeline.commit(
            f"busy {edit}", {PAGE: _page(busy=f"Busy {edit}."), "docs/hub.md": _hub([PAGE], edit)}
        )
    assert _count(_broad(timeline)["docs/hub.md", whole]) == (4, 4, 3, 3)

    timeline.commit(
        "anchor the sections", {"docs/hub.md": _hub([f"{PAGE}#busy", f"{PAGE}#quiet"], 9)}
    )
    broad = _broad(timeline)
    assert list(broad) == [("docs/hub.md", busy)]
    assert _count(broad["docs/hub.md", busy]) == (4, 5, 3, 3)
    assert ("docs/hub.md", quiet) not in broad


# --- which anchors the second bar names ------------------------------------------------------
#
# The record's share, and enough unrelated commits that no anchor flagged its artefact in
# more than half of the window's: the first bar names nothing.

LIB = Anchor("path", "src/lib/**")
TAIL = tuple(Anchor("path", f"src/tail/{name}.py") for name in "abcd")


def _anchored(name: str, anchors: list[Anchor], n: int = 0) -> str:
    """`docs/<name>.md`, its path `anchors` in the order given, revalidated as it was at
    `_at(n)`, or at the base."""
    return document(
        name,
        anchors={"path": [anchor.value for anchor in anchors]},
        at=_at(n) if n else T2,
        outcome="unchanged",
        because="it still says what it does",
    )


def _asked(timeline: Timeline, n: int, sources: list[str], **anchored: list[Anchor]) -> str:
    """Commit `n`: an edit of each of `sources`, and each document `anchored` names
    revalidated as it was."""
    files = {source: f"EDIT = {n}\n" for source in sources}
    files.update({f"docs/{name}.md": _anchored(name, a, n) for name, a in anchored.items()})
    return timeline.commit(f"edit {n}", files)


def test_an_artefact_with_one_anchor_has_it_named(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Three CLI commits revalidate the guide as it was, more than the bar of two: its one
    anchor drives the whole count."""
    _window(monkeypatch, 100, share=0.5, unchanged=2)
    timeline.start({GUIDE: _anchored("guide", [CLI])})
    for n in (1, 2, 3):
        _asked(timeline, n, ["src/cli/main.py"], guide=[CLI])
    for n in (1, 2, 3, 4):
        _unrelated(timeline, n)

    broad = _broad(timeline)
    assert list(broad) == [(GUIDE, CLI)]
    assert _count(broad[GUIDE, CLI]) == (4, 8, 3, 3)
    assert _bars(broad[GUIDE, CLI]) == (False, True)


def _files(*anchors: Anchor) -> dict[str, str]:
    """A file for each of the path `anchors`, each on one file."""
    return {anchor.value: "EDIT = 0\n" for anchor in anchors}


def test_two_anchors_that_always_ask_together_are_named_together(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A and B asked the guide in the same six commits, C in four others: ten asks. A alone
    clears none of them, since B asked in each of its six; A and B together clear six,
    more than half, so both are named, and C is not (critic G1, ADR-080 point 3)."""
    _window(monkeypatch, 100, share=0.5, unchanged=9)
    a, b, c = (Anchor("path", f"src/{name}.py") for name in "abc")
    anchors = [a, b, c]
    timeline.start({GUIDE: _anchored("guide", anchors), **_files(*anchors)})
    for n in range(1, 7):
        _asked(timeline, n, [a.value, b.value], guide=anchors)
    for n in range(7, 11):
        _asked(timeline, n, [c.value], guide=anchors)

    broad = _broad(timeline)
    assert sorted(broad, key=str) == sorted([(GUIDE, a), (GUIDE, b)], key=str)
    assert _count(broad[GUIDE, a]) == (7, 11, 10, 6)
    assert _count(broad[GUIDE, b]) == (7, 11, 10, 6)


def test_five_anchors_that_ask_together_are_named_beside_one_that_asks_alone(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A1 to A5 asked the guide in the same six commits, B in six others: twelve asks, each
    anchor's share six. Named in the order declared, the five clear six, no more than
    half, so B is named too: all six are, and narrowing any fewer leaves more than half
    of the asks (critic G1, ADR-080 point 3)."""
    _window(monkeypatch, 100, share=0.5, unchanged=11)
    five = [Anchor("path", f"src/a{n}.py") for n in range(1, 6)]
    alone = Anchor("path", "src/b.py")
    anchors = [*five, alone]
    timeline.start({GUIDE: _anchored("guide", anchors), **_files(*anchors)})
    for n in range(1, 7):
        _asked(timeline, n, [anchor.value for anchor in five], guide=anchors)
    for n in range(7, 13):
        _asked(timeline, n, [alone.value], guide=anchors)

    broad = _broad(timeline)
    assert sorted(broad, key=str) == sorted(((GUIDE, anchor) for anchor in anchors), key=str)
    assert {_count(message)[2:] for message in broad.values()} == {(12, 6)}


def test_a_long_tail_of_small_shares_is_not_named(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI's anchor asked the guide in five commits, and each of four anchors on one
    file in one more: nine asks, over the bar of five. The CLI's five are more than half
    of them, so the four anchors with a share of one are not named."""
    _window(monkeypatch, 100, share=0.5, unchanged=5)
    anchors = [CLI, *TAIL]
    tail = {anchor.value: "TAIL = 0\n" for anchor in TAIL}
    timeline.start({GUIDE: _anchored("guide", anchors), **tail})
    for n in (1, 2, 3, 4, 5):
        _asked(timeline, n, ["src/cli/main.py"], guide=anchors)
    for n, anchor in enumerate(TAIL, start=6):
        _asked(timeline, n, [anchor.value], guide=anchors)
    for n in (1, 2):
        _unrelated(timeline, n)

    broad = _broad(timeline)
    assert list(broad) == [(GUIDE, CLI)]
    assert _count(broad[GUIDE, CLI]) == (6, 12, 9, 5)


def test_a_tie_is_broken_by_the_order_the_artefact_declares_its_anchors(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The library's anchor asked in four commits, the CLI's and the engine's in two each,
    each commit revalidating the guide and the manual as they were: eight asks of each.
    The library's four are no more than half, and the next anchor, either of two shares
    of two, brings them to six: the one each document declares first is named."""
    _window(monkeypatch, 100, share=0.5, unchanged=5)
    guide_s, manual_s = [LIB, CLI, CORE], [LIB, CORE, CLI]
    timeline.start(
        {
            GUIDE: _anchored("guide", guide_s),
            "docs/manual.md": _anchored("manual", manual_s),
            "src/lib/util.py": "LIB = 0\n",
        }
    )
    edits = ["src/lib/util.py"] * 4 + ["src/cli/main.py"] * 2 + ["src/core/engine.py"] * 2
    for n, source in enumerate(edits, start=1):
        _asked(timeline, n, [source], guide=guide_s, manual=manual_s)
    _unrelated(timeline, 1)

    broad = _broad(timeline)
    assert sorted(broad, key=str) == sorted(
        [(GUIDE, LIB), (GUIDE, CLI), ("docs/manual.md", LIB), ("docs/manual.md", CORE)], key=str
    )
    assert _count(broad[GUIDE, LIB]) == (5, 10, 8, 4)
    assert _count(broad[GUIDE, CLI]) == (3, 10, 8, 2)
    assert _count(broad["docs/manual.md", CORE]) == (3, 10, 8, 2)


def test_an_ask_left_as_debt_or_deferred_is_not_counted(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Of three CLI commits, one revalidates the guide as it was, one leaves it stale and
    one defers the CLI's anchor: only the first is an ask that left the guide as it was.
    The others report drift, which the guide owes still (critic C3)."""
    _window(monkeypatch, 10, unchanged=0)
    timeline.start({GUIDE: guide()})
    _cli(timeline, 2, answered=True)
    _cli(timeline, 3)
    deferral = [("path", "src/cli/**", "the CLI's help text is rewritten next")]
    _cli_files = {"src/cli/main.py": "print('cli 4')\n", GUIDE: guide(at=_at(2), deferred=deferral)}
    timeline.commit("cli 4, deferred", _cli_files)

    assert _count(_broad(timeline)[GUIDE, CLI]) == (4, 4, 1, 1)


def test_an_ask_is_counted_by_the_artefact_s_next_revalidation_on_the_line(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two CLI commits leave the guide stale and a third defers the CLI's anchor; a sweep
    then revalidates the guide as it was, answering all three. A CLI commit answered in a
    commit of its own, as a rebase lands one, is counted too. One answered by an update,
    with the guide's content changed, is not, nor is the newest, which nothing has
    revalidated yet (critic G3, ADR-080 point 3)."""
    timeline.start({GUIDE: guide()})
    _cli(timeline, 2)
    _cli(timeline, 3)
    deferral = [("path", "src/cli/**", "the CLI's help text is rewritten next")]
    timeline.commit(
        "cli 4, deferred",
        {"src/cli/main.py": "print('cli 4')\n", GUIDE: guide(deferred=deferral)},
    )
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (4, 4, 0, 0)

    timeline.commit("the sweep", {GUIDE: guide(at=_at(5))})
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (4, 5, 3, 3)

    _cli(timeline, 6)
    timeline.commit("its answer", {GUIDE: guide(at=_at(7))})
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (5, 7, 4, 4)

    _cli(timeline, 8)
    updated = guide(at=_at(9), outcome="updated", because=None, body="Body, updated.")
    timeline.commit("the update", {GUIDE: updated})
    _cli(timeline, 10)
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (7, 10, 4, 4)


def test_an_answer_in_a_block_is_read_and_one_moved_from_it_is_none(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before the answers moved into files, a revalidation was written in the artefact's
    block: two CLI commits revalidate the guide there. The move writes the block's answer
    in a file of its own; a CLI commit beside it revalidates nothing, since the answer was
    the block's already (COR-062 point 3)."""
    _window(monkeypatch, 10, unchanged=0)
    root = timeline.adopter.root
    with blocks_in_history():
        timeline.start({GUIDE: guide()})
        _cli(timeline, 2, answered=True)
        _cli(timeline, 3, answered=True)
    (root / "src/cli/main.py").write_text("print('cli 4')\n", encoding="utf-8")
    move_answers(root)
    timeline.adopter.git("add", "-A")
    timeline.commit_index("cli 4, and the move")

    assert _count(_broad(timeline)[GUIDE, CLI]) == (4, 4, 2, 2)


def test_an_answer_file_renamed_or_a_value_written_back_is_no_revalidation(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A revert of a revalidation writes the earlier `at` back in the guide's block; after
    the move, an answer file carries an `at` the block carried before; a CLI commit
    renames that answer file. None of them revalidates the guide, since its answers
    carried each value before (COR-050 point 3, COR-062 point 3): each of those commits
    flagged the guide, and none is an ask that left it as it was until a new value
    answers them, with the guide as it was."""
    root = timeline.adopter.root
    with blocks_in_history():
        timeline.start({GUIDE: guide()})
        _cli(timeline, 2, answered=True)
        third = _cli(timeline, 3, answered=True)
        timeline.revert(third)
    move_answers(root)
    timeline.adopter.git("add", "-A")
    timeline.commit_index("the move")
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (4, 5, 2, 2)

    timeline.commit(
        "cli 4, and an earlier value",
        {"src/cli/main.py": "print('cli 4')\n", GUIDE: guide(at=_at(3))},
    )
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (5, 6, 2, 2)

    newest = af.path_of(own_file_of(timeline, GUIDE))
    text = (root / newest).read_text(encoding="utf-8")
    renamed = af.path_of("20261005T000600Z-0000000f.yaml")
    timeline.commit(
        "cli 5, and a rename",
        {"src/cli/main.py": "print('cli 5')\n", newest: None, renamed: text},
    )
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (6, 7, 2, 2)

    _cli(timeline, 6, answered=True)  # a new value answers the three asks before it
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (7, 8, 6, 6)


def test_an_answer_file_rewritten_with_a_new_value_revalidates(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A change may rewrite an answer file it added itself, as a fix round does (COR-062
    point 3), and where its commits land one by one the rewrite is a commit of its own. A
    CLI commit adds an answer file revalidating the guide; the next leaves the guide stale;
    a third rewrites the file with a new `at`, the guide as it was, and answers it. A
    fourth rewrites the file again keeping that `at`, and revalidates nothing."""
    root = timeline.adopter.root
    timeline.start({GUIDE: guide()})
    _cli(timeline, 2, answered=True)
    own = af.path_of(own_file_of(timeline, GUIDE))
    _cli(timeline, 3)
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (3, 3, 1, 1)

    first = (root / own).read_text(encoding="utf-8")
    rewritten = first.replace(_at(2), _at(4))
    assert rewritten != first, first
    timeline.commit("the fix round", {own: rewritten})
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (3, 4, 2, 2)

    _cli(timeline, 5)
    again = rewritten.replace("unchanged-because: ", "unchanged-because: Again, ")
    timeline.commit("the file again", {own: again})
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (4, 6, 2, 2)


def own_file_of(timeline: Timeline, location: str) -> str:
    """The name of the newest committed answer file naming `location`."""
    root = timeline.adopter.root
    log = timeline.adopter.git(
        "log", "--format=", "--name-only", "--diff-filter=A", "--", af.FOLDER
    ).stdout.split()
    files = af.working_tree_files(root)
    return next(
        af.name_of(rel)
        for rel in log
        if af.name_of(rel) in files
        and any(e.location == location for e in files[af.name_of(rel)].entries)
    )


def test_the_count_reads_what_a_commit_wrote_not_the_answers_live_after_it(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The change check judges the answers live at a change's head against its base's values;
    the count reads what each commit wrote, since reading which answers are live at every
    commit costs too much (ADR-080 point 1). One commit adds two answers on the guide: one
    with a new `at`, and one that reads it and writes back an earlier `at`. Only the
    second is live, and it is new to nothing, so the change check finds the guide owing
    its answer still; the count reads the first, and counts the ask."""
    root, repo = timeline.adopter.root, timeline.adopter
    timeline.start({GUIDE: guide()})
    _cli(timeline, 2, answered=True)
    earlier = af.working_tree_files(root)
    repo.checkout("topic", create=True)
    because = "the CLI surface is as described"
    new, back = "20261005T000300Z-0000000a.yaml", "20261005T000300Z-0000000b.yaml"

    def answers(at: str, read: list[str]) -> str:
        entry: dict[str, object] = {af.ARTEFACT_KEY: GUIDE}
        if read:
            entry[af.READ_KEY] = read
        entry[af.REVALIDATED_KEY] = {"at": at, "outcome": "unchanged", "unchanged-because": because}
        return answer_file_text([entry])[0]

    timeline.commit(
        "cli 3, an answer and its write-back",
        {
            "src/cli/main.py": "print('cli 3')\n",
            af.path_of(new): answers(_at(3), []),
            af.path_of(back): answers(_at(2), [*sorted(earlier), new]),
        },
    )

    change = fc.run_change_check(root, "main")
    owed = [f for f in change.findings if f.kind is fc.FindingKind.FRICTION]
    assert [f.location for f in owed] == [GUIDE]
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (3, 3, 2, 2)


def test_a_collection_entry_is_counted_apart_from_its_file_s_other_entries(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two entries of one file, each anchored to the engine. Both are revalidated as they
    were by the first engine commit; the second edits RS-2's text, so only RS-1 is left as
    it was; the third revalidates neither."""
    _window(monkeypatch, 10, unchanged=0)
    rules = "docs/rules.md"

    def collection(rs1: int, rs2: int, text: str = "Two.") -> str:
        front = {
            entry: {
                "pkit": {
                    "friction": {
                        "anchors": {"path": ["src/core/**"]},
                        "revalidated": {
                            "at": _at(n),
                            "outcome": "unchanged",
                            "unchanged-because": "holds",
                        },
                    }
                }
            }
            for entry, n in (("RS-1", rs1), ("RS-2", rs2))
        }
        body = f"## RS-1 — One\n\nOne.\n\n## RS-2 — Two\n\n{text}\n"
        return f"---\n{json.dumps(front)}\n---\n\n{body}"

    timeline.start({rules: collection(1, 1)})
    _engine(timeline, 2, **{rules: collection(2, 2)})
    _engine(timeline, 3, **{rules: collection(3, 3, "Two, edited.")})
    _engine(timeline, 4)

    broad = _broad(timeline)
    assert _count(broad[f"{rules}#RS-1", CORE]) == (4, 4, 2, 2)
    assert _count(broad[f"{rules}#RS-2", CORE]) == (4, 4, 1, 1)


def test_a_rename_of_the_artefact_or_of_its_target_in_the_window_is_followed(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guide is renamed between two pairs of CLI commits that revalidate it: its asks
    are read under both names. The hub names the page by its id, and the page is renamed
    between two pairs of edits that revalidate the hub: the anchor flags across the
    rename, which itself changed no content."""
    _window(monkeypatch, 20, unchanged=0)
    by_id = Anchor("artefact", "page")
    timeline.start({GUIDE: guide(), "docs/hub.md": _hub(["page"]), PAGE: _page()})
    for version in (2, 3):
        _cli(timeline, version, answered=True)
        timeline.commit(
            f"busy {version}",
            {PAGE: _page(busy=f"Busy {version}."), "docs/hub.md": _hub(["page"], version)},
        )
    timeline.rename(GUIDE, "docs/manual.md")
    timeline.rename(PAGE, "docs/pages/page.md")
    for version in (4, 5):
        timeline.commit(
            f"cli {version}",
            {
                "src/cli/main.py": f"print('cli {version}')\n",
                "docs/manual.md": guide(at=_at(version)),
            },
        )
        timeline.commit(
            f"busy {version}",
            {
                "docs/pages/page.md": _page(busy=f"Busy {version}."),
                "docs/hub.md": _hub(["page"], version),
            },
        )

    broad = _broad(timeline)
    assert _count(broad["docs/manual.md", CLI]) == (5, 11, 4, 4)
    assert _count(broad["docs/hub.md", by_id]) == (5, 11, 4, 4)


# --- what an anchor stands on, kind by kind --------------------------------------------------


def test_a_path_anchor_counts_the_commits_that_touched_what_it_stands_on(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    timeline.start({GUIDE: guide(anchors=BOTH)})
    for version in (2, 3, 4):
        _cli(timeline, version, answered=True, anchors=BOTH)
    _engine(timeline, 2, **{GUIDE: guide(anchors=BOTH, at=_at(9))})
    _unrelated(timeline, 1)

    broad = _whole_line(timeline, monkeypatch)
    assert _count(broad[GUIDE, CLI]) == (4, 6, 4, 3)
    assert _count(broad[GUIDE, CORE]) == (2, 6, 4, 1)


def test_an_artefact_anchor_on_a_busy_page_is_over_broad_and_one_on_a_quiet_section_is_not(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The issue's case, over a window as long as the line: a page anchoring another whole is
    asked at each of its edits; anchored on the section it rests on, only when that
    section changes."""
    whole, quiet = Anchor("artefact", PAGE), Anchor("artefact", f"{PAGE}#quiet")
    timeline.start({"docs/hub.md": _hub([PAGE, f"{PAGE}#quiet"]), PAGE: _page()})
    for edit in (1, 2, 3):
        timeline.commit(f"busy {edit}", {PAGE: _page(busy=f"Busy {edit}.")})

    monkeypatch.setattr(fr, "OVER_BROAD_WINDOW", 4)
    broad = _broad(timeline)
    assert list(broad) == [("docs/hub.md", whole)]
    assert _count(broad["docs/hub.md", whole]) == (4, 4, 0, 0)
    assert broad["docs/hub.md", whole].endswith(
        "anchor only the sections of it, or its lead, that the artefact rests on"
    )
    assert ("docs/hub.md", quiet) not in broad  # flagged once, where the base added it


def test_a_flag_reached_through_another_artefact_counts_only_where_it_changed(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The engine flags the page twice. Revalidated as it was, the page's content stays
    the same, so the hub that anchors it is not flagged; updated, its content changes and
    flags the hub, as the change check's cascade reads it (ADR-080 point 1). The update
    revalidates the hub as it was."""
    on_page = Anchor("artefact", PAGE)
    timeline.start({"docs/hub.md": _hub([PAGE]), PAGE: _page()})
    _engine(timeline, 2, **{PAGE: _page(at=T2, outcome="unchanged", because="it still says it")})
    _engine(
        timeline,
        3,
        **{
            PAGE: _page(busy="Busy, again.", at="2026-10-03T09:00:00Z", outcome="updated"),
            "docs/hub.md": _hub([PAGE], 1),
        },
    )

    broad = _whole_line(timeline, monkeypatch)
    assert _count(broad[PAGE, CORE]) == (3, 3, 1, 1)  # the base, and each engine commit
    assert _count(broad["docs/hub.md", on_page]) == (2, 3, 1, 1)  # the base, and the update


def test_a_change_to_a_placed_file_s_containers_alone_flags_no_path_anchor(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Markdown file a place holds is read by its content (COR-050 point 5): a commit
    that wrote only its `pkit` container is no change to a path anchor on it."""
    on_page = Anchor("path", PAGE)
    timeline.start({GUIDE: guide(anchors={"path": [PAGE]}), PAGE: _page()})
    timeline.commit("anchor the page wider", {PAGE: _page(anchors={"path": ["src/**"]})})
    timeline.commit("anchor it back", {PAGE: _page()})
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, on_page]) == (
        1,
        3,
        0,
        0,
    )  # the base alone

    timeline.commit(
        "edit the page",
        {PAGE: _page(quiet="Quiet, edited."), GUIDE: guide(anchors={"path": [PAGE]}, at=_at(1))},
    )
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, on_page]) == (2, 4, 1, 1)


def test_a_record_anchor_counts_the_commits_to_what_its_point_stands_on(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point 3 changes three times, point 1 never after the base. Nothing names less than
    a point, and the finding says so."""
    one, three = Anchor("record", "ADR-007#1"), Anchor("record", "ADR-007#3")
    anchored = guide(anchors={"record": ["ADR-007#1", "ADR-007#3"]})
    timeline.start({**ADR_OVERLAY, ADR: adr(), GUIDE: anchored})
    for edit in (1, 2, 3):
        decision = (
            "## Decision\n\nThe engine stays one module.\n\n### 1. One\n\nOne.\n\n"
            f"### 3. Three\n\nThree, edited {edit}.\n"
        )
        timeline.commit(f"point 3, edit {edit}", {ADR: adr(body=decision)})

    broad = _whole_line(timeline, monkeypatch)
    assert _count(broad[GUIDE, one]) == (1, 4, 0, 0)
    assert _count(broad[GUIDE, three]) == (4, 4, 0, 0)
    assert broad[GUIDE, three].endswith(
        "nothing names less of what it stands on: remove it unless the artefact rests on all "
        "of it, or split what it stands on into parts an anchor can name, or the artefact "
        "into parts that each rest on less"
    )


# --- what the finding says to do --------------------------------------------------------------


def test_the_fix_suits_what_the_anchor_names(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A glob on several files: narrow it. A whole record with points, or its file: anchor
    its points. A document's file, or a section that holds a sub-section: anchor those. A
    lead, and a code file where no kind is registered: nothing names less, and the
    message offers splitting what it stands on, or the artefact (ADR-080 point 3)."""
    page = document("page", anchors={"path": ["src/core/**"]}, body="Lead.\n\n## A\n\n### B\n\nB.")
    anchors = {
        "path": ["src/**", ADR, PAGE, "src/cli/main.py"],
        "record": ["ADR-007"],
        "artefact": [f"{PAGE}#a", f"{PAGE}#"],
    }
    timeline.start({**ADR_OVERLAY, ADR: adr(), PAGE: page, GUIDE: guide(anchors=anchors)})

    broad = _whole_line(timeline, monkeypatch)
    fixes = {
        anchor.value: message.split(" — ", 1)[1]
        for (location, anchor), message in broad.items()
        if location == GUIDE and anchor is not None
    }
    nothing = (
        "nothing names less of what it stands on: remove it unless the artefact rests on all "
        "of it, or split what it stands on into parts an anchor can name, or the artefact "
        "into parts that each rest on less"
    )
    assert fixes == {
        "src/**": "narrow it to the files the artefact rests on",
        ADR: "anchor only the points of the record the artefact rests on",
        PAGE: "anchor only the sections of it, or its lead, that the artefact rests on",
        "src/cli/main.py": nothing,
        "ADR-007": "anchor only the points of the record the artefact rests on",
        f"{PAGE}#a": "anchor only the sub-sections of it the artefact rests on",
        f"{PAGE}#": nothing,
    }


# --- the window ----------------------------------------------------------------------------


def test_only_the_window_s_commits_count(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    timeline.start({GUIDE: guide()})
    for version in (2, 3, 4):
        _cli(timeline, version, answered=True)
    for n in (1, 2):
        _unrelated(timeline, n)

    _window(monkeypatch, 3)  # the two unrelated commits and the last CLI commit
    assert _count(_broad(timeline)[GUIDE, CLI]) == (1, 3, 1, 1)
    _window(monkeypatch, 5)
    assert _count(_broad(timeline)[GUIDE, CLI]) == (3, 5, 3, 3)


def test_a_merge_on_the_line_is_one_commit_against_its_first_parent(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The branch's two CLI commits are not on the line; the merge that brings them in is
    one commit, read against its first parent, which lists the CLI though git's combined
    diff does not. The branch revalidated the guide, so the merge answered its ask."""
    repo = timeline.adopter
    base = timeline.start({GUIDE: guide()})
    repo.checkout("topic", create=True)
    _cli(timeline, 2)
    _cli(timeline, 3, answered=True)
    repo.checkout("main")
    beside = _unrelated(timeline, 1)
    merge = timeline.merge("topic")

    history = fh.read_history(repo.root, merge)
    changes = fh.first_parent_changes(repo.root, history, 10)
    assert [history.commits[c.index].sha for c in changes] == [merge, beside, base]
    assert sorted(e.path for e in changes[0].entries if not e.path.startswith(".pkit/")) == [
        "src/cli/main.py"
    ]
    assert not fh.cut_short(history, changes, 10)
    assert _count(_whole_line(timeline, monkeypatch)[GUIDE, CLI]) == (2, 3, 1, 1)


def test_the_line_ends_before_the_root_and_before_a_shallow_clone_s_cut(
    timeline: Timeline, tmp_path: Path
) -> None:
    """Neither has a parent in the clone to be compared with, so neither is counted. A
    line that ends at the root holds all there is; one cut by a shallow clone is told
    apart, the clone lacking history that exists."""
    repo = timeline.adopter
    base = timeline.start({GUIDE: guide()})
    second, third = _cli(timeline, 2), _cli(timeline, 3)

    history = fh.read_history(repo.root, third)
    changes = fh.first_parent_changes(repo.root, history, 10)
    assert [history.commits[c.index].sha for c in changes] == [third, second, base]
    assert len(fh.first_parent_changes(repo.root, history, 2)) == 2
    assert not fh.cut_short(history, changes, 10)

    shallow = tmp_path / "shallow"
    repo.git("clone", "-q", "--depth", "2", f"file://{repo.root}", str(shallow))
    cut = fh.read_history(shallow, third)
    in_clone = fh.first_parent_changes(shallow, cut, 10)
    assert [cut.commits[c.index].sha for c in in_clone] == [third]
    assert fh.cut_short(cut, in_clone, 10)
    assert not fh.cut_short(cut, in_clone, 1)  # the window is full: nothing is missing


def test_a_window_a_shallow_clone_cut_short_is_not_judged_by_the_first_bar(
    timeline: Timeline, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In a clone two commits deep, the window holds the newest CLI commit alone: the CLI's
    anchor flagged the guide in 1 of 1, which the first bar does not judge, since the
    clone holds less than the window. The full history, as long as the window, warns. The
    second bar reads what the clone holds, and the message says the window was cut, and
    at how many (architect item 5)."""
    repo = timeline.adopter
    timeline.start({GUIDE: guide()})
    _cli(timeline, 2, answered=True)
    _cli(timeline, 3, answered=True)
    shallow = tmp_path / "shallow"
    repo.git("clone", "-q", "--depth", "2", f"file://{repo.root}", str(shallow))
    monkeypatch.setattr(fr, "OVER_BROAD_WINDOW", 3)
    assert _broad_in(shallow) == {}
    assert _count(_broad(timeline)[GUIDE, CLI]) == (3, 3, 2, 2)  # the full history warns

    monkeypatch.setattr(fr, "OVER_BROAD_UNCHANGED_ASKS", 0)
    message = _broad_in(shallow)[GUIDE, CLI]
    assert message.startswith(
        "flagged its artefact in 1 of the 1 commits on the first-parent line that this "
        "shallow clone holds; in 1 of them, more than 0, its anchors"
    )
    assert _count(message) == (1, 1, 1, 1)
    assert _bars(message) == (False, True)


# --- what is never over-broad --------------------------------------------------------------


def test_an_artefact_that_owes_no_answer_has_no_over_broad_anchor(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An artefact under an excluded path is never asked for an answer, so no commit
    flags it (ADR-080 point 1)."""
    files = {GUIDE: guide(), "docs/vendored/copy.md": guide()}
    timeline.start(files, friction_config(exclude=["docs/vendored"]))
    for version in (2, 3):
        _cli(timeline, version)
    assert list(_whole_line(timeline, monkeypatch)) == [(GUIDE, CLI)]


def test_an_anchor_reported_dead_is_not_counted(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The engine's files are gone at HEAD, so its anchor is dead, and reported so alone,
    though the window's commits touched them."""
    _window(monkeypatch, 10)
    timeline.start({GUIDE: guide(anchors=BOTH)})
    _engine(timeline, 2)
    timeline.commit("drop the engine", {"src/core/engine.py": None})

    result = fr.run_repository_check(timeline.adopter.root)
    kinds = {(f.kind, f.anchor) for f in result.findings if f.anchor == CORE}
    assert kinds == {(fr.RepositoryFindingKind.DEAD_ANCHOR, CORE)}


def test_the_human_view_names_the_record_s_bars_in_its_legend(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    timeline.start({GUIDE: guide()})
    _cli(timeline, 2)
    _whole_line(timeline, monkeypatch)
    human = fr.render_human(fr.run_repository_check(timeline.adopter.root))
    assert "1 over-broad" in human
    assert (
        "an anchor that flagged its artefact in more than 50% of the last 100 commits on the "
        "first-parent line; or, of an artefact asked in more than 10 of them for a "
        "revalidation that left it as it was, the anchors behind most of those asks, in one "
        "finding for the artefact"
    ) in human


# --- how the findings are shown ----------------------------------------------------------------


def _shown(root: Path, location: str) -> list[str]:
    """The lines the human view gives under `location`'s line, up to the next artefact's."""
    lines = fr.render_human(fr.run_repository_check(root)).splitlines()
    start = next(n for n, line in enumerate(lines) if line.startswith(f"  {location}"))
    under = []
    for line in lines[start + 1 :]:
        if not line.startswith("    "):
            break
        under.append(" ".join(line.split()))
    return under


def _bars_in_json(root: Path) -> list[tuple[str | None, str | None, str | None, int | None]]:
    """(location, anchor value, bar, share) of each over-broad finding the JSON document
    lists, in its order."""
    document = json.loads(fr.render_json(fr.run_repository_check(root)))
    return [
        (f["location"], f["anchor"]["value"], f["bar"], f["share"])
        for f in document["findings"]
        if f["kind"] == "over-broad"
    ]


def test_the_second_bar_is_one_finding_for_the_artefact_its_anchors_by_share(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guide declares the CLI's anchor before the library's. The library's asked it in
    four commits, the CLI's and the engine's in two each: eight asks, over the bar of five.
    The human view gives one finding for the guide. It names the library's anchor first,
    with the narrower anchor its glob on two files has, then the CLI's, which nothing
    narrower names here, and ends with the advice for the artefact. The JSON document
    lists each named anchor apart, in the same order, with its bar and its share, and its
    count of over-broad findings counts each, where the summary counts the guide's once
    (ADR-080 point 3)."""
    _window(monkeypatch, 100, share=0.5, unchanged=5)
    anchors = [CLI, LIB, CORE]
    timeline.start(
        {
            GUIDE: _anchored("guide", anchors),
            "src/lib/util.py": "LIB = 0\n",
            "src/lib/more.py": "MORE = 0\n",
        }
    )
    edits = ["src/lib/util.py"] * 4 + ["src/cli/main.py"] * 2 + ["src/core/engine.py"] * 2
    for n, source in enumerate(edits, start=1):
        _asked(timeline, n, [source], guide=anchors)

    root = timeline.adopter.root
    under = _shown(root, GUIDE)
    assert under[0].startswith(
        "over-broad — the artefact was asked in 8 of the last 9 commits on the first-parent "
        "line, more than 5, for a revalidation that left it as it was; the anchors behind most "
        "of those asks, by their share of them, the largest first:"
    ), under
    assert under[1:] == [
        "path src/lib/** 4 narrow it to the files the artefact rests on",
        "path src/cli/** 2",
        fr.ASKED_ADVICE,
    ]
    assert _bars_in_json(root) == [(GUIDE, LIB.value, "asks", 4), (GUIDE, CLI.value, "asks", 2)]
    result = fr.run_repository_check(root)
    assert json.loads(fr.render_json(result))["counts"]["over-broad"] == 2
    assert "1 over-broad" in fr.render_human(result).splitlines()[0]

    explanation = frep.run_explain(root, GUIDE)
    explained = frep.render_explain_human(explanation).splitlines()
    start = next(n for n, line in enumerate(explained) if line.startswith("  over-broad"))
    assert [" ".join(line.split()) for line in explained[start + 1 : start + 4]] == [
        "path src/lib/** 4 narrow it to the files the artefact rests on",
        "path src/cli/** 2",
        f"clears it — {fr.ASKED_ADVICE}; then revalidate (a changed anchor list needs a "
        f"revalidation)",
    ]
    document = json.loads(frep.render_explain_json(explanation))
    assert [
        (f["anchor"]["value"], f["bar"], f["share"])
        for f in document["findings"]
        if f["kind"] == "over-broad"
    ] == [(LIB.value, "asks", 4), (CLI.value, "asks", 2)]


def test_the_first_bar_is_a_finding_for_each_anchor(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI's anchor and the engine's each flagged the guide in every commit, and none
    revalidated it: each crosses the first bar, and each has a finding of its own, with
    its own message (ADR-080 point 3)."""
    timeline.start({GUIDE: guide(anchors=BOTH)})
    for version in (2, 3, 4):
        timeline.commit(
            f"both {version}",
            {"src/cli/main.py": f"CLI = {version}\n", "src/core/engine.py": f"E = {version}\n"},
        )
    broad = _whole_line(timeline, monkeypatch, share=0.5)
    assert list(broad) == [(GUIDE, CLI), (GUIDE, CORE)]

    root = timeline.adopter.root
    under = _shown(root, GUIDE)
    flagged = [line for line in under if line.startswith("over-broad")]
    assert [line.split(" flagged ", 1)[0] for line in flagged] == [
        "over-broad path src/cli/**",
        "over-broad path src/core/**",
    ]
    assert _bars_in_json(root) == [
        (GUIDE, CLI.value, "flags", None),
        (GUIDE, CORE.value, "flags", None),
    ]
    assert "2 over-broad" in fr.render_human(fr.run_repository_check(root)).splitlines()[0]


def test_an_anchor_over_both_bars_is_in_both_findings(
    timeline: Timeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI's anchor flagged the guide in each of the line's commits but one, and four
    of them revalidated it as it was, over the bar of three: the anchor has the first
    bar's finding of its own, and the guide's one finding for the second bar names it
    too. The JSON document lists it once for each bar (ADR-080 point 3)."""
    timeline.start({GUIDE: guide()})
    for version in (2, 3, 4, 5):
        _cli(timeline, version, answered=True)
    _unrelated(timeline, 1)
    _whole_line(timeline, monkeypatch, share=0.5, unchanged=3)

    root = timeline.adopter.root
    under = _shown(root, GUIDE)
    assert under[0].startswith("over-broad path src/cli/** flagged its artefact in 5 of the last 6")
    assert under[1].startswith("over-broad — the artefact was asked in 4 of the last 6 commits")
    assert under[2:] == ["path src/cli/** 4", fr.ASKED_ADVICE]
    assert _bars_in_json(root) == [(GUIDE, CLI.value, "flags", None), (GUIDE, CLI.value, "asks", 4)]
    assert "2 over-broad" in fr.render_human(fr.run_repository_check(root)).splitlines()[0]
