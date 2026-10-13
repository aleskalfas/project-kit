"""`pkit decisions check-diff`: a change's numbering, checked against its base (COR-058 point 8).

Each test builds a repository whose `main` holds the records at the branch point,
cuts a branch `change`, and edits the working tree there. Where the default
branch moved on, `main` gains a commit after the branch left it. The command
reads its base as every comparison does (COR-054): with no remote, the local
`main`, said on standard error.

Each case is tested failing and passing, and each finding names the record and
the id.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from project_kit import decisions_check_diff, record_points
from project_kit.cli import main
from tests.adopter_repo import GitRepo, MakeAdopterRepo

PROJECT = ".pkit/decisions/project"
RECORD = f"{PROJECT}/PRJ-001-a.md"


def _record(decision: str, *, record_id: str = "PRJ-001", extra: str = "") -> str:
    """A record whose Decision is `decision`, with `extra` lines in its front matter."""
    return (
        f"---\nid: {record_id}\ntitle: A record\nstatus: accepted\ndate: 2026-10-13\n"
        f"author: t\n{extra}---\n\n## Context\n\nWhy.\n\n## Decision\n\nWhat.\n\n{decision}\n"
        f"## Rationale\n\nBecause.\n"
    )


def _points(*ids: str, text: str = "Text of") -> str:
    """A point heading `### <id>. Point <id>` and one line of text each."""
    return "".join(_point(point_id, text=text) for point_id in ids)


def _point(point_id: str, *, title: str | None = None, text: str = "Text of") -> str:
    heading = f"{point_id}. {title or f'Point {point_id}'}"
    if not point_id.isdigit():
        heading = f"{point_id} — {title or f'Point {point_id}'}"
    return f"### {heading}\n\n{text} {point_id}.\n\n"


def _stub(point_id: str, sentence: str) -> str:
    return f"### {point_id}. Retired\n\n{sentence}\n\n"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GitRepo:
    """A repository on `main` with no commit yet, the command's working directory."""
    made = GitRepo.init(tmp_path / "work")
    monkeypatch.chdir(made.root)
    monkeypatch.delenv("PKIT_CHECK_BASE", raising=False)
    return made


def _branch(repo: GitRepo, records: dict[str, str]) -> None:
    """`main` holds `records` at the branch point, and the branch `change` leaves it."""
    repo.commit("records", records)
    repo.checkout("change", create=True)


def _land(repo: GitRepo, records: dict[str, str]) -> None:
    """Another change lands `records` on `main` after `change` left it."""
    repo.checkout("main")
    repo.commit("another change", records)
    repo.checkout("change")


def _run(*args: str) -> Result:
    return CliRunner().invoke(main, ["decisions", "check-diff", *args])


def _found(repo: GitRepo) -> list[tuple[str, str]]:
    """Each finding as `(severity, location)`, through the module."""
    head = decisions_check_diff.head_records(repo.root)
    fork = repo.git("merge-base", "main", "HEAD").stdout.strip()
    tip = repo.git("rev-parse", "main").stdout.strip()
    report = decisions_check_diff.check(repo.root, head, base="main", fork=fork, tip=tip)
    return [(finding.severity.value, finding.location) for finding in report.findings]


def _messages(repo: GitRepo) -> list[str]:
    head = decisions_check_diff.head_records(repo.root)
    fork = repo.git("merge-base", "main", "HEAD").stdout.strip()
    tip = repo.git("rev-parse", "main").stdout.strip()
    report = decisions_check_diff.check(repo.root, head, base="main", fork=fork, tip=tip)
    return [finding.message for finding in report.findings]


# --- the change's own edits ----------------------------------------------------------


def test_a_point_edited_in_place_and_a_new_point_past_every_id_pass(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2", "3"))})
    repo.write(
        {RECORD: _record(_points("1") + _point("4") + _point("2", text="Edited") + _points("3"))}
    )

    result = _run()

    assert result.exit_code == 0, result.output
    assert "0 error(s) and 0 warning(s)" in result.output


def test_a_point_dropped_without_being_retired_fails_and_one_retired_passes(
    repo: GitRepo,
) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2", "3"))})
    repo.write({RECORD: _record(_points("1", "3"))})
    assert _found(repo) == [("error", f"{RECORD}#2")]
    assert (
        "the branch point holds `2`, and the head neither holds nor retires it"
        in (_messages(repo)[0])
    )

    retired = 'retired-points:\n  "2": []\n'
    stub = _stub("2", "Its content is in no other point.")
    repo.write({RECORD: _record(_points("1") + stub + _points("3"), extra=retired)})
    assert _found(repo) == []


def test_a_retired_id_the_head_no_longer_retires_fails(repo: GitRepo) -> None:
    retired = 'retired-points:\n  "2": []\n'
    stub = _stub("2", "Its content is in no other point.")
    _branch(repo, {RECORD: _record(_points("1") + stub + _points("3"), extra=retired)})
    repo.write({RECORD: _record(_points("1", "3"))})

    assert _found(repo) == [("error", f"{RECORD}#2")]
    assert "the branch point retires `2`" in _messages(repo)[0]


def test_a_new_id_not_past_every_id_fails_naming_the_next_unused(repo: GitRepo) -> None:
    retired = 'retired-points:\n  "4": []\n'
    stub = _stub("4", "Its content is in no other point.")
    _branch(repo, {RECORD: _record(_points("1", "2", "5") + stub, extra=retired)})
    repo.write({RECORD: _record(_points("1", "2", "3", "5") + stub, extra=retired)})

    assert _found(repo) == [("error", f"{RECORD}#3")]
    assert "the new id `3` is not past every id" in _messages(repo)[0]
    assert "`6`" in _messages(repo)[0]

    repo.write({RECORD: _record(_points("1", "2", "6", "5") + stub, extra=retired)})
    assert _found(repo) == []


def test_a_new_label_not_past_its_series_fails(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1", "D1", "D3"))})
    repo.write({RECORD: _record(_points("1", "D1", "D2", "D3"))})

    assert _found(repo) == [("error", f"{RECORD}#D2")]
    assert "`D4`" in _messages(repo)[0]


def test_the_next_unused_id_named_is_past_the_heads_ids_too(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2", "5"))})
    repo.write({RECORD: _record(_points("1", "2", "3", "5", "6"))})

    assert _found(repo) == [("error", f"{RECORD}#3")]
    assert "the next unused number, `7`" in _messages(repo)[0]


def test_a_label_counts_in_its_own_series(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2") + _points("D1", "D2"))})
    repo.write({RECORD: _record(_points("1", "2", "3") + _points("D1", "D2", "D1"))})

    found = _found(repo)

    assert ("error", f"{RECORD}#D1") in found  # the duplicate the change added
    assert ("error", f"{RECORD}#3") not in found  # past every number, whatever the labels


def test_a_renumbered_point_fails_where_its_text_sits_only_under_another_id(
    repo: GitRepo,
) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2", "3"))})
    renumbered = "### 4. Point 3\n\nText of 3.\n\n"
    repo.write({RECORD: _record(_points("1", "2") + renumbered)})

    # Two errors on one id: `3` is dropped, and its text sits under `4` alone.
    assert _found(repo) == [("error", f"{RECORD}#3"), ("error", f"{RECORD}#3")]
    messages = _messages(repo)
    assert "the branch point holds `3`, and the head neither holds nor retires it" in messages[0]
    assert (
        "the text of point `3` at the branch point sits at the head only under `4`" in (messages[1])
    )


def test_a_retirement_whose_successor_kept_the_claim_fails(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2", "3"))})
    retired = 'retired-points:\n  "2": ["4"]\n'
    kept = _point("1") + _stub("2", "Its content is in point 4.") + _point("3")
    kept += _point("4", title="Point 2", text="Text of").replace("Text of 4.", "Text of 2.")
    repo.write({RECORD: _record(kept, extra=retired)})

    assert _found(repo) == [("error", f"{RECORD}#2")]
    assert "a retirement whose successor kept the claim" in _messages(repo)[0]


def test_a_title_under_another_id_with_its_text_changed_warns(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1") + _point("2", title="Scope") + _points("3"))})
    moved = _points("1", "3") + _point("4", title="Scope", text="Rewritten")
    retired = 'retired-points:\n  "2": ["4"]\n'
    stub = _stub("2", "Its content is in point 4.")
    repo.write({RECORD: _record(_points("1") + stub + moved[len(_points("1")) :], extra=retired)})

    assert _found(repo) == [("warning", f"{RECORD}#2")]
    result = _run()
    assert result.exit_code == 0, result.output
    assert '"Scope", sits at the head under `4`, with its text changed' in result.output


def test_a_duplicate_id_the_change_adds_fails_and_one_the_base_held_does_not(
    repo: GitRepo,
) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2", "2"))})
    repo.write({RECORD: _record(_points("1", "2", "2") + _point("3", text="New"))})
    assert _found(repo) == []

    repo.write({RECORD: _record(_points("1", "2", "2", "3", "3"))})
    assert _found(repo) == [("error", f"{RECORD}#3")]
    assert "the change adds a duplicate id. 2 headings take `3`" in _messages(repo)[0]


def test_a_refused_heading_form_the_change_adds_fails_and_one_the_base_held_does_not(
    repo: GitRepo,
) -> None:
    _branch(repo, {RECORD: _record(_points("1") + "### 2 - Old\n\nOld.\n\n")})
    repo.write({RECORD: _record(_points("1", "3") + "### 2 - Old\n\nOld.\n\n")})
    assert _found(repo) == []

    repo.write({RECORD: _record(_points("1") + "### 2 - Old\n\nOld.\n\n### 5.1 New\n\nNew.\n\n")})
    assert _found(repo) == [("error", f"{RECORD}#5.1")]
    assert "the change adds the heading `### 5.1 New`" in _messages(repo)[0]


def test_a_new_record_whose_every_point_heading_is_refused_fails(repo: GitRepo) -> None:
    """A record with no point heading and no list is still read for refused headings."""
    _branch(repo, {RECORD: _record(_points("1"))})
    other = f"{PROJECT}/PRJ-002-b.md"
    repo.write({other: _record("### 1 — A\n\nA.\n\n### 2 — B\n\nB.\n\n", record_id="PRJ-002")})

    assert _found(repo) == [("error", f"{other}#1"), ("error", f"{other}#2")]


def test_a_prose_decision_that_gains_a_refused_heading_fails(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record("")})
    repo.write({RECORD: _record("### 1 — A\n\nA.\n\n")})
    assert _found(repo) == [("error", f"{RECORD}#1")]


def test_a_refused_heading_the_base_held_without_point_headings_passes(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record("### 1 — A\n\nA.\n\n")})
    repo.write({RECORD: _record("### 1 — A\n\nA, edited.\n\n")})
    assert _found(repo) == []


def test_a_headed_record_turned_back_into_a_list_drops_every_id(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2"))})
    repo.write({RECORD: _record("1. **Point 1.** Text of 1.\n2. **Point 2.** Text of 2.\n\n")})

    assert _found(repo) == [("error", f"{RECORD}#1"), ("error", f"{RECORD}#2")]


def test_a_retired_id_without_its_stub_and_a_stub_without_its_entry_fail(
    repo: GitRepo,
) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2", "3"))})
    repo.write(
        {
            RECORD: _record(
                _points("1", "3") + _stub("4", "Its content is in point 1."),
                extra='retired-points:\n  "2": ["3"]\n',
            )
        }
    )

    found = _found(repo)

    assert ("error", f"{RECORD}#2") in found
    assert ("error", f"{RECORD}#4") in found
    messages = _messages(repo)
    assert any("retired point `2` has no stub at the head" in m for m in messages)
    assert any("the stub of `4` at line" in m and "has no entry" in m for m in messages)


def test_the_stub_is_held_to_its_entry_through_hold_stubs(
    repo: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check reads a record through `read_points` and holds its stubs through
    `hold_stubs`, as validation does (#1414)."""
    _branch(repo, {RECORD: _record(_points("1", "2"))})
    repo.write({RECORD: _record(_points("1", "2", "3"))})
    calls: list[str] = []
    read, hold = record_points.read_points, record_points.hold_stubs

    def reading(text: str) -> record_points.RecordPoints:
        calls.append("read_points")
        return read(text)

    def holding(points: record_points.RecordPoints) -> tuple[record_points.StubMismatch, ...]:
        calls.append("hold_stubs")
        return hold(points)

    monkeypatch.setattr(record_points, "read_points", reading)
    monkeypatch.setattr(record_points, "hold_stubs", holding)
    _found(repo)

    assert calls == ["read_points", "read_points", "hold_stubs"]


def test_a_new_entry_whose_successor_is_no_live_point_fails(repo: GitRepo) -> None:
    retired = 'retired-points:\n  "3": []\n'
    stub3 = _stub("3", "Its content is in no other point.")
    _branch(repo, {RECORD: _record(_points("1", "2") + stub3, extra=retired)})
    entries = 'retired-points:\n  "2": ["3"]\n  "3": []\n'
    stub2 = _stub("2", "Its content is in point 3.")
    repo.write({RECORD: _record(_points("1") + stub2 + stub3, extra=entries)})

    assert _found(repo) == [("error", f"{RECORD}#2")]
    assert "names `3`, which is no live point at the head" in _messages(repo)[0]

    entries = 'retired-points:\n  "2": ["1"]\n  "3": []\n'
    stub2 = _stub("2", "Its content is in point 1.")
    repo.write({RECORD: _record(_points("1") + stub2 + stub3, extra=entries)})
    assert _found(repo) == []


# --- a record in list form, and its conversion ---------------------------------------


_LIST = "1. **First.** One.\n2. **Second.** Two.\n3. **Third.** Three.\n\n"


def test_a_point_added_to_a_record_in_list_form_warns_and_an_edit_does_not(
    repo: GitRepo,
) -> None:
    _branch(repo, {RECORD: _record(_LIST)})
    repo.write({RECORD: _record(_LIST.replace("Two.", "Two, edited."))})
    assert _found(repo) == []

    repo.write({RECORD: _record(_LIST.replace("3. **Third.**", "3. **New.** New.\n4. **Third.**"))})
    assert _found(repo) == [("warning", RECORD)]
    message = _messages(repo)[0]
    assert "PRJ-001 is in list form, and the change adds a point" in message
    assert "refining rule lets the list keep working" in message
    assert "convert the record to point headings by hand" in message
    result = _run()
    assert result.exit_code == 0, result.output


def test_a_new_record_in_list_form_warns(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1"))})
    other = f"{PROJECT}/PRJ-002-b.md"
    repo.write({other: _record(_LIST, record_id="PRJ-002")})

    assert _found(repo) == [("warning", other)]
    assert "PRJ-002 is a new record in list form" in _messages(repo)[0]


def test_a_conversion_keeping_every_number_passes(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_LIST)})
    converted = (
        "### 1. First\n\nOne.\n\n### 2. Second\n\nTwo.\n\n### 3. Third\n\nThree.\n\n"
        "### 4. Fourth\n\nNew.\n\n"
    )
    repo.write({RECORD: _record(converted)})
    assert _found(repo) == []


def test_a_converted_point_whose_id_differs_from_its_items_number_fails(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_LIST)})
    converted = "### 1. First\n\nOne.\n\n### 2. Second\n\nTwo.\n\n### 4. Third\n\nThree.\n\n"
    repo.write({RECORD: _record(converted)})

    assert _found(repo) == [("error", f"{RECORD}#4")]
    assert "comes from the numbered item that showed `3`" in _messages(repo)[0]


def test_a_converted_point_whose_id_differs_from_its_bold_number_warns(repo: GitRepo) -> None:
    bold = "**1. First.** One.\n\n**2. Second.** Two.\n\n"
    _branch(repo, {RECORD: _record(bold)})
    repo.write({RECORD: _record("### 1. First\n\nOne.\n\n### 3. Second\n\nTwo.\n\n")})

    assert _found(repo) == [("warning", f"{RECORD}#3")]
    assert "opened with the bold `2`" in _messages(repo)[0]


def test_an_untitled_list_converted_with_its_numbers_passes(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record("1. First text.\n2. Second text.\n\n")})
    converted = "### 1. First\n\nFirst text.\n\n### 2. Second\n\nSecond text.\n\n"
    repo.write({RECORD: _record(converted)})
    assert _found(repo) == []


def test_an_untitled_items_words_under_another_id_fail_the_conversion(repo: GitRepo) -> None:
    """The item a point came from is the one whose words it holds, never the one with
    its id: a point inserted under `3` moves the third item's words to `4`."""
    _branch(repo, {RECORD: _record("1. First text.\n2. Second text.\n3. Third text.\n\n")})
    converted = (
        "### 1. First\n\nFirst text.\n\n### 2. Second\n\nSecond text.\n\n"
        "### 3. Inserted\n\nNew text.\n\n### 4. Third\n\nThird text.\n\n"
    )
    repo.write({RECORD: _record(converted)})

    assert _found(repo) == [("error", f"{RECORD}#4")]
    assert "point `4` comes from the numbered item that showed `3`" in _messages(repo)[0]


def test_a_retitled_items_words_under_another_id_fail_the_conversion(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record("1. **A.** One.\n2. **B.** Two.\n\n")})
    converted = "### 1. A\n\nOne.\n\n### 2. Inserted\n\nNew.\n\n### 3. B renamed\n\nTwo.\n\n"
    repo.write({RECORD: _record(converted)})

    assert ("error", f"{RECORD}#3") in _found(repo)
    assert any(
        "point `3` comes from the numbered item that showed `2`" in m for m in _messages(repo)
    )


def test_a_bold_number_conversion_keeping_its_ids_passes(repo: GitRepo) -> None:
    bold = "**1. First.** One.\n\nMore of one.\n\n**2. Second.** Two.\n\n"
    _branch(repo, {RECORD: _record(bold)})
    converted = "### 1. First\n\nOne.\n\nMore of one.\n\n### 2. Second\n\nTwo.\n\n"
    repo.write({RECORD: _record(converted)})
    assert _found(repo) == []


def test_a_conversion_that_drops_a_list_point_fails(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_LIST)})
    repo.write({RECORD: _record("### 1. First\n\nOne.\n\n### 2. Second\n\nTwo.\n\n")})

    assert _found(repo) == [("error", f"{RECORD}#3")]
    assert "the branch point's list holds `3`" in _messages(repo)[0]


# --- what the default branch took meanwhile ------------------------------------------


def test_a_point_id_the_default_branch_took_meanwhile_fails(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2"))})
    theirs = _point("3", title="Theirs", text="Theirs")
    _land(repo, {RECORD: _record(_points("1", "2") + theirs)})
    repo.write({RECORD: _record(_points("1", "2") + _point("3", title="Ours", text="Ours"))})

    assert _found(repo) == [("error", f"{RECORD}#3")]
    message = _messages(repo)[0]
    assert "another change took `3` on main since this branch left it" in message
    assert "the next unused, `4`" in message
    assert "If the point is a parent branch's that landed, merge main in instead" in message


def test_the_ids_the_default_branch_took_pass_when_the_change_takes_none(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2"))})
    _land(repo, {RECORD: _record(_points("1", "2") + _point("3", text="Theirs"))})
    repo.write({RECORD: _record(_point("1", text="Edited") + _points("2"))})

    assert _found(repo) == []


def test_a_parents_point_landed_on_the_default_branch_is_no_clash(repo: GitRepo) -> None:
    """A stacked branch is not failed for its parent's ids: the tip holds them with the
    very text the head does."""
    _branch(repo, {RECORD: _record(_points("1", "2"))})
    _land(repo, {RECORD: _record(_points("1", "2") + _point("3", text="Parent's"))})
    repo.write({RECORD: _record(_points("1", "2") + _point("3", text="Parent's") + _points("4"))})

    assert _found(repo) == []


def test_a_parents_point_edited_since_it_landed_is_no_clash(repo: GitRepo) -> None:
    """The tip holds the parent's point under its title, with text edited since on
    either side: still this change's own work, landed."""
    _branch(repo, {RECORD: _record(_points("1", "2"))})
    _land(repo, {RECORD: _record(_points("1", "2") + _point("3", text="Edited on main"))})
    repo.write({RECORD: _record(_points("1", "2") + _point("3", text="Edited here"))})

    assert _found(repo) == []


def test_a_record_id_the_default_branch_took_meanwhile_fails(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1"))})
    _land(repo, {f"{PROJECT}/PRJ-002-theirs.md": _record(_points("1"), record_id="PRJ-002")})
    ours = f"{PROJECT}/PRJ-002-ours.md"
    repo.write({ours: _record(_points("1"), record_id="PRJ-002")})

    assert _found(repo) == [("error", ours)]
    message = _messages(repo)[0]
    assert "another change took the record id `PRJ-002` on main" in message
    assert f"`{PROJECT}/PRJ-002-theirs.md`" in message
    assert "renumber this record to `PRJ-003`" in message


def test_a_record_the_default_branch_holds_at_its_own_path_is_no_clash(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1"))})
    ours = f"{PROJECT}/PRJ-002-ours.md"
    _land(repo, {ours: _record(_points("1"), record_id="PRJ-002")})
    repo.write({ours: _record(_points("1"), record_id="PRJ-002")})

    assert _found(repo) == []


# --- which records, and the command ---------------------------------------------------


def test_a_record_renamed_by_the_change_keeps_its_pair(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2"))})
    repo.git("mv", RECORD, f"{PROJECT}/PRJ-001-renamed.md")
    repo.write({f"{PROJECT}/PRJ-001-renamed.md": _record(_points("1", "2", "3"))})

    assert _found(repo) == []


def test_every_id_space_is_read(repo: GitRepo) -> None:
    capability = ".pkit/capabilities/alpha/decisions/DEC-001-a.md"
    core = ".pkit/decisions/core/COR-001-a.md"
    _branch(
        repo,
        {
            capability: _record(_points("1", "2"), record_id="DEC-001"),
            core: _record(_points("1", "2"), record_id="COR-001"),
        },
    )
    repo.write(
        {
            capability: _record(_points("1"), record_id="DEC-001"),
            core: _record(_points("2"), record_id="COR-001"),
        }
    )

    assert _found(repo) == [("error", f"{capability}#2"), ("error", f"{core}#1")]


def test_a_synced_copy_is_skipped_and_the_projects_own_record_is_checked(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The project cannot mend a record it receives by sync, which is checked where it
    is authored (COR-058 point 8)."""
    adopter = make_adopter_repo()
    monkeypatch.chdir(adopter.root)
    monkeypatch.delenv("PKIT_CHECK_BASE", raising=False)
    core = ".pkit/decisions/core/COR-900-a.md"
    own = f"{PROJECT}/PRJ-900-a.md"
    adopter.commit(
        "install",
        {
            core: _record(_points("1", "2"), record_id="COR-900"),
            own: _record(_points("1", "2"), record_id="PRJ-900"),
        },
    )
    adopter.checkout("change", create=True)
    adopter.write(
        {
            core: _record(_points("1"), record_id="COR-900"),
            own: _record(_points("1"), record_id="PRJ-900"),
        }
    )

    result = _run()

    assert result.exit_code == 1
    assert f"{own}#2" in result.output
    assert core not in result.output


def test_the_command_fails_on_an_error_naming_the_record_and_the_id(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2"))})
    repo.write({RECORD: _record(_points("1"))})

    result = _run()

    assert result.exit_code == 1
    assert "Compared 1 decision record(s) with main" in result.output
    assert f"error    {RECORD}#2" in result.output
    assert "PRJ-001: the branch point holds `2`" in result.output
    assert "1 error(s) in the change's numbering found." in result.output


def test_it_passes_on_the_default_branch(repo: GitRepo) -> None:
    repo.commit("records", {RECORD: _record(_points("1", "2"))})

    result = _run()

    assert result.exit_code == 0, result.output
    assert "No decision record differs from main" in result.output


def test_it_reads_its_base_through_the_default_branch_declaration_and_the_override(
    repo: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _branch(repo, {RECORD: _record(_points("1", "2"))})
    repo.commit("drop", {RECORD: _record(_points("1"))})
    repo.checkout("trunk", create=True)
    repo.checkout("change")
    repo.commit(
        "declare",
        {".pkit/project/config.yaml": "repository:\n  default-branch: trunk\n"},
    )

    assert "No decision record differs from trunk" in _run().output  # the declaration
    assert f"{RECORD}#2" in _run("--base", "main").output  # a base named for one run
    monkeypatch.setenv("PKIT_CHECK_BASE", "main")
    assert f"{RECORD}#2" in _run().output  # the pipeline's override


def test_a_base_that_resolves_nowhere_refuses_the_run(repo: GitRepo) -> None:
    _branch(repo, {RECORD: _record(_points("1"))})

    result = _run("--base", "nowhere")

    assert result.exit_code == 1
    assert "the base 'nowhere' does not resolve" in result.output


def test_with_no_record_to_check_no_base_is_read(repo: GitRepo) -> None:
    repo.commit("nothing", {"README.md": "x\n"})

    result = _run("--base", "nowhere")

    assert result.exit_code == 0, result.output
    assert "No decision record here to check; no base read." in result.output
