"""The makers' record of drafts and `pkit visual draft` (visual-communication DEC-042 point 7,
DEC-029 points 3 and 4, #3224).

Held here:

- **the digest**: over a text normalised as the command states, so a reflowed text keeps it
  and a changed word, letter case or mark changes it;
- **the schema**: an entry holds a kind, a language and a digest, and refuses a text;
- **whose a text is**: a text that matches its recorded digest is the designer's, and one
  that differs from it, or that the record lists nothing for, is the asker's;
- **the command writes nothing**: no command changes what a brief says (DEC-029 point 4).

The commands run in the test's own process (`tests/in_process.py`).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_checks import deck_project
from tests.test_visual_communication_pipeline import PIECE, PIECE_FOLDER
from tests.visual_communication_project import bound, importable, write, yaml_text

drafts, files, seam, svg, draft = load(
    "visual-communication",
    "drafts",
    "files",
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


def run(root: Path, *args: str) -> Any:
    return run_main(draft, PIECE, *args, cwd=root)


def recorded(text: str, kind: str = "title") -> dict[str, str]:
    return drafts.entry(kind, "en", text)


def rules_title(root: Path) -> str:
    """The English title of the deck's `rules` slide."""
    return str(
        next(
            s
            for s in drafts.pl.read_piece(root, "visual", PIECE).contents["en"]["slides"]
            if s["id"] == "rules"
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
    assert recorded(rules_title(root))["digest"] in done.stdout
    assert "add to `pages.rules.drafts`" in done.stdout
    assert (root / BRIEF).exists() == before


def test_a_text_that_matches_its_recorded_digest_is_the_designers(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    brief_with(root, rules={"drafts": [recorded(rules_title(root))]})

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
