"""The makers' record of drafts and `pkit visual draft` (visual-communication DEC-070 point 4,
DEC-029 points 3 and 4, #3224).

Held here:

- **the digest**: over a text normalised as the command states, so a reflowed text keeps it
  and a changed word, letter case or mark changes it;
- **the schema**: an entry holds a kind, a language and a digest, and refuses a text;
- **whose a text is**: a text that matches its recorded digest is the designer's, and one
  that differs from it, or that the record lists nothing for, is the asker's;
- **the command writes nothing**: no command changes what a brief says (DEC-029 point 4);
- **a page before the first render**: a piece with no lock yet finds its page under the
  versions its first render would lock, so a draft is digested as it is written (DEC-070
  point 4), and what that render's search refuses refuses the draft;
- **a brief that cannot be read is refused**, with `--check` or without, and never read as
  no brief, so a refused read is never told as whose a text is;
- **the part an entry lies in**: each draft of a piece whose top holds pages, such as a
  deck, even of one page, a lead, a title or a takeaway, lies in its page's part, so one
  named by no page is refused, never taken as the whole piece's, and so is one whose
  piece's top cannot be read; on a piece whose top is a page alone, such as a figure, it is
  the whole piece's (DEC-029 point 3);
- **a page's lead or title that the piece's top holds**, such as a hero's in a one-page
  site's shared header, which is that page's (DEC-068 point 4): named with `--from-top` by
  its key path from the content's top, its entry given for its page's part and checked
  there as an entry of the page's own content is, and a key path from the top that leads
  into the pages refused (#3418).

The commands run in the test's own process (`tests/in_process.py`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_checks import deck_project, slides
from tests.test_visual_communication_pipeline import PIECE, PIECE_FOLDER, drawing_project
from tests.test_visual_communication_site import site_location
from tests.visual_communication_project import bound, importable, project, write, yaml_text

drafts, files, reading, seam, svg, draft = load(
    "visual-communication",
    "drafts",
    "files",
    "reading",
    "plugins.seam",
    "plugins.svg",
    "draft.py",
)

BRIEF = f"{PIECE_FOLDER}/brief.yaml"
TITLE = ["--kind", "title", "--language", "en", "--page", "rules", "--at", "title"]
TAKEAWAY = ["--kind", "takeaway", "--language", "en", "--page", "cover"]


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    importable(monkeypatch, svg)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)


def brief_with(root: Path, **pages: Any) -> Path:
    return write(root / BRIEF, yaml_text(bound("brief", pages=pages)))


def with_piece_fields(root: Path, **fields: Any) -> None:
    """The piece's `piece.yaml` with each of `fields` set, or taken out where it is None."""
    path = root / PIECE_FOLDER / "piece.yaml"
    data = dict(reading.read_yaml(path))
    for key, value in fields.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    write(path, yaml_text(data))


def run(root: Path, *args: str, piece: str = PIECE) -> Any:
    return run_main(draft, piece, *args, cwd=root)


def recorded(text: str, kind: str = "title") -> dict[str, str]:
    return drafts.entry(kind, "en", text)


def slide_title(root: Path, slide: str = "rules") -> str:
    """The English title of the deck's slide `slide`."""
    return str(
        next(
            s
            for s in drafts.pl.read_piece(root, "visual", PIECE).contents["en"]["slides"]
            if s["id"] == slide
        )["title"]
    )


# --- the digest ---------------------------------------------------------------------------------


def test_a_digest_is_over_the_text_with_its_white_space_made_one_space_and_its_ends_trimmed() -> (
    None
):
    assert drafts.digest("Plan  the\n  work. ") == drafts.digest("Plan the work.")
    assert drafts.digest("Plan the work.").startswith("sha256:")


def test_a_changed_word_case_or_mark_changes_the_digest() -> None:
    base = drafts.digest("Plan the work.")
    for changed in ("Plan the work", "plan the work.", "Plan a work."):
        assert drafts.digest(changed) != base


def test_text_in_two_forms_of_one_letter_has_one_digest() -> None:
    assert drafts.digest("café") == drafts.digest("café")


# --- the schema ---------------------------------------------------------------------------------


def test_the_record_holds_a_kind_a_language_and_a_digest_and_refuses_a_text() -> None:
    entry = recorded("Plan the work.")
    part = {"drafts": [entry]}
    assert files.shape_problems(bound("brief", piece=part), "brief") == []
    assert files.shape_problems(bound("brief", pages={"a": part}), "brief") == []
    with_text = {"drafts": [{**entry, "text": "Plan the work."}]}
    assert files.shape_problems(bound("brief", piece=with_text), "brief") != []
    bad = {"drafts": [{**entry, "digest": "Plan the work."}]}
    assert files.shape_problems(bound("brief", piece=bad), "brief") != []
    other = {"drafts": [{**entry, "kind": "goal"}]}
    assert files.shape_problems(bound("brief", piece=other), "brief") != []


# --- whose a text is ----------------------------------------------------------------------------


def test_the_command_prints_the_digest_of_the_text_it_reads_and_writes_nothing(
    tmp_path: Path,
) -> None:
    root = deck_project(tmp_path)
    before = (root / BRIEF).exists()

    done = run(root, *TITLE)

    assert done.returncode == 0, done.stderr
    assert recorded(slide_title(root))["digest"] in done.stdout
    assert "add to `pages.rules.drafts`" in done.stdout
    assert (root / BRIEF).exists() == before


def test_a_text_that_matches_its_recorded_digest_is_the_designers(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    brief_with(root, rules={"drafts": [recorded(slide_title(root))]})

    done = run(root, *TITLE, "--check")

    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("matches")


def test_a_recorded_drafts_text_changed_is_the_askers(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    brief_with(root, rules={"drafts": [recorded("An earlier title.")]})

    done = run(root, *TITLE, "--check")

    assert done.returncode == 3
    assert done.stdout.startswith("differs")
    assert "asker's" in done.stdout


def test_a_text_the_record_lists_nothing_for_is_the_askers(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    brief_with(root, rules={"drafts": [recorded("Whatever.", "lead")]})
    assert run(root, *TITLE, "--check").returncode == 3

    (root / BRIEF).unlink()
    done = run(root, *TITLE, "--check")
    assert done.returncode == 3
    assert done.stdout.startswith("no-entry")


def test_a_takeaway_is_read_from_the_brief_and_its_change_is_the_askers(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    said = "What the talk is about."
    brief_with(root, cover={"takeaway": said, "drafts": [recorded(said, "takeaway")]})
    assert run(root, *TAKEAWAY, "--check").returncode == 0

    brief_with(root, cover={"takeaway": "Another point.", "drafts": [recorded(said, "takeaway")]})
    assert run(root, *TAKEAWAY, "--check").returncode == 3


def test_a_piece_with_no_lock_yet_finds_its_page_as_its_first_render_would(
    tmp_path: Path,
) -> None:
    root = deck_project(tmp_path)
    locked = run(root, *TITLE)
    with_piece_fields(root, lock=None)

    done = run(root, *TITLE)

    assert done.returncode == 0, done.stderr
    assert done.stdout == locked.stdout


def test_a_pinned_draft_with_no_lock_is_refused_as_its_render_is(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    with_piece_fields(root, lock=None, pinned=True)

    done = run(root, *TITLE)

    assert done.returncode == 1
    assert "unpin it for its first render" in done.stderr


def test_a_draft_is_refused_where_the_text_cannot_be_found(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    for args in (
        ["--kind", "title", "--language", "en", "--page", "nope", "--at", "title"],
        ["--kind", "title", "--language", "en", "--page", "rules", "--at", "nothing"],
        ["--kind", "title", "--language", "en", "--page", "rules"],
        ["--kind", "title", "--language", "de", "--page", "rules", "--at", "title"],
        TAKEAWAY,
    ):
        done = run(root, *args)
        assert done.returncode == 1, args
        assert "error:" in done.stderr


def test_a_brief_that_cannot_be_read_is_refused_never_read_as_no_brief(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    unbound = yaml_text({"piece": {"takeaway": "What the talk is about."}})
    for brief in ("pages: [unclosed\n", unbound):
        write(root / BRIEF, brief)
        for args in (TITLE, [*TITLE, "--check"], TAKEAWAY, [*TAKEAWAY, "--check"]):
            done = run(root, *args)
            assert done.returncode == 1, (brief, args)
            assert "brief.yaml" in done.stderr, (brief, args)


# --- the part an entry lies in ------------------------------------------------------------------


def one_page_deck(tmp_path: Path) -> Path:
    """The deck with its cover alone: a piece of one page, whose top still holds pages."""
    return deck_project(tmp_path, **{language: slides(language)[:1] for language in ("en", "cs")})


#: The decks a draft named by no page is refused on: of several pages, and of one.
DECKS = pytest.mark.parametrize("deck", [deck_project, one_page_deck], ids=["several", "one"])


@DECKS
def test_a_lead_or_a_title_of_a_piece_whose_top_holds_pages_named_by_no_page_is_refused(
    tmp_path: Path, deck: Callable[[Path], Path]
) -> None:
    root = deck(tmp_path)
    cover = recorded(slide_title(root, "cover"))
    write(root / BRIEF, yaml_text(bound("brief", piece={"drafts": [cover]})))
    for kind in ("lead", "title"):
        named = ["--kind", kind, "--language", "en", "--at", "slides[cover].title"]
        for args in (named, [*named, "--check"]):
            done = run(root, *args)
            assert done.returncode == 1, args
            assert f"a {kind} of a piece whose top holds pages" in done.stderr, args
            assert "even of one page, lies in its page's part" in done.stderr, args
            assert "--page" in done.stderr, args
            assert done.stdout == "", args


@DECKS
def test_a_takeaway_of_a_piece_whose_top_holds_pages_named_by_no_page_is_refused(
    tmp_path: Path, deck: Callable[[Path], Path]
) -> None:
    root = deck(tmp_path)
    said = "What the talk is about."
    write(
        root / BRIEF,
        yaml_text(bound("brief", piece={"takeaway": said, "drafts": [recorded(said, "takeaway")]})),
    )
    whole = ["--kind", "takeaway", "--language", "en"]
    for args in (whole, [*whole, "--check"]):
        done = run(root, *args)
        assert done.returncode == 1, args
        assert "a takeaway of a piece whose top holds pages" in done.stderr, args
        assert "even of one page, lies in its page's part" in done.stderr, args
        assert "--page" in done.stderr, args
        assert done.stdout == "", args


def test_a_draft_of_a_piece_whose_top_is_a_page_alone_named_by_no_page_is_the_whole_pieces(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path)
    said = "What the figure shows."
    caption = ["--kind", "lead", "--language", "en", "--at", "caption"]
    whole = ["--kind", "takeaway", "--language", "en"]

    lead = run(root, *caption)

    assert lead.returncode == 0, lead.stderr
    assert "add to `piece.drafts`" in lead.stdout
    entries = [recorded("The flow.", "lead"), recorded(said, "takeaway")]
    assert entries[0]["digest"] in lead.stdout
    write(root / BRIEF, yaml_text(bound("brief", piece={"takeaway": said, "drafts": entries})))
    taken = run(root, *whole)
    assert taken.returncode == 0, taken.stderr
    assert "add to `piece.drafts`" in taken.stdout
    assert entries[1]["digest"] in taken.stdout
    for args in (caption, whole):
        assert run(root, *args, "--check").returncode == 0, args


def test_a_draft_named_by_no_page_is_refused_where_the_top_cannot_be_read(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False, top="tests/nothing")
    write(root / BRIEF, yaml_text(bound("brief", piece={"takeaway": "What the figure shows."})))

    for args in (
        ["--kind", "lead", "--language", "en", "--at", "body"],
        ["--kind", "takeaway", "--language", "en"],
    ):
        done = run(root, *args)
        assert done.returncode == 1, args
        assert "whether it holds pages cannot be told" in done.stderr, args


def test_a_top_holds_pages_where_its_layouts_are_their_forms_or_a_slot_of_one_holds_them() -> None:
    forms = {"fields": {"properties": {"slides": {"type": "array", "x-pkit-pages": True}}}}
    slot = {"layouts": {"site": {"slots": {"pages": {"pages": True}, "header": {}}}}}
    alone = {"layouts": {"frame": {"slots": {"body": {}, "caption": {}}}}}
    assert drafts.holds_pages(forms)
    assert drafts.holds_pages(slot)
    assert not drafts.holds_pages(alone)
    assert not drafts.holds_pages({})


# --- a page's lead or title that the piece's top holds ------------------------------------------

#: The site of one page whose shared header holds its hero, so the hero's heading is the
#: page's title and its text the page's lead (DEC-068 point 4).
SITE = "page"
SITE_FOLDER = f"visual/pieces/{SITE}"
HERO = ["--language", "en", "--page", "home", "--from-top"]
HERO_TITLE = ["--kind", "title", *HERO, "--at", "header.head"]
HERO_LEAD = ["--kind", "lead", *HERO, "--at", "header.text"]


def one_page_site(tmp_path: Path) -> Path:
    return site_location(project(tmp_path))


def hero(root: Path, field: str = "head") -> str:
    """The English text of the field `field` of the site's shared header."""
    return str(drafts.pl.read_piece(root, "visual", SITE).contents["en"]["header"][field])


def site_brief(root: Path, **parts: Any) -> Path:
    return write(root / SITE_FOLDER / "brief.yaml", yaml_text(bound("brief", **parts)))


def test_a_title_the_pieces_top_holds_is_read_from_the_contents_top_for_its_pages_part(
    tmp_path: Path,
) -> None:
    root = one_page_site(tmp_path)

    done = run(root, *HERO_TITLE, piece=SITE)

    assert done.returncode == 0, done.stderr
    assert recorded(hero(root))["digest"] in done.stdout
    assert "add to `pages.home.drafts`" in done.stdout
    assert not (root / SITE_FOLDER / "brief.yaml").exists()


def test_a_lead_or_a_title_the_pieces_top_holds_is_checked_in_its_pages_part(
    tmp_path: Path,
) -> None:
    """Its entry lies in the page's part, as an entry of the page's own content does, so one
    in the part for the whole piece is no entry of it."""
    root = one_page_site(tmp_path)
    entries = [recorded(hero(root)), recorded(hero(root, "text"), "lead")]
    site_brief(root, pages={"home": {"drafts": entries}})
    for args in (HERO_TITLE, HERO_LEAD):
        done = run(root, *args, "--check", piece=SITE)
        assert done.returncode == 0, (args, done.stderr)
        assert done.stdout.startswith("matches"), args

    site_brief(root, pages={"home": {"drafts": [recorded("An earlier name.")]}})
    done = run(root, *HERO_TITLE, "--check", piece=SITE)
    assert done.returncode == 3
    assert done.stdout.startswith("differs")
    assert "asker's" in done.stdout

    site_brief(root, piece={"drafts": entries})
    for args in (HERO_TITLE, HERO_LEAD):
        done = run(root, *args, "--check", piece=SITE)
        assert done.returncode == 3, args
        assert done.stdout.startswith("no-entry"), args


def test_without_from_top_the_key_path_of_a_text_the_pieces_top_holds_is_read_from_the_page(
    tmp_path: Path,
) -> None:
    root = one_page_site(tmp_path)
    from_page = [arg for arg in HERO_TITLE if arg != "--from-top"]

    done = run(root, *from_page, piece=SITE)

    assert done.returncode == 1
    assert "`header.head` names `header`, which the content does not give there" in done.stderr


def test_a_key_path_from_the_contents_top_that_leads_into_the_pages_is_refused(
    tmp_path: Path,
) -> None:
    """It names a page's own content, which is named from its page, so its entry never lies
    in another page's part."""
    site = one_page_site(tmp_path)
    deck = deck_project(tmp_path / "deck")
    from_deck = ["--kind", "title", "--language", "en", "--page", "rules", "--from-top"]
    for root, piece, args in (
        (site, SITE, ["--kind", "title", *HERO, "--at", "pages[home].main.head"]),
        (deck, PIECE, [*from_deck, "--at", "slides[cover].title"]),
    ):
        for given in (args, [*args, "--check"]):
            done = run(root, *given, piece=piece)
            assert done.returncode == 1, given
            assert "leads into the pages, so it names a page's own content" in done.stderr
            assert done.stdout == "", given


def test_a_text_the_pieces_top_holds_is_refused_for_a_page_the_content_does_not_hold(
    tmp_path: Path,
) -> None:
    root = one_page_site(tmp_path)
    args = ["--kind", "title", "--language", "en", "--page", "nope", "--from-top"]

    done = run(root, *args, "--at", "header.head", piece=SITE)

    assert done.returncode == 1
    assert "holds no page `nope`" in done.stderr


def test_on_a_piece_whose_top_is_a_page_alone_from_top_reads_the_key_path_as_before(
    tmp_path: Path,
) -> None:
    """Named by no page, the key path starts at the content's top already."""
    root = drawing_project(tmp_path)
    caption = ["--kind", "lead", "--language", "en", "--at", "caption"]

    done = run(root, *caption, "--from-top")

    assert done.returncode == 0, done.stderr
    assert done.stdout == run(root, *caption).stdout
